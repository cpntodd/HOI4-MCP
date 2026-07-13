# HOI4-MCP — Setup Guide

> Everything you need to get the HOI4-MCP server running with your AI coding assistant.
>
> **Based on:** [Agentic-HOI4-Modding](https://github.com/klimPaskov/Agentic-HOI4-Modding) by [klimPaskov](https://github.com/klimPaskov) — the original project that pioneered AI-agent-assisted HOI4 modding with MCP servers.

---

## Quick Start (5 Minutes)

### Prerequisites
- **Python 3.10+** with `pip`
- **HOI4 game install** (for vanilla database — optional but recommended)
- **VS Code** with an MCP-capable AI assistant (GitHub Copilot, or any MCP client)

### Step 1: Install the Server

```bash
cd /path/to/HOI4-MCP/hoi4-mcp-server
pip install -e .
```

This installs the `hoi4_mcp` package in development mode. All dependencies (`mcp`, `pyyaml`) are installed automatically.

### Step 2: Build the Vanilla Database

```bash
index-vanilla --vanilla-path "/path/to/Hearts of Iron IV"
```

This parses all vanilla game files into `~/.hoi4_mcp/vanilla.db`. Takes 1-2 minutes. You only need to do this once — or after a major game update.

**Common HOI4 install locations:**
- **Steam (Linux):** `~/.steam/steam/steamapps/common/Hearts of Iron IV`
- **Steam (Windows):** `C:\Program Files (x86)\Steam\steamapps\common\Hearts of Iron IV`
- **Steam (macOS):** `~/Library/Application Support/Steam/steamapps/common/Hearts of Iron IV`

### Step 3: Configure VS Code

Create the user-level MCP config at `~/.config/Code/User/mcp.json` (Linux) or equivalent for your OS:

```json
{
  "servers": {
    "hoi4-modder": {
      "type": "stdio",
      "command": "/absolute/path/to/hoi4-mcp-server/.venv/bin/python",
      "args": [
        "-m", "hoi4_mcp.server",
        "--vanilla-db", "~/.hoi4_mcp/vanilla.db",
        "--auto-detect-mod"
      ]
    }
  }
}
```

**What `--auto-detect-mod` does:** The server scans your current workspace folder for a `descriptor.mod` file. If found, it automatically sets that as the active mod. If not found, mod-specific tools gracefully report "no mod configured."

### Step 4: Reload VS Code

`Ctrl+Shift+P` → `Developer: Reload Window`

### Step 5: Verify

Ask your AI agent: *"List the active learned rules"* — if it returns 14 seed rules, everything is working.

---

## Detailed Setup

### CLI Flags Reference

| Flag | Purpose | Default | Env Var Fallback |
|------|---------|---------|-----------------|
| `--mod-path` | Path to mod directory | `HOI4_MOD_PATH` | `HOI4_MOD_PATH` |
| `--vanilla-path` | Path to vanilla HOI4 install | `HOI4_VANILLA_PATH` | `HOI4_VANILLA_PATH` |
| `--vanilla-db` | Path to vanilla SQLite DB | `~/.hoi4_mcp/vanilla.db` | `HOI4_VANILLA_DB` |
| `--error-log-path` | Path to HOI4 error.log | Auto-detected | `HOI4_ERROR_LOG` |
| `--auto-detect-mod` | Auto-find mod from CWD | Off | — |
| `--build-vanilla-db` | Build vanilla DB on startup | Off | — |
| `--report OUTPUT.html` | Generate HTML mod report and exit | — | — |

### Environment Variables

All CLI flags have corresponding environment variables. Use these for CI/CD or container setups:

```bash
export HOI4_MOD_PATH="/home/user/MyMod"
export HOI4_VANILLA_DB="$HOME/.hoi4_mcp/vanilla.db"
export HOI4_ERROR_LOG="$HOME/.local/share/Paradox Interactive/Hearts of Iron IV/logs/error.log"
hoi4-mcp
```

### Per-Workspace Mod Config

For mod-specific workspaces, create `.vscode/mcp.json` in your mod's root:

```json
{
  "servers": {
    "hoi4-modder": {
      "type": "stdio",
      "command": "/path/to/hoi4-mcp-server/.venv/bin/python",
      "args": [
        "-m", "hoi4_mcp.server",
        "--mod-path", "/absolute/path/to/this/mod",
        "--vanilla-db", "~/.hoi4_mcp/vanilla.db"
      ]
    }
  }
}
```

Workspace configs override the user-level config for that specific project.

### Switching Mods at Runtime

Use the `set_mod_path` MCP tool — no server restart needed:

```
set_mod_path(mod_path="/path/to/other/mod")
# or auto-detect from current workspace:
set_mod_path(auto_detect=true)
```

All mod-dependent caches are automatically invalidated.

### Running Without a Mod

The server starts without a mod path. These tools work without any mod:
- `validate_syntax` — check any Clausewitz or YML snippet
- `lookup_vanilla` — query the vanilla game database
- `get_latest_errors` — parse the HOI4 error log
- `get_learned_rules` / `record_mistake` — learning system
- `export_learned_rules` / `import_learned_rules` — rule sharing

These tools require a mod path:
- `get_mod_index`, `search_mod`, `get_next_id`, `check_id_exists`, `generate_province_rgb`

---

## Troubleshooting

### "No mod path configured"
The server started without `--mod-path`, `--auto-detect-mod` didn't find a mod, and `HOI4_MOD_PATH` isn't set. Use `set_mod_path` or add a workspace `.vscode/mcp.json`.

### "Vanilla database not found"
Run `index-vanilla --vanilla-path "/path/to/hoi4"` to build it. The DB is stored at `~/.hoi4_mcp/vanilla.db`.

### Server starts but tools return errors
Check the VS Code terminal for server output. The server logs to stdout/stderr. Common issues: wrong Python path, missing dependencies, permission denied on DB path.

### Reload required after config changes
VS Code doesn't hot-reload MCP configs. Use `Developer: Reload Window` after editing `mcp.json`.
