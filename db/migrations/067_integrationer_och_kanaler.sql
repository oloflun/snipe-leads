-- 067: Integrationer och kanaler för support-agenten (bd snipe-36u).
--
-- OBS: körs via scripts/railway_migrate.py mot Railway — katalognamnet är
-- historiskt, filen ska aldrig köras mot Supabase (se CLAUDE.md).
--
-- ## Vad och varför
--
-- Ebbot-researchen 2026-09-18: deras agent "går att integrera med de flesta
-- ärendehanterings- och CRM-system ... så länge det finns öppna API:er eller
-- MCP", och den svarar i WhatsApp, Messenger, Slack och Teams. Motsvarigheten
-- här:
--
--   ss_integrations          kundens HTTP-verktyg (Ebbot-kompatibel
--                            requests-array) och MCP-servrar. Läses av
--                            app/integrationer/.
--   ss_channel_connections   kundens anslutning till en meddelandekanal
--                            (WhatsApp Cloud API, Messenger, Slack, Teams).
--   ss_channel_contacts      vem på kanalen som är vilken kund hos oss, och
--                            vart ett svar ska skickas (Teams behöver en hel
--                            konversationsreferens, inte bara ett id).
--   ss_channel_inbound_seen  dubblettspärr: Meta och Slack skickar om samma
--                            webhook vid minsta tvekan, och en omsändning ska
--                            inte ge kunden två svar.
--
-- ## Hemligheterna
--
-- `hemligheter_krypterat` är EN Fernet-token (INTEGRATION_NYCKEL, se
-- app/integrationer/hemligheter.py). `hemlighetsnamn` är namnen i klartext,
-- så att portalen kan visa vilka nycklar som finns utan att dekryptera.
-- Konfigurationen (`konfig`) innehåller aldrig ett hemligt värde; den visas i
-- portalen och loggas i felspår.
--
-- ## Rättigheter
--
-- Default privileges (009) ger snajp_app select/insert/update på nya tabeller,
-- aldrig delete (se 041). Integrationer och kanalanslutningar går att ta bort
-- i portalen, och dubblettspärren städas — därför uttryckliga delete-grants.
--
-- Idempotent enligt husets regel: kan köras om utan verkan.

-- -- Integrationer --------------------------------------------------------

create table if not exists ss_integrations (
  id                     uuid primary key default gen_random_uuid(),
  tenant_id              uuid not null references ss_tenants(id) on delete cascade,
  typ                    text not null check (typ in ('http', 'mcp')),
  namn                   text not null check (length(namn) between 1 and 80),
  beskrivning            text not null default '',
  konfig                 jsonb not null default '{}'::jsonb,
  hemlighetsnamn         text[] not null default '{}',
  hemligheter_krypterat  text,
  aktiv                  boolean not null default true,
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now()
);

create unique index if not exists ss_integrations_tenant_namn_key
  on ss_integrations (tenant_id, lower(namn));

alter table ss_integrations enable row level security;
alter table ss_integrations force row level security;
drop policy if exists tenant_isolation on ss_integrations;
create policy tenant_isolation on ss_integrations
  using (tenant_id = current_setting('app.tenant_id', true)::uuid)
  with check (tenant_id = current_setting('app.tenant_id', true)::uuid);

comment on table ss_integrations is
  'Kundens HTTP-verktyg och MCP-servrar åt support-agenten (067, bd snipe-36u). Hemligheter krypterade med INTEGRATION_NYCKEL.';

-- -- Kanalanslutningar ----------------------------------------------------

create table if not exists ss_channel_connections (
  id                     uuid primary key default gen_random_uuid(),
  tenant_id              uuid not null references ss_tenants(id) on delete cascade,
  kanal                  text not null check (kanal in ('whatsapp', 'messenger', 'slack', 'teams')),
  namn                   text not null default '',
  -- Kanalens eget id för anslutningen: WhatsApp phone_number_id, Messenger
  -- page_id, Slack team_id, Teams bot-appens id. Unikt per kanal ÖVER alla
  -- tenants — ett och samma WhatsApp-nummer kan inte svara för två kunder.
  extern_id              text not null check (length(extern_id) between 1 and 200),
  konfig                 jsonb not null default '{}'::jsonb,
  hemlighetsnamn         text[] not null default '{}',
  hemligheter_krypterat  text,
  aktiv                  boolean not null default true,
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now()
);

