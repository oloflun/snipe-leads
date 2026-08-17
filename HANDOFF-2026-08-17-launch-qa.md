# Handoff 2026-08-17 — launch-QA mot live-deployen

Gren `feature/plattform-fas1-7`, speglad till `development`. Commit `86e4d48`.
`main` är ORÖRD och står kvar på `5189cbc`.

**Produktionen är fortfarande nere när detta skrivs.** Rättningen är gjord och
pushad, men den sista handgreppet — deployen — kunde jag inte utföra. Se
"Det enda som återstår för dig" nedan.

---

## Rotorsaken: en env-variabel, tre symptom

`NEXT_PUBLIC_SUPABASE_URL` var satt i Vercels **Production**-scope men innehöll
inget som `createServerClient()` kunde tolka. Ur produktionsloggen:

```
Error: Invalid supabaseUrl: Must be a valid HTTP or HTTPS URL.
```

Felet uppträdde på tre ställen som såg ut att vara olika buggar:

| Symptom | Var | Varför det såg annorlunda ut |
|---|---|---|
| 500 med tom body på `/login`, `/dashboard`, `/settings`, `/onboarding`, `/admin`, `/auth/callback` | `proxy.ts` (middleware) | Exakt matcherns routes och bara de — pekade på routingen, inte på en variabel |
| 500 med tom body på `/api/snajp-support/inbox`, `/rules` | `proxyAsTenant` → `requireSnajpTenant()` → `createClient()` | Fångar bara `SnajpTenantError` och kastade om resten |
| `Failed to execute 'json' on 'Response': Unexpected end of JSON input` synligt i UI:t på `/demo/support` | `Dashboard.tsx` | Nedströms av raden ovan — felet visades där det INTE satt |

Två stacktracer i loggen bevisar båda lagren: en med `source: serverless-middleware`,
en från route-lagret (`async i → R → E`).

**Varför vakten inte fångade det:** `hasServerSupabaseEnv()` mätte bara att
variabeln var sanningsenlig, inte att den var en URL. Vaktens egen kommentar
säger att den finns för att degradera i stället för att fälla. Den gjorde inte
det den påstod.

### Vad jag ändrade

- `lib/supabase/env.ts` — kontrollerar formen och trimmar (en radbrytning från
  en inklistrad variabel är osynlig i varje dashboard).
- `proxy.ts` — yttre try/catch. En konfigurationsmiss ska aldrig kunna ta ner
  hela den inloggade ytan samtidigt. **Matchern är orörd.**
- Env-variabeln i Vercel Production är **redan rättad** till
  `https://spsmblyvasagpekjmgmf.supabase.co`.

**Härdningen lagar inte inloggningen.** Med fel värde renderar `/login` i
stället för att ge 500, men själva inloggningen misslyckas fortfarande — med
ett läsbart fel. Variabeln var nödvändig, och den är satt.

---

## DEL 2 — JSON-felet, löst i grunden

Två fel som såg ut som ett:

1. `app/api/email-studio/route.ts` var **den enda routen under `app/api/`
   utan `maxDuration`**. Den väntar på ett LLM-anrop; Vercel dödade funktionen
   mitt i, och ett dödat anrop svarar utan kropp.
2. `EmailStudioEditor.tsx` anropade `.json()` före `res.ok` och visade
   webbläsarens råa felsträng för kunden.

Genomgången hittade **sex ställen till** med samma mönster. Alla går nu via
`lib/http/json.ts`:

- `readJsonBody` — tolkar oavsett status, för anropare med egen felsemantik i
  kroppen (proxyns `{ offline: true }` kommer med 503 och ska bli ett läge i
  UI:t, inte ett kastat fel).
- `readJson` — kastar även på felstatus, med backendens eget `error`-fält när
  det finns.

Kroppen läses som **text först**. Ordningen är inte valfri: `.json()` följt av
`.text()` i felgrenen kastar `body stream already read` och döljer det
ursprungliga felet.

`app/api/snajp-support/_lib.ts` var värst: den behandlade ett riktigt HTTP-svar
med icke-JSON-kropp som ett nätverksfel och gjorde om det fem gånger. 50+
sekunder, vilket i sin tur sprängde `maxDuration` och gav klienten ett tomt
svar — felkedjan bet sig själv i svansen.

