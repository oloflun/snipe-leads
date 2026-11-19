-- 095: appen får läsa spegelmarkören (Flytta till main, plan del E).
--
-- Uppmätt 2026-10-05: public.mirror_meta har radnivåsäkerhet påslagen men
-- ingen policy, så snajp_app ser noll rader. spegel_info() svarade då None i
-- development, panelen "Flytta till main" renderades aldrig (den visas bara i
-- en spegel), och mottagarens spärr mot import i en spegel slutade gälla.
--
-- Tabellen finns bara där nattspegeln skapat den (development), så allt sker
-- villkorat: i main är filen en no-op. Bara läsning: markören skrivs av
-- scripts/railway_seed_dev.py med en privilegierad anslutning.
do $$
begin
  if to_regclass('public.mirror_meta') is not null
     and exists (select 1 from pg_roles where rolname = 'snajp_app') then
    drop policy if exists app_las_markor on public.mirror_meta;
    create policy app_las_markor on public.mirror_meta for select to snajp_app using (true);
    grant select on table public.mirror_meta to snajp_app;
  end if;
end $$;
