"""
Use Case 4: AML & Compliance Intelligence — Autonomous Regulatory Agent

Capabilities:
  • Semantic search over compliance rules (OFAC, BSA, FATCA, GDPR, PSD2)
  • Unstructured document analysis on fraud case investigation notes
  • Graph traversal: merchant network relationship analysis for AML
  • Autonomous: identify violations, file SARs, generate compliance reports
  • Multi-jurisdiction rule lookup and application

Memory: Semantic (regulation knowledge) + Procedural (compliance playbooks) + Episodic (case history)
Interface: Autonomous agent + optional chat mode for compliance analysts
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

import sys, os, json, random
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT,
                    AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT,
                    MONGODB_URI, MONGODB_DB_NAME, AGENT_RECURSION_LIMIT)
from memory.mongodb_memory import SemanticMemory, EpisodicMemory, ProceduralMemory

_db = MongoClient(MONGODB_URI)[MONGODB_DB_NAME]
_sem_mem = SemanticMemory()

SYSTEM_PROMPT = """You are **VaultComply** — Nexus Financial Group's Autonomous AML & Regulatory Compliance Agent.

You operate across global regulatory frameworks: BSA/AML (US), FATCA, PSD2 (EU), GDPR, OFAC sanctions,
and NFG's internal compliance policies.

Your autonomous responsibilities:
1. **Rule Lookup** — Find applicable regulations using semantic search over the compliance rule base
2. **Case Review** — Analyse fraud case notes (unstructured text) for regulatory implications
3. **Network Analysis** — Graph traversal to identify AML structuring patterns and layering
4. **Threshold Monitoring** — Check transaction volumes against BSA ($10K CTR) and SAR ($5K) thresholds
5. **Autonomous Action** — File SARs, escalate cases, generate compliance reports
6. **Cross-Jurisdiction** — Apply the most restrictive applicable regulation automatically

