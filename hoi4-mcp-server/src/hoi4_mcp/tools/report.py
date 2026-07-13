"""
Mod Report Generator — produces a self-contained HTML report for a HOI4 mod.

Usage (standalone):
    python -m hoi4_mcp.tools.report --mod-path /path/to/mod --output report.html

Usage (via server):
    python -m hoi4_mcp.server --mod-path /path/to/mod --report report.html
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .indexer import ModIndexer, ModIndex
from .error_log import parse_error_log, ErrorLog, find_error_log


# ---------------------------------------------------------------------------
# Single-file HTML template with embedded CSS/JS
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HOI4 Mod Report — {mod_name}</title>
<style>
:root {{
  --bg: #1a1a2e;
  --surface: #16213e;
  --surface2: #0f3460;
  --text: #e0e0e0;
  --text2: #a0a0b8;
  --accent: #e94560;
  --accent2: #0ea5e9;
  --green: #22c55e;
  --yellow: #eab308;
  --red: #ef4444;
  --border: #2a2a4a;
  --radius: 6px;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
}}
header {{
  background: linear-gradient(135deg, var(--surface2), var(--surface));
  padding: 24px 32px;
  border-bottom: 2px solid var(--accent);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}}
header h1 {{ font-size: 1.4rem; font-weight: 600; }}
header .meta {{ color: var(--text2); font-size: 0.85rem; }}
nav {{
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 0 32px;
  display: flex;
  gap: 0;
  overflow-x: auto;
}}
nav button {{
  background: none; border: none; color: var(--text2);
  padding: 12px 20px; cursor: pointer; font-size: 0.9rem;
  border-bottom: 2px solid transparent; transition: all 0.2s;
  white-space: nowrap;
}}
nav button:hover {{ color: var(--text); }}
nav button.active {{ color: var(--accent); border-bottom-color: var(--accent); }}
nav button .badge {{
  display: inline-block; background: var(--surface2); color: var(--text2);
  padding: 1px 6px; border-radius: 10px; font-size: 0.7rem; margin-left: 4px;
  vertical-align: middle;
}}
main {{ max-width: 1400px; margin: 0 auto; padding: 24px 32px; }}
section {{ display: none; }}
section.active {{ display: block; }}
.summary-cards {{
  display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px; margin-bottom: 24px;
}}
.card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 16px;
}}
.card .value {{ font-size: 2rem; font-weight: 700; color: var(--accent2); }}
.card .label {{ font-size: 0.8rem; color: var(--text2); margin-top: 4px; }}
.card.warn .value {{ color: var(--yellow); }}
.card.err .value {{ color: var(--red); }}
table {{
  width: 100%; border-collapse: collapse; font-size: 0.9rem;
}}
th {{
  text-align: left; padding: 10px 12px; background: var(--surface2);
  color: var(--text2); font-weight: 600; border-bottom: 2px solid var(--border);
  position: sticky; top: 0; z-index: 1;
}}
td {{ padding: 8px 12px; border-bottom: 1px solid var(--border); }}
tr:hover td {{ background: rgba(233, 69, 96, 0.05); }}
.search-box {{
  margin-bottom: 16px; display: flex; gap: 8px; align-items: center;
}}
.search-box input {{
  flex: 1; max-width: 400px; padding: 8px 12px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); color: var(--text); font-size: 0.9rem;
}}
.search-box input:focus {{ outline: none; border-color: var(--accent2); }}
.search-box .filter-select {{
  padding: 8px 12px; background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); color: var(--text); font-size: 0.9rem;
}}
details {{ margin-bottom: 4px; }}
details summary {{
  cursor: pointer; padding: 8px 12px; background: var(--surface);
  border: 1px solid var(--border); border-radius: var(--radius);
  font-weight: 500; user-select: none;
}}
details summary:hover {{ background: var(--surface2); }}
details .detail-content {{
  padding: 16px; background: rgba(22,33,62,0.5); border: 1px solid var(--border);
  border-top: none; border-radius: 0 0 var(--radius) var(--radius);
  max-height: 500px; overflow-y: auto;
}}
.error-group {{
  margin-bottom: 16px; border: 1px solid var(--border); border-radius: var(--radius);
  overflow: hidden;
}}
.error-group-header {{
  background: var(--surface); padding: 10px 16px; font-weight: 600;
  display: flex; justify-content: space-between; align-items: center;
}}
.error-group-body {{ padding: 8px 16px; font-size: 0.85rem; }}
.error-line {{
  padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.03);
  font-family: 'Cascadia Code', 'Fira Code', monospace; font-size: 0.8rem;
}}
.error-line .cat {{
  display: inline-block; padding: 1px 6px; border-radius: 3px;
  font-size: 0.7rem; margin-right: 8px; font-weight: 600;
}}
.cat-unexpected_token {{ background: var(--red); color: #fff; }}
.cat-duplicate_id {{ background: var(--yellow); color: #000; }}
.cat-invalid_scope {{ background: #f97316; color: #fff; }}
.cat-missing_loc {{ background: var(--accent2); color: #fff; }}
.cat-missing_texture {{ background: #8b5cf6; color: #fff; }}
.cat-bad_trigger {{ background: var(--red); color: #fff; }}
.cat-parse_error {{ background: var(--yellow); color: #000; }}
.cat-missing_file {{ background: #ec4899; color: #fff; }}
.cat-database_error {{ background: var(--red); color: #fff; }}
.cat-unknown {{ background: #555; color: #fff; }}
footer {{
  text-align: center; padding: 24px; color: var(--text2); font-size: 0.8rem;
  border-top: 1px solid var(--border); margin-top: 32px;
}}
.no-data {{ color: var(--text2); font-style: italic; padding: 16px; }}
.warning-box {{
  background: rgba(234,179,8,0.1); border: 1px solid var(--yellow);
  border-radius: var(--radius); padding: 12px 16px; margin-bottom: 16px;
  font-size: 0.9rem;
}}
.warning-box strong {{ color: var(--yellow); }}
.tag {{
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 0.75rem; font-weight: 600; margin-right: 4px;
}}
.tag-triggered {{ background: var(--accent2); color: #fff; }}
.tag-hidden {{ background: #555; color: #ccc; }}
.tag-country_leader {{ background: #f97316; color: #fff; }}
.tag-advisor {{ background: #8b5cf6; color: #fff; }}
.tag-corps_commander {{ background: #22c55e; color: #000; }}
</style>
</head>
<body>

<header>
  <div>
    <h1>🛠 HOI4 Mod Report</h1>
    <div class="meta">Generated {timestamp}</div>
  </div>
  <div class="meta">
    Mod: <strong>{mod_name}</strong><br>
    Version: {mod_version}<br>
    Files indexed: {files_indexed}
  </div>
</header>

<nav>
  <button class="active" onclick="showTab('overview')">Overview</button>
  <button onclick="showTab('events')">Events <span class="badge">{event_count}</span></button>
  <button onclick="showTab('focuses')">Focuses <span class="badge">{focus_count}</span></button>
  <button onclick="showTab('decisions')">Decisions <span class="badge">{decision_count}</span></button>
  <button onclick="showTab('ideas')">Ideas <span class="badge">{idea_count}</span></button>
  <button onclick="showTab('characters')">Characters <span class="badge">{char_count}</span></button>
  <button onclick="showTab('scripted')">Scripted <span class="badge">{scripted_count}</span></button>
  <button onclick="showTab('localisation')">Loc Keys <span class="badge">{loc_count}</span></button>
  <button onclick="showTab('errors')">Errors <span class="badge">{error_count}</span></button>
  <button onclick="showTab('vanilla')">Vanilla DB</button>
</nav>

<main>
  <section id="tab-overview" class="active">
    <div class="summary-cards">
      {overview_cards}
    </div>
    {warnings_html}
    <h3 style="margin-bottom:12px">Namespaces</h3>
    {namespaces_html}
    <h3 style="margin:20px 0 12px">Focus Trees</h3>
    {focus_trees_html}
  </section>

  <section id="tab-events">
    <div class="search-box">
      <input type="text" placeholder="Filter events..." oninput="filterTable('events-table', this.value)">
      <select class="filter-select" onchange="filterTableCol('events-table', 2, this.value)">
        <option value="">All types</option>
        <option>country_event</option>
        <option>news_event</option>
        <option>state_event</option>
        <option>unit_event</option>
        <option>decision_event</option>
      </select>
    </div>
    <table id="events-table">
      <thead><tr><th>ID</th><th>File</th><th>Type</th><th>Title</th><th>Flags</th></tr></thead>
      <tbody>{events_rows}</tbody>
    </table>
  </section>

  <section id="tab-focuses">
    <div class="search-box">
      <input type="text" placeholder="Filter focuses..." oninput="filterTable('focuses-table', this.value)">
    </div>
    <table id="focuses-table">
      <thead><tr><th>ID</th><th>Tree</th><th>X</th><th>Y</th><th>File</th></tr></thead>
      <tbody>{focuses_rows}</tbody>
    </table>
  </section>

  <section id="tab-decisions">
    <div class="search-box">
      <input type="text" placeholder="Filter decisions..." oninput="filterTable('decisions-table', this.value)">
    </div>
    <table id="decisions-table">
      <thead><tr><th>Key</th><th>Category</th><th>Cost</th><th>File</th></tr></thead>
      <tbody>{decisions_rows}</tbody>
    </table>
  </section>

  <section id="tab-ideas">
    <div class="search-box">
      <input type="text" placeholder="Filter ideas..." oninput="filterTable('ideas-table', this.value)">
    </div>
    <table id="ideas-table">
      <thead><tr><th>Key</th><th>Category</th><th>Picture</th><th>Slot</th><th>File</th></tr></thead>
      <tbody>{ideas_rows}</tbody>
    </table>
  </section>

  <section id="tab-characters">
    <div class="search-box">
      <input type="text" placeholder="Filter characters..." oninput="filterTable('chars-table', this.value)">
    </div>
    <table id="chars-table">
      <thead><tr><th>ID</th><th>Name</th><th>Roles</th><th>File</th></tr></thead>
      <tbody>{chars_rows}</tbody>
    </table>
  </section>

  <section id="tab-scripted">
    <h3 style="margin-bottom:12px">Scripted Effects ({se_count})</h3>
    {se_html}
    <h3 style="margin:20px 0 12px">Scripted Triggers ({st_count})</h3>
    {st_html}
    <h3 style="margin:20px 0 12px">On Actions ({oa_count})</h3>
    {oa_html}
  </section>

  <section id="tab-localisation">
    <div class="search-box">
      <input type="text" placeholder="Filter localisation keys..." oninput="filterTable('loc-table', this.value)">
    </div>
    <table id="loc-table">
      <thead><tr><th>#</th><th>Localisation Key</th></tr></thead>
      <tbody>{loc_rows}</tbody>
    </table>
  </section>

  <section id="tab-errors">
    {errors_html}
  </section>

  <section id="tab-vanilla">
    {vanilla_html}
  </section>
</main>

<footer>HOI4 Mod Report &mdash; Generated by hoi4-mcp-server {server_version}</footer>

<script>
function showTab(name) {{
  document.querySelectorAll('section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  event.target.classList.add('active');
}}
function filterTable(tableId, query) {{
  const rows = document.querySelectorAll('#' + tableId + ' tbody tr');
  const q = query.toLowerCase();
  rows.forEach(row => {{
    row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}}
function filterTableCol(tableId, colIdx, value) {{
  const rows = document.querySelectorAll('#' + tableId + ' tbody tr');
  rows.forEach(row => {{
    if (!value) {{ row.style.display = ''; return; }}
    const cell = row.cells[colIdx];
    row.style.display = cell && cell.textContent.trim() === value ? '' : 'none';
  }});
}}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

@dataclass
class VanillaStats:
    """Summary of the vanilla database."""
    db_path: str = ""
    exists: bool = False
    focuses: int = 0
    events: int = 0
    ideas: int = 0
    technologies: int = 0
    countries: int = 0
    modifiers: int = 0
    total: int = 0


def _escape_html(text: str) -> str:
    """Escape HTML entities in text."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


