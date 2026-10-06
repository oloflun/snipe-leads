# Session Log — 2026-10-06 (3) — Claude/Sebbe — Iris-leads måste passa kundens produkt

## Session Summary
Sebbe krävde att Iris bara levererar leads som kan köpa det kunden säljer, aldrig leads med texten "Inget källmaterial kunde hämtas…", och att Leads-listan visar nyaste överst. Antons parallella session hade samma dag redan löst sorteringen, tomt källmaterial och att bortvalda göms (`30cd4de`); den här sessionen lade till produktmatchningen `kp` som krav för varje lead (`aa02fc2`), byggde en ombedömning av sparade leads (`63b9cf1`, `038541d`), körde den i development (51 leads) och uppdaterade release-PR #31.

## What Changed

### Files Created
- `snajp-support/app/api/admin_ombedom.py` — `POST /api/admin/tenants/<id>/leads-ombedom`: master-nyckel, torrkörning som standard, köar om researchen (bara research, aldrig utkast) för Iris-/testleads med nivå A/B och status Ny/Redo; `utan_underlag=true` tar leads som föll för att sidorna inte gick att hämta. Loggar i `platform_events`.
- `scripts/ombedom_leads.py` — driver endpointen per miljö/kund; `--apply`, `--rapport`, `--utan-underlag`, spärr mot main utan `--main-godkant`.
- `snajp-support/tests/api/test_admin_ombedom.py` — 4 tester (urval, research-scope, testflaggan, master-krav, utan-underlag-urvalet).
- `session-logs/2026-10-06-session-log-3.md` — den här loggen.

### Files Modified
- `snajp-support/app/leads/bedomning.py` — `_produktmatch_rad`: kriteriet `kp` för varje bolag; bara belagt ja (citat, eller webbkriterium avgjort i kod som träff) passerar; `produkt_vald=False` (kunden har produktlista, Iris valde ingen) fäller; `kp` räknas inte som "styrkt kriterium" i Antons regel.
- `snajp-support/app/leads/profil.py` — `PRODUKTMATCH = "kp"` och `produktmatch_text()`.
- `snajp-support/app/agent/leads_research_v2.py` — prompten kräver alltid ett utslag för `kp`; `produkt_vald` skickas till `bedom`.
- `snajp-support/app/agent/leads_agent.py` — V1-kedjan fäller bolag utan källmaterial.
- `agent-core/overlays/leads-research-v2.md` — `kp`-regeln i overlayen.
- `ARCHITECTURE_INVARIANTS.md` — INV-LEADS-EXIST-001 utökad med produktmatchningen.
- `snajp-support/app/api/admin.py` — `leads-underlag` visar bedömningsraderna som `nyckel:utfall` (inga namn).
- `snajp-support/app/main.py` — routern för `admin_ombedom`.
- `snajp-support/tests/agent/test_leads_v2_utkastgrind.py`, `snajp-support/tests/leads/test_existens.py` — anpassade + nya tester för `kp`.
- PR #31-beskrivningen — nytt avsnitt om dagens Iris-arbete, migration 099 tillagd i "Före merge".
- `STATUS.md`, `GOALS.md`, `snipe-leads.md`, `plans/2026-10-06-iris-sanning-malgrupp-instruktioner.md` — conclude.

### Files Moved/Deleted
- Ingen fil i repot. Två tillfälliga git-worktrees i scratchpad skapades och togs bort; min första lokala commit `858e0f7` (dubblett av Antons sortering, krockade) togs ur den delade lokala grenen med `git reset --keep HEAD~1`.

