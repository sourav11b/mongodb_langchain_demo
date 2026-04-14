"""
FastMCP server exposing mock external tool calls used by NFG AI agents.
Simulates: credit bureau, OFAC sanctions, push notify, card block,
           geo-alert, AML SAR filing, merchant risk check.

Run standalone:  python -m tools.mcp_server
Accessed by agents via HTTP at http://localhost:8100/mcp/
"""

from __future__ import annotations
import random, time
from datetime import datetime, timezone
from typing import Annotated

import os, sys
from fastmcp import FastMCP

mcp = FastMCP(
    name="VaultIQAgentTools",
    instructions=(
        "External tool integrations for VaultIQ AI agents. "
        "Use these tools to perform actions like blocking cards, filing SARs, "
        "screening against sanctions lists, and verifying cardholder identity."
    ),
)


# ── 1. OFAC / Sanctions Screening ─────────────────────────────────────────────
@mcp.tool()
def screen_sanctions(
    name: Annotated[str, "Full name of individual or entity to screen"],
    country: Annotated[str, "ISO country code (e.g. US, RU, IR)"],
    transaction_id: Annotated[str | None, "Associated transaction ID"] = None,
) -> dict:
    """Screen a name + country against OFAC SDN and global sanctions lists."""
    HIGH_RISK = {"RU", "IR", "KP", "SY", "CU", "VE", "BY"}
    match_score = random.uniform(0.0, 0.15) if country not in HIGH_RISK else random.uniform(0.1, 0.6)
    is_match = match_score > 0.4

    return {
        "screened_name": name,
        "country": country,
        "transaction_id": transaction_id,
        "match_score": round(match_score, 3),
        "is_match": is_match,
        "matched_list": "OFAC SDN" if is_match else None,
        "matched_entry": f"SDN-{random.randint(10000,99999)}" if is_match else None,
        "action_required": "BLOCK_AND_REPORT" if is_match else "CLEAR",
        "screened_at": datetime.now(timezone.utc).isoformat(),
        "source": "OFAC_SDN_v2024.11 | EU_SANCTIONS | UN_CONSOLIDATED",
    }


