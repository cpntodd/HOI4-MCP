<!-- GAP-022:PARTIAL — 2 of 16 checklists done. 14 remaining. -->

# hoi4_decision_mission_auditor — Platform-Agnostic Checklist

**Purpose:** Audit decision and mission files for cost balance, trigger correctness, AI behavior, tooltip accuracy, and structural issues.

**Source:** Derived from `.codex/agents/hoi4_decision_mission_auditor.toml`.

## Checklist

### 1. Key Uniqueness
- [ ] Every decision/mission has a unique key within its category
- [ ] No key collisions with vanilla decisions (use `search_mod` or `check_id_exists`)
- [ ] Keys follow mod naming convention

### 2. Visibility & Availability
- [ ] `visible = { }` used for DLC/flags gating (hides from UI entirely)
- [ ] `available = { }` used for dynamic conditions (greys out when false)
- [ ] `allowed = { }` used for final take-check
- [ ] No confusion between these three blocks

### 3. Costs
- [ ] Costs are varied — not just political power
- [ ] `cost = <int>` is appropriate for the decision's impact
- [ ] `removal_cost` is set (not defaulting to free removal)
- [ ] Time costs use `days_remove` / `days_re_enable` where appropriate

### 4. Missions
- [ ] `targeted = yes` is set for mission-style decisions
- [ ] `target_trigger` runs in TARGET scope (use `FROM` for decision-taker)
- [ ] `completed_trigger` conditions are achievable
- [ ] `on_map_mode = 1` enabled for targetable missions

### 5. AI Behavior
- [ ] `ai_will_do = { factor = ... }` exists on every decision
- [ ] AI factor reflects strategic value (not 1.0 for everything)
- [ ] AI won't bankrupt itself on expensive decisions

### 6. Effects
- [ ] `complete_effect` fires events that exist
- [ ] `complete_effect` adds ideas that exist
- [ ] No silent failures (effects with missing targets)

### 7. Localisation
- [ ] Decision title, description, and tooltip keys exist
- [ ] `custom_effect_tooltip` used for complex effects

## Common Issues

| Issue | Fix |
|-------|-----|
| Decision costs only PP | Add XP, equipment, manpower, stability costs |
| `visible` used where `available` should be | `visible` hides entirely; `available` greys out |
| Mission `target_trigger` missing `FROM` | Target scope doesn't know about decision-taker |
| No `ai_will_do` | AI never takes the decision |
| Effect references non-existent event/idea | Silent failure at runtime |

## Output Format

```
## Decision Audit: <category_name>

### Errors (must fix)
- [key] Description

### Warnings (should fix)
- [key] Description

### AI Coverage
- X of Y decisions have ai_will_do
```
