"""SQLite index for session lookups (GAP-025).

A disposable derived index over the JSONL session store. The index is always
rebuildable from the canonical JSONL files. On any corruption or failure,
``available`` is set to ``False`` and the store falls back to JSONL scanning.

Schema: sessions (summary fields) + session_tasks (task→session linking).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import SessionSummary

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT PRIMARY KEY,
    title        TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL DEFAULT '',
    updated_at   TEXT NOT NULL DEFAULT '',
    message_count INTEGER NOT NULL DEFAULT 0,
    task_count   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS session_tasks (
    task_id      TEXT PRIMARY KEY,
    session_id   TEXT NOT NULL,
    task_type    TEXT NOT NULL DEFAULT '',
    description  TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'pending',
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_updated
    ON sessions(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_tasks_session
    ON session_tasks(session_id);
"""


class SessionIndex:
    """Derived SQLite index for fast O(1) session lookups and listing.

    Always disposable — rebuildable from the JSONL store at any time.
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self.available = False

    def _ensure_conn(self) -> sqlite3.Connection | None:
        """Get or create the SQLite connection. Returns None on failure."""
        if self._conn is not None:
            return self._conn
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(_SCHEMA)
            conn.commit()
            self._conn = conn
            self.available = True
            return conn
        except (OSError, sqlite3.Error):
            self.available = False
            return None

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass
            self._conn = None
            self.available = False

    # -- Upserts ----------------------------------------------------------

    def upsert_session(
        self,
        session_id: str,
        title: str,
        created_at: str,
        updated_at: str,
        message_count: int = 0,
        task_count: int = 0,
    ) -> bool:
        conn = self._ensure_conn()
        if conn is None:
            return False
        try:
            conn.execute(
                """INSERT INTO sessions (session_id, title, created_at, updated_at, message_count, task_count)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(session_id) DO UPDATE SET
                       title=excluded.title,
                       updated_at=excluded.updated_at,
                       message_count=excluded.message_count,
                       task_count=excluded.task_count""",
                (session_id, title, created_at, updated_at, message_count, task_count),
            )
            conn.commit()
            return True
        except sqlite3.Error:
            self.available = False
            return False

    def upsert_task(
        self,
        task_id: str,
        session_id: str,
        task_type: str,
        description: str,
        status: str,
    ) -> bool:
        conn = self._ensure_conn()
        if conn is None:
            return False
        try:
            conn.execute(
                """INSERT INTO session_tasks (task_id, session_id, task_type, description, status)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(task_id) DO UPDATE SET
                       session_id=excluded.session_id,
                       task_type=excluded.task_type,
                       description=excluded.description,
                       status=excluded.status""",
                (task_id, session_id, task_type, description, status),
            )
            conn.commit()
            return True
        except sqlite3.Error:
            self.available = False
            return False

    # -- Queries ----------------------------------------------------------

    def list_summaries(
        self, *, limit: int = 50, order: str = "recent"
    ) -> list[SessionSummary] | None:
        """Return session summaries, newest first. Returns None on failure."""
        conn = self._ensure_conn()
        if conn is None:
            return None
        try:
            direction = "DESC" if order == "recent" else "ASC"
            rows = conn.execute(
                f"SELECT session_id, title, created_at, updated_at, message_count, task_count "
                f"FROM sessions ORDER BY updated_at {direction} LIMIT ?",
                (max(1, limit),),
            ).fetchall()
            return [
                SessionSummary(
                    session_id=row["session_id"],
                    title=row["title"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    message_count=row["message_count"],
                    task_count=row["task_count"],
                )
                for row in rows
            ]
        except sqlite3.Error:
            self.available = False
            return None

    def find_session_by_task(self, task_id: str) -> str | None:
        """Return the session_id that owns a task. None if not found."""
        conn = self._ensure_conn()
        if conn is None:
            return None
        try:
            row = conn.execute(
                "SELECT session_id FROM session_tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            return row["session_id"] if row else None
        except sqlite3.Error:
            self.available = False
            return None

    def rebuild(self, store: "SessionStore") -> bool:  # noqa: F821
        """Rebuild the index from the canonical JSONL store.

        Drops all tables, recreates schema, and rescans every session.
        """
        conn = self._ensure_conn()
        if conn is None:
            return False
        try:
            conn.execute("DROP TABLE IF EXISTS session_tasks")
            conn.execute("DROP TABLE IF EXISTS sessions")
            conn.executescript(_SCHEMA)
            conn.commit()
            self.available = True

            # Rescan all sessions from the store (imported lazily to avoid circular)
            summaries = store._list_sessions_scan(limit=999999, order="recent")
            for summary in summaries:
                self.upsert_session(
                    session_id=summary.session_id,
                    title=summary.title,
                    created_at=summary.created_at,
                    updated_at=summary.updated_at,
                    message_count=summary.message_count,
                    task_count=summary.task_count,
                )
            return True
        except sqlite3.Error:
            self.available = False
            return False
