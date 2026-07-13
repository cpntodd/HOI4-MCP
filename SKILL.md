---
name: hoi4-modding-reference
description: "Use when: need detailed HOI4 modding syntax reference — focus tree structure, event scripting, decision templates, national spirit modifiers, technology trees, OOB format, GUI definitions, localisation YML format, map file specs, AI strategy plans, scripted effects/triggers, or debugging workflows. HOI4, Hearts of Iron IV, Clausewitz, Paradox modding reference."
user-invocable: true
last_updated: "2026-07-13"
game_version: "1.15.x"
---
<!-- GAP-016:COMPLETED — Version tracking added -->
# HOI4 Modding Syntax Reference

Detailed syntax patterns, gotchas, and file format specifications for Hearts of Iron IV modding. Load this when the agent needs precise syntax for a specific task type.

## AGENT BEHAVIORAL DIRECTIVES (READ FIRST)
When using this reference file, you MUST adhere to these rules:
1. **Never Guess Syntax:** If you do not remember the exact structure for a block (e.g., GUI, Map editing), you must read the relevant section below. Do not rely on general LLM training data for Clausewitz syntax.
2. **The "Checklist" Rule:** Before closing a file generation task, mentally check the "Common Pitfalls" section for that specific task type to ensure you haven't violated any of them.
3. **Cross-File Awareness:** Syntax is useless without cross-file links. If you generate a Focus (requires GFX, localisation, on_actions), you must generate ALL accompanying syntax or explicitly state what is missing.

## Focus Trees

### File Location
`common/national_focus/<name>.txt`

### Structure
```
focus_tree = {
    id = <tree_id>
    country = { factor = 1 }
    default = yes  # optional, makes this the default tree
    
    focus = {
        id = <namespace>_<focus_name>
        icon = GFX_<icon_name>
        x = <int>
        y = <int>
        relative_position_id = <other_focus_id>  # optional
        cost = <float>  # default 10
        available_if_capitulated = yes/no
        cancel_if_invalid = yes/no  # optional
        mutually_exclusive = { focus = <other_id> }  # optional
        
        prerequisite = { focus = <id1> focus = <id2> }  # optional
        allow_branch = {  # controls line drawing
            <triggers>
        }
        available = {  # controls clickability
            <triggers>
        }
        
        completion_reward = {
            <effects>
        }
        
        ai_will_do = {
            factor = <float>
            modifier = {
                factor = <float>
                <triggers>
            }
        }
    }
}
```

### Key Rules
- **x/y range**: Keep between -10 and +10. `x=0, y=0` is top-left. Negatives go left/up, positives go right/down. Spacing of 1 unit between focuses is standard; 2 units for branches.
- **`allow_branch` vs `available`**: `allow_branch` draws the line from prerequisite. `available` controls whether the focus button is enabled. A focus can have a visible line but be greyed out.
- **`mutually_exclusive`**: Put on each branch focus, NOT the shared prerequisite. Example: if A leads to B or C, put `mutually_exclusive = { focus = C }` on B and `mutually_exclusive = { focus = B }` on C. Each mutually exclusive focus lists the other. Putting `mutually_exclusive` on prerequisite A would block both B and C from ever being taken.
- **`completion_reward`**: ALWAYS include, even if `completion_reward = {}`. Missing it = parse error.
- **`relative_position_id`**: Positions this focus relative to another. Offsets apply on top.
- **Shared focuses**: Multiple countries can share a tree by listing them in the `focus_tree` block or using separate trees that reference shared focus IDs.

### Common Pitfalls
- **Invisible focuses**: x/y outside renderable area, duplicate positions, or `allow_branch` failing (no visible line but focus exists).
- **Broken prerequisites**: Referencing a focus ID that doesn't exist in any loaded tree.
- **DLC-locked focus icons**: `GFX_goal_<dlc>_<name>` icons are DLC-specific. Base-game icons use `GFX_goal_<name>` or `GFX_goal_generic_<name>`.

---

## Events

### File Location
`events/<name>.txt`

### Country Event Structure
```
add_namespace = <namespace>

country_event = {
    id = <namespace>.<id>
    title = <localisation_key>
    desc = <localisation_key>
    picture = GFX_<picture_name>
    
    is_triggered_only = yes  # or omit for MTTH
    hide_window = yes  # for hidden events
    fire_only_once = yes  # optional
    
    trigger = {
        <conditions>  # only for MTTH events
    }
    
    mean_time_to_happen = {
        days = <int>
        modifier = {
            factor = <float>
            <conditions>
        }
    }
    
    immediate = {
        <effects>  # runs before window appears
    }
    
    option = {
        name = <localisation_key>
        <effects>
        # Chain to next event:
        country_event = { id = <namespace>.<next_id> days = <int> }
    }
    
    option = {
        name = <localisation_key>
        <effects>
    }
}
```

### News Event Structure
```
news_event = {
    id = <namespace>.<id>
    title = <localisation_key>
    desc = <localisation_key>
    picture = GFX_<picture_name>
    
    is_triggered_only = yes
    
    option = {
        name = <localisation_key>
        <effects>
    }
}
```