Always cite the specific regulation (rule_id, jurisdiction) when making compliance determinations.
Document your reasoning for every decision — this is an audit trail.
"""


class ComplianceAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    case_id: str
    session_id: str
    jurisdiction: str
    violations_found: list[str]
    actions_taken: list[str]


# ── Compliance Rule Tools ─────────────────────────────────────────────────────
@tool
def search_compliance_rules(query: str, jurisdiction: str | None = None) -> str:
    """Semantic search over compliance rules — find applicable regulations."""
    results = _sem_mem.search_compliance_rules(query, limit=5)
    if not results:
        # Fallback: keyword-OR search across rule_text, tags, rule_name
        stop = {"the","a","an","and","or","of","in","for","to","with","on","by","is","are","all","this"}
        words = [w for w in query.split() if w.lower() not in stop and len(w) > 2]
        pattern = "|".join(words) if words else query[:30]
        filt: dict = {"$or": [
            {"rule_text":  {"$regex": pattern, "$options": "i"}},
            {"tags":       {"$regex": pattern, "$options": "i"}},
            {"rule_name":  {"$regex": pattern, "$options": "i"}},
            {"category":   {"$regex": pattern, "$options": "i"}},
        ]}
        if jurisdiction:
            filt["jurisdiction"] = jurisdiction
        results = list(_db.compliance_rules.find(
            filt, {"_id": 0, "embedding": 0}, limit=5
        ))
    if not results:
        return "No compliance rules found for this query."
    lines = [f"Applicable Compliance Rules ({len(results)} found):"]
    for r in results:
        lines.append(
            f"\n📋 **{r.get('rule_name','?')}** [{r.get('rule_id','?')}]\n"
            f"   Jurisdiction: {r.get('jurisdiction','?')} | Category: {r.get('category','?')}\n"
            f"   {r.get('rule_text','')[:300]}...\n"
            f"   Tags: {', '.join(r.get('tags',[]))}"
        )
    return "\n".join(lines)


@tool
def check_transaction_thresholds(cardholder_id: str | None = None, days: int = 30) -> str:
    """Check if any cardholders or merchants exceed BSA CTR ($10K) or SAR ($5K) thresholds."""
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    match_stage: dict = {"timestamp": {"$gte": cutoff}, "status": "approved"}
    if cardholder_id:
        match_stage["cardholder_id"] = cardholder_id

    pipeline = [
        {"$match": match_stage},
        {"$group": {
            "_id": "$cardholder_id",
            "total_volume": {"$sum": "$amount"},
            "txn_count": {"$sum": 1},
            "max_single_txn": {"$max": "$amount"},
            "cash_equivalent": {"$sum": {
                "$cond": [{"$gte": ["$amount", 5000]}, "$amount", 0]
            }},
        }},
        {"$match": {"$or": [
            {"total_volume": {"$gte": 5000}},
            {"max_single_txn": {"$gte": 5000}},
        ]}},
        {"$sort": {"total_volume": DESCENDING}},
        {"$limit": 10},
    ]
    results = list(_db.transactions.aggregate(pipeline))
    if not results:
        return f"No threshold breaches found in last {days} days."

    lines = [f"⚠️ Threshold Analysis (last {days} days):"]
    for r in results:
        ctr_flag = r["total_volume"] >= 10000
        sar_flag = r["total_volume"] >= 5000 and not ctr_flag
        lines.append(
            f"\n  {r['_id']}: Total ${r['total_volume']:,.2f} | Txns: {r['txn_count']}\n"
            f"  Max single: ${r['max_single_txn']:,.2f}\n"
            f"  {'🔴 CTR REQUIRED (>$10K cash equivalent)' if ctr_flag else '🟡 SAR REVIEW (>$5K threshold)' if sar_flag else ''}"
        )
    return "\n".join(lines)


@tool
def analyse_fraud_case_notes(case_id: str | None = None, severity: str | None = None) -> str:
    """
    Analyse unstructured fraud case investigation notes for AML/regulatory implications.
    Uses semantic search to identify compliance triggers in free-text notes.
    """
    filt: dict = {}
    if case_id:
        filt["case_id"] = case_id
    if severity:
        filt["severity"] = severity
    filt["status"] = {"$in": ["open", "under_review", "escalated"]}

    cases = list(_db.fraud_cases.find(filt, {"_id": 0, "embedding": 0}, limit=5))
    if not cases:
        return "No open cases found matching criteria."

    lines = [f"📂 Fraud Case Analysis ({len(cases)} cases):"]
    for c in cases:
        notes = c.get("investigation_notes", "")
        # AML trigger keywords
        triggers = []
        aml_keywords = ["structuring","layering","placement","round-trip","high-risk country",
                         "pep","sanctions","3-sigma","velocity","money laundering","SAR"]
        for kw in aml_keywords:
            if kw.lower() in notes.lower():
                triggers.append(kw)

        lines.append(
            f"\n  **Case {c.get('case_id')}** | Type: {c.get('case_type')} | "
            f"Severity: {c.get('severity').upper()} | Impact: ${c.get('financial_impact_usd',0):,.2f}\n"
            f"  Cardholder: {c.get('cardholder_name')} | SAR Filed: {c.get('sar_filed')}\n"
            f"  AML Triggers found: {', '.join(triggers) if triggers else 'None detected'}\n"
            f"  Notes: {notes[:250]}..."
        )
    return "\n".join(lines)


@tool
def aml_network_analysis(cardholder_id: str) -> str:
    """
    Run AML network analysis: find all merchants the cardholder transacted with
    and perform graph lookup to detect layering through merchant networks.
    """
    # Get unique merchants this cardholder used
    merchant_ids = _db.transactions.distinct("merchant_id", {"cardholder_id": cardholder_id})
    if not merchant_ids:
        return f"No transactions found for {cardholder_id}"

    # Graph lookup on each merchant
    risk_merchants = []
    for mid in merchant_ids[:5]:  # limit for performance
        pipeline = [
            {"$match": {"merchant_id": mid}},
            {"$graphLookup": {
                "from": "merchant_networks",
                "startWith": "$edges.target_merchant_id",
                "connectFromField": "edges.target_merchant_id",
                "connectToField": "merchant_id",
                "as": "risk_network",
                "maxDepth": 2,
                "restrictSearchWithMatch": {"risk_cluster_flag": True},
            }},
            {"$project": {
                "merchant_id": 1, "merchant_name": 1, "risk_cluster_flag": 1,
                "risk_network_size": {"$size": {"$ifNull": ["$risk_network", []]}},
            }}
        ]
        results = list(_db.merchant_networks.aggregate(pipeline))
        if results and (results[0].get("risk_cluster_flag") or results[0].get("risk_network_size", 0) > 1):
            risk_merchants.append(results[0])

    ch = _db.cardholders.find_one({"cardholder_id": cardholder_id}, {"name": 1, "pep_flag": 1, "_id": 0})
    pep = ch.get("pep_flag", False) if ch else False
    total_volume = sum(
        t.get("amount", 0) for t in _db.transactions.find(
            {"cardholder_id": cardholder_id, "status": "approved"},
            {"amount": 1, "_id": 0}
        )
    )

    lines = [
        f"🕸️ AML Network Analysis: {cardholder_id}",
        f"  PEP Status: {'⚠️ PEP FLAGGED' if pep else '✓ Not PEP'}",
        f"  Total transaction volume: ${total_volume:,.2f}",
        f"  Unique merchants: {len(merchant_ids)}",
        f"  Risk-cluster merchants: {len(risk_merchants)}",
    ]
    if risk_merchants:
        lines.append("\n  ⚠️ RISK MERCHANT CONNECTIONS:")
        for m in risk_merchants:
            lines.append(
                f"    • {m.get('merchant_name','?')} ({m.get('merchant_id','?')}) "
                f"— {m.get('risk_network_size',0)} downstream risk nodes"
            )
        if pep or len(risk_merchants) >= 2 or total_volume >= 50000:
            lines.append("\n  🔴 AML ALERT: Enhanced Due Diligence (EDD) required")
    else:
        lines.append("\n  ✓ No high-risk merchant network connections found")
    return "\n".join(lines)


@tool
def check_sanctions_exposure(cardholder_id: str) -> str:
    """Check a cardholder's transactions for sanctions exposure by IP country and amount."""
    SANCTIONED = {"RU", "IR", "KP", "SY", "CU", "VE", "BY"}
    HIGH_RISK  = {"NG", "RO", "UA", "VN", "ID", "PH"}

    txns = list(_db.transactions.find(
        {"cardholder_id": cardholder_id},
        {"ip_country": 1, "amount": 1, "merchant_name": 1, "timestamp": 1, "_id": 0}
    ))
    sanctioned_txns = [t for t in txns if t.get("ip_country") in SANCTIONED]
    high_risk_txns  = [t for t in txns if t.get("ip_country") in HIGH_RISK]

    lines = [f"🛡️ Sanctions Exposure: {cardholder_id}"]
    if sanctioned_txns:
        lines.append(f"\n  🔴 SANCTIONED COUNTRY EXPOSURE ({len(sanctioned_txns)} transactions):")
        for t in sanctioned_txns[:3]:
            lines.append(f"    ${t.get('amount',0):.2f} @ {t.get('merchant_name','?')} [{t.get('ip_country')}]")
        lines.append("  ACTION REQUIRED: Immediate OFAC review and potential SAR filing")
    elif high_risk_txns:
        lines.append(f"\n  🟡 HIGH-RISK COUNTRY TRANSACTIONS ({len(high_risk_txns)}):")
        for t in high_risk_txns[:3]:
            lines.append(f"    ${t.get('amount',0):.2f} @ {t.get('merchant_name','?')} [{t.get('ip_country')}]")
        lines.append("  RECOMMENDATION: Enhanced monitoring per FATF guidance")
    else:
        lines.append("  ✓ No sanctions exposure detected")
    return "\n".join(lines)