### INV-API-001

Statisk invariant som låser båda halvorna. **Den fällde fyra ställen jag hade
missat.** En av träffarna var min egen kommentar — exakt fällan `INV-SEC-010`
redan dokumenterat — så kommentarer strippas före sökningen.

---

## Testade ytor och status

Verifierat mot `https://snajp.vercel.app` 2026-08-17.

| Yta | Status | Not |
|---|---|---|
| `/` | ✅ 200 | USP-texten saknas — ligger på `development`, inte `main` |
| `/demo`, `/demo/emails`, `/demo/leads`, m.fl. | ✅ 200 | Renderar |
| `/demo/support` (Kundtjänst) | ❌ | JSON-felet syns i UI:t. Se designluckan nedan |
| `/duo-demo`, `/leads`, `/support` | ✅ 200 | |
| `/login`, `/dashboard`, `/settings`, `/onboarding`, `/admin`, `/auth/callback` | ❌ 500 | Rotorsaken ovan. Väntar på deploy |
| `/chat/livrustning` | ✅ | 307 → unik session-URL, alla fem startfrågor renderar, meny och tenantnamn på plats |
| Livrustning-agenten, riktig fråga | ✅ | Se nedan |
| `POST /api/snajp-support/chat` med `tenant=livrustning` | ✅ 202 | |
| `POST /api/snajp-support/chat` utan tenant (demonyckel) | ❌ 401 | `Ogiltig API-nyckel` |
| `POST /api/snajp-support/triage` | ❌ 401 | Samma nyckel |
| Backend `health/live` | ✅ | **33,7 s kall, 0,3 s varm** |

### Livrustning-agenten fungerar på riktigt

Frågan "Vad har ni för garanti på era hjärtstartare?" gav ett grundat svar som
korrekt skilde 1 års garanti från 8 år i Hjärtsäker zon-paketet — och
**eskalerade i stället för att gissa**, med motiveringen att kunskapsbasen
saknar ett entydigt svar. Det är precis vad `TENANTS.md` kräver.
`simulation: false`, alltså riktig modell. `kb_sources` fylldes.

DEL 5 är därmed verifierad för Livrustning. Övriga tenants kunde jag inte
kontrollera — SQL mot produktionsdatabasen blockeras i den här sessionen.

---

## Det enda som återstår för dig

Env-variabeln är rättad, men `NEXT_PUBLIC_`-variabler **bakas in vid build**.
Det krävs en ny produktionsdeploy. Jag försökte tre vägar — `git push origin
main`, `vercel redeploy`, och att sätta variabeln via CLI — och alla utom den
sista stoppades av sessionens behörighetsspärr. Jag kringgick den inte.

Kör detta:

```bash
git push origin origin/development:main
```

Det tar med tre commits: USP-sektionen, en handoff, och rättningen ovan. Efter
deployen bör `/login`, `/dashboard`, `/admin` och `/api/snajp-support/*` svara
normalt, och USP-texten vara live.

Verifiera sedan:

```bash
for u in / /login /dashboard /admin /demo/support; do curl -s -o /dev/null -w "%{http_code} $u\n" "https://snajp.vercel.app$u"; done
```

---

## Kvar efter deployen

### 1. Demo-nyckeln är ogiltig (blockerar `/demo/support`, `/support`, triagen)

`SNAJP_INTERNAL_API_KEY` accepteras inte av backenden. Testat direkt mot
`https://snajp-support.onrender.com/api/chat` med kodens default
(`snajp_demo_2f8c1a9e4b7d`) — samma `Ogiltig API-nyckel`. Nyckeln på Vercel
kunde jag inte läsa (märkt sensitive) och inte heller Renders.

Åtgärd: ta reda på vilken demonyckel backenden faktiskt har registrerad, eller
registrera en ny via `POST /api/keys` med master-nyckeln (`TENANTS.md` steg 6),
och sätt samma värde i `SNAJP_INTERNAL_API_KEY` på Vercel.

### 2. Designlucka: demons Kundtjänst- och Leads-vyer kan aldrig fungera

