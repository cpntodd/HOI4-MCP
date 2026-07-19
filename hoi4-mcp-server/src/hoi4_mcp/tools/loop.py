"""Autonomous mod validation loop (GAP-027).

Adapted from DeepCode's P3 loop engineering centrepiece. Runs rounds of
HOI4 mod validation — each round generates/fixes mod content, validates
with ``validate_syntax``, and feeds results back as handoff notes for the
next round. Stops when validation passes or circuit breakers fire.

The loop is HOI4-specific:
- Test backpressure = ``validate_syntax`` on mod files (not pytest)
- Handoff notes track: namespace, IDs created, files touched, validation errors
- Failure ratchet escalates the prompt when the same validation error
  persists across rounds

Architecture:
- Fresh agent context per round (context never grows without bound)
- Durable JSON-on-disk state at ``<mod>/.hoi4_mcp/loop/state.json``
- Declarative stop policy: green validation, round budget, stall detection
- Injected round runner for testability
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Awaitable

# ---------------------------------------------------------------------------
# Loop state (durable, crash-proof)
# ---------------------------------------------------------------------------

STATUS_RUNNING = "running"
STATUS_SUCCEEDED = "succeeded"
STATUS_EXHAUSTED = "exhausted"
STATUS_STALLED = "stalled"
STATUS_ERROR = "error"
TERMINAL = {STATUS_SUCCEEDED, STATUS_EXHAUSTED, STATUS_STALLED, STATUS_ERROR}

_STATE_SUBPATH = ".hoi4_mcp/loop/state.json"
_DEFAULT_STALL_ROUNDS = 3
_HANDOFF_MAX = 2400


@dataclass
class RoundRecord:
    """One round: what the agent produced and what validation said."""
    index: int
    agent_stop_reason: str = ""
    validation_passed: bool | None = None
    validation_summary: str = ""
    validation_signature: str = ""  # stable fingerprint for stall detection
    files_touched: list[str] = field(default_factory=list)
    handoff: str = ""  # compact note carried to next round


@dataclass
class LoopState:
    """Full, persistable state of a mod validation loop."""
    goal: str
    workspace: str
    max_rounds: int = 8
    status: str = STATUS_RUNNING
    stop_reason: str = ""
    rounds: list[RoundRecord] = field(default_factory=list)

    @property
    def round_count(self) -> int:
        return len(self.rounds)

    @property
    def last_round(self) -> RoundRecord | None:
        return self.rounds[-1] if self.rounds else None

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL

    def add_round(self, record: RoundRecord) -> None:
        self.rounds.append(record)

    def finish(self, status: str, reason: str) -> None:
        self.status = status
        self.stop_reason = reason

    @staticmethod
    def path_for(workspace: str | Path) -> Path:
        return Path(workspace) / _STATE_SUBPATH

    def save(self) -> None:
        path = self.path_for(self.workspace)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "goal": self.goal,
            "workspace": self.workspace,
            "max_rounds": self.max_rounds,
            "status": self.status,
            "stop_reason": self.stop_reason,
            "rounds": [
                {
                    "index": r.index,
                    "agent_stop_reason": r.agent_stop_reason,
                    "validation_passed": r.validation_passed,
                    "validation_summary": r.validation_summary,
                    "validation_signature": r.validation_signature,
                    "files_touched": r.files_touched,
                    "handoff": r.handoff,
                }
                for r in self.rounds
            ],
        }
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @classmethod
    def load(cls, workspace: str | Path) -> "LoopState | None":
        path = cls.path_for(workspace)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        rounds = [RoundRecord(**r) for r in data.pop("rounds", [])]
        return cls(**data, rounds=rounds)


# ---------------------------------------------------------------------------
# Stop policy (declarative rule table)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Decision:
    stop: bool
    status: str
    reason: str


def decide(state: LoopState, *, stall_rounds: int = _DEFAULT_STALL_ROUNDS) -> Decision:
    """Decide whether the loop should stop after the latest round."""
    last = state.last_round
    if last is None:
        return Decision(False, STATUS_RUNNING, "no rounds yet")

    # 1) Success: validation passed
    if last.validation_passed is True:
        return Decision(True, STATUS_SUCCEEDED, "mod validation passed")

    # 2) Budget: hit round cap
    if state.round_count >= state.max_rounds:
        return Decision(
            True, STATUS_EXHAUSTED,
            f"reached max_rounds ({state.max_rounds}) without passing validation",
        )

    # 3) Stall: same validation failure signature across recent rounds
    if _is_stalled(state, stall_rounds):
        return Decision(
            True, STATUS_STALLED,
            f"no progress across {stall_rounds} rounds (identical validation failure)",
        )

    return Decision(False, STATUS_RUNNING, "continue")


def _is_stalled(state: LoopState, stall_rounds: int) -> bool:
    if state.round_count < stall_rounds:
        return False
    recent = state.rounds[-stall_rounds:]
    signatures = {r.validation_signature for r in recent}
    return len(signatures) == 1 and "" not in signatures


# ---------------------------------------------------------------------------
# Handoff accumulation (failure ratchet)
# ---------------------------------------------------------------------------

def _summarize_round(index: int, final_text: str, validation_passed: bool | None) -> str:
    """Create a compact handoff note from one round's result."""
    text_sample = final_text[:160].replace("\n", " ").strip()
    status = "✅ passed" if validation_passed else ("❌ failed" if validation_passed is False else "⚪ not run")
    return f"Round {index}: {status}. {text_sample}..."


