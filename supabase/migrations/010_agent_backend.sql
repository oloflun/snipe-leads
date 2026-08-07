-- Agent-backend på DeepSeek v4 Flash (plan Del K). Numrerad 010, inte 009 —
-- 009 gick till G1 (snajp_app-rollen), som måste finnas innan denna körs.
-- Samma RLS-mönster som 003_snajp_multitenant.sql: explicit tenant_id på
-- varje kunddatatabell (även barn-tabeller som prospect_sources/ab_results/
-- outreach_messages/send_queue — ingen policy förlitar sig på en join för
-- isolering, samma val som redan gjorts för ss_messages/ss_conversations).
--
-- agent_skill_packs är medvetet UTAN tenant_id — det är den delade
-- baseline-katalogen (Del B skikt 0-1), inte kunddata.

-- 1. Skill-packs (delad, ingen tenant-isolering) --------------------------

create table if not exists agent_skill_packs (
  id uuid primary key default gen_random_uuid(),
  version text not null unique,  -- Del B: "<manifest_hash>:<playbook-namn>"
  manifest_hash text not null,
  playbook_name text not null,
  changelog text not null default '',
  created_at timestamptz not null default now()
);

-- 2. Agent-konfiguration per tenant + agenttyp -----------------------------

create table if not exists agent_configs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  agent_type text not null check (agent_type in ('support', 'leads')),
  pinned_pack_version text references agent_skill_packs(version),
  instructions_md text not null default '',
  tone text not null default '',
  -- A4: kundkonfigurerbar taxonomi. Applikationen MÅSTE validera varje
  -- värde mot ss_knowledge_base_category_check vid sparning (se TENANTS.md
  -- — databasen har avvikit från migrationerna förut).
  taxonomy text[] not null default '{}',
  language_policy text not null default 'sv_default',
  status text not null default 'draft' check (status in ('draft', 'active', 'paused')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, agent_type)
);

-- 3. Tenant-kontextdokument (produktmarknadsföring, kundresearch, uppladdat,
--    retentionsplaybook) — det som blir kontextpaketet (Del C punkt 1) -----

create table if not exists agent_context_docs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  kind text not null check (kind in
    ('product_marketing', 'customer_research', 'upload', 'retention_playbook')),
  content text not null,
  source text not null default '',
  version int not null default 1,
  created_at timestamptz not null default now()
);

create index if not exists agent_context_docs_tenant_kind_idx
  on agent_context_docs(tenant_id, kind);

-- 4. Feedback och evals (skuggkörning -> godkännande -> pin, Del B) --------

create table if not exists agent_runs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  agent_type text not null check (agent_type in ('support', 'leads')),
  pack_version text not null,
  skills_used text[] not null default '{}',
  input text,
  output text,
  tokens_in int,
  tokens_out int,
  cost_usd numeric(10, 6),
  latency_ms int,
  created_at timestamptz not null default now()
);

create index if not exists agent_runs_tenant_idx on agent_runs(tenant_id);

create table if not exists agent_feedback (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  run_id uuid not null references agent_runs(id) on delete cascade,
  verdict text not null check (verdict in ('good', 'bad', 'needs_review')),
  comment text,
  corrected_output text,
  created_at timestamptz not null default now()
);

create table if not exists agent_evals (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  agent_type text not null check (agent_type in ('support', 'leads')),
  input text not null,
  expected_traits text not null,
  approved_output text,
  created_at timestamptz not null default now()
);

-- 5. Leads: prospekt + proveniens -------------------------------------------

create table if not exists prospects (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  company_name text not null,
  contact_name text,
  contact_email text,
  -- INV-LANG-001: default 'sv', flippar bara på ett bekräftat engelskt svar
  -- från PROSPEKTET (aldrig av engelskt bolagsnamn/profil).
  language_state text not null default 'sv' check (language_state in ('sv', 'en_confirmed')),
  status text not null default 'new' check (status in
    ('new', 'researching', 'ready', 'contacted', 'replied', 'meeting', 'won', 'lost', 'suppressed')),
  created_at timestamptz not null default now()
);

create index if not exists prospects_tenant_idx on prospects(tenant_id);

