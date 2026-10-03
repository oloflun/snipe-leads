-- 088: NULLIF-vakten på dev_flytt_ko (rättar 085).
--
-- 085 skrev tenant-policyn utan vakten som 068 införde för alla tabeller.
-- Med `app.tenant_id` satt till tom sträng (anslutningspoolens nollställning)
-- kastar `''::uuid` ett fel i stället för att policyn bara inte matchar, så en
-- läsning av flyttkön faller med 500 i stället för att svara tomt. Fångat av
-- tests/test_rls_nullif_vakt.py 2026-10-03.
--
-- Idempotent: drop + create, samma villkor som 068.

drop policy if exists tenant_isolation on public.dev_flytt_ko;
create policy tenant_isolation on public.dev_flytt_ko
  using (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  with check (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);
