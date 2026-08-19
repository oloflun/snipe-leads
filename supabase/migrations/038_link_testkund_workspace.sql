-- Testarbetsytan kunde inte koppla sig själv till sin tenant.
--
-- UPPMÄTT 2026-08-19 mot railway-development: onboardingen körde
--
--     update public.workspaces set slug='testkund', ss_tenant_id=…
--      where id=$1 and slug is null
--
-- som `snajp_web` via sqlAsUser. Noll rader ändrades. Inget fel kastades.
--
-- ORSAKEN: `public.workspaces` har exakt EN policy — "workspace members can
-- read workspace", med `polcmd = 'r'`. Det finns ingen UPDATE-policy alls, och
-- när ingen policy gäller kommandot ger RLS noll rader utan att kasta.
--
-- Det är TREDJE gången samma tysthet slår till i den här kodbasen: 020:s
-- självrefererande policy, 033:s rollbindning till `authenticated`, och nu en
-- saknad UPDATE-policy. Alla tre ser likadana ut utifrån — något gick inte att
-- göra, och koden läser svaret som "då var det så".
--
-- FIXEN är inte en UPDATE-policy på workspaces. En sådan hade öppnat HELA
-- raden för appen — namn, produkter, is_demo, och framför allt `slug`, som är
-- det som avgör VILKEN KUNDS data arbetsytan ser. En bugg i frontenden hade då
-- kunnat flytta en arbetsyta till en annan kunds tenant.
--
-- I stället en smal dörr, samma mönster som `ensure_workspace_for_current_user`
-- i 006: en security definer-funktion som bara kan göra EN sak, och där
-- villkoren sitter i funktionskroppen där appen inte når dem.
--
-- Vad funktionen INTE kan göra, med flit:
--   * peka på någon annan tenant än `testkund` — slugen är en literal
--   * röra en arbetsyta som redan har en slug — `where slug is null`
--   * röra någon annans arbetsyta — workspacet läses ur anroparens profil
--
-- Den är därför säker att ge till appen, till skillnad från en UPDATE-policy.

create or replace function public.link_testkund_workspace()
returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
  ws_id uuid;
  tenant uuid;
begin
  select p.workspace_id into ws_id
    from public.profiles p
   where p.id = nullif(current_setting('app.user_id', true), '')::uuid;

  if ws_id is null then
    return false;
  end if;

  select t.id into tenant from public.ss_tenants t where t.slug = 'testkund';

  if tenant is null then
    -- Tenanten skapas av backendens POST /api/keys
    -- (scripts/railway_tenant_keys.py). Saknas den är svaret nej, inte ett
    -- undantag: onboardingen ska inte falla för att en testyta inte kunde
    -- kopplas — affärskontexten är redan sparad.
    return false;
  end if;

  update public.workspaces
     set slug = 'testkund',
         ss_tenant_id = tenant,
         is_demo = true
   where id = ws_id
     and slug is null;

  return found;
end;
$$;

revoke execute on function public.link_testkund_workspace() from public, anon;
grant execute on function public.link_testkund_workspace() to authenticated, snajp_web;

comment on function public.link_testkund_workspace() is
  'Kopplar den INLOGGADES arbetsyta till den delade testkund-tenanten, en gång. '
  'Finns för att workspaces saknar UPDATE-policy med flit: en sådan hade låtit '
  'appen skriva om slug, alltså byta vilken kunds data arbetsytan ser.';
