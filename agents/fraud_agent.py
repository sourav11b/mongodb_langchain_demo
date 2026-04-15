"""
Use Case 2: Fraud Intelligence — Autonomous Multi-Step Fraud Detection Agent

Capabilities:
  • Scan recent transactions for fraud signals (time-series + ML score)
  • Geo-velocity impossible-travel detection (geospatial)
  • Graph traversal for merchant fraud-ring connections
  • Autonomous remediation: block cards, file SARs, notify cardholders
  • All actions via FastMCP tool calls

Memory: Episodic (case history) + Procedural (fraud playbooks) + Working (LangGraph state)
Interface: Autonomous agent — triggered programmatically or via UI "Investigate" button
"""

from __future__ import annotations
import json, random
from typing import Annotated, TypedDict, Literal

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pymongo import MongoClient, DESCENDING

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT,
                    AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT,
                    MONGODB_URI, MONGODB_DB_NAME, AGENT_RECURSION_LIMIT)
from memory.mongodb_memory import ProceduralMemory, EpisodicMemory

_db = MongoClient(MONGODB_URI)[MONGODB_DB_NAME]
_proc_mem = ProceduralMemory()

SYSTEM_PROMPT = """You are **VaultShield** — Nexus Financial Group's Autonomous Fraud Intelligence Agent.

Your mission: protect cardholders and the NFG network by autonomously detecting, investigating,
and remediating fraud in real-time.

You follow a structured investigation process:
1. **Detect** — Identify high-risk transactions using fraud scores and velocity rules
2. **Investigate** — Cross-reference with geo data, merchant networks, and cardholder history
3. **Decide** — Apply fraud playbooks to determine the appropriate response
4. **Act** — Take autonomous action: block cards, notify cardholders, file SARs as needed
5. **Report** — Produce a clear investigation summary with evidence and actions taken

You have access to:
- MongoDB transaction data (time-series, geo, fraud scores)
- Merchant network graph for fraud-ring detection
- External MCP tools: OFAC screening, card blocking, SAR filing, notifications

Always be decisive. When fraud confidence > 80%, act immediately. Document everything.
"""


# ── Agent State ────────────────────────────────────────────────────────────────
class FraudAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    case_id: str
    cardholder_id: str
    fraud_type: str
    severity: str
    actions_taken: list[str]
    investigation_complete: bool


# ── MongoDB Query Tools ────────────────────────────────────────────────────────
@tool
def get_recent_transactions(cardholder_id: str, limit: int = 10) -> str:
    """Retrieve recent transactions for a cardholder, ordered by timestamp descending."""
    txns = list(_db.transactions.find(
        {"cardholder_id": cardholder_id},
        {"_id": 0, "embedding": 0},
        sort=[("timestamp", DESCENDING)],
        limit=min(limit, 20)
    ))
    if not txns:
        return f"No transactions found for {cardholder_id}"
    lines = [f"Last {len(txns)} transactions for {cardholder_id}:"]
    for t in txns:
        flag = "🚨 FLAGGED" if t.get("is_flagged") else ""
        ts = t.get("timestamp", "?")
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if hasattr(ts, "strftime") else str(ts)[:19]
        lines.append(
            f"  {ts_str} | ${t.get('amount',0):>10.2f} | "
            f"{str(t.get('merchant_name','?'))[:25]:<25} | {str(t.get('channel','?')):<12} | "
            f"Score:{t.get('fraud_score',0):.3f} | {t.get('status','?')} {flag}"
        )
    return "\n".join(lines)


@tool
def get_flagged_transactions(min_fraud_score: float = 0.65, limit: int = 15) -> str:
    """Get all recently flagged transactions above a fraud score threshold."""
    txns = list(_db.transactions.find(
        {"fraud_score": {"$gte": min_fraud_score}},
        {"_id": 0, "embedding": 0},
        sort=[("fraud_score", DESCENDING)],
        limit=min(limit, 25)
    ))
    if not txns:
        return f"No transactions with fraud score ≥ {min_fraud_score}"
    lines = [f"Found {len(txns)} high-risk transactions (score ≥ {min_fraud_score}):"]
    for t in txns:
        lines.append(
            f"  🚨 {t.get('cardholder_id')} | ${t.get('amount',0):>9.2f} | "
            f"{str(t.get('merchant_name','?'))[:20]:<20} | Score:{t.get('fraud_score',0):.3f} | "
            f"IP:{t.get('ip_country','?')} | {t.get('channel','?')}"
        )
    return "\n".join(lines)


