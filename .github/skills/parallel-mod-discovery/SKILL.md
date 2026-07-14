---
name: parallel-mod-discovery
description: "Mandatory pre-coding phase for HOI4 modding. Runs get_mod_index, get_learned_rules, search_mod, and lookup_vanilla in parallel before ANY Clausewitz code is written. Eliminates hallucination by grounding the agent in actual mod + vanilla data."
---

# Parallel Mod Discovery

## Purpose

This skill codifies **Phase 0.5** of the hoi4-modder workflow. Before writing ANY Clausewitz code, the agent MUST run multiple discovery operations simultaneously to ground itself in the actual state of the mod and vanilla game. This prevents hallucinated IDs, non-existent modifier names, and duplicate ID collisions.

## When to Use

**Mandatory** before generating any of the following:
- Events (`.txt` in `events/`)
- National focuses (`.txt` in `common/national_focus/`)
- Decisions (`.txt` in `common/decisions/`)
- Ideas / National spirits (`.txt` in `common/ideas/`)
- Technologies (`.txt` in `common/technologies/`)
- On actions (`.txt` in `common/on_actions/`)
- Localisation (`.yml` in `localisation/`)
- Scripted effects/triggers (`.txt` in `common/scripted_effects/` or `common/scripted_triggers/`)
- Any file referencing vanilla IDs, modifiers, or country tags

## The Parallel Discovery Plan

Execute these calls **simultaneously** (batch them in a single tool call block):

### Core Triad (ALWAYS run these three)

| # | Tool | Parameters | What it returns |
|---|------|-----------|-----------------|
| 1 | `get_mod_index` | `summary_only=false` | Complete map of all mod IDs, namespaces, tokens, localisation keys |
| 2 | `get_learned_rules` | `context_tags="<relevant tags>"` | All previously recorded mistakes for this system |
| 3 | `search_mod` | `query="<key pattern>"`, `subdir="<relevant subdir>"` | Existing mod files using similar IDs or patterns |

### Supplemental (add as needed)

| # | Tool | When to add |
|---|------|-------------|
| 4 | `lookup_vanilla` | If referencing ANY vanilla ID, modifier, focus, event, idea, decision, character, or country tag |
| 5 | `get_next_id` | If creating a new event, focus, decision, or character |
| 6 | `check_id_exists` | If unsure whether a planned ID is already taken |

## Context Tag Reference

Map your task to the correct `context_tags` for `get_learned_rules`:

| Task | Tags |
|------|------|
| Events | `events, mtth, on_actions, localisation` |
| Focus trees | `focus_trees, completion_reward, modifiers, ideas` |
| Decisions | `decisions, missions, ideas` |
| Ideas/Spirits | `ideas, spirits, modifiers` |
| Technologies | `tech, equipment` |
| Characters | `characters` |
| Map editing | `map, assets` |
| Localisation | `localisation` |

## Synthesis Before Action

After ALL parallel calls return, synthesize findings:

1. **ID Collision Check:** Does the planned ID already exist? (from `get_mod_index` + `check_id_exists`)
2. **Vanilla Verification:** Do all referenced vanilla IDs actually exist? (from `lookup_vanilla`)
3. **Pattern Conformity:** Does the mod use custom scripted effects/triggers instead of vanilla ones? (from `get_mod_index`)
4. **Mistake Awareness:** Are there known anti-patterns for this system? (from `get_learned_rules`)
5. **Existing Patterns:** How does the mod currently handle similar content? (from `search_mod`)

Only after this synthesis may the agent proceed to Phase 1 (Establish Mod Context) and code generation.

## Anti-Pattern: The "I Know This" Fallacy

> **⛔ NEVER skip this phase because you "already know" a vanilla ID.** Even common IDs like `GER`, `political_power`, or `army_experience` can be modified by the mod or DLC. Always verify. Every time. No exceptions.

## Example: Before Creating a New Event

```
Task: Create event for Germany gaining a national spirit

Parallel discovery batch:
1. get_mod_index(summary_only=false)          → learn namespace, existing event IDs, idea keys
2. get_learned_rules(context_tags="events, ideas, spirits")
3. search_mod(query="germany", subdir="events")
4. lookup_vanilla(query_type="country", query="GER")    → verify tag exists
5. lookup_vanilla(query_type="idea", search="germany")  → check for naming collisions
6. get_next_id(id_type="event", namespace="<mod_ns>")   → safe next event ID
7. check_id_exists(id_value="<planned_spirit_key>")      → prevent idea collision
```