def _tag(label: str, cls: str) -> str:
    """Generate an HTML tag span."""
    return f'<span class="tag tag-{cls}">{_escape_html(label)}</span>'


def _build_overview_cards(index: ModIndex, errors: list[dict], vanilla: VanillaStats) -> str:
    """Build the overview summary cards."""
    cards = [
        ("Events", str(len(index.events)), "", "accent2"),
        ("Focuses", str(len(index.focuses)), "", "accent2"),
        ("Decisions", str(len(index.decisions)), "", "accent2"),
        ("Ideas / Spirits", str(len(index.ideas)), "", "accent2"),
        ("Characters", str(len(index.characters)), "", "accent2"),
        ("Scripted Effects", str(len(index.scripted_effects)), "", "accent2"),
        ("Scripted Triggers", str(len(index.scripted_triggers)), "", "accent2"),
        ("On Actions", str(len(index.on_actions)), "", "accent2"),
        ("Loc Keys", str(len(index.localisation_keys)), "", "accent2"),
        ("Namespaces", str(len(index.namespaces)), "", "accent2"),
        ("Indexing Errors", str(len(index.errors)), "err" if index.errors else "", "red" if index.errors else "accent2"),
        ("Error.log Errors", str(len(errors)), "err" if errors else "", "red" if errors else "accent2"),
        ("Vanilla DB Entries", str(vanilla.total), "", "accent2" if vanilla.exists else "text2"),
        ("Files Indexed", str(index.files_indexed), "", "accent2"),
    ]
    return "\n".join(
        f'<div class="card {c[2]}"><div class="value" style="color:var(--{c[3]})">{c[0]}</div><div class="label">{c[1]}</div></div>'
        for c in cards
    )


