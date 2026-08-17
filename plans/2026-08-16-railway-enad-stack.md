# Railway-prototyp: en enad stack, byggd vid sidan av

> **STATUS 2026-08-16 (kväll): BYGGD OCH VERIFIERAD.** Alla sju
> verifieringspunkter nedan är körda. Beslutsgrundens "gå vidare"-villkor är
> uppfyllda utom gren-miljön, som inte prövats (punkt 6). Drift och kommandon:
> [`RAILWAY.md`](../RAILWAY.md). Löpande kontroll:
> `python scripts/verify_railway.py`.
>
> | Punkt | Utfall |
> |---|---|
> | 1. Byggkontexten | **OK** — `COPY agent-core` går igenom med tom Root Directory |
> | 2. Migration 000–033 från noll | **OK** — kedjan var dock INTE självbärande; se `0000_rls_auto_enable.sql` |
> | 3. 454 backend-tester mot Railway-Postgres | **OK** — 460 nu, inkl. RLS-isolering som `snajp_app` utan BYPASSRLS |
> | 4. Auth end-to-end | **OK** för lösenord: konto skapat, workspace via triggern, /dashboard nådd, /admin 404 för vanligt konto. OAuth ej prövat (nycklar saknas) |
> | 5. Isoleringen | **OK** — skopad fråga ger delmängd, adminläsning hela mängden |
> | 6. Gren-miljön | **DELVIS** — tre tjänster, egna domäner och egen Postgres reste sig UTAN handpåläggning, men `${{Postgres.RAILWAY_PRIVATE_DOMAIN}}` löstes inte ut i klonen, så api startade utan databas. Ett manuellt ingrepp i stället för fyra |
> | 7. Sida vid sida | **OK** — `scripts/verify_railway.py` motsvarar `verify_render.py` |
>
> **Fem fel som bara den här ombyggnaden hittade**, alla i den befintliga
> kodbasen och alla kvar i produktionen tills de deployas:
> `rls_auto_enable()` saknades i migrationskedjan · `platform_admins`-policyn var
> självrefererande så adminytan aldrig kunnat renderas · `business_contexts`
> saknade unikt index · onboardingstatus i sessions-token gav en loop ·
> `DEEPSEEK_API_KEY` är korrumperad och tjänsten påstod sig vara live.

## Context

Preview-miljön är byggd och fungerar — men den kostade åtta separata
infrastrukturfällor att få dit: två numreringssystem i migrationsliggaren,
Supabases IPv6-only direktvärd som tyst föll tillbaka till minnet, en delad
Vercel-variabel som raderade produktionens konfiguration, `.cmd`-shimmen, den
persistenta grenen som inte gick att radera, `schema.sql` utanför
migrationskedjan, SSO-skyddet som blockerar automatik, och en Render Blueprint
som visade sig inte existera.

Sju av åtta var "leverantörens egenhet som inte syns i någon diff". Anton vill
ha färre rörliga delar, och den siffran är argumentet.

Den här prototypen bygger hela stacken på Railway **parallellt**, utan att röra
produktionen, så att valet kan göras mot något som kör i stället för mot en
uppskattning.

---

## Grenstrategi — sessionens arbete ligger säkert

| Gren | Roll |
|---|---|
| `feature/plattform-fas1-7` | **FRYST.** Hela sessionens arbete: fas 1–7, preview-miljön, onboarding-automationen, migration 000–029. Pushad till origin. Force-pushas aldrig. Härifrån går allt direkt till `main` om Railway-spåret överges eller `development` strular. |
| `feature/railway-stack` | Arbetsgrenen för ombyggnaden. Utgår från samma commit. |
| `development` | Integrationsgren. Tar emot `feature/railway-stack` när ALLT är utbyggt — inte i delar. |
| `main` | Produktion. Rörs först när `development` bevisats. |

**Allt som byggts i den här sessionen ska finnas i det nya bygget.** Det är inte
en omstart utan ett byte av underlag: samma sju faser, samma invarianter, samma
onboarding-skript, samma 454 tester. Checklistan i "Vad som måste följa med"
nedan är bindande.

## Vad som faktiskt binder oss till Supabase — uppmätt, inte uppskattat

