# Miljöer och driftsättning

Två miljöer, två grenar. Inget deployas genom att någon klickar i en dashboard.

| | Produktion | Preview |
|---|---|---|
| Gren | `main` | `development` |
| Frontend | Vercel-projekt `snajp` | samma projekt, Preview-scope |
| Backend | Render `snajp-support` (`main`) | Render `snajp-support-dev` (`development`) |
| Databas | Supabase `spsmblyvasagpekjmgmf` | Supabase-gren `development` (`eppgmjswfnrfwnqvtrge`) |
| Utlöses av | push till `main` | push till `development` |

**Allt arbete går till `development`.** `main` rörs bara när något är verifierat
i previewen.

---

## PROJEKTREGEL: preview-databasen är en spegel av produktionen

Preview-grenen skapas **alltid med `--with-data`**:

```bash
npx supabase branches create development \
  --project-ref spsmblyvasagpekjmgmf --region eu-west-1 \
  --persistent --with-data --git-branch development
```

**Varför:** en ändring ska gå att utvärdera med allt annat lika. En tom
preview-databas testar bara att koden startar — inte att den fungerar mot
verklig datamängd, riktiga tenants och de kanttillfällen som bara finns i
verklig data. Skiljer sig underlaget går skillnaden i utfall inte att tillskriva
ändringen.

**Konsekvensen, som måste stå skriven:** previewen innehåller därmed **riktiga
kunders ärenden, mejladresser och kunskapsbaser**. Den ska behandlas med samma
sekretess som produktionen:

- Inga preview-länkar till utomstående.
- Inga skärmdumpar med kunddata i chattar, ärenden eller dokument.
- Samma personkrets som har åtkomst till produktionen, ingen bredare.

**Har grenen drivit för långt från `main`:** radera och skapa om, lappa inte.
Persistenta grenar måste göras ephemeral först, annars vägrar API:t:

```bash
npx supabase branches update development --persistent=false
npx supabase branches delete development
# skapa sedan om enligt kommandot ovan
```

---

## Migrationskedjan är självbärande sedan `000_base_schema.sql`

`supabase/migrations/000_base_schema.sql` innehåller dashboardens grundtabeller
(`workspaces`, `profiles`, `business_contexts` …). Den finns för att kedjan inte
var självbärande: `001` och framåt förutsätter att `workspaces` finns, men den
skapades bara av `supabase/schema.sql` — som ingen migrationsmekanism kör.

Det märktes först när den första preview-grenen skapades: Supabase replayar
`migrations/`, och grenen fick `ss_tenants` (från `002`) men **inte**
`workspaces`. Ett halvt schema som såg ut att vara helt. Samma lucka gällde
varje framtida gren och varje återställning från noll.

`000` är idempotent — `create table if not exists` och `drop policy if exists`
före varje `create policy` — så den är en no-op mot en databas som redan har
tabellerna.

---

## Render

Blueprinten är `snajp-support/render.yaml` och innehåller **båda** tjänsterna.

`branch:` står i git på båda. Det är inte kosmetik: grenvalet var ett osynligt
dashboardfält, och två produktionsincidenter kom ur att det pekade fel utan att
synas i någon diff. `INV-DEPLOY-001` kräver numera att varje tjänst anger sin
gren, och kontrollerar `rootDir`/`dockerfilePath` **per tjänst** — den var
tidigare blind för allt utom den första.

**Root Directory-fältet i dashboarden ska vara TOMT.** Det har återgått till
`snajp-support` av sig självt och fällt ett Docker-bygge med
`"/agent-core": not found`. `agent-core/` ligger utanför `snajp-support/` och
kan inte kopieras in om byggkontexten är undermappen.

### Kvoten — läs innan du slår på keep-alive för previewen

Renders gratisnivå ger **750 instanstimmar per månad delat på ALLA
gratistjänster** i workspacet. `keep-backend-awake.yml` pingar därför bara
**produktionen** (~250 h/mån). Två varma tjänster hade landat på ~500 h, och när
taket spricker stänger Render av allt till nästa månad.

