<!-- GAP-018:COMPLETED — Project-wide conventions for AI agents working in this repo -->

# AGENTS.md — HOI4-MCP Project Conventions

Repository-wide rules for all AI agents (Codex, DeepSeek, Claude, Z.AI, or any MCP-capable assistant) working on this project.

> **Based on:** [Agentic-HOI4-Modding](https://github.com/klimPaskov/Agentic-HOI4-Modding) by [klimPaskov](https://github.com/klimPaskov) — the original project that established AI-agent-assisted HOI4 modding with MCP servers.

## File Structure Conventions

- **Mod content files** (`.txt` Clausewitz, `.yml` localisation): Follow Paradox Interactive naming — lowercase with underscores, no spaces.
- **Skill files**: `.agents/skills/<skill-name>/SKILL.md` — each skill is a directory with a `SKILL.md` file.
- **Agent definitions**: `.codex/agents/` for Codex-specific TOML files (reference only for non-Codex platforms).
- **MCP server source**: `hoi4-mcp-server/src/hoi4_mcp/` — Python package with submodules.
- **Tests**: `hoi4-mcp-server/tests/` — pytest, one test file per module.
- **Reference data**: `paradox_wiki/` — offline wiki snapshots as Markdown.

## Coding Conventions

### Python (MCP Server)
- Python 3.10+ with `from __future__ import annotations`.
- Follow PEP 8 with 100-column soft limit.
- Lazy initialization for caches (build on first access, not at startup).
- Structured error responses: all tool error paths return `{"success": false, "error_code": "...", "message": "...", "help": "..."}`.
- Use `pathlib.Path` for all file paths, not `os.path`.
- SQLite via `sqlite3` with WAL journal mode and row factories.

### Clausewitz Script (HOI4 Mod Files)
- Always include `completion_reward = {}` on every focus, even if empty.
- Never place `modifier = { }` directly in `completion_reward` — use `add_ideas_effect`.
- Never combine `is_triggered_only = yes` with `mean_time_to_happen`.
- Use `add_namespace` at the top of every event file.
- Validate bracket matching with `validate_syntax` before game launch.

### Agent Prompt / Skills
- Skills should contain both concrete templates AND design philosophy.
- Every skill should have: Quick Start, Common Patterns, Validation Checklist sections.
- Skills reference each other — add dependency notes at the top of each skill.
- Agent prompt is the single source of truth for persona and workflow.

## ID & Namespace Rules
- Event IDs: `<namespace>.<number>` — always use `get_next_id` before creating.
- Focus IDs: `<prefix>_<descriptive_name>` — never guess, use `get_next_id`.
- Decision/idea keys: lowercase with underscores, descriptive.
- Always check `check_id_exists` before using any new ID.
- Vanilla IDs are in `~/.hoi4_mcp/vanilla.db` — use `lookup_vanilla`, never guess.

## Learning System (GAP-000)
- Before generating ANY Clausewitz code, call `get_learned_rules` with relevant context tags.
- After every self-correction, call `record_mistake(source="agent_self_correction", ...)`.
- After every human correction, call `record_mistake(source="human_correction", ...)`.
- Human corrections are the HIGHEST PRIORITY learning signal.
- Export learned rules to `.jsonl` for team sharing — commit to mod repos.

## Mod Detection
- Server auto-detects mods via `descriptor.mod` in CWD/parent directories.
- Use `set_mod_path` tool for runtime switching between mod workspaces.
- Each mod project can have `.vscode/mcp.json` for workspace-specific configuration.

## Testing
- All new modules require pytest coverage.
- Test files go in `hoi4-mcp-server/tests/`.
- Use fixture files (synthetic `.txt`/`.yml`) rather than requiring HOI4 install.
- Run tests with: `cd hoi4-mcp-server && .venv/bin/python -m pytest tests/ -v`

## Git
- Branch: `main`
- Commit style: `type: description (GAP-XXX)` where type is `feat`, `fix`, `docs`, `test`, `refactor`.
- Never commit `.venv/`, `__pycache__/`, `.pytest_cache/`, or database files.
- The `.hoi4-mcp-learned-rules.jsonl` file SHOULD be committed to mod repos.
