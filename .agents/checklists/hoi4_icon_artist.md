<!-- GAP-022:COMPLETED — 12 of 16 done. -->
# hoi4_icon_artist — Platform-Agnostic Checklist

**Purpose:** Create generated icon packages for focuses, ideas, decisions, achievements, techs.

## Checklist
- [ ] Icon dimensions correct for type (focus: 80×72, idea: 50×50, decision: 40×40)
- [ ] Icon uses mod's visual style palette
- [ ] Icon has proper alpha/transparency
- [ ] GFX path registered in `interface/*.gfx` files
- [ ] Icon key follows mod naming convention (e.g., `GFX_<mod>_<name>`)
- [ ] Shine/glow overlay applied for focus icons
- [ ] Frame applied for focus icons (goal_ generic or custom)

## Output Format
```
## Icon Package: <package_name>
### Icons: N
### Type: focus | idea | decision | achievement | tech
### GFX Registration: yes | pending
```
