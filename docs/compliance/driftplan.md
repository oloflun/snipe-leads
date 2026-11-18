# Driftplan: Comp AI CE på Railway (EU) utan repoändring

Bygger på `comp-research.md` (avsnitt 3 och 5). Klon: `trycompai/comp` @ `712ee1b3d722ca1b4f09eb4e5b67cd3bde8713ed` (main, 2026-11-17).
Ingenting har byggts, körts eller skapats. **[V]** = verifierat i fil/källkod (sökväg:rad), **[W]** = officiell dokumentation (URL),
**[F]** = forumsvar från leverantörens personal, **[A]** = antagande.

## 0. Slutsats

**Genomförbar med förbehåll.** Bygget och migreringen går att göra oförändrat. Två saker i koden gör att en oförändrad
installation på en egen domän inte fungerar rakt av. Båda går att kringgå med konfiguration, men lösningen är otestad:

1. **Inloggningen [V].** Sessionskakan sätts av API:t som en kaka som bara gäller API:ts eget värdnamn (cross-subdomain-kakor
   slås bara på för `*.trycomp.ai`; `apps/api/src/auth/auth.server.ts:62–72, 323–331`). Appens proxy letar dessutom bara efter
   kakor med fem bestämda namn (`apps/app/src/proxy.ts:31–36`). Över https heter kakan `__Secure-local.session_token`
   (better-auth `cookies/index.ts:66–76`), och det namnet finns inte bland de fem. Följden är att app och API på separata
   värdnamn ger en inloggningsloop.
   Kringgåendet [A] består av två delar:
   - En egen omvänd proxy (Caddy, i det separata pipeline-repot) lägger API:t under samma värdnamn som appen
     (`/v1/*` och `/api/auth/*`) och portalen.
   - `BASE_URL` sätts till `http://…`, så att kakan får namnet `local.session_token`. Proxyn styr all trafik till https.
2. **TLS mot Postgres [V].** Alla Prisma-klienter vägrar okrypterad eller overifierad TLS mot en databas som inte ligger på
   localhost, om inte `PRISMA_ALLOW_INSECURE_TLS=1` är satt (`apps/api/prisma/client.ts:41–60`, `apps/app/prisma/client.ts`).
   API-imagen och API:ts Trigger-deploy sätter `NODE_EXTRA_CA_CERTS` (AWS RDS-bundle). Därmed väljs grenen för verifierad TLS
   *före* opt-out-flaggan (`Dockerfile.multistage:105`, `apps/api/caBundleExtension.ts:32`), och Railways självsignerade
   certifikat [F] underkänns.
   Kringgåendet [A] har två delar:
   - Startkommandot på Railway gör `unset NODE_EXTRA_CA_CERTS`.
   - I Trigger raderas variabeln via API:t efter varje deploy.

Lås **712ee1b** och inte senaste tagg. v3.111.1 (2026-08-05) saknar ett 30-tal säkerhetsfixar, se fråga 6.

---

## 1. Frågorna

