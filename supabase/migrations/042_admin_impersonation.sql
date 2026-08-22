-- Plattformsadmin ska kunna öppna VILKEN kunds arbetsyta som helst i läsläge.
--
-- BAKGRUNDEN. `lib/vy.ts` har hittills kunnat växla till exakt en tenant:
-- demokontot `nordlys-handel`, hårdkodat. Det räcker för en visning men inte
-- för support — den vanligaste frågan är "hur ser det ut hos DEN här kunden",
-- och svaret har krävt en databasfråga för hand.
--
-- VARFÖR GRINDEN LIGGER I DATABASEN OCH INTE BARA I APPEN.
-- `tenant_api_key_for_current_workspace()` (migration 040) tar med flit ingen
-- parameter: med en workspace_id som argument hade den varit en uppslagsbok
-- över alla arbetsytors API-nycklar, och en enda slarvig anropsplats hade
-- räckt för att läsa fel kunds. Funktionen nedan TAR en parameter, och det är
-- precis därför villkoret måste sitta i funktionskroppen: den kontrollerar
-- själv att anroparen står i `platform_admins`. Appens `getPlatformAdmin()`
-- är då det andra av två lås, inte det enda.
--
-- Läsningen sker med `app.user_id`, samma inställning som resten av Next-appens
-- vägar sätter via `sqlAsUser` (migration 035). `nullif(..., '')` är inte
-- kosmetik — en tom sträng castad till uuid kastar, och migration 028 fick
-- städa upp efter exakt det.

create or replace function public.tenant_api_key_for_admin(p_slug text)
returns text
language plpgsql
security definer
set search_path = public
as $$
declare
  anropare uuid;
  nyckel text;
begin
  anropare := nullif(current_setting('app.user_id', true), '')::uuid;

  if anropare is null then
    return null;
  end if;

  -- Grinden. Fail-closed: ingen rad i platform_admins betyder ingen nyckel,
  -- och funktionen säger inte om sluggen fanns. Den som inte är admin ska inte
  -- kunna räkna upp kunder genom att jämföra svar.
  if not exists (select 1 from public.platform_admins where user_id = anropare) then
    return null;
  end if;

  select k.api_key into nyckel
    from public.workspace_tenant_keys k
   where k.tenant_slug = p_slug;

  return nyckel;
end;
$$;


-- Vilka kunder adminytan får erbjuda att gå in i.
--
-- Egen funktion i stället för en vy: samma platform_admins-villkor ska gälla
-- uppräkningen som nyckeluppslaget. En admin som kan hämta nyckeln men inte se
-- listan hade fått den ur adminvyns tenant-lista ändå — två grindar med olika
-- villkor är i praktiken den svagaste av dem.
create or replace function public.tenants_for_admin()
returns table (slug text, name text, workspace_id uuid, has_key boolean)
language plpgsql
security definer
set search_path = public
as $$
declare
  anropare uuid;
begin
  anropare := nullif(current_setting('app.user_id', true), '')::uuid;

  if anropare is null
     or not exists (select 1 from public.platform_admins where user_id = anropare) then
    return;
  end if;

  return query
    select w.slug,
           w.name,
           w.id,
           -- Kunder med configfil har sin nyckel i en miljövariabel och alltså
           -- ingen rad här. `has_key` säger bara vilken VÄG som gäller, inte om
           -- kunden går att öppna.
           exists (select 1 from public.workspace_tenant_keys k where k.tenant_slug = w.slug)
      from public.workspaces w
     where w.slug is not null
     order by w.name;
end;
$$;


revoke execute on function public.tenant_api_key_for_admin(text) from public, anon;
revoke execute on function public.tenants_for_admin() from public, anon;
grant execute on function public.tenant_api_key_for_admin(text) to authenticated, snajp_web;
grant execute on function public.tenants_for_admin() to authenticated, snajp_web;

comment on function public.tenant_api_key_for_admin(text) is
  'Nyckeln för en NAMNGIVEN kund, men bara för den som står i platform_admins. '
  'Villkoret sitter i funktionskroppen eftersom funktionen tar en parameter och '
  'därmed vore en uppslagsbok över alla kunders nycklar utan det.';
comment on function public.tenants_for_admin() is
  'Kunderna adminytan får öppna i läsläge. Samma platform_admins-villkor som '
  'tenant_api_key_for_admin — två grindar med olika villkor är den svagaste av dem.';


-- Loggen. Varje inträde i en kunds arbetsyta ska gå att se i efterhand.
--
-- `platform_events` skrivs bara av `snajp_app` (migration 026), och Next-appen
-- kör som `snajp_web`. Att bredda den policyn hade gett webbappen skrivrätt på
-- hela notiscentret för att kunna skriva EN sorts rad. Funktionen nedan skriver
-- den raden och ingenting annat, och kontrollerar själv att anroparen är admin.
--
-- Nivån är `info` och inte `warning`: ett kundbesök är en normal supportåtgärd.
-- Det som ska gå att svara på är "vem, vilken kund, när" — inte "gick något
-- sönder".
create or replace function public.log_admin_impersonation(p_slug text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  anropare uuid;
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
end;
$$;

revoke execute on function public.log_admin_impersonation(text) from public, anon;
grant execute on function public.log_admin_impersonation(text) to authenticated, snajp_web;

comment on function public.log_admin_impersonation(text) is
  'Skriver EN rad i platform_events när en plattformsadmin öppnar en kunds '
  'arbetsyta. Finns som security definer för att slippa ge snajp_web skrivrätt '
  'på hela notiscentret.';
