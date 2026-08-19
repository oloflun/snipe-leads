# Railway-stacken

Den enade stacken, byggd vid sidan av den befintliga. Produktionen och
`development`-flödet är orörda — se [`DEPLOY.md`](DEPLOY.md) för dem.

## Två miljöer

Projekt `brave-passion`. Varje miljö har **egna** `api`, `web` och `Postgres`.

| Miljö | Gren | web | api |
|---|---|---|---|
| `main` | `railway-main` | `web-production-1fe2c.up.railway.app` | `api-production-d7695.up.railway.app` |
| `development` | `railway-development` | `web-development-6c85.up.railway.app` | `api-development-5cc3.up.railway.app` |

Push till grenen deployar miljön. `main` och `development` (de riktiga grenarna)
rörs INTE — de håller Vercel/Render vid liv så de två stackarna går att jämföra
mot varandra.

Grenen bärs av **deployment-triggern**, som är miljöspecifik. `serviceConnect`
sätter tjänstens default-gren och gäller alla miljöer — fel verktyg här, och
frånvaron av en miljöspecifik gren är vad som lät web bygga fel gren i tre
deployer i rad.

## Kommandon

```bash
python scripts/railway_provision.py --apply            # båda miljöerna, idempotent
python scripts/railway_migrate.py --env development --apply
python scripts/railway_seed_dev.py --apply             # spegla main -> development
python scripts/verify_railway.py                       # driftkontroll, båda miljöerna
python scripts/keys.py --push-railway                  # LLM-nycklar till båda + verifiera
python scripts/admin_cleanup.py --env railway-development --diagnos  # varför 404 på /admin?
python scripts/admin_cleanup.py --env railway-development            # skapa/laga adminraden
```

## Dataspegeln — envägs, och låst åt det hållet

`development` ska vara en 1:1-kopia av `main` så att en ändring kan utvärderas
med allt annat lika. Data flödar **bara** main → development. Tillbaka går
enbart strukturella ändringar, genom migrationskedjan.

```
main ──── railway_seed_dev.py ────> development     (data, på begäran)
main <─── railway_migrate.py ────── development     (bara schema)
```

Kunddata som testkörningar skapar i dev har **ingen** kanal till main. Tre
spärrar, inte en konvention:

1. **Målet är hårdkodat** till `development`. Ingen `--target`-flagga finns.
2. **Markörtabellen `public.mirror_meta`.** Skriptet vägrar skriva till en
   databas vars markör inte säger `development`, och vägrar LÄSA från en som
   har en markörrad alls — att spegla en spegel är alltid ett misstag.
   `main` saknar tabellen och kan därför aldrig bli mål.
3. **INV-DATA-001** — statisk invariant som fäller en `--target`-flagga, ett
   omskrivet mål, eller en bulk-COPY mot main i någon annan scriptfil.

Båda runtime-spärrarna är prövade negativt i drift: main nekades som mål, dev
nekades som källa. Verifierat med riktiga rader att en agentkörning i dev
skrev till dev (5 ärenden) och lämnade main orörd (4).

Speglingen använder `COPY (format binary)` via psycopg2 — inga
postgres-klientbinärer finns lokalt. `session_replication_role = replica`
stänger av både främmande nycklar och triggern `on_auth_user_created` under
kopieringen; utan det skapar varje kopierad `auth.users`-rad ett extra
workspace.

### Konsekvensen att känna till

En 1:1-spegel innebär att mains **tenant-nycklar och kunddata också finns i
dev**. Det är oundvikligt om agenterna ska bete sig identiskt, och det är samma
avvägning som preview-spegeln i `CLAUDE.md`. Dev ska därför behandlas med samma
sekretess som produktionen.

Det som INTE delas är miljöernas egna hemligheter — se tabellen nedan.

## Vad som skiljer miljöerna åt

Sex värden är per miljö med flit. Ett delat värde här är tyst korskoppling.

