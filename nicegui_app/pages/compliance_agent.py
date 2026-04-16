"""
NiceGUI — Compliance Audit page  (/compliance)
"""
from __future__ import annotations
import sys, os, logging, asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nicegui import ui, app
from nicegui_app.theme import (inject_css, nav_bar, page_header, render_tool_chips,
                               show_spinner, render_answer_box)

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
    nav_bar("/compliance")

    page_header(
        "⚖️ Use Case 4: AML & Compliance Intelligence Agent",
        "Autonomous regulatory review across BSA · FATCA · OFAC · GDPR · PSD2 — graph-powered AML network analysis",
        '<span class="blog-feature-tag bft-vector">🔵 Atlas Vector Search</span>'
        '<span class="blog-feature-tag bft-mql">🟡 Text-to-MQL</span>'
        '<span class="blog-feature-tag bft-ckpt">🟣 MongoDB Checkpointer</span>'
        '<span class="blog-feature-tag bft-smith">🔴 LangSmith Observability</span>',
    )

    # ── Info columns ──────────────────────────────────────────────────────
    with ui.row().classes("w-full gap-4"):
        with ui.column().classes("flex-grow"):
            ui.label("Regulatory Frameworks Covered:").classes("font-bold text-sm")
            regs = [
                ("BSA/AML", "#FDEDEC", "#c0392b", "Currency Transaction Reports ($10K), SAR filing ($5K), structuring"),
                ("FATCA",   "#EAFAF1", "#1a7340", "Foreign account reporting, withholding on non-compliant entities"),
                ("OFAC",    "#FEF9E7", "#B7950B", "Real-time SDN list screening, sanctions exposure mapping"),
                ("GDPR",    "#EBF5FB", "#2471A3", "Data retention rules, right to erasure, data minimisation"),
                ("PSD2",    "#EBF5FB", "#2471A3", "Strong Customer Authentication thresholds for EU payments"),
            ]
            for reg, bg, color, desc in regs:
                ui.html(f'<span style="background:{bg};color:{color};padding:3px 10px;border-radius:12px;'
                        f'font-size:.75rem;font-weight:700;display:inline-block;margin:2px">{reg}</span>'
                        f' <span style="font-size:.88rem">{desc}</span>')

            ui.label("Autonomous Capabilities:").classes("font-bold text-sm mt-2")
            caps = [
                "📋 Semantic rule lookup (compliance vector search)",
                "🕸️ Graph-based AML network analysis (layering detection)",
                "📄 Unstructured case note analysis (AML trigger extraction)",
                "💰 Threshold monitoring (BSA CTR + SAR thresholds)",
                "📡 OFAC sanctions exposure mapping by IP country",
                "📝 Autonomous SAR filing via FastMCP",
            ]
            for c in caps:
                ui.label(c).classes("text-sm my-0")

            ui.label("MCP Tools:").classes("font-bold text-sm mt-2")
            ui.html('<span class="tool-badge-red">mcp_file_sar_compliance</span>'
                    ' <span class="tool-badge-red">mcp_ofac_screen_compliance</span>')

        with ui.column().style("min-width:260px; max-width:340px"):
            ui.html("""<div class="memory-box">
              <strong>🧠 Memory Architecture</strong><br><br>
              <strong>🧩 Episodic Memory</strong><br>
              Each compliance audit stored with full regulatory citation trail.<br><br>
              <strong>📚 Semantic Memory</strong><br>
              Compliance rules embedded via Voyage AI for intent-based retrieval.<br><br>
              <strong>⚡ Working Memory</strong><br>
              LangGraph <code>ComplianceAgentState</code> tracks violations, severity, remediation status.
            </div>""")

    # ── Blog feature callout ──────────────────────────────────────────────
    ui.html("""<div class="info-section" style="border-left-color:#2471A3;">
      <span class="blog-feature-tag bft-vector">🔵 Blog Feature: Compliance Rule Retrieval</span>
      &nbsp; Compliance rules (BSA, FATCA, GDPR, OFAC, PSD2) are retrieved via
      <code>$vectorSearch</code> — semantic similarity. The agent finds relevant regulations
      even when case descriptions use different terminology.
      &nbsp;&nbsp;
      <span class="blog-feature-tag bft-mql">🟡 Blog Feature: Text-to-MQL</span>
      &nbsp; The agent generates MQL aggregation pipelines to query transaction thresholds
      and case histories from plain-language instructions.
    </div>""")

    ui.separator().classes("my-2")

    # ── Run Controls ──────────────────────────────────────────────────────
    ui.label("🎯 Run Compliance Investigation").classes("text-xl font-bold")

    with ui.tabs().classes("w-full") as tabs:
        tab_full = ui.tab("🔍 Full Compliance Audit")
        tab_individual = ui.tab("👤 Individual Cardholder Review")

    result_box = ui.column().classes("w-full gap-2 mt-2")
    status = ui.label("").classes("text-xs text-gray-500 mt-1")

    with ui.tab_panels(tabs, value=tab_full).classes("w-full"):
        # ── Tab 1: Full Compliance Audit ──────────────────────────────
        with ui.tab_panel(tab_full):
            ui.markdown("""**Full Audit** performs:
1. Look up top AML and sanctions rules
2. Identify cardholders breaching BSA thresholds
3. Analyse open fraud cases for AML triggers in unstructured notes
4. Run network graph analysis on highest-risk cardholder
5. Check sanctions exposure, file SAR if needed
6. Generate compliance report""")
            full_btn = ui.button("⚖️ Run Full Compliance Audit", color="primary").classes("text-base font-bold")

        # ── Tab 2: Individual Cardholder Review ───────────────────────
        with ui.tab_panel(tab_individual):
            with ui.row().classes("gap-2 items-end"):
                ch_custom = ui.select(
                    [f"CH_{i:04d}" for i in range(1, 16)],
                    value="CH_0005", label="Cardholder:",
                ).classes("w-48")
            custom_input = ui.textarea(
                label="Custom compliance question (optional):",
                placeholder="e.g. Does this cardholder have sanctions exposure?",
            ).classes("w-full").style("height:80px")

            # Quick start buttons
            ui.label("💡 Quick starts — click to auto-fill:").classes("text-sm font-semibold mt-2")
            with ui.row().classes("gap-2 flex-wrap"):
                for label, prompt in COMPLIANCE_PROMPTS:
                    ui.button(
                        label,
                        on_click=lambda p=prompt: custom_input.set_value(p),
                    ).tooltip(prompt).classes("text-xs")

            custom_btn = ui.button("🔍 Investigate Cardholder Compliance", color="primary").classes("mt-2 text-base font-bold")

    # ── Handlers ──────────────────────────────────────────────────────────
    async def _run_compliance(cardholder: str | None, prompt: str | None, session_id: str = "comp-session"):
        target = cardholder or "all cardholders"
        show_spinner(result_box,
                     f"🤖 VaultComply running regulatory review…",
                     f"Target: {target} | Check: {prompt or 'Full compliance audit'}")

        try:
            import asyncio
            from agents.compliance_agent import run_compliance_investigation
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: run_compliance_investigation(
                    prompt=prompt, cardholder_id=cardholder, session_id=session_id,
                ),
            )
        except Exception as e:
            logger.exception("Compliance error: %s", e)
            result = {"answer": f"⚠️ Error: {e}", "tool_calls": [], "messages": []}

        result_box.clear()
        answer = result.get("answer", "") or "⚠️ Empty response."
        tools = result.get("tool_calls", [])

        with result_box:
            ui.label(f"📋 Compliance Report{': ' + cardholder if cardholder else ''}").classes("text-lg font-bold")
            render_answer_box(result_box, answer, css_class="answer-box-green")

            if tools:
                ui.label("🔧 Regulatory Actions Taken").classes("text-lg font-bold mt-3")
                render_tool_chips(tools)

            # Full agent trace (expandable)
            if result.get("messages"):
                with ui.expansion("📜 Full Agent Trace").classes("w-full mt-2"):
                    for msg in result.get("messages", []):
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tc in msg.tool_calls:
                                ui.markdown(f"**🔧 `{tc.get('name','?')}`** — args: {tc.get('args',{})}")
                        elif getattr(msg, "type", None) == "tool":
                            ui.code(str(msg.content)[:600])

        status.text = f"✅ Done — {len(tools)} tools called"

    full_btn.on_click(lambda: _run_compliance(None, None, "audit-full"))
    custom_btn.on_click(lambda: _run_compliance(
        ch_custom.value,
        custom_input.value.strip() if custom_input.value.strip() else None,
        f"comp-{ch_custom.value}",
    ))

    # ── Compliance Rules Preview ──────────────────────────────────────────
    ui.separator().classes("my-2")
    rules_box = ui.column().classes("w-full")

    async def _load_rules():
        try:
            import asyncio as _aio
            from pymongo import MongoClient
            from config import MONGODB_URI, MONGODB_DB_NAME

            def _fetch():
                db = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)[MONGODB_DB_NAME]
                return list(db.compliance_rules.find({}, {"_id": 0, "embedding": 0}).limit(5))

            rules = await _aio.get_event_loop().run_in_executor(None, _fetch)
            with rules_box:
                ui.label("📋 Compliance Rule Base (MongoDB Vector-Indexed)").classes("text-lg font-bold")
                if rules:
                    for r in rules:
                        ui.html(f"""<div class="step-box">
                          <strong>{r.get('rule_name','?')}</strong>
                          <span style="background:#EBF5FB;color:#2471A3;padding:2px 8px;border-radius:10px;
                            font-size:.72rem;font-weight:600;margin-left:6px">{r.get('rule_id','?')}</span>
                          <span style="background:#EAFAF1;color:#1a7340;padding:2px 8px;border-radius:10px;
                            font-size:.72rem;font-weight:600;margin-left:4px">{r.get('jurisdiction','?')}</span>
                          <span style="background:#FEF9E7;color:#B7950B;padding:2px 8px;border-radius:10px;
                            font-size:.72rem;font-weight:600;margin-left:4px">{r.get('category','?')}</span>
                          <br><small style="color:#666">{r.get('rule_text','')[:220]}…</small>
                        </div>""")
                else:
                    ui.label("No rules found. Run Setup → Seed Data.").classes("text-gray-500 text-sm")
        except Exception as e:
            with rules_box:
                ui.label(f"Cannot load rules: {e}").classes("text-gray-500 text-sm")

    asyncio.ensure_future(_load_rules())

    # ── Architecture diagram ──────────────────────────────────────────────
    ui.separator().classes("my-2")
    with ui.expansion("🏗️ Architecture — AML Agent Graph + MongoDB Patterns", value=False).classes("w-full"):
        ui.html("""<pre style="font-size:.78rem; background:#f8f9fa; padding:1rem; border-radius:6px; overflow-x:auto;">
Compliance Trigger (threshold breach / case flag / scheduled audit)
    │
    ▼
[search_compliance_rules] → Voyage AI → Atlas Vector Search → top-N rules
    │
    ▼
[check_transaction_thresholds] → $group aggregation → BSA CTR/SAR flags
    │
    ▼
[analyse_fraud_case_notes] → regex + semantic match on free-text notes
    │
    ▼
[aml_network_analysis] → $graphLookup (merchant_networks, depth≤2)
    │                    → merchant risk cluster detection
    ▼
[check_sanctions_exposure] → IP country mapping to OFAC sanctioned list
    │
    ├─ SAR warranted? → [mcp_file_sar_compliance] → FastMCP → FinCEN
    │
    └─► [generate_compliance_report] → write to MongoDB compliance_reports
</pre>""")
        ui.markdown("""
**Key MongoDB features:**
- `$graphLookup` on `merchant_networks` to detect AML layering patterns
- Vector search on `compliance_rules` for semantic regulation retrieval
- `$group` pipeline on `transactions` for threshold monitoring
- Unstructured text in `fraud_cases.investigation_notes` analysed by LLM
- Episodic audit trail in `conversation_history` collection
""")
