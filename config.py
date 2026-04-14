"""
Central configuration for VaultIQ — NextGen AI Financial Intelligence Suite.
Powered by MongoDB Atlas · LangChain · Azure OpenAI · Voyage AI

All environment variables are loaded here and exported as typed constants.
.env is loaded from the directory containing this file (project root),
so config works correctly regardless of the working directory the app
is launched from.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv

# Always resolve .env relative to this file — safe regardless of CWD.
# override=True ensures that if the app is already running and .env is updated
# (e.g. adding a LangSmith key), the new values are picked up on the next import.
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)

# ── MongoDB ────────────────────────────────────────────────────────────────────
MONGODB_URI: str     = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "vaultiq_fsi")

# Collection names — override via .env for different deployment environments
COLLECTIONS = {
    "transactions":         os.getenv("MONGODB_COLLECTION_TRANSACTIONS",        "transactions"),
    "cardholders":          os.getenv("MONGODB_COLLECTION_CARDHOLDERS",         "cardholders"),
    "merchants":            os.getenv("MONGODB_COLLECTION_MERCHANTS",           "merchants"),
    "offers":               os.getenv("MONGODB_COLLECTION_OFFERS",              "offers"),
    "data_catalog":         os.getenv("MONGODB_COLLECTION_DATA_CATALOG",        "data_catalog"),
    "fraud_cases":          os.getenv("MONGODB_COLLECTION_FRAUD_CASES",         "fraud_cases"),
    "compliance_rules":     os.getenv("MONGODB_COLLECTION_COMPLIANCE_RULES",    "compliance_rules"),
    "merchant_networks":    os.getenv("MONGODB_COLLECTION_MERCHANT_NETWORKS",   "merchant_networks"),
    "conversation_history": os.getenv("MONGODB_COLLECTION_CONVERSATION_HISTORY","conversation_history"),
    "agent_checkpoints":    os.getenv("MONGODB_COLLECTION_AGENT_CHECKPOINTS",   "agent_checkpoints"),
    "agent_memory":         os.getenv("MONGODB_COLLECTION_AGENT_MEMORY",        "agent_memory"),
    "session_memories":     os.getenv("MONGODB_COLLECTION_SESSION_MEMORIES",    "session_memories"),
}

# Atlas Search index names — read from .env
_VECTOR_INDEX_DEFAULT = os.getenv("ATLAS_VECTOR_SEARCH_INDEX_NAME", "vector_index_embedding")
_TEXT_INDEX_DEFAULT   = os.getenv("ATLAS_SEARCH_INDEX_NAME",        "knowledge_text_search")

VECTOR_INDEXES = {
    "offers":           _VECTOR_INDEX_DEFAULT,
    "data_catalog":     _VECTOR_INDEX_DEFAULT,
    "compliance_rules": _VECTOR_INDEX_DEFAULT,
    "merchants":        _VECTOR_INDEX_DEFAULT,
    "cardholders":      _VECTOR_INDEX_DEFAULT,
    "fraud_cases":      _VECTOR_INDEX_DEFAULT,
    "session_memories": _VECTOR_INDEX_DEFAULT,
}

TEXT_SEARCH_INDEX: str = _TEXT_INDEX_DEFAULT

# Atlas Full-Text Search index names used by $rankFusion hybrid search
FTS_INDEXES = {
    "data_catalog": os.getenv("ATLAS_FTS_INDEX_CATALOG", "catalog_fts_index"),
    "offers":       os.getenv("ATLAS_FTS_INDEX_OFFERS",  "offers_fts_index"),
}

# Atlas Admin API
ATLAS_API_CLIENT_ID: str     = os.getenv("ATLAS_API_CLIENT_ID", "")
ATLAS_API_CLIENT_SECRET: str = os.getenv("ATLAS_API_CLIENT_SECRET", "")
ATLAS_API_CLUSTER_NAME: str  = os.getenv("ATLAS_API_CLUSTER_NAME", "")

# ── Azure OpenAI ───────────────────────────────────────────────────────────────
AZURE_OPENAI_API_KEY: str     = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT: str    = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
AZURE_OPENAI_DEPLOYMENT: str  = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
AZURE_OPENAI_EMB_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")

# ── Voyage AI ──────────────────────────────────────────────────────────────────
VOYAGE_API_KEY: str = os.getenv("VOYAGE_API_KEY", "")
VOYAGE_MODEL: str   = os.getenv("VOYAGE_MODEL", "voyage-finance-2")
EMBEDDING_DIMENSION: int = 1024        # voyage-finance-2 output dimension

# ── LangSmith ─────────────────────────────────────────────────────────────────
LANGCHAIN_API_KEY: str     = os.getenv("LANGCHAIN_API_KEY", "")
LANGCHAIN_PROJECT: str     = os.getenv("LANGCHAIN_PROJECT", "vaultiq-fsi")
# Only enable tracing when a valid API key is present — prevents 401 spam and
# blocking background-thread errors when no key is configured.
_tracing_requested = os.getenv("LANGCHAIN_TRACING_V2", "true").lower() == "true"
LANGCHAIN_TRACING_V2: str  = "true" if (_tracing_requested and LANGCHAIN_API_KEY) else "false"
# Push the resolved value back into the environment so LangSmith's SDK sees it.
os.environ["LANGCHAIN_TRACING_V2"] = LANGCHAIN_TRACING_V2
if LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY

# ── FastMCP (VaultIQ mock tool server) ────────────────────────────────────────
MCP_SERVER_HOST: str = os.getenv("MCP_SERVER_HOST", "localhost")
MCP_SERVER_PORT: int = int(os.getenv("MCP_SERVER_PORT", "8100"))
MCP_SERVER_URL: str  = f"http://{MCP_SERVER_HOST}:{MCP_SERVER_PORT}"

# ── MongoDB MCP Server (official @mongodb-js/mongodb-mcp-server) ──────────────
#
# MONGODB_MCP_TRANSPORT controls how the agent connects to the MCP server:
#
#   embedded  (default) — langchain-mcp-adapters spawns npx as a stdio subprocess
#                         automatically.  No separate server process needed.
#                         Requires Node.js / npx on PATH.
#
#   http                — Agent connects to an already-running HTTP server.
#                         Start it first:
#                           MDB_MCP_CONNECTION_STRING=<uri> \
#                           npx -y mongodb-mcp-server@latest \
#                             --transport http --httpPort 3001 \
#                             --readOnly --disabledTools atlas
#
MONGODB_MCP_TRANSPORT: str   = os.getenv("MONGODB_MCP_TRANSPORT", "embedded")   # "embedded" | "http"
MONGODB_MCP_HOST: str        = os.getenv("MONGODB_MCP_HOST", "localhost")
MONGODB_MCP_PORT: int        = int(os.getenv("MONGODB_MCP_PORT", "3001"))
MONGODB_MCP_SERVER_URL: str  = f"http://{MONGODB_MCP_HOST}:{MONGODB_MCP_PORT}"
MONGODB_MCP_READ_ONLY: bool  = os.getenv("MONGODB_MCP_READ_ONLY", "true").lower() == "true"

# ── App ────────────────────────────────────────────────────────────────────────
APP_ENV: str   = os.getenv("APP_ENV", "demo")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# ── File logging setup ────────────────────────────────────────────────────────
_LOG_DIR = Path(__file__).parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)
LOG_FILE: Path = _LOG_DIR / "vaultiq.log"

def _setup_logging() -> None:
    """
    Configure root logger with:
      • RotatingFileHandler  → logs/vaultiq.log  (DEBUG+, 10 MB × 5 files)
      • StreamHandler        → stderr/terminal    (WARNING+ to keep terminal clean)
    Call once at startup.  Idempotent — skips if handlers already attached.
    """
    root = logging.getLogger()
    numeric_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    root.setLevel(logging.DEBUG)           # capture everything; handlers filter

    if any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        return                             # already configured

    fmt_file    = "%(asctime)s | %(levelname)-8s | %(name)-35s | %(message)s"
    fmt_console = "%(levelname)-8s | %(name)s | %(message)s"
    datefmt     = "%Y-%m-%d %H:%M:%S"

    # File handler — DEBUG and above → logs/vaultiq.log
    fh = RotatingFileHandler(
        LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(fmt_file, datefmt=datefmt))

    # Console handler — WARNING and above (keeps terminal readable)
    ch = logging.StreamHandler()
    ch.setLevel(numeric_level)
    ch.setFormatter(logging.Formatter(fmt_console))

    root.addHandler(fh)
    root.addHandler(ch)

    # Silence noisy 3rd-party loggers — file still gets WARNING+, but not
    # thousands of lines of HTTP request headers, pymongo wire protocol, etc.
    for noisy in (
        "watchdog", "watchdog.observers.inotify_buffer",
        "httpcore", "httpcore.http11", "httpcore.connection",
        "httpx", "openai", "openai._base_client",
        "pymongo", "pymongo.command", "pymongo.connection", "pymongo.serverSelection",
        "langsmith", "langsmith.client",
        "urllib3", "urllib3.connectionpool",
        "asyncio", "charset_normalizer",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)

_setup_logging()

# VaultIQ brand colours — MongoDB Atlas palette
BRAND_PRIMARY   = "#00ED64"   # MongoDB bright green
BRAND_DARK      = "#001E2B"   # MongoDB dark navy
BRAND_MID       = "#00A35C"   # MongoDB deeper green
BRAND_LIGHT     = "#E3FCF0"   # light green tint
BRAND_WHITE     = "#FFFFFF"

# ── LLM Defaults ──────────────────────────────────────────────────────────────
LLM_TEMPERATURE: float     = 0.0
LLM_MAX_TOKENS: int        = 4096
AGENT_MAX_ITERATIONS: int  = 15
AGENT_RECURSION_LIMIT: int = 50
