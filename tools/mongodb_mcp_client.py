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
    MONGODB_DB_NAME,
    MONGODB_MCP_SERVER_URL,
    MONGODB_MCP_TRANSPORT,
    MONGODB_MCP_READ_ONLY,
)

logger = logging.getLogger(__name__)

_DISABLED_TOOLS = "atlas"
TransportMode = Literal["embedded", "http"]


# ── Per-transport connection configs ──────────────────────────────────────────

def _mcp_connection_string() -> str:
    """
    Build MCP connection string with the database name in the URI path.
    The MCP server uses the database from the connection string; without it
    the server defaults to the collection name as the database, causing
    'ns does not exist' errors (e.g. transactions.transactions).
    """
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(MONGODB_URI)
    # Only inject DB name if the path is empty or just "/"
    if parsed.path in ("", "/"):
        parsed = parsed._replace(path=f"/{MONGODB_DB_NAME}")
    return urlunparse(parsed)


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
                "MDB_MCP_CONNECTION_STRING": _mcp_connection_string(),
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

    from langchain_mcp_adapters.tools import load_mcp_tools
    import traceback as _tb

    # ─── Architecture ──────────────────────────────────────────────────────────
    #
    # Three-phase approach prevents the "generator didn't stop" error:
    #   Phase 1 (connect): fail → yield [] → return  (clean single-yield exit)
    #   Phase 2 (load):    fail → close session → yield [] → return
    #   Phase 3 (yield):   agent runs; exceptions propagate; finally closes session
    #
    # We catch BaseException (not just Exception) because anyio wraps subprocess
    # errors in BaseExceptionGroup — a BaseException subclass that slips past
    # plain `except Exception` and crashes the generator.
    # ───────────────────────────────────────────────────────────────────────────

    logger.debug("① Creating MultiServerMCPClient | config=%s | transport=%s",
                 list(config.keys()), transport_label)
    try:
        client = MultiServerMCPClient(config)
        logger.debug("② Entering client.session('mongodb') — spawns npx subprocess...")
        session_cm = client.session("mongodb")
        session = await session_cm.__aenter__()
    except BaseException as err:
        logger.error("✗ MCP connect failed [%s]: %s\n%s",
                     transport_label, err, _tb.format_exc())
        yield []
        return

    # ── Phase 2: load tool definitions ──────────────────────────────────────
    try:
        logger.debug("③ Session open — calling load_mcp_tools(session)...")
        tools = await load_mcp_tools(session)
        logger.info("④ MCP [%s] loaded %d tools: %s",
                    transport_label, len(tools), [t.name for t in tools])
    except BaseException as err:
        logger.error("✗ load_mcp_tools failed [%s]: %s\n%s",
                     transport_label, err, _tb.format_exc())
        try:
            await session_cm.__aexit__(None, None, None)
        except BaseException:
            pass
        yield []
        return

    # ── Phase 3: yield tools — session stays open for agent invocations ─────
    try:
        yield tools
        logger.debug("⑤ Agent finished — MCP session closing cleanly.")
    finally:
        try:
            await session_cm.__aexit__(None, None, None)
        except BaseException:
            logger.debug("  Session cleanup raised (subprocess already dead) — ignored.")


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
