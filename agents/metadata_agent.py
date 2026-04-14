"""
Use Case 1: Semantic Metadata Layer — Natural Language Data Discovery & Querying

Capabilities:
  • Discover datasets via semantic search over the VaultIQ data catalog
  • Inspect collection schemas
  • Generate and execute MQL queries from natural-language questions
  • Hybrid search (BM25 + vector) for catalog entries
  • Graph lookup across merchant_networks

Memory: Semantic (catalog knowledge) + Episodic (conversation history)
Interface: Chat (human-in-the-loop)
"""

from __future__ import annotations
from typing import Annotated, TypedDict, Any

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pymongo import MongoClient

import sys, os, json, asyncio, concurrent.futures, logging

logger = logging.getLogger(__name__)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT,
                    AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT,
                    MONGODB_URI, MONGODB_DB_NAME, AGENT_RECURSION_LIMIT)
from embeddings.voyage_client import embed_texts
from memory.mongodb_memory import SemanticMemory, EpisodicMemory

_db_client = MongoClient(MONGODB_URI)
_db = _db_client[MONGODB_DB_NAME]
_sem_mem = SemanticMemory()

SYSTEM_PROMPT = """You are **VaultIQ Data Intelligence** — a semantic metadata layer
that helps business analysts, data scientists, and compliance teams at Nexus Financial Group
discover, understand, and query enterprise data using plain English.

You have access to the entire VaultIQ data catalog backed by MongoDB Atlas with:
- **MongoDB MCP Server tools** (official @mongodb-js/mongodb-mcp-server):
    `find`, `aggregate`, `collection-schema`, `collection-indexes`,
    `list-collections`, `list-databases`, `count`, `db-stats`, `explain`
    These let you run real MongoDB queries and inspect schemas directly.
- **Native VaultIQ vector tools**:
    `search_data_catalog` — semantic vector search over the data catalog
    `hybrid_search_catalog` — BM25 + vector combined search
    `graph_lookup_merchant_network` — $graphLookup on fraud ring graph
    `geo_query_nearby_merchants` — $near geospatial merchant proximity
- **Fallback pymongo tools** (if MCP server not running):
    `inspect_collection_schema`, `execute_mql_query`

Preferred tool order for data queries:
1. Use `search_data_catalog` or `hybrid_search_catalog` to identify which collection to query
2. Use `collection-schema` (MCP) to understand the fields, or `inspect_collection_schema` as fallback
3. Use `find` or `aggregate` (MCP) to execute the actual query, or `execute_mql_query` as fallback
4. For graph traversal: use `graph_lookup_merchant_network` (native $graphLookup)
5. For geo: use `geo_query_nearby_merchants` (native $near)

Always cite which dataset(s) you queried, which tool you used, and show the MQL generated.
Format results in a clear, business-friendly way with key metrics highlighted.
"""


# ── Agent State ───────────────────────────────────────────────────────────────
class MetadataAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    session_id: str
    catalog_context: list[dict]
    last_query_mql: str
    last_query_results: list[dict]


# ── Tools ─────────────────────────────────────────────────────────────────────
@tool
def search_data_catalog(query: str) -> str:
    """Search the VaultIQ data catalog using semantic vector search to find relevant datasets."""
    results = _sem_mem.search_data_catalog(query, limit=4)
    if not results:
        # Fallback: simple regex text search
        results = list(_db.data_catalog.find(
            {"description": {"$regex": query, "$options": "i"}}, limit=4
        ))
    formatted = []
    for r in results:
        formatted.append(
            f"**{r.get('name','?')}** (ID: {r.get('dataset_id','?')})\n"
            f"  Collection: `{r.get('collection','?')}`\n"
            f"  Owner: {r.get('owner','?')}\n"
            f"  Description: {r.get('description','')[:200]}...\n"
            f"  Schema: {r.get('schema_summary','')}\n"
            f"  Sensitivity: {r.get('sensitivity','?')}\n"
            f"  Sample queries: {'; '.join(r.get('sample_queries',[])[:2])}"
        )
    return "\n\n".join(formatted) if formatted else "No matching datasets found."


