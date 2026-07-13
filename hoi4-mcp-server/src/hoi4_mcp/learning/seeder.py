"""
learning/seeder.py — Bootstrap initial learned rules from the agent prompt's
hardcoded constraints. These are proven, battle-tested rules that shouldn't
wait for a mistake to be recorded.
"""

from __future__ import annotations

from typing import Any

from .db import LearnedRulesDB

SEED_RULES: list[dict[str, str]] = [
    {
        "category": "logic",
        "severity": "error",
        "context": "Focus tree completion rewards with static modifiers",
        "context_tags": "focus_trees,completion_reward,modifiers",
        "pattern": "Placing modifier = { } directly inside completion_reward of a focus",
        "correction": "The game engine does not apply static modifiers in completion_reward. Use add_ideas_effect = { idea = <your_idea> } to add a national spirit, or use a scripted effect that applies the modifier via add_static_modifier.",
        "source": "seed",
    },
    {
        "category": "logic",
        "severity": "error",
        "context": "Events using MTTH (mean time to happen)",
        "context_tags": "events,mtth,triggers",
        "pattern": "Setting is_triggered_only = yes on an event that uses mtth = { } block",
        "correction": "MTTH events fire probabilistically based on trigger conditions — they cannot be trigger-only. Remove is_triggered_only. If the event must only fire from a specific trigger, use a hidden event chain instead.",
        "source": "seed",
    },
    {
        "category": "syntax",
        "severity": "error",
        "context": "Events with hide_window",
        "context_tags": "events,hide_window,is_triggered_only",
        "pattern": "Using hide_window = yes without also setting is_triggered_only = yes",
        "correction": "hide_window requires is_triggered_only. A hidden event that isn't trigger-only would fire randomly with no UI feedback, making it impossible to debug. Always pair: hide_window = yes AND is_triggered_only = yes.",
        "source": "seed",
    },
    {
        "category": "logic",
        "severity": "error",
        "context": "Focus trees missing completion rewards",
        "context_tags": "focus_trees,completion_reward",
        "pattern": "Creating a focus node without a completion_reward = { } block",
        "correction": "Every focus MUST have a completion_reward block, even if it's empty. Missing completion_reward causes the focus to complete silently with no effect, and breaks focus tree navigation for the AI.",
        "source": "seed",
    },
    {
        "category": "scope",
        "severity": "error",
        "context": "Effect/trigger name correctness",
        "context_tags": "effects,triggers,scopes",
        "pattern": "Using effect names as triggers or vice versa (e.g., using 'add_political_power' in a trigger limit)",
        "correction": "Effects and triggers are separate namespaces. 'add_political_power' is an effect, not a trigger. 'has_political_power' is a trigger, not an effect. Always verify the correct namespace before using a command.",
        "source": "seed",
    },
    {
        "category": "design",
        "severity": "warning",
        "context": "Focus tree AI navigation",
        "context_tags": "focus_trees,ai,focus_ai",
        "pattern": "Creating focus trees without ai_will_do factors on any focus",
        "correction": "Without ai_will_do = { } blocks, the AI picks focuses essentially at random within each branch. Add ai_will_do to at least branch-point focuses to guide AI behavior toward sensible historical or alt-history paths.",
        "source": "seed",
    },
    {
        "category": "design",
        "severity": "warning",
        "context": "Decision availability vs allowability",
        "context_tags": "decisions,available,allowed",
        "pattern": "Confusing available = { } (player visibility) with allowed = { } (player can take) or visible = { } (show in UI at all)",
        "correction": "visible controls whether the decision appears in the UI at all. available controls whether it's clickable (greyed out vs active). allowed is checked at the moment of taking. Use visible for gating by DLC/flags, available for dynamic conditions, and allowed for final take-check.",
        "source": "seed",
    },
    {
        "category": "localisation",
        "severity": "error",
        "context": "Localisation key consistency",
        "context_tags": "localisation,keys,naming",
        "pattern": "Using a localisation key in code that doesn't match any entry in the .yml localisation files",
        "correction": "Every localisation key referenced in code (event titles, descriptions, focus names, idea names, button labels) MUST have a corresponding entry in the mod's localisation files. Missing keys display as raw key strings in-game. Use validate_syntax on .yml files and cross-reference with code.",
        "source": "seed",
    },
]


def seed_if_empty(db: LearnedRulesDB) -> dict[str, int]:
    """Seed the database with initial rules if it's empty.
    Returns {"seeded": N, "skipped": M} where skipped means DB already had rules.
    """
    db.ensure_schema()
    existing = db.query(include_resolved=True)
    if existing:
        return {"seeded": 0, "skipped": len(existing)}

    seeded = 0
    for rule_def in SEED_RULES:
        result = db.record(**rule_def)
        if result:
            seeded += 1

    return {"seeded": seeded, "skipped": 0}
