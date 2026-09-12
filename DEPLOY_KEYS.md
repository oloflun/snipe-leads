# Nycklar: lokalt och vid deploy

## Kort svar på "kan vi lagra dem i Supabase?"

**Nej — och det löser inte problemet.** Två skäl:

1. **Det bryter mot en invariant vi själva satt.** `ARCHITECTURE_INVARIANTS.md`
   INV-SEC-006 / plan G5: *"Hemligheter i env, aldrig i databasen."* Skälet är
   konkret: en läsbehörighet på en tabell ska aldrig räcka för att komma åt
   kundens mejlkonto eller vår LLM-faktura. Samma resonemang som redan gäller
   `IMAP_PASSWORD_<SLUG>` i [TENANTS.md](TENANTS.md).
2. **Det är cirkulärt.** För att läsa en nyckel ur Supabase behöver tjänsten en
   Supabase-nyckel — som måste ligga i env. Man har alltså inte tagit bort
   env-beroendet, bara lagt till ett extra ställe där hemligheter kan läcka.

Undantaget vore Supabase Vault (`vault.secrets`, krypterad i vila) för
**per-kund-hemligheter som måste kunna roteras utan en deploy** — t.ex. om
varje kund en dag får egen SMTP. Det är en annan sak än att flytta våra
plattformsnycklar dit, och behövs inte i dag.

---

## Ett verktyg, körs varifrån som helst

```bash
python "C:\Users\Anton L\snipe-leads\scripts\keys.py"
```

Sökvägar löses ur skriptets egen plats, inte ur `cwd` — du behöver inte stå i
repot. Värdena läses med `getpass`: de syns aldrig på skärmen och hamnar
aldrig i shell-historiken. Skriptet vägrar köra om målfilerna inte är
gitignorerade.

| Kommando | Gör |
| --- | --- |
| `keys.py` | Frågar efter nycklarna, skriver till `snajp-support/.env`, verifierar |
| `keys.py --check` | Verifierar bara (visar längd + fyra sista tecken, aldrig värdet) |
| `keys.py --pull` | Hämtar env från Vercel till `.env.local` (Email Studio-relaterat, se nedan) |
| `keys.py --push` | Skickar Vercel-relevanta nycklar dit. I dag är alla tre backend/Render-hemligheter, så den har inget att skicka — se Render-tabellen nedan. |

**Du behöver bara `DEEPSEEK_API_KEY` för att komma igång.** Den driver alla
agentkörningar. De andra två är valfria och låser bara upp delfunktioner —
och båda är valda specifikt för sina GRATISNIVÅER:

| Nyckel | Krävs? | Utan den |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | **Ja** | Ingenting kan köras — allt faller till simuleringsläge |
| `SCRAPEGRAPHAI_API_KEY` | Nej | Fas B-research kan inte skrapa prospektsajter |
| `GEMINI_API_KEY` | Nej* | Ingen bildbeskrivning i ärenden; KB använder fulltext i stället för vektorsökning |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Nej* | Vertex AI service account JSON — ersätter GEMINI_API_KEY |
| `GOOGLE_CLOUD_REGION` | Nej | Default `europe-west1`. Bara om annan region behövs |

\* Minst en av `GEMINI_API_KEY` eller `GOOGLE_SERVICE_ACCOUNT_JSON` krävs för
Gemini. Sedan Google tog bort Cloud-krediter från AI Studio (2026-09) behövs
`GOOGLE_SERVICE_ACCOUNT_JSON` — den innehåller hela JSON-filen från
Google Cloud Console (service account key). Är den satt används Vertex AI
med OAuth2-tokens i stället för AI Studio med enkel API-nyckel.

Nycklarna skapas en gång i respektive tjänsts dashboard — det går inte att
automatisera, och ska inte gå att automatisera:

- DeepSeek: <https://platform.deepseek.com/api_keys>
- ScrapeGraphAI: <https://dashboard.scrapegraphai.com>
- Gemini (gratisnivå): <https://aistudio.google.com/apikey>

**Not om OpenAI:** Email Studio (`app/api/email-studio/route.ts`, Next.js-sidan)
har en egen, separat `OPENAI_API_KEY` i `.env.local` — orört av den här
omläggningen. Det är en annan integration (Vercel AI SDK) än backendens
vision/embeddings-sidovagn. Säg till om den också ska bytas till Gemini.

---

## Deploy

### Backend (Railway) — huvudsaklig deploy-plattform sedan 2026-08

Nycklarna sätts via skript — ALDRIG genom att klistra in dem i Railway-
dashboarden (de hamnar i shell-historiken):

```bash
# Sätt GOOGLE_SERVICE_ACCOUNT_JSON lokalt (frågar efter filsökväg):
python scripts/keys.py --key GOOGLE_SERVICE_ACCOUNT_JSON

# Pusha alla backend-nycklar till BÅDA Railway-miljöerna och verifiera:
python scripts/keys.py --push-railway
```

| Variabel | Värde |
| --- | --- |
| `LLM_PROVIDER` | `gemini` |
| `MODEL` | `gemini-2.5-flash` |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Hela JSON-filen som en rad (sätts av `keys.py`) |
| `GEMINI_API_KEY` | AI Studio-nyckel (fallback, gratisnivå — 20 anrop/dygn) |
| `DEEPSEEK_API_KEY` | Bara för lokal syntetisk data, SPÄRRAD i main/development |

**Obs:** `LLM_PROVIDER=deepseek` vägrar starta i miljöer med riktig kunddata
(main, development). Det är en dataskyddsspärr, inte en bugg — se CLAUDE.md.

### Frontend (Vercel — avvecklat för backend)

Email Studio (`app/api/email-studio/route.ts`) har en separat `OPENAI_API_KEY`
i `.env.local`. Den rörs inte av Vertex AI-omläggningen.

---

## Vad som går sönder utan nycklar

`app/config.py:is_simulation()` behandlar en tom eller platshållarliknande
nyckel som "ingen nyckel". Då:

- **Supporten** faller tillbaka på `app/simulation/sim_agent.py` — deterministiska
  svar, ingen riktig agent, inga skills lästa.
- **Leads-ytorna** (`/api/leads/onboarding/chat`, `/research/step`,
  `/outreach/draft`) svarar `503` med en förklarande text i stället för att
  köra på låtsas.
- **ScrapeGraphAI-verktyget** returnerar ett tydligt fel i stället för att
  skrapa.

Det är avsiktligt: tjänsten ska degradera synligt, inte tyst producera
påhittade svar.
