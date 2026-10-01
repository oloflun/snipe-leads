-- Paketet får en admin-skrivväg, och kontot får ett LÄGE i stället för en bool.
--
-- ## Vad som saknades
--
-- `set_workspace_products` (044/047) skriver bara den EGNA arbetsytan — den är
-- kundens självbetjäning. Adminytan hade därför ingen väg att byta en kunds
-- paket: tilläggen fick sin skrivväg i 063, paketet fick aldrig någon.
-- `admin_set_workspace_products` nedan är spegeln av `set_workspace_addons`,
-- samma grind (platform_admins), samma adressering (ss_tenant_id), samma
-- domare (check-villkoret `workspaces_products_valid`).
--
-- ## Varför `status` och inte bara `active`
--
-- `ss_tenants.active` är spärren (validate_api_key avvisar inaktiva), men den
-- bär ingen AVSIKT: en kund som pausat över sommaren och en kund vars avtal
-- sagts upp ser identiska ut i varje vy och varje händelselogg. `status`
-- skiljer dem åt — 'pausad' är en förhandling som ska öppnas igen, 'avstangd'
-- är ett avslut. `active` står kvar som den enda spärr koden läser;
-- applikationen håller dem i synk (set_tenant_status/set_tenant_active i
-- storage), kolumnen är etiketten, inte en andra spärr.
--
-- Idempotent enligt husets regel.

alter table public.ss_tenants
  add column if not exists status text not null default 'aktiv';

-- Drop + skapa om, samma mönster som 047 för check-villkor.
alter table public.ss_tenants
  drop constraint if exists ss_tenants_status_valid;

alter table public.ss_tenants
  add constraint ss_tenants_status_valid
  check (status in ('aktiv', 'pausad', 'avstangd'));

-- Backfill: ett konto som redan är avstängt var avstängt innan ordet fanns.
update public.ss_tenants set status = 'avstangd'
 where not active and status = 'aktiv';

comment on column public.ss_tenants.status is
  'Kontots läge: aktiv, pausad (tillfälligt, öppnas igen) eller avstangd '
  '(avslut/uppsägning). active är spärren och hålls i synk av applikationen; '
  'status är avsikten bakom den.';

-- ---------------------------------------------------------------------------
-- Admin byter en kunds paket. Spegel av set_workspace_addons (063).
-- ---------------------------------------------------------------------------
--
-- Funktionen räknar INTE upp giltiga produkter själv: den försöker skriva och
-- låter `workspaces_products_valid` (047) vara domaren, exakt som 063 gör med
-- addons-checken. Två uppräkningar av samma sanning glider isär.

create or replace function public.admin_set_workspace_products(mal_tenant uuid, nya text[])
returns text[]
language plpgsql
security definer
set search_path to 'public', 'pg_temp'
as $$
declare
  anvandare uuid := nullif(current_setting('app.user_id', true), '')::uuid;
  resultat text[];
begin
  if anvandare is null then
    raise exception 'ingen inloggad användare';
  end if;

  if not exists (select 1 from public.platform_admins where user_id = anvandare) then
    -- Samma svar som en okänd tenant hade gett. Ett särskilt
    -- behörighetsfel bekräftar att arbetsytan finns.
    raise exception 'arbetsytan finns inte';
  end if;

  if nya is null or array_length(nya, 1) is null then
    -- Checken kräver minst en produkt; ett tomt paket är inte ett paket.
    raise exception 'paketet saknar produkter';
  end if;

  begin
    update public.workspaces
       set products = nya
     where ss_tenant_id = mal_tenant
    returning products into resultat;
  exception
    when check_violation then
      raise exception 'okänd produkt i listan: %', array_to_string(nya, ', ');
  end;

  if resultat is null then
    raise exception 'arbetsytan finns inte';
  end if;

  return resultat;
end;
$$;

-- Migration 018 återkallade execute på public för alla funktioner — samma
-- grunter som 063, annars blir svaret "permission denied" och ser ut som RLS.
revoke all on function public.admin_set_workspace_products(uuid, text[]) from public;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    grant execute on function public.admin_set_workspace_products(uuid, text[]) to snajp_web;
  end if;
  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    grant execute on function public.admin_set_workspace_products(uuid, text[]) to authenticated;
  end if;
end $$;

comment on function public.admin_set_workspace_products(uuid, text[]) is
  'Plattformsadmin byter en arbetsytas paket (products). Grindad på '
  'platform_admins; värdemängden ägs av workspaces_products_valid, inte av '
  'funktionen.';
