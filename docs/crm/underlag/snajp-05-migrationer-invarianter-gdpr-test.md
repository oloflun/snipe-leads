# Snajp CRM, underlag 05: migrationer, invarianter, GDPR och tester

Skrivet 2026-11-25 som läsunderlag för den som bygger Snajp CRM (kundsynk IN åt
Buddy först). Inget i repot är ändrat. Allt nedan är **läst** i arbetsträdet
`claude/snajp-crm-dd0d83` (grenen står på `859ba438`; `origin/development` står
på `9970d304` och har samma migrationskatalog) om det inte uttryckligen står
**Antagande** eller **Slutsats**. Radnummer gäller filerna som de ser ut i dag.

Kortversionen för den som bara läser en sak:

1. Nästa lediga migration är **153**. Filnamn `2026112XHHMMSS_153_<namn>.sql`,
   tidsstämpeln måste sortera efter `20261123110000_152_import_avtalsslut_extra.sql`.
   Ingen gren på `origin` har en 153 (kontrollerat med `git ls-tree` över alla
   fjärrgrenar 2026-11-25).
2. RLS slås på automatiskt för varje ny tabell (`0000_rls_auto_enable.sql`),
   men utan en `tenant_isolation`-policy ser `snajp_app` **noll rader** utan
   fel. Kopiera policymallen från migration 149 ordagrant (avsnitt 1.4).
3. `snajp_app` får automatiskt `select, insert, update` på nya tabeller, aldrig
   `delete`. `snajp_web` får sedan migration 126 **ingenting** automatiskt.
4. En ny tabell med en kolumn vars namn matchar
   `email|epost|e_post|mejl|mail|namn|name|telefon|phone|kontaktperson|kontaktnummer|adress|address`
   fäller `tests/test_gdpr_radera.py` tills den står i `scripts/gdpr_radera.py`.
5. En ny tabell med `on delete cascade` mot något gallringen raderar
   (`prospects`, `ss_tickets`, `ss_emails`, `ss_customers`, `contacts` m.fl.)
   fäller databastestet `test_varje_kaskad_fran_gallringen_raknas` tills den
   räknas i `public.gallring_kaskad` (mönster: migration 151).
6. Nya UI-kataloger (t.ex. `app/crm/`) granskas **inte** av INV-UI-001 och
   INV-COPY-001 förrän de läggs in i testernas listor. `components/crm/` finns
   redan i INV-COPY-001:s lista.

---

## 1. Mall för en ny migration

### 1.1 Filnamn och numrering (läst)

- Katalog: `db/migrations/`. 200 filer i dag.
- Form för alla nyare filer: `YYYYMMDDHHMMSS_NNN_snake_namn.sql`, t.ex.
  `20261122090000_149_iris_konversationer.sql`,
  `20261123110000_152_import_avtalsslut_extra.sql`. Äldre filer heter bara
  `NNN_namn.sql` (`000_base_schema.sql`, `009_snajp_app_role.sql`).
- Ordningen är **filnamnets sortering**: `scripts/railway_migrate.py:98-101`
  (`planned()`): först `railway/000_auth_compat.sql`, sedan
  `sorted(MIGRATIONS.glob("*.sql"))`.
- Liggaren nycklar på **hela filstammen**, inte på numret:
  `railway_migrate.py:146-148` jämför `version` = `p.stem` mot
  `supabase_migrations.schema_migrations.version`. Därför:
  - ett omdöpt filnamn är en ny migration som körs igen;
  - dubbla nummer har förekommit (`030`–`033`, se `MIGRATIONS-PENDING.md:83-100`)
    och är inget tekniskt fel för Railway, men undvik dem.
- Senaste fil: `20261123110000_152_import_avtalsslut_extra.sql`. **Nästa: 153**,
  med en tidsstämpel efter `20261123110000`, t.ex.
  `20261125090000_153_crm_grund.sql`. Två CRM-migrationer samma dag får olika
  klockslag (mönstret i 149–152 är jämna timmar).
- Liggaren heter `supabase_migrations.schema_migrations` med flit
  (`railway_migrate.py:12-14`), trots att Supabase är borttaget.

### 1.2 Hur filen körs (läst) och vad det kräver

- `railway_migrate.py:116-118`: `psycopg2.connect(...)`, `autocommit = False`.
- `railway_migrate.py:164-176`: **hela filen körs med ett enda
  `cur.execute(sql)`**, liggarraden skrivs i samma transaktion, sedan `commit`.
  Vid fel: `rollback`, `! <version> FAILED`, kedjan **stannar** (`break`).
- `railway_migrate.py:123`: `--apply` tar `pg_advisory_lock(hashtext('snajp:railway_migrate'))`,
  så att GitHub-jobbet och Railway-tjänsten `migrera` inte kör samtidigt.
- En fil utan annat än kommentarer registreras utan att köras
  (`railway_migrate.py:42-52, 154-163`).

Följder (**slutsats** av ovanstående):

- Skriv inte `begin;`/`commit;` i filen, och använd inte
  `create index concurrently` (kan inte köras i en transaktion).
- En migration är allt-eller-inget. En halvkörd fil finns inte.
- Samma kedja körs av `scripts/lokal_stack.py:153-200` (`kor_kedjan`), som
  importerar `planned()`, `LEDGER` och `_has_sql` därifrån.

### 1.3 Additiv och idempotent (läst)

