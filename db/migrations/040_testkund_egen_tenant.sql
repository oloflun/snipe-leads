-- En egen tenant per testkund, utan en kodändring per testkonto.
--
-- ## Vad som var fel
--
-- Alla testarbetsytor pekade på den DELADE tenanten `testkund` (migration 038,
-- lib/tenants/testkund.ts). De delade därmed inkorg, kunskapsbas och
-- röstdokument. Två följder, och den första är den allvarliga:
--
--  1. Kund A:s villkor kunde grunda ett svar till kund B:s kund.
--     Grundningsgrinden ser en träff — den kan inte se att artikeln kom från
--     ett annat bolag. Ju fler testkunder, desto sämre svar för alla.
--  2. Ingenting följde med vid konvertering. En testkund som blev kund fick en
--     ny tenant, och allt de konfigurerat under testet låg kvar i den delade.
--
-- ## Varför det inte gick att lösa förut
--
-- En egen tenant krävde TVÅ saker som bara en utvecklare kan göra: en configfil
-- i `lib/tenants/` och en miljövariabel med API-nyckeln (`requireSnajpTenant`
-- läser `process.env[tenant.supportKeyEnv]`). Alltså en commit och en deploy per
-- testkonto — precis den friktion testarbetsytan fanns för att ta bort.
--
-- Backenden kunde redan skapa tenants i drift (`POST /api/keys` med
-- master-nyckeln). Det som saknades var ett ställe för nyckeln som inte är en
-- miljövariabel.
--
-- ## Varför nyckeln inte ligger i workspaces
--
-- Samma resonemang som 038:s: en UPDATE-policy på `workspaces` hade öppnat hela
-- raden för appen, inklusive `slug` — kolumnen som avgör VILKEN KUNDS data
-- arbetsytan ser. Nyckeln får därför en egen tabell UTAN policies, och appen når
-- den bara genom två security definer-funktioner som var och en kan göra exakt
-- en sak.

create table if not exists public.workspace_tenant_keys (
  workspace_id uuid primary key references public.workspaces(id) on delete cascade,
  tenant_slug text not null,
  ss_tenant_id uuid not null,
  -- Nyckeln i klartext. Backenden lagrar bara sha256-hashen och kan därför inte
  -- lämna tillbaka den; någon måste hålla originalet för att kunna anropa
  -- backenden i kundens namn. Raden är oläsbar för appen (ingen policy nedan)
  -- och nås bara genom funktionen längst ned.
  api_key text not null,
  created_at timestamptz not null default now()
);

alter table public.workspace_tenant_keys enable row level security;

-- INGA policies, med flit. RLS utan policy = noll rader för alla roller utom
-- ägaren och security definer-funktioner. Det är hela skyddet: en bugg i
-- frontenden kan inte läsa ut en annan arbetsytas nyckel, eftersom den inte kan
-- läsa tabellen alls.
revoke all on table public.workspace_tenant_keys from public, anon, authenticated;

comment on table public.workspace_tenant_keys is
  'API-nyckeln till arbetsytans EGNA backend-tenant, för tenants som skapas i '
  'drift och därför inte har någon configfil. Läs aldrig direkt — använd '
  'tenant_api_key_for_current_workspace().';


-- Skapar kopplingen. Villkoren sitter i funktionskroppen där appen inte når dem.
--
-- Vad funktionen INTE kan göra:
--   * peka på en tenant som inte är en testtenant — sluggen måste börja på
--     'testkund-', annars kunde en manipulerad frontend flytta arbetsytan till
--     en RIKTIG kunds tenant
--   * röra en arbetsyta som redan har en slug — `where slug is null`
--   * röra någon annans arbetsyta — workspacet läses ur anroparens profil
create or replace function public.link_test_tenant(
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
  if p_slug is null or p_slug !~ '^testkund-[a-z0-9]{4,32}$' then
    -- Fail-closed och tyst: den som råkar anropa fel ska inte få veta vilket
    -- mönster som hade fungerat.
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
         ss_tenant_id = p_tenant_id,
         is_demo = true
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


-- Läsvägen. Returnerar nyckeln för DEN INLOGGADES arbetsyta och ingen annans.
-- Ingen parameter: en workspace_id som argument hade gjort funktionen till en
-- uppslagsbok över alla arbetsytors nycklar.
create or replace function public.tenant_api_key_for_current_workspace()
returns text
language plpgsql
security definer
set search_path = public
as $$
declare
  nyckel text;
begin
  select k.api_key into nyckel
    from public.workspace_tenant_keys k
    join public.profiles p on p.workspace_id = k.workspace_id
   where p.id = nullif(current_setting('app.user_id', true), '')::uuid;

  return nyckel;
end;
$$;

revoke execute on function public.link_test_tenant(text, uuid, text) from public, anon;
revoke execute on function public.tenant_api_key_for_current_workspace() from public, anon;
grant execute on function public.link_test_tenant(text, uuid, text) to authenticated, snajp_web;
grant execute on function public.tenant_api_key_for_current_workspace() to authenticated, snajp_web;

comment on function public.link_test_tenant(text, uuid, text) is
  'Kopplar den INLOGGADES arbetsyta till en EGEN testtenant och sparar dess '
  'API-nyckel. Sluggen måste börja på testkund- : annars hade en manipulerad '
  'frontend kunnat flytta arbetsytan till en riktig kunds tenant.';
