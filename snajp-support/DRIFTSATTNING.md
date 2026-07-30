# Driftsättning — från demo till riktiga kundmail

Checklista i den ordning stegen måste tas. Ordningen spelar roll: databasen
måste vara migrerad innan persistens slås på, och backend-URL:en måste finnas
innan frontend kan peka på den.

Aktuellt läge i den här installationen anges som **[KLART]** eller **[KVAR]**.

---

## A. Render — backendens miljövariabler

Tjänst: `snajp-support` · https://snajp-support.onrender.com ·
[dashboard](https://dashboard.render.com/web/srv-d9k99ktg1s2s73fl0v6g)
Sätts under **Environment** → *Add Environment Variable* → **Save, rebuild, and deploy**.

### Måste sättas för riktiga AI-svar

| Variabel | Värde | Varför |
|---|---|---|
| `DEEPSEEK_API_KEY` | din nyckel från platform.deepseek.com | **[KVAR]** Utan denna kör tjänsten regelmotorn, inte AI. Detta är det enda som skiljer "riktiga svar" från "simulerade". |
| `DATABASE_URL` | `postgresql://postgres.spsmblyvasagpekjmgmf:<DB-LÖSENORD>@aws-0-eu-west-1.pooler.supabase.com:6543/postgres` | **[KVAR]** Utan denna ligger allt i minnet och försvinner när tjänsten somnar (15 min). Ärenden, utkast och kunskapsbas måste överleva. |

> `DATABASE_URL` får INTE sättas innan migration 005 är applicerad — databasen
> skulle då avvisa kategorierna `garanti` och `utbildning`. **[KLART]** —
> migrationen är applicerad, så det är fritt fram.

### Bör sättas

| Variabel | Värde | Varför |
|---|---|---|
| `EMBEDDING_API_KEY` | en OpenAI-nyckel | **[KVAR]** DeepSeek saknar embeddings. Utan denna används nyckelordssökning i kunskapsbasen i stället för semantisk sökning — fungerar, men hittar färre relevanta artiklar. |

### Redan satta **[KLART]**

`LLM_PROVIDER=deepseek` · `MODEL=deepseek-chat` · `SNAJP_DEMO_API_KEY` ·
`SNAJP_PILOT_API_KEY` · `SNAJP_MASTER_API_KEY` · `PILOT_TENANT_NAME` ·
`ALLOW_AUTO_SEND=false` · `AUTO_SEND_MIN_CONFIDENCE=0.75` ·
`INBOX_POLL_SECONDS=0` · `IMAP_HOST/USER/PASSWORD/FOLDER` · `IMAP_TENANT=pilot` ·
`SMTP_FROM_NAME`

### Utgående mail — viktigt på gratisplanen

**Render blockerar utgående SMTP (portarna 25/465/587) på gratis web services**
sedan september 2025. Godkända svar kan därför inte skickas via Gmails SMTP
därifrån; felet blir *"Network is unreachable"*. Ärendet markeras aldrig som
skickat när det händer — utkastet ligger kvar och kan skickas om.

Två vägar framåt:

| Val | Vad som krävs |
|---|---|
| **Resend** (gratis, rekommenderas) | Skapa konto på [resend.com](https://resend.com), hämta API-nyckel. Sätt `EMAIL_PROVIDER=resend`, `RESEND_API_KEY=<nyckel>`, `EMAIL_FROM=onboarding@resend.dev` (eller egen verifierad domän). Går över HTTPS, alltså opåverkat av blockeringen. 3000 mail/mån gratis. |
| **Betald Render-plan** | Uppgradera till Starter (~7 USD/mån) → SMTP-portarna öppnas och Gmail-uppgifterna räcker. |

Kör du lokalt eller på en plattform utan blockering fungerar SMTP direkt — det
är default, och uppgifterna ärvs från IMAP-kontot (`imap.gmail.com` →
`smtp.gmail.com`).

### Kallstart

Gratisplanen somnar efter 15 minuter utan trafik och tar ~1 minut att vakna.
Proxyn gör om anropet upp till tre gånger, så vanliga klick klarar sig. Vill du
bort från det helt krävs betald plan (Starter, ~7 USD/mån) eller en
keep-alive-ping mot `/health/live` var 10:e minut.

---

## B. Vercel — frontendens miljövariabler

Projekt: **snipra** (inte `snajp` — det är en separat landningssida).
Settings → Environment Variables. **Deploya om efteråt**, annars får den nya
deployen inte variablerna.

| Variabel | Värde | Status |
|---|---|---|
| `SNAJP_SUPPORT_URL` | `https://snajp-support.onrender.com` | **[KLART]** |
| `SNAJP_INTERNAL_API_KEY` | samma som Renders `SNAJP_DEMO_API_KEY` | **[KLART]** |
| `SNAJP_PILOT_API_KEY` | samma som Renders `SNAJP_PILOT_API_KEY` | **[KLART]** |
| `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` | från Supabase | **[KLART]** — krävs för inloggningen till `/kundtjanst` |

### CORS

Behövs **inte**. Webbläsaren anropar aldrig backenden direkt — Next-proxyn gör
det server-side, vilket också är skälet till att API-nycklarna aldrig når
klienten. `ALLOWED_ORIGINS` finns för den dag en kund vill anropa API:t från
sin egen webbapp; lämna tom annars.

---

## C. Koppla Gmail-inkorgen

1. Använd en **egen supportadress**, inte någons personliga inkorg. Agenten
   markerar hämtade mail som lästa.
2. Slå på tvåstegsverifiering på kontot.
3. Skapa app-lösenord: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   → namnge det → kopiera de 16 tecknen (mellanslag tas bort).
4. Sätt på Render: `IMAP_HOST=imap.gmail.com`, `IMAP_USER=<adressen>`,
   `IMAP_PASSWORD=<app-lösenordet>`, `IMAP_TENANT=pilot`. **[KLART]**
5. Hämta mail: logga in på `/kundtjanst` och tryck **Hämta nya mail**.
   Vill du ha automatik, sätt `INBOX_POLL_SECONDS=60`.

**Outlook/Microsoft 365** kräver numera OAuth2 för IMAP — app-lösenord räcker
inte. Det är en egen integration som inte är byggd. Använd Gmail för piloten.

---

## D. Fyll kunskapsbasen

Utan innehåll eskalerar agenten varje ärende — korrekt, men oanvändbart.

1. Logga in på `/kundtjanst` → fliken **Kunskapsbas**.
2. **Hämta branschmall** → 17 artiklar med rätt rubriker och kategorier,
   märkta `[PLATSHÅLLARE]`.
3. Ersätt varje text med bolagets faktiska villkor. Skriv som ni skulle svara
   en kund — det är precis så texten används.
4. Sikta på **noll platshållare** innan riktiga kunder besvaras. Antalet visas
   överst på sidan.

Via API i stället: `POST /api/kb/template` respektive `POST /api/kb` med
`X-API-Key: <SNAJP_PILOT_API_KEY>`.

---

## E. Verifiera att ett riktigt mail går hela vägen

När A–D är klara:

1. **Skicka ett testmail** från en adress du kontrollerar till supportadressen.
   Skriv något kunskapsbasen kan svara på, t.ex. *"Hur lång är garantitiden på
   era hjärtstartare?"*. Låt det ligga oläst.
2. **Hämta:** logga in på `/kundtjanst` → **Hämta nya mail**. Mailet ska dyka
   upp med ett fack och en konfidenssiffra.
3. **Granska:** öppna ärendet. Kontrollera att facket stämmer, att förslaget
   bygger på rätt artikel (källorna visas), och läs beslutsloggen.
4. **Skicka:** tryck **Godkänn & skicka**. Svaret ska landa i din inkorg —
   **i samma mailtråd** som ditt ursprungliga mail.
5. **Kontrollera statusen:** ärendet ska stå som **Skickat**. Står det kvar som
   **Utkast** gick sändningen inte igenom — felet visas då i rutan, och
   ärendet markeras aldrig som besvarat om mailet inte gick fram.

Testa också ett känsligt fall, t.ex. *"Jag vill ha pengarna tillbaka"* — det
ska bli **Eskalerat** utan förslag att skicka.

---

## Felsökning

| Symptom | Orsak |
|---|---|
| "Backenden svarar inte" | Render sover (vänta ~1 min och ladda om) eller `SNAJP_SUPPORT_URL` saknas i den deployen |
| "SNAJP_SUPPORT_URL är inte satt" | Variabeln finns inte, eller så deployades inte om efter att den lades till |
| Alla ärenden eskaleras | Tom kunskapsbas, eller frågor som saknar underlag |
| Svaren låter mallade | `DEEPSEEK_API_KEY` saknas → regelmotorn, inte AI |
| Allt försvinner ibland | `DATABASE_URL` saknas → in-memory + spin-down |
| "Ingen kopplad inkorg" i demon | Avsiktligt — riktiga mail går bara till pilot-arbetsytan |

`GET /health/ready` listar allt som saknas i klartext.
