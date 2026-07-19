"""JSONL+SQLite session store for HOI4 modding sessions (GAP-025).

Filesystem-backed persistence for agent modding sessions. Dual storage:
- JSONL files are the canonical source of truth (human-readable, crash-safe,
  append-only for the hot path).
- SQLite index is a disposable derived cache for fast list/lookup queries.

Directory layout::

    ~/.hoi4_mcp/sessions/
      index.db              # derived SQLite index (disposable)
      <session_id>/
        session.jsonl       # line 1 = metadata, subsequent = messages
        tasks.jsonl         # one line per attached task

Concurrency: ``threading.RLock`` for in-process serialization; re-reads
metadata before writes to handle cross-process trampling. Pure-append
JSONL writes are OS-level atomic for small payloads.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from .index import SessionIndex
from .models import (
    Session,
    SessionMessage,
    SessionSummary,
    SessionTask,
    _new_session_id,
    _utcnow_iso,
)

_DEFAULT_ROOT = Path.home() / ".hoi4_mcp" / "sessions"


class SessionStore:
    """Read/write JSONL sessions with an optional derived SQLite index."""

    def __init__(
        self, root: Path | str | None = None, *, use_index: bool = True
    ) -> None:
        self.root = Path(root).expanduser().resolve() if root else _DEFAULT_ROOT
        self._lock = threading.RLock()
        self._cache: dict[str, Session] = {}
        self._index: SessionIndex | None = (
            SessionIndex(self.root / "index.db") if use_index else None
        )
        # Eagerly initialize the index connection so upserts work immediately
        if self._index is not None:
            self._index._ensure_conn()

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _session_dir(self, session_id: str) -> Path:
        return self.root / session_id

    def _session_jsonl(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "session.jsonl"

    def _tasks_jsonl(self, session_id: str) -> Path:
        return self._session_dir(session_id) / "tasks.jsonl"

    # ------------------------------------------------------------------
    # Create / read
    # ------------------------------------------------------------------

    def create_session(
        self,
        *,
        title: str = "",
        session_id: str | None = None,
        metadata: dict | None = None,
    ) -> Session:
        """Create and persist a new empty session."""
        with self._lock:
            sid = session_id or _new_session_id()
            attempts = 0
            while self._session_dir(sid).exists():
                sid = _new_session_id()
                attempts += 1
                if attempts > 8:
                    raise RuntimeError("Could not allocate a unique session_id")

            session = Session(
                session_id=sid,
                title=title,
                metadata=dict(metadata or {}),
            )
            self._session_dir(sid).mkdir(parents=True, exist_ok=True)
            self._rewrite_metadata(session)
            self._cache[sid] = session
            self._index_session(session)
            return session

    def get_session(self, session_id: str) -> Session | None:
        """Load a session from disk (cached on subsequent calls)."""
        with self._lock:
            cached = self._cache.get(session_id)
            if cached is not None:
                return cached
            session = self._load(session_id)
            if session is not None:
                self._cache[session_id] = session
            return session

    def list_sessions(
        self, *, limit: int = 50, order: str = "recent"
    ) -> list[SessionSummary]:
        """Return summaries for the ``limit`` most recent sessions.

        Served from SQLite index when available, falling back to JSONL scan.
        """
        with self._lock:
            if self._index is not None and self._index.available:
                summaries = self._index.list_summaries(limit=limit, order=order)
                if summaries is not None:
                    return summaries
            return self._list_sessions_scan(limit=limit, order=order)

    def _list_sessions_scan(
        self, *, limit: int, order: str
    ) -> list[SessionSummary]:
        """Pure-JSONL listing (fallback + index-rebuild source)."""
        with self._lock:
            if not self.root.exists():
                return []
            summaries: list[SessionSummary] = []
            for entry in sorted(self.root.iterdir()):
                if not entry.is_dir():
                    continue
                jsonl = entry / "session.jsonl"
                if not jsonl.exists():
                    continue
                metadata = self._read_metadata(entry.name)
                if metadata is None:
                    continue
                message_count = self._count_jsonl(jsonl) - 1
                task_count = self._count_jsonl(self._tasks_jsonl(entry.name))
                summaries.append(
                    SessionSummary(
                        session_id=metadata["session_id"],
                        title=metadata.get("title", ""),
                        created_at=metadata.get("created_at", ""),
                        updated_at=metadata.get("updated_at", ""),
                        message_count=max(0, message_count),
                        task_count=task_count,
                    )
                )
            if order == "recent":
                summaries.sort(key=lambda s: s.updated_at, reverse=True)
            elif order == "oldest":
                summaries.sort(key=lambda s: s.updated_at)
            return summaries[: max(1, limit)]

    # ------------------------------------------------------------------
    # Append helpers (hot path — pure-append JSONL, OS-level atomic)
    # ------------------------------------------------------------------

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        *,
        task_id_ref: str | None = None,
        metadata: dict | None = None,
    ) -> SessionMessage | None:
        """Append a transcript message. Returns None if session not found."""
        with self._lock:
            session = self.get_session(session_id)
            if session is None:
                return None
            msg = SessionMessage(
                role=role,
                content=content,
                task_id_ref=task_id_ref,
                metadata=metadata,
            )
            self._append_jsonl(self._session_jsonl(session_id), msg.to_dict())
            session.messages.append(msg)
            session.touch()
            self._rewrite_metadata(session)
            self._index_session(session)
            return msg

    def attach_task(self, session_id: str, task: SessionTask) -> bool:
        """Attach a workflow task to a session."""
        with self._lock:
            session = self.get_session(session_id)
            if session is None:
                return False
            self._append_jsonl(self._tasks_jsonl(session_id), task.to_dict())
            session.tasks.append(task)
            session.touch()
            self._rewrite_metadata(session)
            self._index_session(session)
            if self._index is not None and self._index.available:
                self._index.upsert_task(
                    task_id=task.task_id,
                    session_id=session_id,
                    task_type=task.task_type,
                    description=task.description,
                    status=task.status,
                )
            return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self, session_id: str) -> Session | None:
        """Load a full session (metadata + messages + tasks) from JSONL."""
        jsonl = self._session_jsonl(session_id)
        if not jsonl.exists():
            return None
        metadata = self._read_metadata(session_id)
        if metadata is None:
            return None
        session = Session.from_metadata(metadata)
        # Load messages
        try:
            lines = jsonl.read_text(encoding="utf-8").strip().split("\n")
            for line in lines[1:]:  # skip metadata line
                if line.strip():
                    session.messages.append(SessionMessage.from_dict(json.loads(line)))
        except (OSError, json.JSONDecodeError):
            pass
        # Load tasks
        tasks_jsonl = self._tasks_jsonl(session_id)
        if tasks_jsonl.exists():
            try:
                for line in tasks_jsonl.read_text(encoding="utf-8").strip().split("\n"):
                    if line.strip():
                        session.tasks.append(SessionTask.from_dict(json.loads(line)))
            except (OSError, json.JSONDecodeError):
                pass
        return session

    def _read_metadata(self, session_id: str) -> dict | None:
        """Read just the first line (metadata) of a session JSONL."""
        jsonl = self._session_jsonl(session_id)
        if not jsonl.exists():
            return None
        try:
            with open(jsonl, "r", encoding="utf-8") as fh:
                first_line = fh.readline().strip()
            if first_line:
                return json.loads(first_line)
        except (OSError, json.JSONDecodeError):
            pass
        return None

    def _rewrite_metadata(self, session: Session) -> None:
        """Rewrite metadata as the first line of session.jsonl.

        Reads all messages, writes metadata + all messages back.
        """
        jsonl = self._session_jsonl(session.session_id)
        messages = []
        if jsonl.exists():
            try:
                lines = jsonl.read_text(encoding="utf-8").strip().split("\n")
                for line in lines[1:]:
                    if line.strip():
                        messages.append(line)
            except OSError:
                pass
        meta_line = json.dumps(session.to_metadata_dict(), ensure_ascii=False)
        new_content = meta_line + "\n" + "\n".join(messages) + ("\n" if messages else "")
        jsonl.write_text(new_content, encoding="utf-8")

    @staticmethod
    def _append_jsonl(path: Path, obj: dict) -> None:
        """Pure-append one JSON line to a JSONL file (OS-level atomic for small writes)."""
        line = json.dumps(obj, ensure_ascii=False) + "\n"
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line)

    @staticmethod
    def _count_jsonl(path: Path) -> int:
        """Count non-empty lines in a JSONL file (fast line scan)."""
        if not path.exists():
            return 0
        try:
            return sum(1 for _ in open(path, "r", encoding="utf-8") if _.strip())
        except OSError:
            return 0

    def _index_session(self, session: Session) -> None:
        """Update the SQLite index for a session (best-effort)."""
        if self._index is None or not self._index.available:
            return
        self._index.upsert_session(
            session_id=session.session_id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=len(session.messages),
            task_count=len(session.tasks),
        )