Previewen får alltså en minuts kallstart vid första anropet efter inaktivitet.
Det är rätt avvägning för en testmiljö. Behövs dygnet-runt-drift: uppgradera en
tjänst till Starter (~7 USD/mån), vilket också tar bort SMTP-blockeringen.

---

## Vercel

Variabler sätts **per scope**. `vercel env add <namn> preview`.

Efter Auth.js-bytet (`3c2cb2b`) är de kritiska Preview-variablerna:

`AUTH_SECRET` — signerar sessions-JWT:n. Utan den är ALLA oinloggade: proxyn
redirectar `/dashboard` → `/login` (fail-closed) och inloggningen svarar med en
konfig-felsträng i stället för en generisk 500. Generera: `openssl rand -base64 32`.

`DATABASE_URL` — pooler-värdet för Postgres (se fälla 3 nedan). PER MILJÖ:
preview pekar på preview-grenens databas, production på produktionsdatabasen.
Utan den kastar `lib/db.ts` och inloggningen 500:ar.

Sedan de som redan fanns: `SNAJP_SUPPORT_URL`, `SNAJP_INTERNAL_API_KEY`,
`SNAJP_MASTER_API_KEY` (backend-proxy + admin), `OPENAI_API_KEY` (email-studio,
simulerar utan), `AUTH_GOOGLE_ID` / `AUTH_MICROSOFT_ENTRA_ID_ID` (SSO, valfria).

De gamla Supabase-auth-variablerna (`NEXT_PUBLIC_SUPABASE_URL`,
`NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`,
`NEXT_PUBLIC_SITE_URL`) konsumeras INTE längre av frontenden — Supabase-klienten
är borttagen i Auth.js-bytet.

### `NEXT_PUBLIC_SITE_URL` är fällan

Den läses i `lib/actions/auth.ts` med defaulten `http://localhost:3000` och
**bakas in vid build**, inte vid runtime. Tre konsekvenser:

1. Sätts den inte i Preview-scopet ärvs produktionsvärdet, och varje magic link
   och lösenordsåterställning från previewen skickar användaren till
   **produktionssajten**.
2. Sätts den inte alls hamnar de på `localhost:3000`.
3. Den går inte att ändra efter deploy utan ombyggnad.

Använd den **stabila grenaliasen**
(`https://snajp-git-development-olofluns-projects.vercel.app`), inte
deployment-URL:en som byts vid varje push.

Supabase Auth → URL Configuration i **preview-grenens** projekt måste lista
`<grenalias>/auth/callback`, annars avvisas varje inloggningsredirect.

### Saknas Supabase-env står auth-grinden helt öppen

`hasServerSupabaseEnv()` gör att `proxy.ts` **står åt sidan** i stället för att
kasta — det var medvetet, eftersom ett kast tog ner de publika sidorna. Men
följden är att `/dashboard/*` och `/settings/*` inte grindas alls när
variablerna saknas. Alla tre Supabase-variablerna måste sättas i preview.

---

## Känd begränsning: kundytor går inte att testa på `.vercel.app`

`tenantSlugFromHost()` (`lib/tenants/index.ts`) returnerar medvetet `null` för
allt som slutar på `.vercel.app`, eftersom preview-URL:er har formen
`snajp-git-branch-team.vercel.app` där första etiketten inte är en kund.

Kundspecifika ytor kräver alltså en egen wildcard-domän för att kunna testas i
preview. Dokumenterat i stället för kringgått.

---

## Email Studio behöver en modellnyckel på WEBB-tjänsten

Åtgärderna i Email Studio (Kortare, Skriv om, Förbättra, Personalisera,
Översätt, Uppföljning, Analysera, A/B) körs av `app/api/email-studio/route.ts`,
alltså i Next-appen — **inte** av agent-backenden. Nyckeln måste därför ligga på
`web`, inte bara på `api`.

