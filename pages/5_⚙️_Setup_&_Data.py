"""
Page 5: Setup & Data — Seed MongoDB, embed vectors, view data stats
"""

import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

st.set_page_config(page_title="Setup & Data | VaultIQ", page_icon="⚙️", layout="wide")

st.markdown("""
<style>
  [data-testid="stSidebar"] { background: linear-gradient(180deg,#003087 0%,#006FCF 100%); }
  [data-testid="stSidebar"] > div > div > div > * { color: white !important; }
  [data-testid="stSidebar"] [data-testid="stExpander"] details { background:rgba(255,255,255,.95); border-radius:8px; }
  [data-testid="stSidebar"] [data-testid="stExpander"] summary span,
  [data-testid="stSidebar"] [data-testid="stExpander"] summary svg { color:#001E2B !important; }
  [data-testid="stSidebar"] [data-testid="stExpander"] p,
  [data-testid="stSidebar"] [data-testid="stExpander"] span:not(summary span),
  [data-testid="stSidebar"] [data-testid="stExpander"] code,
  [data-testid="stSidebar"] [data-testid="stExpander"] small { color:#1a1a2e !important; }
  [data-testid="stSidebar"] [data-testid="stExpander"] code { background:#e8ecf1; padding:1px 5px; border-radius:3px; }
  [data-testid="stSidebar"] [data-baseweb="select"] * { color:#1a1a2e !important; }
  [data-testid="stSidebar"] [data-testid="stTextInput"] input { color:#1a1a2e !important; }
  [data-testid="stSidebar"] .stAlert p, [data-testid="stSidebar"] .stAlert span { color:#1a1a2e !important; }
  .page-header { background: linear-gradient(135deg,#2c3e50,#34495e); padding:1.5rem 2rem;
    border-radius:10px; margin-bottom:1.2rem; }
  .page-header h2 { color:white; margin:0; }
  .page-header p  { color:rgba(255,255,255,.88); margin:.3rem 0 0; }
  .stat-card { background:white; border:1px solid #e0e8f5; border-radius:10px;
    padding:1rem 1.2rem; text-align:center; }
  .stat-card .num { font-size:2rem; font-weight:700; color:#006FCF; }
  .stat-card .label { font-size:.85rem; color:#666; }
  .code-box { background:#1e2127; border-radius:8px; padding:1rem 1.2rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
  <h2>⚙️ Setup & Data Management</h2>
  <p>Seed MongoDB with synthetic NFG data, generate Voyage AI embeddings, and verify your environment</p>
</div>
""", unsafe_allow_html=True)

from config import MONGODB_URI, MONGODB_DB_NAME, MCP_SERVER_URL

# ── Database Stats ─────────────────────────────────────────────────────────────
st.markdown("### 📊 MongoDB Collection Stats")