### Key Rules
- **`is_triggered_only = yes`**: Event fires only when called from another event/effect. No MTTH.
- **`hide_window = yes`**: Must be paired with `is_triggered_only = yes`. No popup appears. Used for backend logic.
- **`fire_only_once = yes`**: After firing once, never fires again. Omit for repeatable events.
- **MTTH events**: Use `mean_time_to_happen` without `is_triggered_only`. The `trigger` block determines eligibility. MTTH is checked every 20 days by default.
- **`immediate` block**: Effects that execute BEFORE the event window appears. Use for backend state changes.
- **Event chains**: Call the next event inside an option with `country_event = { id = X days = Y }`. `hours = Z` also works.
- **`option` blocks**: ALWAYS provide at least one, even for hidden events. Zero options = soft-lock.
- **`add_namespace`**: Placed at the top of an event file (before any event definition). It automatically prefixes all event IDs in that file. So `add_namespace = mymod` + `id = 1` produces the full event ID `mymod.1`. This prevents ID collisions without typing long prefixes on every event. Always use it.

### Event Localisation Suffix Convention
Use dot-style suffixes to match vanilla. Both styles work identically in the localisation system, but dot-style is the vanilla convention and avoids any ambiguity with event ID parsing:
- Dot-style (use this): `mymod.1.t`, `mymod.1.d`, `mymod.1.a`, `mymod.1.b`
- Legacy underscore: `mymod.1_t`, `mymod.1_d`, `mymod.1_a`, `mymod.1_b`
Match whichever convention the existing mod files use. For new mods, default to dot-style.

### Common Pitfalls
- **Forgotten `is_triggered_only`**: MTTH event with no trigger = fires randomly. Hidden event without `is_triggered_only` = may fire as MTTH.
- **Wrong namespace**: `add_namespace = mac` at top of file, then refer to `mac.1`, `mac.2`, etc.
- **`fire_only_once` + `is_triggered_only`**: Works fine, but ensure the triggering event doesn't try to fire it again.

---

## On Actions

### File Location
`common/on_actions/<name>.txt`

On actions are the **primary mechanism** for triggering events in HOI4. They hook into game lifecycle moments and fire effects at specific times.

### Structure
```
on_actions = {
    on_game_start = {          # fires once when a new game starts
        effect = {
            event_target:my_country = {
                country_event = { id = my_mod.1 }
            }
        }
    }

    on_focus_complete = {      # fires when ANY country completes a focus
        effect = {
            if = {
                limit = { focus = my_focus_id }
                country_event = { id = my_mod.2 days = 5 }
            }
        }
    }

    on_war_declared = {        # fires when any war is declared
        effect = {
            # FROM = declarer, ROOT = target
            if = {
                limit = { tag = FROM }
                country_event = { id = my_mod.3 }
            }
        }
    }
}
```

### Key On Action Types
| On Action | Fires When | Scope Notes |
|-----------|-----------|-------------|
| `on_game_start` | New game begins | Country scope (iterates all countries) |
| `on_new_nation` | A new country is created (civil war, release) | New country is ROOT |
| `on_focus_complete` | Any country completes a national focus | Country scope |
| `on_war_declared` | A war is declared | FROM = declarer, ROOT = target |
| `on_peace` | A peace conference concludes | Country scope |
| `on_political_power_change` | PP changes by any amount | Country scope |
| `on_capitulation` | A country capitulates | FROM = capitulator, ROOT = victor |
| `on_civil_war_start` | A civil war begins | Country scope |
| `on_annex` | A country is annexed | FROM = annexer, ROOT = annexed |
| `on_puppet` | A country is puppeted | FROM = overlord, ROOT = puppet |
| `on_surrender` | A country surrenders (peace conference starts) | Country scope |
| `on_tick` | Every game tick (daily) | Country scope — be very careful with performance |
| `on_building_complete` | Any building finishes construction | State scope — FROM = building type |
| `on_unit_transfer` | A unit changes controller | Country scope |
| `on_election` | An election concludes | Country scope — fires after the election |
| `on_actions_reload` | On actions are reloaded (hot-reload) | Global scope |
| `on_government_change` | Ruling party or leader changes | Country scope |
| `on_state_control_changed` | A state changes controller | State scope — FROM = old controller, ROOT = new controller |
| `on_technology_stolen` | A tech is stolen via espionage | Country scope |

### Common Pitfalls
- **Missing scope reference**: On actions run in a generic scope. Always explicitly specify which country receives the event using a tag or `event_target:`.
- **Firing too often**: `on_political_power_change` fires on every PP tick. Wrap effects in condition checks to avoid event spam.
- **`on_tick` is expensive**: Runs every single day for every country. Use only for critical continuous mechanics (corruption decay, timed modifiers). Prefer `mean_time_to_happen` events or monthly pulses over `on_tick` when possible.

---

## Decisions & Missions

### File Location
`common/decisions/<name>.txt`

### Decision Structure
```
<category_name> = {
    <decision_name> = {
        icon = GFX_<icon_name>
        
        allowed = {
            <triggers>
        }
        
        available = {
            <triggers>
        }
        
        visible = {
            <triggers>  # optional, can hide with conditions
        }
        
        cost = <int>  # PP cost to take the decision
        
        removal_cost = -1  # PP cost to cancel (-1 = free, 50 = 50 PP, or a modifier block)
        
        days_remove = <int>  # optional
        days_re_enable = <int>  # optional
        
        on_map_mode = 1  # optional, enables map highlighting
        
        complete_effect = {
            <effects>
        }
        
        ai_will_do = {
            factor = <float>
        }
    }
}
```