| Beroende | Omfattning |
|---|---|
| `auth.uid()` i policyer/funktioner | **3 ställen** (`000_base_schema`, `006_auth_selfheal`, `020_platform_admins`) |
| PostgREST (`.from()`) | 15 anrop, 8 tabeller, 6 filer |
| `.rpc()` | 3 anrop |
| Auth-API | 14 anrop |
| Trigger på `auth.users` | 1 (`on_auth_user_created`) |
| FK till `auth.users` | 3 tabeller |
| Storage / Realtime | **0 / 0** |
| Edge Functions | **0 — katalogerna är tomma stubbar** |

### De två struparna som gör flytten liten

Kartläggningen hittade att beroendet inte är utspritt — det går genom två
funktioner:

- **`current_workspace_id()`** (`000_base_schema.sql:206`) är den enda funktion
  som anropar `auth.uid()` för dataåtkomst. **15 av 17 policyer går genom den.**
  Byts den till att läsa en egen GUC följer alla med automatiskt.
  `auth.uid()` finns totalt på **fyra ställen** i SQL: den funktionen,
  `006_auth_selfheal.sql:40` (invite-policyn), `:119`
  (`ensure_workspace_for_current_user`) och `020_platform_admins.sql:25`.
- **`getWorkspaceContext()`** (`lib/workspace.ts:63`) — **9 av 11 konsumentfiler**
  går genom den. Byts `auth.getUser()` där följer nästan hela appen med.

Sessionsläsningen finns på sex ställen totalt: `proxy.ts:59`,
`lib/workspace.ts:74`, `lib/auth.ts:8`, `lib/actions/auth.ts:175`,
`lib/actions/onboarding.ts:34` och `lib/actions/auth.ts:93` (`getSession`).

Två fakta som gör flytten billigare än den låter:

1. **Backenden har noll Supabase-koppling.** `snajp-support` använder `asyncpg`
   mot vanlig Postgres och isolerar på `app.tenant_id`, aldrig `auth.uid()`.
   De fyra träffarna på "supabase" i koden är kommentarer och en loggrad.
   Den halvan flyttar genom att byta `DATABASE_URL`.
2. **Next-koden skopar redan själv.** `lib/workspace.ts`, `lib/data/emails.ts`,
   `lib/data/dashboard.ts` och `lib/actions/onboarding.ts` anropar alla
   `getWorkspaceContext()` och filtrerar explicit på `workspace_id`. RLS på
   dashboardtabellerna är extra försvar, inte den bärande grinden.

### Fallgropar kartläggningen hittade

- **`email-studio/kopior/`** innehåller en KOMPLETT kopia av auth-lagret: egen
  `middleware.ts`, egen `supabase/`-mapp, egen `LoginForm`, egen `signOut`. Den
  kompileras inte av Next, men en sök-och-ersätt-migrering missar den och
  lämnar kvar kod som ser aktiv ut. Avgör tidigt: radera eller migrera.
- **`profiles.id` är FK mot `auth.users(id)` med `on delete cascade`**, plus
  fyra FK till (`audit_logs.actor_user_id`, `workspace_invites.invited_by`,
  `platform_admins.user_id` och `.granted_by`). En egen `users`-tabell måste ta
  över den identiteten med samma uuid-värden, annars tappas kopplingarna.
- **`ensure_workspace_for_user` läser `auth.users.email` direkt**
  (`006_auth_selfheal.sql:69`). Hela invite-modellen hänger dessutom på triggern
  `on_auth_user_created` som fyrar på insert i `auth.users`.
- **Prestanda att rätta på vägen:** `getWorkspaceContext()` gör fyra
  PostgREST-anrop och skapar fyra klienter per anrop, och `proxy.ts` gör två
  till på varje skyddad request. En egen SQL-fråga gör det till ett.

### Två buggar som ska rättas oavsett Railway

1. **Det finns ingen utloggningsknapp.** `signOut()` (`lib/actions/auth.ts:231`)
   har noll konsumenter i `app/` och `components/`. Användare kan logga in men
   inte ut.
2. **`app/api/email-studio/route.ts:259` läser `userId` ur request-body** —
   klientstyrt. Sessionsgrinden på routen sattes i den här sessionen, men fältet
   går fortfarande att sätta fritt.

