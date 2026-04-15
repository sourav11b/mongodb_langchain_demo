"""
Page 4: AML & Compliance Intelligence — Autonomous Regulatory Agent
"""

import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

st.set_page_config(page_title="Compliance Agent | VaultIQ", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
  [data-testid="stSidebar"] { background: linear-gradient(180deg,#003087 0%,#006FCF 100%); }
  [data-testid="stSidebar"] > div > div > div > * { color: white !important; }
  [data-testid="stSidebar"] [data-testid="stExpander"] details { background:rgba(255,255,255,.95); border-radius:8px; }
  [data-testid="stSidebar"] [data-testid="stExpander"] summary span,
  [data-testid="stSidebar"] [data-testid="stExpander"] summary svg { color:#003087 !important; }
  [data-testid="stSidebar"] [data-testid="stExpander"] p,
  [data-testid="stSidebar"] [data-testid="stExpander"] span:not(summary span),
  [data-testid="stSidebar"] [data-testid="stExpander"] code,
  [data-testid="stSidebar"] [data-testid="stExpander"] small { color:#1a1a2e !important; }
  [data-testid="stSidebar"] [data-testid="stExpander"] code { background:#e8ecf1; padding:1px 5px; border-radius:3px; }
  [data-testid="stSidebar"] [data-baseweb="select"] * { color:#1a1a2e !important; }
  [data-testid="stSidebar"] [data-testid="stTextInput"] input { color:#1a1a2e !important; }
  [data-testid="stSidebar"] .stAlert p, [data-testid="stSidebar"] .stAlert span { color:#1a1a2e !important; }
  .page-header { background: linear-gradient(135deg,#4a235a,#8e44ad); padding:1.5rem 2rem;
    border-radius:10px; margin-bottom:1.2rem; }
  .page-header h2 { color:white; margin:0; } .page-header p { color:rgba(255,255,255,.88); margin:.3rem 0 0; }
  .tool-badge { background:#F5EEF8; color:#8e44ad; border-radius:6px; padding:2px 10px;
    font-size:.8rem; font-weight:600; display:inline-block; margin:2px; }
  .memory-box { background:#FFF8E7; border-left:4px solid #B5A06A; padding:.8rem 1rem; border-radius:6px; font-size:.88rem; }
  .answer-box { background:#F9F0FF; border:1px solid #D7BDE2; border-radius:10px; padding:1.2rem 1.5rem; }
  .rule-card { background:#FFF; border:1px solid #D7BDE2; border-radius:8px; padding:1rem; margin:.5rem 0;
    border-left:4px solid #8e44ad; }
  .reg-badge { padding:3px 10px; border-radius:12px; font-size:.75rem; font-weight:700;
    display:inline-block; margin:2px; }
  .reg-bsa { background:#FDEDEC; color:#c0392b; }
  .reg-gdpr { background:#EBF5FB; color:#2471A3; }
  .reg-fatca { background:#EAFAF1; color:#1a7340; }
  .reg-ofac { background:#FEF9E7; color:#B7950B; }
  .blog-feature-tag {
    display:inline-block; padding:.18rem .65rem; border-radius:20px;
    font-size:.73rem; font-weight:700; margin:.15rem; border:1.5px solid;
  }
  .bft-vector { background:#dbeafe; color:#1d4ed8; border-color:#93c5fd; }
  .bft-hybrid { background:#d1fae5; color:#065f46; border-color:#6ee7b7; }
  .bft-mql    { background:#fef3c7; color:#92400e; border-color:#fcd34d; }
  .bft-ckpt   { background:#ede9fe; color:#5b21b6; border-color:#c4b5fd; }
  .bft-smith  { background:#fee2e2; color:#991b1b; border-color:#fca5a5; }
  .blog-note  { background:#f8faff; border:1px solid #c8d8f0; border-left:4px solid #8e44ad;
    border-radius:6px; padding:.55rem .9rem; font-size:.82rem; color:#334; margin:.4rem 0; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
  <h2>⚖️ Use Case 4: AML & Compliance Intelligence Agent</h2>
  <p>Autonomous regulatory review across BSA · FATCA · OFAC · GDPR · PSD2 — graph-powered AML network analysis</p>
  <p style="margin-top:.6rem;">
    <span class="blog-feature-tag bft-vector">🔵 Atlas Vector Search</span>
    <span class="blog-feature-tag bft-mql">🟡 Text-to-MQL</span>
    <span class="blog-feature-tag bft-ckpt">🟣 MongoDB Checkpointer</span>
    <span class="blog-feature-tag bft-smith">🔴 LangSmith Observability</span>
    &nbsp;<a href="https://blog.langchain.com/announcing-the-langchain-mongodb-partnership-the-ai-agent-stack-that-runs-on-the-database-you-already-trust/" target="_blank" style="color:rgba(255,255,255,.75);font-size:.78rem;">📄 Partnership blog →</a>
  </p>
</div>
""", unsafe_allow_html=True)

# ── Overview ───────────────────────────────────────────────────────────────────
col_info, col_mem = st.columns([2, 1])
with col_info:
    st.markdown("**Regulatory Frameworks Covered:**")
    regs = [
        ("BSA/AML", "reg-bsa", "Currency Transaction Reports ($10K), SAR filing ($5K), structuring detection"),
        ("FATCA", "reg-fatca", "Foreign account reporting, withholding on non-compliant entities"),
        ("OFAC", "reg-ofac", "Real-time SDN list screening, sanctions exposure mapping"),
        ("GDPR", "reg-gdpr", "Data retention rules, right to erasure, data minimisation"),
        ("PSD2", "reg-gdpr", "Strong Customer Authentication thresholds for EU payments"),
    ]
    for reg, cls, desc in regs:
        st.markdown(f'<span class="reg-badge {cls}">{reg}</span> {desc}', unsafe_allow_html=True)

    st.markdown("\n**Autonomous Capabilities:**")
    st.markdown("""
- 📋 Semantic rule lookup (compliance vector search)
- 🕸️ Graph-based AML network analysis (layering detection)
- 📄 Unstructured case note analysis (AML trigger extraction)
- 💰 Threshold monitoring (BSA CTR + SAR thresholds)
- 📡 OFAC sanctions exposure mapping by IP country
- 📝 Autonomous SAR filing via FastMCP
- 📊 Compliance report generation with audit trail
""")
    st.markdown("**MCP Tools:**")
    for t in ["mcp_file_sar_compliance","mcp_ofac_screen_compliance"]:
        st.markdown(f'<span class="tool-badge">{t}</span>', unsafe_allow_html=True)

    st.markdown("""
<div class="blog-note" style="margin-top:.6rem;">
  <span class="blog-feature-tag bft-vector">🔵 Blog Feature: Atlas Vector Search</span>
  &nbsp; Compliance rules (BSA, FATCA, GDPR, OFAC, PSD2) are retrieved by semantic similarity via
  <code>$vectorSearch</code> — no rigid keyword matching. The agent finds relevant regulations
  even when case descriptions use different terminology.
  &nbsp;&nbsp;
  <span class="blog-feature-tag bft-mql">🟡 Blog Feature: Text-to-MQL</span>
  &nbsp; The agent generates MQL aggregation pipelines to query transaction thresholds and
  case histories from plain-language instructions — the <em>natural-language querying over operational data</em>
  pattern from the <a href="https://blog.langchain.com/announcing-the-langchain-mongodb-partnership-the-ai-agent-stack-that-runs-on-the-database-you-already-trust/" target="_blank">LangChain × MongoDB blog</a>.
</div>
""", unsafe_allow_html=True)

with col_mem:
    st.markdown('<div class="memory-box">', unsafe_allow_html=True)
    st.markdown("**🧠 Memory Architecture**")
    st.markdown("""
**📚 Semantic Memory**
10 compliance rules (BSA, FATCA, GDPR, OFAC, PSD2) vector-indexed with Voyage AI. Agent retrieves relevant regulations by semantic similarity — not keyword matching.

**🔧 Procedural Memory**
AML playbooks define step-by-step investigation procedures: detect → analyse → escalate → report.

**🧩 Episodic Memory**
All compliance actions written to MongoDB for full regulatory audit trail.
""")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# ── Run Controls ───────────────────────────────────────────────────────────────
st.markdown("### 🎯 Run Compliance Investigation")

tab1, tab2 = st.tabs(["🔍 Full Compliance Audit", "👤 Individual Cardholder Review"])

with tab1:
    st.markdown("""
**Full Audit** performs:
1. Look up top AML and sanctions rules
2. Identify cardholders breaching BSA thresholds
3. Analyse open fraud cases for AML triggers in unstructured notes
4. Run network graph analysis on highest-risk cardholder
5. Check sanctions exposure, file SAR if needed
6. Generate compliance report
""")
    col_btn1, _ = st.columns([2, 3])
    with col_btn1:
        if st.button("⚖️ Run Full Compliance Audit", type="primary"):
            with st.spinner("🤖 VaultComply running regulatory review..."):
                try:
                    from agents.compliance_agent import run_compliance_investigation
                    result = run_compliance_investigation(session_id="audit-full")
                    st.markdown("### 📋 Compliance Report")
                    st.markdown(f'<div class="answer-box">{result["answer"]}</div>', unsafe_allow_html=True)
                    if result.get("tool_calls"):
                        st.markdown("### 🔧 Regulatory Actions Taken")
                        cols = st.columns(min(4, len(result["tool_calls"])))
                        for i, tc in enumerate(result["tool_calls"]):
                            cols[i % 4].info(f"⚖️ {tc}")
                    with st.expander("📜 Full Agent Trace"):
                        for msg in result.get("messages", []):
                            if hasattr(msg, "tool_calls") and msg.tool_calls:
                                for tc in msg.tool_calls:
                                    st.markdown(f"**🔧 `{tc.get('name','?')}`** — args: {tc.get('args',{})}")
                            elif msg.type == "tool":
                                st.code(str(msg.content)[:600], language="text")
                except Exception as e:
                    st.error(f"Agent error: {e}")
                    st.info("Ensure .env configured and MongoDB seeded.")

with tab2:
    col_ch, col_q = st.columns([1, 2])
    with col_ch:
        ch_id = st.selectbox("Cardholder:", [f"CH_{i:04d}" for i in range(1, 16)])
    with col_q:
        custom_prompt = st.text_area(
            "Custom compliance question (optional):",
            placeholder="e.g. Does this cardholder have sanctions exposure?",
            height=80,
        )

    # ── Feature-specific Quick Start prompts ───────────────────────────────
    COMPLIANCE_PROMPTS = [
        # 📋 Semantic rule lookup → search_compliance_rules
        ("📋 Rule Lookup", "Search for AML and Know-Your-Customer regulations applicable to high-value wire transfers"),
        # 💰 BSA Thresholds → check_transaction_thresholds
        ("💰 BSA Thresholds", "Check if this cardholder has breached the BSA $10,000 CTR or $5,000 SAR reporting thresholds"),
        # 📡 Sanctions Exposure → check_sanctions_exposure
        ("📡 Sanctions", "Does this cardholder have transactions to OFAC-sanctioned countries like Russia, Iran, or North Korea?"),
        # 🕸️ AML Network → aml_network_analysis
        ("🕸️ AML Network", "Run AML network analysis to detect layering through connected merchant networks"),
        # 📄 Case Notes → analyse_fraud_case_notes
        ("📄 Case Notes", "Analyse open fraud case investigation notes for AML triggers and regulatory implications"),
        # 📡 OFAC Screen → mcp_ofac_screen_compliance
        ("📡 OFAC Screen", "Run OFAC sanctions screening on this cardholder's name and home country"),
    ]
    st.markdown("**💡 Quick starts — click to auto-fill:**")
    qs_cols = st.columns(3)
    for i, (label, prompt_text) in enumerate(COMPLIANCE_PROMPTS):
        if qs_cols[i % 3].button(label, key=f"comp_qs_{i}", use_container_width=True, help=prompt_text):
            st.session_state["_comp_auto_fill"] = prompt_text
            st.rerun()

    _auto_fill = st.session_state.pop("_comp_auto_fill", None)
    effective_prompt = _auto_fill or (custom_prompt.strip() if custom_prompt.strip() else None)

    if st.button("🔍 Investigate Cardholder Compliance", type="primary"):
        with st.spinner(f"🤖 Reviewing {ch_id} for regulatory compliance..."):
            try:
                from agents.compliance_agent import run_compliance_investigation
                result = run_compliance_investigation(
                    prompt=effective_prompt,
                    cardholder_id=ch_id,
                    session_id=f"comp-{ch_id}",
                )
                st.markdown(f"### 📋 Report: {ch_id}")
                st.markdown(f'<div class="answer-box">{result["answer"]}</div>', unsafe_allow_html=True)
                if result.get("tool_calls"):
                    st.markdown("**Tools:**")
                    for tc in result["tool_calls"]:
                        st.markdown(f'<span class="tool-badge">⚖️ {tc}</span>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error: {e}")

# ── Compliance Rules Preview ───────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 📋 Compliance Rule Base (MongoDB Vector-Indexed)")

try:
    from pymongo import MongoClient
    from config import MONGODB_URI, MONGODB_DB_NAME
    db = MongoClient(MONGODB_URI)[MONGODB_DB_NAME]
    rules = list(db.compliance_rules.find({}, {"_id": 0, "embedding": 0}, limit=5))
    if rules:
        for r in rules:
            cls_map = {"AML":"reg-bsa","Tax Compliance":"reg-fatca","Sanctions":"reg-ofac",
                       "Data Privacy":"reg-gdpr","Payments":"reg-gdpr","KYC":"reg-fatca","Fraud":"reg-ofac"}
            cls = cls_map.get(r.get("category",""), "reg-bsa")
            st.markdown(f"""
<div class="rule-card">
  <strong>{r.get('rule_name','?')}</strong>
  <span class="reg-badge {cls}">{r.get('rule_id','?')}</span>
  <span class="reg-badge {cls}">{r.get('jurisdiction','?')}</span>
  <span class="reg-badge {cls}">{r.get('category','?')}</span>
  <br><small style="color:#666">{r.get('rule_text','')[:220]}...</small>
</div>
""", unsafe_allow_html=True)
    else:
        st.info("Run `python -m data.seed_data` to populate compliance rules.")
except Exception as e:
    st.warning(f"Cannot load rules from MongoDB: {e}")

st.markdown("---")
with st.expander("🏗️ Architecture — AML Agent Graph + MongoDB Patterns"):
    st.markdown("""
**AML Investigation Flow:**
```
Compliance Trigger (threshold breach / case flag / scheduled audit)
    │
    ▼
[search_compliance_rules] → Voyage AI → Atlas Vector Search → top-N rules
    │
    ▼
[check_transaction_thresholds] → $group aggregation → BSA CTR/SAR flags
    │
    ▼
[analyse_fraud_case_notes] → regex + semantic match on free-text notes
    │
    ▼
[aml_network_analysis] → $graphLookup (merchant_networks, depth≤2)
    │                    → merchant risk cluster detection
    ▼
[check_sanctions_exposure] → IP country mapping to OFAC sanctioned list
    │
    ├─ SAR warranted? → [mcp_file_sar_compliance] → FastMCP → FinCEN
    │
    └─► [generate_compliance_report] → write to MongoDB compliance_reports
```
**Key MongoDB features:**
- `$graphLookup` on `merchant_networks` to detect AML layering patterns
- Vector search on `compliance_rules` for semantic regulation retrieval
- `$group` pipeline on `transactions` for threshold monitoring
- Unstructured text in `fraud_cases.investigation_notes` analysed by LLM
- Episodic audit trail in `conversation_history` collection
""")
