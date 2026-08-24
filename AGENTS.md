<!-- agent-chorus:context-pack:codex:start -->
## Context Pack

When asked to understand this repository:

1. Read `.agent-context/current/00_START_HERE.md`.
2. Read `.agent-context/current/routes.json`.
3. Identify the active task type in `routes.json`.
4. Read the matching entries in `completeness_contract.json`, `reporting_rules.json`, and `search_scope.json`.
5. Search ONLY within the directories listed in `search_scope.json` for your task type.
6. Use `verification_shortcuts` to check specific line ranges instead of reading full files.
7. Do not enumerate files in directories marked `exclude_from_search`.
8. Do not open repo files before those steps unless a referenced structured file is missing.

If `.agent-context/current/routes.json` is missing, fall back to the markdown pack only.
<!-- agent-chorus:context-pack:codex:end -->

## Arbetssätt: automatisera först, fråga sist

**Sträva alltid efter minsta möjliga friktion för användaren.** Varje fråga du
ställer är arbete du lämpar över. Innan du ber om något:

1. **Undersök om det verkligen kräver användarens hand.** Ofta finns ett CLI,
   ett API eller en MCP som gör samma sak. Att ett moment står beskrivet som
   "gör detta i dashboarden" betyder inte att det måste göras där.
2. **Installera verktyget själv** om tjänsten redan används i projektet.
   Supabase CLI (`npx supabase`), Vercel CLI, Render REST API, `gh` — alla
   används här och får installeras och konfigureras utan att fråga.
3. **Bygg ett skript i stället för en instruktion.** `scripts/keys.py`,
   `scripts/onboard_tenant.py` och `scripts/verify_render.py` är mönstret: det
   som annars blivit en punktlista i ett dokument blir ett kommando som går att
   köra om, verifiera och falsifiera.
4. **Fråga bara om du inte kan lösa det själv** — och säg då exakt varför, inte
   bara att det behövs.

Undantag som ALLTID kräver användaren, oavsett hur automatiserbart det ser ut:
lösenord till konton, betalningar och planuppgraderingar, OAuth-samtycken hos
tredjepartskonsoler, och åtgärder som är svåra att ångra (force-push som
skriver över någon annans arbete, radering av produktionsdata).

**Läckagespärr:** när du automatiserar med hemligheter — skriv aldrig ut dem.
Läs in dem ur `.env.deploy` (gitignorerad) i skriptet, echa dem aldrig i ett
skalkommando, och kom ihåg att en `cat` under felsökning läcker lika mycket som
en `echo`. Det har hänt i den här kodbasen.

<!-- agent-chorus:codex:start -->
## Agent Chorus Integration

This project is wired for cross-agent coordination via `chorus`.
Provider snippet: `.agent-chorus\providers\codex.md`

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
<!-- agent-chorus:codex:end -->

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:970c3bf2 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   bd dolt push
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->

<!-- BEGIN BEADS CODEX SETUP: generated by bd setup codex -->
## Beads Issue Tracker

Use Beads (`bd`) for durable task tracking in repositories that include it. Use the `beads` skill at `.agents/skills/beads/SKILL.md` (project install) or `~/.agents/skills/beads/SKILL.md` (global install) for Beads workflow guidance, then use the `bd` CLI for issue operations.

### Quick Reference

```bash
bd ready                # Find available work
bd show <id>            # View issue details
bd update <id> --claim  # Claim work
bd close <id>           # Complete work
bd prime                # Refresh Beads context
```

### Rules

- Use `bd` for all task tracking; do not create markdown TODO lists.
- Run `bd prime` when Beads context is missing or stale. Codex 0.129.0+ can load Beads context automatically through native hooks; use `/hooks` to inspect or toggle them.
- Keep persistent project memory in Beads via `bd remember`; do not create ad hoc memory files.

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.
<!-- END BEADS CODEX SETUP -->
