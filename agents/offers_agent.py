"""
Use Case 3: Personalised Offers & Spending Intelligence — Chat Agent

Capabilities:
  • Semantic search: find offers matching cardholder interests
  • Hybrid search: keyword + vector for offer discovery
  • Geospatial: find nearby preferred merchants with active offers
  • Spending analytics: query cardholder's transaction history
  • Personalised recommendations based on card tier + preferences

Memory: Episodic (multi-turn chat) + Semantic (offer knowledge, preferences)
Interface: Chat (human cardholder interaction)
"""

from __future__ import annotations
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pymongo import MongoClient, DESCENDING

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT,
                    AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT,
                    MONGODB_URI, MONGODB_DB_NAME, AGENT_RECURSION_LIMIT)
from embeddings.voyage_client import embed_texts
from memory.mongodb_memory import SemanticMemory, EpisodicMemory

_db = MongoClient(MONGODB_URI)[MONGODB_DB_NAME]
_sem_mem = SemanticMemory()

SYSTEM_PROMPT = """You are **VaultConcierge** — a personalised AI assistant for Nexus Financial Group cardholders.

You help cardholders get the most from their NFG membership by:
- Discovering relevant offers and rewards tailored to their spending habits
- Finding nearby preferred partner merchants with exclusive NFG benefits
- Analysing their spending patterns and providing actionable insights
- Answering questions about Nexus Rewards, benefits, and account features

You have access to real-time offer data, merchant locations, and transaction history.
Always be warm, professional, and highlight the premium value of their NFG card.
Mention specific offer benefits and savings opportunities.

When recommending offers: prioritise NFG Preferred Partners ⭐, mention expiry dates,
and tailor recommendations to their card tier (Nexus Elite > Platinum > Gold > Classic).
"""


class OffersAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    session_id: str
    cardholder_id: str
    card_tier: str


# ── Tools ──────────────────────────────────────────────────────────────────────
@tool
def find_relevant_offers(
    query: str,
    card_tier: str | None = None,
    category: str | None = None,
    limit: int = 5,
) -> str:
    """Semantic vector search for offers with Atlas Vector Search PRE-FILTERING.

    Pre-filtering narrows the ANN candidate set *inside the index* before
    cosine similarity runs — faster and more relevant than post-filtering.

    Pre-filter fields (declared in the offers_vector_index definition):
        - card_tier: "Green", "Gold", "Platinum", "Centurion"
        - category: "Restaurant", "Travel", "Shopping", "Entertainment", etc.

    Examples:
        find_relevant_offers("dining rewards", card_tier="Platinum")
        find_relevant_offers("travel perks", category="Travel")
        find_relevant_offers("cashback", card_tier="Gold", category="Shopping")
    """
    results = _sem_mem.search_offers(query, card_tier=card_tier, category=category, limit=limit)
    if not results:
        # Fallback: keyword-OR text search across benefit_text, category, merchant_name
        stop = {"the","a","an","and","or","of","in","for","to","with","on","by","is","are","my","me","all"}
        words = [w for w in query.split() if w.lower() not in stop and len(w) > 2]
        filt: dict = {}
        if card_tier:
            filt["eligible_tiers"] = card_tier
        if category:
            filt["category"] = category
        if words:
            pattern = "|".join(words)
            filt["$or"] = [
                {"benefit_text":  {"$regex": pattern, "$options": "i"}},
                {"category":      {"$regex": pattern, "$options": "i"}},
                {"merchant_name": {"$regex": pattern, "$options": "i"}},
            ]
        results = list(_db.offers.find(filt, {"_id": 0, "embedding": 0}, limit=limit))
    if not results:
        return "No offers found matching your search."
    lines = [f"Found {len(results)} offers for you:"]
    for o in results:
        partner = " ⭐" if _db.merchants.find_one(
            {"merchant_id": o.get("merchant_id"), "nfg_preferred_partner": True}
        ) else ""
        lines.append(
            f"\n🎁 **{o.get('merchant_name','?')}{partner}** — {o.get('city','?')}\n"
            f"   {o.get('benefit_text','')}\n"
            f"   Valid until: {o.get('valid_until','?')[:10]} | Category: {o.get('category','?')}"
        )
    return "\n".join(lines)


