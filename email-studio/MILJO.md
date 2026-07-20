# Miljövariabler

## Skapa `.env.local`

```powershell
cd C:\Users\sebbe\snipe-leads
copy email-studio\env\.env.local.example .env.local
```

Redigera `.env.local` i projektroten (aldrig committa den).

## Supabase (redan konfigurerat)

| Variabel | Beskrivning |
|----------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://spsmblyvasagpekjmgmf.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Publishable key (`sb_publishable_...`) |
| `SUPABASE_SERVICE_ROLE_KEY` | Secret key (server only) |
| `NEXT_PUBLIC_SITE_URL` | `http://localhost:3000` lokalt |

Schema är applicerat (`npm run apply:schema`). 15 tabeller + signup-trigger live.

## LLM — Email Studio

| Variabel | Beskrivning |
|----------|-------------|
| `LLM_PROVIDER` | `deepseek` (rekommenderat) eller `openai` |
| `DEEPSEEK_API_KEY` | **Krävs för live DeepSeek** — hämta från platform.deepseek.com |
| `OPENAI_API_KEY` | Alternativ; placeholder `sk-...` → simulation |
| `LLM_REFINE_MODEL` | `deepseek-chat` eller `gpt-4o-mini` |
| `LLM_GENERATE_MODEL` | Samma som ovan |

### Simulation vs live

- **Ingen giltig API-nyckel** → `route.ts` kör `simulateAction()` (begränsad men testbar)
- **Giltig nyckel** → riktigt LLM-anrop med marketing skills i prompten

**Efter ändring:** starta om dev-servern.

## Supabase Dashboard (manuellt)

1. Gå till Authentication → Providers → Email
2. Stäng av **Confirm email** (annars fastnar signup)
3. (Valfritt) höj rate limits om du testar många konton

## Starta server (PowerShell)

```powershell
cd C:\Users\sebbe\snipe-leads
$env:PATH = "C:\Program Files\nodejs;" + $env:PATH
npm.cmd run dev
```

## API-test (curl / Postman)

```
POST http://localhost:3000/api/email-studio
Content-Type: application/json

{
  "action": "shorter",
  "draft": "Hej, vi såg att ni expanderar...",
  "subject": "Kort idé",
  "context": { "companyName": "Byggkompaniet Syd", "signal": "Expansion Hyllie" },
  "userId": "demo"
}
```