-- En avregistrering får ALDRIG falla på att kunden saknar arbetsyta.
--
-- ## Vad som hände
--
-- `suppressions.workspace_id` är `not null` sedan 000, från den tid då
-- spärrlistan bara var en dashboard-funktion. Backenden kom senare och skopar
-- på `tenant_id` (migration 030) — men NOT NULL-villkoret blev kvar.
--
-- Följden upptäcktes när avregistreringskedjan provkördes skarpt mot
-- development 2026-08-24: `avregistrera_via_token` reste ett undantag för
-- `nordlys-handel`, som inte har någon arbetsyta. Mottagaren hade fått
-- "Något gick fel på vår sida" och stått kvar i utskickslistan.
--
-- Samma lucka, tystare, i `PostgresStorage.add_suppression`: den skriver med
-- `insert ... select ... from workspaces where ss_tenant_id = $1`, och en
-- select utan träffar infogar noll rader. Ingen krasch, inget felmeddelande,
-- ingen avregistrering. Den är rättad i samma ändring.
--
-- ## Varför kolumnen blir nullbar i stället för att vi hittar på en arbetsyta
--
-- Att peka avregistreringen på NÅGON arbetsyta hade varit att lägga en persons
-- avregistrering hos fel bolag — samma fel som backfillen i 030 uttryckligen
-- vägrade göra. Och att vägra spara är värst av allt: det är den enda
-- kodvägen vars misslyckande betyder att en människa inte kan sluta få våra
-- mejl.
--
-- Vad kostar en NULL? Dashboardens vy skopar på `workspace_id` och visar
-- därför inte raden. Det är en LUCKA I VISNINGEN, inte i skyddet:
-- `send_guard` regel 3 läser via `list_suppressions(tenant_id)` och ser raden
-- oavsett. Och de tenants det gäller — demo-tenanterna — har ingen dashboard
-- att visa den i.
--
-- Idempotent enligt husets regel: kan köras om utan verkan.

alter table public.suppressions
  alter column workspace_id drop not null;

comment on column public.suppressions.workspace_id is
  'Nullbar sedan 049. En avregistrering ska kunna sparas även för en tenant '
  'utan arbetsyta — skyddet läses via tenant_id (se send_guard regel 3), inte '
  'via workspace_id. En NULL döljer raden i dashboarden men inte för spärren.';

-- ---------------------------------------------------------------------------
-- Inlösen: spara alltid, res aldrig ett undantag.
-- ---------------------------------------------------------------------------

create or replace function public.avregistrera_via_token(p_token text)
returns text
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  l record;
  v_workspace uuid;
  v_fanns boolean;
begin
  select * into l
    from public.ss_avregistreringslankar
   where token = p_token;

  if not found then
    return 'okand_token';
  end if;

  select exists (
    select 1 from public.suppressions s
     where s.tenant_id = l.tenant_id
       and lower(s.email) = lower(l.email)
  ) into v_fanns;

  -- Arbetsytan om den finns, annars NULL. INGEN `raise` här: se filhuvudet.
  select w.id into v_workspace
    from public.workspaces w
   where w.ss_tenant_id = l.tenant_id
   limit 1;

  if not v_fanns then
    insert into public.suppressions (workspace_id, tenant_id, email, reason)
    values (v_workspace, l.tenant_id, lower(l.email),
            'avregistrering via länk i utskick');
  end if;

  -- Stämplas även när adressen redan fanns: det säger att LÄNKEN användes,
  -- vilket är den fråga man ställer när någon hävdar att den inte fungerade.
  update public.ss_avregistreringslankar
     set anvand_at = coalesce(anvand_at, now())
   where token = p_token;

  return case when v_fanns then 'redan_avregistrerad' else 'avregistrerad' end;
end;
$$;

revoke all on function public.avregistrera_via_token(text) from public;
grant execute on function public.avregistrera_via_token(text) to snajp_web;
grant execute on function public.avregistrera_via_token(text) to snajp_app;
