<!-- GAP-022:PARTIAL — 4 of 16 checklists done. -->
# hoi4_localisation_auditor — Platform-Agnostic Checklist

**Purpose:** Audit localisation files for missing keys, orphaned keys, scripted loc errors, tooltip formatting, and dynamic text correctness.

## Checklist
- [ ] Every code-referenced key has a localisation entry
- [ ] No orphaned localisation entries (keys with no code reference)
- [ ] All languages in `localisation/` have the same set of keys
- [ ] `KEY:0 "value"` format correct (version 0 for all entries)
- [ ] No BOM in UTF-8 files
- [ ] Scripted localisation `[Scope.GetSomething]` references are valid
- [ ] `£var_name|0£` format correct in dynamic text
- [ ] Color markup `§R§!` etc. is properly closed
- [ ] No hardcoded English text in non-English localisation files
- [ ] Event option names use correct suffix convention (`.a`, `.b`, `.c`)

## Common Issues
| Issue | Fix |
|-------|-----|
| Missing key shows raw string in-game | Add entry to ALL language YML files |
| Orphaned key bloats files | Remove unused keys |
| Wrong BOM | Save as UTF-8 without BOM |
| Color tag not closed | Add closing `§!` after color section |

## Output Format
```
## Localisation Audit
### Missing Keys: N
### Orphaned Keys: N
### Format Errors: N
```
