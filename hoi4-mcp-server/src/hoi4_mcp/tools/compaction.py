"""Two-tier context compaction for HOI4 modding sessions (GAP-026).

Adapted from DeepCode's AgentRunner context governance. HOI4 agents working
with large wiki pages, game files, and mod indices quickly fill the context
window. This module provides:

Tier 1 — Semantic Compaction: When the estimated token count exceeds 90% of
    the context budget, a separate model call condenses the conversation into
    a handoff summary preserving HOI4-critical state (namespace, IDs used,
    files touched, validation results).

Tier 2 — Drop-Based Fallback: If compaction fails or is skipped, keeps the
    most recent messages within budget by dropping from the head.

Plus micro-compaction: replaces old tool results from "compactable" tools
(read_file, grep, search_mod, get_mod_index, lookup_vanilla) with
``[result omitted]`` markers once they fall outside the recent window.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Trigger summarization when estimated tokens exceed this fraction of budget.
COMPACT_TRIGGER_FRACTION = 0.9

# Characters of recent user messages kept verbatim before the summary.
COMPACT_KEEP_USER_CHARS = 60_000

# How many recent tool results to keep verbatim before micro-compacting.
MICROCOMPACT_KEEP_RECENT = 10

# Minimum characters a tool result must have to be worth compacting.
MICROCOMPACT_MIN_CHARS = 500

# HOI4-specific summarization prompt.
SUMMARIZATION_PROMPT = """You are performing a CONTEXT CHECKPOINT COMPACTION for a Hearts of Iron IV modding session. Create a handoff summary for another agent that will resume this task.

Include:
- **Namespace & IDs Used**: All event namespaces, focus IDs, decision keys, idea keys, character IDs created or referenced.
- **Files Touched**: Which mod files were created or edited (with paths relative to mod root).
- **Current Progress**: What has been completed (focus tree branches, event chains, decisions, localisation).
- **Validation Status**: Latest syntax validation results — what passed, what errors remain.
- **Key Decisions**: Why certain design choices were made (e.g., "used hidden event for timing because on_action didn't fire reliably").
- **Next Steps**: What remains to be done, in priority order.
- **Critical Context**: Any vanilla IDs, modifier names, or game mechanics the next agent must know.

