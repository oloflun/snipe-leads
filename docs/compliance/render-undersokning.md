# Render: vad fyller det för funktion i dag?

Undersökt 2026-11-17 23:21 till 2026-11-18 ca 00:30 UTC. Endast läsning: GET mot Renders API och de publika hälsoadresserna, `git`/`gh` i läsläge, DNS-uppslag. Inga ändringar hos Render, Railway eller i repot.

Belägg:
- `D:\comp-compliance\evidence\render-lage-2026-11-18.txt`: tjänster, deployer, variabelnamn, domäner, övriga resurser, hälsosvar. Skript: `scripts\render_lage.py`.
- `D:\comp-compliance\evidence\render-loggar-2026-11-18.txt`: hela deployhistoriken och en sammanställning av loggarna. Skript: `scripts\render_loggar.py`.
- `scripts\render_logg_sok.py`: riktad loggsökning. Den skriver bara ut tid och HTTP-rad.

## Kort svar

Render fyller **ingen funktion** för Snajp i dag. Ingenting i produkten, i Railway eller i DNS pekar dit, och loggarna visar ingen trafik från kunder.

Båda tjänsterna lever ändå, och de håller kvar hemligheter: en Gmail-inkorg, anslutningar till de två gamla Supabase-databaserna och API-nycklar. Previewtjänsten deployar dessutom om sig själv vid varje push till `development` och kör bakgrundsjobb mot den gamla preview-databasen. Ingenting behöver flyttas till Railway. Allt ska stängas.

## 1. Kontot (Renders API)

- Nyckeln `RENDER_API_KEY` i `.env.deploy` **godtas fortfarande** (`GET /owners` gav 200 kl. 2026-11-17T23:21Z). Det är samma nyckel som exponerades 2026-08-24 och 2026-08-28 (`INCIDENT_RESPONSE.md:85`, `session-logs/2026-08-28-session-log.md:59`). Den är alltså inte roterad.
- Workspace: ett team, `Snajp` (`tea-d9k8rbht0dsc7396t5bg`). Ett projekt, `Snajp`.

