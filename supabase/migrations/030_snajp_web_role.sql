-- Next-appens egen Postgres-roll, för när inloggningen inte längre går via
-- Supabase.
--
-- FORMEN ÄR MEDVETET SAMMA SOM SUPABASES `authenticated`: breda grants, RLS som
-- grind. Det är inte slarv — det är vad vi ersätter. Supabase ger
-- `authenticated` select/insert/update/delete på hela `public` och låter
-- policyerna avgöra vad som syns. Byter vi till smala per-tabell-grants byter
-- vi samtidigt ut den bärande mekanismen, och då är det inte längre samma
-- system som testerna och de 63 policyerna beskriver.
--
-- Det som DÄREMOT inte får ärvas är `postgres`-rollen. Tabellägaren kringgår
-- RLS utan att något syns i en diff, och resultatet blir trovärdiga men
-- felaktiga siffror — exakt felet migration 029 fick städa upp. Därför
-- `nobypassrls`, uttryckligen.
--
-- Identiteten sätts per transaktion med `set_config('app.user_id', …)`, som
-- auth.uid() läser (railway/000_auth_compat.sql). Samma mönster som backenden
-- redan använder för `app.tenant_id`: ett mönster i kodbasen i stället för två.

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'snajp_web') then
    create role snajp_web with login nobypassrls;
  else
    alter role snajp_web with login nobypassrls;
  end if;
end $$;

grant usage on schema public to snajp_web;
grant select, insert, update, delete on all tables in schema public to snajp_web;
grant usage, select on all sequences in schema public to snajp_web;
alter default privileges in schema public
  grant select, insert, update, delete on tables to snajp_web;
alter default privileges in schema public
  grant usage, select on sequences to snajp_web;

-- auth.users ägs av kompatibilitetslagret, inte av GoTrue. Next skriver
-- registreringar dit, och triggern on_auth_user_created (001/006) skapar
-- workspace + profil precis som förut.
grant usage on schema auth to snajp_web;
grant select, insert, update on auth.users to snajp_web;

-- ensure_workspace_for_current_user() är security definer och anropas efter
-- inloggning för att läka konton utan profil. 018 revokade PUBLIC-graden och
-- gav den till `authenticated`; snajp_web behöver samma grad av samma skäl.
grant execute on function public.ensure_workspace_for_current_user() to snajp_web;
grant execute on function public.current_workspace_id() to snajp_web;