# ── 2. Credit Bureau Lookup ────────────────────────────────────────────────────
@mcp.tool()
def credit_bureau_lookup(
    cardholder_id: Annotated[str, "NFG cardholder ID (e.g. CH_0001)"],
    bureau: Annotated[str, "Credit bureau: experian | equifax | transunion"] = "experian",
) -> dict:
    """Fetch credit profile summary from a credit bureau for risk assessment."""
    score = random.randint(520, 850)
    return {
        "cardholder_id": cardholder_id,
        "bureau": bureau,
        "credit_score": score,
        "score_band": "Excellent" if score >= 750 else "Good" if score >= 670 else "Fair" if score >= 580 else "Poor",
        "derogatory_marks": random.randint(0, 3),
        "open_accounts": random.randint(3, 15),
        "credit_utilization_pct": round(random.uniform(5, 85), 1),
        "hard_inquiries_6m": random.randint(0, 5),
        "bankruptcy_flag": random.random() < 0.03,
        "collections": random.randint(0, 2),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


# ── 3. Block / Freeze Card ────────────────────────────────────────────────────
@mcp.tool()
def block_card(
    cardholder_id: Annotated[str, "Cardholder ID whose card to block"],
    reason: Annotated[str, "Reason for block: fraud_suspected | compliance | cardholder_request | aml"],
    case_id: Annotated[str | None, "Associated fraud/compliance case ID"] = None,
    temporary: Annotated[bool, "True for temporary hold, False for permanent block"] = True,
) -> dict:
    """Block or temporarily freeze an NFG card. Triggers cardholder notification."""
    action = "TEMPORARY_HOLD" if temporary else "PERMANENT_BLOCK"
    ref = f"BLK-{random.randint(100000,999999)}"
    return {
        "cardholder_id": cardholder_id,
        "action": action,
        "reason": reason,
        "case_id": case_id,
        "reference_number": ref,
        "notification_sent": True,
        "notification_channels": ["SMS", "push", "email"],
        "effective_at": datetime.now(timezone.utc).isoformat(),
        "reversal_url": f"https://api.nexusfinancial.internal/cards/unblock/{ref}",
        "status": "SUCCESS",
    }


# ── 4. Push / SMS Notification ────────────────────────────────────────────────
@mcp.tool()
def send_notification(
    cardholder_id: Annotated[str, "Cardholder ID to notify"],
    message: Annotated[str, "Notification message text (max 160 chars for SMS)"],
    channel: Annotated[str, "Channel: push | sms | email | all"] = "push",
    priority: Annotated[str, "Priority: normal | high | urgent"] = "normal",
) -> dict:
    """Send a push/SMS/email notification to an NFG cardholder."""
    notif_id = f"NOTIF-{random.randint(100000,999999)}"
    return {
        "notification_id": notif_id,
        "cardholder_id": cardholder_id,
        "channel": channel,
        "priority": priority,
        "message_preview": message[:80] + ("..." if len(message) > 80 else ""),
        "delivered": random.random() > 0.02,
        "delivery_latency_ms": random.randint(50, 800),
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


# ── 5. File SAR (Suspicious Activity Report) ──────────────────────────────────
@mcp.tool()
def file_sar(
    case_id: Annotated[str, "Internal case ID"],
    cardholder_id: Annotated[str, "Cardholder ID involved"],
    activity_type: Annotated[str, "Type: structuring | money_laundering | fraud | terrorist_financing"],
    amount_usd: Annotated[float, "Total suspicious amount in USD"],
    narrative: Annotated[str, "Investigator narrative describing the suspicious activity"],
) -> dict:
    """File a Suspicious Activity Report (SAR) with FinCEN for AML compliance."""
    sar_ref = f"SAR-{random.randint(10000000,99999999)}"
    return {
        "sar_reference": sar_ref,
        "case_id": case_id,
        "cardholder_id": cardholder_id,
        "activity_type": activity_type,
        "amount_usd": amount_usd,
        "filing_deadline": "Within 30 days of detection",
        "status": "FILED_PENDING_FINCEN_ACK",
        "fincen_tracking": f"FCN-{random.randint(100000,999999)}",
        "filed_at": datetime.now(timezone.utc).isoformat(),
        "narrative_length": len(narrative),
        "legal_hold_applied": True,
    }


# ── 6. Merchant Risk Check ─────────────────────────────────────────────────────
@mcp.tool()
def merchant_risk_check(
    merchant_id: Annotated[str, "Merchant ID to check"],
    check_type: Annotated[str, "Type: chargeback_ratio | fraud_ring | ownership | all"] = "all",
) -> dict:
    """Run a comprehensive risk check on a merchant across NFG risk systems."""
    chargeback = round(random.uniform(0.001, 0.035), 4)
    return {
        "merchant_id": merchant_id,
        "check_type": check_type,
        "chargeback_ratio": chargeback,
        "chargeback_risk": "HIGH" if chargeback > 0.02 else "MEDIUM" if chargeback > 0.01 else "LOW",
        "fraud_ring_connection": random.random() < 0.12,
        "known_fraud_network": f"NET-{random.randint(100,999)}" if random.random() < 0.08 else None,
        "ownership_verified": random.random() > 0.05,
        "pep_connection": random.random() < 0.04,
        "risk_score": round(random.uniform(0.01, 0.95), 3),
        "recommended_action": random.choice(["MONITOR","ENHANCED_REVIEW","SUSPEND","TERMINATE"]),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


# ── 7. Geo-Velocity Alert ─────────────────────────────────────────────────────
@mcp.tool()
def geo_velocity_check(
    cardholder_id: Annotated[str, "Cardholder ID"],
    current_lon: Annotated[float, "Current transaction longitude"],
    current_lat: Annotated[float, "Current transaction latitude"],
    prev_lon: Annotated[float, "Previous transaction longitude"],
    prev_lat: Annotated[float, "Previous transaction latitude"],
    time_gap_minutes: Annotated[float, "Minutes between transactions"],
) -> dict:
    """Check if cardholder could physically have moved between two transaction locations."""
    import math
    R = 6371
    phi1, phi2 = math.radians(prev_lat), math.radians(current_lat)
    dphi = math.radians(current_lat - prev_lat)
    dlambda = math.radians(current_lon - prev_lon)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    distance_km = 2 * R * math.asin(math.sqrt(a))
    required_speed_kmh = (distance_km / max(time_gap_minutes, 0.1)) * 60
    is_impossible = required_speed_kmh > 1000
    return {
        "cardholder_id": cardholder_id,
        "distance_km": round(distance_km, 2),
        "time_gap_minutes": time_gap_minutes,
        "required_speed_kmh": round(required_speed_kmh, 1),
        "is_impossible_travel": is_impossible,
        "alert_level": "CRITICAL" if is_impossible else "CLEAR",
        "recommendation": "FRAUD_REVIEW" if is_impossible else "APPROVED",
    }


# ── Run server ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from config import MCP_SERVER_HOST, MCP_SERVER_PORT
    mcp.run(transport="streamable-http", host=MCP_SERVER_HOST, port=MCP_SERVER_PORT)
