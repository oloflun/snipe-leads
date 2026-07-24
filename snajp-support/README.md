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
| GET | `/health` `/health/live` `/health/ready` | Status/probes |

Fack: `teknisk_support`, `leverans`, `betalning`, `retur_reklamation`, `konto`, `ovrigt`.

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
