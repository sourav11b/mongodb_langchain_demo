"""
Page 8: langchain-mongodb Integration Showcase

One page showcasing every module in the langchain-mongodb package:
  1. MongoDBAtlasVectorSearch       — semantic similarity retrieval
  2. FullTextSearchRetriever        — Atlas full-text (BM25-style)
  3. HybridSearchRetriever          — vector + text combined
  4. MongoDBChatMessageHistory      — persistent conversation memory
  5. MongoDBCache                   — exact-match LLM response cache
  6. MongoDBAtlasSemanticCache      — meaning-based LLM cache
  7. MongoDBGraphStore              — knowledge graph from unstructured text
  8. MongoDBLoader                  — load MongoDB docs into LangChain
  9. MongoDBRecordManager           — deduplicate document ingestion
  10. MongoDBDatabaseToolkit        — Text-to-MQL agent toolkit
"""

import streamlit as st
import sys, os, json, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger("vaultiq.page.langchain_mongodb")
st.set_page_config(page_title="langchain-mongodb | VaultIQ", page_icon="🍃", layout="wide")

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
  .page-header { background:linear-gradient(135deg,#00684A,#00ED64);
    padding:1.5rem 2rem; border-radius:10px; margin-bottom:1rem; }
  .page-header h2 { color:white; margin:0; }
  .page-header p  { color:rgba(255,255,255,.92); margin:.3rem 0 0; }
  .feat-tag { display:inline-block; padding:.18rem .65rem; border-radius:20px;
    font-size:.73rem; font-weight:700; margin:.15rem; border:1.5px solid; }
  .ft-green  { background:#d1fae5; color:#065f46; border-color:#6ee7b7; }
  .ft-blue   { background:#dbeafe; color:#1d4ed8; border-color:#93c5fd; }
  .ft-purple { background:#ede9fe; color:#5b21b6; border-color:#c4b5fd; }
  .ft-yellow { background:#fef3c7; color:#92400e; border-color:#fcd34d; }
  .ft-red    { background:#fee2e2; color:#991b1b; border-color:#fca5a5; }
  .demo-box  { background:#f0fdf4; border:2px solid #86efac; border-radius:10px;
    padding:1rem; margin:.5rem 0; }
  .code-snippet { background:#1e293b; color:#e2e8f0; padding:.8rem 1rem;
    border-radius:6px; font-size:.78rem; font-family:monospace; overflow-x:auto; }
  .metric-card { background:#f8fafc; border:2px solid #e2e8f0; border-radius:10px;
    padding:.6rem 1rem; text-align:center; }
  .metric-card .big { font-size:1.5rem; font-weight:800; color:#065f46; }
  .metric-card .lbl { font-size:.78rem; color:#666; }
  .section-num { background:#00684A; color:white; border-radius:50%; width:28px;
    height:28px; display:inline-flex; align-items:center; justify-content:center;
    font-weight:800; font-size:.85rem; margin-right:.5rem; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
  <h2>🍃 langchain-mongodb Integration Showcase</h2>
  <p>Live demos of every module in the <code style="color:#fcd34d">langchain-mongodb</code>
     package — 10 features, all running against your MongoDB Atlas cluster</p>
  <p style="margin-top:.6rem">
    <span class="feat-tag ft-green">🍃 langchain-mongodb v0.11+</span>
    <span class="feat-tag ft-blue">🔵 Atlas Vector Search</span>
    <span class="feat-tag ft-purple">🕸️ GraphRAG</span>
    <span class="feat-tag ft-yellow">🟡 Text-to-MQL</span>
    <span class="feat-tag ft-red">🔴 LangSmith</span>
  </p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
**`langchain-mongodb`** is the official LangChain integration for MongoDB Atlas.
This page demonstrates **every module** with a live, runnable demo against the VaultIQ database.
Click any **▶️ Run Demo** button to see the module in action.
""")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: MongoDBAtlasVectorSearch
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<span class="section-num">1</span> **MongoDBAtlasVectorSearch** — Semantic Similarity Retrieval', unsafe_allow_html=True)
col1a, col1b = st.columns([3, 2])
with col1a:
    st.markdown("""
Wraps Atlas Vector Search as a LangChain `VectorStore`. Embed your query with
Voyage AI, then find the most semantically similar documents via HNSW index.
Supports **pre-filtering** — narrow the ANN candidate set inside the index.
""")
    vs_query = st.text_input("Query:", value="high cashback dining offers", key="vs_q")
    if st.button("▶️ Run Demo", key="run_vs"):
        with st.spinner("Running vector search…"):
            from tools.langchain_mongodb_showcase import demo_vector_search
            r = demo_vector_search(vs_query)
            st.markdown(f'<div class="demo-box">Found <strong>{r["count"]}</strong> results in <strong>{r["elapsed_ms"]}ms</strong></div>', unsafe_allow_html=True)
            for i, doc in enumerate(r["results"]):
                score_str = f"**Score: `{doc['score']}`**" if doc.get("score") is not None else ""
                with st.expander(f"Result {i+1} {score_str} — {doc['content'][:80]}…", expanded=(i == 0)):
                    st.markdown(doc["content"])
                    st.json(doc.get("metadata", {}))
with col1b:
    st.markdown("""<div class="code-snippet">
from langchain_mongodb import MongoDBAtlasVectorSearch<br><br>
vs = MongoDBAtlasVectorSearch(<br>
&nbsp;&nbsp;collection=coll,<br>
&nbsp;&nbsp;embedding=VoyageAIEmbeddings("voyage-finance-2"),<br>
&nbsp;&nbsp;index_name="offers_vector_index",<br>
)<br>
docs = vs.similarity_search("cashback dining", k=3)
</div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: FullTextSearchRetriever
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<span class="section-num">2</span> **MongoDBAtlasFullTextSearchRetriever** — Atlas Full-Text Search', unsafe_allow_html=True)
col2a, col2b = st.columns([3, 2])
with col2a:
    st.markdown("Keyword-based retrieval using Atlas Search (Lucene). Best for exact terms, keyword matching, and structured queries.")
    fts_query = st.text_input("Query:", value="3x points dining cashback", key="fts_q")
    if st.button("▶️ Run Demo", key="run_fts"):
        with st.spinner("Running full-text search…"):
            from tools.langchain_mongodb_showcase import demo_fulltext_search
            r = demo_fulltext_search(fts_query)
            st.markdown(f'<div class="demo-box">Found <strong>{r["count"]}</strong> results in <strong>{r["elapsed_ms"]}ms</strong> · Index: <code>{r.get("index_used","")}</code></div>', unsafe_allow_html=True)
            for i, doc in enumerate(r["results"]):
                score_str = f"**Score: `{doc['score']}`**" if doc.get("score") is not None else ""
                with st.expander(f"Result {i+1} {score_str} — {doc['content'][:80]}…", expanded=(i == 0)):
                    st.markdown(doc["content"])
                    st.json(doc.get("metadata", {}))
with col2b:
    st.markdown("""<div class="code-snippet">
from langchain_mongodb.retrievers import \\<br>
&nbsp;&nbsp;MongoDBAtlasFullTextSearchRetriever<br><br>
retriever = MongoDBAtlasFullTextSearchRetriever(<br>
&nbsp;&nbsp;collection=coll,<br>
&nbsp;&nbsp;search_field="rule_text",<br>
)<br>
docs = retriever.invoke("BSA reporting")
</div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: HybridSearchRetriever
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<span class="section-num">3</span> **MongoDBAtlasHybridSearchRetriever** — Vector + Text Combined', unsafe_allow_html=True)
col3a, col3b = st.columns([3, 2])
with col3a:
    st.markdown("Combines semantic vector search with keyword full-text search using **reciprocal rank fusion**.")
    hy_query = st.text_input("Query:", value="rewards points for travel purchases", key="hy_q")
    if st.button("▶️ Run Demo", key="run_hy"):
        with st.spinner("Running hybrid search…"):
            from tools.langchain_mongodb_showcase import demo_hybrid_search
            r = demo_hybrid_search(hy_query)
            st.markdown(f'<div class="demo-box">Found <strong>{r["count"]}</strong> results in <strong>{r["elapsed_ms"]}ms</strong> · Method: reciprocal rank fusion</div>', unsafe_allow_html=True)
            for i, doc in enumerate(r["results"]):
                score_str = f"**Score: `{doc['score']}`**" if doc.get("score") is not None else ""
                with st.expander(f"Result {i+1} {score_str} — {doc['content'][:80]}…", expanded=(i == 0)):
                    st.markdown(doc["content"])
                    st.json(doc.get("metadata", {}))
with col3b:
    st.markdown("""<div class="code-snippet">
from langchain_mongodb.retrievers import \\<br>
&nbsp;&nbsp;MongoDBAtlasHybridSearchRetriever<br><br>
retriever = MongoDBAtlasHybridSearchRetriever(<br>
&nbsp;&nbsp;collection=coll, embedding=embeddings,<br>
&nbsp;&nbsp;vector_search_index="offers_vector_index",<br>
)<br>
docs = retriever.invoke("travel rewards")
</div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: MongoDBChatMessageHistory
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<span class="section-num">4</span> **MongoDBChatMessageHistory** — Persistent Conversation Memory', unsafe_allow_html=True)
col4a, col4b = st.columns([3, 2])
with col4a:
    st.markdown("Store and retrieve multi-turn conversations directly in MongoDB. Supports session isolation and history management.")
    hist_session = st.text_input("Session ID:", value="demo-session", key="hist_s")
    if st.button("▶️ Run Demo", key="run_hist"):
        with st.spinner("Storing and retrieving messages…"):
            from tools.langchain_mongodb_showcase import demo_chat_history
            r = demo_chat_history(hist_session)
            st.markdown(f'<div class="demo-box"><strong>{r["message_count"]}</strong> messages in session <code>{r["session_id"]}</code></div>', unsafe_allow_html=True)
            for m in r["messages"]:
                icon = "👤" if m["type"] == "human" else "🤖"
                st.markdown(f"{icon} **{m['type']}:** {m['content'][:150]}")
with col4b:
    st.markdown("""<div class="code-snippet">
from langchain_mongodb.chat_message_histories \\<br>
&nbsp;&nbsp;import MongoDBChatMessageHistory<br><br>
history = MongoDBChatMessageHistory(<br>
&nbsp;&nbsp;connection_string=MONGODB_URI,<br>
&nbsp;&nbsp;database_name=DB_NAME,<br>
&nbsp;&nbsp;collection_name="chat_history",<br>
&nbsp;&nbsp;session_id="user-123",<br>
)<br>
history.add_user_message("Hello")<br>
msgs = history.messages
</div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: MongoDBCache
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<span class="section-num">5</span> **MongoDBCache** — Exact-Match LLM Response Cache', unsafe_allow_html=True)
col5a, col5b = st.columns([3, 2])
with col5a:
    st.markdown("""
Cache LLM responses in MongoDB. If the same prompt is sent twice, the cached response
is returned instantly — **no LLM call needed**. Reduces latency and API costs.
""")
    if st.button("▶️ Run Demo (sends 2 LLM calls)", key="run_cache"):
        with st.spinner("First call (cache miss) → second call (cache hit)…"):
            from tools.langchain_mongodb_showcase import demo_cache
            r = demo_cache()
            c1, c2, c3 = st.columns(3)
            c1.markdown(f'<div class="metric-card"><div class="big">{r["cache_miss_ms"]}ms</div><div class="lbl">Cache MISS</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-card"><div class="big">{r["cache_hit_ms"]}ms</div><div class="lbl">Cache HIT</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-card"><div class="big">{r["speedup"]}</div><div class="lbl">Speedup</div></div>', unsafe_allow_html=True)
            st.markdown(f"**Answer:** {r['answer'][:200]}")
with col5b:
    st.markdown("""<div class="code-snippet">
from langchain_mongodb.cache import MongoDBCache<br>
from langchain_core.globals import set_llm_cache<br><br>
cache = MongoDBCache(<br>
&nbsp;&nbsp;connection_string=MONGODB_URI,<br>
&nbsp;&nbsp;database_name=DB_NAME,<br>
&nbsp;&nbsp;collection_name="llm_cache",<br>
)<br>
set_llm_cache(cache)<br>
# Now all llm.invoke() calls are cached!
</div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6: MongoDBAtlasSemanticCache
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<span class="section-num">6</span> **MongoDBAtlasSemanticCache** — Meaning-Based LLM Cache', unsafe_allow_html=True)
col6a, col6b = st.columns([3, 2])
with col6a:
    st.markdown("""
Like MongoDBCache but matches by **semantic similarity**, not exact string.
"Explain MongoDB change streams" and "What are change streams in MongoDB?"
return the same cached answer — even though the words are different.
""")
    if st.button("▶️ Run Demo (sends 2 different prompts)", key="run_sem_cache"):
        with st.spinner("Prompt 1 (miss) → Prompt 2 (semantic hit)…"):
            from tools.langchain_mongodb_showcase import demo_semantic_cache
            r = demo_semantic_cache()
            st.markdown(f"**Prompt 1:** `{r['prompt_1']}`")
            st.markdown(f"**Prompt 2 (similar):** `{r['prompt_2_similar']}`")
            c1, c2 = st.columns(2)
            c1.markdown(f'<div class="metric-card"><div class="big">{r["first_call_ms"]}ms</div><div class="lbl">First call</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-card"><div class="big">{r["semantic_hit_ms"]}ms</div><div class="lbl">Semantic hit</div></div>', unsafe_allow_html=True)
            st.markdown(f"**Same answer returned:** {r['same_answer']}")
with col6b:
    st.markdown("""<div class="code-snippet">
from langchain_mongodb.cache import \\<br>
&nbsp;&nbsp;MongoDBAtlasSemanticCache<br><br>
cache = MongoDBAtlasSemanticCache(<br>
&nbsp;&nbsp;connection_string=MONGODB_URI,<br>
&nbsp;&nbsp;embedding=embeddings,<br>
&nbsp;&nbsp;score_threshold=0.95,<br>
)<br>
set_llm_cache(cache)<br>
# "Explain X" and "What is X?" → same cache hit
</div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7: MongoDBGraphStore + GraphRAGRetriever
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<span class="section-num">7</span> **MongoDBGraphStore + GraphRAGRetriever** — Knowledge Graph from Text', unsafe_allow_html=True)
col7a, col7b = st.columns([3, 2])
with col7a:
    st.markdown("""
Build a knowledge graph automatically from text. The LLM extracts entities
(Cardholder, Merchant, FraudCase) and relationships (HAS_TRANSACTION, FRAUD_RING_WITH),
then stores them as MongoDB documents. Query via graph traversal.
""")
    GRAPH_SAMPLES = [
        "Cardholder CH_0005 is a Platinum member in London. They transacted with Merchant MER_0042 which has high fraud risk. MER_0042 is connected to MER_0043 via same ownership.",
        "Fraud case FC_012 involves card-not-present fraud. Cardholder CH_0022 reported unauthorized transactions at MER_0088 and MER_0091. Investigation revealed both merchants share owner John Smith.",
        "BSA rule requires reporting transactions over $10,000. Cardholder CH_0010 made 5 transactions of $9,500 each at MER_0055 within 24 hours, triggering structuring alert SA-2025-0042.",
    ]
    graph_sample = st.selectbox("Sample texts:", GRAPH_SAMPLES, key="graph_sample")
    graph_text = st.text_area("Input text:", value=graph_sample, height=80, key="graph_t")
    if st.button("▶️ Run Demo", key="run_graph"):
        with st.spinner("LLM extracting entities → building graph…"):
            from tools.langchain_mongodb_showcase import demo_graph_store
            r = demo_graph_store(graph_text)
            graph_total = r.get("entity_count_in_graph", "?")
            st.markdown(f'<div class="demo-box">Extracted <strong>{len(r["entities_extracted"])}</strong> entities in <strong>{r["build_ms"]}ms</strong> · Total in graph: <strong>{graph_total}</strong></div>', unsafe_allow_html=True)
            ent_chips = " ".join(f'<span class="feat-tag ft-purple">{e}</span>' for e in r["entities_extracted"])
            st.markdown(f"**Entities extracted by LLM:** {ent_chips}", unsafe_allow_html=True)
            if r["related_entities"]:
                st.markdown(f"**🔗 Graph traversal — {len(r['related_entities'])} related entities found:**")
                for i, rel in enumerate(r["related_entities"][:8]):
                    label = rel.get("_id", rel) if isinstance(rel, dict) else str(rel)
                    with st.expander(f"🔗 {label}", expanded=(i < 3)):
                        if isinstance(rel, dict):
                            st.json(rel)
                        else:
                            st.text(str(rel))
            else:
                st.info("Entities stored in graph. Run the demo again — the graph needs 2+ runs to build connections between entities.")
with col7b:
    st.markdown("""<div class="code-snippet">
from langchain_mongodb.graphrag.graph \\<br>
&nbsp;&nbsp;import MongoDBGraphStore<br>
from langchain_mongodb.retrievers.graphrag \\<br>
&nbsp;&nbsp;import MongoDBGraphRAGRetriever<br><br>
graph = MongoDBGraphStore.from_connection_string(<br>
&nbsp;&nbsp;MONGODB_URI, database_name=DB_NAME,<br>
&nbsp;&nbsp;entity_extraction_model=llm,<br>
)<br>
graph.add_documents(docs)<br>
retriever = MongoDBGraphRAGRetriever(<br>
&nbsp;&nbsp;graph_store=graph)<br>
docs = retriever.invoke("multi-hop question")
</div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8: MongoDBLoader
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<span class="section-num">8</span> **MongoDBLoader** — Load MongoDB Docs into LangChain', unsafe_allow_html=True)
col8a, col8b = st.columns([3, 2])
with col8a:
    st.markdown("Import MongoDB documents as LangChain `Document` objects for use in chains, retrievers, or embeddings.")
    load_coll = st.selectbox("Collection:", ["compliance_rules", "fraud_cases", "cardholders", "offers", "merchants"], key="load_c")
    if st.button("▶️ Run Demo", key="run_load"):
        with st.spinner("Loading documents…"):
            from tools.langchain_mongodb_showcase import demo_loader
            r = demo_loader(load_coll)
            st.markdown(f'<div class="demo-box">Loaded <strong>{r["total_loaded"]}</strong> documents from <code>{r["collection"]}</code> in <strong>{r["elapsed_ms"]}ms</strong></div>', unsafe_allow_html=True)
            for doc in r["sample_docs"][:3]:
                with st.expander(f"Document (keys: {list(doc['metadata'].keys())[:4]})"):
                    st.text(doc["content"][:400])
with col8b:
    st.markdown("""<div class="code-snippet">
from langchain_mongodb.loaders import MongoDBLoader<br>
from pymongo import MongoClient<br><br>
client = MongoClient(MONGODB_URI)<br>
coll = client[DB_NAME]["compliance_rules"]<br><br>
loader = MongoDBLoader(collection=coll)<br>
docs = loader.load()<br>
# docs[0].page_content → document text<br>
# docs[0].metadata → MongoDB fields
</div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9: MongoDBRecordManager
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<span class="section-num">9</span> **MongoDBRecordManager** — Deduplicate Document Ingestion', unsafe_allow_html=True)
col9a, col9b = st.columns([3, 2])
with col9a:
    st.markdown("""
Track which documents have been indexed to **prevent duplicates** during re-ingestion.
Essential for production RAG pipelines where data sources are refreshed periodically.
""")
    if st.button("▶️ Run Demo", key="run_rm"):
        with st.spinner("Registering and checking records…"):
            from tools.langchain_mongodb_showcase import demo_record_manager
            r = demo_record_manager()
            st.markdown(f'<div class="demo-box">Registered <strong>{len(r["keys_registered"])}</strong> keys in <strong>{r["elapsed_ms"]}ms</strong></div>', unsafe_allow_html=True)
            st.markdown(f"**Keys:** `{r['keys_registered']}`")
            st.markdown(f"**Exists check:** `{r['exists_check']}`")
with col9b:
    st.markdown("""<div class="code-snippet">
from langchain_mongodb.indexes import \\<br>
&nbsp;&nbsp;MongoDBRecordManager<br>
from pymongo import MongoClient<br><br>
coll = MongoClient(URI)[DB]["record_mgr"]<br>
rm = MongoDBRecordManager(collection=coll)<br>
rm.create_schema()<br>
rm.update(["doc_1", "doc_2"])<br>
rm.exists(["doc_1"]) → [True]
</div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 10: MongoDBDatabaseToolkit
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<span class="section-num">10</span> **MongoDBDatabaseToolkit** — Text-to-MQL Agent Toolkit', unsafe_allow_html=True)
col10a, col10b = st.columns([3, 2])
with col10a:
    st.markdown("""
A complete toolkit for building LLM agents that query MongoDB using natural language.
Provides tools that auto-discover schemas, generate MQL, validate queries, and execute them.
""")
    SAMPLE_NL_QUERIES = [
        "How many Platinum cardholders are there?",
        "Show me the top 5 merchants by transaction count",
        "Find all fraud cases with severity critical",
        "What compliance rules apply to jurisdiction US-Federal?",
        "List all offers in the Travel category",
        "Count transactions over 5000 dollars",
    ]
    st.markdown("**🟡 Sample Natural-Language Queries:**")
    for i, sq in enumerate(SAMPLE_NL_QUERIES):
        if st.button(f"📋 {sq}", key=f"tk_s_{i}", use_container_width=True):
            st.session_state["tk_query_val"] = sq
    tk_query = st.text_input("Or type your own:", value=st.session_state.get("tk_query_val", ""), key="tk_q")
    c_tools, c_run = st.columns(2)
    with c_tools:
        if st.button("🔧 Show Toolkit Tools", key="run_tk"):
            with st.spinner("Loading toolkit…"):
                from tools.langchain_mongodb_showcase import demo_toolkit
                r = demo_toolkit()
                st.markdown(f'<div class="demo-box"><strong>{r["tool_count"]}</strong> tools</div>', unsafe_allow_html=True)
                for t in r["tools"]:
                    st.markdown(f"- **`{t['name']}`** — {t['description'][:120]}")
    with c_run:
        if st.button("▶️ Run Query via Agent", key="run_tk_query") and tk_query.strip():
            with st.spinner("Agent thinking → generating MQL → executing…"):
                try:
                    from agents.database_agent import run_database_query
                    result = run_database_query(tk_query.strip())
                    answer = result.get("answer", str(result))
                    st.markdown(f'<div class="demo-box">{answer}</div>', unsafe_allow_html=True)
                    tool_calls = result.get("tool_calls", [])
                    if tool_calls:
                        st.markdown("**🔧 Tools used:** " + " → ".join(f"`{t}`" for t in tool_calls))
                except Exception as e:
                    st.error(f"Agent error: {e}")
with col10b:
    st.markdown("""<div class="code-snippet">
from langchain_mongodb.agent_toolkit import \\<br>
&nbsp;&nbsp;MongoDBDatabaseToolkit, MongoDBDatabase<br><br>
db = MongoDBDatabase.from_connection_string(<br>
&nbsp;&nbsp;MONGODB_URI, database=DB_NAME)<br>
toolkit = MongoDBDatabaseToolkit(db=db, llm=llm)<br>
tools = toolkit.get_tools()<br>
# Tools: query_mongodb, info_mongodb,<br>
# list_mongodb, check_query_mongodb<br><br>
agent = create_react_agent(llm, tools)<br>
agent.invoke("How many Platinum members?")
</div>""", unsafe_allow_html=True)

# ── Summary ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 📊 Feature Summary")
st.markdown("""
| # | Module | Category | Used in VaultIQ |
|---|--------|----------|-----------------|
| 1 | `MongoDBAtlasVectorSearch` | Retrieval | Offers, Data Discovery, Compliance |
| 2 | `FullTextSearchRetriever` | Retrieval | Compliance rules search |
| 3 | `HybridSearchRetriever` | Retrieval | Offers (reciprocal rank fusion) |
| 4 | `MongoDBChatMessageHistory` | Memory | All agents (conversation history) |
| 5 | `MongoDBCache` | Caching | LLM response deduplication |
| 6 | `MongoDBAtlasSemanticCache` | Caching | Semantic query deduplication |
| 7 | `MongoDBGraphStore` | Knowledge Graph | Fraud ring detection, entity mapping |
| 8 | `MongoDBLoader` | Data Loading | Seed data ingestion to LangChain |
| 9 | `MongoDBRecordManager` | Data Loading | Prevent duplicate embeddings |
| 10 | `MongoDBDatabaseToolkit` | Agent Toolkit | Natural-language DB queries |
""")

st.caption("All demos run against your live MongoDB Atlas cluster · Powered by [langchain-mongodb](https://github.com/langchain-ai/langchain-mongodb)")