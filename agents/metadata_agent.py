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

## Tool Priority — ALWAYS follow this order

### 1. MongoDB MCP Server tools ← PRIMARY for ALL data interaction
Use these for every query, listing, schema inspection, and aggregation.
Never skip to semantic search before trying these first.

| Tool | When to use |
|------|-------------|
| `list-collections` | User asks what collections/tables/datasets exist |
| `list-databases` | User asks what databases exist |
| `collection-schema` | User wants to understand fields/structure of a collection |
| `collection-indexes` | User asks about indexes |
| `find` | Filter-based data retrieval (generates MQL filter JSON) |
| `aggregate` | Aggregation pipelines, grouping, $graphLookup, etc. |
| `count` | Count documents matching a filter |
| `db-stats` | Database statistics |
| `explain` | Query plan analysis |

### 2. Native VaultIQ vector tools ← ONLY for semantic catalog discovery
Use these ONLY when the user is explicitly asking to search the metadata catalog
by topic or keyword (e.g. "find datasets related to fraud", "what data do we have about merchants").
Do NOT call these for general data queries, listing, or schema inspection.

| Tool | When to use |
|------|-------------|
| `search_data_catalog` | Semantic search over the metadata catalog |
| `hybrid_search_catalog` | $rankFusion (BM25 + vector) catalog search |
| `graph_lookup_merchant_network` | $graphLookup fraud ring traversal |
| `geo_query_nearby_merchants` | $near geospatial proximity |

### 3. Pymongo fallback tools ← ONLY if MCP server is unavailable
`inspect_collection_schema`, `execute_mql_query`

## Rules
- For "show me all collections", "what tables exist", "list databases" → call `list-collections` or `list-databases` IMMEDIATELY. Never run semantic search first.
- For "what's in collection X", "schema of X" → call `collection-schema` IMMEDIATELY.
- For "query X", "show me data from X" → call `find` or `aggregate` IMMEDIATELY.
- Always show the MQL / pipeline you generated.
- Cite which tool was used in your response.
- Format results in a clear, business-friendly way with key metrics highlighted.
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


# ── Fallback system prompt (pymongo-only tools) ──────────────────────────────
FALLBACK_SYSTEM_PROMPT = """You are **VaultIQ Data Intelligence** — a data discovery agent
for Nexus Financial Group running in **pymongo fallback mode** (MCP server unavailable).

## Available tools — USE ONLY THESE

| Tool | When to use |
|------|-------------|
| `search_data_catalog` | Semantic vector search over the metadata catalog |
| `hybrid_search_catalog` | $rankFusion (BM25 + vector) catalog search |
| `inspect_collection_schema` | View schema/fields of a specific collection |
| `execute_mql_query` | Run a find or aggregate query (pass MQL as JSON) |
| `graph_lookup_merchant_network` | $graphLookup fraud ring traversal |
| `geo_query_nearby_merchants` | $near geospatial proximity |

## Rules
- You do NOT have `list-collections`, `list-databases`, `find`, `aggregate`, or any MCP tools.
- To list collections, use `inspect_collection_schema` on known collection names or tell the user MCP is unavailable.
- To query data, use `execute_mql_query` — pass a JSON filter or pipeline.
- For "what datasets exist", use `search_data_catalog` with a broad query.
- Keep it concise. Show the MQL you generated. Format results in business-friendly way.
- Do NOT repeatedly call the same tool with the same input — if a tool returns no results, say so and stop.
"""


