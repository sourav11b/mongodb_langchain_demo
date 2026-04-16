"""
NiceGUI — Fraud Intelligence page  (/fraud)
Matches the Streamlit Fraud Intelligence page: scenario injection sidebar,
investigation pipeline info, cardholder select, formatted result output.
"""
from __future__ import annotations
import sys, os, logging, asyncio
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nicegui import ui, app
from nicegui_app.theme import (inject_css, nav_bar, page_header, render_tool_chips,
                               show_spinner, render_answer_box, _md_to_html)

logger = logging.getLogger("vaultiq.nicegui.fraud")

# ── Scenario definitions (mirrors Streamlit page) ────────────────────────────
FRAUD_SCENARIOS = {
    "🛒 Card-Not-Present Burst": {
        "id": "cnp_burst",
        "desc": "8 rapid online transactions across 5 countries in 20 min — classic CNP fraud.",
        "cardholder_id": "CH_DEMO_CNP_001",
    },
    "🔐 Account Takeover (ATO)": {
        "id": "ato_attack",
        "desc": "Password reset from new device, then immediate high-value purchases.",
        "cardholder_id": "CH_DEMO_ATO_001",
    },
    "🕸️ Merchant Fraud Ring": {
        "id": "merchant_ring",
        "desc": "3 shell merchants laundering money through circular transactions ($graphLookup).",
        "cardholder_id": "CH_DEMO_RING_001",
    },
    "✈️ Impossible Travel": {
        "id": "impossible_travel",
        "desc": "In-store London, then Tokyo 45 min later — physically impossible.",
        "cardholder_id": "CH_DEMO_TRAVEL_001",
    },
    "🏛️ Sanctions / PEP Hit": {
        "id": "sanctions_pep",
        "desc": "PEP with transactions to sanctioned regions — triggers OFAC screening.",
        "cardholder_id": "CH_DEMO_PEP_001",
    },
}