Kravet står på tre ställen: `.github/workflows/migrera.yml:24-25`
("Migrationer ska vara additiva och idempotenta (create … if not exists, add
column if not exists), så att schemat får ligga före koden"), `CLAUDE.md`
(projektreglerna) och sista raden i varje färsk migration ("Additiv och
idempotent."). Mönstret i 149–152:

| Vad | Form |
|---|---|
| Tabell | `create table if not exists public.<t> (...)` |
| Kolumn | `alter table public.<t> add column if not exists <k> <typ>;` |
| Index | `create index if not exists <namn> on public.<t> (...);` |
| Check-villkor | `alter table ... drop constraint if exists <namn>;` följt av `add constraint <namn> check (...)` (149:41-44) |
| Policy | `drop policy if exists <namn> on public.<t>;` följt av `create policy ...` |
| Trigger | `drop trigger if exists <namn> on public.<t>;` följt av `create trigger ...` |
| Funktion | `create or replace function ...` med samma signatur |
| Rättighet | inne i `do $$ ... if exists (select 1 from pg_roles where rolname = '<roll>') then grant ...` |

"Additiv" betyder i praktiken: nya kolumner är nullbara eller har default, så
att gammal kod (som deployas efter migrationen eller rullas tillbaka) fortsätter
fungera. Exempel: 152 lägger `avtalsslut date`, `extra jsonb`, `importinfo jsonb`
utan default ("Null på gamla rader", 152:16). Ingen migration i 140–152 tar
bort en kolumn eller tabell.

### 1.4 RLS-mallen, ordagrant ur migration 149

`db/migrations/20261122090000_149_iris_konversationer.sql:46-90`, förkortad
bara i kolumnlistan:

```sql
create table if not exists public.lead_handelser (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references public.ss_tenants(id) on delete cascade,
  prospect_id uuid not null references public.prospects(id) on delete cascade,
  thread_id   uuid references public.outreach_threads(id) on delete cascade,
  ...
  created_at  timestamptz not null default now()
);

create index if not exists lead_handelser_trad_idx
  on public.lead_handelser (tenant_id, thread_id, created_at);

alter table public.lead_handelser enable row level security;
alter table public.lead_handelser force row level security;
drop policy if exists tenant_isolation on public.lead_handelser;
create policy tenant_isolation on public.lead_handelser
  using (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  with check (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    grant select, insert, update on table public.lead_handelser to snajp_app;
  end if;
  if exists (select 1 from pg_roles where rolname = 'synk_las') then
    grant select on table public.lead_handelser to synk_las;
  end if;
end $$;

-- Synken (111): ändringstid och raderingslogg, som de andra synkade tabellerna.
alter table public.lead_handelser
  add column if not exists synk_andrad_at timestamptz not null default now();
drop trigger if exists synk_markera on public.lead_handelser;
create trigger synk_markera before insert or update on public.lead_handelser
  for each row execute function public.synk_markera();
drop trigger if exists synk_radera on public.lead_handelser;
create trigger synk_radera after delete on public.lead_handelser
  for each row execute function public.synk_radera('id');

comment on table public.lead_handelser is '...';
```

Delarna och varför de krävs:

- **`nullif(current_setting('app.tenant_id', true), '')::uuid`** är obligatorisk.
  Utan `nullif` kastar `''::uuid` på en poolad anslutning efter första skopade
  transaktionen (`railway/000_auth_compat.sql:72-75`, `MIGRATIONS-PENDING.md:344-375`,
  `DEPLOY.md:598-610`). Vakter: `tests/test_rls_nullif_vakt.py` (statisk, letar
  efter rå `current_setting('app.tenant_id'` utan `nullif(` före) och
  `lokal_stack.py:214-223` (räknar policyer i `pg_policies` utan `NULLIF`).
- **`force row level security`**: tabellägaren omfattas också.
- **`app.tenant_id`** sätts av backenden per transaktion:
  `snajp-support/app/storage/postgres.py:289-298` (`_scoped`:
  `select set_config('app.tenant_id', $1, true)` inne i `conn.transaction()`).
- **`app.user_id`** är webbens motsvarighet: `auth.uid()` läser
  `nullif(current_setting('app.user_id', true), '')::uuid`
  (`railway/000_auth_compat.sql:77-83`). Dashboardens tabeller grindas på
  arbetsyta via `auth.uid()`, backendens på `app.tenant_id`
  (`DEPLOY.md:666-670`). **Beslut för CRM:et:** vilken av de två vägarna CRM-
  appen läser genom avgör vilken policyform tabellerna ska ha.
- **`synk_las`-grant, `synk_andrad_at`, `synk_markera`, `synk_radera`**: bara
  för tabeller som ska speglas main → development (se 4.3). En tabell som inte
  synkas behöver dem inte.
- **Tenant-FK** `references public.ss_tenants(id) on delete cascade` är mönstret.

### 1.5 Det som händer med en ny tabell utan att du gör något (läst)

| Vad | Var | Följd |
|---|---|---|
| RLS påslagen automatiskt | event-triggern `ensure_rls` / `public.rls_auto_enable()` i `db/migrations/0000_rls_auto_enable.sql` | En tabell utan policy ger `snajp_app` (nobypassrls) noll rader, utan felmeddelande. |
| `snajp_app` får `select, insert, update` | `009_snajp_app_role.sql:50` (`alter default privileges ... grant select, insert, update on tables to snajp_app`) | **Aldrig `delete`.** Raderar `postgres.py` ur tabellen krävs `grant delete ... to snajp_app` i en migration (vakt: `snajp-support/tests/invariants/test_delete_grants.py`). |
| `snajp_web` får ingenting | `126_snajp_web_minsta_rattighet.sql:26-28, 48-49` | Ska Next-appen (CRM-appen?) läsa tabellen direkt via `lib/db.ts` måste rättigheten ges uttryckligen OCH raden läggas i `TILLATET` i `snajp-support/tests/db/test_snajp_web_rattigheter.py` (testet fäller både för mycket och för lite, rad 123-160). |
| `synk_las` får ingenting | 122, 149:77-79 | Krävs bara för synkade tabeller. |

### 1.6 Kommentarshuvudet (läst, konvention)

Varje migration i 124–152 börjar med `-- NNN: <rubrik>` och ett resonemang:
varför, vad, vem som skriver, spegelns hantering och sist "Additiv och
idempotent." Projektregeln i `CLAUDE.md` kräver dessutom en rad i
`docs/BESLUT.md` för varje nytt beslut. `COMMENT ON TABLE` används för att
peka ut vilken modul som skriver och läser (149:92-94, 124:52-55).

### 1.7 Hur migrationen når databaserna (läst)

- Push till `development` eller `main` som rör `db/migrations/**` eller
  `railway/000_auth_compat.sql` kör kedjan mot samma miljö
  (`.github/workflows/migrera.yml:34-41, 63-125`). Jobbet kontrollerar efteråt
  att inget väntar (`migrera.yml:116-125`).
- Sedan 2026-11-23 kör även Railway-tjänsterna `migrera` (development) och
  `migrera-main` (main) samma skript; GitHub-flödet är reserv
  (`DEPLOY.md:90-120`). De delar det rådgivande låset.
- PR mot `main` får kontrollen `releasens migrationer` som fäller PR:en om
  development har okörda migrationer (`migrera.yml:143-200`).
- Det är "en ordning och ingen grind": Railway bygger koden parallellt och
  väntar inte (`migrera.yml:11-17`, `DEPLOY.md:127-131`). Därav kravet på
  additivitet: schemat får ligga före koden, aldrig efter.
- För hand: `python scripts/railway_migrate.py --env development` (torrkörning),
  sedan `--apply`. Aldrig via Supabase Management-API (`DEPLOY.md:150-152`).
- Verifiera som `snajp_web` med `app.user_id` satt eller som `snajp_app`, aldrig
  som `postgres` ("Tabellägaren kringgår RLS utan att något syns i en diff",
  `DEPLOY.md:154-155`).

---

## 2. Invarianterna ett CRM måste klara

### 2.1 Hur invarianterna fungerar (läst)

- `ARCHITECTURE_INVARIANTS.md:7-14`: en invariant utan test är ingen invariant.
  `tests/invariants/test_meta_invariants.py` parsar `### INV-...`-rubrikerna
  under `## Active` (regex `^### (INV-[A-Z]+-\d+) — `, rad 22), kräver en
  `Test:`-rad som pekar på en befintlig fil, och fäller på utgångna waivers i
  `waivers.yml`.
- Format för en ny invariant: `ARCHITECTURE_INVARIANTS.md:16-24`. Områdesdelen
  får inte innehålla siffror (därför INV-COPY, inte INV-I18N).
- Att bryta en aktiv invariant kräver en daterad, ägd, utgående post i
  `waivers.yml` (`ARCHITECTURE_INVARIANTS.md:1178-1181`).
- CI (`.github/workflows/verify.yml`) kör, i ett jobb:
  `pytest` i `snajp-support/` (rad 190-193, `testpaths = tests`),
  `pytest tests/invariants` i roten (rad 195-198),
  `tests/test_gdpr_radera.py`, `tests/test_sakerhetsbevakning.py`,
  `tests/test_railway_baslinje.py` (rad 208-213), databasstegen mot en
  Postgres 17 med pgvector där kedjan reses från noll (rad 218-251),
  `npm run type-check` (rad 259-263) och två docker-byggen.
- **Läst ur verify.yml, och värt att veta:** följande rottester körs INTE i CI:
  `tests/test_rls_nullif_vakt.py`, `tests/test_gallring_spegel.py`,
  `tests/test_railway_synk.py` och övriga `tests/test_*.py` utöver de tre
  ovan. Inte heller `npm test` (`node --test "lib/**/*.test.ts"`, `package.json:10`).
  Kör dem lokalt själv när du rör det de vaktar.
- Verify är detektion, inte grind: Railway bygger ändå (`verify.yml:15-17`).

### 2.2 Tabell: varje invariant, vad den kontrollerar mekaniskt, och om CRM:et berörs

"Skannar" anger vad testet faktiskt läser. "Berör" är min bedömning
(**slutsats**) för ett CRM med nya tabeller, endpoints, UI-text och
bakgrundsjobb.

#### Statiska tester i roten, `tests/invariants/` (körs i CI)

| Id / fil | Kontrollerar mekaniskt | Skannar | Berör CRM |
|---|---|---|---|
| INV-SEC-010 `test_inv_sec_010.py` | Varje `route.ts` under `app/api/` innehåller någon av `proxyAsTenant`, `requireSnajpTenant`, `getWorkspaceContext`, `getPlatformAdmin` (rad 79-84), eller står i `ANON_ALLOWLIST` med skäl som också står i filen (ordet "anonym"). Anonyma routes får inte innehålla `/api/keys`, `/api/tenants`, `/api/admin`. Proxy-matchern får inte utökas till `/api`. | `app/api/**/route.ts` (alla, `rglob`) | **Ja.** Varje ny Next-route i CRM-appen. Ligger CRM-appen utanför `app/api/` (egen app/eget repo) täcks den inte, och då finns ingen motsvarande grind. |
| INV-API-001 `test_inv_api_001.py` | Varje `await x.json()` under `app/`, `lib/`, `components/` går via `readJson`/`readJsonBody` (`lib/http/json.ts`) eller har `.catch()`. Varje `route.ts`/sida som innehåller `generateText`, `proxyWithApiKey`, `proxyToBackend`, `proxyAsTenant`, `listTenants`, `listRuns`, `listEvents`, `getRun` exporterar `maxDuration`. | `app/`, `lib/`, `components/` | **Ja.** Alla CRM-routes som proxar till backenden. |
| INV-UI-001 `test_inv_ui_001.py` | Förbjuder `kicker`, `uppercase`, `tracking-[0.06em]+`, kursiv Fraunces-rubrik och em-streck (`—`) i kod utanför kommentarer. | Bara listan `APPYTOR` (rad 25-52): `app/admin`, `app/dashboard`, `app/settings`, `components/{admin,dashboard,leads,settings,kvitton,snajp,shell}` och några enskilda filer. | **Ja, men bara om nya kataloger läggs in i `APPYTOR`.** `app/crm/` och `components/crm/` granskas i dag INTE. |
| INV-COPY-001 `test_inv_copy_001.py` | Ingen rad med å/ä/ö i en strängliteral eller JSX-text utan att vara halvan av ett `{ sv, en }`-par (`_PARAD`, rad 83) eller ett namnfält (`_NAMNFALT`, rad 93). Undantag per rad: `// inte-copy`. Skuldlistan `_SKULD_2026_10_02` är tom. | Listan `YTOR` (rad 46-71): `APPYTOR` plus `app/{demo,kvitton,support,leads,avregistrera,integritetspolicy,villkor,angerratt,cookies}`, **`components/crm`**, `components/{marketing,auth}` och sökordssidorna. | **Ja.** `components/crm/` (i dag bara `CrmDemo.tsx`) granskas redan. `app/crm/` gör det inte förrän den läggs in i `YTOR` (eller i `APPYTOR`, som `YTOR` ärver). Lägg till den i samma commit som katalogen skapas. |
| INV-SEC-013 `test_inv_sec_013.py` | Varje FastAPI-route under `/api/admin` och `/api/keys` har `deps.require_master_key` i beroendeträdet; ett riktigt anrop mot minneslagret ger en rad i åtkomstloggen utan frågesträng och nyckel. Undantag: `POST /api/admin/flytt/importera`. | Alla routes i `app.main:app` (importerar appen) | **Ja**, om CRM:et får adminvägar (t.ex. plattformsadminens vy över kundernas synkar). En CRM-route under `/api/admin` utan master-nyckel fäller. |
| INV-TENANT-001 `test_inv_tenant_001.py` | `lib/tenants/<slug>.ts` har `supportKeyEnv: "SNAJP_KEY_<SLUG>"`, och Next-sidans slug = backendens `_slugify`. | `lib/tenants/*.ts` | Bara om Buddy får en egen tenantfil. |
| INV-AUTH-001 `test_inv_auth_001.py` | `jwt`-callbacken i `lib/auth.ts` skriver inte `token.onboarded/workspaceId/role/addons/products/entitlement`. | `lib/auth.ts`, `proxy.ts` | **Ja**, om CRM-åtkomst blir ett tillval: lägg det aldrig i token, läs färskt. |
| INV-DATA-001 `test_inv_data_001.py` | `scripts/railway_seed_dev.py`: `TARGET_ENV = "development"` hårdkodat, ingen `--target`. | skriptet | Nej. |
| INV-DEPLOY-001 `test_inv_deploy_001.py` | api-tjänstens rootDirectory/Dockerfile, `agent-core` i byggkontexten, ingen `SKILL_SOURCE`. | `scripts/`, `.github/workflows/`, Dockerfile | Bara om CRM:et blir en ny Railway-tjänst. |
| INV-DEPLOY-002 `test_inv_deploy_002.py` | `scripts/railway_provision.py` har `ENVIRONMENTS` med utskriven gren per miljö; `railway-main` får inte förekomma. | provisioneringsskriptet | **Ja om CRM-appen blir en egen Railway-tjänst**: grenen ska stå i kod. |
| INV-PROC-001 `test_inv_proc_001.py` | PR-mallen har avsnitten "Säkerhet och dataskydd" och "AI-påverkan"; `pr-granskning.yml` fäller PR mot development utan ikryssat svar. | `.github/` | **Ja**, varje CRM-PR mot development. |
| INV-SKILL-005/006 | sha256 för `agent-core/skills/**` mot manifestet; ändring kräver `VENDOR-BUMP:`-trailer. | `agent-core/` | Nej (rör inte skills). |
| INV-SEC-009, INV-SEC-011, INV-SEC-012, INV-SEO-001 | SOUL i användarposition; vybytet till demo kräver plattformsadmin; KB-text wrappad; sökordssidor. | respektive filer | Nej, utom om CRM-text matas till en modell (då gäller INV-SEC-003/009-principen: kundtext i användarposition, wrappad). |
| `test_inga_reservlosenord.py` | Inget skript i `scripts/` har `QA_ADMIN_LOSEN`/`AGENTSAJT_LOSEN` med en strängliteral som reserv. | `scripts/*` | Ja för nya QA-skript. |
| `test_render_avvecklad.py` | Inga Render-spår i `scripts/` och `.github/`. | skript och flöden | Nej. |

#### Backendtester, `snajp-support/tests/invariants/` (körs av `pytest` i `snajp-support/`)

| Id / fil | Kontrollerar mekaniskt | Berör CRM |
|---|---|---|
| INV-STORE-001 `test_inv_store_001.py` | Varje publik metod i protokollet `app/storage/base.Storage` finns i både `MemoryStorage` och `PostgresStorage` med samma parameternamn, ordning och default-värden. | **Ja, alltid.** Varje ny lagringsmetod för CRM:et (t.ex. `upsert_crm_bolag`) måste finnas i `base.py`, `memory.py` och `postgres.py` med identisk signatur. Värdemängder (statusar) ska bo i `base.py` och anropas av båda (mönster: `AGENT_RUN_TYPES`, `BK_STATUSAR`). |
| `test_delete_grants.py` | Varje tabell i `delete from <t>` i `app/storage/postgres.py` har `grant ... delete ... on <t>` i någon migration. | **Ja.** |
| `test_inv_driftavbild.py` | Varje lokal modul som ett skript i `railway/Dockerfile.drift` importerar kopieras och släpps igenom av `.dockerignore`. | Ja, om synken eller ett nytt driftjobb för CRM:et körs i driftavbilden. |
| INV-DATA-003 `test_inv_data_003.py` | Spegelskriptet pekar bara mot development; `/api/admin/flytt/importera` bakom HMAC; bara `admin_flytt` skriver `importerad_fran`; synken synkar aldrig provkörningar; `skickas_har(item, spegel)` minst två gånger och `if tvavags(spegel):` i `scheduler.py`, `tvavags(` i `email_pipeline/poller.py`. | **Ja för bakgrundsjobb.** Mönstret: jobb som läser externa källor (inkorgar, uppföljningar) körs bara i main; development är en spegel (`scheduler.py:838-844`). En kundsynk IN från Buddys API bör följa samma regel, annars blir varje import två (se risker). |
| INV-DATA-004/006/007 | Uppstarten fälls utan Vertex-servicekonto/EU-region där data är riktig; personnummer maskeras före embeddings och klassare; Googles sökverktyg bara i `discovery`. | Ja, om CRM-data går till en modell (sammanfattning, matchning). Ingen ny modellväg utanför `agent/llm.py`. |
| INV-DATA-005 `test_inv_data_005.py` | Statisk halva av gallringen: `suppressions`, `bk_underlag`, `bk_verifikat`, `bk_verifikat_rad`, `kvitto_mejl_lasta` raderas aldrig i en gallringsmigration; `update public.suppressions set contact_id = null` före `delete from public.contacts`; `'ingen_policy'` finns; ingen migration gör `insert into ss_gallringspolicy`; dygnsspärr och spegelkontroll. | Ja, om CRM:et ska gallras (avsnitt 3.4). |
| INV-DATA-008 `test_inv_data_008.py` | Synken skriver bara till development, kontrollerar anslutningarna. | Ja om CRM-tabeller läggs i `SYNK`. |
| INV-REDIS-001 `test_inv_redis_001.py` | Alla Redis-nycklar byggs med `app/redisnycklar.nyckel()`. | **Ja** om synkjobbet använder Redis (kö, lås, cache). |
| INV-JOB-001/002/003 | Chattjobb idempotenta vid återtag; leadsjobb läser `leads_job_ledger` först; körningens tillstånd skrivs i liggaren efter varje steg. | **Ja i princip** för synkjobbet: Postgres är sanningen, Redis-TTL är aldrig enda platsen (jfr projektregeln om att följa flödet). |
| INV-AVTAL-001 `test_inv_avtal_001.py` | `ss_tenants.kraver_avtal` default true; ny tenant utan värde vägras av `app/avtalsgrind.py` tills `ss_customer_details.avtal_signerat` har datum. | **Ja.** Buddy får ingen trafik utan registrerat avtal. Avtalsgrinden anropas i dag från `chat.py`, `triage.py`, `email_pipeline/processor.py`, `kanaler/mottagning.py`. En ny publik/inkommande CRM-väg bör fråga `avtal_saknas` på samma sätt (**slutsats**). |
| INV-AI-001, INV-CACHE-001, INV-ESC-001, INV-LEADS-* , INV-GROUND-* | Supportsvarets AI-upplysning, svarscache, överlämning, Iris-grindar. | Indirekt: Iris-uteslutningen av befintliga kunder rör Iris-körningen; testerna i `test_inv_leads_*` måste fortfarande gå. |
| `test_inv_tvafaktor_inrullning.py`, `test_korning_fortsatter_till_malet.py` | Tvåfaktor och körningsmålet. | Nej. |

#### Backendtester utanför `tests/invariants/` som CRM:et träffar

| Test | Kontrollerar | Berör CRM |
|---|---|---|
| `snajp-support/tests/agent/test_tool_schema_security.py` (INV-SEC-002) | Inget `@function_tool` exponerar `tenant_id`/`workspace_id`/`tenant`/`workspace`. | Ja, om CRM-verktyg ges till en agent. |
| `snajp-support/tests/leads/test_webbpool.py` (INV-SEC-008) | Webbpoolen bär bara `POOLFALT`, ingen kontakt eller källkund. | Ja: CRM-data får aldrig läcka in i webbpoolen. |
| `CLAUDE.md`, webbbedömningen | Inget test, men en regel: webbrevision, webbnivå, betyg m.m. syns bara för plattformsadmin, Umeå Webdesign och Alunix. `app/api/admin_listor.py:LISTRADSFALT` saknar dem med flit. | **Ja.** Visar CRM:ets bolagskort leadsfält, grinda webbfälten i samma commit. |

#### Databastester (körs i CI mot en tom Postgres; hoppas över lokalt utan DSN)

| Test | Kontrollerar | Berör CRM |
|---|---|---|
| `tests/db/test_rls_isolation.py` (INV-SEC-001) | Som `snajp_app` scopad till fel tenant ger en id-läsning av ett annat tenants ärende 0 rader. Testar `ss_tickets`, inte alla tabeller. | Skriv motsvarande för CRM-tabellerna; det befintliga testet täcker dem inte. |
| `tests/db/test_snajp_web_rattigheter.py` | `snajp_web` har exakt `TILLATET` (rad 123-136); nya tabeller ger inte webben rätt (rad 138-160); varje SQL-sats i filer som importerar `lib/db.ts` körs som `snajp_web` med EXPLAIN (rad 250-266). | **Ja** om CRM-appen läser direkt via `lib/db.ts`. |
| `tests/db/test_gallring.py::test_varje_kaskad_fran_gallringen_raknas` (rad 1192-1232) | Läser `pg_constraint` (`confdeltype = 'c'`) och kräver att varje tabell som kaskadraderas från en tabell `gallra_tenant` raderar ur står i `gallring_kaskad` eller är en egen kategori. Undantag bara `(suppressions, contacts)`. | **Ja.** En CRM-tabell med `on delete cascade` mot `prospects`, `contacts`, `ss_customers`, `ss_tickets` eller `ss_emails` fäller tills `gallring_kaskad` får en rad (151 är mallen). |
| `tests/db/test_gdpr_radera_db.py` | Rättighetsskriptet söker, lämnar ut och raderar mot hela schemat; begränsningen speglas. | Ja, om CRM-tabellerna läggs i skriptet (de ska). |
| `tests/db/test_adminlogg.py` | Åtkomstloggens funktioner. | Ja för adminvägar. |

---

## 3. GDPR-maskineriet som finns

### 3.1 Översikt (läst)

| Rättighet / plikt | Mekanism | Var |
|---|---|---|
| Tillgång, registerutdrag (art. 15) | `scripts/gdpr_radera.py --env railway-main --epost X [--export] [--fritext]` | `scripts/gdpr_radera.py:22-31, 480-485` |
| Radering (art. 17) | samma skript med `--radera` (bekräftas genom att skriva adressen igen, `_bekrafta`, rad 314-323) | `gdpr_radera.py:494-547` |
| Begränsning (art. 18) | tabellen `public.behandlingsbegransningar` (migration 124), `--begransa SKÄL` / `--hav-begransning SKÄL` | `db/migrations/20261118140000_124_behandlingsbegransning.sql`, `gdpr_radera.py:349-404` |
| Lagringsminimering (art. 5.1 e) | `public.gallra_tenant(uuid, boolean, integer, text)` och `public.gallra_alla` (119, senast ersatt i 147), policy i `ss_gallringspolicy`, logg i `ss_gallringslogg`, dygnsspärr `ss_gallringskorning` | migration 119, 133–147, 151; `snajp-support/app/jobs/gallring.py`; `scripts/gallra.py` |
| "Behandlingslogg": senaste behandling per rad | kolumnen `behandlad_at` + triggern `gallring_behandlad` (141, 142) | `db/migrations/20261119220000_142_varje_andring_ar_behandling.sql:41-75` |
| Åtkomstlogg för admin (art. 32) | `audit_logs` via `logga_adminatkomst` (123), anropad av `deps.require_master_key` → `adminlogg.logga_masteranrop` | migration 123; INV-SEC-013 |
| Art. 14-information i kallmejl | `snajp-support/app/leads/utskicksfot.py` | `docs/JURIDIK_ATGARDER.md:25` |
| Spärrlista | `suppressions`, raderas aldrig | `gdpr_radera.py:126-132`; INV-DATA-005 |

Det finns **inget API eller UI** för registerutdrag, radering eller begränsning
i dag: allt går genom skriptet, kört av ägaren mot `railway-main`
(`gdpr_radera.py:4-12`). `docs/JURIDIK_ATGARDER.md:71` (punkt 18) säger att
verktyget inte täckte tabeller efter augusti och aldrig provkörts skarpt;
`JURIDIK_ATGARDER.md:106-107` att det inte körts skarpt.

### 3.2 Rättighetsskriptet: exakt vad en ny tabell måste anslutas till

`scripts/gdpr_radera.py` har fem listor. Nyckeln är alltid **e-postadressen**
(skriptet tar `--epost`, rad 414); det finns ingen sökning på telefon,
personnummer eller namn.

| Lista | Rader | Betydelse | Form på en post |
|---|---|---|---|
| `TABELLER` | 112-123 | Raderas med `--radera`, **i listans ordning** (FK utan kaskad kräver att barnet raderas först). | `("tabell", "kolumn_eller_villkor_med_%s", "beskrivning")` |
| `BEHALLS` | 126-132 | Raderas aldrig (`suppressions`, `bk_underlag`, `behandlingsbegransningar`). | samma |
| `KASKAD` | 137-162 | Försvinner i kaskaden från en förälder i `TABELLER`; räknas och lämnas ut. | `("barn", "villkor_med_%s", "förälder")` |
| `MANUELLT` | 167-179 | Hittas och lämnas ut, raderas inte. | `("tabell", "kolumn_eller_villkor", "beskrivning")` |
| `FRITEXT` | 183-208 | Söks i löptext med `--fritext`, raderas aldrig. | `("tabell", "sql-uttryck")` |
| `NAMNS_MANUELLT` | 213-216 | Nämns i svaret, söks inte. | `("tabell", "beskrivning")` |
| `KOPIOR_SOM_INTE_NAS` | 220-227 | Redis, development-spegeln, `synk_kopia_*`, Railways säkerhetskopior, gamla Supabase. | text |

Hjälpvillkoren som andra poster bygger på: `_MEJL`, `_KUND`, `_KONTAKT`,
`_PROSPEKT`, `_TRAD`, `_ARENDE` (rad 92-100). En CRM-person som nås via
`prospects` eller `ss_customers` kan alltså uttryckas som en `KASKAD`-post med
`f"prospect_id in ({_PROSPEKT})"`.

Grinden som tvingar fram det: **`tests/test_gdpr_radera.py`** (körs i CI,
`verify.yml:208-213`). Den läser alla migrationer utan databas och fäller:

- `test_varje_personuppgiftskolumn_ar_hanterad` (rad 143-155): varje kolumn
  vars namn matchar `PERSONUPPGIFT` (rad 108-110,
  `email|epost|e_post|mejl|mail|namn|name|telefon|phone|kontaktperson|kontaktnummer|adress|address`)
  i en tabell som inte står i `TABELLER`/`BEHALLS`/`MANUELLT`/`KASKAD` och inte
  i `UNDANTAG` (rad 33-53, med motivering). Regexen söker delsträngar, så
  `fornamn`, `efternamn`, `foretagsnamn` och `kontakt_email` fångas.
  `personnummer`, `orgnr`, `titel`, `roll` och `mobil` fångas INTE. Lägg ändå
  personnummer- och mobilkolumner i skriptet (**slutsats**).
- `test_tabellerna_i_forteckningen_finns_i_schemat` (rad 157-166): varje
  tabell och enkel kolumn i listorna finns i migrationerna.
- `test_inget_som_behalls_forsvinner_i_en_kaskad` (rad 183-186),
  `test_kaskadraderna_foljer_verkligen_med` (rad 189-193): en `KASKAD`-post
  måste verkligen kaskadera från en förälder i `TABELLER`.
- `test_raderingsordningen_haller_for_framande_nycklar` (rad 196-207): en FK
  utan kaskad in i något som raderas kräver att barnet raderas tidigare.
- `test_manuella_beslut_raderas_inte_av_skriptet` (rad 210-214): ingen radering
  får kaskadera in i en `MANUELLT`-tabell.
- `test_undantagen_ar_inte_inaktuella` (rad 217-220).

Parsern är regex på migrationstexten (`_schema`, rad 69-97): den förstår
`create table`, `alter table ... add column`, `rename to`, `drop table` och FK:er
med `references <t>(...) on delete <regel>`. Skriv därför FK:er på samma rad som
kolumnen, i den formen, annars ser testet dem inte.

**Gör så här för en ny CRM-tabell med personuppgifter (slutsats ur ovan):**

1. Har tabellen en egen mejlkolumn: lägg den i `TABELLER` (raderas) eller
   `MANUELLT` (beslut per fall), på rätt plats i ordningen.
2. Kaskaderar den från `prospects`/`ss_customers`/`contacts`: lägg den i
   `KASKAD` med förälderns hjälpvillkor.
3. Har den fritext som kan bära adressen (anteckningar, aktivitetstext):
   lägg den i `FRITEXT`.
4. Är en matchande kolumn inte en personuppgift (t.ex. `crm_bolag.namn`,
   bolagsnamnet): lägg den i `UNDANTAG` i testet med motivering.
5. Se till att ingen radering kaskaderar in i `suppressions` eller en
   `MANUELLT`-tabell.

### 3.3 Begränsning av behandling (art. 18): vad nya kodvägar måste fråga

- Tabell `public.behandlingsbegransningar` (124:39-47): `id`, `email`, `skal`,
  `begard_at`, `havd_at`, `havd_skal`, `created_at`. Aktiv = `havd_at is null`.
  Unikt index på `lower(email) where havd_at is null` (124:50-51).
- **Global, utan `tenant_id`**: begäran gäller personen hos alla kunder
  (124:24-29). Bara ägarrollen skriver; `snajp_app` och `snajp_web` får bara
  `select` (124:57-75).
- Läses i appen via `storage.list_begransade(tenant_id)` (`app/storage/base.py:878`).
- Används i dag på tre ställen, alla fail-closed:
  - sändspärren: `snajp-support/app/leads/scheduler.py:121-141`
    (`begransning_okand` → köas om; `begransad_behandling` → blockeras);
  - inkommande mejl: `app/email_pipeline/processor.py:560-568` (sparas, går
    till Att hantera utan AI);
  - supportsvar: `app/email_pipeline/sender.py:86-141` (`_vagra_begransad`).
- Gallringen respekterar den (144) och spegeln väntar på en färsk synk av den
  (147).
- Speglas av `gdpr_radera.py` till development (`_spegla_till_development`,
  rad 381-404) och av synken.

**För CRM:et (slutsats):** varje ny väg som behandlar en person automatiskt
(utskick, AI-sammanfattning, berikning, export till kundens system via
tvåvägs-API) ska fråga `list_begransade` och vägra fail-closed. Kundsynken IN
får lagra (lagring är tillåten under begränsning) men bör inte trigga
automatisk behandling av en begränsad adress.

### 3.4 Gallringen: vad en ny tabell måste anslutas till

Läst:

- Bara databasfunktionerna raderar; appen raderar aldrig själv
  (`ARCHITECTURE_INVARIANTS.md:1019-1057`).
- Utan rad i `ss_gallringspolicy` gallras kunden aldrig (`'ingen_policy'`);
  ingen migration får skriva en policy (INV-DATA-005-testet).
- Jobbet `app/jobs/gallring.py` är AV som standard (`GALLRING_AKTIV`), körs
  högst en gång per svenskt dygn, tak `GALLRING_TAK`, logg läsbar via
  `GET /api/admin/gallring` och `GET /api/admin/tenants/{tenant_id}/gallring`
  (`app/api/admin_gallring.py:25, 45`).
- `gallra_tenant` (senaste versionen i 147) raderar ur exakt dessa tabeller
  (`grep "delete from public"` i 147): `agent_evals`, `agent_suggestions`,
  `contacts`, `customer_memory`, `generated_emails`, `lead_list_items`,
  `lead_lists`, `leads_job_ledger`, `leads_sidcache`, `platform_events`,
  `prospects`, `saljlista`, `ss_avregistreringslankar`,
  `ss_channel_inbound_seen`, `ss_customers`, `ss_emails`, `ss_tickets`. Allt
  annat försvinner i kaskad och räknas i `gallring_kaskad` (151).
- Urvalet per kategori räknar senaste aktivitet ur bl.a. `behandlad_at`, och
  triggern `gallring_behandlad` (142:41-75) sätter `behandlad_at = now()` vid
  varje UPDATE som faktiskt ändrar raden, på 25 tabeller (lista 142:58-64).

Vad en ny CRM-tabell kräver, beroende på hur den hänger ihop (slutsats):

| Fall | Krav |
|---|---|
| Barn med `on delete cascade` till en tabell gallringen raderar (t.ex. `crm_aktivitet.prospect_id → prospects`) | Ny migration som `create or replace function public.gallring_kaskad(...)` med en rad till, som 151. Annars fäller `test_varje_kaskad_fran_gallringen_raknas`. Fundera också på om barnets aktivitet ska skydda föräldern (151:12-17 resonerar om varför `lead_handelser` inte gör det). |
| Egen rot med bara `tenant_id`-FK (t.ex. `crm_bolag`, `crm_personer`) | **Gallras inte alls** av dagens funktion. Integritetspolicyn lovar 24 månader "i alla kategorier" (`ARCHITECTURE_INVARIANTS.md:1051-1052`). Antingen en ny kategori i `gallra_tenant` (en 500–600 raders `create or replace`, med två varv, radlås, spegelvillkor, begränsningsundantag, takräkning och `behandlad_at`) eller ett uttryckligt beslut i `docs/BESLUT.md` om att CRM-data har en annan lagringsgrund (kundens eget register, som kunden ansvarar för). **Öppen fråga till Anton.** |
| Tabellen ska räkna som aktivitet | `behandlad_at timestamptz` utan default + triggern `gallring_behandlad` (form: 142:66-74). |

Fälla som står i invarianten: "ingen återkommande teknisk skrivning får röra
gamla rader i de tabellerna, för då gallras de aldrig"
(`ARCHITECTURE_INVARIANTS.md:1044-1046`). En kundsynk som var tionde minut
skriver t.ex. `synkad_at = now()` på `prospects` eller `contacts` bumpar
`behandlad_at` varje gång och gör att raderna aldrig gallras. Triggern bumpar
bara när `to_jsonb(new)` skiljer sig från `to_jsonb(old)` (142:45-49), så en
idempotent upsert som inte ändrar något är ofarlig; en tidsstämpel per synk är
det inte. Lägg synkens tidsstämplar i en egen tabell.

### 3.5 Spegeln och persondata

- Development är en spegel av main med riktig kunddata (`DEPLOY.md:193-215`).
  Synken (`scripts/railway_synk.py`, `SYNK` på rad 118-149) för över de listade
  tabellerna; provrader (`origin in ('test','example')`, `is_test`) synkas aldrig.
- Ska en CRM-tabell synkas: lägg den i `SYNK` med provradsvillkor, ge
  `synk_las` select, lägg `synk_andrad_at` och triggrarna `synk_markera`/
  `synk_radera` (149:72-90), och uppdatera `gallra_tenant`:s spegelvillkor
  (`tests/test_gallring_spegel.py:48-80` håller villkoren lika med `SYNK`;
  körs inte i CI). Ett kaskadbarn utanför `SYNK` till en förälder i `SYNK`
  måste städas i `gallra_spegelns_foraldralosa`
  (`test_gallring_spegel.py:150-162`).
- Ska den inte synkas: development gallrar den själv (133), och raderingar
  i main når den inte (`gdpr_radera.py:222-223`).

### 3.6 Avtal och förteckningar (läst)

- Underbiträden står på fyra ställen: `lib/bolag.ts`, `docs/pub-avtal.md`
  Bilaga 3, `docs/pilotavtal.md` Bilaga 1, `docs/registerforteckning.md`; en
  ny leverantör läggs in på alla fyra i samma ändring
  (`docs/JURIDIK_ATGARDER.md:94-96`).
- "Kanaler och CRM som kunden slår på saknas i PUB-avtalet (blir B när en
  kund aktiverar en kanal)" (`JURIDIK_ATGARDER.md:80`, punkt 22). Buddys
  kundsynk gör den punkten blockerande (**slutsats**).
