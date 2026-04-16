"""
MongoDB Change Stream Monitor — real-time event-driven agent triggers.

Watches one or more collections for inserts/updates via Change Streams,
then dispatches events to registered callbacks. Designed for Streamlit
where a background thread feeds results into st.session_state.

Requires MongoDB Atlas (replica set) — Change Streams are not supported
on standalone deployments.

Usage
-----
    monitor = ChangeStreamMonitor(mongo_uri, db_name)
    monitor.watch(
        collection="transactions",
        pipeline=[{"$match": {"operationType": "insert"}}],
        callback=my_handler,
        label="fraud-watcher",
    )
    monitor.start()           # spawns background threads
    events = monitor.drain()  # non-blocking: returns list of events since last drain
    monitor.stop()
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from pymongo import MongoClient
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)


@dataclass
class ChangeEvent:
    """A single change-stream event that has been processed."""
    label: str
    collection: str
    operation: str
    document_key: Any
    timestamp: datetime
    agent_result: dict | None = None
    raw_change: dict = field(default_factory=dict, repr=False)
    error: str | None = None


class ChangeStreamMonitor:
    """Manages background change-stream watchers and collects agent results."""

    def __init__(self, mongo_uri: str, db_name: str):
        self._uri = mongo_uri
        self._db_name = db_name
        self._watchers: list[dict] = []
        self._threads: list[threading.Thread] = []
        self._events: deque[ChangeEvent] = deque(maxlen=200)
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._running = False

    # ── Registration ──────────────────────────────────────────────────────
    def watch(
        self,
        collection: str,
        pipeline: list[dict] | None = None,
        callback: Callable[[dict, Any], dict | None] | None = None,
        label: str = "",
    ):
        """Register a collection to watch.

        ``callback(change_doc, db)`` is called for every matching change.
        It should return a dict (agent result) or None.
        """
        self._watchers.append({
            "collection": collection,
            "pipeline": pipeline or [],
            "callback": callback,
            "label": label or collection,
        })

    # ── Lifecycle ─────────────────────────────────────────────────────────
    def start(self):
        if self._running:
            return
        self._stop.clear()
        self._running = True
        for w in self._watchers:
            t = threading.Thread(
                target=self._watch_loop,
                args=(w,),
                daemon=True,
                name=f"cs-{w['label']}",
            )
            t.start()
            self._threads.append(t)
        logger.info("ChangeStreamMonitor started %d watchers", len(self._threads))

    def stop(self):
        self._stop.set()
        self._running = False
        for t in self._threads:
            t.join(timeout=5)
        self._threads.clear()
        logger.info("ChangeStreamMonitor stopped")

    @property
    def is_running(self) -> bool:
        return self._running and not self._stop.is_set()

    # ── Event access ──────────────────────────────────────────────────────
    def drain(self) -> list[ChangeEvent]:
        """Return all events accumulated since last drain (thread-safe)."""
        with self._lock:
            events = list(self._events)
            self._events.clear()
        return events

    def event_count(self) -> int:
        return len(self._events)

    # ── Internal watcher loop ─────────────────────────────────────────────
    def _watch_loop(self, watcher: dict):
        label = watcher["label"]
        coll_name = watcher["collection"]
        pipeline = watcher["pipeline"]
        callback = watcher["callback"]

        while not self._stop.is_set():
            client = None
            try:
                client = MongoClient(self._uri, serverSelectionTimeoutMS=5000)
                db = client[self._db_name]
                coll = db[coll_name]
                logger.info("[%s] Opening change stream on %s.%s", label, self._db_name, coll_name)

                with coll.watch(pipeline, full_document="updateLookup") as stream:
                    while not self._stop.is_set():
                        change = stream.try_next()
                        if change is None:
                            time.sleep(0.5)
                            continue

                        event = ChangeEvent(
                            label=label,
                            collection=coll_name,
                            operation=op,
                            document_key=doc_key,
                            timestamp=ts,
                            raw_change=change,
                        )

                        # Run the callback (agent invocation) if provided
                        if callback:
                            try:
                                result = callback(change, db)
                                event.agent_result = result
                            except Exception as cb_err:
                                logger.exception("[%s] Callback error: %s", label, cb_err)
                                event.error = str(cb_err)

                        with self._lock:
                            self._events.append(event)

            except PyMongoError as e:
                logger.warning("[%s] Change stream error (will retry in 5s): %s", label, e)
                time.sleep(5)
            except Exception as e:
                logger.exception("[%s] Unexpected error: %s", label, e)
                time.sleep(5)
            finally:
                if client:
                    try:
                        client.close()
                    except Exception:
                        pass
