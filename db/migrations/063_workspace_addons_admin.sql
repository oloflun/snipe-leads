-- Tilläggen får en skrivväg. Plattformsadminens, inte kundens.
--
-- ## Vad som saknades
--
-- `workspaces.addons` har funnits sedan migration 022 och grindar riktiga
-- vyer (Leadslistor, kopplad inkorg, bildanalys …), men INGEN kodväg har
-- någonsin skrivit kolumnen. Uppmätt 2026-09-08: varje tillägg i produkten
-- slutar i "Hör av dig", och den enda vägen att faktiskt aktivera ett var
-- handskriven SQL mot databasen. En pilotkund som köper Leadslistor krävde
-- alltså ett databasingrepp per kund.
--
-- ## Varför admin och inte kunden
--
-- `products` (migration 044) är självbetjäning med flit: paketet ÄR
-- entitlementen och kunden får byta det själv. Ett TILLÄGG är något vi
-- sätter upp — en IMAP-koppling, en verifierad domän, en egen kvot — och
-- det som avgör om det fungerar är arbete hos oss, inte en kryssruta hos
-- kunden. En kund som kunde slå på "Kopplad inkorg" själv hade fått en vy
-- som inte kan leverera. Grinden är därför `platform_admins`, samma tabell
-- som `/admin` självt vilar på (migration 020).
--
-- ## Varför två funktioner och ingen UPDATE-policy
--
-- Samma skäl som 044 stavar ut: en UPDATE-policy på `workspaces` gäller
-- RADEN, inte kolumnen, och hade öppnat `slug` och `ss_tenant_id` — som
-- binder arbetsytan till sin backend-tenant. Läsningen går samma väg av ett
-- besläktat skäl: adminen läser en ANNAN arbetsyta än sin egen, alltså
-- utanför sin RLS-scope, och den korsningen ska ske i en funktion som
-- kontrollerar behörigheten själv — inte genom en oskopad anslutning.
--
-- ## Adressering på ss_tenant_id
--
-- Adminytan bär tenantens UUID i adressen (se app/admin/kunder/[id]), och
-- att översätta id → slug → workspace i en yta som SKRIVER är ett uppslag
-- till som kan peka fel kund. Funktionerna tar därför tenant-id:t direkt.
--
-- Idempotent enligt husets regel.

-- ---------------------------------------------------------------------------
-- Den giltiga mängden, på ETT ställe i databasen.
-- ---------------------------------------------------------------------------
--
-- Check-villkoret (022, utökat i 060) och den här funktionen räknade upp
-- samma sju värden var för sig. Två uppräkningar av samma sanning glider —
-- det är precis felklassen `agent_runs.agent_type` levde med i ett halvår.
-- Funktionen nedan läser därför INTE en egen lista: den försöker skriva, och
-- låter check-villkoret vara domaren. Felet översätts till svenska så att
-- "workspaces_addons_check" inte är det en människa möter.

create or replace function public.set_workspace_addons(mal_tenant uuid, nya text[])
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

  if nya is null then
    raise exception 'tilläggslistan saknas';
  end if;

  begin
    update public.workspaces
       set addons = nya
     where ss_tenant_id = mal_tenant
    returning addons into resultat;
  exception
    when check_violation then
      raise exception 'okänt tillägg i listan: %', array_to_string(nya, ', ');
  end;

  if resultat is null then
    raise exception 'arbetsytan finns inte';
  end if;

  return resultat;
end;
$$;

-- ---------------------------------------------------------------------------
-- Läsningen. Samma grind, samma svar på en okänd tenant.
-- ---------------------------------------------------------------------------

create or replace function public.admin_workspace_addons(mal_tenant uuid)
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
    raise exception 'arbetsytan finns inte';
  end if;

  select addons into resultat
    from public.workspaces
   where ss_tenant_id = mal_tenant;

  if resultat is null then
    raise exception 'arbetsytan finns inte';
  end if;

  return resultat;
end;
$$;

-- Migration 018 återkallade execute på public för alla funktioner. Utan de
-- här grunten svarar RPC:n "permission denied", och det felet ser ut som ett
-- RLS-problem — alltså fel ställe att leta på. Samma not som 044.
revoke all on function public.set_workspace_addons(uuid, text[]) from public;
revoke all on function public.admin_workspace_addons(uuid) from public;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_web') then
    grant execute on function public.set_workspace_addons(uuid, text[]) to snajp_web;
    grant execute on function public.admin_workspace_addons(uuid) to snajp_web;
  end if;
  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    grant execute on function public.set_workspace_addons(uuid, text[]) to authenticated;
    grant execute on function public.admin_workspace_addons(uuid) to authenticated;
  end if;
end $$;

comment on function public.set_workspace_addons(uuid, text[]) is
  'Plattformsadmin sätter en arbetsytas tillägg. Grindad på platform_admins; '
  'värdemängden ägs av workspaces_addons_check, inte av funktionen.';
comment on function public.admin_workspace_addons(uuid) is
  'Plattformsadmin läser en arbetsytas tillägg. Korsar RLS-scope med flit — '
  'därför samma grind som skrivfunktionen.';
