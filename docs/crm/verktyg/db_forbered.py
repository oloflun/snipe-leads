"""Reser det CRM-migrationerna behöver i en tom PGlite, och kör dem två gånger.

Hela migrationskedjan går inte att resa i PGlite (tillägg, roller och auth-
schemat saknas), så här skapas bara det CRM-migrationerna pekar på: kunderna,
prospekten, arbetsytorna, nycklarna och appens roll. Migrationerna själva körs
som de står, två gånger, för att visa att de är omkörbara.
"""
import sys
from pathlib import Path

import psycopg2

DSN = "postgresql://postgres:postgres@127.0.0.1:54329/postgres?sslmode=disable"
MIG = Path(r"C:\Users\Anton L\snipe-leads\.claude\worktrees\snajp-crm-dd0d83\db\migrations")

FORE = """
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'snajp_app') then
    create role snajp_app nologin nobypassrls;
  end if;
end $$;
create table if not exists public.ss_tenants (
  id uuid primary key default gen_random_uuid(), slug text not null unique, name text not null,
  created_at timestamptz not null default now());
create table if not exists public.prospects (id uuid primary key default gen_random_uuid());
create table if not exists public.workspaces (
  id uuid primary key default gen_random_uuid(), ss_tenant_id uuid, addons text[] not null default '{}',
  trial_slut date, created_at timestamptz not null default now());
create table if not exists public.ss_api_keys (
  id uuid primary key default gen_random_uuid(), tenant_id uuid not null references public.ss_tenants(id),
  key_hash text not null unique, key_prefix text not null, active boolean not null default true,
  created_at timestamptz not null default now(), last_used_at timestamptz);
alter table public.ss_api_keys add column if not exists tenant_name text;
-- Som kedjan: active (003) och policyerna tenant_self/tenant_lookup med NULLIF (028).
alter table public.ss_tenants add column if not exists active boolean not null default true;
alter table public.ss_tenants enable row level security;
alter table public.ss_tenants force row level security;
drop policy if exists tenant_self on public.ss_tenants;
create policy tenant_self on public.ss_tenants
  using (id = nullif(current_setting('app.tenant_id', true), '')::uuid);
drop policy if exists tenant_lookup on public.ss_tenants;
create policy tenant_lookup on public.ss_tenants for select
  using (nullif(current_setting('app.tenant_id', true), '') is null);
grant usage on schema public to snajp_app;
grant select, insert, update, delete on public.ss_tenants, public.ss_api_keys, public.workspaces to snajp_app;
"""

conn = psycopg2.connect(DSN, connect_timeout=8)
conn.autocommit = True
cur = conn.cursor()
cur.execute(FORE)
filer = sorted(f for f in MIG.glob("*.sql") if any(f"_{n}_crm" in f.name for n in sys.argv[1:] or ["160", "161", "162", "163"]))
for varv in (1, 2):
    for fil in filer:
        try:
            cur.execute(fil.read_text(encoding="utf-8"))
            print(f"varv {varv}: {fil.name} ok")
        except psycopg2.Error as fel:
            print(f"varv {varv}: {fil.name} FEL: {str(fel).strip()[:500]}")
            sys.exit(1)
cur.execute("select count(*) from information_schema.tables where table_schema = 'public' and table_name like 'crm_%'")
print("crm-tabeller:", cur.fetchone()[0])