### Mission Structure
Missions extend decisions with targeting:
```
<decision_name> = {
    # ... same as decision ...
    
    target_trigger = {
        <conditions for valid target>
    }
    
    completed_trigger = {
        <conditions marking mission complete>
    }
    
    targeted = yes  # enables target selection UI
}
```

### Key Rules
- **`allowed` vs `available` vs `visible`**: `allowed` = appears in tab. `available` = can be clicked (greyed out if false). `visible` = shown at all (hidden if false, even from tab). All default to `yes` if omitted.
- **`hidden_trigger`**: Can be nested in `available` or `allowed` for secret conditions the player doesn't see.
- **`days_remove`**: Decision auto-removes after N days. Combine with `days_re_enable` for cycling decisions.
- **`removal_cost`**: PP cost to manually cancel a decision. `removal_cost = -1` = free removal. `removal_cost = 50` = costs 50 PP. Can also use a modifier block: `removal_cost = { stability = -0.05 }`.
- **Mission scope**: `target_trigger` and `completed_trigger` run in the target's scope. Use `FROM` to reference the decision-taker.

### Common Pitfalls
- **Mission targeting**: `target_trigger` scope is the TARGET. Don't use country-scope conditions like `has_political_power` without `FROM`.
- **Missing `targeted = yes`**: Without this, missions won't enter target-selection mode.

---

## National Spirits, Ideas, Laws & Advisors

### File Location
`common/ideas/<name>.txt`

### National Spirit
```
<idea_key> = {
    picture = GFX_<icon_name>
    
    allowed = {
        <triggers>  # conditions to have this spirit
    }
    
    allowed_civil_war = {
        <side>  # which civil war side gets it
    }
    
    modifier = {
        <modifiers>
    }
    
    ai_will_do = {
        factor = <float>
    }
}
```

### Advisor
```
<advisor_key> = {
    picture = GFX_<icon_name>
    
    allowed = {
        <triggers>
    }
    
    slot = political_advisor  # or high_command, theorist, army_chief, navy_chief, air_chief
    
    cost = {
        political_power = <int>
    }
    
    modifier = {
        <modifiers>
    }
    
    ai_will_do = {
        factor = <float>
    }
}
```

### Key Rules
- **Advisor slots**: `political_advisor`, `high_command`, `theorist`, `army_chief`, `navy_chief`, `air_chief`. Check the country's `set_politics` history for available slot counts.
- **`allowed_civil_war`**: Controls which side (democratic, fascist, communist, neutral) keeps the spirit in a civil war. Without this, the original tag keeps it.
- **Idea categories**: Wrap ideas in named categories like `political_ideas = { ... }`, `country = { ... }`, etc.

---

## Characters

### File Location
`common/characters/<name>.txt`

Introduced in No Step Back. The character system replaces the old `create_country_leader` and `create_corps_commander` effects for custom leaders, generals, and advisors.

### Structure
```
characters = {
    <character_id> = {
        name = <loc_key>
        gender = male  # or female
        
        portrait = {
            civilian = {
                large = "GFX_<portrait_large>"
                small = "GFX_<portrait_small>"
            }
            army = {
                large = "GFX_<army_portrait_large>"
                small = "GFX_<army_portrait_small>"
            }
        }
        
        # Pick the role(s) the character fills:
        country_leader = {
            ideology = <ideology_key>
            traits = { <trait1> <trait2> }
            expire = "1965.1.1"  # optional
            id = -1  # -1 = auto-assign
        }
        
        advisor = {
            slot = political_advisor
            idea_token = <idea_key>
            traits = { <trait1> }
            available = { <triggers> }
            cost = 150
            id = -1
        }
        
        corps_commander = {
            group = army  # army, navy, or air
            division_template = "<template_key>"
            traits = { <trait1> }
            skill = 3
            attack_skill = 2
            defense_skill = 3
            planning_skill = 2
            logistics_skill = 1
            id = -1
        }
    }
}
```

### Key Rules
- **Character IDs must be unique** across all character files in the mod.
- **`id = -1`**: Auto-assigns a unique numeric ID. Use for characters that don't need to be referenced by ID elsewhere.
- **Portrait textures**: Must exist at the specified GFX paths. Large portraits = 156×210 px, small = 65×67 px.
- **DLC requirement**: The character system requires **No Step Back** or later. For base-game compatibility, use the legacy `create_country_leader` effect.
- **Roles can coexist**: A character can have multiple role blocks (e.g., `country_leader` + `corps_commander` for a leader who also commands armies).

---

## Country & State History Files

### Country History
`history/countries/<TAG> - <name>.txt`

This is where a country's starting situation is defined. The file runs once at game start.

```
capital = <province_id>
set_research_slots = 3

set_politics = {
    ruling_party = democratic
    last_election = "1936.1.1"
    election_frequency = 48
    elections_allowed = yes
}

set_popularities = {
    democratic = 55
    communism = 15
    fascism = 15
    neutrality = 15
}

set_technology = {
    infantry_weapons = 1
    infantry_weapons1 = 1
}

set_stability = 0.60
set_war_support = 0.40

# Starting national spirits
add_ideas = {
    <spirit_1>
    <spirit_2>
}

# DLC-gated tech setup
if = {
    limit = { has_dlc = "No Step Back" }
    set_technology = {
        gwtank_chassis = 1
    }
}

# Starting units (OOB)
if = {
    limit = { has_dlc = "No Step Back" }
    division = {
        name = "1. Infantry Division"
        template_name = "Infantry Division"
        location = <province_id>
    }
}
```