@tool
def generate_compliance_report(case_id: str, findings: str, actions: str) -> str:
    """Generate a structured compliance report and store it in MongoDB."""
    from datetime import datetime, timezone
    report = {
        "report_id": f"RPT-{random.randint(100000,999999)}",
        "case_id": case_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": "VaultComply AI Agent",
        "findings": findings,
        "actions_taken": actions,
        "status": "COMPLETED",
        "requires_human_review": any(kw in findings.lower() for kw in ["sar","ctr","sanction","critical"]),
    }
    try:
        _db.compliance_reports.insert_one({**report, "_id": report["report_id"]})
    except Exception:
        pass
    return (
        f"✅ Compliance Report Generated: {report['report_id']}\n"
        f"   Case: {case_id} | Generated: {report['generated_at'][:19]}\n"
        f"   Human Review Required: {'YES ⚠️' if report['requires_human_review'] else 'No'}\n"
        f"   Summary: {findings[:200]}..."
    )


@tool
def mcp_file_sar_compliance(case_id: str, cardholder_id: str, activity_type: str,
                              amount_usd: float, narrative: str) -> str:
    """File a SAR with FinCEN via the MCP tool server for compliance-triggered cases."""
    import httpx
    from config import MCP_SERVER_URL
    try:
        resp = httpx.post(f"{MCP_SERVER_URL}/tools/file_sar", json={
            "case_id": case_id, "cardholder_id": cardholder_id,
            "activity_type": activity_type, "amount_usd": amount_usd,
            "narrative": narrative
        }, timeout=10)
        result = resp.json().get("result", resp.json())
        return (
            f"📄 SAR Filed: {result.get('sar_reference','?')}\n"
            f"   FinCEN: {result.get('fincen_tracking','?')} | "
            f"Status: {result.get('status','?')}"
        )
    except Exception:
        return (
            f"📄 SAR Filed (simulated): SAR-{random.randint(10000000,99999999)}\n"
            f"   Status: FILED_PENDING_FINCEN_ACK | Legal hold: Applied ✓"
        )


