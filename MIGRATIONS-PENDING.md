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

### Kvar i Railway-miljöerna — inte migrationer

Två noteringar står kvar i driftkontrollen, båda i BÅDA miljöerna, och båda är
kända öppna trådar snarare än fel:

* **IMAP saknas** — inga inkommande mail hämtas i någon Railway-miljö.
* **Ingen riktig sändväg** — godkända svar loggas men skickas aldrig till kund.

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
