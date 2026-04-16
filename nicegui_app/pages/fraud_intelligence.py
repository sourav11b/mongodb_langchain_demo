"""
NiceGUI — Fraud Intelligence page  (/fraud)
"""
from __future__ import annotations
import sys, os, logging, json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nicegui import ui, app
from nicegui_app.theme import inject_css, page_header, render_chat_bubble

logger = logging.getLogger("vaultiq.nicegui.fraud")

FRAUD_SCENARIOS = {
    "velocity_spike": {
        "label": "⚡ Velocity Spike",
        "desc": "Inject 8 rapid-fire transactions for CH_0005 within 2 minutes.",
        "collection": "transactions",
    },
    "geo_impossible": {
        "label": "🌍 Impossible Travel",
        "desc": "Inject two large transactions for CH_0003 — London then Tokyo, 30 min apart.",
        "collection": "transactions",
    },
    "merchant_ring": {
        "label": "🕸️ Merchant Ring",
        "desc": "Create a 4-merchant fraud ring cluster with shared terminals.",
        "collection": "merchant_networks",
    },
    "structuring": {
        "label": "💵 Structuring",
        "desc": "Inject 12 cash-equivalent transactions just under $9,900 for CH_0007.",
        "collection": "transactions",
    },
}


@ui.page("/fraud")
async def fraud_page():
    await ui.context.client.connected()
    state = app.storage.tab
    state.setdefault("fraud_result", None)
    state.setdefault("fraud_scenarios", [])

    inject_css()
    page_header(
        "🚨 Fraud Intelligence — Real-Time Detection",
        "Graph analysis · Velocity checks · Geo-impossible travel · MCP tools",
        '<span class="blog-feature-tag bft-graph">🕸️ $graphLookup</span>'
        '<span class="blog-feature-tag bft-mql">🟡 Text-to-MQL</span>'
        '<span class="blog-feature-tag bft-mcp">🍃 MCP Server</span>'
        '<span class="blog-feature-tag bft-smith">🔴 LangSmith</span>',
    )

    # ── Sidebar: scenario injection ───────────────────────────────────────
    with ui.left_drawer(value=True).style(
        "width:310px; background:linear-gradient(180deg,#7f1d1d,#b91c1c);"
    ):
        ui.label("🧪 Scenario Injection").classes("text-white text-lg font-bold mt-4")
        ui.label("Inject test data to trigger fraud patterns").classes("text-white/70 text-xs mb-2")

        for key, sc in FRAUD_SCENARIOS.items():
            with ui.card().classes("scenario-card w-full"):
                ui.label(sc["label"]).classes("font-bold text-sm")
                ui.label(sc["desc"]).classes("text-xs text-gray-700")
                ui.button(
                    "Inject", color="orange",
                    on_click=lambda k=key: _inject_scenario(k),
                ).classes("mt-1").props("dense size=sm")

        ui.separator().classes("bg-white/20 my-2")
        if state["fraud_scenarios"]:
            ui.label("Injected:").classes("text-white font-bold text-xs")
            for s in state["fraud_scenarios"]:
                ui.label(f"✅ {s}").classes("text-white/80 text-xs")
        ui.button("🗑️ Clear Injected Data", on_click=_clear_scenarios,
                  color="white").classes("mt-2").props("outline dense size=sm")

    # ── Main content ──────────────────────────────────────────────────────
    with ui.row().classes("w-full gap-2 items-end"):
        ch_select = ui.select(
            [f"CH_{i:04d}" for i in range(1, 16)],
            value="CH_0005", label="Cardholder",
        ).classes("w-48")
        run_btn = ui.button("🚨 Run Fraud Analysis", color="red-8")

    status = ui.label("").classes("text-xs text-gray-500 mt-1")
    result_box = ui.column().classes("w-full gap-2 mt-2")


    # ── Handlers ──────────────────────────────────────────────────────────
    async def _run_fraud():
        cardholder = ch_select.value
        status.text = f"🤖 Analysing {cardholder}…"
        result_box.clear()

        try:
            from agents.fraud_agent import run_fraud_investigation
            result = run_fraud_investigation(cardholder_id=cardholder)
        except Exception as e:
            logger.exception("Fraud agent error: %s", e)
            result = {"answer": f"⚠️ Error: {e}", "tool_calls": []}

        state["fraud_result"] = result
        answer = result.get("answer", "") or "⚠️ Empty response."
        tools = result.get("tool_calls", [])

        with result_box:
            ui.html(f'<div class="bubble-agent">🤖 <strong>Fraud Agent</strong>'
                    f'<br>{answer}</div>')
            if tools:
                from nicegui_app.theme import render_tool_chips
                render_tool_chips(tools)

        status.text = f"✅ Done — {len(tools)} tools called"

    run_btn.on_click(_run_fraud)

    async def _inject_scenario(key: str):
        try:
            from data.seed_data import inject_fraud_scenario
            inject_fraud_scenario(key)
            state["fraud_scenarios"].append(FRAUD_SCENARIOS[key]["label"])
            ui.notify(f"Injected: {FRAUD_SCENARIOS[key]['label']}", type="positive")
        except Exception as e:
            ui.notify(f"Injection failed: {e}", type="negative")

    async def _clear_scenarios():
        state["fraud_scenarios"] = []
        ui.notify("Cleared injected scenarios", type="info")