### Key Commands in Country History
| Command | Purpose |
|---------|---------|
| `capital` | Sets capital province |
| `set_research_slots` | Number of research slots (usually 3-5) |
| `set_politics` | Ruling party, elections, election frequency |
| `set_popularities` | Starting ideology support percentages |
| `set_technology` | Starting researched technologies |
| `set_stability` | Starting stability (0.00 to 1.00) |
| `set_war_support` | Starting war support (0.00 to 1.00) |
| `add_ideas` | Starting national spirits and ideas |
| `create_country_leader` | Legacy leader creation (non-NSB fallback) |
| `set_convoys` | Starting convoy count |
| `add_equipment_to_stockpile` | Starting equipment stockpile |

### State History
`history/states/<state_id>.txt`

Controls who owns, controls, and has cores on a state at game start.

```
state = {
    id = <state_id>
    name = "STATE_<id>"
    
    # Province list (defined in map/definition.csv)
    provinces = {
        <id1> <id2> <id3> ...
    }
    
    # Manpower
    manpower = <int>
    
    # Resources
    resources = {
        steel = <int>
        chromium = <int>
        oil = <int>
    }
    
    # Owner and controller
    history = {
        owner = <TAG>
        controller = <TAG>
        
        # Cores
        add_core_of = <TAG>
        
        # Starting buildings
        buildings = {
            infrastructure = <level>
            industrial_complex = <level>
            arms_factory = <level>
            dockyard = <level>
            air_base = <level>
            naval_base = <level>
            bunker = <level>
            anti_air_building = <level>
            synthetic_refinery = <level>
            fuel_silo = <level>
            radar_station = <level>
            rocket_site = <level>
            nuclear_reactor = <level>
        }
        
        # Victory points
        victory_points = {
            <province_id> <value>
        }
    }
}
```

### Key State Rules
- **Owner vs Controller**: `owner` = who the state rightfully belongs to (cores); `controller` = who occupies it at game start. These differ during occupations.
- **Buildings use levels**: Infrastructure is 1-10, most factories are 1-20. Max level depends on state category.
- **Province IDs must match `map/definition.csv`**: Mismatched IDs cause errors.
- **Manpower scales by state category**: Metropolitan states: 1M+, towns: 100K-1M, rural: <100K. Check vanilla state files for reference values.

---

## Technology Trees
<!-- GAP-015:PARTIAL — Technology Trees section added. Remaining: Equipment, Map, Scripted GUI, MIOs, BOP, AI Strategies, Ideology, Cosmetic Tags, Country Creation, Faction, Intelligence Agency, Namelist -->

### File Location
`common/technology/<name>.txt`

### Structure
```
technologies = {
    <tech_key> = {
        # Research
        enable_tech_sharing = yes  # optional
        start_year = <int>
        folder = {
            name = <folder_name>
            position = { x = <int> y = <int> }
        }
        
        # Categories
        categories = {
            <category_name>
        }
        
        # Cost
        research_cost = <float>
        base_cost = <float>  # optional, overrides research_cost for base cost
        
        # Prerequisites
        prerequisites = { <tech1> <tech2> }
        
        # Effects on completion
        on_research_complete = {
            <effects>
        }
        
        # AI behavior
        ai_will_do = {
            factor = <float>
            modifier = {
                factor = <float>
                <triggers>
            }
        }
        
        # Optional: mutually exclusive
        mutually_exclusive = { <other_tech> }
        
        # Optional: DLC requirement
        allow = {
            has_dlc = "<dlc_name>"
        }
    }
}
```

### Key Rules
- **`start_year`**: Year the tech becomes available. Before this year, a -50% research penalty applies per year ahead of time.
- **`folder`**: Organizes techs in the UI tree. Position is relative within the folder.
- **`categories`**: Assigns techs to research categories (e.g., `infantry_weapons`, `industry`, `air_doctrine`). Categories are defined separately.
- **`prerequisites`**: Simple list of tech keys. No OR logic — all prerequisites must be completed. Use `any_scope` or multiple tech entries for branching prerequisites.
- **`research_cost`**: Base days to research. Modified by research speed bonuses.
- **`on_research_complete`**: Effects that fire when research finishes. Use for unlocking equipment, enabling units, adding ideas.
- **`mutually_exclusive`**: Used for doctrine paths (e.g., Mobile Warfare vs Superior Firepower). Put on EACH mutually exclusive tech.
- **Doctrine trees**: Use `folder` groups and `mutually_exclusive` to create branching doctrine paths.

### Technology Categories
Defined in `common/technology_tags/`:
```
<category> = {
    name = <localisation>
    sprite = <gfx_index>
}
```

### Common Pitfalls
- **Missing prerequisites**: A tech with `prerequisites = { tech_a }` where `tech_a` doesn't exist anywhere.
- **Circular prerequisites**: Tech A requires Tech B which requires Tech A — game hangs.
- **Wrong start_year**: Setting `start_year` too early makes the tech researchable in 1936 at full speed.
- **No `ai_will_do`**: Without AI weights, AI picks techs randomly, often ignoring critical military techs.

---

## Vanilla Modifier Reference

Commonly used vanilla modifiers for national spirits, ideas, leader traits, and focus rewards.

