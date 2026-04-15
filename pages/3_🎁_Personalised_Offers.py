"""
Page 3: Personalised Offers Concierge — Multi-Turn Chat Agent
"""

import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

st.set_page_config(page_title="Personalised Offers | VaultIQ", page_icon="🎁", layout="wide")

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
  .page-header { background: linear-gradient(135deg,#1a7340,#27ae60); padding:1.5rem 2rem;
    border-radius:10px; margin-bottom:1.2rem; }
  .page-header h2 { color:white; margin:0; } .page-header p { color:rgba(255,255,255,.88); margin:.3rem 0 0; }
  .chat-human { background:#EBF5FB; border-radius:12px 12px 4px 12px; padding:.8rem 1.1rem; margin:.4rem 0; }
  .chat-agent { background:#EAFAF1; border-radius:12px 12px 12px 4px; padding:.8rem 1.1rem; margin:.4rem 0; border-left:3px solid #27ae60; }
  .tool-badge { background:#E9F7EF; color:#27ae60; border-radius:6px; padding:2px 10px;
    font-size:.8rem; font-weight:600; display:inline-block; margin:2px; }
  .memory-box { background:#FFF8E7; border-left:4px solid #B5A06A; padding:.8rem 1rem; border-radius:6px; font-size:.88rem; }
  .cardholder-card { background:linear-gradient(135deg,#003087,#006FCF); border-radius:12px;
    padding:1.2rem 1.5rem; color:white; margin-bottom:1rem; }
  .blog-feature-tag {
    display:inline-block; padding:.18rem .65rem; border-radius:20px;
    font-size:.73rem; font-weight:700; margin:.15rem; border:1.5px solid;
  }
  .bft-vector { background:#dbeafe; color:#1d4ed8; border-color:#93c5fd; }
  .bft-hybrid { background:#d1fae5; color:#065f46; border-color:#6ee7b7; }
  .bft-mql    { background:#fef3c7; color:#92400e; border-color:#fcd34d; }
  .bft-ckpt   { background:#ede9fe; color:#5b21b6; border-color:#c4b5fd; }
  .bft-smith  { background:#fee2e2; color:#991b1b; border-color:#fca5a5; }
  .blog-note  { background:#f8faff; border:1px solid #c8d8f0; border-left:4px solid #27ae60;
    border-radius:6px; padding:.55rem .9rem; font-size:.82rem; color:#334; margin:.4rem 0; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
  <h2>🎁 Use Case 3: Personalised Offers Concierge</h2>
  <p>Multi-turn cardholder chat — semantic offer matching, geo-proximity discovery, and spending intelligence</p>
  <p style="margin-top:.6rem;">
    <span class="blog-feature-tag bft-vector">🔵 Atlas Vector Search</span>
    <span class="blog-feature-tag bft-hybrid">🟢 Hybrid Search ($rankFusion)</span>
    <span class="blog-feature-tag bft-ckpt">🟣 MongoDB Checkpointer</span>
    <span class="blog-feature-tag bft-smith">🔴 LangSmith Observability</span>
    &nbsp;<a href="https://blog.langchain.com/announcing-the-langchain-mongodb-partnership-the-ai-agent-stack-that-runs-on-the-database-you-already-trust/" target="_blank" style="color:rgba(255,255,255,.75);font-size:.78rem;">📄 Partnership blog →</a>
  </p>
</div>
""", unsafe_allow_html=True)

col_config, col_mem = st.columns([2, 1])
with col_config:
    st.markdown("**Capabilities:**")
    st.markdown("""
- 🔍 **Semantic search** — find offers matching interests (vector similarity)
- 🔀 **Hybrid search** — `$rankFusion`: `$vectorSearch` + `$search` (BM25) in one Atlas pipeline, fused server-side
- 📍 **Geo proximity** — locate nearby preferred partner merchants
- 💳 **Spending analytics** — category breakdown from transaction history
- ✨ **Points estimate** — Membership Rewards calculation by category multipliers
""")
    st.markdown("**Tools:**")
    for t in ["find_relevant_offers","hybrid_search_offers","find_nearby_offers","get_spending_summary","get_points_estimate"]:
        st.markdown(f'<span class="tool-badge">{t}</span>', unsafe_allow_html=True)

    st.markdown("""
<div class="blog-note" style="margin-top:.6rem;">
  <span class="blog-feature-tag bft-hybrid">🟢 Blog Feature: Hybrid Search — native Atlas <code>$rankFusion</code></span>
  &nbsp; <code>hybrid_search_offers</code> implements the <em>"Hybrid search combining keyword full-text search with vector similarity"</em>
  pattern from the <a href="https://blog.langchain.com/announcing-the-langchain-mongodb-partnership-the-ai-agent-stack-that-runs-on-the-database-you-already-trust/" target="_blank">LangChain × MongoDB blog</a>
  using a <strong>single Atlas aggregation pipeline</strong>:
  <ul style="margin:.4rem 0 .2rem 1.2rem; font-size:.85rem;">
    <li><code>$vectorSearch</code> leg — Voyage AI <code>voyage-finance-2</code> embeddings for semantic intent matching</li>
    <li><code>$search</code> leg — BM25 full-text on <code>description</code>, <code>benefit_text</code>, <code>merchant_name</code>, <code>category</code></li>
    <li><code>$rankFusion</code> — Reciprocal Rank Fusion runs <strong>inside Atlas</strong>, zero Python-side score merging</li>
  </ul>
  &nbsp;&nbsp;
  <span class="blog-feature-tag bft-vector">🔵 Blog Feature: Atlas Vector Search</span>
  &nbsp; <code>find_relevant_offers</code> uses pure <code>$vectorSearch</code> for intent-based offer matching.
</div>
""", unsafe_allow_html=True)

with col_mem:
    st.markdown('<div class="memory-box">', unsafe_allow_html=True)
    st.markdown("**🧠 Memory Architecture**")
    st.markdown("""
**🧩 Episodic Memory**
Full multi-turn conversation stored in MongoDB. Context preserved across messages — agent remembers what you asked before.

**📚 Semantic Memory**
Voyage AI vector embeddings on all offers and merchant descriptions enable intent-based discovery.
""")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# ── Cardholder Setup ───────────────────────────────────────────────────────────
st.markdown("### 👤 Cardholder Profile")

ccol1, ccol2, ccol3 = st.columns(3)
with ccol1:
    cardholder_id = st.selectbox("Select Cardholder:", [f"CH_{i:04d}" for i in range(1, 16)], index=0)
with ccol2:
    card_tier = st.selectbox("Card Tier:", ["Green","Gold","Platinum","Centurion"], index=2)
with ccol3:
    session_id = st.text_input("Session:", value=f"offers-{cardholder_id}")

st.markdown(f"""
<div class="cardholder-card">
  💳 <strong>Nexus Financial Group {card_tier} Card</strong> &nbsp;|&nbsp;
  Cardholder: {cardholder_id} &nbsp;|&nbsp;
  Session: {session_id}
</div>
""", unsafe_allow_html=True)

# ── Chat History ───────────────────────────────────────────────────────────────
if "offers_messages" not in st.session_state:
    st.session_state.offers_messages = []
if "offers_tool_calls" not in st.session_state:
    st.session_state.offers_tool_calls = []

# ── Example Prompts ────────────────────────────────────────────────────────────
EXAMPLE_PROMPTS = [
    "What dining offers are available for my Platinum card?",
    "Find me travel rewards near New York (lon: -74.006, lat: 40.713)",
    "Show my spending breakdown for the last 30 days",
    "How many Membership Rewards points have I earned recently?",
    "Any exclusive hotel offers expiring soon?",
    "Find cashback offers at grocery stores",
]

st.markdown("### 💬 Chat with VaultConcierge")
st.markdown("**💡 Quick starts:**")
ex_cols = st.columns(3)
for i, ep in enumerate(EXAMPLE_PROMPTS):
    if ex_cols[i % 3].button(ep[:40] + "...", key=f"ep_{i}", use_container_width=True):
        st.session_state["_offers_auto_send"] = ep
        st.rerun()

# ── Chat Display ───────────────────────────────────────────────────────────────
chat_container = st.container()
with chat_container:
    for msg in st.session_state.offers_messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-human">🧑 <strong>You:</strong> {msg["content"]}</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-agent">🤖 <strong>VaultConcierge:</strong><br>{msg["content"]}</div>',
                        unsafe_allow_html=True)

# ── Input ──────────────────────────────────────────────────────────────────────
with st.form("offers_form", clear_on_submit=True):
    user_input = st.text_input(
        "Your message:",
        placeholder="Ask about offers, spending, rewards...",
        key="offers_input_field",
    )
    submitted = st.form_submit_button("Send 💬", use_container_width=True)

_auto_send = st.session_state.pop("_offers_auto_send", None)
question_raw = _auto_send or (user_input.strip() if submitted else "")
if question_raw:
    st.session_state.offers_messages.append({"role": "user", "content": question_raw})
    user_input = question_raw

    with st.spinner("🤖 Concierge is finding your personalised offers..."):
        try:
            from agents.offers_agent import run_offers_chat
            from langchain_core.messages import HumanMessage, AIMessage

            # Reconstruct history
            history = []
            for m in st.session_state.offers_messages[:-1]:
                if m["role"] == "user":
                    history.append(HumanMessage(content=m["content"]))
                else:
                    history.append(AIMessage(content=m["content"]))

            result = run_offers_chat(
                message=user_input,
                cardholder_id=cardholder_id,
                card_tier=card_tier,
                session_id=session_id,
                history=history,
            )

            answer = result["answer"]
            st.session_state.offers_messages.append({"role": "assistant", "content": answer})
            if result.get("tool_calls"):
                st.session_state.offers_tool_calls = result["tool_calls"]

            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
            st.info("Ensure .env is configured and MongoDB is seeded.")

# ── Tool calls sidebar ─────────────────────────────────────────────────────────
if st.session_state.offers_tool_calls:
    with st.expander("🔧 Last Response — Tools Used"):
        for tc in st.session_state.offers_tool_calls:
            st.markdown(f'<span class="tool-badge">✓ {tc}</span>', unsafe_allow_html=True)

# ── Clear ──────────────────────────────────────────────────────────────────────
if st.button("🗑️ Clear Conversation"):
    st.session_state.offers_messages = []
    st.session_state.offers_tool_calls = []
    st.rerun()

st.markdown("---")
with st.expander("🔍 How Offer Matching Works"):
    st.markdown("""
**Hybrid Search Flow (native Atlas `$rankFusion`):**
```
User: "dining offers near Times Square for Platinum card"
        │
        └─► hybrid_search_offers → single $rankFusion aggregation pipeline sent to Atlas
                │
                ├─► $vectorSearch leg: Voyage AI embeds query → cosine similarity over offer embeddings
                │
                ├─► $search leg: BM25 full-text on description / benefit_text / merchant_name / category
                │
                └─► $rankFusion: Atlas fuses both legs via Reciprocal Rank Fusion SERVER-SIDE
                        │  (no Python score merging — one network round-trip)
        ├─► Geo filter: $near on offer.location for proximity ranking
        │
        └─► Tier filter: eligible_tiers includes "Platinum" → personalised results
```
**Why `$rankFusion`?** Pure `$vectorSearch` catches semantic intent ("fine dining" → "upscale restaurant"),
while `$search` (BM25) catches exact keywords ("Times Square", "Platinum"). Atlas fuses both server-side
via Reciprocal Rank Fusion — best recall + precision in a single query, no Python-side merging.
""")
