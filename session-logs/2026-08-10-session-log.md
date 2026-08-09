# Session Log — 2026-08-10

## Session Summary

Migrerade leads-agenten (Fas B research + Fas C outreach) från en hopklistrad
`Runner.run`-loop till per-steg-körning via `step_runner.run_step`, vilket var
förkravet för att `THINKING_MODE` överhuvudtaget skulle nå API-anropet — utan
den migreringen mätte 2026-08-08 års jämförelse ingenting. Körde sedan den
giltiga jämförelsen: 3 svenska bolag × 2 thinking-lägen × 12 skill-steg = 72
skarpa LLM-anrop, med varje stegs kompletta utdata dokumenterad. Användaren
läste igenom rådatan, **underkände min rekommendation (som var thinking PÅ)**
och beslutade thinking HELT AV för leadsflödet; beslutet är verkställt per
steg i kod, inte bara i dokumentation. Körningen avslöjade dessutom tre buggar
varav två åtgärdades.

## What Changed

### Files Created
- `scripts/render_leads_report.py` — renderar den fullständiga leadsrapporten ur
  en körnings JSON. Separat från körskriptet så rapporten kan byggas om utan att
  köra 72 skarpa anrop igen.
- `tests/invariants/test_inv_skill_005.py` — hash-grinden som gör "ändra aldrig
  skillsen" mekaniskt tvingad i stället för en instruktion i ett dokument.
- `docs/LEADS_THINKING_COMPARISON.md` — 811 KB genererad rapport, 72
  steg-utdatablock (ett per LLM-anrop) med komplett output och reasoning-spår.
- `docs/live-tests/leads-20260809-140940.json` — rådata från körningen.
- `docs/live-tests/skill-audit-20260809-140408.json` — skill-integritetsaudit.

### Files Modified
- `snajp-support/app/agent/leads_agent.py` — **omskriven**. Tre `Runner.run`-anrop
  → per-steg-orkestrering (8 research-steg, 4 outreach-steg). Skrapning flyttad
  till kod före steg 1; köning av utkast flyttad till kod efter språk-/tidsgrind.
  Ny `sign_off()`-grind. Fas A medvetet kvar på `Runner.run`.
- `snajp-support/app/agent/step_runner.py` — `playbook_role`-parameter (leads-steg
  skulle annars få veta att de utför "en svensk kundtjänst-playbook") och
  `RunTrace.as_full()` som bär hela stegets utdata till rapporten utan att svälla
  DB-loggen.
- `snajp-support/app/agent/research_tools.py` — `_as_markdown()`; ScrapeGraphAI
  returnerar `results['markdown']['data']` som LISTA, inte sträng.
- `snajp-support/app/leads/research_playbook.py` — `THINKING = "disabled"`, satt
  explicit på varje steg. Källan till beslutet för alla tre leads-playbooks.
- `snajp-support/app/leads/outreach_playbook.py` — samma pin på alla fyra steg.
- `snajp-support/app/leads/onboarding_playbook.py` — samma pin, med kommentar om
  att den inte får verkan förrän Fas A migreras.
- `snajp-support/tests/agent/test_leads_agent_wiring.py` — omskriven till den nya
  arkitekturen; 19 → 22 tester, inkl. regressionstestet för thinking-buggen och
  två som låser AV-beslutet.
- `snajp-support/tests/agent/test_research_tools.py` — regressionstest för
  listformatet; mockens docstring varnar för att den tidigare antog sträng.
- `scripts/run_live_leads.py` — riktad om till Snajps egen tenant (uppgiften var
  "marknadsför Snajps tjänster till tre bolag"), erbjudandet kommer nu från
  researchens `mk:offers`-steg i stället för en hårdkodad sträng, inkrementell
  skrivning så en avbruten körning inte kastar bort betalda anrop.
- `scripts/run_live_tests.py` — `--leads` renderar nu markdown, inte bara JSON.
- `ARCHITECTURE_INVARIANTS.md` — INV-SKILL-005 tillagd under Active.
- `HANDOFF.md` — Steg 1 markerat klart, §4 leads ersatt med det fattade beslutet,
  fälla 2 uppgraderad från rekommendation till tvingad regel.
- `docs/THINKING_MODE_COMPARISON.md` — §6 statusmarkerad, §7 (migreringen) och §8
  (den giltiga jämförelsen + beslutet) tillagda. Min felaktiga §8.5-rekommendation
  ersatt med användarens beslut och en förklaring av varför jag hade fel.

