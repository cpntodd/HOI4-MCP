"""
learning/db.py — LearnedRulesDB
SQLite wrapper for the adaptive learning system.
Separate DB from vanilla.db (different lifecycles).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DB_PATH_DEFAULT = Path.home() / ".hoi4_mcp" / "learned_rules.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS learned_rules (
    id                TEXT PRIMARY KEY,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT NOT NULL DEFAULT (datetime('now')),

    category          TEXT NOT NULL
        CHECK(category IN (
            'syntax','logic','design','scope',
            'localisation','id_collision','convention','performance'
        )),
    severity          TEXT NOT NULL DEFAULT 'error'
        CHECK(severity IN ('error','warning','style')),

    context           TEXT NOT NULL,
    context_tags      TEXT DEFAULT '',

    pattern           TEXT NOT NULL,
    correction        TEXT NOT NULL,

    source            TEXT NOT NULL
        CHECK(source IN (
            'agent_self_correction','human_correction',
            'game_log','validation','vanilla_reference','seed'
        )),
    file_path         TEXT DEFAULT '',
    line_range        TEXT DEFAULT '',

    occurrence_count  INTEGER NOT NULL DEFAULT 1,
    last_triggered_at TEXT,

    resolved          INTEGER NOT NULL DEFAULT 0,
    resolved_at       TEXT,
    resolved_note     TEXT DEFAULT '',
    superseded_by     TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_lr_tags      ON learned_rules(context_tags);
CREATE INDEX IF NOT EXISTS idx_lr_category   ON learned_rules(category);
CREATE INDEX IF NOT EXISTS idx_lr_resolved   ON learned_rules(resolved);
CREATE INDEX IF NOT EXISTS idx_lr_severity   ON learned_rules(severity);
CREATE INDEX IF NOT EXISTS idx_lr_source     ON learned_rules(source);
"""


