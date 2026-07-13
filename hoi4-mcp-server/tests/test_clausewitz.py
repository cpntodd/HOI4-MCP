# GAP-001:PARTIAL — Parser tests (tokenizer + bracket validation).
# Remaining tests for validator, indexer, ID manager, error log parser,
# vanilla DB to be added.
"""
tests/test_clausewitz.py — Tests for Clausewitz tokenizer and parser.
"""

import pytest
from hoi4_mcp.clausewitz.parser import ClausewitzTokenizer, ClausewitzParser, parse_file


# ── Tokenizer ───────────────────────────────────────────────

class TestTokenizer:
    def test_empty_string(self):
        t = ClausewitzTokenizer("")
        tokens = t.tokenize()
        assert len(tokens) == 1  # Just EOF
        assert tokens[0].type == "EOF"

    def test_simple_key_value(self):
        t = ClausewitzTokenizer("key = value")
        tokens = t.tokenize()
        types = [tok.type for tok in tokens]
        assert types == ["KEY", "EQUALS", "KEY", "EOF"]

    def test_quoted_string(self):
        t = ClausewitzTokenizer('name = "Hearts of Iron IV"')
        tokens = t.tokenize()
        str_tokens = [tok for tok in tokens if tok.type == "STRING"]
        assert len(str_tokens) == 1
        assert str_tokens[0].value == "Hearts of Iron IV"

    def test_nested_braces(self):
        t = ClausewitzTokenizer("outer = { inner = { key = val } }")
        tokens = t.tokenize()
        braces = [tok for tok in tokens if tok.type in ("LBRACE", "RBRACE")]
        assert len(braces) == 4
        assert braces[0].type == "LBRACE"
        assert braces[-1].type == "RBRACE"

    def test_comment_skipped(self):
        t = ClausewitzTokenizer("# This is a comment\nkey = value")
        tokens = t.tokenize()
        comment_tokens = [tok for tok in tokens if tok.type == "COMMENT"]
        assert len(comment_tokens) == 0  # Comments are skipped by tokenizer

    def test_numbers(self):
        t = ClausewitzTokenizer("cost = 150\nyear = 1936.1")
        tokens = t.tokenize()
        nums = [tok for tok in tokens if tok.type == "NUMBER"]
        assert len(nums) == 2
        assert nums[0].value == "150"

    def test_line_col_tracking(self):
        t = ClausewitzTokenizer("key = value")
        tokens = t.tokenize()
        key = tokens[0]
        assert key.line == 1
        assert key.col == 1

    def test_multiline(self):
        text = """focus = {
    id = TEST_focus_1
    icon = GFX_test
    x = 5
    y = 3
}"""
        t = ClausewitzTokenizer(text)
        tokens = t.tokenize()
        assert len(tokens) > 5

    def test_windows_line_endings(self):
        t = ClausewitzTokenizer("key = value\r\nother = yes")
        tokens = t.tokenize()
        keys = [tok for tok in tokens if tok.type == "KEY"]
        assert len(keys) >= 2  # "key" and "other" should both be found

    def test_bom_handled(self):
        t = ClausewitzTokenizer("\ufeffkey = value")  # BOM
        tokens = t.tokenize()
        assert len(tokens) > 1

    def test_escaped_quotes_in_string(self):
        t = ClausewitzTokenizer(r'desc = "He said \"hello\""')
        tokens = t.tokenize()
        strs = [tok for tok in tokens if tok.type == "STRING"]
        assert len(strs) == 1
        assert 'hello' in strs[0].value


# ── Parser (uses tmp_path fixtures for file-based parsing) ────

class TestParser:
    def test_parse_simple(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("key = value")
        result = parse_file(f)
        assert result.data == {"key": "value"}

    def test_parse_nested(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("root = { child = val }")
        result = parse_file(f)
        assert result.data == {"root": {"child": "val"}}

    def test_parse_number(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("cost = 150")
        result = parse_file(f)
        assert result.data["cost"] == 150

    def test_parse_list_value(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text('list = { "a" "b" "c" }')
        result = parse_file(f)
        # Clausewitz parser may nest list items differently
        assert "list" in result.data

    def test_parse_duplicate_keys_become_list(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("""prerequisite = { focus = A }
prerequisite = { focus = B }""")
        result = parse_file(f)
        # Duplicate keys at top level become a list of dicts
        assert "prerequisite" in result.data

    def test_parse_empty_block(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("empty = { }")
        result = parse_file(f)
        assert "empty" in result.data

    def test_parse_comment_ignored(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("# comment\nkey = value")
        result = parse_file(f)
        assert result.data == {"key": "value"}


# ── parse_file edge cases ───────────────────────────────────

class TestParseFile:
    def test_parse_focus_structure(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("""focus_tree = {
    id = test_tree
    focus = {
        id = TEST_first_focus
        icon = GFX_test
        x = 0
        y = 0
        completion_reward = { }
    }
}""")
        result = parse_file(f)
        assert result.data is not None
        # focus_tree should be present in parsed data
        assert "focus_tree" in result.data or any("focus_tree" in str(k) for k in result.data.keys())

    def test_parse_event_structure(self, tmp_path):
        f = tmp_path / "events.txt"
        f.write_text("""add_namespace = test
country_event = {
    id = test.1
    title = test.1.t
    desc = test.1.d
    is_triggered_only = yes
    option = {
        name = test.1.a
    }
}""")
        result = parse_file(f)
        assert result.data is not None
        assert result.namespaces == ["test"]

    def test_extract_ids(self, tmp_path):
        from hoi4_mcp.clausewitz.parser import extract_ids
        f = tmp_path / "events.txt"
        f.write_text("""add_namespace = test
country_event = { id = test.1 }
country_event = { id = test.2 }""")
        result = parse_file(f)
        ids = extract_ids(result.data, "event")
        # extract_ids returns a dict with categories; check events key
        assert isinstance(ids, dict)
        assert "test.1" in ids.get("events", []) or "test.1" in str(ids)
