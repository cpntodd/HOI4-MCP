# Clausewitz Parser Deep Scan — Scripted GUI Handling Audit

> **Generated:** 2026-07-13  
> **Purpose:** Analyze why the parser/indexer only captures 1 of 16 scripted GUI files, and propose fixes.

---

## 1. What's Actually Happening

### The Indexer Code (the root cause)

```python
# tools/indexer.py — _index_scripted_guis
def _index_scripted_guis(self, index: ModIndex) -> None:
    for filepath in self._scan_txt_files("common/scripted_guis"):
        parsed = parse_file(filepath)
        index.files_indexed += 1
        for gui_name, gui_data in parsed.data.items():  # ← BUG: iterates top-level
            if isinstance(gui_data, dict):
                index.scripted_guis[str(gui_name)] = {
                    "file": str(filepath.relative_to(self.mod_path)),
                    "context_type": str(gui_data.get("context_type", "")),
                }
```

### What the GUI Files Look Like

Every Toolpack GUI file wraps its contents in `scripted_gui = { ... }`:

```
scripted_gui = {
    gui_name_1 = {
        context_type = selected_state_context
        window_name = "gui_name_1"
        visible = { ... }
        effects = { ... }
        triggers = { ... }
    }
    gui_name_2 = {
        context_type = player_context
        window_name = "gui_name_2"
        ...
    }
}
```

### What Happens After Parsing

```python
parsed.data = {
    "scripted_gui": {
        "gui_name_1": {"context_type": "selected_state_context", ...},
        "gui_name_2": {"context_type": "player_context", ...},
    }
}
```

### Why Only 1 GUI Is Found

The indexer iterates `parsed.data.items()` → finds ONE key: `"scripted_gui"`.  
It checks `isinstance(gui_data, dict)` → True (it IS a dict).  
It creates: `index.scripted_guis["scripted_gui"] = {"file": "...", "context_type": ""}`.  
The 4 actual GUI entries (`gui_name_1`, `gui_name_2`, ...) are never reached — they're nested one level deeper.

**The parser IS working correctly.** The indexer is just looking at the wrong level.

---

## 2. Parser Capability Assessment

### What the Parser Handles Well

| Pattern | Example | Status |
|---------|---------|--------|
| Nested blocks (4-5 levels) | `container → button → nested → icon` | ✅ |
| Bare `yes`/`no` values | `is_triggered_only = yes` | ✅ (read as KEY, returned as string) |
| Dotted identifiers | `bst_background_1`, `var:global.bst_position_1` | ✅ (colon not a stop char) |
| Multiple same-key blocks → list | `country_event = { }` repeated | ✅ |
| Comments `#` | `# This is a comment` | ✅ |
| Quoted strings with escapes | `"He said \"hello\""` | ✅ |
| Comparison operators | `!=`, `<=`, `>=`, `==` | ✅ (read as EQUALS) |
| Numeric values | `x = 5`, `y = 3` | ✅ |

### What the Parser Struggles With

| Pattern | Why It Fails | Severity |
|---------|-------------|----------|
| `properties = { element = { y = var:global.var } }` | Works fine — just nested dicts | None |
| `if = { limit = { ... } }` / `else = { ... }` | Works — `if` and `else` are different keys, won't merge | None |
| `meta_effect = { text = "..." var = val }` | `meta_effect` as key, dict value — works | None |
| `dynamic_lists = { grid = { array = global.arr } }` | Deep nesting with dots in values — works | None |
| Extremely deep nesting (>100 levels) | No depth limit — could stack overflow | 🟡 Low |
| Malformed braces `{ { }` | `_parse_block` expects RBRACE but gets LBRACE — raises SyntaxError, loses all data | 🟡 Medium |
| Top-level bare values | `some_value` without `key =` prefix — parser creates synthetic key `"0"` | 🟢 Low |

---

## 3. Recommended Fixes

### Fix 1: Indexer — Recurse into `scripted_gui` wrapper (🔴 Critical)

This is the actual bug. The indexer should check for and unwrap the `scripted_gui` outer container.

**Current code (broken):**
```python
for gui_name, gui_data in parsed.data.items():
    if isinstance(gui_data, dict):
        index.scripted_guis[str(gui_name)] = {
            "file": str(filepath.relative_to(self.mod_path)),
            "context_type": str(gui_data.get("context_type", "")),
        }
```

**Proposed fix:**
```python
# Unwrap the scripted_gui = { ... } outer container if present
gui_entries = parsed.data
if "scripted_gui" in gui_entries and isinstance(gui_entries["scripted_gui"], dict):
    gui_entries = gui_entries["scripted_gui"]

for gui_name, gui_data in gui_entries.items():
    if isinstance(gui_data, dict):
        index.scripted_guis[str(gui_name)] = {
            "file": str(filepath.relative_to(self.mod_path)),
            "context_type": str(gui_data.get("context_type", "")),
            "window_name": str(gui_data.get("window_name", "")),
        }
```