| Tjänst | Id | Typ / plan / region | Gren | autoDeploy | Avstängd | Skapad | Senaste lyckade deploy | Senaste försök |
|---|---|---|---|---|---|---|---|---|
| snajp-support | srv-d9k99ktg1s2s73fl0v6g | web, docker, **free**, frankfurt | main | yes | **nej** (`not_suspended`) | 2026-07-28 | **2026-08-24 23:28Z, commit 860c74d0** (PR #7) | 2026-11-17 11:09Z, fe43310a, `update_failed` |
| snajp-support-dev | srv-da0dopojo6nc73ea3b6g | web, docker, **free**, frankfurt | development | yes | **nej** | 2026-08-15 | **2026-11-17 23:21Z, commit 1b44c364** (PR #45) | samma, `live` |

- Produktionstjänsten: 65 deployer. Alla 32 försök sedan 2026-09-14 har misslyckats (`update_failed`). Den nya koden vägrar starta: "LLM_PROVIDER=deepseek är inte tillåtet här" (loggrad 2026-11-17T11:10:36Z). Därför kör den fortfarande koden från 2026-08-24. Den koden ligger **1 102 commits** efter `main` och saknar spärren `llm_provider_fault` (`git grep` på 860c74d0 ger noll träffar).
- Previewtjänsten: 758 deployer, 738 av dem lyckade. Den följer `development` commit för commit. Senast deployade den 2026-11-17T23:21Z, 50 sekunder efter att PR #45 mergades.
- Egna domäner: inga på någon av tjänsterna. Inga secret files.
- Övriga resurser: 0 Postgres, 0 key-value/Redis, 0 env-grupper, **0 blueprints**, 0 diskar, 0 registry-credentials, 0 webhooks. Tjänstetyperna är bara `web_service` × 2, så det finns inga cron-jobb, statiska sajter eller workers. (`/cron-jobs` finns inte som endpoint och gav 404. Cron-jobb är en tjänstetyp och skulle ha syns i `/services`.)

### Miljövariabler (namn, aldrig värden)

**snajp-support (produktion):** ALLOW_AUTO_SEND, AUTO_SEND_MIN_CONFIDENCE=0.75, DATABASE_URL → `postgresql://aws-0-eu-west-1.pooler.supabase.com:6543`, DEEPSEEK_API_KEY (tom), GEMINI_API_KEY, IMAP_FOLDER=INBOX, IMAP_HOST → `imap.gmail.com`, IMAP_PASSWORD, IMAP_TENANT, IMAP_USER, INBOX_POLL_SECONDS=0, **LLM_PROVIDER=deepseek, MODEL=deepseek-v4-flash**, PILOT_TENANT_NAME, SCRAPEGRAPHAI_API_KEY, SMTP_FROM_NAME, SNAJP_DEMO_API_KEY, SNAJP_MASTER_API_KEY, SNAJP_PILOT_API_KEY, SNAJP_SKILL_UNLOCK_KEY.

**snajp-support-dev (preview):** AUTO_SEND_MIN_CONFIDENCE=0.75, DATABASE_URL → `postgresql://aws-1-eu-west-1.pooler.supabase.com:6543`, DEEPSEEK_API_KEY (tom), GEMINI_API_KEY, IMAP_FOLDER=INBOX, INBOX_POLL_SECONDS=0, LLM_PROVIDER=openai, MODEL=gpt-4o-mini (ingen OpenAI-nyckel finns), SCRAPEGRAPHAI_API_KEY, SNAJP_DEMO_API_KEY, SNAJP_MASTER_API_KEY, SNAJP_SKILL_UNLOCK_KEY.

## 2. Lever tjänsterna?

Ja, båda två. Hälsoanrop 2026-11-17 ca 23:25Z:

- `snajp-support.onrender.com/health` → 200 efter 18,7 s (kallstart): `mode: simulation`, `model: deepseek-v4-flash`, `storage: postgres`. `/health/ready` → 200, `degraded: true`, med varningarna "Ingen giltig LLM-nyckel" och "Ingen riktig sändväg".
- `snajp-support-dev.onrender.com/health` → 200 efter 0,5 s: `mode: simulation`, `model: gpt-4o-mini`, `storage: postgres`. `/health/ready` → 200, `degraded`.
- Ingen av dem använder alltså en språkmodell i dag. Båda **ansluter till sin gamla Supabase-databas**. Produktionen loggar "Lagring: Postgres (Supabase)" vid varje start. Previewen kör frågor mot sin databas, se nedan.

### Trafiken enligt loggarna (ingen loggrad innehöll en e-postadress)

**Produktionen** (2 770 rader, 2026-11-11 13:11Z till 2026-11-17 23:26Z):
- 2 258 `GET /health/live` från 10.x: Renders egen hälsokontroll.
- Tjänsten startar bara när GitHub-pingen väcker den. Starttiderna stämmer med körningarna av workflowen "Håll Snajp-Support vaken" (`gh run list`). Exempel: 11-12 14:09:15 körning och 14:09:34 start; 11-16 23:23:53 och 23:24:10; 11-17 22:50:23 och 22:50:39. Övriga starter är deployförsök.
- **Två `POST /api/chat/samtal` → 404** 2026-11-17 11:10:38Z och 11:10:39Z, under ett misslyckat deployförsök. Den sökvägen finns inte i koden från augusti, men den finns i dagens kod. Någon klient med den nya koden har alltså anropat Render-adressen. Källan går inte att se, eftersom Renders proxy döljer adressen (10.x). Se punkt 5(v).
- Ingen IMAP-, SMTP- eller utskicksaktivitet. INBOX_POLL_SECONDS=0.

**Previewen** (2 000 rader från 2026-11-16 07:13Z, sedan svarade API:t 429 för rate limit):
- 175 `GET /health/live` (Render), ett `HEAD /` från en extern adress (en skanner), inga API-anrop utifrån.
- **Bakgrundsjobb körs varje minut** mot den gamla preview-databasen: `vack_stillastaende_korningar` och `jobs.stadare`. Båda faller på `relation "leads_job_ledger" does not exist`. Tjänsten **ansluter alltså och kör frågor** mot preview-Supabase. Jobben körs per kund-id (maskade i belägget).

## 3. Pekar något på Render?

**(a) Koden** (sökt i arbetsträdet och på `origin/main` och `origin/development`):

| Träff | Vad den gör | Mer än historik? |
|---|---|---|
| `.github/workflows/keep-backend-awake.yml` | Pingar `snajp-support.onrender.com/health/live` var tionde minut, vardagar 06–17 UTC. | Ja, och den var verksam till och med 2026-11-17. Schemalagda körningar går från förvalsgrenen `development`. Där togs filen bort när PR #45 mergades 2026-11-17T23:20:27Z. Sista körningen var 22:50:23Z. Filen **ligger kvar på `main`** (`git show origin/main:...`) men körs inte därifrån. `gh workflow list --all` visar den inte längre. |
| `scripts/keys.py:540-545` `RENDER_SERVICES`, `:688-817` `cmd_push_render`, `:861-862` och `:918-919` flaggan `--push-render` | Läser `RENDER_API_KEY`. Skriver sedan med **PUT** `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `SCRAPEGRAPHAI_API_KEY` och `SNAJP_SKILL_UNLOCK_KEY` ur `snajp-support/.env`, plus `LLM_PROVIDER=deepseek` och `MODEL=deepseek-v4-flash` (`FIXED`, rad 158), till **båda** Render-tjänsterna. Därefter startar den deployer med POST. | **Ja, en fara.** Det räcker att någon kör `python scripts/keys.py --push-render` för att lägga fler hemligheter hos Render och slå på DeepSeek där igen. Den körs bara med den flaggan, inte av `--push`. |
| `scripts/verify_render.py` | Läser tjänstelistan (GET). Exporterar `api_key()` och `API`, som `keys.py` använder. | Bara läsning, men det är beroendet som håller Render-koden i `keys.py` vid liv. |
| `snajp-support/render.yaml` | Blueprint märkt VILANDE. Ingen blueprint är registrerad hos Render (`/blueprints` gav 0). | Nej, den styr ingenting. Men `tests/invariants/test_inv_deploy_001.py:32,57,169` läser filen, så testet måste ändras när filen raderas. |
| `app/api/snajp-support/_lib.ts:6,8` | Kommentar om "Render-URL:en". Förvalet är `http://127.0.0.1:8000`, inte Render. | Nej, kommentaren är inaktuell. |
| `public/widget.js:38-40` | Tar sin origin från sin egen `script.src` och har ingen hårdkodad värd. | Nej. |
| `snajp-support/tests/test_dataskydd_provider.py:171` | Ett påhittat render.com-värdnamn i ett test. | Nej. |
| Dokument: `DEPLOY.md:126-128,199-227,566-600,645`, `snajp-support/README.md:140-145` (säger åt läsaren att skapa en Render-blueprint), `RAILWAY.md:16`, `DEPLOY_KEYS.md:39`, `ARCHITECTURE_INVARIANTS.md:250,426,429`, `INCIDENT_RESPONSE.md:85-86`, `docs/JURIDIK_ATGARDER.md:68`, `docs/dpia_supportagenten.md:130` | Historik och öppna poster. | `snajp-support/README.md` är den enda som ger en instruktion att använda Render. |

**(b) Railway.** `evidence/railway-konfiguration-2026-11-17-efter.txt` innehåller 0 träffar på "render" eller "onrender". `SNAJP_SUPPORT_URL` pekar på `api-production-d7695.up.railway.app` (main, rad 198 och 301) och `api-development-5cc3.up.railway.app` (development, rad 34 och 154).

**(c) DNS** (Resolve-DnsName, 2026-11-18). Inget namn pekar på Render, vars adresser är `*.onrender.com` eller 216.24.57.x.
- `www.snajp.se` → CNAME `2yamxcbe.up.railway.app` (Railway).
- `snajp.se` → A 76.76.21.21. Det är **Vercel**, som bara svarar `308 → https://www.snajp.se/` (`Server: Vercel`). Det är inte Render, men det är en rest av den avvecklade stacken. Se punkt 5(v).
- `api`, `support`, `app`, `session`, `livrustning`, `test`, `hej`, `dev` och `admin.snajp.se` → 194.9.94.85/86. Det är Loopias jokertecken eller parkering, och inga av dem har en egen post.
- `send.snajp.se` → CNAME `send.forge.rmta.net`, som är en e-postsändare. MX för `snajp.se` går till Loopia.

**(d) Externa integrationer.** Webhookadresser för kanaler byggs av `API_PUBLIK_URL` eller `RAILWAY_PUBLIC_DOMAIN` (`snajp-support/app/api/kanaler.py:63-76`), aldrig av en Render-adress. Koden som kör på Render i produktion är från augusti och har inga kanaler. Render-kontot har inga webhooks (`/webhooks` gav 0). Vad som är sparat i Resends, Metas, Slacks, Googles och Microsofts egna konsoler går inte att läsa härifrån.

## 4. Vad kör där?

- **Produktionen:** commit 860c74d0 från 2026-08-17, deployad 2026-08-24. Den är en förfader till `main` men ligger 1 102 commits efter. Railways api-tjänst i main följer `main` (fe43310a). Render kör alltså **en tre månader gammal version** av samma backend. Den är utan DeepSeek-spärren och ansluten till **den gamla Supabase-produktionsdatabasen** (`aws-0-eu-west-1.pooler.supabase.com`). Den är nåbar från internet med sin egen `SNAJP_MASTER_API_KEY`.
- **Previewen:** samma kod som `development` (1b44c364), ansluten till **den gamla preview-Supabase** (`aws-1-eu-west-1.pooler.supabase.com`). Railway development använder i stället `postgres.railway.internal`.
- **Språkmodell:** ingen i bruk, båda kör i simuleringsläge. Produktionen är konfigurerad för DeepSeek med tom nyckel. Previewen är konfigurerad för OpenAI utan nyckel.
- **Inloggningsuppgifter till riktiga system som ligger hos Render:**
  - Gmail-inkorg: `IMAP_HOST` (imap.gmail.com), `IMAP_USER`, `IMAP_PASSWORD`, `IMAP_TENANT` (produktionen).
  - Gamla databaser: `DATABASE_URL` på båda. Där ligger användare och lösenord till Supabase-prod respektive Supabase-preview.
  - API-nycklar: `GEMINI_API_KEY`, `SCRAPEGRAPHAI_API_KEY` och `SNAJP_SKILL_UNLOCK_KEY` (båda tjänsterna). `keys.py --push-render` skickar samma lokala värden som `--push-railway`, så de är troligen **identiska med Railways**.
  - Snajps egna nycklar: `SNAJP_MASTER_API_KEY` och `SNAJP_DEMO_API_KEY` (båda), `SNAJP_PILOT_API_KEY` (produktionen).
  - Inget sändkonto: ingen SMTP_HOST, ingen Resend-nyckel. `SMTP_FROM_NAME` är bara ett namn.

## 5. Slutsats

### (i) Vad fyller Render för funktion i dag?
**Ingen.** Inget pekar på Render: inte DNS (3c), inte Railway (3b), inte Next-delen eller widgeten (3a), och kontot har inga egna domäner (1). Det enda som har anropat tjänsterna är GitHub-pingen, Renders egen hälsokontroll, en skanner och två okända chattanrop som fick 404 (2). Inga mejl tas emot och inga skickas.

Render är i dag bara en risk. Två internetnåbara tjänster bär lösenord till en Gmail-inkorg och två gamla databaser. Previewen kör jobb mot sin databas varje minut och deployar om vid varje push.

### (ii) Finns det något på Render som inte redan finns på Railway?
Nej. Det finns ingen databas, ingen disk, ingen Redis, inga cron-jobb, inga domäner och inga filer på Render (1). Backendkoden finns på Railway i en nyare version.

Variablerna som bara finns hos Render (`IMAP_HOST`, `IMAP_USER`, `IMAP_PASSWORD`, `IMAP_TENANT`, `PILOT_TENANT_NAME`, `SNAJP_PILOT_API_KEY`, `ALLOW_AUTO_SEND`) hör till den gamla modellen med en enda pilotinkorg. Railway har ersatt den (`IMAP_PASSWORD_SNAJP` på api i båda miljöerna, evidence rad 93 och 246). Ingenting behöver flyttas. Om Gmail-kontot på Render är ett annat än Railways och fortfarande ska användas läggs det in som en kund-inkorg via Railway-vägen, inte som en kopia av Render-variablerna. Det gick inte att avgöra här, se (v).

### (iii) Avveckla Render helt, i ordning

| # | Steg | Vem |
|---|---|---|
| 1 | Ta bort pingen. Den är redan gjord på `development` (PR #45, 2026-11-17T23:20Z) och följer med `main` vid nästa release. | Gjort / Anton mergar releasen |
| 2 | Suspendera båda tjänsterna i Render-dashboarden. Det stoppar previewens jobb mot den gamla databasen och auto-deployerna direkt. Exportera loggarna först om de behövs för incidentbedömningen (gratisnivån sparar dem bara kort). | Anton |
| 3 | Radera båda tjänsterna (Settings → Delete). Avinstallera Render GitHub-appen eller ta bort dess åtkomst till `oloflun/snipe-leads` (GitHub → Settings → Applications). Den har i dag läsåtkomst till det privata repot för att kunna auto-deploya. | Anton |
| 4 | Rotera det som legat hos Render, se (iv). Sätt sedan de nya värdena på Railway med `keys.py --push-railway`, där samma nycklar används. | Anton roterar hos leverantören, agenten kan pusha till Railway och verifiera |
| 5 | Ta bort Render-koden: `RENDER_SERVICES`, `cmd_push_render` och `--push-render` i `scripts/keys.py`, `scripts/verify_render.py`, `snajp-support/render.yaml`, och ändra `tests/invariants/test_inv_deploy_001.py` (och kontrollera `ARCHITECTURE_INVARIANTS.md`, INV-DEPLOY-001). Allt i en PR mot `development`. | Agenten förbereder, Anton godkänner |
| 6 | Radera API-nyckeln i Render (Account Settings → API Keys), stäng Render-kontot eller teamet och ta bort `RENDER_API_KEY` ur `.env.deploy`. | Anton (nyckel och konto), agenten (raden i `.env.deploy` på Antons ord) |
| 7 | Begär raderingsbekräftelse från Render (support eller privacy) för tjänsterna, loggarna och miljövariablerna. | Anton |
| 8 | Stryk Render ur dokumenten: `snajp-support/README.md:140-145`, `DEPLOY.md` (avsnitten Render och Legacy), `RAILWAY.md:16`, `DEPLOY_KEYS.md`, `docs/dpia_supportagenten.md:130`, `docs/registerforteckning.md` om Render står som biträde, kommentaren i `app/api/snajp-support/_lib.ts:6`. Skriv beslutet i `docs/BESLUT.md`. | Agenten |
| 9 | Stäng `INCIDENT_RESPONSE.md:85-86` och `docs/JURIDIK_ATGARDER.md:68` (P0.2, P0.2b) med datum för suspendering, radering, rotation och bekräftelse, och bedöm posterna (anmälningsplikt). | Anton bedömer, agenten skriver in |

Den gamla Supabase-projektets radering hör till samma post (JURIDIK nr 15) men är ett separat steg.

### (iv) Hemligheter som bör roteras för att de legat hos Render
- `RENDER_API_KEY` (exponerad 2026-08-24 och 08-28, godtas fortfarande).
- `IMAP_PASSWORD` (Gmail-applösenord), och granska `IMAP_USER`-kontots åtkomst.
- `DATABASE_URL` på båda: lösenorden till Supabase-prod och Supabase-preview. Görs genom att radera projekten eller byta lösenorden.
- `GEMINI_API_KEY`, `SCRAPEGRAPHAI_API_KEY` och `SNAJP_SKILL_UNLOCK_KEY`. Troligen samma värden som på Railway, så rotationen måste föras över till Railway samtidigt.
- `SNAJP_MASTER_API_KEY`, `SNAJP_DEMO_API_KEY` och `SNAJP_PILOT_API_KEY`. De ger bara åtkomst till Render-instanserna och de gamla databaserna, och de dör med tjänsterna. Rotera dem bara om samma värde används på Railway. Railway slumpar egna värden (`keys.py:525-527`).

### (v) Det som inte gick att belägga
- **Vem som skickade de två `POST /api/chat/samtal`** 2026-11-17 11:10Z. Renders proxy döljer källadressen. En misstänkt källa är det gamla Vercel-projektet som fortfarande svarar på `snajp.se` (A 76.76.21.21), om det har kvar `SNAJP_SUPPORT_URL` mot Render. Det är inte kontrollerat.
- **Tredje parters sparade adresser** (Resend, Meta/WhatsApp, Slack, Teams, Google och Microsoft OAuth, kunders inbäddningar). Inget i koden eller i Render-kontot pekar dit, men konsolerna har inte lästs.
- **Om Render-värdena är identiska med Railways** (Gemini, ScrapeGraph, skill-nyckel, Gmail-kontot). Värdena jämfördes inte, med flit.
- **Om gamla Supabase-databaserna innehåller persondata i dag.** Previewen ansluter och kör frågor mot sin databas, och produktionen ansluter vid start. Innehållet har inte lästs.
- **Om ett skarpt anrop med `SNAJP_MASTER_API_KEY` mot Render-produktionen kan läsa ur den gamla databasen eller trigga en IMAP-hämtning** (koden från augusti har `api/inbox.py`). Det är inte prövat, eftersom det vore att använda tjänsten.
- **Previewloggarna före 2026-11-16 07:13Z.** API:t svarade 429 innan sökningen nått så långt bak. Produktionsloggarna sträcker sig till 2026-11-11.
