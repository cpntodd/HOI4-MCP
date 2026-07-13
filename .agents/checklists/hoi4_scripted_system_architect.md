<!-- GAP-022:PARTIAL — 5 of 16 checklists done. -->
# hoi4_scripted_system_architect — Platform-Agnostic Checklist

**Purpose:** Create and audit reusable scripted effects, triggers, and constants for cross-mod consistency.

## Checklist
- [ ] New scripted effect has a unique, descriptive name
- [ ] Effect uses `$ARG$` parameter syntax where applicable
- [ ] Effect handles edge cases (null target, missing flag, etc.)
- [ ] Scripted trigger returns correct boolean in all conditions
- [ ] Constants are defined in `script_constants` or file-scoped
- [ ] No duplicated logic across multiple scripted effects
- [ ] All scripted effects/triggers registered in correct directory
- [ ] Variables used within effects are properly scoped (global vs country)

## Common Issues
| Issue | Fix |
|-------|-----|
| Effect doesn't handle null target | Add `exists = yes` check |
| Duplicate logic | Extract to shared scripted effect |
| Wrong variable scope | Use `set_variable` (country) or `set_global_variable` (global) |

## Output Format
```
## Scripted System Audit
### Effects Created: N
### Triggers Created: N
### Constants Defined: N
```
