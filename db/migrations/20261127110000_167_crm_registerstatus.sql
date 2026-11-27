-- 167: Snajp CRM, bolagets status i SCB:s företagsregister.
--
-- Antons beslut 2026-11-27 (docs/crm/SVENSK-STANDARD.md § 4 fråga 4, svar 10:
-- ja, bara bolagsnivå): ett bolag kan berikas ur SCB:s företagsregister
-- (app/crm/scb.py, POST /api/crm/v1/companies/{id}/enrich).
--
-- crm_bolag.registerstatus: vad registret senast sa om bolaget, i API:ts egna
--   ord: 'active' (verksamt), 'inactive' (ej verksamt), 'never_active' (aldrig
--   verksamt), 'deregistered' (avregistrerat, avfört, konkurs eller
--   likvidation avslutad, upplöst) eller 'unknown'. Skrivs bara av
--   berikningen, aldrig av synken eller för hand.
-- crm_bolag.registret_last_at: när registret senast lästes för bolaget.
--
-- Registret ger aldrig personer här: inga firmatecknare, ingen styrelse, inga
-- innehavare. En enskild firma slås inte upp alls.
--
-- Inga nya tabeller: radskyddet, grants och force row level security från 160
-- gäller de nya kolumnerna som de står. Additiv och idempotent.

alter table public.crm_bolag add column if not exists registerstatus text;
alter table public.crm_bolag add column if not exists registret_last_at timestamptz;

alter table public.crm_bolag drop constraint if exists crm_bolag_registerstatus_check;
alter table public.crm_bolag add constraint crm_bolag_registerstatus_check
  check (registerstatus is null
         or registerstatus in ('active', 'inactive', 'never_active', 'deregistered', 'unknown'));
