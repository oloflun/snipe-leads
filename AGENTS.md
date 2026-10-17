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

## Projektregler — kod

**Vid varje sessionsstart: hämta senaste arbetsgrenen från GitHub innan något
annat** (Antons regel 2026-10-07). `git fetch origin`, sedan
`git merge --ff-only origin/<gren>`; har grenarna divergerat
`git merge origin/<gren>`. Aldrig rebase, reset eller stash av någon annans
ocommittade filer, och vid konflikt: stanna och rapportera. Läs koden från den
hämtade grenen: Sebbe pushar flera gånger per dag, och en plan byggd på en
inaktuell gren gör om arbete som redan finns. Projektets SessionStart-hook
(`.claude/settings.json`) hämtar och säger hur många commits grenen ligger efter.

**Webbplatsbedömningen är hemlig (Antons beslut 2026-10-08).** Webbrevisionen
och allt som härleds ur den (`webbrevision`, `webbniva`, betyg, brister,
platshållarskäl, webbpoolens listor och `lan`-fördelningen) syns BARA för
plattformsadmin och kunderna Umeå Webdesign och Alunix. Varje API-svar, UI,
CSV-export, listkopiering, utkast och prompt som bär den ska grindas på det:
övriga kunder får aldrig se fälten, inte heller via en kopierad lista
(`app/api/admin_listor.py:LISTRADSFALT` saknar dem med flit) eller en flytt
till main. Lägger du till ett ställe som visar eller skickar vidare
bedömningen: grinda det i samma commit, annars är det en läcka.

**Varje funktion har ett sätt att följa flödet (Antons regel 2026-10-10).**
Allt som körs i bakgrunden eller tar mer än ett ögonblick ska visa förlopp och
utfall där användaren startade det, i den befintliga miljön och utan ny flik om
det inte är absolut nödvändigt, och utfallet ska finnas kvar efter en
omladdning. Är det tveksamt om det ska synas för kunden: fråga Anton.

**Varje nytt beslut skrivs i `docs/BESLUT.md` med beslutsfattarens
resonemang** (Antons regel 2026-10-10).

**Varje komponent med användarvänd text är tvåspråkig, utan undantag.**
Svenska och engelska via `lib/i18n.tsx` (`useLocale().text({ sv, en })`, `t(nyckel)`
eller en modulkonstant av `Localized`; adminytan via `lib/admin/sprak.ts`). Det
gäller rubriker, knappar, tomlägen, felmeddelanden, `aria-label` och CSV-rubriker,
i nya komponenter och i varje komponent som ändras. Grinden är mekanisk:
`tests/invariants/test_inv_copy_001.py` (INV-COPY-001) fäller svenska bokstäver i
strängar och JSX-text som saknar sitt par, och en fil som översatts ska strykas ur
testets skuldlista i samma commit. Antons beställning 2026-10-02 efter att den
engelska versionen visat sig vara svensk på de flesta sidor.

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

**Ändring 2026-10-07 (Anton) — fördelningen efter kontaktsökningen. Går före
regel 1, 4, 5, 7, 8 och 10 där de krockar:**

12. **Ett bolag med webbplats har alltid ett kontaktsätt.** Kontaktsökningen
    läser startsidan och kontakt- och Om oss-sidorna (länkade eller gissade)
    och avkodar skyddade adresser. Hittas ändå inget är jobbet inte grundligt
    gjort: bolaget lämnas fritt, prövas igen nästa körning och räknas i
    körningsrapporten. Ett bolag med webbplats hamnar aldrig bland ej
    kvalificerade.
13. **Mejladress → Iris.** En adress som bolaget självt publicerar på sin
    webbplats är bolagets kontaktadress, även på gmail/telia eller en annan
    domän. Registrets bolags-e-post (bolagsnivå, inte en person) räcker också.
    HR-, ekonomi-, jobb- och robotadresser utesluts som förut.
14. **Tilltal.** Personlig adress → personens namn. Bolagets adress och en Om
    oss-sida med högst två personer där en tydligt är ägare eller VD → den
    personens namn. Annars en inledning utan namn.
