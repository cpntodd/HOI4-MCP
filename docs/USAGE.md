# HOI4-MCP — Usage Guide

> How to use the MCP server tools and agent skills for HOI4 modding.

---

## Tool Reference

### Mod Indexing

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `get_mod_index` | Complete JSON map of mod | `summary_only`, `refresh`, `category` (events/focuses/decisions/etc.) |
| `search_mod` | Text search across mod files | `query`, `subdir`, `file_pattern`, `max_results` |

**Example:**
```
get_mod_index(category="events")  →  Only event data, not the full index
search_mod(query="add_namespace") →  Find namespace declarations
```

### ID Management

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `get_next_id` | Next safe numeric ID | `id_type` (event/focus/decision/character), `namespace`, `prefix` |
| `check_id_exists` | Verify ID is free | `id_value`, `id_type` |

**Example:**
```
get_next_id(id_type="event", namespace="mymod")  →  "mymod.7"
check_id_exists(id_value="mymod.1", id_type="event")  →  {"found": true}
```

### Validation & Debugging

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `validate_syntax` | Pre-flight syntax check | `text`, `file_type` (clausewitz/localisation) |
| `get_latest_errors` | Parsed error.log | `log_path`, `tail_lines`, `detect_recurring` |

**Example:**
```
validate_syntax(text="focus = { id = TEST completion_reward = { } }")
  →  {"is_valid": true, "warnings": [], "errors": []}

get_latest_errors(detect_recurring=true)
  →  Errors + recurring pattern suggestions for learned rules
```

### Vanilla Reference

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `lookup_vanilla` | Exact vanilla game data | `query_type`, `query` (exact ID), `search` (substring) |

**Example:**
```
lookup_vanilla(query_type="focus", search="danzig")
  →  Finds GER_danzig_or_war and all related focuses

lookup_vanilla(query_type="modifier", query="army_attack_factor")
  →  "Division attack percentage"
```

### Learning System

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `get_learned_rules` | Retrieve active rules | `context_tags`, `category`, `severity` |
| `record_mistake` | Record a correction | `category`, `context`, `pattern`, `correction`, `severity`, `source` |
| `resolve_mistake` | Deactivate a rule | `rule_id`, `note`, `superseded_by` |
| `export_learned_rules` | Export to .jsonl | `format` (json/markdown), `include_resolved` |
| `import_learned_rules` | Import from .jsonl | `input_path` |
| `session_review` | Session-end review & auto-record | `candidate_rules`, `consistency_check`, `agent_instructions_snippet` |

**Example:**
```
get_learned_rules(context_tags="focus_trees,completion_reward")
  →  3 rules about completion_reward patterns

record_mistake(
    category="syntax", context="Events with MTTH",
    context_tags="events,mtth",
    pattern="is_triggered_only with MTTH",
    correction="Remove is_triggered_only",
    severity="error", source="agent_self_correction"
)  →  "Recorded as LR-0015"
```

### Map & Runtime

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `generate_province_rgb` | Unused RGB colors | `definition_csv_path` |
| `set_mod_path` | Switch mod at runtime | `mod_path`, `auto_detect` |

### Session Review

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `session_review` | Review & record session lessons | `candidate_rules` (JSON array), `consistency_check`, `agent_instructions_snippet` |

The `session_review` tool is called by the agent during `/bye` (Phase 5). It:
- Checks each candidate lesson against the learned rules DB for duplicates
- Detects conflicts (overlapping context tags + different correction)
- Auto-records non-conflicting rules
- Flags conflicting rules for human review
- Optionally checks agent instructions for consistency with learned rules

**Example response:**
```json
{
  "summary": {
    "total_candidates": 5,
    "auto_recorded": 3,
    "needs_review": 1,
    "skipped_duplicates": 1,
    "consistency_issues": 0
  },
  "message": "Reviewed 5 candidate(s): 3 auto-recorded, 1 need review, 1 skipped (duplicates)."
}
```

---

## Common Workflows

### Workflow 1: Add a New Focus

```
1. set_mod_path(auto_detect=true)                              # Point to your mod
2. get_learned_rules(context_tags="focus_trees")               # Load focus rules
3. get_mod_index(category="focuses")                           # Check existing focuses
4. get_next_id(id_type="focus", prefix="mymod_")              # Get next ID
5. lookup_vanilla(query_type="focus", search="infantry")      # Find vanilla reference
6. [Generate your focus code]
7. validate_syntax(text="<your focus code>")                   # Check before game launch
8. record_mistake(...) if you self-corrected anything          # Learn from mistakes
```

### Workflow 2: Debug a Broken Event

```
1. get_latest_errors(detect_recurring=true)                    # Check error.log
2. search_mod(query="my_event_id")                             # Find where it's used
3. get_mod_index(category="events")                            # Check event IDs
4. lookup_vanilla(query_type="event", search="similar_event")  # Compare to vanilla
5. validate_syntax(text="<fixed event code>")                  # Verify fix
```

### Workflow 3: Audit a Mod