Så var det inte. Uppmätt 2026-08-23 saknades `OPENAI_API_KEY` på `web` i båda
miljöerna, och routen föll då till sitt simuleringsläge. Följden var att varje
**inloggad, betalande** kund fick mallgenererad text med `success: true` och
ingenting som sa att den inte kom från en modell. Åtgärderna tog noll sekunder,
vilket var det enda som avslöjade det.

| Variabel | Tjänst | Betydelse |
|---|---|---|
| `OPENAI_API_KEY` | `web` | Används först när den finns |
| `DEEPSEEK_API_KEY` | `web` | Används annars, mot `https://api.deepseek.com` |
| `EMAIL_STUDIO_MODEL` | `web` | Valfri. Default `gpt-4o-mini` / `deepseek-chat` |

DeepSeek talar OpenAI-protokollet och är vad agenterna redan kör mot, så
projektet betalar inte för en ny leverantör. Nyckeln är kopierad från `api` till
`web` i båda miljöerna.

**Saknas båda simulerar routen fortfarande** — men svaret bär nu `simulated:
true` och editorn skriver "Exempelsvar" ovanför resultatet. Ta inte bort den
markeringen: utan den går ett simulerat svar inte att skilja från agentens
arbete.

**Anonyma anrop simuleras ALLTID**, oavsett vilka nycklar som finns. Det är den
raden som gör att marknadssidans knappar fungerar utan att en oinloggad kan
bränna nyckeln (INV-SEC-010). Den kontrollen får inte tas bort.

## DNS hos Loopia — automatiserat, utom API-användaren

`www.snajp.se` är tillagd i Railway och väntar på en CNAME. Posten sätts med

```bash
python scripts/loopia_dns.py            # visa nuvarande poster
python scripts/loopia_dns.py --apply    # sätt CNAME mot Railway
```

Skriptet talar XML-RPC mot `https://api.loopia.se/RPCSERV`, städar bort poster
som krockar med en CNAME på samma namn, och skriver ut zonen före och efter.

**Det enda som kräver en människa** är en LoopiaAPI-användare. Den skapas i
kundzonen under **Kontoinställningar → LoopiaAPI** och är en egen inloggning,
skild från kontolösenordet. Lägg den i `.env.deploy`:

```
LOOPIA_API_USER=nagot@loopiaapi
LOOPIA_API_PASSWORD=...
```

Det är ett kontolösenord, alltså ett av undantagen i CLAUDE.md som alltid
kräver dig. Allt efter den punkten är ett kommando.

### Apex går inte att peka på Railway

Och det är inte en begränsning i skriptet:

* En CNAME får enligt DNS-standarden inte samexistera med andra poster på
  samma namn, och apex MÅSTE ha NS och SOA. Det kräver ALIAS/ANAME, som är en
  leverantörsspecifik utökning — Loopia har den inte.
* Railways plan tillåter dessutom bara **en** egen domän per tjänst, och den är
  använd av `www`. Apex avvisades med *"You have reached the limit for custom
  domains per service on your plan."*

Lös det med Loopias egen **webbvidarebefordran**, `snajp.se` →
`https://www.snajp.se`. Den funktionen finns inte i LoopiaAPI, så den punkten
förblir manuell. Skriptet upptäcker att apex pekar på Loopias parkering
(194.9.94.85/86) och påminner om det.

Verifiera kopplingen från Railways sida när DNS spridit sig:

```bash
python scripts/railway_doman.py --env main
```

Den skriver `OK` i stället för `VÄNTAR` när posten pekar rätt.

## Ny kund

```bash
python scripts/onboard_tenant.py --slug bolaget --name "Bolaget AB" --env preview
```

Skriptet gör de fem maskinella stegen: tenant + API-nyckel, workspace-kopplingen,
configfilen, KB-stubben och nyckeln till rätt Vercel-scope. Research, KB-innehåll,
logotyp och besiktning kräver ögon och skrivs ut som checklista. Se `TENANTS.md`.


