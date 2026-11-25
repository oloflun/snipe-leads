# Underlag 04: tenants, inloggning, roller, API-lagret och bakgrundsjobb

Kartläggning för Snajp CRM (2026-11-25), gjord mot grenen `claude/snajp-crm-dd0d83`
(HEAD `9970d304`). Bara läsning; ingen befintlig fil är ändrad.
Andra genomläsningen (2026-11-25, HEAD `859ba438`): radhänvisningarna i avsnitt 1–9
kontrollerade mot koden igen (`deps.py`, `keys.py`, `rate_limit*.py`, `main.py`,
`postgres.py` `_scoped`/`validate_api_key`/`create_api_key`/rate events/liggaren,
`jobs/store.py`, `jobs/bakgrund.py`, `kvitton.py`, `avtalsgrind.py`, `integrationer/*`,
`_auth.ts`, `_lib.ts`, `tenant.ts`, migrationerna 002, 003, 019, 022, 059, 063, 080);
en hänvisning rättad (`inbox.py`). Tillägg: `bakgrund._pagaende` (en start per
`tenant_id:slag`) är processlokal (`snajp-support/app/jobs/bakgrund.py:41-45`), och
`dubbelstart` likaså (`dubbelstart.py:14-16`); kör api:t fler repliker räcker ingen av dem.

**Läsanvisning.** Varje påstående om koden har `fil:rad`. Det som är
**[ANTAGET]** eller **[EJ VERIFIERAT]** är märkt så; allt annat är läst i koden.
Sökvägar under `snajp-support/` är backenden (FastAPI), övriga är Next-appen.

---

## 0. Det viktigaste först (för den som bygger)

1. **Två auth-lager.** Webben (Next, Auth.js-JWT i cookie) och backenden (FastAPI,
   `X-API-Key`). En inloggad användare pratar *aldrig* direkt med backenden: Next-routen
   härleder tenanten ur sessionen, slår upp kundens backendnyckel och skickar anropet
   vidare server-side (`app/api/snajp-support/_auth.ts:20-71`).
2. **I FastAPI fastställs tenanten av `Depends(require_tenant)`**, som returnerar en
   `dict` `{"tenant_id", "tenant_name", "master": False}` (`snajp-support/app/api/deps.py:42-72`).
   Backenden vet inget om användare eller roller utöver det ogenomskinliga
   `X-Snajp-User`-huvudet (bara för timtak). **Roller och läsrollens skrivspärr finns
   bara i Next** (`_auth.ts:35-37`).
3. **Tenantisolering = RLS + explicit `tenant_id`**: varje fråga körs i
   `storage._scoped(tenant_id)` som sätter `app.tenant_id` transaktionslokalt
   (`snajp-support/app/storage/postgres.py:289-306`), policyn `tenant_isolation` på varje
   tabell, och `where tenant_id = $1` i frågan ändå (försvar på djupet).
4. **API-nycklar per tenant finns** (`ss_api_keys`, sha256, ingen omfångskolumn, ingen
   återkallelse- eller listningsendpoint, bara `POST /api/keys` med master-nyckel). En
   publik CRM-API-nyckel kan *byggas på* detta men kräver minst omfång (scope),
   återkallelse och egen hastighetsbegränsning.
5. **Hastighetsbegränsningen** `rate_limit_db` är generisk nog att återanvända (en
   `Scope(scope_kind, id, cap, event_kind)` mot tabellen `platform_rate_events`), men
   `scope_kind` har ett check-villkor `('tenant','user','ip')` och fönstret är fast en
   timme. Ett per-nyckel-tak kräver en migration (nytt `scope_kind`) eller att man
   räknar per tenant med ett eget `event_kind`.
6. **Grindning per kund** sker på tre nivåer: `workspaces.products` (agenter),
   `workspaces.addons` (tillägg, check-villkor i databasen) och avtalsgrinden
   (`ss_tenants.kraver_avtal` + `ss_customer_details.avtal_signerat`). Tilläggsgrinden
   sitter i dag **bara i Next**; backenden har bara `require_bookkeeping_tenant` som
   produktgrind.
7. **Bakgrundsjobb**: `app/jobs/bakgrund.py:starta/lasa` + `GET /api/jobs/{id}` ger
   förlopp, men jobbposten ligger i Redis med TTL 1 h. Regeln "utfallet finns kvar efter
   omladdning" uppfylls i dag bara där ett eget liggarrad skrivs i Postgres
   (`leads_job_ledger`, INV-JOB-003). En CRM-synk ska ha en egen liggartabell.
8. **Routrar** registreras i `snajp-support/app/main.py:438-496` med `/api/<område>` i
   full sökväg i dekoratorn (ibland `APIRouter(prefix=...)`). **Ingen versionering
   (`/api/v1`) finns.** FastAPI skapas utan `docs_url`/`openapi_url`-argument
   (`main.py:412`), alltså med FastAPI:s standard: **[ANTAGET, ej provat mot deployen]**
   `/docs`, `/redoc` och `/openapi.json` är öppna utan nyckel på api-tjänstens publika
   adress.
9. **Tvåvägs-/envägssynken dev↔main** (`scripts/railway_synk.py:117-149`, tabellistan
   `SYNK`) och gallringen måste få veta om nya CRM-tabeller, annars hamnar CRM-data bara i
   en miljö.

---

## 1. Hur en inloggad användare och dess tenant fastställs

### 1.1 Webben (Next.js, tjänsten `web`)

| Steg | Var | Vad |
|---|---|---|
| Inloggning | `lib/auth.ts:127-226`, `lib/actions/auth.ts` | Auth.js v5, Credentials (+ Google/Microsoft om variablerna finns, av i drift enligt `AUTH.md:167-178`). `session: { strategy: "jwt" }` (`lib/auth.ts:194`). JWT:n bär bara `sub` (användar-id) och `tvafaktor` (`lib/auth.ts:211-226`). |
| Identitet | `auth.users` i appens egen Postgres (`AUTH.md:27-30`) | Lösenord scrypt (`lib/password.ts`). |
| Sidskydd | `proxy.ts:14-81`, matcher `proxy.ts:87-105` | Bara `/dashboard`, `/settings`, `/onboarding`, `/admin`, `/login`, `/embed`. **`/api/*` täcks inte med flit** (`proxy.ts:95-98`, `_auth.ts:16-18`); varje API-route kontrollerar sessionen själv. |
| Kontext per request | `lib/workspace.ts:61-114` `getWorkspaceContext()` | En SQL-fråga som användaren (`sqlAsUser`) läser `profiles`, `workspaces`, `business_contexts` och `exists(platform_admins)`. Returnerar `{ user, profile, workspace, businessContext, isPlatformAdmin }`. Cachad per request med React `cache`. |
| DB-identitet | `lib/db.ts:74-100` `withUser` / `sqlAsUser` | `begin; select set_config('app.user_id', '<uuid>', true)` – transaktionslokalt, så RLS-policyerna (via `current_workspace_id()`, migration `035_app_user_id_rls.sql:18-25`) skopar på användarens arbetsyta. `sql()` utan identitet finns för medveten tvärläsning (`lib/db.ts:56-63`). |
| Databasroll | `AUTH.md:188-197` | Webben ansluter som `snajp_web` (`nobypassrls`), minsta rättighet sedan migration 126; **en ny tabell som webben ska läsa kräver grant i ny migration + rad i `TILLATET` i `snajp-support/tests/db/test_snajp_web_rattigheter.py`**, annars faller CI. |