def _build_events_rows(events: dict[str, dict]) -> str:
    """Build HTML table rows for events."""
    if not events:
        return '<tr><td colspan="5" class="no-data">No events found.</td></tr>'
    rows = []
    for eid, data in sorted(events.items()):
        flags = []
        if data.get("is_triggered_only"):
            flags.append(_tag("triggered", "triggered"))
        if data.get("hide_window"):
            flags.append(_tag("hidden", "hidden"))
        rows.append(
            f'<tr>'
            f'<td><code>{_escape_html(eid)}</code></td>'
            f'<td style="font-size:0.8rem;color:var(--text2)">{_escape_html(data.get("file", ""))}</td>'
            f'<td>{_escape_html(data.get("type", ""))}</td>'
            f'<td>{_escape_html(data.get("title", ""))}</td>'
            f'<td>{" ".join(flags)}</td>'
            f'</tr>'
        )
    return "\n".join(rows)


def _build_focuses_rows(focuses: dict[str, dict]) -> str:
    """Build HTML table rows for focuses."""
    if not focuses:
        return '<tr><td colspan="5" class="no-data">No focuses found.</td></tr>'
    rows = []
    for fid, data in sorted(focuses.items()):
        rows.append(
            f'<tr>'
            f'<td><code>{_escape_html(fid)}</code></td>'
            f'<td>{_escape_html(data.get("tree", ""))}</td>'
            f'<td>{data.get("x", "")}</td>'
            f'<td>{data.get("y", "")}</td>'
            f'<td style="font-size:0.8rem;color:var(--text2)">{_escape_html(data.get("file", ""))}</td>'
            f'</tr>'
        )
    return "\n".join(rows)


