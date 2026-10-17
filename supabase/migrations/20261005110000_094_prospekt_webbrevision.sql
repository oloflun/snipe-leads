-- 094: webbrevisionen på prospektet (plan 2026-10-05, fas 3).
--
-- PageSpeed-poäng, bildbedömningens modernitetsbetyg (1-10), layoutepok och
-- de tre synliga bristerna (app/leads/webbrevision.py). Betyget avgör
-- webbkriterierna i kod (bedomning.webbutslag) och visas i Leads-tabellen;
-- bristerna är underlag för mejlets ingång. Skärmbilden sparas aldrig.

alter table public.prospects
  add column if not exists webbrevision jsonb;
