"""Error log parser — reads and parses the Hearts of Iron IV error.log file.

Provides structured JSON output of errors, classified by type, instead of 
forcing the AI to parse raw text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Error classification patterns
# ---------------------------------------------------------------------------

ERROR_PATTERNS = {
    "unexpected_token": re.compile(
        r'Unexpected token',
        re.IGNORECASE
    ),
    "duplicate_id": re.compile(
        r'Duplicate (?:ID|key)',
        re.IGNORECASE
    ),
    "invalid_scope": re.compile(
        r'Invalid scope',
        re.IGNORECASE
    ),
    "missing_loc": re.compile(
        r'Missing localisation key',
        re.IGNORECASE
    ),
    "missing_texture": re.compile(
        r'Could not (?:find|load) texture',
        re.IGNORECASE
    ),
    "invalid_province": re.compile(
        r'Invalid province',
        re.IGNORECASE
    ),
    "bad_trigger": re.compile(
        r'(?:Trigger|Effect) not valid',
        re.IGNORECASE
    ),
    "parse_error": re.compile(
        r'(?:parse|syntax) error',
        re.IGNORECASE
    ),
    "missing_file": re.compile(
        r'(?:cannot|Could not) (?:open|find|read) file',
        re.IGNORECASE
    ),
    "database_error": re.compile(
        r'(?:database|DB) (?:error|inconsistency)',
        re.IGNORECASE
    ),
}


@dataclass
class ParsedError:
    """A single parsed error from error.log."""
    category: str
    message: str
    file: str = ""
    line: int = 0
    raw: str = ""


@dataclass
class ErrorLog:
    """Parsed representation of the error.log file."""
    path: str = ""
    total_errors: int = 0
    errors: list[ParsedError] = field(default_factory=list)
    by_category: dict[str, list[ParsedError]] = field(default_factory=dict)
    by_file: dict[str, list[ParsedError]] = field(default_factory=dict)
    raw_lines: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def find_error_log() -> Path | None:
    """Locate the HOI4 error.log file based on OS."""
    import platform

    system = platform.system()
    home = Path.home()

    if system == "Linux":
        candidates = [
            home / ".local" / "share" / "Paradox Interactive" / "Hearts of Iron IV" / "logs" / "error.log",
            home / ".paradox" / "Hearts of Iron IV" / "logs" / "error.log",
        ]
    elif system == "Darwin":  # macOS
        candidates = [
            home / "Documents" / "Paradox Interactive" / "Hearts of Iron IV" / "logs" / "error.log",
        ]
    elif system == "Windows":
        candidates = [
            home / "Documents" / "Paradox Interactive" / "Hearts of Iron IV" / "logs" / "error.log",
        ]
    else:
        candidates = []

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def parse_error_log(filepath: str | Path | None = None, tail_lines: int = 200) -> ErrorLog:
    """Parse the HOI4 error.log file into structured data.

    Args:
        filepath: Path to error.log. If None, auto-detect based on OS.
        tail_lines: Number of lines to read from the end of the file.
    
    Returns:
        ErrorLog with structured error data.
    """
    if filepath is None:
        found = find_error_log()
        if found is None:
            return ErrorLog(
                path="(not found)",
                errors=[],
            )
        filepath = found

    path = Path(filepath)
    if not path.exists():
        return ErrorLog(
            path=str(filepath),
            errors=[],
        )

    # Read last N lines
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ErrorLog(path=str(path), errors=[])

    all_lines = text.strip().split("\n")
    lines = all_lines[-tail_lines:] if len(all_lines) > tail_lines else all_lines

    errors: list[ParsedError] = []
    by_category: dict[str, list[ParsedError]] = {}
    by_file: dict[str, list[ParsedError]] = {}

    # Also try to extract line numbers from file references like:
    # [16:42:30][gameobject.cpp:1234]: ...  OR
    # [pdx_assert.cpp:620]: ...
    file_line_pattern = re.compile(r'\[(?P<file>[^\]]+\.txt)\]:?(?P<line>\d+)?\]?')

    for raw_line in lines:
        if not raw_line.strip():
            continue
        
        # Only classify lines that look like errors (contain error-like patterns)
        is_error_line = (
            "error" in raw_line.lower() or
            "unexpected" in raw_line.lower() or
            "duplicate" in raw_line.lower() or
            "missing" in raw_line.lower() or
            "invalid" in raw_line.lower() or
            "could not" in raw_line.lower() or
            "cannot" in raw_line.lower() or
            "warning" in raw_line.lower()
        )
        if not is_error_line:
            continue

        parsed = ParsedError(
            category="unknown",
            message=raw_line.strip(),
            raw=raw_line.strip(),
        )

        # Try to classify
        for category, pattern in ERROR_PATTERNS.items():
            match = pattern.search(raw_line)
            if match:
                parsed.category = category
                parsed.file = match.groupdict().get("file", "")
                parsed.message = raw_line.strip()
                break

        # Extract file/line if not already set
        if not parsed.file:
            fl_match = file_line_pattern.search(raw_line)
            if fl_match:
                parsed.file = fl_match.group("file")
                line_str = fl_match.group("line")
                if line_str:
                    try:
                        parsed.line = int(line_str)
                    except ValueError:
                        pass

        errors.append(parsed)

        # Categorize
        if parsed.category not in by_category:
            by_category[parsed.category] = []
        by_category[parsed.category].append(parsed)

        # By file
        fname = parsed.file or "(unknown)"
        if fname not in by_file:
            by_file[fname] = []
        by_file[fname].append(parsed)

    return ErrorLog(
        path=str(path),
        total_errors=len(errors),
        errors=errors,
        by_category=by_category,
        by_file=by_file,
        raw_lines=lines,
    )


def error_log_summary(filepath: str | Path | None = None) -> dict[str, Any]:
    """Return a JSON-serializable summary of the error log.

    This is the primary output for the `get_latest_errors` MCP tool.
    """
    log = parse_error_log(filepath)

    return {
        "path": log.path,
        "total_errors": log.total_errors,
        "errors_by_category": {
            cat: len(errs) for cat, errs in log.by_category.items()
        },
        "errors_by_file": {
            fname: len(errs) for fname, errs in log.by_file.items()
        },
        "recent_errors": [
            {
                "category": e.category,
                "message": e.message[:200],  # truncate long messages
                "file": e.file,
                "line": e.line,
            }
            for e in log.errors[-20:]  # Last 20 errors
        ],
        "categories": {
            "unexpected_token": "Bracket/syntax error — likely unclosed brace before this line",
            "duplicate_id": "Two definitions share the same ID; second overwrites first silently",
            "invalid_scope": "Using a country-scope effect in a state scope (or vice versa)",
            "missing_loc": "A string key has no matching YML entry",
            "missing_texture": "GFX path is wrong or DDS file is missing",
            "invalid_province": "Province in map file doesn't exist in definition.csv",
            "bad_trigger": "Using a trigger where an effect is expected (or vice versa)",
            "unknown": "Unclassified error — review raw message",
        },
    }
