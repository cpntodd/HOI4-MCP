# Agent Memory — HOI4-MCP

> This file is maintained automatically by the hoi4-modder agent.
> Each session appends a new entry. Do NOT manually delete entries.
> Last updated by: hoi4-modder agent

---

## Project Overview

- **Purpose:** MCP server + agent tooling for AI-assisted Hearts of Iron IV modding. Provides tools for mod indexing, vanilla lookups, ID collision prevention, syntax validation, error log analysis, and adaptive learning from mistakes.
- **Primary language:** Python 3.10+ (MCP server), Clausewitz script (mod files), YML (localisation)
- **Framework:** MCP (Model Context Protocol) via `hoi4_mcp` package
- **Entry point:** `hoi4-mcp-server/src/hoi4_mcp/server.py`
- **Test command:** `cd hoi4-mcp-server && .venv/bin/python -m pytest tests/ -v`
- **Key conventions:**
  - Always call `get_learned_rules` before generating Clausewitz code
  - Never use vanilla IDs from memory — always `lookup_vanilla` first
  - Never place modifiers directly in `completion_reward` — use ideas
  - Never combine `is_triggered_only = yes` with `mean_time_to_happen`
  - Always `validate_syntax` after file creation/edits

---

## Active Mod Context

<!-- Update this section when working with a specific mod -->
- **Current mod path:** (set via `set_mod_path` or `.vscode/mcp.json`)
- **Mod namespace:** (discovered via `get_mod_index`)
- **Mod custom effects/triggers:** (discovered via `get_mod_index`)

---

<!-- Agent session entries are appended below this line -->
