# Indexer Gap Fix Proposal — For Review

> **Generated:** 2026-07-13  
> **Purpose:** Present existing code alongside proposed fixes for each indexer gap found during testing.  
> **For:** AI agent or human developer to review and determine if proposed fixes would work before implementation.

---

## Gap Summary

| # | Gap | Severity | Impact |
|---|-----|----------|--------|
| **I-1** | `SCAN_DIRS` missing `scripted_guis`, `scripted_localisation` | 🔴 High | `get_mod_index` returns 0 scripted GUIs even when mod has 16+ GUI files |
| **I-2** | `localisation` scanner hardcoded to `english/` subdirectory | 🔴 High | Kaiserreich returns 0 localisation keys because its english dir doesn't match |
| **I-3** | Technology DB path uses `common/technology` (singular) | 🔴 High | Vanilla DB returns 0 technologies — path should be `common/technologies` (plural) |
| **I-4** | Event indexer misses namespaced events in non-standard structures | 🟡 Medium | Toolpack returns 0 events; Kaiserreich returns 48 (should be thousands) |
| **I-5** | `GER_rhineland` exact lookup fails | 🟢 Low | Not a bug — the vanilla focus ID is `GER_remilitarize_rhineland`. Expected behavior. |

---

## I-1: SCAN_DIRS Missing Scripted GUIs & Scripted Localisation

### Existing Code (`tools/indexer.py`, lines ~84-96)

```python
SCAN_DIRS = {
    "events": "events",
    "national_focus": "common/national_focus",
    "decisions": "common/decisions",
    "ideas": "common/ideas",
    "characters": "common/characters",
    "technologies": "common/technology",
    "scripted_effects": "common/scripted_effects",
    "scripted_triggers": "common/scripted_triggers",
    "on_actions": "common/on_actions",
    "localisation": "localisation/english",
    "country_history": "history/countries",
}
```

### Problem
- `common/scripted_guis/` is not in the scan map — the indexer never looks there.
- `common/scripted_localisation/` is also missing.
- The ModIndex dataclass doesn't have fields for these system types.

### Proposed Fix

**A) Add missing directories to `SCAN_DIRS`:**

```python
SCAN_DIRS = {
    "events": "events",
    "national_focus": "common/national_focus",
    "decisions": "common/decisions",
    "ideas": "common/ideas",
    "characters": "common/characters",
    "technologies": "common/technology",
    "scripted_effects": "common/scripted_effects",
    "scripted_triggers": "common/scripted_triggers",
    "scripted_guis": "common/scripted_guis",          # ← NEW
    "scripted_localisation": "common/scripted_localisation",  # ← NEW
    "on_actions": "common/on_actions",
    "localisation": "localisation/english",
    "country_history": "history/countries",
}
```

**B) Add fields to `ModIndex` dataclass (around line 30):**

```python
@dataclass
class ModIndex:
    # ... existing fields ...
    scripted_guis: dict[str, dict[str, Any]] = field(default_factory=dict)       # ← NEW
    scripted_localisation: dict[str, dict[str, Any]] = field(default_factory=dict)  # ← NEW
```

**C) Add indexing methods for scripted GUIs and scripted localisation:**

```python
def _index_scripted_guis(self, index: ModIndex) -> None:
    """Index scripted GUI files."""
    for filepath in self._scan_txt_files("common/scripted_guis"):
        parsed = parse_file(filepath)
        index.files_indexed += 1
        for gui_name, gui_data in parsed.data.items():
            if isinstance(gui_data, dict):
                index.scripted_guis[str(gui_name)] = {
                    "file": str(filepath.relative_to(self.mod_path)),
                    "context_type": str(gui_data.get("context_type", "")),
                }

def _index_scripted_localisation(self, index: ModIndex) -> None:
    """Index scripted localisation files."""
    for filepath in self._scan_txt_files("common/scripted_localisation"):
        parsed = parse_file(filepath)
        index.files_indexed += 1
        for loc_key, loc_data in parsed.data.items():
            index.scripted_localisation[str(loc_key)] = {
                "file": str(filepath.relative_to(self.mod_path)),
            }
```

**D) Register new methods in `build_index()` (around line 336):**

```python
def build_index(self) -> ModIndex:
    # ... existing ...
    self._index_scripted_guis,            # ← NEW
    self._index_scripted_localisation,    # ← NEW
```

### Review Questions
1. Are there other post-1.12 system directories we're missing? (`common/bop/`, `common/raids/`, `common/military_industrial_organization/`, `common/special_projects/`)
2. Should `_index_scripted_guis` extract individual GUI element types (container, button, iconType, etc.) or just file-level references?

