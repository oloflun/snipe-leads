-- Bokföringen blir en produkt en arbetsyta kan äga.
--
-- ## Vad som faktiskt ändras
--
-- Ett värde i check-villkoret från 005, och ingenting annat. Ingen kolumn,
-- ingen tabell, ingen backfill: `products` har redan rätt form, den fick bara
-- inte innehålla `bookkeeping`.
--
-- ## Varför ingen arbetsyta får värdet här
--
-- Migrationen VIDGAR vad som är tillåtet. Den delar inte ut produkten. Att
-- passa på att ge alla befintliga arbetsytor bokföring hade varit att sälja
-- något ingen beställt — och entitlements är fail-closed sedan Fas 3 (se
-- lib/data/dashboard.ts) just för att en felkonfigurerad arbetsyta ska se
-- MINDRE, inte allt.
--
-- Vägen in för en kund som köper den är `set_workspace_products` (migration
-- 044) eller ett adminbeslut, inte en migration.
--
-- ## Varför villkoret skrivs om i stället för att utökas
--
-- Ett check-villkor går inte att lägga till i. Det droppas och skapas om, och
-- det är samma mönster som 022 använder för `workspaces_addons_check`. Att
-- göra det idempotent är inte kosmetik: migrationskedjan ska gå att resa från
-- noll, och `railway_migrate.py` är testet av det påståendet.

alter table public.workspaces
  drop constraint if exists workspaces_products_valid;

alter table public.workspaces
  add constraint workspaces_products_valid
  check (
    products <@ array['leads', 'support', 'bookkeeping']::text[]
    and array_length(products, 1) >= 1
  );

comment on column public.workspaces.products is
  'Entitlement: vilka Snajp-produkter arbetsytan får använda. Delmängd av '
  '{leads, support, bookkeeping}, aldrig tom. Bokföringen tillkom i 047 — '
  'den delas ut per kund, aldrig av en migration.';

-- ---------------------------------------------------------------------------
-- RPC:n som kunden byter paket med känner också till listan.
--
-- `set_workspace_products` (migration 044) validerar mot sin EGEN uppräkning
-- innan den skriver, med flit: ett check-brott från djupet av en UPDATE säger
-- bara "workspaces_products_valid", vilket inte hjälper den som skickade fel
-- lista. Priset för det begripliga felet är att listan står på två ställen,
-- och de måste ändras tillsammans.
--
-- Missas den här halvan syns det inte i något check-villkor: kolumnen tillåter
-- värdet, men funktionen vägrar skriva det. Paketbytet hade svarat "okänd
-- produkt i listan" för en produkt som finns.
--
-- Funktionen skrivs om i sin helhet (create or replace) i stället för att
-- lappas — en funktionskropp går inte att ändra styckvis, och en halv
-- omskrivning är ingen omskrivning.

create or replace function public.set_workspace_products(nya text[])
returns text[]
language plpgsql
security definer
set search_path to 'public', 'pg_temp'
as $$
declare
  anvandare uuid := nullif(current_setting('app.user_id', true), '')::uuid;
  arbetsyta uuid;
  resultat text[];
begin
  if anvandare is null then
    raise exception 'ingen inloggad användare';
  end if;

  select workspace_id into arbetsyta from public.profiles where id = anvandare;
  if arbetsyta is null then
    raise exception 'användaren saknar arbetsyta';
  end if;

  if nya is null or array_length(nya, 1) is null then
    raise exception 'en arbetsyta måste ha minst en produkt';
  end if;
  if not (nya <@ array['leads', 'support', 'bookkeeping']::text[]) then
    raise exception 'okänd produkt i listan';
  end if;

  update public.workspaces
     set products = nya
   where id = arbetsyta
  returning products into resultat;

  return resultat;
end;
$$;

revoke all on function public.set_workspace_products(text[]) from public;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    grant execute on function public.set_workspace_products(text[]) to snajp_web;
  end if;
  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    grant execute on function public.set_workspace_products(text[]) to authenticated;
  end if;
end $$;
