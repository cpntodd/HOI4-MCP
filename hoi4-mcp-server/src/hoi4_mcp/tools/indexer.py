"""Mod indexer — scans an entire HOI4 mod directory and builds a comprehensive
index of all IDs, namespaces, scripted effects, and other tokens.

This is the core of the "Mod Indexer" MCP tool. It replaces the AI's need
to run multiple search/read operations by providing a pre-built JSON map
of the entire mod.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..clausewitz.parser import parse_file, extract_ids, ParsedFile


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ModIndex:
    """Complete index of a HOI4 mod's content."""
    mod_path: str = ""
    mod_name: str = ""

    # Namespaces (from add_namespace in event files)
    namespaces: list[str] = field(default_factory=list)

    # Events: {namespace.event_id: {"file": "...", "line": 0, "type": "country_event"}}
    events: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Focuses: {focus_id: {"file": "...", "tree": "..."}}
    focuses: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Focus trees: {tree_id: {"file": "...", "country": [...]}}
    focus_trees: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Decisions: {decision_key: {"file": "...", "category": "..."}}
    decisions: dict[str, dict[str, Any]] = field(default_factory=dict)

    # National spirits / Ideas: {idea_key: {"file": "...", "category": "..."}}
    ideas: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Characters: {char_id: {"file": "...", "roles": [...]}}
    characters: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Technologies: {tech_key: {"file": "...", "category": "..."}}
    technologies: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Scripted effects: {effect_name: {"file": "...", "arg_count": 0}}
    scripted_effects: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Scripted triggers: {trigger_name: {"file": "...", "arg_count": 0}}
    scripted_triggers: dict[str, dict[str, Any]] = field(default_factory=dict)

    # On actions: {on_action_name: {"file": "..."}}
    on_actions: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Scripted GUIs: {gui_name: {"file": "...", "context_type": "..."}}
    scripted_guis: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Scripted localisation: {loc_key: {"file": "..."}}
    scripted_localisation: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Localisation keys found: set of all keys
    localisation_keys: set[str] = field(default_factory=set)

    # Errors encountered during indexing
    errors: list[str] = field(default_factory=list)

    # File count
    files_indexed: int = 0

    # Mod descriptor info
    descriptor: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Indexer
# ---------------------------------------------------------------------------

