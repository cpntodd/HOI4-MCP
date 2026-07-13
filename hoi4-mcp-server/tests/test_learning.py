"""
tests/test_learning.py — Tests for the adaptive learning system (GAP-000).
"""

import json
from pathlib import Path

import pytest

from hoi4_mcp.learning import (
    LearnedRulesDB,
    detect_recurring_patterns,
    export_to_file,
    import_from_file,
    format_rules_block,
    rules_to_jsonl,
    rules_to_markdown,
    validate_rule_fields,
    seed_if_empty,
)


@pytest.fixture
def db(tmp_path):
    """Fresh on-disk DB for each test."""
    db_path = tmp_path / "test_learned.db"
    db = LearnedRulesDB(db_path)
    db.ensure_schema()
    return db


# ── Validation ───────────────────────────────────────────────

class TestValidateRuleFields:
    def test_valid_rule(self):
        errors = validate_rule_fields(
            category="syntax", severity="error", source="human_correction",
            pattern="bad pattern", correction="good pattern", context="test context",
        )
        assert errors == []

    def test_invalid_category(self):
        errors = validate_rule_fields(
            category="bogus", severity="error", source="human_correction",
            pattern="p", correction="c", context="ctx",
        )
        assert any("Invalid category" in e for e in errors)

    def test_invalid_severity(self):
        errors = validate_rule_fields(
            category="syntax", severity="critical", source="human_correction",
            pattern="p", correction="c", context="ctx",
        )
        assert any("Invalid severity" in e for e in errors)

    def test_invalid_source(self):
        errors = validate_rule_fields(
            category="syntax", severity="error", source="made_up_source",
            pattern="p", correction="c", context="ctx",
        )
        assert any("Invalid source" in e for e in errors)

    def test_empty_pattern(self):
        errors = validate_rule_fields(
            category="syntax", severity="error", source="human_correction",
            pattern="", correction="c", context="ctx",
        )
        assert any("pattern must not be empty" in e for e in errors)

    def test_empty_correction(self):
        errors = validate_rule_fields(
            category="syntax", severity="error", source="human_correction",
            pattern="p", correction="", context="ctx",
        )
        assert any("correction must not be empty" in e for e in errors)

    def test_empty_context(self):
        errors = validate_rule_fields(
            category="syntax", severity="error", source="human_correction",
            pattern="p", correction="c", context="",
        )
        assert any("context must not be empty" in e for e in errors)

    def test_multiple_errors(self):
        errors = validate_rule_fields(
            category="x", severity="y", source="z",
            pattern="", correction="", context="",
        )
        assert len(errors) >= 4


# ── CRUD ─────────────────────────────────────────────────────

class TestRecordAndGet:
    def test_record_returns_rule_with_id(self, db):
        rule = db.record(
            category="syntax", context="Test context", context_tags="test",
            pattern="bad thing", correction="good thing",
            severity="error", source="human_correction",
        )
        assert rule["id"] == "LR-0001"
        assert rule["pattern"] == "bad thing"
        assert rule["occurrence_count"] == 1
        assert rule["resolved"] == 0

    def test_get_by_id(self, db):
        db.record(
            category="syntax", context="C", context_tags="t",
            pattern="p", correction="c", source="seed",
        )
        rule = db.get_by_id("LR-0001")
        assert rule is not None
        assert rule["context"] == "C"

    def test_get_by_id_missing(self, db):
        assert db.get_by_id("LR-9999") is None

    def test_sequential_ids(self, db):
        db.record(category="syntax", context="A", context_tags="a", pattern="p1", correction="c1", source="seed")
        db.record(category="logic", context="B", context_tags="b", pattern="p2", correction="c2", source="seed")
        assert db.get_by_id("LR-0001")["context"] == "A"
        assert db.get_by_id("LR-0002")["context"] == "B"


# ── Query ────────────────────────────────────────────────────

