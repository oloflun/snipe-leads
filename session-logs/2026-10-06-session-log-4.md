# Session Log — 2026-10-06 (4)

## Session Summary
Iris levererar nu bara leads som uppfyller kraven (varje nej eller ostyrkt måste-krav ger nivå C, och nivå C når aldrig listan), och nyaste leads står överst. Planens kvarvarande faser byggdes: insynsvyn Underlag och flöde (fas 7), kundens produkter, segment och egna önskemål (fas 8), omindexering av kunskapsbasen och kalibrering mot kundens egna utslag (fas 9), samt mätningen av skillvarianterna, som behöll variant (c) och hittade två grindluckor som rättades. En sista dubblettkontroll mellan Iris och leadslistorna lades in precis före skrivningen; allt är sammanslaget med Sebbes och en annan sessions arbete och pushat till development. Handoff: `HANDOFF-2026-10-06-KVALITET-INSYN-KUNDYTA.md`.

## What Changed

### Files Created
- `~/snipe-leads/HANDOFF-2026-10-06-KVALITET-INSYN-KUNDYTA.md` — utförlig handoff: läge, byggt, kvar, fällor, Antons ord
- `~/snipe-leads/snajp-support/app/leads/utslag.py` — Iris kalibreras av kundens manuella utslag (fas 9)
- `~/snipe-leads/snajp-support/app/leads/onskemal.py` — kundens egna önskemål per agent, användarposition (fas 8)
- `~/snipe-leads/snajp-support/app/leads/tilltal.py` — hälsningen sätts i kod till VD:ns förnamn eller "Hej,"
- `~/snipe-leads/snajp-support/app/agentcore/insyn.py` m.fl. — fas 7 (Opus-agent, granskad och sammanslagen)
- `~/snipe-leads/components/leads/IrisProdukter.tsx`, `~/snipe-leads/components/settings/AgentOnskemal.tsx` — kundens paneler
- `~/snipe-leads/components/admin/insyn/*`, `~/snipe-leads/app/admin/kunder/[id]/insyn/page.tsx`, `~/snipe-leads/lib/actions/insyn.ts` — fas 7-vyn
- `~/snipe-leads/app/forhandsvisning/kundinstallningar/page.tsx` — förhandsvisning av fas 8 med syntetiska svar
- `~/snipe-leads/supabase/migrations/20261007090000_101_prompt_lager.sql`, `~/snipe-leads/supabase/migrations/20261007100000_102_kundonskemal.sql` — ej körda
- `~/snipe-leads/scripts/badda_in_kb.py`, `~/snipe-leads/scripts/radera_prospekt.py`, `~/snipe-leads/scripts/mat_skillvarianter.py`
- Tester: `~/snipe-leads/snajp-support/tests/leads/test_utslag.py`, `~/snipe-leads/snajp-support/tests/api/test_kundonskemal_api.py`, `~/snipe-leads/snajp-support/tests/api/test_admin_kb_inbaddning.py`, `~/snipe-leads/snajp-support/tests/agentcore/test_insyn.py`, `~/snipe-leads/snajp-support/tests/orgnr_fixtur.py`

### Files Modified
- `~/snipe-leads/snajp-support/app/leads/bedomning.py` — nej/ostyrkt måste fäller, självmotsägande motivering ersätts
- `~/snipe-leads/snajp-support/app/api/leads.py` — listan döljer nivå C, leverbarhetsfall sparas som C, önskemål-endpoints, config visar produkter/segment, dubblettkontroll före skrivning
- `~/snipe-leads/components/leads/LeadsTabell.tsx` — nyaste först, Visa bortvalda borttagen
- `~/snipe-leads/snajp-support/app/agent/leads_research_v2.py` — kalibrering, Jev-klassning bara för kvalificerade, tilltal
- `~/snipe-leads/snajp-support/app/leads/grounding_gate.py` — fäller oifyllda mallfält (placeholder)
- `~/snipe-leads/snajp-support/app/leads/soul.py`, `~/snipe-leads/snajp-support/app/agent/triage.py`, `~/snipe-leads/snajp-support/app/email_pipeline/processor.py` — önskemålen läses med rösten och i mejlinkorgen
- `~/snipe-leads/snajp-support/app/agent/step_runner.py`, `~/snipe-leads/snajp-support/app/storage/{base,memory,postgres}.py` — fas 7 och KB-omindexering
- `~/snipe-leads/plans/2026-10-06-iris-sanning-malgrupp-instruktioner.md` — fas 1b, rättelse om hybridsökning, mätresultat, byggt per fas, a11y-skuld
- `~/snipe-leads/ARCHITECTURE_INVARIANTS.md` — INV-LEADS-EXIST-001 utökad (lead = alla måste styrkta, inget nej; listan aldrig C)
- `~/snipe-leads/tests/invariants/test_inv_sec_009.py` — önskemålen aldrig i systemprompten
- `~/snipe-leads/STATUS.md`, `~/snipe-leads/snipe-leads.md`, `~/snipe-leads/GOALS.md`

