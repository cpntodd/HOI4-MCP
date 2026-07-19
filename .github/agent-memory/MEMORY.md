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

---
### [2026-07-14 18:55] ⏹ Session ended
- Branch at close: `main`
- Review entries above and complete the Session Completion Checklist:
  - [ ] All new IDs verified with check_id_exists / get_next_id?
  - [ ] All vanilla references verified with lookup_vanilla?
  - [ ] All new files passed validate_syntax?
  - [ ] Mistakes recorded via record_mistake?
---

---
### [2026-07-14 18:56] ⏹ Session ended
- Branch at close: `main`
- Review entries above and complete the Session Completion Checklist:
  - [ ] All new IDs verified with check_id_exists / get_next_id?
  - [ ] All vanilla references verified with lookup_vanilla?
  - [ ] All new files passed validate_syntax?
  - [ ] Mistakes recorded via record_mistake?
---

---
### [2026-07-14 18:57] ⏹ Session ended
- Branch at close: `main`
- Review entries above and complete the Session Completion Checklist:
  - [ ] All new IDs verified with check_id_exists / get_next_id?
  - [ ] All vanilla references verified with lookup_vanilla?
  - [ ] All new files passed validate_syntax?
  - [ ] Mistakes recorded via record_mistake?
---

### [2026-07-16 23:16] Auto-logged edit
- Tool: `replace_string_in_file`  File: `/mnt/Data/Projects/HOI4-MCP/hoi4-mcp-server/src/hoi4_mcp/learning/db.py`

### [2026-07-16 23:16] Auto-logged edit
- Tool: `replace_string_in_file`  File: `/mnt/Data/Projects/HOI4-MCP/hoi4-mcp-server/src/hoi4_mcp/server.py`

### [2026-07-16 23:17] Auto-logged edit
- Tool: `replace_string_in_file`  File: `/mnt/Data/Projects/HOI4-MCP/hoi4-modder.agent.md`

---
### [2026-07-16 23:18] ⏹ Session ended
- Branch at close: `main`
- Review entries above and complete the Session Completion Checklist:
  - [ ] All new IDs verified with check_id_exists / get_next_id?
  - [ ] All vanilla references verified with lookup_vanilla?
  - [ ] All new files passed validate_syntax?
  - [ ] Mistakes recorded via record_mistake?
---

---
### [2026-07-16 23:18] ⏹ Session ended
- Branch at close: `main`
- Review entries above and complete the Session Completion Checklist:
  - [ ] All new IDs verified with check_id_exists / get_next_id?
  - [ ] All vanilla references verified with lookup_vanilla?
  - [ ] All new files passed validate_syntax?
  - [ ] Mistakes recorded via record_mistake?
---

### [2026-07-16 23:20] Auto-logged edit
- Tool: `multi_replace_string_in_file`  File: `unknown`

### [2026-07-16 23:21] Auto-logged edit
- Tool: `replace_string_in_file`  File: `/mnt/Data/Projects/HOI4-MCP/hoi4-modder.agent.md`

### [2026-07-16 23:21] Auto-logged edit
- Tool: `multi_replace_string_in_file`  File: `unknown`

---
### [2026-07-16 23:22] ⏹ Session ended
- Branch at close: `main`
- Review entries above and complete the Session Completion Checklist:
  - [ ] All new IDs verified with check_id_exists / get_next_id?
  - [ ] All vanilla references verified with lookup_vanilla?
  - [ ] All new files passed validate_syntax?
  - [ ] Mistakes recorded via record_mistake?
---

### [2026-07-16 23:24] Auto-logged edit
- Tool: `multi_replace_string_in_file`  File: `unknown`

### [2026-07-16 23:24] Auto-logged edit
- Tool: `multi_replace_string_in_file`  File: `unknown`

### [2026-07-16 23:24] Auto-logged edit
- Tool: `multi_replace_string_in_file`  File: `unknown`

### [2026-07-16 23:24] Auto-logged edit
- Tool: `replace_string_in_file`  File: `/mnt/Data/Projects/HOI4-MCP/docs/USAGE.md`

### [2026-07-16 23:25] Auto-logged edit
- Tool: `replace_string_in_file`  File: `/mnt/Data/Projects/HOI4-MCP/docs/SETUP.md`

---
### [2026-07-16 23:26] ⏹ Session ended
- Branch at close: `main`
- Review entries above and complete the Session Completion Checklist:
  - [ ] All new IDs verified with check_id_exists / get_next_id?
  - [ ] All vanilla references verified with lookup_vanilla?
  - [ ] All new files passed validate_syntax?
  - [ ] Mistakes recorded via record_mistake?
