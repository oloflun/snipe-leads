-- Snajp-Support: kopplingen mellan snipe-leads-inloggningen och en Snajp-tenant.
-- Körs efter 006. Idempotent.
--
-- Ett workspace (organisationen som skapas av triggern i 001_handle_new_user.sql)
-- mappar till exakt en tenant i Snajp-Support. Raden skapas lat av Next-appen
-- första gången någon i workspacet öppnar /snajp-support — ingen seed, inga
-- .env-ändringar per kund.
--
-- Till skillnad från ss_-tabellerna hör den här tabellen till Next-appens domän:
-- den läses server-side med service-role-nyckeln, aldrig av webbläsaren.

create table if not exists snajp_workspace_tenants (
  workspace_id uuid primary key references workspaces(id) on delete cascade,
  tenant_id uuid not null unique,
  tenant_slug text,
  -- Tenantens API-nyckel i klartext. Backenden lagrar bara sha256-hashen och kan
  -- alltså inte visa nyckeln igen, så proxyn måste kunna läsa den här för att
  -- kunna anropa backenden som rätt tenant.
  --
  -- Skyddet är att tabellen är oåtkomlig för alla klientroller (se RLS nedan) —
  -- bara service-role-nyckeln, som bara finns server-side, kommer åt den.
  -- Vill du härda ytterligare: kryptera kolumnen med pgcrypto (extensionen är
  -- redan påslagen i 002) och håll nyckeln i en env-var på Vercel.
  api_key text not null,
  -- Visas i UI:t så kunden känner igen sin nyckel utan att vi röjer den.
  key_prefix text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Ingen FK mot ss_tenants: backenden kan peka på en annan databas än Next-appen,
-- och tenanten skapas via API:t (inte via SQL). Unikhetsvillkoret ovan är det som
-- garanterar att två workspaces aldrig delar tenant.

-- RLS med NOLLA policyer = ingen klientroll (anon/authenticated) kommer åt raden,
-- varken läsning eller skrivning. service_role har BYPASSRLS och påverkas inte.
-- FORCE gör att inte heller tabellägaren slipper undan.
alter table snajp_workspace_tenants enable row level security;
alter table snajp_workspace_tenants force row level security;

-- Explicit: dra tillbaka de default-grants Supabase ger klientrollerna, så att
-- nyckeln inte kan läsas ens om någon senare lägger på en slarvig policy.
revoke all on snajp_workspace_tenants from anon, authenticated;