create table if not exists prospect_sources (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  prospect_id uuid not null references prospects(id) on delete cascade,
  source_url text not null,
  retrieved_at timestamptz not null default now(),
  -- INV-DATA-002: en rad med source_type='linkedin' och is_first_source=true
  -- ska aldrig kunna existera som ENDA raden för ett prospekt — verkställs i
  -- applikationslagret (provenienshgrinden, Del F), inte som en DB-constraint,
  -- eftersom "första källan" är en egenskap av HELA raduppsättningen.
  source_type text not null default 'other' check (source_type in
    ('company_website', 'public_news', 'business_register', 'job_signal',
     'manual_note', 'enrichment_adapter', 'linkedin', 'other')),
  lawful_basis text not null
);

create index if not exists prospect_sources_prospect_idx on prospect_sources(prospect_id);

-- 6. Erbjudanden + A/B (Del H — värdeekvationens fyra spakar) --------------

create table if not exists offers (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  name text not null,
  -- {"dream_outcome": 1-10, "perceived_likelihood": 1-10, "time_delay": 1-10, "effort_sacrifice": 1-10}
  value_equation_scores jsonb not null default '{}'::jsonb,
  weakest_lever text check (weakest_lever in
    ('dream_outcome', 'perceived_likelihood', 'time_delay', 'effort_sacrifice')),
  created_at timestamptz not null default now()
);

create table if not exists ab_variants (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  offer_id uuid not null references offers(id) on delete cascade,
  lever text not null check (lever in
    ('dream_outcome', 'perceived_likelihood', 'time_delay', 'effort_sacrifice')),
  content text not null,
  created_at timestamptz not null default now()
);

-- ab_results: den ENDA tabell G11:s segmentaggregat får läsa ifrån, och
-- bara aggregerat per lever, aldrig radvis. Se migration 011 (G11) för vyn.
create table if not exists ab_results (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  variant_id uuid not null references ab_variants(id) on delete cascade,
  sent int not null default 0,
  replies int not null default 0,
  positive int not null default 0,
  updated_at timestamptz not null default now()
);

-- 7. Outreach + sändkö (G3/INV-SEC-004: modellen kan bara köa) -------------

create table if not exists outreach_threads (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  prospect_id uuid not null references prospects(id) on delete cascade,
  offer_id uuid references offers(id),
  language_state text not null default 'sv' check (language_state in ('sv', 'en_confirmed')),
  last_inbound_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists outreach_messages (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  thread_id uuid not null references outreach_threads(id) on delete cascade,
  direction text not null check (direction in ('inbound', 'outbound')),
  body text not null,
  humanizer_variant text,
  sent_at timestamptz
);

create index if not exists outreach_messages_thread_idx on outreach_messages(thread_id);

create table if not exists send_queue (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references ss_tenants(id),
  thread_id uuid not null references outreach_threads(id) on delete cascade,
  scheduled_at timestamptz not null,
  status text not null default 'queued' check (status in
    ('queued', 'sent', 'cancelled', 'blocked')),
  -- Resultatet av språk-/tidsgrinden vid KÖNING och vid faktisk UTSKICKSTID
  -- (Del J: schemaläggaren kontrollerar grindarna igen — köad tid kan ha
  -- passerat fönstret).
  gate_checks jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists send_queue_scheduled_idx on send_queue(status, scheduled_at);

-- 8. RLS: samma mönster som 003 för varje tabell med tenant_id -------------

do $$
declare
  t text;
begin
  foreach t in array array[
    'agent_configs', 'agent_context_docs', 'agent_runs', 'agent_feedback',
    'agent_evals', 'prospects', 'prospect_sources', 'offers', 'ab_variants',
    'ab_results', 'outreach_threads', 'outreach_messages', 'send_queue'
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

-- agent_skill_packs: delad läsning, ingen tenant-kolumn att filtrera på.
-- Skrivning sker bara via migrationer/adminverktyg, aldrig av snajp_app i
-- körningsläge (grants nedan ger bara select).
alter table agent_skill_packs enable row level security;
alter table agent_skill_packs force row level security;
drop policy if exists skill_packs_read_all on agent_skill_packs;
create policy skill_packs_read_all on agent_skill_packs for select using (true);

-- snajp_app (G1/009) får bara select på skill-packs, inte insert/update —
-- nya packar registreras via migrationer/adminverktyg, inte av tjänsten.
-- Migration 009:s "alter default privileges" ger annars snajp_app
-- select+insert+update på ALLA nya tabeller automatiskt; det motverkas
-- här explicit för just denna tabell.
grant select on table agent_skill_packs to snajp_app;
revoke insert, update on table agent_skill_packs from snajp_app;
