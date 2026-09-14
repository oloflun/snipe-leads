-- Railway-kompatibilitetslager: gör vanlig Postgres tillräckligt Supabase-lik
-- för att migration 000–029 ska köra OFÖRÄNDRADE.
--
-- VARFÖR SÅ HÄR, OCH INTE GENOM ATT SKRIVA OM MIGRATIONERNA:
--
-- Kartläggningen i plans/2026-08-16-railway-enad-stack.md hittade att hela
-- Supabase-beroendet i SQL går genom EN funktion: `auth.uid()`. 15 av 17
-- policyer läser den. Byts funktionens KROPP följer alla med automatiskt.
-- Att i stället söka-och-ersätta i 30 migrationsfiler hade betytt 30 tillfällen
-- att tappa något — och migrationskedjan är det enda vi har som bevisar att
-- schemat går att resa från noll.
--
-- Så: `auth`-schemat och `auth.uid()` byggs här, med samma signatur men egen
-- kropp. Alla FK:er, triggern `on_auth_user_created` och
-- `ensure_workspace_for_user`s läsning av `auth.users.email` fortsätter fungera
-- ordagrant. Auth.js skriver i `auth.users` i stället för GoTrue.
--
-- Identiteten kommer från samma mekanism som backenden redan använder för
-- tenants: en GUC satt per transaktion. Ett mönster i kodbasen i stället för
-- två.

create extension if not exists "pgcrypto";

-- 1. Rollerna som Supabase tillhandahåller ---------------------------------
-- `anon`, `authenticated` och `service_role` finns bara för att GRANT/REVOKE i
-- migrationerna ska ha något att peka på. De används inte för inloggning här;
-- appen ansluter som `snajp_app`. 018_rpc_hardening REVOKE:ar från dem, och en
-- REVOKE mot en icke-existerande roll är ett hårt fel — därför måste de finnas.

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then
    create role anon nologin noinherit;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    create role authenticated nologin noinherit;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role') then
    create role service_role nologin noinherit bypassrls;
  end if;
end
$$;

-- 2. auth-schemat ----------------------------------------------------------

create schema if not exists auth;

-- Kolumnerna är exakt de som migrationerna och app-koden faktiskt läser:
--   id                  — FK-mål för profiles, audit_logs, workspace_invites,
--                         platform_admins (fyra tabeller)
--   email               — 006_auth_selfheal:69 och 021_seed_platform_admin
--   raw_user_meta_data  — 001_handle_new_user:14 (full_name)
-- Resten är Auth.js egna behov. Inget mer, eftersom varje extra kolumn är en
-- kolumn någon senare tror att GoTrue underhåller.
create table if not exists auth.users (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  encrypted_password text,
  email_confirmed_at timestamptz,
  raw_user_meta_data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Citext finns inte garanterat; unikhet på lower(email) ger samma sak och är
-- samma form som workspace_invites redan använder.
create unique index if not exists auth_users_email_key on auth.users (lower(email));

-- 3. auth.uid() ------------------------------------------------------------
-- Samma signatur som Supabases. Kroppen läser en GUC i stället för en JWT.
--
-- NULLIF är inte kosmetik: `current_setting(..., true)` ger tom sträng, aldrig
-- NULL, efter första skopade transaktionen på en poolad anslutning. Utan
-- NULLIF kastas ''::uuid och varje senare oskopad fråga kraschar. Exakt buggen
-- som migration 028 fick städa upp i produktion.

create or replace function auth.uid()
returns uuid
language sql
stable
as $$
  select nullif(current_setting('app.user_id', true), '')::uuid
$$;

grant usage on schema auth to public;
grant select on auth.users to public;
