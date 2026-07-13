"""
learning/exporter.py — Export learned rules to .jsonl for repo sharing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .db import LearnedRulesDB
from .rules import rules_to_jsonl, rules_to_markdown


DEFAULT_EXPORT_FILENAME = ".hoi4-mcp-learned-rules.jsonl"


def export_to_file(
    db: LearnedRulesDB,
    *,
    output_path: Path | str | None = None,
    format: str = "json",  # "json" = .jsonl, "markdown" = .md
    include_resolved: bool = False,
) -> dict[str, Any]:
    """Export rules to a file. Returns {"path": ..., "count": ...}."""
    rules = db.export_all(include_resolved=include_resolved)

    if output_path is None:
        output_path = DEFAULT_EXPORT_FILENAME

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if format == "markdown":
        content = rules_to_markdown(rules)
        if not output_path.suffix:
            output_path = output_path.with_suffix(".md")
    else:
        content = rules_to_jsonl(rules)
        if not output_path.suffix:
            output_path = output_path.with_suffix(".jsonl")

    output_path.write_text(content, encoding="utf-8")

    return {
        "path": str(output_path),
        "count": len(rules),
        "format": format,
    }


def import_from_file(
    db: LearnedRulesDB,
    *,
    input_path: Path | str,
) -> dict[str, Any]:
    """Import rules from a .jsonl file. Returns {"imported": N, "skipped": M}."""
    input_path = Path(input_path)
    if not input_path.exists():
        return {"imported": 0, "skipped": 0, "error": f"File not found: {input_path}"}

    rules: list[dict[str, Any]] = []
    for line_num, line in enumerate(input_path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            rules.append(json.loads(line))
        except json.JSONDecodeError as e:
            # Skip malformed lines but note them
            rules.append({
                "_skip": True,
                "_error": f"Line {line_num}: {e}",
            })

    valid_rules = [r for r in rules if not r.get("_skip")]
    skipped_malformed = len(rules) - len(valid_rules)

    result = db.import_rules(valid_rules)
    result["skipped_malformed_lines"] = skipped_malformed
    return result
