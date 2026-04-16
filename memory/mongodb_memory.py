"""
Agentic Memory Architecture for the VaultIQ Showcase.

Four memory types — all backed by MongoDB Atlas:

┌────────────────────┬──────────────────────────────────────────────────────────┐
│ Memory Type        │ Description                                              │
├────────────────────┼──────────────────────────────────────────────────────────┤
│ Episodic Memory    │ Conversation history & past interactions per session.    │
│                    │ Stored in MongoDB, retrieved via LangGraph checkpointer. │
├────────────────────┼──────────────────────────────────────────────────────────┤
│ Semantic Memory    │ Long-term factual knowledge: cardholder profiles,        │
│                    │ compliance rules, data catalog — vector-searchable.      │
├────────────────────┼──────────────────────────────────────────────────────────┤
│ Procedural Memory  │ Agent skills: tool registry, MQL templates, fraud        │
│                    │ playbooks — tells the agent HOW to do things.           │
├────────────────────┼──────────────────────────────────────────────────────────┤
│ Working Memory     │ Ephemeral in-flight state managed by LangGraph's         │
│                    │ AgentState TypedDict — lives only during execution.      │
└────────────────────┴──────────────────────────────────────────────────────────┘
"""

from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from pymongo import MongoClient, DESCENDING
from pymongo.operations import SearchIndexModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import MONGODB_URI, MONGODB_DB_NAME, COLLECTIONS
from embeddings.voyage_client import embed_texts


# ── MongoDB client helper ──────────────────────────────────────────────────────
def _get_db():
    client = MongoClient(MONGODB_URI)
    return client, client[MONGODB_DB_NAME]


# ══════════════════════════════════════════════════════════════════════════════
# 1. EPISODIC MEMORY — conversation history per (agent, session)
# ══════════════════════════════════════════════════════════════════════════════
class EpisodicMemory:
    """
    Stores & retrieves conversation turns for a given agent session.
    Mirrors what the LangGraph MongoDB Checkpointer does under the hood
    but surfaces it as an explicit, readable store for demo purposes.
    """

    def __init__(self, agent_name: str, session_id: str) -> None:
        self.agent_name = agent_name
        self.session_id = session_id
        _, self.db = _get_db()
        self.coll = self.db[COLLECTIONS["conversation_history"]]

    def add_turn(self, role: str, content: str, metadata: dict | None = None) -> None:
        """Append a conversation turn (human or ai)."""
        self.coll.insert_one({
            "agent_name": self.agent_name,
            "session_id": self.session_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc),
        })

    def get_history(self, limit: int = 20) -> list[BaseMessage]:
        """Return recent turns as LangChain message objects."""
        docs = list(
            self.coll.find(
                {"agent_name": self.agent_name, "session_id": self.session_id},
                sort=[("timestamp", DESCENDING)],
                limit=limit,
            )
        )
        docs.reverse()
        messages = []
        for d in docs:
            if d["role"] == "human":
                messages.append(HumanMessage(content=d["content"]))
            else:
                messages.append(AIMessage(content=d["content"]))
        return messages

    def clear_session(self) -> int:
        result = self.coll.delete_many({
            "agent_name": self.agent_name,
            "session_id": self.session_id,
        })
        return result.deleted_count

    def get_session_summary(self) -> dict:
        count = self.coll.count_documents({
            "agent_name": self.agent_name,
            "session_id": self.session_id,
        })
        return {"agent": self.agent_name, "session": self.session_id, "turns": count}


