# Railway-stacken

Den enade stacken, byggd vid sidan av den befintliga. Produktionen och
`development`-flödet är orörda — se [`DEPLOY.md`](DEPLOY.md) för dem.

## Vad som kör

| Tjänst | Bygge | URL |
|---|---|---|
| `api` | `snajp-support/Dockerfile`, byggkontext repo-roten | `api-production-d7695.up.railway.app` |
| `web` | railpack (Next) | `web-production-1fe2c.up.railway.app` |
| `Postgres` | `postgres-ssl:17` + volym | privat nät, TCP-proxy för migrationer |

Projekt `brave-passion`, miljö `production`, gren `feature/railway-stack`.

## Kommandon

```bash
python scripts/railway_provision.py --apply   # skapa/uppdatera tjänster, idempotent
python scripts/railway_migrate.py --apply     # kör migrationskedjan
python scripts/verify_railway.py              # driftkontroll mot verkligheten
```

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
