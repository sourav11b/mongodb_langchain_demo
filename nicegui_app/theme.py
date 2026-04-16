"""
Shared CSS and layout helpers for the NiceGUI VaultIQ app.
"""
from __future__ import annotations
from nicegui import ui

MCP_TOOL_NAMES = {
    "find", "aggregate", "collection-schema", "collection-indexes",
    "collection-storage-size", "count", "db-stats", "explain",
    "list-collections", "list-databases", "search-knowledge",
    "list-knowledge-sources",
}

CUSTOM_CSS = """
<style>
/* ── Page header ───────────────────────────────────────────────────────── */
.page-header { background:linear-gradient(135deg,#003087,#006FCF);
  padding:1.5rem 2rem; border-radius:10px; margin-bottom:1rem; color:white; }
.page-header h2 { margin:0; }
.page-header p  { color:rgba(255,255,255,.88); margin:.3rem 0 0; }
.page-header-red { background:linear-gradient(135deg,#8B0000,#c0392b); }
.page-header-green { background:linear-gradient(135deg,#1a7340,#27ae60); }

/* ── Chat bubbles ──────────────────────────────────────────────────────── */
.bubble-human { background:#EBF5FB; border-radius:16px 16px 4px 16px;
  padding:.75rem 1.1rem; margin:.5rem 0 .5rem 12%; border-left:3px solid #006FCF; }
.bubble-agent { background:#F0FFF4; border-radius:16px 16px 16px 4px;
  padding:.75rem 1.1rem; margin:.5rem 0; border-left:3px solid #27ae60;
  white-space:pre-wrap; line-height:1.7; }
.bubble-agent strong { color:#1a5c32; }
.bubble-context { background:#FFF8E7; border-radius:8px;
  padding:.6rem 1rem; margin:.4rem 8%; border-left:3px solid #B5A06A; font-size:.85rem; }

/* ── Answer box (for single-shot results like fraud/compliance) ────────── */
.answer-box { background:#F8F9FA; border:1px solid #DEE2E6; border-radius:10px;
  padding:1.2rem 1.5rem; margin:.8rem 0; white-space:pre-wrap; line-height:1.8;
  font-size:.92rem; }
.answer-box strong, .answer-box b { color:#1a1a2e; }
.answer-box hr { border:none; border-top:1px solid #DEE2E6; margin:.8rem 0; }
.answer-box-red { border-left:4px solid #e74c3c; background:#FFF5F5; }
.answer-box-green { border-left:4px solid #27ae60; background:#F0FFF4; }

/* ── Tool chips ────────────────────────────────────────────────────────── */
.tool-chip { background:#EEF3FB; color:#006FCF; border-radius:5px;
  padding:2px 10px; font-size:.78rem; font-weight:600; display:inline-block; margin:2px; }
.mcp-chip  { background:#E9F7EF; color:#1a7340; border-radius:5px;
  padding:2px 10px; font-size:.78rem; font-weight:600; display:inline-block; margin:2px; }
.tool-badge-red { background:#FFF0F0; color:#c0392b; border-radius:6px;
  padding:2px 10px; font-size:.8rem; font-weight:600; display:inline-block; margin:2px; }

/* ── Feature tags ──────────────────────────────────────────────────────── */
.blog-feature-tag { display:inline-block; padding:.18rem .65rem; border-radius:20px;
  font-size:.73rem; font-weight:700; margin:.15rem; border:1.5px solid; }
.bft-vector { background:#dbeafe; color:#1d4ed8; border-color:#93c5fd; }
.bft-hybrid { background:#d1fae5; color:#065f46; border-color:#6ee7b7; }
.bft-mql    { background:#fef3c7; color:#92400e; border-color:#fcd34d; }
.bft-ckpt   { background:#ede9fe; color:#5b21b6; border-color:#c4b5fd; }
.bft-smith  { background:#fee2e2; color:#991b1b; border-color:#fca5a5; }
.bft-geo    { background:#e0f2fe; color:#075985; border-color:#7dd3fc; }
.bft-graph  { background:#f3e8ff; color:#6b21a8; border-color:#c084fc; }
.bft-mcp    { background:#ecfdf5; color:#065f46; border-color:#6ee7b7; }

/* ── Cards ─────────────────────────────────────────────────────────────── */
.scenario-card { background:#fffbe6; border:1px solid #ffe58f; border-radius:10px;
  padding:.7rem 1rem; margin:.4rem 0; }
.stat-card { background:white; border-radius:10px; padding:1rem;
  border:1px solid #e2e8f0; text-align:center; }
.cardholder-card { background:linear-gradient(135deg,#003087,#006FCF); border-radius:12px;
  padding:1rem 1.5rem; color:white; margin:.8rem 0; font-size:.95rem; }
.memory-box { background:#FFF8E7; border-left:4px solid #B5A06A;
  padding:.8rem 1rem; border-radius:6px; font-size:.88rem; }
.step-box { background:#F8F9FA; border:1px solid #DEE2E6; border-radius:8px;
  padding:.6rem 1rem; margin:.3rem 0; }
.alert-red { background:#FFE4E1; border-left:4px solid #e74c3c;
  padding:.8rem 1rem; border-radius:6px; }
.info-section { background:#f8faff; border:1px solid #c8d8f0; border-left:4px solid #006FCF;
  border-radius:6px; padding:.8rem 1rem; margin:.5rem 0; font-size:.88rem; }

/* ── Bold spinner ──────────────────────────────────────────────────────── */
.spinner-box { background:linear-gradient(135deg,#EBF5FB,#E8F8F5);
  border:2px solid #006FCF; border-radius:12px; padding:1.2rem 1.5rem;
  margin:.8rem 0; text-align:center; animation:pulse-border 1.5s ease-in-out infinite; }
.spinner-box .spinner-text { font-size:1.1rem; font-weight:700; color:#003087; }
.spinner-box .spinner-sub  { font-size:.82rem; color:#555; margin-top:.3rem; }
@keyframes pulse-border {
  0%, 100% { border-color:#006FCF; box-shadow:0 0 0 0 rgba(0,111,207,.3); }
  50% { border-color:#27ae60; box-shadow:0 0 12px 4px rgba(0,111,207,.15); }
}
</style>
"""


