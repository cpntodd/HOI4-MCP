"""
Clausewitz script parser for Hearts of Iron IV mod files.

Handles the Paradox "Clausewitz engine" script format used in .txt files:
- key = value pairs
- Nested blocks with { }
- Comments with #
- Bare word values, quoted strings, numbers

This parser converts Clausewitz script into a Python dict/list structure
and provides utilities for extracting specific patterns (namespaces, IDs, etc.).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

@dataclass
class Token:
    type: str  # 'KEY', 'EQUALS', 'STRING', 'NUMBER', 'LBRACE', 'RBRACE', 'COMMENT', 'EOF'
    value: str
    line: int
    col: int


class ClausewitzTokenizer:
    """Tokenize Clausewitz script into a stream of tokens."""

    def __init__(self, text: str, source_name: str = "<string>"):
        self.text = text
        self.source = source_name
        self.pos = 0
        self.line = 1
        self.col = 1

    def _peek(self, n: int = 0) -> str:
        idx = self.pos + n
        return self.text[idx] if idx < len(self.text) else ""

    def _advance(self, n: int = 1) -> None:
        for _ in range(n):
            if self.pos >= len(self.text):
                break
            if self.text[self.pos] == "\n":
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            self.pos += 1

    def _skip_whitespace_and_comments(self) -> None:
        while self.pos < len(self.text):
            c = self._peek()
            if c in " \t\r\n":
                self._advance()
            elif c == "#":
                # Comment — skip to end of line
                while self.pos < len(self.text) and self._peek() != "\n":
                    self._advance()
            else:
                break

    def _read_string(self) -> Token:
        """Read a quoted string value."""
        start_line, start_col = self.line, self.col
        self._advance()  # skip opening quote
        chars = []
        while self.pos < len(self.text):
            c = self._peek()
            if c == '"':
                self._advance()
                return Token("STRING", "".join(chars), start_line, start_col)
            elif c == "\\" and self._peek(1) in ('"', "\\", "n"):
                chars.append("\n" if self._peek(1) == "n" else self._peek(1))
                self._advance(2)
            elif c == "\n":
                # Unterminated string — treat newline as end
                return Token("STRING", "".join(chars), start_line, start_col)
            else:
                chars.append(c)
                self._advance()
        return Token("STRING", "".join(chars), start_line, start_col)

    def _read_bare_word(self) -> Token:
        """Read an unquoted value or key."""
        start_line, start_col = self.line, self.col
        chars = []
        while self.pos < len(self.text):
            c = self._peek()
            if c in " \t\r\n{}#=":
                break
            chars.append(c)
            self._advance()
        word = "".join(chars)
        if not word:
            return Token("KEY", "", start_line, start_col)
        # Try to parse as number — only classify as NUMBER if conversion succeeds
        try:
            int(word)
            return Token("NUMBER", word, start_line, start_col)
        except ValueError:
            pass
        try:
            float(word)
            return Token("NUMBER", word, start_line, start_col)
        except ValueError:
            pass
        return Token("KEY", word, start_line, start_col)

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while self.pos < len(self.text):
            self._skip_whitespace_and_comments()
            if self.pos >= len(self.text):
                break

            c = self._peek()
            start_line, start_col = self.line, self.col

            if c == "{":
                tokens.append(Token("LBRACE", "{", start_line, start_col))
                self._advance()
            elif c == "}":
                tokens.append(Token("RBRACE", "}", start_line, start_col))
                self._advance()
            elif c == "=":
                # Could be '=' or '==' (comparison)
                if self._peek(1) == "=":
                    tokens.append(Token("EQUALS", "==", start_line, start_col))
                    self._advance(2)
                else:
                    tokens.append(Token("EQUALS", "=", start_line, start_col))
                    self._advance()
            elif c == '"':
                tokens.append(self._read_string())
            elif c in "<>!" and self._peek(1) == "=":
                # Comparison operators: <=  >=  !=
                tokens.append(Token("EQUALS", c + "=", start_line, start_col))
                self._advance(2)
            elif c in "<>":
                tokens.append(Token("EQUALS", c, start_line, start_col))
                self._advance()
            else:
                tokens.append(self._read_bare_word())

        tokens.append(Token("EOF", "", self.line, self.col))
        return tokens


# ---------------------------------------------------------------------------
# Parser — converts token stream to Python dict/list
# ---------------------------------------------------------------------------

class ClausewitzParser:
    """Parse Clausewitz token stream into nested Python dicts."""

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.idx = 0

    def _peek(self) -> Token:
        return self.tokens[self.idx] if self.idx < len(self.tokens) else self.tokens[-1]

    def _advance(self) -> Token:
        tok = self._peek()
        self.idx += 1
        return tok

    def _expect(self, typ: str) -> Token:
        tok = self._advance()
        if tok.type != typ:
            raise SyntaxError(
                f"Expected {typ}, got {tok.type} ('{tok.value}') "
                f"at line {tok.line}, col {tok.col}"
            )
        return tok

    def _parse_value(self) -> Any:
        """Parse a single value: string, number, or block."""
        tok = self._peek()
        if tok.type == "STRING":
            self._advance()
            return tok.value
        elif tok.type == "NUMBER":
            self._advance()
            # Return as int if no decimal point
            if "." in tok.value:
                return float(tok.value)
            return int(tok.value)
        elif tok.type == "LBRACE":
            return self._parse_block()
        elif tok.type == "KEY":
            self._advance()
            return tok.value
        else:
            # Unexpected — return as string as fallback
            self._advance()
            return tok.value

    def _parse_block(self) -> dict[str, Any]:
        """Parse a { ... } block into a dict. Keys may repeat — later ones 
        become a list if the same key appears multiple times."""
        self._expect("LBRACE")
        result: dict[str, Any] = {}

        while self._peek().type not in ("RBRACE", "EOF"):
            # Read key (or bare value in a list context)
            key_tok = self._peek()
            if key_tok.type in ("KEY", "STRING", "NUMBER"):
                key = self._advance().value
            else:
                # Unexpected token — skip
                self._advance()
                continue

            # Check for = sign
            if self._peek().type == "EQUALS":
                self._advance()
                value = self._parse_value()
            elif self._peek().type in ("KEY", "STRING", "NUMBER", "LBRACE"):
                # Implicit list — key followed by another value with no =
                # This handles patterns like: prerequisite = { focus = A focus = B }
                # which is actually key=value pairs, but also:
                # add_ideas = { idea_1 idea_2 idea_3 }
                value = self._parse_value()
                # Actually the above pattern with `key value` without = means
                # this is a list. We'll handle it differently.
                # Re-parse: the key is actually a list element
                result[key] = value
                continue
            else:
                value = None

            # Store: if key already exists, convert to list
            if key in result:
                existing = result[key]
                if isinstance(existing, list):
                    existing.append(value)
                else:
                    result[key] = [existing, value]
            else:
                result[key] = value

        self._expect("RBRACE")
        return result

    def parse(self) -> dict[str, Any]:
        """Parse the entire token stream into a dict."""
        result: dict[str, Any] = {}
        while self._peek().type != "EOF":
            tok = self._peek()
            if tok.type == "KEY":
                key = self._advance().value
                if self._peek().type == "EQUALS":
                    self._advance()
                    value = self._parse_value()
                else:
                    value = self._parse_value()
                if key in result:
                    existing = result[key]
                    if isinstance(existing, list):
                        existing.append(value)
                    else:
                        result[key] = [existing, value]
                else:
                    result[key] = value
            elif tok.type in ("STRING", "NUMBER", "LBRACE"):
                # Top-level value without key? Rare but handle.
                value = self._parse_value()
                result[str(len(result))] = value
            else:
                self._advance()
        return result


# ---------------------------------------------------------------------------
# High-level file parser
# ---------------------------------------------------------------------------

@dataclass
class ParseError:
    """Represents a parse error with location information."""
    line: int
    col: int
    message: str
    file: str = ""


@dataclass
class ParsedFile:
    """Result of parsing a Clausewitz file."""
    path: Path
    data: dict[str, Any]
    errors: list[ParseError] = field(default_factory=list)
    namespaces: list[str] = field(default_factory=list)
    tokens: list[Token] = field(default_factory=list)


def parse_file(filepath: Path) -> ParsedFile:
    """Parse a single Clausewitz .txt file and return structured data."""
    try:
        text = filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            text = filepath.read_text(encoding="latin-1")
        except Exception:
            return ParsedFile(path=filepath, data={}, errors=[
                ParseError(0, 0, f"Could not read file: {filepath}", str(filepath))
            ])

    tokenizer = ClausewitzTokenizer(text, str(filepath))
    tokens = tokenizer.tokenize()

    errors: list[ParseError] = []

    # Bracket validation
    depth = 0
    for tok in tokens:
        if tok.type == "LBRACE":
            depth += 1
        elif tok.type == "RBRACE":
            depth -= 1
        if depth < 0:
            errors.append(ParseError(
                tok.line, tok.col,
                "Unexpected closing brace '}' — no matching opening brace",
                str(filepath)
            ))
            depth = 0

    if depth > 0:
        errors.append(ParseError(
            0, 0,
            f"Unclosed brace: {depth} opening brace(s) without matching close",
            str(filepath)
        ))

    # Parse
    parser = ClausewitzParser(tokens)
    try:
        data = parser.parse()
    except SyntaxError as e:
        errors.append(ParseError(0, 0, str(e), str(filepath)))
        data = {}

    # Extract namespaces
    namespaces: list[str] = []
    if "add_namespace" in data:
        ns = data["add_namespace"]
        if isinstance(ns, list):
            namespaces.extend(str(n) for n in ns)
        else:
            namespaces.append(str(ns))

    return ParsedFile(
        path=filepath,
        data=data,
        errors=errors,
        namespaces=namespaces,
        tokens=tokens,
    )


# ---------------------------------------------------------------------------
# Utility: extract IDs from parsed data
# ---------------------------------------------------------------------------

def extract_ids(data: dict[str, Any], prefix: str = "") -> dict[str, list[str]]:
    """Walk a parsed dict and extract known ID-bearing keys.
    
    Returns a dict mapping category -> list of IDs found.
    Categories: 'events', 'focuses', 'decisions', 'ideas', 'characters',
                'namespaces', 'technologies', 'scripted_effects', 'scripted_triggers'
    """
    found: dict[str, list[str]] = {
        "events": [],
        "focuses": [],
        "decisions": [],
        "ideas": [],
        "characters": [],
        "namespaces": [],
        "technologies": [],
        "scripted_effects": [],
        "scripted_triggers": [],
    }

    def _walk(obj: Any, parent_key: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                full_key = f"{parent_key}.{k}" if parent_key else k

                # Namespace detection
                if k == "add_namespace":
                    val = str(v) if not isinstance(v, list) else [str(x) for x in v]
                    found["namespaces"].extend(val if isinstance(val, list) else [val])

                # Event IDs
                if k == "id" and ("event" in parent_key.lower() or parent_key == ""):
                    found["events"].append(str(v))

                # Focus IDs
                if k == "id" and "focus" in parent_key.lower():
                    found["focuses"].append(str(v))

                # Focus tree
                if k == "focus_tree":
                    if isinstance(v, dict):
                        for fk in v:
                            if fk == "focus" and isinstance(v[fk], dict):
                                fid = v[fk].get("id", "")
                                if fid:
                                    found["focuses"].append(str(fid))

                # Decision IDs (key is the decision name)
                if k == "allowed" and isinstance(v, dict):
                    # Parent key might be a decision/mission name
                    pass

                # Idea keys
                if k == "picture" and isinstance(v, str) and v.startswith("GFX_"):
                    # Parent might be an idea
                    pass

                # Character IDs
                if k == "characters" and isinstance(v, dict):
                    for char_id in v:
                        found["characters"].append(str(char_id))

                # Technology keys
                if k == "technologies" and isinstance(v, dict):
                    for tech_id in v:
                        found["technologies"].append(str(tech_id))

                # Scripted effects/triggers
                if parent_key == "" and k not in ("add_namespace",):
                    # Top-level keys in scripted_effects/triggers files
                    pass

                _walk(v, full_key)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item, parent_key)

    _walk(data)
    return found


def find_id_in_data(data: dict[str, Any], target_id: str) -> list[str]:
    """Search for a specific ID in parsed data. Returns paths where found."""
    results: list[str] = []

    def _search(obj: Any, path: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_path = f"{path}.{k}" if path else k
                if k == "id" and str(v) == target_id:
                    results.append(new_path)
                _search(v, new_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _search(item, f"{path}[{i}]")

    _search(data)
    return results
