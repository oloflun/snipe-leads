-- Organisationsnumret, läsbart för den tenant som frågar om SIG SJÄLV.
--
-- ## Varför funktionen behövs
--
-- `orgnr` bor i `ss_customer_details` (migration 053), och den tabellens
-- RLS-policy släpper BARA igenom anrop där `app.tenant_id` inte är satt —
-- alltså en oskopad admin-anslutning. Det var rätt beslut för kundregistret:
-- fakturaadress och avtalsdatum ska inte vara läsbara från en agentkörning.
--
-- Men Skatteverket-uppslaget (app/leads/skatteverket.py) körs tenant-SKOPAT och
-- behöver exakt ett fält ur den raden: organisationsnumret för det bolag som
-- redan är inloggat. Utan den här funktionen läser koden noll rader och
-- funktionen självdör tyst — precis den sortens fel som `har_riktig_kunddata`
-- och `active_llm_key` finns dokumenterade för att förhindra.
--
-- ## Varför INGEN parameter
--
-- Samma skäl som `tenant_api_key_for_current_workspace()` i migration 040
-- skriver ut: ett `tenant_id` som argument hade gjort funktionen till en
-- uppslagsbok över ALLA kunders organisationsnummer, och en bugg i en enda
-- anropsplats hade räckt för att läsa fel bolags. Tenanten läses i stället ur
-- `app.tenant_id`, som backenden sätter per transaktion och modellen aldrig
-- rör (INV-SEC-002).
--
-- Är `app.tenant_id` inte satt returnerar funktionen null i stället för att
-- gissa. En oskopad anslutning har redan admin-vägen via `ss_customer_details`.
--
-- ## Varför bara orgnr och inget annat
--
-- Funktionen returnerar EN kolumn. Att returnera hela raden hade öppnat
-- fakturaadress, avtalsdatum och kontaktuppgifter för varje agentkörning —
-- alltså tagit bort skyddet 053 medvetet byggde, för att lösa ett behov som
-- gäller ett enda fält.

create or replace function public.orgnr_for_current_tenant()
returns text
language plpgsql
security definer
set search_path = public
as $$
declare
  aktiv uuid;
  nummer text;
begin
  aktiv := nullif(current_setting('app.tenant_id', true), '')::uuid;
  if aktiv is null then
    return null;
  end if;

  select d.orgnr into nummer
  from public.ss_customer_details d
  where d.tenant_id = aktiv;

  return nummer;
exception
  -- Ett trasigt app.tenant_id (inte ett uuid) ska ge "vet inte", inte fälla
  -- hela agentkörningen på en cast.
  when invalid_text_representation then
    return null;
end $$;

comment on function public.orgnr_for_current_tenant() is
  'Organisationsnumret för tenanten i app.tenant_id, eller null. Ingen '
  'parameter med flit — se migrationens kommentar. Används av '
  'app/leads/skatteverket.py för Skatteverket-uppslaget.';

revoke all on function public.orgnr_for_current_tenant() from public;
grant execute on function public.orgnr_for_current_tenant() to snajp_app;
