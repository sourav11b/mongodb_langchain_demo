"""
Use Case 6: Knowledge Graph Agent — MongoDBGraphStore + GraphRAG Retriever

Uses MongoDBGraphStore to build a knowledge graph from fraud cases,
compliance rules, and merchant network data. The LLM extracts entities
and relationships, stores them in MongoDB, then answers multi-hop
questions by traversing the graph via $graphLookup.

Architecture:
  Seed docs → LLM entity extraction → MongoDBGraphStore (MongoDB collection)
  User query → entity extraction → $graphLookup traversal → LLM answer
"""

from __future__ import annotations

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_openai import AzureChatOpenAI
from langchain_mongodb.graphrag.graph import MongoDBGraphStore
from langchain_core.documents import Document

from config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT,
    MONGODB_URI,
    MONGODB_DB_NAME,
)

logger = logging.getLogger(__name__)

GRAPH_COLLECTION = "knowledge_graph"

# Entity types and relationships relevant to financial domain
ALLOWED_ENTITY_TYPES = [
    "Cardholder", "Merchant", "Transaction", "FraudCase",
    "ComplianceRule", "Regulation", "Country", "City",
    "CardTier", "MerchantCategory", "FraudType", "RiskLevel",
]

ALLOWED_RELATIONSHIP_TYPES = [
    "HAS_TRANSACTION", "FLAGGED_BY", "INVESTIGATED_IN",
    "VIOLATES", "APPLIES_TO", "LOCATED_IN", "CONNECTED_TO",
    "OWNS", "BELONGS_TO", "HAS_TIER", "OPERATES_IN",
    "SAME_OWNER_AS", "FRAUD_RING_WITH", "REGULATED_BY",
]

ENTITY_EXAMPLES = [
    "Cardholder CH_0001 is a Platinum tier member in New York",
    "Merchant MER_0042 operates in Restaurant category with high risk",
    "Fraud case FC_001 involves card-not-present fraud, severity critical",
    "BSA CTR Reporting rule requires reporting transactions over $10,000",
    "Merchants MER_0042 and MER_0043 share the same owner (fraud ring indicator)",
]


def _get_llm():
    return AzureChatOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_deployment=AZURE_OPENAI_DEPLOYMENT,
        temperature=0,
    )


def get_graph_store() -> MongoDBGraphStore:
    """Create and return a MongoDBGraphStore connected to Atlas."""
    llm = _get_llm()
    return MongoDBGraphStore.from_connection_string(
        connection_string=MONGODB_URI,
        database_name=MONGODB_DB_NAME,
        collection_name=GRAPH_COLLECTION,
        entity_extraction_model=llm,
        allowed_entity_types=ALLOWED_ENTITY_TYPES,
        allowed_relationship_types=ALLOWED_RELATIONSHIP_TYPES,
        entity_examples=ENTITY_EXAMPLES,
    )


def build_graph_from_collection(
    collection_name: str = "fraud_cases",
    max_docs: int = 10,
) -> dict:
    """Build the knowledge graph from existing MongoDB documents.

    Reads documents from the specified collection, converts them to
    LangChain Documents, and feeds them to MongoDBGraphStore which
    uses LLM entity extraction to build the graph.

    Returns: {"docs_processed": int, "collection": str}
    """
    from pymongo import MongoClient

    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGODB_DB_NAME]

    raw_docs = list(db[collection_name].find(
        {}, {"_id": 0, "embedding": 0}
    ).limit(max_docs))
    client.close()

    if not raw_docs:
        return {"docs_processed": 0, "collection": collection_name, "error": "No documents found"}

    # Convert to LangChain Documents
    lc_docs = []
    for doc in raw_docs:
        # Build a text representation of the document
        text_parts = []
        for key, val in doc.items():
            if isinstance(val, (str, int, float, bool)):
                text_parts.append(f"{key}: {val}")
            elif isinstance(val, list) and len(val) <= 5:
                text_parts.append(f"{key}: {val}")
        content = "\n".join(text_parts)
        lc_docs.append(Document(page_content=content, metadata={"source": collection_name}))

    graph_store = get_graph_store()
    graph_store.add_documents(lc_docs)

    logger.info("Built graph from %d docs in %s", len(lc_docs), collection_name)
    return {"docs_processed": len(lc_docs), "collection": collection_name}


def query_graph(question: str) -> dict:
    """Query the knowledge graph using MongoDBGraphRAGRetriever + chat.

    The retriever extracts entities from the question, traverses
    the graph via related_entities, and returns context docs.
    Then chat_response uses LLM to generate an answer from the graph.

    Returns: {"answer": str, "retrieved_docs": list, "entities_found": list}
    """
    from langchain_mongodb.retrievers.graphrag import MongoDBGraphRAGRetriever

    graph_store = get_graph_store()

    # Use the retriever to get graph context
    retriever = MongoDBGraphRAGRetriever(graph_store=graph_store)
    retrieved_docs = retriever.invoke(question)
    retrieved_texts = [doc.page_content for doc in retrieved_docs]

    # Use chat_response for a full LLM-generated answer
    response = graph_store.chat_response(question)
    answer = response.content if hasattr(response, "content") else str(response)

    # Extract entity names that were found
    entity_names = graph_store.extract_entity_names(question)

    return {
        "answer": answer,
        "question": question,
        "retrieved_docs": retrieved_texts,
        "entities_found": entity_names,
    }


def get_related_entities(entity_name: str, max_depth: int = 2) -> dict:
    """Find all entities related to a given entity via graph traversal.

    Uses $graphLookup under the hood to traverse the knowledge graph.

    Returns: {"entity": str, "related": list[dict]}
    """
    graph_store = get_graph_store()
    related = graph_store.related_entities(entity_name, max_depth=max_depth)
    return {
        "entity": entity_name,
        "related": related,
        "count": len(related),
    }


def get_graph_stats() -> dict:
    """Return stats about the knowledge graph collection."""
    from pymongo import MongoClient
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGODB_DB_NAME]
    count = db[GRAPH_COLLECTION].count_documents({})
    sample = list(db[GRAPH_COLLECTION].find({}, {"_id": 0}).limit(5))
    client.close()

    # Count unique entity types
    entity_types = {}
    for doc in sample:
        t = doc.get("type", "unknown")
        entity_types[t] = entity_types.get(t, 0) + 1

    return {
        "entity_count": count,
        "sample_entities": sample,
        "entity_types": entity_types,
    }
