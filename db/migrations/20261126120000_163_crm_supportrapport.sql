-- 163: Snajp CRM, synkens rapport till supporten (Antons svar 2026-11-26).
--
-- Kunden ser synkens förlopp och felen i enkla ord, med beskedet att de gått
-- vidare till supporten. Supporten får hela rapporten med koder. Rapporten
-- byggs när körningen avslutas (app/crm/supportrapport.py) och sparas på
-- körningen, så att den finns kvar efter en omladdning och inte beror på att
-- någon tittar just då.
--
-- supportrapport     hela rapporten: räknare, anslutningens inställningar och
--                    varje felrad med kod. Värden som inte gick att tolka står
--                    med sin FORM (siffror som 9, bokstäver som a), inte med
--                    innehållet: en felskriven adress är fortfarande en adress.
-- support_lamnad_at  när rapporten lades fram till supporten.
-- support_arende     ärendets nummer, satt av supportsystemet när det tagit
--                    emot rapporten (POST /api/admin/crm/supportrapporter/…).
--
-- Additiv och idempotent.

alter table public.crm_synkkorningar add column if not exists supportrapport jsonb;
alter table public.crm_synkkorningar add column if not exists support_lamnad_at timestamptz;
alter table public.crm_synkkorningar add column if not exists support_arende text;

create index if not exists crm_synkkorningar_support_idx
  on public.crm_synkkorningar (tenant_id, support_lamnad_at desc)
  where support_lamnad_at is not null;

comment on column public.crm_synkkorningar.supportrapport is
  'Hela felrapporten till supporten (migration 163). Felaktiga värden står med sin form, '
  'inte med innehållet. Byggs av app/crm/supportrapport.py när körningen avslutas.';
