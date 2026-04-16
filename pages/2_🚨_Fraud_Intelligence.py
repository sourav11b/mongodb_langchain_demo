"""
Page 2: Fraud Intelligence — Autonomous Multi-Step Fraud Detection Agent
"""

import streamlit as st
import sys, os, logging
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger("vaultiq.page.fraud")

st.set_page_config(page_title="Fraud Intelligence | VaultIQ", page_icon="🚨", layout="wide")

st.markdown("""
<style>
  [data-testid="stSidebar"] { background: linear-gradient(180deg,#003087 0%,#006FCF 100%); }
  [data-testid="stSidebar"] > div > div > div > * { color: white !important; }
  [data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] span, [data-testid="stSidebar"] h1,
  [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
  [data-testid="stSidebar"] h4, [data-testid="stSidebar"] li,
  [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
  [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] * { color: white !important; }
  [data-testid="stSidebar"] [data-testid="stRadio"] label span { color: white !important; }
  /* Fix contrast inside sidebar expanders — dark text on white panel */
  [data-testid="stSidebar"] [data-testid="stExpander"] details {
    background: rgba(255,255,255,0.95); border-radius: 8px;
  }
  [data-testid="stSidebar"] [data-testid="stExpander"] summary span,
  [data-testid="stSidebar"] [data-testid="stExpander"] summary svg { color: #003087 !important; }
  [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stMarkdownContainer"],
  [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stMarkdownContainer"] *,
  [data-testid="stSidebar"] [data-testid="stExpander"] p,
  [data-testid="stSidebar"] [data-testid="stExpander"] code,
  [data-testid="stSidebar"] [data-testid="stExpander"] small { color: #1a1a2e !important; }
  [data-testid="stSidebar"] [data-testid="stExpander"] code {
    background: #e8ecf1; padding: 1px 5px; border-radius: 3px; font-size: .82rem;
  }
  .page-header { background: linear-gradient(135deg,#8B0000,#c0392b); padding:1.5rem 2rem;
    border-radius:10px; margin-bottom:1.2rem; }
  .page-header h2 { color:white; margin:0; } .page-header p { color:rgba(255,255,255,.88); margin:.3rem 0 0; }
  .tool-badge { background:#FFF0F0; color:#c0392b; border-radius:6px; padding:2px 10px;
    font-size:.8rem; font-weight:600; display:inline-block; margin:2px; }
  .memory-box { background:#FFF8E7; border-left:4px solid #B5A06A; padding:.8rem 1rem; border-radius:6px; font-size:.88rem; }
  .answer-box { background:#FFF5F5; border:1px solid #F5C6CB; border-radius:10px; padding:1.2rem 1.5rem; }
  .step-box { background:#F8F9FA; border:1px solid #DEE2E6; border-radius:8px; padding:1rem; margin:.5rem 0; }
  .alert-red { background:#FFE4E1; border-left:4px solid #e74c3c; padding:.8rem 1rem; border-radius:6px; }
  .blog-feature-tag {
    display:inline-block; padding:.18rem .65rem; border-radius:20px;
    font-size:.73rem; font-weight:700; margin:.15rem; border:1.5px solid;
  }
  .bft-vector { background:#dbeafe; color:#1d4ed8; border-color:#93c5fd; }
  .bft-hybrid { background:#d1fae5; color:#065f46; border-color:#6ee7b7; }
  .bft-mql    { background:#fef3c7; color:#92400e; border-color:#fcd34d; }
  .bft-ckpt   { background:#ede9fe; color:#5b21b6; border-color:#c4b5fd; }
  .bft-smith  { background:#fee2e2; color:#991b1b; border-color:#fca5a5; }
  .blog-note  { background:#f8faff; border:1px solid #c8d8f0; border-left:4px solid #c0392b;
    border-radius:6px; padding:.55rem .9rem; font-size:.82rem; color:#334; margin:.4rem 0; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
  <h2>🚨 Use Case 2: Fraud Intelligence Agent</h2>
  <p>Autonomous multi-step fraud detection, investigation, and remediation — zero human intervention required</p>
  <p style="margin-top:.6rem;">
    <span class="blog-feature-tag bft-vector">🔵 Atlas Vector Search</span>
    <span class="blog-feature-tag bft-ckpt">🟣 MongoDB Checkpointer</span>
    <span class="blog-feature-tag bft-smith">🔴 LangSmith Observability</span>
    &nbsp;<a href="https://blog.langchain.com/announcing-the-langchain-mongodb-partnership-the-ai-agent-stack-that-runs-on-the-database-you-already-trust/" target="_blank" style="color:rgba(255,255,255,.75);font-size:.78rem;">📄 Partnership blog →</a>
  </p>
</div>
""", unsafe_allow_html=True)

