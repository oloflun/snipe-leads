# Comp AI Community Edition: drift oförändrad och compliance-processen

Underlag för Snajps EU-compliance inför första kund-onboardingen.
Källa: grund kloning av `trycompai/comp` i `D:\comp-compliance\comp`, commit `712ee1b3` (2026-11-17).
Inga skript ur klonen har körts. Analysskripten ligger i `D:\comp-compliance\scripts\` (läser bara JSON).

**Märkning:** **[V]** är verifierat i en fil i klonen (sökvägen anges). **[A]** är ett antagande eller
extern kunskap som inte är kontrollerad i klonen. **[W]** är kontrollerat i extern dokumentation eller i GitHub-issues.

---

## 0. Slutsats först

1. **Docker-guiden är inaktuell mot koden.** `docker-compose.yml` saknar API-tjänsten (`apps/api`, NestJS,
   port 3333). Inloggning, sessioner och nästan alla mutationer går numera genom den tjänsten.
   Den som följer SELF_HOSTING.md exakt får en app som inte går att logga in i. **[V]**
   (se avsnitt 3.2)
2. **README kräver att repot ändras.** Trigger.dev-projekt-id:t är hårdkodat i två `trigger.config.ts`.
   README säger åt en att skriva in sitt eget id, och för Google och Upstash föreslår den att värden
   hårdkodas i källfiler. **[V]** CLI-flaggan `--project-ref` kan möjligen användas i stället, men det är
   inte bekräftat att den går före config-filen. **[W/A]**
3. **Allt AI-arbete och all e-post körs i Trigger.dev Cloud,** även inloggningsmejl (magic link/OTP).
   Trigger-tasks läser databasen direkt. Comp blir därmed ett biträdesled med minst Trigger.dev, Resend,
   S3-leverantör, Vercel AI Gateway, OpenAI, Anthropic och Firecrawl. **[V]**
4. **Den GDPR-mall som följer med är tunn:** 19 krav, 12 kontroller, 6 policyer och 15 uppgifter.
   ISO 27001 har 26 policyer. NIS 2 är dold och i praktiken tom, och EU AI Act saknas helt. **[V]**

---

## 1. Ramverk i seed-datan

Seed-data finns i `packages/db/prisma/seed/primitives/*.json` och `relations/*.json`. Den laddas av
`packages/db/prisma/seed/seed.ts`. **[V]**

Totalt finns 23 ramverk, 1 334 krav, 204 kontrollmallar, 52 policymallar, 148 uppgiftsmallar och
5 utbildningsvideor (YouTube, "Security Awareness Training del 1–5", `FrameworkEditorVideo.json`). **[V]**

I onboarding visas bara ramverk med `visible: true` (`apps/api/src/frameworks/frameworks.service.ts:428, 690`). **[V]**

Antalen nedan är framräknade via relationerna krav→kontroll→policy/uppgift (`scripts/fw.py`). **[V]**

| Ramverk | Version | Synligt | Krav | Kontroller | Policyer | Uppgifter |
|---|---|---|---|---|---|---|
| **GDPR** | 1.0.0 | ja | 19 | 12 | 6 | 15 |
| **ISO 27001** | 2022 | ja | 119 | 27 | 26 | 24 |
| **ISO 42001** (AI-ledningssystem) | 1.0.0 | ja | 70 | 76 | 21 | 61 |
| SOC 2 | v1 | ja | 63 | 35 | 25 | 26 |
| HIPAA | 2025 | ja | 77 | 20 | 18 | 35 |
| PCI DSS Level 1 | 1.0.0 | ja | 233 | 41 | 23 | 29 |
| PCI DSS | 1.0.0 | ja | 1 | 1 | 14 | 17 |
| CCPA | 1.0.0 | ja | 12 | 21 | 9 | 11 |
| ISO 9001 | 1.0.0 | ja | 37 | 1 | 6 | 9 |
| NEN 7510 | 1.0.0 | ja | 1 | 1 | 5 | 7 |
| **NIS 2** | 2022/2555 | **nej** | 160 | 1 | 0 | 1 |
| NIST CSF | 2.0 | nej | 106 | 0 | 0 | 0 |
| PIPEDA | 1.0.0 | nej | 10 | 28 | 26 | 21 |
| Övriga dolda (SOC 2-varianter, PCI v0, "GDPR (Test)", Example PCI, NIST 800-53, Cloud Cybersecurity Controls) | | nej | | | | |

**EU-relevans:**
- GDPR: finns, men är liten (se nedan).
- ISO 27001:2022: komplett bilaga A (A.5–A.8) och klausul 4–10.
- ISO 42001: finns. Det är det närmaste AI-förordningen plattformen kommer.
- NIS 2: 160 krav är inlagda men kopplade till bara 1 kontroll och 0 policyer, och ramverket är dolt. Det
  går inte att använda i onboarding. **[V]**
- EU AI Act: finns inte. **[V]**

### 1.1 GDPR i detalj **[V]**

Ramverket har id `frk_681ef1952907deb7cb85896d`.

**Krav och kontroller:**

| Krav | Kontroll |
|---|---|
| AG-1 Accountability Owner, AG-3 EU Representative, AG-4 DPO | GDPR Accountability Roles and Representatives |
| AG-2 Data Processor Agreements | Data Processing Agreements with Third Parties |
| DS-1 Privacy by Design/Default | Privacy by Design and by Default |
| DS-2 Minimization/Pseudonymization | Data Minimization, Encryption, and Pseudonymization |
| DS-3 Internal Security Policy | Information Security Policy and Awareness Training |
| DS-4 DPIA | Data Protection Impact Assessment Process |
| DS-5 Breach Notification | Personal Data Breach Response Procedure |
| LBT-1 Information Audit | Data Inventory and Mapping |
| LBT-2 Legal Justification | Lawful Basis Register, Privacy Notice |
| LBT-3 Transparent Privacy Policy | Privacy Notice |
| PR-1…PR-6 (tillgång, rättelse, radering, begränsning, portabilitet, invändning) | Data Subject Rights Request Workflow |
| PR-7 Automated Decision-Making | Automated Decision-Making Safeguards |

**Policyer (6):**
- Compliance & Regulatory Monitoring
- Data Classification & Handling
- Incident Response & Breach Notification
- Privacy & Data-Subject Rights
- Security & Privacy Awareness Training
- Vendor & Third-Party Risk

**Uppgifter/bevis (15):**
- App Availability
- Appoint or Review Data Protection Officer
- Cookie Consent and Tracking Review
- DPIA Trigger Review and Execution
- Data Protection Awareness Training
- Data Subject Rights Request Handling
- Encryption at Rest
- Incident Response
- Maintain Records of Processing Activities (RoPA)
- Manage Third-party and EU Representative Relationships
- Monitoring & Alerting
- Public Policies
- Review Data Retention, Minimization, and Encryption
- Review International Data Transfers
- Secure Code

**Kommentar [A]:** Policyerna för åtkomststyrning, kryptering, backup/kontinuitet och SDLC (artikel 32,
säkerhet i behandlingen) följer bara med om ISO 27001 också väljs. **GDPR + ISO 27001** ger 26
policyer och är den rimliga kombinationen. Lägg till **ISO 42001** om AI-hanteringen ska täckas.

### 1.2 Alla 52 policymallar **[V]**

`FrameworkEditorPolicyTemplate.json`:

AI Policy Control Framework · Acceptable Use & Workstation Security · Access Control & Least Privilege ·
Authentication & Password · Background Screening & On/Off-boarding · Backup, Business Continuity & Disaster
Recovery · Change & Release Management · Change Management Policy · Children's and Minors' Data Policy · Code of
Business Conduct · Compliance & Regulatory Monitoring · Consumer Rights Request Policy · Data Classification &
Handling · Data Classification and Inventory Policy · Data Retention and Disposal Policy · Document Control
Procedure · Encryption & Crypto Controls · Incident Response & Breach Notification · Incident Response and Breach
Notification Policy · Information Security & Privacy Governance · Information Security Policy · Information
Sharing & Transfer · Internal Audit Procedure · Logging, Monitoring & Audit · Network Security · PIPEDA (6 st:
Access Request, Consent Management, Data Accuracy, PI Inventory & Purpose Register, Privacy Complaint, Privacy
Notice) · Physical Security & Environmental · Policy Management & Exception Handling · Privacy & Data-Subject
Rights · Privacy Awareness and Training Policy · Privacy Policy · QMS Scope · Quality Objectives · Quality Policy
· Remote Access & BYOD · Retention & Secure Disposal · Risk Management · Sanctions & Disciplinary · Secure
Configuration & Hardening · Secure Software Development Lifecycle · Security & Privacy Awareness Training ·
Service Provider Acknowledgement · Supplier / Vendor Evaluation Policy · Third-Party Processors (Vendors) ·
Vendor & Third-Party Risk · Vendor and Third-Party Management Policy · Vulnerability & Patch Management

---

## 2. Processen i plattformen

### 2.1 Steg för steg (enligt koden; dokumentationen har ingen samlad processbeskrivning)

`packages/docs/quickstart.mdx` är Mintlifys standardmall och beskriver inte produkten. **[V]**

| # | Steg | Var i koden | Vem | Via API? |
|---|---|---|---|---|
| 1 | Logga in (magic link eller 6-siffrig e-post-OTP; Google/GitHub/Microsoft valfritt) | `apps/api/src/auth/auth.server.ts:294` (lösenord avstängt), `:533` magicLink, `:553` emailOTP | Människa | Nej |
| 2 | Setup: välj ramverk och svara på 16 frågor: ramverk, bolagsnamn, webbplats, beskrivning, bransch, antal anställda, C-suite, vem som signerar rapporten, enheter, inloggningsmetod, hosting, mjukvara, arbetssätt, datatyper, dataplats, leveransadress för certifikat | `apps/app/src/app/(app)/setup/lib/constants.ts:53–166` | Människa | Delvis (`GET /v1/organization/onboarding` ger bara status) |
| 3 | Organisationen skapas. Self-hosted godkänns automatiskt (`hasAccess`) | `setup/actions/create-organization-minimal.ts:83,171`, `upgrade/[orgId]/page.tsx:79`, `apps/api/src/organization-access/organization-access.service.ts:19–21` | Automatiskt | – |
| 4 | Trigger-tasken `onboard-organization`: ramverksinstanser, kontroller, policyer och uppgifter skapas ur mallar. AI anpassar policyerna efter svaren, extraherar leverantörer ur svaren och skapar leverantörer och risker med åtgärdsförslag | `apps/app/src/trigger/tasks/onboarding/onboard-organization.ts:108–218`, `update-policies-helpers.ts:64` (Claude Sonnet via Vercel AI Gateway), `onboard-organization-helpers.ts:21` (`google/gemini-3-flash` via Gateway) | Automatiskt | – |
| 5 | Granska och redigera policyer (AI-editor), skicka för godkännande, publicera | `/v1/policies/*`, docs `ai-policy-editor.mdx` | Människa (godkännare) | **Ja**: `PATCH /v1/policies/{id}`, `POST …/versions`, `…/submit-for-approval`, `…/versions/publish`, `POST /v1/policies/publish-all`, `…/regenerate` |
| 6 | Leverantörsregister och riskbedömning (Firecrawl-research) | `/v1/vendors`, `apps/api/src/trigger/vendor/*` | Människa/AI | **Ja**: `POST/PATCH /v1/vendors`, `…/trigger-assessment` |
| 7 | Riskregister | `/v1/risks` | Människa | **Ja**: `POST/PATCH /v1/risks` |
| 8 | Uppgifter med bevis: ladda upp filer, formulärbevis, granska och godkänna | `/v1/tasks/*`, `/v1/evidence-forms/*` | Människa | **Ja**: `POST /v1/tasks/{id}/attachments`, `…/submit-for-review`, `…/approve`, `PATCH /v1/tasks/bulk` |
| 9 | Automatiska bevis: integrationer, molntester (AWS/Azure/GCP), webbläsarautomationer (Browserbase) | docs `automated-evidence.mdx`, `cloud-tests/*`, `browser-automations.mdx` | Engångsuppkoppling (människa) | Ja, för automationer |
| 10 | Personal: bjud in, portalen (policygodkännande per anställd, 5 utbildningsvideor, device agent) | `apps/portal/…`, `/v1/people/*`, `/v1/training/*` | **Varje anställd** | Inbjudan ja; signering i portalen nej |
| 11 | Dokument: ISO 27001 SoA (AI-autofyll), ISMS-dokument | `/v1/soa/*`, `apps/api/src/isms` | Människa godkänner | Ja |
| 12 | Säkerhetsfrågeformulär och kunskapsbas | `/v1/questionnaire/*`, `/v1/knowledge-base/*` | AI + människa | Ja |
| 13 | Trust Center | `/v1/trust-portal/*` | – | API finns, men **frontenden finns inte i CE** (se 6) |
| 14 | Revisorsvy och bevisexport | `/v1/evidence-export/all`, `[orgId]/auditor` | Revisor | Ja |

### 2.2 API, API-nycklar och MCP **[V]**

**Autentisering:**
- Header `X-API-Key: comp_…`. Nyckeln skapas i appen under Settings → API Keys, eller via `POST /v1/organization/api-keys`, som kräver en inloggad session.
- Varje nyckel måste ha explicita scopes av formen `resource:action`. Giltighetstid väljs bland never, 30days, 90days och 1year.
- Nyckeln lagras saltad och hashad. Se `apps/api/src/auth/api-key.service.ts:38–102, 303`.
- Nyckeln bär RBAC.

**API-ytan:**
- Swagger finns på `{BASE_URL}/api/docs` (`apps/api/src/main.ts`).
- Den publika spec:en har 334 sökvägar och 412 operationer (`packages/docs/openapi.json`). Dess `servers` pekar på `api.trycomp.ai`, men en egen instans genererar den från `BASE_URL`.
- Kärnendpoints för en agent:
  - `/v1/policies`
  - `/v1/tasks/{id}/attachments`
  - `/v1/vendors`
  - `/v1/risks`
  - `/v1/controls/{id}/{policies|tasks|requirements}/link`
  - `/v1/frameworks` (lägg till ramverk)
  - `/v1/context` (organisationskontext, CRUD)
  - `/v1/people/invite`
  - `/v1/knowledge-base/documents/upload`
  - `/v1/soa/auto-fill`

**MCP:**
- `apps/mcp-server` är npm-paketet `@trycompai/mcp-server` 0.2.8, genererat av Speakeasy, med 373 verktygsfiler.
- Det körs via stdio med `npx -y @trycompai/mcp-server start --apikey comp_… --server-url https://<egen-api>`.
- Flaggan `--server-url` finns i `apps/mcp-server/src/mcp-server/cli/start/command.ts:54` och används i `impl.ts:38`. Standardvärdet är `https://api.trycomp.ai` (`src/lib/config.ts:18`).
- **Slutsats:** en agent kan fylla i policyer, uppgifter/bevis, leverantörer och risker programmatiskt mot den egna instansen.
- Hostad MCP via OAuth (Gram) kräver `GRAM_*`-variablerna och är valfri (`apps/api/.env.example:21–27`).

**Kräver människa oavsett:**
- Första inloggningen.
- Att skapa API-nyckeln (session).
- Anställdas policysignering och utbildning i portalen.
- Att godkänna policyer och SoA. Rollen *approver* kan i princip vara en människa som agerar via API [A].
- OAuth-uppkopplingar av integrationer.

---

## 3. Drift oförändrad

### 3.1 Det dokumenterade läget **[V]**

Källor: `SELF_HOSTING.md`, `packages/docs/self-hosting/docker.mdx` och `env-reference.mdx`.

| Tjänst (compose) | Dockerfile-mål | Port | Kommando |
|---|---|---|---|
| migrator | `migrator` (oven/bun:1.4.4) | – | `bunx prisma migrate deploy --schema=node_modules/@trycompai/db/dist/schema.prisma` |
| seeder | `migrator` | – | `bunx prisma generate … && bun packages/db/prisma/seed/seed.js` |
| app | `app` (node:22.23.4-alpine, Next standalone) | 3000 | `node apps/app/server.js` |
| portal | `portal` | 3002→3000 | `node apps/portal/server.js` |

**Byggargument i root-`Dockerfile`:**
- App (rad 76–81): `NEXT_PUBLIC_BETTER_AUTH_URL`, `NEXT_PUBLIC_PORTAL_URL`, `NEXT_PUBLIC_POSTHOG_KEY`, `NEXT_PUBLIC_POSTHOG_HOST`, `NEXT_PUBLIC_IS_DUB_ENABLED` och `NEXT_PUBLIC_API_URL`.
- Portal (rad 129): bara `NEXT_PUBLIC_BETTER_AUTH_URL`.
- Compose skickar bara `NEXT_PUBLIC_BETTER_AUTH_URL` (`docker-compose.yml:31–32, 50–51`).
- Byggena sätter `SKIP_ENV_VALIDATION=true` och `NODE_OPTIONS=--max_old_space_size=6144` (rad 90, 133).

**Trigger.dev:** tasks ska deployas från en arbetsstation med `cd apps/app && bunx trigger.dev@latest deploy` (`SELF_HOSTING.md:66–74`).

### 3.2 Vad koden faktiskt kräver (avviker från guiden) **[V]**

- **API-tjänsten är obligatorisk.** Appens server-auth anropar `${BACKEND_API_URL || NEXT_PUBLIC_API_URL}/api/auth/get-session`
  (`apps/app/src/utils/auth.ts:1–8, 17–19, 141`). Webbläsarklienten använder `NEXT_PUBLIC_API_URL` (`apps/app/src/utils/auth-client.ts:22–25`).
  238 filer i appen använder `apiClient` mot NestJS (`apps/app/src/lib/api-client.ts`). Portalen gör likadant
  (`apps/portal/src/app/lib/auth-client.ts:10`, `auth.ts:14`).
  - API:t byggs med `apps/api/Dockerfile.multistage`, mål `production`, port 3333, healthcheck `/v1/health`.
  - `apps/api/docker-compose.yml` är märkt "FOR TESTING LOCALY ONLY".
  - Bekräftas av issue #1705 ("API service … completely missing from docker-compose.yml") och #3331. **[W]**
- **API:t startar inte utan S3-uppgifter.** `awsConfig` laddas i `ConfigModule` (`apps/api/src/app.module.ts:71`) och kastar
  ett fel om nyckel, hemlighet eller bucket saknas (`apps/api/src/config/aws.config.ts:4–31`).
  Det kräver också `SECRET_KEY` på minst 16 tecken (`auth.server.ts:246–258`).
- **Inloggningsmejlen skickas via Trigger.dev.** `triggerEmail` → `tasks.trigger('send-email')` (`apps/api/src/email/trigger-email.ts`),
  som körs i **API:ts** Trigger-projekt (`apps/api/trigger.config.ts:9`, `proj_zhioyrusqertqgafqgpj`).
  Appens tasks finns i ett annat projekt (`apps/app/trigger.config.ts:7`, `proj_lhxjliiqgcdyqbgtucda`).
  **Två Trigger-projekt behöver deployas.** Guiden nämner bara appens.
- **Seedern ser trasig ut enligt filerna.**
  - Compose kör `seed/seed.js`, men repot har bara `seed.ts`.
  - `seed.ts` importerar `@prisma/adapter-pg` (rad 2), som migrator-imagen inte installerar. Imagen har bara `prisma ^6.14`, `@prisma/client`, `@trycompai/db ^1.3.4` och `zod` (`Dockerfile:40`).
  - Klienten genereras ur det publicerade `@trycompai/db` 1.x-schemat, medan den lokala db-versionen är 2.3.0 med Prisma 7.6.0 (`packages/db/package.json:4,7,13`).
  - Ingen körning är gjord. Det är högst sannolikt att det fallerar [A]. `bun prisma/seed/seed.ts` är repots eget kommando (`packages/db/package.json:58`).
- **`NEXT_PUBLIC_SELF_HOSTED` är inte ett byggargument.** Docs säger att den ska sättas i `apps/app/.env` (runtime).
  - NEXT_PUBLIC-värden bakas in vid `next build` [A, standardbeteende i Next].
  - Utan ARG i Dockerfile blir värdet tomt i imagen.
  - Det som räddar läget är att appen faller tillbaka till `POST /v1/organization-access/auto-approve`. API:t läser `SELF_HOSTED`/`NEXT_PUBLIC_SELF_HOSTED` vid runtime (`organization-access.service.ts:19–21`).
  - **Sätt `SELF_HOSTED=true` på API-tjänsten.**
  - Effekt: organisationer godkänns automatiskt och Stripe- och bokningssteget hoppas över (`SELF_HOSTING.md:30–33`).
- **Portalen kan inte få `NEXT_PUBLIC_API_URL` via Dockerfile:n**, eftersom ARG saknas (rad 129).
  Portalens inloggning i webbläsaren pekar då på `http://localhost:3333`. Med oförändrad Dockerfile går det
  inte att lösa; se 5.2 för en alternativ byggväg.
- **Policygenereringen kräver Vercel AI Gateway** (`@ai-sdk/gateway`, `createGatewayProvider`;
  `update-policies-helpers.ts:9,64`, `onboard-organization-helpers.ts:18–21`). `AI_GATEWAY_API_KEY` står i
  `turbo.json:6` men nämns inte i env-referensen.

### 3.3 Miljövariabler per tjänst

**(a) Krävs för att tjänsten ska starta**

| Variabel | migrator/seeder | api | app | portal | Belägg |
|---|---|---|---|---|---|
| `DATABASE_URL` (SSL) | x | x | x | x | env-reference:20 |
| `SECRET_KEY` (≥16 tecken; better-auth-hemlighet) | | x | x | | auth.server.ts:246, app env |
| `BASE_URL` (API:ts publika URL) | | x | | | auth.server.ts:153, main.ts:147 |
| `APP_AWS_ACCESS_KEY_ID`, `APP_AWS_SECRET_ACCESS_KEY`, `APP_AWS_BUCKET_NAME`, `APP_AWS_REGION` (+`APP_AWS_ENDPOINT` för S3-kompatibel lagring) | | x | (x) | (x) | aws.config.ts |
| `AUTH_SECRET`, `RESEND_API_KEY`, `REVALIDATION_SECRET`, `NEXT_PUBLIC_PORTAL_URL` | | | x | | app/src/env.mjs:10,16,24,37 |
| `RESEND_API_KEY` | | | | x | portal/src/env.mjs:8 |
| Byggargument `NEXT_PUBLIC_BETTER_AUTH_URL`, `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_PORTAL_URL` | | | x | x (endast BETTER_AUTH) | Dockerfile:76–81,129 |
| `PORT=3333`, `NODE_ENV=production` | | x | | | Dockerfile.multistage:130 |

**(b) Krävs för att kärnprocessen ska fungera**

| Funktion | Variabler | Var |
|---|---|---|
| Inloggning och e-post | `RESEND_API_KEY`, `RESEND_FROM_SYSTEM`, `RESEND_FROM_DEFAULT`; `TRIGGER_SECRET_KEY` (API-projektet) | api `.env.example:45,81–85`; send-email-tasken körs i Trigger |
| Cookies, CORS och länkar | `BETTER_AUTH_URL`, `NEXT_PUBLIC_APP_URL` (api), `AUTH_TRUSTED_ORIGINS` (komma-separerad lista med app, portal och api) | origin-policy.ts:1–41; standardlistan innehåller bara localhost och trycomp.ai |
| Bakgrundsjobb, onboarding | `TRIGGER_SECRET_KEY` (app-projektet), `TRIGGER_APP_SECRET_KEY` (api) | app env.mjs:21, api `.env.example:47` |
| Tjänst-till-tjänst | `SERVICE_TOKEN_TRIGGER` (app, api och Trigger-miljön), `SERVICE_TOKEN_PORTAL`, `INTERNAL_API_TOKEN` (samma värde i app, api och portal), `UNSUBSCRIBE_SECRET` | service-token.config.ts:18,29; `.env.example` |
| AI-generering av policyer, leverantörer och risker | `AI_GATEWAY_API_KEY` (Vercel), `OPENAI_API_KEY` ("Required for app to work", app `.env.example:18`), `ANTHROPIC_API_KEY` (policy-chatten: `app/api/policies/[policyId]/chat/route.ts:194`) | se 3.2 |
| Leverantörsresearch | `FIRECRAWL_API_KEY` ("Required", app `.env.example:57`) | api/app trigger |
| Filer och bevis | `APP_AWS_ORG_ASSETS_BUCKET`, `APP_AWS_QUESTIONNAIRE_UPLOAD_BUCKET`, `APP_AWS_KNOWLEDGE_BASE_BUCKET` | env-reference:76–83 |
| Self-hosted-godkännande | `SELF_HOSTED=true` (api) | organization-access.service.ts:20 |
| **Trigger.dev-miljön** (i Triggers dashboard, inte i Railway) | Samma DB-, Resend-, S3-, AI- och service-token-variabler som tasks läser | process.env-räkning i `apps/*/src/trigger`; issue #2199 [W] |

**(c) Valfria:** Google, GitHub och Microsoft OAuth; `UPSTASH_REDIS_*`/`UPSTASH_VECTOR_*` (rate limit,
CORS-cache och vektorsök för frågeformulär; Upstash REST, **inte** kompatibelt med Redis Cloud [A]); `GROQ_API_KEY`;
PostHog; Vercel-domäner; `FLEET_URL`/`FLEET_TOKEN` (MDM); Novu; Stripe; Browserbase; 1Password (`OP_SERVICE_ACCOUNT_TOKEN`);
bakgrundskontroller; Dub; Sentry; `GRAM_*` (hostad MCP); `CATALYST_OTLP_TOKEN`.

### 3.4 Inloggning utan Google **[V]**

Lösenord är avstängt (`emailAndPassword.enabled: false`). Magic link (1 h) och e-post-OTP (6 siffror,
10 min) är alltid på. Båda kräver att Resend och API:ts Trigger-projekt fungerar, eftersom mejlet går via
Trigger-tasken `send-email`.

---

## 4. Externa tjänster och dataflöden

| Tjänst | Krävs? | Vad den ser | EU-region |
|---|---|---|---|
| **Trigger.dev Cloud** | Ja (två projekt) | Kör onboarding, policy-AI, e-post och leverantörsbedömning. **Tasks ansluter direkt till databasen** och ser all compliance-data, personaldata och mejlinnehåll | Körningar kan läggas i `eu-central-1`, men "the region only determines where runs execute"; payload, loggar och output lagras oberoende av region [W, trigger.dev/docs/triggering]. Self-hosting av Trigger stöds (`TRIGGER_API_URL`, `.env.example:24`) men är en egen stor stack [A] |
| **Resend** | Ja | Mottagare och e-postinnehåll (inloggningslänkar, inbjudningar) | EU-region (eu-west-1) finns [A]; Snajp använder redan Resend |
| **S3-kompatibel lagring** | Ja (API startar inte annars) | Bevisfiler, policy-PDF:er, frågeformulär | Valfri region/leverantör via `APP_AWS_REGION`/`APP_AWS_ENDPOINT` (t.ex. AWS eu-north-1) [V, A om leverantör] |
| **Vercel AI Gateway** | Ja för onboarding-AI | Bolagsbeskrivning och policyinnehåll; vidare till Google (Gemini) och Anthropic | Amerikanskt mellanled [A] |
| **OpenAI** | Ja (enligt `.env.example`) | Policy-AI (`gpt-5.5`), SoA-RAG, leverantörsscore | EU-dataresidens finns för vissa konton [A] |
| **Anthropic** | Ja för policy-chatt och -redigering | Policytext | USA [A] |
| **Firecrawl** | Ja för leverantörsresearch | Leverantörsdomäner (offentlig data) | USA [A] |
| Postgres | Ja | Allt | Railway EU (redan befintlig) |
| Upstash, Groq, Browserbase, Fleet, Novu, PostHog | Nej | – | – |

**Konsekvens [A]:** innehållet i Comp är främst Snajps egna styrdokument, personalens namn och e-post
och leverantörslistor, inte Snajps kunders kunddata. Biträdeskedjan måste ändå föras in i Snajps eget
RoPA och leverantörsregister, med SCC/DPF för de amerikanska leden. Ladda inte upp kunders personuppgifter
som bevis.

---

## 5. Lämplighet för Railway (EU)

### 5.1 Tjänster att skapa

Postgres finns redan; det går att använda en separat databas eller ett schema [A].

| Railway-tjänst | Bygg | Minne vid runtime [A] |
|---|---|---|
| api | `apps/api/Dockerfile.multistage` (sista steget = `production`, fungerar utan target) | 400–800 MB |
| app | root-`Dockerfile`, mål `app` | 300–700 MB |
| portal | root-`Dockerfile`, mål `portal` (= sista steget) | 200–400 MB |
| migrator | root-`Dockerfile`, mål `migrator`, engångsjobb | kort |

### 5.2 Konkreta hinder

1. **Byggmål.** Railway bygger det sista steget i en Dockerfile. Jag har inte hittat något stöd för att
   välja `--target` [A, verifiera i Railways docs]. Root-Dockerfile:ns sista steg är `portal`, så `app` och
   `migrator` går inte att bygga direkt.
   **Väg utan repoändring:** bygg imagerna i en egen CI-pipeline med `docker build --target … --build-arg …`
   (t.ex. GitHub Actions i ett separat repo, push till GHCR) och låt Railway deploya från imagen.
2. **Byggminne.** Next-byggena kräver `--max_old_space_size=6144`, i praktiken 7–8 GB RAM per bygge. Den
   lokala maskinen (16 GB, delad) bör inte göra det. Railways byggkapacitet per plan behöver kontrolleras [A].
3. **Portalens `NEXT_PUBLIC_API_URL`** kan inte sättas via Dockerfile:n. Alternativen är:
   - (a) Bygg portalen med Railpack/Nixpacks direkt från monorepot, där alla variabler finns vid bygget. Det
     följer dock inte repots Docker-väg och är inte testat [A].
   - (b) Acceptera att portalen (anställdas policysignering och utbildning) inte fungerar.
   - (c) Ändra Dockerfile:n, vilket inte är tillåtet.
4. **Trigger.dev-deploy** måste köras från en arbetsstation eller CI med `bunx trigger.dev@4.7.7 deploy`.
   Det kräver `bun install` för hela monorepot, vilket är tungt. Det behövs för **både** `apps/app` och
   `apps/api`. Projekt-id:t är hårdkodat. `deploy --project-ref` finns, men den
   kan vara "Required if there is no config file" och går kanske inte före config-filen [W, ej verifierat].
   Annars gäller README:s instruktion att redigera `trigger.config.ts` (README.md:214–221), vilket bryter mot
   kravet att inte ändra repot.
5. **README föreslår hårdkodning** av värden i källfiler (README.md:207, 241–258). Det ska inte följas.
6. **Seedern** behöver troligen köras med repots eget kommando (`bun packages/db/prisma/seed/seed.ts` efter
   `bun install` i `packages/db`) i stället för compose-kommandot (se 3.2).
7. **Databasen nås från Trigger.dev Cloud.** Railway-Postgres måste ha publik proxy med SSL, med de
   säkerhetskonsekvenser det får [A].
8. **Disk [A]:** byggcachen för monorepot är 5–10 GB. Färdiga images är ungefär 0,5–1,5 GB vardera.
   Klonen här är cirka 130 MB med `--depth 1`.

---

## 6. Fallgropar (issues och kod)

| Fallgrop | Källa |
|---|---|
| API saknas i compose; dokumentation och kod går isär; 4 `.env.example` med överlapp | #1705 [W], 3.2 [V] |
| `apps/api` startar inte från källkod (Nest DI `HybridAuthGuard`; Node: `Unexpected token '<'`) och blockerar inloggning | #3331, öppen [W] |
| Trust Center-frontend finns inte i CE. `TRUST_APP_URL=http://localhost:3008` pekar på en app som inte finns i `apps/` | #3445, öppen [W]; `.env.example:31`, `ls apps` [V] |
| Kunskapsbasens dokument fallerar om `APP_AWS_KNOWLEDGE_BASE_BUCKET` saknas i **Trigger-miljön** | #2199, öppen [W] |
| Stora ramverk (ISO 27001, SOC 2) fallerade med Prisma P2028 (transaktionstimeout) vid tillägg | #1556, stängd [W] |
| `SKIP_ENV_VALIDATION=true` gör att saknade variabler först syns när tjänsten kraschar vid runtime | Dockerfile:93,136 [V] |
| `AUTH_TRUSTED_ORIGINS` måste sättas, annars är bara localhost och trycomp.ai betrodda (CSRF/CORS) | origin-policy.ts:1–41 [V] |
| Device agent: portalen serverar binärer ur egen bucket (`FLEET_AGENT_BUCKET_NAME`, `device-agent/production/...`). Binärerna måste byggas, signeras och laddas upp av en själv | `apps/portal/src/app/api/download-agent/*` [V] |
| Upstash-klienten skapas med `!`-asserterade env-värden; fel fångas, men det loggas brus | auth.server.ts (corsRedisClient) [V] |

---

## 7. Gränsdragning

- **Verifierat i filer:** ramverkstal, GDPR-innehåll, policymallar, Dockerfile och compose, env-scheman,
  inloggningsmetoder, AI-leverantörer, API- och MCP-yta, hårdkodade Trigger-id, seed-filnamn och beroenden.
- **Inte verifierat (ingenting har byggts eller körts):** att seedern faktiskt fallerar; Next-inbakning av
  `NEXT_PUBLIC_SELF_HOSTED`; Railways stöd för byggmål och byggminne; att `--project-ref` går före config;
  EU-regioner för Resend, OpenAI och AI Gateway; minnesbehov.
