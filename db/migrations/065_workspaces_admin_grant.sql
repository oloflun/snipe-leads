-- 064 lade POLICYN workspaces_admin_read för snajp_app — men aldrig GRANTEN.
--
-- RLS-policyer filtrerar rader; de ger ingen tabellrättighet. Utan
-- `grant select` kastar frågan InsufficientPrivilegeError innan policyn ens
-- konsulteras. Uppmätt 2026-09-15 i BÅDA miljöerna: main-api:t loggade
-- tracebacken var 30:e sekund från list_tenants_with_stats, koden föll
-- (avsiktligt) tillbaka på härledda paket — dvs. exakt testarfyndet som 064
-- skulle laga stod kvar, tyst. 064:s eget verifieringskommando ("som
-- snajp_app") hade fångat det; det kördes uppenbarligen aldrig så.
--
-- Endast SELECT. Radmängden begränsas fortfarande av 064-policyn: bara när
-- ingen tenant-kontext är satt (adminens oskopade väg bakom master-nyckeln).

grant select on public.workspaces to snajp_app;

-- Verifiering efter körning — SOM snajp_app, utan tenant-kontext:
--   set role snajp_app;
--   select count(*) from public.workspaces where ss_tenant_id is not null;
--   -- ska ge > 0 utan fel, och matcha antalet postgres ser
