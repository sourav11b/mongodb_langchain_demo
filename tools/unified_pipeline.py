"""
Unified Aggregate Pipeline — combines $rankFusion, time-series $lookup,
$geoWithin, and $graphLookup in a single MongoDB aggregate pipeline,
then reranks results with Voyage AI rerank-2.

Demonstrates: every major MongoDB aggregation feature in ONE query.
"""

from __future__ import annotations
import time, logging, math, json
from datetime import datetime, timedelta, timezone
from typing import Any

import voyageai
from pymongo import MongoClient

from config import MONGODB_URI, MONGODB_DB_NAME, VOYAGE_API_KEY
from embeddings.voyage_client import embed_texts

logger = logging.getLogger(__name__)

# City hub coordinates (lon, lat)
CITY_COORDS: dict[str, list[float]] = {
    "New York":    [-74.0060, 40.7128],
    "Los Angeles": [-118.2437, 34.0522],
    "Chicago":     [-87.6298, 41.8781],
    "London":      [-0.1276, 51.5074],
    "Dubai":       [55.2708, 25.2048],
    "Singapore":   [103.8198, 1.3521],
    "Tokyo":       [139.6917, 35.6895],
    "Sydney":      [151.2093, -33.8688],
}

SAMPLE_QUERIES = [
    "Find travel rewards and dining cashback offers near Manhattan from merchants with clean fraud networks",
    "High-value luxury hotel offers in London with low-risk merchant connections and recent transaction volume",
    "Cashback grocery deals near Chicago — check merchant fraud ring status and 90-day spend trends",
    "Premium lounge access offers in Dubai from high-volume merchants with no suspicious network links",
    "Electronics shopping rewards in Tokyo — show transaction patterns and merchant risk clusters",
]


def build_pipeline(
    query: str,
    query_embedding: list[float],
    coords: list[float],
    radius_km: float,
    days_back: int,
) -> list[dict]:
    """Build the unified 4-stage aggregate pipeline."""

    radius_radians = radius_km / 6378.1  # Earth radius in km
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    return [
        # ── Stage 1: $rankFusion — hybrid semantic + keyword search ──
        {
            "$rankFusion": {
                "input": {
                    "pipelines": {
                        "vector": [
                            {
                                "$vectorSearch": {
                                    "index": "offers_vector_index",
                                    "path": "embedding",
                                    "queryVector": query_embedding,
                                    "numCandidates": 40,
                                    "limit": 15,
                                }
                            }
                        ],
                        "fullText": [
                            {
                                "$search": {
                                    "index": "offers_fts_index",
                                    "text": {
                                        "query": query,
                                        "path": ["description", "benefit_text",
                                                 "merchant_name", "category"],
                                    },
                                }
                            },
                            {"$limit": 15},
                        ],
                    }
                },
                "combination": {"weights": {"vector": 0.6, "fullText": 0.4}},
            }
        },

        # ── Stage 2: $geoWithin — filter by proximity to city hub ──
        {
            "$match": {
                "location": {
                    "$geoWithin": {
                        "$centerSphere": [coords, radius_radians]
                    }
                }
            }
        },

        # ── Stage 3: $lookup — time-series transaction analysis ──
        {
            "$lookup": {
                "from": "transactions",
                "let": {"mid": "$merchant_id"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$merchant_id", "$$mid"]}}},
                    {"$match": {"timestamp": {"$gte": cutoff}}},
                    {"$group": {
                        "_id": None,
                        "txn_count": {"$sum": 1},
                        "total_volume": {"$sum": "$amount"},
                        "avg_amount": {"$avg": "$amount"},
                        "max_fraud_score": {"$max": "$fraud_score"},
                        "flagged_count": {
                            "$sum": {"$cond": ["$is_flagged", 1, 0]}
                        },
                    }}
                ],
                "as": "txn_stats"
            }
        },

        # ── Stage 4: $graphLookup — merchant network traversal ──
        {
            "$graphLookup": {
                "from": "merchant_networks",
                "startWith": "$merchant_id",
                "connectFromField": "edges.target_merchant_id",
                "connectToField": "merchant_id",
                "as": "network",
                "maxDepth": 2,
            }
        },

        # ── Enrich with computed fields ──
        {
            "$addFields": {
                "txn_summary": {"$arrayElemAt": ["$txn_stats", 0]},
                "network_depth": {"$size": "$network"},
                "risk_connections": {
                    "$size": {
                        "$filter": {
                            "input": "$network",
                            "cond": {"$eq": ["$$this.risk_cluster_flag", True]}
                        }
                    }
                },
            }
        },

        # ── Clean up and limit ──
        {"$project": {
            "embedding": 0, "txn_stats": 0, "_id": 0,
            "network.edges": 0, "network.betweenness_centrality": 0,
            "network.community_risk_score": 0,
        }},
        {"$limit": 10},
    ]


