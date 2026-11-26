-- 160: Snajp CRM, grunden och kundsynken in (Antons beställning 2026-11-24).
--
-- Buddy vill inte ladda upp sin kundlista för hand: kunddatan ska synkas in
-- över ett API och hållas aktuell, och kunderna ska gå att hantera i Snajp.
-- Fram till nu har ett "bolag" bara funnits som en rad i prospects eller i
-- lead_list_items, utan egen nyckel (docs/crm/underlag/snajp-01). Här får
-- bolaget och personen egna tabeller, med organisationsnumret som unik nyckel
-- per kund. Skälen till valen står i docs/BESLUT.md 2026-11-25.
--
-- 1. crm_anslutningar: en källa per system kunden synkar från (HubSpot,
--    Pipedrive, Lime, Lime Go, Upsales, Salesforce, Twenty, SuperOffice,
--    Dynamics, Fortnox, Visma eller eget format). Bär
--    fältmappningen, konfliktregeln och vad som händer med poster som saknas
--    i en full synk.
-- 2. crm_bolag och crm_personer. Namnen companies och contacts är upptagna av
--    äldre tabeller i 000_base_schema.sql och används inte.
--    orgnr_nyckel är tio siffror utan bindestreck och sekelprefix, samma
--    nyckel som app/leads/upptagna.py räknar fram, så att ett bolag i CRM:et
--    är samma bolag som i leads. En enskild firmas organisationsnummer är ett
--    personnummer och sparas inte (beslut 2026-11-23): raden får enskild_firma
--    = true och tomt nummer, och bolaget känns igen på domän eller namn.
--    manuellt_andrade bär vilka fält en människa ändrat i Snajp och när, så
--    att konfliktregeln kan avgöra fält för fält.
--    Radering är mjuk (raderad_at): den som synkar måste kunna se att en post
--    försvunnit, och den som raderat av misstag kan ångra sig. Efter 30 dagar,
--    eller direkt vid en permanent radering, töms raden på allt utom id och
--    tider (kalla = 'gravsten'), så att papperskorgen inte blir ett register
--    över personer som bett att få bli borttagna.
-- 3. crm_externa_id: källsystemets id för varje post, per anslutning. Det är
--    den som gör att en omsynk uppdaterar i stället för att skapa dubbletter.
-- 4. crm_synkkorningar: liggaren över varje synk. Förlopp och utfall läses
--    härifrån och finns kvar efter omladdning och driftsättning (regeln
--    2026-10-10, INV-JOB-003).
-- 5. crm_idempotens: svaret på ett anrop med Idempotency-Key, i ett dygn.
-- 6. ss_api_keys får omfång, namn och återkallelse. Befintliga nycklar
--    behåller '{*}' (allt). En nyckel som bara bär crm-omfång når inget annat
--    än CRM-API:t (app/api/deps.py: require_tenant).
--
-- Additiv och idempotent.

-- 1. Anslutningar ---------------------------------------------------------