### Stability & Political
| Modifier | Type | Range |
|----------|------|-------|
| `stability_factor` | % | -1.0 to 1.0 (e.g., `0.10` = +10%) |
| `war_support_factor` | % | -1.0 to 1.0 |
| `political_power_factor` | % | -1.0 to 1.0 |
| `political_power_cost` | flat | Negative = cheaper, positive = more expensive |
| `command_power_gain_mult` | multiplier | `0.1` = +10% CP gain |
| `drift_defence_factor` | % | 0.0 to 1.0 (e.g., `0.25` = +25% drift defense) |
| `communism_drift` | flat | Daily ideology drift (positive = toward, negative = away) |
| `fascism_drift` | flat | Daily ideology drift |

### Production & Economy
| Modifier | Type | Range |
|----------|------|-------|
| `production_factory_efficiency_gain_factor` | % | Factory output efficiency gain |
| `production_factory_max_efficiency_factor` | % | Maximum factory efficiency cap |
| `production_speed_dockyard_factor` | % | Dockyard output speed |
| `industrial_capacity_factory` | flat | Raw factory count |
| `industrial_capacity_dockyard` | flat | Raw dockyard count |
| `consumer_goods_factor` | % | Negative reduces consumer goods needed |
| `production_lack_of_resource_penalty_factor` | % | Reduces penalty from resource shortages |
| `research_speed_factor` | % | Global research speed |

### Military — Army
| Modifier | Type | Range |
|----------|------|-------|
| `army_morale_factor` | % | Division morale (org recovery) |
| `army_org_factor` | % | Maximum organization |
| `army_org_regain` | % | Organization regain rate |
| `army_attack_factor` | % | Division attack |
| `army_defence_factor` | % | Division defense |
| `army_speed_factor` | % | Division movement speed |
| `army_core_attack_factor` | % | Attack on core territory |
| `army_core_defence_factor` | % | Defense on core territory |
| `breakthrough_factor` | % | Division breakthrough stat |
| `max_organisation` | % | Maximum org for all divisions |
| `max_planning_factor` | % | Planning bonus cap |
| `planning_speed` | % | Planning speed |
| `dig_in_speed_factor` | % | Entrenchment speed |
| `land_reinforce_rate` | % | Reinforcement speed |
| `supply_consumption_factor` | % | Negative reduces supply consumption |
| `experience_gain_army_factor` | % | Army XP gain rate |
| `experience_gain_army_unit_factor` | % | Division XP gain rate |
| `army_fuel_consumption_factor` | % | Fuel consumption |

### Military — Air & Navy
| Modifier | Type | Range |
|----------|------|-------|
| `air_attack_factor` | % | Air attack |
| `air_agility_factor` | % | Air agility |
| `air_detection` | % | Air detection |
| `air_mission_efficiency` | % | All air mission efficiency |
| `ground_attack_factor` | % | CAS ground attack |
| `air_fuel_consumption_factor` | % | Aircraft fuel use |
| `naval_speed_factor` | % | Ship speed |
| `naval_detection` | % | Naval detection |
| `naval_hit_chance` | % | Naval hit chance |
| `naval_morale_factor` | % | Naval morale |

### Diplomacy & Trade
| Modifier | Type | Range |
|----------|------|-------|
| `trade_opinion_factor` | % | Trade deal acceptance |
| `opinion_gain_monthly_factor` | % | Monthly opinion drift |
| `lend_lease_tension` | % | Tension from lend-lease |
| `send_volunteers_tension` | % | Tension from volunteers |
| `send_volunteer_factor` | % | Volunteer limit |
| `supply_factor` | % | Supply to allies |

### Other
| Modifier | Type | Range |
|----------|------|-------|
| `surrender_limit` | % | Surrender progress threshold |
| `resistance_target` | % | Resistance in occupied states |
| `no_supply_grace` | hours | Hours before supply penalty (higher = better) |
| `attrition` | % | Equipment attrition |
| `winter_attrition` | % | Winter-specific attrition |
| `heat_attrition` | % | Heat-specific attrition |
| `org_loss_when_moving` | % | Org lost during movement |
| `supply_consumption_factor` | % | Supply use (negative = less supply needed) |

### Key Rules
- **All factor modifiers are percentages**: `0.10` = +10%, `-0.05` = -5%. Use decimal, never percentage integers.
- **`_factor` suffix means percentage-based**: Always a decimal multiplier.
- **Flat modifiers use integers**: `industrial_capacity_factory = 2` adds 2 factories directly. `political_power_cost = -25` reduces PP costs by 25.
- **Custom modifiers require definition**: If you create a modifier not on this list, you MUST define it in `common/modifiers/*.txt` or it will silently fail.

---

## Technology & Equipment

### Technology File
`common/technology/<name>.txt`

```
technologies = {
    <tech_key> = {
        category = <category_key>
        
        allow_branch = {
            <tech_key> = 1  # prerequisite tech
        }
        
        start_year = <int>
        folder = {
            name = <folder_key>
            position = { x = <int> y = <int> }
        }
        
        research_cost = <float>
        
        on_research_complete = {
            <effects>
        }
        
        # Equipment unlocks:
        <equipment_type> = 1  # enables equipment archetype
    }
}
```

### Equipment Archetype
`common/units/equipment/<name>.txt`
```
equipment = {
    type = <type_key>
    <stat> = <value>
    # ...
}
```

