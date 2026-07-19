"""Session data models for JSONL persistence (GAP-025).

Lightweight dataclasses representing sessions, messages, and tasks
stored in the JSONL+SQLite dual storage system.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _new_session_id() -> str:
    """Generate an 8-char hex session ID."""
    return secrets.token_hex(4)


def _utcnow_iso() -> str:
    """Current UTC timestamp in ISO 8601 (compact, no microseconds)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class SessionMessage:
    """One transcript message in a session."""
    role: str  # "user" | "assistant" | "tool" | "system"
    content: str
    timestamp: str = field(default_factory=_utcnow_iso)
    task_id_ref: str | None = None  # optional task this message belongs to
    metadata: dict | None = None

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "task_id_ref": self.task_id_ref,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionMessage":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp", _utcnow_iso()),
            task_id_ref=data.get("task_id_ref"),
            metadata=data.get("metadata"),
        )


@dataclass
class SessionTask:
    """A workflow task attached to a session."""
    task_id: str
    task_type: str  # e.g., "focus_tree", "event_chain", "decision_set"
    description: str = ""
    status: str = "pending"  # pending | running | completed | failed
    created_at: str = field(default_factory=_utcnow_iso)
    metadata: dict | None = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionTask":
        return cls(
            task_id=data["task_id"],
            task_type=data.get("task_type", "unknown"),
            description=data.get("description", ""),
            status=data.get("status", "pending"),
            created_at=data.get("created_at", _utcnow_iso()),
            metadata=data.get("metadata"),
        )


@dataclass
class Session:
    """A modding session — persists across VS Code restarts."""
    session_id: str = field(default_factory=_new_session_id)
    title: str = ""
    created_at: str = field(default_factory=_utcnow_iso)
    updated_at: str = field(default_factory=_utcnow_iso)
    metadata: dict | None = None
    # Not persisted directly — loaded from JSONL
    messages: list[SessionMessage] = field(default_factory=list)
    tasks: list[SessionTask] = field(default_factory=list)

    def touch(self) -> None:
        """Update the modification timestamp."""
        self.updated_at = _utcnow_iso()

    def to_metadata_dict(self) -> dict:
        """Serialize metadata line (first line of session.jsonl)."""
        return {
            "session_id": self.session_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_metadata(cls, data: dict) -> "Session":
        return cls(
            session_id=data["session_id"],
            title=data.get("title", ""),
            created_at=data.get("created_at", _utcnow_iso()),
            updated_at=data.get("updated_at", _utcnow_iso()),
            metadata=data.get("metadata"),
            messages=[],
            tasks=[],
        )


@dataclass
class SessionSummary:
    """Lightweight session card for listing — no full message bodies."""
    session_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0
    task_count: int = 0
