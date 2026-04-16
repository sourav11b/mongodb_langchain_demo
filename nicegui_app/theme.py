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
.page-header { background:linear-gradient(135deg,#003087,#006FCF);
  padding:1.5rem 2rem; border-radius:10px; margin-bottom:1rem; color:white; }
.page-header h2 { margin:0; }
.page-header p  { color:rgba(255,255,255,.88); margin:.3rem 0 0; }
.bubble-human { background:#EBF5FB; border-radius:16px 16px 4px 16px;
  padding:.75rem 1.1rem; margin:.5rem 0 .5rem 12%; border-left:3px solid #006FCF; }
.bubble-agent { background:#F0FFF4; border-radius:16px 16px 16px 4px;
  padding:.75rem 1.1rem; margin:.5rem 12% .5rem 0; border-left:3px solid #27ae60; }
.bubble-context { background:#FFF8E7; border-radius:8px;
  padding:.6rem 1rem; margin:.4rem 8%; border-left:3px solid #B5A06A; font-size:.85rem; }
.tool-chip { background:#EEF3FB; color:#006FCF; border-radius:5px;
  padding:1px 8px; font-size:.76rem; font-weight:600; display:inline-block; margin:1px; }
.mcp-chip  { background:#E9F7EF; color:#1a7340; border-radius:5px;
  padding:1px 8px; font-size:.76rem; font-weight:600; display:inline-block; margin:1px; }
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
.scenario-card { background:#fffbe6; border:1px solid #ffe58f; border-radius:10px;
  padding:.7rem 1rem; margin:.4rem 0; }
.stat-card { background:white; border-radius:10px; padding:1rem;
  border:1px solid #e2e8f0; text-align:center; }
</style>
"""


def inject_css():
    """Call once at the top of each page to add shared CSS."""
    ui.add_head_html(CUSTOM_CSS)


def page_header(title: str, subtitle: str, tags_html: str = ""):
    """Render a gradient page header with feature tags."""
    ui.html(f"""
    <div class="page-header">
      <h2>{title}</h2>
      <p>{subtitle}</p>
      {"<p style='margin-top:.6rem;'>" + tags_html + "</p>" if tags_html else ""}
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
    ui.html(chips)


def render_chat_bubble(container, turn: dict):
    """Append a single chat bubble to the given container."""
    with container:
        if turn["role"] == "context":
            ui.html(f'<div class="bubble-context">📚 '
                    f'<em>{turn["content"][:300]}…</em></div>')
        elif turn["role"] == "user":
            ui.html(f'<div class="bubble-human">🧑 <strong>You</strong>'
                    f'<br>{turn["content"]}</div>')
        else:
            mcp_on = turn.get("mcp", False)
            badge = "🍃 MongoDB MCP" if mcp_on else "⚙️ pymongo fallback"
            ui.html(
                f'<div class="bubble-agent">🤖 <strong>Agent</strong> '
                f'<small>({badge})</small><br>{turn["content"]}</div>'
            )
            render_tool_chips(turn.get("tools", []))
