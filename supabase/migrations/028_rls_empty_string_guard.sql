-- INV-SEC-001-grinden: RLS-policyerna tål inte tom sträng, och det är exakt
-- vad `app.tenant_id` blir efter första användningen på en poolad anslutning.
--
-- KÖR DEN HÄR INNAN DATABASE_URL BYTS TILL snajp_app. Utan den går
-- schemaläggaren och adminvyn sönder i samma sekund som cutovern sker.
--
-- Mekanismen, uppmätt mot produktionen 2026-08-15:
--
--   `set_config('app.tenant_id', <id>, true)` är transaktionslokal. Efter
--   COMMIT återgår GUC:en till sitt FÖREGÅENDE värde — men en custom-GUC som
--   aldrig satts på sessionsnivå har `''` som utgångsvärde, inte NULL. Varken
--   `RESET app.tenant_id` eller `set_config(..., NULL, false)` gör den NULL
--   igen; båda testade, båda ger `''`.
--
--   Följden: varje senare OSKOPAD fråga på samma anslutning möter policyer som
--   gör `''::uuid` och kastar
--   `invalid input syntax for type uuid: ""`.
--
-- Vad som faktiskt går sönder:
--
--   * `ss_tenants.tenant_lookup` är `current_setting(...) IS NULL`. Med `''`
--     gäller den inte längre, och `tenant_self` kastar på castet. `list_tenants()`
--     är det schemaläggaren använder för att räkna upp kunder — den slutar
--     alltså fungera, tyst för den ena policyn och högljutt för den andra.
--   * `list_agent_runs_all`, `get_agent_run` och `list_platform_events`
--     (admin, oskopade per design) kastar på samma sätt.
--
-- Varför ingen märkt det: backenden kör som `postgres` med BYPASSRLS, så
-- policyerna evalueras aldrig. Buggen har legat latent sedan multi-tenancy
-- infördes och blir verklig först vid cutovern.
--
-- Fixen är `NULLIF(..., '')` i varje policy, vilket återställer den avsedda
-- betydelsen: tom sträng ÄR "ingen tenant satt".
--
-- ponytail: en DO-loop i stället för 33 handskrivna policyer. Att skriva av
-- dem för hand är 33 tillfällen att stava fel på ett villkor som avgör om en
-- kund ser en annan kunds data.

do $$
declare
  p record;
  ny_qual text;
  ny_check text;
  roller text;
  sats text;
begin
  for p in
    select n.nspname as schemat,
           c.relname as tabellen,
           pol.polname as policyn,
           pol.polcmd as kommandot,
           pg_get_expr(pol.polqual, pol.polrelid) as qual,
           pg_get_expr(pol.polwithcheck, pol.polrelid) as med_check,
           array_to_string(array(
             select rolname from pg_roles where oid = any(pol.polroles)
           ), ', ') as rollerna
    from pg_policy pol
    join pg_class c on c.oid = pol.polrelid
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public'
      and (pg_get_expr(pol.polqual, pol.polrelid) like '%app.tenant_id%'
        or pg_get_expr(pol.polwithcheck, pol.polrelid) like '%app.tenant_id%')
  loop
    ny_qual := replace(p.qual,
      'current_setting(''app.tenant_id''::text, true)',
      'NULLIF(current_setting(''app.tenant_id''::text, true), '''')');
    ny_check := replace(coalesce(p.med_check, ''),
      'current_setting(''app.tenant_id''::text, true)',
      'NULLIF(current_setting(''app.tenant_id''::text, true), '''')');

    -- Tom rollista i pg_policy betyder PUBLIC.
    roller := coalesce(nullif(p.rollerna, ''), 'public');

    sats := format('drop policy %I on %I.%I', p.policyn, p.schemat, p.tabellen);
    execute sats;

    sats := format('create policy %I on %I.%I for %s to %s',
      p.policyn, p.schemat, p.tabellen,
      case p.kommandot
        when 'r' then 'select' when 'a' then 'insert'
        when 'w' then 'update' when 'd' then 'delete'
        else 'all' end,
      roller);

    if ny_qual is not null and ny_qual <> '' then
      sats := sats || format(' using (%s)', ny_qual);
    end if;
    if ny_check is not null and ny_check <> '' then
      sats := sats || format(' with check (%s)', ny_check);
    end if;

    execute sats;
    raise notice 'omskriven: %.% / %', p.schemat, p.tabellen, p.policyn;
  end loop;
end $$;

-- Verifiering efter körning — ska ge 0:
--   select count(*) from pg_policies
--   where schemaname = 'public'
--     and qual like '%app.tenant_id%'
--     and qual not like '%NULLIF%';