@tool
def check_transaction_velocity(cardholder_id: str, hours: int = 1) -> str:
    """Check transaction velocity — number of transactions in the last N hours."""
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    txns = list(_db.transactions.find({
        "cardholder_id": cardholder_id,
        "timestamp": {"$gte": cutoff},
    }, {"_id": 0, "amount": 1, "channel": 1, "status": 1, "merchant_name": 1}))

    total = sum(t.get("amount", 0) for t in txns)
    declined = sum(1 for t in txns if t.get("status") == "declined")
    cnp = sum(1 for t in txns if t.get("channel") == "online")
    alert = (len(txns) > 5) or (declined > 2) or (cnp > 4)
    return (
        f"Velocity check for {cardholder_id} (last {hours}h):\n"
        f"  Transactions: {len(txns)} | Total: ${total:.2f}\n"
        f"  Declined: {declined} | Online/CNP: {cnp}\n"
        f"  {'⚠️ VELOCITY ALERT — suspicious activity pattern' if alert else '✓ Normal velocity'}"
    )


@tool
def get_cardholder_profile(cardholder_id: str) -> str:
    """Retrieve a cardholder's profile including risk score, tier, and PEP status."""
    ch = _db.cardholders.find_one(
        {"cardholder_id": cardholder_id},
        {"_id": 0, "embedding": 0}
    )
    if not ch:
        return f"Cardholder {cardholder_id} not found."
    return (
        f"Cardholder: {ch.get('name')} ({cardholder_id})\n"
        f"  Tier: {ch.get('card_tier')} | KYC: {'✓' if ch.get('kyc_verified') else '✗'} | "
        f"PEP: {'⚠️ YES' if ch.get('pep_flag') else 'No'}\n"
        f"  Home: {ch.get('home_city')} | Risk Score: {ch.get('risk_score',0):.3f}\n"
        f"  Annual Spend: ${ch.get('annual_spend_usd',0):,.2f}"
    )


@tool
def check_merchant_fraud_ring(merchant_id: str) -> str:
    """Use $graphLookup to check if a merchant is connected to a fraud ring."""
    pipeline = [
        {"$match": {"merchant_id": merchant_id}},
        {"$graphLookup": {
            "from": "merchant_networks",
            "startWith": "$edges.target_merchant_id",
            "connectFromField": "edges.target_merchant_id",
            "connectToField": "merchant_id",
            "as": "network",
            "maxDepth": 2,
            "restrictSearchWithMatch": {"risk_cluster_flag": True},
        }},
        {"$project": {
            "merchant_name": 1, "risk_cluster_flag": 1, "cluster_id": 1,
            "ring_connections": {"$size": {"$ifNull": ["$network", []]}},
            "top_connections": {"$slice": [{"$ifNull": ["$network.merchant_name", []]}, 3]},
        }}
    ]
    results = list(_db.merchant_networks.aggregate(pipeline))
    if not results:
        return f"Merchant {merchant_id} not found in network graph."
    r = results[0]
    ring_size = r.get("ring_connections", 0)
    in_ring = r.get("risk_cluster_flag", False) or ring_size > 2
    return (
        f"Merchant Network Analysis: {r.get('merchant_name','?')} ({merchant_id})\n"
        f"  Cluster: {r.get('cluster_id','?')} | Risk Cluster: {'⚠️ YES' if r.get('risk_cluster_flag') else 'No'}\n"
        f"  Connected risk nodes: {ring_size}\n"
        f"  {'🚨 FRAUD RING DETECTED — merchant connected to {ring_size} risk nodes' if in_ring else '✓ No fraud ring connection'}\n"
        f"  Connected merchants: {', '.join(r.get('top_connections',[]))}"
    )


