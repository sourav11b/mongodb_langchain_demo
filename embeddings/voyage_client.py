"""
Voyage AI embeddings client — LangChain-compatible wrapper.
Uses voyage-finance-2 (1024-dim) optimised for financial text.

Also provides embed_and_store() to batch-embed MongoDB documents.
"""

from __future__ import annotations
import time
from typing import Any

import voyageai
from pymongo import MongoClient

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import VOYAGE_API_KEY, VOYAGE_MODEL, EMBEDDING_DIMENSION, MONGODB_URI, MONGODB_DB_NAME


# ── Thin LangChain-compatible embeddings wrapper (no langchain-voyageai needed) ─
class VoyageEmbeddings:
    """Minimal LangChain Embeddings-compatible wrapper around voyageai.Client."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model   = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        client = voyageai.Client(api_key=self.api_key)
        result = client.embed(texts, model=self.model, input_type="document")
        return result.embeddings

    def embed_query(self, text: str) -> list[float]:
        client = voyageai.Client(api_key=self.api_key)
        result = client.embed([text], model=self.model, input_type="query")
        return result.embeddings[0]


def get_embeddings() -> VoyageEmbeddings:
    """Return a LangChain-compatible Voyage AI embeddings instance."""
    return VoyageEmbeddings(api_key=VOYAGE_API_KEY, model=VOYAGE_MODEL)


# ── Low-level Voyage client (for batch ops) ────────────────────────────────────
def get_voyage_client() -> voyageai.Client:
    return voyageai.Client(api_key=VOYAGE_API_KEY)


def embed_texts(texts: list[str], input_type: str = "document") -> list[list[float]]:
    """
    Embed a list of texts using Voyage AI with retry logic.
    input_type: 'document' for storage, 'query' for retrieval.
    """
    client = get_voyage_client()
    all_embeddings: list[list[float]] = []
    batch_size = 128

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        for attempt in range(3):
            try:
                result = client.embed(batch, model=VOYAGE_MODEL, input_type=input_type)
                all_embeddings.extend(result.embeddings)
                break
            except Exception as e:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)

    return all_embeddings


# ── Batch embed & store to MongoDB ─────────────────────────────────────────────
def embed_and_store(
    collection_name: str,
    text_field: str,
    filter_query: dict | None = None,
    batch_size: int = 64,
) -> int:
    """
    Fetch documents from MongoDB, embed their text_field, and write
    back the 'embedding' array.  Returns the count of docs updated.
    """
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    coll = db[collection_name]

    query = filter_query or {"embedding": {"$in": [None, []]}}
    docs  = list(coll.find(query, {"_id": 1, text_field: 1}))

    if not docs:
        print(f"  ⚠ No documents to embed in '{collection_name}'")
        client.close()
        return 0

    texts = [str(d.get(text_field, "")) for d in docs]
    embeddings = embed_texts(texts, input_type="document")

    bulk_ops = []
    from pymongo import UpdateOne
    for doc, emb in zip(docs, embeddings):
        bulk_ops.append(UpdateOne({"_id": doc["_id"]}, {"$set": {"embedding": emb}}))

    if bulk_ops:
        result = coll.bulk_write(bulk_ops)
        print(f"  ✓ Embedded {result.modified_count} docs in '{collection_name}'")

    client.close()
    return len(bulk_ops)


def embed_all_collections() -> None:
    """Embed all relevant collections after seeding."""
    configs = [
        ("offers",          "description"),
        ("data_catalog",    "description"),
        ("compliance_rules","rule_text"),
        ("merchants",       "description"),
        ("cardholders",     "profile_text"),
        ("fraud_cases",     "investigation_notes"),
    ]
    for coll, field in configs:
        print(f"Embedding '{coll}' on field '{field}'...")
        embed_and_store(coll, field)


if __name__ == "__main__":
    embed_all_collections()
