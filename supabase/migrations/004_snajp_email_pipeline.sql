-- Snajp-Support: email-pipeline (inkorg → triage → utkast/autosvar → granskning).
-- Körs efter 002 + 003. Alla tabeller är tenant-skopade med samma RLS-mönster
-- som 003_snajp_multitenant.sql.

-- Anslutna inkorgar (Gmail/Outlook via IMAP, eller mock för test).
create table if not exists ss_mailboxes (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  provider text not null check (provider in ('gmail', 'outlook', 'imap', 'mock')),
  address text not null,
  status text not null default 'active' check (status in ('active', 'error', 'disabled')),
  last_sync_at timestamptz,
  last_error text,
  created_at timestamptz not null default now(),
  unique (tenant_id, address)
);

-- Råmail som de kom in (en rad per inkommande mail, dedupe på provider_message_id).
create table if not exists ss_emails (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  mailbox_id uuid references ss_mailboxes(id),
  provider text not null default 'mock',
  provider_message_id text not null,
  from_email text not null,
  from_name text,
  subject text not null default '',
  body_text text not null default '',
  received_at timestamptz not null default now(),
  status text not null default 'new' check (status in
    ('new', 'processing', 'awaiting_approval', 'auto_sent', 'sent',
     'escalated', 'rejected', 'taken_over', 'failed')),
  ticket_id uuid references ss_tickets(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, provider_message_id)
);

create index if not exists ss_emails_status_idx on ss_emails(tenant_id, status);
create index if not exists ss_emails_received_idx on ss_emails(tenant_id, received_at desc);

create table if not exists ss_email_attachments (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  email_id uuid not null references ss_emails(id) on delete cascade,
  filename text not null,
  content_type text not null,
  size_bytes integer not null default 0,
  -- data-URL (base64). Enkelt och portabelt; flytta till objektlagring vid volym.
  data_url text,
  is_image boolean not null default false,
  created_at timestamptz not null default now()
);

-- Agentens klassificering av varje mail (fack, sentiment, konfidens, motivering).
create table if not exists ss_classifications (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  email_id uuid not null references ss_emails(id) on delete cascade,
  category text not null check (category in
    ('teknisk_support', 'leverans', 'betalning', 'retur_reklamation',
     'orderstatus', 'konto', 'ovrigt')),
  priority text not null default 'normal',
  sentiment numeric(3, 2),
  confidence numeric(3, 2) not null default 0.5,
  escalate boolean not null default false,
  escalation_reason text,
  reasoning text,                 -- varför agenten valde detta (beslutslogg i klartext)
  kb_sources jsonb not null default '[]',
  model text not null default 'simulation',
  created_at timestamptz not null default now()
);

-- AI-genererade svarsutkast som väntar på (eller passerat) mänsklig granskning.
create table if not exists ss_drafts (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  email_id uuid not null references ss_emails(id) on delete cascade,
  ticket_id uuid references ss_tickets(id),
  content text not null,
  status text not null default 'pending' check (status in
    ('pending', 'approved', 'rejected', 'auto_sent')),
  auto boolean not null default false,
  confidence numeric(3, 2) not null default 0.5,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ss_drafts_status_idx on ss_drafts(tenant_id, status);

-- Mänskliga granskningsbeslut (godkänn/redigera/avvisa/ta över).
create table if not exists ss_human_reviews (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  draft_id uuid not null references ss_drafts(id) on delete cascade,
  action text not null check (action in ('approve', 'edit', 'reject', 'takeover')),
  edited_content text,
  note text,
  created_at timestamptz not null default now()
);

-- Regler per fack: auto = skicka direkt, draft = kräver godkännande, escalate = alltid människa.
create table if not exists ss_category_rules (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  category text not null,
  mode text not null default 'draft' check (mode in ('auto', 'draft', 'escalate')),
  unique (tenant_id, category)
);

-- Logg över varje beslut agenten tar (mottaget, klassificerat, eskalerat, skickat ...).
create table if not exists ss_decision_log (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  email_id uuid references ss_emails(id) on delete cascade,
  event text not null,
  detail jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create index if not exists ss_decision_log_email_idx on ss_decision_log(tenant_id, email_id);

-- Utöka ticket-kategorierna med orderstatus (nytt fack i denna iteration).
alter table ss_tickets drop constraint if exists ss_tickets_category_check;
alter table ss_tickets add constraint ss_tickets_category_check check (category in
  ('teknisk_support', 'leverans', 'betalning', 'retur_reklamation',
   'orderstatus', 'konto', 'ovrigt'));
alter table ss_knowledge_base drop constraint if exists ss_knowledge_base_category_check;
alter table ss_knowledge_base add constraint ss_knowledge_base_category_check check (category in
  ('teknisk_support', 'leverans', 'betalning', 'retur_reklamation',
   'orderstatus', 'konto', 'ovrigt'));

-- RLS: samma mönster som 003.
do $$
declare
  t text;
begin
  foreach t in array array[
    'ss_mailboxes', 'ss_emails', 'ss_email_attachments', 'ss_classifications',
    'ss_drafts', 'ss_human_reviews', 'ss_category_rules', 'ss_decision_log'
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
