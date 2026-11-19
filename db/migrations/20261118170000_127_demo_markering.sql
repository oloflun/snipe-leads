-- 127: demon markeras igen (rättar startDemo, 2026-11-18).
--
-- FELET: `startDemo` (lib/actions/auth.ts) körde
--
--     update public.workspaces set is_demo = true
--       from public.profiles p where workspaces.id = p.workspace_id and p.id = $1
--
-- med `sql()`, alltså som snajp_web UTAN identitet. `workspaces` har ingen
-- update-policy (med flit, se 038), och utan identitet ser select-policyn
-- ingenting heller: uppdateringen träffade noll rader utan att kasta. Varje
-- demo fick fullt löptak och ingen uppgraderingsväg. 126 behöll update-rätten
-- på `is_demo` just för att satsen inte skulle bli ett fel; felet var redan där.
--
-- RÄTTELSEN följer 038 och 006: en smal dörr i stället för en update-policy.
-- En update-policy på workspaces hade öppnat hela raden, också `slug`, som
-- avgör vilken kunds data arbetsytan ser. Funktionen kan bara göra EN sak:
--   * markera den INLOGGADES egen arbetsyta (identiteten ur `app.user_id`,
--     som `sqlAsUser` sätter), aldrig någon annans;
--   * bara för ett konto som startDemo skapar: adressen
--     `demo-<uuid>@snajp.se`, skapat de senaste tio minuterna;
--   * bara en arbetsyta utan slug och utan andra medlemmar, alltså den tomma
--     yta triggern on_auth_user_created just skapade.
-- En vanlig kund kan alltså inte märka (eller av-märka) sin arbetsyta, och
-- funktionen kan aldrig sätta is_demo till false.
--
-- Webbens kolumnrätt `update (is_demo)` från 126 tas bort: den behövs inte
-- längre, och en rättighet ingen fråga använder är bara yta.
-- `snajp-support/tests/db/test_snajp_web_rattigheter.py` (TILLATET) följer med.
--
-- Additiv och idempotent: create or replace, revoke och grant kan köras om.

create or replace function public.markera_demoarbetsyta()
returns boolean
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_uid uuid := nullif(current_setting('app.user_id', true), '')::uuid;
  v_ws  uuid;
begin
  if v_uid is null then
    return false;
  end if;

  if not exists (
    select 1
      from auth.users u
     where u.id = v_uid
       and lower(u.email) ~ '^demo-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}@snajp\.se$'
       and u.created_at > now() - interval '10 minutes'
  ) then
    return false;
  end if;

  select p.workspace_id into v_ws from public.profiles p where p.id = v_uid;
  if v_ws is null then
    return false;
  end if;

  update public.workspaces w
     set is_demo = true
   where w.id = v_ws
     and w.slug is null
     and not exists (
       select 1 from public.profiles p2 where p2.workspace_id = w.id and p2.id <> v_uid
     );

  return found;
end;
$$;

comment on function public.markera_demoarbetsyta() is
  'Märker den inloggades nyss skapade demoarbetsyta is_demo (127). Bara konton '
  'demo-<uuid>@snajp.se yngre än tio minuter, bara en arbetsyta utan slug och '
  'utan andra medlemmar. Ersätter webbens update-rätt på workspaces.is_demo.';

revoke all on function public.markera_demoarbetsyta() from public;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on function public.markera_demoarbetsyta() from anon;
  end if;
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    grant execute on function public.markera_demoarbetsyta() to snajp_web;
    -- Kolumnrätten från 126 behövs inte längre.
    revoke update (is_demo) on public.workspaces from snajp_web;
  end if;
end;
$$;
