<!-- GAP-022:PARTIAL — Representative checklist. Remaining 15 checklists to be created following this pattern. -->

# hoi4_focus_tree_auditor — Platform-Agnostic Checklist

**Purpose:** Audit focus tree files for route logic errors, missing prerequisites, broken AI weights, icon mismatches, localisation gaps, and structural issues.

**Source:** Derived from `.codex/agents/hoi4_focus_tree_auditor.toml` — same knowledge, any platform.

## Checklist

### 1. ID Uniqueness
- [ ] Every `focus = { id = ... }` has a unique ID
- [ ] No ID collisions with vanilla focuses (use `lookup_vanilla` or `check_id_exists`)
- [ ] IDs follow the mod's naming convention (check `AGENTS.md`)

### 2. Prerequisites
- [ ] Every `prerequisite = { focus = X }` references a focus that EXISTS in the mod or vanilla
- [ ] Shared prerequisites are placed on child focuses, not the parent
- [ ] `mutually_exclusive` is on EACH branch focus (listing the OTHER), not on the shared prerequisite

### 3. Position & Layout
- [ ] All x/y values are within renderable range (-10 to +10 recommended)
- [ ] No two focuses occupy the same (x, y) position in the same tree
- [ ] `relative_position_id` references an existing focus in the same tree

### 4. Completion Rewards
- [ ] Every focus has a `completion_reward = { }` block (even if empty)
- [ ] No raw `modifier = { }` in completion_reward (use `add_ideas_effect` instead)
- [ ] Rewards reference existing ideas, events, or scripted effects

### 5. AI Navigation
- [ ] Branch-point focuses have `ai_will_do = { factor = ... }` blocks
- [ ] Political branches have route-specific AI weights (different factors for different ideologies)
- [ ] AI can reach every focus in the tree (no dead-end prerequisites)

### 6. Icons & GFX
- [ ] Every `icon = GFX_...` references an existing GFX definition or vanilla icon
- [ ] DLC icons are not used without `has_dlc` gating on the focus `available`

### 7. Localisation
- [ ] Every focus has a corresponding localisation key: `<focus_id>` and `<focus_id>_desc`
- [ ] No missing or orphaned localisation keys

### 8. Cross-References
- [ ] Effects that fire events use existing event IDs
- [ ] Effects that add ideas use existing idea keys
- [ ] Effects that unlock decisions use existing decision keys

## Common Issues

| Issue | Fix |
|-------|-----|
| `mutually_exclusive` on shared prerequisite | Move to each branch focus |
| Focus at x=0, y=0 with no positioning | Add `relative_position_id` or explicit x/y |
| `completion_reward` missing entirely | Add `completion_reward = {}` |
| AI stuck at branch point | Add `ai_will_do` with ideology-gated modifiers |
| GFX icon doesn't exist | Check vanilla icon list or create custom icon |

## Output Format

```
## Focus Tree Audit: <tree_id>

### Errors (must fix)
- [file:line] Description of error

### Warnings (should fix)  
- [file:line] Description of warning

### Style (consider fixing)
- [file:line] Suggestion

### Summary
- Focuses audited: N
- Errors: N
- Warnings: N
- AI coverage: X% of branch points have ai_will_do
```
