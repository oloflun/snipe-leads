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

## 039 och 040 — SKRIVNA, INTE KÖRDA (2026-08-20)

Koden som använder dem är deployad. Båda är additiva och kan köras när som
helst; ingen av dem rör befintliga rader.

| Migration | Vad den ger | Vad som INTE fungerar förrän den körts |
|---|---|---|
| `039_prospect_origin` | `prospects.origin` (`manual`/`example`/`import`) | Exempelbolagen. `POST /api/leads/prospects/exempel` svarar med ett förklarande fel; vanliga prospekt skapas som förut (fallback i `postgres.create_prospect`). |
| `040_testkund_egen_tenant` | `workspace_tenant_keys` + `link_test_tenant()` + `tenant_api_key_for_current_workspace()` | Egen tenant per testarbetsyta. Onboardingen faller tillbaka på den DELADE `testkund`-tenanten — alltså dagens beteende, med delad kunskapsbas. |

Fallbackarna är avsiktliga och inte tysta: koden deployas från grenen och
migrationerna körs av en människa med databaslösenordet, så de landar aldrig
samtidigt. En ny kolumn får inte ta ner den befintliga pipelinen under den
timmen.

```bash
python scripts/railway_migrate.py --env development --apply
```

**Mätt 2026-08-20 mot Railway-development, utan databasanslutning:** `GET
/api/leads/prospects` (dev-api, demo-nyckeln) svarar 200 och raden saknar
fältet `origin`. Migration 039 är alltså inte körd där. Fälten från `031`
(`orgnr`, `ort`, `postnr`, `sni`, `website`, `anstallda`, `omsattning`,
`foretagsnyckel`) finns däremot allihop, så kedjan står stilla just före 039.

Provet är läsande och kostar ingenting — till skillnad från
`POST /api/leads/prospects/exempel`, som skapar rader om kolumnen finns. Det
skiljer "inte körd" från "körd men trasig" utan att röra data.

Kommandot kräver `RAILWAY_DEVELOPMENT_PG_{PASSWORD,HOST,PORT}` i `.env.deploy`.
Verifiera efteråt som `authenticated` med ett riktigt konto, aldrig som
`postgres` — se lärdomen från 030–033 ovan.

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
