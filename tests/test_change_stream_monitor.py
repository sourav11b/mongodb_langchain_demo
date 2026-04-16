"""
Tests for tools/change_stream_monitor.py

Uses mocks to simulate MongoDB change streams — no real Atlas required.
"""

import threading
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from tools.change_stream_monitor import ChangeEvent, ChangeStreamMonitor


# ── Unit tests for ChangeEvent ──────────────────────────────────────────────
class TestChangeEvent:
    def test_create_basic(self):
        ev = ChangeEvent(
            label="test",
            collection="transactions",
            operation="insert",
            document_key={"_id": "abc"},
            timestamp=datetime.now(timezone.utc),
        )
        assert ev.label == "test"
        assert ev.collection == "transactions"
        assert ev.operation == "insert"
        assert ev.agent_result is None
        assert ev.error is None

    def test_with_agent_result(self):
        ev = ChangeEvent(
            label="x", collection="c", operation="insert",
            document_key={}, timestamp=datetime.now(timezone.utc),
            agent_result={"answer": "fraud detected"},
        )
        assert ev.agent_result["answer"] == "fraud detected"


# ── Unit tests for ChangeStreamMonitor ──────────────────────────────────────
class TestChangeStreamMonitor:
    def test_watch_registers_watcher(self):
        m = ChangeStreamMonitor("mongodb://fake", "testdb")
        m.watch(collection="txns", label="w1")
        assert len(m._watchers) == 1
        assert m._watchers[0]["collection"] == "txns"
        assert m._watchers[0]["label"] == "w1"

    def test_watch_multiple(self):
        m = ChangeStreamMonitor("mongodb://fake", "testdb")
        m.watch(collection="txns", label="w1")
        m.watch(collection="offers", label="w2")
        assert len(m._watchers) == 2

    def test_drain_empty(self):
        m = ChangeStreamMonitor("mongodb://fake", "testdb")
        events = m.drain()
        assert events == []

    def test_drain_returns_and_clears(self):
        m = ChangeStreamMonitor("mongodb://fake", "testdb")
        ev = ChangeEvent("t", "c", "insert", {}, datetime.now(timezone.utc))
        m._events.append(ev)
        assert m.event_count() == 1
        events = m.drain()
        assert len(events) == 1
        assert events[0].label == "t"
        assert m.event_count() == 0  # cleared

    def test_stop_without_start(self):
        """Stop on a never-started monitor should not raise."""
        m = ChangeStreamMonitor("mongodb://fake", "testdb")
        m.stop()
        assert not m.is_running

    @patch("tools.change_stream_monitor.MongoClient")
    def test_watch_loop_processes_change(self, MockClient):
        """Simulate a change stream yielding one document, verify event is captured."""
        # Set up the mock change stream
        fake_change = {
            "operationType": "insert",
            "documentKey": {"_id": "doc_001"},
            "fullDocument": {
                "cardholder_id": "CH_TEST",
                "amount": 9999,
                "fraud_score": 0.95,
                "is_flagged": True,
            },
        }

        # Mock the stream context manager
        mock_stream = MagicMock()
        # First call returns the change, second returns None (to allow loop to check stop)
        mock_stream.try_next = MagicMock(side_effect=[fake_change, None, None, None])
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)

        mock_coll = MagicMock()
        mock_coll.watch.return_value = mock_stream
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_coll)
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        MockClient.return_value = mock_client

        # Callback that returns a result dict
        def my_callback(change_doc, db):
            full_doc = change_doc.get("fullDocument", {})
            return {"cardholder_id": full_doc.get("cardholder_id"), "detected": True}

        monitor = ChangeStreamMonitor("mongodb://fake", "testdb")
        monitor.watch(
            collection="transactions",
            pipeline=[{"$match": {"operationType": "insert"}}],
            callback=my_callback,
            label="fraud-test",
        )
        monitor.start()

        # Wait for background thread to process the change
        time.sleep(2)
        monitor.stop()

        events = monitor.drain()
        assert len(events) >= 1, f"Expected at least 1 event, got {len(events)}"

        ev = events[0]
        assert ev.operation == "insert"
        assert ev.collection == "transactions"
        assert ev.label == "fraud-test"
        assert ev.document_key == {"_id": "doc_001"}
        assert ev.agent_result is not None
        assert ev.agent_result["cardholder_id"] == "CH_TEST"
        assert ev.agent_result["detected"] is True
        assert ev.error is None

    @patch("tools.change_stream_monitor.MongoClient")
    def test_callback_error_captured(self, MockClient):
        """If callback raises, error is stored on the event."""
        fake_change = {
            "operationType": "insert",
            "documentKey": {"_id": "err_doc"},
            "fullDocument": {},
        }
        mock_stream = MagicMock()
        mock_stream.try_next = MagicMock(side_effect=[fake_change, None, None])
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)

        def bad_callback(change_doc, db):
            raise ValueError("Agent crashed!")

        monitor = ChangeStreamMonitor("mongodb://fake", "testdb")
        monitor.watch(collection="txns", callback=bad_callback, label="err-test")
        monitor.start()
        time.sleep(2)
        monitor.stop()

        events = monitor.drain()
        assert len(events) >= 1
        ev = events[0]
        assert ev.error is not None
        assert "Agent crashed" in ev.error
        assert ev.agent_result is None

    @patch("tools.change_stream_monitor.MongoClient")
    def test_no_callback_still_captures_event(self, MockClient):
        """Even without a callback, events should be captured."""
        fake_change = {
            "operationType": "update",
            "documentKey": {"_id": "upd_001"},
            "fullDocument": {"status": "blocked"},
        }
        mock_stream = MagicMock()
        mock_stream.try_next = MagicMock(side_effect=[fake_change, None, None])
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_coll = MagicMock()
        mock_coll.watch.return_value = mock_stream
        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_coll)
        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        MockClient.return_value = mock_client

        monitor = ChangeStreamMonitor("mongodb://fake", "testdb")
        monitor.watch(collection="offers", label="no-cb")
        # No callback registered
        monitor.start()
        time.sleep(2)
        monitor.stop()

        events = monitor.drain()
        assert len(events) >= 1
        ev = events[0]
        assert ev.operation == "update"
        assert ev.agent_result is None
        assert ev.error is None