def _clean_doc(doc: dict) -> dict:
    """Recursively clean a MongoDB doc for JSON serialisation."""
    cleaned = {}
    for k, v in doc.items():
        if isinstance(v, datetime):
            cleaned[k] = v.isoformat()
        elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            cleaned[k] = None
        elif isinstance(v, dict):
            cleaned[k] = _clean_doc(v)
        elif isinstance(v, list):
            cleaned[k] = [
                _clean_doc(x) if isinstance(x, dict)
                else x.isoformat() if isinstance(x, datetime)
                else x
                for x in v[:8]       # cap list length for display
            ]
        else:
            cleaned[k] = v
    return cleaned


def _build_rerank_text(r: dict) -> str:
    """Build a text representation of a result for the reranker."""
    txn = r.get("txn_summary") or {}
    return (
        f"{r.get('merchant_name', '')} — {r.get('description', '')} | "
        f"Category: {r.get('category', '')} | "
        f"Benefit: {r.get('benefit_text', '')} | "
        f"Txns: {txn.get('txn_count', 0)}, "
        f"Vol: ${txn.get('total_volume', 0):,.0f}, "
        f"Max fraud: {txn.get('max_fraud_score', 0):.3f} | "
        f"Network nodes: {r.get('network_depth', 0)}, "
        f"Risk links: {r.get('risk_connections', 0)}"
    )


def run_unified_pipeline(
    query: str,
    city: str = "New York",
    radius_km: float = 50.0,
    days_back: int = 90,
    rerank_top_k: int = 5,
) -> dict[str, Any]:
    """Execute the unified 4-feature aggregate pipeline + Voyage AI reranking."""

    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]

    # Embed query for vector search leg
    query_embedding = embed_texts([query], input_type="query")[0]

    coords = CITY_COORDS.get(city, CITY_COORDS["New York"])

    pipeline = build_pipeline(query, query_embedding, coords, radius_km, days_back)

    # ── Execute pipeline ──
    t0 = time.time()
    raw_results = list(db.offers.aggregate(pipeline, allowDiskUse=True))
    pipeline_ms = round((time.time() - t0) * 1000)

    # ── Voyage AI Reranking ──
    reranked: list[dict] = []
    rerank_ms = 0

    if raw_results:
        docs_for_rerank = [_build_rerank_text(r) for r in raw_results]

        try:
            vo = voyageai.Client(api_key=VOYAGE_API_KEY)
            t1 = time.time()
            rr = vo.rerank(
                query, docs_for_rerank,
                model="rerank-2",
                top_k=min(rerank_top_k, len(docs_for_rerank)),
            )
            rerank_ms = round((time.time() - t1) * 1000)

            for item in rr.results:
                entry = raw_results[item.index].copy()
                entry["rerank_score"] = round(item.relevance_score, 4)
                entry["rerank_position"] = len(reranked) + 1
                entry["original_position"] = item.index + 1
                reranked.append(entry)
        except Exception as e:
            logger.warning("Voyage rerank error: %s", e)
            for i, r in enumerate(raw_results[:rerank_top_k]):
                r["rerank_score"] = None
                r["rerank_position"] = i + 1
                r["original_position"] = i + 1
                reranked.append(r)

    client.close()

    # Build a display-safe copy of the pipeline (without the huge embedding vector)
    pipeline_display = json.loads(json.dumps(pipeline, default=str))
    vec_stage = pipeline_display[0]["$rankFusion"]["input"]["pipelines"]["vector"][0]
    vec_stage["$vectorSearch"]["queryVector"] = "[...1024-dim vector...]"

    return {
        "query": query,
        "city": city,
        "coords": coords,
        "radius_km": radius_km,
        "days_back": days_back,
        "pipeline_stages": [
            "$rankFusion (vector + BM25)",
            "$geoWithin ($centerSphere)",
            "$lookup (time-series txn stats)",
            "$graphLookup (merchant network, depth≤2)",
        ],
        "raw_count": len(raw_results),
        "reranked_count": len(reranked),
        "pipeline_ms": pipeline_ms,
        "rerank_ms": rerank_ms,
        "total_ms": pipeline_ms + rerank_ms,
        "raw_results": [_clean_doc(r) for r in raw_results],
        "reranked_results": [_clean_doc(r) for r in reranked],
        "pipeline_mql": pipeline_display,
    }