@ui.page("/fraud")
async def fraud_page():
    await ui.context.client.connected()
    inject_css()
    nav_bar("/fraud")

    page_header(
        "🚨 Use Case 2: Fraud Intelligence Agent",
        "Autonomous multi-step fraud detection, investigation, and remediation",
        '<span class="blog-feature-tag bft-vector">🔵 Atlas Vector Search</span>'
        '<span class="blog-feature-tag bft-ckpt">🟣 MongoDB Checkpointer</span>'
        '<span class="blog-feature-tag bft-smith">🔴 LangSmith Observability</span>',
    )

    # ── Sidebar: scenario injection ───────────────────────────────────────
    with ui.left_drawer(value=True).style(
        "width:310px; background:linear-gradient(180deg,#7f1d1d,#b91c1c);"
    ):
        ui.label("🧪 Fraud Scenario Injection").classes("text-white text-lg font-bold mt-4")
        ui.html('<p style="color:rgba(255,255,255,.7);font-size:.78rem;">Inject realistic fraud '
                'patterns into MongoDB so the agent has live data to detect and investigate.</p>')

        for key, sc in FRAUD_SCENARIOS.items():
            with ui.expansion(key).classes("w-full bg-white/90 rounded my-1"):
                ui.label(sc["desc"]).classes("text-xs text-gray-700")
                ui.label(f"cardholder_id: {sc['cardholder_id']}").classes("text-xs font-mono text-gray-500")
                ui.button("💉 Inject", color="orange",
                          on_click=lambda k=key: _inject(k)).props("dense size=sm").classes("mt-1")

        ui.separator().classes("bg-white/20 my-2")
        ui.button("🗑️ Clear All Injected Scenarios",
                  on_click=_clear_injected, color="white").props("outline dense size=sm")
        injected_label = ui.label("").classes("text-white/70 text-xs mt-1")

    # ── Info columns: pipeline + memory ───────────────────────────────────
    with ui.row().classes("w-full gap-4"):
        with ui.column().classes("flex-grow"):
            ui.label("Autonomous Investigation Pipeline:").classes("font-bold text-sm")
            steps = [
                ("1. Detect", "Scan transaction time-series for fraud scores ≥ 0.70, velocity anomalies"),
                ("2. Investigate", "Cross-reference cardholder profile, geo-velocity impossible travel"),
                ("3. Network Check", "$graphLookup to detect merchant fraud ring connections (depth ≤ 2)"),
                ("4. External Verify", "FastMCP: OFAC sanctions screening, merchant risk check"),
                ("5. Remediate", "FastMCP: Block card, send notification, file SAR if warranted"),
                ("6. Report", "Generate structured investigation summary with all evidence"),
            ]
            for label, desc in steps:
                ui.html(f'<div class="step-box"><strong>{label}</strong> — {desc}</div>')

            ui.label("MCP Tools (mock external APIs):").classes("font-bold text-sm mt-2")
            mcp_tools = ["screen_sanctions", "block_card", "send_notification", "file_sar", "merchant_risk_check"]
            ui.html(" ".join(f'<span class="tool-badge-red">{t}</span>' for t in mcp_tools))

        with ui.column().style("min-width:280px; max-width:360px"):
            ui.html("""<div class="memory-box">
              <strong>🧠 Memory Architecture</strong><br><br>
              <strong>🧩 Episodic Memory</strong><br>
              Each fraud investigation is stored in MongoDB with full audit trail.<br><br>
              <strong>🔧 Procedural Memory</strong><br>
              Fraud playbooks (CNP, ATO, money laundering) guide investigation steps.<br><br>
              <strong>⚡ Working Memory</strong><br>
              LangGraph <code>FraudAgentState</code> carries severity, actions_taken, fraud_type across reasoning steps.
            </div>""")

    # ── Blog feature callout ──────────────────────────────────────────────
    ui.html("""<div class="info-section" style="border-left-color:#c0392b;">
      <span class="blog-feature-tag bft-vector">🔵 Atlas Vector Search</span>
      Fraud playbooks retrieved via <code>$vectorSearch</code> — semantic similarity.
      &nbsp;&nbsp;
      <span class="blog-feature-tag bft-ckpt">🟣 MongoDB Checkpointer</span>
      LangGraph <code>FraudAgentState</code> persists across every reasoning step.
      &nbsp;&nbsp;
      <span class="blog-feature-tag bft-smith">🔴 LangSmith Observability</span>
      Every tool call traced end-to-end.
    </div>""")

    ui.separator().classes("my-2")

    # ── Controls ──────────────────────────────────────────────────────────
    ui.label("🎯 Run Fraud Investigation").classes("text-xl font-bold mt-2")

    mode = ui.radio(
        ["🔍 Full Network Scan", "👤 Specific Cardholder"],
        value="👤 Specific Cardholder",
    ).props("inline")

    # Build cardholder list: injected scenario IDs first, then defaults
    injected_ids = [sc["cardholder_id"] for sc in FRAUD_SCENARIOS.values()]
    default_ids = [f"CH_{i:04d}" for i in range(1, 21)]
    all_ids = injected_ids + default_ids

    with ui.row().classes("w-full gap-2 items-end"):
        ch_select = ui.select(all_ids, value=all_ids[0], label="Select Cardholder:").classes("w-64")
        ch_select.bind_visibility_from(mode, "value", value="👤 Specific Cardholder")
        session_input = ui.input("Session ID:", value="fraud-session-1").classes("w-48")

    with ui.row().classes("w-full gap-2 items-center"):
        run_btn = ui.button("🚨 Launch Autonomous Investigation", color="red-8").classes("text-base font-bold")
        warn_box = ui.column()

    # Show warning when Full Scan is selected
    def _update_warn():
        warn_box.clear()
        if mode.value == "🔍 Full Network Scan":
            with warn_box:
                ui.html('<div class="alert-red">⚠️ <strong>Full Scan Mode:</strong> Agent will '
                        'autonomously investigate top-risk transactions and may block cards and '
                        'file SARs (simulated).</div>')
    mode.on_value_change(lambda: _update_warn())

    result_box = ui.column().classes("w-full gap-2 mt-3")

    # ── Run handler ───────────────────────────────────────────────────────
    async def _run_fraud():
        trigger = "scan" if mode.value == "🔍 Full Network Scan" else "cardholder"
        cardholder = ch_select.value if trigger == "cardholder" else None

        show_spinner(result_box,
                     "🤖 VaultShield running autonomous fraud investigation…",
                     f"Trigger: {trigger} | Cardholder: {cardholder or 'all'} | Session: {session_input.value}")

        try:
            from agents.fraud_agent import run_fraud_investigation
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: run_fraud_investigation(
                    trigger=trigger,
                    cardholder_id=cardholder,
                    session_id=session_input.value,
                ),
            )
        except Exception as e:
            logger.exception("Fraud agent error: %s", e)
            result = {"answer": f"⚠️ Error: {e}", "tool_calls": [], "messages": []}

        result_box.clear()
        answer = result.get("answer", "") or "⚠️ Empty response."
        tools = result.get("tool_calls", [])

        with result_box:
            # Investigation Report
            ui.label("📋 Investigation Report").classes("text-lg font-bold")
            render_answer_box(result_box, answer, css_class="answer-box-red")

            # Categorised tool actions
            if tools:
                ui.label("🔧 Agent Actions Taken").classes("text-lg font-bold mt-3")
                detect = [t for t in tools if any(w in t for w in ("transaction", "flagged", "velocity", "trend"))]
                invest = [t for t in tools if any(w in t for w in ("profile", "merchant", "playbook"))]
                action = [t for t in tools if any(w in t for w in ("mcp", "block", "sar", "notify", "sanction"))]
                other  = [t for t in tools if t not in detect + invest + action]

                with ui.row().classes("w-full gap-4"):
                    with ui.column().classes("flex-1"):
                        ui.label("🔍 Detection").classes("font-bold text-sm")
                        for t in detect:
                            ui.html(f'<div style="background:#d1fae5;padding:4px 8px;border-radius:4px;margin:2px;font-size:.82rem;">✓ {t}</div>')
                    with ui.column().classes("flex-1"):
                        ui.label("🔎 Investigation").classes("font-bold text-sm")
                        for t in invest:
                            ui.html(f'<div style="background:#dbeafe;padding:4px 8px;border-radius:4px;margin:2px;font-size:.82rem;">✓ {t}</div>')
                    with ui.column().classes("flex-1"):
                        ui.label("⚡ Actions").classes("font-bold text-sm")
                        for t in action:
                            ui.html(f'<div style="background:#fef3c7;padding:4px 8px;border-radius:4px;margin:2px;font-size:.82rem;">⚡ {t}</div>')
                if other:
                    render_tool_chips(other)

    run_btn.on_click(_run_fraud)

    # ── Architecture diagram ──────────────────────────────────────────────
    ui.separator().classes("my-2")
    with ui.expansion("🏗️ Architecture — Fraud Agent Reasoning Graph", value=False).classes("w-full"):
        ui.html("""<pre style="font-size:.78rem; background:#f8f9fa; padding:1rem; border-radius:6px; overflow-x:auto;">
                    ┌─────────────────────────────────────┐
                    │         FraudAgentState              │
                    │  messages · case_id · severity       │
                    │  actions_taken · fraud_type          │
                    └─────────────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   [Agent Node]     │  ← Azure GPT-4o
                    │   VaultShield LLM  │    reads playbook
                    └─────────┬──────────┘    (Procedural Memory)
              tool_calls?     │  no tool_calls
         ┌───────────────────►│◄────────────────────── END
         │           ┌────────┘
         │           ▼
         │  ┌─────────────────────────────────────────────┐
         │  │              [Tool Node]                    │
         │  │  MongoDB Tools:                             │
         │  │    get_flagged_transactions (time-series)   │
         │  │    check_transaction_velocity               │
         │  │    check_merchant_fraud_ring ($graphLookup) │
         │  │    timeseries_fraud_trend (aggregation)     │
         │  │  FastMCP Tools:                             │
         │  │    mcp_screen_sanctions → OFAC API         │
         │  │    mcp_block_card → NFG Card System       │
         │  │    mcp_file_sar → FinCEN SAR Portal        │
         │  │    mcp_send_notification → Push/SMS        │
         │  └─────────────────────────────────────────────┘
         │           │
         └───────────┘  (loops until no more tool calls)
</pre>""")
        ui.markdown("""
**MongoDB query patterns used:**
- `$match` + `$sort` on `fraud_score` and `timestamp` (time-series)
- `$graphLookup` on `merchant_networks` (depth ≤ 2) for fraud ring detection
- `$group` + `$dateToString` for daily fraud trend aggregation
- All case history written to `conversation_history` (Episodic Memory)
""")

    # ── Scenario injection handlers ───────────────────────────────────────
    async def _inject(key: str):
        try:
            from pymongo import MongoClient
            from config import MONGODB_URI, MONGODB_DB_NAME
            from datetime import timedelta
            import random

            db = MongoClient(MONGODB_URI)[MONGODB_DB_NAME]
            sc = FRAUD_SCENARIOS[key]
            tag = sc["id"]
            _tag_field = "_injected_scenario"

            # Clean previous injection of same scenario
            for col in ("transactions", "cardholders", "merchant_networks"):
                db[col].delete_many({_tag_field: tag})

            now = datetime.now(timezone.utc)
            ch_id = sc["cardholder_id"]

            # Create a demo cardholder
            db.cardholders.insert_one({
                "cardholder_id": ch_id,
                "name": f"Demo {tag}",
                "card_tier": "Platinum",
                "home_city": "London",
                "status": "active",
                _tag_field: tag,
            })

            # Create demo transactions matching the scenario
            txns = []
            for i in range(5):
                txns.append({
                    "transaction_id": f"TXN_DEMO_{tag}_{i:03d}",
                    "cardholder_id": ch_id,
                    "amount": round(random.uniform(500, 9999), 2),
                    "currency": "USD",
                    "timestamp": now - timedelta(minutes=i * 3),
                    "fraud_score": round(random.uniform(0.7, 0.99), 2),
                    "is_flagged": True,
                    "status": "pending_review",
                    _tag_field: tag,
                })
            db.transactions.insert_many(txns)

            ui.notify(f"✅ Injected: {key} — 1 cardholder + {len(txns)} transactions", type="positive")
            logger.info("Injected scenario %s: 1 cardholder, %d txns", tag, len(txns))
        except Exception as e:
            ui.notify(f"Injection failed: {e}", type="negative")
            logger.exception("Injection failed: %s", e)

    async def _clear_injected():
        try:
            from pymongo import MongoClient
            from config import MONGODB_URI, MONGODB_DB_NAME
            db = MongoClient(MONGODB_URI)[MONGODB_DB_NAME]
            total = 0
            for col in ("transactions", "cardholders", "merchant_networks"):
                r = db[col].delete_many({"_injected_scenario": {"$exists": True}})
                total += r.deleted_count
            ui.notify(f"Cleared {total} injected documents", type="info")
        except Exception as e:
            ui.notify(f"Clear failed: {e}", type="negative")