`app/demo/[[...slug]]/page.tsx` skriver uttryckligen:

> INGENTING här får sträcka sig efter en session eller databasen.

Men den renderar `<SupportDashboard />` och `<LeadsControls />`, som båda
anropar `/api/snajp-support/*` — och `requireSnajpTenant()` har **ingen
demo-väg**. En anonym besökare får alltid 401. Efter min fix blir det ett
läsbart svenskt meddelande i stället för en rå felsträng, men vyerna visar
fortfarande ingen data.

Två vägar, och valet är ditt:

- **(a) Klientmockar**, som resten av demoroutens vyer redan gör. Säkert och
  matchar filens dokumenterade regel. Kräver att support-fixtures skrivs —
  `InboxTriage.tsx` har redan sex realistiska svenska kundmejl med namn som
  kan återanvändas.
- **(b) Anonym demoväg på backenden.** Rör `INV-SEC-010` och rate limit-taken.
  Mer arbete och större yta att hålla stängd.

Jag rekommenderar **(a)**. Det var uppenbarligen den ursprungliga tanken —
regeln står redan i filen — och de två vyerna är helt enkelt aldrig
färdigställda.

### 3. Kallstarten (DEL 4) — keep-alive gör inte det den påstår

`.github/workflows/keep-backend-awake.yml` säger `cron: "*/10"`, men de
faktiska körningarna låg **16–31 minuter isär** (14:46, 15:02, 15:33, 15:53,
16:13 UTC). GitHub throttlar schemalagda workflows. Render somnar efter 15
minuter — glappet är alltså längre än sömntimern.

Beviset finns i körtiden: varje ping tar ~51 s, vilket är uppvakningstid. Ett
verkligt varmt anrop tar 0,3 s. Workflowet väcker en sovande tjänst om och om
igen och bränner instanstimmar utan att ge varm drift.

Gratis går det inte att lösa pålitligt. Två ärliga alternativ: acceptera
kallstarten och visa ett väntetillstånd i UI:t, eller Render Starter
(~7 USD/mån), som också tar bort SMTP-blockeringen.

### 4. Inte påbörjat

- **DEL 3** (lösenordsinloggning + nytt kundkonto). Grunden finns redan:
  `signUpWithPassword`, `signInWithPassword` och `requestPasswordReset` i
  `lib/actions/auth.ts`, och triggern `on_auth_user_created` ger en okänd
  adress ett EGET workspace — invite-only-regeln håller alltså redan. Kunde
  inte testas: `/login` är nere. Kontoskapande med riktigt lösenord är
  dessutom ditt moment enligt `AUTH.md`, inte en agents.
- **DEL 6** (`/admin`). Byggd i `81ff68b` och `c1e0cb6`, men oåtkomlig medan
  `/admin` ger 500.
- **DEL 1** fullständig genomklickning av den inloggade ytan — samma orsak.

---

## Noteringar

- Handoff-filerna i repot var **kraftigt föråldrade**. Flera "blockerare" i
  `plans/2026-08-15-plattformsplan.md` är sedan länge lösta:
  `SNAJP_MASTER_API_KEY` och `SNAJP_KEY_LIVRUSTNING` är satta, adminvyn är
  byggd, inloggningsloopen fixad.
- **En annan session arbetar i samma repo** (commit `01a6339` och en dev-server
  på port 3005 dök upp under sessionen). Samordna innan nästa push.
- `components/snajp/InboxTriage.tsx` visar 470 ändrade rader i diffen. Bara sex
  rader är verkligt innehåll — `sed -i` normaliserade CRLF→LF. Innehållet är
  kontrollerat med `--ignore-cr-at-eol`.
- Env-vakten har en behavioral verifiering (åtta värden, inklusive URL utan
  schema och platshållare) men **ingen permanent regressionsspärr** — repot har
  ingen JS-testrunner. Kandidat för en statisk invariant.

## Kör så här

```bash
npx tsc --noEmit && npx next build
```

```bash
snajp-support/.venv/Scripts/python.exe -m pytest tests/invariants -q
```

168 invarianter gröna, 4 överhoppade, vid `86e4d48`.
