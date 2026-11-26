-- 161: Snajp CRM, Antons svar 2026-11-26 i schemat (docs/BESLUT.md samma dag).
--
-- 1. CRM:et är ett tillägg. Nyckeln 'crm' läggs i workspaces_addons_check,
--    i samma ändring som lib/addons.ts (tests/test_tillagg_synk.py håller
--    dem ihop). Tillgången avgörs i app/crm/tillgang.py: tillägget, eller en
--    provperiod som inte gått ut (workspaces.trial_slut, migration 074).
-- 2. Privatpersoner. Synken hoppar över dem om anslutningen inte uttryckligen
--    slår på dem (crm_anslutningar.privatpersoner). Påslagna sparas de utan
--    personnummer, märks (crm_bolag.privatperson) och får kontakta_inte =
--    true: Snajp är ett B2B-verktyg, och marknadsföring till konsumenter
--    kräver samtycke och NIX-kontroll.
-- 3. Papperskorgen läses nyast raderad först: ett eget index för den frågan.
--
-- Additiv och idempotent.

-- 1. Tillägget ------------------------------------------------------------

alter table public.workspaces
  drop constraint if exists workspaces_addons_check;

alter table public.workspaces
  add constraint workspaces_addons_check check (
    addons <@ array[
      'inbox',           -- kundens riktiga IMAP-inkorg kopplad
      'vision',          -- bildanalys av kundens bifogade foton
      'kb_autoingest',   -- kunskapsbasen synkas från kundens egen sajt
      'multilang',       -- engelsk agent vid sidan av den svenska
      'own_domain',      -- chatten på kundens egen domän
      'reports',         -- månatlig sammanställning
      'leadlists',       -- färdiga leadslistor (AP7, 2026-09-02)
      'crm'              -- Snajp CRM (2026-11-26), fritt under provperioden
    ]::text[]
  );

-- 2. Privatpersoner -------------------------------------------------------

alter table public.crm_anslutningar
  add column if not exists privatpersoner boolean not null default false;
alter table public.crm_bolag
  add column if not exists privatperson boolean not null default false;

-- En privatperson får aldrig stå som kontaktbar. Villkoret gör regeln till
-- databasens, inte bara kodens.
alter table public.crm_bolag drop constraint if exists crm_bolag_privatperson_check;
alter table public.crm_bolag add constraint crm_bolag_privatperson_check
  check (not privatperson or kontakta_inte);

comment on column public.crm_anslutningar.privatpersoner is
  'Synkar anslutningen också privatpersoner? Falskt som standard: de hoppas då över '
  '(app/crm/synk.py, orsaken privatperson).';
comment on column public.crm_bolag.privatperson is
  'Kunden är en privatperson, inte ett bolag. Inget personnummer sparas, och raden '
  'har alltid kontakta_inte = true (crm_bolag_privatperson_check).';

-- 3. Papperskorgen --------------------------------------------------------

create index if not exists crm_bolag_raderad_idx
  on public.crm_bolag (tenant_id, raderad_at desc) where raderad_at is not null;
create index if not exists crm_personer_raderad_idx
  on public.crm_personer (tenant_id, raderad_at desc) where raderad_at is not null;
