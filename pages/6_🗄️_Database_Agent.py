"""
Page 6: Natural-Language Database Agent — MongoDBDatabaseToolkit

Uses the official LangChain MongoDBDatabaseToolkit to let users
query any MongoDB collection with plain English. The toolkit
auto-discovers schemas, generates MQL, validates queries, and
executes them — all via a LangGraph ReAct agent.
"""

import streamlit as st
import sys, os, logging
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger("vaultiq.page.database_agent")

st.set_page_config(page_title="Database Agent | VaultIQ", page_icon="🗄️", layout="wide")

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stSidebar"] { background: linear-gradient(180deg,#003087 0%,#006FCF 100%); }
  [data-testid="stSidebar"] > div > div > div > * { color: white !important; }
  [data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] span, [data-testid="stSidebar"] h1,
  [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
  [data-testid="stSidebar"] h4, [data-testid="stSidebar"] li,
  [data-testid="stSidebar"] a,
  [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
  [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] * { color: white !important; }
  [data-testid="stSidebarNav"] a, [data-testid="stSidebarNav"] span { color: white !important; }
  [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.2); }
  [data-testid="stSidebar"] [data-testid="stExpander"] details { background:rgba(255,255,255,.95); border-radius:8px; }
  [data-testid="stSidebar"] [data-testid="stExpander"] summary span,
  [data-testid="stSidebar"] [data-testid="stExpander"] summary svg { color:#003087 !important; }
  [data-testid="stSidebar"] [data-testid="stExpander"] p,
  [data-testid="stSidebar"] [data-testid="stExpander"] span:not(summary span),
  [data-testid="stSidebar"] [data-testid="stExpander"] code,
  [data-testid="stSidebar"] [data-testid="stExpander"] small { color:#1a1a2e !important; }
  [data-testid="stSidebar"] [data-testid="stExpander"] code { background:#e8ecf1; padding:1px 5px; border-radius:3px; }
  [data-testid="stSidebar"] .stAlert p, [data-testid="stSidebar"] .stAlert span { color:#1a1a2e !important; }
  .page-header {
    background: linear-gradient(135deg,#003087,#006FCF);
    padding:1.5rem 2rem; border-radius:10px; margin-bottom:1rem;
  }
  .page-header h2 { color:white; margin:0; }
  .page-header p  { color:rgba(255,255,255,.88); margin:.3rem 0 0; }
  .blog-feature-tag {
    display:inline-block; padding:.18rem .65rem; border-radius:20px;
    font-size:.73rem; font-weight:700; margin:.15rem; border:1.5px solid;
  }
  .bft-vector { background:#dbeafe; color:#1d4ed8; border-color:#93c5fd; }
  .bft-mql    { background:#fef3c7; color:#92400e; border-color:#fcd34d; }
  .bft-ckpt   { background:#ede9fe; color:#5b21b6; border-color:#c4b5fd; }
  .bft-smith  { background:#fee2e2; color:#991b1b; border-color:#fca5a5; }
  .bft-toolkit { background:#d1fae5; color:#065f46; border-color:#6ee7b7; }
  .blog-note  { background:#f8faff; border:1px solid #c8d8f0; border-left:4px solid #006FCF;
    border-radius:6px; padding:.55rem .9rem; font-size:.82rem; color:#334; margin:.4rem 0; }
  .answer-box { background:#f0fff4; border:1px solid #b7e4c7; border-left:4px solid #27ae60;
    border-radius:6px; padding:1rem; margin:.5rem 0; }
  .tool-chip { background:#EEF3FB; color:#006FCF; border-radius:5px;
    padding:1px 8px; font-size:.76rem; font-weight:600; display:inline-block; margin:1px; }
  .step-box { background:#f8f9fa; border:1px solid #d5e0ea; border-radius:6px;
    padding:.7rem 1rem; margin:.4rem 0; }
  .alert-red { background:#fff5f5; border-left:4px solid #e53e3e; padding:.6rem 1rem;
    border-radius:0 6px 6px 0; margin:.3rem 0; font-size:.85rem; }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
  <h2>🗄️ Use Case 5: Natural-Language Database Agent</h2>
  <p>Query any MongoDB collection using plain English — powered by
     <code style="color:#fcd34d">MongoDBDatabaseToolkit</code></p>
  <p style="margin-top:.6rem">
    <span class="blog-feature-tag bft-toolkit">🍃 MongoDBDatabaseToolkit</span>
    <span class="blog-feature-tag bft-mql">🟡 Text-to-MQL</span>
    <span class="blog-feature-tag bft-ckpt">🟣 MongoDB Checkpointer</span>
    <span class="blog-feature-tag bft-smith">🔴 LangSmith Observability</span>
  </p>
</div>
""", unsafe_allow_html=True)


# ── Overview columns ───────────────────────────────────────────────────────────
col_info, col_tools = st.columns([3, 2])

with col_info:
    st.markdown("""
**What is MongoDBDatabaseToolkit?**

The [MongoDBDatabaseToolkit](https://langchain-mongodb.readthedocs.io/en/stable/) is the
official LangChain integration for MongoDB. It provides a set of tools that allow an LLM agent
to autonomously discover, query, and validate MongoDB data using natural language.

Unlike hand-built tools, the toolkit **auto-discovers** your schema and generates MQL
dynamically — no per-collection tool definitions needed.

**How it works:**
1. 🔎 Agent inspects collection schemas and sample documents
2. 📝 LLM generates an MQL aggregation pipeline from your question
3. ✅ Query checker validates the pipeline before execution
4. ⚡ Query runs against MongoDB Atlas and results are returned
5. 💬 LLM formats results into a human-readable answer
""")

    st.markdown("""
<div class="blog-note">
  <span class="blog-feature-tag bft-toolkit">🍃 Blog Feature: MongoDBDatabaseToolkit</span>
  &nbsp; This page uses <code>MongoDBDatabaseToolkit</code> from <code>langchain-mongodb</code>.
  The agent has <strong>zero hard-coded queries</strong> — every MQL pipeline is generated
  dynamically by the LLM based on your natural-language question. The toolkit also includes
  a query-checker tool that validates generated MQL before execution.
</div>
""", unsafe_allow_html=True)

with col_tools:
    st.markdown("**🔧 Toolkit Tools (auto-provided):**")
    toolkit_tools = [
        ("📋 ListMongoDBDatabaseTool", "Lists all collections in the database"),
        ("🔍 InfoMongoDBDatabaseTool", "Shows schema, indexes, and sample docs for a collection"),
        ("⚡ QueryMongoDBDatabaseTool", "Executes MQL find/aggregate queries"),
        ("✅ QueryMongoDBCheckerTool", "LLM validates the generated query before execution"),
    ]
    for name, desc in toolkit_tools:
        st.markdown(f"""<div class="step-box">
          <strong>{name}</strong><br>
          <small style="color:#555">{desc}</small>
        </div>""", unsafe_allow_html=True)

    st.markdown("**📚 Available Collections:**")
    collections = [
        "cardholders", "transactions", "merchants", "offers",
        "fraud_cases", "compliance_rules", "merchant_networks",
        "data_catalog", "conversation_history",
    ]
    chips = " ".join(f'<span class="tool-chip">{c}</span>' for c in collections)
    st.markdown(chips, unsafe_allow_html=True)

# ── Sidebar: example queries ──────────────────────────────────────────────────
EXAMPLE_QUERIES = [
    ("💳 Top spenders", "Who are the top 5 cardholders by total transaction amount?"),
    ("🚨 Fraud hotspots", "Which merchant categories have the highest average fraud scores?"),
    ("🎁 Best offers", "What offers are available for Platinum tier cardholders?"),
    ("📊 Monthly trends", "Show me the total transaction volume by month for the last 6 months."),
    ("🌍 Geo analysis", "Which cities have the most cardholders?"),
    ("⚖️ Compliance rules", "List all BSA compliance rules and their thresholds."),
    ("🕸️ Merchant networks", "Show me all merchant network connections with risk_tier 'high'."),
    ("📈 Fraud cases", "How many fraud cases are open vs closed? What's the average severity?"),
]

with st.sidebar:
    st.markdown("### 🗄️ Example Queries")
    st.markdown(
        "<small>Click any example to auto-fill the query input.</small>",
        unsafe_allow_html=True,
    )
    for label, query in EXAMPLE_QUERIES:
        with st.expander(label, expanded=False):
            st.markdown(f"<small>{query}</small>", unsafe_allow_html=True)
            if st.button("📋 Use this query", key=f"eq_{label}"):
                st.session_state["db_query_input"] = query

# ── Query input ───────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🎯 Ask the Database Agent")

if "db_query_input" not in st.session_state:
    st.session_state["db_query_input"] = ""
if "db_results" not in st.session_state:
    st.session_state["db_results"] = []

query_input = st.text_area(
    "Ask any question about your MongoDB data:",
    value=st.session_state.get("db_query_input", ""),
    placeholder="e.g. Who are the top 5 cardholders by total transaction amount?",
    height=80,
    key="db_query_text",
)

col_run, col_clear = st.columns([1, 4])
with col_run:
    run_clicked = st.button("🚀 Run Query", type="primary")
with col_clear:
    if st.button("🗑️ Clear History"):
        st.session_state["db_results"] = []
        st.session_state["db_query_input"] = ""
        st.rerun()

if run_clicked and query_input.strip():
    with st.spinner("🤖 Agent is discovering schema, generating MQL, and querying MongoDB…"):
        try:
            from agents.database_agent import run_database_query
            result = run_database_query(
                question=query_input.strip(),
                session_id="streamlit-db-agent",
            )
            st.session_state["db_results"].insert(0, {
                "question": query_input.strip(),
                "answer": result.get("answer", ""),
                "tool_calls": result.get("tool_calls", []),
                "messages": result.get("messages", []),
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            })
            st.session_state["db_query_input"] = ""
            st.rerun()
        except Exception as e:
            st.error(f"❌ Agent error: {e}")
            logger.exception("Database agent error: %s", e)

# ── Results feed ──────────────────────────────────────────────────────────────
if st.session_state["db_results"]:
    for i, r in enumerate(st.session_state["db_results"][:10]):
        ts = r.get("timestamp", "?")
        q = r.get("question", "?")
        ans = r.get("answer", "")
        tools = r.get("tool_calls", [])

        with st.expander(f"⏰ {ts} — **{q[:80]}**", expanded=(i == 0)):
            # Tool trace
            if tools:
                tool_chips = " ".join(f'<span class="tool-chip">{t}</span>' for t in tools)
                st.markdown(f"**🔧 Toolkit tools used:** {tool_chips}", unsafe_allow_html=True)

            # Answer
            st.markdown(f'<div class="answer-box">{ans}</div>', unsafe_allow_html=True)

            # Full agent trace
            msgs = r.get("messages", [])
            if msgs:
                with st.expander("📜 Full Agent Trace (MQL generated, tool calls, validation)"):
                    for msg in msgs:
                        role = getattr(msg, "type", "?")
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tc in msg.tool_calls:
                                name = tc.get("name", "?")
                                args = tc.get("args", {})
                                st.markdown(f"**🔧 Tool Call → `{name}`**")
                                st.code(str(args)[:800], language="json")
                        elif role == "tool":
                            st.markdown(f"**📤 Tool Result:**")
                            st.code(str(msg.content)[:1000])
                        elif role == "ai" and msg.content:
                            st.markdown(f"**🤖 Agent:**")
                            st.markdown(msg.content[:500])

# ── Architecture ──────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("🏗️ Architecture — MongoDBDatabaseToolkit Agent Flow"):
    st.markdown("""
```
User Question (natural language)
    │
    ▼
┌────────────────────────────────────────────────────────┐
│              LangGraph ReAct Agent                      │
│              (Azure GPT-4o)                             │
│                                                         │
│  System Prompt: MONGODB_AGENT_SYSTEM_PROMPT             │
│  + NFG collection context                               │
└────────────┬───────────────────────────────────────────┘
             │
    ┌────────▼────────────────────────────────────────────┐
    │        MongoDBDatabaseToolkit                        │
    │                                                      │
    │  ┌─────────────────────────────────────────────┐     │
    │  │ 1. ListMongoDBDatabaseTool                  │     │
    │  │    → lists all collections                   │     │
    │  ├─────────────────────────────────────────────┤     │
    │  │ 2. InfoMongoDBDatabaseTool                  │     │
    │  │    → schema + sample docs + indexes          │     │
    │  ├─────────────────────────────────────────────┤     │
    │  │ 3. QueryMongoDBCheckerTool                  │     │
    │  │    → LLM validates generated MQL             │     │
    │  ├─────────────────────────────────────────────┤     │
    │  │ 4. QueryMongoDBDatabaseTool                 │     │
    │  │    → executes MQL against MongoDB Atlas      │     │
    │  └─────────────────────────────────────────────┘     │
    └─────────────────────────────────────────────────────┘
             │
             ▼
    MongoDB Atlas (VaultIQ database)
    ┌─────────────────────────────────────────────────────┐
    │  cardholders │ transactions │ merchants │ offers    │
    │  fraud_cases │ compliance_rules │ merchant_networks │
    │  data_catalog │ conversation_history                │
    └─────────────────────────────────────────────────────┘
```

**Key difference from other agents:** This agent has **zero custom tools**.
All 4 tools come from `MongoDBDatabaseToolkit` out of the box. The LLM
generates every MQL pipeline dynamically based on the question and schema.

**Python setup:**
```python
from langchain_mongodb.agent_toolkit import (
    MongoDBDatabaseToolkit, MongoDBDatabase, MONGODB_AGENT_SYSTEM_PROMPT,
)
from langgraph.prebuilt import create_react_agent

db = MongoDBDatabase.from_connection_string(MONGODB_URI, database=DB_NAME)
toolkit = MongoDBDatabaseToolkit(db=db, llm=llm)
agent = create_react_agent(llm, toolkit.get_tools(), prompt=system_prompt)
```
""")

st.markdown("---")
st.caption("Powered by [langchain-mongodb](https://github.com/langchain-ai/langchain-mongodb) · MongoDBDatabaseToolkit")