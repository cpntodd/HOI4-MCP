<!-- GAP-019:COMPLETED — AI Strategies skill from 1.19.x scan -->
---
name: hoi4-ai-strategies
description: Use when designing, implementing, auditing, or fixing Hearts of Iron IV AI strategies, AI strategy plans, focus selection weights, diplomatic preferences, and production priorities for AI-controlled countries.
---

# HOI4 AI Strategies
<!-- GAP-021:COMPLETED -->
**Depends on:** `hoi4-focus-trees` (strategies guide AI through focus trees) · `hoi4-events` (strategies fire events)
**Depended on by:** `hoi4-feature-planning` · `hoi4-improvement-loop`

Use this skill for AI strategy work: telling AI countries which focuses to pick, who to ally with, what to produce, and when to go to war.

## Working Model

AI strategies use a `type`/`id`/`value` pattern where `value` is an integer weight: higher = stronger preference, negative = avoidance.

## Quick Start: Historical Focus Strategy

```txt
GER_historical_focus = {
    allowed = { original_tag = GER }
    enable = { tag = GER }
    abort = {
        has_completed_focus = GER_danzig_or_war
    }

    ai_strategy = {
        type = focus
        id = GER_rhineland
        value = 100
    }
    ai_strategy = {
        type = alliance
        id = ITA
        value = 50
    }
    ai_strategy = {
        type = antagonize
        id = POL
        value = 80
    }
}
```

## Key Rules
- **`allowed`**: Country-scope trigger. Strategy only activates for matching countries.
- **`abort`**: When true, strategy permanently deactivates. Critical for one-time historical behaviors.
- **Strategy types**: `focus` (pick specific focus), `alliance` (seek alliance), `antagonize` (prepare war), `production` (build specific equipment), `research` (prioritize tech).
- **Plans can chain**: One plan can `set_strategy = <next_plan>` to sequence AI behavior.

## Validation Checklist
- [ ] `allowed` trigger is scoped correctly to the right country
- [ ] `abort` condition eventually becomes true (strategy doesn't permanently lock AI)
- [ ] All referenced focus IDs exist in the mod or vanilla
- [ ] `value` weights make sense relative to other strategies (0 = ignored by AI)