# ── Agent builder (accepts any tool list) ─────────────────────────────────────
def build_agent_with_tools(tools: list, system_prompt: str | None = None):
    """
    Compile a LangGraph ReAct agent with the given tool list.
    Called once per session with the combined MCP + native tool set.
    """
    prompt = system_prompt or SYSTEM_PROMPT
    llm = get_llm().bind_tools(tools)

    def agent_node(state: MetadataAgentState):
        messages = [SystemMessage(content=prompt)] + state["messages"]
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

    import time as _time
    t0 = _time.time()
    logger.debug("➤ _run_with_mcp START | q=%r | session=%s", question[:60], session_id)

    ep = EpisodicMemory("metadata_agent", session_id)
    ep.add_turn("human", question)
    logger.debug("  EpisodicMemory initialised (%.1fs)", _time.time() - t0)

    logger.debug("  Entering run_with_mongodb_mcp_tools()...")
    async with run_with_mongodb_mcp_tools() as mcp_tools:
        logger.debug("  MCP tools yielded: %d (%.1fs)", len(mcp_tools), _time.time() - t0)
        mcp_available = len(mcp_tools) > 0
        all_tools = (mcp_tools + NATIVE_AMEX_TOOLS) if mcp_available else PYMONGO_FALLBACK_TOOLS
        logger.debug("  Tool set: %s — %d tools total",
                     "MCP+native" if mcp_available else "pymongo fallback", len(all_tools))

        agent = build_agent_with_tools(all_tools)
        logger.debug("  LangGraph agent compiled (%.1fs)", _time.time() - t0)

        # Build message list: [memory_context?] [prior turns...] [current question]
        prior: list[BaseMessage] = list(history or [])
        if memory_context is not None:
            if not prior:
                prior = [memory_context]

        state: MetadataAgentState = {
            "messages": prior + [HumanMessage(content=question)],
            "session_id": session_id,
            "catalog_context": [],
            "last_query_mql": "",
            "last_query_results": [],
        }
        logger.debug("  State ready — %d messages. Calling agent.ainvoke()...",
                     len(state["messages"]))

        result = await agent.ainvoke(state, {"recursion_limit": AGENT_RECURSION_LIMIT})
        logger.debug("  agent.ainvoke() RETURNED (%.1fs total)", _time.time() - t0)

        final_msg = result["messages"][-1]
        answer = final_msg.content if hasattr(final_msg, "content") else str(final_msg)
        logger.debug("  Answer: %d chars", len(answer))

        ep.add_turn("ai", answer)

        tool_calls_used = []
        for msg in result["messages"]:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls_used.append(tc.get("name", "unknown"))
        logger.debug("  Tools called: %s", tool_calls_used)

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
    import time as _time
    import sys
    t_start = _time.time()
    logger.debug("▶ run_metadata_query CALLED | q=%r | timeout=%ds", question[:60], timeout)

    def _thread_target():
        """
        Run the async MCP coroutine in a brand-new event loop inside its own
        dedicated thread — isolating it from Streamlit's event loop.

        Windows : ProactorEventLoop (default since Py 3.8) supports subprocess natively.
        Linux   : ThreadedChildWatcher routes SIGCHLD to the thread's loop (Py <3.12).
                  Python 3.12+ removed ThreadedChildWatcher; default policy works.
        """
        logger.debug("  Thread started | platform=%s | py=%s", sys.platform, sys.version.split()[0])
        loop = asyncio.new_event_loop()

        if sys.platform != "win32":
            try:
                watcher = asyncio.ThreadedChildWatcher()   # removed in Py 3.12
                asyncio.get_event_loop_policy().set_child_watcher(watcher)
                watcher.attach_loop(loop)
                logger.debug("  ThreadedChildWatcher attached (Python < 3.12)")
            except AttributeError:
                logger.debug("  No ThreadedChildWatcher needed (Python >= 3.12)")

        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                _run_with_mcp(question, session_id, history, memory_context)
            )
            logger.debug("  loop.run_until_complete DONE (%.1fs)", _time.time() - t_start)
            return result
        except Exception as _e:
            logger.exception("  Thread EXCEPTION: %s", _e)
            raise
        finally:
            loop.close()
            logger.debug("  Event loop closed")

    try:
        logger.debug("  Submitting to ThreadPoolExecutor (timeout=%ds)...", timeout)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_thread_target)
            result = future.result(timeout=timeout)
            logger.debug("✓ run_metadata_query done in %.1fs | mcp=%s | tools=%s",
                         _time.time() - t_start,
                         result.get("mcp_tools_active"),
                         result.get("tool_calls"))
            return result
    except concurrent.futures.TimeoutError:
        logger.warning("✗ run_metadata_query TIMEOUT after %ds — falling back to pymongo", timeout)
        return _run_pymongo_fallback(
            question, session_id, history,
            error=f"Agent timed out after {timeout}s. Using pymongo fallback.",
        )
    except BaseException as e:
        # Catch BaseException to handle BaseExceptionGroup from anyio/TaskGroup
        # that wraps MCP subprocess errors (e.g. BrokenResourceError).
        logger.exception("✗ run_metadata_query EXCEPTION: %s — falling back to pymongo", e)
        return _run_pymongo_fallback(question, session_id, history, error=str(e))


def _run_pymongo_fallback(
    question: str,
    session_id: str,
    history: list[BaseMessage] | None = None,
    error: str = "",
) -> dict:
    """Emergency sync fallback using only pymongo tools (no MCP, no async)."""
    logger.info("Running pymongo fallback | reason=%s", error)
    ep = EpisodicMemory("metadata_agent", session_id)
    ep.add_turn("human", question)

    agent = build_agent_with_tools(PYMONGO_FALLBACK_TOOLS, system_prompt=FALLBACK_SYSTEM_PROMPT)
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