class TestQuery:
    def _seed(self, db):
        db.record(category="syntax", context="Event error", context_tags="events,syntax", pattern="p1", correction="c1", severity="error", source="seed")
        db.record(category="design", context="Focus design", context_tags="focus_trees,design", pattern="p2", correction="c2", severity="warning", source="seed")
        db.record(category="logic", context="Event logic", context_tags="events,logic", pattern="p3", correction="c3", severity="error", source="seed")

    def test_query_by_tag(self, db):
        self._seed(db)
        rules = db.query(context_tags="events")
        assert len(rules) == 2
        assert all("events" in r["context_tags"] for r in rules)

    def test_query_by_category(self, db):
        self._seed(db)
        rules = db.query(category="syntax")
        assert len(rules) == 1
        assert rules[0]["id"] == "LR-0001"

    def test_query_by_severity(self, db):
        self._seed(db)
        rules = db.query(severity="warning")
        assert len(rules) == 1
        assert rules[0]["id"] == "LR-0002"

    def test_query_excludes_resolved(self, db):
        self._seed(db)
        db.resolve("LR-0001", note="test")
        rules = db.query(context_tags="events")
        assert len(rules) == 1
        assert rules[0]["id"] == "LR-0003"

    def test_query_include_resolved(self, db):
        self._seed(db)
        db.resolve("LR-0001", note="test")
        rules = db.query(context_tags="events", include_resolved=True)
        assert len(rules) == 2

    def test_query_empty(self, db):
        rules = db.query(context_tags="nonexistent")
        assert rules == []

    def test_query_combined_filters(self, db):
        self._seed(db)
        rules = db.query(context_tags="events", severity="error")
        assert len(rules) == 2  # LR-0001 (syntax,error) and LR-0003 (logic,error)
        assert all(r["severity"] == "error" for r in rules)

    def test_query_multiple_tags(self, db):
        self._seed(db)
        rules = db.query(context_tags="syntax,focus_trees")
        assert len(rules) == 2  # LR-0001 (events,syntax) and LR-0002 (focus_trees,design)


# ── Resolve ──────────────────────────────────────────────────

class TestResolve:
    def test_resolve_marks_inactive(self, db):
        db.record(category="syntax", context="C", context_tags="t", pattern="p", correction="c", source="seed")
        rule = db.resolve("LR-0001", note="fixed in patch")
        assert rule["resolved"] == 1
        assert rule["resolved_note"] == "fixed in patch"
        assert rule["resolved_at"] is not None

    def test_resolve_nonexistent(self, db):
        assert db.resolve("LR-9999") is None

    def test_superseded_by(self, db):
        db.record(category="syntax", context="Old", context_tags="t", pattern="p1", correction="c1", source="seed")
        db.record(category="syntax", context="New", context_tags="t", pattern="p2", correction="c2", source="seed")
        db.resolve("LR-0001", superseded_by="LR-0002")
        assert db.get_by_id("LR-0001")["superseded_by"] == "LR-0002"


# ── Deduplication ───────────────────────────────────────────

class TestDedup:
    def test_similar_pattern_increments(self, db):
        db.record(
            category="syntax", context="C", context_tags="events,focus_trees,completion_reward",
            pattern="placing modifier directly inside completion_reward of focus", correction="use add_ideas_effect",
            source="human_correction",
        )
        # Very similar pattern — only differs by "placing" vs "putting" (1 token),
        # "{placing, modifier, directly, inside, completion_reward, of, focus}" vs "{putting, modifier, inside, completion_reward, focus}"
        # Intersection: {modifier, inside, completion_reward, focus} = 4, Union: {placing, modifier, directly, inside, completion_reward, of, focus, putting} = 8
        # Pattern Jaccard: 4/8 = 0.5, Tag Jaccard: 1.0 (exact same), Combined: 0.6*0.5 + 0.4*1.0 = 0.7
        rule = db.record(
            category="syntax", context="C", context_tags="events,focus_trees,completion_reward",
            pattern="putting modifier inside completion_reward focus", correction="use add_ideas_effect instead",
            source="agent_self_correction",
        )
        assert rule["id"] == "LR-0001"
        assert rule["occurrence_count"] == 2

    def test_different_pattern_creates_new(self, db):
        db.record(
            category="syntax", context="C1", context_tags="events",
            pattern="missing closing bracket", correction="add bracket",
            source="seed",
        )
        rule = db.record(
            category="design", context="C2", context_tags="focus_trees",
            pattern="no ai_will_do factor", correction="add ai_will_do",
            source="seed",
        )
        assert rule["id"] == "LR-0002"
        assert rule["occurrence_count"] == 1

    def test_identical_pattern_same_tags_dedup(self, db):
        db.record(
            category="syntax", context="ctx", context_tags="events,mtth",
            pattern="is_triggered_only with mtth", correction="remove is_triggered_only",
            source="human_correction",
        )
        rule = db.record(
            category="logic", context="ctx", context_tags="events,mtth",
            pattern="is_triggered_only with mtth", correction="remove is_triggered_only",
            source="agent_self_correction",
        )
        assert rule["id"] == "LR-0001"
        assert rule["occurrence_count"] == 2