@tool
def timeseries_fraud_trend(cardholder_id: str | None = None, days: int = 30) -> str:
    """Aggregate fraud score trends over time (time-series analysis)."""
    match_stage: dict = {}
    if cardholder_id:
        match_stage["cardholder_id"] = cardholder_id
    pipeline = [
        {"$match": match_stage},
        {"$addFields": {
            "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}}
        }},
        {"$group": {
            "_id": "$date",
            "avg_fraud_score": {"$avg": "$fraud_score"},
            "flagged_count": {"$sum": {"$cond": ["$is_flagged", 1, 0]}},
            "total_amount": {"$sum": "$amount"},
            "txn_count": {"$sum": 1},
        }},
        {"$sort": {"_id": DESCENDING}},
        {"$limit": days},
    ]
    results = list(_db.transactions.aggregate(pipeline))
    if not results:
        return "No time-series data available."
    lines = [f"Fraud Trend (last {len(results)} days):"]
    for r in sorted(results, key=lambda x: x["_id"]):
        bar = "█" * int(r.get("avg_fraud_score", 0) * 20)
        lines.append(
            f"  {r['_id']} | Score:{r.get('avg_fraud_score',0):.3f} {bar:<20} | "
            f"Flagged:{r.get('flagged_count',0):>3} | Txns:{r.get('txn_count',0):>3}"
        )
    return "\n".join(lines)


# ── MCP Tool Wrappers (calls FastMCP server) ──────────────────────────────────
@tool
def mcp_screen_sanctions(name: str, country: str, transaction_id: str | None = None) -> str:
    """Screen a person/entity against OFAC sanctions via MCP tool server."""
    import httpx
    from config import MCP_SERVER_URL
    try:
        resp = httpx.post(f"{MCP_SERVER_URL}/tools/screen_sanctions", json={
            "name": name, "country": country, "transaction_id": transaction_id
        }, timeout=10)
        data = resp.json()
        result = data.get("result", data)
        is_match = result.get("is_match", False)
        return (
            f"OFAC Screening: {name} ({country})\n"
            f"  Match Score: {result.get('match_score',0):.3f}\n"
            f"  {'🚨 MATCH FOUND — ' + result.get('matched_list','') if is_match else '✓ CLEAR — no sanctions match'}\n"
            f"  Action: {result.get('action_required','UNKNOWN')}"
        )
    except Exception as e:
        # Demo fallback: simulate response
        hit = random.random() < 0.1 if country not in ["NG","RO","UA"] else random.random() < 0.4
        return (
            f"OFAC Screening (simulated): {name} ({country})\n"
            f"  {'🚨 POTENTIAL MATCH — manual review required' if hit else '✓ CLEAR'}"
        )


@tool
def mcp_block_card(cardholder_id: str, reason: str, case_id: str | None = None, temporary: bool = True) -> str:
    """Block a cardholder's NFG card via MCP tool server."""
    import httpx
    from config import MCP_SERVER_URL
    try:
        resp = httpx.post(f"{MCP_SERVER_URL}/tools/block_card", json={
            "cardholder_id": cardholder_id, "reason": reason,
            "case_id": case_id, "temporary": temporary
        }, timeout=10)
        data = resp.json()
        result = data.get("result", data)
        return (
            f"Card {'Hold' if temporary else 'Block'}: {cardholder_id}\n"
            f"  Reference: {result.get('reference_number','?')}\n"
            f"  Status: {result.get('status','?')}\n"
            f"  Notifications: {', '.join(result.get('notification_channels',[]))}"
        )
    except Exception:
        ref = f"BLK-{random.randint(100000,999999)}"
        return (
            f"Card {'Hold' if temporary else 'Block'} (simulated): {cardholder_id}\n"
            f"  Reference: {ref} | Status: SUCCESS\n"
            f"  Notifications sent via: SMS, push, email"
        )


@tool
def mcp_send_notification(cardholder_id: str, message: str, channel: str = "push") -> str:
    """Send push/SMS notification to cardholder via MCP tool server."""
    import httpx
    from config import MCP_SERVER_URL
    try:
        resp = httpx.post(f"{MCP_SERVER_URL}/tools/send_notification", json={
            "cardholder_id": cardholder_id, "message": message,
            "channel": channel, "priority": "urgent"
        }, timeout=10)
        data = resp.json()
        result = data.get("result", data)
        return f"Notification sent to {cardholder_id} via {channel}: {result.get('notification_id','?')}"
    except Exception:
        return f"Notification (simulated) sent to {cardholder_id} via {channel} ✓"