# ── Fraud Scenario Injection (Sidebar) ─────────────────────────────────────────
from pymongo import MongoClient
from config import MONGODB_URI, MONGODB_DB_NAME

_inject_db = MongoClient(MONGODB_URI)[MONGODB_DB_NAME]
_INJECT_TAG = "_injected_scenario"     # tag field for cleanup

def _now(**kw):
    return datetime.now(timezone.utc) + timedelta(**kw)

FRAUD_SCENARIOS = {
    "🛒 Card-Not-Present Burst": {
        "id": "cnp_burst",
        "desc": "8 rapid online transactions across 5 countries in 20 minutes — classic CNP fraud.",
        "cardholder_id": "CH_DEMO_CNP_001",
        "cardholders": [{
            "cardholder_id": "CH_DEMO_CNP_001", "name": "Marcus Webb",
            "card_tier": "Platinum", "kyc_verified": True, "pep_flag": False,
            "home_city": "New York", "risk_score": 0.82, "annual_spend_usd": 48000,
        }],
        "transactions": lambda: [
            {"cardholder_id": "CH_DEMO_CNP_001", "amount": a, "merchant_name": m,
             "channel": "online", "ip_country": c, "fraud_score": s,
             "is_flagged": True, "status": st_, "timestamp": _now(minutes=-i*3)}
            for i, (a, m, c, s, st_) in enumerate([
                (4999, "ElectroMax Global", "Nigeria", 0.97, "declined"),
                (3200, "LuxBags24.com", "Romania", 0.94, "declined"),
                (1850, "TechVault UK", "UK", 0.91, "approved"),
                (2400, "DigiStore DE", "Germany", 0.89, "approved"),
                (5000, "QuickShip NG", "Nigeria", 0.95, "declined"),
                (780, "StreamPlus", "USA", 0.72, "approved"),
                (6100, "GoldWatch.co", "UAE", 0.98, "declined"),
                (950, "CloudApps Inc", "USA", 0.68, "approved"),
            ])
        ],
    },
    "🔐 Account Takeover (ATO)": {
        "id": "ato_attack",
        "desc": "Password reset from new device, followed by immediate high-value purchases — ATO pattern.",
        "cardholder_id": "CH_DEMO_ATO_001",
        "cardholders": [{
            "cardholder_id": "CH_DEMO_ATO_001", "name": "Sarah Chen",
            "card_tier": "Gold", "kyc_verified": True, "pep_flag": False,
            "home_city": "San Francisco", "risk_score": 0.76, "annual_spend_usd": 32000,
        }],
        "transactions": lambda: [
            {"cardholder_id": "CH_DEMO_ATO_001", "amount": a, "merchant_name": m,
             "channel": ch, "ip_country": c, "fraud_score": s,
             "is_flagged": s >= 0.70, "status": st_, "timestamp": _now(minutes=-i*5)}
            for i, (a, m, ch, c, s, st_) in enumerate([
                (9999, "Cartier Official", "in_store", "USA", 0.93, "approved"),
                (7500, "Apple Store Online", "online", "USA", 0.91, "approved"),
                (3200, "BestBuy.com", "online", "USA", 0.88, "approved"),
                (15, "Starbucks #4421", "contactless", "USA", 0.15, "approved"),
                (42, "Uber Rides", "online", "USA", 0.12, "approved"),
            ])
        ],
    },
    "🕸️ Merchant Fraud Ring": {
        "id": "merchant_ring",
        "desc": "3 connected shell merchants laundering money through circular transactions — detected via $graphLookup.",
        "cardholder_id": "CH_DEMO_RING_001",
        "cardholders": [{
            "cardholder_id": "CH_DEMO_RING_001", "name": "Viktor Petrov",
            "card_tier": "Green", "kyc_verified": False, "pep_flag": True,
            "home_city": "Miami", "risk_score": 0.91, "annual_spend_usd": 120000,
        }],
        "transactions": lambda: [
            {"cardholder_id": "CH_DEMO_RING_001", "amount": a, "merchant_name": m,
             "channel": "online", "ip_country": "USA", "fraud_score": s,
             "is_flagged": True, "status": "approved", "timestamp": _now(hours=-i)}
            for i, (a, m, s) in enumerate([
                (25000, "GlobalTrade LLC", 0.96),
                (24800, "Nexus Imports Co", 0.94),
                (24500, "Pacific Ventures", 0.93),
            ])
        ],
        "merchant_networks": [
            {"merchant_id": "M_DEMO_001", "merchant_name": "GlobalTrade LLC",
             "risk_cluster_flag": True, "cluster_id": "RING_DEMO_A",
             "edges": [{"target_merchant_id": "M_DEMO_002", "relationship": "shared_owner"}]},
            {"merchant_id": "M_DEMO_002", "merchant_name": "Nexus Imports Co",
             "risk_cluster_flag": True, "cluster_id": "RING_DEMO_A",
             "edges": [{"target_merchant_id": "M_DEMO_003", "relationship": "shared_terminal"}]},
            {"merchant_id": "M_DEMO_003", "merchant_name": "Pacific Ventures",
             "risk_cluster_flag": True, "cluster_id": "RING_DEMO_A",
             "edges": [{"target_merchant_id": "M_DEMO_001", "relationship": "circular_flow"}]},
        ],
    },
    "✈️ Impossible Travel": {
        "id": "impossible_travel",
        "desc": "In-store purchase in London, then Tokyo 45 minutes later — physically impossible.",
        "cardholder_id": "CH_DEMO_TRAVEL_001",
        "cardholders": [{
            "cardholder_id": "CH_DEMO_TRAVEL_001", "name": "James Whitfield",
            "card_tier": "Centurion", "kyc_verified": True, "pep_flag": False,
            "home_city": "London", "risk_score": 0.85, "annual_spend_usd": 250000,
        }],
        "transactions": lambda: [
            {"cardholder_id": "CH_DEMO_TRAVEL_001", "amount": 8200,
             "merchant_name": "Tokyo Ginza Dept Store", "channel": "in_store",
             "ip_country": "Japan", "fraud_score": 0.96, "is_flagged": True,
             "status": "approved", "timestamp": _now(minutes=0)},
            {"cardholder_id": "CH_DEMO_TRAVEL_001", "amount": 3400,
             "merchant_name": "Harrods London", "channel": "in_store",
             "ip_country": "UK", "fraud_score": 0.22, "is_flagged": False,
             "status": "approved", "timestamp": _now(minutes=-45)},
        ],
    },
    "🏛️ Sanctions / PEP Hit": {
        "id": "sanctions_pep",
        "desc": "Politically Exposed Person with transactions to sanctioned regions — triggers OFAC screening.",
        "cardholder_id": "CH_DEMO_PEP_001",
        "cardholders": [{
            "cardholder_id": "CH_DEMO_PEP_001", "name": "Dmitri Volkov",
            "card_tier": "Gold", "kyc_verified": True, "pep_flag": True,
            "home_city": "Zurich", "risk_score": 0.88, "annual_spend_usd": 95000,
        }],
        "transactions": lambda: [
            {"cardholder_id": "CH_DEMO_PEP_001", "amount": a, "merchant_name": m,
             "channel": "online", "ip_country": c, "fraud_score": s,
             "is_flagged": True, "status": "approved", "timestamp": _now(hours=-i*2)}
            for i, (a, m, c, s) in enumerate([
                (50000, "Minsk Trading House", "Belarus", 0.97),
                (35000, "Sevastopol Shipping", "Russia", 0.95),
                (12000, "Tehran Imports", "Iran", 0.99),
            ])
        ],
    },
}