- Incidentrutinen: `INCIDENT_RESPONSE.md`. 72-timmarsfristen räknas från när
  någon blir medveten; som biträde underrättar vi kunden "utan onödigt
  dröjsmål" (rad 60-71). En läckt API-nyckel roteras först (rad 34-41) – gäller
  också Buddys inkommande API-nyckel.

---

## 4. Köra tester lokalt utan databas, och `lokal_stack.py`

### 4.1 Backendens svit (läst)

- Katalog `snajp-support/`, `pytest.ini`: `testpaths = tests`,
  `norecursedirs = backend frontend databas .venv .git __pycache__`.
- `snajp-support/tests/conftest.py` (autouse) sätter bl.a. `DATABASE_URL`,
  `REDIS_URL`, alla LLM-nycklar, IMAP och leadskällorna till tom sträng. Med
  tom `DATABASE_URL` väljer `app/main.py:165` `MemoryStorage()`. Sviten är
  därmed hermetisk och kör mot minneslagret.
- Avgränsade körningar, från `snajp-support/` (ingen databas, ingen tung process):

  ```bash
  python -m pytest tests/invariants/test_inv_store_001.py -q
  python -m pytest tests/invariants/test_delete_grants.py -q
  python -m pytest tests/invariants -q
  python -m pytest tests/leads/test_<modul>.py -q
  ```

