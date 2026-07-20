# Email Studio — start här

Det här paketet samlar **allt nytt och uppdaterat** som behövs för att Snipra och Email Studio ska bli funktionellt. Koden lever fortfarande i projektroten (`snipe-leads/`); den här mappen är din **handbok + säkerhetskopia av nyckelfiler**.

## Var hittar jag mappen?

```
C:\Users\sebbe\snipe-leads\email-studio\
```

Öppna huvudfilen:

```powershell
cd C:\Users\sebbe\snipe-leads
notepad email-studio\START-HAR.md
```

Eller i Utforskaren: `snipe-leads` → mappen **`email-studio`**.

## Snabbstart (3 steg)

### 1. Miljövariabler
Kopiera mallen och fyll i API-nycklar:

```powershell
cd C:\Users\sebbe\snipe-leads
copy email-studio\env\.env.local.example .env.local
```

Redigera `.env.local`:
- Supabase-nycklar finns redan i mallen (projekt `spsmblyvasagpekjmgmf`)
- **Lägg till giltig `DEEPSEEK_API_KEY`** (beslutat som primär LLM)
- Alternativt: giltig `OPENAI_API_KEY` om du vill köra OpenAI

Se `MILJO.md` för alla variabler.

### 2. Starta dev-server

```powershell
cd C:\Users\sebbe\snipe-leads
& "C:\Program Files\nodejs\npm.cmd" run dev
```

Vänta på `Local: http://localhost:3000`.

### 3. Testa Email Studio

1. Gå till http://localhost:3000/login — logga in
2. Gå till http://localhost:3000/emails
3. Skriv mejltext, klicka **Kortare**, **Skriv om**, **Förbättra** m.fl.
4. Texten ska uppdateras via `POST /api/email-studio`

## Vad finns i paketet?

| Fil / mapp | Innehåll |
|------------|----------|
| **START-HAR.md** | Denna fil — börja här |
| **CHECKLIST.md** | Steg-för-steg tills allt är live |
| **FILKARTA.md** | Var varje fil ligger i det riktiga projektet |
| **MILJO.md** | Env-variabler, Supabase, LLM |
| **docs/** | Plan, sessionlogg, produktkontext |
| **env/** | `.env.local.example` (inga hemligheter) |
| **kopior/** | Spegel av alla nyckelkällfiler |

## Beslut som gäller (låsta)

| # | Beslut |
|---|--------|
| 1 | Marketing skills: `references/marketingskills-main/` |
| 2 | **DeepSeek** som primär LLM |
| 3 | OK att skicka företags-/signaldata till DeepSeek |
| 4 | **Ingen** smak-feedback-UI (inga Bra/Inte rätt-knappar) |

## Arkitektur i korthet

```
/emails (UI)
  → EmailStudioEditor.tsx
  → POST /api/email-studio (route.ts)
      → marketing-skills.ts (läser 44 skills från disk)
      → llm.ts (DeepSeek / OpenAI)
  → lib/actions/emails.ts (server action, legacy/simulation)
  → lib/data/emails.ts (Supabase + mock-fallback)
```

Edge Function `refine-email` finns för hosted Supabase men **lokal dev använder API-routen**.

## Vad återstår?

Se **CHECKLIST.md** — viktigast:
- [ ] `DEEPSEEK_API_KEY` i `.env.local`
- [ ] Stäng av **Confirm email** i Supabase Dashboard
- [ ] Testa alla refine-knappar live
- [ ] (Valfritt) Seed `generated_emails` för riktig Supabase-data

## Relaterade filer utanför paketet

| Resurs | Sökväg |
|--------|--------|
| Marketing skills (44 st) | `snipe-leads\references\marketingskills-main\skills\` |
| Supabase schema | `snipe-leads\supabase\schema.sql` |
| Projektstatus | `snipe-leads\STATUS.md` |
| Gammal sammanfattning | `snipe-leads\EMAIL_STUDIO.md` (ersatt av detta paket) |

## Hjälp nästa session

Säg till agenten: *"Läs `snipe-leads/email-studio/START-HAR.md` och fortsätt Email Studio."*