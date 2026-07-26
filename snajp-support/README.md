# Snajp-Support

Headless AI-kundtjänstbackend för Snipra. Arkitekturen är baserad på
[jawwad-ali/ai-customer-support-agent](https://github.com/jawwad-ali/ai-customer-support-agent):
FastAPI som tunt HTTP-lager, agentloop via OpenAI Agents SDK, Postgres/pgvector som
CRM + semantisk kunskapsbas, async jobb med 202 + polling, eskaleringsregler och
kanalspecifik ton. Frontend/demo bor i Next-appen på `/snajp-support`.

## Snabbstart (localhost)

```powershell
# Terminal 1 — backend (port 8000)
cd snajp-support
python -m venv .venv                       # första gången
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\uvicorn app.main:app --port 8000

# Terminal 2 — frontend (port 3000)
npm run dev
```

Öppna http://localhost:3000/snajp-support

## Lägen (graceful degradation)

| Beroende | Finns | Saknas |
|---|---|---|
| `OPENAI_API_KEY` (riktig) | Riktig agent (gpt-4o-mini), vision, embeddings + vektorsökning | **Simuleringsläge**: deterministisk svensk regelpipeline, nyckelords-KB-sökning, svar flaggas `simulation: true` |
| `DATABASE_URL` (Supabase) | Postgres-lagring (`ss_`-tabeller, pgvector) | In-memory-lagring med samma gränssnitt |
| `REDIS_URL` | Redis-jobbkö | In-memory-jobbkö (TTL + 5 min auto-fail) |

`GET /health` visar aktivt läge.

## Aktivera riktig AI + Supabase

1. Fyll i riktig `OPENAI_API_KEY` i `snajp-support/.env` (och i rotens `.env.local` om Email Studio också ska bli live).
2. Fyll i riktigt `SUPABASE_DB_PASSWORD` i rotens `.env` och kör `node scripts/apply-snajp-migration.mjs` (skapar `ss_`-tabellerna).
3. Sätt `DATABASE_URL` i `snajp-support/.env` (pooler-format, host `aws-0-eu-west-1.pooler.supabase.com`, se `.env.example`).
4. Seeda kunskapsbasen: `.venv\Scripts\python -m app.scripts.seed_kb` (beräknar embeddings med riktig nyckel).
5. Starta om uvicorn.

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

Utgående sändning är i detta steg **simulerad och loggad** (samma avgränsning som
referensrepot) — riktig SMTP/Gmail/Graph-sändning är nästa iteration.

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

Fack: `teknisk_support`, `leverans`, `betalning`, `retur_reklamation`, `konto`, `ovrigt`.

## Tester

```powershell
cd snajp-support
.venv\Scripts\python -m pytest tests -q
```

## Deploy

`Dockerfile` + `docker-compose.yml` medföljer (API + Redis). Sätt env-variablerna
från `.env.example` som secrets. Kubernetes-mönstret från referensrepot (probes mot
`/health/live` och `/health/ready`) fungerar rakt av.
