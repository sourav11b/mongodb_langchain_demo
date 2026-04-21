"""
Page 9: MongoDB Agent Skills

Displays the official MongoDB Agent Skills from github.com/mongodb/agent-skills.
These are prompt-engineering skills (SKILL.md files) that teach coding agents
(Claude, Cursor, Gemini, Copilot) how to work with MongoDB effectively.
"""

import streamlit as st
import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger("vaultiq.page.agent_skills")
st.set_page_config(page_title="Agent Skills | VaultIQ", page_icon="🤖", layout="wide")

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stSidebar"] { background: linear-gradient(180deg,#003087 0%,#006FCF 100%); }
  [data-testid="stSidebar"] > div > div > div > * { color: white !important; }
  [data-testid="stSidebar"] label,[data-testid="stSidebar"] p,
  [data-testid="stSidebar"] span,[data-testid="stSidebar"] h1,
  [data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3,
  [data-testid="stSidebar"] h4,[data-testid="stSidebar"] li,
  [data-testid="stSidebar"] a,
  [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
  [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] * { color: white !important; }
  [data-testid="stSidebarNav"] a,[data-testid="stSidebarNav"] span { color: white !important; }
  [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.2); }
  .page-header { background:linear-gradient(135deg,#1a1a2e,#16213e);
    padding:1.5rem 2rem; border-radius:10px; margin-bottom:1rem; }
  .page-header h2 { color:white; margin:0; }
  .page-header p  { color:rgba(255,255,255,.88); margin:.3rem 0 0; }
  .feat-tag { display:inline-block; padding:.18rem .65rem; border-radius:20px;
    font-size:.73rem; font-weight:700; margin:.15rem; border:1.5px solid; }
  .ft-green  { background:#d1fae5; color:#065f46; border-color:#6ee7b7; }
  .ft-blue   { background:#dbeafe; color:#1d4ed8; border-color:#93c5fd; }
  .ft-purple { background:#ede9fe; color:#5b21b6; border-color:#c4b5fd; }
  .ft-yellow { background:#fef3c7; color:#92400e; border-color:#fcd34d; }
  .ft-red    { background:#fee2e2; color:#991b1b; border-color:#fca5a5; }
  .skill-card { background:#f8fafc; border:2px solid #e2e8f0; border-radius:12px;
    padding:1.2rem; margin:.5rem 0; transition: border-color 0.2s; }
  .skill-card:hover { border-color:#006FCF; }
  .skill-card h4 { margin:0 0 .4rem; color:#1e293b; }
  .skill-card p  { margin:0; font-size:.85rem; color:#555; }
  .install-box { background:#1e293b; color:#e2e8f0; padding:.8rem 1rem;
    border-radius:8px; font-family:monospace; font-size:.82rem; margin:.5rem 0; }
  .agent-badge { display:inline-block; padding:.2rem .6rem; border-radius:6px;
    font-size:.72rem; font-weight:700; margin:.1rem; }
  .ab-claude  { background:#d4a574; color:#2d1810; }
  .ab-cursor  { background:#00d4aa; color:#003322; }
  .ab-gemini  { background:#8ab4f8; color:#1a237e; }
  .ab-copilot { background:#6e40c9; color:white; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
  <h2>🤖 MongoDB Agent Skills</h2>
  <p>Official MongoDB skills for coding agents — teach Claude, Cursor, Gemini, and Copilot
     how to work with MongoDB effectively</p>
  <p style="margin-top:.6rem">
    <span class="agent-badge ab-claude">Claude</span>
    <span class="agent-badge ab-cursor">Cursor</span>
    <span class="agent-badge ab-gemini">Gemini CLI</span>
    <span class="agent-badge ab-copilot">Copilot CLI</span>
    <span class="feat-tag ft-green">🍃 Official MongoDB</span>
    <span class="feat-tag ft-blue">🔧 MCP Server</span>
  </p>
</div>
""", unsafe_allow_html=True)


GITHUB_RAW_BASE = "https://raw.githubusercontent.com/mongodb/agent-skills/main/skills"

@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_skill(skill_id: str) -> None:
    """Fetch and display the SKILL.md content from GitHub."""
    import requests
    url = f"{GITHUB_RAW_BASE}/{skill_id}/SKILL.md"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            st.markdown(resp.text[:8000])
            if len(resp.text) > 8000:
                st.caption(f"…truncated ({len(resp.text):,} chars total). [View full on GitHub](https://github.com/mongodb/agent-skills/blob/main/skills/{skill_id}/SKILL.md)")
        else:
            st.warning(f"Could not fetch SKILL.md (HTTP {resp.status_code}). [View on GitHub](https://github.com/mongodb/agent-skills/tree/main/skills/{skill_id})")
    except Exception as e:
        st.warning(f"Fetch error: {e}. [View on GitHub](https://github.com/mongodb/agent-skills/tree/main/skills/{skill_id})")

# ── Overview ──────────────────────────────────────────────────────────────────
col_intro, col_install = st.columns([3, 2])

with col_intro:
    st.markdown("""
**What are MongoDB Agent Skills?**

[MongoDB Agent Skills](https://github.com/mongodb/agent-skills) are a collection of
**prompt-engineering knowledge files** (`SKILL.md`) that teach coding agents how to work
with MongoDB. They're not code libraries — they're **context files** that get loaded into
the agent's context window, giving it deep expertise on MongoDB patterns and best practices.

Each skill contains:
- **Best practices** and anti-patterns
- **Code examples** with correct syntax
- **Reference documentation** for MongoDB features
- **Decision frameworks** for schema design, query optimization, etc.

When installed, your coding agent automatically applies this knowledge when working
with MongoDB code — writing better queries, designing better schemas, and following
official patterns.
""")

with col_install:
    st.markdown("**⚡ Quick Install:**")
    st.markdown("""
<div class="install-box">
<strong>Vercel Skills CLI:</strong><br>
npx skills add mongodb/agent-skills<br><br>
<strong>MCP Server (required):</strong><br>
npx mongodb-mcp-server@1 setup<br><br>
<strong>Manual:</strong><br>
Clone the repo and copy SKILL.md files<br>
into your project's context directory.
</div>
""", unsafe_allow_html=True)
    st.markdown("""
**Compatible with:**
<span class="agent-badge ab-claude">Claude Code</span>
<span class="agent-badge ab-cursor">Cursor</span>
<span class="agent-badge ab-gemini">Gemini CLI</span>
<span class="agent-badge ab-copilot">GitHub Copilot</span>
""", unsafe_allow_html=True)

# ── Skills Catalog ────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 📚 Skills Catalog")
st.markdown("7 official skills from [`mongodb/agent-skills`](https://github.com/mongodb/agent-skills) — each teaches your coding agent a different MongoDB capability.")

SKILLS = [
    {
        "id": "mongodb-search-and-ai",
        "icon": "🔍",
        "title": "Search & AI",
        "desc": "Atlas Vector Search ($vectorSearch), full-text search ($search), hybrid search with $rankFusion, embedding strategies, and RAG pipeline patterns.",
        "tag_cls": "ft-purple", "tag_label": "AI/Search",
        "vaultiq": "Core skill behind Pages 1, 3, 7, 8 — vector search, hybrid search, GraphRAG.",
    },
    {
        "id": "mongodb-natural-language-querying",
        "icon": "💬",
        "title": "Natural Language Querying",
        "desc": "Teaches agents to translate natural language into MQL — find(), aggregate(), $match, $group, $lookup, $unwind, and complex pipeline construction.",
        "tag_cls": "ft-yellow", "tag_label": "Text-to-MQL",
        "vaultiq": "Used by the Database Agent (Page 6) and Data Discovery agent (Page 1).",
    },
    {
        "id": "mongodb-schema-design",
        "icon": "🏗️",
        "title": "Schema Design",
        "desc": "Document modeling best practices — embedding vs referencing, polymorphic patterns, schema versioning, Subset / Computed / Bucket patterns.",
        "tag_cls": "ft-green", "tag_label": "Schema",
        "vaultiq": "Our cardholders, merchants, fraud_cases collections follow embedded document pattern.",
    },
    {
        "id": "mongodb-query-optimizer",
        "icon": "⚡",
        "title": "Query Optimizer",
        "desc": "Index selection, explain() analysis, covered queries, compound index ordering, partial indexes, aggregation pipeline optimization.",
        "tag_cls": "ft-blue", "tag_label": "Performance",
        "vaultiq": "Guides index creation for vector search, FTS, and compound indexes.",
    },
    {
        "id": "mongodb-mcp-setup",
        "icon": "🔧",
        "title": "MCP Server Setup",
        "desc": "Installing and configuring the MongoDB MCP Server — authentication, connection options, tool discovery, agent integration.",
        "tag_cls": "ft-blue", "tag_label": "MCP",
        "vaultiq": "Data Discovery agent (Page 1) uses MCP Server in embedded mode with 12+ tools.",
    },
    {
        "id": "mongodb-connection",
        "icon": "🔌",
        "title": "Connection Management",
        "desc": "Connection string formats, pooling, retry logic, read/write concerns, replica set config, Atlas connection best practices.",
        "tag_cls": "ft-green", "tag_label": "Infrastructure",
        "vaultiq": "config.py uses the recommended Atlas connection string with retryWrites and w=majority.",
    },
    {
        "id": "atlas-stream-processing",
        "icon": "🌊",
        "title": "Atlas Stream Processing",
        "desc": "Real-time stream processing — window functions, aggregation on streams, triggers, change streams integration.",
        "tag_cls": "ft-red", "tag_label": "Streaming",
        "vaultiq": "Could extend Fraud Agent (Page 2) with real-time transaction stream processing.",
    },
]

# Render skill cards in 2 columns
for i in range(0, len(SKILLS), 2):
    cols = st.columns(2)
    for j, col in enumerate(cols):
        idx = i + j
        if idx >= len(SKILLS):
            break
        s = SKILLS[idx]
        with col:
            st.markdown(f"""
<div class="skill-card">
  <h4>{s['icon']} {s['title']} <span class="feat-tag {s['tag_cls']}">{s['tag_label']}</span></h4>
  <p>{s['desc']}</p>
  <p style="margin-top:.5rem; font-size:.78rem; color:#006FCF;"><strong>Used in VaultIQ:</strong> {s['vaultiq']}</p>
</div>
""", unsafe_allow_html=True)
            with st.expander(f"📄 View SKILL.md for {s['title']}"):
                _fetch_skill(s["id"])

# ── How VaultIQ Uses These Skills ─────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🏦 How VaultIQ Applies These Skills")
st.markdown("""
| Skill | VaultIQ Page | How It's Applied |
|-------|-------------|-----------------|
| 🔍 Search & AI | P1 Data Discovery, P3 Offers, P7 Knowledge Graph, P8 Showcase | `$vectorSearch` with Voyage AI embeddings, `$rankFusion` hybrid search, GraphRAG |
| 💬 NL Querying | P1 Data Discovery, P6 Database Agent | MongoDBDatabaseToolkit generates MQL from natural language via MCP Server |
| 🏗️ Schema Design | All pages | Embedded document pattern, denormalized reads, flexible schema for different card tiers |
| ⚡ Query Optimizer | P2 Fraud, P4 Compliance | Compound indexes on fraud_score + timestamp, covered queries for compliance lookups |
| 🔧 MCP Setup | P1 Data Discovery, P5 Setup | MCP Server in embedded mode (`npx mongodb-mcp-server`), 12+ auto-discovered tools |
| 🔌 Connection | All pages | Atlas connection string with retryWrites, connection pooling in config.py |
| 🌊 Stream Processing | Future | Could extend P2 Fraud with real-time transaction stream processing |
""")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
**📖 Resources:**
- [mongodb/agent-skills on GitHub](https://github.com/mongodb/agent-skills)
- [MongoDB MCP Server](https://www.npmjs.com/package/mongodb-mcp-server)
- [Agent Skills Documentation](https://github.com/mongodb/agent-skills#readme)
""")
st.caption("Skills are maintained by MongoDB · Content fetched live from GitHub")