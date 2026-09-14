-- Varje arbetsyta ska kunna få en EGEN backend-tenant utan en deploy.
--
-- ## Vad som var trasigt
--
-- Migration 040 gav testarbetsytor en egen tenant i drift. RIKTIGA kunder fick
-- ingen: `lib/actions/onboarding.ts` kopplade bara `input.testkund`-fallet, och
-- en vanlig registrering lämnade `workspaces.slug` som null. Följden var mätbar
-- i drift — `requireSnajpTenant()` svarade 409 "Arbetsytan är inte kopplad till
-- någon kund ännu" på VARJE inloggad yta: översikten fick streck i stället för
-- siffror, `/settings/soul` visade "Kunde inte hämta röstdokumentet" och
-- `/settings/leads` renderade ett meddelande om databaskolumner. En kund som
-- registrerar sig i dag kan alltså inte använda produkten förrän någon av oss
-- kör `scripts/onboard_tenant.py` för hand.
--
-- Samma lucka på adminsidan: "Byt kund" listar backendens ALLA tenants, och de
-- som saknar både nyckelrad och miljövariabel (`nordlys-handel`, `public-demo`)
-- gav 409 så fort man klickade på dem.
--
-- ## Två funktioner, två olika villkor — och varför de inte är en
--
-- `link_workspace_tenant` kopplar den INLOGGADES egen arbetsyta. Den är
-- syskonet till `link_test_tenant` (migration 040) och skiljer sig på exakt två
-- punkter: sluggmönstret är `kund-` i stället för `testkund-`, och `is_demo`
-- rörs inte — en riktig kund är inte en demo och ska inte köra med sänkt tak.
--
-- `save_admin_tenant_key` skriver nyckeln för en NAMNGIVEN kund och kräver
-- därför `platform_admins`, precis som `tenant_api_key_for_admin` (migration
-- 042). Villkoret sitter i funktionskroppen och inte hos anroparen, av samma
-- skäl som där: funktionen tar en parameter och vore utan villkoret en
-- skrivväg mot vilken kunds nyckel som helst.
--
-- Sluggmönstret är hela skyddet i den första: utan det kunde en manipulerad
-- frontend peka sin egen arbetsyta på en RIKTIG kunds tenant och läsa deras
-- inkorg. `kund-<8 tecken ur workspace-id>` går inte att gissa sig till någon
-- annans slug med, eftersom `where slug is null` dessutom hindrar att en redan
-- kopplad arbetsyta flyttas.


-- Kopplar den INLOGGADES arbetsyta till en egen, RIKTIG tenant.
--
-- Speglar `testtenantSlug()`/`kundtenantSlug()` i lib/snajp/testtenant.ts.
-- Ändras mönstret på ena stället måste det ändras på det andra — annars
-- avvisas varje koppling tyst och arbetsytan står kvar utan slug.
create or replace function public.link_workspace_tenant(
  p_slug text,
  p_tenant_id uuid,
  p_api_key text
)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
  ws_id uuid;
begin
  if p_slug is null or p_slug !~ '^kund-[a-z0-9]{4,32}$' then
    -- Fail-closed och tyst, som link_test_tenant: den som råkar anropa fel ska
    -- inte få veta vilket mönster som hade fungerat.
    return false;
  end if;

  select p.workspace_id into ws_id
    from public.profiles p
   where p.id = nullif(current_setting('app.user_id', true), '')::uuid;

  if ws_id is null then
    return false;
  end if;

  update public.workspaces
     set slug = p_slug,
         ss_tenant_id = p_tenant_id
   where id = ws_id
     and slug is null;

  if not found then
    return false;
  end if;

  insert into public.workspace_tenant_keys (workspace_id, tenant_slug, ss_tenant_id, api_key)
  values (ws_id, p_slug, p_tenant_id, p_api_key)
  on conflict (workspace_id) do update
    set tenant_slug = excluded.tenant_slug,
        ss_tenant_id = excluded.ss_tenant_id,
        api_key = excluded.api_key;

  return true;
end;
$$;


-- Sparar nyckeln för en namngiven kund. Bara plattformsadmin, och bara för en
-- arbetsyta som REDAN bär sluggen.
--
-- Varför den behövs: kunder som lades upp före migration 040 har varken en
-- nyckelrad eller en miljövariabel i den här miljön. Backenden lämnar aldrig
-- tillbaka en utfärdad nyckel (bara sha256-hashen sparas), så den enda vägen
-- är att utfärda en ny och lägga den här. Utan det måste en människa köra
-- `scripts/railway_tenantnyckel.py` per kund och miljö.
--
-- `ss_tenant_id` kontrolleras i stället för att skrivas över när den redan är
-- satt. En nyckel som pekar på en ANNAN tenant än arbetsytan hade tyst öppnat
-- fel kunds inkorg — det ska vara ett fel, inte en tyst korrigering.
create or replace function public.save_admin_tenant_key(
  p_slug text,
  p_tenant_id uuid,
  p_api_key text
)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
  anropare uuid;
  ws_id uuid;
  befintlig uuid;
begin
  anropare := nullif(current_setting('app.user_id', true), '')::uuid;

  if anropare is null
     or not exists (select 1 from public.platform_admins where user_id = anropare) then
    return false;
  end if;

  select w.id, w.ss_tenant_id into ws_id, befintlig
    from public.workspaces w
   where w.slug = p_slug
   limit 1;

  if ws_id is null then
    return false;
  end if;

  if befintlig is not null and befintlig <> p_tenant_id then
    return false;
  end if;

  if befintlig is null then
    update public.workspaces set ss_tenant_id = p_tenant_id where id = ws_id;
  end if;

  insert into public.workspace_tenant_keys (workspace_id, tenant_slug, ss_tenant_id, api_key)
  values (ws_id, p_slug, p_tenant_id, p_api_key)
  on conflict (workspace_id) do update
    set tenant_slug = excluded.tenant_slug,
        ss_tenant_id = excluded.ss_tenant_id,
        api_key = excluded.api_key;

  return true;
end;
$$;


revoke execute on function public.link_workspace_tenant(text, uuid, text) from public, anon;
revoke execute on function public.save_admin_tenant_key(text, uuid, text) from public, anon;
grant execute on function public.link_workspace_tenant(text, uuid, text) to authenticated, snajp_web;
grant execute on function public.save_admin_tenant_key(text, uuid, text) to authenticated, snajp_web;

comment on function public.link_workspace_tenant(text, uuid, text) is
  'Kopplar den INLOGGADES arbetsyta till en egen RIKTIG tenant och sparar dess '
  'API-nyckel. Sluggen måste börja på kund- : annars hade en manipulerad '
  'frontend kunnat flytta arbetsytan till en annan kunds tenant.';
comment on function public.save_admin_tenant_key(text, uuid, text) is
  'Sparar en utfärdad nyckel för en NAMNGIVEN kund. Kräver platform_admins och '
  'att arbetsytan redan bär sluggen; en nyckel som pekar på en annan tenant än '
  'arbetsytans avvisas i stället för att tyst skriva över den.';
