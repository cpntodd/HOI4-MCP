<!-- GAP-019:COMPLETED — Scripted GUI skill from 1.19.x scan -->
---
name: hoi4-scripted-gui
description: Use when designing, implementing, auditing, or fixing Hearts of Iron IV scripted GUIs, custom UI panels, dynamic buttons, containers, icon types, textboxes, and GUI localisation.
---

# HOI4 Scripted GUIs
<!-- GAP-021:COMPLETED -->
**Depends on:** `hoi4-feature-assets` (GFX sprite definitions) · `hoi4-events` (GUI event handlers)
**Depended on by:** `hoi4-feature-planning` · `hoi4-improvement-loop`

Use this skill for scripted GUI work: creating custom UI panels for BOP displays, faction management, custom decision interfaces, and complex mechanic UIs.

## Element Types Quick Reference

| Element | Use |
|---------|-----|
| `container` | Nestable box with position, size, clipping, background |
| `iconType` | Static/animated icon (needs `spriteType` GFX) |
| `instantTextboxType` | Text with font, alignment, max width/height |
| `buttonType` | Clickable button with animation states |
| `gridboxType` | Auto-sized grid layout |
| `listboxType` | Scrollable list |
| `windowType` | Draggable, closeable overlay |
| `scrollareaType` | Scrollable content zone |

## Quick Start: Simple Panel

```txt
my_gui = {
    container = {
        name = main_panel
        position = { x = 100 y = 50 }
        width = 400
        height = 300
        orientation = upper_left
        movable = yes
        clipping = yes
        visible = { has_country_flag = my_flag }

        iconType = {
            name = header_icon
            position = { x = 10 y = 10 }
            spriteType = "GFX_my_icon"
        }
        instantTextboxType = {
            name = title_text
            position = { x = 50 y = 10 }
            text = "my_title_loc"
            font = "hoi_18mbs"
            maxWidth = 300
            maxHeight = 30
            format = left
        }
    }
}
```

## Key Rules
- **All positions are relative to parent**: `x=0, y=0` = top-left of parent container.
- **Conditional visibility**: Each element can have `visible = { <country_scope_triggers> }`.
- **GFX must exist**: Every `spriteType` must be registered in `gfx/` — missing = blank element or CTD.
- **Clipping**: Set `clipping = yes` + explicit `width`/`height` to prevent overflow.

## Validation Checklist
- [ ] All `spriteType` references exist in registered GFX
- [ ] All localisation keys have entries
- [ ] `clipping = yes` containers have explicit `width`/`height`
- [ ] Textboxes have `maxWidth`/`maxHeight` set
- [ ] GUI is registered in `interface/` with `on_open` handler

<!-- GAP-020:COMPLETED — Real-world patterns from Toolpack + Global Market mod scans -->

## Real-World Patterns

### Flag-Based State Machine (Toolpack)
Every interactive element uses global flags for state. Toggle buttons set/clear flags; visibility checks flags.
```txt
my_button_on_click = { set_global_flag = my_feature_enabled }
my_button_off_click = { clr_global_flag = my_feature_enabled }
my_button_on_visible = { NOT = { has_global_flag = my_feature_enabled } }
```

### Mutually Exclusive Radio Pattern
Setting one flag clears all siblings — no radio group widget needed.
```txt
option_a_on_click = { set_global_flag = option_a; clr_global_flag = option_b; clr_global_flag = option_c }
```

### Multi-Target Mark & Batch Execute
Mark targets with flags, then execute on `every_country`/`every_state` with that flag.
```txt
batch_execute = { every_country = { limit = { has_country_flag = marked } <effects>; clr_country_flag = marked } }
```

### Confirmation Flow
Actions set a confirm flag + open confirmation window. The confirmation GUI reads the flag to determine action.
```txt
request_confirm = { set_global_flag = confirm_delete; set_global_flag = tp_open_confirmation_window }
confirm_effect = { if = { limit = { has_global_flag = confirm_delete } <delete_effect> } }
```

### Dynamic Lists from Arrays (Toolpack MP Action Log)
Use `dynamic_lists` to render scrollable lists from variable arrays.
```txt
dynamic_lists = { my_list_grid = { array = global.my_data_array; index = i; value = v; entry_container = my_entry } }
```

### Pure Scripted GUI Architecture (Global Market mod)
Entire systems can run without ANY decisions. All interaction through scripted GUIs with flag-based navigation tabs, global variable economies, and custom calendar systems. Use when the vanilla decision UI doesn't fit the mechanic.