def inject_css():
    """Call once at the top of each page to add shared CSS."""
    ui.add_head_html(CUSTOM_CSS)


def page_header(title: str, subtitle: str, tags_html: str = ""):
    """Render a gradient page header with feature tags + Atlas status banner."""
    atlas_status_banner()
    ui.html(f"""
    <div class="page-header">
      <h2>{title}</h2>
      <p>{subtitle}</p>
      {"<p style='margin-top:.6rem;'>" + tags_html + "</p>" if tags_html else ""}
    </div>
    """)


def atlas_status_banner():
    """Show a banner if Atlas cluster is not OK (set by startup check in main.py)."""
    from nicegui import app as _app
    status = _app.storage.general.get("atlas_status", "unknown")
    message = _app.storage.general.get("atlas_message", "")
    if status == "ok" or not message:
        return
    color_map = {"resuming": "#FFF3CD", "error": "#F8D7DA", "unknown": "#E2E8F0"}
    border_map = {"resuming": "#FFD700", "error": "#DC3545", "unknown": "#94a3b8"}
    bg = color_map.get(status, "#E2E8F0")
    border = border_map.get(status, "#94a3b8")
    ui.html(f"""
    <div style="background:{bg}; border:2px solid {border}; border-radius:8px;
                padding:0.8rem 1.2rem; margin-bottom:1rem; font-size:0.9rem;">
      <strong>🏥 Atlas Cluster Status:</strong> {message}
    </div>
    """)


def render_tool_chips(tools: list[str]):
    """Render tool call badges (MCP green vs native blue)."""
    if not tools:
        return
    chips = " ".join(
        f'<span class="{"mcp-chip" if t in MCP_TOOL_NAMES else "tool-chip"}">'
        f'{"🍃 " if t in MCP_TOOL_NAMES else "✓ "}{t}</span>'
        for t in tools
    )
    ui.html(f'<div style="margin:.4rem 0">🛠️ <strong>Tools:</strong> {chips}</div>')


def _md_to_html(text: str) -> str:
    """Minimal markdown→HTML: bold, line breaks, horizontal rules."""
    import re
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    text = re.sub(r'^---+$', '<hr>', text, flags=re.MULTILINE)
    text = re.sub(r'^- (.+)$', r'• \1', text, flags=re.MULTILINE)
    text = text.replace("\n", "<br>")
    return text


def show_spinner(container, title: str = "Agent reasoning…",
                 subtitle: str = "Querying MongoDB, running tools, generating response…"):
    """Show a bold, animated spinner box inside the given container."""
    container.clear()
    with container:
        ui.html(f"""
        <div class="spinner-box">
          <div class="spinner-text">⏳ {title}</div>
          <div class="spinner-sub">{subtitle}</div>
        </div>
        """)


def render_answer_box(container, answer: str, tools: list[str] | None = None,
                      style: str = "", css_class: str = ""):
    """Render a formatted answer box with tool chips."""
    with container:
        ui.html(f'<div class="answer-box {css_class}" style="{style}">'
                f'{_md_to_html(answer)}</div>')
        if tools:
            render_tool_chips(tools)


def render_chat_bubble(container, turn: dict):
    """Append a single chat bubble to the given container."""
    with container:
        if turn["role"] == "context":
            ui.html(f'<div class="bubble-context">📚 '
                    f'<em>{turn["content"][:300]}…</em></div>')
        elif turn["role"] == "user":
            ui.html(f'<div class="bubble-human">🧑 <strong>You</strong>'
                    f'<br>{_md_to_html(turn["content"])}</div>')
        else:
            mcp_on = turn.get("mcp", False)
            badge = "🍃 MongoDB MCP" if mcp_on else "⚙️ pymongo fallback"
            ui.html(
                f'<div class="bubble-agent">🤖 <strong>Agent</strong> '
                f'<small>({badge})</small><br>{_md_to_html(turn["content"])}</div>'
            )
            render_tool_chips(turn.get("tools", []))