---

## I-2: Localisation Scanner Hardcoded to `english/`

### Existing Code (`tools/indexer.py`, line 96)

```python
"localisation": "localisation/english",
```

And the localisation indexer (around line 300):

```python
def _index_localisation(self, index: ModIndex) -> None:
    """Parse localisation YML files and extract keys."""
    for filepath in self._scan_yml_files("localisation/english"):
        # ...
```

### Problem
- The path `localisation/english` is hardcoded. Mods can name their English directory `english/`, `simp_chinese/english/`, or organize localisation differently.
- Toolpack has a `localisation/english/` directory so it works. Kaiserreich may use a different structure.
- The `_scan_yml_files` method uses `self.mod_path / subdir` which means the hardcoded subdir must exist.

### Proposed Fix (Option A — Scan All Language Directories)

Replace the hardcoded single directory with a recursive scan of all `localisation/` subdirectories:

```python
def _index_localisation(self, index: ModIndex) -> None:
    """Parse localisation YML files and extract keys from ALL language subdirs."""
    loc_root = self.mod_path / "localisation"
    if not loc_root.exists():
        return
    
    # Find all .yml files in all subdirectories under localisation/
    yml_files = sorted(loc_root.rglob("*.yml"))
    for filepath in yml_files:
        try:
            text = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        
        index.files_indexed += 1
        loc_keys = extract_loc_keys(text)
        index.localisation_keys.update(loc_keys)
```

### Proposed Fix (Option B — Try Multiple Common Language Directories)

```python
SCAN_DIRS = {
    # ...
    # Remove hardcoded "localisation/english" from SCAN_DIRS
}

def _index_localisation(self, index: ModIndex) -> None:
    """Try common language directories, fall back to recursive scan."""
    common_langs = ["english", "l_english"]
    found = False
    
    for lang in common_langs:
        # Check both localisation/english/ and localisation/*/english/ patterns
        for pattern in [f"localisation/{lang}", f"localisation/*/{lang}"]:
            for filepath in self._scan_yml_files(pattern):
                if filepath.name.endswith(".yml"):
                    found = True
                    # ... process ...
    
    if not found:
        # Fallback: recursive scan
        loc_root = self.mod_path / "localisation"
        for filepath in sorted(loc_root.rglob("*.yml")):
            # ... process ...
```

### Recommendation
**Option A** (recursive scan of all `localisation/` subdirectories) is simpler and more robust. The only downside is scanning all 10 language subdirectories in Toolpack, but that's negligible (887 keys across all languages is fast).

### Review Questions
1. Is there a risk of duplicate keys across language files inflating the count? Should we deduplicate by key name?
2. Should we track which language each key comes from?

---

## I-3: Technology DB Path — `common/technology` vs `common/technologies`

### Existing Code (`db/vanilla_index.py`, line 695-698)

```python
def index_technologies(self) -> int:
    """Index all vanilla technologies."""
    count = 0
    self.conn.execute("DELETE FROM vanilla_technologies")
    for fp in self._txt_files("common/technology"):  # ← BUG: singular
```

### Problem
The vanilla game path is `common/technologies/` (plural). The `_txt_files` method appends `*.txt` glob to the directory, so `common/technology/*.txt` finds nothing because the directory doesn't exist.

### Existing Code (`tools/indexer.py`, line 92)

```python
"technologies": "common/technology",  # ← Also singular here
```

### Proposed Fix

Change both occurrences from singular to plural:

**`db/vanilla_index.py`:**
```python
for fp in self._txt_files("common/technologies"):  # ← FIX: plural
```

**`tools/indexer.py`:**
```python
"technologies": "common/technologies",  # ← FIX: plural
```

