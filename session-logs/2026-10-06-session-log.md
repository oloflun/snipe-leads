# Session Log — 2026-10-06

## Session Summary
Iris och leadslistorna hämtar inte längre samma bolag: Iris-prospekt, rader i varje lista och kundens CRM-kunder bildar nu en gemensam uteslutningsmängd som både Iris-sökningen och listbygget läser. Kunder (och Snajp-admin i kundens vy) kan ladda upp sin befintliga CRM-kundlista under Leads › Listor, med en länk från översikten; listan prospekteras aldrig. Allt ligger i commit `b57316f` på `development` och i release-PR #31; migration 098 är körd mot development och torrkörd mot main, där skrivningen väntar på Antons godkännande.

## What Changed

### Files Created
- `~/snipe-leads/snajp-support/app/leads/upptagna.py` — uteslutningsmängden: nyckel på orgnr eller på namnet utan bolagsform, `hamta()` läser prospekt + alla listrader.
- `~/snipe-leads/components/leads/CrmKundlista.tsx` — panelen "Ladda upp befintlig CRM-kundlista" överst i Leads › Listor.
- `~/snipe-leads/supabase/migrations/20261006120000_098_listor_crm.sql` — `lead_lists.kalla` tillåter `'crm'` + index på `lead_list_items(tenant_id)`.
- `~/snipe-leads/snajp-support/tests/leads/test_upptagna_bolag.py` — 10 tester: nycklar, listbygget, merinfo på orgnr, listspåret, CRM-import och 409-spärrarna.
- `~/snipe-leads/plans/2026-10-06-listor-crm-separation.md` — planen för det här arbetet.

### Files Modified
- `~/snipe-leads/snajp-support/app/api/leads.py` — Iris-sökningen och körningsloopen läser uteslutningsmängden; listbygget skickar den till merinfo och discovery och filtrerar efteråt; listspåret dubblerar inte befintliga listor; `_kraev_ej_crm` (409) på till-iris, prospektbefordran och kombinera.
- `~/snipe-leads/snajp-support/app/api/leads_suite.py` — `ImportRequest.kalla` (`import`|`crm`), CRM-importen slår ihop dubbletter.
- `~/snipe-leads/snajp-support/app/leads/discovery.py` — normaliserade nycklar i `_rena_traffar`, källfederationen och `hitta_bolag`; sökprompten får högst 150 uteslutna namn, klamrar escapade.
- `~/snipe-leads/snajp-support/app/leads/sources/merinfo.py` — `sok` hoppar över upptagna bolag på namn eller orgnr innan bolagssidan hämtas.
- `~/snipe-leads/snajp-support/app/storage/{base,memory,postgres}.py` — `lista_upptagna_bolag`; minnet tillåter `kalla='crm'`.
- `~/snipe-leads/components/leads/ImportCsv.tsx` — `kalla`-prop med CRM-texter.
- `~/snipe-leads/components/leads/LeadslistorView.tsx` — CRM-panelen, förklaring under "Beställ en lista", CRM-listor utan kombinera/flytta/skriv mejl.
- `~/snipe-leads/components/leads/LeadsSida.tsx` — `?crm=1` öppnar panelen; panelen syns även utan listtillägget.
- `~/snipe-leads/components/dashboard/Oversikt.tsx` — länken "Ladda upp befintlig CRM-kundlista" vid Pipeline.
- `~/snipe-leads/components/AppShell.tsx` — `demoAnpassa` behåller frågesträngen (länkar med `?vy=` lämnade demon).
- `~/snipe-leads/GOALS.md`, `~/snipe-leads/STATUS.md`, `~/snipe-leads/snipe-leads.md` — läget efter sessionen.
- PR #31 (GitHub) — titel och beskrivning: CRM-avsnitt, migration 098, steget "Anton godkänner" före migrationerna mot main.

### Files Moved/Deleted
- Inga.

