-- Adminytans paketkolumn: läsning av workspaces.products över tenants.
--
-- `list_tenants_with_stats` läser paketet ur `workspaces.products` i en egen
-- fråga (tillagd 2026-09-13, testarfynd: översikten visade "Snajp Duo" efter
-- bytet till Trio och adminvyn gissade paketet ur aktiviteten). Frågan körs
-- OSKOPAD under `snajp_app`, men `workspaces` har bara policyn
-- "workspace members can read workspace" (000), som kräver en inloggad
-- medlem. Utan den här policyn ser adminvyn noll rader — tyst, och koden
-- faller tillbaka på gissningen, så felet syns bara som "härlett" i fotnoten.
--
-- Samma villkor och samma säkerhetsresonemang som 029: läsning bara när INGEN
-- tenant-kontext är satt. Varje kundvänd kodväg sätter kontexten via
-- _scoped(); den oskopade vägen finns i app/api/admin.py bakom
-- require_master_key. Endast SELECT — ingen skrivning över tenants.

drop policy if exists workspaces_admin_read on public.workspaces;
create policy workspaces_admin_read on public.workspaces
  for select to snajp_app
  using (nullif(current_setting('app.tenant_id', true), '') is null);

-- Verifiering efter körning — som snajp_app, utan tenant-kontext:
--   select count(*) from workspaces where ss_tenant_id is not null;
--   -- ska ge samma antal som postgres ser