- Från repo-roten:

  ```bash
  python -m pytest tests/invariants/test_inv_copy_001.py tests/invariants/test_inv_ui_001.py -q
  python -m pytest tests/invariants/test_inv_sec_010.py tests/invariants/test_inv_api_001.py -q
  python -m pytest tests/test_gdpr_radera.py tests/test_rls_nullif_vakt.py -q
  ```

  `test_inv_sec_013.py` importerar `app.main` och behöver backendens beroenden
  (`snajp-support/requirements.txt`). `test_gdpr_radera.py` importerar
  `scripts/gdpr_radera.py`, som importerar `psycopg2`
  (`verify.yml:211-212` installerar `psycopg2-binary` före).
- Databastesterna (`tests/db/*`) hoppas över utan `GALLRING_TEST_DSN`,
  `GALLRING_TEST_APP_DSN` (och `GALLRING_TEST_WEB_DSN`), och vägrar allt annat
  än `localhost`/`127.0.0.1`/`::1` och en databas med spegelmarkör
  (`tests/db/test_gallring.py:29-35, 42-56`).
- `npm test` = `node --test "lib/**/*.test.ts"` (`package.json:10`); kör en fil:
  `node --test lib/leads/konversation.test.ts`.
- **Antagande:** det finns ingen `.venv` i det här arbetsträdet eller i
  huvudcheckouten (`snajp-support/.venv` saknas, kontrollerat). Använd den
  Python som har `snajp-support/requirements.txt` installerat.
