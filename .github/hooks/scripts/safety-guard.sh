#!/usr/bin/env bash
# .github/hooks/scripts/safety-guard.sh
# PreToolUse hook — blocks destructive commands, warns on unverified mod edits
# Adapted from HOI4StudioGUI's safety-guard.sh

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null)

# ── Guard 1: Dangerous terminal commands ────────────────────────────────────
if [ "$TOOL_NAME" = "runTerminalCommand" ] || [ "$TOOL_NAME" = "terminal" ] || [ "$TOOL_NAME" = "run_in_terminal" ]; then
  CMD=$(echo "$INPUT" | python3 -c "
import sys,json
d=json.load(sys.stdin)
ti = d.get('tool_input',{})
print(ti.get('command',''))
" 2>/dev/null)

  if echo "$CMD" | grep -qEi '(rm\s+-rf\s+/|DROP\s+TABLE|DELETE\s+FROM.*WHERE\s+1|format\s+[A-Z]:|git\s+push\s+--force|git\s+reset\s+--hard|git\s+clean)'; then
    cat <<'EOJSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Blocked by safety-guard: potentially destructive command detected. Confirm explicitly with the user before retrying."
  }
}
EOJSON
    exit 0
  fi
fi

# ── Guard 2: Protect agent memory from overwrites ────────────────────────────
if [ "$TOOL_NAME" = "create" ] || [ "$TOOL_NAME" = "createFile" ] || [ "$TOOL_NAME" = "create_file" ]; then
  FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys,json
d=json.load(sys.stdin)
ti=d.get('tool_input',{})
print(ti.get('filePath') or ti.get('path',''))
" 2>/dev/null)

  if echo "$FILE_PATH" | grep -q "agent-memory/MEMORY.md"; then
    if [ -f "$FILE_PATH" ]; then
      cat <<'EOJSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "MEMORY.md already exists. Use append only — never overwrite the memory log."
  }
}
EOJSON
      exit 0
    fi
  fi
fi

# ── Guard 3: Warn on mod file edits without MCP verification ─────────────────
# Only warns (doesn't block) — legitimate quick fixes shouldn't be blocked
if [ "$TOOL_NAME" = "edit" ] || [ "$TOOL_NAME" = "replace_string_in_file" ] || [ "$TOOL_NAME" = "create_file" ] || [ "$TOOL_NAME" = "multi_replace_string_in_file" ]; then
  FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys,json
d=json.load(sys.stdin)
ti=d.get('tool_input',{})
print(ti.get('filePath') or ti.get('path',''))
" 2>/dev/null)

  # Check if this is a Clausewitz or localisation file in a mod
  if echo "$FILE_PATH" | grep -qE '\.(txt|yml)$'; then
    if echo "$FILE_PATH" | grep -qE '(events|common|localisation|history|map|decisions|national_focus)'; then
      cat <<'EOJSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "⚠️ Mod file edit detected. Ensure get_mod_index, get_learned_rules, and lookup_vanilla (for vanilla references) have been called this session BEFORE this edit. Verify all IDs with check_id_exists/get_next_id."
  }
}
EOJSON
      exit 0
    fi
  fi
fi

echo '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}'
