-- G11: segmentlärandet — den ENDA avsiktliga vägen över en tenantgräns.
-- "Det är per definition ett hål i isoleringen och byggs därför så här":
--
-- - Bara ab_results AGGREGERAT per (segment, lever) korsar gränsen. Aldrig
--   prospekt, kundnamn, mejltext eller erbjudandetexter.
-- - Minst TRE tenants i ett segment innan en grupp är läsbar — verkställt
--   av HAVING i själva SQL-funktionen, inte ett app-lager-filter som går
--   att kringgå.
-- - security definer + BYPASSRLS-rollen som kör migrationer (samma roll
--   003_snajp_multitenant.sql varnade för — här används den gapet
--   AVSIKTLIGT och SMALT, till skillnad från appens egen DATABASE_URL
--   som G1/009 stängde). Ingen kodväg får tenant_id från något annat än
--   körkontexten (G2) — den här funktionen har inget tenant_id-argument
--   och ingen tenant_id-kolumn i resultatet att filtrera på.
-- - search_path pinnad explicit — undviker samma
--   function_search_path_mutable-varning andra funktioner i databasen
--   redan har (sett via get_advisors innan denna migration skrevs).

alter table ss_tenants add column if not exists segment text;

create or replace function segment_ab_aggregate()
returns table (
  segment text,
  lever text,
  tenant_count bigint,
  sent bigint,
  replies bigint,
  positive bigint
)
language sql
security definer
set search_path = public
stable
as $$
  select
    t.segment,
    v.lever,
    count(distinct t.id) as tenant_count,
    coalesce(sum(r.sent), 0) as sent,
    coalesce(sum(r.replies), 0) as replies,
    coalesce(sum(r.positive), 0) as positive
  from ab_results r
  join ab_variants v on v.id = r.variant_id
  join offers o on o.id = v.offer_id
  join ss_tenants t on t.id = o.tenant_id
  where t.segment is not null
  group by t.segment, v.lever
  having count(distinct t.id) >= 3;
$$;

-- Bara snajp_app (tjänstens egen roll, inte anon/authenticated) får anropa den.
-- Supabase ger annars anon/authenticated execute på nya publika funktioner
-- som standard (bekräftat via get_advisors — samma lucka som redan fanns
-- på andra funktioner i databasen; stäng den här explicit i stället för
-- att anta att "revoke from public" räcker).
revoke all on function segment_ab_aggregate() from public;
revoke execute on function segment_ab_aggregate() from anon, authenticated;
grant execute on function segment_ab_aggregate() to snajp_app;
