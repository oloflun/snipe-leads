-- Snajp-Support: self-service (egen ton/systemprompt, egna nycklar) + förbrukningsmätning.
-- Körs efter 005. Idempotent.
--
-- Tillför tre saker:
--   1. Tenantens egna inställningar — ton och branschprompt, så SYSTEM_PROMPT
--      inte längre är hårdkodad till hjärtstartarbranschen.
--   2. Nyckelmetadata — etikett + återkallande, så en kund kan hantera sina egna
--      nycklar utan att någon behöver redigera .env.
--   3. ss_usage — antal svar och tokens per tenant, underlag för framtida tak
--      och fakturering. INGEN betalning här, bara mätningen.
--
-- OBS samma RLS-förbehåll som i 003: Supabase-rollen "postgres" kan ha BYPASSRLS,
-- så policyerna nedan är försvar-på-djupet. Den faktiska isoleringen bärs av att
-- applikationen alltid filtrerar explicit på tenant_id och sätter
-- set_config('app.tenant_id', ...) per transaktion.

-- 1. Tenantens egna inställningar ------------------------------------------

alter table ss_tenants add column if not exists company_name text;
-- Tom ton => kanalens default i ss_channel_configs används (oförändrat beteende).
alter table ss_tenants add column if not exists tone text;
-- Läggs till SIST i systemprompten. Kärnreglerna (arbetsordning, grundningsregel,
-- eskalering) ligger kvar i koden och kan inte skrivas över av en kund.
alter table ss_tenants add column if not exists system_prompt_extra text;
alter table ss_tenants add column if not exists updated_at timestamptz not null default now();

-- 2. Nyckelmetadata ---------------------------------------------------------
-- (key_prefix, active och last_used_at finns redan från 002.)

alter table ss_api_keys add column if not exists label text;
alter table ss_api_keys add column if not exists revoked_at timestamptz;

-- 3. Förbrukning ------------------------------------------------------------

create table if not exists ss_usage (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  -- Vad förbrukningen kom från. Nya källor läggs till här när de byggs.
  kind text not null default 'chat' check (kind in
    ('chat', 'triage', 'email_draft', 'embedding')),
  model text not null default 'simulation',
  -- Simuleringsläget kostar ingenting men ska ändå synas som aktivitet —
  -- annars ser ett testkört konto ut som noll förbrukning.
  simulated boolean not null default false,
  prompt_tokens integer not null default 0,
  completion_tokens integer not null default 0,
  total_tokens integer not null default 0,
  -- Svarsräkningen är antal rader; responses finns som separat kolumn för de
  -- fall ett anrop genererar flera svar (batch-triage).
  responses integer not null default 1,
  ticket_id uuid references ss_tickets(id) on delete set null,
  email_id uuid references ss_emails(id) on delete set null,
  created_at timestamptz not null default now()
);

create index if not exists ss_usage_tenant_created_idx
  on ss_usage(tenant_id, created_at desc);

-- 4. RLS: samma mönster som 003/004 ----------------------------------------

alter table ss_usage enable row level security;
alter table ss_usage force row level security;
drop policy if exists tenant_isolation on ss_usage;
create policy tenant_isolation on ss_usage
  using (tenant_id = current_setting('app.tenant_id', true)::uuid)
  with check (tenant_id = current_setting('app.tenant_id', true)::uuid);