```
1. get_mod_index()                                             # Full mod overview
2. For each system: get_mod_index(category="<system>")        # Drill into specifics
3. search_mod(query="has_dlc")                                 # Find DLC dependencies
4. validate_syntax on each edited file                         # Pre-flight checks
5. export_learned_rules(format="markdown")                     # Document findings
```

### Workflow 4: Share Learned Rules with Team

```
1. export_learned_rules(format="json")                         # Export as .jsonl
2. Commit .hoi4-mcp-learned-rules.jsonl to your mod repo       # Share with team
3. Team member: import_learned_rules(input_path="rules.jsonl") # Import on fresh setup
```

### Workflow 5: End Session with `/bye`

```
1. Type /bye in chat                                             # Trigger Phase 5
2. Agent reviews conversation for lessons                        # Human corrections, self-corrections, patterns
3. Agent queries chronicle for past unrecorded lessons           # Cross-reference session history
4. Agent calls session_review(candidate_rules=<json>)            # Auto-record + conflict detection
5. Review results:                                                #
   - ✅ Auto-recorded rules (accepted)                           #
   - ⚠️ Rules needing your approval (conflicts found)            #
   - ℹ️ Skipped duplicates                                       #
6. Export updated rules: export_learned_rules(format="json")     # Save for team sharing
```

**What `/bye` records:** Human corrections (highest priority), agent self-corrections, new mod patterns discovered, design decisions with rationale, verified vanilla facts.

**Auto-approval rules:** A lesson is auto-recorded if no existing rule has overlapping `context_tags` with a *different* correction. If tags overlap but corrections differ → flagged for human review. Exact duplicates are silently skipped.

---

## Agent Integration (for AI Agents)

### Mandatory Pre-Flight (Phase 0)

Before generating ANY Clausewitz code, the agent MUST:

1. Determine the system being worked on (events, focus_trees, decisions, etc.)
2. Call `get_learned_rules(context_tags="<system>")`
3. Enforce all `severity=error` rules as HARD BLOCKS
4. Apply `severity=warning` rules as strong suggestions
5. Follow `severity=style` rules as conventions

### After Every Self-Correction

When the agent identifies and fixes its own mistake:
```
record_mistake(
    source="agent_self_correction",
    category=<syntax|logic|design|scope|localisation|id_collision|convention|performance>,
    context_tags="<comma-separated system tags>",
    pattern="<ANTI-PATTERN — what NOT to do>",
    correction="<what to do INSTEAD>"
)
```

### When the Human Corrects You

Human corrections are the HIGHEST PRIORITY learning signal:
```
record_mistake(
    source="human_correction",
    ... same fields as above ...
)
```

### Session Wrap-Up (`/bye` Command — Phase 5)

When the user types `/bye`, the agent MUST perform a complete session review:

1. **Extract lessons** from the current conversation (human corrections, self-corrections, new patterns, design decisions)
2. **Query chronicle** for past sessions with unrecorded HOI4 lessons
3. **Call `session_review`** with all candidate rules — the tool auto-records non-conflicting rules, flags conflicts for review
4. **Present results**: auto-recorded ✅, needs review ⚠️, skipped duplicates ℹ️, consistency issues 🔍
5. **Export** updated rules via `export_learned_rules(format="json")`

If no new lessons are found, respond: **"Nothing to do here."**

See `hoi4-modder.agent.md` → Phase 5 for the full specification.

### Skill Loading Guide

| Task | Load Skill | Context Tags |
|------|-----------|--------------|
| Events, event chains | `hoi4-events` | events, mtth, on_actions |
| Focus trees | `hoi4-focus-trees` | focus_trees, completion_reward |
| Decisions, missions | `hoi4-decisions-missions` | decisions, missions |
| Tech trees | `hoi4-technology` | technologies, research |
| Equipment | `hoi4-equipment` | equipment, modules, production |
| AI strategies | `hoi4-ai-strategies` | ai, strategies, ai_will_do |
| Scripted GUIs | `hoi4-scripted-gui` | scripted_gui, gui, ui |
| GFX assets | `hoi4-feature-assets` | assets, textures, gfx |
| Feature planning | `hoi4-feature-planning` | planning, design |
| Improvement passes | `hoi4-improvement-loop` | improvement, design |

---

## Testing

### Run All Tests
```bash
cd hoi4-mcp-server
.venv/bin/python -m pytest tests/ -v
# 101 tests in 0.18s
```

### Test Against a Real Mod
```bash
.venv/bin/python -c "
from hoi4_mcp.tools.indexer import ModIndexer
from pathlib import Path
import json
idx = ModIndexer(Path('/path/to/your/mod'))
data = json.loads(idx.build_index_json())
print(f'Events: {len(data[\"events\"])}, Focuses: {len(data[\"focuses\"])}')
"
```

### Verify Learning System
```bash
.venv/bin/python -c "
from hoi4_mcp.learning import LearnedRulesDB, seed_if_empty
db = LearnedRulesDB(); seed_if_empty(db)
print(f'Active rules: {len(db.query())}')
for r in db.query(context_tags='focus_trees'):
    print(f'  {r[\"id\"]}: {r[\"pattern\"][:60]}')
db.close()
"
```
