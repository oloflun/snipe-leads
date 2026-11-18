-- 117: kunskapsbasens artiklar får en källa och en giltighetstid.
--
-- source_url: var artikeln kommer ifrån. Webbskanningen (app/kb_skanning.py)
--   tog redan fram en källadress per artikelutkast, men den tappades när
--   artikeln sparades via POST /api/kb.
-- giltig_till: sista dagen artikeln gäller (svensk dag). Efter den lämnar
--   search_kb inte längre ut artikeln till agenten; portalens lista visar den
--   fortfarande så att kunden kan byta ut den. Null = gäller tills vidare.
--
-- Additiv och idempotent. Ingen backfill: befintliga artiklar saknar källa och
-- gäller tills vidare, precis som förut. Inga nya index: filtret körs alltid
-- tillsammans med tenant_id och en vektor- eller fulltextsökning över en
-- tenants egen, liten bas. Grants på tabellnivå (009, 069) täcker kolumnerna.
--
-- Måste vara körd innan koden som läser kolumnerna går live
-- (app/storage/postgres.py: search_kb, list_kb, add_kb_article).

alter table public.ss_knowledge_base add column if not exists source_url text;
alter table public.ss_knowledge_base add column if not exists giltig_till date;