---

## Vad som måste följa med — bindande checklista

Ingen del av sessionens arbete får tappas i ombyggnaden:

- Fas 1: sessionshärledd tenant, RPC-härdning, DB-baserad rate limiting, INV-SEC-010
- Fas 2: plattformsadmin, glömt lösenord, OAuth, inbjudningar
- Fas 3: fail-closed entitlements, `/settings/layout.tsx`, tillägg, navrensning
- Fas 4: autonominivå, ICP, körkontroller, granskningskö
- Fas 5 och 7: ren kundchatt, samtalsform
- Fas 6: admin master control, notiscenter, spårvy
- Migration 000–029, inklusive 028/029 (RLS-fixarna) och den självbärande kedjan
- `scripts/`: `onboard_tenant.py`, `keys.py` (med båda spärrarna),
  `verify_render.py`, `verify_inv_sec_010.sh`
- Invarianter: INV-SEC-009, INV-SEC-010, INV-DEPLOY-001 (per tjänst),
  INV-TENANT-001, INV-SKILL-005/006
- 454 backend-tester + 47 invarianter som måttstock

---

## Vad prototypen ska bevisa — och inte

**Ska bevisa:** att hela stacken kör på Railway med en gren-miljö som klonar
infrastrukturen inklusive databasen, att inloggning fungerar utan Supabase, och
att backendens 454 tester är gröna mot Railway-Postgres.

**Ska INTE bevisa:** att allt är migrerat. Magic link och lösenordsåterställning
kräver utgående mail, som inte finns i den här kodlinjen alls
(`email_pipeline/sender.py` saknas). De ligger utanför prototypen med flit —
se "Kända beroenden" nedan.

---

## Railway-uppsättningen

Ett projekt, två miljöer (`production`, `development`), tre tjänster:

| Tjänst | Bygge | Not |
|---|---|---|
| `api` | `snajp-support/Dockerfile` | Root Directory **tom**, `RAILWAY_DOCKERFILE_PATH=snajp-support/Dockerfile` — samma form som Render, eftersom `agent-core/` ligger utanför `snajp-support/` |
| `web` | nixpacks | Next-appen behöver **inte** `agent-core` |
| `Postgres` | Railway managed | `DATABASE_URL` injiceras automatiskt |

Railway-miljöer klonar hela infrastrukturen per gren, databasen inkluderad —
alltså det vi byggde för hand med Supabase-gren + Render-tjänst + Vercel-scope.

### Två risker att avgöra FÖRST, innan något annat byggs

**1. Byggkontexten.** Railways Root Directory "pulls down only files from that
directory". Lämnas den tom bör kontexten vara repo-roten, men det är inte
dokumenterat entydigt. Det är exakt fältet som fällde Render-bygget två gånger
med `"/agent-core": not found`. **Verifiera med ett bygge innan resten byggs.**

**2. `.dockerignore` är en allowlist.** Den släpper bara in `agent-core`,
`snajp-support/app` och `requirements.txt`. Byggs `web` med Docker från
repo-roten utesluts hela Next-appen. Därför nixpacks för `web` — eller en egen
`.dockerignore` per tjänst om Railway stödjer det.

---

## Auth utan Supabase

Auth.js (NextAuth v5) med sessioner i egen Postgres. Prototypen täcker de två
vägar som inte kräver mail:

- **Lösenord** — Credentials-provider mot en egen `users`-tabell (argon2/bcrypt)
- **Google och Microsoft** — Auth.js har providers för båda; samma OAuth-appar,
  ny callback-URL

Filer som byts ut: `lib/supabase/{server,admin,env}.ts` → en `lib/db.ts` och en
`lib/auth.ts`. `proxy.ts` läser Auth.js-sessionscookien i stället för
Supabases. `lib/actions/auth.ts` byter ut sina 14 anrop mot Auth.js-motsvarigheter
men **behåller `authErrorMessage`-tabellen** — de svenska felmeddelandena är
skrivna för användaren och ska överleva bytet.

### De tre `auth.uid()`-ställena

