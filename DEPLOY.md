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

Sju variabler måste finnas i Preview-scopet:
`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`,
`SUPABASE_SERVICE_ROLE_KEY`, `NEXT_PUBLIC_SITE_URL`, `SNAJP_SUPPORT_URL`,
`SNAJP_INTERNAL_API_KEY`, `SNAJP_MASTER_API_KEY`.

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

**Render-tjänsten skapades via API:t, inte genom att synka blueprinten.** Att
synka hade krävt att `render.yaml` fanns på den gren blueprinten läser
(`main`), och inget går till `main` innan det verifierats i preview. Blueprinten
och de två tjänsterna beskriver alltså samma sak, men tjänsterna skapades
separat — synka blueprinten nästa gång `main` uppdateras, så de inte glider isär.

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