| Variabel | Varför den inte får delas |
|---|---|
| `AUTH_SECRET` | Delad ⇒ en sessionscookie utfärdad i dev är giltig i main. |
| `DATABASE_URL` | Egen databas per miljö. Literalt värde, inte referens. |
| `SNAJP_MASTER_API_KEY` | Delad ⇒ dev-nyckeln öppnar mains `/api/admin`. |
| `SNAJP_DEMO_API_KEY` | Delad ⇒ dev-frontend kan tala med main-backend obemärkt. |
| `SNAJP_SUPPORT_URL` | Måste peka på samma miljös api. |
| `NEXT_PUBLIC_SITE_URL` | Måste peka på samma miljös web. |

`verify_railway.py` mäter det: mains demo-nyckel ska ge **401** mot dev-api och
tvärtom. Uppmätt, inte antaget.

`verify_railway.py` är den som räknas. Den frågar Railway och Postgres i
stället för att läsa en fil, eftersom fälten som styr driften — gren,
byggkontext, roll, radsäkerhet — inte syns i någon diff.

## Fyra fällor som slog till på riktigt

**1. `.dockerignore` var en allowlist skriven för api.** Den släppte in
`agent-core` och `snajp-support/app` och inget annat, och gällde alla tjänster.
web-bygget föll på `"/package-lock.json": not found` — inte ett fel i
Next-appen, utan hela Next-appen bortfiltrerad innan bygget började.
Allowlisten bor numera i `snajp-support/Dockerfile.dockerignore`; BuildKit läser
`<Dockerfile>.dockerignore` före repo-rotens, så båda tjänsterna kan ha rätt.

**2. Grenen sattes aldrig.** `serviceCreate` med bara `source: {repo}` väljer
tyst repots default-gren. `web` byggde `development` i tre deployer i rad medan
felsökningen letade i byggkontexten — felmeddelandet var sant, men beskrev en
annan commit. `INV-DEPLOY-002` spärrar det nu.

**3. Healthchecken pekade på en route som inte fanns**, så deployen fastnade i
`DEPLOYING` i stället för att gå live. Svaret var inte att ta bort grinden utan
att bygga `/api/health` — utan healthcheck går ett trasigt bygge live tyst.

**4. Cloudflare svarar 403 (error 1010) på Python-urllibs default-UA.** Det ser
ut som ett auth-fel och är det inte. `scripts/railway.py` sätter en egen
User-Agent.

## Byggkontexten — det som fällde Render två gånger

`agent-core/` ligger utanför `snajp-support/`, och Docker kan inte `COPY` något
utanför sin byggkontext. På Railway: Root Directory **tom** (`/`) plus
`dockerfilePath: snajp-support/Dockerfile`. Verifierat i bygglogg —
`[6/7] COPY agent-core ./agent-core` går igenom — och i drift: en skarp
agentkörning nådde `client.chat.completions.create`, alltså efter att skill,
overlay och `agent-core/AGENTS.md` alla laddats. Hade `agent-core` saknats hade
den fallit tidigare, på `UnknownSkillError`.

## Auth utan Supabase

Auth.js (NextAuth v5), lösenord med `node:crypto` scrypt, Google och Microsoft
via providers. **Identiteten bor kvar i `auth.users`** — samma tabell, samma
uuid:n, samma fyra främmande nycklar. Bara skrivaren byts, så triggern
`on_auth_user_created` och hela inbjudningsmodellen håller oförändrade.

`railway/000_auth_compat.sql` bygger `auth`-schemat, `auth.users` och en
`auth.uid()` som läser GUC:en `app.user_id`. Kartläggningen visade att 15 av 17
policyer går genom den enda funktionen: byts kroppen följer alla med, och
migration 000–033 kan köras **oförändrade**.

**Sessionen bär bara identitet.** Onboardingstatus låg först som ett anspråk i
token och gav en loop i drift: raden skrevs, cookien sa fortfarande false, och
`unstable_update` skrev inte om den. En token är en ögonblicksbild; föränderligt
tillstånd läses färskt (`lib/auth/onboarding-gate.ts`). `INV-AUTH-001` spärrar
återfall.

## Roller

| Roll | Används av | BYPASSRLS |
|---|---|---|
| `snajp_app` | backenden | nej |
| `snajp_web` | Next-appen | nej |
| `postgres` | migrationer | ja (ägare) |

