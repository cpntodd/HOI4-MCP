"""Progressive skill disclosure tool for HOI4 modding skills (GAP-022).

Adapted from DeepCode's Claude Code-compatible SKILL.md system. Skills are
discovered from ``.agents/skills/`` (project-level) and loaded on-demand via
the ``skill`` MCP tool. This keeps the system prompt lean — only skill names
and descriptions are injected; full instructions load when the agent decides
a task matches a skill.

Discovery sources:
- ``<workspace>/.agents/skills/<skill-name>/SKILL.md`` (project skills)
- Each skill has YAML frontmatter with ``name``, ``description``, optional
  ``allowed-tools``, plus a Markdown body of instructions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SKILL_FILE = "SKILL.md"
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_MAX_BODY_CHARS = 16000  # cap to keep context bounded


class SkillError(ValueError):
    """A SKILL.md is malformed (missing frontmatter, name, or description)."""


@dataclass(frozen=True)
class Skill:
    """A discovered HOI4 modding skill."""
    name: str
    description: str
    instructions: str
    allowed_tools: tuple[str, ...] = ()
    directory: str = ""  # skill folder path (for reading bundled resources)
    source: str = ""  # discovery source (e.g., "project:.agents/skills")

    @property
    def summary_line(self) -> str:
        return f"- **{self.name}**: {self.description}"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _coerce_tools(value: Any) -> tuple[str, ...]:
    """Accept ``allowed-tools`` as a list or a comma-separated string."""
    if not value:
        return ()
    if isinstance(value, str):
        return tuple(t.strip() for t in value.split(",") if t.strip())
    if isinstance(value, (list, tuple)):
        return tuple(str(t).strip() for t in value if str(t).strip())
    return ()


def parse_skill_md(path: str | Path, *, source: str = "") -> Skill:
    """Parse one ``SKILL.md`` into a :class:`Skill`.

    Raises :class:`SkillError` on missing frontmatter block or missing
    name/description.
    """
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise SkillError(f"cannot read {p}: {exc}") from exc

    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise SkillError(f"{p}: SKILL.md must open with a YAML frontmatter block")

    import yaml

    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise SkillError(f"{p}: invalid YAML frontmatter: {exc}") from exc
    if not isinstance(meta, dict):
        raise SkillError(f"{p}: frontmatter must be a mapping")

    # ``name`` falls back to the skill folder name (Claude Code convention).
    name = str(meta.get("name") or p.parent.name).strip()
    description = str(meta.get("description") or "").strip()
    if not name:
        raise SkillError(f"{p}: skill needs a name")
    if not description:
        raise SkillError(f"{p}: skill {name!r} needs a description")

    body = text[match.end() :].strip()
    # Cap body length to bound context
    if len(body) > _MAX_BODY_CHARS:
        body = body[:_MAX_BODY_CHARS] + "\n\n[Skill instructions truncated — too large for context window]"

    allowed = _coerce_tools(meta.get("allowed-tools", meta.get("allowed_tools")))
    return Skill(
        name=name,
        description=description,
        instructions=body,
        allowed_tools=allowed,
        directory=str(p.parent),
        source=source,
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class SkillRegistry:
    """The skills available to a session, keyed by name (first-added wins)."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}
        self.errors: list[str] = []  # malformed skills surfaced, not swallowed

    def add(self, skill: Skill) -> bool:
        """Register ``skill`` unless a higher-precedence one holds the name.

        Returns whether it was added.
        """
        if skill.name in self._skills:
            return False
        self._skills[skill.name] = skill
        return True

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def all(self) -> list[Skill]:
        return sorted(self._skills.values(), key=lambda s: s.name)

    def names(self) -> list[str]:
        return sorted(self._skills)

    def __len__(self) -> int:
        return len(self._skills)

    def __bool__(self) -> bool:
        return bool(self._skills)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

# HOI4-MCP project-level skill roots (precedence order).
_PROJECT_ROOTS = (".agents/skills",)


def _iter_skill_files(root: Path) -> list[Path]:
    """Yield each ``<root>/<name>/SKILL.md`` that exists, sorted by folder name."""
    if not root.is_dir():
        return []
    result = []
    for child in sorted(root.iterdir()):
        if child.is_dir():
            skill_file = child / _SKILL_FILE
            if skill_file.is_file():
                result.append(skill_file)
    return result


def discover_skills(workspace: str | Path) -> SkillRegistry:
    """Discover HOI4 modding skills from the project's ``.agents/skills/`` directory.

    Args:
        workspace: The HOI4-MCP project root (contains .agents/skills/).
    """
    registry = SkillRegistry()
    ws = Path(workspace)
    roots: list[tuple[Path, str]] = [
        (ws / rel, f"project:{rel}") for rel in _PROJECT_ROOTS
    ]
    for root, source in roots:
        for skill_file in _iter_skill_files(root):
            try:
                registry.add(parse_skill_md(skill_file, source=source))
            except SkillError as exc:
                registry.errors.append(str(exc))
    return registry


def build_skills_preamble(registry: SkillRegistry) -> str:
    """Build the skills section for the system prompt — names + descriptions only.

    This is injected into the system prompt for progressive disclosure:
    the model sees what skills are available but loads full instructions
    on demand via the ``skill`` tool.
    """
    if not registry:
        return ""
    lines = ["## Available HOI4 Modding Skills", ""]
    for skill in registry.all():
        lines.append(skill.summary_line)
    lines.append("")
    lines.append(
        "Use the `skill` tool to load full instructions for any skill above "
        "when a task matches its domain."
    )
    return "\n".join(lines)


def build_skill_tool_response(name: str, registry: SkillRegistry) -> str:
    """Build the full skill instructions response for the ``skill`` tool.

    Returns the complete instructions with header, or an error/listing message
    if the skill is not found.
    """
    skill = registry.get(name)
    if skill is None:
        available = registry.names()
        if available:
            return (
                f"Skill '{name}' not found. Available skills: {', '.join(available)}"
            )
        return f"Skill '{name}' not found. No skills are currently loaded."

    lines = [
        f"# Skill: {skill.name}",
        f"**Description:** {skill.description}",
    ]
    if skill.allowed_tools:
        lines.append(f"**Allowed tools:** {', '.join(skill.allowed_tools)}")
    if skill.directory:
        lines.append(f"**Directory:** {skill.directory}")
    lines.append("")
    lines.append("## Instructions")
    lines.append("")
    lines.append(skill.instructions)
    return "\n".join(lines)
