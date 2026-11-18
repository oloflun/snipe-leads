-- 089: NULLIF-vakten på Leads Suite-tabellerna (rättar 086).
--
-- 086 skrev tenant-policyerna i en DO-loop med format(), utan vakten som 068
-- införde. Med `app.tenant_id` satt till tom sträng (anslutningspoolens
-- nollställning) kastar `''::uuid` ett fel i stället för att policyn bara inte
-- matchar. tests/test_rls_nullif_vakt.py såg det inte: citattecknen är
-- dubblade inuti format()-strängen. Fångat när den lokala stacken restes
-- 2026-10-03; regexen läser nu båda formerna.
--
-- Idempotent: drop + create, samma villkor som 068 och 088.

do $$
declare
  t text;
begin
  foreach t in array array['lead_anteckningar', 'lead_uppgifter', 'prospect_status_logg', 'lead_vyer']
  loop
    execute format('drop policy if exists tenant_isolation on public.%I', t);
    execute format(
      'create policy tenant_isolation on public.%I
         using (tenant_id = nullif(current_setting(''app.tenant_id'', true), '''')::uuid)
         with check (tenant_id = nullif(current_setting(''app.tenant_id'', true), '''')::uuid)',
      t
    );
  end loop;
end
$$;
