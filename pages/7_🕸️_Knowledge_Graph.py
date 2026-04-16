"""
Page 7: Knowledge Graph Agent — MongoDBGraphStore + GraphRAG Retriever

Build a knowledge graph from fraud cases, compliance rules, and merchant
networks. Query it with natural language — the retriever traverses the
graph via $graphLookup and the LLM synthesises multi-hop answers.
"""

import streamlit as st
import sys, os, logging, json
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger("vaultiq.page.knowledge_graph")

st.set_page_config(page_title="Knowledge Graph | VaultIQ", page_icon="🕸️", layout="wide")

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
  .page-header {
    background: linear-gradient(135deg,#1a0533,#4a1a8a);
    padding:1.5rem 2rem; border-radius:10px; margin-bottom:1rem;
  }
  .page-header h2 { color:white; margin:0; }
  .page-header p  { color:rgba(255,255,255,.88); margin:.3rem 0 0; }
  .blog-feature-tag {
    display:inline-block; padding:.18rem .65rem; border-radius:20px;
    font-size:.73rem; font-weight:700; margin:.15rem; border:1.5px solid;
  }
  .bft-graph  { background:#ede9fe; color:#5b21b6; border-color:#c4b5fd; }
  .bft-vector { background:#dbeafe; color:#1d4ed8; border-color:#93c5fd; }
  .bft-smith  { background:#fee2e2; color:#991b1b; border-color:#fca5a5; }
  .bft-toolkit { background:#d1fae5; color:#065f46; border-color:#6ee7b7; }
  .blog-note  { background:#f8faff; border:1px solid #c8d8f0; border-left:4px solid #6b21a8;
    border-radius:6px; padding:.55rem .9rem; font-size:.82rem; color:#334; margin:.4rem 0; }
  .answer-box { background:#f5f0ff; border:1px solid #c4b5fd; border-left:4px solid #6b21a8;
    border-radius:6px; padding:1rem; margin:.5rem 0; }
  .entity-chip { background:#ede9fe; color:#5b21b6; border-radius:5px;
    padding:2px 10px; font-size:.78rem; font-weight:600; display:inline-block; margin:2px; }
  .rel-chip { background:#fef3c7; color:#92400e; border-radius:5px;
    padding:2px 10px; font-size:.78rem; font-weight:600; display:inline-block; margin:2px; }
  .step-box { background:#f8f9fa; border:1px solid #d5e0ea; border-radius:6px;
    padding:.7rem 1rem; margin:.4rem 0; }
  .graph-stat { background:#f5f0ff; border:2px solid #c4b5fd; border-radius:10px;
    padding:.8rem 1.2rem; text-align:center; }
  .graph-stat .big { font-size:1.8rem; font-weight:800; color:#5b21b6; }
  .graph-stat .lbl { font-size:.8rem; color:#666; }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
  <h2>🕸️ Use Case 6: Knowledge Graph Agent</h2>
  <p>Build a knowledge graph from financial data using LLM entity extraction —
     then query it with natural language via graph traversal</p>
  <p style="margin-top:.6rem">
    <span class="blog-feature-tag bft-graph">🕸️ MongoDBGraphStore</span>
    <span class="blog-feature-tag bft-graph">🔍 GraphRAG Retriever</span>
    <span class="blog-feature-tag bft-vector">🔵 Atlas Vector Search</span>
    <span class="blog-feature-tag bft-toolkit">🍃 langchain-mongodb</span>
    <span class="blog-feature-tag bft-smith">🔴 LangSmith</span>
  </p>
</div>
""", unsafe_allow_html=True)


# ── Overview ───────────────────────────────────────────────────────────────────
col_info, col_arch = st.columns([3, 2])

with col_info:
    st.markdown("""
**What is MongoDBGraphStore + GraphRAG?**

[MongoDBGraphStore](https://langchain-mongodb.readthedocs.io/en/stable/) stores a
**knowledge graph** directly in MongoDB — entities as documents, relationships as
embedded arrays. The LLM automatically extracts entities and relationships from
unstructured text (fraud case notes, compliance rules, merchant data).

[MongoDBGraphRAGRetriever](https://langchain-mongodb.readthedocs.io/en/stable/)
answers multi-hop questions by:
1. Extracting entity names from the question
2. Traversing the graph via `related_entities` (uses `$graphLookup`)
3. Gathering context from connected entities
4. Synthesising an answer from the graph context

**Why is this powerful for financial services?**
- 🕸️ Discover hidden connections between merchants, fraud cases, and cardholders
- 📋 Trace which compliance rules apply to which entities
- 🔍 Answer multi-hop questions like "Which merchants connected to fraud rings
  also have cardholders flagged for BSA violations?"
""")

    st.markdown("""
<div class="blog-note">
  <span class="blog-feature-tag bft-graph">🕸️ Blog Feature: Knowledge Graph</span>
  &nbsp; Unlike <code>$graphLookup</code> on pre-structured data, GraphRAG <strong>builds the graph
  automatically</strong> from unstructured text using LLM entity extraction. Entities,
  types, and relationships are inferred — no schema pre-definition required.
</div>
""", unsafe_allow_html=True)

with col_arch:
    st.markdown("**🧩 Entity Types (extracted by LLM):**")
    entity_types = [
        "Cardholder", "Merchant", "Transaction", "FraudCase",
        "ComplianceRule", "Regulation", "Country", "City",
        "CardTier", "MerchantCategory", "FraudType", "RiskLevel",
    ]
    chips = " ".join(f'<span class="entity-chip">{e}</span>' for e in entity_types)
    st.markdown(chips, unsafe_allow_html=True)

    st.markdown("**🔗 Relationship Types:**")
    rel_types = [
        "HAS_TRANSACTION", "FLAGGED_BY", "INVESTIGATED_IN",
        "VIOLATES", "LOCATED_IN", "CONNECTED_TO", "OWNS",
        "FRAUD_RING_WITH", "REGULATED_BY",
    ]
    chips = " ".join(f'<span class="rel-chip">{r}</span>' for r in rel_types)
    st.markdown(chips, unsafe_allow_html=True)

    st.markdown("**📚 Source Collections:**")
    sources = ["fraud_cases", "compliance_rules", "merchant_networks", "cardholders"]
    chips = " ".join(f'<span class="entity-chip" style="background:#d1fae5;color:#065f46">{s}</span>' for s in sources)
    st.markdown(chips, unsafe_allow_html=True)

# ── Sidebar: example queries ──────────────────────────────────────────────────
EXAMPLE_QUERIES = [
    ("🕸️ Fraud rings", "Which merchants are connected to fraud rings and what cardholders are affected?"),
    ("⚖️ BSA violations", "Which cardholders have transactions that violate BSA reporting thresholds?"),
    ("🔗 Multi-hop", "Find all entities connected to cardholder CH_0005 — merchants, fraud cases, and compliance violations"),
    ("🌍 Cross-border", "What compliance rules apply to cross-border transactions involving sanctioned countries?"),
    ("📋 Case connections", "What fraud cases are connected to merchant fraud rings?"),
    ("🏦 High risk", "Which high-risk merchants are connected to multiple fraud cases?"),
]

with st.sidebar:
    st.markdown("### 🕸️ Example Graph Queries")
    st.markdown(
        "<small>Multi-hop questions that traverse the knowledge graph.</small>",
        unsafe_allow_html=True,
    )
    for label, query in EXAMPLE_QUERIES:
        with st.expander(label, expanded=False):
            st.markdown(f"<small>{query}</small>", unsafe_allow_html=True)
            if st.button("📋 Use", key=f"gq_{label}"):
                st.session_state["graph_query_input"] = query

# ── Step 1: Build the Knowledge Graph ─────────────────────────────────────────
st.markdown("---")
st.markdown("### 🏗️ Step 1: Build the Knowledge Graph")
st.markdown("""
The LLM reads documents from your MongoDB collections and **automatically extracts
entities and relationships** into a knowledge graph stored in the `knowledge_graph` collection.
""")

col_build, col_stats = st.columns([3, 2])

with col_build:
    build_collection = st.selectbox(
        "Source collection:",
        ["fraud_cases", "compliance_rules", "cardholders", "merchant_networks", "transactions"],
        index=0,
    )
    build_max = st.slider("Documents to process:", 3, 20, 5)

    if st.button("🏗️ Build Graph from Collection", type="primary"):
        with st.spinner(f"🤖 Extracting entities from {build_max} docs in `{build_collection}`… (LLM entity extraction)"):
            try:
                from agents.graphrag_agent import build_graph_from_collection
                result = build_graph_from_collection(build_collection, build_max)
                if result.get("error"):
                    st.warning(result["error"])
                else:
                    st.success(f"✅ Processed {result['docs_processed']} documents from `{result['collection']}`")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Build failed: {e}")
                logger.exception("Graph build error: %s", e)

with col_stats:
    st.markdown("**📊 Graph Statistics:**")
    try:
        from agents.graphrag_agent import get_graph_stats
        stats = get_graph_stats()
        st.markdown(f"""
        <div class="graph-stat">
          <div class="big">{stats['entity_count']}</div>
          <div class="lbl">Entities in graph</div>
        </div>
        """, unsafe_allow_html=True)
        if stats.get("sample_entities"):
            with st.expander("📄 Sample Entities"):
                for ent in stats["sample_entities"]:
                    st.json(ent)
    except Exception as e:
        st.info(f"Graph not yet built or unavailable: {e}")

# ── Step 2: Query the Knowledge Graph ─────────────────────────────────────────
st.markdown("---")
st.markdown("### 🔍 Step 2: Query the Knowledge Graph")
st.markdown("""
Ask multi-hop questions — the **MongoDBGraphRAGRetriever** extracts entities from
your question, traverses the graph, and the LLM synthesises an answer from the graph context.
""")

if "graph_query_input" not in st.session_state:
    st.session_state["graph_query_input"] = ""
if "graph_results" not in st.session_state:
    st.session_state["graph_results"] = []

query_input = st.text_area(
    "Ask a multi-hop question about the knowledge graph:",
    value=st.session_state.get("graph_query_input", ""),
    placeholder="e.g. Which merchants are connected to fraud rings and what cardholders are affected?",
    height=80,
    key="graph_query_text",
)

col_run, col_explore, col_clear = st.columns([1, 2, 2])
with col_run:
    run_clicked = st.button("🔍 Query Graph", type="primary")
with col_explore:
    entity_name = st.text_input("Explore entity:", placeholder="e.g. CH_0005, MER_0042")
    explore_clicked = st.button("🕸️ Find Related")
with col_clear:
    if st.button("🗑️ Clear History"):
        st.session_state["graph_results"] = []
        st.session_state["graph_query_input"] = ""
        st.rerun()

if run_clicked and query_input.strip():
    with st.spinner("🤖 Extracting entities → traversing graph → synthesising answer…"):
        try:
            from agents.graphrag_agent import query_graph
            result = query_graph(query_input.strip())
            st.session_state["graph_results"].insert(0, {
                "type": "query",
                "question": query_input.strip(),
                "answer": result.get("answer", ""),
                "retrieved_docs": result.get("retrieved_docs", []),
                "entities_found": result.get("entities_found", []),
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            })
            st.session_state["graph_query_input"] = ""
            st.rerun()
        except Exception as e:
            st.error(f"❌ Query failed: {e}")
            logger.exception("Graph query error: %s", e)

if explore_clicked and entity_name.strip():
    with st.spinner(f"🕸️ Traversing graph from '{entity_name.strip()}'…"):
        try:
            from agents.graphrag_agent import get_related_entities
            result = get_related_entities(entity_name.strip())
            st.session_state["graph_results"].insert(0, {
                "type": "explore",
                "entity": entity_name.strip(),
                "related": result.get("related", []),
                "count": result.get("count", 0),
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            })
            st.rerun()
        except Exception as e:
            st.error(f"❌ Explore failed: {e}")

# ── Results ───────────────────────────────────────────────────────────────────
if st.session_state["graph_results"]:
    for i, r in enumerate(st.session_state["graph_results"][:10]):
        ts = r.get("timestamp", "?")
        if r["type"] == "query":
            q = r.get("question", "?")
            entities = r.get("entities_found", [])
            entity_chips = " ".join(f'<span class="entity-chip">{e}</span>' for e in entities) if entities else "none"
            with st.expander(f"⏰ {ts} — 🔍 **{q[:80]}**", expanded=(i == 0)):
                st.markdown(f"**Entities extracted:** {entity_chips}", unsafe_allow_html=True)
                st.markdown(f'<div class="answer-box">{r.get("answer", "")}</div>', unsafe_allow_html=True)
                docs = r.get("retrieved_docs", [])
                if docs:
                    with st.expander(f"📄 Retrieved Graph Context ({len(docs)} docs)"):
                        for doc in docs:
                            st.code(doc[:500])
        elif r["type"] == "explore":
            ent = r.get("entity", "?")
            count = r.get("count", 0)
            with st.expander(f"⏰ {ts} — 🕸️ **{ent}** → {count} related entities", expanded=(i == 0)):
                related = r.get("related", [])
                if related:
                    for rel in related[:20]:
                        st.json(rel)
                else:
                    st.info("No related entities found. Build the graph first.")

# ── Architecture ──────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("🏗️ Architecture — GraphRAG Pipeline"):
    st.markdown("""
```
                        BUILD PHASE
                        ──────────
MongoDB Collection (fraud_cases, compliance_rules, …)
    │
    ▼
MongoDBGraphStore.add_documents(docs)
    │
    ▼
LLM Entity Extraction (Azure GPT-4o)
    │  extracts: entities, types, relationships
    ▼
knowledge_graph collection (MongoDB)
    ┌──────────────────────────────────────────┐
    │ { _id: "CH_0005",                        │
    │   type: "Cardholder",                    │
    │   relationships: {                       │
    │     target_ids: ["MER_0042", "FC_001"],  │
    │     types: ["HAS_TRANSACTION", "FLAGGED"]│
    │   }                                      │
    │ }                                        │
    └──────────────────────────────────────────┘

                        QUERY PHASE
                        ──────────
User Question (natural language)
    │
    ▼
MongoDBGraphRAGRetriever.invoke(question)
    │
    ├─ 1. extract_entity_names(question)  → ["CH_0005", "MER_0042"]
    │
    ├─ 2. related_entities(each_name)     → $graphLookup traversal
    │                                        (max_depth=3)
    │
    ├─ 3. Gather context from connected entities
    │
    ▼
graph_store.chat_response(question)
    │  LLM synthesises answer from graph context
    ▼
Final Answer (multi-hop, relationship-aware)
```

**Key MongoDB features used:**
- `knowledge_graph` collection: entities stored as documents with embedded relationship arrays
- `$graphLookup`: recursive traversal for multi-hop entity discovery
- LLM entity extraction: no manual schema definition needed
- Compatible with Atlas Vector Search for hybrid graph + semantic queries

**Python setup:**
```python
from langchain_mongodb.graphrag.graph import MongoDBGraphStore
from langchain_mongodb.retrievers.graphrag import MongoDBGraphRAGRetriever

graph_store = MongoDBGraphStore.from_connection_string(
    MONGODB_URI, database_name=DB_NAME,
    collection_name="knowledge_graph",
    entity_extraction_model=llm,
    allowed_entity_types=[...],
    allowed_relationship_types=[...],
)

# Build: graph_store.add_documents(docs)
# Query: retriever = MongoDBGraphRAGRetriever(graph_store=graph_store)
#         docs = retriever.invoke("multi-hop question")
```
""")

st.markdown("---")
st.caption("Powered by [langchain-mongodb](https://github.com/langchain-ai/langchain-mongodb) · MongoDBGraphStore · GraphRAGRetriever")