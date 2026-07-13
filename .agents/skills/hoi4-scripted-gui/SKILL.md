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
