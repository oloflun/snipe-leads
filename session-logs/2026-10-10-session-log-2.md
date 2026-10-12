# Session Log — 2026-10-10 (2)

## Session Summary
Parallella körningar slutar dela bolag, hitta.se ger kontakt till bolag som saknade det, listorna fick egna verktyg (detaljvy, utkast, Processa om med förlopp), kön kan skicka nu eller omplanera, och en avstängd autopilot för dagliga körningar är byggd. Allt är testat (3161 gröna) men ocommittat; den visuella granskningen avbröts av full disk.

## What Changed
Se `HANDOFF-2026-10-10-PARALLELL-KATALOG-AUTOPILOT.md` avsnitt 2 för fil-för-fil.
### Files Created
- `snajp-support/app/leads/katalog.py`, `autopilot.py` — hitta.se-uppslag resp. daglig körning
- `snajp-support/tests/leads/test_katalog.py`, `test_autopilot.py`, `tests/api/test_schemalagg_utskick.py`
- `supabase/migrations/20261010090000_110_listrader_i_listan.sql` — torrkörd, inte körd
- `docs/BESLUT.md` — beslut med resonemang
- `HANDOFF-2026-10-10-PARALLELL-KATALOG-AUTOPILOT.md`
### Files Modified
- Backend: `api/leads.py`, `api/schemas.py`, `jobs/stadare.py`, `leads/automation.py`, `omprova.py`, `platshallare.py`, `sources/merinfo.py`, `storage/{base,memory,postgres}.py` + tester
- Frontend: `LeadslistorView.tsx`, `SkickatLista.tsx`, `IrisAutomation.tsx`, `LeadsOversikt.tsx`, `app/forhandsvisning/listutkast/page.tsx`
- `CLAUDE.md`, `AGENTS.md` — två nya regler
### Files Moved/Deleted
- `.next/` raderad (byggcache, 0,8 GB) när C: stod på 0 byte

## Decisions Made
- **Ingen förklädnad mot Eniro:** 403 för bot och nummer bakom klick — lämnas öppen, kringgås inte.
- **Gemini bara för bolagshändelser, med länkkontroll:** kontaktuppgifter blev fel eller tomma.
- **Skicka nu följer sändfönstret 08–16:** skyddar avsändardomänen (väntar på Antons bekräftelse).
- **Autopilot av som standard:** `LEADS_AUTOPILOT=1` krävs; 10/vardag, tak 50.

## Context & Discussion
- Ingenting skickas automatiskt i någon miljö i dag; utskicksloopen är av. Svarshantering och uppföljningsutkast är redan automatiska.
- Diskfyllnaden kom från qmd-omindexering (1,4 GB) och AppData/Local/Microsoft (1,1 GB).

## Open Threads
- Anton frigör disk; committa/migrera 110/pusha efter ja; fyra beslutsfrågor (commit, hitta.se-nummer utan VD, sändfönster för Skicka nu, autopilot i main); visuell granskning + a11y; /simplify; bd-ärenden när Dolt finns; Gemini 3 Vertex global-beslut.

## Cross-Project Handoffs
None this session.

## Current State After This Session
Koden för dagens beställning är klar och grön lokalt men inte committad. Nästa session börjar med Antons svar på commit-frågan och diskutrymme, sedan migration 110 i development och visuell granskning av förlopp, detaljvy och kö.

<!-- session-state
date: 2026-10-10
type: feature
files_created:
  - snajp-support/app/leads/katalog.py
  - snajp-support/app/leads/autopilot.py
  - supabase/migrations/20261010090000_110_listrader_i_listan.sql
  - docs/BESLUT.md
  - HANDOFF-2026-10-10-PARALLELL-KATALOG-AUTOPILOT.md
files_modified:
  - snajp-support/app/api/leads.py
  - snajp-support/app/leads/automation.py
  - components/leads/LeadslistorView.tsx
  - components/leads/SkickatLista.tsx
  - CLAUDE.md
  - AGENTS.md
decisions_made: 4
open_threads: 8
handoffs_pending: []
priority_changes: true
status_updated: true
goals_updated: yes
next_session_focus: "Antons svar på commit och disk, migration 110 i development, visuell granskning"
session-state -->
