# Migrationer — status

## 030–033: APPLICERADE MOT PRODUKTIONEN 2026-08-17

Kördes med versioner som matchar filnamnen (`030`–`033`), inte med nya
tidsstämplar. Det är avsiktligt: Management-API:t registrerar annars egna
14-siffriga versioner utan motsvarande fil, vilket är exakt den dubbla
bokföring som fällde branching-checken tidigare i veckan.

| Migration | Verifierat med |
|---|---|
| `030_suppressions_tenant_scope` | `tenant_id` finns på `suppressions`, index och RLS-policy för `snajp_app` på plats. Backfillen var en no-op — tabellen är tom. |
| `031_prospect_nischfalt` | Alla åtta kolumner finns (`orgnr`, `ort`, `postnr`, `sni`, `website`, `anstallda`, `omsattning`, `foretagsnyckel`). Den genererade nyckeln räknas i databasen, inte i koden. |
| `032_platform_admin_bootstrap` | `snajpsupport@gmail.com` står i `platform_admins`. Triggern på `auth.users` är exception-säker enligt läxan i `006`. |
| `033_platform_admins_recursion` | Policyvillkoret är `user_id = auth.uid()` — rör inte längre sin egen tabell. |

**Den avgörande verifieringen** gjordes som `authenticated` med adminkontots
uid, inte som `postgres`. Frågan `isPlatformAdmin()` ställer ger nu exakt en
rad. Som `postgres` med BYPASSRLS hade den sett rätt ut hela tiden — det är
precis den blindheten som lät rekursionen ligga oupptäckt.

## Återstår

### `SNAJP_KEY_SNAJP`

Vår egen arbetsyta har `slug='snajp'`, `ss_tenant_id` satt och en configfil i
`lib/tenants/snajp.ts`. Kvar är API-nyckeln mot backenden:

```bash
python scripts/onboard_tenant.py --slug snajp --name "Snajp" --env production
```

Utan den svarar `requireSnajpTenant()` med 503 och namnger variabeln. Det är
avsiktligt — utan nyckel svarar vi hellre inte alls än som ett annat bolag.

### `021_seed_platform_admin.sql`

Ersatt av `032`, som gör samma sak utan ordningsberoende. Kan tas bort.

## railway-main: cutovern är GJORD (2026-08-22)

`railway-main` bär sedan 2026-08-22 samma kod som `development` (`b5277d1`).
Vägen dit blev alternativ 1 nedan — force-push — efter ett uttryckligt ja.

De 22 commits som bara fanns i den grenens historik ligger kvar på
`railway-main-fore-cutover-2026-08-22` (`0329452`). Den grenen är inte kopplad
till någon miljö och deployar ingenting; den finns för att en force-push aldrig
ska vara det enda som stod mellan oss och en historik.

Verifierat mot produktionen efter deployen, inte antaget:

| Kontroll | Utfall |
|---|---|
| `web` och `api`, miljö `main` | SUCCESS, båda |
| `web/`, `/leads`, `/api/health` | 200 |
| `api/health/ready` | `ok`, `mode: live`, storage postgres |
| `POST /api/triage` | 200 med riktig klassificering (leverans, konfidens 0.7) |
| `POST /api/chat` + jobbpollning | `completed`, svaret grundat i kunskapsbasen |
| `POST /api/inbox/mock` | 6 ärenden inlästa och processade |
| `POST /api/inbox/sync` | `connected: false` med kundvänlig text |

Det som fällde den gamla koden — `KeyError: 'conversation_id'` vid en
agentkörning — är alltså borta: körningen ovan gick hela vägen.

`health/ready` rapporterar fortfarande `degraded: true` med två varningar, och
båda är sanna och sedan tidigare kända: ingen IMAP-inkorg är kopplad, och det
finns ingen riktig sändväg (godkända svar loggas, de skickas inte till kund).
Ingen av dem är en följd av cutovern.

### Det som INTE är gjort

`SNAJP_SUPPORT_URL` på Vercel pekar fortfarande på den gamla backenden. Nu när
koden i railway-main faktiskt kan köra är det ett beslut, inte en blockering.

### Historik: så såg blockeringen ut (2026-08-21 kväll)

Cutovern av `snajp.vercel.app` till Railway är förberedd men **blockerad**, och
blockeringen är en grendivergens — inte något som går att lösa med en flagga.

### Vad som ÄR gjort

| Steg | Läge |
|---|---|
| API-nycklar i railway-main | `RAILWAY_MAIN_KEY_SNAJP`, `RAILWAY_MAIN_KEY_LIVRUSTNING` utfärdade |
| Livrustnings agentprofil | **Migrerad**: 22 KB-artiklar, 8 fackregler, ICP och autonomi |
| Vektorer i railway-main | 41 skrivna, 0 misslyckade — livrustning 22/22, nordlys 16/16, public-demo 3/3, alla 1536 dim |
| Migrationskedjan i railway-main | 82 av 82 |

