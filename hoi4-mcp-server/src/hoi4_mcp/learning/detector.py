"""
learning/detector.py — Detect recurring patterns in game error logs.
Groups errors by (category + normalized message stem) and flags
those appearing >= threshold times as suggested learned rules.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

# Minimal normalization: lowercase, strip file paths, strip numbers and IDs
_PATH_RE = re.compile(r"[\"\']?[\w/\\.\-]+\.(txt|yml|gfx|dds|png|ogg)[\"\']?")
_NUM_RE = re.compile(r"\b\d+\b")  # Strip any numeric value (not just 4+ digits)
_ID_RE = re.compile(r"\b\w+\.\d+\b")  # Strip dotted identifiers like "my_event.1"


def normalize_error_message(msg: str) -> str:
    """Strip variable parts from an error message to find the pattern stem."""
    s = msg.lower().strip()
    s = _PATH_RE.sub("<FILE>", s)
    s = _ID_RE.sub("<ID>", s)
    s = _NUM_RE.sub("<N>", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s)
    return s


def detect_recurring_patterns(
    errors: list[dict[str, Any]],
    threshold: int = 3,
) -> list[dict[str, Any]]:
    """Analyze parsed errors and suggest learned rules for recurring patterns.

    Args:
        errors: List of error dicts from error_log.py (each has 'category' and 'message').
        threshold: Minimum occurrences to flag as recurring.

    Returns:
        List of suggested rules (not yet recorded — agent proposes to human).
    """
    # Group by (category, normalized_message)
    signatures: Counter[tuple[str, str]] = Counter()
    message_examples: dict[tuple[str, str], str] = {}

    for err in errors:
        cat = err.get("category", "unknown")
        msg = err.get("message", "")
        if not msg:
            continue
        normalized = normalize_error_message(msg)
        sig = (cat, normalized)
        signatures[sig] += 1
        # Keep the first (most complete) example
        if sig not in message_examples:
            message_examples[sig] = msg

    suggestions: list[dict[str, Any]] = []
    for (cat, normalized), count in signatures.most_common():
        if count < threshold:
            continue

        # Infer context_tags from category
        tag_map = {
            "duplicate_id": "id_collision",
            "invalid_scope": "scopes,effects,triggers",
            "missing_loc": "localisation,keys",
            "missing_texture": "assets,textures,gfx",
            "invalid_province": "map,provinces,states",
            "bad_trigger": "triggers,scopes",
            "parse_error": "syntax,brackets,parsing",
            "unexpected_token": "syntax,parsing",
            "missing_file": "files,paths,references",
            "database_error": "database,setup",
            "unknown": "errors",
        }
        tags = tag_map.get(cat, "errors")

        # Build a human-readable suggestion
        example_msg = message_examples.get((cat, normalized), "")
        # Try to extract file reference from original message
        file_match = re.search(r"[\w/\\.\-]+\.(txt|yml)", example_msg)
        file_hint = file_match.group(0) if file_match else ""

        suggestions.append({
            "suggested_category": cat if cat in {
                "syntax", "logic", "design", "scope",
                "localisation", "id_collision", "convention", "performance",
            } else "syntax",
            "suggested_context": f"Recurring {cat} error in game log",
            "suggested_context_tags": tags,
            "suggested_pattern": example_msg[:300],
            "suggested_correction": f"[REQUIRES HUMAN INPUT] This error occurred {count} times. What is the correct approach to prevent this?",
            "suggested_severity": "error",
            "occurrence_count": count,
            "file_hint": file_hint,
            "normalized_signature": normalized,
        })

    return suggestions
