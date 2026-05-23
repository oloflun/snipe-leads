<!-- agent-chorus:context-pack:claude:start -->
## Context Pack

**BEFORE starting any task**, read the context pack in this order:

1. `.agent-context/current/00_START_HERE.md` — entrypoint, routing, stop rules
2. `.agent-context/current/30_BEHAVIORAL_INVARIANTS.md` — change checklists, file families, what NOT to do
3. `.agent-context/current/20_CODE_MAP.md` — navigation index, tracing flows

Read these three files BEFORE opening any repo source files. Then open only the files the pack identifies as relevant.

For architecture questions, also read `10_SYSTEM_OVERVIEW.md`. For test/deploy questions, also read `40_OPERATIONS_AND_RELEASE.md`.
<!-- agent-chorus:context-pack:claude:end -->

<!-- agent-chorus:claude:start -->
## Agent Chorus Integration

This project is wired for cross-agent coordination via `chorus`.
Provider snippet: `.agent-chorus\providers\claude.md`

When a user asks for another agent status (for example "What is Claude doing?"),
run Agent Chorus commands first and answer with evidence from session output.

Session routing and defaults:
1. Start with `chorus read --agent <target-agent> --cwd <project-path> --json` (omit `--id` for latest).
2. "past session" means previous session: list 2 and read the second session ID.
3. "past N sessions" means exclude latest: list N+1 and read the older N session IDs.
4. "last N sessions" means include latest: list N and read/summarize those sessions.
5. Ask for a session ID only after an initial read/list attempt fails or when exact ID is requested.

Support commands:
- `chorus list --agent <agent> --cwd <project-path> --json`
- `chorus search "<query>" --agent <agent> --cwd <project-path> --json`
- `chorus compare --source codex --source gemini --source claude --cwd <project-path> --json`

If command syntax is unclear, run `chorus --help`.
<!-- agent-chorus:claude:end -->
