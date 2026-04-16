"""
NiceGUI — Compliance Audit page  (/compliance)
"""
from __future__ import annotations
import sys, os, logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nicegui import ui, app
from nicegui_app.theme import inject_css, page_header, render_tool_chips

logger = logging.getLogger("vaultiq.nicegui.compliance")

COMPLIANCE_PROMPTS = [
    ("📋 Rule Lookup",   "Search for AML and Know-Your-Customer regulations applicable to high-value wire transfers"),
    ("💰 BSA Thresholds", "Check if this cardholder has breached the BSA $10,000 CTR or $5,000 SAR reporting thresholds"),
    ("📡 Sanctions",     "Check this cardholder for transactions to high-risk or sanctioned countries such as Nigeria, Romania, or Ukraine"),
    ("🕸️ AML Network",   "Run AML network analysis to detect layering through connected merchant networks"),
    ("📄 Case Notes",    "Analyse open fraud case investigation notes for AML triggers and regulatory implications"),
    ("📡 OFAC Screen",   "Run OFAC sanctions screening on this cardholder's name and home country"),
]

PRESET_CHECKS = [
    "Full Regulatory Compliance Audit",
    "BSA/AML Transaction Threshold Review",
    "OFAC & Sanctions Exposure Screening",
    "PEP & High-Risk Customer Review",
    "Cross-Border Wire Transfer Review",
]


@ui.page("/compliance")
async def compliance_page():
    await ui.context.client.connected()
    state = app.storage.tab
    state.setdefault("comp_result", None)

    inject_css()

    page_header(
        "⚖️ Compliance Audit — Regulatory Intelligence",
        "BSA/AML · OFAC screening · PEP checks · Graph-based AML network analysis",
        '<span class="blog-feature-tag bft-vector">🔵 Vector Search</span>'
        '<span class="blog-feature-tag bft-graph">🕸️ $graphLookup</span>'
        '<span class="blog-feature-tag bft-mql">🟡 Text-to-MQL</span>'
        '<span class="blog-feature-tag bft-mcp">🍃 MCP Server</span>'
        '<span class="blog-feature-tag bft-smith">🔴 LangSmith</span>',
    )

    # ── Tab layout (mirrors Streamlit version) ────────────────────────────
    with ui.tabs().classes("w-full") as tabs:
        tab_preset = ui.tab("Preset Checks")
        tab_custom = ui.tab("Custom Investigation")

    with ui.tab_panels(tabs, value=tab_preset).classes("w-full"):
        # ── Tab 1: Preset ─────────────────────────────────────────────
        with ui.tab_panel(tab_preset):
            with ui.row().classes("gap-2 items-end"):
                ch_preset = ui.select(
                    [f"CH_{i:04d}" for i in range(1, 16)],
                    value="CH_0005", label="Cardholder",
                ).classes("w-48")
                check_select = ui.select(
                    PRESET_CHECKS, value=PRESET_CHECKS[0], label="Check Type",
                ).classes("w-80")
                preset_btn = ui.button("🔍 Run Check", color="primary")

        # ── Tab 2: Custom ─────────────────────────────────────────────
        with ui.tab_panel(tab_custom):
            with ui.row().classes("gap-2 items-end"):
                ch_custom = ui.select(
                    [f"CH_{i:04d}" for i in range(1, 16)],
                    value="CH_0005", label="Cardholder",
                ).classes("w-48")
            custom_input = ui.textarea(
                label="Custom compliance question (optional):",
                placeholder="e.g. Does this cardholder have sanctions exposure?",
            ).classes("w-full")

            # Quick start buttons
            ui.label("💡 Quick starts — click to auto-fill:").classes("text-sm font-semibold mt-2")
            with ui.row().classes("gap-2 flex-wrap"):
                for label, prompt in COMPLIANCE_PROMPTS:
                    ui.button(
                        label,
                        on_click=lambda p=prompt: custom_input.set_value(p),
                    ).tooltip(prompt).classes("text-xs")

            custom_btn = ui.button("🔍 Investigate", color="primary").classes("mt-2")

    # ── Results ───────────────────────────────────────────────────────────
    status = ui.label("").classes("text-xs text-gray-500 mt-1")
    result_box = ui.column().classes("w-full gap-2 mt-2")

    # ── Handlers ──────────────────────────────────────────────────────────
    async def _run_compliance(cardholder: str, prompt: str | None):
        status.text = f"🤖 Auditing {cardholder}…"
        result_box.clear()

        try:
            from agents.compliance_agent import run_compliance_investigation
            result = run_compliance_investigation(
                prompt=prompt, cardholder_id=cardholder,
            )
        except Exception as e:
            logger.exception("Compliance error: %s", e)
            result = {"answer": f"⚠️ Error: {e}", "tool_calls": []}

        state["comp_result"] = result
        answer = result.get("answer", "") or "⚠️ Empty response."
        tools = result.get("tool_calls", [])

        with result_box:
            ui.html(f'<div class="bubble-agent">🤖 <strong>Compliance Agent</strong>'
                    f'<br>{answer}</div>')
            render_tool_chips(tools)

        status.text = f"✅ Done — {len(tools)} tools called"

    preset_btn.on_click(
        lambda: _run_compliance(ch_preset.value, check_select.value))
    custom_btn.on_click(
        lambda: _run_compliance(
            ch_custom.value,
            custom_input.value.strip() if custom_input.value.strip() else None))
