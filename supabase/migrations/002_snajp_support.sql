-- Snajp-Support: kundservice-agentens schema (prefix ss_ för att inte krocka med Snipra-tabellerna).
-- Arkitekturen speglar jawwad-ali/ai-customer-support-agent: CRM + tickets + pgvector-KB i samma databas.

create extension if not exists vector;
create extension if not exists pgcrypto;

create table if not exists ss_customers (
  id uuid primary key default gen_random_uuid(),
  name text,
  created_at timestamptz not null default now()
);

create table if not exists ss_customer_identifiers (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid not null references ss_customers(id) on delete cascade,
  type text not null check (type in ('email', 'phone')),
  value text not null,
  created_at timestamptz not null default now(),
  unique (type, value)
);

create table if not exists ss_tickets (
  id uuid primary key default gen_random_uuid(),
  customer_id uuid not null references ss_customers(id) on delete cascade,
  subject text not null default '',
  category text not null default 'ovrigt' check (category in
    ('teknisk_support', 'leverans', 'betalning', 'retur_reklamation', 'konto', 'ovrigt')),
  status text not null default 'open' check (status in
    ('open', 'in_progress', 'escalated', 'resolved', 'closed')),
  priority text not null default 'normal' check (priority in ('low', 'normal', 'high')),
  escalation_reason text,
  channel text not null default 'web' check (channel in ('web', 'email', 'whatsapp')),
  parent_ticket_id uuid references ss_tickets(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ss_tickets_customer_idx on ss_tickets(customer_id);
create index if not exists ss_tickets_category_idx on ss_tickets(category);

create table if not exists ss_conversations (
  id uuid primary key default gen_random_uuid(),
  ticket_id uuid not null unique references ss_tickets(id) on delete cascade,
  channel text not null default 'web',
  created_at timestamptz not null default now()
);

create table if not exists ss_messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references ss_conversations(id) on delete cascade,
  direction text not null check (direction in ('inbound', 'outbound')),
  content text not null,
  sentiment numeric(3, 2) check (sentiment >= 0 and sentiment <= 1),
  has_image boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists ss_messages_conversation_idx on ss_messages(conversation_id);

create table if not exists ss_knowledge_base (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  content text not null,
  category text not null default 'ovrigt' check (category in
    ('teknisk_support', 'leverans', 'betalning', 'retur_reklamation', 'konto', 'ovrigt')),
  embedding vector(1536),
  search_tsv tsvector generated always as
    (to_tsvector('swedish', title || ' ' || content)) stored,
  created_at timestamptz not null default now()
);

create index if not exists ss_kb_tsv_idx on ss_knowledge_base using gin(search_tsv);
create index if not exists ss_kb_embedding_idx on ss_knowledge_base
  using ivfflat (embedding vector_cosine_ops) with (lists = 10);

create table if not exists ss_channel_configs (
  channel text primary key,
  tone text not null,
  max_length integer not null
);

insert into ss_channel_configs (channel, tone, max_length) values
  ('web', 'halvformell, vänlig och lösningsorienterad', 1500),
  ('email', 'formell, professionell och tydlig', 2500),
  ('whatsapp', 'kortfattad och vardaglig men artig', 800)
on conflict (channel) do nothing;

create table if not exists ss_agent_metrics (
  id uuid primary key default gen_random_uuid(),
  ticket_id uuid references ss_tickets(id) on delete set null,
  metric_name text not null,
  value numeric,
  created_at timestamptz not null default now()
);

create table if not exists ss_api_keys (
  id uuid primary key default gen_random_uuid(),
  tenant_name text not null,
  key_prefix text not null,
  key_hash text not null unique,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  last_used_at timestamptz
);
