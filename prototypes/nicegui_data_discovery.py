"""
NiceGUI prototype — Data Discovery page
========================================
Compare with pages/1_🔍_Data_Discovery.py (536 lines of Streamlit).

Key differences:
 • async-native: `await agent.ainvoke()` directly — no ThreadPoolExecutor,
   no _thread_target, no ThreadedChildWatcher hacks
 • Partial UI updates via Vue.js — no st.rerun() full-page re-render
 • Real-time streaming via ui.timer / SSE — no polling

Run:
    pip install nicegui
    python prototypes/nicegui_data_discovery.py
"""
from __future__ import annotations
import sys, os, uuid, asyncio, logging
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from nicegui import ui, app

logger = logging.getLogger("vaultiq.nicegui.discovery")

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE — stored per-browser-tab via app.storage.tab
# (NiceGUI equivalent of st.session_state, but without full-page reruns)
# ══════════════════════════════════════════════════════════════════════════════
MCP_TOOL_NAMES = {
    "find", "aggregate", "collection-schema", "collection-indexes",
    "collection-storage-size", "count", "db-stats", "explain",
    "list-collections", "list-databases", "search-knowledge", "list-knowledge-sources",
}

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


# ══════════════════════════════════════════════════════════════════════════════
# CUSTOM CSS (same visual style as the Streamlit version)
# ══════════════════════════════════════════════════════════════════════════════
CUSTOM_CSS = """
<style>
.page-header { background:linear-gradient(135deg,#003087,#006FCF);
  padding:1.5rem 2rem; border-radius:10px; margin-bottom:1rem; color:white; }
.page-header h2 { margin:0; }
.page-header p  { color:rgba(255,255,255,.88); margin:.3rem 0 0; }
.bubble-human { background:#EBF5FB; border-radius:16px 16px 4px 16px;
  padding:.75rem 1.1rem; margin:.5rem 0 .5rem 12%; border-left:3px solid #006FCF; }
.bubble-agent { background:#F0FFF4; border-radius:16px 16px 16px 4px;
  padding:.75rem 1.1rem; margin:.5rem 12% .5rem 0; border-left:3px solid #27ae60; }
.bubble-context { background:#FFF8E7; border-radius:8px;
  padding:.6rem 1rem; margin:.4rem 8%; border-left:3px solid #B5A06A; font-size:.85rem; }
.tool-chip { background:#EEF3FB; color:#006FCF; border-radius:5px;
  padding:1px 8px; font-size:.76rem; font-weight:600; display:inline-block; margin:1px; }
.mcp-chip  { background:#E9F7EF; color:#1a7340; border-radius:5px;
  padding:1px 8px; font-size:.76rem; font-weight:600; display:inline-block; margin:1px; }
.blog-feature-tag { display:inline-block; padding:.18rem .65rem; border-radius:20px;
  font-size:.73rem; font-weight:700; margin:.15rem; border:1.5px solid; }
.bft-vector { background:#dbeafe; color:#1d4ed8; border-color:#93c5fd; }
.bft-hybrid { background:#d1fae5; color:#065f46; border-color:#6ee7b7; }
.bft-mql    { background:#fef3c7; color:#92400e; border-color:#fcd34d; }
.bft-ckpt   { background:#ede9fe; color:#5b21b6; border-color:#c4b5fd; }
.bft-smith  { background:#fee2e2; color:#991b1b; border-color:#fca5a5; }
.mem-card   { background:#fff; border:1px solid #d5e8f7; border-radius:10px;
  padding:.9rem 1rem; margin:.5rem 0; border-top:3px solid #8e44ad; }
</style>
"""



