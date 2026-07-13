<!-- GAP-019:COMPLETED — Equipment skill from 1.19.x scan -->
---
name: hoi4-equipment
description: Use when designing, implementing, auditing, or fixing Hearts of Iron IV equipment archetypes, module slots, production costs, resources, and equipment upgrade paths.
---

# HOI4 Equipment Modding
<!-- GAP-021:COMPLETED -->
**Depends on:** `hoi4-technology` (techs unlock equipment) · `hoi4-feature-assets` (equipment icons/GFX)
**Depended on by:** `hoi4-focus-trees` · `hoi4-decisions-missions` (both may grant equipment bonuses)

Use this skill for HOI4 equipment archetype work: defining new tanks, planes, ships, infantry kits, their module slots, production costs, and upgrade paths.

## Working Model

Equipment is defined through archetypes with module slots. Each module slot accepts specific module archetypes. The base variant (`is_base = yes`) is always available; upgraded variants unlock via technology.

## Quick Start: Infantry Equipment

```txt
equipment = {
    infantry_equipment = {
        type = { infantry }
        group = infantry_equipment
        is_buildable = yes
        is_base = yes
        active = yes

        modules = {
            infantry_kit = {
                category = infantry_kit
                archetype = infantry_kit
                required = yes
                default = infantry_kit_0
            }
        }

        resources = { steel = 2 }
        build_cost_ic = 0.5
        reliability = 0.9
        defense = 20
        breakthrough = 2
        maximum_speed = 4.0

        start_year = 1936
        priority = 100
    }
}
```

## Key Rules
- **`is_base`**: Base variants available from game start. Non-base variants are unlocked by research.
- **Module slots**: Each `category` maps to a module archetype. Check the module system for valid combinations.
- **`required = yes`**: Module slot must be filled for the equipment to be producible.
- **`default`**: Fallback module when no specific module is assigned — prevents production deadlock.
- **Resources per factory**: `resources = { steel = 2 }` means 2 steel per factory producing this equipment.

## Validation Checklist
- [ ] All module archetypes referenced in slots exist
- [ ] Required slots have `default` modules
- [ ] `group` matches the equipment's production category
- [ ] `start_year` is ≤ game start year for base equipment
- [ ] GFX references are valid sprite types
