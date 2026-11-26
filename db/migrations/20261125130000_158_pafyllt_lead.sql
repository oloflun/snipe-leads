-- 158: ett påfyllt Iris-lead märks (Antons regel 2026-11-24).
--
-- "Iris får aldrig, under inga omständigheter leverera under beställt antal,
-- i värsta fall får man ta ett av de (mest kvalificerade) bortsorterade
-- bolagen för att fylla ut kvoten, om inga fullt kvalificerade hittas."
--
--   prospects.pafylld       leadet fyllde på kvoten (korning.py § Påfyllnaden)
--   prospects.pafylld_skal  koden för det närmaste skälet ("b", "a:62:70",
--                           "storlek:anstallda:max:55:49"), som gränssnittet
--                           översätter till kundens språk ("Påfyllt: …").
--                           Aldrig webbrevisionens fält.
--
-- Leadet behåller sin riktiga bedömning (nivå, poäng, skäl). Flaggan är det
-- uttryckliga undantaget som släpper det förbi leadslistans, leverbarhetens
-- och sändspärrens krav på nivå A/B (INV-LEADS-EXIST-001).
--
-- Additiv och idempotent. false/null på gamla rader: inget ändras för dem.

alter table public.prospects
  add column if not exists pafylld boolean not null default false,
  add column if not exists pafylld_skal text;
