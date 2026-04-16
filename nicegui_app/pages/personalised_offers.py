"""
NiceGUI — Personalised Offers Concierge  (/offers)
Matches the Streamlit page: capabilities, tools, memory arch, cardholder card, chat.
"""
from __future__ import annotations
import sys, os, asyncio, logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nicegui import ui, app
from nicegui_app.theme import (inject_css, page_header, render_chat_bubble,
                               show_spinner, render_tool_chips)

logger = logging.getLogger("vaultiq.nicegui.offers")

EXAMPLE_PROMPTS = [
    ("🔵 Offer Search",  "Find Restaurant and Entertainment offers available for a Platinum card"),
    ("🟢 Hybrid Search", "Search offers with cashback or points multiplier at Travel and Hotel merchants"),
    ("📍 Nearby Offers", "Find offers at Restaurant merchants within 5km of Canary Wharf London (longitude: -0.0235, latitude: 51.5054)"),
    ("💰 Spending",      "Show spending breakdown by category for cardholder CH_0001 over the last 30 days"),
    ("🎯 Rewards Points","How many Membership Rewards points has cardholder CH_0001 earned in the last 30 days?"),
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

    page_header(
        "🎁 Use Case 3: Personalised Offers Concierge",
        "Multi-turn cardholder chat — semantic offer matching, geo-proximity, spending intelligence",
        '<span class="blog-feature-tag bft-vector">🔵 Atlas Vector Search</span>'
        '<span class="blog-feature-tag bft-hybrid">🟢 Hybrid Search ($rankFusion)</span>'
        '<span class="blog-feature-tag bft-ckpt">🟣 MongoDB Checkpointer</span>'
        '<span class="blog-feature-tag bft-smith">🔴 LangSmith Observability</span>',
    )

    # ── Info columns: capabilities + memory ───────────────────────────────
    with ui.row().classes("w-full gap-4"):
        with ui.column().classes("flex-grow"):
            ui.label("Capabilities:").classes("font-bold text-sm")
            caps = [
                "🔍 **Semantic search** — find offers matching interests (vector similarity)",
                "🔀 **Hybrid search** — `$rankFusion`: `$vectorSearch` + `$search` (BM25) in one Atlas pipeline",
                "📍 **Geo proximity** — locate nearby preferred partner merchants",
                "💳 **Spending analytics** — category breakdown from transaction history",
                "✨ **Points estimate** — Membership Rewards calculation by category multipliers",
            ]
            for c in caps:
                ui.markdown(c).classes("text-sm my-0")

            ui.label("Tools:").classes("font-bold text-sm mt-2")
            tools = ["find_relevant_offers", "hybrid_search_offers", "find_nearby_offers",
                     "get_spending_summary", "get_points_estimate"]
            ui.html(" ".join(f'<span class="tool-chip">{t}</span>' for t in tools))

            ui.html("""<div class="info-section" style="border-left-color:#27ae60; margin-top:.6rem;">
              <span class="blog-feature-tag bft-hybrid">🟢 Hybrid Search — native Atlas $rankFusion</span>
              <code>hybrid_search_offers</code> implements a <strong>single Atlas aggregation pipeline</strong>:
              <code>$vectorSearch</code> + <code>$search</code> (BM25) fused with <code>$rankFusion</code> server-side.
              &nbsp;&nbsp;
              <span class="blog-feature-tag bft-vector">🔵 Atlas Vector Search</span>
              <code>find_relevant_offers</code> uses pure <code>$vectorSearch</code> for intent-based matching.
            </div>""")

        with ui.column().style("min-width:260px; max-width:340px"):
            ui.html("""<div class="memory-box">
              <strong>🧠 Memory Architecture</strong><br><br>
              <strong>🧩 Episodic Memory</strong><br>
              Full multi-turn conversation stored in MongoDB. Context preserved across messages.<br><br>
              <strong>📚 Semantic Memory</strong><br>
              Voyage AI vector embeddings on all offers and merchant descriptions enable intent-based discovery.
            </div>""")

    ui.separator().classes("my-2")

    # ── Cardholder Setup ──────────────────────────────────────────────────
    ui.label("👤 Cardholder Profile").classes("text-xl font-bold")
    with ui.row().classes("w-full gap-2 items-end"):
        ch_id = ui.select([f"CH_{i:04d}" for i in range(1, 16)], value="CH_0001",
                          label="Select Cardholder:").classes("w-48")
        card_tier = ui.select(["Green", "Gold", "Platinum", "Centurion"], value="Platinum",
                              label="Card Tier:").classes("w-36")
        session_input = ui.input("Session:", value="offers-CH_0001").classes("w-48")

    card_banner = ui.column().classes("w-full")

    def _update_banner():
        card_banner.clear()
        with card_banner:
            ui.html(f"""<div class="cardholder-card">
              💳 <strong>Nexus Financial Group {card_tier.value} Card</strong> &nbsp;|&nbsp;
              Cardholder: {ch_id.value} &nbsp;|&nbsp;
              Session: {session_input.value}
            </div>""")

    ch_id.on_value_change(lambda: _update_banner())
    card_tier.on_value_change(lambda: _update_banner())
    session_input.on("blur", lambda: _update_banner())
    _update_banner()

    # ── Chat ──────────────────────────────────────────────────────────────
    ui.label("💬 Chat with VaultConcierge").classes("text-xl font-bold mt-2")

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

        # Bold spinner while agent works
        spinner_box = ui.column().classes("w-full")
        show_spinner(spinner_box,
                     "🤖 VaultConcierge thinking…",
                     f"Cardholder: {ch_id.value} | Tier: {card_tier.value}")

        try:
            from agents.offers_agent import run_offers_chat
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: run_offers_chat(
                    message=q,
                    cardholder_id=ch_id.value,
                    card_tier=card_tier.value,
                    session_id=session_input.value,
                    history=state["hist"],
                ),
            )
        except Exception as e:
            logger.exception("Offers agent error: %s", e)
            result = {"answer": f"⚠️ Error: {e}", "tool_calls": []}

        spinner_box.clear()
        spinner_box.delete()

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