Ingen av approllerna får kringgå radsäkerheten. Tabellägaren gör det utan att
något syns i en diff, och resultatet blir trovärdiga men felaktiga siffror —
felet migration 029 fick städa upp.

## Gren-miljöer — mätt, inte antaget

`environmentCreate` med `sourceEnvironmentId` klonade alla tre tjänsterna, gav
var och en en egen publik domän (`api-gren-test`, `web-gren-test`) och
provisionerade en egen Postgres. Inga manuella steg. På nuvarande stack krävde
motsvarande fyra: Supabase-gren, Render-tjänst, Vercel-scope och variabler för
hand.

**Men det är inte gratis.** `DATABASE_URL` var satt som en referens
(`${{Postgres.RAILWAY_PRIVATE_DOMAIN}}`) och löstes INTE ut i klonen — api
startade med `storage: memory`, och en omdeploy hjälpte inte. En ärlig
`/health/ready` gjorde det synligt direkt i stället för att låta miljön se frisk
ut. Kloning ger dessutom infrastruktur, inte data: den nya databasen är tom och
migrationskedjan måste köras.

Nettot är ett manuellt ingrepp i stället för fyra, inte noll i stället för fyra.

## Plattformsadmin — raden som migrationskedjan inte skapar

`/admin` grindas av `getPlatformAdmin()`, som läser `public.platform_admins`.
Den raden skapas av `scripts/admin_cleanup.py`, **inte** av migrationskedjan.
Skriptet hade tidigare bara Supabase-miljöer (`production`, `preview`), så
Railway-stacken hade ingen ingång alls — och symptomet är tyst, eftersom
`isPlatformAdmin()` är fail-closed med flit:

* `/admin` och `/admin/*` svarar **404** för rätt person.
* `/dashboard` slutar dirigera till adminytan, eftersom den dirigeringen är
  villkorad på samma uppslag. Inloggningen ser alltså ut att "gå till fel
  ställe" när den i själva verket går till enda stället som finns.

Uppmätt 2026-08-19 mot **båda** Railway-miljöerna: inloggningen lyckades,
`/api/auth/session` gav `snajpsupport@gmail.com`, och varje `/admin*` gav 404.
Koden var rätt och deployad — `/login` byggd från grenens HEAD var byte-identisk
med den utcheckade koden. Det som saknades var raden.

```bash
python scripts/admin_cleanup.py --env railway-development --diagnos   # bara läsa
python scripts/admin_cleanup.py --env railway-development             # skapa/laga
python scripts/admin_cleanup.py --env railway-main
```

DSN:en byggs av `RAILWAY_{MAIN,DEVELOPMENT}_PG_{PASSWORD,HOST,PORT}` i
`.env.deploy` — samma variabler som `railway_migrate.py` läser, och samma
miljöprefix, så `--env railway-development` inte kan träffa main.

`--diagnos` ställer adminfrågan **som appen ställer den**: som `snajp_web`, med
`app.user_id` satt, så att RLS-policyn evalueras. Som `postgres` (BYPASSRLS)
evalueras ingen policy och svaret ser rätt ut även när det inte är det — precis
den blindheten som lät den självrefererande policyn i `020` ligga oupptäckt
(se `033`).

### Speglingen tar med sig frånvaron

`railway_seed_dev.py` kopierar alla publika tabeller **inklusive**
`platform_admins`. Saknas raden i `main` saknas den i `development` efter varje
spegling. Kör därför skriptet mot `railway-main` först, och mot
`railway-development` efter varje `--apply` av spegeln.

## Kvar att lösa

- **Utgående mail saknas i hela kodlinjen.** Magic link och
  lösenordsåterställning svarar därför ärligt att de inte är kopplade, i stället
  för att lova ett mail som aldrig lämnar servern.
- **`DEEPSEEK_API_KEY` i `snajp-support/.env` är korrumperad** (`\xe0` på
  position 0 och 2). Backenden upptäcker det nu vid start och går i
  simuleringsläge i stället för att falla på första anropet, men en skarp
  agentkörning kräver en ny nyckel.
- **OAuth-nycklar är inte satta** (`AUTH_GOOGLE_ID`,
  `AUTH_MICROSOFT_ENTRA_ID_ID`). Providrarna registreras bara när de finns.