### Equipment Variant
```
create_equipment_variant = {
    name = "<name>"
    type = <equipment_type>
    upgrade = {
        <upgrade_name> = <level>
    }
}
```

---

## OOB & Division Templates

### Division Template
`common/units/<name>.txt`
```
division_template = {
    name = "<name>"
    regiments = {
        <regiment_key> = { x = <int> y = <int> }
    }
    support = {
        <support_key> = { x = <int> y = <int> }
    }
    priority = <int>
}
```

### OOB File
`history/units/<country_tag>_<year>_<month>_<day>.txt` (e.g., `GER_1936_1_1.txt`, `SOV_1939_8_23.txt`)
```
units = {
    division = {
        name = "<name>"
        location = <province_id>
        division_template = "<template_name>"
        start_experience = <float>
        force_equipment_variants = {
            <type> = { <variant_name> }
        }
    }
}
```

---

## GUI & Interface

### GUI File
`interface/<name>.gui`
```
guiTypes = {
    containerWindowType = {
        name = "<unique_name>"
        position = { x = <int> y = <int> }
        size = { width = <int> height = <int> }
        moveable = yes/no
        clipping = yes/no
        Orientation = <upper_left/center/...>
        
        iconType = {
            name = "<unique_name>"
            position = { x = <int> y = <int> }
            spriteType = "GFX_<sprite_name>"
        }
        
        instantTextBoxType = {
            name = "<unique_name>"
            position = { x = <int> y = <int> }
            size = { width = <int> height = <int> }
            text = "<text_key>"
            font = "<font_name>"
            maxWidth = <int>
            maxHeight = <int>
            format = <left/center/right>
        }
        
        buttonType = {
            name = "<unique_name>"
            position = { x = <int> y = <int> }
            size = { width = <int> height = <int> }
            spriteType = "GFX_<sprite_name>"
            effect = "<effect_key>"
        }
    }
}
```

### GFX Sprite Definitions
`interface/<name>.gfx`
```
spriteTypes = {
    spriteType = {
        name = "GFX_<sprite_name>"
        texturefile = "gfx/interface/<path>.dds"
        noOfFrames = <int>  # default 1
    }
}
```

### Key Rules
- **Unique `name`**: Every element within a GUI file must have a unique `name` attribute.
- **`parent` references**: If omitted, the element is a child of the root container.
- **`position` is relative**: Inside a container, positions are relative to the parent's top-left.
- **`clipping = yes`**: Clips child elements to the container bounds. Crucial for scrollable lists.
- **Texture format**: `.dds` files with DXT1/DXT5 compression. Paths are relative to the mod's `gfx/` folder.

---

## Localisation

### File Location
`localisation/english/<name>_l_english.yml`
(or `french`, `german`, `spanish`, `polish`, `russian`, `braz_por`, `japanese`, `simp_chinese`)

### Format
```
l_english:
 KEY:0 "Value text here"
 KEY_desc:0 "Description text"
 KEY_tooltip:0 "Tooltip text"
```

### Format Rules (STRICT)
- **First line MUST be** `l_english:` on its own line (no leading space). The game silently fails to load the entire file without this header.
- **All keys MUST have exactly one leading space** (indented under `l_english:`).
- **Colon** immediately after key.
- **Version number** `0` (or `1`, `2` for gender variants) after colon, no space.
- **Space** after version number, then **quoted string**.
- **File encoding**: UTF-8 without BOM.

### Scope-Based Strings
- `[ROOT.GetName]` — country scope ROOT's name
- `[ROOT.GetNameWithFlag]` — name + flag
- `[FROM.GetRulingParty]` — FROM scope's ruling party
- `[THIS.GetName]` — current scope's name
- `[FROM.FROM.GetLeader]` — two scopes back, leader name
- `[TAG.GetName]` — specific country tag's name

### Formatting
Color codes wrap around the text they color. `§` opens a code and `§!` resets to default:
- `§Rred text§!` — Red
- `§Ggreen text§!` — Green
- `§Yyellow text§!` — Yellow
- `§Bblue text§!` — Blue
- `§Wwhite text§!` — White
- `§Hhighlighted text§!` — Highlight
- `§!` on its own resets all formatting to default
- `\n` — Newline

### Common Pitfalls
- **Missing leading space**: `KEY:0 "value"` (no space before KEY) → parse error.
- **Tab instead of space**: Invisible issue, causes silent failures.
- **Unescaped quotes inside string**: Use `\"` or avoid.
- **Key mismatch**: Event references `my_event.1.t` but localisation has `my_event.1.title`.

---

## Map Editing

### definition.csv
`map/definition.csv`
```
province_id;red;green;blue;type;is_coastal;terrain;continent
1;255;0;0;land;true;plains;europe
```
- **RGB values**: Must be unique across all provinces. The game uses these to identify provinces from the `provinces.bmp` file.
- **Terrain types**: `plains`, `forest`, `hills`, `mountain`, `desert`, `marsh`, `jungle`, `urban`.
- **Continent**: Must match a continent defined in `map/continent.txt`.

### Province Files
`map/provinces/<id>.bmp` — one BMP per province, named by province ID. Must exist for every province in `definition.csv`.

### Strategic Regions
`map/strategicregions/<name>.txt`
```
strategic_region = {
    id = <int>
    name = "<localisation_key>"
    provinces = {
        <id1> <id2> <id3> ...
    }
    weather = {
        period = {
            temperature = { <min> <max> }
            weather = { <type> = <weight> }
        }
    }
}
```