# ══════════════════════════════════════════════════════════════════════════════
# 2. SEMANTIC MEMORY — vector-searchable long-term knowledge
# ══════════════════════════════════════════════════════════════════════════════
class SemanticMemory:
    """
    Retrieves relevant knowledge from MongoDB vector collections.
    Backed by Atlas Vector Search + Voyage AI embeddings.
    Falls back to text-match if Atlas Vector Search unavailable.
    """

    def __init__(self) -> None:
        _, self.db = _get_db()

    def _vector_search(
        self, collection_name: str, query: str, index_name: str,
        limit: int = 5, filter_: dict | None = None,
    ) -> list[dict]:
        """Run Atlas Vector Search pipeline."""
        try:
            q_emb = embed_texts([query], input_type="query")[0]
            pipeline: list[dict] = [
                {"$vectorSearch": {
                    "index": index_name,
                    "path": "embedding",
                    "queryVector": q_emb,
                    "numCandidates": limit * 10,
                    "limit": limit,
                    **({"filter": filter_} if filter_ else {}),
                }},
                {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
            ]
            return list(self.db[collection_name].aggregate(pipeline))
        except Exception:
            # Fallback: simple text search
            text_query: dict = {"$text": {"$search": query}}
            if filter_:
                text_query.update(filter_)
            return list(self.db[collection_name].find(text_query, limit=limit))

    def search_compliance_rules(self, query: str, limit: int = 4) -> list[dict]:
        """Find relevant compliance rules by semantic similarity."""
        return self._vector_search("compliance_rules", query, "compliance_vector_index", limit)

    def search_data_catalog(self, query: str, limit: int = 5) -> list[dict]:
        """Find relevant datasets from the NFG data catalog."""
        return self._vector_search("data_catalog", query, "catalog_vector_index", limit)

    def search_offers(
        self, query: str, card_tier: str | None = None,
        category: str | None = None, limit: int = 6,
    ) -> list[dict]:
        """Semantic search over offers with Atlas Vector Search pre-filtering.

        Pre-filters narrow the ANN candidate set *before* the vector search runs,
        which is both faster and more relevant than post-filtering.

        Filterable fields (declared in the vector index definition):
            - eligible_tiers: e.g. "Platinum", "Gold"
            - category: e.g. "Restaurant", "Travel", "Shopping"
        """
        filter_: dict = {}
        if card_tier:
            filter_["eligible_tiers"] = card_tier
        if category:
            filter_["category"] = category
        return self._vector_search(
            "offers", query, "offers_vector_index", limit,
            filter_ if filter_ else None,
        )

    def search_cardholder_profiles(self, query: str, limit: int = 5) -> list[dict]:
        """Semantic search over cardholder profiles."""
        return self._vector_search("cardholders", query, "cardholders_vector_index", limit)


# ══════════════════════════════════════════════════════════════════════════════
# 3. PROCEDURAL MEMORY — agent skills: MQL playbooks & tool specs
# ══════════════════════════════════════════════════════════════════════════════
FRAUD_PLAYBOOKS = {
    "card_not_present": [
        "1. Retrieve all CNP transactions in last 24h for cardholder",
        "2. Check velocity: >3 CNP declines in 1h → flag",
        "3. Run geo_velocity_check on consecutive transactions",
        "4. Screen merchant against known CNP fraud rings",
        "5. If score > 0.8: block_card(temporary=True), send_notification, escalate",
    ],
    "account_takeover": [
        "1. Check for recent login from new device/location",
        "2. Identify profile changes (email, phone, address) in last 48h",
        "3. Review spending pattern deviation from 90-day baseline",
        "4. Verify via credit_bureau_lookup for identity confirmation",
        "5. If confident: block_card, file_sar if amount > $5000",
    ],
    "money_laundering": [
        "1. Map transaction graph: look for structuring below $10K threshold",
        "2. Identify round-trip flows across merchant network graph",
        "3. Screen all parties via screen_sanctions",
        "4. Calculate total flow volume over 30 days",
        "5. If AML indicators: file_sar with complete narrative",
    ],
}

MQL_TEMPLATES = {
    "high_fraud_score_txns": {
        "description": "Transactions with fraud score above threshold",
        "template": {"collection": "transactions", "filter": {"fraud_score": {"$gte": 0.7}, "status": "approved"}},
    },
    "cardholder_90d_spend": {
        "description": "Total spend per cardholder in last 90 days",
        "template": {"collection": "transactions", "pipeline": [
            {"$match": {"timestamp": {"$gte": "{{90_days_ago}}"}}},
            {"$group": {"_id": "$cardholder_id", "total_spend": {"$sum": "$amount"}}},
            {"$sort": {"total_spend": -1}},
        ]},
    },
    "geo_nearby_merchants": {
        "description": "Merchants within N km of a location",
        "template": {"collection": "merchants", "filter": {"location": {"$near": {
            "$geometry": {"type": "Point", "coordinates": ["{{lon}}", "{{lat}}"]},
            "$maxDistance": "{{max_distance_m}}",
        }}}},
    },
    "graph_fraud_ring": {
        "description": "Graph lookup: merchants connected to a suspected fraud ring",
        "template": {"collection": "merchant_networks", "pipeline": [
            {"$match": {"merchant_id": "{{merchant_id}}"}},
            {"$graphLookup": {
                "from": "merchant_networks",
                "startWith": "$edges.target_merchant_id",
                "connectFromField": "edges.target_merchant_id",
                "connectToField": "merchant_id",
                "as": "connected_merchants",
                "maxDepth": 2,
                "restrictSearchWithMatch": {"risk_cluster_flag": True},
            }},
        ]},
    },
}


class ProceduralMemory:
    """
    Provides agents with structured playbooks and MQL templates.
    This is HOW the agent knows to do things — its skills.
    """

    @staticmethod
    def get_fraud_playbook(fraud_type: str) -> list[str]:
        return FRAUD_PLAYBOOKS.get(fraud_type, FRAUD_PLAYBOOKS["card_not_present"])

    @staticmethod
    def get_mql_template(template_name: str) -> dict:
        return MQL_TEMPLATES.get(template_name, {})

    @staticmethod
    def list_available_tools() -> list[str]:
        return ["screen_sanctions", "credit_bureau_lookup", "block_card",
                "send_notification", "file_sar", "merchant_risk_check", "geo_velocity_check"]

    @staticmethod
    def get_all_playbooks() -> dict:
        return FRAUD_PLAYBOOKS

    @staticmethod
    def get_all_templates() -> dict:
        return MQL_TEMPLATES


# ══════════════════════════════════════════════════════════════════════════════
# 4. SESSION MEMORY STORE — episodic → semantic distillation at session end
# ══════════════════════════════════════════════════════════════════════════════
class SessionMemoryStore:
    """
    Converts a finished conversation (episodic memory) into a compressed,
    vector-embedded semantic memory stored permanently in MongoDB.

    Flow
    ────
    1. User clicks "End Session"
    2. Raw turns pulled from EpisodicMemory (conversation_history collection)
    3. LLM (Azure GPT-4o) distils them into a structured JSON summary
    4. Summary text embedded with Voyage AI (voyage-finance-2, 1024-dim)
    5. Document upserted into `session_memories` collection
    6. On the NEXT session start, semantic search retrieves the most relevant
       past summaries and injects them as context → agent "remembers"

    Collection schema
    ─────────────────
    {
      memory_id:         "MEM-<uuid>",
      agent_name:        "metadata_agent",
      session_id:        "...",
      created_at:        ISODate,
      turn_count:        12,
      summary:           "User explored fraud and geo datasets...",
      datasets_explored: ["transactions", "merchants"],
      key_insights:      ["500 transactions, ~5% flagged", ...],
      queries_run:       ["high fraud score filter", ...],
      data_patterns:     ["transactions skew toward NY/LA", ...],
      tools_used:        ["find", "aggregate", "search_data_catalog"],
      embedding:         [0.012, -0.034, ...]   ← 1024-dim Voyage AI
    }
    """

    COLLECTION = "session_memories"
    VECTOR_INDEX = "session_memories_vector_index"

    # LLM distillation prompt
    _DISTIL_PROMPT = """You are a knowledge distillation assistant for the NFG Data Intelligence system.

Summarise the following data-discovery conversation into a structured semantic memory that will
be retrieved and used as context in future sessions.

Focus on:
- Which datasets / MongoDB collections were explored
- What queries were run and what they returned (key numbers, patterns)
- Important schema details discovered
- Noteworthy data insights (volumes, anomalies, distributions)
- Any dead-ends or limitations found

Conversation transcript:
{transcript}

Respond ONLY with valid JSON in exactly this format:
{{
  "summary": "<2-3 sentence plain-English overview of what was explored and found>",
  "datasets_explored": ["collection1", "collection2"],
  "key_insights": [
    "<specific finding with numbers>",
    "<another finding>"
  ],
  "queries_run": ["<brief description of query 1>", "<query 2>"],
  "data_patterns": ["<pattern 1>", "<pattern 2>"],
  "tools_used": ["<tool1>", "<tool2>"]
}}"""

    def __init__(self, agent_name: str = "metadata_agent") -> None:
        self.agent_name = agent_name
        _, self.db = _get_db()
        self.coll = self.db[self.COLLECTION]
        self._ensure_index()

    def _ensure_index(self) -> None:
        """Create Atlas Vector Search index on session_memories if not already present."""
        try:
            existing = list(self.coll.list_search_indexes())
            if not any(i.get("name") == self.VECTOR_INDEX for i in existing):
                model = SearchIndexModel(
                    definition={
                        "type": "vectorSearch",
                        "fields": [{
                            "type": "vector",
                            "path": "embedding",
                            "numDimensions": 1024,
                            "similarity": "cosine",
                        }],
                    },
                    name=self.VECTOR_INDEX,
                    type="vectorSearch",
                )
                self.coll.create_search_index(model)
        except Exception:
            pass  # local MongoDB or index already exists

    # ── Distil & Store ────────────────────────────────────────────────────────
    def condense_and_store(
        self,
        session_id: str,
        messages: list[BaseMessage],
        llm=None,
        extra_metadata: dict | None = None,
    ) -> dict:
        """
        Distil a completed conversation into a semantic memory document.

        Parameters
        ----------
        session_id : str
            The session being closed.
        messages : list[BaseMessage]
            All HumanMessage / AIMessage turns from the session.
        llm : optional
            A LangChain chat model (e.g. AzureChatOpenAI) to run the
            distillation prompt.  If None, a plain concatenation is stored.
        extra_metadata : dict, optional
            Any extra fields to merge into the stored document.

        Returns
        -------
        dict
            The stored memory document (without embedding for display).
        """
        if not messages:
            return {}

        # Build readable transcript (cap each turn to keep tokens manageable)
        transcript_lines = []
        for m in messages:
            role = "User" if isinstance(m, HumanMessage) else "Agent"
            transcript_lines.append(f"{role}: {m.content[:800]}")
        transcript = "\n\n".join(transcript_lines)

        # ── LLM distillation ──────────────────────────────────────────────────
        structured: dict = {}
        if llm is not None:
            try:
                prompt = self._DISTIL_PROMPT.format(transcript=transcript)
                response = llm.invoke(prompt)
                raw = response.content.strip()
                # Strip markdown code fences if present
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                structured = json.loads(raw)
            except Exception as e:
                structured = {"summary": f"Session distillation failed: {e}"}
        else:
            # No LLM — store a plain transcript excerpt
            structured = {
                "summary": transcript[:400] + ("..." if len(transcript) > 400 else ""),
            }

        # Ensure all expected keys exist
        structured.setdefault("summary", "No summary available.")
        structured.setdefault("datasets_explored", [])
        structured.setdefault("key_insights", [])
        structured.setdefault("queries_run", [])
        structured.setdefault("data_patterns", [])
        structured.setdefault("tools_used", [])

        # ── Embed the summary + insights ──────────────────────────────────────
        embed_text = (
            structured["summary"]
            + " "
            + " ".join(structured["key_insights"])
            + " "
            + " ".join(structured["datasets_explored"])
        ).strip()

        embedding: list[float] = []
        if embed_text:
            try:
                embedding = embed_texts([embed_text], input_type="document")[0]
            except Exception:
                pass  # voyage not configured — store without embedding

        # ── Build & upsert document ───────────────────────────────────────────
        memory_id = f"MEM-{session_id}"
        doc: dict = {
            "memory_id": memory_id,
            "agent_name": self.agent_name,
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc),
            "turn_count": len(messages),
            "summary": structured["summary"],
            "datasets_explored": structured["datasets_explored"],
            "key_insights": structured["key_insights"],
            "queries_run": structured["queries_run"],
            "data_patterns": structured["data_patterns"],
            "tools_used": structured["tools_used"],
            "embedding": embedding,
            **(extra_metadata or {}),
        }

        self.coll.replace_one({"memory_id": memory_id}, doc, upsert=True)

        # Return without the raw embedding vector (for display)
        display = {k: v for k, v in doc.items() if k != "embedding"}
        return display

    # ── Retrieve ──────────────────────────────────────────────────────────────
    def retrieve_relevant_memories(
        self, query: str, limit: int = 3, min_score: float = 0.70
    ) -> list[dict]:
        """
        Semantic vector search over stored session memories.
        Returns the most relevant past sessions for the given query.
        Falls back to recency sort if Atlas Vector Search is unavailable.
        """
        try:
            q_emb = embed_texts([query], input_type="query")[0]
            pipeline = [
                {"$vectorSearch": {
                    "index": self.VECTOR_INDEX,
                    "path": "embedding",
                    "queryVector": q_emb,
                    "numCandidates": limit * 15,
                    "limit": limit,
                    "filter": {"agent_name": self.agent_name},
                }},
                {"$addFields": {"relevance_score": {"$meta": "vectorSearchScore"}}},
                {"$match": {"relevance_score": {"$gte": min_score}}},
                {"$project": {"embedding": 0}},
            ]
            return list(self.coll.aggregate(pipeline))
        except Exception:
            # Fallback: most recent memories
            return list(self.coll.find(
                {"agent_name": self.agent_name},
                {"embedding": 0},
                sort=[("created_at", DESCENDING)],
                limit=limit,
            ))

    def build_memory_context_message(
        self, query: str, limit: int = 2
    ) -> SystemMessage | None:
        """
        Retrieve relevant past sessions and format them as a single
        SystemMessage to prepend to the agent's conversation.
        Returns None if no relevant memories exist.
        """
        memories = self.retrieve_relevant_memories(query, limit=limit)
        if not memories:
            return None

        lines = ["📚 PAST SESSION CONTEXT (from semantic memory):", ""]
        for i, m in enumerate(memories, 1):
            ts = m.get("created_at", "")
            if hasattr(ts, "strftime"):
                ts = ts.strftime("%Y-%m-%d %H:%M UTC")
            lines.append(f"Session {i} — {ts} ({m.get('turn_count', '?')} turns)")
            lines.append(f"  Summary: {m.get('summary', '')}")
            if m.get("datasets_explored"):
                lines.append(f"  Collections explored: {', '.join(m['datasets_explored'])}")
            if m.get("key_insights"):
                for insight in m["key_insights"][:3]:
                    lines.append(f"  • {insight}")
            lines.append("")

        lines.append(
            "Use the above as background knowledge. "
            "Do not repeat findings already confirmed in a past session unless the user asks."
        )
        return SystemMessage(content="\n".join(lines))

    # ── List / Admin ──────────────────────────────────────────────────────────
    def list_all_memories(self, limit: int = 20) -> list[dict]:
        """Return all stored session memories (newest first), without embeddings."""
        return list(self.coll.find(
            {"agent_name": self.agent_name},
            {"embedding": 0},
            sort=[("created_at", DESCENDING)],
            limit=limit,
        ))

    def delete_memory(self, memory_id: str) -> bool:
        result = self.coll.delete_one({"memory_id": memory_id})
        return result.deleted_count > 0

    def count(self) -> int:
        return self.coll.count_documents({"agent_name": self.agent_name})
