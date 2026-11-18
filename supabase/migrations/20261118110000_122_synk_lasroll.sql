-- 122: en roll som bara får läsa, för synken hos Railway.
--
-- docs/compliance/synkflytt-plan.md, upplägg A: synken flyttar från GitHub
-- Actions till en cron-tjänst i Railway-miljön main. Den läser produktionen
-- över mains privata nät och ska då inte vara superanvändaren postgres, utan
-- en roll som inte KAN skriva: riktningen main -> development ska gälla även om
-- koden ändras. railway_synk.main_kan_skriva vägrar köra hos Railway om
-- main-anslutningen får ändra någon tabell (INV-DATA-008).
--
-- Rollen skapas UTAN inloggning och utan lösenord. Ett lösenord i en migration
-- hamnar i git. Ägaren slår på inloggningen i main, och bara där, med
-- `alter role synk_las with login password ...` och ett värde som läses ur
-- stdin (docs/compliance/synkflytt-runbook.md, steg 6). I development, där
-- migrationen körs av sig själv vid pushen, blir rollen alltså en roll som
-- ingen kan logga in som: den finns, men ingen väg leder till den.
--
-- Idempotent: en befintlig roll lämnas som den är (en ny körning får inte
-- stänga av inloggningen ägaren slagit på). Additiv: bara nya rättigheter till
-- den nya rollen; inget som finns ändras.
--
-- BYPASSRLS: de synkade tabellerna har radnivåsäkerhet med policyer på
-- app.tenant_id, och synken läser alla kunder. Läsrätten är ändå begränsad till
-- tabellerna nedan: de 28 i railway_synk.SYNK, ss_tenants (snittet av kunder),
-- synk_raderingar (raderingsloggen, 111), mirror_meta (spärren mot en
-- spegelmarkör i main; tabellen saknas oftast i main och tas då inte med) och
-- migrationsliggaren (schemajämförelsen).

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'synk_las') then
    create role synk_las nologin bypassrls;
  end if;
end $$;

-- Varje transaktion som rollen öppnar är skrivskyddad, utöver att rollen
-- saknar skrivrätt och att synken öppnar main med readonly=True.
alter role synk_las set default_transaction_read_only = on;

grant usage on schema public to synk_las;
grant usage on schema supabase_migrations to synk_las;
grant select on table supabase_migrations.schema_migrations to synk_las;

do $$
declare
  t text;
begin
  foreach t in array array[
    'ss_customers', 'ss_customer_identifiers', 'ss_tickets', 'ss_conversations',
    'ss_messages', 'ss_emails', 'ss_email_attachments', 'ss_classifications',
    'ss_decision_log', 'ss_drafts', 'ss_human_reviews', 'ss_agent_metrics',
    'customer_memory', 'agent_suggestions', 'prospects', 'prospect_sources',
    'prospect_status_logg', 'outreach_threads', 'outreach_messages', 'send_queue',
    'lead_lists', 'lead_list_items', 'lead_samtal', 'lead_anteckningar',
    'lead_uppgifter', 'suppressions', 'leads_job_ledger', 'agent_runs',
    'ss_tenants', 'synk_raderingar', 'mirror_meta'
  ] loop
    if to_regclass('public.' || t) is not null then
      execute format('grant select on table public.%I to synk_las', t);
    end if;
  end loop;
end $$;
