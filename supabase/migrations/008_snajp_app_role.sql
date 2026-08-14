-- Snajp-Support: dedikerad applikationsroll UTAN bypass, så RLS faktiskt gäller.
-- Körs efter 007. Idempotent.
--
-- BAKGRUND — det här är hela poängen med migrationen:
-- Policyerna i 003/004/006 ser bra ut men är i praktiken verkningslösa i dag.
-- Tjänsten ansluter som `postgres.<project_ref>` (pooler-användaren för rollen
-- `postgres`), och den rollen har BYPASSRLS i Supabase. En roll med BYPASSRLS
-- går förbi alla policyer — även `FORCE ROW LEVEL SECURITY`. Det som håller
-- isär tenants i drift är alltså ENBART att applikationskoden filtrerar på
-- tenant_id. En enda glömd where-sats räcker för en läcka.
--
-- Efter den här migrationen finns en roll som inte kan gå förbi RLS. Byt
-- DATABASE_URL till den rollen, så blir databasen det andra försvarslagret
-- som var tänkt från början.
--
-- OBS: kräver ett lösenord. Sätt det i psql-sessionen INNAN körning, t.ex.
--   \set snajp_app_password 'ett-starkt-losenord'
-- eller ersätt platshållaren nedan manuellt. Lägg aldrig lösenordet i repot.

-- 1. Rollen -----------------------------------------------------------------

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'snajp_app') then
    -- Byt ut lösenordet innan körning.
    execute 'create role snajp_app login password ' || quote_literal('BYT-MIG-INNAN-KORNING');
  end if;
end $$;

-- Uttryckligen ingen bypass, ingen superuser, ingen rollskapning.
alter role snajp_app nobypassrls nosuperuser nocreatedb nocreaterole;

-- 2. Rättigheter -------------------------------------------------------------
-- Rollen ska kunna läsa och skriva kunddata, men inte ändra schemat.

grant usage on schema public to snajp_app;

grant select, insert, update, delete on
  ss_tenants, ss_customers, ss_customer_identifiers, ss_tickets,
  ss_conversations, ss_messages, ss_knowledge_base, ss_agent_metrics,
  ss_api_keys, ss_channel_configs, ss_usage,
  ss_mailboxes, ss_emails, ss_email_attachments, ss_classifications,
  ss_drafts, ss_human_reviews, ss_category_rules, ss_decision_log
to snajp_app;

grant usage, select on all sequences in schema public to snajp_app;

-- Framtida ss_-tabeller ska inte behöva kommas ihåg här.
alter default privileges in schema public
  grant select, insert, update, delete on tables to snajp_app;
alter default privileges in schema public
  grant usage, select on sequences to snajp_app;

-- 3. Kontroll ----------------------------------------------------------------
-- Ska returnera false. Gör den inte det är hela övningen meningslös.

do $$
declare
  bypasses boolean;
begin
  select rolbypassrls into bypasses from pg_roles where rolname = 'snajp_app';
  if bypasses then
    raise exception 'snajp_app har BYPASSRLS — RLS skulle fortsätta vara verkningslös.';
  end if;
  raise notice 'snajp_app skapad utan BYPASSRLS. Byt DATABASE_URL till denna roll.';
end $$;

-- 4. Efter körning -----------------------------------------------------------
-- a) Sätt lösenordet:  alter role snajp_app password '<starkt lösenord>';
-- b) Byt DATABASE_URL (Render + .env) till:
--      postgresql://snajp_app.<project_ref>:<lösenord>@aws-0-eu-west-1.pooler.supabase.com:6543/postgres
-- c) Verifiera med testsviten:
--      $env:TEST_DATABASE_URL = "<samma sträng mot en engångsdatabas>"
--      python -m pytest tests/test_rls_enforcement.py -v
--    test_role_does_not_bypass_rls faller om fel roll används.
