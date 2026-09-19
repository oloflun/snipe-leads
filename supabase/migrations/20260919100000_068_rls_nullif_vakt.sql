-- 028:s NULLIF-vakt på de elva tenant-policyer som skapats efter 028.
--
-- 028 skrev om varje policy som fanns då: `app.tenant_id` är '' och inte NULL
-- efter första användningen på en poolad anslutning, och utan NULLIF kastar
-- en oskopad fråga `invalid input syntax for type uuid: ""` i stället för att
-- ge noll rader. Tabellerna nedan kom till senare (051, 052, 059, 060, 061,
-- 066, 067) med villkoret skrivet på det gamla sättet. scripts/lokal_stack.py
-- fångar det: kedjan rest från noll stannade på sin egen kontroll.
-- tests/test_rls_nullif_vakt.py fäller nästa migration som glömmer vakten.
--
-- Innebörden är i övrigt identisk: samma tabeller, samma namn, FOR ALL,
-- TO public, samma USING och WITH CHECK. Tidsstämpelnamnet är avsiktligt:
-- ss_sending_domains skapas i en tidsstämpelnamngiven fil, och kedjan körs i
-- sorterad filordning.

drop policy if exists tenant_isolation on public.agent_suggestions;
create policy tenant_isolation on public.agent_suggestions for all to public
  using (tenant_id = (nullif(current_setting('app.tenant_id', true), ''))::uuid)
  with check (tenant_id = (nullif(current_setting('app.tenant_id', true), ''))::uuid);

drop policy if exists tenant_isolation on public.customer_memory;
create policy tenant_isolation on public.customer_memory for all to public
  using (tenant_id = (nullif(current_setting('app.tenant_id', true), ''))::uuid)
  with check (tenant_id = (nullif(current_setting('app.tenant_id', true), ''))::uuid);

drop policy if exists tenant_isolation on public.leads_job_ledger;
create policy tenant_isolation on public.leads_job_ledger for all to public
  using (tenant_id = (nullif(current_setting('app.tenant_id', true), ''))::uuid)
  with check (tenant_id = (nullif(current_setting('app.tenant_id', true), ''))::uuid);

drop policy if exists tenant_isolation on public.lead_lists;
create policy tenant_isolation on public.lead_lists for all to public
  using (tenant_id = (nullif(current_setting('app.tenant_id', true), ''))::uuid)
  with check (tenant_id = (nullif(current_setting('app.tenant_id', true), ''))::uuid);

drop policy if exists tenant_isolation on public.lead_list_items;
create policy tenant_isolation on public.lead_list_items for all to public
  using (tenant_id = (nullif(current_setting('app.tenant_id', true), ''))::uuid)
  with check (tenant_id = (nullif(current_setting('app.tenant_id', true), ''))::uuid);

drop policy if exists sending_domains_tenant on public.ss_sending_domains;
create policy sending_domains_tenant on public.ss_sending_domains for all to public
  using (tenant_id = (nullif(current_setting('app.tenant_id', true), ''))::uuid)
  with check (tenant_id = (nullif(current_setting('app.tenant_id', true), ''))::uuid);

-- 066/067 (support-samtal, integrationer, kanaler). Villkorat på att tabellen
-- finns: kedjan ska gå att resa även i en databas där de ännu inte körts.
do $$
declare
  t text;
begin
  foreach t in array array['ss_chat_state', 'ss_integrations', 'ss_channel_connections',
                           'ss_channel_contacts', 'ss_channel_inbound_seen']
  loop
    if to_regclass('public.' || t) is not null then
      execute format('drop policy if exists tenant_isolation on public.%I', t);
      execute format(
        'create policy tenant_isolation on public.%I for all to public
           using (tenant_id = (nullif(current_setting(''app.tenant_id'', true), ''''))::uuid)
           with check (tenant_id = (nullif(current_setting(''app.tenant_id'', true), ''''))::uuid)', t);
    end if;
  end loop;
end $$;
