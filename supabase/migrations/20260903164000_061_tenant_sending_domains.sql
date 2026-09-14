-- Per-tenant Resend sending identity. DNS secrets are public records, never API keys.
create table if not exists ss_sending_domains (
  tenant_id uuid primary key references ss_tenants(id) on delete cascade,
  resend_domain_id text not null unique,
  sending_domain text not null,
  from_local_part text not null default 'support',
  from_name text not null default '',
  reply_to text not null,
  status text not null default 'not_started',
  dns_records jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
alter table ss_sending_domains enable row level security;
create policy sending_domains_tenant on ss_sending_domains using (tenant_id=current_setting('app.tenant_id',true)::uuid) with check (tenant_id=current_setting('app.tenant_id',true)::uuid);
grant select,insert,update on ss_sending_domains to snajp_app;
