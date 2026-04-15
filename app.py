"""
VaultIQ — NextGen AI Financial Intelligence Suite
Powered by: MongoDB Atlas · LangChain · LangGraph · Voyage AI · Azure OpenAI · FastMCP
"""

import streamlit as st
import os, sys, logging
sys.path.insert(0, os.path.dirname(__file__))

logger = logging.getLogger("vaultiq.app")

# ── Page config (must be first Streamlit call) ─────────────────────────────────
st.set_page_config(
    page_title="VaultIQ — AI Financial Intelligence",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── VaultIQ brand CSS (MongoDB Atlas palette) ──────────────────────────────────
st.markdown("""
<style>
  /* VaultIQ · MongoDB Atlas palette */
  :root {
    --brand-primary: #00ED64;
    --brand-dark:    #001E2B;
    --brand-mid:     #00A35C;
    --brand-light:   #E3FCF0;
  }
  [data-testid="stSidebar"] { background: linear-gradient(180deg, #001E2B 0%, #023047 100%); }
  [data-testid="stSidebar"] * { color: white !important; }
  [data-testid="stSidebar"] .stMarkdown h1,
  [data-testid="stSidebar"] .stMarkdown h2,
  [data-testid="stSidebar"] .stMarkdown h3 { color: #00ED64 !important; }
  [data-testid="stSidebar"] hr { border-color: rgba(0,237,100,0.25); }
  .main-header {
    background: linear-gradient(135deg, #001E2B 0%, #023047 60%, #0D3B50 100%);
    padding: 2rem 2.5rem; border-radius: 12px; margin-bottom: 1.5rem;
    box-shadow: 0 4px 20px rgba(0,237,100,0.2);
    border: 1px solid rgba(0,237,100,0.15);
  }
  .main-header h1 { color: white; font-size: 2.4rem; font-weight: 700; margin: 0; }
  .main-header p  { color: rgba(255,255,255,0.88); font-size: 1.05rem; margin: 0.5rem 0 0; }
  .badge {
    display: inline-block; padding: 0.25rem 0.75rem; border-radius: 20px;
    font-size: 0.78rem; font-weight: 600; margin: 0.2rem;
  }
  .badge-blue   { background:#00A35C; color:white; }
  .badge-green  { background:#00ED64; color:#001E2B; }
  .badge-gold   { background:#FFD700; color:#001E2B; }
  .badge-purple { background:#7C3AED; color:white; }
  .use-case-card {
    background: white; border: 1px solid #c8f0da; border-radius: 12px;
    padding: 1.4rem 1.6rem; margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06); transition: box-shadow 0.2s;
  }
  .use-case-card:hover { box-shadow: 0 4px 16px rgba(0,163,92,0.18); }
  .use-case-card h3 { color: #001E2B; margin-bottom: 0.4rem; }
  .use-case-card p  { color: #444; font-size: 0.95rem; }
  .tech-pill {
    background: #E3FCF0; color: #00593A; border-radius: 6px;
    padding: 2px 10px; font-size: 0.78rem; font-weight: 600;
    display: inline-block; margin: 2px;
  }
  .memory-box {
    background: #F0FFF6; border-left: 4px solid #00ED64;
    padding: 0.8rem 1rem; border-radius: 6px; margin: 0.5rem 0;
    font-size: 0.88rem; color: #555;
  }
  .stButton > button {
    background: #00A35C; color: white; border-radius: 8px;
    border: none; font-weight: 600; padding: 0.5rem 1.5rem;
  }
  .stButton > button:hover { background: #001E2B; }
  /* Blog feature badges */
  .blog-banner {
    background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
    border: 1px solid #30363d; border-radius: 10px;
    padding: 1rem 1.4rem; margin: 1rem 0;
    display: flex; align-items: flex-start; gap: 1rem;
  }
  .blog-banner p { color: #c9d1d9; margin: 0; font-size: 0.92rem; }
  .blog-banner a { color: #58a6ff; text-decoration: none; font-weight: 600; }
  .blog-feature-tag {
    display: inline-block; padding: 0.18rem 0.65rem; border-radius: 20px;
    font-size: 0.74rem; font-weight: 700; margin: 0.15rem;
    border: 1.5px solid;
  }
  .bft-vector  { background:#dbeafe; color:#1d4ed8; border-color:#93c5fd; }
  .bft-hybrid  { background:#d1fae5; color:#065f46; border-color:#6ee7b7; }
  .bft-mql     { background:#fef3c7; color:#92400e; border-color:#fcd34d; }
  .bft-ckpt    { background:#ede9fe; color:#5b21b6; border-color:#c4b5fd; }
  .bft-smith   { background:#fee2e2; color:#991b1b; border-color:#fca5a5; }
  .feature-table { width:100%; border-collapse:collapse; font-size:0.88rem; }
  .feature-table th {
    background:#EEF3FB; color:#003087; padding:0.55rem 0.8rem;
    text-align:left; border-bottom:2px solid #c8d8f0;
  }
  .feature-table td { padding:0.5rem 0.8rem; border-bottom:1px solid #e8eef8; vertical-align:top; }
  .feature-table tr:hover td { background:#f8faff; }
  .check { color:#27ae60; font-weight:700; }
  .dash  { color:#bbb; }
</style>
""", unsafe_allow_html=True)

# ── Atlas Cluster Health Check (runs once per session) ─────────────────────────
from tools.atlas_cluster import (
    is_configured as _atlas_configured,
    get_cluster_status, resume_cluster, wait_for_ready,
)
from pymongo import MongoClient as _HealthCheckClient
from pymongo.errors import ConnectionFailure as _ConnFail, ServerSelectionTimeoutError as _SSTimeout
from config import MONGODB_URI

if "atlas_checked" not in st.session_state:
    st.session_state.atlas_checked = False

if not st.session_state.atlas_checked:
    # ── Step 1: direct pymongo ping (works without Atlas API) ──────────────
    _cluster_reachable = False
    try:
        _hc = _HealthCheckClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        _hc.admin.command("ping")
        _cluster_reachable = True
        _hc.close()
        logger.info("Atlas cluster ping OK — cluster is reachable")
    except (_ConnFail, _SSTimeout, Exception) as _ping_err:
        logger.warning("Atlas cluster ping FAILED: %s", _ping_err)

    if _cluster_reachable:
        # Cluster is up — nothing to do
        st.session_state.atlas_checked = True

    elif _atlas_configured():
        # ── Step 2: cluster unreachable + API configured → check & resume ──
        status = get_cluster_status()
        logger.info("Atlas API cluster status: %s", status)

        if status.get("paused"):
            with st.status("⏸️ Atlas cluster is paused — auto-resuming…", expanded=True) as atlas_status:
                atlas_status.write(f"Cluster **{status.get('name')}** is paused. Sending resume request…")
                resume_result = resume_cluster()
                if resume_result.get("error"):
                    atlas_status.update(label=f"❌ Failed to resume: {resume_result['error']}", state="error")
                    st.stop()
                atlas_status.write("✅ Resume request accepted. Waiting for cluster to become ready…")
                atlas_status.write("_This typically takes 1–3 minutes for M0/M10, longer for larger tiers._")
                ready = wait_for_ready(max_wait=300, poll_interval=15)
                if ready.get("stateName") == "IDLE":
                    atlas_status.update(
                        label=f"✅ Atlas cluster ready ({ready.get('elapsed', '?')}s)",
                        state="complete", expanded=False,
                    )
                    st.session_state.atlas_checked = True
                    st.toast(f"Atlas cluster resumed in {ready.get('elapsed')}s ✅", icon="🍃")
                else:
                    atlas_status.update(
                        label=f"⚠️ Cluster not ready: {ready.get('stateName')}",
                        state="error",
                    )
                    st.stop()
        else:
            # API says not paused but pymongo can't reach it — network/firewall issue
            st.error(
                f"🔌 **Cannot reach Atlas cluster.**\n\n"
                f"Atlas API says cluster state is **{status.get('stateName', 'UNKNOWN')}** (not paused), "
                f"but pymongo ping failed.\n\n"
                f"**Check:**\n"
                f"- Is your IP address in the Atlas Network Access allowlist?\n"
                f"- Is `MONGODB_URI` correct in `.env`?\n"
                f"- Is there a firewall/VPN blocking port 27017?"
            )
            st.stop()

    else:
        # ── Step 3: cluster unreachable + no API → show manual instructions ──
        st.error(
            "🔌 **Cannot connect to MongoDB Atlas cluster.**\n\n"
            f"```\n{str(_ping_err)[:300]}\n```\n\n"
            "**The cluster may be paused.** To auto-resume on startup, add these to `.env`:\n"
            "```\n"
            "ATLAS_API_CLIENT_ID=your-service-account-client-id\n"
            "ATLAS_API_CLIENT_SECRET=your-service-account-client-secret\n"
            "ATLAS_API_PROJECT_ID=your-atlas-project-id\n"
            "ATLAS_API_CLUSTER_NAME=your-cluster-name\n"
            "```\n\n"
            "Or resume manually at [cloud.mongodb.com](https://cloud.mongodb.com)."
        )
        st.stop()


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    try:
        st.image("assets/logo.svg", use_container_width=True)
    except Exception:
        st.markdown("## 🏦 VaultIQ")
    st.markdown("### NextGen AI · FSI Intelligence")
    st.markdown("---")
    st.markdown("""
**Powered by**
- 🔗 LangChain + LangGraph
- 🍃 MongoDB Atlas
- 🚀 Voyage AI Embeddings
- 🤖 Azure OpenAI GPT-4o
- ⚡ FastMCP Tool Server
""")
    st.markdown("---")
    st.markdown("**🔗 LangChain × MongoDB Blog Features**")
    st.markdown(
        '<a href="https://blog.langchain.com/announcing-the-langchain-mongodb-partnership-the-ai-agent-stack-that-runs-on-the-database-you-already-trust/" '
        'target="_blank" style="color:#B5A06A;font-size:0.78rem;">📄 Read the partnership blog →</a>',
        unsafe_allow_html=True,
    )
    st.markdown("""
- 🔵 **Atlas Vector Search**
- 🟢 **Hybrid Search** (`$rankFusion`: BM25 + vector, server-side Atlas)
- 🟡 **Text-to-MQL** (NL → MongoDB)
- 🟣 **MongoDB Checkpointer**
- 🔴 **LangSmith Observability**
""")
    st.markdown("---")
    st.markdown("**MongoDB Query Patterns**")
    st.markdown("""
- 🔍 Vector Search
- 🔀 `$rankFusion` Hybrid Search
- 🕸️ Graph Lookup
- 📍 Geospatial Queries
- 📈 Time-Series Aggregation
- 🗂️ Structured + Unstructured
""")
    st.markdown("---")
    st.markdown("**Agent Memory Types**")
    st.markdown("""
- 🧠 Episodic (chat history)
- 📚 Semantic (vector knowledge)
- 🔧 Procedural (playbooks)
- ⚡ Working (LangGraph state)
""")
    st.markdown("---")
    st.caption("© 2025 Nexus Financial Group · VaultIQ Platform | Demo Only")

# ── Logo + Hero ────────────────────────────────────────────────────────────────
try:
    st.image("assets/logo.svg", width=480)
except Exception:
    pass

st.markdown("""
<div class="main-header">
  <h1>🏦 VaultIQ &nbsp;·&nbsp; NextGen AI Financial Intelligence Suite</h1>
  <p>
    Built for <strong>Nexus Financial Group</strong> on
    <strong>MongoDB Atlas</strong> · <strong>LangChain + LangGraph</strong> ·
    <strong>Voyage AI</strong> · <strong>Azure OpenAI GPT-4o</strong> · <strong>FastMCP</strong>
  </p>
  <div style="margin-top:1rem;">
    <span class="badge badge-blue">Vector Search</span>
    <span class="badge badge-blue">Hybrid Search</span>
    <span class="badge badge-blue">Graph Lookup</span>
    <span class="badge badge-blue">Geospatial</span>
    <span class="badge badge-blue">Time-Series</span>
    <span class="badge badge-gold">Autonomous Agents</span>
    <span class="badge badge-green">Multi-Turn Chat</span>
    <span class="badge badge-purple">Agentic Memory</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Context ────────────────────────────────────────────────────────────────────
st.markdown("### Why VaultIQ · MongoDB Atlas · LangChain?")
col1, col2, col3 = st.columns(3)
with col1:
    st.info("""
**AI-Native FSI Platform**
VaultIQ is built ground-up on MongoDB Atlas — eliminating data silos and enabling real-time AI across transactions, risk, compliance and personalisation.
""")
with col2:
    st.info("""
**60M+ Cardholders · 1M+ Merchants**
Nexus Financial Group's scale demands AI that operates across fragmented data: transactions, profiles, merchant networks, and compliance rules — all in one platform.
""")
with col3:
    st.info("""
**LangChain × MongoDB Partnership**
Atlas Vector Search + $rankFusion Hybrid Search + LangGraph Checkpointer + Text-to-MQL — one database for operational data and AI agent infrastructure.
""")


# ── LangChain × MongoDB Blog banner ───────────────────────────────────────────
st.markdown("""
<div class="blog-banner">
  <div style="font-size:2rem;line-height:1;">📄</div>
  <div>
    <p><strong style="color:#f0f6fc;">🔗 LangChain × MongoDB Partnership</strong>
    &nbsp;—&nbsp; This showcase demonstrates every key feature announced in the official partnership blog.</p>
    <p style="margin-top:0.4rem;">
      <a href="https://blog.langchain.com/announcing-the-langchain-mongodb-partnership-the-ai-agent-stack-that-runs-on-the-database-you-already-trust/" target="_blank">
        Read: "The AI Agent Stack That Runs On The Database You Already Trust" →
      </a>
    </p>
    <p style="margin-top:0.5rem;">
      <span class="blog-feature-tag bft-vector">🔵 Atlas Vector Search</span>
      <span class="blog-feature-tag bft-hybrid">🟢 Hybrid Search ($rankFusion)</span>
      <span class="blog-feature-tag bft-mql">🟡 Text-to-MQL</span>
      <span class="blog-feature-tag bft-ckpt">🟣 MongoDB Checkpointer</span>
      <span class="blog-feature-tag bft-smith">🔴 LangSmith Observability</span>
    </p>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Blog Feature → Use Case mapping table ─────────────────────────────────────
with st.expander("📊 Blog Feature Coverage — where each feature is demonstrated", expanded=True):
    st.markdown("""
<table class="feature-table">
  <thead>
    <tr>
      <th>Blog Feature</th>
      <th>🔍 P1 · Data Discovery</th>
      <th>🚨 P2 · Fraud Intelligence</th>
      <th>🎁 P3 · Personalised Offers</th>
      <th>⚖️ P4 · Compliance</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><span class="blog-feature-tag bft-vector">🔵 Atlas Vector Search</span><br><small>Semantic retrieval over enterprise data</small></td>
      <td class="check">✅ Data catalog + cross-session memory recall</td>
      <td class="check">✅ Fraud case semantic search</td>
      <td class="check">✅ Offer semantic matching</td>
      <td class="check">✅ Compliance rule retrieval</td>
    </tr>
    <tr>
      <td><span class="blog-feature-tag bft-hybrid">🟢 Hybrid Search</span><br><small><code>$rankFusion</code>: <code>$vectorSearch</code> + <code>$search</code> (BM25) fused server-side in Atlas — zero Python merging</small></td>
      <td class="check">✅ Hybrid catalog search</td>
      <td class="dash">—</td>
      <td class="check">✅ Hybrid offer search</td>
      <td class="dash">—</td>
    </tr>
    <tr>
      <td><span class="blog-feature-tag bft-mql">🟡 Text-to-MQL</span><br><small>NL → MQL via MongoDB MCP Server</small></td>
      <td class="check">✅ MCP find / aggregate / schema tools</td>
      <td class="dash">—</td>
      <td class="dash">—</td>
      <td class="check">✅ NL compliance rule queries</td>
    </tr>
    <tr>
      <td><span class="blog-feature-tag bft-ckpt">🟣 MongoDB Checkpointer</span><br><small>Persistent LangGraph agent state</small></td>
      <td class="check">✅ Multi-turn session + semantic memory store</td>
      <td class="check">✅ Autonomous investigation audit trail</td>
      <td class="check">✅ Chat history persistence</td>
      <td class="check">✅ Regulatory case history</td>
    </tr>
    <tr>
      <td><span class="blog-feature-tag bft-smith">🔴 LangSmith Observability</span><br><small>End-to-end agent traces</small></td>
      <td class="check">✅ MCP tool + retrieval traces</td>
      <td class="check">✅ Autonomous pipeline traces</td>
      <td class="check">✅ Offer tool traces</td>
      <td class="check">✅ Compliance step traces</td>
    </tr>
  </tbody>
</table>
""", unsafe_allow_html=True)

st.markdown("---")

# ── Use Case Cards ─────────────────────────────────────────────────────────────
st.markdown("### 🚀 Use Cases — Navigate via Sidebar Pages")

cases = [
    {
        "icon": "🔍", "num": "1",
        "title": "Semantic Metadata Layer",
        "desc": "Business analysts and data scientists discover and query VaultIQ's enterprise data catalog using plain English. The agent finds relevant datasets, inspects schemas, generates MQL, and executes queries — no SQL or MQL knowledge needed.",
        "memory": "Semantic + Episodic",
        "type": "💬 Chat Interface",
        "techs": ["Vector Search", "Hybrid Search", "Text-to-MQL", "Graph Lookup", "Geospatial"],
        "color": "#006FCF",
    },
    {
        "icon": "🚨", "num": "2",
        "title": "Fraud Intelligence Agent",
        "desc": "Autonomous agent that scans real-time transaction streams, detects impossible-travel patterns, traces merchant fraud rings via graph traversal, then autonomously blocks cards, files SARs, and notifies cardholders.",
        "memory": "Episodic + Procedural + Working",
        "type": "🤖 Autonomous Agent",
        "techs": ["Time-Series", "Geospatial", "Graph Lookup", "FastMCP Tools", "Vector Search"],
        "color": "#e74c3c",
    },
    {
        "icon": "🎁", "num": "3",
        "title": "Personalised Offers Concierge",
        "desc": "Cardholder-facing chat agent that recommends hyper-relevant NFG offers using MongoDB Atlas $rankFusion hybrid search, finds nearby preferred partner merchants via geospatial queries, and provides spending analytics with Nexus Rewards estimates.",
        "memory": "Episodic + Semantic",
        "type": "💬 Chat Interface",
        "techs": ["Hybrid Search", "Vector Search", "Geospatial", "Time-Series Aggregation"],
        "color": "#27ae60",
    },
    {
        "icon": "⚖️", "num": "4",
        "title": "AML & Compliance Intelligence",
        "desc": "Autonomous regulatory agent operating across BSA, FATCA, OFAC, GDPR, and PSD2. Analyses unstructured case notes for AML triggers, performs network graph analysis for layering detection, and autonomously files SARs with FinCEN.",
        "memory": "Semantic + Procedural + Episodic",
        "type": "🤖 Autonomous Agent",
        "techs": ["Vector Search", "Graph Lookup", "Unstructured Text", "FastMCP Tools", "Text-to-MQL"],
        "color": "#8e44ad",
    },
]

for case in cases:
    with st.container():
        st.markdown(f"""
<div class="use-case-card" style="border-top: 4px solid {case['color']};">
  <h3>{case['icon']} Use Case {case['num']}: {case['title']}</h3>
  <p>{case['desc']}</p>
  <div style="margin-top:0.6rem;">
    <strong style="color:{case['color']};">Interface:</strong> {case['type']} &nbsp;|&nbsp;
    <strong style="color:{case['color']};">Memory:</strong> {case['memory']}
  </div>
  <div style="margin-top:0.5rem;">
    {''.join(f'<span class="tech-pill">{t}</span>' for t in case['techs'])}
  </div>
</div>
""", unsafe_allow_html=True)

# ── Architecture Diagram Caption ───────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🏗️ Architecture")

arch_cols = st.columns([1, 2, 1])
with arch_cols[1]:
    st.markdown("""
```
┌─────────────────────────────────────────────────────────┐
│               Streamlit UI (VaultIQ Branding)             │
│   Chat Pages        │      Autonomous Agent Pages        │
├─────────────────────┴──────────────────────────────────┤
│              LangGraph Agent Orchestration               │
│  ┌──────────────────┐    ┌──────────────────────────┐  │
│  │   Agent  Node    │◄──►│    Tool  Node            │  │
│  │  Azure GPT-4o    │    │  MongoDB + MCP Tools     │  │
│  └──────────────────┘    └──────────────────────────┘  │
├────────────────────────────────────────────────────────┤
│                  MongoDB Atlas                          │
│  Vector│Hybrid│Graph│Geo│TimeSeries│Checkpointer       │
│  Voyage AI Embeddings (voyage-finance-2, 1024-dim)     │
├────────────────────────────────────────────────────────┤
│   FastMCP Server  │  LangSmith Observability           │
│   (Mock External  │  (Traces · Evals · Deployments)   │
│    API Tools)     │                                    │
└────────────────────────────────────────────────────────┘
```
""")

st.markdown("---")
st.caption(
    "This demo uses synthetic data only. No real cardholder PII. "
    "Built for Nexus Financial Group · VaultIQ Platform · LangChain × MongoDB showcase purposes."
)