Migreringen gjordes med `scripts/migrera_till_railway.py` via API:t, inte via
SQL: båda ändarna scopar varje läsning på tenanten nyckeln pekar ut, så två
kunder kan per konstruktion inte blandas ihop.

### Blockeringen

`railway-main` står på `0329452` från **16 augusti**. `development` är 158
commits före — och `railway-main` har samtidigt **22 egna commits** som
development saknar. Grenarna har alltså divergerat, och 61 filer skiljer.

Följden är mätbar, i två riktningar:

* **Gammal kod mot nytt schema.** En agentkörning mot railway-main faller med
  `KeyError: 'conversation_id'`. Databasen bär hela kedjan (jag körde den i
  morse), koden gör det inte.
* **Dimensionskrocken.** `POST /api/kb` svarade 500 tills jag tillfälligt tömde
  `GEMINI_API_KEY`: koden saknar `dimensions=1536` och skickade en 3072-vektor
  mot en `vector(1536)`-kolumn. Nyckeln är återställd, och vektorerna räknades i
  stället LOKALT med den rättade koden (`scripts/fyll_embeddings.py --env main`).

### Vad som måste bestämmas

Migrationsnumren har förgrenat sig: `030` heter `suppressions_tenant_scope` i
development och `snajp_web_role` i railway-main. Innehållet finns sannolikt i
båda grenarna, men under olika filnamn — och båda kedjorna är redan APPLICERADE
i var sin databas.

Det går alltså inte att merga mekaniskt. Två vägar:

1. **Force-push** `development` → `railway-main`. Snabbast, men kastar 22
   commits ur den grenens historik. Kräver ett uttryckligt ja — det står i
   CLAUDE.md att force-push som skriver över annans arbete alltid gör det.
2. **Merge** och stäm av migrationsfilerna mot liggaren i båda databaserna, så
   att inget körs två gånger under ett annat namn.

Förrän en av dem är gjord ska `SNAJP_SUPPORT_URL` på Vercel **inte** peka om.
Kunskapsbasen finns nu i Railway, men agenten som ska svara ur den kan inte
köra.

## Railway: BÅDA miljöerna är i kapp (2026-08-20 kväll)

Migrationskedjan är körd hela vägen i både `railway-development` och
`railway-main`. Ingen migration väntar i någondera miljön.

| Miljö | Före | Efter |
|---|---|---|
| `railway-development` | stod just före `039` | hela kedjan, inklusive 039 och 040 |
| `railway-main` | 36 av 82 | 82 av 82 — 46 migrationer körda i en följd |

**Verifierat direkt mot databasen, inte via API:t:** `prospects.origin` finns,
`public.workspace_tenant_keys` finns, och båda versionerna står i
`supabase_migrations.schema_migrations`. Ett API-svar hade bara visat att
tjänsten svarar; frågan var om kolumnen finns.

`verify_railway.py` säger numera **"Alla kontroller gröna, båda miljöerna"** —
inklusive radsäkerhet på varje publik tabell, `snajp_app`/`snajp_web` utan
BYPASSRLS, och korskopplingen (mains nyckel avvisas av dev-api och tvärtom).

Två skarpa prov, inte bara gröna kontroller:

* **Exempelbolag i drift.** `POST /api/leads/prospects/exempel` mot
  dev-deployen skapade `Eknäs Bygg Gruppen AB` med `origin='example'`. Raden
  ligger kvar i dev; den kan aldrig mejlas (spärr noll i
  `scheduler._kor_send_guard`).
* **Plattformsadmin.** `admin_cleanup.py --diagnos` säger
  `isPlatformAdmin() som appen . True` i BÅDA miljöerna. Frågan ställs som
  `snajp_web` med `app.user_id` satt, alltså med RLS påslagen — som `postgres`
  (BYPASSRLS) hade den sett rätt ut även när den inte var det. Det var precis
  den blindheten som lät rekursionen i `033` ligga oupptäckt.

**LLM-nyckeln i `main` är lagad.** Värdet hade ett tecken utanför ASCII på
position 0 och kunde därför inte skickas i ett Authorization-huvud. Kandidaten
prövades mot DeepSeek FÖRE skrivning (status 200), och `/health/ready` gick
från `simulation` till `live` 50 sekunder efter omdeployen.

### Fällan som kostade en körning

