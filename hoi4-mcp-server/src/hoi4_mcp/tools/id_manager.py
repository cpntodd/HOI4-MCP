"""ID Manager — finds the next available numeric ID for events, focuses, decisions, etc.

Solves the "Duplicate ID silently overwrites" problem by scanning existing files
and returning the next safe number.
"""

from __future__ import annotations

from pathlib import Path


class IDManager:
    """Manages ID sequences across a mod's files to prevent collisions."""

    def __init__(self, mod_path: str | Path):
        self.mod_path = Path(mod_path)
        if not self.mod_path.exists():
            raise FileNotFoundError(f"Mod path does not exist: {mod_path}")

    def _scan_ids_in_files(self, subdir: str, key_pattern: str = "id") -> set[str]:
        """Scan files in a subdirectory and extract IDs matching a pattern."""
        full_path = self.mod_path / subdir
        if not full_path.exists():
            return set()

        ids: set[str] = set()
        for filepath in sorted(full_path.rglob("*.txt")):
            try:
                text = filepath.read_text(encoding="utf-8")
            except Exception:
                continue

            # Simple regex-free scan for "id = <value>" patterns
            lines = text.split("\n")
            for line in lines:
                line = line.strip()
                # Match: id = some_value
                if "=" not in line:
                    continue
                parts = line.split("=", 1)
                lhs = parts[0].strip()
                rhs = parts[1].strip().rstrip("#").strip()
                if lhs == "id":
                    # Remove quotes if present
                    rhs = rhs.strip('"').strip("'")
                    ids.add(rhs)

        return ids

    def get_next_event_id(self, namespace: str) -> int:
        """Find the next available event ID for a given namespace.

        Scans all event files for matching 'namespace.X' patterns and returns
        the highest number + 1.
        """
        existing = self._scan_ids_in_files("events")
        prefix = f"{namespace}."
        nums = []
        for eid in existing:
            if eid.startswith(prefix):
                try:
                    nums.append(int(eid[len(prefix):]))
                except ValueError:
                    pass
        return max(nums) + 1 if nums else 1

    def get_next_focus_id(self, prefix: str = "") -> int:
        """Find the next available focus ID number.

        Focus IDs typically follow pattern: <namespace>_<number> or <prefix>_<number>.
        """
        full_path = self.mod_path / "common" / "national_focus"
        if not full_path.exists():
            return 1

        existing_ids: set[str] = set()
        for filepath in sorted(full_path.rglob("*.txt")):
            try:
                text = filepath.read_text(encoding="utf-8")
            except Exception:
                continue
            for line in text.split("\n"):
                line = line.strip()
                if "=" not in line:
                    continue
                parts = line.split("=", 1)
                lhs = parts[0].strip()
                rhs = parts[1].strip().rstrip("#").strip().strip('"')
                if lhs == "id":
                    existing_ids.add(rhs)

        # Extract numeric suffixes from matching IDs
        nums = []
        for fid in existing_ids:
            if prefix and not fid.startswith(prefix):
                continue
            # Try to find trailing numbers
            import re
            match = re.search(r'_(\d+)$', fid)
            if match:
                nums.append(int(match.group(1)))

        return max(nums) + 1 if nums else 1

    def get_next_decision_id(self) -> int:
        """Find the next available decision numeric suffix."""
        full_path = self.mod_path / "common" / "decisions"
        if not full_path.exists():
            return 1

        nums = []
        for filepath in sorted(full_path.rglob("*.txt")):
            try:
                text = filepath.read_text(encoding="utf-8")
            except Exception:
                continue
            import re
            # Look for decision names with trailing numbers
            for match in re.finditer(r'(\w+)_(\d+)\s*=', text):
                try:
                    nums.append(int(match.group(2)))
                except ValueError:
                    pass

        return max(nums) + 1 if nums else 1

    def get_next_character_id(self) -> int:
        """Find the next available character numeric ID."""
        full_path = self.mod_path / "common" / "characters"
        if not full_path.exists():
            return 1

        nums = []
        for filepath in sorted(full_path.rglob("*.txt")):
            try:
                text = filepath.read_text(encoding="utf-8")
            except Exception:
                continue
            import re
            for match in re.finditer(r'(\w+)_character_(\d+)', text):
                try:
                    nums.append(int(match.group(2)))
                except ValueError:
                    pass
            # Also check for bare numeric IDs
            for match in re.finditer(r'^\s*(\d+)\s*=', text, re.MULTILINE):
                try:
                    nums.append(int(match.group(1)))
                except ValueError:
                    pass

        return max(nums) + 1 if nums else 1

    def check_id_exists(self, id_value: str, id_type: str = "any") -> dict:
        """Check if an ID already exists in the mod and return details.

        Args:
            id_value: The ID to check (e.g., 'mymod.1', 'my_focus_1').
            id_type: One of 'event', 'focus', 'decision', 'idea', 'character', 'any'.
        
        Returns:
            Dict with 'exists' (bool), 'locations' (list of files), 'type' (str).
        """
        locations = []

        checks = []
        if id_type in ("any", "event"):
            checks.append(("events", "Events"))
        if id_type in ("any", "focus"):
            checks.append(("common/national_focus", "Focuses"))
        if id_type in ("any", "decision"):
            checks.append(("common/decisions", "Decisions"))
        if id_type in ("any", "idea"):
            checks.append(("common/ideas", "Ideas"))
        if id_type in ("any", "character"):
            checks.append(("common/characters", "Characters"))

        for subdir, label in checks:
            full_path = self.mod_path / subdir
            if not full_path.exists():
                continue
            for filepath in sorted(full_path.rglob("*.txt")):
                try:
                    text = filepath.read_text(encoding="utf-8")
                except Exception:
                    continue
                if id_value in text:
                    locations.append({
                        "file": str(filepath.relative_to(self.mod_path)),
                        "type": label,
                    })

        return {
            "exists": len(locations) > 0,
            "id": id_value,
            "locations": locations,
        }