- Minne: maskinen har 16 GB; kör inte hela sviten, `tsc` eller `next dev`
  parallellt (användarens globala regler, och projektets minnesanteckning om
  avgränsad tsc).

### 4.2 `scripts/lokal_stack.py` (läst)

Hela stacken mot en **tom lokal** Postgres, aldrig mot development (som bär
riktig kunddata).

| Kommando | Gör |
|---|---|
| `python scripts/lokal_stack.py --kontrollera` | Kollar Postgres på `LOKAL_DSN` (default `postgresql://postgres:localdev@127.0.0.1:5432/railway`, rad 57), att `pgvector` finns, att `node_modules` finns. Ändrar inget. |
| `python scripts/lokal_stack.py --apply` | Kör migrationskedjan (`kor_kedjan`, rad 153-226), sätter lösenord på `snajp_web` (`localweb`) och `snajp_app` (`localapp`), räknar policyer utan `NULLIF`, skapar plattformsadmin via `admin_cleanup.py`, en testkund (`kund@example.com`) kopplad till `livrustning`, seedar `agent_runs`/`platform_events`, skriver `.env.local` om den saknas, och utfärdar `SNAJP_KEY_SNAJP`/`SNAJP_KEY_LIVRUSTNING` om backenden svarar på `127.0.0.1:8000`. |
| `--apply --nollstall` | River databasen först (terminerar anslutningar, `drop database`). |

