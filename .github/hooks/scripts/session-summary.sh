#!/usr/bin/env bash
# .github/hooks/scripts/session-summary.sh
# Stop hook — writes a session-end marker to the agent memory log
# Adapted from HOI4StudioGUI's session-summary.sh

INPUT=$(cat)
STOP_HOOK_ACTIVE=$(echo "$INPUT" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(d.get('stop_hook_active', False))
" 2>/dev/null)

# Avoid infinite loops
if [ "$STOP_HOOK_ACTIVE" = "True" ]; then
  echo '{"continue": true}'
  exit 0
fi

TIMESTAMP=$(date "+%Y-%m-%d %H:%M")
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
MEMORY_FILE=".github/agent-memory/MEMORY.md"

mkdir -p "$(dirname "$MEMORY_FILE")"

cat >> "$MEMORY_FILE" <<EOF

---
### [$TIMESTAMP] ⏹ Session ended
- Branch at close: \`$BRANCH\`
- Review entries above and complete the Session Completion Checklist:
  - [ ] All new IDs verified with check_id_exists / get_next_id?
  - [ ] All vanilla references verified with lookup_vanilla?
  - [ ] All new files passed validate_syntax?
  - [ ] Mistakes recorded via record_mistake?
---
EOF

echo '{"continue": true}'
