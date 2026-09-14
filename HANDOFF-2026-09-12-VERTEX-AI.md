# Handoff — Vertex AI ersätter AI Studio (2026-09-12)

## Vad som hänt

Google tog bort möjligheten att använda Cloud-krediter via AI Studio i
september 2026. Det innebär att en vanlig `GEMINI_API_KEY` (den som skapas på
https://aistudio.google.com/apikey) inte längre kan debiteras mot ett
faktureringskonto i Google Cloud — den kör bara gratisnivåns 20 anrop per dygn,
oavsett hur kontot ser ut.

**Att fylla på krediter i AI Studio eller skapa en ny API-nyckel där löser alltså
inte problemet.** Gratisnivåns tak gäller oavsett.

Vi har bytt till **Vertex AI**, som är Googles molntjänst för AI-modeller. Det
innebär en annan typ av nyckel (en service account JSON-fil i stället för en
enkel textsträng) och en annan autentiseringsmetod (OAuth2-tokens som förnyas
automatiskt i stället för en fast API-nyckel i URL:en).

**Bytet är redan gjort i koden och deployat.** Båda Railway-miljöerna
(development och main) kör med Vertex AI sedan 2026-09-12 och är verifierade
(`/health/ready` svarar `mode: live`).


## Vad Sebbe behöver veta

### Den gamla nyckeln (GEMINI_API_KEY) räcker inte längre

`GEMINI_API_KEY` fungerar fortfarande tekniskt — den ansluter mot AI Studio —
men den har 20 anrop per dygn på gratisnivån. Det räcker inte ens för en enda
kundsession. **Att lägga till pengar på Google-kontot eller skapa fler
AI Studio-nycklar hjälper inte**, för Google har stängt av möjligheten att
använda Cloud-krediter via den vägen.

### Den nya nyckeln heter GOOGLE_SERVICE_ACCOUNT_JSON

Den är en JSON-fil (inte en textsträng) som laddas ner från Google Cloud
Console. Den innehåller ett project_id, en private_key, en client_email och
fler fält. Koden läser den vid uppstart, skapar OAuth2-tokens automatiskt, och
använder dem mot Vertex AI:s API.

**Anton har redan skapat en service account** (`snajp-vertex` i projektet
`snajp-506221`) och lagt nyckeln både lokalt och på Railway. Sebbe behöver
alltså inte skapa någon ny nyckel — den finns redan och båda miljöerna kör
med den.


## Hur man lägger in nyckeln lokalt (om Sebbe kör backenden på sin maskin)

1. **Hämta JSON-filen.** Anton har den — filen heter något i stil med
   `snajp-506221-xxxxxxxx.json` och laddades ner från Google Cloud Console
   (IAM → Service Accounts → Keys → Add Key → JSON).

2. **Kör skriptet:**
   ```
   cd snipe-leads
   python scripts/keys.py --key GOOGLE_SERVICE_ACCOUNT_JSON
   ```
   Skriptet frågar efter **sökvägen till JSON-filen** (inte innehållet).
   Skriv in hela sökvägen, t.ex.:
   ```
   C:\Users\Sebbe\Downloads\snajp-506221-729f902431e1.json
   ```
   Skriptet läser filen, validerar att det är giltig JSON, kompakterar den
   till en rad, och sparar i `snajp-support/.env`.

3. **Verifiera:**
   ```
   python scripts/keys.py --check
   ```
   `GOOGLE_SERVICE_ACCOUNT_JSON` ska visa `OK (len=2308, ...om"})`.

4. **.env måste ha rätt provider och modell:**
   ```
   LLM_PROVIDER=gemini
   MODEL=gemini-2.5-flash
   ```
   Om det står `deepseek` där, ändra det. Med `LLM_PROVIDER=deepseek` och en
   riktig databas (inte localhost) vägrar backenden starta — det är en
   dataskyddsspärr, inte en bugg.


## Hur man verifierar att deployen fungerar

Båda Railway-miljöerna svarar redan `mode: live`, men om Sebbe vill kontrollera:

```
curl https://api-development-5cc3.up.railway.app/health/ready
curl https://api-production-d7695.up.railway.app/health/ready
```

Svar ska vara `{"mode": "live", ...}`. Om det står `"mode": "simulation"` kör
tjänsten utan riktig LLM-nyckel och allt faller tillbaka på regelbaserade svar.


## Vad som INTE ingår i den här omläggningen

- **Email Studio** (`app/api/email-studio/route.ts`, Next.js-sidan) använder
  fortfarande en vanlig `GEMINI_API_KEY` mot AI Studio. Den behöver en egen
  lösning (antingen en separat API-nyckel som funkar med AI Studio:s gratisnivå,
  eller en Node.js-implementering av Vertex AI-token-flödet). Det är separat
  arbete.

- **Embeddings** (kunskapsbasens vektorsökning) fungerar inte via Vertex AI:s
  OpenAI-kompatibla endpoint just nu — Googles server svarar med HTTP 500.
  Systemet faller tillbaka på svensk full-text-sökning, som fungerar men hittar
  färre saker. Det är en Google-bugg, inte något vi kan fixa i vår kod.


## Sammanfattning för den som skummar

| Fråga | Svar |
|---|---|
| Behöver jag skapa en ny nyckel? | Nej, Anton har redan gjort det |
| Är koden ändrad? | Ja, committat och pushat till `development` |
| Är Railway uppdaterat? | Ja, båda miljöerna kör med nya nyckeln |
| Hjälper det att fylla på AI Studio-krediter? | Nej, Google har stängt den vägen |
| Vilken modell kör vi? | `gemini-2.5-flash` via Vertex AI |
| Vad kostar det? | Vertex AI debiteras mot projektets faktureringskonto i Google Cloud |
