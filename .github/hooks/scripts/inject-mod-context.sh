#!/usr/bin/env bash
# .github/hooks/scripts/inject-mod-context.sh
# SessionStart hook — injects mod metadata and agent memory into context
# Adapted from HOI4StudioGUI's inject-project-context.sh

INPUT=$(cat)

PROJECT_NAME=$(basename "$PWD")
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")

# Detect active mod from .vscode/mcp.json if present
MOD_PATH=""
if [ -f ".vscode/mcp.json" ]; then
  MOD_PATH=$(python3 -c "
import json, sys
try:
    with open('.vscode/mcp.json') as f:
        data = json.load(f)
    servers = data.get('servers', {})
    for name, cfg in servers.items():
        args = cfg.get('args', [])
        for i, arg in enumerate(args):
            if arg == '--mod-path' and i+1 < len(args):
                print(args[i+1])
                sys.exit(0)
except: pass
" 2>/dev/null)
fi

# Read mod descriptor if mod path found
MOD_INFO=""
if [ -n "$MOD_PATH" ] && [ -f "$MOD_PATH/descriptor.mod" ]; then
  MOD_INFO=$(head -20 "$MOD_PATH/descriptor.mod" 2>/dev/null)
fi

# Read last 40 lines of agent memory
MEMORY_SNIPPET=""
MEMORY_FILE=".github/agent-memory/MEMORY.md"
if [ -f "$MEMORY_FILE" ]; then
  MEMORY_SNIPPET=$(tail -40 "$MEMORY_FILE")
fi

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "=== HOI4-MCP PROJECT CONTEXT ===\\nProject: $PROJECT_NAME\\nBranch: $BRANCH\\n\\n=== ACTIVE MOD CONTEXT ===\\nMod path: ${MOD_PATH:-NOT DETECTED}\\n$MOD_INFO\\n\\n=== RECENT AGENT MEMORY ===\\n$MEMORY_SNIPPET\\n\\nIMPORTANT: Read the full memory file at $MEMORY_FILE before making changes. If working on a mod, call get_mod_index BEFORE writing any Clausewitz code."
  }
}
EOF
