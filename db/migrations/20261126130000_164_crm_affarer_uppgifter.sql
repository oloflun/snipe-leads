-- 164: Snajp CRM, affärer, uppgifter, anteckningar, aktiviteter och bilagor.
--
-- Fram till nu bar CRM:et bara bolag och personer (160). En säljare behöver
-- också veta vad som är på gång med ett bolag: vilka affärer som pågår och i
-- vilket steg, vad som ska göras och när, vad som sagts och vilka filer som
-- hör till. Förlagan är Twentys opportunity, task, note och attachment
-- (docs/crm/underlag/twenty-01 och twenty-03); koden är vår egen.
--
-- 1. crm_affarssteg: affärens steg, en uppsättning per kund. Stegen skapas av
--    koden första gången kunden läser dem (app/crm/objekt.py), inte här: en
--    kund som aldrig öppnar tavlan ska inte få rader. Det unika namnet gör att
--    två samtidiga första läsningar inte ger två uppsättningar.
-- 2. crm_affarer: en affär hör till ett steg (restrict: ett steg med affärer
--    går inte att ta bort) och kan peka på ett bolag och en person.
--    avslutad_at sätts när affären når ett vunnet eller förlorat steg och
--    nollas när den flyttas tillbaka. position är ordningen inom steget på
--    tavlan; ett flyttat kort får ett värde mellan sina grannar.
--    steg_id är tom bara på en tömd affär.
-- 3. crm_uppgifter: får stå fria. klar_at följer status.
-- 4. crm_anteckningar, 5. crm_aktiviteter (loggade samtal, möten, mejl och
--    besök) och 6. crm_bilagor kräver minst en koppling; koden ser till det.
--    Bilagans innehåll ligger i raden (bytea), högst 10 MB per fil och
--    500 MB per kund, och läses bara när filen hämtas.
--
-- Radering är mjuk som för bolag och personer: raderad_at, trettio dagar i
-- papperskorgen, sedan töms raden på allt utom id och tider (kalla =
-- 'gravsten'). Töms ett bolag eller en person för gott (GDPR artikel 17)
-- töms också anteckningar, aktiviteter och bilagor som pekar på posten, och
-- uppgifter och affärer tappar kopplingen (app/crm/lagring.py: gor_gravsten).
--
-- Radskydd som de övriga CRM-tabellerna (160, 162). Additiv och idempotent.

-- 1. Affärens steg --------------------------------------------------------