create unique index if not exists ss_channel_connections_kanal_extern_key
  on ss_channel_connections (kanal, extern_id);
create index if not exists ss_channel_connections_tenant_idx
  on ss_channel_connections (tenant_id);

alter table ss_channel_connections enable row level security;
alter table ss_channel_connections force row level security;
drop policy if exists tenant_isolation on ss_channel_connections;
create policy tenant_isolation on ss_channel_connections
  using (tenant_id = current_setting('app.tenant_id', true)::uuid)
  with check (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- -- Kanalkontakter -------------------------------------------------------

create table if not exists ss_channel_contacts (
  id                     uuid primary key default gen_random_uuid(),
  tenant_id              uuid not null references ss_tenants(id) on delete cascade,
  anslutning_id          uuid not null references ss_channel_connections(id) on delete cascade,
  customer_id            uuid not null references ss_customers(id) on delete cascade,
  -- WhatsApp: wa_id (telefonnummer). Messenger: PSID. Slack: användar-id.
  -- Teams: aad-objekt-id eller kanalens användar-id.
  extern_anvandare       text not null,
  -- Allt som behövs för att SKICKA till kontakten senare (medarbetarsvar i
  -- sömlös överlämning): Slack-kanal, Teams serviceUrl + konversations-id.
  adress                 jsonb not null default '{}'::jsonb,
  visningsnamn           text,
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now(),
  unique (anslutning_id, extern_anvandare)
);

create index if not exists ss_channel_contacts_kund_idx
  on ss_channel_contacts (tenant_id, customer_id, updated_at desc);

alter table ss_channel_contacts enable row level security;
alter table ss_channel_contacts force row level security;
drop policy if exists tenant_isolation on ss_channel_contacts;
create policy tenant_isolation on ss_channel_contacts
  using (tenant_id = current_setting('app.tenant_id', true)::uuid)
  with check (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- -- Dubblettspärr för inkommande -----------------------------------------

create table if not exists ss_channel_inbound_seen (
  anslutning_id          uuid not null references ss_channel_connections(id) on delete cascade,
  extern_meddelande_id   text not null,
  tenant_id              uuid not null references ss_tenants(id) on delete cascade,
  seen_at                timestamptz not null default now(),
  primary key (anslutning_id, extern_meddelande_id)
);

create index if not exists ss_channel_inbound_seen_tid_idx
  on ss_channel_inbound_seen (seen_at);

alter table ss_channel_inbound_seen enable row level security;
alter table ss_channel_inbound_seen force row level security;
drop policy if exists tenant_isolation on ss_channel_inbound_seen;
create policy tenant_isolation on ss_channel_inbound_seen
  using (tenant_id = current_setting('app.tenant_id', true)::uuid)
  with check (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- -- Ärendets kanal -------------------------------------------------------
--
-- 002 tillät web/email/whatsapp. Messenger, Slack och Teams läggs till;
-- inget befintligt värde försvinner.

alter table ss_tickets drop constraint if exists ss_tickets_channel_check;
alter table ss_tickets add constraint ss_tickets_channel_check
  check (channel in ('web', 'email', 'whatsapp', 'messenger', 'slack', 'teams'));

-- Globala standardvärden (tenant_id null) för de nya kanalernas ton och längd.
-- WhatsApp fanns redan (002). Längden följer kanalens egna gränser med
-- marginal: Messenger kapar vid 2 000 tecken, Slack och Teams läses som chatt.
insert into ss_channel_configs (channel, tone, max_length)
select v.channel, v.tone, v.max_length
from (values
  ('messenger', 'kortfattad och vardaglig men artig', 900),
  ('slack', 'saklig och kortfattad, som en hjälpsam kollega', 1200),
  ('teams', 'saklig och kortfattad, som en hjälpsam kollega', 1200)
) as v(channel, tone, max_length)
where not exists (
  select 1 from ss_channel_configs c where c.channel = v.channel and c.tenant_id is null
);

-- -- Rättigheter ----------------------------------------------------------

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    grant delete on table ss_integrations to snajp_app;
    grant delete on table ss_channel_connections to snajp_app;
    grant delete on table ss_channel_contacts to snajp_app;
    grant delete on table ss_channel_inbound_seen to snajp_app;
  end if;
end $$;
