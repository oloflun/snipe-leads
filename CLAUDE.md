<!-- agent-chorus:context-pack:claude:start -->
## Context Pack

**BEFORE starting any task**, read the context pack in this order:

1. `.agent-context/current/00_START_HERE.md` — entrypoint, routing, stop rules
2. `.agent-context/current/30_BEHAVIORAL_INVARIANTS.md` — change checklists, file families, what NOT to do
3. `.agent-context/current/20_CODE_MAP.md` — navigation index, tracing flows

Read these three files BEFORE opening any repo source files. Then open only the files the pack identifies as relevant.

For architecture questions, also read `10_SYSTEM_OVERVIEW.md`. For test/deploy questions, also read `40_OPERATIONS_AND_RELEASE.md`.
<!-- agent-chorus:context-pack:claude:end -->

## Projektregler — drift

**Allt arbete går till `development`, aldrig direkt till `main`.**

**Men `development` DEPLOYAR INGENTING.** Produkten kör på Railway, och Railways
deployment trigger pekar på en annan gren. Två pushar krävs:

```bash
git push origin development
git push origin development:railway-development
```

Utan den andra syns ändringen ingenstans — och GitHub Actions går ändå grönt,
för den kedjan deployar en Vercel-preview som ligger på den gamla, döda stacken
(Vercel + Render + Supabase-grenar). Inloggning där ger `CallbackRouteError`,
eftersom Supabase-grenen står i `MIGRATIONS_FAILED`. Det är inte ett kodfel.

Levande dev-miljö: `https://web-development-6c85.up.railway.app`
Migrationer: `python scripts/railway_migrate.py --env development --apply`

**Skriv ALDRIG till Supabase.** Grenen `development` i Supabase är död —
`MIGRATIONS_FAILED` sedan 15 augusti, ett fel på Supabases sida, och beslutet
i `MIGRATIONS-PENDING.md` är att lämna den som den är. Använd inte
`mcp__supabase-snipra__apply_migration`, `rebase_branch`, `reset_branch`,
`create_branch` eller något annat skrivande Supabase-MCP-anrop — de
skrivläsande verktygen (`list_tables`, `get_advisors`, `execute_sql` för
läsning) är okej, men varje mutation ska gå till Railway via
`scripts/railway_migrate.py`, aldrig till Supabase. En SQL-fil i
`supabase/migrations/` är källkod som konsumeras av det Railway-skriptet —
katalognamnet är historiskt, inte en instruktion att köra den mot Supabase.

**Development-databasen är en SPEGEL av produktionen** — Railway-miljön
`development` bär en spegelmarkör, så att en ändring går att utvärdera med allt
annat lika. En tom databas testar bara att koden startar.

**Följden:** den innehåller riktiga kunders ärenden och mejladresser och ska
behandlas med samma sekretess som produktionen — inga länkar till utomstående,
inga skärmdumpar med kunddata, och peka aldrig en lokal utvecklingsserver dit.
Kör `python scripts/lokal_stack.py --apply` i stället.

Fullständig beskrivning av miljöer, variabler och fällor: [`DEPLOY.md`](DEPLOY.md).

## Dataskydd: DeepSeek får inte se kunddata

**Beslut 2026-08-24. Vänd inte tillbaka det utan att läsa varför.**

DeepSeek behandlar prompten i Kina. Allt som går genom support-agenten är
kundens kundmejl — namn, adresser, ärendetext — och en sådan
tredjelandsöverföring kräver SCC, en överföringskonsekvensbedömning och ett
uttryckligt villkor i PUB-avtalet. Inget av det finns.

`LLM_PROVIDER=deepseek` fäller därför uppstarten i varje miljö som bär eller
speglar riktig kunddata (`main`, `development` — kom ihåg att development är en
spegel av produktionen). Spärren sitter i `Settings.llm_provider_fault()` och
körs från `app/main.py` innan databasen ens öppnas. En felaktig deploy ska dö
högljutt, inte tyst skicka kunddata utomlands.

DeepSeek får köras lokalt och i testsviten, mot MemoryStorage och syntetiska
fixtures. Det är där den hör hemma.

Vill vi ta tillbaka den i drift av kostnadsskäl är det ett **avtalsbeslut**,
inte ett kodbeslut: SCC, TIA, PUB-villkor och information till kunden vid
tecknandet. Flagga till Anton — bygg inte tyst in det igen.

Status för resten av dataskyddsarbetet: [`docs/JURIDIK_ATGARDER.md`](docs/JURIDIK_ATGARDER.md).
Incidenter: [`INCIDENT_RESPONSE.md`](INCIDENT_RESPONSE.md).

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


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:6cd5cc61 -->
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
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->