Därefter (rad 451-474): backenden med
`cd snajp-support && python lokal_stack_backend.py` (sätter `DATABASE_URL` till
`snajp_app:localapp@127.0.0.1:5432/railway`, master-nyckeln
`snajp_master_local_test_key`, tom `REDIS_URL`), webben med
`npm run build && npm start`. Kör skriptet igen efter att backenden startat
för att få tenantnycklarna.

Databastesterna lokalt efter `--apply` (samma DSN:er som CI, `verify.yml:221-224`):

```bash
cd snajp-support
GALLRING_TEST_DSN=postgresql://postgres:localdev@127.0.0.1:5432/railway \
GALLRING_TEST_APP_DSN=postgresql://snajp_app:localapp@127.0.0.1:5432/railway \
GALLRING_TEST_WEB_DSN=postgresql://snajp_web:localweb@127.0.0.1:5432/railway \
python -m pytest tests/db/test_gallring.py -k kaskad -rs
```

Samma kedja är i sig testet att en ny migration går att resa från noll: CI
gör exakt `lokal_stack.kor_kedjan()` (`verify.yml:218-226`).

Synliga ändringar ska renderas i en förhandsvisning under
`app/forhandsvisning/` (anropen besvaras i webbläsaren, ingen databas) och ses
på desktop och mobil före commit (projektregel i `CLAUDE.md`).

