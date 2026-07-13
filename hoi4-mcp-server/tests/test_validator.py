# GAP-001:PARTIAL — Validator tests added. ID manager, error log parser, indexer, vanilla DB tests still needed.
"""
tests/test_validator.py — Tests for Clausewitz script and YML validation.
"""

import pytest
from hoi4_mcp.clausewitz.validator import (
    validate_clausewitz,
    validate_localisation,
    ValidationResult,
    YMLValidationResult,
)


# ── Clausewitz Validator ────────────────────────────────────

class TestClausewitzValidation:
    def test_valid_focus_returns_no_errors(self):
        text = """focus = {
    id = TEST_focus_1
    icon = GFX_test
    completion_reward = { }
}"""
        result = validate_clausewitz(text)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_valid_event_returns_no_errors(self):
        text = """country_event = {
    id = test.1
    is_triggered_only = yes
    option = { name = test.1.a }
}"""
        result = validate_clausewitz(text)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_unclosed_brace_produces_error(self):
        text = "focus = { id = test"
        result = validate_clausewitz(text)
        assert not result.is_valid
        assert any("Unclosed" in e.message for e in result.errors)

    def test_unexpected_closing_brace_produces_error(self):
        text = "} focus = { id = test }"
        result = validate_clausewitz(text)
        assert not result.is_valid
        assert any("Unexpected closing" in e.message for e in result.errors)

    def test_consecutive_equals_produces_error(self):
        # The tokenizer reads == as a single token, so use = followed by bare =
        text = "key = =value"
        result = validate_clausewitz(text)
        assert not result.is_valid
        assert any("Consecutive" in e.message for e in result.errors)

    def test_double_equals_is_valid(self):
        # == is treated as a single operator token — valid in Clausewitz
        text = "key == value"
        result = validate_clausewitz(text)
        assert result.is_valid

    def test_file_starts_with_brace_warns(self):
        text = "{ key = value }"
        result = validate_clausewitz(text)
        assert any("starts with" in w.message for w in result.warnings)

    def test_hide_window_without_is_triggered_only_warns(self):
        text = """country_event = {
    id = test.1
    hide_window = yes
    option = { name = test.1.a }
}"""
        result = validate_clausewitz(text)
        # Should warn about missing is_triggered_only
        assert any("hide_window" in w.message.lower() and "is_triggered_only" in w.message.lower()
                   for w in result.warnings)

    def test_hide_window_with_is_triggered_only_no_warning(self):
        text = """country_event = {
    id = test.1
    is_triggered_only = yes
    hide_window = yes
    option = { name = test.1.a }
}"""
        result = validate_clausewitz(text)
        assert not any("hide_window" in w.message.lower() for w in result.warnings)

    def test_focus_without_completion_reward_warns(self):
        text = """focus = {
    id = TEST_focus
    icon = GFX_test
}"""
        result = validate_clausewitz(text)
        assert any("completion_reward" in w.message.lower() for w in result.warnings)

    def test_focus_with_completion_reward_no_warning(self):
        text = """focus = {
    id = TEST_focus
    icon = GFX_test
    completion_reward = { }
}"""
        result = validate_clausewitz(text)
        assert not any("completion_reward" in w.message.lower() for w in result.warnings)

    def test_country_event_with_state_trigger_warns(self):
        text = """country_event = {
    id = test.1
    trigger = { controls_state = 123 }
    option = { name = test.1.a }
}"""
        result = validate_clausewitz(text)
        assert any("state-scope" in w.message.lower() for w in result.warnings)

    def test_empty_text(self):
        result = validate_clausewitz("")
        assert result.is_valid
        assert result.token_count == 0

    def test_nested_braces_balanced(self):
        text = """root = {
    level1 = {
        level2 = {
            key = value
        }
    }
}"""
        result = validate_clausewitz(text)
        assert result.is_valid

    def test_bracket_depth_tracked(self):
        text = "a { b { c { d } } }"
        result = validate_clausewitz(text)
        assert result.bracket_depth == 0

    def test_token_count(self):
        text = "key = value"
        result = validate_clausewitz(text)
        assert result.token_count == 3  # KEY, EQUALS, KEY


# ── Localisation YML Validator ──────────────────────────────

class TestYMLValidation:
    def test_valid_yml(self):
        text = """l_english:
 key1:0 "Value one"
 key2:0 "Value two"
"""
        result = validate_localisation(text)
        assert result.is_valid
        assert result.language == "english"
        assert result.entry_count > 0

    def test_bom_produces_warning(self):
        text = "\ufeffl_english:\n key1:0 \"Value\"\n"
        result = validate_localisation(text)
        assert any("BOM" in w.message for w in result.warnings)

    def test_missing_language_header(self):
        text = "key1:0 \"Value\"\n"
        result = validate_localisation(text)
        assert not result.is_valid

    def test_empty_text(self):
        result = validate_localisation("")
        assert not result.is_valid

    def test_tab_character_produces_error(self):
        text = "l_english:\n\tkey1:0 \"Value\"\n"
        result = validate_localisation(text)
        # Tab in indentation should be flagged
        assert not result.is_valid or any("tab" in e.message.lower() for e in result.errors)

    def test_comment_lines_skipped(self):
        text = """l_english:
 # This is a comment
 key1:0 "Value"
"""
        result = validate_localisation(text)
        assert result.is_valid

    def test_detects_french_language(self):
        text = "l_french:\n key1:0 \"Valeur\"\n"
        result = validate_localisation(text)
        assert result.language == "french"

    def test_detects_german_language(self):
        text = "l_german:\n key1:0 \"Wert\"\n"
        result = validate_localisation(text)
        assert result.language == "german"
