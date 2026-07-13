# HOI4-MCP — Comprehensive Test Results

> **Date:** 2026-07-13  
> **HOI4 Version:** 1.19.x  
> **Vanilla DB:** 40,040 events · 5,676 focuses · 5,129 decisions · 5,306 characters · 552 technologies · 613 ideas · 363 countries · 387 modifiers

---

## Reference Mod Test Results

| Mod | Size | Files | Time | Events | Focuses | Decisions | Ideas | Chars | Scr.Eff | Scr.GUIs | Loc Keys | Errors |
|-----|------|-------|------|--------|---------|-----------|-------|-------|---------|----------|----------|--------|
| Parliament GUI | 196K | 6 | 0.0s | 0 | 0 | 0 | 0 | 0 | 5 | 1 | 12 | 0 |
| Global Market | 2.8M | 15 | 0.4s | 16 | 0 | 0 | 0 | 0 | 8 | 0 | 638 | 0 |
| Greater Macedonia | 17M | 25 | 0.2s | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5,163 | 0 |
| Toolpack | 14M | 171 | 0.7s | 5 | 0 | 4 | 1 | 0 | 56 | 21 | 1,045 | 0 |
| Old World Blues | 3.6G | 2,745 | 21.4s | 1,360 | 1,386 | 1,565 | 1,474 | 4,021 | 3,421 | 0 | 124,607 | 0 |
| Kaiserreich | 1.2G | 2,156 | 51.0s | 19,558 | 17,597 | 3,870 | 25 | 6,977 | 3,932 | 49 | 252,105 | 0 |

### Key Observations

- **All 6 mods indexed with zero errors** — no parse failures, no crashes
- **Parliament GUI** (1.10.*): 13 files, 0.0s — backwards-compatible with old HOI4 versions
- **Global Market** (1.19.*): Pure scripted GUI architecture, no decisions/ideas — correctly identified
- **Greater Macedonia** (1.19.*): Country pack — 5,163 loc keys from a focused mod
- **Toolpack** (1.19.*): 21 scripted GUIs captured (fix verified), 56 scripted effects, multi-lang localisation
- **Old World Blues** (1.19.*): 3.6GB, 21.4s index — largest mod tested, 3,421 scripted effects
- **Kaiserreich** (1.19.2.*): 51.0s index, 252K loc keys, 394 namespaces — most complex mod

---

## Vanilla Game Reference

| System | Count | Notes |
|--------|-------|-------|
| Events | 40,040 | Country, news, state, unit, decision events |
| Focuses | 5,676 | All DLC focuses included |
| Decisions | 5,129 | All categories |
| Characters | 5,306 | Leaders, advisors, corps commanders |
| Technologies | 552 | All tech trees |
| Ideas | 613 | National spirits, advisors, laws |
| Countries | 363 | All tags |
| Modifiers | 387 | Hardcoded modifier reference |

---

## Automated Test Suite

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_clausewitz.py` | 21 | Tokenizer, parser, parse_file, extract_ids |
| `test_validator.py` | 24 | Bracket matching, hide_window, completion_reward, state-scope, BOM, language headers |
| `test_learning.py` | 56 | Validation, CRUD, query, resolve, dedup, export/import, seeder, detector, formatting, stats |
| **Total** | **101** | **All passing in 0.18s** |

---

## Learning System

| Metric | Value |
|--------|-------|
| Seed rules | 14 |
| Rule categories | syntax, logic, design, scope, localisation, id_collision, convention, performance |
| Severity levels | error, warning, style |
| Sources | agent_self_correction, human_correction, game_log, validation, seed |
| Dedup method | Token-overlap Jaccard similarity (≥0.7 threshold) |
| Export format | .jsonl (one JSON per line, git-diffable) |

---

## Performance Benchmarks

| Scenario | Time | Files/sec |
|----------|------|-----------|
| Small mod (13 files) | <0.1s | — |
| Medium mod (392 files) | 0.7s | ~560/s |
| Large mod (2.7K files) | 21.4s | ~128/s |
| XL mod (2.2K files, deep) | 51.0s | ~42/s |
| Vanilla DB build | ~60s | — |

Indexing speed decreases with file complexity (deeper nesting = slower parsing). The category filter on `get_mod_index` prevents large JSON responses from overwhelming AI context windows.
