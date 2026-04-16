"""
NiceGUI — Data Discovery page  (/discovery)
Async-native — agent calls are a single `await _run_with_mcp()`.
"""
from __future__ import annotations
import sys, os, uuid, asyncio, logging
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nicegui import ui, app
from nicegui_app.theme import inject_css, page_header, render_chat_bubble

logger = logging.getLogger("vaultiq.nicegui.discovery")

EXAMPLE_QUERIES = [
    ("🔵 Vector Search",   "Find datasets related to fraud detection and transaction risk scoring"),
    ("🟢 Hybrid Search",   "Search the catalog for datasets containing fraud_score in the transactions collection"),
    ("🟡 Text-to-MQL",     "Show all Platinum cardholder transactions above $5000 with a fraud_score greater than 0.7"),
    ("📊 Schema",          "Inspect the schema of the merchant_networks collection"),
    ("🕸️ Graph Traverse",  "Traverse the merchant network graph for merchant MER_0001 to depth 2"),
    ("📍 Geo Query",       "Find Restaurant merchants within 5km of Canary Wharf London (longitude: -0.0235, latitude: 51.5054)"),
]


def _new_session_id() -> str:
    return f"disco-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"


@ui.page("/discovery")
async def discovery_page():
    await ui.context.client.connected()
    state = app.storage.tab
    state.setdefault("disco_sid", _new_session_id())
    state.setdefault("disco_msgs", [])
    state.setdefault("disco_hist", [])
    state.setdefault("disco_mem", False)

    inject_css()

    # ── Sidebar: semantic memory ──────────────────────────────────────────
    with ui.left_drawer(value=True).style(
        "width:310px; background:linear-gradient(180deg,#003087,#006FCF);"
    ):
        ui.label("🧠 Semantic Memory").classes("text-white text-lg font-bold mt-4")
        try:
            from memory.mongodb_memory import SessionMemoryStore
            sms = SessionMemoryStore("metadata_agent")
            for m in sms.list_all_memories(limit=6):
                ts = m.get("created_at", "")
                ts = ts.strftime("%b %d %H:%M") if hasattr(ts, "strftime") else str(ts)[:16]
                with ui.card().classes("w-full my-1").style(
                    "border-top:3px solid #8e44ad; padding:.6rem"
                ):
                    ui.label(f"{m.get('memory_id','')} · {ts}").classes("text-purple-700 text-xs font-bold")
                    ui.label(m.get("summary", "")[:100]).classes("text-gray-600 text-xs italic")
        except Exception:
            ui.label("Memory store unavailable").classes("text-white/60 text-xs")

    # ── Header ────────────────────────────────────────────────────────────
    page_header(
        "🔍 Data Discovery — Conversational Intelligence",
        "Multi-turn chat · MongoDB MCP Server · Voyage AI semantic memory",
        '<span class="blog-feature-tag bft-mql">🟡 Text-to-MQL</span>'
        '<span class="blog-feature-tag bft-vector">🔵 Atlas Vector Search</span>'
        '<span class="blog-feature-tag bft-hybrid">🟢 Hybrid ($rankFusion)</span>'
        '<span class="blog-feature-tag bft-graph">🟣 $graphLookup</span>'
        '<span class="blog-feature-tag bft-geo">📍 Geospatial</span>'
        '<span class="blog-feature-tag bft-mcp">🍃 MCP Server</span>',
    )

    chat_box = ui.column().classes("w-full gap-1")
    for turn in state["disco_msgs"]:
        render_chat_bubble(chat_box, turn)

    # ── Quick Start ───────────────────────────────────────────────────────
    qs = ui.row().classes("w-full gap-2 flex-wrap")
    if not state["disco_msgs"]:
        with qs:
            ui.label("💡 Quick starts — each highlights a different feature:").classes("w-full text-sm font-semibold")
            for label, prompt in EXAMPLE_QUERIES:
                ui.button(label, on_click=lambda p=prompt: _fill(p)).tooltip(prompt).classes("text-xs")

    # ── Input ─────────────────────────────────────────────────────────────
    with ui.row().classes("w-full items-center gap-2 mt-3"):
        inp = ui.input(placeholder="Ask about any NFG dataset…").classes("flex-grow").props("outlined dense")
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
        state["disco_msgs"].append(user_turn)
        render_chat_bubble(chat_box, user_turn)
        status.text = "🤖 Agent reasoning…"

        try:
            from agents.metadata_agent import _run_with_mcp
            result = await _run_with_mcp(
                question=q, session_id=state["disco_sid"],
                history=state["disco_hist"], memory_context=None,
            )
        except Exception as e:
            logger.exception("Agent error: %s", e)
            result = {"answer": f"⚠️ Error: {e}", "tool_calls": [],
                      "mcp_tools_active": False, "fallback_reason": str(e)}

        answer = result.get("answer", "") or "⚠️ Empty response."
        if result.get("fallback_reason"):
            answer += "\n\n> ⚠️ *MCP unavailable — pymongo fallback.*"
        agent_turn = {"role": "assistant", "content": answer,
                      "tools": result.get("tool_calls", []),
                      "mcp": result.get("mcp_tools_active", False)}
        state["disco_msgs"].append(agent_turn)
        render_chat_bubble(chat_box, agent_turn)

        from langchain_core.messages import HumanMessage, AIMessage
        state["disco_hist"].append(HumanMessage(content=q))
        state["disco_hist"].append(AIMessage(content=answer))
        status.text = f"✅ Done — Tools: {agent_turn['tools']}"

    def _fill(prompt: str):
        inp.value = prompt
        asyncio.ensure_future(_send())

    inp.on("keydown.enter", lambda: _send())

    # ── Actions ───────────────────────────────────────────────────────────
    with ui.row().classes("w-full gap-2 mt-2"):
        async def _clear():
            state["disco_msgs"], state["disco_hist"] = [], []
            state["disco_sid"] = _new_session_id()
            chat_box.clear()
            status.text = ""

        async def _end_session():
            if not state["disco_hist"]:
                ui.notify("Nothing to store.", type="warning")
                return
            try:
                from memory.mongodb_memory import SessionMemoryStore
                from langchain_openai import AzureChatOpenAI
                from config import (AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT,
                                    AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT)
                llm = AzureChatOpenAI(
                    azure_endpoint=AZURE_OPENAI_ENDPOINT, api_key=AZURE_OPENAI_API_KEY,
                    api_version=AZURE_OPENAI_API_VERSION,
                    azure_deployment=AZURE_OPENAI_DEPLOYMENT, temperature=0)
                sms = SessionMemoryStore("metadata_agent")
                stored = sms.condense_and_store(
                    session_id=state["disco_sid"], messages=state["disco_hist"], llm=llm)
                ui.notify(f"✅ Stored: {stored.get('memory_id')}", type="positive")
            except Exception as e:
                ui.notify(f"Failed: {e}", type="negative")
            await _clear()

        ui.button("💾 End Session", on_click=_end_session).props("outline")
        ui.button("🗑️ Clear", on_click=_clear).props("outline")