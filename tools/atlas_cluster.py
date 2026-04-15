"""
Atlas Cluster Health — check status, auto-resume paused clusters.

Uses the Atlas Admin API v2 with OAuth2 service-account credentials.
Docs: https://www.mongodb.com/docs/atlas/reference/api-resources-spec/v2/
"""

import logging
import time
import requests
from config import (
    ATLAS_API_CLIENT_ID,
    ATLAS_API_CLIENT_SECRET,
    ATLAS_API_PROJECT_ID,
    ATLAS_API_CLUSTER_NAME,
)

logger = logging.getLogger("vaultiq.atlas_cluster")

_BASE = "https://cloud.mongodb.com/api/atlas/v2"
_TOKEN_URL = "https://cloud.mongodb.com/api/oauth/token"


# ── OAuth2 token ──────────────────────────────────────────────────────────────
_cached_token: dict = {}


def _get_token() -> str:
    """Get (or refresh) an OAuth2 access token via client_credentials grant."""
    now = time.time()
    if _cached_token.get("access_token") and _cached_token.get("expires_at", 0) > now:
        return _cached_token["access_token"]

    resp = requests.post(
        _TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": ATLAS_API_CLIENT_ID,
            "client_secret": ATLAS_API_CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    resp.raise_for_status()
    body = resp.json()
    _cached_token["access_token"] = body["access_token"]
    _cached_token["expires_at"] = now + body.get("expires_in", 3600) - 60
    logger.debug("OAuth2 token acquired (expires in %ds)", body.get("expires_in"))
    return body["access_token"]


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.atlas.2023-02-01+json",
    }


# ── Cluster status ────────────────────────────────────────────────────────────

def is_configured() -> bool:
    """Return True if all Atlas Admin API env vars are set."""
    return all([
        ATLAS_API_CLIENT_ID,
        ATLAS_API_CLIENT_SECRET,
        ATLAS_API_PROJECT_ID,
        ATLAS_API_CLUSTER_NAME,
    ])


def get_cluster_status() -> dict:
    """
    Get cluster status from Atlas Admin API.
    Returns dict with keys: name, stateName, paused, error (if any).
    """
    if not is_configured():
        return {"error": "Atlas Admin API not configured", "stateName": "UNKNOWN", "paused": False}

    url = f"{_BASE}/groups/{ATLAS_API_PROJECT_ID}/clusters/{ATLAS_API_CLUSTER_NAME}"
    try:
        resp = requests.get(url, headers=_headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return {
            "name": data.get("name"),
            "stateName": data.get("stateName", "UNKNOWN"),
            "paused": data.get("paused", False),
        }
    except Exception as e:
        logger.exception("Failed to get cluster status: %s", e)
        return {"error": str(e), "stateName": "UNKNOWN", "paused": False}


def resume_cluster() -> dict:
    """
    Resume a paused cluster by PATCHing { paused: false }.
    Returns updated status dict.
    """
    url = f"{_BASE}/groups/{ATLAS_API_PROJECT_ID}/clusters/{ATLAS_API_CLUSTER_NAME}"
    try:
        resp = requests.patch(url, json={"paused": False}, headers=_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        logger.info("Resume request sent — stateName=%s", data.get("stateName"))
        return {
            "name": data.get("name"),
            "stateName": data.get("stateName"),
            "paused": data.get("paused", False),
        }
    except Exception as e:
        logger.exception("Failed to resume cluster: %s", e)
        return {"error": str(e), "stateName": "UNKNOWN", "paused": True}


def wait_for_ready(max_wait: int = 300, poll_interval: int = 15) -> dict:
    """
    Poll cluster status until stateName is IDLE (ready) or timeout.
    Returns final status dict with extra key 'elapsed'.
    """
    start = time.time()
    while time.time() - start < max_wait:
        status = get_cluster_status()
        logger.debug("Polling cluster: stateName=%s (%.0fs elapsed)",
                     status.get("stateName"), time.time() - start)
        if status.get("stateName") == "IDLE" and not status.get("paused"):
            status["elapsed"] = round(time.time() - start)
            return status
        if status.get("error"):
            status["elapsed"] = round(time.time() - start)
            return status
        time.sleep(poll_interval)

    return {
        "error": f"Cluster not ready after {max_wait}s",
        "stateName": "TIMEOUT",
        "elapsed": max_wait,
    }
