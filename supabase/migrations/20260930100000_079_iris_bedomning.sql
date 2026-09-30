-- Iris-bedömningen på prospektraden (plan nuvarande-problem-leadsagenten,
-- steg 1.8). Uppmätt 2026-09-29 hos Alunix: poäng och motivering sparades
-- aldrig för sökta bolag — UI:t visade "—" och "Ingen poängmotivering
-- sparad." score_total/score_breakdown finns sedan 031; det här är resten.
--
--   motivering     2–3 meningar till kunden: varför bolaget passar eller inte
--                  (INV-LEADS-SCORE-001: får aldrig vara tom efter research).
--   niva           A = alla måste-kriterier uppfyllda, B = möjlig, C = bortvald.
--                  Räknas i kod (app/leads/bedomning.py), aldrig av modellen.
--   profil_version vilken Iris-profil bolaget bedömdes mot — kundens profil
--                  kan ändras efteråt, och en bedömning utan version går inte
--                  att förklara i efterhand.
--   jev            TypeSafe Jevs triage/klassning (app/leads/jev.py), sparad
--                  bredvid kodens nivå för jämförelse.
alter table public.prospects
  add column if not exists motivering text,
  add column if not exists niva text check (niva in ('A', 'B', 'C')),
  add column if not exists profil_version text,
  add column if not exists jev jsonb;

create index if not exists prospects_niva_idx on public.prospects (tenant_id, niva);
