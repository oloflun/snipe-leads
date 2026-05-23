# Context Pack Generation Guide

This guide tells AI agents how to fill in the context pack templates.

## Process
1. Read each file in `.agent-context/current/` in numeric order.
2. Fill the markdown templates with repository-derived content.
3. Update the structured files (`routes.json`, `completeness_contract.json`, `reporting_rules.json`) so they describe routing, completeness, and reporting rules.
4. After filling all sections, run `chorus context-pack seal` to finalize (manifest + snapshot).

## Quality Criteria
- Content must be factual and verifiable from the repository.
- Prefer concise bullets over long prose.
- Keep total word count under ~2000 words across all files.
- Do not include secrets or credentials.
- If unsure, note `TBD` rather than inventing details.
- Structured artifacts should stay deterministic and explicit. Do not auto-generate them from prose in v1.

## When to Update
- After significant architectural or contract changes.
- After adding new commands/APIs/features.
- When `chorus context-pack check-freshness` reports stale content.
