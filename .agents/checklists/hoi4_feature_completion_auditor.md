<!-- GAP-022:PARTIAL — 6 of 16 checklists done. -->
# hoi4_feature_completion_auditor — Platform-Agnostic Checklist

**Purpose:** Compare feature specifications against implementation, flagging missing mechanics, incomplete wiring, or spec deviations.

## Checklist
- [ ] Every mechanic described in the spec has a corresponding implementation file
- [ ] All referenced event IDs, focus IDs, decision keys exist in mod files
- [ ] AI behavior is implemented for all major routes
- [ ] Localisation exists for all user-facing text
- [ ] GFX assets are wired for all icons, pictures, and UI elements
- [ ] On_actions are registered for all system hooks
- [ ] DLC gating is consistent between spec and implementation
- [ ] Edge cases from spec are handled in code
- [ ] No mechanics exist in code that aren't in the spec (scope creep)

## Common Issues
| Issue | Fix |
|-------|-----|
| Spec mentions mechanic not in code | Implement or update spec |
| Code has mechanic not in spec | Document or remove |
| Missing AI weights | Add ai_will_do blocks |
| GFX path referenced but not created | Create asset or update reference |

## Output Format
```
## Feature Completion Audit: <feature_name>
### Complete: N/N mechanics
### Missing: [list]
### Extra: [list]
### AI Coverage: X%
```