`railway_gor_klart.py` startar varje steg med `sys.executable`. Körd med
systemets Python — som saknar `psycopg2` — föll alla fem databassteg på
`ModuleNotFoundError`, ett i taget, medan sammanfattningen ändå avslutade med
"exempelbolagsvägen: GRÖN". Skriptet kontrollerar numera tolken före planen.
Kör det med en tolk som har beroendena:

```bash
snajp-support/.venv/Scripts/python.exe scripts/railway_gor_klart.py --apply
```

### Testytorna är kopplade — en tenant var (2026-08-20 kväll)

Migration 040 ger nya konton en egen tenant. Den körs bara för NYA konton, så
nio arbetsytor i development stod kvar med `slug = null` — och
`requireSnajpTenant()` svarar 409 på varenda av deras egna ytor. En testkund
som inte kan använda produkten testar ingenting.

`scripts/koppla_testytor.py --env development --apply` kopplade fem av dem.
Uppmätt efteråt:

| Arbetsyta | Slug | Egen KB | Egen nyckel |
|---|---|---|---|
| Test Testsson workspace | `testkund-50287cb4` | 16 artiklar | ja |
| Demo workspace | `testkund-1fc3df92` | 16 artiklar | ja |
| Testkund 66677210 workspace | `testkund-1d8909f0` | 16 artiklar | ja |
| Testkund 67000961 workspace | `testkund-02ae648c` | 16 artiklar | ja |
| Testkund 68331404 workspace | `testkund-b5aa5b93` | 16 artiklar | ja |

**Fem arbetsytor, fem SKILDA tenants.** En delad tenant hade gett en. Ingen av
dem kan längre grunda ett svar i ett annat bolags villkor.

Fyra arbetsytor hoppades över: de saknar profilrader helt. Kopplingen sker i
den inloggades namn (`app.user_id`), så en arbetsyta utan medlem har ingen att
göra det som — de listas i stället för att gissas åt.

Den gamla delade `testkund`-tenanten har nu exakt EN arbetsyta kvar och är
därmed i praktiken isolerad den också.

### Kvar i Railway-miljöerna — inte migrationer

Två noteringar står kvar i driftkontrollen, båda i BÅDA miljöerna, och båda är
kända öppna trådar snarare än fel:

* **IMAP saknas** — inga inkommande mail hämtas i någon Railway-miljö.
* **Ingen riktig sändväg** — godkända svar loggas men skickas aldrig till kund.

## 041_delete_grants — körd i BÅDA Railway-miljöerna 2026-08-21

`snajp_app` hade `select, insert, update` på arton tabeller sedan migration
009, och `alter default privileges` upprepade samma tre för allt som skapats
sedan dess. Aldrig `delete`.

Det märktes först 2026-08-21: `POST /api/inbox/mock` svarade 500 med
`permission denied for table ss_emails`. Det gick alltså inte att generera ett
enda testmejl i någon miljö som kör med den roll INV-SEC-001 kräver. Två skäl
till att det låg dolt — bara två kodvägar i hela backenden gör DELETE, och
sviten kör mot MemoryStorage, som inte har några rättigheter att sakna.

Kört och verifierat i `development` och `main` (`= 041_delete_grants` i
liggaren, och `/api/inbox/mock` svarar 201 med sex mejl).

**Supabase-produktionen har SAMMA lucka och den är INTE åtgärdad.** Den är
ofarlig där just nu eftersom `DATABASE_URL` fortfarande pekar på en roll med
BYPASSRLS — men den blir akut i samma sekund som `snajp_app`-övergången görs,
och den övergången är redan blockerad av 028. Kör 041 tillsammans med 028.

## Fortfarande öppet — inte migrationer

1. **`SNAJP_MASTER_API_KEY` på Vercel.** Utan den svarar `/api/admin/*` med
   503 och ett meddelande som namnger variabeln.
2. **`snajp_app`-rollens lösenord är nu satt** (2026-08-15, med ditt
   godkännande). Rollen är `nobypassrls` och verifierad: RLS-isoleringstestet
   kördes skarpt mot produktionen som den rollen och gav noll rader för fel
   tenant. Det är första gången INV-SEC-001 är BEVISAD och inte bara påstådd.

   **Men cutovern är blockerad av `028` — läs nästa avsnitt innan du byter
   DATABASE_URL på Render.**

   Lösenordet står i klartext i den här sessionens transkript, eftersom det
   fick skrivas in i ett SQL-anrop. Rotera med en rad om det stör:
   `alter role snajp_app with password '<nytt>';`
3. **`SNAJP_KEY_LIVRUSTNING` på Vercel.**
4. **Leaked-password-skyddet** i Supabase Auth → Providers → Email. Rådgivaren
   flaggar det fortfarande.