def _accumulate_handoff(
    current_handoff: str, record: RoundRecord, max_chars: int = _HANDOFF_MAX
) -> str:
    """Accumulate handoff notes, keeping the most recent rounds within the budget."""
    new_entry = record.handoff or _summarize_round(
        record.index, "", record.validation_passed
    )
    combined = f"{current_handoff}\n{new_entry}".strip()
    if len(combined) <= max_chars:
        return combined
    # Drop oldest entries until within budget
    entries = combined.split("\n")
    while entries and len("\n".join(entries)) > max_chars:
        entries.pop(0)
    return "\n".join(entries)


def _repeated_failures(state: LoopState) -> int:
    """Count consecutive rounds with the same validation signature."""
    if state.round_count < 2:
        return 0
    last_sig = state.rounds[-1].validation_signature
    if not last_sig:
        return 0
    count = 0
    for r in reversed(state.rounds):
        if r.validation_signature == last_sig:
            count += 1
        else:
            break
    return count - 1  # 0 = first occurrence, 1+ = repeated


# ---------------------------------------------------------------------------
# Loop task builder
# ---------------------------------------------------------------------------

def build_round_prompt(
    goal: str,
    index: int,
    handoff: str,
    last_validation_errors: list[str] | None = None,
    repeat_count: int = 0,
) -> str:
    """Build the prompt for one loop round.

    Args:
        goal: The modding goal (e.g., "Create a focus tree for TAG_XYZ").
        index: Zero-based round index.
        handoff: Accumulated handoff notes from previous rounds.
        last_validation_errors: Validation error messages from the last round.
        repeat_count: How many times the same failure has repeated (0 = first).
    """
    parts = [f"**Goal:** {goal}"]

    if index == 0:
        parts.append(
            "Implement what the goal asks. Create the necessary mod files "
            "(events, focuses, decisions, localisation) and validate them "
            "using `validate_syntax`. Your work is only done when all files "
            "pass validation with zero errors."
        )
    else:
        if handoff:
            parts.append(
                "**Progress so far (previous rounds):**\n" + handoff
            )
        if last_validation_errors:
            parts.append(
                "**Validation is currently FAILING.** Here are the errors:\n"
                + "\n".join(f"- {e}" for e in last_validation_errors[:20])
                + "\n\nDiagnose the failures and fix the mod files so validation passes."
            )

        # Failure ratchet: same error surviving multiple rounds
        if repeat_count >= 1:
            parts.append(
                f"⚠️ **IMPORTANT:** This exact validation failure has now persisted "
                f"through {repeat_count + 1} attempts — your recent changes did NOT "
                f"affect the error. Stop refining the current approach. Take a "
                f"**different implementation strategy.** Consider:\n"
                f"- Rewriting the affected block from scratch\n"
                f"- Using a different scope chain or event structure\n"
                f"- Checking if the error is in a dependency file, not the one you've been editing\n"
                f"- Looking at vanilla examples for the correct pattern"
            )

    parts.append(
        "\nAfter making changes, run `validate_syntax` on each modified file "
        "to confirm it passes."
    )
    return "\n\n".join(parts)
