"""
HOI4 MCP Server — Model Context Protocol server for Hearts of Iron IV modding.

Exposes tools and resources that give AI coding assistants deterministic access
to mod structure, vanilla game data, syntax validation, and error logs.

Usage:
    hoi4-mcp --mod-path /path/to/your/mod
    hoi4-mcp --mod-path /path/to/mod --vanilla-db ~/.hoi4_mcp/vanilla.db
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from mcp.server import FastMCP
from mcp.types import TextContent

from .clausewitz.parser import parse_file as clausewitz_parse_file
from .clausewitz.validator import (
    validate_clausewitz,
    validate_localisation,
    extract_loc_keys,
)
from .tools.indexer import ModIndexer
from .tools.id_manager import IDManager
from .tools.error_log import error_log_summary, parse_error_log, find_error_log
from .db.vanilla_index import VanillaLookup, VanillaDBBuilder
from .learning import (
    LearnedRulesDB,
    detect_recurring_patterns,
    export_to_file as learning_export_to_file,
    import_from_file as learning_import_from_file,
    format_rules_block,
    validate_rule_fields,
    seed_if_empty,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _structured_error(error_code: str, message: str, help: str = "") -> str:
    """Consistent structured error format for all tool error paths (GAP-002)."""
    obj: dict[str, Any] = {"success": False, "error_code": error_code, "message": message}
    if help:
        obj["help"] = help
    return json.dumps(obj, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class ServerConfig:
    """Runtime configuration for the MCP server."""

    def __init__(
        self,
        mod_path: str | None = None,
        vanilla_path: str | None = None,
        vanilla_db_path: str | None = None,
        auto_detect_mod: bool = False,
    ):
        self.vanilla_path = Path(vanilla_path) if vanilla_path else None
        self.vanilla_db_path = (
            Path(vanilla_db_path)
            if vanilla_db_path
            else Path.home() / ".hoi4_mcp" / "vanilla.db"
        )

        # Auto-detect mod from workspace if requested and no explicit path
        if auto_detect_mod and not mod_path:
            detected = self._auto_detect_mod()
            if detected:
                mod_path = str(detected)

        self.mod_path = Path(mod_path) if mod_path else None

        # Validate
        if self.mod_path and not self.mod_path.exists():
            raise FileNotFoundError(f"Mod path not found: {self.mod_path}")

    @staticmethod
    def _auto_detect_mod() -> Path | None:
        """Scan CWD and parent directories for a HOI4 mod descriptor file."""
        cwd = Path.cwd()
        # Check CWD and up to 3 parent levels
        for directory in [cwd] + list(cwd.parents)[:3]:
            # Check for descriptor.mod or *.mod files
            descriptor = directory / "descriptor.mod"
            if descriptor.exists():
                return directory
            # Check for .mod files (Steam Workshop style)
            mod_files = list(directory.glob("*.mod"))
            if mod_files:
                return directory
        return None

    def set_mod_path(self, path: str | Path | None) -> bool:
        """Update the active mod path at runtime. Returns True if successful."""
        if path is None:
            self.mod_path = None
            return True
        p = Path(path)
        if not p.exists():
            return False
        self.mod_path = p
        return True

    @property
    def has_mod(self) -> bool:
        return self.mod_path is not None and self.mod_path.exists()

    @property
    def has_vanilla_db(self) -> bool:
        return self.vanilla_db_path.exists()


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

def create_hoi4_server(config: ServerConfig) -> FastMCP:
    """Create and configure the HOI4 MCP server."""
    
    server = FastMCP("hoi4-modding-server")

    # Mutable state so set_mod_path can dynamically switch mods (GAP-004)
    _state: dict[str, Any] = {
        "mod_path": config.mod_path,
    }

    def _has_mod() -> bool:
        return _state["mod_path"] is not None and _state["mod_path"].exists()

    # Lazy-initialized tools
    _mod_index_cache: dict[str, Any] | None = None
    _vanilla_lookup: VanillaLookup | None = None
    _id_manager: IDManager | None = None

    def _invalidate_mod_caches() -> None:
        """Invalidate all mod-dependent caches when mod path changes."""
        nonlocal _mod_index_cache, _id_manager
        _mod_index_cache = None
        _id_manager = None

    def _get_mod_index() -> dict[str, Any]:
        nonlocal _mod_index_cache
        if _mod_index_cache is None and _has_mod():
            indexer = ModIndexer(_state["mod_path"])
            _mod_index_cache = json.loads(indexer.build_index_json())
        return _mod_index_cache or {}

    def _get_vanilla_lookup() -> VanillaLookup:
        nonlocal _vanilla_lookup
        if _vanilla_lookup is None:
            _vanilla_lookup = VanillaLookup(config.vanilla_db_path)
        return _vanilla_lookup

    def _get_id_manager() -> IDManager:
        nonlocal _id_manager
        if _id_manager is None and _has_mod():
            _id_manager = IDManager(_state["mod_path"])
        return _id_manager

    # Lazy-initialized learning system (GAP-000)
    _learning_db: LearnedRulesDB | None = None

    def _get_learning_db() -> LearnedRulesDB:
        nonlocal _learning_db
        if _learning_db is None:
            _learning_db = LearnedRulesDB()
            _learning_db.ensure_schema()
            seed_if_empty(_learning_db)
        return _learning_db

    # -----------------------------------------------------------------------
    # Tool: get_mod_index
    # -----------------------------------------------------------------------
    @server.tool()
    async def get_mod_index(
        summary_only: bool = False,
        refresh: bool = False,
        category: str = "",
    ) -> list[TextContent]:
        """Returns a comprehensive JSON index of the active HOI4 mod.

        This is the primary tool for understanding the mod's structure in one call.
        Returns ALL namespaces, event IDs, focus IDs, decision keys, idea keys,
        character IDs, scripted effects/triggers, on_actions, and localisation keys.

        Use this at the START of any modding session to get a complete map of the mod.
        Saves 5-10 tool calls and thousands of tokens vs. searching individual files.

        Args:
            summary_only: If true, returns only counts and namespaces (no full index).
                          Use when you just need a quick overview or after edits.
            refresh: If true, rebuilds the index from disk (use after editing mod files).
            category: Optional — return only one section: events, focuses, focus_trees,
                      decisions, ideas, characters, technologies, scripted_effects,
                      scripted_triggers, on_actions, localisation, namespaces.
                      Empty = all sections (GAP-003).

        Requires: --mod-path to be set when launching the server.
        """
        nonlocal _mod_index_cache

        if not _has_mod():
            return [TextContent(
                type="text",
                text="Error: No mod path configured. Launch with --mod-path, set HOI4_MOD_PATH env var, or use set_mod_path tool."
            )]

        # Invalidate cache if requested
        if refresh:
            _invalidate_mod_caches()

        index = _get_mod_index()

        # GAP-003: Category filter for large mods
        _valid_categories = {
            "events", "focuses", "focus_trees", "decisions", "ideas",
            "characters", "technologies", "scripted_effects", "scripted_triggers",
            "on_actions", "localisation", "namespaces",
        }
        if category and category not in _valid_categories:
            return [TextContent(
                type="text",
                text=f"Error: Invalid category '{category}'. Use one of: {', '.join(sorted(_valid_categories))}"
            )]

        if summary_only:
            summary = {
                "mod_name": index.get("mod_name", "unknown"),
                "namespaces": index.get("namespaces", []),
                "counts": {
                    "events": len(index.get("events", {})),
                    "focuses": len(index.get("focuses", {})),
                    "focus_trees": len(index.get("focus_trees", {})),
                    "decisions": len(index.get("decisions", {})),
                    "ideas": len(index.get("ideas", {})),
                    "characters": len(index.get("characters", {})),
                    "scripted_effects": len(index.get("scripted_effects", {})),
                    "scripted_triggers": len(index.get("scripted_triggers", {})),
                    "on_actions": len(index.get("on_actions", {})),
                    "localisation_keys": index.get("localisation_key_count", 0),
                    "files_indexed": index.get("files_indexed", 0),
                    "errors": len(index.get("errors", [])),
                },
            }
            return [TextContent(
                type="text",
                text=json.dumps(summary, indent=2, default=str)
            )]

        # Category-filtered response (GAP-003)
        if category:
            if category == "localisation":
                result = {
                    "mod_name": index.get("mod_name", "unknown"),
                    "category": category,
                    "localisation_keys": sorted(index.get("localisation_keys", [])),
                    "localisation_key_count": index.get("localisation_key_count", 0),
                }
            elif category == "namespaces":
                result = {
                    "mod_name": index.get("mod_name", "unknown"),
                    "category": category,
                    "namespaces": index.get("namespaces", []),
                }
            else:
                result = {
                    "mod_name": index.get("mod_name", "unknown"),
                    "category": category,
                    "data": index.get(category, {}),
                    "count": len(index.get(category, {})),
                }
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, default=str)
            )]

        # Full index response
        summary = {
            "mod_name": index.get("mod_name", "unknown"),
            "namespaces": index.get("namespaces", []),
            "counts": {
                "events": len(index.get("events", {})),
                "focuses": len(index.get("focuses", {})),
                "focus_trees": len(index.get("focus_trees", {})),
                "decisions": len(index.get("decisions", {})),
                "ideas": len(index.get("ideas", {})),
                "characters": len(index.get("characters", {})),
                "scripted_effects": len(index.get("scripted_effects", {})),
                "scripted_triggers": len(index.get("scripted_triggers", {})),
                "on_actions": len(index.get("on_actions", {})),
                "localisation_keys": index.get("localisation_key_count", 0),
                "files_indexed": index.get("files_indexed", 0),
                "errors": len(index.get("errors", [])),
            },
            "full_index": index,
        }
        return [TextContent(
            type="text",
            text=json.dumps(summary, indent=2, default=str)
        )]

    # -----------------------------------------------------------------------
    # Tool: get_next_id
    # -----------------------------------------------------------------------
    @server.tool()
    async def get_next_id(
        id_type: str = "event",
        namespace: str = "",
        prefix: str = "",
    ) -> list[TextContent]:
        """Finds the next available numeric ID to prevent collisions.

        In HOI4, duplicate IDs silently overwrite — this tool eliminates that risk
        by scanning existing files and returning the highest number + 1.

        Args:
            id_type: One of 'event', 'focus', 'decision', 'character'.
            namespace: For events — the namespace (e.g., 'mymod'). Required for event type.
            prefix: For focuses — an optional prefix to filter (e.g., 'mymod_').
        """
        if not _has_mod():
            return [TextContent(
                type="text",
                text="Error: No mod path configured."
            )]

        mgr = _get_id_manager()

        if id_type == "event":
            if not namespace:
                return [TextContent(
                    type="text",
                    text="Error: 'namespace' is required for event ID lookup."
                )]
            next_id = mgr.get_next_event_id(namespace)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "type": "event",
                    "namespace": namespace,
                    "next_id": next_id,
                    "suggested": f"{namespace}.{next_id}",
                }, indent=2)
            )]

        elif id_type == "focus":
            next_id = mgr.get_next_focus_id(prefix)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "type": "focus",
                    "prefix": prefix,
                    "next_numeric": next_id,
                    "suggested": f"{prefix}_{next_id}" if prefix else str(next_id),
                }, indent=2)
            )]

        elif id_type == "decision":
            next_id = mgr.get_next_decision_id()
            return [TextContent(
                type="text",
                text=json.dumps({
                    "type": "decision",
                    "next_numeric": next_id,
                }, indent=2)
            )]

        elif id_type == "character":
            next_id = mgr.get_next_character_id()
            return [TextContent(
                type="text",
                text=json.dumps({
                    "type": "character",
                    "next_numeric": next_id,
                }, indent=2)
            )]

        else:
            return [TextContent(
                type="text",
                text=f"Error: Unknown id_type '{id_type}'. Use 'event', 'focus', 'decision', or 'character'."
            )]

    # -----------------------------------------------------------------------
    # Tool: check_id_exists
    # -----------------------------------------------------------------------
    @server.tool()
    async def check_id_exists(
        id_value: str = "",
        id_type: str = "any",
    ) -> list[TextContent]:
        """Check if a specific ID already exists in the mod (prevents silent overwrites).

        Args:
            id_value: The exact ID string to check (e.g., 'mymod.1', 'my_focus_name').
            id_type: Scope to search — 'event', 'focus', 'decision', 'idea', 'character', or 'any'.
        """
        if not _has_mod():
            return [TextContent(
                type="text",
                text="Error: No mod path configured."
            )]
        if not id_value:
            return [TextContent(
                type="text",
                text="Error: 'id_value' is required."
            )]

        mgr = _get_id_manager()
        result = mgr.check_id_exists(id_value, id_type)
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]

    # -----------------------------------------------------------------------
    # Tool: search_mod
    # -----------------------------------------------------------------------
    @server.tool()
    async def search_mod(
        query: str = "",
        subdir: str = "",
        file_pattern: str = "*.txt",
        max_results: int = 30,
    ) -> list[TextContent]:
        """Fast text search across mod files for arbitrary patterns.

        Searches the mod directory for files containing the query string.
        Use this to find where a specific ID, tag, modifier, or pattern is used
        across the entire mod — without needing workspace grep/search tools.

        Args:
            query: The text pattern to search for (case-insensitive).
            subdir: Optional subdirectory to limit search (e.g., 'events', 'common/national_focus').
            file_pattern: File glob pattern (default: '*.txt'). Use '*.yml' for localisation.
            max_results: Maximum results to return (default: 30).
        """
        if not _has_mod():
            return [TextContent(
                type="text",
                text="Error: No mod path configured."
            )]
        if not query:
            return [TextContent(
                type="text",
                text="Error: 'query' parameter is required."
            )]

        import fnmatch

        search_root = _state["mod_path"] / subdir if subdir else _state["mod_path"]
        if not search_root.exists():
            return [TextContent(
                type="text",
                text=f"Error: Directory not found: {search_root}"
            )]

        results = []
        query_lower = query.lower()
        for filepath in sorted(search_root.rglob(file_pattern)):
            try:
                text = filepath.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            if query_lower in text.lower():
                # Find line numbers of matches
                lines = text.split("\n")
                matching_lines = []
                for i, line in enumerate(lines, 1):
                    if query_lower in line.lower():
                        matching_lines.append({
                            "line": i,
                            "text": line.strip()[:200],  # truncate long lines
                        })
                        if len(matching_lines) >= 5:
                            break

                rel_path = str(filepath.relative_to(_state["mod_path"]))
                results.append({
                    "file": rel_path,
                    "match_count": sum(1 for l in lines if query_lower in l.lower()),
                    "first_matches": matching_lines,
                })

                if len(results) >= max_results:
                    break

        return [TextContent(
            type="text",
            text=json.dumps({
                "query": query,
                "subdir": subdir or "(mod root)",
                "total_files_matched": len(results),
                "results": results,
            }, indent=2)
        )]

    # -----------------------------------------------------------------------
    # Tool: validate_syntax
    # -----------------------------------------------------------------------
    @server.tool()
    async def validate_syntax(
        text: str = "",
        file_type: str = "clausewitz",
    ) -> list[TextContent]:
        """Validates Clausewitz script or localisation YML for syntax errors.

        Checks bracket { } matching, missing = signs, YML formatting, and
        common pitfalls like 'hide_window' without 'is_triggered_only'.

        Use this BEFORE the user launches the game to catch errors instantly.

        Args:
            text: The complete file content to validate.
            file_type: 'clausewitz' for .txt files, 'localisation' for .yml files.
        """
        if not text:
            return [TextContent(
                type="text",
                text="Error: 'text' parameter is required — provide the file content to validate."
            )]

        if file_type == "clausewitz":
            result = validate_clausewitz(text)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "is_valid": result.is_valid,
                    "error_count": len(result.errors),
                    "warning_count": len(result.warnings),
                    "errors": [
                        {"line": e.line, "col": e.col, "message": e.message}
                        for e in result.errors
                    ],
                    "warnings": [
                        {"line": w.line, "col": w.col, "message": w.message}
                        for w in result.warnings
                    ],
                }, indent=2)
            )]

        elif file_type == "localisation":
            result = validate_localisation(text)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "is_valid": result.is_valid,
                    "language": result.language,
                    "entry_count": result.entry_count,
                    "error_count": len(result.errors),
                    "warning_count": len(result.warnings),
                    "errors": [
                        {"line": e.line, "col": e.col, "message": e.message}
                        for e in result.errors
                    ],
                    "warnings": [
                        {"line": w.line, "col": w.col, "message": w.message}
                        for w in result.warnings
                    ],
                }, indent=2)
            )]

        else:
            return [TextContent(
                type="text",
                text=f"Error: Unknown file_type '{file_type}'. Use 'clausewitz' or 'localisation'."
            )]

    # -----------------------------------------------------------------------
    # Tool: get_latest_errors
    # -----------------------------------------------------------------------
    @server.tool()
    async def get_latest_errors(
        log_path: str = "",
        tail_lines: int = 200,
        detect_recurring: bool = False,
    ) -> list[TextContent]:
        """Reads and parses the HOI4 error.log file into structured JSON.

        Categorizes errors by type (unexpected token, duplicate ID, invalid scope,
        missing localisation, missing texture, etc.) and groups by file.

        Args:
            log_path: Path to error.log. If empty, auto-detects based on OS.
            tail_lines: Number of recent lines to parse (default: 200).
            detect_recurring: If true, also analyzes for recurring patterns
                (3+ occurrences of the same error signature) and returns
                suggested learned rules. Present these to the human for
                confirmation before recording via record_mistake().
        """
        path = Path(log_path) if log_path else None
        summary = error_log_summary(path)

        response: dict[str, Any] = dict(summary) if isinstance(summary, dict) else {"errors": []}

        if detect_recurring and response.get("errors"):
            suggestions = detect_recurring_patterns(response["errors"], threshold=3)
            if suggestions:
                response["recurring_patterns"] = suggestions
                response["recurring_notice"] = (
                    f"Found {len(suggestions)} recurring error pattern(s). "
                    "These are SUGGESTIONS — present to the human for confirmation "
                    "before recording as learned rules via record_mistake()."
                )

        return [TextContent(
            type="text",
            text=json.dumps(response, indent=2, default=str)
        )]

    # -----------------------------------------------------------------------
    # Tool: lookup_vanilla
    # -----------------------------------------------------------------------
    @server.tool()
    async def lookup_vanilla(
        query_type: str = "focus",
        query: str = "",
        search: str = "",
    ) -> list[TextContent]:
        """Queries the vanilla HOI4 database for exact game data.

        Prevents AI hallucinations about vanilla IDs, prerequisites, modifiers, etc.
        Requires the vanilla database to be built first (run 'index-vanilla').

        Args:
            query_type: One of 'focus', 'event', 'idea', 'decision', 'character', 'technology', 'country', 'modifier'.
            query: Exact ID to look up (e.g., 'GER_danzig_or_war').
            search: Substring search across IDs (e.g., 'danzig' to find all matching focuses).
        """
        try:
            lookup = _get_vanilla_lookup()
        except FileNotFoundError as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": str(e),
                    "help": "Run: index-vanilla --vanilla-path /path/to/hoi4/install"
                }, indent=2)
            )]

        # Search mode
        if search:
            results = []
            if query_type == "focus":
                results = lookup.search_focuses(search)
            elif query_type == "event":
                results = lookup.search_events(search)
            elif query_type == "idea":
                results = lookup.search_ideas(search)
            elif query_type == "decision":
                results = lookup.search_decisions(search)
            elif query_type == "character":
                results = lookup.search_characters(search)
            elif query_type == "modifier":
                results = lookup.search_modifiers(search)
            else:
                return [TextContent(
                    type="text",
                    text=f"Error: Search not supported for type '{query_type}'. Use 'focus', 'event', 'idea', 'decision', 'character', or 'modifier'."
                )]
            return [TextContent(
                type="text",
                text=json.dumps({"search": search, "type": query_type, "results": results}, indent=2)
            )]

        # Exact lookup mode
        if not query:
            return [TextContent(
                type="text",
                text="Error: Provide 'query' for exact lookup or 'search' for substring search."
            )]

        result = None
        if query_type == "focus":
            result = lookup.lookup_focus(query)
        elif query_type == "event":
            result = lookup.lookup_event(query)
        elif query_type == "idea":
            result = lookup.lookup_idea(query)
        elif query_type == "decision":
            result = lookup.lookup_decision(query)
        elif query_type == "character":
            result = lookup.lookup_character(query)
        elif query_type == "technology":
            result = lookup.lookup_technology(query)
        elif query_type == "country":
            result = lookup.lookup_country(query)
        elif query_type == "modifier":
            result = lookup.lookup_modifier(query)
        else:
            return [TextContent(
                type="text",
                text=f"Error: Unknown query_type '{query_type}'. Use 'focus', 'event', 'idea', 'decision', 'character', 'technology', 'country', or 'modifier'."
            )]

        if result is None:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "found": False,
                    "query": query,
                    "type": query_type,
                    "message": f"No vanilla {query_type} found with ID '{query}'."
                }, indent=2)
            )]

        return [TextContent(
            type="text",
            text=json.dumps({"found": True, "type": query_type, "data": result}, indent=2, default=str)
        )]

    # -----------------------------------------------------------------------
    # Tool: generate_province_rgb
    # -----------------------------------------------------------------------
    @server.tool()
    async def generate_province_rgb(
        definition_csv_path: str = "",
    ) -> list[TextContent]:
        """Reads map/definition.csv and returns an unused RGB color for new provinces.

        Prevents the common map modding error of duplicate RGB values (which causes
        silent province overwrites).

        Args:
            definition_csv_path: Path to definition.csv. If empty, looks in the mod's map/ dir.
        """
        if definition_csv_path:
            csv_path = Path(definition_csv_path)
        elif _has_mod():
            csv_path = _state["mod_path"] / "map" / "definition.csv"
        else:
            return [TextContent(
                type="text",
                text="Error: No definition.csv path provided and no mod path configured."
            )]

        if not csv_path.exists():
            return [TextContent(
                type="text",
                text=f"Error: definition.csv not found at {csv_path}"
            )]

        # Parse existing RGB values
        used_colors: set[tuple[int, int, int]] = set()
        max_province_id = 0
        try:
            text = csv_path.read_text(encoding="utf-8")
            for line in text.strip().split("\n"):
                parts = line.strip().split(";")
                if len(parts) >= 4:
                    try:
                        r, g, b = int(parts[1]), int(parts[2]), int(parts[3])
                        used_colors.add((r, g, b))
                        pid = int(parts[0])
                        if pid > max_province_id:
                            max_province_id = pid
                    except ValueError:
                        pass
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error reading definition.csv: {e}"
            )]

        # Find an unused color
        # Strategy: start from a base and vary hues systematically
        import colorsys
        candidates = []
        for hue in range(0, 360, 13):  # ~27 distinct hues
            for sat in [180, 220, 255]:
                for val in [180, 220, 255]:
                    r, g, b = colorsys.hsv_to_rgb(hue / 360, sat / 255, val / 255)
                    rgb = (int(r * 255), int(g * 255), int(b * 255))
                    if rgb not in used_colors:
                        candidates.append(rgb)
                        if len(candidates) >= 5:
                            break
                    if len(candidates) >= 5:
                        break
                if len(candidates) >= 5:
                    break

        if not candidates:
            # Fallback: sequential scan
            for r in range(256):
                for g in range(256):
                    for b in range(256):
                        if (r, g, b) not in used_colors:
                            candidates.append((r, g, b))
                            break
                    if candidates:
                        break
                if candidates:
                    break

        return [TextContent(
            type="text",
            text=json.dumps({
                "used_colors_count": len(used_colors),
                "max_province_id": max_province_id,
                "suggested_next_province_id": max_province_id + 1,
                "suggested_colors": [
                    {"r": c[0], "g": c[1], "b": c[2],
                     "hex": f"#{c[0]:02X}{c[1]:02X}{c[2]:02X}"}
                    for c in candidates[:5]
                ],
            }, indent=2)
        )]

    # -----------------------------------------------------------------------
    # Learning System Tools (GAP-000)
    # -----------------------------------------------------------------------

    @server.tool()
    async def record_mistake(
        category: str,
        context: str,
        context_tags: str,
        pattern: str,
        correction: str,
        severity: str = "error",
        source: str = "agent_self_correction",
        file_path: str = "",
        line_range: str = "",
    ) -> list[TextContent]:
        """Record a learned rule from a caught mistake.

        Called when the agent fixes its own error, or when a human corrects it.
        The rule is stored in the learning database and will be enforced in
        future sessions via get_learned_rules.

        Args:
            category: One of: syntax, logic, design, scope, localisation, id_collision, convention, performance
            context: Human-readable description of when this applies (e.g., "Events with MTTH blocks")
            context_tags: Comma-separated tags for filtering (e.g., "events,mtth,triggers")
            pattern: What the mistake looks like — the ANTI-PATTERN
            correction: What to do instead
            severity: error (hard block), warning (strong suggestion), style (convention)
            source: agent_self_correction, human_correction, game_log, or validation
            file_path: Optional — where the mistake occurred
            line_range: Optional — which lines (e.g., "45-52")
        """
        # Validate
        errors = validate_rule_fields(
            category=category, severity=severity, source=source,
            pattern=pattern, correction=correction, context=context,
        )
        if errors:
            return [TextContent(
                type="text",
                text=_structured_error(
                    "INVALID_RULE_FIELDS",
                    "Rule validation failed",
                    help="; ".join(errors),
                ),
            )]

        db = _get_learning_db()
        try:
            rule = db.record(
                category=category, context=context, context_tags=context_tags,
                pattern=pattern, correction=correction, severity=severity,
                source=source, file_path=file_path, line_range=line_range,
            )
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "rule_id": rule["id"],
                    "is_new": rule["occurrence_count"] == 1,
                    "occurrence_count": rule["occurrence_count"],
                    "message": f"Recorded as {rule['id']}."
                        + (" This matched an existing rule — count incremented." if rule["occurrence_count"] > 1 else ""),
                }, ensure_ascii=False),
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=_structured_error("RECORD_FAILED", str(e)),
            )]

    @server.tool()
    async def get_learned_rules(
        context_tags: str = "",
        category: str = "",
        severity: str = "",
        include_resolved: bool = False,
    ) -> list[TextContent]:
        """Retrieve active learned rules, filtered by context.

        The agent MUST call this before generating any Clausewitz code (Phase 0).
        Returns rules formatted with severity markers (⛔/⚠️/💡) and anti-pattern/correction pairs.

        Args:
            context_tags: Comma-separated tags to filter by (e.g., "events,mtth"). Matches ANY tag.
            category: Optional exact category filter
            severity: Optional exact severity filter
            include_resolved: If true, include resolved/inactive rules
        """
        db = _get_learning_db()
        try:
            rules = db.query(
                context_tags=context_tags,
                category=category,
                severity=severity,
                include_resolved=include_resolved,
            )
            if not rules:
                return [TextContent(type="text", text="No active learned rules match this context.")]
            return [TextContent(type="text", text=format_rules_block(rules))]
        except Exception as e:
            return [TextContent(
                type="text",
                text=_structured_error("QUERY_FAILED", str(e)),
            )]

    @server.tool()
    async def resolve_mistake(
        rule_id: str,
        note: str = "",
        superseded_by: str = "",
    ) -> list[TextContent]:
        """Mark a learned rule as resolved/inactive.

        Use when a rule is no longer relevant (game patch, design change, etc.)

        Args:
            rule_id: The rule ID to resolve (e.g., "LR-0001")
            note: Why it's being resolved
            superseded_by: Optional ID of a new rule that replaces this one
        """
        if not rule_id.strip():
            return [TextContent(
                type="text",
                text=_structured_error("MISSING_RULE_ID", "rule_id is required"),
            )]

        db = _get_learning_db()
        try:
            rule = db.resolve(rule_id=rule_id.strip(), note=note, superseded_by=superseded_by)
            if rule is None:
                return [TextContent(
                    type="text",
                    text=_structured_error("RULE_NOT_FOUND", f"Rule '{rule_id}' does not exist."),
                )]
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "rule_id": rule_id,
                    "status": "resolved",
                    "message": f"Rule {rule_id} marked as resolved." + (f" Note: {note}" if note else ""),
                }, ensure_ascii=False),
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=_structured_error("RESOLVE_FAILED", str(e)),
            )]

    @server.tool()
    async def export_learned_rules(
        format: str = "json",
        include_resolved: bool = False,
    ) -> list[TextContent]:
        """Export all learned rules in a structured format.

        JSON output is .jsonl (one object per line) — suitable for saving as
        .hoi4-mcp-learned-rules.jsonl and committing to the mod repository
        for team sharing. Markdown output is human-readable for review.

        Args:
            format: "json" (jsonl) or "markdown" (human-readable review format)
            include_resolved: Include resolved/inactive rules in export
        """
        if format not in ("json", "markdown"):
            return [TextContent(
                type="text",
                text=_structured_error("INVALID_FORMAT", "format must be 'json' or 'markdown'"),
            )]

        db = _get_learning_db()
        try:
            result = learning_export_to_file(
                db, format=format, include_resolved=include_resolved,
            )
            stats = db.stats()
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "path": result["path"],
                    "count": result["count"],
                    "format": result["format"],
                    "db_stats": stats,
                    "message": (
                        f"Exported {result['count']} rules to {result['path']}.\n"
                        f"Commit this file to your mod repo to share rules with your team.\n"
                        f"DB stats: {stats['active']} active, {stats['resolved']} resolved, {stats['total']} total."
                    ),
                }, ensure_ascii=False),
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=_structured_error("EXPORT_FAILED", str(e)),
            )]

    @server.tool()
    async def import_learned_rules(
        input_path: str = "",
    ) -> list[TextContent]:
        """Import learned rules from a .jsonl file.

        Use on fresh setups to load rules shared via the mod repository.
        Skips rules whose IDs already exist in the database.

        Args:
            input_path: Path to the .hoi4-mcp-learned-rules.jsonl file
        """
        if not input_path.strip():
            return [TextContent(
                type="text",
                text=_structured_error("MISSING_PATH", "input_path is required"),
            )]

        db = _get_learning_db()
        try:
            result = learning_import_from_file(db, input_path=input_path.strip())
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "imported": result["imported"],
                    "skipped_existing": result["skipped"],
                    "skipped_malformed": result.get("skipped_malformed_lines", 0),
                    "message": (
                        f"Imported {result['imported']} new rules, "
                        f"skipped {result['skipped']} existing, "
                        f"{result.get('skipped_malformed_lines', 0)} malformed lines."
                    ),
                }, ensure_ascii=False),
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=_structured_error("IMPORT_FAILED", str(e)),
            )]

    # -----------------------------------------------------------------------
    # Tool: set_mod_path (GAP-004 — dynamic workspace switching)
    # -----------------------------------------------------------------------
    @server.tool()
    async def set_mod_path(
        mod_path: str = "",
        auto_detect: bool = False,
    ) -> list[TextContent]:
        """Switch the active mod at runtime without restarting the server.

        Use this when opening a different HOI4 mod workspace. The server
        invalidates all mod caches and re-indexes the new mod on next access.

        Args:
            mod_path: Absolute path to the new mod directory. If empty and
                      auto_detect=True, scans CWD/parents for descriptor.mod.
            auto_detect: If true, auto-detect a mod from the current working
                         directory and parent directories.
        """
        if auto_detect:
            detected = ServerConfig._auto_detect_mod()
            if detected:
                mod_path = str(detected)
            else:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error_code": "NO_MOD_DETECTED",
                        "message": "No HOI4 mod found in CWD or parent directories.",
                        "help": "Provide an explicit mod_path or ensure the workspace contains a descriptor.mod file.",
                    }, ensure_ascii=False),
                )]

        if not mod_path.strip():
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error_code": "MISSING_PATH",
                    "message": "Provide mod_path or set auto_detect=true.",
                }, ensure_ascii=False),
            )]

        p = Path(mod_path.strip())
        if not p.exists():
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error_code": "PATH_NOT_FOUND",
                    "message": f"Mod path does not exist: {p}",
                }, ensure_ascii=False),
            )]

        # Check it looks like a mod directory
        if not (p / "descriptor.mod").exists() and not list(p.glob("*.mod")):
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error_code": "NOT_A_MOD",
                    "message": f"Directory does not appear to be a HOI4 mod (no descriptor.mod or .mod file found): {p}",
                }, ensure_ascii=False),
            )]

        # Switch
        old_path = str(_state["mod_path"]) if _state["mod_path"] else "none"
        _state["mod_path"] = p
        _invalidate_mod_caches()

        # Verify the index builds
        try:
            index = _get_mod_index()
            mod_name = index.get("mod_name", p.name)
            event_count = len(index.get("events", {}))
            focus_count = len(index.get("focuses", {}))
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error_code": "INDEX_FAILED",
                    "message": f"Mod path set but index failed: {e}",
                }, ensure_ascii=False),
            )]

        return [TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "previous": old_path,
                "current": str(p),
                "mod_name": mod_name,
                "events": event_count,
                "focuses": focus_count,
                "message": f"Switched to mod: {mod_name} ({event_count} events, {focus_count} focuses). All caches invalidated.",
            }, ensure_ascii=False),
        )]

    # -----------------------------------------------------------------------
    # Resources
    # -----------------------------------------------------------------------
    @server.resource("mod://descriptor")
    async def get_mod_descriptor() -> str:
        """Returns the mod descriptor data (name, version, dependencies, etc.)."""
        if not _has_mod():
            return json.dumps({"error": "No mod path configured"})
        index = _get_mod_index()
        return json.dumps(index.get("descriptor", {}), indent=2)

    @server.resource("logs://error_latest")
    async def get_error_log_resource() -> str:
        """Returns the last 50 lines of error.log parsed as JSON."""
        log = parse_error_log(None, tail_lines=50)
        return json.dumps({
            "path": log.path,
            "total_errors": log.total_errors,
            "errors": [
                {"category": e.category, "message": e.message, "file": e.file}
                for e in log.errors
            ],
        }, indent=2)

    return server


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_server(config: ServerConfig) -> None:
    """Run the MCP server with stdio transport."""
    server = create_hoi4_server(config)
    server.run(transport='stdio')


def main() -> None:
    """CLI entry point for the HOI4 MCP server."""
    import argparse

    parser = argparse.ArgumentParser(
        description="HOI4 MCP Server — Model Context Protocol server for Hearts of Iron IV modding."
    )
    parser.add_argument(
        "--mod-path",
        help="Path to the HOI4 mod directory to index and manage.",
        default=os.environ.get("HOI4_MOD_PATH", None),
    )
    parser.add_argument(
        "--vanilla-path",
        help="Path to the vanilla HOI4 game install (for database building).",
        default=os.environ.get("HOI4_VANILLA_PATH", None),
    )
    parser.add_argument(
        "--vanilla-db",
        help="Path to the vanilla SQLite database (default: ~/.hoi4_mcp/vanilla.db).",
        default=os.environ.get("HOI4_VANILLA_DB", None),
    )
    parser.add_argument(
        "--build-vanilla-db",
        action="store_true",
        help="Build the vanilla database on startup if needed.",
    )
    parser.add_argument(
        "--auto-detect-mod",
        action="store_true",
        help="Auto-detect the mod path from the current working directory (looks for descriptor.mod).",
    )
    parser.add_argument(
        "--error-log-path",
        help="Path to the HOI4 error.log file (overrides auto-detection).",
        default=os.environ.get("HOI4_ERROR_LOG", None),
    )
    parser.add_argument(
        "--report",
        help="Generate a self-contained HTML mod report and exit.",
        default=None,
        metavar="OUTPUT.html",
    )

    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Report mode: generate HTML report and exit
    # ------------------------------------------------------------------
    if args.report:
        from .tools.report import generate_report
        output = generate_report(
            mod_path=args.mod_path,
            output_path=args.report,
            vanilla_db_path=args.vanilla_db,
        )
        print(f"Report generated: {output}")
        print(f"Size: {output.stat().st_size:,} bytes")
        return

    # Build vanilla DB if requested
    if args.build_vanilla_db and args.vanilla_path:
        db_path = args.vanilla_db or str(Path.home() / ".hoi4_mcp" / "vanilla.db")
        print(f"Building vanilla database from: {args.vanilla_path}")
        builder = VanillaDBBuilder(args.vanilla_path, db_path)
        counts = builder.build_all()
        builder.close()
        print(f"Done. Indexed: {counts}")

    config = ServerConfig(
        mod_path=args.mod_path,
        vanilla_path=args.vanilla_path,
        vanilla_db_path=args.vanilla_db,
        auto_detect_mod=args.auto_detect_mod,
    )

    if not config.has_mod:
        print("Warning: No --mod-path provided and no mod auto-detected. Mod-specific tools will be unavailable.")
        print("Set HOI4_MOD_PATH environment variable, pass --mod-path, or use --auto-detect-mod.")

    run_server(config)


if __name__ == "__main__":
    main()
