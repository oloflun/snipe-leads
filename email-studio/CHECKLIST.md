# Checklista — Snipra + Email Studio funktionellt

## Fas A: Miljö (collaborator-maskin)

- [ ] Node finns: `C:\Program Files\nodejs\node.exe`
- [ ] Python 3.12 installerat (för agent-stack, ej krävs för Email Studio)
- [ ] `.env.local` skapad från `email-studio/env/.env.local.example`
- [ ] `DEEPSEEK_API_KEY` satt (eller giltig `OPENAI_API_KEY`)
- [ ] Dev-server startad: `npm.cmd run dev` från `snipe-leads/`

## Fas B: Supabase Auth (krävs för /emails)

- [ ] Projekt: https://spsmblyvasagpekjmgmf.supabase.co
- [ ] Schema applicerat (`npm run apply:schema` — redan kört)
- [ ] **Dashboard → Authentication → Providers → Email → Confirm email: AV**
- [ ] Logga in via `/login` med befintligt konto
- [ ] Onboarding sparar `business_contexts` → redirect `/dashboard`
- [ ] Auth kvar efter siduppdatering

## Fas C: Email Studio knappar

- [ ] `/emails` laddar utan fel
- [ ] Skriv text i mejlfältet
- [ ] **Kortare** — text förkortas, resultatpanel visas
- [ ] **Skriv om** — ny version genereras
- [ ] **Förbättra** — tydligare CTA/struktur
- [ ] **Personalisera** — använder company/signal-kontext
- [ ] **Översätt** — sv/en enligt kontext
- [ ] **A/B-varianter** — returnerar flera förslag
- [ ] **Uppföljning** — follow-up-stil
- [ ] **Analysera** — feedback utan att ändra text

### Om knappar inte svarar

1. Kontrollera Network-fliken: `POST /api/email-studio` → status 200?
2. Saknas API-nyckel → simulation körs (begränsad men fungerar)
3. Starta om dev-server efter `.env`-ändring

## Fas D: Marketing skills

- [ ] Skills finns: `references/marketingskills-main/skills/` (44 st)
- [ ] Kör vid behov: `npm run bundle:skills` → uppdaterar `lib/agent/skills-corpus.json`
- [ ] Agent läser skills live via `lib/agent/marketing-skills.ts`

## Fas E: Data (valfritt men rekommenderat)

- [ ] Seed `generated_emails` i Supabase så `/emails` visar riktig data (inte bara mock)
- [ ] Verifiera `lib/data/emails.ts` fallback-logik

## Fas F: Deploy (senare)

- [ ] Deploy Edge Function `refine-email` om hosted LLM ska köras i Supabase
- [ ] Sätt `DEEPSEEK_API_KEY` som Supabase secret
- [ ] Vercel env-variabler speglar `.env.local`

## Verifiering

```powershell
cd C:\Users\sebbe\snipe-leads
& "C:\Program Files\nodejs\npm.cmd" run type-check
& "C:\Program Files\nodejs\npm.cmd" run build
```

Båda ska passera utan fel.