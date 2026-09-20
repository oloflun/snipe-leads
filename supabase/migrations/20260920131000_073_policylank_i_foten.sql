-- Integritetspolicylänk i utskicksfoten + tenantens läsning av sina egna
-- avsändaruppgifter.
--
-- Utskicksfoten (app/leads/utskicksfot.py) bär art. 14-informationen som
-- löpande text men ingen länk till hyreskundens integritetspolicy — och
-- art. 14.2 pekar mot mer information än fyra meningar rymmer (lagringstid,
-- mottagare, rätten att klaga till IMY). Länken blir obligatorisk i
-- send_guard, så fältet måste finnas att fylla i.
--
-- Fältet läggs i kundregistret (053), som redan är hemmet för det manuella
-- lagret av kundens bolagsuppgifter (orgnr, adresser). Ingen ny tabell.
alter table public.ss_customer_details
  add column if not exists policy_url text;

comment on column public.ss_customer_details.policy_url is
  'URL till kundens egen integritetspolicy. Obligatorisk i kallmejlfoten '
  '(send_guard) — utan den blockeras kundens utskick.';

-- Fotbygget körs tenant-skopat (leads_tools -> get_tenant -> _scoped), men
-- 053:s policy släpper bara igenom läsning UTAN tenant-kontext (adminvägen).
-- En tenant måste kunna läsa sin EGEN registerrad för att foten ska kunna
-- byggas ur orgnr, företagsadress och policy_url. Enbart select — skrivningar
-- går fortsatt genom adminvägen bakom masternyckeln.
drop policy if exists ss_customer_details_tenant_read on public.ss_customer_details;
create policy ss_customer_details_tenant_read on public.ss_customer_details
  for select to snajp_app
  using (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

-- Verifiering efter körning — som snajp_app med app.tenant_id satt till en
-- kund: select policy_url from ss_customer_details; ska ge exakt en rad
-- (kundens egen) eller noll om registret saknar raden.
