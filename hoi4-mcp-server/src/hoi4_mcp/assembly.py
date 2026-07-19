"""Single assembly point for HOI4-MCP agent sessions (GAP-024).

Adapted from DeepCode's ``core/agent_setup.py:build_agent_session()`` pattern.
One function assembles the complete modding agent context — skill registry,
system prompt preamble, tool descriptions — for every consumer (MCP tools,
loop tasks, skill loader). Zero duplication across entry points.

Assembly order:
1. Discover skills from .agents/skills/
2. Build skills preamble for system prompt
3. Build tool capability summary
4. Return complete AgentContext
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .tools.skill_tool import (
    SkillRegistry,
    discover_skills,
    build_skills_preamble,
)


@dataclass
class AgentContext:
    """The fully assembled modding agent context.

    All frontends (MCP tools, loop tasks, CLI) consume this same structure.
    """
    # Skill system
    skill_registry: SkillRegistry = field(default_factory=SkillRegistry)
    skills_preamble: str = ""

    # Tool registry (names + descriptions for system prompt)
    tool_descriptions: list[str] = field(default_factory=list)

    # Workspace info
    workspace_root: str = ""

    @property
    def system_prompt_addendum(self) -> str:
        """The complete addendum to inject into the system prompt.

        Includes skills preamble + tool descriptions + HOI4 modding context.
        """
        parts: list[str] = []

        # Skills section
        if self.skills_preamble:
            parts.append(self.skills_preamble)

        # Tool capabilities
        if self.tool_descriptions:
            parts.append("\n## Available HOI4 Modding Tools\n")
            for desc in self.tool_descriptions:
                parts.append(f"- {desc}")

        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Default HOI4 modding tool descriptions
# ---------------------------------------------------------------------------

HOI4_TOOL_DESCRIPTIONS = [
    "**get_mod_index** — Complete map of the mod's events, focuses, decisions, ideas, characters, scripted effects/triggers, on_actions, and localisation keys.",
    "**search_mod** — Fast text search across all mod files for any ID, tag, modifier, or pattern.",
    "**lookup_vanilla** — Verify any vanilla ID, modifier, focus, event, idea, decision, character, country, or technology against the game database.",
    "**get_next_id** — Find the next available numeric ID for events, focuses, decisions, or characters (prevents silent overwrites).",
    "**check_id_exists** — Verify a specific ID is free before using it.",
    "**validate_syntax** — Validate Clausewitz script or YML localisation for bracket mismatches, missing = signs, and common pitfalls.",
    "**get_latest_errors** — Read and parse the HOI4 error.log into structured, categorized errors with recurring pattern detection.",
    "**generate_province_rgb** — Find unused RGB colors for new map provinces.",
    "**fuzzy_edit** — Edit mod files with 9-strategy fuzzy matching for inconsistent Clausewitz formatting.",
    "**skill** — Load full instructions for any HOI4 modding skill on demand.",
    "**record_mistake** — Record a learned rule from a correction (self or human).",
    "**get_learned_rules** — Retrieve active learned rules for the current modding system (MANDATORY before code generation).",
    "**resolve_mistake** — Mark a learned rule as resolved/inactive.",
    "**export_learned_rules** / **import_learned_rules** — Share learned rules via .jsonl for team use.",
    "**session_review** — End-of-session review: auto-record lessons, detect conflicts, check consistency.",
    "**set_mod_path** — Switch the active mod at runtime without restarting the server.",
]


# ---------------------------------------------------------------------------
# Assembly function
# ---------------------------------------------------------------------------

def build_agent_context(
    workspace: str | Path,
    *,
    discover: bool = True,
) -> AgentContext:
    """Assemble the complete modding agent context.

    This is the SINGLE assembly point — every frontend (MCP server, loop tasks,
    CLI) calls this to get a consistent agent setup.

    Args:
        workspace: Path to the HOI4-MCP project root (contains .agents/skills/).
        discover: If True, scan .agents/skills/ for skill files.
    """
    ctx = AgentContext(workspace_root=str(workspace))

    # 1. Discover skills
    if discover:
        ctx.skill_registry = discover_skills(workspace)
        ctx.skills_preamble = build_skills_preamble(ctx.skill_registry)

    # 2. Tool descriptions
    ctx.tool_descriptions = list(HOI4_TOOL_DESCRIPTIONS)

    return ctx


def build_skill_registry_for_tool(workspace: str | Path) -> SkillRegistry:
    """Build a skill registry specifically for the ``skill`` MCP tool.

    This is a lightweight assembly — skills only, no tool descriptions.
    Used by the MCP server's skill tool handler.
    """
    return discover_skills(workspace)