Be concise, structured, and focused on helping the next agent seamlessly continue the HOI4 modding work."""

SUMMARY_PREFIX = (
    "An earlier agent worked on this HOI4 modding task and produced the summary "
    "below of its progress and the state of the tools it used. Build on this work "
    "and avoid duplicating it. Here is the summary:"
)

# Tools whose old results can be safely replaced with [result omitted]
# because re-reading is cheap and the content is reference data, not state.
COMPACTABLE_TOOLS = frozenset({
    "read_file",
    "grep_search",
    "file_search",
    "search_mod",
    "get_mod_index",
    "lookup_vanilla",
    "get_latest_errors",
})

# Tools whose results should NEVER be compacted — they contain critical state.
NON_COMPACTABLE_TOOLS = frozenset({
    "validate_syntax",
    "record_mistake",
    "get_learned_rules",
    "get_next_id",
    "check_id_exists",
})


# ---------------------------------------------------------------------------
# Token estimation (simple character-based heuristic)
# ---------------------------------------------------------------------------

def estimate_tokens(text: str) -> int:
    """Rough token count — ~4 chars per token for English text.

    For precise counts, the actual model tokenizer should be used.
    This is a budget-check heuristic, not a billing tool.
    """
    return len(text) // 4


def estimate_message_tokens(message: dict) -> int:
    """Estimate tokens for one message dict (role + content)."""
    content = message.get("content", "")
    if isinstance(content, list):
        # Multi-part content (text blocks + tool calls)
        total = 0
        for part in content:
            if isinstance(part, dict):
                total += estimate_tokens(str(part.get("text", "")))
            else:
                total += estimate_tokens(str(part))
        return total
    return estimate_tokens(str(content)) + 4  # ~4 tokens for role overhead


def estimate_total_tokens(messages: list[dict]) -> int:
    """Estimate total tokens for a message list."""
    return sum(estimate_message_tokens(m) for m in messages)


# ---------------------------------------------------------------------------
# Micro-compaction: drop old tool results from compactable tools
# ---------------------------------------------------------------------------

def microcompact_messages(
    messages: list[dict],
    *,
    keep_recent: int = MICROCOMPACT_KEEP_RECENT,
    min_chars: int = MICROCOMPACT_MIN_CHARS,
) -> list[dict]:
    """Replace old tool results from compactable tools with ``[result omitted]``.

    Only affects tool results older than the ``keep_recent`` most recent tools,
    and only for tools in ``COMPACTABLE_TOOLS``. Non-compactable tool results
    are always preserved.
    """
    if len(messages) <= keep_recent:
        return messages

    result = list(messages)
    tool_indices = [
        i for i, m in enumerate(result)
        if m.get("role") == "tool" and m.get("name")
    ]

    if len(tool_indices) <= keep_recent:
        return result

    # The most recent `keep_recent` tool messages are preserved verbatim.
    compactable_indices = tool_indices[:-keep_recent]

    for idx in compactable_indices:
        msg = result[idx]
        tool_name = msg.get("name", "")
        if tool_name in NON_COMPACTABLE_TOOLS:
            continue
        if tool_name in COMPACTABLE_TOOLS:
            content = msg.get("content", "")
            if isinstance(content, str) and len(content) > min_chars:
                result[idx] = {
                    **msg,
                    "content": f"[Tool result omitted — {tool_name} output was {len(content)} chars]",
                }

    return result


# ---------------------------------------------------------------------------
# Tier 2: Drop-based history snipping
# ---------------------------------------------------------------------------

def snip_history(
    messages: list[dict],
    budget_tokens: int,
    *,
    safety_buffer: int = 1024,
) -> list[dict]:
    """Keep the most recent messages that fit within ``budget_tokens``.

    Always preserves system messages. Drops from the head (oldest first).
    Ensures the first kept non-system message is a ``user`` role.
    """
    if not messages:
        return messages

    system_msgs = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]

    system_tokens = estimate_total_tokens(system_msgs)
    available = budget_tokens - system_tokens - safety_buffer

    if available <= 0:
        # Extreme: keep only system messages + last 2 non-system
        return system_msgs + non_system[-2:]

    # Walk backward, keeping messages until budget exhausted
    kept: list[dict] = []
    remaining = available

    for msg in reversed(non_system):
        tokens = estimate_message_tokens(msg)
        if tokens <= remaining:
            kept.insert(0, msg)
            remaining -= tokens
        else:
            break

    # Ensure first kept non-system message is a user message
    # (models typically need user→assistant alternation)
    if kept and kept[0].get("role") != "user":
        # Find the nearest preceding user message in the original list
        first_kept_idx = non_system.index(kept[0])
        for i in range(first_kept_idx - 1, -1, -1):
            if non_system[i].get("role") == "user":
                kept.insert(0, non_system[i])
                break

    return system_msgs + kept


# ---------------------------------------------------------------------------
# Tier 1: Compaction summary helper
# ---------------------------------------------------------------------------

def build_compaction_prompt(
    messages: list[dict],
    keep_user_chars: int = COMPACT_KEEP_USER_CHARS,
) -> tuple[str, list[dict]]:
    """Build the summarization call and the compacted message list.

    Returns:
        (summarization_prompt, compacted_messages) where compacted_messages
        retains system messages + recent user messages verbatim + the summary
        injected as a final user message.
    """
    system_msgs = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]

    # Collect recent user messages to keep verbatim
    kept_user_chars = 0
    recent_start = len(non_system)
    for i in range(len(non_system) - 1, -1, -1):
        msg = non_system[i]
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                str(p.get("text", "")) for p in content if isinstance(p, dict)
            )
        kept_user_chars += len(str(content))
        recent_start = i
        if kept_user_chars >= keep_user_chars:
            break

    recent_msgs = non_system[recent_start:]

    # Build compacted message list
    compacted = list(system_msgs)
    compacted.append({
        "role": "user",
        "content": SUMMARY_PREFIX,
    })
    compacted.extend(recent_msgs)

    return SUMMARIZATION_PROMPT, compacted


def needs_compaction(
    messages: list[dict],
    context_window_tokens: int,
    *,
    trigger_fraction: float = COMPACT_TRIGGER_FRACTION,
) -> bool:
    """Check whether semantic compaction should be triggered.

    Returns True when estimated tokens exceed ``trigger_fraction`` of the
    context window AND there are at least 4 non-system messages (enough
    conversation history to be worth summarizing).
    """
    if not context_window_tokens or context_window_tokens <= 0:
        return False

    total = estimate_total_tokens(messages)
    if total < context_window_tokens * trigger_fraction:
        return False

    non_system = [m for m in messages if m.get("role") != "system"]
    return len(non_system) >= 4
