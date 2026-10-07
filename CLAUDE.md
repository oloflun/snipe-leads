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

**Varje komponent med användarvänd text är tvåspråkig, utan undantag.**
Svenska och engelska via `lib/i18n.tsx` (`useLocale().text({ sv, en })`, `t(nyckel)`
eller en modulkonstant av `Localized`; adminytan via `lib/admin/sprak.ts`). Det
gäller rubriker, knappar, tomlägen, felmeddelanden, `aria-label` och CSV-rubriker,
i nya komponenter och i varje komponent som ändras. Grinden är mekanisk:
`tests/invariants/test_inv_copy_001.py` (INV-COPY-001) fäller svenska bokstäver i
strängar och JSX-text som saknar sitt par, och en fil som översatts ska strykas ur
testets skuldlista i samma commit. Antons beställning 2026-10-02 efter att den
engelska versionen visat sig vara svensk på de flesta sidor.

**Allt arbete går till `development`, aldrig direkt till `main`.**

**`development` deployar sig själv sedan 2026-08-27.** Railways deployment
trigger för `web` och `api` i miljön `development` pekar på grenen
`development` direkt (omlagt via GraphQL, `deploymentTriggerUpdate` — se
`DEPLOY.md`). En enda push räcker:

```bash
git push origin development
```

Vercel är avvecklat helt. `railway-development` som gren är överflödig för
development men rörs inte — inget läser den längre.

**`main` deployar sig själv sedan 2026-09-15.** §8.1-ordningen kördes
2026-09-14/15 med Antons godkännande och mains triggers pekar nu på grenen
`main` direkt (se `DEPLOY.md`s main-avsnitt). Release = PR `development` →
`main`; grenskyddet kräver code owner-review från `oloflun` (Anton), så
mergen är alltid hans handgrepp — det ERSÄTTER inte §8.1a: varje release
mot produktion kräver fortfarande Antons uttryckliga ord. Kör migrationer
mot main (torrkörning först) INNAN mergen när releasen bär nya.
**⛔ `railway-main` är pensionerad** — pusha aldrig till den; den gamla
tvåstegskedjan i äldre dokument/handoffs ska inte följas. De döda GitHub
Actions-kedjorna (`deploy-production.yml`, `deploy-development.yml`) är
borttagna 2026-08-29 — de gav bara falska gröna signaler mot den gamla
stacken.

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

## Leads: källor, filter och kontakter (Antons regler 2026-10-04)

**Gäller tills Anton säger annat. Bygg varje ny leadsfunktion utifrån dem.**

1. **Registret (merinfo, senare allabolag via API) är ett filter, inte en
   kontaktkälla.** Det väljer bolag på bransch, geografi, storlek och
   omsättning. Registrets personer och telefonnummer blir aldrig ett leads
   kontakt: ett bolagsnummer går inte att knyta till en viss person.
2. **Jev är första filtret.** Bolagen som passerat registret klassas av Jev
   mot kundens kriterier (Iris-profilen) innan något dyrare steg körs.
3. **Kontakta bara VD.** Aldrig styrelseledamöter, suppleanter eller
   revisorer. En kontaktuppgift används bara om den kan styrkas tillhöra en
   viss person.
4. **Iris-leads (de detaljerade):** använd registerdatan för att hitta
   bolagets webbplats. Kontaktperson, roll och bolagshändelser/nyheter hämtas
   därifrån och bygger ingången i mejlet. **Har bolaget ingen webbplats, gå
   vidare till nästa.**
5. **Listor:** det räcker med mejladress eller telefonnummer, men bara om
   uppgiften kan styrkas tillhöra VD (mindre bolag utan hemsida har oftast VD
   som beslutsfattare). Ett nummer som inte kan knytas till VD hör inte hemma
   i en lista.
6. **Inga privatpersonsidor.** Registrets personsidor (bostad, ålder,
   familj) är inte B2B-källor och används inte.

**Tillägg 2026-10-05 (Anton):**

7. **Ensam VD är undantaget från regel 1.** När VD är den enda personen i
   bolaget (högst en anställd, ingen annan med roll; suppleant och revisor
   räknas inte) får registrets telefonnummer användas: det är då VD:s.
   Bara i listor, aldrig som Iris-kontakt. Kod: `merinfo.ensam_vd_telefon`.
8. **Bolag som inte blir Iris-leads kastas inte.** Utan webbplats, med
   parkerad domän eller utan VD-kontakt på sajten hamnar bolaget i
   körningens lista "Utan webbplats" (listspåret), för utkast med ett mer
   generellt erbjudande senare. Ingen dyr research körs på dem.
9. **Webbkriterier avgörs i kod.** Betyget från webbrevisionen (PageSpeed
   plus bildbedömning, `app/leads/webbrevision.py`) översätts till träff,
   miss eller gränsfall i `bedomning.webbutslag`, inte av modellens fria
   utslag. Merinfos råsida når aldrig researchprompten, bara bolagsfakta
   utan personer och nummer (`merinfo.bolagsfakta_text`).

**Tillägg 2026-10-07 (Sebbe) — ERSATT samma dag av ändringen nedan; behålls bara som historik:**

10a. ~~Iris-leads kräver en namngiven kontaktperson — inte nödvändigtvis VD.~~
    Regel 3 reviderad för Iris: kontakten måste vara en namngiven person
    styrkt från bolagets egen sajt (namnet intill adressen, lokaldelen bär
    namnet). VD föredras, ägare/chef/ansvarig därnäst, och en namngiven
    anställd utan uttalad roll duger i sista hand. Utkast går bara till en
    adress som bär personens namn på bolagets domän — funktionsadresser
    aldrig. Förbudet mot styrelseledamöter, suppleanter och revisorer UR
    REGISTRET står kvar, liksom listspårets VD-krav (regel 5 och 7).
    Kod: `app/leads/discovery.py:hamta_person_kontakt` / `mottagare`.

**Ändring 2026-10-07 (Sebbe) — ersätter regel 3 och 4 för Iris-leads:**

10. **Det enda kontaktkravet för ett Iris-lead är en kontaktmejl till
    bolaget** som utkastet kan nå fram till. Ingen VD krävs, ingen
    namngiven person krävs. En namngiven persons styrkta adress föredras;
    annars duger bolagets egen adress (info@, kontakt@) på bolagets domän.
    Aldrig en privat adress, en främmande domän eller en HR-, ekonomi- eller
    robotadress (`discovery.mottagare`, `_EJ_SALJADRESS`). En telefon ensam
    räcker inte. Bolaget måste fortfarande ha en webbplats (adressen hämtas
    därifrån); utan webbplats går det till listspåret som förut.
11. **Ger registret färre bolag än beställt fyller den gamla sökkedjan på**
    (grounded sökning + existensgrinden), så att körningar hittar leads som
    innan merinfo-filtret. Listornas VD-krav (regel 5, 7) är oförändrat.
    Anton ska informeras om ändringen.

Koden: `snajp-support/app/leads/sources/merinfo.py` (filtret, `lage="iris"`
och `lage="lista"`), `app/leads/discovery.py:hamta_person_kontakt`
(kontaktkontrollen; `hamta_vd_kontakt` är listspårets strängare VD-variant).

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