---

## Faktiska identiteter (2026-08-15)

| | Värde |
|---|---|
| Vercel-projekt | `snajp` — `prj_ZXXMG8Jlz0zHeLdg5NTMhN0tHpw9` |
| Preview-alias | `https://snajp-git-development-olofluns-projects.vercel.app` |
| Render produktion | `srv-d9k99ktg1s2s73fl0v6g` — https://snajp-support.onrender.com |
| Render preview | `srv-da0dopojo6nc73ea3b6g` — https://snajp-support-dev.onrender.com |
| Supabase produktion | `spsmblyvasagpekjmgmf` (org Snipe, eu-west-1) |
| Supabase preview-gren | `eppgmjswfnrfwnqvtrge`, persistent, `with_data: true` |

Hemligheter och anslutningssträngar ligger i `.env.deploy` (gitignorerad).

### Det finns ingen Render Blueprint

`GET /v1/blueprints` returnerar en **tom lista**. Båda tjänsterna är
fristående — produktionen skapad i dashboarden, previewen via API:t.
`render.yaml` läses alltså inte av någonting.

Det betyder att `INV-DEPLOY-001` vaktar en fil som inte styr driften, och att
sanningen ligger i Renders databas där ingen diff visar den. Det är precis den
luckan som orsakade två incidenter: Root Directory som svängde tillbaka till
`snajp-support`, och grenvalet som pekade mot `development` medan frontenden
deployade från `main`.

**Fixen är en driftkontroll, inte en blueprint:**

```bash
python scripts/verify_render.py
```

Den jämför Renders faktiska tjänster mot `render.yaml` — gren, rootDir,
dockerfilePath, healthCheckPath och plan — och returnerar 1 vid avvikelse.
Kör den efter varje ändring i dashboarden och som del av driftsättningsrutinen.
Filen beskriver avsikten; skriptet bevisar att verkligheten stämmer.

Att i stället registrera en riktig Blueprint hade krävt att `render.yaml` fanns
på den gren blueprinten läser (`main`), alltså en push till produktion innan
något verifierats i preview. Fel ordning.

## Migrationer 028 och 029 — kör BÅDA före rollbytet

Bevisade mot preview-spegeln, med produktionens verkliga datamängd:

- **028** stoppar kraschen `invalid input syntax for type uuid: ""`. Efter en
  skopad fråga blir `app.tenant_id` tom sträng, inte NULL, för resten av
  anslutningen — och varje senare oskopad fråga föll på `''::uuid`.
- **029** stoppar TYSTNADEN. 028 räckte inte: `list_agent_runs_all` gav 0 rader
  trots 10 i databasen, och kundöversikten fyra kunder med nollställda tal.
  Trovärdiga men felaktiga siffror är värre än en tom vy.

Efter båda, mätt som `snajp_app` utan BYPASSRLS: rätt antal överallt, och
skopade frågor ger fortfarande en delmängd — isoleringen håller.


---

## Två fällor som slog till på riktigt vid uppsättningen

**1. `vercel env rm NAME preview` raderar HELA posten.**
Vercel lagrar en variabel som gäller flera miljöer som EN post. `SNAJP_SUPPORT_URL`
och `SNAJP_INTERNAL_API_KEY` gällde "Production, Preview" — att sätta ett
preview-värde tog bort dem ur **produktionen**. Upptäckt genom att lista
scopet efteråt, inte av något felmeddelande.

`scripts/keys.py:vercel_env_set()` vägrar numera skriva till en delad post och
säger vad man ska göra i stället. Varje variabel bör vara en post per miljö.

**2. Preview-deployen är SSO-skyddad, och ska förbli det.**
`ssoProtection` är på för allt utom egna domäner, så `*.vercel.app` kräver
Vercel-inloggning. Med spegelregeln innehåller previewen riktig kunddata —
att stänga av skyddet vore ett dataläckage.

