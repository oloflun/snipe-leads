-- 093: sidcache för leads (plan 2026-10-05, fas 2).
--
-- 109 ScrapeGraph-krediter på en dag (2026-10-04). Cachen låg i en
-- processdict som försvann vid varje deploy, och researchen hade ingen alls,
-- så samma merinfo-sida betalades två gånger i samma körning och om igen i
-- nästa. Den här tabellen är cachen för app/leads/sidhamtning.py: en rad per
-- (kund, url), innehållet som text, eller felet när hämtningen misslyckades.
--
-- Per kund och inte global med flit: RLS-mönstret är detsamma som resten av
-- leadstabellerna, och vinsten av att dela en publik sida mellan kunder är
-- liten mot risken med en tabell utan tenant-isolering.

create table if not exists public.leads_sidcache (
  tenant_id  uuid not null references public.ss_tenants(id) on delete cascade,
  url        text not null,
  -- Null när hämtningen misslyckades; då bär `fel` skälet och raden
  -- lever kortare (ett dygn, se sidhamtning.FEL_LIVSLANGD).
  innehall   text,
  fel        text,
  hamtad_at  timestamptz not null default now(),
  primary key (tenant_id, url)
);

comment on table public.leads_sidcache is
  'Hämtade sidor för leads per kund (app/leads/sidhamtning.py). Livslängden '
  'avgörs i koden per sorts sida: listsidor 7 dagar, bolagssidor 30, sajter 14.';

alter table public.leads_sidcache enable row level security;
alter table public.leads_sidcache force row level security;
drop policy if exists tenant_isolation on public.leads_sidcache;
create policy tenant_isolation on public.leads_sidcache
  using (tenant_id = current_setting('app.tenant_id', true)::uuid)
  with check (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Default privileges ger snajp_app select/insert/update (se 041/087).
-- Ingen kodväg raderar i cachen, så ingen delete-grant behövs. Raderna
-- försvinner med kunden (on delete cascade) eller skrivs över.

-- OBS DEPLOYORDNING: kör migrationen innan koden når miljön. Utan tabellen
-- loggar sidhamtning ett fel per sida och hämtar utan cache (den fäller inte
-- körningen), men varje anrop kostar då en kredit.