def _build_decisions_rows(decisions: dict[str, dict]) -> str:
    """Build HTML table rows for decisions."""
    if not decisions:
        return '<tr><td colspan="4" class="no-data">No decisions found.</td></tr>'
    rows = []
    for dkey, data in sorted(decisions.items()):
        rows.append(
            f'<tr>'
            f'<td><code>{_escape_html(dkey)}</code></td>'
            f'<td>{_escape_html(data.get("category", ""))}</td>'
            f'<td>{data.get("cost", "")}</td>'
            f'<td style="font-size:0.8rem;color:var(--text2)">{_escape_html(data.get("file", ""))}</td>'
            f'</tr>'
        )
    return "\n".join(rows)


def _build_ideas_rows(ideas: dict[str, dict]) -> str:
    """Build HTML table rows for ideas."""
    if not ideas:
        return '<tr><td colspan="5" class="no-data">No ideas found.</td></tr>'
    rows = []
    for ikey, data in sorted(ideas.items()):
        rows.append(
            f'<tr>'
            f'<td><code>{_escape_html(ikey)}</code></td>'
            f'<td>{_escape_html(data.get("category", ""))}</td>'
            f'<td>{_escape_html(data.get("picture", ""))}</td>'
            f'<td>{_escape_html(data.get("slot", ""))}</td>'
            f'<td style="font-size:0.8rem;color:var(--text2)">{_escape_html(data.get("file", ""))}</td>'
            f'</tr>'
        )
    return "\n".join(rows)


