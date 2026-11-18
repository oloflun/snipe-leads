-- Avregistreringar måste gå att läsa från BACKENDEN, inte bara dashboarden.
--
-- Problemet: `public.suppressions` (från 000) är workspace-skopad. Dashboarden
-- (Next.js) läser den på `workspace_id`. Men den kod som faktiskt avgör om ett
-- mejl går iväg — `app/leads/send_guard.py` regel 3 — kör i backenden, och
-- backenden känner bara till `tenant_id`.
--
-- Följden utan den här migrationen: avregistreringen skrivs på ett ställe och
-- kontrolleras inte alls på det andra. En mottagare som klickat "avregistrera"
-- hade fått nästa utskick ändå, och löftet i mejlet blivit ett brutet löfte.
--
-- VARFÖR EN KOLUMN OCH INTE EN NY TABELL: två suppressionslistor som kan säga
-- emot varandra är värre än ingen. Vilken av dem som gäller hade avgjorts av
-- vilken kodväg som råkade fråga, och den sortens fråga besvaras alltid vid
-- fel tillfälle — efter att mejlet gått.
--
-- Idempotent enligt husets regel: kan köras om utan verkan.

alter table public.suppressions
  add column if not exists tenant_id uuid references public.ss_tenants(id) on delete cascade;

-- Backfill ur den befintliga kopplingen workspace → tenant (migration 007).
-- Rader vars workspace saknar tenant lämnas med NULL: de hör till ett
-- workspace som inte har någon backend-kund, och att gissa en tenant åt dem
-- hade flyttat någons avregistrering till fel bolag.
update public.suppressions s
   set tenant_id = w.ss_tenant_id
  from public.workspaces w
 where w.id = s.workspace_id
   and s.tenant_id is null
   and w.ss_tenant_id is not null;

-- Uppslaget send_guard gör vid VARJE utskick: "har den här adressen
-- avregistrerat sig hos den här kunden?". Utan index är det en full scan i
-- sändningsögonblicket.
create index if not exists suppressions_tenant_email_idx
  on public.suppressions (tenant_id, lower(email));

-- Samma tenant-isolering som resten av backendens tabeller, med 028:s
-- nullif-skydd inbyggt från början. Utan nullif kastar policyn
-- `invalid input syntax for type uuid: ""` så fort en skopad fråga körts
-- tidigare på samma poolade anslutning — se 028 för hela mekanismen.
drop policy if exists suppressions_tenant_isolation on public.suppressions;
create policy suppressions_tenant_isolation on public.suppressions
  for all to snajp_app
  using (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  with check (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

comment on column public.suppressions.tenant_id is
  'Backendens väg in. Dashboarden skopar på workspace_id; send_guard regel 3 '
  'skopar på tenant_id. Samma rader, två läsare — aldrig två listor.';
