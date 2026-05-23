# Context Pack: Start Here

## Snapshot
- Repo: `snipe-leads`
- Branch at generation: `unknown`
- HEAD commit: `unknown`
- Generated at: `2026-05-22T16:44:43.125Z`

## Read Order — MANDATORY before starting work
1. Read this file completely.
2. Read `30_BEHAVIORAL_INVARIANTS.md` — change checklists, file families, negative guidance.
3. Read `20_CODE_MAP.md` — navigation index, tracing flows, extension recipe.

Do NOT open repo source files until you have read steps 1-3. These three files give you enough context to avoid common mistakes (wrong patterns, missing files, deprecated approaches).

Read on demand:
- `10_SYSTEM_OVERVIEW.md` — for architecture or diagnosis tasks.
- `40_OPERATIONS_AND_RELEASE.md` — for test, CI, or deploy tasks.

## Task-Type Routing
**Impact analysis** (list every file that must change): read `30_BEHAVIORAL_INVARIANTS.md` Update Checklist *before* `20_CODE_MAP.md` — the checklist has the full blast radius per change type. CODE_MAP alone is not exhaustive.
**Navigation / lookup** (find a file, find a value): start with `20_CODE_MAP.md` Scope Rule.
**Planning** (add a new feature/module): follow the Extension Recipe in `20_CODE_MAP.md`, then cross-check the BEHAVIORAL_INVARIANTS checklist for that change type.
**Diagnosis** (silent failures, unexpected output): start with `10_SYSTEM_OVERVIEW.md` Silent Failure Modes, then the relevant diagnostic row in `30_BEHAVIORAL_INVARIANTS.md`.

## Structured Routing
- If `routes.json` exists, use it as the authoritative task router before opening repo files.
- Use `completeness_contract.json` for "what must be included" and `reporting_rules.json` for "how to report it".
- Use `search_scope.json` for "where to search" — it bounds search directories and lists verification shortcuts.
- If the structured layer and markdown disagree, continue exploring and report the mismatch explicitly.

## Fast Facts
<!-- AGENT: Replace with 3-5 bullets covering product, languages/entry points, quality gate, core risk. -->

## Scope Rule
<!-- AGENT: Provide navigation rules — what to open first for each area of the codebase, what to skip. -->

## Stop Rules
<!-- AGENT: Describe when a task has enough evidence to stop. Keep this short and operational.
Call out grouped reporting defaults, generated-file avoidance, and any cases where agents may keep exploring because the pack and repo diverge. -->
