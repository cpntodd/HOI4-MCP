"""
learning/ — Adaptive Learning & Mistake Memory System for HOI4-MCP.

Provides:
- LearnedRulesDB: SQLite-backed rule storage
- Rule validation and formatting
- .jsonl export/import for repo sharing
- Seed data from existing agent constraints
- Recurring error pattern detection
"""

from .db import LearnedRulesDB
from .detector import detect_recurring_patterns
from .exporter import export_to_file, import_from_file
from .rules import (
    format_rule_for_agent,
    format_rules_block,
    rules_to_jsonl,
    rules_to_markdown,
    validate_rule_fields,
)
from .seeder import seed_if_empty

__all__ = [
    "LearnedRulesDB",
    "detect_recurring_patterns",
    "export_to_file",
    "import_from_file",
    "format_rule_for_agent",
    "format_rules_block",
    "rules_to_jsonl",
    "rules_to_markdown",
    "validate_rule_fields",
    "seed_if_empty",
]