class LearnedRulesDB:
    """Thin wrapper around the learned_rules SQLite database."""

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else _DB_PATH_DEFAULT
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    # ── Connection lifecycle ──────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def ensure_schema(self) -> None:
        conn = self._connect()
        conn.executescript(_SCHEMA)
        conn.commit()

    # ── Next ID ───────────────────────────────────────────────

    def _next_id(self) -> str:
        conn = self._connect()
        row = conn.execute(
            "SELECT id FROM learned_rules ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return "LR-0001"
        try:
            num = int(row["id"].split("-")[1]) + 1
        except (ValueError, IndexError):
            num = 1
        return f"LR-{num:04d}"

    # ── Record (insert or increment on dedup match) ───────────

    def record(
        self,
        *,
        category: str,
        context: str,
        context_tags: str,
        pattern: str,
        correction: str,
        severity: str = "error",
        source: str = "agent_self_correction",
        file_path: str = "",
        line_range: str = "",
    ) -> dict[str, Any]:
        """Insert a new rule or increment an existing match. Returns the rule dict."""
        self.ensure_schema()
        conn = self._connect()

        # Check for dedup match first
        existing = self._find_similar(pattern, context_tags)
        if existing:
            conn.execute(
                """UPDATE learned_rules
                   SET occurrence_count  = occurrence_count + 1,
                       last_triggered_at = datetime('now'),
                       updated_at        = datetime('now')
                   WHERE id = ?""",
                (existing["id"],),
            )
            conn.commit()
            return self.get_by_id(existing["id"])

        rule_id = self._next_id()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO learned_rules
               (id, category, severity, context, context_tags,
                pattern, correction, source, file_path, line_range,
                occurrence_count, last_triggered_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
            (
                rule_id, category, severity, context, context_tags,
                pattern, correction, source, file_path, line_range,
                now,
            ),
        )
        conn.commit()
        return self.get_by_id(rule_id)

    # ── Query ─────────────────────────────────────────────────

    def get_by_id(self, rule_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM learned_rules WHERE id = ?", (rule_id,)
        ).fetchone()
        return dict(row) if row else None

    def query(
        self,
        *,
        context_tags: str = "",
        category: str = "",
        severity: str = "",
        include_resolved: bool = False,
    ) -> list[dict[str, Any]]:
        """Query active rules with optional filters.

        context_tags: comma-separated — matches if ANY tag overlaps.
        category/severity: exact match if non-empty.
        """
        self.ensure_schema()
        conn = self._connect()

        clauses: list[str] = []
        params: list[Any] = []

        if not include_resolved:
            clauses.append("resolved = 0")

        if category:
            clauses.append("category = ?")
            params.append(category)

        if severity:
            clauses.append("severity = ?")
            params.append(severity)

        if context_tags:
            # Build OR conditions for each tag
            tags = [t.strip().lower() for t in context_tags.split(",") if t.strip()]
            if tags:
                tag_clauses = []
                for tag in tags:
                    tag_clauses.append(
                        "LOWER(context_tags) LIKE ?"
                    )
                    params.append(f"%{tag}%")
                clauses.append(f"({' OR '.join(tag_clauses)})")

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM learned_rules {where} ORDER BY severity != 'error', severity != 'warning', id"

        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_promotion_candidates(
        self, min_occurrences: int = 10, min_days: int = 30
    ) -> list[dict[str, Any]]:
        """Rules eligible for promotion to SKILL.md / agent prompt."""
        self.ensure_schema()
        conn = self._connect()
        rows = conn.execute(
            """SELECT * FROM learned_rules
               WHERE resolved = 0
                 AND occurrence_count >= ?
                 AND created_at <= datetime('now', '-' || ? || ' days')
               ORDER BY occurrence_count DESC""",
            (min_occurrences, min_days),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_decay_candidates(
        self, source: str = "agent_self_correction", inactive_days: int = 30
    ) -> list[dict[str, Any]]:
        """Low-confidence rules that haven't been re-triggered."""
        self.ensure_schema()
        conn = self._connect()
        rows = conn.execute(
            """SELECT * FROM learned_rules
               WHERE resolved = 0
                 AND source = ?
                 AND (last_triggered_at IS NULL
                      OR last_triggered_at <= datetime('now', '-' || ? || ' days'))
                 AND occurrence_count <= 2
               ORDER BY created_at ASC""",
            (source, inactive_days),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Resolve ───────────────────────────────────────────────

    def resolve(
        self,
        rule_id: str,
        note: str = "",
        superseded_by: str = "",
    ) -> dict[str, Any] | None:
        conn = self._connect()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """UPDATE learned_rules
               SET resolved = 1, resolved_at = ?,
                   resolved_note = ?, superseded_by = ?,
                   updated_at = datetime('now')
               WHERE id = ?""",
            (now, note, superseded_by, rule_id),
        )
        conn.commit()
        return self.get_by_id(rule_id)

    # ── Statistics ────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        conn = self._connect()
        self.ensure_schema()
        total = conn.execute("SELECT COUNT(*) FROM learned_rules").fetchone()[0]
        active = conn.execute(
            "SELECT COUNT(*) FROM learned_rules WHERE resolved = 0"
        ).fetchone()[0]
        by_category = {}
        for row in conn.execute(
            "SELECT category, COUNT(*) as cnt FROM learned_rules WHERE resolved = 0 GROUP BY category"
        ):
            by_category[row[0]] = row[1]
        by_severity = {}
        for row in conn.execute(
            "SELECT severity, COUNT(*) as cnt FROM learned_rules WHERE resolved = 0 GROUP BY severity"
        ):
            by_severity[row[0]] = row[1]
        by_source = {}
        for row in conn.execute(
            "SELECT source, COUNT(*) as cnt FROM learned_rules WHERE resolved = 0 GROUP BY source"
        ):
            by_source[row[0]] = row[1]
        top_rules = [
            dict(r) for r in conn.execute(
                "SELECT id, pattern, occurrence_count FROM learned_rules WHERE resolved = 0 ORDER BY occurrence_count DESC LIMIT 5"
            ).fetchall()
        ]
        return {
            "total": total,
            "active": active,
            "resolved": total - active,
            "by_category": by_category,
            "by_severity": by_severity,
            "by_source": by_source,
            "top_rules": top_rules,
        }

    # ── Export ────────────────────────────────────────────────

    def export_all(
        self, *, include_resolved: bool = False
    ) -> list[dict[str, Any]]:
        conn = self._connect()
        where = "" if include_resolved else "WHERE resolved = 0"
        rows = conn.execute(f"SELECT * FROM learned_rules {where} ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    # ── Import ────────────────────────────────────────────────

    def import_rules(self, rules: list[dict[str, Any]]) -> dict[str, int]:
        """Import rules from .jsonl data. Skips IDs that already exist.
        Returns {"imported": N, "skipped": M}."""
        self.ensure_schema()
        conn = self._connect()
        imported = 0
        skipped = 0
        now = datetime.now(timezone.utc).isoformat()
        for rule in rules:
            rule_id = rule.get("id", "")
            if not rule_id:
                continue
            existing = self.get_by_id(rule_id)
            if existing:
                skipped += 1
                continue
            conn.execute(
                """INSERT OR IGNORE INTO learned_rules
                   (id, created_at, updated_at, category, severity,
                    context, context_tags, pattern, correction, source,
                    file_path, line_range, occurrence_count,
                    last_triggered_at, resolved, resolved_at,
                    resolved_note, superseded_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    rule_id,
                    rule.get("created_at", now),
                    rule.get("updated_at", now),
                    rule.get("category", "convention"),
                    rule.get("severity", "error"),
                    rule.get("context", ""),
                    rule.get("context_tags", ""),
                    rule.get("pattern", ""),
                    rule.get("correction", ""),
                    rule.get("source", "seed"),
                    rule.get("file_path", ""),
                    rule.get("line_range", ""),
                    rule.get("occurrence_count", 1),
                    rule.get("last_triggered_at"),
                    rule.get("resolved", 0),
                    rule.get("resolved_at"),
                    rule.get("resolved_note", ""),
                    rule.get("superseded_by", ""),
                ),
            )
            imported += 1
        conn.commit()
        return {"imported": imported, "skipped": skipped}

    # ── Deduplication (internal) ──────────────────────────────

    def _find_similar(
        self, pattern: str, context_tags: str, threshold: float = 0.7
    ) -> dict[str, Any] | None:
        """Token-overlap Jaccard similarity. Weighted: 60% pattern, 40% tags."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM learned_rules WHERE resolved = 0"
        ).fetchall()

        new_tokens = set(pattern.lower().split())
        new_tags = set(t.strip().lower() for t in context_tags.split(",") if t.strip())

        if not new_tokens:
            return None

        best_match: dict[str, Any] | None = None
        best_score = 0.0

        for row in rows:
            rule = dict(row)
            existing_tokens = set(rule["pattern"].lower().split())
            if not existing_tokens:
                continue

            # Pattern similarity (Jaccard)
            intersection_p = len(new_tokens & existing_tokens)
            union_p = len(new_tokens | existing_tokens)
            pattern_sim = intersection_p / union_p if union_p else 0.0

            # Tag similarity (Jaccard)
            existing_tags = set(
                t.strip().lower() for t in rule["context_tags"].split(",") if t.strip()
            )
            union_t = len(new_tags | existing_tags)
            tag_sim = len(new_tags & existing_tags) / union_t if union_t else 0.0

            combined = 0.6 * pattern_sim + 0.4 * tag_sim

            if combined >= threshold and combined > best_score:
                best_score = combined
                best_match = rule

        return best_match

    # ── Conflict Detection (for session_review) ───────────────

    def find_conflicts(
        self, context_tags: str, correction: str, pattern: str = ""
    ) -> list[dict[str, Any]]:
        """Find existing rules that may conflict with a candidate rule.

        A conflict is: overlapping context_tags but DIFFERENT correction.
        This is used by session_review to flag rules needing human review.

        Returns list of potentially conflicting existing rules (empty = no conflict).
        """
        conn = self._connect()
        all_active = conn.execute(
            "SELECT * FROM learned_rules WHERE resolved = 0"
        ).fetchall()

        if not all_active:
            return []

        new_tags = set(t.strip().lower() for t in context_tags.split(",") if t.strip())
        new_correction_tokens = set(correction.lower().split())
        new_pattern_tokens = set(pattern.lower().split()) if pattern else set()

        conflicts: list[dict[str, Any]] = []

        for row in all_active:
            rule = dict(row)
            existing_tags = set(
                t.strip().lower() for t in rule["context_tags"].split(",") if t.strip()
            )

            # Must have at least 1 overlapping tag
            if not (new_tags & existing_tags):
                continue

            existing_correction_tokens = set(rule["correction"].lower().split())

            # If corrections are highly similar, it's NOT a conflict (it's a duplicate/near-duplicate)
            if new_correction_tokens and existing_correction_tokens:
                union_c = len(new_correction_tokens | existing_correction_tokens)
                correction_sim = (
                    len(new_correction_tokens & existing_correction_tokens) / union_c
                    if union_c else 0.0
                )
                if correction_sim >= 0.7:
                    continue  # Same correction approach — not a conflict

            # Also check if patterns are similar (same mistake, different fix = conflict)
            if new_pattern_tokens:
                existing_pattern_tokens = set(rule["pattern"].lower().split())
                if existing_pattern_tokens:
                    union_p = len(new_pattern_tokens | existing_pattern_tokens)
                    pattern_sim = (
                        len(new_pattern_tokens & existing_pattern_tokens) / union_p
                        if union_p else 0.0
                    )
                    # High pattern similarity + low correction similarity = CONFLICT
                    if pattern_sim >= 0.5:
                        conflicts.append(rule)
                        continue

            # Overlapping tags but different corrections → potential conflict
            conflicts.append(rule)

        return conflicts

    def get_all_active_rules(self) -> list[dict[str, Any]]:
        """Return all active (non-resolved) rules. Used for consistency checks."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM learned_rules WHERE resolved = 0 ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]