### F1. .env-filer vid bygget
- **Byggkontexten.** Rotens `.dockerignore` innehåller `.env` utan `**/` [V]. Mönster matchas relativt kontextens rot, och
  `**` krävs för att träffa på godtyckligt djup [W https://docs.docker.com/build/concepts/context/]. Därför utesluts bara
  rotens `.env`.
  - `COPY apps/app ./apps/app` och `COPY apps/portal ./apps/portal` tar med `apps/*/.env` (`Dockerfile:62,119`) [V].
  - Filerna är git-ignorerade (`apps/app/.gitignore:34`, `apps/portal/.gitignore:34`). Att skapa dem ändrar alltså inte repot.
- **Hur bygget körs.** Turbo används inte. Bygget kör `cd apps/portal && bun run build:docker`, alltså
  `prisma generate … && next build` med `apps/portal` som cwd (`Dockerfile:136`, `apps/portal/package.json:60`) [V].
  `turbo.json` påverkar inte Docker-bygget.
- **Hur Next läser .env.** Next laddar `.env.production.local`, `.env.local`, `.env.production` och `.env` ur projektkatalogen.
  Ett värde ur en fil används bara om nyckeln är **odefinierad** i processmiljön (`@next/env` `packages/next-env/index.ts:97–98`,
  canary) [V].
  Portalens `NEXT_PUBLIC_API_URL` har ingen ENV i Dockerfile:n. Värdet i `apps/portal/.env` används därför och bakas in
  (`env.mjs:26,33`; `auth-client.ts:10` läser `process.env.NEXT_PUBLIC_API_URL`) [V].
- **Fällan i appen.** Varje ARG blir `ENV X=$X` (`Dockerfile:82–87`). En ARG som inte skickas blir därmed en tom sträng, som
  **går före** `.env` [V].
  - Appens sex NEXT_PUBLIC-ARG:ar måste alltså skickas som `--build-arg`.
  - `NEXT_PUBLIC_SELF_HOSTED` har ingen ARG och kan därför läggas i `apps/app/.env` (`create-organization-minimal.ts:83`
    och `upgrade/[orgId]/page.tsx:79` läser den) [V].
  - Compose skickar bara en ARG. Därför blir appens `NEXT_PUBLIC_API_URL` tom även på compose-vägen.
- **Slutsats.** Ja, portalen går att bygga korrekt på den dokumenterade vägen utan ändring. Lägg bara **publika** värden i
  bygg-`.env`. Det är okänt om standalone-utdatan kopierar `.env` in i imagen [A].

### F2. Trigger.dev (CLI 4.7.7, taggen `v4.7.7`)
- **Projekt-id kan överstyras utan att config-filen ändras** [V]:
  - `packages/cli-v3/src/commands/deploy.ts:147–148`: "-p, --project-ref … This will override the project specified in the
    config file".
  - `deploy.ts:426`: `overrides: { project: options.projectRef ?? envVars.TRIGGER_PROJECT_REF }`.
  - `config.ts:215–227` slår ihop med `defu(…, overrides, config, …)`, där vänster argument vinner.
  - Ordningen blir: `--project-ref` > `TRIGGER_PROJECT_REF` i `.env` > processmiljön > `trigger.config.ts`.
- **CI.** `TRIGGER_ACCESS_TOKEN` (en PAT, `tr_pat_…`) räcker. Ingen `trigger login` behövs (`commands/login.ts:165–182, 365`) [V].
  Den officiella guiden kör `npx trigger.dev@… deploy --env prod` med `TRIGGER_ACCESS_TOKEN` som secret
  [W https://trigger.dev/docs/github-actions].
  Repots egna workflows är en färdig mall: `.github/workflows/trigger-tasks-deploy-release.yml` och
  `trigger-api-tasks-deploy-release.yml` [V].
- **Bygget.** Fjärrbygge är standard, så Docker behövs inte lokalt (`deploy.ts:662–675`)
  [W https://trigger.dev/docs/deployment/overview]. CLI:t paketerar dock lokalt, och det kräver `bun install` av hela
  monorepot. Gör det i CI, inte på den här maskinen.
- **Miljövariabler.** De sätts i dashboarden eller via `syncEnvVars`-tillägget [W .../config/extensions/syncEnvVars].
  `--env-file` laddar bara variabler in i CLI-processen (`deploy.ts:159–160`) [V]. Deploy fallerar inte på att variabler
  saknas; felet syns först när tasken körs [A].
  **Fälla:** `deploy.sync.env` laddas upp med `override: true` vid varje deploy (`deploy.ts:1008–1019`) [V]. API-projektets
  `caBundleExtension` skriver alltså över `NODE_EXTRA_CA_CERTS` varje gång.
- **Build-tillägg** [V, W https://trigger.dev/docs/config/extensions/puppeteer]:

  | Projekt | Tillägg | Vad det gör |
  |---|---|---|
  | app | `prismaExtension` (lokal, Prisma 7.6.0) | – |
  | app | `puppeteer()` | Installerar Chrome i imagen och sätter `PUPPETEER_EXECUTABLE_PATH`; inget extra krav |
  | api | `caBundleExtension` | Kopierar `packages/db/certs/rds-global-bundle.pem` och synkar `NODE_EXTRA_CA_CERTS` |
  | api | `prismaExtension` | – |
  | api | `integrationPlatformExtension` | – |
  | api | `emailExtension` | – |
- **Region.** Körningar kan läggas i `eu-central-1` (Frankfurt). Standardregion väljs i dashboardens sida Regions
  [W https://trigger.dev/changelog/multi-region-workers].
  DPA:ns bilaga 2 säger dock att data lagras i "AWS East-1" (USA) [W https://trigger.dev/legal/dpa]. DPA:n accepteras via
  villkoren och hänvisar till SCC 2021/914. Underbiträdena finns huvudsakligen i USA [W https://trigger.dev/legal/subprocessors].
- **Pris** [W https://trigger.dev/pricing]:

  | Plan | Pris | Ingår | Samtidiga körningar | Loggar sparas |
  |---|---|---|---|---|
  | Free | 0 $ | 5 $ beräkningskredit | 20 | 1 dygn |
  | Hobby | 10 $/mån | 10 $ | 50 | 7 dygn |
  | Pro | 50 $/mån | 50 $ | 200+ | 30 dygn |

### F3. Railway
- **(a) Byggmål.** `--target` stöds inte. Config-as-code har `builder`, `dockerfilePath`, `buildCommand`, `watchPatterns` och
  `railpackVersion`, men inget `target` [W https://docs.railway.com/reference/config-as-code, /guides/dockerfiles]. Det finns
  en öppen önskan om stöd [F https://station.railway.com/feedback/support-target-for-multi-stage-dockerfil-7f5337a6].
  Byggvariabler når bara en `ARG` som deklarerats i rätt steg [W]. Inget dokumenterat byggminne finns; personal anger 8 GB [F].
- **(b) Bygg i GitHub Actions, deploya image.**
  - Runners [W https://docs.github.com/en/actions/reference/runners/github-hosted-runners]:
    - publikt repo: 4 CPU, 16 GB RAM, 14 GB SSD
    - privat repo: 2 CPU, 8 GB RAM
  - En heap på 6144 MB ryms i 8 GB, men med liten marginal. Ett publikt pipeline-repo (bara YAML, hemligheter i Actions
    secrets) ger 16 GB.
  - Disken på 14 GB är trång eftersom `node_modules` kopieras i flera lager. Bygg en image per jobb och frigör disk först [A].
  - Privata images från GHCR kräver Railways **Pro**-plan. Användarnamn och en klassisk PAT med `read:packages` anges när
    tjänsten skapas [W https://docs.railway.com/guides/services].
  - Alternativet är att göra images publika. De innehåller bara öppen källkod och publika URL:er, och då räcker Hobby [A].
  - Lagring och trafik i GHCR är gratis för containerimages [W https://docs.github.com/en/billing/concepts/product-billing/github-packages].
- **(c) Buckets** finns: privata, S3-kompatibla och GA sedan 2025-11-28.
  - Variabler: `ENDPOINT`, `ACCESS_KEY_ID`, `SECRET_ACCESS_KEY`, `BUCKET` och `REGION=auto`.
  - Adressering: virtual-hosted som standard; path-style bara för äldre buckets.
  - Pris: 0,015 $/GB-mån.
  - Region väljs när bucketen skapas, men EU-stöd står inte i dokumentationen.

  Källor: [W https://docs.railway.com/storage-buckets, /storage-buckets/billing].

  Buckets passar **inte** repot oförändrat:
  - Huvudklienterna sätter `forcePathStyle: !!APP_AWS_ENDPOINT` (`apps/api/src/app/s3.ts:55–62`, `apps/app/src/app/s3.ts`).
  - Dessa klienter saknar endpoint helt och går alltid mot AWS:
    - `parse-questionnaire-extraction.ts:109–121`
    - `process-knowledge-base-document.ts:14–27`
    - `vector-store/lib/sync/sync-utils.ts:42–55`
    - `device-agent.service.ts:76`
  - `policies.controller.ts:542,656,839,951` signerar URL:er för policy-PDF med `AWS_REGION` och AWS:s standardkedja [V].

  **Använd AWS S3 i eu-north-1.** Det kräver ett AWS-konto.
- **(d) Engångsjobb.** Cron-tjänster måste avsluta sig själva; `restartPolicyType: NEVER` och `preDeployCommand` finns
  [W https://docs.railway.com/reference/cron-jobs, config-as-code]. Enklast är att köra migrering och seed som ett manuellt
  GitHub Actions-jobb mot den publika proxyn. Det är repots eget mönster (`database-migrations-release.yml`) [V].
- **(e) Postgres utifrån.** Public Access skapar en TCP-proxy och `DATABASE_PUBLIC_URL`. Trafiken räknas som egress,
  0,05 $/GB [W https://docs.railway.com/databases/postgresql].
  - SSL fungerar, men certifikatet är självsignerat (CN `localhost`), så `verify-full` fallerar [F].
  - Repot strippar `sslmode` och sätter ssl själv. Utan `PRISMA_ALLOW_INSECURE_TLS=1` kastas ett fel vid uppstart
    (api, portal) eller vid första frågan (app) [V].
  - Seed-skriptet använder `pg` direkt (`seed.ts:7`). Där betyder `sslmode=require` verify-full, så använd
    `sslmode=no-verify` [W pg-connection-string README].
- **(f) Region.** EU West heter `europe-west4-drams3a` (Amsterdam). Den sätts per tjänst eller via
  `deploy.multiRegionConfig` [W https://docs.railway.com/reference/deployment-regions].
- **(g) Kostnad.** Hobby kostar 5 $ (5 $ ingår), Pro 20 $ (20 $ ingår). RAM kostar ungefär 10 $/GB-mån och CPU ungefär
  20 $/vCPU-mån [W https://docs.railway.com/reference/pricing].
  För api, app, portal, Caddy och Postgres med ungefär 2 GB RAM och 0,2 vCPU blir det ungefär 22–28 $/mån på Pro [A].

### F4. AI-leden [V om inget annat anges]

| Steg | Var | Modell | Nyckel |
|---|---|---|---|
| Onboarding: leverantörer, risker, åtgärdsplaner | `onboard-organization-helpers.ts:18–21, 508, 676, 1045, 1117` | `google/gemini-3-flash` via Gateway | `AI_GATEWAY_API_KEY` |
| Onboarding: policyanpassning (separata `update-policy`-tasks) | `update-policies-helpers.ts:9,64` | `anthropic/claude-sonnet-4.6` via Gateway | `AI_GATEWAY_API_KEY` |
| Revisorstext efter onboarding | `generate-auditor-content.ts:119` | `gpt-5.5` | `OPENAI_API_KEY` |
| Revisorstext efter onboarding: webbskrapning | `generate-auditor-content.ts:23` | Firecrawl | `FIRECRAWL_API_KEY` |
| Leverantörsresearch (fire-and-forget) | `scrape/research.ts`, `lib/research.ts:48` | Firecrawl | `FIRECRAWL_API_KEY` |
| Leverantörsresearch: riskpoäng | `score-vendor-risk.ts` | `gpt-4.1-mini` | `OPENAI_API_KEY` |
| Leverantörsbedömning i API:t | `trigger/vendor/*` | Firecrawl `spark-1-pro`, Claude | `FIRECRAWL_API_KEY`, `ANTHROPIC_API_KEY` |
| Policy-AI i API:t | `policies.controller.ts:1570` | `gpt-5.5` | `OPENAI_API_KEY` |
| Policy-chatt och sektionsredigering i appen | `chat/route.ts`, `edit-section/route.ts` | `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` |
| Polering av policytext | `refine-cue-lines.ts:65` | `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` |
| SoA-autofyll | `soa-answer-generator.ts:161,229` | OpenAI | `OPENAI_API_KEY` |
| Inbäddningar (kunskapsbas, frågeformulär) | `generate-embedding.ts` | `text-embedding-3-small` | `OPENAI_API_KEY` |
| Automationer | – | Groq, Gateway | Valfria |

**Vad onboardingen kräver.**
- Absolut nödvändigt: `AI_GATEWAY_API_KEY` och DB-åtkomst i Trigger-appmiljön.
- `extractVendorsFromContext` anropar `generateObject` utan try/catch (`helpers.ts:498–508`). Utan Gateway-nyckel kastas ett fel,
  tasken görs om 3 gånger och onboardingen fallerar.
- `REVALIDATION_SECRET` och `NEXT_PUBLIC_BETTER_AUTH_URL` behövs för revalidering. Ett fel där fångas (`onboard-organization.ts:235–252`).

**Om nycklar saknas.**
- Utan `FIRECRAWL_API_KEY` startas research med `void` och avbryter inte onboardingen (`helpers.ts:1378–1384`). API:ts variant
  hoppar över med en varning (`firecrawl-agent-shared.ts:44–47`).
- Utan `OPENAI_API_KEY` går onboardingen igenom, men följande slutar fungera:
  - revisorstexten (kastar fel i en egen task)
  - SoA
  - inbäddningar (`throw`)
  - policy-AI i API:t

**Leverantörsvillkor.**

| Leverantör | Träning | Lagring | DPA/SCC | Region |
|---|---|---|---|---|
| Vercel AI Gateway | Tränar inte | Sparar inga prompter, bara metadata (30 dagar) | DPA med SCC 2021, accepteras via villkoren | `inferenceRegion` EU gratis per anrop. ZDR/EU kräver köpt kredit; gratiskrediten räknas inte |
| OpenAI | Inte som standard | Missbruksloggar upp till 30 dagar; ZDR efter godkännande | Kunde inte läsas (403) [A] | EU-residens för nya projekt (+10 %) |
| Anthropic | Inte som standard | 30 dagar | DPA med SCC i Commercial Terms | Ingen EU-inferens i förstaparts-API:t |
| Firecrawl | – | – | DPA först från Standard-planen; Free har 1 000 krediter | USA |
| Resend | – | Loggar i USA | DPA med SCC, förhandssignerad | Sändning i eu-west-1 |

Källor:
- Vercel: [W https://vercel.com/docs/ai-gateway/security-and-compliance/zdr, …/regional-inference, …/faq, https://vercel.com/legal/dpa]
- OpenAI: [W https://developers.openai.com/api/docs/guides/your-data, …/data-residency]
- Anthropic: [W https://privacy.claude.com/en/articles/7996866, …/7996862, https://platform.claude.com/docs/en/manage-claude/data-residency]
- Firecrawl: [W https://www.firecrawl.dev/privacy-policy, /pricing]
- Resend: [W https://resend.com/docs/dashboard/domains/regions, /legal/dpa]

### F5. Migrering och seed
- **Migrering, repots egen väg** (`database-migrations-release.yml`) [V]:
  ```
  cd packages/db && bun install --frozen-lockfile --ignore-scripts && bunx prisma migrate deploy
  ```
  Kommandot använder Prisma 7.6 och `prisma.config.ts`. Dockerfile-målet `migrator` blandar Prisma 6, `@trycompai/db` 1.x och
  lokala migreringar (`Dockerfile:40–51`). Undvik det.
- **Seed är nödvändig.** Migreringarna lägger bara in en äldre SOC 2-post (`20250516160714_insert_hardcoded_framework_to_db`).
  GDPR, ISO 27001 och ISO 42001 kommer från `prisma/seed/primitives/*.json` via `seed.ts`, som gör upsert och tål omkörning
  (`seed.ts:35–40`) [V].
- **Kommandot.** Compose-kommandot `seed.js` finns inte. Repots kommando är `bun run db:seed` (`packages/db/package.json:58`),
  efter `bun run db:generate`. Skälet är att `--ignore-scripts` hoppar över postinstall-genereringen av `@prisma/client` (`:64`).
- **Var det körs.** Som ett manuellt GitHub Actions-jobb mot `DATABASE_PUBLIC_URL` (runbook steg 6).

### F6. Kända startfel och versionslåsning
- **#3331** (öppen sedan 2026-07-02) gäller körning från källkod med `nest start` och Bun eller Node utan bygge [W].
  `Dockerfile.multistage` bygger med `nest build` på Node och kör `node dist/src/main.js` (`:46, 84, 142`). Uppströms
  produktion bygger samma fil via `buildspec.multistage.yml:21–26` [V]. Felet gäller därför sannolikt inte Docker-vägen [A].
- **Releaser.** Senaste tagg är v3.111.1 (2026-08-05). `release`-grenens topp är `ced98cb4` (2026-09-23).
  - `712ee1b` ligger 35 commits före `release`: säkerhetssvep, Next 16.4.6 (CVE), Bun 1.4.4 (CVE), flera better-auth-fixar
    och #3681 (ny onboardingkontroll) [W `gh api compare`].
  - Main deployas till uppströms staging (712ee1b gör migreringar från main) [V].
  - **Rekommendation:** lås 712ee1b. Reserv: `ced98cb4`, uppströms produktion, men med färre säkerhetsfixar.

---

## 2. Runbook (från noll till inloggningsbar instans)

Använd egna domäner. Exemplen nedan är `comp.example.se` (app plus API) och `portal.comp.example.se` (portal plus API).
Båda pekar på Caddy-tjänsten.

1. **Konton och nycklar** (avsnitt 3). Verifiera avsändardomänen i Resend, region eu-west-1.
2. **AWS S3** i eu-north-1:
   - Skapa bucketarna `comp-attachments`, `comp-org-assets`, `comp-questionnaire` och `comp-kb`. Blockera all publik åtkomst
     och sätt CORS för `https://comp.example.se` och `https://portal.comp.example.se` (PUT, GET).
   - Skapa en IAM-användare med `s3:GetObject`, `s3:PutObject` och `s3:DeleteObject` på bucketarna.
3. **Railway-projekt** (Pro), region `europe-west4-drams3a` för alla tjänster:
   - Lägg till Postgres och slå på Public Access (TCP-proxy).
   - Skapa de tomma tjänsterna `api`, `app`, `portal` och `caddy`.
   - Koppla domänerna till `caddy` och sätt DNS-CNAME.
4. **Trigger.dev**: skapa projekten `comp-app` och `comp-api`, och sätt standardregionen till eu-central-1. Notera:
   - projekt-ref (`proj_…`)
   - prod-nycklarna `tr_prod_…`
   - en PAT (`tr_pat_…`)
5. **Pipeline-repo** (eget, t.ex. `comp-deploy`). Det innehåller bara workflows, `caddy/Caddyfile` och `caddy/Dockerfile`.
   - Actions secrets: `TRIGGER_ACCESS_TOKEN`, `COMP_APP_PROJECT_REF`, `COMP_API_PROJECT_REF`, `DATABASE_PUBLIC_URL`,
     `RAILWAY_TOKEN` (projekttoken).
   - Variabler: `APP_URL=https://comp.example.se`, `PORTAL_URL=https://portal.comp.example.se`.
6. **Workflow `db.yml`** (manuell start), migrering och seed:
   ```yaml
   - uses: actions/checkout@v4
     with: { repository: trycompai/comp, ref: 712ee1b3d722ca1b4f09eb4e5b67cd3bde8713ed }
   - uses: oven-sh/setup-bun@v2
     with: { bun-version: '1.4.4' }
   - working-directory: packages/db
     run: bun install --frozen-lockfile --ignore-scripts && bun run db:generate
   - working-directory: packages/db
     env: { DATABASE_URL: "${{ secrets.DATABASE_PUBLIC_URL }}?sslmode=require" }
     run: bunx prisma migrate deploy
   - working-directory: packages/db
     env: { DATABASE_URL: "${{ secrets.DATABASE_PUBLIC_URL }}?sslmode=no-verify" }
     run: bun run db:seed
   ```
   Kontrollera efteråt: `SELECT name, visible FROM "FrameworkEditorFramework";` ska ge 23 rader.
7. **Workflow `images.yml`** (manuell start), matris med ett jobb per image, `ubuntu-latest`. Inget bakas in i imagen utom
   publika URL:er.
   ```yaml
   - uses: actions/checkout@v4
     with: { repository: trycompai/comp, ref: 712ee1b3d722ca1b4f09eb4e5b67cd3bde8713ed, path: comp }
   - run: sudo rm -rf /usr/share/dotnet /usr/local/lib/android /opt/ghc /opt/hostedtoolcache/CodeQL
   - name: Ospårade bygg-.env enligt docker.mdx (bara publika värden)
     run: |
       printf 'NEXT_PUBLIC_SELF_HOSTED=true\n' > comp/apps/app/.env
       printf 'NEXT_PUBLIC_API_URL=%s\nNEXT_PUBLIC_BETTER_AUTH_URL=%s\n' "$PORTAL_URL" "$PORTAL_URL" > comp/apps/portal/.env
   - uses: docker/login-action@v3
     with: { registry: ghcr.io, username: ${{ github.actor }}, password: ${{ secrets.GITHUB_TOKEN }} }
   - uses: docker/build-push-action@v6
     with:
       context: comp
       file: comp/${{ matrix.file }}   # Dockerfile (app, portal) | apps/api/Dockerfile.multistage (api)
       target: ${{ matrix.target }}    # app | portal | production
       push: true
       tags: ghcr.io/<ägare>/comp-${{ matrix.name }}:712ee1b
       build-args: |
         NEXT_PUBLIC_BETTER_AUTH_URL=${{ matrix.name == 'portal' && vars.PORTAL_URL || vars.APP_URL }}
         NEXT_PUBLIC_API_URL=${{ vars.APP_URL }}
         NEXT_PUBLIC_PORTAL_URL=${{ vars.PORTAL_URL }}
         NEXT_PUBLIC_IS_DUB_ENABLED=false
   ```
   Motsvarande `docker build` för hand:
   ```
   docker build --target app -f Dockerfile \
     --build-arg NEXT_PUBLIC_BETTER_AUTH_URL=… \
     --build-arg NEXT_PUBLIC_API_URL=… \
     --build-arg NEXT_PUBLIC_PORTAL_URL=… .
   ```
   Kör också ett fjärde jobb som bygger `caddy/` till `ghcr.io/<ägare>/comp-caddy`.
8. **Caddyfile** i pipeline-repot. Det är där API:t läggs under samma värdnamn som appen respektive portalen, se 0.1 [A]:
   ```
   { admin off
     auto_https off
     servers { trusted_proxies static private_ranges } }
   :{$PORT} {
     @plain header X-Forwarded-Proto http
     redir @plain https://{host}{uri} permanent
     @api {
       path /v1/* /api/auth/* /api/docs /api/docs/*
       not path /api/auth/invitation*
     }
     handle @api { reverse_proxy api.railway.internal:3333 }
     @portal host {$PORTAL_HOST}
     handle @portal { reverse_proxy portal.railway.internal:3000 }
     handle { reverse_proxy app.railway.internal:3000 }
   }
   ```
9. **Railway-tjänster från image** (GHCR-inloggning med en PAT som har `read:packages`). Variabler, se tabellen nedan.
   - `api`:
     - startkommando: `sh -c "unset NODE_EXTRA_CA_CERTS; exec node --report-on-fatalerror dist/src/main.js"`
     - healthcheck: `/v1/health`
   - `app`:
     - `HOSTNAME=::`
     - `PORT=3000`
     - healthcheck: `/api/health`
   - `portal`:
     - `HOSTNAME=::`
     - `PORT=3000`
   - `caddy`: `PORTAL_HOST=portal.comp.example.se`.
   - Uppdatera efter varje nytt image-bygge: `railway redeploy --service <namn>` med `RAILWAY_TOKEN`, eller slå på automatiska
     image-uppdateringar [W].
10. **Workflow `trigger.yml`** (manuell start). Kopiera stegen från uppströms `trigger-tasks-deploy-release.yml` och
    `trigger-api-tasks-deploy-release.yml` och lägg till projekt-ref:
    ```
    cd apps/app && bunx trigger.dev@4.7.7 deploy --env prod --project-ref "$COMP_APP_PROJECT_REF"
    cd apps/api && bunx trigger.dev@4.7.7 deploy --env prod --project-ref "$COMP_API_PROJECT_REF"
    curl -fsS -X DELETE -H "Authorization: Bearer $TRIGGER_ACCESS_TOKEN" \
      "https://api.trigger.dev/api/v1/projects/$COMP_API_PROJECT_REF/envvars/prod/NODE_EXTRA_CA_CERTS"
    ```
    Delete-anropet finns dokumenterat [W https://trigger.dev/docs/management/envvars/delete].
    Stegen `bun install` och `cp`/`prisma generate` i uppströms workflows skriver bara genererade filer i CI-utcheckningen.
    Workflowen kör repots postinstall-skript på runnern, inte lokalt.
11. **Trigger-miljövariabler** (dashboard, prod), se tabellen nedan.
12. **Test**:
    - `GET https://comp.example.se/v1/health`
    - Logga in med e-post-OTP eller magic link och kontrollera att kakan `local.session_token` sätts på `comp.example.se`.
    - Kör setup: välj GDPR + ISO 27001 (+ ISO 42001) och se att `onboard-organization` går grönt i Trigger.
    - Logga in i portalen.

### Variabler per tjänst

`G` = kan genereras slumpmässigt, med `openssl rand -base64 32` eller Railways `${{ secret(32) }}` [A]. Värdet måste vara
**samma** i alla tjänster och Trigger-miljöer som listas. `E` = kräver ett externt konto.

| Variabel | api | app | portal | Trigger app | Trigger api | Typ |
|---|---|---|---|---|---|---|
| `DATABASE_URL` (internt: `${{Postgres.DATABASE_URL}}`; Trigger: publik URL + `?sslmode=require`) | x | x | x | x | x | Railway |
| `PRISMA_ALLOW_INSECURE_TLS=1` | x | x | x | x | x | fast |
| `SECRET_KEY` (≥ 16 tecken) | x | x | | | | G |
| `AUTH_SECRET`, `BETTER_AUTH_SECRET` | x | x | x | | | G |
| `REVALIDATION_SECRET` | | x | | x | | G |
| `INTERNAL_API_TOKEN` | x | x | x | | | G |
| `SERVICE_TOKEN_TRIGGER` | x | | | x | x | G |
| `SERVICE_TOKEN_PORTAL` | x | | x | | | G |
| `UNSUBSCRIBE_SECRET` | x | | | | x | G |
| `BASE_URL=http://comp.example.se` (http med avsikt, se 0.1) | x | | | | x | fast |
| `BETTER_AUTH_URL`, `NEXT_PUBLIC_APP_URL=https://comp.example.se` | x | x | | x | x | fast |
| `AUTH_TRUSTED_ORIGINS` = `https://comp.example.se,https://portal.comp.example.se,http://comp.example.se` | x | | | | | fast |
| `BACKEND_API_URL=http://api.railway.internal:3333` | | x | x | | | fast |
| `NEXT_PUBLIC_API_URL` / `API_BASE_URL` = `https://comp.example.se` | | | | x | x | fast |
| `NEXT_PUBLIC_PORTAL_URL` | | x | | x | | fast |
| `SELF_HOSTED=true` | x | | | | | fast |
| `PORT=3333`, `NODE_ENV=production` | x | | | | | fast |
| `APP_AWS_REGION=eu-north-1`, `APP_AWS_ACCESS_KEY_ID`, `APP_AWS_SECRET_ACCESS_KEY`, `APP_AWS_BUCKET_NAME`, `APP_AWS_ORG_ASSETS_BUCKET` | x | x | x | x | x | E (AWS) |
| `APP_AWS_QUESTIONNAIRE_UPLOAD_BUCKET`, `APP_AWS_KNOWLEDGE_BASE_BUCKET` | x | | | | x | E |
| `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (samma IAM-nyckel; policy-PDF:er) | x | | | | | E |
| `RESEND_API_KEY` | x | x | x | | x | E |
| `RESEND_FROM_SYSTEM`, `RESEND_FROM_DEFAULT` | x | | | | x | E |
| `TRIGGER_SECRET_KEY` (api: api-projektets nyckel; app: app-projektets) | x | x | | | | E |
| `TRIGGER_APP_SECRET_KEY` (app-projektets nyckel) | x | | | | | E |
| `AI_GATEWAY_API_KEY` | | | | x | | E (krävs) |
| `OPENAI_API_KEY` | x | x | | x | x | E |
| `ANTHROPIC_API_KEY` | x | x | | | x | E |
| `FIRECRAWL_API_KEY` | x | | | x | x | E (valfri) |

Valfria variabler som lämnas osatta: `UPSTASH_*` (ger bara loggbrus), Groq, Browserbase, Novu, PostHog, Sentry och Stripe.

---

## 3. Konton och nycklar som ägaren skapar själv

| Konto / nyckel | Används till | Kostnad |
|---|---|---|
| Railway (Pro) | api, app, portal, caddy, Postgres; GHCR-pull | 20 $/mån, inkl. 20 $ förbrukning; ungefär 22–28 $ totalt [A] |
| GitHub: pipeline-repo, PAT med `read:packages` åt Railway | Bygge, migrering, Trigger-deploy | 0 $ (publikt repo, eller 12 $ i månatlig kredit för privata) |
| Trigger.dev: 2 projekt, PAT, 2 prod-nycklar | Bakgrundsjobb, e-post | Free 0 $ (5 $ kredit), Hobby 10 $ vid behov |
| AWS: IAM-nyckel och S3 i eu-north-1 | Bevis, PDF:er, kunskapsbas | Under 1 $/mån vid låg volym [A] |
| Resend: API-nyckel och verifierad domän | Inloggningsmejl | 0 $ (3 000 mejl/mån) |
| Vercel: AI Gateway-nyckel | Onboarding-AI (krävs) | Betalt per token. Gratiskredit kräver kort men ger inte ZDR/EU. Ungefär 1–5 $/mån [A] |
| OpenAI: API-nyckel, helst ett EU-projekt | SoA, inbäddningar, policy-AI | Betalt per token, ungefär 1–5 $/mån [A] |
| Anthropic: API-nyckel | Policy-chatt och -redigering | Betalt per token, ungefär 1–5 $/mån [A] |
| Firecrawl (valfritt) | Leverantörsresearch | 0 $ (1 000 krediter). DPA först från Standard |
| DNS hos domänleverantören | Två CNAME till caddy | – |

**Totalt ungefär 30–45 $/mån** vid mycket låg trafik: Railway ungefär 25 $, Trigger 0–10 $, AI ungefär 3–15 $, övrigt
under 1 $ [A].

---

## 4. Risker där planen kan spricka

1. **Inloggning genom proxyn (största risken) [A].**
   - `BASE_URL=http://…` ger kakor utan Secure-flagga och http-länkar i mejlen; Caddy omdirigerar dem.
   - better-auth kan neka origin när `https://`-origin skiljer sig från baseURL. Mildras av `AUTH_TRUSTED_ORIGINS`.
   - Magic link från portalen landar på appens värdnamn. Portalen använder OTP.
   - Testa detta först, gärna med bara api, app och caddy.

   Om det fallerar finns ingen konfigurationsväg kvar. Då krävs en kodändring (lägg till kaknamnet i `proxy.ts`, eller ett
   cookie-domän-env), alternativt drift under `*.trycomp.ai`, vilket är omöjligt.
2. **Overifierad TLS mot Postgres** (`PRISMA_ALLOW_INSECURE_TLS=1`) mot Railways självsignerade certifikat:
   - Internt nät: låg risk.
   - Publik TCP-proxy från Trigger: risk för MITM.
   - `unset NODE_EXTRA_CA_CERTS` och borttagningen i Trigger måste göras efter **varje** deploy. Körningar som startar i
     glappet fallerar.
   - Det är otestat att Railway-Postgres tar emot SSL på det privata nätet [A].
   - Alternativet är en EU-Postgres vars certifikat verifieras utan opt-out, t.ex. AWS RDS eu-north-1, som repot är byggt för.
3. **Trigger.dev lagrar payloads, loggar och utdata i USA** trots EU-körning. Tasks läser hela databasen via den publika proxyn,
   och upp till 20 samtidiga körningar (Free) öppnar var sin anslutning mot Postgres (max_connections ungefär 100 [A]). Ska in i RoPA med SCC.
4. **Byggminne och disk på GitHub-runnern:** 8 GB på privat repo, 14 GB disk. Next-bygget med 6 GB heap kan fallera.
   Använd ett publikt pipeline-repo (16 GB) eller en större runner.
5. **Prisma-motorn och URL-parametrar:** `prisma migrate deploy` med `sslmode=require` mot ett självsignerat certifikat är inte
   verifierat [A]. Om det fallerar, prova `sslaccept=accept_invalid_certs`.
6. **#3681 och nya säkerhetsfixar på main** är inte släppta i någon tagg. Onboardingen kan bete sig annorlunda än i
   dokumentationen.
7. **Policy-PDF och andra klienter med hårdkodad AWS-region och -kedja** fungerar bara mot riktig AWS S3. Railway Buckets eller
   MinIO bryter frågeformulär, kunskapsbas och PDF-visning [V, F3c].
8. **Okänt:**
   - om Next standalone kopierar bygg-`.env` in i imagen (håll dem fria från hemligheter)
   - om Railway accepterar startkommandot för en image med `CMD` i exec-form [A]
   - om `HOSTNAME=::` behövs för Next på Railways IPv6-nät [A]
9. **Trust Center finns inte i CE** (#3445). Device agent kräver egna signerade binärer. Ingen av dem behövs för inloggning
   eller onboarding.
