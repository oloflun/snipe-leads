-- G1 (INV-SEC-001): dedicated Postgres role for the Snajp-Support service,
-- without BYPASSRLS. Closes the gap flagged but never fixed in
-- 003_snajp_multitenant.sql:5-12 — the service's DATABASE_URL has run as the
-- Supabase "postgres" role since multi-tenancy shipped, and that role can
-- bypass row level security, making every tenant_isolation policy decorative
-- for that connection. Least privilege, scoped only to the ss_* tables the
-- Python service actually touches — not "all tables in schema public".
--
-- This migration creates the role and grants. It does NOT set a password —
-- that is generated and applied out-of-band (never committed to git) and the
-- deployed DATABASE_URL is cut over separately, manually, after verifying the
-- new role can do everything the service needs. See ARCHITECTURE_INVARIANTS.md
-- INV-SEC-001.

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'snajp_app') then
    create role snajp_app with login nobypassrls;
  else
    alter role snajp_app with login nobypassrls;
  end if;
end $$;

grant usage on schema public to snajp_app;

grant select, insert, update on table
  ss_tenants,
  ss_customers,
  ss_customer_identifiers,
  ss_tickets,
  ss_conversations,
  ss_messages,
  ss_knowledge_base,
  ss_channel_configs,
  ss_agent_metrics,
  ss_api_keys,
  ss_mailboxes,
  ss_emails,
  ss_email_attachments,
  ss_classifications,
  ss_drafts,
  ss_human_reviews,
  ss_category_rules,
  ss_decision_log
to snajp_app;

-- Tables migration 009 (Del K) and later add to the ss_/agent_ surface are
-- picked up automatically, provided they're created by the same role that
-- runs migrations (the Supabase MCP / dashboard SQL editor default role).
alter default privileges in schema public
  grant select, insert, update on tables to snajp_app;
