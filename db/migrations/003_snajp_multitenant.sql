-- Snajp-Support: multi-tenant.
-- Lägger till ss_tenants, tenant_id på alla kunddatatabeller (backfyllt till
-- default-tenanten Nordlys Handel) samt RLS-policyer per tenant.
--
-- OBS RLS-förbehåll: Supabase-rollen "postgres" kan ha BYPASSRLS. Policyerna
-- nedan är därför försvar-på-djupet — applikationen filtrerar dessutom alltid
-- explicit på tenant_id och sätter set_config('app.tenant_id', ...) per
-- transaktion. För produktion, skapa en dedikerad roll utan bypass, t.ex.:
--   create role snajp_app login password '...';
--   grant usage on schema public to snajp_app;
--   grant select, insert, update on all tables in schema public to snajp_app;
-- och låt tjänstens DATABASE_URL använda den rollen.

-- 1. Tenants ---------------------------------------------------------------

create table if not exists ss_tenants (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

-- Default-tenant med fast UUID; all befintlig data backfylls hit.
insert into ss_tenants (id, slug, name)
values ('00000000-0000-4000-a000-000000000001', 'nordlys-handel', 'Nordlys Handel')
on conflict (slug) do nothing;

-- 2. tenant_id på kunddatatabellerna ---------------------------------------

do $$
declare
  t text;
begin
  foreach t in array array[
    'ss_customers', 'ss_customer_identifiers', 'ss_tickets', 'ss_conversations',
    'ss_messages', 'ss_knowledge_base', 'ss_agent_metrics', 'ss_api_keys'
  ] loop
    execute format(
      'alter table %I add column if not exists tenant_id uuid references ss_tenants(id)', t);
    execute format(
      'update %I set tenant_id = ''00000000-0000-4000-a000-000000000001'' where tenant_id is null', t);
    execute format('alter table %I alter column tenant_id set not null', t);
    execute format('create index if not exists %I on %I(tenant_id)', t || '_tenant_idx', t);
  end loop;
end $$;

-- Samma e-post/telefon måste kunna finnas hos flera tenants.
alter table ss_customer_identifiers
  drop constraint if exists ss_customer_identifiers_type_value_key;
alter table ss_customer_identifiers
  add constraint ss_customer_identifiers_tenant_type_value_key unique (tenant_id, type, value);

-- 3. Kanalkonfiguration: NULL tenant_id = global default, annars per tenant --

alter table ss_channel_configs add column if not exists tenant_id uuid references ss_tenants(id);
alter table ss_channel_configs add column if not exists id uuid not null default gen_random_uuid();
alter table ss_channel_configs drop constraint if exists ss_channel_configs_pkey;
alter table ss_channel_configs add primary key (id);
-- Unik per (tenant, kanal); globala rader (NULL) hanteras via coalesce-sentinel.
create unique index if not exists ss_channel_configs_tenant_channel_key
  on ss_channel_configs (
    coalesce(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid), channel);

-- 4. RLS: varje tenant ser bara sina egna rader -----------------------------

do $$
declare
  t text;
begin
  foreach t in array array[
    'ss_customers', 'ss_customer_identifiers', 'ss_tickets', 'ss_conversations',
    'ss_messages', 'ss_knowledge_base', 'ss_agent_metrics', 'ss_api_keys'
  ] loop
    execute format('alter table %I enable row level security', t);
    execute format('alter table %I force row level security', t);
    execute format('drop policy if exists tenant_isolation on %I', t);
    execute format(
      'create policy tenant_isolation on %I
         using (tenant_id = current_setting(''app.tenant_id'', true)::uuid)
         with check (tenant_id = current_setting(''app.tenant_id'', true)::uuid)', t);
  end loop;
end $$;

-- Tenant-tabellen: en session ser bara sin egen tenant-rad.
alter table ss_tenants enable row level security;
alter table ss_tenants force row level security;
drop policy if exists tenant_self on ss_tenants;
create policy tenant_self on ss_tenants
  using (id = current_setting('app.tenant_id', true)::uuid);

-- Kanalkonfig: egna rader + de globala default-raderna (läsning).
alter table ss_channel_configs enable row level security;
alter table ss_channel_configs force row level security;
drop policy if exists tenant_channel_read on ss_channel_configs;
create policy tenant_channel_read on ss_channel_configs
  using (tenant_id is null or tenant_id = current_setting('app.tenant_id', true)::uuid)
  with check (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Undantag för nyckeluppslag: valideringen av en API-nyckel sker INNAN tenant
-- är känd. Den görs därför av admin-anslutningen (utan app.tenant_id) i
-- Postgres-läget; policyerna ovan blockerar den inte för rollen postgres
-- (ägare/bypass), men en dedikerad snajp_app-roll behöver denna policy:
drop policy if exists api_key_lookup on ss_api_keys;
create policy api_key_lookup on ss_api_keys
  for select
  using (current_setting('app.tenant_id', true) is null);

-- Nyckelvalideringen joinar ss_tenants (för active-flaggan) innan tenant är känd.
drop policy if exists tenant_lookup on ss_tenants;
create policy tenant_lookup on ss_tenants
  for select
  using (current_setting('app.tenant_id', true) is null);
