"""
learning/rules.py — Rule validation, formatting, and convenience functions.
"""

from __future__ import annotations

import json
from typing import Any

VALID_CATEGORIES = frozenset({
    "syntax", "logic", "design", "scope",
    "localisation", "id_collision", "convention", "performance",
})

VALID_SEVERITIES = frozenset({"error", "warning", "style"})

VALID_SOURCES = frozenset({
    "agent_self_correction", "human_correction",
    "game_log", "validation", "vanilla_reference", "seed",
})


class RuleValidationError(ValueError):
    """Raised when rule fields fail validation."""


def validate_rule_fields(
    *,
    category: str,
    severity: str,
    source: str,
    pattern: str,
    correction: str,
    context: str,
) -> list[str]:
    """Validate rule fields. Returns list of error messages (empty = valid)."""
    errors: list[str] = []

    if category not in VALID_CATEGORIES:
        errors.append(
            f"Invalid category '{category}'. Must be one of: {sorted(VALID_CATEGORIES)}"
        )
    if severity not in VALID_SEVERITIES:
        errors.append(
            f"Invalid severity '{severity}'. Must be one of: {sorted(VALID_SEVERITIES)}"
        )
    if source not in VALID_SOURCES:
        errors.append(
            f"Invalid source '{source}'. Must be one of: {sorted(VALID_SOURCES)}"
        )
    if not pattern.strip():
        errors.append("pattern must not be empty")
    if not correction.strip():
        errors.append("correction must not be empty")
    if not context.strip():
        errors.append("context must not be empty")

    return errors


def format_rule_for_agent(rule: dict[str, Any]) -> str:
    """Format a rule for injection into agent context.
    Compact, actionable format designed for LLM consumption.
    """
    sev_marker = {"error": "⛔", "warning": "⚠️", "style": "💡"}.get(
        rule.get("severity", "error"), "⛔"
    )
    lines = [
        f"{sev_marker} [{rule['id']}] ({rule['severity'].upper()}) {rule['context']}",
        f"  ANTI-PATTERN: {rule['pattern']}",
        f"  DO INSTEAD:   {rule['correction']}",
    ]
    if rule.get("occurrence_count", 1) > 1:
        lines.append(f"  (Seen {rule['occurrence_count']} times)")
    return "\n".join(lines)


def format_rules_block(rules: list[dict[str, Any]], title: str = "Active Learned Rules") -> str:
    """Format multiple rules as a block suitable for MCP tool response."""
    if not rules:
        return f"## {title}\n\nNo active rules for this context.\n"
    header = f"## {title} ({len(rules)} rules)\n"
    separator = "---\n"
    entries = separator.join(format_rule_for_agent(r) for r in rules)
    return header + separator + entries + "\n"


def rules_to_jsonl(rules: list[dict[str, Any]]) -> str:
    """Serialize rules to .jsonl format (one JSON object per line)."""
    return "\n".join(json.dumps(r, ensure_ascii=False) for r in rules) + "\n"


def rules_to_markdown(rules: list[dict[str, Any]]) -> str:
    """Serialize rules to human-readable markdown for review."""
    if not rules:
        return "# Learned Rules\n\nNo rules.\n"
    lines = ["# Learned Rules\n"]
    for r in rules:
        status = "~~resolved~~" if r.get("resolved") else "active"
        lines.append(f"## [{r['id']}] {r['context']} ({status})\n")
        lines.append(f"- **Category:** {r['category']}")
        lines.append(f"- **Severity:** {r['severity']}")
        lines.append(f"- **Source:** {r['source']}")
        lines.append(f"- **Occurrences:** {r.get('occurrence_count', 1)}")
        if r.get("file_path"):
            lines.append(f"- **File:** `{r['file_path']}` {r.get('line_range', '')}")
        lines.append(f"\n**Anti-pattern:** {r['pattern']}\n")
        lines.append(f"**Correction:** {r['correction']}\n")
        if r.get("resolved_note"):
            lines.append(f"**Resolution:** {r['resolved_note']}\n")
        lines.append("---\n")
    return "\n".join(lines)
