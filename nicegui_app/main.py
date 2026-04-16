"""
VaultIQ — NiceGUI Edition
==========================
Async-native alternative to the Streamlit app.
Same agents, same tools, same MongoDB backend — zero threading hacks.

Run:
    pip install nicegui
    python -m nicegui_app.main          # from repo root
    # or
    python nicegui_app/main.py
"""
from __future__ import annotations
import sys, os, logging

# ── Ensure repo root is on sys.path so agents/ config/ etc. are importable ───
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nicegui import ui, app

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Suppress noisy "not found" warnings from browser probing for Streamlit endpoints
logging.getLogger("nicegui").setLevel(logging.ERROR)

# ── Import page modules (each registers its own @ui.page routes) ─────────────
import nicegui_app.pages.setup            # noqa: F401  →  /setup
import nicegui_app.pages.data_discovery   # noqa: F401  →  /discovery
import nicegui_app.pages.fraud_intelligence  # noqa: F401  →  /fraud
import nicegui_app.pages.personalised_offers  # noqa: F401  →  /offers
import nicegui_app.pages.compliance_agent  # noqa: F401  →  /compliance

logger = logging.getLogger("vaultiq.nicegui")


# ══════════════════════════════════════════════════════════════════════════════
# ATLAS CLUSTER STARTUP CHECK
# Runs once when the server starts — pings MongoDB, auto-resumes if paused.
# Result stored in app.storage.general so every page can show a banner.
# ══════════════════════════════════════════════════════════════════════════════
async def _atlas_startup_check():
    """Check Atlas cluster reachability; auto-resume if paused."""
    import asyncio
    from config import MONGODB_URI
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

    # Step 1: direct pymongo ping (run in executor to avoid blocking event loop)
    logger.info("=" * 60)
    logger.info("🏥 ATLAS CLUSTER HEALTH CHECK — starting")
    logger.info("=" * 60)
    logger.info("Step 1/3: Attempting pymongo ping (5s timeout)…")

    def _ping():
        hc = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        hc.admin.command("ping")
        hc.close()

    try:
        await asyncio.get_event_loop().run_in_executor(None, _ping)
        logger.info("✅ Step 1: pymongo ping OK — cluster is reachable")
        app.storage.general["atlas_status"] = "ok"
        app.storage.general["atlas_message"] = "✅ Atlas cluster is reachable"
        return
    except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as e:
        logger.warning("⚠️ Step 1: pymongo ping FAILED: %s", str(e)[:200])

    # Step 2: check Atlas Admin API credentials
    logger.info("Step 2/3: Checking Atlas Admin API credentials…")
    from tools.atlas_cluster import is_configured, get_cluster_status, resume_cluster, wait_for_ready

    if not is_configured():
        msg = ("❌ Cannot connect to MongoDB and Atlas Admin API is not configured. "
               "Set ATLAS_API_CLIENT_ID, ATLAS_API_CLIENT_SECRET, "
               "ATLAS_API_PROJECT_ID, ATLAS_API_CLUSTER_NAME in .env")
        logger.error(msg)
        app.storage.general["atlas_status"] = "error"
        app.storage.general["atlas_message"] = msg
        return

    # Step 3: query Atlas API for cluster state
    logger.info("Step 3/3: Querying Atlas Admin API for cluster status…")
    status = get_cluster_status()
    logger.info("📡 Atlas API response: %s", status)

    if status.get("error"):
        msg = f"❌ Atlas API error: {status['error']}"
        logger.error(msg)
        app.storage.general["atlas_status"] = "error"
        app.storage.general["atlas_message"] = msg
        return

    if status.get("paused"):
        logger.info("⏸️ Cluster '%s' is PAUSED — sending resume request…",
                     status.get("name"))
        app.storage.general["atlas_status"] = "resuming"
        app.storage.general["atlas_message"] = (
            f"⏸️ Cluster '{status.get('name')}' is paused — auto-resuming…"
        )
        resume_result = resume_cluster()
        if resume_result.get("error"):
            msg = f"❌ Failed to resume cluster: {resume_result['error']}"
            logger.error(msg)
            app.storage.general["atlas_status"] = "error"
            app.storage.general["atlas_message"] = msg
            return
        logger.info("✅ Resume request accepted. Waiting for cluster (up to 5 min)…")
        app.storage.general["atlas_message"] = (
            "🔄 Resume request accepted. Waiting for cluster to become ready (up to 5 min)…"
        )

        def _wait():
            return wait_for_ready(max_wait=300, poll_interval=15)

        ready = await asyncio.get_event_loop().run_in_executor(None, _wait)
        if ready.get("stateName") == "IDLE":
            msg = f"✅ Atlas cluster ready ({ready.get('elapsed', '?')}s)"
            logger.info(msg)
            app.storage.general["atlas_status"] = "ok"
            app.storage.general["atlas_message"] = msg
        else:
            msg = f"⚠️ Cluster not ready after waiting: {ready.get('stateName')}"
            logger.error(msg)
            app.storage.general["atlas_status"] = "error"
            app.storage.general["atlas_message"] = msg
    else:
        msg = (f"🔌 Atlas API says cluster state is '{status.get('stateName', 'UNKNOWN')}' "
               f"(not paused) but pymongo ping failed. "
               f"Check: IP allowlist, MONGODB_URI, firewall.")
        logger.error(msg)
        app.storage.general["atlas_status"] = "error"
        app.storage.general["atlas_message"] = msg

    logger.info("=" * 60)
    logger.info("🏥 ATLAS CLUSTER HEALTH CHECK — done")
    logger.info("=" * 60)


app.on_startup(_atlas_startup_check)


# ══════════════════════════════════════════════════════════════════════════════
# HOME PAGE — landing / navigation
# ══════════════════════════════════════════════════════════════════════════════
@ui.page("/")
async def home():
    from nicegui_app.theme import inject_css
    inject_css()

    ui.html("""
    <div class="page-header">
      <h2>🏦 VaultIQ — Financial Intelligence Platform</h2>
      <p>MongoDB Atlas · LangGraph Agents · MCP Integration · Voyage AI</p>
    </div>
    """)

    ui.markdown("### Navigate to a module:")

    cards = [
        ("⚙️ Setup & Seeding",     "/setup",      "Seed data, create indexes, generate embeddings"),
        ("🔍 Data Discovery",       "/discovery",  "Multi-turn conversational data exploration"),
        ("🚨 Fraud Intelligence",   "/fraud",      "Real-time fraud detection with scenario injection"),
        ("🎁 Personalised Offers",  "/offers",     "AI concierge with hyper-personalised recommendations"),
        ("⚖️ Compliance Audit",     "/compliance", "Regulatory compliance & sanctions screening"),
    ]

    with ui.row().classes("w-full gap-4 flex-wrap"):
        for emoji_title, path, desc in cards:
            with ui.card().classes("cursor-pointer hover:shadow-lg transition-shadow").style(
                "width:280px"
            ).on("click", lambda p=path: ui.navigate.to(p)):
                ui.label(emoji_title).classes("text-lg font-bold text-blue-800")
                ui.label(desc).classes("text-sm text-gray-600")

    ui.markdown("""
---
**NiceGUI Edition** — async-native, zero threading hacks.
Same agents and tools as the Streamlit app.
    """)


# ══════════════════════════════════════════════════════════════════════════════
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="VaultIQ | NiceGUI",
        host="0.0.0.0",      # bind all interfaces (needed for EC2 public IP)
        port=8502,            # 8502 so it doesn't clash with Streamlit on 8501
        reload=True,
        storage_secret="vaultiq-nicegui",
    )
