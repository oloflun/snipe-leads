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
| `GEMINI_API_KEY` | Nej | Ingen bildbeskrivning i ärenden; KB använder fulltext i stället för vektorsökning |

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

### Backend (Render — `snajp-support`) — där alla tre nycklar hör hemma

Render CLI:t kan inte skriva env-variabler utan en separat API-token, så det
här steget görs i dashboarden: **snajp-support → Environment**.

| Variabel | Värde |
| --- | --- |
| `DEEPSEEK_API_KEY` | din nyckel |
| `SCRAPEGRAPHAI_API_KEY` | din nyckel (om Fas B ska köra) |
| `GEMINI_API_KEY` | din nyckel (om vision/embeddings ska köra) |
| `LLM_PROVIDER` | `deepseek` |
| `MODEL` | `deepseek-v4-flash` |

`render.yaml` deklarerar redan `DEEPSEEK_API_KEY` och `GEMINI_API_KEY` med
`sync: false` — det betyder just "värdet sätts i dashboarden, inte i repot".

### Frontend (Vercel)

Inget i den här omläggningen behöver Vercel — se noten om Email Studios
separata `OPENAI_API_KEY` ovan om den frontend-integrationen ska bytas också.

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