def _build_chars_rows(characters: dict[str, dict]) -> str:
    """Build HTML table rows for characters."""
    if not characters:
        return '<tr><td colspan="4" class="no-data">No characters found.</td></tr>'
    rows = []
    for cid, data in sorted(characters.items()):
        roles_html = " ".join(
            _tag(role, role) for role in data.get("roles", [])
        )
        rows.append(
            f'<tr>'
            f'<td><code>{_escape_html(cid)}</code></td>'
            f'<td>{_escape_html(data.get("name", ""))}</td>'
            f'<td>{roles_html}</td>'
            f'<td style="font-size:0.8rem;color:var(--text2)">{_escape_html(data.get("file", ""))}</td>'
            f'</tr>'
        )
    return "\n".join(rows)


def _build_scripted_html(effects: dict[str, dict], triggers: dict[str, dict],
                          on_actions: dict[str, dict]) -> dict:
    """Build HTML for scripted effects, triggers, and on_actions."""
    se_rows = []
    for name, data in sorted(effects.items()):
        se_rows.append(
            f'<tr><td><code>{_escape_html(name)}</code></td>'
            f'<td style="font-size:0.8rem;color:var(--text2)">{_escape_html(data.get("file", ""))}</td></tr>'
        )
    se_html = ('<table><thead><tr><th>Name</th><th>File</th></tr></thead><tbody>' +
               "\n".join(se_rows) + '</tbody></table>') if se_rows else \
              '<div class="no-data">No scripted effects found.</div>'

    st_rows = []
    for name, data in sorted(triggers.items()):
        st_rows.append(
            f'<tr><td><code>{_escape_html(name)}</code></td>'
            f'<td style="font-size:0.8rem;color:var(--text2)">{_escape_html(data.get("file", ""))}</td></tr>'
        )
    st_html = ('<table><thead><tr><th>Name</th><th>File</th></tr></thead><tbody>' +
               "\n".join(st_rows) + '</tbody></table>') if st_rows else \
              '<div class="no-data">No scripted triggers found.</div>'

    oa_rows = []
    for name, data in sorted(on_actions.items()):
        oa_rows.append(
            f'<tr><td><code>{_escape_html(name)}</code></td>'
            f'<td style="font-size:0.8rem;color:var(--text2)">{_escape_html(data.get("file", ""))}</td></tr>'
        )
    oa_html = ('<table><thead><tr><th>Name</th><th>File</th></tr></thead><tbody>' +
               "\n".join(oa_rows) + '</tbody></table>') if oa_rows else \
              '<div class="no-data">No on_actions found.</div>'

    return {
        "se_html": se_html,
        "st_html": st_html,
        "oa_html": oa_html,
        "se_count": len(effects),
        "st_count": len(triggers),
        "oa_count": len(on_actions),
    }


def _build_loc_rows(loc_keys: set) -> str:
    """Build HTML table rows for localisation keys."""
    sorted_keys = sorted(loc_keys)
    if not sorted_keys:
        return '<tr><td colspan="2" class="no-data">No localisation keys found.</td></tr>'
    rows = []
    for i, key in enumerate(sorted_keys, 1):
        rows.append(f'<tr><td style="width:60px;color:var(--text2)">{i}</td><td><code>{_escape_html(key)}</code></td></tr>')
    return "\n".join(rows)


def _build_errors_html(error_log: ErrorLog) -> str:
    """Build HTML for the errors tab."""
    if error_log.total_errors == 0:
        return '<div class="no-data">No errors found in error.log (or file not found).</div>'

    sections = []
    for category, errs in sorted(error_log.by_category.items()):
        sections.append(
            f'<div class="error-group">'
            f'<div class="error-group-header">'
            f'<span><span class="cat cat-{category}">{category}</span>'
            f' {len(errs)} errors</span>'
            f'</div>'
            f'<div class="error-group-body">'
            f'{"".join(f'<div class="error-line">{_escape_html(e.message)}</div>' for e in errs[:50])}'
        )
        if len(errs) > 50:
            sections[-1] += f'<div class="no-data">... and {len(errs) - 50} more errors</div>'
        sections[-1] += '</div></div>'

    return "\n".join(sections)


