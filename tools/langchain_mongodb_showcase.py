"""
langchain-mongodb Integration Showcase

Live demos for every module in the langchain-mongodb package.
Each function is self-contained and returns a result dict for the Streamlit page.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT,
    MONGODB_URI,
    MONGODB_DB_NAME,
)

logger = logging.getLogger(__name__)


def _get_llm():
    from langchain_openai import AzureChatOpenAI
    return AzureChatOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_deployment=AZURE_OPENAI_DEPLOYMENT,
        temperature=0,
    )


def _get_embeddings():
    from langchain_voyageai import VoyageAIEmbeddings
    import os
    return VoyageAIEmbeddings(
        model="voyage-finance-2",
        voyage_api_key=os.environ.get("VOYAGE_API_KEY", ""),
    )


# ── 1. MongoDBAtlasVectorSearch ──────────────────────────────────────────────

def demo_vector_search(query: str = "high cashback dining offers", collection: str = "offers",
                       index_name: str = "offers_vector_index", k: int = 3) -> dict:
    """Atlas Vector Search via MongoDBAtlasVectorSearch class."""
    from langchain_mongodb import MongoDBAtlasVectorSearch
    from pymongo import MongoClient

    client = MongoClient(MONGODB_URI)
    coll = client[MONGODB_DB_NAME][collection]
    embeddings = _get_embeddings()

    vs = MongoDBAtlasVectorSearch(
        collection=coll,
        embedding=embeddings,
        index_name=index_name,
        text_key="description" if collection == "offers" else "text",
        embedding_key="embedding",
    )

    t0 = time.time()
    docs = vs.similarity_search(query, k=k)
    elapsed = time.time() - t0
    client.close()

    return {
        "class": "MongoDBAtlasVectorSearch",
        "query": query,
        "results": [{"content": d.page_content[:300], "metadata": d.metadata} for d in docs],
        "count": len(docs),
        "elapsed_ms": round(elapsed * 1000),
    }


# ── 2. FullTextSearchRetriever ───────────────────────────────────────────────

def demo_fulltext_search(query: str = "BSA currency transaction reporting",
                         collection: str = "compliance_rules", k: int = 3) -> dict:
    """Atlas Full-Text Search via MongoDBAtlasFullTextSearchRetriever."""
    from langchain_mongodb.retrievers import MongoDBAtlasFullTextSearchRetriever
    from pymongo import MongoClient

    client = MongoClient(MONGODB_URI)
    coll = client[MONGODB_DB_NAME][collection]

    retriever = MongoDBAtlasFullTextSearchRetriever(
        collection=coll,
        search_index_name="default",
        search_field="rule_text" if collection == "compliance_rules" else "description",
        top_k=k,
    )

    t0 = time.time()
    docs = retriever.invoke(query)
    elapsed = time.time() - t0
    client.close()

    return {
        "class": "MongoDBAtlasFullTextSearchRetriever",
        "query": query,
        "results": [{"content": d.page_content[:300], "metadata": d.metadata} for d in docs],
        "count": len(docs),
        "elapsed_ms": round(elapsed * 1000),
    }


# ── 3. HybridSearchRetriever ────────────────────────────────────────────────

def demo_hybrid_search(query: str = "rewards points for travel purchases",
                       collection: str = "offers", k: int = 3) -> dict:
    """Hybrid (vector + full-text) via MongoDBAtlasHybridSearchRetriever."""
    from langchain_mongodb.retrievers import MongoDBAtlasHybridSearchRetriever
    from pymongo import MongoClient

    client = MongoClient(MONGODB_URI)
    coll = client[MONGODB_DB_NAME][collection]
    embeddings = _get_embeddings()

    retriever = MongoDBAtlasHybridSearchRetriever(
        collection=coll,
        embedding=embeddings,
        vector_search_index="offers_vector_index",
        search_index_name="default",
        text_key="description",
        embedding_key="embedding",
        top_k=k,
    )

    t0 = time.time()
    docs = retriever.invoke(query)
    elapsed = time.time() - t0
    client.close()

    return {
        "class": "MongoDBAtlasHybridSearchRetriever",
        "query": query,
        "results": [{"content": d.page_content[:300], "metadata": d.metadata} for d in docs],
        "count": len(docs),
        "elapsed_ms": round(elapsed * 1000),
    }



# ── 4. MongoDBChatMessageHistory ─────────────────────────────────────────────

def demo_chat_history(session_id: str = "demo-session") -> dict:
    """Store and retrieve chat messages via MongoDBChatMessageHistory."""
    from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory

    history = MongoDBChatMessageHistory(
        connection_string=MONGODB_URI,
        database_name=MONGODB_DB_NAME,
        collection_name="langchain_chat_history",
        session_id=session_id,
    )

    # Add demo messages
    history.add_user_message(f"What are my best cashback offers? (demo at {datetime.now(timezone.utc).isoformat()})")
    history.add_ai_message("Based on your Platinum tier, I found 3 cashback offers: ...")

    messages = history.messages
    return {
        "class": "MongoDBChatMessageHistory",
        "session_id": session_id,
        "message_count": len(messages),
        "messages": [{"type": m.type, "content": m.content[:200]} for m in messages[-4:]],
    }


# ── 5. MongoDBCache (exact match) ───────────────────────────────────────────

def demo_cache() -> dict:
    """LLM response cache via MongoDBCache (exact string match)."""
    from langchain_mongodb.cache import MongoDBCache
    from langchain_core.globals import set_llm_cache

    cache = MongoDBCache(
        connection_string=MONGODB_URI,
        database_name=MONGODB_DB_NAME,
        collection_name="langchain_cache",
    )
    set_llm_cache(cache)

    llm = _get_llm()
    prompt = "What is MongoDB Atlas Vector Search in one sentence?"

    # First call — cache miss
    t0 = time.time()
    r1 = llm.invoke(prompt)
    t_miss = time.time() - t0

    # Second call — cache hit
    t0 = time.time()
    r2 = llm.invoke(prompt)
    t_hit = time.time() - t0

    set_llm_cache(None)  # Reset global cache

    return {
        "class": "MongoDBCache",
        "prompt": prompt,
        "answer": r1.content[:300],
        "cache_miss_ms": round(t_miss * 1000),
        "cache_hit_ms": round(t_hit * 1000),
        "speedup": f"{t_miss / max(t_hit, 0.001):.1f}x",
    }


# ── 6. MongoDBAtlasSemanticCache ─────────────────────────────────────────────

def demo_semantic_cache() -> dict:
    """Semantic LLM cache — matches by meaning, not exact string."""
    from langchain_mongodb.cache import MongoDBAtlasSemanticCache
    from langchain_core.globals import set_llm_cache

    embeddings = _get_embeddings()
    cache = MongoDBAtlasSemanticCache(
        connection_string=MONGODB_URI,
        database_name=MONGODB_DB_NAME,
        collection_name="langchain_semantic_cache",
        embedding=embeddings,
        score_threshold=0.95,
    )
    set_llm_cache(cache)
    llm = _get_llm()

    prompt1 = "Explain MongoDB change streams"
    t0 = time.time()
    r1 = llm.invoke(prompt1)
    t1 = time.time() - t0

    # Semantically similar but different wording
    prompt2 = "What are change streams in MongoDB?"
    t0 = time.time()
    r2 = llm.invoke(prompt2)
    t2 = time.time() - t0

    set_llm_cache(None)
    return {
        "class": "MongoDBAtlasSemanticCache",
        "prompt_1": prompt1,
        "prompt_2_similar": prompt2,
        "answer": r1.content[:300],
        "first_call_ms": round(t1 * 1000),
        "semantic_hit_ms": round(t2 * 1000),
        "same_answer": r1.content[:100] == r2.content[:100],
    }


# ── 7. MongoDBGraphStore ─────────────────────────────────────────────────────

def demo_graph_store(text: str = "Cardholder CH_0005 is a Platinum member in London. "
                     "They transacted with Merchant MER_0042 which has high fraud risk. "
                     "MER_0042 is connected to MER_0043 via same ownership.") -> dict:
    """Build a knowledge graph from text via MongoDBGraphStore."""
    from langchain_mongodb.graphrag.graph import MongoDBGraphStore
    from langchain_core.documents import Document

    graph_store = MongoDBGraphStore.from_connection_string(
        connection_string=MONGODB_URI,
        database_name=MONGODB_DB_NAME,
        collection_name="langchain_graph_demo",
        entity_extraction_model=_get_llm(),
    )

    doc = Document(page_content=text, metadata={"source": "demo"})
    t0 = time.time()
    graph_store.add_documents([doc])
    elapsed = time.time() - t0

    # Query the graph
    entities = graph_store.extract_entity_names(text)
    related = []
    for ent in entities[:2]:
        try:
            r = graph_store.related_entities(ent)
            related.extend(r)
        except Exception:
            pass

    return {
        "class": "MongoDBGraphStore",
        "input_text": text[:200],
        "entities_extracted": entities,
        "related_entities": related[:10],
        "build_ms": round(elapsed * 1000),
    }


# ── 8. MongoDBLoader ────────────────────────────────────────────────────────

def demo_loader(collection: str = "compliance_rules", max_docs: int = 3) -> dict:
    """Load MongoDB docs as LangChain Documents via MongoDBLoader."""
    from langchain_mongodb.loaders import MongoDBLoader

    loader = MongoDBLoader(
        connection_string=MONGODB_URI,
        db_name=MONGODB_DB_NAME,
        collection_name=collection,
        filter_criteria={},
        field_names=None,  # load all fields
    )

    t0 = time.time()
    docs = loader.load()
    elapsed = time.time() - t0

    return {
        "class": "MongoDBLoader",
        "collection": collection,
        "total_loaded": len(docs),
        "sample_docs": [{"content": d.page_content[:300], "metadata": d.metadata} for d in docs[:max_docs]],
        "elapsed_ms": round(elapsed * 1000),
    }


# ── 9. MongoDBRecordManager ─────────────────────────────────────────────────

def demo_record_manager() -> dict:
    """Track document indexing to prevent duplicates via MongoDBRecordManager."""
    from langchain_mongodb.indexes import MongoDBRecordManager

    rm = MongoDBRecordManager(
        namespace="vaultiq_demo",
        connection_string=MONGODB_URI,
        db_name=MONGODB_DB_NAME,
        collection_name="langchain_record_manager",
    )
    rm.create_schema()

    t0 = time.time()
    # Record some keys
    keys = ["doc_001", "doc_002", "doc_003"]
    rm.update(keys, group_ids=["batch_1"] * 3)

    # Check if exists
    exists = rm.exists(keys)
    elapsed = time.time() - t0

    return {
        "class": "MongoDBRecordManager",
        "namespace": "vaultiq_demo",
        "keys_registered": keys,
        "exists_check": exists,
        "elapsed_ms": round(elapsed * 1000),
    }


# ── 10. MongoDBDatabaseToolkit ───────────────────────────────────────────────

def demo_toolkit() -> dict:
    """List all tools provided by MongoDBDatabaseToolkit."""
    from langchain_mongodb.agent_toolkit import MongoDBDatabaseToolkit, MongoDBDatabase

    db = MongoDBDatabase.from_connection_string(MONGODB_URI, database=MONGODB_DB_NAME)
    toolkit = MongoDBDatabaseToolkit(db=db, llm=_get_llm())
    tools = toolkit.get_tools()

    return {
        "class": "MongoDBDatabaseToolkit",
        "tool_count": len(tools),
        "tools": [{"name": t.name, "description": t.description[:150]} for t in tools],
    }