@tool
def hybrid_search_offers(query: str, category: str | None = None) -> str:
    """Hybrid BM25 + vector search for maximum offer relevance using MongoDB Atlas $rankFusion.

    Combines a $vectorSearch (Voyage AI semantic embeddings) with a $search
    (Atlas Full-Text Search / BM25) sub-pipeline and merges them server-side
    via Reciprocal Rank Fusion. An optional category $match is applied after
    fusion to narrow results.
    """
    query_embedding = embed_texts([query], input_type="query")[0]

    pipeline = [
        {
            "$rankFusion": {
                "input": {
                    "pipelines": {
                        # ── Leg 1: semantic vector search ──────────────────
                        "vector": [
                            {
                                "$vectorSearch": {
                                    "index": "offers_vector_index",
                                    "path": "embedding",
                                    "queryVector": query_embedding,
                                    "numCandidates": 20,
                                    "limit": 10,
                                }
                            }
                        ],
                        # ── Leg 2: BM25 full-text search ───────────────────
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
                            {"$limit": 10},
                        ],
                    }
                },
                "combination": {"weights": {"vector": 0.5, "fullText": 0.5}},
            }
        },
        # Optional post-fusion category filter
        *([ {"$match": {"category": category}} ] if category else []),
        {"$limit": 6},
        {"$project": {"embedding": 0, "_id": 0}},
    ]

    try:
        results = list(_db.offers.aggregate(pipeline))
    except Exception as exc:
        return f"Hybrid search failed: {exc}"

    if not results:
        return "No matching offers found."

    lines = [f"Hybrid search ($rankFusion: BM25 + vector) — {len(results)} best matched offers:"]
    for o in results:
        lines.append(f"  • **{o.get('merchant_name')}** | {o.get('benefit_text')}")
    return "\n".join(lines)


@tool
def find_nearby_offers(longitude: float, latitude: float, radius_km: float = 3.0,
                        category: str | None = None) -> str:
    """Find NFG offers at merchants near a geographic location."""
    geo_query: dict = {
        "location": {
            "$near": {
                "$geometry": {"type": "Point", "coordinates": [longitude, latitude]},
                "$maxDistance": int(radius_km * 1000),
            }
        }
    }
    if category:
        geo_query["category"] = category

    nearby_merchants = list(_db.merchants.find(geo_query, {"merchant_id": 1, "name": 1, "category": 1}, limit=15))
    merchant_ids = [m["merchant_id"] for m in nearby_merchants]
    merchant_map = {m["merchant_id"]: m["name"] for m in nearby_merchants}

    offers = list(_db.offers.find(
        {"merchant_id": {"$in": merchant_ids}},
        {"_id": 0, "embedding": 0}, limit=8
    ))

    if not offers:
        return f"No offers found within {radius_km}km of your location."

    lines = [f"📍 {len(offers)} offers near you (within {radius_km}km):"]
    for o in offers:
        lines.append(
            f"\n  🏪 **{o.get('merchant_name','?')}** — {o.get('category','?')}\n"
            f"     {o.get('benefit_text','')}\n"
            f"     Expires: {o.get('valid_until','?')[:10]}"
        )
    return "\n".join(lines)


@tool
def get_spending_summary(cardholder_id: str, period_days: int = 30) -> str:
    """Get a spending summary for a cardholder over the last N days."""
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)
    pipeline = [
        {"$match": {"cardholder_id": cardholder_id, "timestamp": {"$gte": cutoff}, "status": "approved"}},
        {"$group": {
            "_id": "$category",
            "total": {"$sum": "$amount"},
            "count": {"$sum": 1},
            "avg": {"$avg": "$amount"},
        }},
        {"$sort": {"total": -1}},
    ]
    results = list(_db.transactions.aggregate(pipeline))
    if not results:
        return f"No approved transactions in the last {period_days} days."

    grand_total = sum(r["total"] for r in results)
    lines = [f"💳 Spending Summary — Last {period_days} days\n", f"Total: **${grand_total:,.2f}**\n"]
    for r in results[:8]:
        pct = (r["total"] / grand_total * 100) if grand_total else 0
        bar = "█" * int(pct / 5)
        lines.append(
            f"  {r['_id']:<15} ${r['total']:>10,.2f} ({pct:4.1f}%) {bar} "
            f"({r['count']} txns, avg ${r['avg']:.0f})"
        )
    return "\n".join(lines)


