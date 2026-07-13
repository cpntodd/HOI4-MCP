# HOI4 MCP Server

**Model Context Protocol server for Hearts of Iron IV modding.**

Turns your AI coding assistant into a HOI4 modding expert by giving it deterministic, structured access to your mod's structure, vanilla game data, syntax validation, and error logs — without wasting tokens on generic search/read operations.

## The Problem This Solves

When an AI helps you mod HOI4, it wastes enormous context on:
- Searching 50+ event files to find your namespace
- Reading focus trees one by one to check for ID collisions
- Hallucinating vanilla IDs (e.g., `GER_drive_to_the_west` vs real `GER_drives_to_the_west`)
- Waiting for you to run the game, check `error.log`, and paste errors back
- Miscounting brackets `{}` in complex scripts

**This MCP server replaces ALL of that.** One tool call. Deterministic results.

## Tools Exposed

| Tool | What It Does |
|------|-------------|
| `get_mod_index` | Returns a complete JSON map of your mod: every namespace, event ID, focus ID, decision key, idea, character, scripted effect, and localisation key. **One call instead of 10+ searches.** |
| `get_next_id` | Scans all files and returns the next safe numeric ID for events/focuses/decisions/characters. **Zero risk of silent overwrites.** |
| `check_id_exists` | Checks if a specific ID is already used anywhere in the mod. |
| `validate_syntax` | Checks bracket matching, YML formatting, and common pitfalls **before you launch the game**. Catches `Unexpected token` errors instantly. |
| `get_latest_errors` | Reads and parses `error.log` into structured JSON — categorized by error type, grouped by file. No more raw log scanning. |
| `lookup_vanilla` | Queries a local SQLite database of vanilla HOI4 files. Exact focus prerequisites, event chains, tech stats, modifier names. **No hallucinations.** |
| `generate_province_rgb` | Reads `definition.csv` and returns unused RGB colors for new provinces. Offloads deterministic math to code. |

## Resources

| URI | Description |
|-----|-------------|
| `mod://descriptor` | Mod metadata (name, version, dependencies) |
| `logs://error_latest` | Last 50 lines of error.log as parsed JSON |

## Quick Start

### 1. Install

```bash
cd hoi4-mcp-server
pip install -e .
```

### 2. Build the Vanilla Database (one-time)

```bash
index-vanilla --vanilla-path "/path/to/Hearts of Iron IV"
```

This parses all vanilla game files into `~/.hoi4_mcp/vanilla.db`. Takes 1-2 minutes.

### 3. Configure Your MCP Client

Add to your MCP client configuration (e.g., `claude_desktop_config.json` for Claude Desktop, or your Cline/Continue config):

```json
{
  "mcpServers": {
    "hoi4-modder": {
      "command": "python",
      "args": [
        "-m", "hoi4_mcp.server",
        "--mod-path", "/path/to/your/hoi4/mod",
        "--vanilla-db", "~/.hoi4_mcp/vanilla.db"
      ]
    }
  }
}
```

### 4. Use It

In your AI chat, the tools are automatically available. The AI can now:

```
# Before (without MCP): 5+ tool calls, 10K+ tokens
search("add_namespace") → read 3 event files → search("focus_tree") → read 4 focus files → ...

# After (with MCP): 1 tool call, ~500 tokens
get_mod_index() → Complete map of entire mod
```

## Manual Run (for testing)

```bash
hoi4-mcp --mod-path /path/to/your/mod
```

Or with environment variables:

```bash
export HOI4_MOD_PATH=/path/to/your/mod
export HOI4_VANILLA_DB=~/.hoi4_mcp/vanilla.db
hoi4-mcp
```

## Requirements

- Python 3.10+
- `mcp` package (installed automatically)
- A HOI4 mod directory (for mod-specific tools)
- HOI4 game install (for vanilla database — optional but recommended)

## Architecture

```
hoi4-mcp-server/
├── src/hoi4_mcp/
│   ├── server.py              # MCP server entry point & tool definitions
│   ├── clausewitz/
│   │   ├── parser.py          # Clausewitz .txt tokenizer & parser
│   │   └── validator.py       # Bracket matching, YML validation
│   ├── tools/
│   │   ├── indexer.py         # Mod file scanner & ID indexer
│   │   ├── id_manager.py      # Next-available-ID logic
│   │   └── error_log.py       # Error.log parser & classifier
│   └── db/
│       └── vanilla_index.py   # Vanilla HOI4 → SQLite builder & query
├── scripts/
│   └── setup.sh               # One-time setup
└── pyproject.toml
```

## How It Fits With the Agent & Skill Files

This MCP server is designed to work alongside the HOI4 modding agent prompt and skill reference:

```
┌──────────────────────────────────────────────┐
│                  AI Assistant                 │
│                                              │
│  ┌──────────────┐  ┌──────────────────────┐  │
│  │ .agent.md    │  │ SKILL.md             │  │
│  │ (persona,    │  │ (syntax reference,   │  │
│  │  workflows)  │  │  modifier lists)     │  │
│  └──────────────┘  └──────────────────────┘  │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │        HOI4 MCP Server 🔌            │    │
│  │  • get_mod_index()                   │    │
│  │  • validate_syntax()                 │    │
│  │  • lookup_vanilla()                  │    │
│  │  • get_next_id()                     │    │
│  │  • get_latest_errors()               │    │
│  │  • generate_province_rgb()           │    │
│  └──────────────────────────────────────┘    │
│              │  MCP Protocol  │              │
│              ▼                ▼              │
│     ┌──────────┐     ┌──────────────┐       │
│     │ Your Mod │     │ Vanilla HOI4 │       │
│     │  Files   │     │   SQLite DB  │       │
│     └──────────┘     └──────────────┘       │
└──────────────────────────────────────────────┘
```

The `.agent.md` file tells the AI **how** to think about HOI4 modding.  
The `SKILL.md` file tells the AI **what** syntax to use.  
The **MCP server** gives the AI **deterministic data** about the specific mod and game.