# ── Export/Import ────────────────────────────────────────────

class TestExportImport:
    def test_export_jsonl(self, db, tmp_path):
        db.record(category="syntax", context="C", context_tags="t", pattern="p", correction="c", source="seed")
        out = tmp_path / "rules.jsonl"
        result = export_to_file(db, output_path=out, format="json")
        assert result["count"] == 1
        content = out.read_text()
        lines = [l for l in content.strip().splitlines() if l.strip()]
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["id"] == "LR-0001"

    def test_export_markdown(self, db, tmp_path):
        db.record(category="syntax", context="C", context_tags="t", pattern="p", correction="c", source="seed")
        out = tmp_path / "rules.md"
        result = export_to_file(db, output_path=out, format="markdown")
        assert result["format"] == "markdown"
        content = out.read_text()
        assert "LR-0001" in content
        assert "Anti-pattern" in content

    def test_import_from_jsonl(self, db, tmp_path):
        rules_data = [
            {"id": "LR-0100", "category": "syntax", "severity": "error",
             "context": "Imported rule", "context_tags": "test",
             "pattern": "imported pattern", "correction": "imported correction",
             "source": "seed", "occurrence_count": 1},
        ]
        jl_path = tmp_path / "import.jsonl"
        jl_path.write_text("\n".join(json.dumps(r) for r in rules_data))

        result = import_from_file(db, input_path=str(jl_path))
        assert result["imported"] == 1

        rule = db.get_by_id("LR-0100")
        assert rule is not None
        assert rule["pattern"] == "imported pattern"

    def test_import_skips_existing(self, db, tmp_path):
        db.record(category="syntax", context="C", context_tags="t", pattern="p", correction="c", source="seed")
        rules_data = [
            {"id": "LR-0001", "category": "syntax", "severity": "error",
             "context": "Different", "context_tags": "x",
             "pattern": "different", "correction": "different",
             "source": "seed"},
        ]
        jl_path = tmp_path / "import.jsonl"
        jl_path.write_text(json.dumps(rules_data[0]))

        result = import_from_file(db, input_path=str(jl_path))
        assert result["imported"] == 0
        assert result["skipped"] == 1
        # Original unchanged
        assert db.get_by_id("LR-0001")["pattern"] == "p"

    def test_import_nonexistent_file(self, db, tmp_path):
        result = import_from_file(db, input_path=tmp_path / "does_not_exist.jsonl")
        assert result["imported"] == 0
        assert "error" in result

    def test_export_excludes_resolved_by_default(self, db, tmp_path):
        db.record(category="syntax", context="C1", context_tags="t", pattern="p1", correction="c1", source="seed")
        db.record(category="logic", context="C2", context_tags="t", pattern="p2", correction="c2", source="seed")
        db.resolve("LR-0002", note="done")
        out = tmp_path / "rules.jsonl"
        result = export_to_file(db, output_path=out, format="json", include_resolved=False)
        assert result["count"] == 1

    def test_export_includes_resolved_when_requested(self, db, tmp_path):
        db.record(category="syntax", context="C1", context_tags="t", pattern="p1", correction="c1", source="seed")
        db.record(category="logic", context="C2", context_tags="t", pattern="p2", correction="c2", source="seed")
        db.resolve("LR-0002", note="done")
        out = tmp_path / "rules.jsonl"
        result = export_to_file(db, output_path=out, format="json", include_resolved=True)
        assert result["count"] == 2