create table if not exists public.crm_affarssteg (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references public.ss_tenants(id) on delete cascade,
  namn         text not null,
  position     integer not null default 0,
  sannolikhet  integer not null default 0,
  typ          text not null default 'oppen',
  farg         text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

alter table public.crm_affarssteg drop constraint if exists crm_affarssteg_typ_check;
alter table public.crm_affarssteg add constraint crm_affarssteg_typ_check
  check (typ in ('oppen', 'vunnen', 'forlorad'));
alter table public.crm_affarssteg drop constraint if exists crm_affarssteg_sannolikhet_check;
alter table public.crm_affarssteg add constraint crm_affarssteg_sannolikhet_check
  check (sannolikhet between 0 and 100);

create unique index if not exists crm_affarssteg_namn_uq
  on public.crm_affarssteg (tenant_id, lower(namn));

-- 2. Affärer --------------------------------------------------------------

create table if not exists public.crm_affarer (
  id                uuid primary key default gen_random_uuid(),
  tenant_id         uuid not null references public.ss_tenants(id) on delete cascade,
  namn              text not null,
  bolag_id          uuid references public.crm_bolag(id) on delete set null,
  person_id         uuid references public.crm_personer(id) on delete set null,
  steg_id           uuid references public.crm_affarssteg(id) on delete restrict,
  belopp            bigint,
  valuta            text not null default 'SEK',
  sannolikhet       integer,
  forvantat_avslut  date,
  avslutad_at       timestamptz,
  forlustorsak      text,
  ansvarig          text,
  position          double precision not null default 0,
  extra             jsonb not null default '{}'::jsonb,
  kalla             text not null default 'manuell',
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  raderad_at        timestamptz
);

alter table public.crm_affarer drop constraint if exists crm_affarer_sannolikhet_check;
alter table public.crm_affarer add constraint crm_affarer_sannolikhet_check
  check (sannolikhet is null or sannolikhet between 0 and 100);

create index if not exists crm_affarer_tavla_idx on public.crm_affarer (tenant_id, steg_id, position);
create index if not exists crm_affarer_bolag_idx on public.crm_affarer (tenant_id, bolag_id);
create index if not exists crm_affarer_andrad_idx on public.crm_affarer (tenant_id, updated_at, id);

-- 3. Uppgifter ------------------------------------------------------------

create table if not exists public.crm_uppgifter (
  id            uuid primary key default gen_random_uuid(),
  tenant_id     uuid not null references public.ss_tenants(id) on delete cascade,
  titel         text not null,
  beskrivning   text,
  status        text not null default 'att_gora',
  forfaller_at  timestamptz,
  klar_at       timestamptz,
  ansvarig      text,
  bolag_id      uuid references public.crm_bolag(id) on delete set null,
  person_id     uuid references public.crm_personer(id) on delete set null,
  affar_id      uuid references public.crm_affarer(id) on delete set null,
  kalla         text not null default 'manuell',
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  raderad_at    timestamptz
);

alter table public.crm_uppgifter drop constraint if exists crm_uppgifter_status_check;
alter table public.crm_uppgifter add constraint crm_uppgifter_status_check
  check (status in ('att_gora', 'pagar', 'klar'));

create index if not exists crm_uppgifter_andrad_idx on public.crm_uppgifter (tenant_id, updated_at, id);
create index if not exists crm_uppgifter_forfaller_idx on public.crm_uppgifter (tenant_id, forfaller_at);
create index if not exists crm_uppgifter_bolag_idx on public.crm_uppgifter (tenant_id, bolag_id);
create index if not exists crm_uppgifter_affar_idx on public.crm_uppgifter (tenant_id, affar_id);

-- 4. Anteckningar ---------------------------------------------------------

create table if not exists public.crm_anteckningar (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references public.ss_tenants(id) on delete cascade,
  titel       text,
  text        text not null default '',
  fast        boolean not null default false,
  forfattare  text,
  bolag_id    uuid references public.crm_bolag(id) on delete set null,
  person_id   uuid references public.crm_personer(id) on delete set null,
  affar_id    uuid references public.crm_affarer(id) on delete set null,
  kalla       text not null default 'manuell',
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  raderad_at  timestamptz
);

alter table public.crm_anteckningar drop constraint if exists crm_anteckningar_text_check;
alter table public.crm_anteckningar add constraint crm_anteckningar_text_check
  check (char_length(text) <= 20000);

create index if not exists crm_anteckningar_andrad_idx on public.crm_anteckningar (tenant_id, updated_at, id);
create index if not exists crm_anteckningar_bolag_idx on public.crm_anteckningar (tenant_id, bolag_id);
create index if not exists crm_anteckningar_person_idx on public.crm_anteckningar (tenant_id, person_id);
create index if not exists crm_anteckningar_affar_idx on public.crm_anteckningar (tenant_id, affar_id);

-- 5. Aktiviteter ----------------------------------------------------------

create table if not exists public.crm_aktiviteter (
  id               uuid primary key default gen_random_uuid(),
  tenant_id        uuid not null references public.ss_tenants(id) on delete cascade,
  typ              text not null default 'ovrigt',
  rubrik           text not null,
  text             text,
  tid              timestamptz not null default now(),
  varaktighet_min  integer,
  utfall           text,
  ansvarig         text,
  bolag_id         uuid references public.crm_bolag(id) on delete set null,
  person_id        uuid references public.crm_personer(id) on delete set null,
  affar_id         uuid references public.crm_affarer(id) on delete set null,
  kalla            text not null default 'manuell',
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  raderad_at       timestamptz
);

alter table public.crm_aktiviteter drop constraint if exists crm_aktiviteter_typ_check;
alter table public.crm_aktiviteter add constraint crm_aktiviteter_typ_check
  check (typ in ('samtal', 'mote', 'mejl', 'besok', 'ovrigt'));

create index if not exists crm_aktiviteter_andrad_idx on public.crm_aktiviteter (tenant_id, updated_at, id);
create index if not exists crm_aktiviteter_bolag_idx on public.crm_aktiviteter (tenant_id, bolag_id);
create index if not exists crm_aktiviteter_person_idx on public.crm_aktiviteter (tenant_id, person_id);
create index if not exists crm_aktiviteter_affar_idx on public.crm_aktiviteter (tenant_id, affar_id);

-- 6. Bilagor --------------------------------------------------------------

create table if not exists public.crm_bilagor (
  id             uuid primary key default gen_random_uuid(),
  tenant_id      uuid not null references public.ss_tenants(id) on delete cascade,
  filnamn        text not null,
  typ            text not null,
  storlek        integer not null,
  innehall       bytea not null,
  uppladdad_av   text,
  bolag_id       uuid references public.crm_bolag(id) on delete set null,
  person_id      uuid references public.crm_personer(id) on delete set null,
  affar_id       uuid references public.crm_affarer(id) on delete set null,
  anteckning_id  uuid references public.crm_anteckningar(id) on delete cascade,
  kalla          text not null default 'manuell',
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  raderad_at     timestamptz
);

alter table public.crm_bilagor drop constraint if exists crm_bilagor_storlek_check;
alter table public.crm_bilagor add constraint crm_bilagor_storlek_check
  check (storlek between 0 and 10485760);

create index if not exists crm_bilagor_andrad_idx on public.crm_bilagor (tenant_id, updated_at, id);
create index if not exists crm_bilagor_bolag_idx on public.crm_bilagor (tenant_id, bolag_id);
create index if not exists crm_bilagor_person_idx on public.crm_bilagor (tenant_id, person_id);
create index if not exists crm_bilagor_affar_idx on public.crm_bilagor (tenant_id, affar_id);
create index if not exists crm_bilagor_anteckning_idx on public.crm_bilagor (tenant_id, anteckning_id);

-- RLS och rättigheter, lika för alla sex tabellerna ------------------------

do $$
declare
  t text;
begin
  foreach t in array array['crm_affarssteg', 'crm_affarer', 'crm_uppgifter', 'crm_anteckningar',
                           'crm_aktiviteter', 'crm_bilagor']
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

comment on table public.crm_affarssteg is
  'Snajp CRM: affärens steg per kund (migration 164). Skapas av app/crm/objekt.py första '
  'gången kunden läser dem. Minst ett öppet, ett vunnet och ett förlorat steg finns alltid.';
comment on table public.crm_affarer is
  'Snajp CRM: affärer per kund (migration 164). position är ordningen inom steget på tavlan; '
  'avslutad_at sätts när affären når ett vunnet eller förlorat steg.';
comment on table public.crm_uppgifter is
  'Snajp CRM: uppgifter per kund (migration 164). Får stå fria från bolag, person och affär.';
comment on table public.crm_anteckningar is
  'Snajp CRM: anteckningar (migration 164). Fritext som kan bära personuppgifter: töms när '
  'posten den pekar på töms för gott.';
comment on table public.crm_aktiviteter is
  'Snajp CRM: loggade samtal, möten, mejl och besök (migration 164).';
comment on table public.crm_bilagor is
  'Snajp CRM: filer på en post (migration 164). innehall läses bara vid nedladdning; listor '
  'bär det aldrig. Högst 10 MB per fil och 500 MB per kund (app/crm/objekt.py).';