### Files Moved/Deleted
- `docs/live-tests/leads-partial.json` — raderad efter körningen (mellanfil för
  krasch-återhämtning, hade tjänat sitt syfte).

## Decisions Made

- **Thinking HELT AV för leadsflödet** (användarens beslut, efter genomläsning av
  rådatan): utkasten är personligare och har rätt ton med AV; PÅ blev hackigt och
  robotaktigt trots övertänkandet ("i drift hos Livrustning" utan förklaring); och
  AV hade RÄTT om att B2C passar supportprodukten — hög volym privatkunder med
  enkla ärenden är precis den belastning agenten avlastar.
- **Beslutet pinnas per steg, inte ärvs från `settings.thinking_mode`.** Support
  ger samma värde i dag, men ett leadsbeslut som tyst hänger på ett supportbeslut
  flyttar med när supportbeslutet ändras. Två tester låser det.
- **Skrapningen görs i kod, inte som modellverktyg.** Allowlisten är oförändrad,
  men hämtningen kan inte längre utebli för att modellen "glömde" verktyget — G4
  blir en kodväg i stället för ett hopp.
- **Fas A (onboarding) migreras INTE.** Flerturssamtal passar inte per-steg-
  kontrakt. Medvetet val, dokumenterat som kvarvarande lucka — inte som klart.
- **INV-SKILL-005: skills ändras aldrig i tysthet.** Hård regel per användarens
  uttryckliga instruktion, mekaniskt tvingad via sha256 mot manifestet. Grinden
  förbjuder inte ändring, den gör den omöjlig att göra omärkt.
- **Finjustering sker med TILLÄGGSINSTRUKTIONER**, i playbookens `task`/
  `case_context` — aldrig genom att redigera skillen. Ska utvärderas i kommande
  tester.
- **Harnesset kördes bara mot Snajp-tenanten**, inte även Nordlys Handel som
  2026-08-07-versionen. Uppgiften gällde Snajps egna tjänster; luckhanteringen
  utan onboarding har eget test.

## Context & Discussion

- **Användaren korrigerade min slutsats, och korrigeringen är den viktigaste
  behållningen av sessionen.** Jag rekommenderade thinking PÅ utifrån mätvärden:
  PÅ bröt utdatakontraktet noll gånger mot AV:s sex, differentierade sina
  konfidenssiffror där AV svarade 0,55 rakt igenom, och gjorde en skeptiskare
  ICP-bedömning. Jag läste det som kvalitet. Användaren läste vad modellen
  **faktiskt producerade** — sex färdiga mejlutkast — och där var AV bättre på
  varje punkt som betyder något för en mottagare. Lärdomen: i ett flöde vars
  output går till en människa är läsningen av outputen den enda mätning som
  räknas; proxymått kan peka åt motsatt håll och låta övertygande.
- **Min §8.2-tolkning var fel.** Jag skrev att AV "resonerade sig förbi" en
  ICP-avvikelse den själv upptäckt, och läste det som slarv. Användaren:
  AV:s slutsats var den riktiga, motiveringen var kortfattad snarare än slarvig.
  PÅ:s underkännande av alla tre var pessimism, inte skärpa — exakt det §8.3
  varnade för. Observationen står kvar i dokumentet, tolkningen är rättad.
- **AV:s research höll genuint hög kvalitet:** den undersökte om bolagen redan
  hade en chatbotlösning på sajten, identifierade en öppning via Instagram där en
  stor del av deras kunder befinner sig, och förberedde rimliga invändningar med
  raka, användbara svar redan i researchsteget.
- **Två testmockar har nu visat sig ljuga om verkligheten** — `_fake_scrape_result`
  antog sträng där API:t ger lista, och (förra sessionen) `MemoryStorage.search_kb`
  som ignorerar embeddings. Samma felklass: en mock som gissar formatet bevisar
  bara att koden är konsekvent med gissningen.
- Grinden i INV-SKILL-005 verifierades genom att faktiskt ändra `mk:offers`, se
  testet fälla, och återställa. En grind som inte kan fela är ingen grind.

## Open Threads