### Fix 2: Parser — Graceful Error Recovery (🟡 Medium)

When the parser hits a `SyntaxError` in `_parse_block`, it raises an exception. The `parse_file` function catches it and returns an empty result. This means a single malformed brace anywhere in the file discards ALL parsed data.

**Proposed fix:** Add a `_recover_to_brace` method that skips tokens until balanced braces are found:

```python
def _recover_to_brace(self, depth: int = 0) -> None:
    """Skip tokens until we find a balanced closing brace."""
    current_depth = depth
    while self._peek().type != "EOF":
        tok = self._advance()
        if tok.type == "LBRACE":
            current_depth += 1
        elif tok.type == "RBRACE":
            current_depth -= 1
            if current_depth <= 0:
                return
```

Then in `_parse_block`, replace `raise SyntaxError(...)` with a recovery attempt:
```python
# Instead of: raise SyntaxError(f"Expected RBRACE, got ...")
# Use:
self._recover_to_brace()
return result  # Return partial data
```

### Fix 3: Tokenizer — Handle `var:scope.path` as Single Token Type (🟢 Low)

Currently `var:global.bst_position_1` is read as a single KEY token. This works but loses semantic information. Adding a dedicated `VAR_REF` token type would enable:
- Better validation (check that `global.` or `var:` prefixes are valid)
- Smarter indexing (extract referenced variable names)
- Future scope validation

**Not needed for fixing the GUI indexer** — the KEY token works fine for parsing.

### Fix 4: Parser — Depth Limit Protection (🟢 Low)

Add a `max_depth` parameter to prevent stack overflow on malicious/deeply nested files:

```python
def _parse_block(self, depth: int = 0, max_depth: int = 200) -> dict[str, Any]:
    if depth > max_depth:
        return {"_parse_error": "Max nesting depth exceeded"}
    # ... rest of method, passing depth+1 to recursive _parse_block calls
```

---

## 4. Expected Results After Fix 1

| File | GUIs | Before Fix | After Fix |
|------|------|-----------|-----------|
| `toolpack.txt` | 4 | 1 (wrong: indexes `scripted_gui` wrapper) | 4 |
| `bst.txt` | 2 | 1 | 2 |
| `dst_A.txt` | 1 | 1 | 1 |
| `dst_B.txt` | 1 | 0 or 1 | 1 |
| `cat.txt` | 1 | 0 or 1 | 1 |
| `cct.txt` | 1 | 0 or 1 | 1 |
| `cpt.txt` | 1 | 0 or 1 | 1 |
| `crt.txt` | 1 | 0 or 1 | 1 |
| `mst_C.txt` | 1 | 0 or 1 | 1 |
| `mst_S.txt` | 1 | 0 or 1 | 1 |
| `mp_toolpack_action_log.txt` | 1 | 0 or 1 | 1 |
| `ret.txt` | 1 | 0 or 1 | 1 |
| `rmt.txt` | 1 | 0 or 1 | 1 |
| `smt.txt` | 1 | 0 or 1 | 1 |
| `sst.txt` | 1 | 0 or 1 | 1 |
| `tpt.txt` | 1 | 0 or 1 | 1 |
| **Total** | **~20** | **1** | **~20** |

---

## 5. Implementation Priority

| Fix | Effort | Impact | Recommendation |
|-----|--------|--------|---------------|
| **Fix 1**: Indexer unwrap `scripted_gui` | 3 lines | Fixes the actual bug — goes from 1 to ~20 GUIs | **Do now** |
| **Fix 2**: Parser graceful recovery | ~20 lines | Prevents data loss from single malformed brace | Do when parser errors are reported |
| **Fix 3**: VAR_REF token type | ~30 lines | Semantic improvement, not a bug | Nice to have |
| **Fix 4**: Depth limit | ~10 lines | Safety, not a bug | Nice to have |

---

## 6. Verdict

**The parser is not the problem.** It correctly parses scripted GUI files — the nesting, the unusual key names, the `var:global.` references, the `meta_effect` blocks, the `properties` blocks, and the `dynamic_lists` — all pass through the parser without issue.

**The indexer is the problem.** It iterates the wrong dict level. One 3-line fix resolves the entire gap.

The parser would benefit from graceful error recovery (Fix 2) for robustness, but that's a separate concern from the GUI indexing gap.

---

*End of audit. Fix 1 is the only change needed to resolve the scripted GUI indexing gap.*