**Modellen användare → arbetsyta → tenant:**

- `profiles.workspace_id uuid not null` (`db/migrations/000_base_schema.sql:26-32`): en
  användare tillhör exakt **en** arbetsyta.
- `workspaces.slug text`, `workspaces.ss_tenant_id uuid` (`db/migrations/007_workspace_tenants.sql:10-12`):
  arbetsytan pekar på en backend-tenant (`ss_tenants`).
- Flera arbetsytor *kan* dela tenant; backenden tar då den äldsta
  (`snajp-support/app/storage/postgres.py:421-440`, "Tidigast skapade arbetsytan vinner").

### 1.2 Next → backend: `requireSnajpTenant` + `proxyAsTenant`

`lib/snajp/tenant.ts:150-414` `requireSnajpTenant()` returnerar typen `SnajpTenant`
(`lib/snajp/tenant.ts:123-148`):

```ts
{ workspaceId, slug, apiKey, userId, isDemo, impersonerar, roll }
```

Ordningen (läst):

1. Ingen kontext → `SnajpTenantError(401, ..., "ej_inloggad")` (`tenant.ts:151-154`).
2. `aktivVy()` (`lib/vy.ts:72-95`) ger `{vy:"admin"|"demo"|"kund", slug}`. Vyerna
   `kund`/`demo` gäller bara plattformsadmin (fail-closed mot `platform_admins`).
   - **Kundbesök** (`tenant.ts:203-275`): nyckeln via security definer-funktionen
     `public.tenant_api_key_for_admin($1)` (migration 042), eller env-variabeln, eller
     utfärdas på plats med `sakerstallAdminnyckel`. `impersonerar: true`.
   - **Demovy** (`tenant.ts:277-295`): `SNAJP_DEMO_API_KEY`.
3. Egen arbetsyta utan slug → kopplas automatiskt efter onboarding via
   `sakerstallKundtenant` (`tenant.ts:314-343`, `lib/snajp/provisionering.ts`).
4. Annars nyckeln ur `workspace_tenant_keys` via
   `select public.tenant_api_key_for_current_workspace()` (`tenant.ts:15-23`) eller ur
   env `SNAJP_KEY_<SLUG>` för configfil-kunder (`tenant.ts:367-370`). Nyckeln cachas 60 s
   i processen (`tenant.ts:35-54`).

`app/api/snajp-support/_auth.ts:20-71` `proxyAsTenant(path, init)`:

- Läsrollen: icke-GET från `roll === "viewer"` → 403 `{kod:"lasroll"}` (`_auth.ts:35-37`).
- Kundbesök + skrivning → `is_test=true` läggs på query och JSON-kropp (`_auth.ts:39-57`).
- Vidare till `proxyWithApiKey(path, init, apiKey, userId, isDemo)`.

`app/api/snajp-support/_lib.ts:180-340` `proxyWithApiKey` sätter huvudena
(`_lib.ts:217-231`):

| Huvud | Källa | Används av backenden till |
|---|---|---|
| `X-API-Key` | tenantens nyckel | `require_api_key` → tenant |
| `X-Snajp-User` | `user.id` ur sessionen | bara användartimtaket (`rate_limit_db.scopes_for`) – kan bara *snäva* kvoten (`tenant.ts:127-133`) |
| `X-Snajp-Demo: true` | `workspaces.is_demo` | lägre timtak (`chat.py:252`, `inbox.py:41, 94`, `triage.py:79`) |
| `X-Snajp-Admin` | plattformsadminens id, bara när nyckeln är master-nyckeln | åtkomstloggen `audit_logs` (`_lib.ts:196-210`, `snajp-support/app/api/adminlogg.py:44`) |

Övrigt i `_lib.ts`: GET görs om upp till 5 × 9 s, POST/PUT/PATCH en gång à 9 s
(`_lib.ts:145-193`); `{"detail": ...}` översätts till `{"error": ...}` (`_lib.ts:271-289`);
`Server-Timing` och `X-Request-Id` följer med (`_lib.ts:293-297`). Internt nät
`SNAJP_SUPPORT_INTERNAL_URL` först, publik `SNAJP_SUPPORT_URL` som reserv (`_lib.ts:9-52`).

Catch-all-routen `app/api/snajp-support/[...path]/route.ts:19-64` mappar
`/api/snajp-support/<x>` → backendens `/api/<x>` för GET/POST/PUT/PATCH/DELETE,
`runtime = "nodejs"`, `maxDuration = 60`. **En ny CRM-yta i Next kan alltså nå nya
backend-endpoints under `/api/crm/...` utan en enda ny Next-route** (anropet blir
`fetch("/api/snajp-support/crm/...")`, se t.ex. `components/dashboard/Aktivitet.tsx:267`).

Adminytan: `app/api/admin/[...path]/route.ts` kräver `getPlatformAdmin()` (404 annars)
och skickar med `SNAJP_MASTER_API_KEY` mot backendens `/api/admin/*`.

### 1.3 Backenden (FastAPI): Depends-kedjan

`snajp-support/app/api/deps.py`:

| Dependency | Rad | Returnerar / gör |
|---|---|---|
| `require_api_key(request, x_api_key=Header())` | `deps.py:42-59` | 401 utan nyckel. Demonyckel → `{"tenant_id": DEFAULT_TENANT_ID, "tenant_name": "Nordlys Handel", "master": False}`. Master → `{"tenant_id": None, "tenant_name": "master", "master": True}`. Annars `storage.validate_api_key(raw)` → `{"tenant_id", "tenant_name", "master": False}`. Fel → 401 `"Ogiltig API-nyckel."` |
| `require_tenant` | `deps.py:62-72` | Som ovan men 403 om master-nyckeln (ingen tenant). **Standard för all kunddata.** |
| `require_master_key` | `deps.py:75-87` | 403 om inte master. Skriver rad i `audit_logs` via `adminlogg.logga_masteranrop` (INV-SEC-013). |
| `require_bookkeeping_tenant` | `deps.py:90-111` | `require_tenant` + 404 om `"bookkeeping"` saknas i `workspaces.products`; `products is None` släpps igenom. **Mallen för en backend-produktgrind.** |
| `kraev_uuid(varde, vad)` | `deps.py:17-39` | 404 (inte 422/500) för felformat id. Använd på varje id i sökvägen. |