- **Påhittade påståenden saknar kodgrind.** AV-utkastet till Sportamore innehöll
  "minskat sina återkommande frågor med 30 procent inom 30 dagar" — kontextpaketet
  innehåller noll procentsiffror (verifierat programmatiskt). `strip_placeholders`
  tar mallrester, inte ogrundade påståenden. Detta är det allvarligaste kvarvarande
  kundvända felet: det hade gått ut i Snajps namn.
- **Fas A (onboarding) kör kvar på `Runner.run`** — saknar thinking-kontroll,
  `step_log` och `agent_runs`-loggning. Pinnen i `onboarding_playbook.py` får
  verkan först vid migrering.
- **Tilläggsinstruktioner ska utvärderas** — kandidater i §8.6: `sa:draft-outreach`
  + `snajp:humanizer-svenska` (tonen avgörs där), grundningskrav på siffror och
  kundreferenser, `mk:prospecting` (behåll AV:s bedömning, motivera tydligare).
- **`DATABASE_URL` fortfarande osatt** → riktiga pgvector-KB-vägen overifierad.
  Blockerad på att `snajp_app`-rollens lösenord aldrig satts (`execute_sql`
  blockerad av miljöns klassificerare). Oförändrat sedan 2026-08-07.
- **Död kod från första implementationspasset** ej väckt eller borttagen:
  `evals.decide_promotion`, `layers.ComposedRun`, `follow_up.build_follow_up_sequence`,
  `handoff.route_handoff`, tabellerna `offers`/`ab_variants`/`ab_results`.
- **`discover-leads` / `generate-outreach` edge functions** fortfarande stubbar.
- **Email Studio-integration och dashboard-vy** för `GET /api/leads/runs` ej byggda.
- **`BLOCKS.md` är 7 060 tecken mot 3 000 i tak** — växte från 6 259. Behöver en
  offload av resolved-block äldre än tre månader till `BLOCKS-RESOLVED.md`.
- **`.~lock.*`-filer** låg i `docs/` under sessionen (LibreOffice hade rapporterna
  öppna). Ska inte committas.

## Cross-Project Handoffs

None this session. Allt arbete låg inom `snipe-leads`. Ingen global
agentinfrastruktur ändrades — inga skills, hooks, CARL-regler eller
installer-relevanta filer rördes, så ingen super-intelligence-synk krävs
("upstream: no changes").

## Current State After This Session

Leadspipelinen kör per-steg med verifierad thinking-kontroll, granskningsbar
`agent_runs.step_log` per skill-anrop, och thinking låst AV genom hela flödet.
275 tester gröna (269 i snajp-support + 6 invarianter), inget committat vid
skrivande stund. Nästa session bör: (1) bygga en grundningsgrind mot påhittade
siffror och kundreferenser i utkast, (2) börja utvärdera tilläggsinstruktioner
enligt §8.6 med `sa:draft-outreach` och humanizern först, (3) ta ställning till
Fas A-migreringen, (4) beta av HANDOFF.md:s döda-kod-lista. `HANDOFF.md` är den
tekniska handoffen; `docs/THINKING_MODE_COMPARISON.md` §7–8 är beslutsunderlaget.

<!-- session-state
date: 2026-08-10
type: feature-implementation + evaluation
files_created:
  - scripts/render_leads_report.py
  - tests/invariants/test_inv_skill_005.py
  - docs/LEADS_THINKING_COMPARISON.md
  - docs/live-tests/leads-20260809-140940.json
  - docs/live-tests/skill-audit-20260809-140408.json
files_modified:
  - snajp-support/app/agent/leads_agent.py
  - snajp-support/app/agent/step_runner.py
  - snajp-support/app/agent/research_tools.py
  - snajp-support/app/leads/research_playbook.py
  - snajp-support/app/leads/outreach_playbook.py
  - snajp-support/app/leads/onboarding_playbook.py
  - snajp-support/tests/agent/test_leads_agent_wiring.py
  - snajp-support/tests/agent/test_research_tools.py
  - scripts/run_live_leads.py
  - scripts/run_live_tests.py
  - ARCHITECTURE_INVARIANTS.md
  - HANDOFF.md
  - docs/THINKING_MODE_COMPARISON.md
decisions_made: 7
open_threads: 9
handoffs_pending: []
priority_changes: true
status_updated: true
next_session_focus: "Grundningsgrind mot påhittade siffror i utkast, sedan utvärdera tilläggsinstruktioner (sa:draft-outreach + humanizern) enligt THINKING_MODE_COMPARISON.md §8.6"
session-state -->
