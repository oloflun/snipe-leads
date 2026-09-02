-- Leadslistor: tilläggspaketet som bygger färdiga, granskningsbara
-- B2B-leadslistor (plan problembild-en-enda-k-rning, AP7).
--
-- ## Vad tillägget är
--
-- Dagens leads-produkt gör SNÄVA körningar: få bolag, djup research,
-- personligt utkast per bolag. Leadslistor är motsatsen i volym: kunden
-- beställer en lista (ICP + antal), agenten kör discovery-federationen
-- (JobTech-annonser, nyhets-RSS, Gemini-utfyllnad) och levererar en tabell
-- med verifierade bolagsträffar — kontaktväg enligt samma fallback-trappa
-- som leads (INV-CONTACT-001), källa och signal per rad, CSV-export. Inga
-- utkast, ingen sändning (INV-SEC-004: list-jobbet har inget sändverktyg).
--
-- MVP:n är BOLAG ENDAST: privatpersoner kräver en art. 6/14-bedömning som
-- är ett juridiskt beslut, inte ett kodbeslut — flaggat till Anton i
-- handoffen 2026-09-02. item_typ-kolumnen finns redan så datamodellen inte
-- behöver migreras om när/om det beslutet tas.
--
-- ## Samma regel som migration 022/051
--
-- Check-villkoret och addonKeys i lib/addons.ts ändras i SAMMA ändring —
-- det var luckan som gömde "ingen leads-körning har någonsin sparats".

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
      'leadlists'        -- färdiga leadslistor (AP7, 2026-09-02)
    ]::text[]
  );

create table if not exists public.lead_lists (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references public.ss_tenants(id) on delete cascade,
  titel        text not null,
  -- ICP:t som beställdes, fruset vid beställningen — listan ska gå att
  -- granska mot exakt det som efterfrågades, inte mot dagens inställningar.
  icp          jsonb not null default '{}'::jsonb,
  antal        integer not null check (antal between 1 and 200),
  status       text not null default 'bestalld'
               check (status in ('bestalld', 'byggs', 'klar', 'fel')),
  felorsak     text,
  is_test      boolean not null default false,
  created_at   timestamptz not null default now(),
  completed_at timestamptz
);

create table if not exists public.lead_list_items (
  id               uuid primary key default gen_random_uuid(),
  list_id          uuid not null references public.lead_lists(id) on delete cascade,
  tenant_id        uuid not null references public.ss_tenants(id) on delete cascade,
  -- 'bolag' är MVP:ns enda värde. 'privatperson' finns i värdemängden så
  -- ett framtida juridiskt godkännande inte kräver en check-migration —
  -- men INGEN kodväg skriver det värdet i dag.
  item_typ         text not null default 'bolag' check (item_typ in ('bolag', 'privatperson')),
  company_name     text not null,
  website          text,
  ort              text,
  contact_name     text,
  contact_role     text,
  contact_email    text,
  contact_level    text
                   check (contact_level is null or contact_level in
                     ('named_role_match', 'named_other', 'role_address', 'contact_form')),
  -- Varifrån träffen kom (jobtech/nyheter/gemini_sok) + belägget — samma
  -- art. 14-krav som prospect_sources bär (INV-DATA-001).
  source_name      text,
  source_url       text,
  signal           text,
  signal_detalj    text,
  created_at       timestamptz not null default now()
);

create index if not exists lead_lists_tenant_idx
  on public.lead_lists (tenant_id, created_at desc);
create index if not exists lead_list_items_list_idx
  on public.lead_list_items (list_id, created_at);

-- RLS: samma tenant_isolation-mönster som migration 010/051/059.
alter table public.lead_lists enable row level security;
alter table public.lead_lists force row level security;
drop policy if exists tenant_isolation on public.lead_lists;
create policy tenant_isolation on public.lead_lists
  using (tenant_id = current_setting('app.tenant_id', true)::uuid)
  with check (tenant_id = current_setting('app.tenant_id', true)::uuid);

alter table public.lead_list_items enable row level security;
alter table public.lead_list_items force row level security;
drop policy if exists tenant_isolation on public.lead_list_items;
create policy tenant_isolation on public.lead_list_items
  using (tenant_id = current_setting('app.tenant_id', true)::uuid)
  with check (tenant_id = current_setting('app.tenant_id', true)::uuid);

grant select, insert, update, delete on table public.lead_lists to snajp_app;
grant select, insert, update, delete on table public.lead_list_items to snajp_app;

-- OBS DEPLOYORDNING (mönster 058/059): kör migrationen via
-- `python scripts/railway_migrate.py --env development --apply` INNAN koden
-- som skriver tabellerna når miljön.