@tool
def mcp_file_sar(case_id: str, cardholder_id: str, activity_type: str,
                  amount_usd: float, narrative: str) -> str:
    """File a Suspicious Activity Report (SAR) with FinCEN via MCP tool server."""
    import httpx
    from config import MCP_SERVER_URL
    try:
        resp = httpx.post(f"{MCP_SERVER_URL}/tools/file_sar", json={
            "case_id": case_id, "cardholder_id": cardholder_id,
            "activity_type": activity_type, "amount_usd": amount_usd,
            "narrative": narrative
        }, timeout=10)
        data = resp.json()
        result = data.get("result", data)
        return (
            f"SAR Filed: {result.get('sar_reference','?')}\n"
            f"  FinCEN Tracking: {result.get('fincen_tracking','?')}\n"
            f"  Status: {result.get('status','?')}"
        )
    except Exception:
        sar_ref = f"SAR-{random.randint(10000000,99999999)}"
        return (
            f"SAR Filed (simulated): {sar_ref}\n"
            f"  Status: FILED_PENDING_FINCEN_ACK | Legal hold applied ✓"
        )


@tool
def get_fraud_playbook(fraud_type: str) -> str:
    """Retrieve the procedural memory playbook for a specific fraud type."""
    steps = ProceduralMemory.get_fraud_playbook(fraud_type)
    return (
        f"Fraud Playbook — {fraud_type.replace('_',' ').title()}:\n"
        + "\n".join(steps)
    )


# ── Build LangGraph Fraud Agent ────────────────────────────────────────────────
FRAUD_TOOLS = [
    get_recent_transactions,
    get_flagged_transactions,
    check_transaction_velocity,
    get_cardholder_profile,
    check_merchant_fraud_ring,
    timeseries_fraud_trend,
    mcp_screen_sanctions,
    mcp_block_card,
    mcp_send_notification,
    mcp_file_sar,
    get_fraud_playbook,
]


def get_llm():
    return AzureChatOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_deployment=AZURE_OPENAI_DEPLOYMENT,
        temperature=0,
    )


def build_fraud_agent():
    llm = get_llm().bind_tools(FRAUD_TOOLS)

    def agent_node(state: FraudAgentState):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = llm.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: FraudAgentState) -> Literal["tools", "__end__"]:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    tool_node = ToolNode(FRAUD_TOOLS)
    graph = StateGraph(FraudAgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


_fraud_agent = None

def get_fraud_agent():
    global _fraud_agent
    if _fraud_agent is None:
        _fraud_agent = build_fraud_agent()
    return _fraud_agent


def run_fraud_investigation(
    trigger: str = "scan",
    cardholder_id: str | None = None,
    session_id: str = "fraud-default",
) -> dict:
    """Run the fraud agent. trigger can be 'scan' (full scan) or a specific cardholder."""
    agent = get_fraud_agent()
    ep = EpisodicMemory("fraud_agent", session_id)

    if trigger == "scan":
        prompt = (
            "Perform a comprehensive fraud scan. Start by retrieving all flagged transactions "
            "(score ≥ 0.70). For the top 2-3 riskiest cases: investigate the cardholder profile, "
            "check transaction velocity, verify the merchant isn't in a fraud ring, run OFAC screening, "
            "and take appropriate autonomous action (block card, notify, file SAR if needed). "
            "Provide a structured investigation report at the end."
        )
    else:
        prompt = (
            f"Investigate cardholder {cardholder_id}. Retrieve their recent transactions, "
            f"check velocity, profile, and merchant risk. Get the relevant fraud playbook. "
            f"Take autonomous protective action if fraud is confirmed. Summarise findings."
        )

    ep.add_turn("human", prompt)
    state = {
        "messages": [HumanMessage(content=prompt)],
        "case_id": f"AUTO-{session_id}",
        "cardholder_id": cardholder_id or "SCAN",
        "fraud_type": "unknown",
        "severity": "unknown",
        "actions_taken": [],
        "investigation_complete": False,
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
    }