try:
    from pymongo import MongoClient
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[MONGODB_DB_NAME]

    COLL_INFO = {
        "transactions":      ("📈 Time-Series + Geo",  "#006FCF"),
        "cardholders":       ("👤 Profiles + Geo",     "#2471A3"),
        "merchants":         ("🏪 Geo + Vector",        "#27ae60"),
        "offers":            ("🎁 Vector Search",       "#B5A06A"),
        "data_catalog":      ("📋 Metadata + Vector",   "#8e44ad"),
        "fraud_cases":       ("🚨 Unstructured + Struct","#e74c3c"),
        "compliance_rules":  ("⚖️ Regulatory + Vector", "#4a235a"),
        "merchant_networks": ("🕸️ Graph Edges",         "#1a7340"),
    }

    cols = st.columns(4)
    for i, (cname, (dtype, color)) in enumerate(COLL_INFO.items()):
        count = db[cname].count_documents({})
        embedded = db[cname].count_documents({"embedding": {"$exists": True, "$ne": []}}) if cname in [
            "offers","data_catalog","compliance_rules","merchants","cardholders","fraud_cases"
        ] else "-"
        with cols[i % 4]:
            st.markdown(f"""
<div class="stat-card" style="border-top:3px solid {color};">
  <div class="num">{count:,}</div>
  <div class="label"><strong>{cname}</strong><br>{dtype}</div>
  <div style="font-size:.75rem;color:#999;margin-top:.3rem;">
    Embedded: {embedded if isinstance(embedded,str) else f"{embedded:,}"}
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Atlas Status Panel ──────────────────────────────────────────────────────
    st.markdown("#### 🔍 Atlas Cluster Status")
    col_atlas1, col_atlas2, col_atlas3 = st.columns(3)
    with col_atlas1:
        # Server info
        try:
            server_info = client.server_info()
            st.markdown(f"""
<div class="stat-card" style="border-top:3px solid #27ae60;">
  <div class="num" style="font-size:1.2rem;">✅ Connected</div>
  <div class="label">MongoDB v{server_info.get('version', '?')}</div>
</div>""", unsafe_allow_html=True)
        except Exception:
            st.markdown('<div class="stat-card" style="border-top:3px solid #e74c3c;"><div class="num" style="color:#e74c3c;">❌ Error</div></div>', unsafe_allow_html=True)
    with col_atlas2:
        total_docs = sum(db[c].count_documents({}) for c in COLL_INFO)
        st.markdown(f"""
<div class="stat-card" style="border-top:3px solid #006FCF;">
  <div class="num">{total_docs:,}</div>
  <div class="label">Total Documents</div>
</div>""", unsafe_allow_html=True)
    with col_atlas3:
        total_indexes = 0
        for c in COLL_INFO:
            try:
                total_indexes += len(list(db[c].list_search_indexes()))
            except Exception:
                pass
        st.markdown(f"""
<div class="stat-card" style="border-top:3px solid #8e44ad;">
  <div class="num">{total_indexes}</div>
  <div class="label">Search Indexes (Vector + FTS)</div>
</div>""", unsafe_allow_html=True)

    client.close()
    st.success("✅ MongoDB connection successful")
except Exception as e:
    st.error(f"❌ MongoDB connection failed: {e}")
    st.info("Check MONGODB_URI in your .env file")

st.markdown("---")

# ── Seed Controls ──────────────────────────────────────────────────────────────
st.markdown("### 🌱 Data Seeding")

col_seed, col_embed = st.columns(2)
with col_seed:
    st.markdown("**Step 1: Seed MongoDB with synthetic NFG data**")
    st.markdown("""
Creates 8 collections:
- 60 cardholders (geo + profiles)
- 80 merchants (geo + descriptions)
- 500 transactions (time-series + geo + fraud scores)
- 60 offers (for vector search)
- 7 data catalog entries
- 40 fraud cases (unstructured notes)
- 10 compliance rules
- 80 merchant network nodes (graph edges)
""")
    if st.button("🌱 Seed MongoDB Data", use_container_width=True):
        with st.spinner("Seeding... (this takes 30-60 seconds)"):
            try:
                import subprocess
                result = subprocess.run(
                    [sys.executable, "-m", "data.seed_data"],
                    capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__))
                )
                if result.returncode == 0:
                    st.success("✅ Data seeded successfully!")
                    st.code(result.stdout, language="text")
                else:
                    st.error("Seeding failed")
                    st.code(result.stderr, language="text")
            except Exception as e:
                st.error(f"Error: {e}")

with col_embed:
    st.markdown("**Step 2: Generate Voyage AI Embeddings**")
    st.markdown("""
Embeds 6 collections using `voyage-finance-2` (1024-dim):
- `offers` — offer descriptions
- `data_catalog` — dataset descriptions
- `compliance_rules` — regulatory text
- `merchants` — merchant descriptions
- `cardholders` — profile summaries
- `fraud_cases` — investigation notes

Requires `VOYAGE_API_KEY` in .env
""")
    if st.button("🚀 Generate Embeddings (Voyage AI)", use_container_width=True):
        with st.spinner("Generating embeddings... (may take 1-2 min)"):
            try:
                import subprocess
                result = subprocess.run(
                    [sys.executable, "-m", "embeddings.voyage_client"],
                    capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__))
                )
                if result.returncode == 0:
                    st.success("✅ Embeddings generated!")
                    st.code(result.stdout, language="text")
                else:
                    st.error("Embedding failed")
                    st.code(result.stderr, language="text")
            except Exception as e:
                st.error(f"Error: {e}")

st.markdown("---")

# ── Drop & Reload ─────────────────────────────────────────────────────────────
st.markdown("### 🔄 Drop & Reload All Data")
st.markdown("""
**⚠️ Destructive operation** — drops all collections, then re-seeds data and regenerates embeddings + indexes.
Use this when you need a clean slate or after code changes to seed data.
""")

col_drop, col_reload = st.columns(2)
with col_drop:
    confirm_drop = st.checkbox("I understand this will delete ALL data", key="confirm_drop")
    if st.button("🗑️ Drop All Collections", type="secondary", use_container_width=True, disabled=not confirm_drop):
        with st.spinner("Dropping all collections…"):
            try:
                from pymongo import MongoClient
                client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
                db = client[MONGODB_DB_NAME]
                dropped = []
                for cname in list(COLL_INFO.keys()) + ["knowledge_graph", "langchain_chat_history",
                    "langchain_cache", "langchain_semantic_cache", "langchain_graph_demo",
                    "langchain_record_manager"]:
                    try:
                        db.drop_collection(cname)
                        dropped.append(cname)
                    except Exception:
                        pass
                client.close()
                st.success(f"✅ Dropped {len(dropped)} collections: {', '.join(dropped)}")
                st.rerun()
            except Exception as e:
                st.error(f"Drop failed: {e}")

with col_reload:
    if st.button("🔄 Full Reload (Seed + Embed + Indexes)", type="primary", use_container_width=True):
        with st.spinner("Step 1/2: Seeding data…"):
            try:
                import subprocess
                result = subprocess.run(
                    [sys.executable, "-m", "data.seed_data"],
                    capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__))
                )
                if result.returncode != 0:
                    st.error("Seeding failed")
                    st.code(result.stderr, language="text")
                    st.stop()
                st.code(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout, language="text")
            except Exception as e:
                st.error(f"Seed error: {e}")
                st.stop()

        with st.spinner("Step 2/2: Generating embeddings…"):
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "embeddings.voyage_client"],
                    capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__))
                )
                if result.returncode != 0:
                    st.error("Embedding failed")
                    st.code(result.stderr, language="text")
                    st.stop()
                st.code(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout, language="text")
            except Exception as e:
                st.error(f"Embed error: {e}")
                st.stop()

        st.success("✅ Full reload complete! Data seeded, embeddings generated, indexes created.")
        st.rerun()

st.markdown("---")

# ── MongoDB MCP Server (official) ─────────────────────────────────────────────
st.markdown("### 🍃 MongoDB MCP Server (Official)")
st.markdown("""
The **official `@mongodb-js/mongodb-mcp-server`** exposes MongoDB operations as MCP tools
that the Data Discovery agent uses directly — no hand-coded query logic needed.
""")

from config import MONGODB_MCP_SERVER_URL, MONGODB_URI

col_mmcp1, col_mmcp2 = st.columns(2)
with col_mmcp1:
    st.markdown("**MCP Tools exposed (read-only mode):**")
    mongodb_mcp_tools = [
        ("find",                   "Run a find query — replaces hand-coded execute_mql_query"),
        ("aggregate",              "Run any aggregation pipeline"),
        ("collection-schema",      "Describe fields & types — replaces inspect_collection_schema"),
        ("collection-indexes",     "List all indexes on a collection"),
        ("collection-storage-size","Storage bytes for a collection"),
        ("count",                  "Count documents with optional filter"),
        ("db-stats",               "Database-level statistics"),
        ("explain",                "Execution plan for find / aggregate"),
        ("list-collections",       "List all collections in the database"),
        ("list-databases",         "List all databases on the connection"),
        ("search-knowledge",       "Search MongoDB official documentation"),
        ("list-knowledge-sources", "List MongoDB documentation sources"),
    ]
    for name, desc in mongodb_mcp_tools:
        st.markdown(f"  • 🍃 **`{name}`** — {desc}")

with col_mmcp2:
    from config import MONGODB_MCP_TRANSPORT
    from tools.mongodb_mcp_client import active_transport
    import httpx

    mode = active_transport()
    st.markdown(f"**Active transport:** `{mode}` *(set `MONGODB_MCP_TRANSPORT` in `.env` to switch)*")

    if mode == "embedded":
        st.success("🟢 **embedded** — mongodb-mcp-server auto-spawned as npx subprocess. No separate server needed.")
        st.code(
            "# .env (current — embedded/stdio, default)\n"
            "MONGODB_MCP_TRANSPORT=embedded\n\n"
            "# Switch to HTTP:\n"
            "# MONGODB_MCP_TRANSPORT=http",
            language="bash",
        )
    else:
        st.markdown(f"**Server URL:** `{MONGODB_MCP_SERVER_URL}`")
        st.markdown("Run in a **separate terminal** (requires Node.js / npx):")
        st.code(
            f"MDB_MCP_CONNECTION_STRING=\"{MONGODB_URI[:55]}\" \\\n"
            f"npx -y mongodb-mcp-server@latest \\\n"
            f"  --transport http --httpPort 3001 \\\n"
            f"  --readOnly --disabledTools atlas --telemetry disabled",
            language="bash",
        )
        st.code(
            "# .env (current — http mode)\n"
            "MONGODB_MCP_TRANSPORT=http\n"
            "MONGODB_MCP_HOST=localhost\n"
            "MONGODB_MCP_PORT=3001\n\n"
            "# Switch back to embedded:\n"
            "# MONGODB_MCP_TRANSPORT=embedded",
            language="bash",
        )
        if st.button("🔌 Ping MongoDB MCP Server", key="ping_mongodb_mcp"):
            try:
                httpx.get(f"{MONGODB_MCP_SERVER_URL}/", timeout=3)
                st.success(f"✅ MongoDB MCP Server RUNNING at {MONGODB_MCP_SERVER_URL}")
            except Exception as e:
                st.warning(f"⚠️ Not running at {MONGODB_MCP_SERVER_URL}: {e}")

    if st.button("🔎 Load & Display MCP Tools", key="load_mcp_tools"):
        with st.spinner(f"Connecting via {mode} transport…"):
            try:
                from tools.mongodb_mcp_client import load_mongodb_mcp_tools_sync
                tools_info = load_mongodb_mcp_tools_sync()
                if tools_info:
                    st.success(f"✅ Loaded {len(tools_info)} tools via **{mode}** transport:")
                    for t in tools_info:
                        st.markdown(f"  🍃 **`{t['name']}`** — {t['description'][:80]}")
                else:
                    st.warning("No tools loaded. Check Node.js is on PATH (embedded) or server is running (http).")
            except Exception as e:
                st.error(f"Error: {e}")

st.markdown("---")

# ── Custom FastMCP Server ──────────────────────────────────────────────────────
st.markdown("### ⚡ Custom FastMCP Tool Server (NFG Mock APIs)")

col_mcp1, col_mcp2 = st.columns(2)
with col_mcp1:
    st.markdown(f"**Server URL:** `{MCP_SERVER_URL}`")
    st.markdown("**Available Tools (mock external NFG APIs):**")
    nexus_mcp_tools = [
        ("screen_sanctions", "OFAC SDN + global sanctions screening"),
        ("credit_bureau_lookup", "Experian/Equifax/TransUnion credit profile"),
        ("block_card", "Temporary hold or permanent card block"),
        ("send_notification", "Push / SMS / email to cardholder"),
        ("file_sar", "FinCEN Suspicious Activity Report filing"),
        ("merchant_risk_check", "Chargeback ratio + fraud ring + ownership"),
        ("geo_velocity_check", "Impossible travel detection"),
    ]
    for name, desc in nexus_mcp_tools:
        st.markdown(f"  • **`{name}`** — {desc}")

with col_mcp2:
    st.markdown("**Step 4: Start the Custom NFG FastMCP Server**")
    st.code("python -m tools.mcp_server", language="bash")
    if st.button("🔌 Ping VaultIQ MCP Server", key="ping_nexus_mcp"):
        try:
            resp = httpx.get(f"{MCP_SERVER_URL}/", timeout=3)
            st.success(f"✅ VaultIQ MCP Server reachable (status {resp.status_code})")
        except Exception as e:
            st.warning(f"⚠️ Not running: {e}")
            st.info("Fraud & Compliance agents use simulated HTTP fallback responses when this server is offline.")

st.markdown("---")
st.markdown("### 📝 Complete Quick Start")
st.code("""
# 1. Copy and configure environment
cp .env.example .env
# Edit .env — set MONGODB_URI, AZURE_OPENAI_*, VOYAGE_API_KEY

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Seed MongoDB with synthetic NFG data
python -m data.seed_data

# 4. Generate Voyage AI embeddings
python -m embeddings.voyage_client

# ── Terminal A: MongoDB MCP Server (official, for Data Discovery agent) ──
MDB_MCP_CONNECTION_STRING="<your-uri>" \\
npx -y mongodb-mcp-server@latest \\
  --transport http --httpPort 3001 \\
  --readOnly --disabledTools atlas --telemetry disabled

# ── Terminal B: Custom NFG FastMCP Server (Fraud & Compliance agents) ──
python -m tools.mcp_server

# ── Terminal C: Streamlit app ──
streamlit run app.py
""", language="bash")
