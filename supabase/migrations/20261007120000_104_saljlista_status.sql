-- 104: Statusfärg per rad i säljlistan (Sebbes beställning 2026-10-06, kväll).
--
-- Raderna i säljlistan ska kunna färgläggas efter hur samtalet gick:
--   'salt'      grönt  — affären är i hamn
--   'signering' blått  — väntar på signering
--   'nej'       rött   — tackade nej
--   'ej_svar'   gult   — svarade inte
--   ''          ingen färg (default)
--
-- Koderna är svenska som resten av tabellen; färg och etikett sätts i UI:t
-- (components/leads/Saljlista.tsx), inte här — databasen lagrar läget, inte
-- utseendet. Idempotent.

alter table public.saljlista
  add column if not exists status text not null default '';

alter table public.saljlista
  drop constraint if exists saljlista_status_check;
alter table public.saljlista
  add constraint saljlista_status_check
    check (status in ('', 'salt', 'signering', 'nej', 'ej_svar'));