def _build_vanilla_html(stats: VanillaStats) -> str:
    """Build HTML for the vanilla DB tab."""
    if not stats.exists:
        return (
            f'<div class="warning-box">'
            f'<strong>No vanilla database found.</strong><br>'
            f'Build it with: <code>index-vanilla --vanilla-path /path/to/hoi4</code><br>'
            f'Expected location: <code>{_escape_html(stats.db_path)}</code>'
            f'</div>'
        )

    return f"""
    <div class="summary-cards">
      <div class="card"><div class="value">{stats.focuses:,}</div><div class="label">Focuses</div></div>
      <div class="card"><div class="value">{stats.events:,}</div><div class="label">Events</div></div>
      <div class="card"><div class="value">{stats.ideas:,}</div><div class="label">Ideas</div></div>
      <div class="card"><div class="value">{stats.technologies:,}</div><div class="label">Technologies</div></div>
      <div class="card"><div class="value">{stats.countries:,}</div><div class="label">Countries</div></div>
      <div class="card"><div class="value">{stats.modifiers:,}</div><div class="label">Modifiers</div></div>
      <div class="card"><div class="value">{stats.total:,}</div><div class="label">Total Entries</div></div>
    </div>
    <div style="font-size:0.85rem;color:var(--text2);margin-top:8px">
      Database: <code>{_escape_html(stats.db_path)}</code>
    </div>
    """


def _build_warnings(index: ModIndex) -> str:
    """Build warning boxes for ID collisions and issues."""
    warnings = []

    # Check for very high event ID numbers within a namespace
    ns_event_counts: dict[str, list[str]] = {}
    for eid in index.events:
        parts = eid.split(".", 1)
        if len(parts) == 2:
            ns = parts[0]
            if ns not in ns_event_counts:
                ns_event_counts[ns] = []
            ns_event_counts[ns].append(eid)

    for ns, eids in sorted(ns_event_counts.items()):
        if len(eids) > 100:
            warnings.append(
                f"<strong>{ns}</strong>: {len(eids)} events — large namespace, "
                f"consider splitting into sub-namespaces."
            )

    if not warnings:
        return ""

    items = "\n".join(f"<li>{w}</li>" for w in warnings)
    return f'<div class="warning-box"><strong>⚠ Warnings</strong><ul style="margin:8px 0 0 16px">{items}</ul></div>'


def _build_namespaces_html(namespaces: list[str]) -> str:
    """Build namespaces display."""
    if not namespaces:
        return '<div class="no-data">No namespaces found.</div>'
    tags = " ".join(
        f'<span class="tag tag-triggered">{_escape_html(ns)}</span>'
        for ns in sorted(namespaces)
    )
    return f'<div style="line-height:2.2">{tags}</div>'


def _build_focus_trees_html(focus_trees: dict[str, dict]) -> str:
    """Build focus trees display."""
    if not focus_trees:
        return '<div class="no-data">No focus trees found.</div>'
    rows = []
    for tid, data in sorted(focus_trees.items()):
        countries = data.get("country", {})
        country_str = ", ".join(
            f"{_escape_html(str(k))}" for k in (countries.keys() if isinstance(countries, dict) else [])
        ) if countries else "none"
        rows.append(
            f'<tr><td><code>{_escape_html(tid)}</code></td>'
            f'<td>{country_str}</td>'
            f'<td style="font-size:0.8rem;color:var(--text2)">{_escape_html(data.get("file", ""))}</td></tr>'
        )
    return ('<table><thead><tr><th>Tree ID</th><th>Countries</th><th>File</th></tr></thead><tbody>' +
            "\n".join(rows) + '</tbody></table>')


def _get_vanilla_stats(db_path: str | Path | None = None) -> VanillaStats:
    """Get summary statistics from the vanilla database."""
    import sqlite3

    if db_path is None:
        db_path = Path.home() / ".hoi4_mcp" / "vanilla.db"
    else:
        db_path = Path(db_path)

    stats = VanillaStats(
        db_path=str(db_path),
        exists=db_path.exists(),
    )

    if not stats.exists:
        return stats

    try:
        conn = sqlite3.connect(str(db_path))
        tables = {
            "focuses": "vanilla_focuses",
            "events": "vanilla_events",
            "ideas": "vanilla_ideas",
            "technologies": "vanilla_technologies",
            "countries": "vanilla_countries",
            "modifiers": "vanilla_modifiers",
        }
        for attr, table in tables.items():
            try:
                row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                count = row[0] if row else 0
                setattr(stats, attr, count)
                stats.total += count
            except Exception:
                pass
        conn.close()
    except Exception:
        pass

    return stats