@tool
def get_points_estimate(cardholder_id: str, period_days: int = 30) -> str:
    """Estimate Membership Rewards points earned based on recent spending."""
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)
    pipeline = [
        {"$match": {"cardholder_id": cardholder_id, "timestamp": {"$gte": cutoff}, "status": "approved"}},
        {"$group": {
            "_id": "$category",
            "total_spend": {"$sum": "$amount"},
        }},
    ]
    results = list(_db.transactions.aggregate(pipeline))
    if not results:
        return "No spending data for points estimation."

    # Multipliers by category (NFG Nexus Rewards rates)
    multipliers = {"Travel": 5, "Airlines": 5, "Hotel": 5, "Restaurant": 4,
                   "Dining": 4, "Grocery": 3, "Shopping": 2, "Electronics": 2}
    base_rate = 1

    total_points = 0
    lines = [f"✨ Membership Rewards Points Estimate (last {period_days} days):"]
    for r in results:
        cat = r["_id"]
        mult = multipliers.get(cat, base_rate)
        pts = int(r["total_spend"] * mult)
        total_points += pts
        lines.append(f"  {cat:<15} ${r['total_spend']:>8,.2f} × {mult}x = {pts:>8,} pts")

    lines.append(f"\n  **TOTAL: {total_points:,} Membership Rewards Points**")
    value_usd = total_points * 0.006  # ~0.6 cents per point
    lines.append(f"  Estimated value: ~${value_usd:.2f}")
    return "\n".join(lines)


@tool
def get_cardholder_info(cardholder_id: str) -> str:
    """Retrieve cardholder profile including tier and preferences."""
    ch = _db.cardholders.find_one(
        {"cardholder_id": cardholder_id}, {"_id": 0, "embedding": 0}
    )
    if not ch:
        return f"Cardholder {cardholder_id} not found."
    return (
        f"Welcome back, **{ch.get('name','?')}**!\n"
        f"  Card Tier: {ch.get('card_tier','?')} | Member since: {ch.get('member_since','?')[:7]}\n"
        f"  Home city: {ch.get('home_city','?')}\n"
        f"  Favourite categories: {', '.join(ch.get('preferred_categories',[]))}"
    )


# ── Build Agent ────────────────────────────────────────────────────────────────
OFFERS_TOOLS = [
    find_relevant_offers, hybrid_search_offers, find_nearby_offers,
    get_spending_summary, get_points_estimate, get_cardholder_info,
]


def get_llm():
    return AzureChatOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_deployment=AZURE_OPENAI_DEPLOYMENT,
        temperature=0.1,
    )


def build_offers_agent():
    llm = get_llm().bind_tools(OFFERS_TOOLS)

    def agent_node(state: OffersAgentState):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = llm.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: OffersAgentState):
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    tool_node = ToolNode(OFFERS_TOOLS)
    graph = StateGraph(OffersAgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


_offers_agent = None

def get_offers_agent():
    global _offers_agent
    if _offers_agent is None:
        _offers_agent = build_offers_agent()
    return _offers_agent


def run_offers_chat(
    message: str,
    cardholder_id: str = "CH_0001",
    card_tier: str = "Platinum",
    session_id: str = "offers-default",
    history: list[BaseMessage] | None = None,
) -> dict:
    """Run the personalised offers chat agent."""
    agent = get_offers_agent()
    ep = EpisodicMemory("offers_agent", session_id)
    ep.add_turn("human", message)

    prior = history or ep.get_history(10)
    state = {
        "messages": prior + [HumanMessage(content=message)],
        "session_id": session_id,
        "cardholder_id": cardholder_id,
        "card_tier": card_tier,
    }

    result = agent.invoke(state, {"recursion_limit": AGENT_RECURSION_LIMIT})
    final = result["messages"][-1]
    answer = final.content if hasattr(final, "content") else str(final)
    ep.add_turn("ai", answer)

    tool_calls = []
    for msg in result["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(tc.get("name", "?"))

    return {
        "answer": answer,
        "tool_calls": tool_calls,
        "messages": result["messages"],
        "history": ep.get_history(20),
    }