Mönstret i en endpoint (exempel `snajp-support/app/api/integrationer.py:122-130`):

```python
@router.get("")
async def lista_integrationer(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    rader = await lagring.lista(request.app.state.storage, tenant["tenant_id"])
```

Lagret nås som `request.app.state.storage` (`PostgresStorage` eller `MemoryStorage`,
`main.py:146-167`), jobblagret som `request.app.state.jobs` (`main.py:169-179`).

`validate_api_key` (`postgres.py:4546-4580`): sha256 av rånyckeln, join mot
`ss_tenants.active`; giltig nyckel cachas 30 s i processen (`_NYCKEL_TTL_S`,
`postgres.py:133`), `last_used_at` skrivs högst var 5:e minut. **En spärrad nyckel eller
avstängd tenant slutar gälla inom 30 s**, utom vid `set_tenant_active/status` som tömmer
cachen (`postgres.py:398, 418`).

---

## 2. Roller och plattformsadmin

| Roll | Var | Vad den ger | Kod |
|---|---|---|---|
| `owner` | `profiles.role` (text, default `'member'`, `000_base_schema.sql:30`) | Ägare av arbetsytan; bara ägaren bjuder in (policy 032, `AUTH.md:184`, `lib/auth/lasroll.ts:22-27`) | — |
| `member` | `profiles.role` | Arbete i egen arbetsyta | — |
| `viewer` (läsroll) | `profiles.role`, sätts via `workspace_invites.role` | Läser allt, skriver inget. Spärren: `proxyAsTenant` (icke-GET → 403) och `arLasare()` i server actions | `lib/auth/lasroll.ts:33-39`, `_auth.ts:35-37` |
| Plattformsadmin | tabellen `platform_admins` (migration 020, 037), **skild från `profiles.role` med flit** | `/admin`, kundbesök i alla arbetsytor, master-nyckeln via adminproxyn | `lib/auth/admin.ts:28-96` |