def generate_report(
    mod_path: str | Path,
    output_path: str | Path,
    vanilla_db_path: str | Path | None = None,
    server_version: str = "0.1.0",
) -> Path:
    """Generate a self-contained HTML report for a HOI4 mod.

    Args:
        mod_path: Path to the mod directory.
        output_path: Where to write the HTML file.
        vanilla_db_path: Path to vanilla.db (for stats).
        server_version: Version string for the footer.

    Returns:
        Path to the generated HTML file.
    """
    mod_path = Path(mod_path)
    output_path = Path(output_path)

    # ------------------------------------------------------------------
    # Build the mod index
    # ------------------------------------------------------------------
    indexer = ModIndexer(mod_path)
    index = indexer.build_index()

    # ------------------------------------------------------------------
    # Parse error.log (if available)
    # ------------------------------------------------------------------
    error_log: ErrorLog
    try:
        error_log = parse_error_log(None, tail_lines=500)
    except Exception:
        error_log = ErrorLog(path="(error reading)", errors=[])

    # ------------------------------------------------------------------
    # Get vanilla DB stats
    # ------------------------------------------------------------------
    vanilla = _get_vanilla_stats(vanilla_db_path)

    # ------------------------------------------------------------------
    # Build all HTML fragments
    # ------------------------------------------------------------------
    scripted = _build_scripted_html(index.scripted_effects, index.scripted_triggers, index.on_actions)

    # Serialize error log errors to a list of dicts for the template
    error_dicts = [
        {"category": e.category, "message": e.message, "file": e.file}
        for e in error_log.errors
    ]

    html = HTML_TEMPLATE.format(
        mod_name=_escape_html(index.mod_name),
        mod_version=_escape_html(str(index.descriptor.get("version", "unknown"))),
        files_indexed=index.files_indexed,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        server_version=server_version,

        # Tab counts
        event_count=len(index.events),
        focus_count=len(index.focuses),
        decision_count=len(index.decisions),
        idea_count=len(index.ideas),
        char_count=len(index.characters),
        scripted_count=len(index.scripted_effects) + len(index.scripted_triggers) + len(index.on_actions),
        loc_count=len(index.localisation_keys),
        error_count=error_log.total_errors,

        # Content
        overview_cards=_build_overview_cards(index, error_dicts, vanilla),
        warnings_html=_build_warnings(index),
        namespaces_html=_build_namespaces_html(index.namespaces),
        focus_trees_html=_build_focus_trees_html(index.focus_trees),
        events_rows=_build_events_rows(index.events),
        focuses_rows=_build_focuses_rows(index.focuses),
        decisions_rows=_build_decisions_rows(index.decisions),
        ideas_rows=_build_ideas_rows(index.ideas),
        chars_rows=_build_chars_rows(index.characters),
        se_html=scripted["se_html"],
        st_html=scripted["st_html"],
        oa_html=scripted["oa_html"],
        se_count=scripted["se_count"],
        st_count=scripted["st_count"],
        oa_count=scripted["oa_count"],
        loc_rows=_build_loc_rows(index.localisation_keys),
        errors_html=_build_errors_html(error_log),
        vanilla_html=_build_vanilla_html(vanilla),
    )

    # Write
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    return output_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI for generating a mod report."""
    import argparse

    parser = argparse.ArgumentParser(
        description="HOI4 Mod Report Generator — produces a self-contained HTML report.",
    )
    parser.add_argument("--mod-path", required=True, help="Path to the mod directory.")
    parser.add_argument("--output", default="mod_report.html", help="Output HTML file path.")
    parser.add_argument("--vanilla-db", help="Path to vanilla.db for stats (optional).")

    args = parser.parse_args()

    result = generate_report(
        mod_path=args.mod_path,
        output_path=args.output,
        vanilla_db_path=args.vanilla_db,
    )

    print(f"Report generated: {result}")
    print(f"Size: {result.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
