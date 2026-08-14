-- Abonnemang per tenant. Körs efter 009. Idempotent.
--
-- Stripe är källan till sanning för BETALNINGEN; den här tabellen är vår spegel
-- av den, så att kvotkontrollen kan göras utan ett API-anrop till Stripe vid
-- varje kundsvar. Webhooks håller den synkad.
--
-- Taken ligger INTE här utan i app/billing/plans.py, så att en justering av en
-- nivå inte kräver en migration och inte kan hamna i otakt mellan rader.

create table if not exists ss_subscriptions (
  tenant_id uuid primary key references ss_tenants(id) on delete cascade,
  -- Matchar Plan.id i app/billing/plans.py.
  plan_id text not null default 'free',
  -- Speglar Stripes prenumerationsstatus. 'none' = aldrig haft en.
  status text not null default 'none' check (status in
    ('none', 'trialing', 'active', 'past_due', 'canceled', 'unpaid', 'incomplete')),
  stripe_customer_id text,
  stripe_subscription_id text unique,
  -- Perioden kvoten räknas mot. Saknas den används innevarande kalendermånad.
  current_period_start timestamptz,
  current_period_end timestamptz,
  cancel_at_period_end boolean not null default false,
  updated_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create index if not exists ss_subscriptions_customer_idx
  on ss_subscriptions(stripe_customer_id);

-- RLS: samma mönster som resten. En tenant ser bara sitt eget abonnemang.
alter table ss_subscriptions enable row level security;
alter table ss_subscriptions force row level security;
drop policy if exists tenant_isolation on ss_subscriptions;
create policy tenant_isolation on ss_subscriptions
  using (tenant_id = current_setting('app.tenant_id', true)::uuid)
  with check (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Webhooken slår upp tenant via stripe_customer_id INNAN tenant är känd, precis
-- som nyckelvalideringen i 003. Samma undantagsmönster.
drop policy if exists subscription_lookup on ss_subscriptions;
create policy subscription_lookup on ss_subscriptions
  for select
  using (current_setting('app.tenant_id', true) is null);

-- Demo- och pilot-tenanten ska aldrig kvotstoppas.
insert into ss_subscriptions (tenant_id, plan_id, status)
values
  ('00000000-0000-4000-a000-000000000001', 'intern', 'active'),
  ('00000000-0000-4000-a000-000000000002', 'intern', 'active')
on conflict (tenant_id) do nothing;
