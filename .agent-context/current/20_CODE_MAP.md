# Code Map

## High-Impact Paths

> **This table is a navigation index, not a complete blast-radius list.** For impact analysis tasks,
> read `30_BEHAVIORAL_INVARIANTS.md` Update Checklist first — it has the full file set per change type.
> Use this table to navigate to those files once you know which are relevant. Verify coverage with grep.

<!-- AGENT: Identify 8-15 key paths. Use [Approach 1], [Approach 2], or [Both] in the Approach column
if the repo has coexisting architectural patterns — omit the column if there is only one approach.
Risk must be filled: use "Silent failure if missed", "KeyError at runtime", "Build drift", etc.
Authority must be filled: "authoritative" (edit this file), "derived" (generated/compiled — do not edit directly), or "reference" (read-only context).
| Path | Approach | What | Why It Matters | Risk | Authority |
| --- | --- | --- | --- | --- | --- | -->

## Quick Lookup Shortcuts
<!-- AGENT: Add 4-6 common lookup patterns. Map intent to exact file and what to look for.
| I need to find... | Open this file | Look for |
| --- | --- | --- | -->

## Cross-Cutting Tracing Flows
<!-- AGENT: For changes that ripple through multiple layers, document the full chain.
Example: "New parameter through call chain: schema → step → client → wrapper → tests"
List files in dependency order so agents trace the change correctly. -->

## Minimum Sufficient Evidence
<!-- AGENT: For the 3-5 most common task types, say what minimum evidence closes the task.
Example: "Lookup closes after authoritative file + exact value + one supporting chain if requested."
These rules should align with reporting_rules.json. -->

## Extension Recipe
<!-- AGENT: Describe how to add a new module/adapter/plugin. List all files that must change together. -->