15. **Bara telefon → ringlistan.** Utan mejladress men med telefon går bolaget
    till ringlistan. Sajtens eget publicerade nummer räcker alltid (regel 12
    går före); registrets bolagsnummer kräver att VD är namngiven i
    registret, och numret antas då vara VD:s.
    Antal anställda visas alltid, så att säljaren vet att numret kan gå till
    någon annan. Enskilda firmor går inte till ringlistan (NIX-spärren gäller
    dem).
16. **Ej kvalificerade** är bolag utan webbplats och utan både mejl och telefon,
    utan namngiven VD, eller enskilda firmor.
17. **Återkoppling.** Varje kontaktat Iris-lead med telefon står i
    återkopplingslistan, äldst kontakt först, med utfallen Ej svar, Återkom
    (datum), Ej intresserad, Kontakta inte och Möte bokat. Systemet bevakar:
    ej svar kommer tillbaka efter två arbetsdagar, återkom på datumet, ett
    mejlsvar tar bort leadet ur listan och avslutande utfall stoppar alla
    utskick. Uppföljningsmejl är alltid utkast som en människa godkänner.

Kod för 12–17: `sources/merinfo.py:fordela` (fördelningen),
`discovery.py:hamta_person_kontakt`/`kontakt_ur_sidor` (kontaktsökningen),
`platshallare.py:kontaktrader_ur_html` (skyddade adresser, JSON-LD),
`app/leads/samtal.py` (ringlista och återkoppling, Leads › Samtal) och
`scripts/omklassa_listspar.py` (äldre listspårsrader genom samma sökning).

**Ändring 2026-10-08 (Anton) — webbplatsbedömningen och webbpoolen:**

18. **Fyra webbnivåer, inget gränsfall.** Bildbedömningen ger akut (1–2),
    dålig (3–5), bra (6–8) eller mycket bra (9–10), avgjort i kod
    (`app/leads/webbrevision.py:webbniva`). Akut avgörs utan bild för parkerad
    domän, felsida (404 hos Netlify/Wix), fillistning, "under konstruktion" och
    en sajt som inte svarar ens på www-varianten. En katalogsida (thingsreview,
    hitta, eniro …) som enda webbnärvaro är bolagets sida och aldrig bättre än
    dålig. Startsidan bedöms, aldrig en undersida. Kalibrerad mot Antons facit
    (`tests/leads/fixtures/webbfacit_2026-10-08.json`,
    `scripts/kalibrera_webbrevision.py`, grind 85 %).
19. **Avvecklade bolag kastas** i alla spår ("under avveckling", "bedriver
    inte längre", konkurs; `platshallare.AVVECKLAT`).
20. **Webbpoolen.** Varje körning och listbygge hos varje kund bildbedöms efter
    körningen, och bolag med akut eller dålig sajt fördelas tyst efter län:
    Alunix (Västra Götaland, Halland) och Umeå Webbdesign (Norrland) får en
    veckolista, mycket bra blir Alunix inspirationslista, bra fördelas aldrig.
    Bara bolagsnivå lämnar källkunden (INV-SEC-008): inga kontakter, inget
    kundinnehåll, aldrig vilken kund som hittade bolaget. Webbyråkunder och
    enskilda firmor är aldrig källa. Utan sajt, parkerad eller trasig är just
    de akuta leadsen för webbyråerna; regel 8 gäller fortfarande källkundens
    egen körning. Kod: `app/leads/webbpool.py`, flaggor `WEBBPOOL_*`.
21. **Skärmbilden.** ScrapeGraph i JS-läge med samtyckescookies (2 krediter),
    stealth bara som andra försök när rutan ändå skymmer (7 krediter).
    PageSpeed bara på mobil, för siffrorna.

Koden: `snajp-support/app/leads/sources/merinfo.py` (filtret, `lage="iris"`
och `lage="lista"`), `app/leads/discovery.py:hamta_vd_kontakt` (VD-kontrollen).

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