Följden: automatiserad verifiering (`scripts/verify_inv_sec_010.sh`) når inte
preview-frontenden. Skapa en **Protection Bypass for Automation**-token i
Vercel → Settings → Deployment Protection, och skicka den som
`x-vercel-protection-bypass`. Då kommer skript in medan människor fortfarande
måste logga in.

**3. Supabases direktvärd (`db.<ref>.supabase.co`) nås inte från Render.**
Den är IPv6-only. `DATABASE_URL` måste använda pooler-värden
(`aws-1-eu-west-1.pooler.supabase.com:6543`) med användarnamnet
`<roll>.<projektref>`. Symptomet är inte ett anslutningsfel utan att tjänsten
tyst faller tillbaka på `MemoryStorage` — vilket `/health/ready` numera säger
rakt ut med `storage: "memory"`.


---

## Neon som fallback

Beslut 2026-08-16: vi utvärderar Supabase-branching, och behåller Neon som
alternativ om speglingen visar sig otillräcklig. Neon har mer trogen
grenspegling och gratis branching (100 projekt, 10 grenar per projekt).

**Priset för ett byte är inte databasen — det är inloggningen.** Mätt i den här
kodbasen:

- **21 referenser** till `auth.users` / `auth.uid()` i 6 migrationsfiler
- **14 auth-anrop** över **13 filer** (`signInWithOAuth`,
  `exchangeCodeForSession`, `resetPasswordForEmail` …)
- Främmande nycklar från `platform_admins`, `workspace_invites` och `profiles`
  rakt in i `auth.users`
- Triggern `on_auth_user_created`, som skapar workspacet vid registrering

Ett byte kräver alltså att autentiseringen skrivs om — mot Neon Auth, Clerk
eller Auth.js — inte bara att anslutningssträngen ändras.

**Vad som skulle göra bytet billigare:** RLS-policyerna delar redan databasen i
två halvor. Backendens tabeller (`ss_*`, `agent_*`) grindas enbart på
`app.tenant_id` och rör aldrig `auth.uid()`. Bara dashboardens tabeller behöver
Supabase. Backenden skulle alltså kunna flytta först, med
`workspaces.ss_tenant_id` nedgraderad från främmande nyckel till mjuk referens.

Utvärderingskriterium: om Supabase-grenens spegling driver isär från
produktionen på ett sätt som gör utvärderingar otillförlitliga, är det signalen
att ta Neon-spåret.


---

## Varför Supabase-workflowen visade MIGRATIONS: FAILED

Två numreringssystem som aldrig möttes.

Repots filer heter `000_base_schema.sql`, `019_rate_limit.sql` och så vidare —
Supabase läser versionen som `000`, `019`. Men allt som faktiskt applicerats
gjordes via Management-API:t, som registrerar sina egna **14-siffriga
tidsstämplar** (`20260815150826`).

Uppmätt i produktionen före fixen:

    totalt: 30    tidsstämplade: 30    repo-numrerade: 0

Branching-workflowen läser `supabase/migrations/` från git-grenen, ser
versionerna `000`–`029`, hittar ingen av dem i `schema_migrations` och försöker
applicera **alla trettio**. De faller direkt, eftersom tabellerna och policyerna
redan finns.

Det var alltså aldrig ett fel i migrationerna. Databasen var korrekt hela
tiden — bokföringen sa bara emot.

**Fixen:** repots versionsnummer är nu registrerade som applicerade i BÅDE
produktionen och grenen. Ingen SQL kördes om; bara liggaren stämmer nu med
verkligheten.

**Regel framåt:** applicera migrationer så att versionen matchar filnamnet, och
kontrollera efteråt:

```sql
select count(*) from supabase_migrations.schema_migrations where version ~ '^[0-9]{1,3}$';
-- ska vara lika många som antalet filer i supabase/migrations/
```