---

## 5. Fällor som dokumenten nämner

| Fälla | Källa | Vad man gör |
|---|---|---|
| **psycopg2 utan autocommit håller lås** ("idle in transaction") under långa skript | `HANDOFF-2026-10-08-CRM-FLODE.md:58-59` | Släpp transaktionen (commit/rollback) före långa nätverkssteg. Gäller varje skript i `scripts/` som läser och sedan anropar ett API (t.ex. en engångsimport åt Buddy). `railway_migrate.py` håller medvetet ett sessionslås över hela kedjan. |
| **Migration före push** när koden skriver nya kolumner | `HANDOFF-2026-10-08-CRM-FLODE.md:57`; `MIGRATIONS-PENDING.md:3-10` (080 skulle köras innan koden deployades) | Sedan 2026-11-16 körs migrationerna av pushen själv, men parallellt med Railway-bygget. Lägg migrationen i samma eller en tidigare push än koden, och kontrollera att jobbet `migrera` (eller Railway-tjänsten `migrera`) blev grönt. asyncpg:s statement-cache kan kasta `InvalidCachedStatementError` en gång efter en schemaändring; poolen töms och svaret blir 503 (`postgres.py:299-306`). |
| **CRLF** | `STATUS.md:1040-1043`; `HANDOFF-2026-10-12-UTKASTKEDJAN.md:154-157`; användarens minnesanteckning `python-write-text-crlf` | Repot är LF med `core.autocrlf=false`. Pythons `open(...,'w')`/`Path.write_text` på Windows skriver CRLF och gör hela filen till en diff. Skriv med `write_bytes(t.encode("utf-8"))` eller med Edit/Write. Jämför `git diff --stat` med `git diff --stat -w`. `.gitattributes` sätter `-text` på `agent-core/**` (sha256-hashade) och `lib/leads/fixtures/**`. |
| **Heredoc förstör escapes** | `HANDOFF-2026-10-12-UTKASTKEDJAN.md:153-155`; `HANDOFF-2026-10-02-LEADS-SUITE-DRIFT.md:183-184` | `\\b` blev 0x08. Skriv skript till en fil i scratchpad eller använd Edit/Write. |
| **Två sessioner i samma arbetsträd** | `HANDOFF-2026-10-08-CRM-FLODE.md:52-55`; `HANDOFF-2026-10-09-SKALA-UTSKICK-SNABBHET.md:3`; `GOALS.md:226-228` | Committa aldrig delade filer med `git apply --unidiff-zero` av utplockade hunkar (b4b29a3 blev oparsbar). Kör `ast.parse` på `git show HEAD:<fil>` före push, eller låt en session committa hela filen. Sebbe pushar flera gånger per dag: `git fetch` och `git merge --ff-only origin/development` först (CLAUDE.md). Aldrig bar `git stash` (delad stack mellan arbetsträd). |
| **Verifiera som `postgres`** | `DEPLOY.md:154-155`; `MIGRATIONS-PENDING.md:38-41` | Ägaren kringgår RLS; en saknad policy syns inte. Pröva som `snajp_app` med `app.tenant_id` eller `snajp_web` med `app.user_id`. |
| **Saknad DELETE-grant** | `MIGRATIONS-PENDING.md:292-310`; `test_delete_grants.py` | Sviten kör mot `MemoryStorage` och ser det aldrig; drift ger 500 `permission denied`. |
| **MemoryStorage ljuger** | INV-STORE-001 (`ARCHITECTURE_INVARIANTS.md:558-575`) | `agent_runs` avvisade leadskörningar i ett halvår med grön svit. Lägg samma villkor (check, unikhet) i minneslagret som i Postgres, och värdemängderna i `base.py`. |
| **Dubbla versionsnummer / Management-API** | `MIGRATIONS-PENDING.md:83-100`; `DEPLOY.md:150-152, 685-714` | Applicera bara via `railway_migrate.py`, byt aldrig namn på en körd fil. |
| **Webbens nya tabeller** | `126:26-28` | `snajp_web` får inget automatiskt; ge rättighet + rad i `TILLATET`. |
| **Glömd NULLIF** | `tests/test_rls_nullif_vakt.py` (tio migrationer behövde lagas i efterhand) | Använd mallen ordagrant. |
| **Bakgrundsjobb i spegeln** | `scheduler.py:838-844`; INV-DATA-003 | Jobb som läser externa källor körs bara i main; annars dubbleras allt. |
| **Hemligheter** | `CLAUDE.md` (läckagespärr), `test_inga_reservlosenord.py`, gitleaks i `verify.yml:96-110` | Läs ur `.env.deploy`, skriv aldrig ut. Ingen nyckelkolumn i databasen (Roadmap INV-SEC-006, `ARCHITECTURE_INVARIANTS.md:1163`). Buddys API-nyckel: samma mönster som `ss_api_keys` (sha256 av nyckeln). |
| **Minnesbrist** | användarens globala regler; projektets minnesanteckning | Under ~4 GB ledigt: en lokal server åt gången, avgränsad tsc. |

