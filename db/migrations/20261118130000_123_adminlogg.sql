-- 123: åtkomstloggen för plattformsadmin och master-nyckeln skrivs i audit_logs.
--
-- ## Varför
--
-- audit_logs har funnits sedan basschemat (000) men ingen kod skrev till den.
-- Plattformsadmin läser och ändrar kunders data på två vägar, och ingen av dem
-- lämnade ett spår som gick att granska efteråt (ISO 27001 A.8.15, A.5.15–
-- A.5.18; GDPR art. 32):
--
--   * master-nyckeln mot backendens /api/admin/* och /api/keys. Next-appens
--     adminyta använder den, liksom provisioneringen av nya kunder;
--   * kundbesöket, där admin öppnar en namngiven kunds arbetsyta (042). Det
--     loggades bara i platform_events, som gallras med kundens egna data
--     (119) och som snajp_app kan skriva fritt i.
--
-- ## Vad en rad bär
--
-- Vem (actor_user_id när en plattformsadmin kan styrkas, annars aktor =
-- 'master-nyckel'), när (created_at), åtgärd (action: 'las', 'andra' eller
-- 'oppna'), kund (tenant_id) och resurs (ruttens MALL, t.ex.
-- /api/admin/tenants/{tenant_id}/kunddata, och ett id ur sökvägen). ALDRIG
-- innehåll, frågesträngar, kroppar, svar eller nycklar.
--
-- ## Vem som får skriva
--
-- Ingen approll skriver i tabellen direkt. Raderna skrivs av de två
-- säkerhetsdefinierade funktionerna nedan, och snajp_app/snajp_web får
-- varken ändra eller radera en rad: en logg den loggade kan skriva om är
-- ingen logg. Funktionen kontrollerar själv att en uppgiven admin finns i
-- platform_admins; ett okänt id ger en rad utan admin, aldrig en falsk.
--
-- ## Gallring
--
-- Raderna sparas i 365 dagar och gallras av logga_adminatkomst själv, vid
-- varje skrivning (indexerad radering, sällan mer än en handfull rader).
-- Gallringen gäller bara åtkomstloggens rader (kanal satt) och beror inte på
-- GALLRING_AKTIV eller kundens policy: en säkerhetslogg ska ha en egen,
-- bestämd lagringstid, inte följa kunddatans. 365 dagar är en teknisk
-- utgångspunkt; ägaren kan ändra den (docs/BESLUT.md 2026-11-18).
--
-- Additiv och idempotent: kan köras om utan verkan.

-- ---------------------------------------------------------------------------
-- Kolumnerna.
-- ---------------------------------------------------------------------------

-- Åtkomstloggens rader hör till en kund (ss_tenants), inte till en arbetsyta.
alter table public.audit_logs alter column workspace_id drop not null;

alter table public.audit_logs
  add column if not exists tenant_id  uuid references public.ss_tenants(id) on delete set null,
  add column if not exists kanal      text,
  add column if not exists aktor      text,
  add column if not exists metod      text,
  add column if not exists resurs     text,
  add column if not exists request_id text;

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'audit_logs_kanal_check') then
    alter table public.audit_logs
      add constraint audit_logs_kanal_check
      check (kanal is null or kanal in ('master', 'kundbesok'));
  end if;
end;
$$;

create index if not exists audit_logs_kanal_created_idx
  on public.audit_logs (created_at) where kanal is not null;
create index if not exists audit_logs_tenant_created_idx
  on public.audit_logs (tenant_id, created_at desc) where tenant_id is not null;

comment on column public.audit_logs.kanal is
  'Åtkomstloggen (123): master = anrop med master-nyckeln, kundbesok = '
  'plattformsadmin öppnade en kunds arbetsyta. Null för äldre radtyper.';
comment on column public.audit_logs.resurs is
  'Ruttens mall, aldrig den ifyllda sökvägen med frågesträng (123).';

-- ---------------------------------------------------------------------------
-- Ingen approll ändrar loggen.
-- ---------------------------------------------------------------------------

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    revoke insert, update, delete on table public.audit_logs from snajp_app;
  end if;
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    revoke insert, update, delete on table public.audit_logs from snajp_web;
  end if;
end;
$$;

-- ---------------------------------------------------------------------------
-- Skrivningen: en rad per anrop, och gallringen av det som passerat 365 dagar.
-- ---------------------------------------------------------------------------

create or replace function public.logga_adminatkomst(
  p_kanal      text,
  p_admin      uuid,
  p_tenant     uuid,
  p_metod      text,
  p_resurs     text,
  p_entity     uuid default null,
  p_request_id text default null
)
returns boolean
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_admin  uuid;
  v_tenant uuid;
  v_metod  text := upper(left(coalesce(p_metod, ''), 10));
begin
  if p_kanal not in ('master', 'kundbesok') then
    raise exception 'okänd kanal %', p_kanal;
  end if;

  -- Bara en admin som finns räknas; ett påhittat id ger en rad utan admin.
  select pa.user_id into v_admin
    from public.platform_admins pa where pa.user_id = p_admin;
  -- En kund som inte finns (fel id i sökvägen) ger en rad utan kund, inte ett
  -- fel: anropet ska loggas även när det svarar 404.
  select t.id into v_tenant from public.ss_tenants t where t.id = p_tenant;

  insert into public.audit_logs
    (workspace_id, actor_user_id, action, entity_type, entity_id, metadata,
     tenant_id, kanal, aktor, metod, resurs, request_id)
  values
    (null, v_admin,
     case when p_kanal = 'kundbesok' then 'oppna'
          when v_metod in ('GET', 'HEAD', 'OPTIONS') then 'las'
          else 'andra' end,
     case when p_kanal = 'kundbesok' then 'arbetsyta' else 'admin_api' end,
     p_entity, '{}'::jsonb,
     v_tenant, p_kanal,
     case when v_admin is not null then 'plattformsadmin'
          when p_kanal = 'master' then 'master-nyckel'
          else 'okand' end,
     nullif(v_metod, ''), left(p_resurs, 300), left(p_request_id, 64));

  -- Gallringen: 365 dagar, bara åtkomstloggens rader.
  delete from public.audit_logs
   where kanal is not null
     and created_at < now() - interval '365 days';

  return v_admin is not null;
end;
$$;

revoke all on function public.logga_adminatkomst(text, uuid, uuid, text, text, uuid, text) from public;
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    grant execute on function public.logga_adminatkomst(text, uuid, uuid, text, text, uuid, text) to snajp_app;
  end if;
end;
$$;

comment on function public.logga_adminatkomst(text, uuid, uuid, text, text, uuid, text) is
  'Åtkomstloggen (123): en rad i audit_logs per master-nyckelanrop eller '
  'kundbesök, och gallring av rader äldre än 365 dagar. Anropas av '
  'snajp-support/app/api/adminlogg.py (via deps.require_master_key) och av '
  'log_admin_impersonation.';

-- ---------------------------------------------------------------------------
-- Kundbesöket (042) skriver nu också i åtkomstloggen.
-- ---------------------------------------------------------------------------
--
-- Samma kontroll som förut: bara en plattformsadmin ger en rad. Raden i
-- platform_events står kvar (notiscentret läser den); åtkomstloggens rad är
-- den som inte gallras med kundens data och inte kan skrivas om av appen.

create or replace function public.log_admin_impersonation(p_slug text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  anropare uuid;
  v_tenant uuid;
begin
  anropare := nullif(current_setting('app.user_id', true), '')::uuid;

  if anropare is null
     or not exists (select 1 from public.platform_admins where user_id = anropare) then
    return;
  end if;

  insert into public.platform_events (tenant_id, level, source, message, detail)
  select w.ss_tenant_id,
         'info',
         'admin.impersonation',
         format('Plattformsadmin öppnade arbetsytan för %s.', coalesce(w.name, p_slug)),
         jsonb_build_object('slug', p_slug, 'admin_user_id', anropare)
    from public.workspaces w
   where w.slug = p_slug;

  select w.ss_tenant_id into v_tenant
    from public.workspaces w where w.slug = p_slug limit 1;
  if v_tenant is null then
    select t.id into v_tenant from public.ss_tenants t where t.slug = p_slug;
  end if;

  perform public.logga_adminatkomst('kundbesok', anropare, v_tenant, null,
                                    left('arbetsyta:' || coalesce(p_slug, ''), 300));
end;
$$;

revoke execute on function public.log_admin_impersonation(text) from public, anon;
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    grant execute on function public.log_admin_impersonation(text) to snajp_web;
  end if;
  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    grant execute on function public.log_admin_impersonation(text) to authenticated;
  end if;
end;
$$;
