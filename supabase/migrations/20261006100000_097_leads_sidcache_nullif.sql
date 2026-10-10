-- 097: NULLIF-vakten på leads_sidcache (rättar 093).
--
-- 093 skrev tenant-policyn utan vakten som 068 införde för alla tabeller.
-- Med `app.tenant_id` satt till tom sträng (anslutningspoolens nollställning)
-- kastar `''::uuid` ett fel i stället för att policyn bara inte matchar, så en
-- cacheläsning på en återanvänd anslutning faller i stället för att svara
-- tomt — och sidhamtning hämtar då om sidan och betalar krediten igen.
-- Fångat av tests/test_rls_nullif_vakt.py 2026-10-06.
--
-- Idempotent: drop + create, samma villkor som 068/088.

drop policy if exists tenant_isolation on public.leads_sidcache;
create policy tenant_isolation on public.leads_sidcache
  using (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  with check (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);
