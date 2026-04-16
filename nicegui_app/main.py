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

# ── Import page modules (each registers its own @ui.page routes) ─────────────
import nicegui_app.pages.setup            # noqa: F401  →  /setup
import nicegui_app.pages.data_discovery   # noqa: F401  →  /discovery
import nicegui_app.pages.fraud_intelligence  # noqa: F401  →  /fraud
import nicegui_app.pages.personalised_offers  # noqa: F401  →  /offers
import nicegui_app.pages.compliance_agent  # noqa: F401  →  /compliance


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
        port=8502,           # 8502 so it doesn't clash with Streamlit on 8501
        reload=True,
        storage_secret="vaultiq-nicegui",
    )