create table if not exists public.crm_anslutningar (
  id                uuid primary key default gen_random_uuid(),
  tenant_id         uuid not null references public.ss_tenants(id) on delete cascade,
  namn              text not null,
  system            text not null default 'generisk',
  mappning          jsonb not null default '{}'::jsonb,
  konfliktregel     text not null default 'kallan_vinner',
  saknade           text not null default 'behall',
  standardrelation  text not null default 'kund',
  aktiv             boolean not null default true,
  senaste_synk_at   timestamptz,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

alter table public.crm_anslutningar drop constraint if exists crm_anslutningar_system_check;
alter table public.crm_anslutningar add constraint crm_anslutningar_system_check
  check (system in ('generisk', 'hubspot', 'pipedrive', 'lime', 'lime_go', 'upsales', 'salesforce',
                    'twenty', 'superoffice', 'dynamics', 'fortnox', 'visma'));
alter table public.crm_anslutningar drop constraint if exists crm_anslutningar_konfliktregel_check;
alter table public.crm_anslutningar add constraint crm_anslutningar_konfliktregel_check
  check (konfliktregel in ('kallan_vinner', 'snajp_vinner', 'nyast_vinner'));
alter table public.crm_anslutningar drop constraint if exists crm_anslutningar_saknade_check;
alter table public.crm_anslutningar add constraint crm_anslutningar_saknade_check
  check (saknade in ('behall', 'tidigare_kund', 'ta_bort'));

create unique index if not exists crm_anslutningar_namn_uq
  on public.crm_anslutningar (tenant_id, lower(namn));

-- 2. Bolag och personer ---------------------------------------------------

create table if not exists public.crm_bolag (
  id                uuid primary key default gen_random_uuid(),
  tenant_id         uuid not null references public.ss_tenants(id) on delete cascade,
  namn              text not null,
  namnnyckel        text not null default '',
  orgnr             text,
  orgnr_nyckel      text,
  enskild_firma     boolean not null default false,
  momsnr            text,
  bolagsform        text,
  sni               text,
  webbplats         text,
  doman             text,
  epost             text,
  telefon           text,
  gatuadress        text,
  co                text,
  postnr            text,
  postort           text,
  land              text not null default 'SE',
  anstallda         integer,
  omsattning        bigint,
  relation          text not null default 'kund',
  kund_sedan        date,
  avtalsslut        date,
  ansvarig          text,
  kontakta_inte     boolean not null default false,
  extra             jsonb not null default '{}'::jsonb,
  manuellt_andrade  jsonb not null default '{}'::jsonb,
  kalla             text not null default 'manuell',
  prospect_id       uuid references public.prospects(id) on delete set null,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  raderad_at        timestamptz
);

alter table public.crm_bolag drop constraint if exists crm_bolag_relation_check;
alter table public.crm_bolag add constraint crm_bolag_relation_check
  check (relation in ('kund', 'tidigare_kund', 'prospekt', 'partner', 'leverantor', 'ovrigt'));
alter table public.crm_bolag drop constraint if exists crm_bolag_orgnr_nyckel_check;
alter table public.crm_bolag add constraint crm_bolag_orgnr_nyckel_check
  check (orgnr_nyckel is null or orgnr_nyckel ~ '^[0-9]{10}$');

-- Ett bolag, en rad: organisationsnumret är unikt per kund bland levande rader.
create unique index if not exists crm_bolag_orgnr_uq
  on public.crm_bolag (tenant_id, orgnr_nyckel)
  where orgnr_nyckel is not null and raderad_at is null;
create index if not exists crm_bolag_namn_idx on public.crm_bolag (tenant_id, namnnyckel);
create index if not exists crm_bolag_doman_idx on public.crm_bolag (tenant_id, doman)
  where doman is not null;
-- Ändringsflödet: den som synkar ut läser i den här ordningen.
create index if not exists crm_bolag_andrad_idx on public.crm_bolag (tenant_id, updated_at, id);

create table if not exists public.crm_personer (
  id                uuid primary key default gen_random_uuid(),
  tenant_id         uuid not null references public.ss_tenants(id) on delete cascade,
  bolag_id          uuid references public.crm_bolag(id) on delete set null,
  fornamn           text,
  efternamn         text,
  titel             text,
  epost             text,
  telefon           text,
  mobil             text,
  rattslig_grund    text,
  kontakta_inte     boolean not null default false,
  extra             jsonb not null default '{}'::jsonb,
  manuellt_andrade  jsonb not null default '{}'::jsonb,
  kalla             text not null default 'manuell',
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  raderad_at        timestamptz
);

alter table public.crm_personer drop constraint if exists crm_personer_rattslig_grund_check;
alter table public.crm_personer add constraint crm_personer_rattslig_grund_check
  check (rattslig_grund is null or rattslig_grund in ('avtal', 'berattigat_intresse', 'samtycke'));

create unique index if not exists crm_personer_epost_uq
  on public.crm_personer (tenant_id, lower(epost))
  where epost is not null and raderad_at is null;
create index if not exists crm_personer_bolag_idx on public.crm_personer (tenant_id, bolag_id);
create index if not exists crm_personer_andrad_idx on public.crm_personer (tenant_id, updated_at, id);

-- 3. Källsystemens id -----------------------------------------------------

create table if not exists public.crm_externa_id (
  id                    uuid primary key default gen_random_uuid(),
  tenant_id             uuid not null references public.ss_tenants(id) on delete cascade,
  anslutning_id         uuid not null references public.crm_anslutningar(id) on delete cascade,
  objekt                text not null,
  externt_id            text not null,
  post_id               uuid not null,
  innehallshash         text,
  extern_uppdaterad_at  timestamptz,
  senast_korning        uuid,
  senast_sedd_at        timestamptz not null default now(),
  created_at            timestamptz not null default now()
);

alter table public.crm_externa_id drop constraint if exists crm_externa_id_objekt_check;
alter table public.crm_externa_id add constraint crm_externa_id_objekt_check
  check (objekt in ('bolag', 'person'));

create unique index if not exists crm_externa_id_uq
  on public.crm_externa_id (anslutning_id, objekt, externt_id);
create index if not exists crm_externa_id_post_idx
  on public.crm_externa_id (tenant_id, objekt, post_id);

-- 4. Synkens liggare ------------------------------------------------------

create table if not exists public.crm_synkkorningar (
  id             uuid primary key default gen_random_uuid(),
  tenant_id      uuid not null references public.ss_tenants(id) on delete cascade,
  anslutning_id  uuid references public.crm_anslutningar(id) on delete set null,
  lage           text not null default 'delta',
  status         text not null default 'processing',
  startad_av     text not null default 'api',
  totalt         integer not null default 0,
  skapade        integer not null default 0,
  uppdaterade    integer not null default 0,
  oforandrade    integer not null default 0,
  hoppade        integer not null default 0,
  konflikter     integer not null default 0,
  borttagna      integer not null default 0,
  fel            jsonb not null default '[]'::jsonb,
  error          text,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  completed_at   timestamptz
);

alter table public.crm_synkkorningar drop constraint if exists crm_synkkorningar_status_check;
alter table public.crm_synkkorningar add constraint crm_synkkorningar_status_check
  check (status in ('queued', 'processing', 'completed', 'failed'));
alter table public.crm_synkkorningar drop constraint if exists crm_synkkorningar_lage_check;
alter table public.crm_synkkorningar add constraint crm_synkkorningar_lage_check
  check (lage in ('delta', 'full'));

create index if not exists crm_synkkorningar_tenant_idx
  on public.crm_synkkorningar (tenant_id, created_at desc);

-- 5. Idempotens -----------------------------------------------------------

create table if not exists public.crm_idempotens (
  tenant_id   uuid not null references public.ss_tenants(id) on delete cascade,
  nyckel      text not null,
  vag         text not null,
  kroppshash  text not null,
  statuskod   integer not null,
  svar        jsonb not null,
  created_at  timestamptz not null default now(),
  primary key (tenant_id, nyckel)
);

create index if not exists crm_idempotens_alder_idx on public.crm_idempotens (created_at);

-- RLS och rättigheter, lika för alla sex tabellerna ------------------------
--
-- delete ges uttryckligen: snajp_app får annars bara select, insert och update
-- (009). Tabellerna speglas INTE till development än: de står inte i
-- scripts/railway_synk.py: SYNK och har därför varken synk_andrad_at eller
-- läsrätt för spegelns roll. Development får sina egna CRM-poster tills det
-- är beslutat (docs/BESLUT.md 2026-11-25).

do $$
declare
  t text;
begin
  foreach t in array array['crm_anslutningar', 'crm_bolag', 'crm_personer', 'crm_externa_id',
                           'crm_synkkorningar', 'crm_idempotens']
  loop
    execute format('alter table public.%I enable row level security', t);
    execute format('alter table public.%I force row level security', t);
    execute format('drop policy if exists tenant_isolation on public.%I', t);
    execute format(
      'create policy tenant_isolation on public.%I
         using (tenant_id = nullif(current_setting(''app.tenant_id'', true), '''')::uuid)
         with check (tenant_id = nullif(current_setting(''app.tenant_id'', true), '''')::uuid)', t);
    if exists (select 1 from pg_roles where rolname = 'snajp_app') then
      execute format('grant select, insert, update, delete on table public.%I to snajp_app', t);
    end if;
  end loop;
end $$;

-- 6. API-nycklarnas omfång ------------------------------------------------

alter table public.ss_api_keys add column if not exists omfang text[] not null default '{*}';
alter table public.ss_api_keys add column if not exists namn text;
alter table public.ss_api_keys add column if not exists revoked_at timestamptz;

comment on table public.crm_bolag is
  'Snajp CRM: bolag per kund (migration 160). orgnr_nyckel är samma nyckel som '
  'app/leads/upptagna.py; varje levande rad utesluts ur Iris-körningarna. '
  'Skrivs av app/crm/, läses av app/api/crm_v1.py.';
comment on column public.crm_bolag.orgnr is
  'Organisationsnummer NNNNNN-NNNN för juridiska personer. En enskild firmas nummer '
  'är ett personnummer och sparas inte: raden har då enskild_firma = true.';
comment on table public.crm_personer is
  'Snajp CRM: kontaktpersoner per kund (migration 160). Personuppgifter som kunden '
  'är ansvarig för och Snajp biträde för.';
comment on table public.crm_synkkorningar is
  'Liggaren över varje kundsynk in (migration 160). Förlopp och utfall läses härifrån.';
comment on column public.ss_api_keys.omfang is
  'Vad nyckeln når. ''{*}'' är allt (kundens egen backendnyckel). En nyckel med '
  'bara crm-omfång når enbart /api/crm/v1 (app/api/deps.py).';