def inject_scenario(scenario_key: str) -> str:
    """Insert scenario data into MongoDB. Returns summary."""
    sc = FRAUD_SCENARIOS[scenario_key]
    tag = sc["id"]
    # Clean any previous injection of same scenario
    _inject_db.transactions.delete_many({_INJECT_TAG: tag})
    _inject_db.cardholders.delete_many({_INJECT_TAG: tag})
    _inject_db.merchant_networks.delete_many({_INJECT_TAG: tag})

    counts = {}
    # Cardholders
    docs = [{**ch, _INJECT_TAG: tag} for ch in sc.get("cardholders", [])]
    if docs:
        _inject_db.cardholders.insert_many(docs)
        counts["cardholders"] = len(docs)
    # Transactions (callable to get fresh timestamps)
    txn_fn = sc.get("transactions")
    txns = txn_fn() if callable(txn_fn) else (txn_fn or [])
    docs = [{**t, _INJECT_TAG: tag} for t in txns]
    if docs:
        _inject_db.transactions.insert_many(docs)
        counts["transactions"] = len(docs)
    # Merchant networks
    nets = sc.get("merchant_networks", [])
    docs = [{**n, _INJECT_TAG: tag} for n in nets]
    if docs:
        _inject_db.merchant_networks.insert_many(docs)
        counts["merchant_networks"] = len(docs)

    logger.info("Injected scenario %r: %s", tag, counts)
    return f"Injected **{scenario_key}**: " + ", ".join(f"{v} {k}" for k, v in counts.items())


