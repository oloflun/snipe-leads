# Snajp-Support

Headless AI-kundtjänstbackend för Snipra. Arkitekturen är baserad på
[jawwad-ali/ai-customer-support-agent](https://github.com/jawwad-ali/ai-customer-support-agent):
FastAPI som tunt HTTP-lager, agentloop via OpenAI Agents SDK, Postgres/pgvector som
CRM + semantisk kunskapsbas, async jobb med 202 + polling, eskaleringsregler och
kanalspecifik ton. Frontend/demo bor i Next-appen på `/snajp-support`.

## Snabbstart (localhost, Docker — ingen venv)

```powershell
# Terminal 1 — backend (port 8000). Kopiera .env.example -> .env och fyll i.
cd snajp-support
docker compose up

# Terminal 2 — frontend (port 3000)
npm run dev
```

Öppna http://localhost:3000/snajp-support

## LLM-provider (OpenAI eller DeepSeek)

Backenden är provider-agnostisk via `LLM_PROVIDER`:

- `LLM_PROVIDER=openai` → OpenAI (`gpt-4o-mini`), vision + embeddings.
- `LLM_PROVIDER=deepseek` → DeepSeek (`deepseek-chat`) via OpenAI-kompatibla
  `https://api.deepseek.com`. Sätt `DEEPSEEK_API_KEY`.

DeepSeek saknar embeddings-endpoint och vision. Vektorsökning i KB kräver därför en
separat `EMBEDDING_API_KEY` (OpenAI); utan den faller KB tillbaka på full-text-sökning,
och bildbilagor noteras i text istället för att analyseras.

## Lägen (graceful degradation)

| Beroende | Finns | Saknas |
|---|---|---|
| LLM-nyckel för aktiv provider (`OPENAI_API_KEY`/`DEEPSEEK_API_KEY`) | Riktig agent + triage | **Simuleringsläge**: deterministisk svensk regelpipeline, nyckelords-KB-sökning, svar flaggas `simulation: true` |
| `EMBEDDING_API_KEY` (OpenAI) | Embeddings + pgvector-sökning | Full-text-sökning i KB |
| `DATABASE_URL` (Supabase) | Postgres-lagring (`ss_`-tabeller, pgvector) | In-memory-lagring med samma gränssnitt |
| `REDIS_URL` | Redis-jobbkö | In-memory-jobbkö (TTL + 5 min auto-fail) |

`GET /health` visar aktivt läge, provider och modell.

## Aktivera riktig AI + Supabase

1. Fyll i nyckel för vald provider i `snajp-support/.env` (`OPENAI_API_KEY` eller
   `DEEPSEEK_API_KEY` + `LLM_PROVIDER`). Vill du ha vektorsökning i KB: sätt även
   `EMBEDDING_API_KEY` (OpenAI).
2. Kör migrationerna mot Supabase — `002`, `003` och `004` (email-pipeline):
   `npx supabase link --project-ref <ref>` följt av `npx supabase db push`.
3. Sätt `DATABASE_URL` i `snajp-support/.env` (pooler-format, host
   `aws-0-eu-west-1.pooler.supabase.com`, se `.env.example`).
4. Seeda kunskapsbasen: `docker compose run --rm api python -m app.scripts.seed_kb`
   (beräknar embeddings om `EMBEDDING_API_KEY` är satt).
5. Starta om tjänsten (`docker compose restart`, eller redeploy på Render).

## Multi-tenant

Tjänsten är multi-tenant: varje kundföretag (tenant) är helt isolerat.

- **En API-nyckel = en tenant.** Demo-nyckeln mappar till default-tenanten
  (Nordlys Handel). Master-nyckeln är enbart administrativ (skapa tenants/nycklar)
  och kan inte läsa kunddata.
- **Onboarda ett nytt företag:** `POST /api/keys` med master-nyckeln och
  `{"tenant_name": "Företaget AB"}` → skapar tenant + returnerar `snajp_live_`-nyckel
  (visas en gång). Fyll sedan företagets kunskapsbas via `POST /api/kb` med den nyckeln.
- **Isolering:** all data (kunder, ärenden, meddelanden, KB, metrics, jobb) bär
  `tenant_id` och filtreras i varje query. I Postgres-läget sätts dessutom
  `app.tenant_id` per transaktion så RLS-policyerna i
  `supabase/migrations/003_snajp_multitenant.sql` verkställs (försvar-på-djupet).
  Samma kund-e-post hos två tenants blir två separata kundposter.
- **Migrationen `003_snajp_multitenant.sql` körs manuellt** (efter 002):
  `ss_tenants`, `tenant_id` på alla kunddatatabeller (backfyllt till default-
  tenanten), RLS med `FORCE ROW LEVEL SECURITY`.

## Email-pipeline (inkorg → triage → utkast/autosvar → granskning)

Agenten tar emot riktiga kundservicemail, sorterar dem i fack och genererar svar:

1. **Inkorg**: mock-testmail (`POST /api/inbox/mock`), API-ingest från externa system
   (`POST /api/inbox/ingest`) eller riktig inkorg via **IMAP** — täcker både Gmail
   (`IMAP_HOST=imap.gmail.com` + app-lösenord) och Microsoft 365/Outlook
   (`IMAP_HOST=outlook.office365.com`). Sätt `IMAP_HOST/IMAP_USER/IMAP_PASSWORD` i
   `.env` och synka med `POST /api/inbox/sync`, eller sätt `INBOX_POLL_SECONDS=60`
   för bakgrundspolling. Råmail + bilagor (bilder som data-URLs) sparas i databasen.
2. **Triage**: varje mail klassificeras (teknisk_support, leverans, betalning,
   retur_reklamation, orderstatus, konto, ovrigt) med konfidens, sentiment och
   motivering. Bilder tolkas med vision i riktigt läge.
3. **Säkert autosvar**: default är **utkast som kräver godkännande**. Regler per fack
   (`PUT /api/rules`): `auto` skickar direkt endast om konfidens ≥ 0.75 och tonen inte
   är negativ; `escalate` går alltid till människa. Pengar/juridik/GDPR/arga kunder
   och KB-missar eskaleras alltid, oavsett regel.
4. **Granskning**: dashboarden på `/snajp-support` (fliken Dashboard) visar fack,
   status, konfidens och beslutslogg. Godkänn/redigera (`POST /api/drafts/{id}/approve`),
   avvisa (`/reject`) eller ta över (`POST /api/inbox/{id}/takeover`).
5. **Beslutslogg**: varje steg (mottaget, klassificerat, eskalerat, autosvar, godkänt)
   loggas i `ss_decision_log` med motivering.

### Utgående svar (SMTP)

Godkända utkast skickas **på riktigt** till kunden via SMTP. Utan `SMTP_*` ärvs
IMAP-kontot (`imap.gmail.com` → `smtp.gmail.com`), så en kopplad Gmail-inkorg
kan både läsa och svara med samma app-lösenord. Svaret trådas mot kundens
ursprungliga mail via `In-Reply-To`/`References`.

Två säkerhetsregler är inbyggda:

- **Ett ärende markeras som `sent` endast om leveransen lyckades.** Misslyckas
  SMTP ligger utkastet kvar som `pending`, felet returneras (502) och loggas som
  `send_failed` — ingen ska tro att kunden fått svar när den inte har det.
- **`ALLOW_AUTO_SEND=false` är en hård global spärr.** Även om en kategori står
  på `auto` skickas ingenting utan mänskligt godkännande; försöket loggas som
  `auto_send_blocked` och svaret läggs som utkast. Håll den avstängd under pilot.

`POST /api/drafts/{id}/approve` tar `send: false` för att godkänna utan utskick
(texten hanteras då manuellt — dashboarden har en kopieringsknapp).

## API (X-API-Key krävs, se `.env`)

| Metod | Endpoint | Beskrivning |
|---|---|---|
| POST | `/api/chat` | Kundmeddelande (+ ev. bildbilagor som data-URL) → `202 {job_id}` |
| GET | `/api/jobs/{job_id}` | Polla: `processing → completed/failed`, `result` innehåller svar, fack, sentiment, eskalering, KB-källor |
| POST | `/api/triage` | Batch-sortering av mail i fack + svarsutkast (synkron) |
| GET | `/api/tickets/{id}` | Ärende med meddelandehistorik |
| GET | `/api/customers/{id}/history` | Kundens alla ärenden |
| POST | `/api/keys` | Skapa tenant + API-nyckel (kräver master-nyckel) |
| GET | `/api/kb` | Lista tenantens egna kunskapsbasartiklar |
| POST | `/api/kb` | Lägg till artiklar i tenantens kunskapsbas |
| POST | `/api/inbox/mock` | Seeda och processa svenska testmail |
| POST | `/api/inbox/ingest` | API-first: externa system postar inkommande mail |
| POST | `/api/inbox/sync` | Hämta nya mail från IMAP (Gmail/Outlook) nu |
| GET | `/api/inbox?status=&category=&q=` | Lista mail med klassificering + utkast |
| GET | `/api/inbox/{id}` | Detalj: bilagor, klassificering, beslutslogg |
| POST | `/api/inbox/{id}/takeover` | Människa tar över ärendet |
| POST | `/api/drafts/{id}/approve` | Godkänn (ev. redigerat) och skicka |
| POST | `/api/drafts/{id}/reject` | Avvisa utkastet |
| GET/PUT | `/api/rules` | Autosvarsregler per fack (auto/draft/escalate) |
| GET | `/health` `/health/live` `/health/ready` | Status/probes |

Fack: `teknisk_support`, `leverans`, `betalning`, `retur_reklamation`, `orderstatus`,
`konto`, `ovrigt`.

## Tester

```powershell
cd snajp-support
docker compose run --rm api python -m pytest tests -q
```

Testerna kör i simuleringsläge och kräver inga nycklar.

## Deploy (Render)

Backenden auto-deployas från GitHub via `render.yaml` (Blueprint):

1. Skapa en Blueprint i Render och peka på repot → Render läser `snajp-support/render.yaml`.
2. Sätt secrets i dashboarden: `DEEPSEEK_API_KEY`, `SNAJP_MASTER_API_KEY`,
   `SNAJP_DEMO_API_KEY` (och valfritt `DATABASE_URL`, `EMBEDDING_API_KEY`).
3. Notera tjänstens URL, t.ex. `https://snajp-support.onrender.com`.
4. På Vercel: sätt `SNAJP_SUPPORT_URL` = Render-URL:en och `SNAJP_INTERNAL_API_KEY`
   = samma värde som `SNAJP_DEMO_API_KEY`. Frontenden pratar då med Render-backenden.

Free-tier spinner ner vid inaktivitet → första anropet efter idle tar ~30–60 s (cold
start). Health-probes: `/health/live`, `/health/ready`. `docker-compose.yml` (API + Redis)
finns kvar för lokal körning.