class ModIndexer:
    """Scans a HOI4 mod directory and builds a ModIndex."""

    # Subdirectories to scan for specific content types
    SCAN_DIRS = {
        "events": "events",
        "national_focus": "common/national_focus",
        "decisions": "common/decisions",
        "ideas": "common/ideas",
        "characters": "common/characters",
        "technologies": "common/technologies",
        "scripted_effects": "common/scripted_effects",
        "scripted_triggers": "common/scripted_triggers",
        "scripted_guis": "common/scripted_guis",
        "scripted_localisation": "common/scripted_localisation",
        "on_actions": "common/on_actions",
        "localisation": "localisation/english",
        "country_history": "history/countries",
    }

    def __init__(self, mod_path: str | Path):
        self.mod_path = Path(mod_path)
        if not self.mod_path.exists():
            raise FileNotFoundError(f"Mod path does not exist: {mod_path}")

    def _read_descriptor(self) -> dict[str, Any]:
        """Read the .mod file or descriptor.mod for mod metadata."""
        # Try descriptor.mod first (local mods)
        descriptor_path = self.mod_path / "descriptor.mod"
        if not descriptor_path.exists():
            # Try .mod files in parent directory (workshop mods)
            for f in self.mod_path.parent.glob("*.mod"):
                parsed = parse_file(f)
                if parsed.data.get("path") == str(self.mod_path) or \
                   parsed.data.get("archive") == str(self.mod_path):
                    descriptor_path = f
                    break

        if descriptor_path.exists():
            parsed = parse_file(descriptor_path)
            return {
                "name": parsed.data.get("name", self.mod_path.name),
                "version": parsed.data.get("supported_version", "unknown"),
                "tags": parsed.data.get("tags", []),
                "dependencies": parsed.data.get("dependencies", []),
                "replace_path": parsed.data.get("replace_path", []),
            }

        return {"name": self.mod_path.name, "version": "unknown"}

    def _scan_txt_files(self, subdir: str) -> list[Path]:
        """Find all .txt files in a subdirectory."""
        full_path = self.mod_path / subdir
        if not full_path.exists():
            return []
        return sorted(full_path.rglob("*.txt"))

    def _scan_yml_files(self, subdir: str) -> list[Path]:
        """Find all .yml files in a subdirectory (localisation)."""
        full_path = self.mod_path / subdir
        if not full_path.exists():
            return []
        return sorted(full_path.rglob("*.yml"))

    def _index_event_files(self, index: ModIndex) -> None:
        """Parse all event files and extract event IDs and namespaces."""
        for filepath in self._scan_txt_files("events"):
            parsed = parse_file(filepath)
            index.files_indexed += 1

            # Extract namespaces
            for ns in parsed.namespaces:
                if ns not in index.namespaces:
                    index.namespaces.append(ns)

            # Extract events (country_event, news_event, unit_event)
            for key, value in parsed.data.items():
                if key in ("country_event", "news_event", "unit_event", 
                           "state_event", "decision_event"):
                    # Handle both single dict and list of dicts (I-4 fix)
                    events_list = value if isinstance(value, list) else [value]
                    for event_val in events_list:
                        if isinstance(event_val, dict) and "id" in event_val:
                            eid = str(event_val["id"])
                            index.events[eid] = {
                                "file": str(filepath.relative_to(self.mod_path)),
                                "type": key,
                                "title": str(event_val.get("title", "")),
                                "is_triggered_only": event_val.get("is_triggered_only", "no") == "yes",
                                "hide_window": event_val.get("hide_window", "no") == "yes",
                            }
                elif key == "add_namespace":
                    pass  # Already handled

            if parsed.errors:
                for err in parsed.errors:
                    index.errors.append(f"{filepath.name}:{err.line}: {err.message}")

    def _index_focus_files(self, index: ModIndex) -> None:
        """Parse focus tree files and extract focus IDs."""
        for filepath in self._scan_txt_files("common/national_focus"):
            parsed = parse_file(filepath)
            index.files_indexed += 1

            for key, value in parsed.data.items():
                if key == "focus_tree":
                    if isinstance(value, dict):
                        tree_id = value.get("id", filepath.stem)
                        index.focus_trees[str(tree_id)] = {
                            "file": str(filepath.relative_to(self.mod_path)),
                            "country": value.get("country", {}),
                        }

                        # Extract individual focuses
                        if "focus" in value:
                            foci = value["focus"]
                            if isinstance(foci, dict):
                                fid = foci.get("id", "")
                                if fid:
                                    index.focuses[str(fid)] = {
                                        "file": str(filepath.relative_to(self.mod_path)),
                                        "tree": str(tree_id),
                                        "x": foci.get("x", 0),
                                        "y": foci.get("y", 0),
                                        "prerequisite": foci.get("prerequisite", {}),
                                        "mutually_exclusive": foci.get("mutually_exclusive", {}),
                                    }
                            elif isinstance(foci, list):
                                for f in foci:
                                    if isinstance(f, dict):
                                        fid = f.get("id", "")
                                        if fid:
                                            index.focuses[str(fid)] = {
                                                "file": str(filepath.relative_to(self.mod_path)),
                                                "tree": str(tree_id),
                                                "x": f.get("x", 0),
                                                "y": f.get("y", 0),
                                            }

            if parsed.errors:
                for err in parsed.errors:
                    index.errors.append(f"{filepath.name}:{err.line}: {err.message}")

    def _index_decision_files(self, index: ModIndex) -> None:
        """Parse decision files and extract decision categories/keys."""
        for filepath in self._scan_txt_files("common/decisions"):
            parsed = parse_file(filepath)
            index.files_indexed += 1

            for category_key, category_value in parsed.data.items():
                if isinstance(category_value, dict):
                    for dec_key, dec_value in category_value.items():
                        if isinstance(dec_value, dict) and "allowed" in dec_value:
                            index.decisions[str(dec_key)] = {
                                "file": str(filepath.relative_to(self.mod_path)),
                                "category": str(category_key),
                                "icon": str(dec_value.get("icon", "")),
                                "cost": dec_value.get("cost", 0),
                            }

    def _index_idea_files(self, index: ModIndex) -> None:
        """Parse idea files and extract spirit/advisor keys."""
        for filepath in self._scan_txt_files("common/ideas"):
            parsed = parse_file(filepath)
            index.files_indexed += 1

            for category_key, category_value in parsed.data.items():
                if isinstance(category_value, dict):
                    for idea_key, idea_value in category_value.items():
                        if isinstance(idea_value, dict):
                            entry = {
                                "file": str(filepath.relative_to(self.mod_path)),
                                "category": str(category_key),
                            }
                            if "picture" in idea_value:
                                entry["picture"] = str(idea_value["picture"])
                            if "slot" in idea_value:
                                entry["slot"] = str(idea_value["slot"])
                            index.ideas[str(idea_key)] = entry

    def _index_character_files(self, index: ModIndex) -> None:
        """Parse character files and extract character IDs."""
        for filepath in self._scan_txt_files("common/characters"):
            parsed = parse_file(filepath)
            index.files_indexed += 1

            if "characters" in parsed.data:
                chars = parsed.data["characters"]
                if isinstance(chars, dict):
                    for char_id, char_data in chars.items():
                        roles = []
                        if isinstance(char_data, dict):
                            if "country_leader" in char_data:
                                roles.append("country_leader")
                            if "advisor" in char_data:
                                roles.append("advisor")
                            if "corps_commander" in char_data:
                                roles.append("corps_commander")
                            index.characters[str(char_id)] = {
                                "file": str(filepath.relative_to(self.mod_path)),
                                "roles": roles,
                                "name": str(char_data.get("name", "")),
                            }

    def _index_scripted_files(self, index: ModIndex) -> None:
        """Parse scripted effects and triggers files."""
        # Scripted effects
        for filepath in self._scan_txt_files("common/scripted_effects"):
            parsed = parse_file(filepath)
            index.files_indexed += 1
            for key in parsed.data:
                if key not in ("add_namespace",):
                    index.scripted_effects[str(key)] = {
                        "file": str(filepath.relative_to(self.mod_path)),
                    }

        # Scripted triggers
        for filepath in self._scan_txt_files("common/scripted_triggers"):
            parsed = parse_file(filepath)
            index.files_indexed += 1
            for key in parsed.data:
                if key not in ("add_namespace",):
                    index.scripted_triggers[str(key)] = {
                        "file": str(filepath.relative_to(self.mod_path)),
                    }

    def _index_on_actions(self, index: ModIndex) -> None:
        """Parse on_action files."""
        for filepath in self._scan_txt_files("common/on_actions"):
            parsed = parse_file(filepath)
            index.files_indexed += 1
            if "on_actions" in parsed.data:
                oa = parsed.data["on_actions"]
                if isinstance(oa, dict):
                    for action_name in oa:
                        index.on_actions[str(action_name)] = {
                            "file": str(filepath.relative_to(self.mod_path)),
                        }

    def _index_localisation(self, index: ModIndex) -> None:
        """Extract all localisation keys from YML files (I-2: recursive scan)."""
        import re
        # Match "KEY:0 \"value\"" (standard), "KEY: \"value\"" (Kaiserreich no-version),
        # and " KEY: \"value\"" (leading whitespace variants)
        loc_pattern = re.compile(r'^\s*([A-Za-z0-9_.-]+):(?:\d+)?\s*"')

        loc_root = self.mod_path / "localisation"
        if not loc_root.exists():
            return

        # Recursively scan all .yml files under localisation/ (all languages)
        for filepath in sorted(loc_root.rglob("*.yml")):
            try:
                text = filepath.read_text(encoding="utf-8")
            except Exception:
                continue
            index.files_indexed += 1
            for line in text.split("\n"):
                match = loc_pattern.match(line)
                if match:
                    index.localisation_keys.add(match.group(1))

    def _index_scripted_guis(self, index: ModIndex) -> None:
        """Index scripted GUI files — unwraps scripted_gui = { ... } outer container."""
        for filepath in self._scan_txt_files("common/scripted_guis"):
            parsed = parse_file(filepath)
            index.files_indexed += 1

            # 1. Extract the wrapper, handling both dict (standard) and list (duplicate keys)
            wrapper = parsed.data.get("scripted_gui")
            blocks = []
            if isinstance(wrapper, dict):
                blocks = [wrapper]
            elif isinstance(wrapper, list):
                blocks = [b for b in wrapper if isinstance(b, dict)]
            else:
                index.errors.append(
                    f"{filepath.name}: No valid 'scripted_gui' wrapper found"
                )
                continue

            # 2. Iterate through the unwrapped blocks
            for block in blocks:
                for gui_name, gui_data in block.items():
                    if isinstance(gui_data, dict):
                        # 3. Detect duplicate GUI names across files (mod conflict)
                        if gui_name in index.scripted_guis:
                            index.errors.append(
                                f"{filepath.name}: Duplicate scripted_gui '{gui_name}' — "
                                f"already defined in {index.scripted_guis[gui_name]['file']}"
                            )

                        # 4. Index the GUI
                        index.scripted_guis[str(gui_name)] = {
                            "file": str(filepath.relative_to(self.mod_path)),
                            "context_type": str(gui_data.get("context_type", "")),
                            "window_name": str(gui_data.get("window_name", "")).strip(),
                        }

    def _index_scripted_localisation(self, index: ModIndex) -> None:
        """Index scripted localisation files (I-1)."""
        for filepath in self._scan_txt_files("common/scripted_localisation"):
            parsed = parse_file(filepath)
            index.files_indexed += 1
            for loc_key, loc_data in parsed.data.items():
                index.scripted_localisation[str(loc_key)] = {
                    "file": str(filepath.relative_to(self.mod_path)),
                }

    def build_index(self) -> ModIndex:
        """Build a complete index of the mod."""
        index = ModIndex(mod_path=str(self.mod_path))
        index.descriptor = self._read_descriptor()
        index.mod_name = str(index.descriptor.get("name", self.mod_path.name))

        # Run all indexers
        indexers = [
            self._index_event_files,
            self._index_focus_files,
            self._index_decision_files,
            self._index_idea_files,
            self._index_character_files,
            self._index_scripted_files,
            self._index_on_actions,
            self._index_localisation,
            self._index_scripted_guis,
            self._index_scripted_localisation,
        ]

        for indexer in indexers:
            try:
                indexer(index)
            except Exception as e:
                index.errors.append(f"Indexer error: {e}")

        return index

    def build_index_json(self) -> str:
        """Build the index and return it as a JSON string."""
        index = self.build_index()
        # Convert sets to lists for JSON serialization
        return json.dumps({
            "mod_name": index.mod_name,
            "mod_path": index.mod_path,
            "descriptor": index.descriptor,
            "namespaces": index.namespaces,
            "events": index.events,
            "focuses": index.focuses,
            "focus_trees": index.focus_trees,
            "decisions": index.decisions,
            "ideas": index.ideas,
            "characters": index.characters,
            "technologies": index.technologies,
            "scripted_effects": index.scripted_effects,
            "scripted_triggers": index.scripted_triggers,
            "scripted_guis": index.scripted_guis,
            "scripted_localisation": index.scripted_localisation,
            "on_actions": index.on_actions,
            "localisation_keys": sorted(index.localisation_keys),
            "localisation_key_count": len(index.localisation_keys),
            "files_indexed": index.files_indexed,
            "errors": index.errors,
        }, indent=2, default=str)