def clear_all_scenarios() -> int:
    """Remove all injected scenario data. Returns total docs removed."""
    total = 0
    for col in ("transactions", "cardholders", "merchant_networks"):
        r = _inject_db[col].delete_many({_INJECT_TAG: {"$exists": True}})
        total += r.deleted_count
    logger.info("Cleared all injected scenarios: %d docs removed", total)
    return total


# ── Sidebar: Scenario Injection Panel ─────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🧪 Fraud Scenario Injection")
    st.markdown(
        "<small>Inject realistic fraud patterns into MongoDB so the agent "
        "has live data to detect and investigate.</small>",
        unsafe_allow_html=True,
    )
    for key, sc in FRAUD_SCENARIOS.items():
        with st.expander(key, expanded=False):
            st.markdown(f"<small>{sc['desc']}</small>", unsafe_allow_html=True)
            st.markdown(f"`cardholder_id`: `{sc['cardholder_id']}`")
            if st.button(f"💉 Inject", key=f"inject_{sc['id']}"):
                msg = inject_scenario(key)
                st.success(msg)

    st.markdown("---")
    if st.button("🗑️ Clear All Injected Scenarios", type="secondary"):
        n = clear_all_scenarios()
        st.info(f"Removed {n} injected documents from MongoDB.")

    # Show active scenarios
    active = _inject_db.transactions.distinct(_INJECT_TAG)
    if active:
        st.markdown(f"**Active scenarios:** `{'`, `'.join(active)}`")
    else:
        st.markdown("*No injected scenarios active*")


# ── Info Columns ───────────────────────────────────────────────────────────────
col_info, col_mem = st.columns([2, 1])
with col_info:
    st.markdown("**Autonomous Investigation Pipeline:**")
    steps = [
        ("1. Detect", "Scan transaction time-series for fraud scores ≥ 0.70, velocity anomalies"),
        ("2. Investigate", "Cross-reference cardholder profile, geo-velocity impossible travel"),
        ("3. Network Check", "$graphLookup to detect merchant fraud ring connections (depth ≤ 2)"),
        ("4. External Verify", "FastMCP: OFAC sanctions screening, merchant risk check"),
        ("5. Remediate", "FastMCP: Block card, send notification, file SAR if warranted"),
        ("6. Report", "Generate structured investigation summary with all evidence"),
    ]
    for label, desc in steps:
        st.markdown(f"**{label}** — {desc}")

    st.markdown("**MCP Tools (mock external APIs):**")
    for t in ["screen_sanctions","block_card","send_notification","file_sar","merchant_risk_check"]:
        st.markdown(f'<span class="tool-badge">{t}</span>', unsafe_allow_html=True)