# ── Seeder ───────────────────────────────────────────────────

class TestSeeder:
    def test_seeds_empty_db(self, db):
        result = seed_if_empty(db)
        assert result["seeded"] == 14  # 8 original + 6 from mod scans
        assert result["skipped"] == 0
        # Verify one of them
        rule = db.get_by_id("LR-0001")
        assert "completion_reward" in rule["pattern"].lower()

    def test_skips_nonempty_db(self, db):
        db.record(category="syntax", context="C", context_tags="t", pattern="p", correction="c", source="seed")
        result = seed_if_empty(db)
        assert result["seeded"] == 0
        assert result["skipped"] == 1


# ── Detector ─────────────────────────────────────────────────

class TestDetector:
    def test_detects_recurring(self):
        errors = [
            {"category": "duplicate_id", "message": "Duplicate id: my_event.1 in file events.txt"},
            {"category": "duplicate_id", "message": "Duplicate id: my_event.2 in file events.txt"},
            {"category": "duplicate_id", "message": "Duplicate id: my_focus.1 in file focuses.txt"},
        ]
        suggestions = detect_recurring_patterns(errors, threshold=3)
        # All 3 share same normalized signature (duplicate_id + <FILE>)
        assert len(suggestions) == 1
        assert suggestions[0]["occurrence_count"] == 3

    def test_below_threshold(self):
        errors = [
            {"category": "duplicate_id", "message": "Duplicate id: x in file a.txt"},
            {"category": "duplicate_id", "message": "Duplicate id: y in file b.txt"},
        ]
        suggestions = detect_recurring_patterns(errors, threshold=3)
        assert len(suggestions) == 0

    def test_different_categories_dont_merge(self):
        errors = [
            {"category": "duplicate_id", "message": "Duplicate id: x in file a.txt"},
            {"category": "missing_loc", "message": "Missing localization for x in file a.txt"},
            {"category": "duplicate_id", "message": "Duplicate id: y in file b.txt"},
        ]
        suggestions = detect_recurring_patterns(errors, threshold=3)
        assert len(suggestions) == 0  # Neither category hits threshold

    def test_empty_errors(self):
        suggestions = detect_recurring_patterns([], threshold=3)
        assert suggestions == []

    def test_includes_file_hint(self):
        errors = [
            {"category": "unexpected_token", "message": "Unexpected token: } at line 42 in common/national_focus/germany.txt"},
            {"category": "unexpected_token", "message": "Unexpected token: } at line 108 in events/political.txt"},
            {"category": "unexpected_token", "message": "Unexpected token: } at line 15 in decisions/categories.txt"},
        ]
        suggestions = detect_recurring_patterns(errors, threshold=3)
        assert len(suggestions) == 1
        assert "file_hint" in suggestions[0]

    def test_custom_threshold(self, db):
        # Use messages where variable parts are numeric (normalized away by _NUM_RE)
        errors = [
            {"category": "missing_loc", "message": "Missing loc key: 1001 in file x.txt"},
            {"category": "missing_loc", "message": "Missing loc key: 1002 in file x.txt"},
            {"category": "missing_loc", "message": "Missing loc key: 1003 in file x.txt"},
            {"category": "missing_loc", "message": "Missing loc key: 1004 in file x.txt"},
            {"category": "missing_loc", "message": "Missing loc key: 1005 in file x.txt"},
        ]
        suggestions = detect_recurring_patterns(errors, threshold=5)
        assert len(suggestions) == 1
        assert suggestions[0]["occurrence_count"] == 5


# ── Formatting ───────────────────────────────────────────────

