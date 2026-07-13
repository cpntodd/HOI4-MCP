<!-- GAP-022:PARTIAL — 3 of 16 checklists done. -->
# hoi4_country_package_auditor — Platform-Agnostic Checklist

**Purpose:** Audit country definitions for tag setup, state ownership, leaders, flags, parties, focus tree loading, and starting units.

**Source:** Derived from `.codex/agents/hoi4_country_package_auditor.toml`.

## Checklist
- [ ] Country tag is unique and follows mod naming convention
- [ ] `graphical_culture` and `graphical_culture_2d` are valid GFX culture keys
- [ ] `color = { R G B }` is defined in both country file and `colors.txt`
- [ ] History file exists at `history/countries/<TAG> - <name>.txt`
- [ ] `capital = <province_id>` references a valid province
- [ ] `set_politics` defines ruling party and election settings
- [ ] `set_popularities` percentages sum appropriately
- [ ] Starting ideas are valid and exist in `common/ideas/`
- [ ] OOB units reference valid division templates and province locations
- [ ] DLC-specific setup is gated with `if = { limit = { has_dlc = "..." } }`
- [ ] Focus tree assignment in history file loads a valid tree
- [ ] Localisation exists for country name, adjective, and party names

## Common Issues
| Issue | Fix |
|-------|-----|
| Missing capital province | Check `definition.csv` for valid province ID |
| Wrong graphical_culture | Check `common/graphicalculturetype.txt` |
| OOB unit in water province | Verify province is land |

## Output Format
```
## Country Audit: <TAG>
### Errors: N
### Warnings: N
```