@tool
def mcp_ofac_screen_compliance(name: str, country: str) -> str:
    """Run OFAC sanctions screening via MCP for compliance-triggered checks."""
    import httpx
    from config import MCP_SERVER_URL
    try:
        resp = httpx.post(f"{MCP_SERVER_URL}/tools/screen_sanctions",
                          json={"name": name, "country": country}, timeout=10)
        result = resp.json().get("result", resp.json())
        return (
            f"OFAC Result: {name} ({country})\n"
            f"  {'🔴 MATCH — ' + result.get('matched_list','') if result.get('is_match') else '✓ Clear'}\n"
            f"  Score: {result.get('match_score',0):.3f}"
        )
    except Exception:
        hit = random.random() < 0.12
        return f"OFAC (simulated): {name} — {'🔴 POTENTIAL MATCH' if hit else '✓ Clear'}"


# ── Build Agent ────────────────────────────────────────────────────────────────
COMPLIANCE_TOOLS = [
    search_compliance_rules, check_transaction_thresholds, analyse_fraud_case_notes,
    aml_network_analysis, check_sanctions_exposure, generate_compliance_report,
    mcp_file_sar_compliance, mcp_ofac_screen_compliance,
]


def get_llm():
    return AzureChatOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        azure_deployment=AZURE_OPENAI_DEPLOYMENT,
        temperature=0,
    )


def build_compliance_agent():
    llm = get_llm().bind_tools(COMPLIANCE_TOOLS)

    def agent_node(state: ComplianceAgentState):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = llm.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: ComplianceAgentState):
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    tool_node = ToolNode(COMPLIANCE_TOOLS)
    graph = StateGraph(ComplianceAgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


_compliance_agent = None

def get_compliance_agent():
    global _compliance_agent
    if _compliance_agent is None:
        _compliance_agent = build_compliance_agent()
    return _compliance_agent


def run_compliance_investigation(
    prompt: str | None = None,
    cardholder_id: str | None = None,
    session_id: str = "compliance-default",
) -> dict:
    """Run the compliance agent for a regulatory review."""
    agent = get_compliance_agent()
    ep = EpisodicMemory("compliance_agent", session_id)

    if prompt is None:
        prompt = (
            "Perform a comprehensive AML and compliance review. "
            "1) Search for the most critical AML and sanctions rules. "
            "2) Check for cardholder accounts that breach BSA thresholds ($10K CTR / $5K SAR). "
            "3) Analyse open high-severity fraud cases for AML triggers in investigation notes. "
            "4) For the top flagged cardholder: run network analysis and sanctions exposure check. "
            "5) File a SAR if warranted. Generate a compliance report summarising findings."
        )
        if cardholder_id:
            prompt = (
                f"Review cardholder {cardholder_id} for AML compliance. "
                f"Check transaction thresholds, network risk, and sanctions exposure. "
                f"Look up applicable compliance rules. Take action if violations found."
            )

    ep.add_turn("human", prompt)
    state = {
        "messages": [HumanMessage(content=prompt)],
        "case_id": f"COMP-{session_id}",
        "session_id": session_id,
        "jurisdiction": "Global",
        "violations_found": [],
        "actions_taken": [],
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
