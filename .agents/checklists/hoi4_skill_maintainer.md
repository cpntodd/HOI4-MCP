<!-- GAP-022:COMPLETED — 15 of 16 done. -->
# hoi4_skill_maintainer — Platform-Agnostic Checklist

**Purpose:** Create, update, and audit `.agents/skills/` files for completeness and consistency.

## Checklist
- [ ] Skill has YAML frontmatter with name + description
- [ ] Skill has both design philosophy AND concrete templates
- [ ] Skill has Quick Start / Common Patterns / Validation Checklist sections
- [ ] Skill has GAP-021 dependency map at top
- [ ] Skill references are valid (no broken file paths)
- [ ] Skill is registered in the skill selection guide in agent prompt
- [ ] Deprecated patterns are marked or removed

## Output Format
```
## Skill Audit: <skill_name>
### Sections: Quick Start [y/n], Patterns [y/n], Checklist [y/n]
### Dependencies: documented | missing
### Agent Prompt Registration: yes | no
```