5. **OAuth-konsolerna** (Google Cloud, Microsoft Entra). Checklista i `AUTH.md`.

## Kvarvarande rådgivarvarningar som är avsiktliga

- `current_workspace_id()` går att anropa som `anon` och `authenticated`.
  Avsiktligt: den anropas inifrån varje workspace-scopad RLS-policy, och de
  policyerna gäller rollen `public`. Utan graden får anon ett behörighetsfel
  i stället för noll rader — samma resultat, sämre form. Funktionen läser
  bara anroparens egen workspace via `auth.uid()` och läcker ingenting.
- `ensure_workspace_for_current_user()` går att anropa som `authenticated`.
  Krävs — `app/auth/callback/route.ts` anropar den efter inloggning.
- `vector` i public-schemat och `chorus_*`-funktionernas search_path är äldre
  än det här arbetet och rörs inte här.

## 028 — MÅSTE köras innan DATABASE_URL byts till snajp_app

**Skriven men INTE applicerad.** Den skriver om 33 RLS-policyer i produktionen,
och det ska du se först.

Uppmätt mot produktionen: `set_config('app.tenant_id', <id>, true)` är
transaktionslokal, men efter COMMIT återgår GUC:en till `''` — inte NULL. En
custom-GUC som aldrig satts på sessionsnivå har tom sträng som utgångsvärde,
och varken `RESET` eller `set_config(..., NULL, false)` gör den NULL igen
(båda testade).

Följden på en POOLAD anslutning: så fort en skopad fråga har körts möter varje
senare **oskopad** fråga policyer som gör `''::uuid` och kastar
`invalid input syntax for type uuid: ""`.

Vad som går sönder vid cutovern:

- `ss_tenants.tenant_lookup` (`current_setting(...) IS NULL`) slutar gälla, och
  `tenant_self` kastar på castet. **`list_tenants()` är det schemaläggaren
  använder för att räkna upp kunder.**
- `list_agent_runs_all`, `get_agent_run`, `list_platform_events` — adminvyns
  oskopade läsningar — kastar likadant.
- Dessutom, redan verifierat: `list_agent_runs_all` ger **noll rader** under
  `snajp_app` även utan kraschen, eftersom `agent_runs.tenant_isolation` kräver
  ett satt `app.tenant_id`. Adminvyn hade visat en tom lista som ser ut som
  "inga körningar" i stället för som ett fel. `list_tenants_with_stats` ger då
  fyra kunder med nollställda siffror — **trovärdiga men fel tal**, vilket är
  värre än tomt.

Buggen har legat latent sedan multi-tenancy infördes. Ingen har märkt den
eftersom backenden kör som `postgres` med BYPASSRLS och policyerna aldrig
evalueras.

## SQL-vägarna — verifierade utan att kunna köra koden

Backenden har ingen `DATABASE_URL` i den här miljön (lösenordet bor bara på
Render), så `PostgresStorage` går inte att köra härifrån. I stället kördes
**exakt de frågor metoderna skickar** mot produktionsschemat. Det fångade tre
buggar som hade kraschat vid första riktiga anropet:

1. `list_review_queue` sorterade på `om.created_at` — `outreach_messages` har
   ingen sådan kolumn.
2. Samma query läste `t.prospect_email` — `outreach_threads` har `prospect_id`.
3. Följdfynd, äldre än det här arbetet: `get_outreach_thread` returnerade
   `select *`, och `scheduler.py` läser `prospect_email` ur resultatet. Mot
   Postgres hade varje utskick adresserats till strängen `"okänd"`.

Alla tre rättade och omkörda. Läsvägarna ger riktiga rader
(`list_tenants_with_stats` → fyra kunder); skrivvägarna kördes och städades:
`generate_series`-inserten, upserten på `agent_configs`, `platform_events` och
den dynamiska SET-listan i `update_prospect`.

**Uppdatering:** Python-koden HAR nu körts mot Postgres, som `snajp_app`.
`PostgresStorage` exercerades skarpt — `list_tenants_with_stats`,
`get_agent_settings`, `set_agent_settings`, `list_review_queue`,
`count_rate_events`, `record_rate_events`, `log_platform_event`,
`list_platform_events`. All testdata raderad och frånvaron kontrollerad.
Hela sviten kör nu 448 gröna med **noll överhoppade** — RLS-testet kördes för
första gången.

Det var den körningen som hittade `028` ovan.

Kvarstår att göra efter deploy:

```bash
bash scripts/verify_inv_sec_010.sh https://<deploy>
```

och en riktig leads-körning mot en testtenant, för att se en `agent_runs`-rad
skapas av koden och inte av en handskriven insert.