### Additional Issue
The `index_technologies` function also extracts `category` from `tech_val.get("category", "")` but the actual technology structure uses `categories = { ... }` (plural, and it's a dict of category keys). The field should be `categories`.

### Review Questions
1. Should we also check `common/technology_tags/` for category definitions?
2. The `start_year` field extraction `tech_val.get("start_year", 1936)` defaults to 1936 — is this correct for techs without explicit start years?

---

## I-4: Event Indexer Misses Namespaced Events

### Existing Code (`tools/indexer.py`, lines 141-173)

```python
def _index_event_files(self, index: ModIndex) -> None:
    """Parse all event files and extract event IDs and namespaces."""
    for filepath in self._scan_txt_files("events"):
        parsed = parse_file(filepath)
        index.files_indexed += 1

        for ns in parsed.namespaces:
            if ns not in index.namespaces:
                index.namespaces.append(ns)

        for key, value in parsed.data.items():
            if key in ("country_event", "news_event", "unit_event", 
                       "state_event", "decision_event"):
                if isinstance(value, dict) and "id" in value:
                    eid = str(value["id"])
                    index.events[eid] = {
                        "file": str(filepath.relative_to(self.mod_path)),
                        "type": key,
                        "title": str(value.get("title", "")),
                        "is_triggered_only": value.get("is_triggered_only", "no") == "yes",
                        "hide_window": value.get("hide_window", "no") == "yes",
                    }
```

### Problem — Toolpack

Toolpack's `events/toolpack_events.txt` has this structure:
```txt
add_namespace = toolpack

country_event = {
    id = toolpack.1
    ...
}
country_event = {
    id = toolpack.2
    ...
}
```

After parsing, the data looks like:
```python
{
    "add_namespace": "toolpack",
    "country_event": [
        {"id": "toolpack.1", ...},
        {"id": "toolpack.2", ...},
    ]
}
```

The current code handles `isinstance(value, dict)` — it looks for a single event dict. But when there are multiple `country_event` blocks, the parser converts them to a **list**. The code needs to handle `isinstance(value, list)` as well.

### Problem — Kaiserreich

Kaiserreich has ~200 event files with hundreds of events each. The current indexer found only 48 because:
1. The list-vs-dict issue above
2. Some event files may have nested structures the parser doesn't flatten

### Proposed Fix

```python
def _index_event_files(self, index: ModIndex) -> None:
    """Parse all event files and extract event IDs and namespaces."""
    for filepath in self._scan_txt_files("events"):
        parsed = parse_file(filepath)
        index.files_indexed += 1

        for ns in parsed.namespaces:
            if ns not in index.namespaces:
                index.namespaces.append(ns)

        for key, value in parsed.data.items():
            if key in ("country_event", "news_event", "unit_event", 
                       "state_event", "decision_event"):
                # Handle both single dict and list of dicts  ← FIX
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
```

The same fix should be applied to the vanilla DB's `index_events` method in `vanilla_index.py`, line 648-656.

### Review Questions
1. Are there event types beyond the 5 listed that should be included? (`meta_event`, `hidden_event`?)
2. Should the indexer recurse into nested blocks to find events that aren't at the top level of parsed data?

---

## I-5: Vanilla Lookup — `GER_rhineland` Not Found

### Not a Bug — Expected Behavior

The vanilla focus ID is `GER_remilitarize_rhineland`, not `GER_rhineland`. The exact lookup correctly returns "not found" for the wrong ID.

### Existing Search Works
```python
vl.search_focuses("rhineland")  # Would find GER_remilitarize_rhineland
```

### Recommendation
No code change needed. This is documented as expected behavior. The AI agent prompt already instructs: "Use `lookup_vanilla` for exact vanilla IDs... never guess."

---

## Fix Implementation Checklist

```
I-1: Scripted GUIs + Scripted Localisation
├── [ ] Add "scripted_guis" to SCAN_DIRS
├── [ ] Add "scripted_localisation" to SCAN_DIRS
├── [ ] Add fields to ModIndex dataclass
├── [ ] Add _index_scripted_guis method
├── [ ] Add _index_scripted_localisation method
└── [ ] Register in build_index()

I-2: Localisation Scanner
├── [ ] Replace hardcoded "localisation/english" with recursive rglob
└── [ ] Test against Kaiserreich (currently 0 loc keys)

I-3: Technology Path
├── [ ] Fix "common/technology" → "common/technologies" in vanilla_index.py
├── [ ] Fix "common/technology" → "common/technologies" in indexer.py
└── [ ] Fix "category" → "categories" in tech extraction

I-4: Event Indexer List Handling
├── [ ] Fix _index_event_files to handle list-of-dicts
├── [ ] Fix vanilla_index.py index_events to handle list-of-dicts
└── [ ] Rebuild vanilla DB after fix

I-5: No code change needed
```

---

## Expected Results After Fixes

| Metric | Before | After (Expected) |
|--------|--------|------------------|
| Toolpack events | 0 | ~6 |
| Toolpack scripted GUIs | 0 | 16 |
| Kaiserreich localisation keys | 0 | ~5,000+ |
| Vanilla technologies | 0 | ~500+ |
| Vanilla events | 15 | ~5,000+ |

---

*End of fix proposal. Review each proposed change and confirm before implementation.*
