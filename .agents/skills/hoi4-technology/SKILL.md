<!-- GAP-019:PARTIAL — Technology skill created. Remaining skills: equipment, map, scripted GUI, MIOs, BOP, AI strategies, ideology, country creation, cosmetic tags, intelligence agency -->
---
name: hoi4-technology
description: Use when designing, implementing, auditing, or fixing Hearts of Iron IV technology trees, tech categories, research bonuses, ahead-of-time penalties, doctrine paths, and tech localisation.
---

# HOI4 Technology Trees
<!-- GAP-021:COMPLETED -->
**Depends on:** `hoi4-events` (on_research_complete fires events) · `hoi4-feature-assets` (tech icons)
**Depended on by:** `hoi4-feature-planning` (tech tree design) · `hoi4-improvement-loop`

Use this skill for HOI4 technology tree work: adding techs, designing doctrine paths, wiring research bonuses, setting up tech categories, and ensuring AI researches sensibly.

## Working Model

A technology entry is not just a stat modifier. It is a contract across:

- Tech key and tech file
- Category and folder placement
- Prerequisites (all required — no OR logic in vanilla)
- `on_research_complete` effects (unlock equipment, enable units, add ideas)
- `ai_will_do` weights (AI must navigate the tree)
- DLC gating via `allow = { has_dlc = "..." }`
- Localisation keys: `<tech_key>` and `<tech_key>_desc`
- Tech icons (GFX references)

## Key Rules

- **`start_year`**: The year the tech becomes available. Before this, -50% penalty per year ahead. Use historical dates as anchors.
- **`research_cost`**: Base days. Most techs range from 42 (simple) to 210 (complex). Doctrine techs are typically 100-200.
- **`prerequisites`**: All listed techs must be completed. No OR. For branching, create separate tech entries or use mutually exclusive.
- **`mutually_exclusive`**: Put on both techs in an exclusive pair. Common for doctrine branches.
- **`on_research_complete`**: Fire-and-forget effects. Common uses: `enable_equipment`, `add_ideas`, `modify_building_speed`, `country_event`.
- **AI must navigate**: Add `ai_will_do` to at least doctrine branch points and key military techs.

## Doctrine Path Example

```txt
technologies = {
    mobile_warfare = {
        start_year = 1936
        research_cost = 100
        folder = { name = doctrine_folder position = { x = 0 y = 0 } }
        categories = { mobile_warfare_doctrine }
        mutually_exclusive = { superior_firepower grand_battleplan mass_assault }
        ai_will_do = { factor = 1 }
        on_research_complete = {
            add_ideas = { mobile_warfare_idea }
        }
    }
}
```

## Common Pitfalls

- **Circular prerequisites**: A → B → A hangs the game
- **Missing `on_research_complete`**: Tech finishes but nothing happens
- **No `ai_will_do`**: AI picks randomly; common for mod-added techs to be ignored
- **Wrong folder position**: Overlapping techs in the UI tree
- **DLC techs without `allow` gate**: Base-game players see researchable DLC techs

## Validation Checklist

- [ ] All tech keys are unique across the mod and vanilla
- [ ] All prerequisites exist (use `lookup_vanilla` or `search_mod`)
- [ ] No circular prerequisite chains
- [ ] `mutually_exclusive` is symmetric (A excludes B, B excludes A)
- [ ] `start_year` matches the tech's historical/intended era
- [ ] `ai_will_do` exists on branch points and key techs
- [ ] All localisation keys exist
- [ ] Tech icons reference valid GFX entries