### Supply Areas
`map/supplyareas/<id>.txt`
```
supply_area = {
    id = <int>
    name = "<localisation_key>"
    value = <int>
    provinces = {
        <id1> <id2> ...
    }
}
```

### Adjacencies
`map/adjacencies.csv`
```
From;To;Type;Through;StartComment;EndComment
<prov1>;<prov2>;<type>;<prov3>;;<comment>
```
- **Types**: `sea`, `canal`, `strait`, `river`, `impassable`, `lake`.
- **`Through`**: Province the crossing passes through (for straits/canals).

### Common Pitfalls
- **Province in definition.csv but no .bmp**: Crash on load.
- **Province in strategic region but not in definition.csv**: Error on load.
- **Duplicate RGB values**: Second province overwrites first silently.
- **Wrong continent**: Province rendered on wrong part of the supply/strategic overlay.

### End-to-End Province Creation Workflow
Adding a new province requires editing files in this exact order:
1. **Paint the province** in `map/provinces.bmp` with a unique RGB color (not used by any existing province)
2. **Add a row** to `map/definition.csv` with that RGB, a new province ID, and terrain/continent data
3. **Create** `map/provinces/<new_id>.bmp` (the province texture file — can be a 1×1 px placeholder)
4. **Add the province** to a state in `history/states/<state_id>.txt` (in the `provinces = { }` list)
5. **Add the province** to a strategic region in `map/strategicregions/<region>.txt`
6. **Add the province** to a supply area in `map/supplyareas/<area>.txt`
7. **Update adjacencies** in `map/adjacencies.csv` if the province involves a river crossing, strait, or needs adjacency data
8. **Delete the map cache** folder (`map/cache/`) so the game regenerates map data on next load
9. **Test**: Load the game and verify the province appears, is clickable, and has correct terrain

---

## AI Strategies & Plans

### AI Strategy (in country history or ideas)
```
ai_strategy = {
    type = <strategy_type>
    id = "<strategy_key>"
    value = <int>  # priority weight
}
```

### AI Plan
`common/ai_strategy_plans/<name>.txt`
```
ai_strategy_plan = {
    id = "<plan_key>"
    
    enable = {
        <triggers>
    }
    
    abort = {
        <triggers>
    }
    
    <plan_type> = {
        <settings>
    }
}
```

### Key Rules
- AI plans have `enable` and `abort` trigger blocks to control activation.
- `ai_will_do` factor scaling: `factor = 0` (never pick), `factor = 1` (baseline), `factor = 10` (10x more likely). Factors are relative weights.
- Strategies defined in country history fire on game start; those in ideas fire when the idea is active.

---

## Scripted Effects & Triggers

### Scripted Effect
`common/scripted_effects/<name>.txt`
```
my_effect_name = {
    <effects using $ARG1$, $ARG2$>
}
```
Usage: `my_effect_name = { ARG1 = <value> ARG2 = <value> }`

### Scripted Trigger
`common/scripted_triggers/<name>.txt`
```
my_trigger_name = {
    <conditions using $ARG1$, $ARG2$>
}
```
Usage: `my_trigger_name = { ARG1 = <value> ARG2 = <value> }` inside any trigger block.

### Key Rules
- **Argument passing**: Arguments use `$ARG_NAME$` in the definition and are passed as `ARG_NAME = value` at the call site.
- **Both are globally scoped**: Scripted effects/triggers from ALL files are available everywhere. Namespace carefully to avoid vanilla collisions.

---

## Script Constants

### File Location
`common/script_constants/<name>.txt`

Script constants allow you to define named numeric values used across multiple files for consistent tuning.

### Definition
```
my_category = {
    MY_KEY = 42
    ANOTHER_KEY = 7.5
}
```

### Usage
```
add_equipment_to_stockpile = {
    type = infantry_equipment
    amount = constant:my_category.MY_KEY
}
```

### Key Rules
- **Categories group constants**: Use descriptive category names matching the feature or mechanic.
- **Constants are read-only at runtime**: They cannot be changed by events or effects. Use variables for dynamic values.
- **Update both sides**: When a constant is mirrored by a file-scoped `@NAME` value (see Duration Gotcha below), update both in the same change.
- **Use for shared tuning**: AI weights, costs, durations, and threshold values that appear in multiple places belong in script constants — not hardcoded.

---

## Duration Field Gotcha (Critical)

Some HOI4 duration fields **reject** both `constant:` tokens and variable tokens, throwing `Malformed token` errors. The known sensitive fields are:

- `set_country_flag = { days = ... }`
- `set_global_flag = { days = ... }`
- Any other timed flag or timed modifier field

### The Fix — File-Scoped Constants + Meta Effect

**Step 1:** Define a file-scoped `@NAME` constant in the same script file:
```
@FLAG_DURATION = 90
```

**Step 2:** Use it directly:
```
set_country_flag = {
    flag = my_flag
    days = @FLAG_DURATION
}
```

**Step 3:** Mirror the value in `common/script_constants/` for cross-file consistency:
```
my_tuning = {
    FLAG_DURATION = 90
}
```

**Step 4:** If the field also rejects variable tokens, wrap the whole block in a `meta_effect`:
```
meta_effect = {
    set_temp_variable = { temp = mtth:my_duration_calc }
    set_country_flag = {
        flag = my_flag
        days = @FLAG_DURATION  # use the file-scoped constant, not the variable
    }
}
```