with col_mem:
    st.markdown('<div class="memory-box">', unsafe_allow_html=True)
    st.markdown("**🧠 Memory Architecture**")
    st.markdown("""
**🧩 Episodic Memory**
Each fraud investigation is stored in MongoDB with full audit trail of all actions taken.

**🔧 Procedural Memory**
Fraud playbooks (card-not-present, ATO, money laundering) guide the agent's step-by-step investigation.

**⚡ Working Memory**
LangGraph `FraudAgentState` carries `severity`, `actions_taken`, `fraud_type` across all reasoning steps.
""")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# ── Blog feature callouts ──────────────────────────────────────────────────────
st.markdown("""
<div class="blog-note">
  <span class="blog-feature-tag bft-vector">🔵 Blog Feature: Atlas Vector Search</span>
  &nbsp; Fraud playbooks and case history are retrieved via <code>$vectorSearch</code> — semantic similarity over unstructured compliance documents.
  &nbsp;&nbsp;
  <span class="blog-feature-tag bft-ckpt">🟣 Blog Feature: MongoDB Checkpointer</span>
  &nbsp; LangGraph's <code>FraudAgentState</code> (severity · actions_taken · fraud_type) persists in MongoDB across every reasoning step — enabling crash recovery and full audit trails, exactly as described in the
  <a href="https://blog.langchain.com/announcing-the-langchain-mongodb-partnership-the-ai-agent-stack-that-runs-on-the-database-you-already-trust/" target="_blank">LangChain × MongoDB blog</a>.
  &nbsp;&nbsp;
  <span class="blog-feature-tag bft-smith">🔴 Blog Feature: LangSmith Observability</span>
  &nbsp; Every tool call, routing decision, and MongoDB retrieval is traced end-to-end in LangSmith.
</div>
""", unsafe_allow_html=True)

# ── Controls ───────────────────────────────────────────────────────────────────
st.markdown("### 🎯 Run Fraud Investigation")

mode = st.radio(
    "Investigation Mode:",
    ["🔍 Full Network Scan", "👤 Specific Cardholder"],
    horizontal=True,
    key="fraud_mode_radio",
)

cardholder_id = None
if mode == "👤 Specific Cardholder":
    # Build cardholder list: injected scenario IDs first, then defaults
    _injected_ids = sorted({
        sc["cardholder_id"] for sc in FRAUD_SCENARIOS.values()
        if sc["id"] in (_inject_db.transactions.distinct(_INJECT_TAG) or [])
    })
    _default_ids = [f"CH_{i:04d}" for i in range(1, 21)]
    _all_ids = (_injected_ids or []) + _default_ids
    cardholder_id = st.selectbox(
        "Select Cardholder:",
        _all_ids,
        index=0,
        key="fraud_cardholder_select",
        help="Injected scenario cardholders appear at the top (if active).",
    )

session_id = st.text_input("Session ID:", value="fraud-session-1", key="fraud_session")

col_btn, col_warn = st.columns([2, 3])
with col_btn:
    run_btn = st.button("🚨 Launch Autonomous Investigation", type="primary")
with col_warn:
    if mode == "🔍 Full Network Scan":
        st.markdown('<div class="alert-red">⚠️ <strong>Full Scan Mode:</strong> Agent will autonomously investigate top-risk transactions and may block cards and file SARs (simulated).</div>', unsafe_allow_html=True)

if run_btn:
    with st.spinner("🤖 VaultShield running autonomous fraud investigation..."):
        try:
            from agents.fraud_agent import run_fraud_investigation
            result = run_fraud_investigation(
                trigger="scan" if mode == "🔍 Full Network Scan" else "cardholder",
                cardholder_id=cardholder_id,
                session_id=session_id,
            )

            st.markdown("### 📋 Investigation Report")
            st.markdown(f'<div class="answer-box">{result["answer"]}</div>', unsafe_allow_html=True)

            if result.get("tool_calls"):
                st.markdown("### 🔧 Agent Actions Taken")
                tc_list = result["tool_calls"]
                # Categorise
                detect_tools = [t for t in tc_list if "transaction" in t or "flagged" in t or "velocity" in t or "trend" in t]
                invest_tools = [t for t in tc_list if "profile" in t or "merchant" in t or "playbook" in t]
                action_tools = [t for t in tc_list if "mcp" in t or "block" in t or "sar" in t or "notify" in t]

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown("**🔍 Detection**")
                    for t in detect_tools: st.success(f"✓ {t}")
                with c2:
                    st.markdown("**🔎 Investigation**")
                    for t in invest_tools: st.info(f"✓ {t}")
                with c3:
                    st.markdown("**⚡ Actions**")
                    for t in action_tools: st.warning(f"⚡ {t}")

            # Show message trace
            with st.expander("🔍 Full Agent Trace (All Tool Calls & Responses)"):
                for msg in result.get("messages", []):
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            st.markdown(f"**🔧 Tool Call:** `{tc.get('name','?')}`")
                            st.json(tc.get("args", {}))
                    elif msg.type == "tool":
                        with st.container():
                            st.markdown(f"**📤 Tool Result:**")
                            st.code(str(msg.content)[:500], language="text")

        except Exception as e:
            st.error(f"Agent error: {e}")
            st.info("Ensure .env is configured and MongoDB is seeded.")

