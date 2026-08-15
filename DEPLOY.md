# Miljöer och driftsättning

Två miljöer, två grenar. Inget deployas genom att någon klickar i en dashboard.

| | Produktion | Preview |
|---|---|---|
| Gren | `main` | `development` |
| Frontend | Vercel-projekt `snajp` | samma projekt, Preview-scope |
| Backend | Render `snajp-support` | Render `snajp-support-dev` |
| Databas | Supabase `spsmblyvasagpekjmgmf` | Supabase-gren `development` |
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