---

## 6. Risker och öppna frågor (slutsatser, inte lästa beslut)

1. **Gallringen av CRM-data saknar beslut.** Egna rot-tabeller gallras inte
   av dagens `gallra_tenant`. Antingen en ny kategori (stort ingrepp i en
   funktion som granskats i 15 Codex-rundor) eller ett beslut om annan
   lagringsgrund. Måste stå i `docs/BESLUT.md` före första riktiga import.
2. **Kundsynken kan stoppa gallringen tyst.** En synk som skriver en
   tidsstämpel på `prospects`/`contacts` varje varv bumpar `behandlad_at`.
3. **Rättighetsskriptet nycklar bara på e-post.** CRM-personer från Buddy kan
   sakna e-post men ha telefon; de hittas då inte av `--export`/`--radera`.
4. **Nya UI-kataloger granskas inte automatiskt.** `app/crm/` måste läggas in
   i `APPYTOR` (INV-UI-001) och/eller `YTOR` (INV-COPY-001) i samma commit.
   Byggs CRM-appen som en separat Next-app utanför `app/` täcker varken
   INV-SEC-010, INV-API-001, INV-UI-001 eller INV-COPY-001 den alls.
5. **Rottester som inte körs i CI** (`test_rls_nullif_vakt.py`,
   `test_gallring_spegel.py`, `test_railway_synk.py`, `npm test`). Kör dem
   för hand när CRM-ändringen rör det de vaktar.
6. **PUB-avtalet** saknar CRM-integrationer (`JURIDIK_ATGARDER.md:80`), och
   avtalsgrinden (INV-AVTAL-001) stoppar Buddys trafik tills avtalsdatum finns.
7. **Synk i development.** Ett pollande synkjobb mot Buddys API som körs även
   i development-spegeln ger dubbletter; följ `tvavags`-mönstret.
8. **Begränsning (art. 18)** gäller globalt per adress; tvåvägs-API:t ut till
   kundens system är också en behandling och ska fråga `list_begransade`.
