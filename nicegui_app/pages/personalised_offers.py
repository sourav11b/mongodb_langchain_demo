"""
NiceGUI — Personalised Offers page  (/offers)
"""
from __future__ import annotations
import sys, os, asyncio, logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nicegui import ui, app
from nicegui_app.theme import inject_css, page_header, render_chat_bubble

logger = logging.getLogger("vaultiq.nicegui.offers")

EXAMPLE_PROMPTS = [
    ("🔵 Offer Search",  "Find Restaurant and Entertainment offers available for a Platinum card"),
    ("🟢 Hybrid Search", "Search offers with cashback or points multiplier at Travel and Hotel merchants"),
    ("📍 Nearby Offers", "Find offers at Restaurant merchants within 5km of Canary Wharf London (longitude: -0.0235, latitude: 51.5054)"),
    ("💰 Spending",      "Show spending breakdown by category for cardholder CH_0001 over the last 30 days"),
    ("🎯 Rewards",       "How many Membership Rewards points has cardholder CH_0001 earned in the last 30 days?"),
    ("👤 Profile",       "Show the full profile and preferences for cardholder CH_0003"),
]


# ── Page-local state (LangChain objects aren't JSON-serializable) ─────────────
_page_state: dict[str, dict] = {}


def _get_state(tab_id: str) -> dict:
    if tab_id not in _page_state:
        _page_state[tab_id] = {"msgs": [], "hist": []}
    return _page_state[tab_id]


@ui.page("/offers")
async def offers_page():
    await ui.context.client.connected()
    tab_id = str(app.storage.tab.get("_id", id(ui.context.client)))
    state = _get_state(tab_id)

    inject_css()

    # ── Sidebar ───────────────────────────────────────────────────────────
    with ui.left_drawer(value=True).style(
        "width:310px; background:linear-gradient(180deg,#065f46,#059669);"
    ):
        ui.label("🎁 Cardholder Context").classes("text-white text-lg font-bold mt-4")
        ch_id = ui.select(
            [f"CH_{i:04d}" for i in range(1, 16)], value="CH_0001",
            label="Active Cardholder",
        ).classes("w-full bg-white rounded mt-2")
        ui.label("The concierge uses this cardholder's profile, spending "
                 "history, and preferences.").classes("text-white/70 text-xs mt-2")

    # ── Header ────────────────────────────────────────────────────────────
    page_header(
        "🎁 Personalised Offers — AI Concierge",
        "Hyper-personalised recommendations · Vector + Hybrid + Geo search",
        '<span class="blog-feature-tag bft-vector">🔵 Vector Search</span>'
        '<span class="blog-feature-tag bft-hybrid">🟢 Hybrid ($rankFusion)</span>'
        '<span class="blog-feature-tag bft-geo">📍 Geospatial</span>'
        '<span class="blog-feature-tag bft-mql">🟡 Aggregation</span>',
    )

    chat_box = ui.column().classes("w-full gap-1")
    for turn in state["msgs"]:
        render_chat_bubble(chat_box, turn)

    # ── Quick Start ───────────────────────────────────────────────────────
    qs = ui.row().classes("w-full gap-2 flex-wrap")
    if not state["msgs"]:
        with qs:
            ui.label("💡 Quick starts — each highlights a different feature:").classes("w-full text-sm font-semibold")
            for label, prompt in EXAMPLE_PROMPTS:
                ui.button(label, on_click=lambda p=prompt: _fill(p)).tooltip(prompt).classes("text-xs")

    # ── Input ─────────────────────────────────────────────────────────────
    with ui.row().classes("w-full items-center gap-2 mt-3"):
        inp = ui.input(placeholder="Ask about offers, rewards, spending…").classes("flex-grow").props("outlined dense")
        ui.button("Send ➤", color="primary", on_click=lambda: _send())
    status = ui.label("").classes("text-xs text-gray-500")

    # ── Handlers ──────────────────────────────────────────────────────────
    async def _send():
        q = inp.value.strip()
        if not q:
            return
        inp.value = ""
        qs.clear()

        user_turn = {"role": "user", "content": q}
        state["msgs"].append(user_turn)
        render_chat_bubble(chat_box, user_turn)
        status.text = "🤖 Concierge thinking…"

        try:
            from agents.offers_agent import run_offers_chat
            result = run_offers_chat(
                question=q, cardholder_id=ch_id.value,
                history=state["hist"],
            )
        except Exception as e:
            logger.exception("Offers agent error: %s", e)
            result = {"answer": f"⚠️ Error: {e}", "tool_calls": []}

        answer = result.get("answer", "") or "⚠️ Empty response."
        agent_turn = {"role": "assistant", "content": answer,
                      "tools": result.get("tool_calls", []), "mcp": False}
        state["msgs"].append(agent_turn)
        render_chat_bubble(chat_box, agent_turn)

        from langchain_core.messages import HumanMessage, AIMessage
        state["hist"].append(HumanMessage(content=q))
        state["hist"].append(AIMessage(content=answer))
        status.text = f"✅ Done — Tools: {agent_turn['tools']}"

    def _fill(prompt: str):
        inp.value = prompt
        asyncio.ensure_future(_send())

    inp.on("keydown.enter", lambda: _send())

    # ── Actions ───────────────────────────────────────────────────────────
    with ui.row().classes("w-full gap-2 mt-2"):
        async def _clear():
            state["msgs"], state["hist"] = [], []
            chat_box.clear()
            status.text = ""

        ui.button("🗑️ Clear Chat", on_click=_clear).props("outline")
