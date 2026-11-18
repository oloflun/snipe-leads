-- Snajp Bokföring — tredje agentens tabeller.
--
-- TRE saker som är avsiktliga och inte råkade bli så:
--
-- 1. ORIGINALFILEN LAGRAS INTE. Det finns ingen bytea-kolumn och ingen
--    storage-referens. Ett kvitto kan bära personnummer och lönebelopp, och
--    en fil vi inte har är en fil som inte kan läcka och som inte behöver
--    någon gallringsrutin. `sha256` är allt som blir kvar, och det räcker för
--    frågan "har vi sett det här kvittot förut?".
--    Ska originalet bevaras — bokföringslagen 7 kap. kräver det av den som FÖR
--    bokföringen — är det ett objektlager plus en retentionspolicy, och ett
--    eget beslut. Vi föreslår; kunden bokför och arkiverar i sitt eget system.
--
-- 2. BELOPP ÄR numeric(14,2), ALDRIG double precision. Se
--    app/bookkeeping/math.py: 0.1 + 0.2 blir inte 0.3 i binär flyttal, och en
--    öresdifferens i en periodrapport går inte att förklara för den som ska
--    skriva under den. `momssats` är numeric(5,4) — 0.2500 exakt, inte 0.25
--    approximerat.
--
-- 3. tenant_id OCH RLS FRÅN RAD ETT, inte som en eftertanke. Samma mönster som
--    ss_*-tabellerna, med 028:s nullif-skydd inbyggt: utan `nullif` kastar
--    policyn `invalid input syntax for type uuid: ""` så fort en skopad fråga
--    körts tidigare på samma poolade anslutning.
--
-- Idempotent enligt husets regel: kan köras om utan verkan.

-- ---------------------------------------------------------------------------
-- Underlaget: ett kvitto eller en faktura, med de fält avläsningen hittade.
-- ---------------------------------------------------------------------------
--
-- Nästan varje fält är nullbart MED FLIT. Ett underlag som verifieringsgrinden
-- fällt ska gå att spara med hål i — annars finns ingen granskningskö att
-- fylla, och det enda alternativet hade varit att fylla i en gissning.
-- Grinden, inte databasen, avgör om ett underlag får bli en periodrapport.

create table if not exists public.bk_underlag (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references public.ss_tenants(id) on delete cascade,
  sha256      text not null,
  filnamn     text not null,
  mimetyp     text not null,
  status      text not null
              check (status in ('granska_manuellt', 'klar', 'godkand')),
  datum       date,
  motpart     text,
  brutto      numeric(14,2),
  momssats    numeric(5,4),
  riktning    text check (riktning is null or riktning in ('intakt', 'kostnad')),
  kategori    text,
  anmarkning  text not null default '',
  created_at  timestamptz not null default now()
);

-- Periodrapporten frågar alltid "allt för den här kunden i det här
-- intervallet". Utan index är det en full scan varje gång rapporten öppnas.
create index if not exists bk_underlag_tenant_datum_idx
  on public.bk_underlag (tenant_id, datum);

-- Dubblettfrågan: samma kvitto uppladdat två gånger ska gå att upptäcka.
-- INTE unique — ett bolag kan ha två identiska kvitton på 39 kr från samma
-- automat samma dag, och en unik-spärr hade avvisat det andra som ett fel.
create index if not exists bk_underlag_tenant_sha_idx
  on public.bk_underlag (tenant_id, sha256);

-- ---------------------------------------------------------------------------
-- Verifikatet och dess konteringsrader — dubbel bokföring.
-- ---------------------------------------------------------------------------

create table if not exists public.bk_verifikat (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references public.ss_tenants(id) on delete cascade,
  underlag_id uuid not null references public.bk_underlag(id) on delete cascade,
  serie       text not null default 'A',
  nummer      text not null,
  datum       date not null,
  text        text not null default '',
  created_at  timestamptz not null default now()
);

create index if not exists bk_verifikat_tenant_datum_idx
  on public.bk_verifikat (tenant_id, datum, nummer);