# ── Live Monitor — Change Stream Autonomous Agent ─────────────────────────────
st.markdown("---")
st.markdown("### 📡 Live Monitor — Real-Time Change Stream Agent")
st.markdown("""
<div class="blog-note">
  <span class="blog-feature-tag bft-vector">🔵 Blog Feature: MongoDB Change Streams</span>
  &nbsp; The agent watches the <code>transactions</code> collection in real-time via
  <a href="https://www.mongodb.com/docs/manual/changeStreams/" target="_blank">Change Streams</a>.
  When you inject a fraud scenario (sidebar), new documents trigger the agent autonomously —
  <strong>no button press needed</strong>.
</div>
""", unsafe_allow_html=True)

# Initialize monitor state
if "fraud_monitor_running" not in st.session_state:
    st.session_state.fraud_monitor_running = False
if "fraud_monitor_events" not in st.session_state:
    st.session_state.fraud_monitor_events = []
if "fraud_monitor_obj" not in st.session_state:
    st.session_state.fraud_monitor_obj = None

col_m1, col_m2, col_m3 = st.columns([2, 2, 3])
with col_m1:
    if not st.session_state.fraud_monitor_running:
        if st.button("▶️ Start Live Monitor", type="primary", key="start_fraud_monitor"):
            try:
                from tools.change_stream_monitor import ChangeStreamMonitor

                def _fraud_change_callback(change_doc, db):
                    """Called by the change-stream thread for each new/updated transaction."""
                    full_doc = change_doc.get("fullDocument", {})
                    op = change_doc.get("operationType", "?")
                    cardholder_id = full_doc.get("cardholder_id", "unknown")
                    fraud_score = full_doc.get("fraud_score", 0)
                    amount = full_doc.get("amount", 0)
                    is_flagged = full_doc.get("is_flagged", False)

                    # Only investigate if it looks suspicious
                    if fraud_score >= 0.5 or is_flagged:
                        try:
                            from agents.fraud_agent import run_fraud_investigation
                            result = run_fraud_investigation(
                                trigger="cardholder",
                                cardholder_id=cardholder_id,
                                session_id=f"live-{cardholder_id}",
                            )
                            return {
                                "cardholder_id": cardholder_id,
                                "fraud_score": fraud_score,
                                "amount": amount,
                                "operation": op,
                                "answer": result.get("answer", ""),
                                "tool_calls": result.get("tool_calls", []),
                            }
                        except Exception as e:
                            return {
                                "cardholder_id": cardholder_id,
                                "fraud_score": fraud_score,
                                "amount": amount,
                                "operation": op,
                                "error": str(e),
                            }
                    return {
                        "cardholder_id": cardholder_id,
                        "fraud_score": fraud_score,
                        "amount": amount,
                        "operation": op,
                        "skipped": True,
                        "reason": f"Below threshold (score={fraud_score:.2f}, flagged={is_flagged})",
                    }

                monitor = ChangeStreamMonitor(MONGODB_URI, MONGODB_DB_NAME)
                monitor.watch(
                    collection="transactions",
                    pipeline=[{"$match": {"operationType": {"$in": ["insert", "update", "replace"]}}}],
                    callback=_fraud_change_callback,
                    label="fraud-live",
                )
                monitor.start()
                st.session_state.fraud_monitor_obj = monitor
                st.session_state.fraud_monitor_running = True
                st.rerun()
            except Exception as e:
                st.error(f"Failed to start monitor: {e}")
    else:
        if st.button("⏹️ Stop Live Monitor", key="stop_fraud_monitor"):
            if st.session_state.fraud_monitor_obj:
                st.session_state.fraud_monitor_obj.stop()
            st.session_state.fraud_monitor_running = False
            st.session_state.fraud_monitor_obj = None
            st.rerun()

with col_m2:
    if st.session_state.fraud_monitor_running:
        st.markdown("🟢 **Monitor ACTIVE** — watching `transactions`")
        st.caption("Inject a scenario from the sidebar to see it in action →")
    else:
        st.markdown("⚪ Monitor stopped")

