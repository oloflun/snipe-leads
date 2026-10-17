-- 109: api-rollen (snajp_app) får läsa och skriva suppressions.
--
-- Upptäckt 2026-10-08: varje godkänt utkast föll i sändaren med
-- `permission denied for table suppressions`. send_guard regel 3 läser
-- listan (storage.list_suppressions) direkt före varje utskick, och
-- avregistreringar/studsar skriver dit (storage.add_suppression). Policyn
-- suppressions_tenant_isolation för snajp_app finns sedan 030, men tabellen
-- grantades aldrig till rollen — bara snajp_web har rättigheter. Inget
-- utskick som nått sändspärrarna har därför kunnat gå ut som snajp_app.
--
-- RLS gäller som förut: snajp_app ser bara raderna för app.tenant_id.

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    grant select, insert on table public.suppressions to snajp_app;
  end if;
end $$;
