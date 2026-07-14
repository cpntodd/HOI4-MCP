#!/usr/bin/env bash
# .github/hooks/scripts/log-edit.sh
# PostToolUse hook — appends an audit line after every file edit
# Adapted from HOI4StudioGUI's log-edit.sh

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null)
TIMESTAMP=$(date "+%Y-%m-%d %H:%M")
MEMORY_FILE=".github/agent-memory/MEMORY.md"

# Only act on file-editing tools
case "$TOOL_NAME" in
  edit|create|editFiles|createFile|replace_string_in_file|create_file|multi_replace_string_in_file|insert_edit_into_file)
    FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys,json
d=json.load(sys.stdin)
ti = d.get('tool_input', {})
print(ti.get('filePath') or ti.get('path') or ti.get('file','unknown'))
" 2>/dev/null)

    mkdir -p "$(dirname "$MEMORY_FILE")"
    if [ ! -f "$MEMORY_FILE" ]; then
      echo "# Agent Memory — $(basename $PWD)" > "$MEMORY_FILE"
      echo "" >> "$MEMORY_FILE"
      echo "> This file is maintained automatically. Each session appends. Do NOT manually delete entries." >> "$MEMORY_FILE"
      echo "" >> "$MEMORY_FILE"
      echo "---" >> "$MEMORY_FILE"
    fi

    echo "" >> "$MEMORY_FILE"
    echo "### [$TIMESTAMP] Auto-logged edit" >> "$MEMORY_FILE"
    echo "- Tool: \`$TOOL_NAME\`  File: \`$FILE_PATH\`" >> "$MEMORY_FILE"
    ;;
esac

echo '{"continue": true}'
