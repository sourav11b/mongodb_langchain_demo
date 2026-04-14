"""
Page 1: Semantic Metadata Layer — Multi-Turn Chat with Persistent Memory

Features
────────
• Full multi-turn chat (chat bubbles, persistent session state)
• MongoDB MCP Server integration (find, aggregate, collection-schema, …)
• Native NFG tools always active (vector search, hybrid, graph, geo)
• Episodic memory: every turn stored in MongoDB conversation_history
• Semantic memory consolidation on session end:
    conversation → LLM summary → Voyage embed → session_memories
• Cross-session recall: past summaries retrieved via Atlas Vector Search
  and injected as context at the start of each new session
"""

import streamlit as st
import sys, os, uuid
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

st.set_page_config(page_title="Data Discovery | VaultIQ", page_icon="🔍", layout="wide")

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stSidebar"] { background: linear-gradient(180deg,#003087 0%,#006FCF 100%); }
  [data-testid="stSidebar"] * { color: white !important; }
  [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.2); }
  .page-header {
    background: linear-gradient(135deg,#003087,#006FCF);
    padding:1.5rem 2rem; border-radius:10px; margin-bottom:1rem;
  }
  .page-header h2 { color:white; margin:0; }
  .page-header p  { color:rgba(255,255,255,.88); margin:.3rem 0 0; }
  .bubble-human {
    background:#EBF5FB; border-radius:16px 16px 4px 16px;
    padding:.75rem 1.1rem; margin:.5rem 0 .5rem 12%;
    border-left:3px solid #006FCF;
  }
  .bubble-agent {
    background:#F0FFF4; border-radius:16px 16px 16px 4px;
    padding:.75rem 1.1rem; margin:.5rem 12% .5rem 0;
    border-left:3px solid #27ae60;
  }
  .bubble-context {
    background:#FFF8E7; border-radius:8px;
    padding:.6rem 1rem; margin:.4rem 8%;
    border-left:3px solid #B5A06A; font-size:.85rem; color:#555;
  }
  .mem-card {
    background:#fff; border:1px solid #d5e8f7; border-radius:10px;
    padding:.9rem 1rem; margin:.5rem 0;
    border-top:3px solid #8e44ad;
  }
  .mem-card h5 { color:#8e44ad; margin:0 0 .4rem; font-size:.9rem; }
  .tool-chip { background:#EEF3FB; color:#006FCF; border-radius:5px;
    padding:1px 8px; font-size:.76rem; font-weight:600; display:inline-block; margin:1px; }
  .mcp-chip  { background:#E9F7EF; color:#1a7340; border-radius:5px;
    padding:1px 8px; font-size:.76rem; font-weight:600; display:inline-block; margin:1px; }
  .blog-feature-tag {
    display:inline-block; padding:.18rem .65rem; border-radius:20px;
    font-size:.73rem; font-weight:700; margin:.15rem; border:1.5px solid;
  }
  .bft-vector { background:#dbeafe; color:#1d4ed8; border-color:#93c5fd; }
  .bft-hybrid { background:#d1fae5; color:#065f46; border-color:#6ee7b7; }
  .bft-mql    { background:#fef3c7; color:#92400e; border-color:#fcd34d; }
  .bft-ckpt   { background:#ede9fe; color:#5b21b6; border-color:#c4b5fd; }
  .bft-smith  { background:#fee2e2; color:#991b1b; border-color:#fca5a5; }
  .blog-note  { background:#f8faff; border:1px solid #c8d8f0; border-left:4px solid #006FCF;
    border-radius:6px; padding:.55rem .9rem; font-size:.82rem; color:#334; margin:.4rem 0; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
  <h2>🔍 Data Discovery — Conversational Intelligence</h2>
  <p>
    Multi-turn chat &nbsp;·&nbsp; MongoDB MCP Server &nbsp;·&nbsp;
    Voyage AI semantic memory &nbsp;·&nbsp; Cross-session recall
  </p>
  <p style="margin-top:.6rem;">
    <span class="blog-feature-tag bft-mql">🟡 Text-to-MQL</span>
    <span class="blog-feature-tag bft-vector">🔵 Atlas Vector Search</span>
    <span class="blog-feature-tag bft-hybrid">🟢 Hybrid Search ($rankFusion)</span>
    <span class="blog-feature-tag bft-ckpt">🟣 MongoDB Checkpointer</span>
    <span class="blog-feature-tag bft-smith">🔴 LangSmith Observability</span>
    &nbsp;<a href="https://blog.langchain.com/announcing-the-langchain-mongodb-partnership-the-ai-agent-stack-that-runs-on-the-database-you-already-trust/" target="_blank" style="color:rgba(255,255,255,.75);font-size:.78rem;">📄 Partnership blog →</a>
  </p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE initialisation
# ══════════════════════════════════════════════════════════════════════════════
MCP_TOOL_NAMES = {
    "find","aggregate","collection-schema","collection-indexes",
    "collection-storage-size","count","db-stats","explain",
    "list-collections","list-databases","search-knowledge","list-knowledge-sources",
}

def _new_session_id() -> str:
    return f"disco-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

if "disco_session_id"   not in st.session_state:
    st.session_state.disco_session_id   = _new_session_id()
if "disco_messages"     not in st.session_state:
    st.session_state.disco_messages     = []   # list of {"role","content","tools","mcp"}
if "disco_lc_history"   not in st.session_state:
    st.session_state.disco_lc_history   = []   # list[BaseMessage] for agent context
if "disco_mem_injected" not in st.session_state:
    st.session_state.disco_mem_injected = False  # only inject memory context once per session
if "disco_last_tools"   not in st.session_state:
    st.session_state.disco_last_tools   = []

# ── Sidebar: memory panel ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    st.markdown("### 🧠 Semantic Memory")
    st.caption("Past sessions — stored in MongoDB, retrieved by vector similarity")

    from memory.mongodb_memory import SessionMemoryStore
    _sms = SessionMemoryStore("metadata_agent")
    _memories = _sms.list_all_memories(limit=8)

    if _memories:
        for m in _memories:
            ts = m.get("created_at", "")
            if hasattr(ts, "strftime"):
                ts = ts.strftime("%b %d %H:%M")
            datasets = ", ".join(m.get("datasets_explored", [])[:3]) or "—"
            st.markdown(
                f"**{m.get('memory_id','?')}** · {ts}\n\n"
                f"_{m.get('summary','')[:120]}..._\n\n"
                f"**Collections:** {datasets}",
                help="\n".join(m.get("key_insights", [])[:5]),
            )
            st.markdown("---")
    else:
        st.caption("No memories yet. End a session to store the first one.")

    st.markdown(f"**Session:** `{st.session_state.disco_session_id}`")

# ── Blog feature callouts ──────────────────────────────────────────────────────
st.markdown("""
<div class="blog-note">
  <span class="blog-feature-tag bft-mql">🟡 Blog Feature: Text-to-MQL</span>
  &nbsp; The <strong>MongoDB MCP Server</strong> below exposes <code>find</code>, <code>aggregate</code>,
  <code>collection-schema</code>, and 9 more tools — giving this agent <em>natural-language-to-MQL</em>
  capability identical to the <a href="https://blog.langchain.com/announcing-the-langchain-mongodb-partnership-the-ai-agent-stack-that-runs-on-the-database-you-already-trust/" target="_blank">MongoDBDatabaseToolkit</a>
  described in the LangChain × MongoDB partnership blog.
  &nbsp;&nbsp;
  <span class="blog-feature-tag bft-hybrid">🟢 Blog Feature: Hybrid Search — native Atlas <code>$rankFusion</code></span>
  &nbsp; <code>hybrid_search_catalog</code> sends a <strong>single aggregation pipeline</strong> to Atlas:
  a <code>$vectorSearch</code> (Voyage AI semantic) leg and a <code>$search</code> (BM25 full-text) leg,
  fused server-side via Reciprocal Rank Fusion inside Atlas — <em>zero Python-side score merging</em>.
</div>
""", unsafe_allow_html=True)

# ── MCP status banner ──────────────────────────────────────────────────────────
with st.expander("⚙️ MongoDB MCP Server Status", expanded=False):
    from config import MONGODB_MCP_SERVER_URL, MONGODB_MCP_TRANSPORT
    from tools.mongodb_mcp_client import active_transport
    import httpx as _httpx

    mode = active_transport()

    if mode == "embedded":
        st.success(
            "🟢 **Transport: embedded** — mongodb-mcp-server spawned automatically "
            "as an npx stdio subprocess on each agent call. No separate server needed."
        )
        st.caption("Switch to HTTP: set `MONGODB_MCP_TRANSPORT=http` in `.env` and restart.")
    else:
        try:
            _httpx.get(f"{MONGODB_MCP_SERVER_URL}/", timeout=2)
            st.success(
                f"🟢 **Transport: http** — MongoDB MCP server RUNNING at `{MONGODB_MCP_SERVER_URL}`"
            )
        except Exception:
            st.error(
                f"🔴 **Transport: http** — server NOT reachable at `{MONGODB_MCP_SERVER_URL}`"
            )
            st.code(
                f"MDB_MCP_CONNECTION_STRING=\"{os.getenv('MONGODB_URI','')}\" \\\n"
                f"npx -y mongodb-mcp-server@latest \\\n"
                f"  --transport http --httpPort 3001 \\\n"
                f"  --readOnly --disabledTools atlas",
                language="bash",
            )
        st.caption("Switch to embedded: set `MONGODB_MCP_TRANSPORT=embedded` in `.env` and restart.")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# CHAT AREA
# ══════════════════════════════════════════════════════════════════════════════

EXAMPLE_QUERIES = [
    "Which datasets contain fraud-related information?",
    "Show the schema of the transactions collection",
    "Find all Platinum cardholder transactions above $5000 last month",
    "What datasets have geospatial data?",
    "Show spending by category for cardholder CH_0001",
    "Which merchants are connected to fraud rings in the network graph?",
    "Find restaurants within 5km of Times Square (lon: -73.985, lat: 40.758)",
    "What are the top 5 highest fraud-score transactions?",
]

# ── Quick-start prompts (only when chat is empty) ──────────────────────────────
if not st.session_state.disco_messages:
    st.markdown("##### 💡 Try one of these to start:")
    ex_cols = st.columns(4)
    for i, eq in enumerate(EXAMPLE_QUERIES):
        if ex_cols[i % 4].button(eq[:38] + "…", key=f"qs_{i}", use_container_width=True):
            st.session_state["_disco_prefill"] = eq

# ── Render existing chat bubbles ───────────────────────────────────────────────
for turn in st.session_state.disco_messages:
    if turn["role"] == "context":
        st.markdown(
            f'<div class="bubble-context">📚 <em>{turn["content"][:200]}…</em></div>',
            unsafe_allow_html=True,
        )
    elif turn["role"] == "user":
        st.markdown(
            f'<div class="bubble-human">🧑 <strong>You</strong><br>{turn["content"]}</div>',
            unsafe_allow_html=True,
        )
    else:  # assistant
        mcp_active = turn.get("mcp", False)
        badge = "🍃 MongoDB MCP" if mcp_active else "⚙️ pymongo fallback"
        st.markdown(
            f'<div class="bubble-agent">🤖 <strong>Agent</strong> <small>({badge})</small>'
            f'<br>{turn["content"]}</div>',
            unsafe_allow_html=True,
        )
        if turn.get("tools"):
            chips = " ".join(
                f'<span class="{"mcp-chip" if t in MCP_TOOL_NAMES else "tool-chip"}">{"🍃 " if t in MCP_TOOL_NAMES else "✓ "}{t}</span>'
                for t in turn["tools"]
            )
            st.markdown(chips, unsafe_allow_html=True)

# ── Input row ──────────────────────────────────────────────────────────────────
st.markdown("")
with st.form("disco_chat_form", clear_on_submit=True):
    inp_col, btn_col = st.columns([7, 1])
    with inp_col:
        user_input = st.text_input(
            "Message",
            value=st.session_state.pop("_disco_prefill", ""),
            placeholder="Ask about any NFG dataset, schema, or data pattern…",
            label_visibility="collapsed",
        )
    with btn_col:
        send = st.form_submit_button("Send ➤", use_container_width=True)

# ── Action buttons row ─────────────────────────────────────────────────────────
act_c1, act_c2, act_c3 = st.columns([2, 2, 3])
with act_c1:
    end_session = st.button(
        "💾 End Session & Store Memory",
        help="🟣 Blog Feature: MongoDB Checkpointer — Condenses this conversation with GPT-4o, embeds with Voyage AI, and upserts as a durable semantic memory document in MongoDB Atlas. Retrieved via Atlas Vector Search in future sessions.",
        use_container_width=True,
    )
with act_c2:
    clear_chat = st.button("🗑️ Clear Chat (keep memory)", use_container_width=True)
with act_c3:
    st.caption(
        f"💬 {len(st.session_state.disco_messages)} turns · "
        f"Session: `{st.session_state.disco_session_id}`"
    )

# ══════════════════════════════════════════════════════════════════════════════
# SEND MESSAGE handler
# ══════════════════════════════════════════════════════════════════════════════
if send and user_input.strip():
    question = user_input.strip()
    from agents.metadata_agent import run_metadata_query
    from memory.mongodb_memory import SessionMemoryStore
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

    sms = SessionMemoryStore("metadata_agent")

    # ── On first turn: retrieve relevant past session memories ────────────────
    memory_ctx_msg = None
    if not st.session_state.disco_mem_injected and st.session_state.disco_lc_history == []:
        memory_ctx_msg = sms.build_memory_context_message(question, limit=2)
        if memory_ctx_msg:
            st.session_state.disco_messages.append({
                "role": "context",
                "content": memory_ctx_msg.content,
            })
        st.session_state.disco_mem_injected = True

    st.session_state.disco_messages.append({"role": "user", "content": question})

    is_first_mcp_call = len(st.session_state.disco_lc_history) == 0
    spinner_msg = (
        "🤖 Agent starting… (first call downloads the MCP npm package — may take ~60 s)"
        if is_first_mcp_call else
        "🤖 Agent reasoning + querying MongoDB…"
    )
    with st.spinner(spinner_msg):
        import traceback as _tb
        try:
            result = run_metadata_query(
                question=question,
                session_id=st.session_state.disco_session_id,
                history=st.session_state.disco_lc_history,
                memory_context=memory_ctx_msg,
            )

            answer = result.get("answer", "")
            tools  = result.get("tool_calls", [])
            mcp_on = result.get("mcp_tools_active", False)

            # Surface fallback reason if present
            fallback_note = ""
            if result.get("fallback_reason"):
                fallback_note = f"\n\n> ⚠️ *MCP unavailable ({result['fallback_reason'][:120]}…) — used pymongo fallback tools.*"

            if not answer:
                answer = "⚠️ Agent returned an empty response. Please try again."

            # Append turn to UI message list
            st.session_state.disco_messages.append({
                "role": "assistant",
                "content": answer + fallback_note,
                "tools": tools,
                "mcp": mcp_on,
            })
            st.session_state.disco_last_tools = tools

            # Update LangChain history for next turn
            st.session_state.disco_lc_history.append(HumanMessage(content=question))
            st.session_state.disco_lc_history.append(AIMessage(content=answer))

        except Exception as e:
            err_detail = _tb.format_exc()
            st.session_state.disco_messages.append({
                "role": "assistant",
                "content": (
                    f"⚠️ **Error calling the agent:**\n\n```\n{err_detail[-800:]}\n```\n\n"
                    "**Quick checks:**\n"
                    "- Is `MONGODB_URI` correct in `.env`?\n"
                    "- Is `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` set?\n"
                    "- Does `npx` work in this terminal? (`npx --version`)\n"
                    "- Set `MONGODB_MCP_TRANSPORT=http` in `.env` to disable embedded mode."
                ),
                "tools": [], "mcp": False,
            })

    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# END SESSION handler — LLM distil → Voyage embed → MongoDB store
# ══════════════════════════════════════════════════════════════════════════════
if end_session:
    lc_msgs = st.session_state.disco_lc_history
    if not lc_msgs:
        st.warning("Nothing to store — the conversation is empty.")
    else:
        with st.spinner("🧠 Condensing conversation with LLM… embedding with Voyage AI… storing in MongoDB…"):
            try:
                from memory.mongodb_memory import SessionMemoryStore
                from langchain_openai import AzureChatOpenAI
                from config import (AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT,
                                    AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT)

                llm = AzureChatOpenAI(
                    azure_endpoint=AZURE_OPENAI_ENDPOINT,
                    api_key=AZURE_OPENAI_API_KEY,
                    api_version=AZURE_OPENAI_API_VERSION,
                    azure_deployment=AZURE_OPENAI_DEPLOYMENT,
                    temperature=0,
                )
                sms = SessionMemoryStore("metadata_agent")
                stored = sms.condense_and_store(
                    session_id=st.session_state.disco_session_id,
                    messages=lc_msgs,
                    llm=llm,
                )

                # Show the condensed summary
                st.success(f"✅ Memory stored: **{stored.get('memory_id')}**")
                st.markdown("**📝 Distilled Summary**")
                st.info(stored.get("summary", ""))

                c1, c2 = st.columns(2)
                with c1:
                    if stored.get("datasets_explored"):
                        st.markdown("**Collections explored:**")
                        for d in stored["datasets_explored"]:
                            st.markdown(f"  • `{d}`")
                    if stored.get("key_insights"):
                        st.markdown("**Key insights:**")
                        for ins in stored["key_insights"]:
                            st.markdown(f"  • {ins}")
                with c2:
                    if stored.get("queries_run"):
                        st.markdown("**Queries run:**")
                        for q in stored["queries_run"]:
                            st.markdown(f"  • {q}")
                    if stored.get("data_patterns"):
                        st.markdown("**Data patterns:**")
                        for p in stored["data_patterns"]:
                            st.markdown(f"  • {p}")

                st.markdown("""
<div class="blog-note">
  <span class="blog-feature-tag bft-ckpt">🟣 Blog Feature: MongoDB Checkpointer</span>
  &nbsp; Conversation distilled by GPT-4o → embedded by Voyage AI (1024-dim) →
  stored as a durable document in <code>session_memories</code>.
  &nbsp;<span class="blog-feature-tag bft-vector">🔵 Blog Feature: Atlas Vector Search</span>
  &nbsp; Future sessions retrieve these memories via <code>$vectorSearch</code> — persistent
  agent state across sessions, exactly as described in the
  <a href="https://blog.langchain.com/announcing-the-langchain-mongodb-partnership-the-ai-agent-stack-that-runs-on-the-database-you-already-trust/" target="_blank">LangChain × MongoDB blog</a>.
</div>
""", unsafe_allow_html=True)

                # Reset session
                st.session_state.disco_messages     = []
                st.session_state.disco_lc_history   = []
                st.session_state.disco_session_id   = _new_session_id()
                st.session_state.disco_mem_injected = False
                st.session_state.disco_last_tools   = []

            except Exception as e:
                st.error(f"Memory consolidation failed: {e}")

        st.rerun()

# ── Clear chat ─────────────────────────────────────────────────────────────────
if clear_chat:
    st.session_state.disco_messages     = []
    st.session_state.disco_lc_history   = []
    st.session_state.disco_mem_injected = False
    st.session_state.disco_session_id   = _new_session_id()
    st.rerun()

# ── How it works expander ──────────────────────────────────────────────────────
st.markdown("---")
with st.expander("🗺️ Memory architecture — how this page works"):
    st.markdown("""
```
┌─────────────────────────────────────────────────────────────────────────┐
│                     WITHIN A SESSION                                     │
│                                                                          │
│  Turn 1: User message                                                    │
│    → retrieve_relevant_memories(query) → Atlas Vector Search             │
│    → inject past session context as SystemMessage (once per session)     │
│    → agent.ainvoke([memory_context, HumanMsg])                           │
│    → MCP tools: find / aggregate / collection-schema …                   │
│    → native tools: vector search / graph / geo                           │
│    → AIMessage appended to disco_lc_history                             │
│                                                                          │
│  Turn 2+: Full history passed to agent each turn                         │
│    → agent.ainvoke([memory_context, H1, A1, H2, A2, … HumanMsg])        │
│    → agent has complete conversational context                           │
│    → episodic turns written to conversation_history collection           │
│                                                                          │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │  "End Session & Store Memory"
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   SESSION MEMORY CONSOLIDATION                           │
│                                                                          │
│  1. Build transcript from all HumanMessage + AIMessage turns             │
│  2. Azure GPT-4o distils into structured JSON:                           │
│       { summary, datasets_explored, key_insights,                        │
│         queries_run, data_patterns, tools_used }                         │
│  3. Voyage AI (voyage-finance-2) embeds summary + insights → 1024-dim   │
│  4. Upsert into MongoDB `session_memories` collection                    │
│  5. Atlas Vector Search index on `embedding` field                       │
│                                                                          │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │  Next session starts
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CROSS-SESSION RECALL                                  │
│                                                                          │
│  1. User sends first message of new session                              │
│  2. query → Voyage AI embed → Atlas Vector Search on session_memories   │
│  3. Top-2 semantically similar past summaries retrieved                  │
│  4. Injected as SystemMessage at position 0 in agent state               │
│  5. Agent now "remembers" past findings without re-running queries       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```
**Transport:** `langchain-mcp-adapters` MultiServerMCPClient · streamable_http · per-invocation session
MongoDB collections accessed: `data_catalog`, `transactions`, `merchants`,
`cardholders`, `offers`, `fraud_cases`, `merchant_networks`
""")
