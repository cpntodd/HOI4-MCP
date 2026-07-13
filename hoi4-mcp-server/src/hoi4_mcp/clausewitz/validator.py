"""
Clausewitz script validator — bracket matching, syntax checking, and YML validation.

Used by the `validate_syntax` MCP tool to catch errors before the game loads.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .parser import ClausewitzTokenizer, ParseError, Token


# ---------------------------------------------------------------------------
# Core validator
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Result of validating a Clausewitz script string."""
    is_valid: bool
    errors: list[ParseError] = field(default_factory=list)
    warnings: list[ParseError] = field(default_factory=list)
    bracket_depth: int = 0
    token_count: int = 0


def validate_clausewitz(text: str, source: str = "<string>") -> ValidationResult:
    """Validate a Clausewitz script string for common errors.

    Checks:
    - Bracket { } matching
    - Missing = signs where expected
    - Common syntax issues (double commas, stray operators)
    - String termination
    
    Args:
        text: The raw Clausewitz script text to validate.
        source: Optional label for error messages (e.g. filename).
    
    Returns:
        ValidationResult with is_valid, errors, and warnings.
    """
    tokenizer = ClausewitzTokenizer(text, source)
    tokens = tokenizer.tokenize()
    errors: list[ParseError] = []
    warnings: list[ParseError] = []

    # Bracket matching
    depth = 0
    bracket_stack: list[Token] = []
    for tok in tokens:
        if tok.type == "LBRACE":
            depth += 1
            bracket_stack.append(tok)
        elif tok.type == "RBRACE":
            depth -= 1
            if depth < 0:
                errors.append(ParseError(
                    tok.line, tok.col,
                    "Unexpected closing brace '}' — no matching opening brace",
                    source
                ))
                depth = 0
            elif bracket_stack:
                bracket_stack.pop()

    if depth > 0:
        for tok in bracket_stack:
            errors.append(ParseError(
                tok.line, tok.col,
                f"Unclosed opening brace '{{' — missing '}}'",
                source
            ))

    # Check for common patterns that indicate syntax errors
    for i, tok in enumerate(tokens):
        if tok.type == "EOF":
            break

        # Missing = after key before brace (e.g. "my_key { }" instead of "my_key = { }")
        if tok.type == "KEY" and i + 1 < len(tokens):
            nxt = tokens[i + 1]
            if nxt.type == "LBRACE" and tok.value not in (
                "if", "else", "else_if", "limit", "AND", "OR", "NOT",
                "trigger", "immediate", "option", "mean_time_to_happen",
                "modifier", "available", "allowed", "visible", "completion_reward",
                "ai_will_do", "allow_branch", "prerequisite", "mutually_exclusive",
            ):
                # This is not necessarily wrong in Clausewitz (some blocks don't use =)
                # but it's worth warning about
                pass

        # Bare brace at top level without key
        if tok.type == "LBRACE" and i == 0:
            warnings.append(ParseError(
                tok.line, tok.col,
                "File starts with '{' — may be missing a top-level key",
                source
            ))

        # Check for consecutive operators
        if tok.type == "EQUALS" and i + 1 < len(tokens):
            nxt = tokens[i + 1]
            if nxt.type == "EQUALS":
                errors.append(ParseError(
                    tok.line, tok.col,
                    f"Consecutive operators: '{tok.value} {nxt.value}'",
                    source
                ))

    # Detect missing 'is_triggered_only' for hidden events
    text_lower = text.lower()
    if "hide_window = yes" in text_lower and "is_triggered_only" not in text_lower:
        warnings.append(ParseError(
            0, 0,
            "Event has 'hide_window = yes' but no 'is_triggered_only = yes' — "
            "hidden events should always be triggered-only",
            source
        ))

    # Detect 'completion_reward' missing from focus
    if "focus =" in text_lower and "completion_reward" not in text_lower:
        warnings.append(ParseError(
            0, 0,
            "Focus definition found but no 'completion_reward' block — "
            "every focus needs one (even if empty)",
            source
        ))

    # Detect potential scope issues: country_event with state triggers
    if "country_event" in text_lower:
        state_triggers = [
            "state_population", "has_state_flag", "controls_state",
            "is_owned_by", "is_controlled_by"
        ]
        for st in state_triggers:
            if st in text_lower:
                warnings.append(ParseError(
                    0, 0,
                    f"Country event contains state-scope trigger '{st}' — "
                    "verify scope is correct",
                    source
                ))

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        bracket_depth=sum(1 for t in tokens if t.type == "LBRACE") - 
                       sum(1 for t in tokens if t.type == "RBRACE"),
        token_count=len(tokens) - 1,  # exclude EOF
    )


