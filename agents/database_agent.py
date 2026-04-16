"""
Use Case 5: Natural-Language Database Agent — MongoDBDatabaseToolkit

Uses the official LangChain MongoDBDatabaseToolkit to let users query any
MongoDB collection using natural language. The toolkit auto-generates and
executes MQL queries, validates them with an LLM checker, and returns results.

Tools provided by the toolkit:
  • InfoMongoDBDatabaseTool      — discover collections, schemas, sample docs
  • QueryMongoDBDatabaseTool     — execute generated MQL against the database
  • QueryMongoDBCheckerTool      — LLM-powered query validation before execution
  • ListMongoDBDatabaseTool      — list available collections

Architecture:
  LangGraph ReAct agent → MongoDBDatabaseToolkit tools → MongoDB Atlas
"""

from __future__ import annotations

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI
from langchain_mongodb.agent_toolkit import (
    MongoDBDatabaseToolkit,
    MongoDBDatabase,
    MONGODB_AGENT_SYSTEM_PROMPT,
)
from langgraph.prebuilt import create_react_agent

from config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT,
    MONGODB_URI,
    MONGODB_DB_NAME,
    AGENT_RECURSION_LIMIT,
)
from memory.mongodb_memory import EpisodicMemory

logger = logging.getLogger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = MONGODB_AGENT_SYSTEM_PROMPT.format(top_k=5) + """

ADDITIONAL CONTEXT — Nexus Financial Group (NFG) Database:
You are querying the VaultIQ financial database. Key collections:

| Collection           | Description                                         |
|----------------------|-----------------------------------------------------|
| cardholders          | Customer profiles (tier, city, status, spend)        |
| transactions         | Payment records (amount, merchant, fraud_score, geo) |
| merchants            | Merchant info (category, risk tier, location)        |
| offers               | Personalised card offers (benefits, tiers)           |
| fraud_cases          | Fraud investigation cases (status, notes)            |
| compliance_rules     | Regulatory rules (BSA, OFAC, GDPR, FATCA, PSD2)     |
| merchant_networks    | Graph edges between merchants (ownership, risk)      |
| data_catalog         | Metadata about all collections and fields            |
| conversation_history | Episodic memory — past agent interactions            |

When answering:
- Always start by listing collections or inspecting schema before querying.
- Format results clearly with amounts as currency, dates as readable.
- Use aggregation pipelines ($group, $sort, $match) for analytics.
- Limit results to top_k=5 unless the user asks for more.
- Explain what MQL you generated and why.
"""


def _get_llm():
    return AzureChatOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_deployment=AZURE_OPENAI_DEPLOYMENT,
        temperature=0,
    )


def _get_toolkit():
    """Create the MongoDBDatabaseToolkit connected to our Atlas cluster."""
    db = MongoDBDatabase.from_connection_string(
        MONGODB_URI,
        database=MONGODB_DB_NAME,
    )
    llm = _get_llm()
    return MongoDBDatabaseToolkit(db=db, llm=llm)


_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        toolkit = _get_toolkit()
        tools = toolkit.get_tools()
        llm = _get_llm()
        _agent = create_react_agent(
            llm,
            tools,
            prompt=SystemMessage(content=SYSTEM_PROMPT),
        )
        logger.info(
            "Database agent created with %d toolkit tools: %s",
            len(tools),
            [t.name for t in tools],
        )
    return _agent


def get_toolkit_tool_names() -> list[str]:
    """Return the list of tool names provided by the toolkit (for UI display)."""
    toolkit = _get_toolkit()
    return [t.name for t in toolkit.get_tools()]


def run_database_query(
    question: str,
    session_id: str = "db-default",
) -> dict:
    """Run a natural-language query against MongoDB via the toolkit agent.

    Returns dict with keys: answer, tool_calls, messages
    """
    agent = _get_agent()
    ep = EpisodicMemory("database_agent", session_id)
    ep.add_turn("human", question)

    state = {"messages": [HumanMessage(content=question)]}
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
    }