@tool
def hybrid_search_catalog(query: str) -> str:
    """Hybrid BM25 + vector search over the data catalog using MongoDB Atlas $rankFusion.

    Combines a $vectorSearch (Voyage AI semantic embeddings) with a $search
    (Atlas Full-Text Search / BM25) sub-pipeline and merges them server-side
    via Reciprocal Rank Fusion — no Python-level merging needed.
    """
    # Generate query embedding for the vector leg
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
                                    "index": "catalog_vector_index",
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
                                    "index": "catalog_fts_index",
                                    "text": {
                                        "query": query,
                                        "path": ["name", "description", "tags", "schema_summary"],
                                    },
                                }
                            },
                            {"$limit": 10},
                        ],
                    }
                },
                # Equal weight to both legs — tunable via env if needed
                "combination": {"weights": {"vector": 0.5, "fullText": 0.5}},
            }
        },
        {"$limit": 5},
        {"$project": {"embedding": 0, "_id": 0}},
    ]

    try:
        results = list(_db.data_catalog.aggregate(pipeline))
    except Exception as exc:
        return f"Hybrid search failed: {exc}"

    if not results:
        return "Hybrid search returned no results for that query."

    lines = [f"Hybrid search ($rankFusion: BM25 + vector) returned {len(results)} results:"]
    for r in results:
        lines.append(
            f"- **{r.get('name')}** [{r.get('dataset_id')}]: "
            f"{r.get('description', '')[:120]}..."
        )
    return "\n".join(lines)


@tool
def inspect_collection_schema(collection_name: str) -> str:
    """Inspect the schema of a MongoDB collection by sampling documents."""
    valid = ["transactions","cardholders","merchants","offers",
             "data_catalog","fraud_cases","compliance_rules","merchant_networks"]
    if collection_name not in valid:
        return f"Unknown collection '{collection_name}'. Valid: {valid}"
    sample = list(_db[collection_name].find({}, limit=2))
    if not sample:
        return f"Collection '{collection_name}' is empty."
    # Extract field names and types
    def _schema(doc, prefix=""):
        fields = {}
        for k, v in doc.items():
            if k == "_id": continue
            fk = f"{prefix}{k}"
            if isinstance(v, dict):
                fields[fk] = "object"
                fields.update(_schema(v, prefix=f"{fk}."))
            elif isinstance(v, list):
                fields[fk] = f"array[{type(v[0]).__name__ if v else 'unknown'}]"
            else:
                fields[fk] = type(v).__name__
        return fields
    schema = _schema(sample[0])
    count = _db[collection_name].count_documents({})
    lines = [f"Collection: `{collection_name}` ({count:,} documents)\n\nFields:"]
    for field, dtype in schema.items():
        lines.append(f"  • {field}: {dtype}")
    return "\n".join(lines)


@tool
def execute_mql_query(collection_name: str, query_json: str, limit: int = 10) -> str:
    """
    Execute a MongoDB query. Provide:
    - collection_name: the collection to query
    - query_json: a JSON string with either a 'filter' or 'pipeline' key
    - limit: max rows to return (default 10)

    Example for pipeline: {"pipeline": [{"$match": {"fraud_score": {"$gte": 0.7}}}, {"$limit": 5}]}
    Example for filter:   {"filter": {"category": "Travel", "status": "approved"}}
    """
    valid = ["transactions","cardholders","merchants","offers",
             "data_catalog","fraud_cases","compliance_rules","merchant_networks"]
    if collection_name not in valid:
        return f"Unknown collection: {collection_name}"
    try:
        q = json.loads(query_json)
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"
    try:
        coll = _db[collection_name]
        if "pipeline" in q:
            pipeline = q["pipeline"]
            # Inject $limit if not already present
            has_limit = any("$limit" in stage for stage in pipeline)
            if not has_limit:
                pipeline.append({"$limit": min(limit, 20)})
            results = list(coll.aggregate(pipeline))
        else:
            filt = q.get("filter", {})
            proj  = q.get("project", {"_id": 0, "embedding": 0})
            results = list(coll.find(filt, proj).limit(min(limit, 20)))

        # Clean results for display
        clean = []
        for r in results:
            r.pop("_id", None)
            r.pop("embedding", None)
            clean.append(r)

        if not clean:
            return "Query executed successfully. No documents matched."
        return (
            f"Query returned {len(clean)} documents from `{collection_name}`:\n\n"
            + json.dumps(clean[:5], indent=2, default=str)
            + (f"\n\n... and {len(clean)-5} more." if len(clean) > 5 else "")
        )
    except Exception as e:
        return f"Query error: {e}"