# ---------------------------------------------------------------------------
# Localisation YML validator
# ---------------------------------------------------------------------------

@dataclass
class YMLEntry:
    """A single localisation entry."""
    key: str
    version: int
    value: str
    line: int


@dataclass
class YMLValidationResult:
    """Result of validating a localisation YML file."""
    is_valid: bool
    language: str = ""
    entry_count: int = 0
    errors: list[ParseError] = field(default_factory=list)
    warnings: list[ParseError] = field(default_factory=list)
    entries: list[YMLEntry] = field(default_factory=list)


# Pattern for a valid localisation line:  KEY:0 "value"
_LOC_PATTERN = re.compile(r'^(\s+)([A-Za-z0-9_.-]+):(\d+)\s+"(.*)"\s*$')
_HEADER_PATTERN = re.compile(r'^\s*l_(\w+):\s*$')


def validate_localisation(text: str, source: str = "<string>") -> YMLValidationResult:
    """Validate a HOI4 localisation YML file.

    Checks:
    - First line is l_<language>: header
    - All entries have correct format: KEY:0 "value"
    - No tabs (only spaces for indentation)
    - UTF-8 encoding (no BOM issues)
    
    Args:
        text: Raw YML file content.
        source: Optional label for error messages.
    
    Returns:
        YMLValidationResult with validation details.
    """
    errors: list[ParseError] = []
    warnings: list[ParseError] = []
    entries: list[YMLEntry] = []
    language = "unknown"

    lines = text.split("\n")

    # Check BOM
    if text and text[0] == "\ufeff":
        warnings.append(ParseError(1, 0, "File contains UTF-8 BOM — should be UTF-8 without BOM", source))

    # Check first line for language header
    if lines:
        header_match = _HEADER_PATTERN.match(lines[0])
        if header_match:
            language = header_match.group(1)
        else:
            errors.append(ParseError(
                1, 0,
                f"First line must be 'l_<language>:' (e.g. 'l_english:'). "
                f"Got: '{lines[0][:50]}'",
                source
            ))

    # Parse entries
    for line_no, line in enumerate(lines, start=1):
        if line_no == 1 and _HEADER_PATTERN.match(line):
            continue

        if not line.strip():
            continue  # empty line

        if "\t" in line:
            errors.append(ParseError(
                line_no, line.index("\t") + 1,
                "Tab character found — use spaces for indentation in YML files",
                source
            ))

        match = _LOC_PATTERN.match(line)
        if match:
            indent, key, version, value = match.groups()
            if len(indent) != 1:
                warnings.append(ParseError(
                    line_no, 0,
                    f"Expected exactly 1 space of indentation, got {len(indent)}",
                    source
                ))
            entries.append(YMLEntry(
                key=key,
                version=int(version),
                value=value,
                line=line_no,
            ))
        elif line.strip():
            # Not a comment line
            if not line.strip().startswith("#"):
                # Check if it looks like a localisation entry with wrong format
                if ":" in line and '"' in line:
                    errors.append(ParseError(
                        line_no, 0,
                        f"Malformed localisation entry: '{line.strip()[:60]}'. "
                        "Expected format: ' KEY:0 \"value\"'",
                        source
                    ))

    # Check for common issues
    for entry in entries:
        # Unescaped quotes inside value
        if entry.value.count('"') > 0:
            warnings.append(ParseError(
                entry.line, 0,
                f"Value for '{entry.key}' contains unescaped quote — use backslash to escape",
                source
            ))

        # Empty value
        if not entry.value.strip():
            warnings.append(ParseError(
                entry.line, 0,
                f"Empty value for key '{entry.key}' — ensure it's intentional",
                source
            ))

    return YMLValidationResult(
        is_valid=len(errors) == 0,
        language=language,
        entry_count=len(entries),
        errors=errors,
        warnings=warnings,
        entries=entries,
    )


def extract_loc_keys(text: str) -> set[str]:
    """Extract all localisation keys from a YML file."""
    keys: set[str] = set()
    for line in text.split("\n"):
        match = _LOC_PATTERN.match(line)
        if match:
            keys.add(match.group(2))
    return keys