## Decisions Made
- **Separation genom uteslutning, inte genom urval:** listorna får aldrig innehålla ett bolag som redan är ett Iris-lead, står i en annan lista eller är kundens kund — men listbygget begränsas inte till bolag som underkänts för Iris. Att bara ta underkända bolag hade krympt listorna kraftigt; frågan är ställd till Sebbe.
- **CRM-listan är en lista med `kalla='crm'`, inte en egen tabell:** återanvänder import, visning och CSV-mallarna, och uteslutningen täcker den automatiskt eftersom alla listrader räknas.
- **CRM-listan prospekteras aldrig:** backenden svarar 409 på flytt, befordran och kombinering; UI:t döljer knapparna.
- **Admin laddar upp i kundens vy:** befintlig kundvy räcker; importen läser inte `is_test`, så listan blir skarp även när admin tittar som kund.
- **Migration 098 mot main väntar på Antons ord:** torrkörningen visar exakt 096–098 och alla är bakåtkompatibla, men CLAUDE.md kräver hans uttryckliga ord för releasesteg mot produktion.

## Context & Discussion
- Sebbes beställning: listor är "kalla samtal" med mindre information och ska inte hämta samma leads som Iris; kunder och Snajp-admin ska kunna ladda upp färdiga CRM-listor under leadslistor, nåbart från översikten.
- Sebbes sista instruktion: "lägg in allt i pr, i development och mot main men Anton måste godkänna" — tolkat som PR + development klara, main torrkörd, skrivningen efter Antons ja.
- En parallell session arbetade samtidigt med supportagenten (commits `c32aab4`, `6976c68`, `3f630b5`, `520d7f9` och ocommittad `snajp-support/app/agent/triage.py`); bara explicita sökvägar committades.
- Stopphooken krävde designskills: `next-best-practices` och `impeccable` (operate) kördes i efterhand, inga ändringar behövdes.

## Open Threads
- Anton ska godkänna migrationerna 096–098 mot main; därefter kör agenten `python scripts/railway_migrate.py --env main --apply` och Anton mergar PR #31.
- Nattspeglingen main → development pausar tills 098 finns i main (schemaskillnad) — den går igen när migrationerna körts mot main.
- CRM-uppladdningen med en riktig fil är inte klickad igenom i UI:t (knappen är avstängd i demon och development bär kunddata); nästa steg är ett prov med en syntetisk CSV på en testtenant.
- Sebbe behöver avgöra om listorna bara ska innehålla bolag som underkänts för Iris; i dag utesluts bara bolag som redan finns någonstans.
- CI-kontrollen "Supabase Preview" är röd på PR #31 av den döda Supabase-grenen, inte av releasen.

## Cross-Project Handoffs
None this session.

## Current State After This Session
`development` bär separationen och CRM-kundlistan och är driftsatt; migration 098 är körd där. Release-PR #31 (development → main) innehåller allt och väntar på Antons godkännande av migrationerna 096–098 mot main och på hans merge. Nästa session: kör migrationerna mot main när Anton sagt ja, prova CRM-uppladdningen med syntetisk data, och ta Sebbes besked om listornas urval.

upstream: no changes · config sync: no diff (CLAUDE.md/AGENTS.md orörda)

<!-- session-state
date: 2026-10-06
type: feature
files_created:
  - snajp-support/app/leads/upptagna.py
  - components/leads/CrmKundlista.tsx
  - supabase/migrations/20261006120000_098_listor_crm.sql
  - snajp-support/tests/leads/test_upptagna_bolag.py
  - plans/2026-10-06-listor-crm-separation.md
  - session-logs/2026-10-06-session-log.md
files_modified:
  - snajp-support/app/api/leads.py
  - snajp-support/app/api/leads_suite.py
  - snajp-support/app/leads/discovery.py
  - snajp-support/app/leads/sources/merinfo.py
  - snajp-support/app/storage/base.py
  - snajp-support/app/storage/memory.py
  - snajp-support/app/storage/postgres.py
  - components/leads/ImportCsv.tsx
  - components/leads/LeadslistorView.tsx
  - components/leads/LeadsSida.tsx
  - components/dashboard/Oversikt.tsx
  - components/AppShell.tsx
  - GOALS.md
  - STATUS.md
  - snipe-leads.md
decisions_made: 5
open_threads: 5
handoffs_pending: []
priority_changes: false
status_updated: true
goals_updated: yes
next_session_focus: "Kör migrationerna 096–098 mot main efter Antons ja, prova CRM-uppladdningen med syntetisk CSV, ta Sebbes besked om listornas urval"
session-state -->