@tool
def graph_lookup_merchant_network(merchant_id: str, max_depth: int = 2) -> str:
    """
    Perform a $graphLookup to traverse the merchant relationship network.
    Useful for discovering fraud rings, ownership hierarchies, and risk clusters.
    """
    pipeline = [
        {"$match": {"merchant_id": merchant_id}},
        {"$graphLookup": {
            "from": "merchant_networks",
            "startWith": "$edges.target_merchant_id",
            "connectFromField": "edges.target_merchant_id",
            "connectToField": "merchant_id",
            "as": "network",
            "maxDepth": max(1, min(max_depth, 3)),
        }},
        {"$project": {
            "merchant_id": 1,
            "merchant_name": 1,
            "cluster_id": 1,
            "risk_cluster_flag": 1,
            "network_size": {"$size": "$network"},
            "network": {"$slice": ["$network", 5]},
        }}
    ]
    results = list(_db.merchant_networks.aggregate(pipeline))
    if not results:
        return f"Merchant '{merchant_id}' not found in network graph."
    r = results[0]
    lines = [
        f"**Merchant Network for {r.get('merchant_name','?')} ({merchant_id})**",
        f"Cluster ID: {r.get('cluster_id','?')} | Risk Cluster: {'⚠️ YES' if r.get('risk_cluster_flag') else '✓ No'}",
        f"Connected merchants (depth ≤ {max_depth}): **{r.get('network_size', 0)}**",
        "",
        "Top connections:",
    ]
    for conn in r.get("network", [])[:5]:
        lines.append(
            f"  • {conn.get('merchant_name','?')} ({conn.get('merchant_id','?')}) "
            f"— cluster {conn.get('cluster_id','?')} "
            f"{'⚠️ Risk' if conn.get('risk_cluster_flag') else ''}"
        )
    return "\n".join(lines)


@tool
def geo_query_nearby_merchants(
    longitude: float, latitude: float, radius_km: float = 5.0, category: str | None = None
) -> str:
    """Find NFG merchants within a given radius of a location (lon/lat)."""
    query: dict = {
        "location": {
            "$near": {
                "$geometry": {"type": "Point", "coordinates": [longitude, latitude]},
                "$maxDistance": int(radius_km * 1000),
            }
        }
    }
    if category:
        query["category"] = category
    results = list(_db.merchants.find(
        query, {"_id": 0, "embedding": 0}, limit=8
    ))
    if not results:
        return f"No merchants found within {radius_km}km."
    lines = [f"Found {len(results)} merchants within {radius_km}km:"]
    for m in results:
        partner = " ⭐ Preferred Partner" if m.get("nfg_preferred_partner") else ""
        lines.append(
            f"  • **{m['name']}** ({m['category']}){partner} — {m['city']}"
        )
    return "\n".join(lines)


# ── Tool sets ─────────────────────────────────────────────────────────────────

# Native VaultIQ tools: vector/hybrid search, graph traversal, geo — always present.
# These have no equivalent in the MongoDB MCP server (they use Atlas Vector Search
# and complex aggregations specific to the VaultIQ data model).
NATIVE_AMEX_TOOLS = [
    search_data_catalog,
    hybrid_search_catalog,
    graph_lookup_merchant_network,
    geo_query_nearby_merchants,
]

# Pymongo fallback tools: used when the MongoDB MCP server is not running.
# When MCP IS running, `find`/`aggregate`/`collection-schema` from the server
# replace these with more capable, general-purpose equivalents.
PYMONGO_FALLBACK_TOOLS = NATIVE_AMEX_TOOLS + [
    inspect_collection_schema,
    execute_mql_query,
]


# ── LLM ───────────────────────────────────────────────────────────────────────
def get_llm() -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_deployment=AZURE_OPENAI_DEPLOYMENT,
        temperature=0,
    )


