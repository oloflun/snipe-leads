# Session Log — 2026-10-06

## Session Summary
Iris rättades i kod efter provkörningen 2026-10-05: inga påhittade bolag (existensgrind, inget underlag ger varken bedömning eller utkast), bara privata bolag och en målgrupp krävs, utkast bara till VD med verifierade citat och vald produkt, och påhittade kundexempel fälls. Iris fick en egen grundprompt, instruktionerna delades per agent med feedback som bakas in i stället för att ersätta, och inbäddningarna lagades. Sju commits på `development`, opushade; migration 099 ej körd; adminvyn ej visuellt kontrollerad. Handoff: `HANDOFF-2026-10-06-IRIS-SANNING-INSTRUKTIONER.md`.

## What Changed

### Files Created
- `snajp-support/app/leads/existens.py` — existensgrinden för sökträffar
- `snajp-support/app/leads/offentlig.py` — offentlig sektor och skolor utesluts
- `snajp-support/app/agent/leads_systemprompt.py` — renderar Iris grundprompt per steg
- `snajp-support/app/agentcore/baka_in.py` — feedback bakas in som ändringar
- `agent-core/prompts/leads-systemprompt.md` — Iris grundprompt
- `supabase/migrations/20261006140000_099_agentinstruktioner_per_agent.sql` — instruktioner per agent
- `scripts/granska_leads_underlag.py`, `scripts/las_agentinstruktioner.py`, `scripts/snajp_malgrupp.py`
- Tester: `tests/leads/test_existens.py`, `tests/leads/test_utkastunderlag.py`, `tests/agentcore/test_radandringar.py`, `tests/api/test_admin_instruktioner_per_agent.py`, `tests/agent/test_embeddings_vertex.py`, `tests/invariants/test_inv_leads_exist_001.py`
- `plans/2026-10-06-iris-sanning-malgrupp-instruktioner.md`, `HANDOFF-2026-10-06-IRIS-SANNING-INSTRUKTIONER.md`

### Files Modified
- `snajp-support/app/leads/{discovery,korning,bedomning,forfilter,profil,scheduler,sidhamtning,webbsignal,grounding_gate,outreach_playbook}.py`, `sources/merinfo.py` — grindar, sökprompt, profil, faktagrind, radändringar
- `snajp-support/app/agent/{leads_research_v2,leads_agent,support_systemprompt,support_agent,triage,embeddings}.py`, `agentcore/{packs,instruktioner}.py`
- `snajp-support/app/api/{leads,admin,admin_profil,schemas,drafts,triage}.py`, `email_pipeline/{processor,omformulering}.py`, `storage/{base,memory,postgres}.py`
- `agent-core/overlays/{leads-research-v2,leads-grounding-repair}.md`, `app/api/email-studio/route.ts`
- `components/admin/Agentinstruktioner.tsx`, `components/leads/IrisKorningar.tsx`, `lib/actions/agentinstruktioner.ts`, `lib/admin/sprak.ts`, `lib/snajp/standard.ts`
- `ARCHITECTURE_INVARIANTS.md` (INV-LEADS-EXIST-001, INV-SKILL-003), `snipe-leads.md`, `STATUS.md`, `GOALS.md`, flera tester

## Decisions Made
- **Bygg vidare på Sebbes grundpromptslager:** hans `agent_md` och supportprompt fanns redan; ett eget lager hade dubblerat.
- **Sökningen frågar bara efter bolag:** kontaktkravet drev modellen att hitta på; kontakt hämtas ur bolagets sidor.
- **Inget underlag ⇒ inget modellanrop:** både sanning och kostnad.
- **Radändringar i playbooken i stället för skillredigering:** skillfilen rörs inte, ändringen bär skäl och faller vid import.
- **Redis Iris tas inte in nu:** vår svarscache är strängare, Agent Memory bryter kontamineringsspärren, Context Retriever kräver data i Redis; inbäddningarna var den verkliga svagheten.
- **Bara privata bolag som standard** (Antons regel), med `offentlig_sektor` som kundval.

## Context & Discussion
- Development kör sedan 2026-10-05 20:05 UTC på mallens fem rader som globala instruktioner; sanningsreglerna saknas där.
- Skillkedjan är hel: 414 filer, noll avvikelser mot manifestet; alla tio playbooks renderar. Spårvyn kapar varje fält vid 8 000 tecken.
- Anton bad om steg-för-steg-förklaring av hur skills läses (motorn injicerar, modellen anropar inte) och var filerna ligger; besvarat i chatten.

## Open Threads
- Push av development efter sammanslagning med Sebbes tre nya commits (Antons ord).
- Migration 099 mot båda miljöerna samma dag (Anton).
- Återställ development-instruktionerna och kör `snajp_malgrupp.py --apply` (Antons ord).
- Visuell kontroll + a11y av instruktionsvyn (blockerad av minne).
- Bädda in KB-artiklar på nytt; skarpt Iris-prov N=5; inventering av gamla påhittade leads.
- Fas 7 (insynsvyn), fas 8 (kundens yta), resten av fas 9.

## Cross-Project Handoffs
None this session.

## Current State After This Session
Koden för alla fel Anton såg 2026-10-05 finns lokalt på development och är testad, men ingenting är driftsatt och development kör fortfarande på överskrivna instruktioner. Nästa session: slå ihop Sebbes nya commits, pusha på Antons ord, kör migration 099, återställ instruktionerna, och gör sedan ett skarpt Iris-prov. Därefter fas 7 och 8.

<!-- session-state
date: 2026-10-06
type: bugfix-and-feature
files_created:
  - ~/snipe-leads/snajp-support/app/leads/existens.py
  - ~/snipe-leads/snajp-support/app/leads/offentlig.py
  - ~/snipe-leads/snajp-support/app/agent/leads_systemprompt.py
  - ~/snipe-leads/snajp-support/app/agentcore/baka_in.py
  - ~/snipe-leads/agent-core/prompts/leads-systemprompt.md
  - ~/snipe-leads/supabase/migrations/20261006140000_099_agentinstruktioner_per_agent.sql
  - ~/snipe-leads/scripts/granska_leads_underlag.py
  - ~/snipe-leads/scripts/las_agentinstruktioner.py
  - ~/snipe-leads/scripts/snajp_malgrupp.py
  - ~/snipe-leads/plans/2026-10-06-iris-sanning-malgrupp-instruktioner.md
  - ~/snipe-leads/HANDOFF-2026-10-06-IRIS-SANNING-INSTRUKTIONER.md
files_modified:
  - ~/snipe-leads/snajp-support/app/api/leads.py
  - ~/snipe-leads/snajp-support/app/agent/leads_research_v2.py
  - ~/snipe-leads/components/admin/Agentinstruktioner.tsx
  - ~/snipe-leads/ARCHITECTURE_INVARIANTS.md
  - ~/snipe-leads/STATUS.md
  - ~/snipe-leads/GOALS.md
  - ~/snipe-leads/snipe-leads.md
decisions_made: 6
open_threads: 6
handoffs_pending: []
priority_changes: true
status_updated: true
goals_updated: yes
next_session_focus: "Slå ihop Sebbes nya commits, push och migration 099 på Antons ord, återställ development-instruktionerna, skarpt Iris-prov"
session-state -->