# ══════════════════════════════════════════════════════════════════════════════
# PAGE LAYOUT
# ══════════════════════════════════════════════════════════════════════════════
@ui.page("/")
async def data_discovery_page():
    """
    Entire page is an async function — no threading hacks needed.
    All `await` calls run natively in NiceGUI's uvicorn event loop.
    """
    # ── Wait for WebSocket before accessing per-tab storage ──────────────
    await ui.context.client.connected()
    state = app.storage.tab
    state.setdefault("session_id", _new_session_id())
    state.setdefault("messages", [])       # list[dict]
    state.setdefault("lc_history", [])     # list[BaseMessage]
    state.setdefault("mem_injected", False)

    ui.add_head_html(CUSTOM_CSS)

    # ── Sidebar: semantic memory panel ────────────────────────────────────
    with ui.left_drawer(value=True).classes(
        "bg-gradient-to-b from-[#003087] to-[#006FCF]"
    ).style("width:320px"):
        ui.label("🧠 Semantic Memory").classes("text-white text-lg font-bold mt-4")
        ui.label(
            "Past sessions — stored in MongoDB, retrieved by vector similarity"
        ).classes("text-white/70 text-xs mb-2")

        try:
            from memory.mongodb_memory import SessionMemoryStore
            sms = SessionMemoryStore("metadata_agent")
            memories = sms.list_all_memories(limit=8)
            if memories:
                for m in memories:
                    ts = m.get("created_at", "")
                    if hasattr(ts, "strftime"):
                        ts = ts.strftime("%b %d %H:%M")
                    datasets = ", ".join(m.get("datasets_explored", [])[:3]) or "—"
                    with ui.card().classes("mem-card w-full"):
                        ui.label(f"{m.get('memory_id','?')} · {ts}").classes(
                            "text-purple-700 font-bold text-sm")
                        ui.label(f"{m.get('summary','')[:120]}…").classes(
                            "text-gray-600 text-xs italic")
                        ui.label(f"Collections: {datasets}").classes(
                            "text-gray-700 text-xs font-semibold")
            else:
                ui.label("No memories yet.").classes("text-white/60 text-xs")
        except Exception:
            ui.label("Memory store unavailable").classes("text-white/60 text-xs")

        ui.separator().classes("bg-white/20 my-2")
        ui.label(f"Session: {state['session_id']}").classes(
            "text-white/80 text-xs font-mono")

    # ── Main content ──────────────────────────────────────────────────────
    ui.html("""
    <div class="page-header">
      <h2>🔍 Data Discovery — Conversational Intelligence</h2>
      <p>Multi-turn chat · MongoDB MCP Server ·
         Voyage AI semantic memory · Cross-session recall</p>
      <p style="margin-top:.6rem;">
        <span class="blog-feature-tag bft-mql">🟡 Text-to-MQL</span>
        <span class="blog-feature-tag bft-vector">🔵 Atlas Vector Search</span>
        <span class="blog-feature-tag bft-hybrid">🟢 Hybrid ($rankFusion)</span>
        <span class="blog-feature-tag bft-ckpt">🟣 MongoDB Checkpointer</span>
        <span class="blog-feature-tag bft-smith">🔴 LangSmith Observability</span>
      </p>
    </div>
    """)

    # ── Chat container (reactive — messages append without page reload) ───
    chat_container = ui.column().classes("w-full gap-1")

    def render_message(turn: dict):
        """Render a single chat bubble into the chat container."""
        with chat_container:
            if turn["role"] == "context":
                ui.html(f'<div class="bubble-context">📚 '
                        f'<em>{turn["content"][:200]}…</em></div>')
            elif turn["role"] == "user":
                ui.html(f'<div class="bubble-human">🧑 <strong>You</strong>'
                        f'<br>{turn["content"]}</div>')
            else:
                mcp_on = turn.get("mcp", False)
                badge = "🍃 MongoDB MCP" if mcp_on else "⚙️ pymongo fallback"
                ui.html(
                    f'<div class="bubble-agent">🤖 <strong>Agent</strong> '
                    f'<small>({badge})</small><br>{turn["content"]}</div>'
                )
                if turn.get("tools"):
                    chips = " ".join(
                        f'<span class="{"mcp-chip" if t in MCP_TOOL_NAMES else "tool-chip"}">'
                        f'{"🍃 " if t in MCP_TOOL_NAMES else "✓ "}{t}</span>'
                        for t in turn["tools"]
                    )
                    ui.html(chips)

    # Render existing history on page load
    for turn in state["messages"]:
        render_message(turn)

    # ── Quick Start buttons (only when chat is empty) ─────────────────────
    qs_container = ui.row().classes("w-full gap-2 flex-wrap")

    if not state["messages"]:
        with qs_container:
            ui.label("💡 Try one — each highlights a different feature:"
                     ).classes("w-full text-sm font-semibold")
            for label, prompt in EXAMPLE_QUERIES:
                ui.button(
                    label,
                    on_click=lambda p=prompt: _fill_and_send(p),
                ).tooltip(prompt).classes("text-xs")

    # ══════════════════════════════════════════════════════════════════════
    # INPUT + SEND — the key difference from Streamlit
    #
    # Streamlit version (metadata_agent.py lines 528-610):
    #   def run_metadata_query(...):
    #       def _thread_target():
    #           loop = asyncio.new_event_loop()
    #           if sys.platform != "win32":
    #               asyncio.set_child_watcher(ThreadedChildWatcher())
    #           result = loop.run_until_complete(_run_with_mcp(...))
    #       with ThreadPoolExecutor(max_workers=1) as executor:
    #           future = executor.submit(_thread_target)
    #           result = future.result(timeout=180)
    #
    # NiceGUI version:
    #   result = await _run_with_mcp(...)
    #   That's it. Same event loop. No threads. No child watcher.
    # ══════════════════════════════════════════════════════════════════════
    with ui.row().classes("w-full items-center gap-2 mt-4"):
        input_box = ui.input(
            placeholder="Ask about any NFG dataset, schema, or data pattern…"
        ).classes("flex-grow").props("outlined dense")
        send_btn = ui.button("Send ➤", color="primary")

    status_label = ui.label("").classes("text-xs text-gray-500")

    async def send_message():
        question = input_box.value.strip()
        if not question:
            return
        input_box.value = ""
        qs_container.clear()

        # ── User bubble (instant — no page reload) ────────────────────
        user_turn = {"role": "user", "content": question}
        state["messages"].append(user_turn)
        render_message(user_turn)

        # ── Call agent — DIRECTLY WITH AWAIT ──────────────────────────
        status_label.text = "🤖 Agent reasoning + querying MongoDB…"
        try:
            from agents.metadata_agent import _run_with_mcp
            result = await _run_with_mcp(
                question=question,
                session_id=state["session_id"],
                history=state["lc_history"],
                memory_context=None,
            )
        except Exception as e:
            logger.exception("Agent error: %s", e)
            result = {
                "answer": f"⚠️ **Error:** {e}",
                "tool_calls": [],
                "mcp_tools_active": False,
                "fallback_reason": str(e),
            }

        # ── Agent bubble (partial update) ─────────────────────────────
        answer = result.get("answer", "") or "⚠️ Empty response."
        tools = result.get("tool_calls", [])
        mcp_on = result.get("mcp_tools_active", False)
        if result.get("fallback_reason"):
            answer += "\n\n> ⚠️ *MCP unavailable — used pymongo fallback.*"

        agent_turn = {
            "role": "assistant", "content": answer,
            "tools": tools, "mcp": mcp_on,
        }
        state["messages"].append(agent_turn)
        render_message(agent_turn)

        from langchain_core.messages import HumanMessage, AIMessage
        state["lc_history"].append(HumanMessage(content=question))
        state["lc_history"].append(AIMessage(content=answer))
        status_label.text = f"✅ Done — MCP: {mcp_on} | Tools: {tools}"

    def _fill_and_send(prompt: str):
        input_box.value = prompt
        asyncio.ensure_future(send_message())

    send_btn.on_click(send_message)
    input_box.on("keydown.enter", send_message)

    # ── Action buttons ────────────────────────────────────────────────────
    with ui.row().classes("w-full gap-2 mt-2"):
        async def end_session():
            if not state["lc_history"]:
                ui.notify("Nothing to store.", type="warning")
                return
            status_label.text = "🧠 Condensing + storing memory…"
            try:
                from memory.mongodb_memory import SessionMemoryStore
                from langchain_openai import AzureChatOpenAI
                from config import (
                    AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT,
                    AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT,
                )
                llm = AzureChatOpenAI(
                    azure_endpoint=AZURE_OPENAI_ENDPOINT,
                    api_key=AZURE_OPENAI_API_KEY,
                    api_version=AZURE_OPENAI_API_VERSION,
                    azure_deployment=AZURE_OPENAI_DEPLOYMENT,
                    temperature=0,
                )
                sms = SessionMemoryStore("metadata_agent")
                stored = sms.condense_and_store(
                    session_id=state["session_id"],
                    messages=state["lc_history"], llm=llm,
                )
                ui.notify(f"✅ Stored: {stored.get('memory_id')}", type="positive")
            except Exception as e:
                ui.notify(f"Failed: {e}", type="negative")
            await clear_chat()

        async def clear_chat():
            state["messages"], state["lc_history"] = [], []
            state["session_id"] = _new_session_id()
            state["mem_injected"] = False
            chat_container.clear()
            status_label.text = ""

        ui.button("💾 End Session & Store Memory",
                  on_click=end_session).props("outline")
        ui.button("🗑️ Clear Chat",
                  on_click=clear_chat).props("outline")
        ui.label(
            f"💬 {len(state['messages'])} turns · {state['session_id']}"
        ).classes("text-xs text-gray-500 ml-auto self-center")


# ══════════════════════════════════════════════════════════════════════════════
# RUN — one line, starts uvicorn
# ══════════════════════════════════════════════════════════════════════════════
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="Data Discovery | VaultIQ",
        port=8501,
        reload=True,
        storage_secret="vaultiq",
    )