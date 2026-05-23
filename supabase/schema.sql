create extension if not exists "pgcrypto";

create table if not exists public.workspaces (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  locale text not null default 'sv-SE',
  timezone text not null default 'Europe/Stockholm',
  created_at timestamptz not null default now()
);

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  full_name text not null,
  role text not null default 'member',
  created_at timestamptz not null default now()
);

create table if not exists public.business_contexts (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  product text not null,
  target_audience text not null,
  industries text[] not null default '{}',
  geography text[] not null default '{}',
  tone text not null,
  offer text not null,
  cta text not null,
  contact_roles text[] not null default '{}',
  updated_at timestamptz not null default now()
);

create table if not exists public.companies (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  name text not null,
  website text,
  industry text not null,
  location text not null,
  company_size text,
  source text not null default 'mock',
  lead_score integer not null default 0 check (lead_score between 0 and 100),
  status text not null default 'researching',
  created_at timestamptz not null default now()
);

create table if not exists public.contacts (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  company_id uuid not null references public.companies(id) on delete cascade,
  full_name text not null,
  role text not null,
  email text,
  linkedin text,
  source text not null default 'manual',
  objection_status text,
  suppression_status text,
  created_at timestamptz not null default now()
);

create table if not exists public.lead_signals (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  company_id uuid not null references public.companies(id) on delete cascade,
  signal_type text not null,
  signal_title text not null,
  signal_summary text not null,
  source_url text,
  detected_at timestamptz not null default now(),
  confidence_score numeric(4,3) not null default 0 check (confidence_score >= 0 and confidence_score <= 1)
);

create table if not exists public.company_insights (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  company_id uuid not null references public.companies(id) on delete cascade,
  summary text not null,
  pain_points jsonb not null default '[]'::jsonb,
  opportunities jsonb not null default '[]'::jsonb,
  recommended_angle text not null,
  recommended_cta text not null,
  updated_at timestamptz not null default now()
);

create table if not exists public.campaigns (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  name text not null,
  product text not null,
  target_audience text not null,
  geography text not null,
  tonalitet text not null,
  offer text not null,
  cta text not null,
  status text not null default 'draft',
  created_at timestamptz not null default now()
);

create table if not exists public.sequences (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  campaign_id uuid not null references public.campaigns(id) on delete cascade,
  name text not null,
  stop_on_reply boolean not null default true,
  send_window text not null default 'Tue-Thu 08:30-15:20 Europe/Stockholm',
  status text not null default 'draft',
  created_at timestamptz not null default now()
);

create table if not exists public.sequence_steps (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  sequence_id uuid not null references public.sequences(id) on delete cascade,
  step_order integer not null,
  wait_days integer not null default 0,
  variant_type text not null,
  goal text not null
);

create table if not exists public.generated_emails (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  campaign_id uuid references public.campaigns(id) on delete set null,
  contact_id uuid references public.contacts(id) on delete set null,
  sequence_id uuid references public.sequences(id) on delete set null,
  subject text not null,
  body text not null,
  variant_length text not null,
  variant_type text not null,
  tone_version text not null default 'sv-low-key-v1',
  status text not null default 'draft',
  sent_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.email_events (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  generated_email_id uuid not null references public.generated_emails(id) on delete cascade,
  event_type text not null,
  event_timestamp timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists public.meetings (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  contact_id uuid references public.contacts(id) on delete set null,
  campaign_id uuid references public.campaigns(id) on delete set null,
  status text not null default 'proposed',
  booked_for timestamptz,
  source text not null default 'email'
);

create table if not exists public.suppressions (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  contact_id uuid references public.contacts(id) on delete cascade,
  email text not null,
  reason text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  actor_user_id uuid references auth.users(id) on delete set null,
  action text not null,
  entity_type text not null,
  entity_id uuid,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.workspaces enable row level security;
alter table public.profiles enable row level security;
alter table public.business_contexts enable row level security;
alter table public.companies enable row level security;
alter table public.contacts enable row level security;
alter table public.lead_signals enable row level security;
alter table public.company_insights enable row level security;
alter table public.campaigns enable row level security;
alter table public.sequences enable row level security;
alter table public.sequence_steps enable row level security;
alter table public.generated_emails enable row level security;
alter table public.email_events enable row level security;
alter table public.meetings enable row level security;
alter table public.suppressions enable row level security;
alter table public.audit_logs enable row level security;

create or replace function public.current_workspace_id()
returns uuid
language sql
security definer
stable
as $$
  select workspace_id from public.profiles where id = auth.uid()
$$;

create policy "workspace members can read workspace"
on public.workspaces for select
using (id = public.current_workspace_id());

create policy "members can manage own profile"
on public.profiles for select
using (workspace_id = public.current_workspace_id());

create policy "workspace scoped business contexts"
on public.business_contexts for all
using (workspace_id = public.current_workspace_id())
with check (workspace_id = public.current_workspace_id());

create policy "workspace scoped companies"
on public.companies for all
using (workspace_id = public.current_workspace_id())
with check (workspace_id = public.current_workspace_id());

create policy "workspace scoped contacts"
on public.contacts for all
using (workspace_id = public.current_workspace_id())
with check (workspace_id = public.current_workspace_id());

create policy "workspace scoped lead signals"
on public.lead_signals for all
using (workspace_id = public.current_workspace_id())
with check (workspace_id = public.current_workspace_id());

create policy "workspace scoped company insights"
on public.company_insights for all
using (workspace_id = public.current_workspace_id())
with check (workspace_id = public.current_workspace_id());

create policy "workspace scoped campaigns"
on public.campaigns for all
using (workspace_id = public.current_workspace_id())
with check (workspace_id = public.current_workspace_id());

create policy "workspace scoped sequences"
on public.sequences for all
using (workspace_id = public.current_workspace_id())
with check (workspace_id = public.current_workspace_id());

create policy "workspace scoped sequence steps"
on public.sequence_steps for all
using (workspace_id = public.current_workspace_id())
with check (workspace_id = public.current_workspace_id());

create policy "workspace scoped generated emails"
on public.generated_emails for all
using (workspace_id = public.current_workspace_id())
with check (workspace_id = public.current_workspace_id());

create policy "workspace scoped email events"
on public.email_events for all
using (workspace_id = public.current_workspace_id())
with check (workspace_id = public.current_workspace_id());

create policy "workspace scoped meetings"
on public.meetings for all
using (workspace_id = public.current_workspace_id())
with check (workspace_id = public.current_workspace_id());

create policy "workspace scoped suppressions"
on public.suppressions for all
using (workspace_id = public.current_workspace_id())
with check (workspace_id = public.current_workspace_id());

create policy "workspace scoped audit logs"
on public.audit_logs for select
using (workspace_id = public.current_workspace_id());