class TestFormatting:
    def test_format_rules_block_empty(self):
        output = format_rules_block([])
        assert "No active rules" in output

    def test_format_rules_block_with_rules(self, db):
        db.record(
            category="syntax", context="Test", context_tags="test",
            pattern="bad", correction="good", severity="error", source="seed",
        )
        rules = db.query()
        output = format_rules_block(rules)
        assert "LR-0001" in output
        assert "⛔" in output
        assert "ANTI-PATTERN" in output
        assert "DO INSTEAD" in output

    def test_format_rules_block_warning(self, db):
        db.record(
            category="design", context="Test", context_tags="test",
            pattern="bad", correction="good", severity="warning", source="seed",
        )
        rules = db.query()
        output = format_rules_block(rules)
        assert "⚠️" in output

    def test_format_rules_block_style(self, db):
        db.record(
            category="convention", context="Test", context_tags="test",
            pattern="bad", correction="good", severity="style", source="seed",
        )
        rules = db.query()
        output = format_rules_block(rules)
        assert "💡" in output

    def test_rules_to_jsonl(self, db):
        db.record(category="syntax", context="C", context_tags="t", pattern="p", correction="c", source="seed")
        output = rules_to_jsonl(db.export_all())
        lines = [l for l in output.strip().splitlines() if l.strip()]
        assert len(lines) == 1
        assert json.loads(lines[0])["id"] == "LR-0001"

    def test_rules_to_jsonl_multiple(self, db):
        db.record(category="syntax", context="A", context_tags="a", pattern="p1", correction="c1", source="seed")
        db.record(category="logic", context="B", context_tags="b", pattern="p2", correction="c2", source="seed")
        output = rules_to_jsonl(db.export_all())
        lines = [l for l in output.strip().splitlines() if l.strip()]
        assert len(lines) == 2
        ids = [json.loads(line)["id"] for line in lines]
        assert "LR-0001" in ids
        assert "LR-0002" in ids

    def test_rules_to_markdown(self, db):
        db.record(category="syntax", context="C", context_tags="t", pattern="p", correction="c", source="seed")
        output = rules_to_markdown(db.export_all())
        assert "LR-0001" in output
        assert "Anti-pattern" in output
        assert "active" in output

    def test_rules_to_markdown_empty(self):
        output = rules_to_markdown([])
        assert "No rules" in output


# ── Stats ────────────────────────────────────────────────────

class TestStats:
    def test_stats_empty(self, db):
        stats = db.stats()
        assert stats["total"] == 0
        assert stats["active"] == 0

    def test_stats_after_seed(self, db):
        seed_if_empty(db)
        stats = db.stats()
        assert stats["total"] == 14
        assert stats["active"] == 14
        assert stats["resolved"] == 0
        assert len(stats["by_category"]) > 0

    def test_stats_mixed(self, db):
        db.record(category="syntax", context="A", context_tags="a", pattern="p1", correction="c1", source="seed")
        db.record(category="logic", context="B", context_tags="b", pattern="p2", correction="c2", source="seed")
        db.resolve("LR-0002", note="done")
        stats = db.stats()
        assert stats["total"] == 2
        assert stats["active"] == 1
        assert stats["resolved"] == 1
        assert stats["by_category"]["syntax"] == 1


# ── Promotion Candidates ─────────────────────────────────────

class TestPromotion:
    def test_no_candidates_below_threshold(self, db):
        db.record(category="syntax", context="C", context_tags="t", pattern="p", correction="c", source="seed")
        candidates = db.get_promotion_candidates(min_occurrences=10)
        assert candidates == []

    def test_no_candidates_when_resolved(self, db):
        # Record a rule and manually bump its count
        db.record(category="syntax", context="C", context_tags="t", pattern="p", correction="c", source="seed")
        conn = db._connect()
        conn.execute("UPDATE learned_rules SET occurrence_count = 15 WHERE id = 'LR-0001'")
        conn.commit()
        db.resolve("LR-0001", note="done")
        candidates = db.get_promotion_candidates(min_occurrences=10, min_days=0)
        assert candidates == []


# ── Decay Candidates ─────────────────────────────────────────

class TestDecay:
    def test_decay_candidates_empty_for_new_rules(self, db):
        db.record(
            category="syntax", context="C", context_tags="t",
            pattern="p", correction="c", source="agent_self_correction",
        )
        candidates = db.get_decay_candidates(source="agent_self_correction", inactive_days=0)
        assert candidates == []  # Not old enough

    def test_decay_different_source_not_flagged(self, db):
        db.record(
            category="syntax", context="C", context_tags="t",
            pattern="p", correction="c", source="human_correction",
        )
        candidates = db.get_decay_candidates(source="agent_self_correction", inactive_days=0)
        assert candidates == []