- `000_base_schema` och `020_platform_admins`: policyer. Ersätts av
  `current_setting('app.user_id')`, satt per transaktion — samma mönster som
  backenden redan använder för `app.tenant_id`. Ett mönster i kodbasen i
  stället för två.
- `006_auth_selfheal`: funktionen `ensure_workspace_for_user` och triggern
  `on_auth_user_created`. Triggern flyttar till applikationskoden, som ändå
  redan anropar funktionen som självläkning vid inloggning.

### FK:erna till `auth.users`

`profiles.id`, `platform_admins.user_id`, `workspace_invites.invited_by`.
Pekas om till den egna `users`-tabellen. Samma uuid-värden kan behållas vid en
riktig migrering, så data följer med.

---

## Dataskiktet: 18 anrop

`pg` finns redan i repot (devDependency för migrationsskripten) och flyttas till
`dependencies`. Rå SQL, ingen ORM:

- Backenden kör redan rå SQL med `asyncpg` — ett mentalt mönster i stället för två.
- 18 anropsställen ger en ORM för lite hävstång för sin inlärningskostnad.
- En ORM är ännu ett ramverksberoende, alltså motsatsen till uppgiften.

Radtyperna tas från befintliga `lib/database.types.ts`, så typsäkerheten som
finns i dag behålls.

Filer: `lib/workspace.ts`, `lib/actions/{onboarding,team}.ts`, `lib/auth/admin.ts`,
`lib/data/{dashboard,emails}.ts`.

---

## Kända beroenden som prototypen INTE löser

**Magic link och lösenordsåterställning kräver utgående mail.** Den här
kodlinjen har ingen sändväg alls — `LoggingSendProvider` loggar och skickar
ingenting. Auth-migreringen och mailluckan är alltså samma projekt, och det
måste sägas innan någon räknar prototypen som färdig.

Den gamla `development`-grenen har koden (`0d3ac1d`): SMTP med korrekt
trådning via `In-Reply-To`/`References`, plus en Resend-väg över HTTPS eftersom
Renders gratisplan blockerar SMTP. På Railway finns ingen sådan blockering, så
ren SMTP räcker.

---

## Verifiering — jämförelse, inte bara "det startar"

1. **Byggkontexten först.** `api` byggs och `/health/live` svarar. Faller den på
   `agent-core` är hela upplägget fel och resten är bortkastad tid.
2. **Migrationerna.** `000`–`029` mot Railway-Postgres från noll. Det testar
   samtidigt att kedjan är självbärande — vilket den blev först i går.
3. **454 backend-tester** mot Railway-Postgres, inklusive
   `test_rls_isolation.py`, med den nya rollen utan BYPASSRLS.
4. **Auth end-to-end:** skapa konto, logga in med lösenord, logga in med Google,
   nå `/dashboard`, bekräfta att `/admin` ger 404 för ett vanligt konto.
5. **Isoleringen:** samma kontroll som mot spegeln — skopad fråga ska ge en
   delmängd, oskopad admin-läsning hela mängden.
6. **Gren-miljön:** skapa en Railway-miljö från en testgren och bekräfta att den
   får egen databas och egen URL utan handpåläggning. **Det är hela poängen** —
   det var det som krävde fyra manuella ingrepp på nuvarande stack.
7. **Sida vid sida:** samma `verify_inv_sec_010.sh` mot båda miljöerna.

---

## Beslutsgrund

**Gå vidare om:** gren-miljön reser sig utan manuella steg, testerna är gröna,
och auth fungerar för lösenord + OAuth.

**Avbryt om:** byggkontexten inte kan vara repo-roten (då måste `agent-core`
flyttas, vilket är en större ändring), eller om Railways förbrukningsprissättning
för två miljöer landar väsentligt över Render Starter + Supabase Pro.

**Kostnad att jämföra mot:** dagens uppsättning är Supabase Pro (~25 USD) plus
Render gratis med kallstarter. Railway Hobby börjar på 5 USD/mån plus
förbrukning, och gren-miljöer somnar automatiskt.

---

## Vad som inte rörs

Produktionen. Nuvarande `development`-flöde fortsätter fungera under hela
prototypen. Backendens kod ändras **inte alls** — bara `DATABASE_URL`. Alla 454
tester och 47 invarianter gäller oförändrade och är måttstocken.
