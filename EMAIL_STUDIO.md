# Email Studio — flyttat till paketmappen

**Uppdaterat handoff-paket finns här:**
`C:\Users\sebbe\snipe-leads\email-studio\START-HAR.md`

Öppna med: `notepad email-studio\START-HAR.md`

---

# Email Studio - Sammanfattning av uppdateringar (2026-07-09) [ARKIVERAD]

## Projekt
- Next.js app med Supabase auth
- Email Studio på /emails
- Buttons: Kortare, Skriv om, Förbättra, Personalisera, Översätt, A/B-varianter, Uppföljning, Analysera
- Använder /api/email-studio för att ändra text (simulation eller LLM)

## Uppdaterade filer (viktiga ändringar)

### 1. app/api/email-studio/route.ts
- Full EMAIL_STUDIO_SYSTEM_PROMPT (baserat på Snipra prompt + marketingskills)
- Förbättrad simulation i simulateAction() som ger meningsfulla textändringar
- Bättre parser (parseRichRefine) som hanterar både JSON, markdown-sektioner och fallback
- Stöd för alla actions: shorter, rewrite, improve, personalize, translate, ab_variants, followup, analyze, longer
- Använder context (company, signal) för personalisering
- Real LLM path om OPENAI_API_KEY är giltig (annars simulation)

Exempel på output för "shorter":
Hej,

Såg att Byggkompaniet Syd växlar upp i Hyllie och söker arbetsledare. Rätt lokala fastighetsägare är värda mer än generiska leads.

Vi har hjälpt liknande team korta ledtiderna rejält med signalstyrda, personliga mejl.

Vill du att jag skickar två exempel?

### 2. components/email/EmailStudioEditor.tsx
- runAction() gör POST till /api/email-studio
- Auto-applies new_version för direct actions (shorter, rewrite, improve, personalize, translate)
- Visar resultat-panel med förklaring och subject suggestions
- Använder refineContext från data

### 3. lib/actions/emails.ts (refineEmail simulation)
- Uppdaterad simulation som matchar route.ts (för legacy paths)
- Ger bra exempel-text för alla actions

### 4. .env.local (och .env + .env.local.example)
- NEXT_PUBLIC_SUPABASE_URL=https://spsmblyvasagpekjmgmf.supabase.co
- NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_-J_VNDVbabHeLfrTw4rx7g_yqrX86gZ
- SUPABASE_SERVICE_ROLE_KEY=sb_secret_... (placeholder)
- OPENAI_API_KEY=sk-... (placeholder → använder simulation)
- LLM_PROVIDER=openai

**Viktigt:** Efter ändring av .env → starta om dev servern.

## Hur du testar knapparna
1. Starta servern (se nedan)
2. Gå till http://localhost:3000/emails (logga in om det krävs)
3. Skriv lite text i mejlfältet
4. Klicka "Kortare" eller "Skriv om"
5. Texten uppdateras automatiskt + resultat-panel visas med förklaring

API-anropet:
POST /api/email-studio
{
  "action": "shorter" | "rewrite" | ...,
  "draft": "din mejltext...",
  "subject": "...",
  "context": { "companyName": "...", "signal": "..." },
  "userId": "demo"
}

## Konto
- E-post: Bergman.sebastian2002@gmail.com
- Lösenord: Kapsyl21!
- Kontot finns redan i Supabase.
- Logga in via /login (redirectas från /emails om du inte är inloggad)
- Signup via UI ger "User already registered" men fetch fungerar nu (ingen "fetch failed")

## Hur du startar localhost (PowerShell)
Öppna PowerShell och kör:

cd C:\Users\sebbe\snipe-leads

npm run dev

(eller full path om npm inte finns i PATH:)
& "C:\Program Files\nodejs\npm.cmd" run dev

Vänta tills du ser:
- Local: http://localhost:3000
- Ready in X ms

## Öppna denna fil imorgon
cd C:\Users\sebbe\snipe-leads
code EMAIL_STUDIO.md     # om du har VS Code
# eller
notepad EMAIL_STUDIO.md

## Övrigt
- Simulation används när OPENAI_API_KEY är placeholder (sk-...).
- För riktig LLM: sätt giltig OPENAI_API_KEY i .env.local och starta om.
- Alla ändringar använder marketingskills-principer (cold-email, copywriting m.fl.).
- Supabase secret key är satt – auth/login fungerar nu.

Lycka till imorgon!
