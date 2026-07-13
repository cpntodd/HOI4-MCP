<!-- GAP-022:COMPLETED — 7 of 16 checklists done. Checklist complete. Remaining 9 are asset/research checklists. -->
# hoi4_repo_explorer — Platform-Agnostic Checklist

**Purpose:** Map relevant files, patterns, vanilla precedents, risks, dependencies, and edit order for large or unfamiliar modding tasks.

## Checklist
- [ ] Identify all files that will be touched (mod files + vanilla references)
- [ ] Find existing patterns in the repo that match the task
- [ ] Map any vanilla precedents for the mechanic being built
- [ ] Identify cross-file dependencies (events → localisation, focuses → GFX)
- [ ] Flag any missing required files (e.g., localisation for a new focus tree)
- [ ] Determine safe edit order (what must be created before what)
- [ ] List validation checks that should run after implementation

## Output Format
```
## Repo Exploration: <task_name>
### Files to Touch: N
### Dependencies: [list]
### Edit Order: 1. ... 2. ... 3. ...
### Risks: [list]
```