### Files Moved/Deleted
- Migrationerna omnumrerade före första körning: `..._100_prompt_lager.sql` → `..._101_prompt_lager.sql`, `..._101_kundonskemal.sql` → `..._102_kundonskemal.sql` (Sebbes `100_snajp_saljlista` tog 100).
- Fas 7-agentens worktree och gren borttagna efter sammanslagning.

## Decisions Made
- **Ett lead måste uppfylla kraven, inte bara inte motsäga dem:** varje nej (även bör) och varje ostyrkt måste-krav fäller — Antons krav; kostar volym, provet mäter hur mycket.
- **Fel i listan, inte i databasen:** nivå C döljs i API:t men raden står kvar, så dedupliceringen fortsätter att utesluta bolaget.
- **Kalibreringen går inte till Jev:** Jev är tredje part och ser aldrig kundens data (Antons beslut 2026-09-30).
- **Variant (c) av skopan står kvar:** enda varianten utan påhitt i mätningen.
- **Hälsningen avgörs i kod:** grinden kontrollerar inte personnamn; billigare och säkrare att sätta namnet än att be modellen.
- **Dubblettkontroll precis före skrivning:** mängden lästes bara vid rundans början; omläsning stänger fönstret mellan samtidiga körningar.
- **Husets kantkontrast rättas i eget pass:** mönstret finns i 17 filer.

## Context & Discussion
- Hybridsökningen i KB fanns redan sedan 2026-08-26 (RRF); det som saknades var vektorerna.
- Klassificeraren nekade agenten två skrivningar mot development: återställning av instruktionerna och raderingen av de nio bolagen. Båda ligger hos Anton med färdiga kommandon.
- Fas 7 tar bort spårets tak: hela kundmejl sparas nu utan gallring — dataskyddsbeslut om period behövs.
- En annan session lade samtidigt till produktmatchning och ombedömning av sparade leads; den byggde ovanpå fas 1b och står kvar.

## Open Threads
- Anton raderar de nio bolagen med `scripts/radera_prospekt.py` (kommandot i handoffen § 3.1).
- Anton återställer development-instruktionerna (Gemensamt, spara tom version).
- Migration 101 och 102 mot development, sedan Antons ja till 096–102 mot main och merge av PR #31.
- Beslut om gallringsperiod för spårets fulltext (förslag 30 dagar).
- Visuell kontroll och a11y av fas 7-vyn; skarpt Iris-prov N=5 efter ScrapeGraph-påfyllning.

## Cross-Project Handoffs
None this session.

## Current State After This Session
Development har all kod för planens fas 0–9 och dubblettspärren; det som saknas för att den ska fungera fullt där är migration 101/102 och återställda instruktioner. Main ligger efter och väntar på Antons ja till migrationerna. Nästa session: kör 101/102 i development, visuell kontroll av insynsvyn, och skarpt Iris-prov när krediten är påfylld.

<!-- session-state
date: 2026-10-06
type: feature-and-quality
files_created:
  - ~/snipe-leads/HANDOFF-2026-10-06-KVALITET-INSYN-KUNDYTA.md
  - ~/snipe-leads/snajp-support/app/leads/utslag.py
  - ~/snipe-leads/snajp-support/app/leads/onskemal.py
  - ~/snipe-leads/snajp-support/app/leads/tilltal.py
  - ~/snipe-leads/snajp-support/app/agentcore/insyn.py
  - ~/snipe-leads/components/leads/IrisProdukter.tsx
  - ~/snipe-leads/components/settings/AgentOnskemal.tsx
  - ~/snipe-leads/scripts/badda_in_kb.py
  - ~/snipe-leads/scripts/radera_prospekt.py
  - ~/snipe-leads/scripts/mat_skillvarianter.py
files_modified:
  - ~/snipe-leads/snajp-support/app/leads/bedomning.py
  - ~/snipe-leads/snajp-support/app/api/leads.py
  - ~/snipe-leads/components/leads/LeadsTabell.tsx
  - ~/snipe-leads/snajp-support/app/agent/leads_research_v2.py
  - ~/snipe-leads/snajp-support/app/leads/grounding_gate.py
  - ~/snipe-leads/plans/2026-10-06-iris-sanning-malgrupp-instruktioner.md
  - ~/snipe-leads/STATUS.md
  - ~/snipe-leads/snipe-leads.md
  - ~/snipe-leads/GOALS.md
decisions_made: 7
open_threads: 5
handoffs_pending: []
priority_changes: true
status_updated: true
goals_updated: yes
next_session_focus: "Migration 101/102 i development, visuell kontroll av Underlag och flöde, skarpt Iris-prov N=5"
session-state -->