Update the `@NAME` value and the `script_constants` entry together whenever tuning changes.

---

## Design Quality Standards

### Focus Trees — Real Branches vs Filler
- A focus tree is a country's playable identity, not a reward ladder. Include political routes, industry, military, diplomacy, expansion, and special mechanics.
- A branch of one or two focuses with only stat modifiers is not a real branch. A real branch needs multiple focuses, at least one mechanical unlock, a meaningful choice/fork, and a clear end-state payoff.
- **Rewards should unlock gameplay**: decisions, missions, units, advisors, leaders, claims, cores, war goals, buildings, events, mechanics, route access, or AI behavior changes. Flat modifiers are supporting rewards, not the main design.
- Political routes should update the visible country package: leader, portrait, advisor roster, ruling party, party names, ideology, cosmetic name, flag, national spirits, and AI strategy.
- Every major branch should answer: "What does the player DO after finishing this?"

### Decisions — Actions, Not a Store
- A decision represents a country DOING something — commit resources, accept risk, meet a deadline, hold a location, secure supply, or manage foreign access. It is not a political-power stat purchase.
- **Use varied costs**: army/navy/air XP, equipment, manpower, fuel, convoys, stability, war support, command power, time pressure, unit placement — not just political power.
- **Timed missions** are for deadline-driven objectives (hold capitals, guard borders, secure rail hubs). **Goal-style missions** should auto-complete when conditions are met — don't make the player click again after already doing the work.
- **Dynamic values**: Costs, durations, cooldowns, and AI willingness should scale with country size, industry, war state, stability, previous outcomes, and campaign stage. Fixed values are tuning anchors, not defaults.
- **Reward quality**: Small modifiers (+1%, -2%) are "fairy dust." A decision reward should change what the player chooses next, open/upgrade a decision family, move a visible mechanic value enough to matter, change the map/production/logistics/diplomacy, or create a real tradeoff with a failure state.

### Ideas — Lifecycles, Not Static Stacks
- National spirits should change over the course of a game. They should be added, upgraded, downgraded, replaced, or removed by focuses, decisions, events, wars, or reforms.
- Starting penalties and negative spirits must create pressure the player must answer. Harmless negative modifiers that can be ignored are not valid design.
- Route-specific ideas should be removed when the player takes a different route. Avoid dead idea stacks that accumulate forever.

### AI — Content Must Be Navigable
- Every major focus route, decision family, and event chain needs `ai_will_do` weights or AI strategy plans so AI-controlled countries can navigate the content.
- Route-specific AI should understand when to choose each political route, when to expand, when to prioritize industry, and when to join or form factions.
- AI strategies defined in country history fire on game start; those in ideas fire when the idea is active.

---

## Debugging Workflow

### Step 1: Check error.log
Path: `~/Documents/Paradox Interactive/Hearts of Iron IV/logs/error.log`
(or Windows: `%USERPROFILE%\Documents\Paradox Interactive\Hearts of Iron IV\logs\error.log`)

### Step 2: Classify Errors
| Error Pattern | Likely Cause |
|---|---|
| `Unexpected token: <x>` | Unclosed bracket before this line |
| `Duplicate ID: <x>` | Two definitions share the same ID; second overwrites first |
| `Invalid scope` | Using a country-scope effect in a state scope (or vice versa) |
| `Missing localisation key` | A string key has no matching YML entry |
| `Could not find texture` | GFX path is wrong or file is missing |
| `Invalid province id` | Province in map file doesn't exist in definition.csv |
| `Trigger not valid in this context` | Using a trigger where an effect is expected (or vice versa) |

### Step 3: Silent Failures (no error, still broken)
- **Duplicate IDs**: Second definition silently replaces first. Check all files for duplicate keys.
- **Wrong scope chains**: `FROM` points to wrong entity. Trace the event chain carefully.
- **Missing `is_triggered_only`**: Event coded as MTTH but never triggers because `trigger` is too narrow.
- **Focus `allow_branch` returning false**: Focus exists but no line drawn to it. Check the trigger.

### Step 4: Crash Diagnosis
- **Check `exception.log`**: Usually in the same `logs/` folder.
- **Map crashes**: Verify `definition.csv` ↔ `provinces/*.bmp` consistency. One mismatch = CTD.
- **Event loops**: Event A → Event B → Event A with `days = 0`. Add a flag check or `fire_only_once`.

---

## DLC Feature Reference

| Feature | Required DLC |
|---------|-------------|
| Autonomy system | Together for Victory |
| Puppet interactions | Together for Victory |
| Equipment conversion | Death or Dishonor |
| General traits | Waking the Tiger |
| Decision categories | Waking the Tiger |
| Ship designer | Man the Guns |
| Fuel system | Man the Guns |
| Intelligence agency | La Résistance |
| Collaboration government | La Résistance |
| Compliance system | La Résistance |
| Faction management | Battle for the Bosporus |
| Tank designer | No Step Back |
| Officer corps | No Step Back |
| Plane designer | By Blood Alone |
| Medal system | By Blood Alone |
| International market | Arms Against Tyranny |
| Military industrial org | Arms Against Tyranny |
| Raids | Trial of Allegiance |
| German focus tree rework | Götterdämmerung |
| Late-war mechanics & raids | Götterdämmerung |
