# Session Log — 2026-10-08

## Session Summary
Antons CRM-beställning för leads är byggd och pushad till development (`e816bd8`). Översikten visar nu det som var Aktivitet, och utkast och skickade mejl räknas rätt. Iris-listan har massåtgärder, skickade leads flyttar till Inkorg › Skickat, kontaktsökningen hittar det som fanns på sajterna, och Leads › Samtal har ringlista och återkoppling. Därtill: ett bolag på ett ställe, Processa om på listor, ta bort och kopiera listor mellan kunder, och regeln att webbplatsbedömningen är hemlig. Arbetet gick genom två egna agenter och samordnades med en parallell session (webbpoolen) i samma arbetsträd. Detaljer: `HANDOFF-2026-10-08-CRM-FLODE.md`.

## What Changed

### Files Created
- `~/snipe-leads/HANDOFF-2026-10-08-CRM-FLODE.md` — handoff, läge, återstående arbete, Antons ord
- `~/snipe-leads/plans/2026-10-08-crm-flode.md` — planen med läge
- `~/snipe-leads/supabase/migrations/20261008090000_107_crm_samtal.sql` — meddelandeordning, kasserade utkast, arkiv, ringspår, lead_samtal (körd i development)
- `~/snipe-leads/snajp-support/app/leads/samtal.py`, `utkaststatus.py`, `omprova.py`, `app/api/leads_massatgard.py`, `app/api/admin_listor.py`
- `~/snipe-leads/components/leads/Samtalslista.tsx`, `lib/leads/utkast.ts`, `lib/actions/listor.ts`, `app/forhandsvisning/samtal/page.tsx`
- `~/snipe-leads/scripts/utkast_status.py`, `scripts/grenstatus.sh`, `scripts/koade_utkast_till_granskning.py`, `scripts/omklassa_listspar.py`
- Tester: `snajp-support/tests/leads/test_samtal.py`, `test_kasserade_utkast.py`, `test_ett_stalle.py`, `test_fordelning.py`, `test_kontaktsokning.py`, `test_omklassa_listspar.py`, `test_crm_flode.py`, `tests/api/test_massatgarder_api.py`

### Files Modified
- `~/snipe-leads/CLAUDE.md`, `~/snipe-leads/AGENTS.md` — hämta arbetsgrenen vid start, leadsregel 12–17, webbplatsbedömningen hemlig
- `~/snipe-leads/.claude/settings.json` — SessionStart-hook grenstatus
- `~/snipe-leads/snajp-support/app/leads/discovery.py`, `sources/merinfo.py`, `sidhamtning.py`, `platshallare.py`, `korning.py`, `scheduler.py`, `send_guard.py`, `follow_up_generator.py`, `upptagna.py` — kontaktsökning, fördelning, bevakning, dubblettgrind
- `~/snipe-leads/snajp-support/app/api/leads.py`, `leads_suite.py`, `app/storage/{base,memory,postgres}.py`
- `~/snipe-leads/components/{dashboard,admin,leads}/*`, `lib/{routes.ts,i18n.tsx,admin/sprak.ts,demo/sektioner.ts}` — meny, Leads-ytor
- `~/snipe-leads/STATUS.md`, `~/snipe-leads/GOALS.md` (ändringslogg)

### Files Moved/Deleted
- `components/dashboard/Oversikt.tsx` borttagen (ersatt av Aktivitet som Översikt)

## Decisions Made
- **Sajtens eget telefonnummer räcker för ringlistan** — regel 12 (en sajt hamnar aldrig bland ej kvalificerade) går före VD-kravet, som gäller registrets nummer.
- **Adress som bolaget själv publicerar räknas**, även gmail/annan domän (regel 13); registrets bolags-e-post räcker för Iris.
- **Processa om flyttar inget** (Antons val): berikar listraderna; användaren flyttar till Iris (alltid research + utkast) eller skriver utkast till dem med mejl.
- **Ett bolag, ett prospekt** i `create_prospect` (org.nr, annars namn utan bolagsform), lås per kund; listrad som blivit prospekt märks `flyttad` och döljs, raderas aldrig.
- **Ta bort** bara för aldrig kontaktade leads; kontaktade arkiveras.
- **Uppföljningar alltid utkast till granskning**, med spegelvakt i development.
- **Webbplatsbedömningen är hemlig** (admin, Umeå Webdesign, Alunix) — regel i CLAUDE.md/AGENTS.md; listkopiering bär aldrig webbfälten.

## Context & Discussion
- Mätt: 26 Snajp-utkast godkända efter sändfönstret 2026-10-07 skickas vardagar 08:00; inget mejl gick ut på 28 dygn — därav Skickade 0.
- Lane B-fynd: `lstrip("www.")` fällde alla mejldomäner på w; VD-telefon kastade redan funnen info@; sidtaket 150/150 tog slut.
- Min commit `b4b29a3` blev oparsbar (hunkar på fel rad); lagad av den andra sessionens `7d1b22a` innan push.
- Min torrkörning höll en transaktion öppen och blockerade migration 108; lagat i skriptet.

## Open Threads
- Processa om (eller `omklassa_listspar.py --apply` efter Antons ja) på de gamla listorna; Snajps torrkörning blev inte klar.
- Stickprov på 166 "ej kvalificerade" hos kund-ea08b974.
- Skarp Iris-körning N=5 i development.
- Release till main med migration 096–108 (Antons ja och merge).
- Kontrollera att webbkolumn/låda i Iris-listan är grindad för övriga kunder.
- Fråga till Anton: slå ihop Säljlista och Ringlista?

## Cross-Project Handoffs
None this session.

## Current State After This Session
Development kör hela CRM-flödet och webbpoolen (`e816bd8`), migration 107 och 108 körda. Main är orörd och väntar på release. Nästa session: Processa om på de gamla listorna, skarp körning, och sedan release.

upstream: no changes · sync-configs: CLAUDE.md och AGENTS.md redigerade för hand med samma text (projektfiler, inte hemkatalogens)

<!-- session-state
date: 2026-10-08
type: feature
files_created:
  - ~/snipe-leads/HANDOFF-2026-10-08-CRM-FLODE.md
  - ~/snipe-leads/plans/2026-10-08-crm-flode.md
  - ~/snipe-leads/snajp-support/app/leads/samtal.py
  - ~/snipe-leads/snajp-support/app/leads/omprova.py
  - ~/snipe-leads/components/leads/Samtalslista.tsx
files_modified:
  - ~/snipe-leads/CLAUDE.md
  - ~/snipe-leads/AGENTS.md
  - ~/snipe-leads/STATUS.md
  - ~/snipe-leads/GOALS.md
  - ~/snipe-leads/snajp-support/app/api/leads.py
decisions_made: 7
open_threads: 6
handoffs_pending: []
priority_changes: true
status_updated: true
goals_updated: yes
next_session_focus: "Processa om på de gamla listorna, skarp Iris-körning N=5, release till main"
session-state -->