- Inget check-villkor på `profiles.role` (`lib/auth/lasroll.ts:24-26`: "kolumnerna är text
  utan check-villkor"). **[ANTAGET]** Det finns inga fler roller i bruk än de tre.
- `getPlatformAdmin()` (`lib/auth/admin.ts:54-72`) är fail-closed och kräver dessutom att
  sessionen gått igenom tvåfaktor om kontot har det; tvånget är av
  (`TVAFAKTOR_KRAVS_FOR_PLATTFORMSADMIN = false`, `AUTH.md:123-127`).
- Plattformsadmin blir man bara genom databasen (migration eller SQL som `postgres`),
  aldrig från appen (`AUTH.md:199-216`).
- **Backenden känner inte roller.** Den ser bara nyckeltyp (kund/master/demo). En
  rollbaserad regel i CRM:et (t.ex. "bara ägare får koppla en API-nyckel") måste sitta i
  Next eller bäras som ett nytt, betrott huvud – det finns inget sådant i dag.

**Kunddata-sekretess per kund (exempel att följa):** webbplatsbedömningen visas bara för
vissa tenants: `snajp-support/app/leads/webbpool.py:91-117` (`SYNLIGA`, `far_se()`,
`dolj()`). Mönstret är "grinda per tenant-slug i backenden, fail-closed vid fel". Varje
CRM-vy/CSV/API-svar som bär `webbrevision`, `webbniva` eller `lan` måste grindas med
`far_se()` (projektregeln 2026-10-08 i CLAUDE.md).

---

## 3. Tenantisolering i lagret

### 3.1 Tre lager

1. **Nyckeln avgör tenant** (`require_tenant`). Tenant kommer aldrig från klientens kropp
   eller från modellen (INV-SEC-002, `ARCHITECTURE_INVARIANTS.md:194-203`).
2. **RLS**: `app.tenant_id` sätts per transaktion i `_scoped`:

   ```python
   # snajp-support/app/storage/postgres.py:289-298
   @asynccontextmanager
   async def _scoped(self, tenant_id: str):
       """Transaktion med app.tenant_id satt, så RLS-policyerna gäller."""
       async with self.pool.acquire() as conn:
           async with conn.transaction():
               await conn.fetchval("select set_config('app.tenant_id', $1, true)", tenant_id)
               yield conn
   ```

   Backenden ansluter som `snajp_app` (`nobypassrls`, migration `009_snajp_app_role.sql:15-22`,
   INV-SEC-001 `ARCHITECTURE_INVARIANTS.md:205-217`, `docs/compliance/datamangder.md:27`).
   `snajp_app` får `select, insert, update` på varje ny tabell via
   `alter default privileges`; **`delete` måste ges uttryckligen**
   (`docs/compliance/datamangder.md:27`).
3. **Explicit `where tenant_id = $1`** i varje fråga ändå (`postgres.py:3-5`).

Oskopade anslutningar (`self.pool.acquire()` utan `_scoped`) används bara för
administrativa vägar bakom `require_master_key` eller för uppslag innan tenant är känd
(`postgres.py:4946-4952`, `validate_api_key`, `count_rate_events`, `get_tenant_products`).

### 3.2 Migrationsmall för en ny tenant-tabell (kopiera)

Nyaste exemplet, `db/migrations/20261122090000_149_iris_konversationer.sql:42-85`:

```sql
create table if not exists public.lead_handelser (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references public.ss_tenants(id) on delete cascade,
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

do $$ begin
  if exists (select 1 from pg_roles where rolname = 'snajp_app') then
    grant select, insert, update on table public.lead_handelser to snajp_app;
  end if;
  if exists (select 1 from pg_roles where rolname = 'synk_las') then
    grant select on table public.lead_handelser to synk_las;
  end if;
end $$;

-- Synken (111)
alter table public.lead_handelser
  add column if not exists synk_andrad_at timestamptz not null default now();
```

Notera `nullif(..., '')` (migration 028/068: tom sträng ska inte kasta), `force row level
security`, grants villkorade på att rollen finns (idempotent, så att den kan köras i alla
miljöer), och `synk_andrad_at` + trigger för synken (migration 111). Migrationer ska vara
additiva och idempotenta (CLAUDE.md, körs automatiskt mot development vid push).

### 3.3 Lagringsmönster att följa

Två sätt finns:

- **Metod på `Storage`-protokollet** (`app/storage/base.py`) implementerad i både
  `postgres.py` och `memory.py` – kräver identiska signaturer (INV-STORE-001,
  `snajp-support/tests/invariants/test_inv_store_001.py`).
- **Egen modul som använder `storage._scoped` direkt**, med minnesfallback – mönstret i
  `snajp-support/app/integrationer/lagring.py:62-111` (och `app/sending_domains.py`).
  Saknad tabell (SQLSTATE `42P01`) ger tom lista på läsvägen, så att koden kan ligga före
  migrationen:

  ```python
  # snajp-support/app/integrationer/lagring.py:95-111
  async def lista(storage, tenant_id, *, bara_aktiva=False):
      if _ar_postgres(storage):
          try:
              async with storage._scoped(tenant_id) as conn:
                  rader = await conn.fetch(
                      f"select {_KOLUMNER} from ss_integrations where {villkor} order by created_at",
                      tenant_id)
          except Exception as fel:
              if _saknar_tabell(fel):
                  return []
              raise
          return [_rad(r) for r in rader]
      rader = [r for r in _minne(storage).values() if r["tenant_id"] == tenant_id]
  ```

  **[REKOMMENDATION]** CRM-lagret passar bäst som en egen modul (t.ex. `app/crm/lagring.py`)
  i det här mönstret: Storage-protokollet är redan ~2 500 rader och INV-STORE-001 gör varje
  ny metod dubbel.

Övrigt: `_row()` (`postgres.py:142-153`) gör `uuid`→`str` och tider→ISO; jsonb kommer
som text från asyncpg och måste avkodas per kolumn (`postgres.py:202-225`).

### 3.4 Invarianter som rör ett CRM

| Id | Regel | Var |
|---|---|---|
| INV-SEC-001 | DB-roll utan BYPASSRLS | `ARCHITECTURE_INVARIANTS.md:205-217` |
| INV-SEC-002 | Tenant kommer aldrig från modellen | `:194-203` |
| INV-SEC-010 | Varje anonym Next-route står i allowlistan med skäl | `tests/invariants/test_inv_sec_010.py:38-77` |
| INV-SEC-013 | Varje `/api/admin`- och `/api/keys`-route har `require_master_key` och loggas | `ARCHITECTURE_INVARIANTS.md:1142-1156` |
| INV-STORE-001 | Memory och Postgres har identiska signaturer | `:558-576` |
| INV-JOB-002/003 | Liggaren i Postgres är sanningen, Redis snabbvägen | `:634-656`, `:921-936` |
| INV-DATA-003/008 | Development och main skrivs bara av synken och admin_flytt | `:801`, `:1108` |
| INV-COPY-001 | All användarvänd text sv+en | `:818` |
| INV-AVTAL-001 | Ny tenant kräver signerat avtal om inget annat sägs | `:985` |
| Roadmap INV-SEC-006 | "Hemligheter i env, aldrig i databasen" (ej tvingad än) | `:1158-1166` |

---

## 4. API-nycklar per tenant (`app/api/keys.py`)

### 4.1 Vad som finns

- **Tabell `ss_api_keys`** (`db/migrations/002_snajp_support.sql:96-104`, `tenant_id`
  tillagd i `003_snajp_multitenant.sql:30-46`):

  | Kolumn | Typ |
  |---|---|
  | `id` | uuid pk |
  | `tenant_id` | uuid not null → `ss_tenants(id)` |
  | `tenant_name` | text not null |
  | `key_prefix` | text not null |
  | `key_hash` | text not null **unique** |
  | `active` | boolean not null default true |
  | `created_at` | timestamptz |
  | `last_used_at` | timestamptz |

  RLS `tenant_isolation` + undantaget `api_key_lookup` (select när `app.tenant_id` inte är
  satt, `003_snajp_multitenant.sql:96-99`). **Inga omfång (scopes), inget namn/etikett,
  ingen utgångstid, ingen `revoked_at`.** Inga senare migrationer ändrar tabellen
  (bara 002, 003, 009 nämner den).
- **Utfärdande:** `POST /api/keys` (`snajp-support/app/api/keys.py:31-79`), bara
  `require_master_key`. Skapar/återanvänder tenanten (`storage.create_tenant`) och
  nyckeln `f"snajp_live_{secrets.token_hex(16)}"` (`keys.py:64`). Klartext returneras en
  gång. Kroppen `CreateKeyRequest` (`schemas.py:46-53`): `tenant_name`, `slug`,
  `kraver_avtal`.
- **Lagring:** `create_api_key` (`postgres.py:4582-4599`) sparar
  `sha256(raw_key).hexdigest()` och `key_prefix = raw_key[:12]`. Prefixet blir
  `snajp_live_` + **ett** hextecken, alltså oanvändbart för att skilja nycklar åt i ett UI.
- **Kontroll:** `require_api_key` → `validate_api_key` (se 1.3). Demo- och master-nyckeln
  jämförs med `==` (`deps.py:48-50`), inte `hmac.compare_digest` (drift.py gör det rätt,
  `snajp-support/app/api/drift.py:34-37`).
- **Var klartexten bor:** för kunder skapade i drift i `workspace_tenant_keys.api_key`
  **i klartext** (`db/migrations/040_testkund_egen_tenant.sql:34-45`), RLS utan policies,
  nås bara via security definer-funktioner; för configfil-kunder i env `SNAJP_KEY_<SLUG>`.
  Webbens egen nyckel per arbetsyta *är* alltså samma typ av nyckel som en extern
  integration skulle få.
- **Saknas:** listning, återkallelse, rotation, per-nyckel-omfång och en kundvänd yta för
  nycklar. `grep ss_api_keys` i `snajp-support/app` ger bara de två metoderna ovan.

### 4.2 Konsekvens för Buddys tvåvägs-API [REKOMMENDATION]

Att ge Buddy en vanlig `snajp_live_`-nyckel ger full åtkomst till **varje**
`require_tenant`-endpoint (inkorg, leads, utkast, utskick, KB …), inte bara CRM:et. Bygg
därför en egen nyckeltyp eller utöka `ss_api_keys` additivt, t.ex.:

- `alter table ss_api_keys add column if not exists omfang text[] not null default '{*}'`,
  `namn text`, `revoked_at timestamptz`, `skapad_av uuid`; befintliga nycklar behåller
  `'{*}'`.
- Ny dependency `require_crm_api(omfang="crm:skriv")` som anropar `require_tenant`, läser
  `omfang` och avvisar med 403; och spegelbilden: vanliga endpoints avvisar en nyckel som
  bara har `crm:*`.
- Ett nytt prefix (t.ex. `snajp_crm_`) gör nyckeltypen läsbar i loggar.
- Nyckelhanteringen (skapa/lista/återkalla) som kundyta bakom ägarrollen i Next, eftersom
  backenden inte känner roller (avsnitt 2).

---

## 5. Hastighetsbegränsning

### 5.1 Två implementationer

| Modul | Lagring | Används till | Rad |
|---|---|---|---|
| `app/api/rate_limit.py` | processminne (deque) | demons IP-tak | `rate_limit.py:27-44` `SlidingWindowRateLimiter.check(key, RateLimitRule(max_requests, window_seconds))` |
| `app/api/rate_limit_db.py` | Postgres `platform_rate_events` | chatt, triage, KB-skanning, kanaler, budget | `rate_limit_db.py:82-156` |

`platform_rate_events` (`db/migrations/019_rate_limit.sql:26-55`):

```sql
id bigserial pk, scope_kind text not null check (scope_kind in ('tenant','user','ip')),
scope_id text not null, kind text not null, created_at timestamptz not null default now()
index (scope_kind, scope_id, kind, created_at desc); index (created_at)
RLS: policy platform_rate_events_service för snajp_app; grant select, insert, delete
```

API:t (`rate_limit_db.py`):

- `Scope(scope_kind, id, cap, event_kind="llm_call")` (`:82-87`).
- `scopes_for(tenant_id, user_id, is_demo=False)` → tenant 400/h, användare 120/h
  (demo 20/h) (`:49-52`, `:90-99`).
- `await enforce(storage, scopes)` kastar `RateLimitDbExceededError(scope_kind, used, cap)`
  (`:106-130`); **fail-open** vid lagringsfel.
- `await record(storage, scopes, antal)` bokför (`:133-156`); städar rader äldre än ett
  dygn (`postgres.py:4937-4944`).
- Fönstret är fast `WINDOW = timedelta(hours=1)` (`:37`).

Återanvändning, exempel med eget `event_kind` (KB-skanningen,
`snajp-support/app/api/kb.py:294-303`):

```python
skanningar = [rate_limit_db.Scope("tenant", tenant["tenant_id"], SKANNINGAR_PER_TIMME, SKANNING)]
try:
    await rate_limit_db.enforce(storage, skanningar)
except rate_limit_db.RateLimitDbExceededError:
    raise HTTPException(status_code=429, detail="För många skanningar den senaste timmen. ...")
await rate_limit_db.record(storage, skanningar, 1)
```

Och 429-mönstret i chatten (`snajp-support/app/api/chat.py:251-259`).

### 5.2 Passar det ett publikt API? [BEDÖMNING]

- **Går:** per tenant och per `kind` (t.ex. `kind="crm_api"`) med timfönster, utan
  migration.
- **Räcker inte:** en rad per anrop i Postgres plus en `count(*)` per anrop är dyrt för
  ett synk-API med många småanrop; fönstret är bara en timme (inget per-minut-tak);
  `scope_kind` tillåter inte `'api_key'`; fail-open betyder att ett DB-fel släpper allt;
  inga `Retry-After`/`X-RateLimit-*`-huvuden sätts någonstans.
- **Förslag:** räkna per tenant med `kind="crm_api"` för timtaket och lägg ett
  minuttak i Redis (jobblagrets klient finns redan, `main.py:169-179`;
  `app/redisnycklar.py:nyckel()` för namnrymd, INV-REDIS-001). Bulkendpoints (batch-upsert
  av kunder) minskar antalet anrop mer än något tak.
- Dubbelklicksskydd för startande POST: `app/api/dubbelstart.py:49-77` `en_gang(nyckel(tenant_id, handling, innehall), arbete)`
  (processlokalt, 30 s).

Inloggningsspärren i webben (migration 125, `lib/auth/inloggningsregler.ts`) är separat
och gäller bara lösenord/återställning (`AUTH.md:49-70`).

---

## 6. Tillägg, produkter och avtalsgrinden

### 6.1 Produkter (`workspaces.products`)

`text[]`, check `products <@ array['leads','support','bookkeeping']` och minst ett värde
(`db/migrations/047_bookkeeping_entitlement.sql:28-35`). Självbetjäning via
`set_workspace_products` (`047:59-103`). Avgör vilka vyer som finns.
Backendgrind: bara `require_bookkeeping_tenant` (`deps.py:90-111`).

### 6.2 Tillägg (`workspaces.addons`)

- `text[] not null default '{}'`, check-villkor som räknar upp värdena
  (`022_workspace_addons.sql:14-30`, senast utökad med `leadlists` i
  `060_leadlists.sql:25-29`).
- Spegel i koden: `lib/addons.ts:15-26` `addonKeys = ["inbox","vision","kb_autoingest","multilang","own_domain","reports","leadlists"]`
  och katalogen `addonCatalog` (sv+en). **Ändras i samma ändring som check-villkoret**
  (`lib/addons.ts:22-24`, `060_leadlists.sql:21`).
- Sätts bara av plattformsadmin: `public.set_workspace_addons(mal_tenant uuid, nya text[])`
  och läses med `public.admin_workspace_addons(mal_tenant uuid)`
  (`063_workspace_addons_admin.sql:50-130`).
- **Grinden sitter i Next**, exempel `lib/actions/saljlista.ts:46-56`:

  ```ts
  const TILLAGG = "leadlists" satisfies (typeof addonKeys)[number];
  async function grind(skriv: boolean): Promise<Behorighet> {
    const context = await getWorkspaceContext();
    if (!context) return { ok: false, fel: "ej_inloggad" };
    if ((await aktivVy()).vy !== "admin") return { ok: false, fel: "fel_vy" };
    if (!(context.workspace.addons ?? []).includes(TILLAGG)) return { ok: false, fel: "saknar_tillagg" };
    if (skriv && arLasare(context)) return { ok: false, fel: "las_roll" };
    return { ok: true, userId: context.user.id, workspaceId: context.workspace.id };
  }
  ```

  Backenden grindar **inte** `leadlists` (uttryckligen, `snajp-support/app/api/leads.py:4476-4479`).
  Listimporten ligger bakom `leadlists`; om Buddy ska ha den utan tillägget är det ett
  prisbeslut (`HANDOFF-2026-11-23-LISTIMPORTEN.md`, "Att bygga vidare på" punkt 3).
- Låsta tillägg visas som upsell, inte gömda (`lib/addons.ts:9-13`); entitlements är
  fail-closed (`022_workspace_addons.sql:32-34`).

**[REKOMMENDATION] för CRM:et:** ett nytt tillägg `crm` (migration som byter
check-villkoret + `lib/addons.ts` i samma commit) *och* en backendgrind
`require_crm_tenant` efter mallen `require_bookkeeping_tenant` – men med läsning av
`addons` i stället för `products`. Det behövs en ny lagringsmetod `get_tenant_addons`
(finns inte) eftersom ett publikt API inte passerar Next-grinden.

### 6.3 Avtalsgrinden (`app/avtalsgrind.py`)

- Fält: `ss_tenants.kraver_avtal` (migration 070, standard `true` för nya tenants sedan
  118) och `ss_customer_details.avtal_signerat` (datum, migration 053)
  (`avtalsgrind.py:13-22`).
- `await avtal_saknas(storage, tenant_id) -> bool` (`avtalsgrind.py:71-98`), cache 60 s,
  fail-open vid lagringsfel, fail-closed vid saknat avtal. `glom(tenant_id)` tömmer en
  tenants cache (`:65-68`).
- Användning: `chat.py:245-246` → `HTTPException(403, KUNDTEXT_AVTAL)`.
- **[BEDÖMNING]** Kundsynk in av Buddys kundregister är personuppgiftsbehandling; samma
  grind bör stå på CRM-API:ts skrivvägar (403 med `KUNDTEXT_AVTAL`).

### 6.4 Budgetar

`app/budget.py` (supportens dygnstak i tokens, env `SUPPORT_BUDGET_<SLUG>`,
`SUPPORT_DAILY_TOKEN_BUDGET`, `budget.py:14-21, 77-80`) och `app/leads/budget.py`. Rör
LLM-kostnad, inte ett CRM-API utan LLM. `GET /api/usage` (`app/api/usage.py:24-49`) är ett
exempel på tenant-skopad läsyta med kundens egen nyckel.

---

## 7. Bakgrundsjobb med förlopp och utfall (regeln 2026-10-10)

### 7.1 Vad som finns

| Del | Var | Beständighet |
|---|---|---|
| Jobblagret `MemoryJobStore`/`RedisJobStore` | `snajp-support/app/jobs/store.py:30-179` | Redis-nyckel `crm:job:<id>` (namnrymd via `redisnycklar.nyckel`), **TTL 3 600 s** (`JOB_TTL_SECONDS`, `store.py:19`), "processing" auto-failas efter 600 s utan förlopp (`store.py:18`, `166-170`). Metoder: `create(tenant_id, status)`, `start`, `complete(result)`, `fail(error)`, `annotate(**falt)`, `get`. |
| Generiskt bakgrundsarbete | `snajp-support/app/jobs/bakgrund.py:70-122` | `starta(app_state, tenant_id, slag, arbete) -> (job_id, pagar)`; `Forlopp.satt(**falt)` skriver `forlopp` på posten och flyttar tidsgränsen; `lasa(app_state, tenant_id, job_id)`. En start per `tenant_id:slag` åt gången. **Lever i api-processen**; dör vid deploy (`bakgrund.py:17-22`). |
| Pollning | `GET /api/jobs/{job_id}` (`snajp-support/app/api/chat.py:368-390`) | Svar: `{status, result, error, fas?, forlopp?}`; 404 om jobbet tillhör annan tenant. Statusvärden: `"processing"`, `"queued"`, `"completed"`, `"failed"`. |
| Hållbar liggare | `leads_job_ledger` (`db/migrations/059_leads_job_ledger.sql:34-47`, utökad i `20261001100000_080_korningar.sql`: `korning jsonb`, `error text`, `is_test boolean`, `updated_at`) | Postgres. Status `('queued','processing','completed','failed')`. Läses av `GET /api/leads/korningar` (`leads.py:1971-1987`). INV-JOB-003. |
| Redis-strömmar som överlever deploy | `app/jobs/stream.py`, `main.py:220-325` | Chatt (`crm:jobb:...`) och leads (`crm:jobb:leads`), egna consumer-grupper. |
| Städare | `app/jobs/stadare.py`, startas i `main.py:356-364` | Ger hängande leadsjobb ett ärligt slut. |

Användare av `bakgrund.starta` i dag: kvittoskanningen (`kvitton.py:212-226`),
körningens utskick (`leads.py:2170-2188`), kampanjutskick (`leads_kampanjer.py:259-267`),
konversationer (`leads_konversationer.py:490`).

**Viktigt:** `bakgrund.starta` + `GET /api/jobs/{id}` uppfyller *förloppet* men **inte**
"utfallet finns kvar efter en omladdning" efter en timme eller en deploy (Redis-TTL). Där
regeln uppfylls helt är det för att arbetet skriver sitt eget tillstånd i Postgres:
`leads_job_ledger.korning` (INV-JOB-003), kampanjen (`leads_kampanjer.py:225-241`, sparas
med `_spara_kampanj` innan uppgiften startas, `status: "pagar"`) och listimportens kvitto
(`lead_lists.importinfo`, migration 152, `leads_suite.py:412-505`).

### 7.2 Komplett exempel att kopiera (förlopp)

`snajp-support/app/api/kvitton.py:188-226`:

```python
@router.post("/api/kvitton/skanning", status_code=202)
async def starta_skanning(request: Request, fran: date | None = None, till: date | None = None,
                         tenant: dict = Depends(require_tenant)) -> dict:
    ...
    async def _arbete(forlopp: bakgrund.Forlopp) -> dict:
        async def _mejl(lasta: int, totalt: int) -> None:
            await forlopp.satt(lasta=lasta, totalt=totalt)
        return await _skanna(request, fran, till, tenant, forlopp=_mejl)

    job_id, pagar = await bakgrund.starta(request.app.state, tenant["tenant_id"], "kvittoskanning", _arbete)
    return {"job_id": job_id, "pagar": pagar}


@router.get("/api/kvitton/skanning/{job_id}")
async def las_skanning(request: Request, job_id: str, tenant: dict = Depends(require_tenant)) -> dict:
    return await bakgrund.lasa(request.app.state, tenant["tenant_id"], job_id)
```

Och med `klara`/`totalt` plus `GET /api/jobs/{id}` (`leads.py:2170-2217`):

```python
jobb, pagar = await bakgrund.starta(
    request.app.state, tenant["tenant_id"], f"korningens-utskick:{job_id}",
    lambda forlopp: _skicka_korningens_utkast(request, job_id, tenant, forlopp=forlopp))
...
if forlopp is not None:
    await forlopp.satt(klara=0, totalt=len(vantande))
for lead in vantande:
    ...
    await forlopp.satt(klara=len(utfall), totalt=len(vantande))
return {"skickade": ..., "vantar_pa_fonstret": ..., "stoppade": [...]}
```

Hållbar liggare (`leads.py:2884-2900`):

```python
async def _spara_korning(app_state, tenant_id: str, batch_id: str, k: dict) -> None:
    await app_state.storage.set_leads_job_status(
        tenant_id, job_id=batch_id,
        status="completed" if k.get("klar") else "processing",
        scope="batch", korning=k, is_test=bool(k.get("is_test")), error="")
```

Läsvägen tar Redis först och faller tillbaka på liggaren (`_las_korning`, `leads.py:2903-2912`).

### 7.3 Förslag för kundsynken [REKOMMENDATION]

En egen liggartabell, t.ex. `crm_synkkorningar` (`id`, `tenant_id`, `kalla`
(`'api'|'fil'|'hubspot'…`), `status` `('queued','processing','completed','failed')`,
`totalt`, `klara`, `skapade`, `uppdaterade`, `hoppade`, `fel jsonb`, `error text`,
`idempotensnyckel text`, `startad_av`, `created_at`, `updated_at`, `synk_andrad_at`), RLS
som 3.2. Bakgrundsarbetet skriver förloppet till **både** `Forlopp.satt` (snabbvägen) och
liggaren efter varje sats; vyn läser liggaren. Ett API-anrop från Buddy som tar emot en
stor batch svarar 202 med körningens id, och `GET /api/crm/synk/{id}` läser liggaren –
då överlever utfallet både omladdning, TTL och deploy. Gör arbetet idempotent (upsert på
`(tenant_id, orgnr)` respektive extern id), eftersom en deploy avbryter `bakgrund`-uppgifter
(`bakgrund.py:17-22`).

---

## 8. Integrationer (`app/integrationer/`)

### 8.1 Vad som finns

| Modul | Rader | Vad |
|---|---|---|
| `__init__.py` | 1-28 | Översikt: två vägar in per kund (HTTP-förfrågningar, MCP-server), två sätt att använda dem (uppslag av modellen, händelser av koden). |
| `modell.py` | 427 | `HttpKonfig` (Ebbot-kompatibel `requests`-array), `McpKonfig`, `las_konfig`, `saknade_hemligheter`, `HANDELSER`, `KONTEXTNAMN`. |
| `http_verktyg.py` | 312 | Kör en förfrågan som verktyg. |
| `mcp_klient.py` | 252 | Listar/anropar verktyg på kundens MCP-server. |
| `uppslag.py` | 300 | Support-agentens uppslagssteg. |
| `handelser.py` | 220 | Kodutlösta anrop vid händelse (`arende_eskalerat`), kastar aldrig, fel → `platform_events`. |
| `natvakt.py` | 285 | SSRF-skydd: bara publik https, varje omdirigering prövas, 3 omdirigeringar, 1 MB, 15 s. |
| `hemligheter.py` | 131 | Kryptering i vila, tvättning ur svar. |
| `lagring.py` | 294 | Tabellen `ss_integrations`. |
| `katalog.py`, `resultat.py` | — | MCP-verktygens skriv-/tillåtlista, resultattyp. |

API: `snajp-support/app/api/integrationer.py` (`APIRouter(prefix="/api/integrationer")`,
`:37`): `GET ""`, `POST ""` (201), `PATCH /{integration_id}`, `DELETE /{integration_id}`,
`GET /{integration_id}/verktyg`, `POST /{integration_id}/prova` (skrivande prov kräver
`tillat_skrivning: true`). Alla `Depends(require_tenant)`.

Kanaler (WhatsApp, Messenger, Slack, Teams): `app/api/kanaler.py`, tabell
`ss_channel_connections` (`067_integrationer_och_kanaler.sql:72-92`); webhooks
autentiseras av kanalens signatur, inte `X-API-Key` (`main.py:442-444`).

**Befintlig CRM-synk UT** (relevant för tvåvägs-API:t): `snajp-support/app/leads/crm_synk.py`
(151 rader) speglar prospekt + en anteckning per händelse till HubSpot
(`https://api.hubapi.com`) eller Pipedrive (`https://api.pipedrive.com/v1`), envägs,
"Ingenting läses tillbaka" (`crm_synk.py:1-10`). Konfigureras per tenant i leads-
inställningarna som `crm_synk: {leverantor: "hubspot"|"pipedrive"|None, integration_id}`
(`schemas.py:285-292`, `leads.py:1775-1783`, `1934-1935`); nyckeln är hemligheten
`api_key` i en `ss_integrations`-rad.

### 8.2 Hur hemligheterna lagras

- Tabell `ss_integrations` (`067_integrationer_och_kanaler.sql:43-58`): `id`, `tenant_id`,
  `typ ('http'|'mcp')`, `namn`, `beskrivning`, `konfig jsonb`, `hemlighetsnamn text[]`
  (namnen i klartext), `hemligheter_krypterat text` (en Fernet-token för alla värden),
  `aktiv`, `created_at`, `updated_at`. Unikt `(tenant_id, lower(namn))`. RLS per tenant.
- Kryptering: Fernet/MultiFernet med env `INTEGRATION_NYCKEL` (kommaseparerad för
  rotation; första krypterar, alla dekrypterar) (`hemligheter.py:17-21, 62-77`). Saknas
  nyckeln i en miljö med riktig kunddata → `IngenNyckelError` → 503 vid sparning. Lokalt en
  fast, publik utvecklingsnyckel (`hemligheter.py:42-46`).
- Ut ur API:t går aldrig värden: `lagring.offentlig()` visar namnen maskerade
  (`lagring.py:76-89`); `dekryptera_hemligheter` anropas bara när ett anrop byggs.
- Samma nyckel krypterar inkorgarnas lösenord (`ss_mailboxes.secret_enc`, migration 077,
  `snajp-support/app/api/inbox.py:25, 228, 281`).
- Undantaget: backendnyckeln per arbetsyta i `workspace_tenant_keys.api_key` är **klartext**
  (avsnitt 4.1).

---

## 9. Routrar, prefix, versioner och OpenAPI

- `app = FastAPI(title="Snajp-Support", version="0.1.0", lifespan=lifespan)`
  (`snajp-support/app/main.py:412`).
- Middleware: `Matning` (Server-Timing) och `Sparning` (anrops-id) (`main.py:415-420`);
  CORS bara om `ALLOWED_ORIGINS` är satt, `allow_credentials=False`, metoder
  `GET, POST, PUT, PATCH, OPTIONS`, huvuden `Content-Type, X-API-Key`
  (`main.py:422-436`). **DELETE finns inte i CORS-listan**, och den finns till för den dag
  en kund anropar API:t från sin egen webbapp (`main.py:422-427`).
- Registrering: importera modulen i `main.py:19-56` och `app.include_router(<modul>.router)`
  i blocket `main.py:438-496`, ofta med en kommentarrad om varför.
- **Prefixkonvention:** full sökväg `/api/<område>/...` i dekoratorn och `router = APIRouter()`
  (t.ex. `keys.py:17, 31`, `usage.py:21-24`), eller `APIRouter(prefix="/api/<område>")`
  (`integrationer.py:37`, `drift.py:22`). Svenska och engelska namn blandas
  (`/api/integrationer`, `/api/leads/korningar`, `/api/tickets`). Adminvägar under
  `/api/admin/*` bakom `require_master_key`.
- **Ingen versionering** (`grep "/api/v1"` ger noll träffar i `snajp-support/app`).
- Felhantering: `install_exception_handler` (`snajp-support/app/api/events.py:133-242`):
  ohanterade fel → 500 `{"error", "referens"}` + rad i `platform_events`; kvot → 429;
  beroende nere → 503. `HTTPException` serialiseras som `{"detail": ...}`, som Next-proxyn
  översätter till `error`.
- **OpenAPI:** ingen kod sätter `docs_url`, `redoc_url` eller `openapi_url` (sökt i
  `snajp-support/app`, Dockerfile, `railway/`). Med FastAPI:s standard är
  `/docs`, `/redoc` och `/openapi.json` alltså på. **[EJ VERIFIERAT mot deployen]** att de
  svarar på api-tjänstens publika adress; inget dokument nämner dem. Det är en informations-
  läcka (hela den interna ytan, inklusive `/api/admin/*`-scheman) snarare än en
  åtkomstläcka, eftersom varje route kräver nyckel.
- Hälsa: `GET /health`, `/health/live`, `/health/ready` (`main.py:527-656`), utan nyckel.

**[REKOMMENDATION] för det publika CRM-API:t:** lägg det under ett eget versionerat prefix
(`/api/crm/v1/...` eller en separat `APIRouter(prefix="/api/v1/crm")`) så att den interna
ytan kan fortsätta ändras fritt; ge det en egen, filtrerad OpenAPI (t.ex. en underapp eller
`get_openapi(routes=crm_router.routes)`) och stäng standarddokumentationen för resten
(`docs_url=None, openapi_url=None` eller grindad).

---

## 10. Risker och fällor för CRM-bygget

1. **Full nyckel = full åtkomst.** En vanlig tenantnyckel till Buddy öppnar hela backenden
   (avsnitt 4.2). Bygg omfång innan någon extern part får en nyckel.
2. **Backenden har ingen tilläggsgrind.** Ett publikt API når backenden utan Next, så
   `addons`-kontrollen måste dupliceras i backenden (avsnitt 6.2).
3. **Rollerna finns bara i Next.** En kund med läsroll kan inte nå backenden via webben
   för skrivning, men en API-nyckel bär ingen roll alls.
4. **Jobbens TTL.** `bakgrund` + Redis räcker inte för regeln 2026-10-10; utfallet måste ha
   en Postgres-rad (avsnitt 7).
5. **Synk dev↔main.** Nya tabeller som ska följa med till development måste in i
   `SYNK` i `scripts/railway_synk.py:117-149` och ha `synk_andrad_at` + trigger
   (migration 111). Tabeller som inte står där finns bara i den miljö de skrevs i.
   Development är en spegel med riktiga kunddata (CLAUDE.md): peka aldrig en lokal server
   dit.
6. **Gallring och behandlingsbegränsning** (migrationer 119, 124, 133, 144) gäller
   kunddata; en CRM-tabell med personuppgifter (kontaktpersoner) måste in i gallringen och
   respektera `list_begransade` (`leads_suite.py:405-409`). **[EJ KARTLAGT i detalj här.]**
7. **`snajp_web` minsta rättighet.** Läser webben CRM-tabellerna direkt (server components
   med `sqlAsUser`) krävs grants och en rad i `TILLATET`
   (`snajp-support/tests/db/test_snajp_web_rattigheter.py`), annars faller CI. Att gå via
   backenden (`/api/snajp-support/crm/...`) slipper det.
8. **`delete` saknas som standardrättighet** för `snajp_app` på nya tabeller.
9. **Nyckelcachen 30 s** (`postgres.py:133`): en återkallad nyckel fungerar upp till 30 s
   till i varje process, om återkallelsen inte tömmer `_nycklar` som
   `set_tenant_active` gör.
10. **`==` på master/demo-nyckeln** (`deps.py:48-50`) är inte konstanttid.
11. **Befintliga kunder finns redan som begrepp**: en leadslista med `kalla='crm'`
    (migration 098) utesluts av Iris och listbygget (`leads_suite.py:96-99, 392-402`,
    `app/leads/upptagna.py`). CRM:ets kundregister måste antingen ersätta eller mata den
    vägen, annars finns två sanningar om "befintlig kund".
12. **Webbplatsbedömningen** (`webbrevision`, `webbniva`, `lan`) får aldrig följa med i ett
    CRM-svar, en export eller API:t utom för tenants i `webbpool.synliga()`.
13. **Tvåspråkighet**: varje ny komponent och varje kundvänd backendtext sv+en
    (INV-COPY-001).

---

## 11. Filer lästa

`AUTH.md`, `TENANTS.md`, `SECURITY.md` (bara en sårbarhetspolicy, inget om API:t),
`ARCHITECTURE_INVARIANTS.md` (rubriker + SEC-001/002/013, STORE-001, JOB-003),
`proxy.ts`, `lib/auth.ts` (callbacks), `lib/auth/admin.ts`, `lib/auth/lasroll.ts`,
`lib/db.ts`, `lib/workspace.ts`, `lib/snajp/tenant.ts`, `lib/addons.ts`, `lib/paket.ts`,
`lib/vy.ts` (rubriker), `lib/actions/saljlista.ts:40-70`,
`app/api/snajp-support/_auth.ts`, `_lib.ts`, `[...path]/route.ts`,
`app/api/admin/[...path]/route.ts`, `tests/invariants/test_inv_sec_010.py:1-80`,
`snajp-support/app/main.py`, `api/deps.py`, `api/keys.py`, `api/rate_limit.py`,
`api/rate_limit_db.py`, `api/schemas.py` (klasslista, `CreateKeyRequest`, `CrmSynkRequest`),
`api/integrationer.py`, `api/events.py`, `api/dubbelstart.py`, `api/usage.py`,
`api/chat.py:225-390`, `api/kvitton.py:180-226`, `api/leads.py` (utdrag),
`api/leads_kampanjer.py:230-300`, `api/leads_suite.py` (utdrag), `api/drift.py` (utdrag),
`jobs/bakgrund.py`, `jobs/store.py`, `avtalsgrind.py`, `budget.py:1-80`,
`config.py` (bara inställningsnamn), `storage/postgres.py` (utdrag), `integrationer/*`
(huvuden, `hemligheter.py:1-80`, `lagring.py:1-140`), `leads/crm_synk.py:1-60`,
`leads/webbpool.py:85-117`, `scripts/railway_synk.py:1-149`, migrationerna
000, 002, 003, 007, 009, 019, 022, 035, 040, 047, 059, 060, 063, 067, 080 (körningar),
111, 149. `app/tenants/` innehåller bara KB- och affärskontextmoduler för
configfil-kunder (`livrustning_kb.py`, `snajp_kb.py`, `konvertera.py` …) och saknar
auth-logik.

Inte lästa i detalj: `lib/snajp/provisionering.ts`, `app/jobs/stream.py`,
`app/jobs/stadare.py`, `app/api/adminlogg.py`, migration 123 (`audit_logs`-funktionen),
`lib/auth/inloggningsregler.ts`.

### Inställningsnamn i `snajp-support/app/config.py` som rör auth/API (bara namn)

`snajp_master_api_key`, `snajp_demo_api_key`, `allowed_origins`, `integration_nyckel`,
`flytt_nyckel`, `schema_lasnyckel`, `database_url`, `redis_url`, `api_publik_url`,
`railway_public_domain`, `publik_bas_url`, `environment`, `railway_environment_name`,
`support_daily_token_budget`, `leads_daily_token_budget`, `chat_workers`, `leads_workers`,
`db_start_forsok`. Webben: `AUTH_SECRET`, `DATABASE_URL`, `SNAJP_SUPPORT_URL`,
`SNAJP_SUPPORT_INTERNAL_URL`, `SNAJP_INTERNAL_API_KEY`, `SNAJP_MASTER_API_KEY`,
`SNAJP_DEMO_API_KEY`, `SNAJP_KEY_<SLUG>` (`AUTH.md:235-243`, `_lib.ts:9-25`).