# ── Agent builder (accepts any tool list) ─────────────────────────────────────
def build_agent_with_tools(tools: list):
    """
    Compile a LangGraph ReAct agent with the given tool list.
    Called once per session with the combined MCP + native tool set.
    """
    llm = get_llm().bind_tools(tools)

    def agent_node(state: MetadataAgentState):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = llm.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: MetadataAgentState):
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    tool_node = ToolNode(tools)
    graph = StateGraph(MetadataAgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


# ── Async runner — uses MongoDB MCP Server ────────────────────────────────────
async def _run_with_mcp(
    question: str,
    session_id: str,
    history: list[BaseMessage] | None = None,
    memory_context: "SystemMessage | None" = None,
) -> dict:
    """
    Open an async MCP session to the MongoDB MCP server, combine its tools
    with native VaultIQ tools, build the LangGraph agent, and invoke it.

    Parameters
    ----------
    question : str
        The user's current message.
    session_id : str
        Identifies the ongoing session (used for episodic memory).
    history : list[BaseMessage], optional
        All prior turns in this session (HumanMessage + AIMessage).
        Passed into the agent state so multi-turn context is preserved.
    memory_context : SystemMessage, optional
        A pre-built SystemMessage injected at position 0 containing
        condensed semantic memories from past sessions.  Generated by
        SessionMemoryStore.build_memory_context_message().
    """
    from tools.mongodb_mcp_client import run_with_mongodb_mcp_tools

    ep = EpisodicMemory("metadata_agent", session_id)
    ep.add_turn("human", question)

    async with run_with_mongodb_mcp_tools() as mcp_tools:
        mcp_available = len(mcp_tools) > 0
        all_tools = (mcp_tools + NATIVE_AMEX_TOOLS) if mcp_available else PYMONGO_FALLBACK_TOOLS

        agent = build_agent_with_tools(all_tools)

        # Build message list:
        #  [memory_context?]  [prior turns...]  [current question]
        prior: list[BaseMessage] = list(history or [])
        if memory_context is not None:
            # Inject semantic memory context only at the very start
            # (avoid re-injecting on every turn after the first)
            if not prior:
                prior = [memory_context]

        state: MetadataAgentState = {
            "messages": prior + [HumanMessage(content=question)],
            "session_id": session_id,
            "catalog_context": [],
            "last_query_mql": "",
            "last_query_results": [],
        }

        result = await agent.ainvoke(state, {"recursion_limit": AGENT_RECURSION_LIMIT})
        final_msg = result["messages"][-1]
        answer = final_msg.content if hasattr(final_msg, "content") else str(final_msg)

        ep.add_turn("ai", answer)

        tool_calls_used = []
        for msg in result["messages"]:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls_used.append(tc.get("name", "unknown"))

        return {
            "answer": answer,
            "tool_calls": tool_calls_used,
            "messages": result["messages"],
            "mcp_tools_active": mcp_available,
            "mcp_tool_count": len(mcp_tools),
        }


# ── Public sync API ───────────────────────────────────────────────────────────
def run_metadata_query(
    question: str,
    session_id: str = "default",
    history: list[BaseMessage] | None = None,
    memory_context: "SystemMessage | None" = None,
    timeout: int = 180,
) -> dict:
    """
    Run the VaultIQ Metadata Agent on a natural-language question.

    Runs the async MCP logic in a dedicated thread so it always gets a
    fresh event loop — avoiding conflicts with Streamlit's own event loop.

    Parameters
    ----------
    question       : The user's current message.
    session_id     : Identifies the ongoing session for episodic memory.
    history        : Prior HumanMessage / AIMessage turns for multi-turn context.
    memory_context : Past-session SystemMessage injected on the first turn.
    timeout        : Seconds before we give up and fall back to pymongo tools.
                     First embedded-MCP run may take ~60 s (npx download).
    """
    def _thread_target():
        """Run the coroutine in a brand-new event loop inside its own thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                _run_with_mcp(question, session_id, history, memory_context)
            )
        finally:
            loop.close()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_thread_target)
            return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        logger.warning(
            f"run_metadata_query timed out after {timeout}s — falling back to pymongo tools."
        )
        return _run_pymongo_fallback(
            question, session_id, history,
            error=f"Agent timed out after {timeout}s (MCP subprocess may still be starting up). Using pymongo fallback.",
        )
    except Exception as e:
        logger.warning(f"run_metadata_query thread error: {e} — falling back to pymongo tools.")
        return _run_pymongo_fallback(question, session_id, history, error=str(e))


def _run_pymongo_fallback(
    question: str,
    session_id: str,
    history: list[BaseMessage] | None = None,
    error: str = "",
) -> dict:
    """Emergency sync fallback using only pymongo tools (no MCP, no async)."""
    ep = EpisodicMemory("metadata_agent", session_id)
    ep.add_turn("human", question)

    agent = build_agent_with_tools(PYMONGO_FALLBACK_TOOLS)
    prior = list(history or [])
    state: MetadataAgentState = {
        "messages": prior + [HumanMessage(content=question)],
        "session_id": session_id,
        "catalog_context": [],
        "last_query_mql": "",
        "last_query_results": [],
    }
    result = agent.invoke(state, {"recursion_limit": AGENT_RECURSION_LIMIT})
    final_msg = result["messages"][-1]
    answer = final_msg.content if hasattr(final_msg, "content") else str(final_msg)
    ep.add_turn("ai", answer)

    tool_calls_used = []
    for msg in result["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls_used.append(tc.get("name", "unknown"))

    return {
        "answer": answer,
        "tool_calls": tool_calls_used,
        "messages": result["messages"],
        "mcp_tools_active": False,
        "mcp_tool_count": 0,
        "fallback_reason": error,
    }