create table if not exists public.bk_verifikat_rad (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references public.ss_tenants(id) on delete cascade,
  verifikat_id uuid not null references public.bk_verifikat(id) on delete cascade,
  konto        text not null,
  debet        numeric(14,2) not null default 0,
  kredit       numeric(14,2) not null default 0,
  text         text not null default ''
);

create index if not exists bk_verifikat_rad_verifikat_idx
  on public.bk_verifikat_rad (verifikat_id);

-- tenant_id ligger även på raden, inte bara på verifikatet. Det är avsiktlig
-- denormalisering: RLS-policyn nedan kan då grinda på raden själv, utan att
-- varje läsning måste joina uppåt. En policy som kräver en join är en policy
-- som går att kringgå med en fråga som inte joinar.

-- ---------------------------------------------------------------------------
-- Radsäkerhet
-- ---------------------------------------------------------------------------

alter table public.bk_underlag      enable row level security;
alter table public.bk_verifikat     enable row level security;
alter table public.bk_verifikat_rad enable row level security;

drop policy if exists bk_underlag_tenant_isolation on public.bk_underlag;
create policy bk_underlag_tenant_isolation on public.bk_underlag
  for all to snajp_app
  using (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  with check (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

drop policy if exists bk_verifikat_tenant_isolation on public.bk_verifikat;
create policy bk_verifikat_tenant_isolation on public.bk_verifikat
  for all to snajp_app
  using (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  with check (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

drop policy if exists bk_verifikat_rad_tenant_isolation on public.bk_verifikat_rad;
create policy bk_verifikat_rad_tenant_isolation on public.bk_verifikat_rad
  for all to snajp_app
  using (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  with check (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

-- ---------------------------------------------------------------------------
-- Rättigheter
-- ---------------------------------------------------------------------------
--
-- `delete` står MED från början. Läxan från 041: `snajp_app` hade
-- select/insert/update på arton tabeller sedan migration 009 och aldrig
-- delete, vilket upptäcktes först när en kodväg behövde den och svarade 500 i
-- drift. Sviten kör mot MemoryStorage, som inte har några rättigheter att
-- sakna, så tystnaden var total.

grant select, insert, update, delete on public.bk_underlag      to snajp_app;
grant select, insert, update, delete on public.bk_verifikat     to snajp_app;
grant select, insert, update, delete on public.bk_verifikat_rad to snajp_app;

-- ---------------------------------------------------------------------------
-- agent_runs släpper in bokföringsagenten
-- ---------------------------------------------------------------------------
--
-- Speglar `AGENT_RUN_TYPES` i app/storage/base.py, och de två MÅSTE ändras i
-- samma commit. Att de en gång glidit isär är hela skälet till att listan bor
-- i base.py och inte i respektive lagring: check-villkoret tillät bara
-- 'support' och 'leads', leads_agent.py skrev 'leads_research', MemoryStorage
-- hade inget villkor alls — och ingen enda leads-körning sparades på ett
-- halvår, med grön testsvit hela tiden.
--
-- tests/api/test_agent_run_types.py läser app/agent/*.py och fäller om ett
-- värde koden skriver saknas i listan.

alter table public.agent_runs drop constraint if exists agent_runs_agent_type_check;
alter table public.agent_runs add constraint agent_runs_agent_type_check
  check (agent_type in (
    'support', 'leads', 'leads_research', 'leads_outreach', 'demo', 'bookkeeping'
  ));

comment on table public.bk_underlag is
  'Utlästa fält ur ett kvitto/en faktura. Originalfilen lagras ALDRIG — bara '
  'sha256. Nullbara fält är granskningskön: grinden, inte databasen, avgör '
  'om ett underlag får bli en periodrapport.';

comment on table public.bk_verifikat_rad is
  'Konteringsrader, dubbel bokföring. Belopp i numeric(14,2) — aldrig float. '
  'tenant_id ligger även här så RLS-policyn slipper joina uppåt.';
