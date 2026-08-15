-- Den andra halvan av INV-SEC-001-grinden. Kör TILLSAMMANS med 028.
--
-- 028 gjorde att oskopade frågor slutade KRASCHA under `snajp_app`. Den gjorde
-- dem inte användbara. Uppmätt mot preview-spegeln, som `snajp_app`:
--
--     list_tenants_with_stats:  4 rader   (rätt antal — men nollställda tal)
--     list_agent_runs_all:      0 rader   (spegeln har 10)
--     list_tenants:             4 rader   (tenant_lookup räddar den)
--
-- Adminvyn hade alltså visat "inga körningar" och fyra kunder med noll ärenden
-- och noll tokens. Tyst. Trovärdiga men felaktiga tal är värre än en tom vy,
-- eftersom ingen ifrågasätter dem.
--
-- ORSAKEN: `agent_runs.tenant_isolation` kräver `tenant_id = app.tenant_id`.
-- Adminläsningarna är OSKOPADE med flit — de spänner över alla kunder — och
-- `postgres` kom undan med det genom BYPASSRLS. `snajp_app` är nobypassrls.
--
-- LÖSNINGEN följer ett mönster som redan finns i schemat: `ss_tenants`
-- har sedan 003 policyn `tenant_lookup`, som tillåter läsning när INGEN
-- tenant-kontext är satt (schemaläggaren måste kunna räkna upp kunder).
-- Samma villkor, samma resonemang, utökat till de tabeller admin-routern
-- faktiskt läser.
--
-- SÄKERHETSRESONEMANGET: villkoret är inte "snajp_app får läsa allt". Det är
-- "när ingen tenant är satt får den läsa över tenants". Så fort en tenant är
-- satt — vilket varje kundvänd kodväg gör via _scoped() — gäller
-- tenant_isolation som förut. Den oskopade vägen finns bara i app/api/admin.py,
-- som i sin helhet ligger bakom require_master_key.

-- 1. Läsning över tenants för adminytan.
do $$
declare
  t text;
begin
  foreach t in array array[
    'agent_runs',        -- /admin/korningar och spårvyn
    'ss_tickets',        -- nyckeltalen i kundöversikten
    'platform_events',   -- notiscentret (har redan en egen policy, tas med för fullständighet)
    'ss_emails',         -- /admin/kunder/<id>/inkorg
    'send_queue',        -- granskningskön i adminvyn
    'outreach_threads',
    'outreach_messages',
    'prospects'
  ] loop
    execute format('drop policy if exists %I on public.%I', t || '_admin_read', t);
    execute format(
      'create policy %I on public.%I for select to snajp_app '
      'using (nullif(current_setting(''app.tenant_id'', true), '''') is null)',
      t || '_admin_read', t
    );
  end loop;
end $$;

-- 2. Administrativ tenant-skapning.
--
-- `storage.create_tenant()` kör oskopat (den skapar tenanten — det finns ingen
-- kontext att sätta ännu) och blockerades av WITH CHECK på `tenant_self`:
--
--     new row violates row-level security policy for table "ss_tenants"
--
-- Det syntes som en uppstartsvarning: KB-seedningen misslyckades tyst och
-- lämnade en kund utan kunskapsbas, alltså en agent som eskalerar allt.
--
-- Samma villkor som ovan: bara när ingen tenant-kontext är satt. Den enda
-- HTTP-vägen hit är POST /api/keys, bakom require_master_key.
drop policy if exists ss_tenants_admin_write on public.ss_tenants;
create policy ss_tenants_admin_write on public.ss_tenants
  for all to snajp_app
  using (nullif(current_setting('app.tenant_id', true), '') is null)
  with check (nullif(current_setting('app.tenant_id', true), '') is null);

-- Verifiering efter körning — som snajp_app, utan tenant-kontext:
--   select count(*) from agent_runs;   -- ska ge samma antal som postgres ser
--   insert into ss_tenants (slug, name) values ('rls-test', 'RLS-test');
--   delete from ss_tenants where slug = 'rls-test';
