"""
Page 9 — Unified Aggregate Pipeline
Combines $rankFusion + $geoWithin + time-series $lookup + $graphLookup
in a single MongoDB aggregate query, then reranks with Voyage AI rerank-2.
"""

import streamlit as st
import json

st.set_page_config(page_title="Unified Pipeline — VaultIQ", page_icon="🔗", layout="wide")

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""<style>
  .stage-badge { display:inline-block; padding:4px 10px; border-radius:12px;
    font-size:.78rem; font-weight:600; margin:2px 4px; }
  .sb-rank   { background:#E8D5F5; color:#6A1B9A; }
  .sb-geo    { background:#D5F5E3; color:#1B5E20; }
  .sb-ts     { background:#FFF3CD; color:#856404; }
  .sb-graph  { background:#D6EAF8; color:#1B4F72; }
  .sb-rerank { background:#FADBD8; color:#922B21; }
  .metric-box { background:#f8f9fa; border:1px solid #dee2e6; border-radius:8px;
    padding:12px 16px; text-align:center; }
  .metric-box h3 { margin:0; font-size:1.6rem; color:#006FCF; }
  .metric-box p  { margin:0; font-size:.78rem; color:#666; }
  .result-card { background:#f8f9fa; border:1px solid #dee2e6; border-radius:8px;
    padding:14px; margin-bottom:10px; }
  .rerank-score { font-size:1.1rem; font-weight:700; color:#006FCF; }
  .pos-change { font-size:.8rem; padding:2px 8px; border-radius:10px; }
  .pos-up   { background:#D5F5E3; color:#1B5E20; }
  .pos-down { background:#FADBD8; color:#922B21; }
  .pos-same { background:#F0F0F0; color:#666; }
</style>""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,#001E2B 0%,#023430 100%);
  padding:1.5rem 2rem; border-radius:12px; margin-bottom:1rem;">
  <h2 style="color:#00ED64; margin:0;">🔗 Unified Aggregate Pipeline</h2>
  <p style="color:#B8C4CE; margin:.3rem 0 0;">
    <strong>4 MongoDB features</strong> in a <strong>single</strong> aggregate query
    — reranked by <strong>Voyage AI rerank-2</strong>
  </p>
</div>
""", unsafe_allow_html=True)

# Pipeline stages legend
st.markdown("""
<span class="stage-badge sb-rank">① $rankFusion</span>
<span class="stage-badge sb-geo">② $geoWithin</span>
<span class="stage-badge sb-ts">③ $lookup (time-series)</span>
<span class="stage-badge sb-graph">④ $graphLookup</span>
<span class="stage-badge sb-rerank">⑤ Voyage AI rerank-2</span>
""", unsafe_allow_html=True)

st.markdown("---")

# ── Imports ──────────────────────────────────────────────────────────────────
from tools.unified_pipeline import run_unified_pipeline, CITY_COORDS, SAMPLE_QUERIES

# ── Input Controls ───────────────────────────────────────────────────────────
col_q, col_params = st.columns([3, 2])

with col_q:
    st.markdown("#### 💬 Query")
    preset = st.selectbox(
        "Sample queries", ["— custom —"] + SAMPLE_QUERIES,
        key="up_preset", label_visibility="collapsed",
    )
    default_q = preset if preset != "— custom —" else ""
    query = st.text_area(
        "Enter your query",
        value=default_q,
        height=80,
        placeholder="e.g. Find travel dining offers near New York from low-risk merchants...",
        label_visibility="collapsed",
    )

with col_params:
    st.markdown("#### ⚙️ Parameters")
    p1, p2 = st.columns(2)
    with p1:
        city = st.selectbox("City hub", list(CITY_COORDS.keys()), key="up_city")
        radius_km = st.slider("Radius (km)", 10, 200, 50, step=10, key="up_radius")
    with p2:
        days_back = st.slider("Time window (days)", 30, 365, 90, step=30, key="up_days")
        rerank_k = st.slider("Rerank top-K", 3, 10, 5, key="up_rerank_k")

run_btn = st.button("🚀 Execute Unified Pipeline", type="primary", use_container_width=True,
                     disabled=not query.strip())

# ── Pipeline Architecture ────────────────────────────────────────────────────
with st.expander("🏗️ Pipeline Architecture — how it works", expanded=False):
    st.markdown("""
```
User Query: "Find travel dining offers near New York from low-risk merchants"
    │
    ▼
┌─── Stage 1: $rankFusion ────────────────────────────────────────────┐
│  ├── $vectorSearch leg: Voyage AI voyage-finance-2 → cosine sim    │
│  └── $search leg: BM25 full-text on description/benefit/category   │
│  Reciprocal Rank Fusion (60% vector, 40% BM25) → merged results   │
└─────────────────────────────────────────────────────────────────────┘
    │ (up to 15 fused results)
    ▼
┌─── Stage 2: $geoWithin ($centerSphere) ────────────────────────────┐
│  Filter offers within radius of city hub coordinates               │
│  Uses $centerSphere for geodesic distance on GeoJSON Points        │
└─────────────────────────────────────────────────────────────────────┘
    │ (geo-filtered subset)
    ▼
┌─── Stage 3: $lookup → transactions (time-series) ──────────────────┐
│  Correlated subquery: join by merchant_id                          │
│  $match timestamp ≥ cutoff → $group for aggregated stats:          │
│    txn_count, total_volume, avg_amount, max_fraud_score, flagged   │
└─────────────────────────────────────────────────────────────────────┘
    │ (enriched with transaction metrics)
    ▼
┌─── Stage 4: $graphLookup → merchant_networks ──────────────────────┐
│  Recursive traversal (depth ≤ 2) across merchant edges             │
│  Computes: network_depth, risk_connections count                   │
└─────────────────────────────────────────────────────────────────────┘
    │ (enriched with network graph data)
    ▼
┌─── Stage 5: Voyage AI rerank-2 ────────────────────────────────────┐
│  Build text repr of each result (offer + txn stats + network info) │
│  Rerank against original query for final relevance ordering        │
│  Returns top-K with rerank_score                                   │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
  Final reranked results with scores
```
""")

# ── Execute & Display Results ────────────────────────────────────────────────
if run_btn and query.strip():
    with st.spinner("Executing unified pipeline — embedding → $rankFusion → $geoWithin → $lookup → $graphLookup → Voyage rerank..."):
        try:
            result = run_unified_pipeline(
                query=query.strip(),
                city=city,
                radius_km=float(radius_km),
                days_back=days_back,
                rerank_top_k=rerank_k,
            )
            st.session_state["up_result"] = result
        except Exception as e:
            st.error(f"Pipeline error: {e}")
            st.session_state.pop("up_result", None)

if "up_result" in st.session_state:
    r = st.session_state["up_result"]

    # ── Metrics Row ──
    st.markdown("### 📊 Pipeline Metrics")
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(f'<div class="metric-box"><h3>{r["pipeline_ms"]}ms</h3><p>Pipeline execution</p></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-box"><h3>{r["rerank_ms"]}ms</h3><p>Voyage rerank-2</p></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-box"><h3>{r["total_ms"]}ms</h3><p>Total latency</p></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="metric-box"><h3>{r["raw_count"]}</h3><p>MongoDB results</p></div>', unsafe_allow_html=True)
    with m5:
        st.markdown(f'<div class="metric-box"><h3>{r["reranked_count"]}</h3><p>Reranked results</p></div>', unsafe_allow_html=True)

    # ── Stages used ──
    st.markdown("**Stages executed:** " + " → ".join(
        f'<span class="stage-badge {cls}">{s}</span>'
        for s, cls in zip(r["pipeline_stages"], ["sb-rank", "sb-geo", "sb-ts", "sb-graph"])
    ) + ' → <span class="stage-badge sb-rerank">Voyage rerank-2</span>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Reranked Results ──
    st.markdown("### 🏆 Reranked Results (Voyage AI rerank-2)")

    if not r["reranked_results"]:
        st.warning("No results found. Try a broader radius or different query.")
    else:
        for i, doc in enumerate(r["reranked_results"]):
            orig_pos = doc.get("original_position", "?")
            new_pos = doc.get("rerank_position", i + 1)
            score = doc.get("rerank_score")
            txn = doc.get("txn_summary") or {}

            # Position change indicator
            if isinstance(orig_pos, int) and isinstance(new_pos, int):
                diff = orig_pos - new_pos
                if diff > 0:
                    pos_html = f'<span class="pos-change pos-up">↑{diff}</span>'
                elif diff < 0:
                    pos_html = f'<span class="pos-change pos-down">↓{abs(diff)}</span>'
                else:
                    pos_html = '<span class="pos-change pos-same">—</span>'
            else:
                pos_html = ""

            score_str = f" · Rerank score: **{score}**" if score is not None else ""
            label = (
                f"#{new_pos} {pos_html} **{doc.get('merchant_name', '?')}** — "
                f"{doc.get('category', '')} | {doc.get('benefit_text', '')[:60]}"
                f"{score_str}"
            )

            with st.expander(label, expanded=(i == 0)):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**📝 Offer Details**")
                    st.markdown(f"- **Merchant:** {doc.get('merchant_name', '?')}")
                    st.markdown(f"- **Category:** {doc.get('category', '?')}")
                    st.markdown(f"- **Benefit:** {doc.get('benefit_text', '?')}")
                    st.markdown(f"- **Description:** {doc.get('description', '')[:200]}")
                    st.markdown(f"- **City:** {doc.get('city', '?')}")
                    tiers = doc.get("eligible_tiers", [])
                    st.markdown(f"- **Eligible tiers:** {', '.join(tiers) if tiers else '—'}")

                with c2:
                    st.markdown("**📈 Transaction Stats** (time-series)")
                    if txn:
                        st.markdown(f"- Transactions: **{txn.get('txn_count', 0)}**")
                        st.markdown(f"- Total volume: **${txn.get('total_volume', 0):,.2f}**")
                        st.markdown(f"- Avg amount: **${txn.get('avg_amount', 0):,.2f}**")
                        st.markdown(f"- Max fraud score: **{txn.get('max_fraud_score', 0):.4f}**")
                        st.markdown(f"- Flagged txns: **{txn.get('flagged_count', 0)}**")
                    else:
                        st.caption("No transactions in time window")

                    st.markdown("**🕸️ Network Graph** ($graphLookup)")
                    st.markdown(f"- Connected nodes: **{doc.get('network_depth', 0)}**")
                    risk = doc.get("risk_connections", 0)
                    risk_icon = "🚨" if risk > 0 else "✅"
                    st.markdown(f"- Risk connections: **{risk}** {risk_icon}")

                    # Show network nodes if present
                    net = doc.get("network", [])
                    if net:
                        names = [n.get("merchant_name", "?") for n in net[:5] if isinstance(n, dict)]
                        if names:
                            st.caption(f"Connected: {', '.join(names)}")

    st.markdown("---")

    # ── Raw MongoDB Results ──
    with st.expander(f"📦 Raw MongoDB Results ({r['raw_count']} docs)", expanded=False):
        for i, doc in enumerate(r["raw_results"]):
            st.markdown(f"**Result {i+1}:** {doc.get('merchant_name', '?')} — {doc.get('category', '')}")
            st.json(doc)

    # ── Pipeline MQL ──
    with st.expander("📝 Full Pipeline MQL", expanded=False):
        st.code(json.dumps(r["pipeline_mql"], indent=2, default=str), language="javascript")

    # ── Pipeline Explanation ──
    with st.expander("📖 What each stage does"):
        st.markdown("""
| Stage | Operator | What It Does |
|-------|----------|-------------|
| 1 | `$rankFusion` | Runs `$vectorSearch` (Voyage AI cosine similarity) and `$search` (BM25 full-text) as parallel legs, then fuses scores via Reciprocal Rank Fusion server-side — **one round-trip** |
| 2 | `$geoWithin` | Filters results by geographic proximity using `$centerSphere` on GeoJSON Point locations — keeps only offers within the selected radius of the city hub |
| 3 | `$lookup` | Correlated subquery joining `transactions` by `merchant_id`, filtering by timestamp ≥ cutoff, then `$group` to compute time-series metrics (count, volume, avg, fraud score) |
| 4 | `$graphLookup` | Recursive traversal of `merchant_networks` graph (depth ≤ 2) to find connected merchants and count risk-flagged cluster connections |
| 5 | Voyage AI `rerank-2` | Application-level reranking — builds a text representation of each enriched result and reranks against the original query for final relevance ordering |
""")
