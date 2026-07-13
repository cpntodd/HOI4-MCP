# HOI4-MCP Project — Comprehensive Audit

> **Generated:** 2026-07-13 — **Revised:** 2026-07-13 (GLM review integrated)  
> **Purpose:** Structured gap analysis for other AI agents and human developers to review and improve.  
> **Target platforms:** DeepSeek, Claude, Z.AI, Codex, and any MCP-capable AI agent.  
> **Revision note:** The original audit focused on *static* quality dimensions (coverage, validation, compatibility). GLM's review identified a critical missing dimension: **adaptive learning across sessions** (GAP-000). This revision integrates that analysis alongside the original 24 gaps.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Layer-by-Layer Analysis](#2-layer-by-layer-analysis)
   - [2.1 MCP Server (`hoi4-mcp-server/`)](#21-mcp-server-hoi4-mcp-server)
   - [2.2 Agent Prompt (`hoi4-modder.agent.md`)](#22-agent-prompt-hoi4-modderagentmd)
   - [2.3 Syntax Reference (`SKILL.md`)](#23-syntax-reference-skillmd)
   - [2.4 Domain Skills (`.agents/skills/`)](#24-domain-skills-agentsskills)
   - [2.5 Codex Subagent Definitions (`.codex/agents/`)](#25-codex-subagent-definitions-codexagents)
   - [2.6 Offline Wiki (`paradox_wiki/`)](#26-offline-wiki-paradox_wiki)
   - [2.7 The Missing Dimension: Adaptive Learning (GAP-000)](#27-the-missing-dimension-adaptive-learning-gap-000)
3. [Cross-Platform Compatibility Matrix](#3-cross-platform-compatibility-matrix)
4. [Prioritized Gap Register](#4-prioritized-gap-register)
5. [Recommended Action Plan](#5-recommended-action-plan)
6. [Appendices](#6-appendices)

---

## 1. Project Overview

The HOI4-MCP project is a **comprehensive AI-assisted Hearts of Iron IV modding framework** that combines an MCP (Model Context Protocol) server, AI agent prompt engineering, domain-specific skills, and reference data.

### Architecture Diagram

```
┌──────────────────────────────────────────────────────────┐
│                    AI Agent Layer                         │
│  ┌─────────────────────┐  ┌───────────────────────────┐  │
│  │ hoi4-modder.agent.md│  │ SKILL.md (syntax ref)     │  │
│  │ (persona, workflow) │  │ (focuses, events, ideas…) │  │
│  └─────────────────────┘  └───────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐   │
│  │ .agents/skills/ (10 domain design guides)         │   │
│  │ events · decisions · focus-trees · assets ·       │   │
│  │ planning · animation · improvement-loop · mtth ·  │   │
│  │ subagents · text-audio-research                   │   │
│  └───────────────────────────────────────────────────┘   │
│  ┌───────────────────────────────────────────────────┐   │
│  │ .codex/agents/ (16 Codex-specific subagents) ⚠️   │   │
│  │ auditors · asset producers · researchers ·        │   │
│  │ planners · maintainers · explorer                 │   │
│  └───────────────────────────────────────────────────┘   │
├──────────────────────────────────────────────────────────┤
│                 MCP Server Layer                          │
│  ┌───────────────────────────────────────────────────┐   │
│  │ FastMCP Server (server.py)                        │   │
│  │ 7 tools + 2 resources                             │   │
│  └───────────────────────────────────────────────────┘   │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────┐   │
│  │ clausewitz/  │ │ tools/       │ │ db/            │   │
│  │ parser.py    │ │ indexer.py   │ │ vanilla_idx.py │   │
│  │ validator.py │ │ id_mgr.py    │ │ (SQLite)       │   │
│  │              │ │ error_log.py │ │                │   │
│  │              │ │ report.py    │ │                │   │
│  └──────────────┘ └──────────────┘ └────────────────┘   │
├──────────────────────────────────────────────────────────┤
│                 Data Layer                                │
│  ┌──────────────────────┐  ┌────────────────────────┐    │
│  │ paradox_wiki/        │  │ ~/.hoi4_mcp/vanilla.db │    │
│  │ (30+ offline MD ref) │  │ (8 tables, full index) │    │
│  └──────────────────────┘  └────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

### Key Metrics

| Metric | Value |
|--------|-------|
| Python source files | 8 (~2,500 lines) |
| MCP tools | 7 |
| MCP resources | 2 |
| Domain skills | 10 |
| Codex subagent definitions | 16 |
| Offline wiki pages | 30+ |
| Test files | **0** |
| CI/CD configuration | **None** |
| `.gitignore` | **Missing** |

---

## 2. Layer-by-Layer Analysis

### 2.1 MCP Server (`hoi4-mcp-server/`)

#### Tools Inventory

| Tool | Status | Quality |
|------|--------|---------|
| `get_mod_index` | ✅ Implemented | Good — supports `summary_only` and `refresh` flags |
| `get_next_id` | ✅ Implemented | Good — covers event/focus/decision/character |
| `check_id_exists` | ✅ Implemented | Good — supports scoped checking |
| `search_mod` | ✅ Implemented | Good — subdir filter, glob pattern, max results |
| `validate_syntax` | ✅ Implemented | Good — Clausewitz + YML, structured error output |
| `get_latest_errors` | ✅ Implemented | Good — auto-detects log path, 11 error categories |
| `lookup_vanilla` | ✅ Implemented | Good — 8 query types, exact + search modes |
| `generate_province_rgb` | ✅ Implemented | Good — colorsys-based, avoids duplicates |

#### Strengths

- **Clean architecture.** Clear separation between `clausewitz/` (parsing), `tools/` (mod operations), and `db/` (vanilla data).
- **Clausewitz tokenizer/parser** is robust — handles comments, quoted strings (with escapes), bare words, numbers, nested blocks, and duplicate keys as lists. Token-level line/col tracking enables precise error reporting.
- **Validator** catches bracket mismatches, missing `=` signs, consecutive operators, `hide_window` without `is_triggered_only`, missing `completion_reward`, and scope mismatches.
- **Error log parser** classifies errors into 11 categories: `unexpected_token`, `duplicate_id`, `invalid_scope`, `missing_loc`, `missing_texture`, `invalid_province`, `bad_trigger`, `parse_error`, `missing_file`, `database_error`, `unknown`.
- **Vanilla DB** schema covers 8 tables with proper indexes on `tree_id` and `namespace`.
- **HTML report generator** produces self-contained, dark-themed, interactive reports with tabbed navigation and search.
- **`setup.sh`** auto-detects HOI4 install paths across common Steam directories.
- **Lazy initialization** pattern — caches are built on first access, not at server startup.

#### Gaps

##### 🔴 GAP-001: No Test Suite
**Severity:** Critical  
**Impact:** Any change to the parser, validator, indexer, or ID manager risks silent regressions. The parser handles complex Clausewitz edge cases — without tests, confidence in correctness is low.

**What's missing:**
- Unit tests for `ClausewitzTokenizer` (tokenization of strings, comments, bare words, numbers, braces, edge cases like empty files, BOM, Windows line endings)
- Unit tests for `ClausewitzParser` (nested blocks, duplicate keys, empty blocks, large files)
- Unit tests for `validate_clausewitz` and `validate_localisation` (bracket matching, missing =, hide_window detection, YML format violations)
- Unit tests for `ModIndexer` (ID extraction from all file types, namespace detection)
- Unit tests for `IDManager` (next ID logic, collision detection)
- Unit tests for `error_log` parser (all 11 classification patterns)
- Integration tests for `VanillaDBBuilder` and `VanillaLookup` (requires a HOI4 install or test fixtures)

**Recommendation:** Add `tests/` directory with `pytest`. Start with parser and validator tests (highest blast radius). Use fixture files (small synthetic `.txt` and `.yml` files) rather than requiring a full HOI4 install.

##### 🔴 GAP-002: Structured Error Responses
**Severity:** Critical  
**Impact:** When tools fail (missing mod path, DB not built, file not found), they return plain-text error strings. The AI agent must parse error messages to determine what went wrong — fragile and breaks programmatic error recovery.

**What's missing:**
- All tool error paths should return structured JSON with at minimum: `{"success": false, "error_code": "MOD_PATH_NOT_CONFIGURED", "message": "...", "help": "..."}`
- MCP supports error types natively — consider using `mcp.types.ErrorContent` or raising structured exceptions

**Files affected:** `server.py` — every tool's error path.

##### 🟠 GAP-003: No Pagination on `get_mod_index`
**Severity:** High  
**Impact:** Large mods (total conversion, overhaul) could have thousands of events, focuses, and ideas. The full JSON response may exceed AI context windows or cause timeout issues.

**What's missing:**
- `page` and `page_size` parameters on `get_mod_index`
- Or a `category` filter to request only specific index sections (e.g., `category="events"`)

##### 🟠 GAP-004: Single Mod Path Binding
**Severity:** High  
**Impact:** The server binds to one `--mod-path` at startup. Modders working on multiple mods must restart the server or run multiple server instances. No workspace switching.

**What's missing:**
- A `set_mod_path` tool to switch active mod without restarting
- Or multi-mod support with `mod_id` parameter on each tool

##### 🟠 GAP-005: Vanilla DB — No Incremental Updates
**Severity:** High  
**Impact:** When HOI4 receives a DLC or patch with new focuses/events/ideas, the entire vanilla DB must be rebuilt from scratch. No way to update specific tables.

**What's missing:**
- Version tracking in the DB (store game version/checksum)
- Incremental indexing of specific directories
- A `--update` flag that only re-indexes changed files

##### 🟡 GAP-006: No File Watcher for Cache Invalidation
**Severity:** Medium  
**Impact:** After the AI agent edits mod files, it must remember to call `get_mod_index(refresh=true)`. If it forgets, subsequent tool calls return stale data.

**What's missing:**
- Optional `watchdog`-based file watcher (already a dev dependency!) that auto-invalidates the cache when mod files change
- Or a `last_modified` check before returning cached data

##### 🟡 GAP-007: Fragile Path Handling in `find_error_log()`
**Severity:** Medium  
**Impact:** `find_error_log()` has hardcoded OS-specific paths:
- Linux: `~/.local/share/Paradox Interactive/Hearts of Iron IV/logs/error.log`
- macOS: `~/Documents/Paradox Interactive/Hearts of Iron IV/logs/error.log`
- Windows: `%USERPROFILE%\Documents\Paradox Interactive\Hearts of Iron IV\logs\error.log`

These paths can differ for GOG, Microsoft Store, or custom install locations.

**Recommendation:** Add a `--error-log-path` CLI flag and `HOI4_ERROR_LOG` env var. Document the auto-detection fallback clearly.

##### 🟡 GAP-008: No Environment Variable Configuration Fallback for All Options
**Severity:** Medium  
**Impact:** Only `HOI4_MOD_PATH`, `HOI4_VANILLA_PATH`, and `HOI4_VANILLA_DB` are read from env vars. The error log path, report output, and other options are CLI-only.

##### 🟢 GAP-009: No Mod Packaging Tool
**Severity:** Low  
**Impact:** Modders must manually create `.zip` archives with correct directory structure for Steam Workshop or Paradox Forum distribution.

**Recommendation:** Add a `package_mod` tool that validates the mod, creates a properly structured zip, and generates/validates the `.mod` metadata file.

##### 🟢 GAP-010: No Docker/Container Setup
**Severity:** Low  
**Impact:** Setup requires Python 3.10+, pip, and manual configuration. Containerized setup would simplify onboarding.

##### 🟢 GAP-011: `VANILLA_MODIFIERS` Dictionary Is Hardcoded
**Severity:** Low  
**Impact:** The 350+ modifier entries in `vanilla_index.py` are hand-maintained. New modifiers added in DLCs/patches won't be in the dictionary until manually added. Missing entries mean `lookup_vanilla(query_type="modifier")` returns incomplete results.

**Recommendation:** Consider parsing modifier definitions from vanilla game files at DB build time rather than maintaining a hardcoded dictionary. Or add a mechanism to merge hardcoded entries with parsed entries.

---

### 2.2 Agent Prompt (`hoi4-modder.agent.md`)

#### Strengths

- **Clear 3-phase workflow** (Establish Context → Generate Code → Self-Correction Loop) with explicit MCP vs. manual fallback paths
- **Strong constraint list** preventing common HOI4 modding mistakes (no modifiers in `completion_reward`, no `is_triggered_only` + MTTH, correct effect/trigger names)
- **Design quality standards** (anti-fairy-dust, real focus branches, decisions as actions, idea lifecycles, AI navigation, dynamic values)
- **Execute tool guardrails** preventing destructive commands and game install modifications
- **Console command cheat sheet** for testing
- **Persona definition**: neutral, professional, teaching-oriented with "Why:" explanations

#### Gaps

##### 🟡 GAP-012: Massive Prompt Size
**Severity:** Medium  
**Impact:** ~200 lines / ~8,000 characters. For context-constrained models or sessions with large mod files, this prompt consumes significant tokens before any work begins.

**What's missing:**
- No mechanism to load a "quick mode" or "minimal" variant
- The prompt is all-or-nothing

**Recommendation:** Add inline `<!-- TRIM: start -->` / `<!-- TRIM: end -->` markers around sections that can be omitted for quick sessions (e.g., design quality standards, console commands, skill ecosystem). Document which sections are essential vs. optional.

##### 🟡 GAP-013: No Skill Selection Decision Tree
**Severity:** Medium  
**Impact:** The prompt mentions that 10 skills exist but doesn't guide the agent on *when* to load which skill. An agent might load all skills (context-expensive) or none (missing guidance).

**What's missing:**
- A decision tree: "If the task involves events → load `hoi4-events` skill. If events need pictures → also load `hoi4-feature-assets`."
- Or a `load_skill` MCP tool that returns the relevant skill content on demand

##### 🟢 GAP-014: Reference to Codex-Only Infrastructure
**Severity:** Low  
**Impact:** The "Skill & Reference Ecosystem" section says ".codex/agents/ (reference only): These TOML files document subagent patterns... They are Codex-specific and cannot be spawned directly on non-Codex models." This is accurate but confusing — why include them at all for non-Codex agents?

**Recommendation:** For non-Codex deployments, either omit this section or restructure it to describe what the subagents *do* (as design patterns) rather than what they *are* (as Codex entities).

---

### 2.3 Syntax Reference (`SKILL.md`)

#### Coverage Map

| System | Covered? | Depth | Notes |
|--------|----------|-------|-------|
| Focus Trees | ✅ | Comprehensive | Structure, rules, pitfalls, `allow_branch` vs `available` |
| Events (country) | ✅ | Comprehensive | `is_triggered_only`, `hide_window`, MTTH, `immediate`, options |
| Events (news) | ✅ | Good | Structure with example |
| On Actions | ✅ | Comprehensive | 18 hooks with scope notes |
| Decisions | ✅ | Good | Structure, `allowed`/`available`/`visible` distinction |
| Missions | ✅ | Good | `target_trigger`, `completed_trigger`, `targeted` |
| National Spirits/Ideas | ✅ | Good | Structure, advisor slots, categories |
| Characters (NSB) | ✅ | Good | Multi-role, portrait specs, `id = -1` |
| Country History | ✅ | Good | Full command table, DLC-gating pattern |
| State History | ✅ | Good | Owner/controller distinction, building levels |
| Vanilla Modifiers | ✅ | Comprehensive | ~100+ modifiers across 6 categories |
| Technology Trees | ❌ | Missing | No section |
| Equipment Modding | ❌ | Missing | No section |
| Map Modding | ❌ | Missing | No section (only province RGB tool, no syntax) |
| Scripted GUI | ❌ | Missing | No section |
| MIOs (Military Industrial Organizations) | ❌ | Missing | Post-1.12 system |
| Balance of Power | ❌ | Missing | Post-1.12 system |
| International Market | ❌ | Missing | Post-1.13 system |
| AI Strategies | ❌ | Missing | No section |
| Ideology Modding | ❌ | Missing | No section |
| Cosmetic Tags | ❌ | Missing | No section |
| Country Creation | ❌ | Missing | No section (wiki exists but no skill integration) |
| Faction Modding | ❌ | Missing | No section |
| Intelligence Agency | ❌ | Missing | No section |
| Namelist Modding | ❌ | Missing | No section |

#### Gaps

##### 🟠 GAP-015: Missing System Coverage
**Severity:** High  
**Impact:** 14 HOI4 modding systems have no syntax reference in SKILL.md. Agents working on these systems must rely on training data (hallucination-prone) or the offline wiki (which has the data but isn't structured as agent reference).

**Systems most needed (by modding frequency):**
1. Technology Trees — nearly every mod touches these
2. Equipment Modding — common for total conversions and alt-history
3. AI Strategies — required for AI to navigate custom focus trees
4. Map Modding — province, state, strategic region definitions
5. Scripted GUI — increasingly common for custom UI

##### 🟡 GAP-016: No Version/Date Tracking
**Severity:** Medium  
**Impact:** No way to know if the reference is current against HOI4 1.15.x. If the game's syntax changes in a patch, the reference silently becomes outdated.

**Recommendation:** Add a `last_updated` and `game_version` field at the top of SKILL.md.

---

### 2.4 Domain Skills (`.agents/skills/`)

#### Inventory

| Skill | Lines (approx.) | Quality | Concrete Examples? | Codex References? |
|-------|-----------------|---------|-------------------|-------------------|
| `hoi4-events` | ~80 | ⭐⭐⭐⭐ | Moderate | Yes — references `hoi4_localisation_auditor`, `hoi4_scripted_system_architect` |
| `hoi4-decisions-missions` | ~60 | ⭐⭐⭐ | Moderate | Some |
| `hoi4-focus-trees` | ~60 | ⭐⭐⭐ | Moderate | Some |
| `hoi4-feature-assets` | ~100 | ⭐⭐⭐⭐ | Yes — includes `process_report_event_image.py` tool | Yes — references `hoi4_asset_source_researcher`, `hoi4_generated_feature_art`, `hoi4_icon_artist` |
| `hoi4-feature-planning` | ~80 | ⭐⭐⭐ | Low | Some |
| `hoi4-improvement-loop` | ~100 | ⭐⭐⭐ | Low | Yes — references `hoi4_improvement_loop_planner` |
| `hoi4-frame-animation` | ~60 | ⭐⭐⭐ | Moderate | Some |
| `hoi4-mtth` | ~40 | ⭐⭐⭐⭐ | Good — code examples | Minimal |
| `hoi4-subagents` | ~200 | ⭐⭐⭐⭐ | N/A (meta-skill) | 🔴 Entirely about Codex subagents |
| `hoi4-text-audio-research` | ~60 | ⭐⭐⭐ | Moderate | Yes — references research subagents |

#### Gaps

##### 🔴 GAP-017: `hoi4-subagents` Skill Is Codex-Only
**Severity:** Critical  
**Impact:** This 200-line skill is the orchestration layer for ALL specialized subagent work. It covers fork context rules, authority model, handoff format, and task routing to 16 subagents. **None of this works on DeepSeek, Claude, or Z.AI.** These platforms have different subagent/task-decomposition mechanisms or none at all.

**What's needed:**
- A platform-agnostic version that describes *what* specialized checks each workflow needs (as structured checklists or specs) rather than *how* to spawn Codex subagents
- Alternatively, convert subagent logic into MCP tools that any agent can call

##### 🔴 GAP-018: Skills Reference Non-Existent `AGENTS.md`
**Severity:** Critical  
**Impact:** Multiple skills say "Repository-wide reading and style rules live in `AGENTS.md`" or "Read AGENTS.md" — but no `AGENTS.md` file exists in the repository. Agents following these instructions will waste time searching for a missing file.

**Recommendation:** Either create `AGENTS.md` with project-wide conventions, or remove the references from skills.

##### 🟠 GAP-019: Missing Skill Coverage
**Severity:** High  
**Impact:** No skills exist for these modding domains (matching GAP-015):
- Technology Trees
- Equipment Modding
- Map Modding
- Scripted GUI
- MIOs
- Balance of Power
- AI Strategies
- Ideology Modding
- Country Creation
- Cosmetic Tags
- Intelligence Agency

##### 🟡 GAP-020: Abstract Over Concrete
**Severity:** Medium  
**Impact:** Skills like `hoi4-improvement-loop` and `hoi4-feature-planning` are heavy on design philosophy ("recursive feature deepening", "stop conditions", "anti-bloat rules") but light on actionable templates. An AI agent needs concrete input/output examples to reliably execute the skill's guidance.

**What each skill should ideally have:**
- A "Quick Start" section with a minimal working example
- A "Common Patterns" section with 2-3 copy-paste templates
- A "Validation Checklist" section with a bullet list of pre-flight checks
- The existing deep design guidance (keep this, just add the above)

##### 🟡 GAP-021: No Cross-Skill Dependency Map
**Severity:** Medium  
**Impact:** Skills reference each other but there's no explicit dependency graph. An agent might miss that `hoi4-events` needs `hoi4-feature-assets` for event pictures, or that `hoi4-focus-trees` needs `hoi4-events` for focus-triggered events.

**Recommendation:** Add a dependency section at the top of each skill: "**Requires:** `hoi4-feature-assets` (for event pictures), `hoi4-text-audio-research` (for quotes)."

---

### 2.5 Codex Subagent Definitions (`.codex/agents/`)

#### Inventory

| Subagent | Type | Purpose |
|----------|------|---------|
| `hoi4_repo_explorer` | Read-only explorer | Maps files, patterns, vanilla precedents, edit order |
| `hoi4_focus_tree_auditor` | Patch-capable auditor | Audits/patches focus route logic, prerequisites, AI, icons |
| `hoi4_decision_mission_auditor` | Patch-capable auditor | Audits/patches decisions, missions, costs, tooltips |
| `hoi4_country_package_auditor` | Patch-capable auditor | Audits/patches tags, states, leaders, flags, parties |
| `hoi4_localisation_auditor` | Patch-capable auditor | Audits/patches localisation keys, scripted loc, tooltips |
| `hoi4_scripted_system_architect` | Patch-capable architect | Creates reusable scripted effects/triggers/constants |
| `hoi4_improvement_loop_planner` | Plan-only | Writes deep expansion addenda (no gameplay patches) |
| `hoi4_feature_completion_auditor` | Read-only auditor | Compares specs vs implementation |
| `hoi4_documentation_curator` | Patch-capable (docs only) | Reconciles specs, plans, handoffs, manifests, READMEs |
| `hoi4_asset_source_researcher` | Asset production | Finds/verifies/processes real archival images |
| `hoi4_generated_feature_art` | Asset production | Generates fictional/symbolic art via `$imagegen` |
| `hoi4_icon_artist` | Asset production | Creates generated icon packages |
| `hoi4_quote_remark_researcher` | Research | Finds/verifies quotes, cultural remarks, slogans |
| `hoi4_audio_researcher` | Research | Researches licensed/public-domain audio, converts to `.ogg` |
| `hoi4_skill_maintainer` | Skill maintenance | Creates/updates/audits `.agents/skills/` |
| `hoi4_spreadsheet_doc_worker` | Documentation | Updates mod-maintained CSV/XLSX tables |

#### Assessment

##### 🔴 GAP-022: Entirely Codex-Specific — Cannot Be Used by Other AI Agents
**Severity:** Critical  
**Impact:** These 16 TOML files represent the most sophisticated part of the project's task-decomposition system. They define specialized worker agents with detailed instructions, sandbox modes, and tool access. **DeepSeek, Claude, Z.AI, and any non-Codex agent cannot parse or spawn these subagents.** The files are effectively dead weight for any platform other than Codex.

**The core value of each subagent is NOT the TOML wrapper — it's the specialized knowledge of WHAT to check, HOW to validate, and WHAT patterns to look for.** This knowledge needs to be extracted into a platform-agnostic format.

**Recommendation:** For each subagent, create a companion `.md` file (or section in a unified document) that captures:
1. **Purpose:** What this specialized check does
2. **Checklist:** The exact things to verify (in checklist format an agent can execute inline)
3. **Common issues:** Known failure patterns
4. **Output format:** What the result should look like

The TOML files can remain for Codex users. The `.md` checklists make the same knowledge usable everywhere.

---

### 2.6 Offline Wiki (`paradox_wiki/`)

#### Assessment

- **30+ markdown files** covering most HOI4 modding systems
- **No version tracking** — unclear which HOI4 version these snapshots correspond to
- **No index/README** — no way to know which files cover which topics without listing the directory
- **`_last_updated_on_27_Nov_2025.txt`** file exists but is a single marker — individual pages may be older/newer

#### Gaps

##### 🟢 GAP-023: No Wiki Index or Cross-Reference
**Severity:** Low  
**Impact:** Agents must list the directory to discover available topics. An index file mapping topic → file would enable faster lookups.

##### 🟢 GAP-024: Unclear Update Cadence
**Severity:** Low  
**Impact:** The single `_last_updated` file implies all pages were updated on the same date, which is unlikely. Per-page "last verified against game version" headers would be more useful.

---

### 2.7 The Missing Dimension: Adaptive Learning (GAP-000)

> **Credit:** This gap and its proposed architecture were identified by GLM's review of the original audit. What follows integrates GLM's analysis with additional connections to existing infrastructure.

#### The Core Problem

The audit identified 24 gaps in *static* quality: parsing, validation, coverage, compatibility. But it missed the **dynamic** dimension entirely: **the system doesn't learn.**

Every session starts from zero. An agent that catches its own mistake on Monday will make the same mistake on Tuesday. A human who corrects a pattern on Wednesday won't benefit from that correction being auto-enforced on Thursday. The agent prompt contains hardcoded constraints (e.g., "DO NOT combine `is_triggered_only` with MTTH"), but these are static — they don't grow with experience.

This is **GAP-000** — the adaptive learning gap. It should be the highest-priority addition because it amplifies the value of every other fix: better validation → better mistake detection → better learned rules → fewer repeated mistakes.

#### Existing Learning-Adjacent Infrastructure

The codebase already has several components that could feed into or benefit from a learning system:

| Component | What It Does | Learning Potential |
|-----------|-------------|-------------------|
| `validate_clausewitz()` | Detects bracket mismatches, `hide_window` without `is_triggered_only`, missing `completion_reward` | Warnings could auto-generate learned rules when same pattern occurs across multiple files |
| `validate_localisation()` | Checks YML format, BOM, unescaped quotes, empty values | Recurring format violations could become convention rules |
| `ERROR_PATTERNS` (11 categories) | Classifies game log errors by type | Recurring errors (3+ occurrences) should trigger rule proposals |
| Agent prompt hard constraints | ~8 hardcoded "DO NOT" rules (e.g., no modifiers in `completion_reward`) | These should be bootstrapped as initial learned rules, not buried in a static prompt |
| `VANILLA_MODIFIERS` dict | 350+ hardcoded modifier→description mappings | This is effectively static learned knowledge — should be queryable through the same system |

#### Proposed Architecture: Adaptive Learning & Mistake Memory System

**Design principles:**
1. **Server-side persistence** — Rules live in SQLite (`learned_rules.db`) with `.jsonl` export for repo sharing. Not in prompts or skills files. Survives server restarts, works on every platform.
2. **Dual-source capture** — Rules recorded when the agent self-corrects AND when a human corrects the agent. Both produce the same structured rule format.
3. **Pre-flight injection** — Before generating any code, the agent queries active rules for the relevant context and enforces them as hard constraints (new Phase 0 in the agent prompt).

**4 new MCP tools:**

| Tool | Purpose |
|------|---------|
| `record_mistake(category, context, context_tags, pattern, correction, severity, source)` | Record a learned rule from a caught mistake. Returns rule ID (e.g., LR-0001). |
| `get_learned_rules(context_tags, category, severity, include_resolved)` | Retrieve active rules filtered by context. Agent MUST call before generating code. |
| `resolve_mistake(rule_id, note, superseded_by)` | Mark a rule as resolved/inactive (game patch, design change). |
| `export_learned_rules(format, include_resolved)` | Export all rules as `.jsonl` (one JSON per line) for repo commit and team sharing. |

**Database schema (separate from `vanilla.db`):**

```sql
CREATE TABLE learned_rules (
    id              TEXT PRIMARY KEY,       -- LR-0001, LR-0002, ...
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    category        TEXT NOT NULL           -- syntax|logic|design|scope|localisation|id_collision|convention|performance
        CHECK(category IN ('syntax','logic','design','scope','localisation','id_collision','convention','performance')),
    severity        TEXT NOT NULL DEFAULT 'error'  -- error|warning|style
        CHECK(severity IN ('error','warning','style')),
    context         TEXT NOT NULL,          -- Human-readable: "Events with MTTH blocks"
    context_tags    TEXT DEFAULT '',        -- Machine-searchable: "events,mtth,triggers"
    pattern         TEXT NOT NULL,          -- What the mistake looks like (the ANTI-pattern)
    correction      TEXT NOT NULL,          -- What to do instead
    source          TEXT NOT NULL           -- agent_self_correction|human_correction|game_log|validation
        CHECK(source IN ('agent_self_correction','human_correction','game_log','validation')),
    file_path       TEXT DEFAULT '',
    line_range      TEXT DEFAULT '',
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    last_triggered_at TEXT,
    resolved        INTEGER NOT NULL DEFAULT 0,
    resolved_at     TEXT,
    resolved_note   TEXT DEFAULT '',
    superseded_by   TEXT DEFAULT ''
);
```

**Deduplication strategy:** Before recording a new rule, fuzzy-match against existing rules using token-overlap (Jaccard similarity on tokenized pattern text, weighted by context_tags overlap). No embedding model or vector DB needed — token overlap at threshold ≥0.7 is sufficient for structured anti-pattern descriptions. If a match is found, increment `occurrence_count` on the existing rule rather than creating a duplicate.

**Agent prompt integration (new Phase 0):**

```markdown
## Phase 0: Load Learned Rules (MANDATORY — every code generation)

Before writing ANY Clausewitz code:
1. Determine which system you're working on (events, focus_trees, decisions, etc.)
2. Call get_learned_rules(context_tags="<system>")
3. For each rule with severity="error": treat the pattern as a HARD BLOCK
4. For each rule with severity="warning": treat as strong suggestion
5. For each rule with severity="style": apply as convention

If you generate code violating an active error-rule, that is a workflow failure.
```

**Human Correction Protocol:**

```markdown
When the human corrects your work:
1. Parse what the mistake was and what the correct approach is
2. Apply the fix to the code
3. Call record_mistake(source="human_correction", ...)
4. Respond: "Recorded as learned rule LR-XXXX. This pattern will not be repeated."

Human corrections are the HIGHEST PRIORITY learning signal.
```

**Auto-learning from game logs:** The `get_latest_errors` tool should gain a `detect_recurring` parameter. When enabled, it groups errors by (category + normalized message) and flags patterns appearing ≥3 times as suggested learned rules. The agent proposes these to the human — never auto-records, because one-off development errors shouldn't become permanent rules.

**Concrete example — before vs. after:**

*Without learning system:*
```
Human: "Add a focus that gives Germany +5% infantry attack"
Agent generates:
  completion_reward = {
      modifier = { infantry_attack = 0.05 }  ← SILENTLY BROKEN
  }
```

*With learning system (LR-0002 exists from prior correction):*
```
Agent calls get_learned_rules(context_tags="focus_trees,completion_reward")
Receives LR-0002: "Placing modifier = { } directly in completion_reward — 
  game engine doesn't apply static modifiers. Use add_ideas_effect instead."
Agent generates:
  completion_reward = {
      add_ideas_effect = { idea = GER_spirit_infantry_5pct }  ← CORRECT
  }
Agent also creates the matching national spirit file because LR-0002 implies it.
```

#### Refinements Beyond GLM's Proposal

While GLM's architecture is sound, the following additions strengthen the connection to existing infrastructure:

1. **Bootstrap from existing constraints.** The 8 hardcoded "DO NOT" rules in `hoi4-modder.agent.md` should be migrated as initial seed rules in `learned_rules.db`. This gives the learning system starting knowledge and proves the pipeline works before any sessions run. The agent prompt can then reference "see learned rules for current constraints" rather than duplicating them.

2. **Validator → learning pipeline.** The `validate_clausewitz()` function already detects patterns like `hide_window` without `is_triggered_only`. When validation runs on a file and finds the SAME warning type multiple times, it should suggest recording a learned rule. This closes the loop: validation doesn't just report errors, it feeds the learning system.

3. **Promotion path to permanent knowledge.** When a learned rule reaches `occurrence_count ≥ 10` and has survived for ≥30 days without being resolved, the system should flag it for promotion: either into `SKILL.md` (as a documented pitfall) or into the agent prompt (as a hard constraint). This prevents the learning DB from becoming the only source of truth — the most battle-tested rules graduate into permanent documentation.

4. **`VANILLA_MODIFIERS` as queryable learned knowledge.** The 350+ hardcoded modifier descriptions should be importable into the learning DB under a special `source='vanilla_reference'` category. This unifies all knowledge retrieval through one tool (`get_learned_rules`) rather than splitting between `lookup_vanilla` and learned rules.

5. **Confidence decay for agent-self-corrected rules.** Rules with `source='agent_self_correction'` should have lower initial confidence than `source='human_correction'`. If an agent-self-corrected rule is never triggered again after 30 days, it could be auto-resolved as low-confidence. Human corrections are permanent until explicitly resolved.

#### Implementation Module Structure

```
hoi4-mcp-server/src/hoi4_mcp/
├── learning/
│   ├── __init__.py
│   ├── db.py           # LearnedRulesDB — SQLite wrapper (create, query, update, resolve)
│   ├── rules.py        # Rule CRUD, validation, deduplication (token-overlap fuzzy match)
│   ├── exporter.py     # JSON/Markdown export, .jsonl sync with mod repo
│   ├── detector.py     # Recurring pattern detection from error logs
│   └── seeder.py       # Bootstrap initial rules from agent prompt constraints
├── server.py           # Add 4 new tool registrations + detect_recurring on get_latest_errors
└── ...
```

---

## 3. Cross-Platform Compatibility Matrix

| Component | Codex | DeepSeek | Claude Desktop | Z.AI | Generic MCP Client |
|-----------|-------|----------|----------------|------|--------------------|
| **MCP Server (stdio)** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **MCP Tools** (7 tools) | ✅ | ✅ | ✅ | ✅ | ✅ |
| **MCP Resources** (2 URIs) | ✅ | ✅ | ✅ | ✅ | ✅ |
| **`hoi4-modder.agent.md`** (prompt) | ✅ | ⚠️¹ | ⚠️¹ | ⚠️¹ | ⚠️¹ |
| **`SKILL.md`** (syntax ref) | ✅ | ✅ | ✅ | ✅ | ✅ |
| **`.agents/skills/`** (10 skills) | ✅ | ✅ | ✅ | ✅ | ✅ |
| **`.codex/agents/`** (16 subagents) | ✅ | ❌ | ❌ | ❌ | ❌ |
| **`paradox_wiki/`** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **`process_report_event_image.py`** | ✅ | ✅² | ✅² | ✅² | ✅² |

**Notes:**
1. ⚠️ = Depends on whether the platform supports custom system/agent prompts. Claude Desktop supports custom system prompts via project config. DeepSeek API supports system messages. Z.AI support varies. Generic MCP clients may or may not support prompt files.
2. ✅² = Requires Python environment with Pillow. Can be executed as a subprocess by any agent with shell access.

### Platform-Specific Concerns

| Concern | DeepSeek | Claude | Z.AI |
|---------|----------|--------|------|
| Custom system prompt support | ✅ (API) | ✅ (projects) | ⚠️ (varies) |
| MCP client implementation | ✅ (via API) | ✅ (Desktop) | ⚠️ (varies) |
| Subagent/task-decomposition | ❌ (no native subagents) | ❌ (no native subagents) | ❌ (no native subagents) |
| Tool calling | ✅ | ✅ | ✅ |
| Context window size | 128K-1M tokens | 200K tokens | Varies |
| File read/write | ✅ | ✅ | ✅ |

**Key insight:** Only Codex has native subagent spawning. For all other platforms, the subagent orchestration pattern must be replaced with either:
- Inline checklists the main agent executes itself
- Additional MCP tools that encapsulate the specialized logic server-side
- A combination of both

---

## 4. Prioritized Gap Register

### 🔴 Critical (blocks functionality or cross-platform usage)

| ID | Gap | Files/Components | Effort | Owner Suggestion |
|----|-----|------------------|--------|------------------|
| **GAP-000** | **No adaptive learning system — mistakes repeat across sessions** | New `learning/` module, `server.py` (4 new tools), `hoi4-modder.agent.md` (Phase 0) | **Medium** (~400 lines, 1-2 days) | **Python developer + Agent engineer** |
| GAP-022 | Codex subagents unusable by other platforms | `.codex/agents/` (16 files), `hoi4-subagents` skill | Large | Agent engineer |
| GAP-017 | `hoi4-subagents` skill is Codex-only | `.agents/skills/hoi4-subagents/SKILL.md` | Medium | Skill author |
| GAP-018 | Skills reference missing `AGENTS.md` | Multiple skills | Small | Skill author |
| GAP-001 | No test suite | All `src/hoi4_mcp/` | Large | Python developer |
| GAP-002 | Structured error responses missing | `server.py` (all tool error paths) | Medium | Python developer |

### 🟠 High (significant capability gaps)

| ID | Gap | Files/Components | Effort | Owner Suggestion |
|----|-----|------------------|--------|------------------|
| GAP-015 | Missing syntax reference for 14 systems | `SKILL.md` | Large | HOI4 modding expert |
| GAP-019 | Missing skill coverage for 11 domains | `.agents/skills/` (new files) | Large | HOI4 modding expert |
| GAP-003 | No pagination on `get_mod_index` | `server.py` | Small | Python developer |
| GAP-004 | Single mod path binding | `server.py`, `ServerConfig` | Medium | Python developer |
| GAP-005 | Vanilla DB no incremental updates | `db/vanilla_index.py` | Medium | Python developer |

### 🟡 Medium (quality & hygiene)

| ID | Gap | Files/Components | Effort | Owner Suggestion |
|----|-----|------------------|--------|------------------|
| GAP-012 | Massive agent prompt size | `hoi4-modder.agent.md` | Small | Agent engineer |
| GAP-013 | No skill selection decision tree | `hoi4-modder.agent.md` | Small | Agent engineer |
| GAP-020 | Skills too abstract (need concrete examples) | Multiple skills | Medium | Skill author |
| GAP-021 | No cross-skill dependency map | All skills | Small | Skill author |
| GAP-006 | No file watcher for cache invalidation | `server.py` | Small | Python developer |
| GAP-007 | Fragile `find_error_log()` paths | `tools/error_log.py` | Small | Python developer |
| GAP-008 | No env var fallback for all CLI options | `server.py` | Small | Python developer |
| GAP-016 | No version tracking in SKILL.md | `SKILL.md` | Trivial | Any |

### 🟢 Low (nice to have)

| ID | Gap | Files/Components | Effort | Owner Suggestion |
|----|-----|------------------|--------|------------------|
| GAP-009 | No mod packaging tool | New tool in `tools/` | Medium | Python developer |
| GAP-010 | No Docker/container setup | New `Dockerfile` | Small | DevOps |
| GAP-011 | Hardcoded `VANILLA_MODIFIERS` dict | `db/vanilla_index.py` | Medium | Python developer |
| GAP-014 | Codex references in agent prompt | `hoi4-modder.agent.md` | Trivial | Agent engineer |
| GAP-023 | No wiki index | `paradox_wiki/` | Small | Any |
| GAP-024 | Unclear wiki update cadence | `paradox_wiki/` | Small | Any |

---

## 5. Recommended Action Plan

Based on the user's confirmed preferences:
- **Agent Prompt Strategy:** Keep single file, add trim guide
- **Subagent Orchestration:** Both approaches (inline checklists + MCP tools)
- **Multi-Mod Support:** High priority
- **Skill Format:** Keep current format (philosophy + syntax mix)

### Phase 0: Learning System (Weeks 1-2) — NEW, Highest Priority

> **Rationale:** GAP-000 is force-multiplying. Every other improvement is a one-time quality boost. The learning system is a **compounding** quality boost — it gets better the more it's used, and it benefits from every other improvement (better validation → better mistake detection → better rules).

```
Week 1: Core learning infrastructure
├── 0.1  Create learning/ module (db.py, rules.py, exporter.py, seeder.py)
├── 0.2  Add 4 new MCP tools to server.py (record_mistake, get_learned_rules,
│        resolve_mistake, export_learned_rules)
├── 0.3  Add detect_recurring parameter to get_latest_errors
├── 0.4  Bootstrap seed rules from existing agent prompt hard constraints
└── 0.5  Add unit tests for learning module (CRUD, dedup, export)

Week 2: Agent integration
├── 0.6  Update agent prompt: add Phase 0 (Load Learned Rules)
├── 0.7  Update agent prompt: add Human Correction Protocol
├── 0.8  Update agent prompt: update Self-Correction Loop to call record_mistake
├── 0.9  Add trim markers to agent prompt (GAP-012) — done alongside Phase 0 edits
└── 0.10 Test end-to-end: mistake → record → query → enforcement on next session
```

### Phase 1: Foundation (Weeks 3-5)

```
Week 3: Critical fixes
├── 1.1 Create AGENTS.md with project-wide conventions (GAP-018)
├── 1.2 Add structured error responses to all MCP tools (GAP-002)
└── 1.3 Create test infrastructure + parser/validator tests (GAP-001)

Week 4-5: Cross-platform compatibility
├── 1.4 Extract subagent logic into platform-agnostic checklists (GAP-022)
│       └── Create .agents/checklists/ with one .md per subagent domain
├── 1.5 Update hoi4-subagents skill to reference checklists (GAP-017)
├── 2.1 Add pagination to get_mod_index (GAP-003)
└── 2.2 Add multi-mod/project switching support (GAP-004)
```

### Phase 2: Expansion (Weeks 6-10)

```
Weeks 6-7: Content coverage
├── 3.1 Add missing syntax reference sections to SKILL.md (GAP-015)
│       Priority: tech trees, equipment, AI strategies, map modding, scripted GUI
├── 3.2 Create missing domain skills (GAP-019)
│       Priority: tech trees, equipment, AI strategies
├── 3.5 Add cross-skill dependency map to each skill (GAP-021)
└── 4.5 Add concrete examples to abstract skills (GAP-020)

Weeks 8-10: Learning system hardening + quality
├── 0.11 Add validator→learning pipeline (auto-suggest rules from recurring validation warnings)
├── 0.12 Add promotion path (high-occurrence rules → SKILL.md permanent pitfalls)
├── 0.13 Add confidence decay for agent-self-corrected rules
├── 4.1 Complete test suite (remaining components from GAP-001)
├── 4.2 Add .gitignore, CI/CD, linting config
├── 2.3 Add env var fallback for all CLI options (GAP-008)
└── 2.4 Fix find_error_log() path handling (GAP-007)
```

### Phase 3: Polish (Ongoing)

```
├── 4.3 Vanilla DB incremental update support (GAP-005)
├── 4.4 File watcher for cache invalidation (GAP-006)
├── 5.1 Docker/container setup (GAP-010)
├── 5.2 Mod packaging tool (GAP-009)
├── 5.3 Dynamic vanilla modifier parsing (GAP-011)
├── 5.4 Wiki index + version tracking (GAP-023, GAP-024)
├── 5.5 Remove/restructure Codex references in agent prompt (GAP-014)
├── 0.14 Add import_learned_rules tool (from .jsonl on fresh setup)
├── 0.15 Add rule statistics dashboard to HTML report
└── 0.16 Unify VANILLA_MODIFIERS into learned_rules under source='vanilla_reference'
```

---

## 6. Appendices

### A. File Manifest

```
/mnt/Data/Projects/HOI4-MCP/
├── hoi4-modder.agent.md          # Agent persona + workflow (200 lines)
├── SKILL.md                      # Syntax reference (650+ lines)
├── PROJECT-AUDIT.md              # This file
├── .agents/
│   └── skills/
│       ├── hoi4-decisions-missions/SKILL.md
│       ├── hoi4-events/SKILL.md
│       ├── hoi4-feature-assets/SKILL.md
│       │   └── tools/process_report_event_image.py
│       ├── hoi4-feature-planning/SKILL.md
│       ├── hoi4-focus-trees/SKILL.md
│       ├── hoi4-frame-animation/SKILL.md
│       ├── hoi4-improvement-loop/SKILL.md
│       ├── hoi4-mtth/SKILL.md
│       ├── hoi4-subagents/SKILL.md
│       └── hoi4-text-audio-research/SKILL.md
├── .codex/
│   └── agents/                   # 16 Codex-specific TOML files
│       ├── hoi4_asset_source_researcher.toml
│       ├── hoi4_audio_researcher.toml
│       ├── hoi4_country_package_auditor.toml
│       ├── hoi4_decision_mission_auditor.toml
│       ├── hoi4_documentation_curator.toml
│       ├── hoi4_feature_completion_auditor.toml
│       ├── hoi4_focus_tree_auditor.toml
│       ├── hoi4_generated_feature_art.toml
│       ├── hoi4_icon_artist.toml
│       ├── hoi4_improvement_loop_planner.toml
│       ├── hoi4_localisation_auditor.toml
│       ├── hoi4_quote_remark_researcher.toml
│       ├── hoi4_repo_explorer.toml
│       ├── hoi4_scripted_system_architect.toml
│       ├── hoi4_skill_maintainer.toml
│       └── hoi4_spreadsheet_doc_worker.toml
├── .vscode/
│   └── mcp.json                  # MCP client config (hardcoded paths)
├── hoi4-mcp-server/
│   ├── pyproject.toml
│   ├── README.md
│   ├── scripts/setup.sh
│   └── src/hoi4_mcp/
│       ├── __init__.py           # v0.1.0
│       ├── server.py             # MCP server (~800 lines)
│       ├── clausewitz/
│       │   ├── __init__.py
│       │   ├── parser.py         # Tokenizer + parser (~350 lines)
│       │   └── validator.py      # Syntax + YML validator (~250 lines)
│       ├── db/
│       │   ├── __init__.py
│       │   └── vanilla_index.py  # SQLite builder + lookup (~650 lines)
│       └── tools/
│           ├── __init__.py
│           ├── error_log.py      # Error log parser (~230 lines)
│           ├── id_manager.py     # ID collision prevention (~170 lines)
│           ├── indexer.py        # Mod file scanner (~350 lines)
│           └── report.py         # HTML report generator (~600 lines)
└── paradox_wiki/                 # 30+ offline Paradox wiki snapshots
```

### B. MCP Tool Signatures (Quick Reference)

```
get_mod_index(summary_only: bool = False, refresh: bool = False) -> list[TextContent]
get_next_id(id_type: str = "event", namespace: str = "", prefix: str = "") -> list[TextContent]
check_id_exists(id_value: str = "", id_type: str = "any") -> list[TextContent]
search_mod(query: str = "", subdir: str = "", file_pattern: str = "*.txt", max_results: int = 30) -> list[TextContent]
validate_syntax(text: str = "", file_type: str = "clausewitz") -> list[TextContent]
get_latest_errors(log_path: str = "", tail_lines: int = 200) -> list[TextContent]
lookup_vanilla(query_type: str = "focus", query: str = "", search: str = "") -> list[TextContent]
generate_province_rgb(definition_csv_path: str = "") -> list[TextContent]

Resources:
  mod://descriptor -> str
  logs://error_latest -> str
```

### C. HOI4 Systems Coverage Gap (Detailed)

| System | SKILL.md | Skill File | Wiki Page | MCP Tool |
|--------|----------|------------|-----------|----------|
| Focus Trees | ✅ | ✅ | ✅ | ✅ (index, validate, ID) |
| Events | ✅ | ✅ | ✅ | ✅ (index, validate, ID) |
| Decisions & Missions | ✅ | ✅ | ✅ | ✅ (index, validate, ID) |
| National Spirits / Ideas | ✅ | ❌ | ✅ | ✅ (index, validate, ID) |
| Characters (NSB) | ✅ | ❌ | ✅ | ✅ (index, ID) |
| Country History | ✅ | ❌ | ✅ | ❌ |
| State History | ✅ | ❌ | ✅ | ❌ |
| On Actions | ✅ | ❌ (in events) | ✅ | ✅ (index) |
| Technology Trees | ❌ | ❌ | ✅ | ⚠️ (vanilla DB only) |
| Equipment Modding | ❌ | ❌ | ✅ | ❌ |
| Map Modding | ❌ | ❌ | ✅ | ✅ (province RGB) |
| Scripted GUI | ❌ | ❌ | ✅ | ❌ |
| MIOs | ❌ | ❌ | ✅ | ❌ |
| Balance of Power | ❌ | ❌ | ✅ | ❌ |
| International Market | ❌ | ❌ | ❌ | ❌ |
| AI Strategies | ❌ | ❌ | ✅ | ❌ |
| AI Modding (general) | ❌ | ❌ | ✅ | ❌ |
| Ideology Modding | ❌ | ❌ | ✅ | ❌ |
| Cosmetic Tags | ❌ | ❌ | ✅ | ❌ |
| Country Creation | ❌ | ❌ | ✅ | ❌ |
| Faction Modding | ❌ | ❌ | ✅ | ❌ |
| Intelligence Agency | ❌ | ❌ | ✅ | ❌ |
| Namelist Modding | ❌ | ❌ | ✅ | ❌ |
| Resource Modding | ❌ | ❌ | ✅ | ❌ |
| Building Modding | ❌ | ❌ | ✅ | ❌ |
| Division Modding | ❌ | ❌ | ✅ | ❌ |
| Music Modding | ❌ | ❌ | ✅ | ❌ |
| Sound Modding | ❌ | ❌ | ✅ | ❌ |
| Portrait Modding | ❌ | ❌ | ✅ | ❌ |
| Entity Modding | ❌ | ❌ | ✅ | ❌ |
| Particle Modding | ❌ | ❌ | ✅ | ❌ |
| Autonomy State | ❌ | ❌ | ✅ | ❌ |
| Achievement Modding | ❌ | ❌ | ✅ | ❌ |
| Interface Modding | ❌ | ❌ | ✅ | ❌ |
| Defines | ❌ | ❌ | ✅ | ❌ |
| Data Structures | ❌ | ❌ | ✅ | ❌ |
| Scopes | ❌ | ❌ | ✅ | ❌ |
| Triggers | ❌ | ❌ | ✅ | ❌ |
| Effects | ❌ | ❌ | ✅ | ❌ |
| Modifiers | ✅ | ❌ | ✅ | ✅ (vanilla DB) |
| Localisation | ❌ (only YML format) | ❌ | ✅ | ✅ (validate) |
| Graphical Assets | ❌ | ✅ (feature-assets) | ✅ | ❌ |

**Key:** ✅ = Covered | ⚠️ = Partial | ❌ = Missing

### D. GAP-000 Quick Reference Card

For implementers starting with the learning system:

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Primary store | SQLite (`~/.hoi4_mcp/learned_rules.db`) | Atomic writes, indexed queries, matches existing `vanilla.db` pattern |
| Separate from `vanilla.db`? | **Yes** | Different lifecycles — vanilla DB is rebuilt on game updates; learned rules grow with sessions |
| Export format | `.jsonl` (one JSON object per line) | Git-diffable, append-friendly, human-readable |
| Deduplication | Token-overlap Jaccard similarity (≥0.7 threshold) | Zero new dependencies, sufficient for structured anti-pattern text |
| Auto-record from game logs? | **No** — agent proposes, human confirms | Prevents one-off dev errors from becoming permanent rules |
| Seed from existing constraints? | **Yes** — migrate 8 hardcoded "DO NOT" rules from agent prompt | Bootstraps the system with proven knowledge |
| Promotion path? | Rules with ≥10 occurrences + ≥30 days → flag for SKILL.md/agent prompt | Prevents learning DB from being the only source of truth |
| Confidence model? | `human_correction` > `game_log` > `agent_self_correction` | Human corrections are permanent until explicitly resolved |
| Required new files | `learning/db.py`, `learning/rules.py`, `learning/exporter.py`, `learning/detector.py`, `learning/seeder.py` | ~400 lines total |
| Tool changes | 4 new tools + `detect_recurring` param on `get_latest_errors` | ~150 lines in `server.py` |
| Agent prompt changes | New Phase 0 + Human Correction Protocol + updated Self-Correction Loop | ~60 lines in `hoi4-modder.agent.md` |

---

*End of audit. For questions or to begin implementation, refer to the gap IDs (GAP-000 through GAP-024) in section 4. GAP-000 is the recommended starting point.*