---

---
### [2026-07-16 23:29] ⏹ Session ended
- Branch at close: `main`
- Review entries above and complete the Session Completion Checklist:
  - [ ] All new IDs verified with check_id_exists / get_next_id?
  - [ ] All vanilla references verified with lookup_vanilla?
  - [ ] All new files passed validate_syntax?
  - [ ] Mistakes recorded via record_mistake?
---

---
### [2026-07-19 08:40] ⏹ Session ended
- Branch at close: `main`
- Review entries above and complete the Session Completion Checklist:
  - [ ] All new IDs verified with check_id_exists / get_next_id?
  - [ ] All vanilla references verified with lookup_vanilla?
  - [ ] All new files passed validate_syntax?
  - [ ] Mistakes recorded via record_mistake?
---

### [2026-07-19 08:55] Auto-logged edit
- Tool: `create_file`  File: `/mnt/Data/Projects/HOI4-MCP/hoi4-mcp-server/src/hoi4_mcp/tools/fuzzy_replace.py`

### [2026-07-19 08:56] Auto-logged edit
- Tool: `create_file`  File: `/mnt/Data/Projects/HOI4-MCP/hoi4-mcp-server/src/hoi4_mcp/sessions/models.py`

### [2026-07-19 08:56] Auto-logged edit
- Tool: `create_file`  File: `/mnt/Data/Projects/HOI4-MCP/hoi4-mcp-server/src/hoi4_mcp/sessions/index.py`

### [2026-07-19 08:56] Auto-logged edit
- Tool: `create_file`  File: `/mnt/Data/Projects/HOI4-MCP/hoi4-mcp-server/src/hoi4_mcp/sessions/store.py`

### [2026-07-19 08:56] Auto-logged edit
- Tool: `create_file`  File: `/mnt/Data/Projects/HOI4-MCP/hoi4-mcp-server/src/hoi4_mcp/sessions/__init__.py`

### [2026-07-19 08:58] Auto-logged edit
- Tool: `create_file`  File: `/mnt/Data/Projects/HOI4-MCP/hoi4-mcp-server/src/hoi4_mcp/tools/skill_tool.py`

### [2026-07-19 08:58] Auto-logged edit
- Tool: `create_file`  File: `/mnt/Data/Projects/HOI4-MCP/hoi4-mcp-server/src/hoi4_mcp/tools/compaction.py`

### [2026-07-19 08:58] Auto-logged edit
- Tool: `create_file`  File: `/mnt/Data/Projects/HOI4-MCP/hoi4-mcp-server/src/hoi4_mcp/assembly.py`

### [2026-07-19 08:58] Auto-logged edit
- Tool: `create_file`  File: `/mnt/Data/Projects/HOI4-MCP/hoi4-mcp-server/src/hoi4_mcp/tools/loop.py`

### [2026-07-19 08:59] Auto-logged edit
- Tool: `multi_replace_string_in_file`  File: `unknown`

### [2026-07-19 08:59] Auto-logged edit
- Tool: `replace_string_in_file`  File: `/mnt/Data/Projects/HOI4-MCP/hoi4-mcp-server/src/hoi4_mcp/server.py`

---
### [2026-07-19 09:01] ⏹ Session ended
- Branch at close: `main`
- Review entries above and complete the Session Completion Checklist:
  - [ ] All new IDs verified with check_id_exists / get_next_id?
  - [ ] All vanilla references verified with lookup_vanilla?
  - [ ] All new files passed validate_syntax?
  - [ ] Mistakes recorded via record_mistake?
---

### [2026-07-19 09:03] Auto-logged edit
- Tool: `replace_string_in_file`  File: `/mnt/Data/Projects/HOI4-MCP/hoi4-mcp-server/src/hoi4_mcp/sessions/store.py`

### [2026-07-19 09:04] Auto-logged edit
- Tool: `replace_string_in_file`  File: `/mnt/Data/Projects/HOI4-MCP/hoi4-mcp-server/src/hoi4_mcp/sessions/store.py`

---
### [2026-07-19 09:04] ⏹ Session ended
- Branch at close: `main`
- Review entries above and complete the Session Completion Checklist:
  - [ ] All new IDs verified with check_id_exists / get_next_id?
  - [ ] All vanilla references verified with lookup_vanilla?
  - [ ] All new files passed validate_syntax?
  - [ ] Mistakes recorded via record_mistake?
---
