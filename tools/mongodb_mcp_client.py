"""
MongoDB MCP Server client for the VaultIQ Showcase.

Transport modes — controlled by MONGODB_MCP_TRANSPORT in .env
──────────────────────────────────────────────────────────────

  embedded  (default)
      langchain-mcp-adapters spawns the official mongodb-mcp-server as an
      npx stdio subprocess automatically on each agent invocation.
      Zero separate process needed — just Node.js / npx on PATH.

        MONGODB_MCP_TRANSPORT=embedded   ← .env default

  http
      Agent connects to an already-running MongoDB MCP HTTP server.
      Start the server in a separate terminal first:

        MDB_MCP_CONNECTION_STRING="<uri>" \\
        npx -y mongodb-mcp-server@latest \\
          --transport http --httpPort 3001 \\
          --readOnly --disabledTools atlas --telemetry disabled

        MONGODB_MCP_TRANSPORT=http       ← .env to enable

In both modes the same 12 MCP tools are exposed:
  find · aggregate · collection-schema · collection-indexes ·
  collection-storage-size · count · db-stats · explain ·
  list-collections · list-databases · search-knowledge · list-knowledge-sources

If the chosen transport fails the context manager yields [] and agents
automatically fall back to their built-in pymongo tools.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Literal

from langchain_core.tools import BaseTool

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (
    MONGODB_URI,
    MONGODB_MCP_SERVER_URL,
    MONGODB_MCP_TRANSPORT,
    MONGODB_MCP_READ_ONLY,
)

logger = logging.getLogger(__name__)

_DISABLED_TOOLS = "atlas"
TransportMode = Literal["embedded", "http"]


# ── Per-transport connection configs ──────────────────────────────────────────

def _embedded_config() -> dict:
    """
    Stdio transport: langchain-mcp-adapters spawns mongodb-mcp-server
    as an npx subprocess.  The subprocess is started and stopped
    automatically inside each `async with` block.
    Requires Node.js / npx on PATH.
    """
    read_only_args = ["--readOnly"] if MONGODB_MCP_READ_ONLY else []
    return {
        "mongodb": {
            "command": "npx",
            "args": [
                "-y", "mongodb-mcp-server@latest",
                *read_only_args,
                "--disabledTools", _DISABLED_TOOLS,
                "--telemetry", "disabled",
                "--loggers", "stderr",
            ],
            "transport": "stdio",
            "env": {
                "MDB_MCP_CONNECTION_STRING": MONGODB_URI,
                "MDB_MCP_TELEMETRY":         "disabled",
                "MDB_MCP_READ_ONLY":         str(MONGODB_MCP_READ_ONLY).lower(),
                "MDB_MCP_DISABLED_TOOLS":    _DISABLED_TOOLS,
            },
        }
    }


def _http_config() -> dict:
    """
    HTTP transport: connects to a mongodb-mcp-server process already
    running at MONGODB_MCP_SERVER_URL.  Stateless per-request HTTP.
    """
    return {
        "mongodb": {
            "url":       f"{MONGODB_MCP_SERVER_URL}/mcp",
            "transport": "streamable_http",
        }
    }


def _config_for(mode: TransportMode) -> dict:
    return _embedded_config() if mode == "embedded" else _http_config()


# ── Main entry point ──────────────────────────────────────────────────────────

@asynccontextmanager
async def run_with_mongodb_mcp_tools(
    transport: TransportMode | None = None,
) -> AsyncIterator[list[BaseTool]]:
    """
    Async context manager that yields LangChain-compatible MongoDB MCP tools.

    Parameters
    ----------
    transport : "embedded" | "http" | None
        Override the transport for this call.
        Defaults to the MONGODB_MCP_TRANSPORT env var (default: "embedded").

    Yields
    ------
    list[BaseTool]
        MCP tools ready to use in a LangGraph agent, or [] if unavailable.

    Usage
    -----
        async with run_with_mongodb_mcp_tools() as mcp_tools:
            all_tools = mcp_tools + native_tools
            result = await agent.ainvoke(...)
    """
    from langchain_mcp_adapters.client import MultiServerMCPClient

    mode: TransportMode = transport or MONGODB_MCP_TRANSPORT  # type: ignore[assignment]
    if mode not in ("embedded", "http"):
        logger.warning(
            f"Unknown MONGODB_MCP_TRANSPORT='{mode}'. "
            "Defaulting to 'embedded'. Valid values: embedded | http"
        )
        mode = "embedded"

    config = _config_for(mode)
    transport_label = "embedded (stdio)" if mode == "embedded" else f"http ({MONGODB_MCP_SERVER_URL})"

    try:
        # langchain-mcp-adapters ≥0.1.0 removed the context-manager protocol.
        # Instantiate directly, then await get_tools(). Keep `client` alive in
        # scope so the underlying MCP subprocess/connection stays open for the
        # entire duration of the yield (agent invocation).
        print(f"[DEBUG][mcp_client] ① Creating MultiServerMCPClient config={list(config.keys())} transport={transport_label}", flush=True)
        client = MultiServerMCPClient(config)
        print(f"[DEBUG][mcp_client] ② Client created. Calling await client.get_tools() — this starts the npx subprocess...", flush=True)
        tools = await client.get_tools()
        print(f"[DEBUG][mcp_client] ③ get_tools() returned {len(tools)} tools: {[t.name for t in tools]}", flush=True)
        logger.info(
            f"MongoDB MCP [{transport_label}]: "
            f"loaded {len(tools)} tools: {[t.name for t in tools]}"
        )
        yield tools
        print(f"[DEBUG][mcp_client] ⑤ Agent finished — MCP context exiting cleanly.", flush=True)
    except Exception as err:
        import traceback as _tb
        print(f"[DEBUG][mcp_client] ✗ EXCEPTION in run_with_mongodb_mcp_tools: {err}", flush=True)
        print(_tb.format_exc(), flush=True)
        logger.warning(
            f"MongoDB MCP [{transport_label}] failed: {err}. "
            "Agents will use pymongo fallback tools."
        )
        yield []


# ── Sync helper (UI display only — tools not invocable after context exits) ───

def load_mongodb_mcp_tools_sync(
    transport: TransportMode | None = None,
) -> list[dict]:
    """
    Synchronous wrapper that loads tool names + descriptions for display.

    Returns list[dict] with 'name' and 'description' keys.
    Do NOT use these objects to invoke tools — the session closes after this
    call.  Use run_with_mongodb_mcp_tools() for actual agent invocation.
    """
    async def _load():
        async with run_with_mongodb_mcp_tools(transport=transport) as tools:
            return [{"name": t.name, "description": t.description} for t in tools]

    try:
        return asyncio.run(_load())
    except RuntimeError:
        import nest_asyncio
        nest_asyncio.apply()
        return asyncio.run(_load())
    except Exception as e:
        logger.warning(f"Could not load MongoDB MCP tool list: {e}")
        return []


def active_transport() -> TransportMode:
    """Return the currently configured transport mode."""
    mode = MONGODB_MCP_TRANSPORT
    return mode if mode in ("embedded", "http") else "embedded"  # type: ignore[return-value]


# ── Tool descriptions (for UI display when server is offline) ─────────────────
MONGODB_MCP_TOOL_DESCRIPTIONS: list[dict] = [
    {"name": "find",                  "description": "Run a find query against any MongoDB collection"},
    {"name": "aggregate",             "description": "Execute an aggregation pipeline (group, sort, lookup, etc.)"},
    {"name": "collection-schema",     "description": "Describe the schema for a collection by sampling documents"},
    {"name": "collection-indexes",    "description": "List all indexes on a collection"},
    {"name": "collection-storage-size","description": "Get storage size in bytes for a collection"},
    {"name": "count",                  "description": "Count documents matching an optional filter"},
    {"name": "db-stats",              "description": "Database-level statistics (size, collections, indexes)"},
    {"name": "explain",               "description": "Return the execution plan for a find or aggregate"},
    {"name": "list-collections",      "description": "List all collections in a database"},
    {"name": "list-databases",        "description": "List all databases on the MongoDB connection"},
    {"name": "search-knowledge",      "description": "Semantic search over MongoDB official documentation"},
    {"name": "list-knowledge-sources","description": "List available MongoDB documentation knowledge sources"},
]