with col_m3:
    if st.session_state.fraud_monitor_running and st.button("🔄 Refresh Feed", key="refresh_fraud_feed"):
        if st.session_state.fraud_monitor_obj:
            new_events = st.session_state.fraud_monitor_obj.drain()
            for ev in new_events:
                st.session_state.fraud_monitor_events.insert(0, {
                    "timestamp": ev.timestamp.strftime("%H:%M:%S"),
                    "collection": ev.collection,
                    "operation": ev.operation,
                    "label": ev.label,
                    "agent_result": ev.agent_result,
                    "error": ev.error,
                })
            # Keep last 50
            st.session_state.fraud_monitor_events = st.session_state.fraud_monitor_events[:50]

# Display live event feed
if st.session_state.fraud_monitor_events:
    st.markdown("#### 📋 Live Agent Event Feed")
    for i, ev in enumerate(st.session_state.fraud_monitor_events[:10]):
        res = ev.get("agent_result", {}) or {}
        ts = ev.get("timestamp", "?")
        ch = res.get("cardholder_id", "?")
        score = res.get("fraud_score", 0)
        amt = res.get("amount", 0)

        if res.get("skipped"):
            st.markdown(f"""<div class="step-box">
              <strong>⏰ {ts}</strong> | <code>{ev['operation']}</code> on <code>{ev['collection']}</code>
              | Cardholder: <code>{ch}</code> | Score: {score:.2f} | ${amt:,.2f}
              <br>⏭️ <em>Skipped — {res.get('reason','below threshold')}</em>
            </div>""", unsafe_allow_html=True)
        elif res.get("error"):
            st.markdown(f"""<div class="alert-red">
              <strong>⏰ {ts}</strong> | <code>{ev['operation']}</code> on <code>{ev['collection']}</code>
              | ❌ Error: {res['error'][:200]}
            </div>""", unsafe_allow_html=True)
        elif res.get("answer"):
            with st.expander(f"⏰ {ts} | 🚨 **{ch}** | Score: {score:.2f} | ${amt:,.2f} — Agent investigated", expanded=(i == 0)):
                st.markdown(f'<div class="answer-box">{res["answer"][:1500]}</div>', unsafe_allow_html=True)
                if res.get("tool_calls"):
                    st.markdown("**Tools used:** " + ", ".join(f"`{t}`" for t in res["tool_calls"]))
        elif ev.get("error"):
            st.error(f"⏰ {ts} | Monitor error: {ev['error'][:200]}")
elif st.session_state.fraud_monitor_running:
    st.info("📡 Listening for changes… Inject a scenario from the sidebar, then click **🔄 Refresh Feed**.")

# ── How it works ───────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("🏗️ Architecture — Fraud Agent Reasoning Graph"):
    st.markdown("""
```
                    ┌─────────────────────────────────────┐
                    │         FraudAgentState              │
                    │  messages · case_id · severity       │
                    │  actions_taken · fraud_type          │
                    └─────────────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   [Agent Node]     │  ← Azure GPT-4o
                    │   VaultShield LLM   │    reads playbook
                    └─────────┬──────────┘    (Procedural Memory)
              tool_calls?     │  no tool_calls
         ┌───────────────────►│◄────────────────────── END
         │           ┌────────┘
         │           ▼
         │  ┌─────────────────────────────────────────────┐
         │  │              [Tool Node]                    │
         │  │  MongoDB Tools:                             │
         │  │    get_flagged_transactions (time-series)   │
         │  │    check_transaction_velocity               │
         │  │    check_merchant_fraud_ring ($graphLookup) │
         │  │    timeseries_fraud_trend (aggregation)     │
         │  │  FastMCP Tools:                             │
         │  │    mcp_screen_sanctions → OFAC API         │
         │  │    mcp_block_card → NFG Card System       │
         │  │    mcp_file_sar → FinCEN SAR Portal        │
         │  │    mcp_send_notification → Push/SMS        │
         │  └─────────────────────────────────────────────┘
         │           │
         └───────────┘  (loops until no more tool calls)
```
**MongoDB query patterns used:**
- `$match` + `$sort` on `fraud_score` and `timestamp` (time-series)
- `$graphLookup` on `merchant_networks` (depth ≤ 2) for fraud ring detection
- `$group` + `$dateToString` for daily fraud trend aggregation
- All case history written to `conversation_history` (Episodic Memory)
""")
