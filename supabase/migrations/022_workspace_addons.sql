-- Tilläggstjänster per arbetsyta.
--
-- Skilt från `workspaces.products` med flit. `products` säger vilken AGENT
-- kunden köpt (support, leads) och avgör vilka vyer som finns över huvud
-- taget. `addons` säger vad den agenten får GÖRA extra. Att slå ihop dem hade
-- betytt att ett tillägg såg ut som en produkt i navigationen.
--
-- Check-villkoret räknar upp värdena i stället för att lita på applikationen.
-- Motivet är mätt: `agent_runs.agent_type` hade ett villkor som koden bröt mot
-- i ett halvår utan att någon märkte det, eftersom minneslagringen inte
-- validerade. Ett villkor som står i databasen kan inte glida isär från sig
-- självt.

alter table public.workspaces
  add column if not exists addons text[] not null default '{}';

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
      'reports'          -- månatlig sammanställning
    ]::text[]
  );

comment on column public.workspaces.addons is
  'Låsta som default. Ett tomt fält betyder inga tillägg, aldrig alla — '
  'entitlements är fail-closed sedan Fas 3 (lib/data/dashboard.ts).';