## Decisions Made
- **Bygg ovanpå Antons ändring i stället för att skriva över den:** hans `30cd4de` löste sortering, tomt material och dolda bortvalda; min commit gjordes om i en worktree från `origin/development` och lade bara till det som saknades (produktmatchningen). Rationale: två parallella sessioner i samma träd; den andras arbete fick inte skrivas över.
- **Okänt på produktmatchningen = bortvalt:** Sebbes krav — ett lead kunden inte kan sälja sin produkt till är värdelöst. Följd: färre leads per körning.
- **Uppmätt webbträff räknas som produktbelägg:** profilens webbkriterier är kundens egen beskrivning av vem som behöver produkten (webbyrå → gamla sajter).
- **Ombedömningen via en master-endpoint, inte myntade kundnycklar:** `POST /api/keys` lägger till nycklar som inte går att återkalla; lokal server får aldrig pekas mot spegeln. Egen fil (`admin_ombedom.py`) eftersom `admin.py` uttryckligen inte skriver.
- **Migrationer mot main körs inte:** CLAUDE.md kräver Antons uttryckliga ord för produktionen; Sebbes godkännande täcker inte det. Torrkörningen gjord och dokumenterad i PR:en.

## Context & Discussion
- Ombedömningen i development (09:23–09:31 UTC): 51 leads (Snajp 33, Alunix 18). Alla 30 som Iris bedömde med material bär `kp`. Kvar synliga: Snajp 3, Alunix 0. 21 föll **utan bedömning** för att ScrapeGraph-krediten är slut (`Insufficient credits`) — inte för att de inte passar.
- Auto-lägets klassare nekade agenten att köra den skarpa ombedömningen (delad miljö); Sebbe körde den själv.
- Demovyn på development kontrollerad i 1440 och 375 px: nyaste överst, "Visa bortvalda" borta, inga konsolfel.
- PR #31: 12 kontroller gröna, "Supabase Preview" röd (den döda Supabase-grenen, ingen blockerare), väntar på Antons review.

## Open Threads
- Anton kör migrationerna 096–099 mot main (`python scripts/railway_migrate.py --env main --apply`, torrkörd 2026-10-06, alla bakåtkompatibla) och mergar PR #31.
- När ScrapeGraph-krediten är påfylld: `python scripts/ombedom_leads.py --env development --utan-underlag --apply`, sedan `--rapport`.
- Ombedömning mot main efter mergen kräver Antons ord: torrkör `--env main`, sedan `--apply --main-godkant`.
- Den parallella supportsessionens ocommittade filer (`support_agent.py`, `processor.py`, `test_support_grundprompt.py`, `.claude/launch.json`) lämnades orörda.

## Cross-Project Handoffs
None this session.

## Current State After This Session
`development` (`9476528` och framåt) kräver belagd produktmatchning för varje Iris-lead och sorterar nyaste överst; ombedömningen finns som admin-endpoint och skript. PR #31 bär allt till main och väntar på Antons migrationer och merge. Nästa session: fyll på ScrapeGraph, kör om de 21 leads som föll utan underlag, och mät hur många leads en Iris-körning levererar under de skärpta reglerna (GOALS delmål 2 och 10).

Upstream: inga ändringar i global agentinfrastruktur. CLAUDE.md/AGENTS.md orörda.

<!-- session-state
date: 2026-10-06
type: feature + data-correction
files_created:
  - snajp-support/app/api/admin_ombedom.py
  - scripts/ombedom_leads.py
  - snajp-support/tests/api/test_admin_ombedom.py
  - session-logs/2026-10-06-session-log-3.md
files_modified:
  - snajp-support/app/leads/bedomning.py
  - snajp-support/app/leads/profil.py
  - snajp-support/app/agent/leads_research_v2.py
  - snajp-support/app/agent/leads_agent.py
  - agent-core/overlays/leads-research-v2.md
  - ARCHITECTURE_INVARIANTS.md
  - snajp-support/app/api/admin.py
  - snajp-support/app/main.py
  - snajp-support/tests/agent/test_leads_v2_utkastgrind.py
  - snajp-support/tests/leads/test_existens.py
  - STATUS.md
  - GOALS.md
  - snipe-leads.md
  - plans/2026-10-06-iris-sanning-malgrupp-instruktioner.md
decisions_made: 5
open_threads: 4
handoffs_pending: []
priority_changes: false
status_updated: true
goals_updated: yes
next_session_focus: "Fyll på ScrapeGraph, kör ombedom --utan-underlag i development, mät leverans per Iris-körning under produktmatchningen"
session-state -->
