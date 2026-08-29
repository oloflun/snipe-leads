# Skarpa körningar, testytor och produktion på main

**Datum:** 2026-08-28 · **Gren:** `development` · **Status:** planering klar, Fas 1 ej påbörjad

## Läge vid sessionens slut (2026-08-28 kväll)

- [x] Kartläggning (fem delagenter) + egen verifiering av varje bärande fynd
- [x] Planen skriven, granskad, publicerad; 17 `bd`-ärenden med beroenden
- [x] Loopia-uppgifter satta och **verifierat live** (`loopia_dns.py` läste riktiga Loopia-poster) — `--apply` återstår, produktionssäkert
- [ ] **Blockerar Fas 1/6:** Antons nya Gemini-nyckel/projekt inte verifierat live än — kör `python scripts/kor_evals.py`, ingen 429 = bekräftat
- [ ] Väntar på Antons ord: vilken fas ska starta först
- [ ] Produktionsdeployen (Fas 7, andra halvan) — spärrad tills Anton säger till, se §8.1a

Fullständig sessionslogg: [session-logs/2026-08-28-session-log.md](../session-logs/2026-08-28-session-log.md)

**Uppdatering 2026-08-29 — parallellt arbete, inte en av de sju faserna
nedan.** Sebbe byggde mejlsändningen (SMTP → Resend/HTTPS, se Fas 4:s
"Ärliga invändning" nedan — det här ÄR den sändvägen) och adminfliken
Kunder & Data mellan 27 och 29 aug. En efterföljande session konfigurerade
Resend (`kontakt@snajp.se`) och en Redis-backad jobbkö i `development`s
Railway-miljö. Ingenting av detta rör produktionsspärren i §8.1a — allt gick
mot `development`. B1 (Gemini-koppling) är fortfarande olöst och blockerar
fortfarande Fas 6/7 som planerat. Se
`session-logs/2026-08-29-session-log.md` för detaljer.

---

Planen svarar på sju saker Anton bad om: gör alla körningar skarpa, skilj
testkörningar från kundens riktiga konto, låt kunden flytta över valda
prospekt, flytta Email-studion in i leaden, bygg en Testchatt-flik, verifiera
med minst 10 riktiga rundor mot både DeepSeek och Gemini, och förbered
produktion på `main` med `snajp.se`.

> ## ⛔ Produktionen rörs inte
>
> **Antons instruktion 2026-08-28:** push:a eller pull:a ingenting mot
> produktion. Förbered bara. Ingen push till `main` eller `railway-main`,
> ingen migration mot `--env main`, ingen provisionering av en befintlig
> miljö. Fullständig lista och vad som ändå går att förbereda: **§8.1a**.
>
> Det är dessutom mer än en preferens just nu — den dokumenterade
> produktionskedjan är trasig på ett sätt som gör en push aktivt farlig (§8.1).

Allt nedan bygger på läst kod. Radhänvisningar är verifierade i den här
sessionen, inte hämtade ur dokumentation.

---

## 0. Diagnosen: varför körningarna ser autogenererade ut

Det är inte *en* orsak, det är **fyra oberoende**, och de förklarar olika
delar av det du ser. Det spelar roll, för tre av dem går att laga billigt och
den fjärde är ett beslut du måste ta.

### 0.1 Email-studion är alltid simulerad — den skriver aldrig något och läser aldrig en riktig lead

Detta är den tydligaste träffen mot "färdiga responser utan riktig AI".

* `valjModell()` i [app/api/email-studio/route.ts:35](app/api/email-studio/route.ts:35) känner bara till **OpenAI och DeepSeek**. Gemini finns inte i funktionen. Backenden kör Gemini.
* `OPENAI_API_KEY` är tom lokalt (längd 1 i `.env.local`) och dokumenteras som osatt på webbtjänsten i *varje* miljö.
* DeepSeek-grenen är spärrad med `NODE_ENV !== "production"` ([route.ts:50](app/api/email-studio/route.ts:50)) — alltså avstängd i både produktion och Railway-dev.
* **Följd:** `valjModell()` returnerar `null` överallt, och routen faller till `simulateAction()` ([route.ts:157](app/api/email-studio/route.ts:157)) — mallgenererad svensk text byggd av `context.companyName`/`signal`/`offer`.

Dessutom: tabellen `generated_emails` **skrivs aldrig**. Repot har en SELECT
([lib/data/emails.ts:130](lib/data/emails.ts:130)) och en UPDATE
([lib/data/emails.ts:211](lib/data/emails.ts:211)) — **ingen INSERT någonstans**.
`loadEmailStudioData()` faller därför alltid till exempelmejlet
([lib/data/emails.ts:141](lib/data/emails.ts:141)). Studion är i praktiken en
frikopplad lekyta som visar samma exempel för varje kund, varje gång.

### 0.2 Exempelbolagen är påhittade *med flit* — inklusive pitchtexten

[snajp-support/app/leads/exempelbolag.py](snajp-support/app/leads/exempelbolag.py)
genererar bolag deterministiskt ur SHA-256, utan LLM, och bygger även **hela
säljpitchen** ur en fast tuple med sex signaler (`_SIGNALER`, rad 93).
Motiveringen i filens egen docstring är god: en ny kund har noll prospekt, och
ett påhittat bolagsnamn ur en språkmodell kan råka vara ett riktigt bolag.

Det är alltså inte en bugg — men det är oskiljbart från "AI:n skrev det här"
i gränssnittet, och det är rimligen en del av det du reagerat på.

### 0.3 Gemini kör fortfarande på gratisnivån — 20 anrop per DYGN

Uppmätt och dokumenterat (`snipe-zfn`): `GenerateRequestsPerMinutePerProject`
`PerModel-FreeTier` slår efter **6 anrop per minut**. Supportplaybooken har
**7 steg** ([support_playbook.py:20](snajp-support/app/agent/support_playbook.py:20)),
alltså 7 sekventiella LLM-anrop. **Ett enda supportärende spränger
minutkvoten på egen hand.** Stegen som faller returnerar fallbacktext.

**Ommätt 2026-08-28:** dygnstaket är det bindande. `quotaValue: 20` för
`gemini-3.6-flash`, kvot-id `GenerateRequestsPerDayPerProjectPerModel-FreeTier`.
Med sju anrop per ärende räcker dygnsransonen till **knappt tre supportärenden
för hela plattformen** — och nyckeln delas mellan alla tre miljöer.

Det förklarar hela symtombilden: de första ärendena varje dygn går igenom, resten
faller till fallbacktext, och `/health` fortsätter rapportera `mode: live`
eftersom en nyckel finns. Se §1.1 — pengarna finns redan, kopplingen saknas.

### 0.4 Simuleringsläget i backenden — men det är INTE aktivt just nu

Jag mätte båda miljöerna i den här sessionen:

```
api-development : {"status":"ok","mode":"live","model":"gemini-3.6-flash"}
api-production  : {"status":"ok","mode":"live","model":"gemini-3.6-flash"}
```

Båda svarar `mode: live`. Regelmotorn (`sim_agent.py`) är alltså **inte** det
du ser. Däremot rapporterar båda `degraded: true` med två varningar:

> "IMAP saknas — inga inkommande mail hämtas."
> "Ingen riktig sändväg — godkända svar loggas men skickas aldrig till kund."

Det senare är avgörande för "Godkänn och skicka": **det finns ingen
sändväg.** `LoggingSendProvider` loggar och returnerar
([send_provider.py:28](snajp-support/app/leads/send_provider.py:28)).

---

## 1. Beslut jag behöver av dig innan Fas 6 och 7

Tre saker är dina, inte mina. De blockerar inte allt arbete, men de blockerar
"skarpt i drift".

| # | Beslut | Varför det inte går att koda sig runt |
|---|---|---|
| **B1** | **Koppla nyckelns projekt till faktureringskontot** | Betalningen är redan gjord — se §1.1. Det som saknas är en länk i Googles konsol, inte ett köp. Kräver dig, för det är ett konto. |
| **B2** | **Juridiken kring Gemini free tier** | `docs/JURIDIK_ATGARDER.md` P0.1c: gratisnivån låter Google använda innehållet till produktförbättring, inklusive mänsklig granskning. Pausen från 24 aug hävdes aldrig formellt, men båda miljöerna kör live igen. **B1 löser även B2** — betald nivå ger normalt åtagandet om att innehållet inte används för produktförbättring. `snipe-a1c`. |
| **B3** | **LoopiaAPI-lösenordet** | Du skrev `LOOPIA_PASSWORD = ditt_api_lösenord` — det är platshållartexten ur dokumentationen, inte ett värde. Se §8. |

### 1.1 Krediterna behöver inte "appliceras" — projektet behöver kopplas

Mätt 2026-08-28, direkt mot API:t:

```
quotaId:     GenerateRequestsPerDayPerProjectPerModel-FreeTier
quotaMetric: generativelanguage.googleapis.com/generate_content_free_tier_requests
quotaValue:  20
dim.model:   gemini-3.6-flash
```

Faktureringskontot (`01D8D9-D35BE6-BE0D5D`) uppgraderades från free trial
**24 augusti** och bär kr 2 910,57 i tillgänglig kredit, 100 % kvar. Krediter i
Google Cloud dras automatiskt när kostnad uppstår — det finns ingenting att
"applicera".

**Men kvot-id:t säger fortfarande `-FreeTier`.** Gemini-API:t
(`generativelanguage.googleapis.com`) har en egen gratisnivå som hänger på
**projektet** som äger API-nyckeln, inte på faktureringskontot. Nyckelns projekt
är alltså inte kopplat till det betalande kontot — därför gäller 20 anrop per
dygn trots att pengarna finns.

**Åtgärd (~2 minuter, kräver dig):** i AI Studio under API-nycklar syns vilket
projekt nyckeln tillhör. Koppla det projektet till faktureringskontot
(Google Cloud-konsolen → välj projektet → Fakturering → Länka ett
faktureringskonto). Kvot-id:t ska då sluta säga `FreeTier`.

**Verifiering efteråt** — kör den och läs kvot-id:t, lita inte på konsolen:

```bash
python scripts/verifiera_gemini_niva.py
```

Skriptet finns inte än; det är ett av stegen i Fas 6. Tills dess duger ett
enda anrop och en blick på `quotaId` i felsvaret.

**Två förbehåll:**

* Kreditraden säger *"Certain usage; see the terms free trial"*. Free
  trial-krediter täcker inte allt. Kontrollera efter kopplingen att saldot
  faktiskt börjar dras när Gemini-anrop görs — annars är kostnaden verklig.
* **Nyckeln delas mellan miljöerna** (verifierat, `snipe-a1c`). Kopplingen
  lyfter därför alla tre samtidigt — men den delade kvoten är i sig ett
  problem: dev-trafik bränner produktionens tak, och en provkörning kan ta ner
  produktionen. Egen nyckel per miljö står redan i P0.1c:s åtgärdslista.

---

## 2. Fas 1 — Gör varje yta skarp

**Mål:** ingen yta svarar med mallgenererad text när en nyckel finns.

| Steg | Ändring | Kontroll som avgör |
|---|---|---|
| 1.1 | Lägg till Gemini i `valjModell()`, [route.ts:35](app/api/email-studio/route.ts:35). Samma base-URL som backenden: `https://generativelanguage.googleapis.com/v1beta/openai/`. Ordning: OpenAI → Gemini → DeepSeek (lokalt). | Anrop mot `/api/email-studio` inloggat returnerar `simulated: false`. |
| 1.2 | Sätt `GEMINI_API_KEY` på **web**-tjänsten i båda Railway-miljöer (den finns bara på `api` i dag). | `simulated_reason` saknas i svaret i dev. |
| 1.3 | Låt `simulated: true` synas i gränssnittet, inte bara i JSON. En rad: "Exempeltext — ingen modell kördes." | Manuell: stäng av nyckeln, texten syns. |
| 1.4 | Märk exempelbolagens pitch i UI:t som exempel (fältet `origin === "example"` finns redan, [Oversikt.tsx:604](components/dashboard/Oversikt.tsx:604)). | Ett exempelbolag går inte att förväxla med en AI-körning. |

**Rör inte** `is_simulation()` eller `llm_provider_fault()`. De är rätt.

**Ponytail:** 1.1 är ~12 rader. Hoppar över att slå ihop `dugerSomNyckel()`
med backendens `_looks_real` — två kopior av fyra villkor är billigare än en
delad modul över språkgränsen. Lägg till när de faktiskt glider isär.

---

## 3. Fas 2 — Testkörningar som inte smutsar ner kundens konto

**Viktigast att veta:** `agent_runs.is_test` finns redan (migration 036) men är
**kosmetisk**. Den märker bara körningsraden. Den når inte
`create_prospect`, `queue_outreach_message` eller `send_guard` — verifierat med
grep. En "testkörning" i dag skapar alltså riktiga prospekt och kan köa
riktiga utskick.

**Design:** bygg på `prospects.origin`, inte en ny kolumn. Den finns
(migration 039), är indexerad på `(tenant_id, origin)` och **send-guarden
läser den redan** ([scheduler.py:80](snajp-support/app/leads/scheduler.py:80)).

| Steg | Ändring | Kontroll |
|---|---|---|
| 2.1 | Migration: utöka check-villkoret till `('manual','example','import','test')`. Använd `DROP CONSTRAINT` + `ADD CONSTRAINT ... NOT VALID` + `VALIDATE` — migration 039 varnar själv för att en ALTER på ett check-villkor låser tabellen i drift. | `railway_migrate.py --env development --apply` går igenom. |
| 2.2 | Tråda `is_test` från `LeadsBatchRequest` hela vägen till `create_prospect(origin="test")`. | Nytt test: en batch med `is_test=true` skapar noll rader med `origin='manual'`. |
| 2.3 | Utöka send-guardens spärr noll till `origin in ('example','test')`. | Nytt test: ett testprospekt når aldrig `provider.send()`. |
| 2.4 | Filtrera `origin='test'` ur kundens prospektlistor by default, med en växel "Visa testkörningar". | Vyn räknar rätt. |
| 2.5 | **Lås buggen:** supportkörningar kan inte märkas test alls — `ChatRequest` saknar fältet och `run_support_agent` skickar aldrig `is_test` ([support_agent.py:774](snajp-support/app/agent/support_agent.py:774)). Detta motsäger komponentens egen kommentar i [Testkorningar.tsx:20](components/admin/Testkorningar.tsx:20). Lägg till fältet. | Adminytans supporttest ger `is_test=true` i `agent_runs`. |

---

## 4. Fas 3 — Flytta över valda prospekt, och demo → riktigt konto

**Rättelse mot första antagandet:** en promote-väg *finns* redan —
[scripts/konvertera_testkund.py](scripts/konvertera_testkund.py). Den flyttar
**konfiguration** (KB med embeddings, kategoriregler, `agent_configs`,
kontextdokument inkl. SOUL) från `testkund-*` till en riktig tenant, med
överskrivning, `--apply` och två riktningsspärrar.

Den utesluter **med flit** prospekt, ärenden, mejl och körningar:
> "en riktig kunds första dag ska inte börja med sex påhittade ärenden i inkorgen"

Det är rätt som default. Det du ber om är ett **opt-in-undantag** för de
prospekt kunden själv pekar ut.

| Steg | Ändring | Kontroll |
|---|---|---|
| 3.1 | Ny endpoint `POST /api/leads/prospects/{id}/befordra` — sätter `origin='manual'` inom samma tenant. Enklaste fallet: testkörning i det egna kontot. | Ett befordrat prospekt passerar send-guarden; ett obefordrat gör det inte. |
| 3.2 | Validering vid befordran: `origin='test'/'example'` kräver **riktigt orgnr** (Luhn — exempelbolagens är medvetet fel, [exempelbolag.py:146](snajp-support/app/leads/exempelbolag.py:146)), riktig domän (inte `.example`) och en mottagaradress. Utan dem: 422 med vad som saknas. | Ett exempelbolag går **inte** att befordra utan att fyllas i. |
| 3.3 | Kryssrutor + "Flytta över valda" i prospektlistan. | Manuell. |
| 3.4 | **Demo → riktigt konto:** utöka `konvertera_testkund.py` med `--prospekt <id>,<id>` som kopierar valda rader till måltenanten med `origin='manual'`, nya id:n, och `prospect_sources` med. | Torrkörning listar exakt vad som flyttas innan `--apply`. |
| 3.5 | Exponera 3.4 som ett steg i onboarding när en demo-arbetsyta får ett riktigt konto. | Manuell genomgång. |

**Fällor som måste hanteras (de tystar, de kraschar inte):**

* `prospects.foretagsnyckel` är en **GENERATED STORED**-kolumn på orgnr/mejldomän med index per tenant. Kopieras ett bolag som redan finns hos måltenanten kringgås 90-dagarskarensen i send-guardens regel 5.
* Följer `origin='example'` med av misstag blockeras prospektet **för alltid**, tyst — send-guarden svarar inte med fel, den bara låter bli.
* `agent_runs.prospect_id` är en FK. Kopiering med nya id:n föräldralöser historiken; det är acceptabelt (historiken är testets), men ska vara ett uttalat val.
* `workspaces.slug` går bara att sätta **en gång** (`where slug is null`, migration 038/040). En "peka om arbetsytan"-lösning öppnar exakt den lucka migrationen skrevs för att stänga. Gå via ny tenant + kopiering, inte ompekning.

---

## 5. Fas 4 — Email-studion in i leaden

**Nuläge:** egen menypost ([lib/routes.ts:94](lib/routes.ts:94)), egen sida,
frikopplad från prospekten. Bolagssidan har i dag en knapp "Skriv mejl ↗" som
länkar *bort* till den generiska studion
([Bolagssida.tsx:185](components/leads/Bolagssida.tsx:185)) — alltså till
E-Tech-exemplet, oavsett vilken lead du tittade på.

Precedens finns redan: [LeadsRunForm.tsx:584](components/leads/LeadsRunForm.tsx:584)
renderar `<EmailStudioEditor compact />` inne i en rad, men bara för
exempelbolag.

| Steg | Ändring | Kontroll |
|---|---|---|
| 5.1 | Ta bort rad 94 ur `appRoutes`. Behåll routen nåbar direkt (mönstret `preview: true` finns). | Menyn har inte längre "Email studio". |
| 5.2 | I [Bolagssida.tsx](components/leads/Bolagssida.tsx): **inget utkast** → bara knappen **"Skapa utkast"**. Ingen studio syns. | Ny lead visar en knapp, inte en editor. |
| 5.3 | "Skapa utkast" anropar den **riktiga** kedjan `POST /api/leads/outreach/draft` (som redan kräver skarp LLM, `_require_live_llm`) — inte studions egen route. | Utkastet har `run_id` i `agent_runs`. |
| 5.4 | När utkast finns: rendera studion inline med leadens verkliga `context` (companyName/signal/offer/cta finns redan i formen). De åtta åtgärderna (`shorter`, `rewrite`, `improve`, `personalize`, `translate`, `ab_variants`, `followup`, `analyze`) fungerar då mot riktig modell tack vare Fas 1. | Två omskrivningar i rad ger olika text. |
| 5.5 | **Persistens:** lägg till INSERT mot `generated_emails` (finns ingen i dag) ELLER koppla studion mot `outreach_messages`. **Rekommendation: `outreach_messages`** — det är den tabell send-kedjan faktiskt läser. `generated_emails` är en parallell, död väg. | En omladdning tappar inte utkastet. |
| 5.6 | **"Godkänn och skicka"** → `POST /api/leads/queue/{id}/approve` (finns). Följdfråga efteråt: "Vill du att agenten skriver utkast automatiskt framöver?" — förkryssat — och "…och skickar automatiskt?" — inte förkryssat. Skriv till `agent_configs.settings.autonomy`. | Nivån syns i `GET /api/leads/config`. |

**Autonominivåerna finns redan:** `draft` → `first_contact` → `meeting` →
`auto_send` ([autonomy.py:31](snajp-support/app/leads/autonomy.py:31)).
`draft` **är** "automatiska utkast, inga utskick" — alltså exakt din default.
Ingen ny flagga behövs.

**Bugg att laga på vägen:** [LeadsControls.tsx:19](components/leads/LeadsControls.tsx:19)
saknar `auto_send` i TS-unionen och i `AUTONOMY_LABEL`, medan backenden
returnerar alla fyra. Fjärde knappen renderar `undefined` som etikett.

**Ärlig invändning:** "Godkänn och skicka" kan i dag inte skicka. Det finns
ingen SMTP-avsändare — `send_provider.py` har bara `LoggingSendProvider` och
`DryRunMailer`. Knappen kan byggas och kön fungerar, men det som lämnar huset
är noll mejl förrän någon skriver `SmtpMailer`. Det ligger som `snipe-ork`.
Jag bygger knappen och köen; **säg till om du vill ha sändvägen i samma svep**,
det är ett eget arbete.

---

## 6. Fas 5 — Testchatt-fliken

**Här krockar önskemålet med tre maskinellt kontrollerade invarianter.** Det
går att bygga precis det du vill ha, men inte på det sätt formuleringen
antyder — och skillnaden är inte formalia.

* **INV-SEC-009:** kundskriven text når aldrig instruktionsposition. Ett
  uppladdat dokument och en fritextfeedback *är* kundskriven text.
* **INV-LEARN-001:** agenten skriver aldrig själv in sina lärdomar i
  underlaget. Enda vägen till en KB-artikel är en människas klick på
  `POST /api/agent/forslag/{id}/godkann`.
* **INV-SEC-003:** opålitlig text placeras aldrig i instruktionsposition.

Skälet, ur invariantens egen text: en kund ska kunna säga *"skriv kortare,
du-tilltal"* och ska **inte** kunna säga *"ignorera reglerna ovan"* — och den
enda robusta skillnaden är **positionen**, inte innehållet.

**Lösning som ger dig allt du bad om utan waiver:** agenten *föreslår*
instruktions- och KB-ändringen, och godkännandeklicket ligger **i chatten**.
Ett klick, direkt i flödet — det känns live, och människan är kvar i loopen.

| Steg | Ändring | Kontroll |
|---|---|---|
| 6.1 | Flik "Testchatt" bredvid "Kundtjänst" i [WorkspaceSection.tsx:152](components/dashboard/WorkspaceSection.tsx:152). Mönstret finns färdigt i [SnajpSupportDemo.tsx:88](components/snajp/SnajpSupportDemo.tsx:88) (i dag oanvänd). Renderar `<SupportChat />` mot inloggad tenant. | Fliken svarar med riktig AI mot kundens egen KB. |
| 6.2 | **Returnera `run_id`** ur `run_support_agent` ([support_agent.py:787](snajp-support/app/agent/support_agent.py:787) returnerar `ticket_id` men inte körningens id). Utan det går feedback inte att koppla. | `run_id` finns i jobbsvaret. |
| 6.3 | Tumme upp/ned + rättningsruta → `POST /api/agent/feedback`. **Endpointen finns redan** ([leads.py:630](snajp-support/app/api/leads.py:630)) och saknar helt anropare. En nedtummad körning med rättad text blir automatiskt ett eval-case. | Feedback syns i `agent_feedback` och ett `agent_evals`-case skapas. |
| 6.4 | Filbilaga. Bilder fungerar redan (`data:image/`, vision-sidovagn). Text (`.txt/.md/.csv/.json/.html`) läses klientsidan i dag av [Kunskapsbas.tsx:40](components/settings/Kunskapsbas.tsx:40). | En textfil blir ett KB-förslag i chatten. |
| 6.5 | **PDF/Word:** i dag medvetet uteslutet — *"en halvläst PDF ger tyst sönderhackad text som agenten sedan citerar som om den vore korrekt"* ([Kunskapsbas.tsx:26](components/settings/Kunskapsbas.tsx:26)). Invändningen gäller **tyst** förlust. Bygg det med `pypdf` **plus en synlig extraktionsförhandsvisning** som kunden måste godkänna. Då är invändningen besvarad, inte kringgången. | Manuell: en tabelltung PDF visar sin extraherade text före godkännande. |
| 6.6 | Agenten föreslår instruktionsändring → visas i chatten med "Lägg till"-knapp → skriver via befintlig godkännandeväg. **Instruktioner läses om vid varje körning** (`las_instruktioner()`), så nästa meddelande använder den nya texten utan cache. | Nytt invarianttest, modell på [tests/invariants/test_inv_sec_009.py](tests/invariants/test_inv_sec_009.py): mata in en promptinjektion via Testchattens filuppladdning och assertera att den bara når prompten inuti sin wrap. |

---

## 7. Fas 6 — Minst 10 riktiga rundor, DeepSeek mot Gemini

**Harnessen finns redan.** Inget behöver byggas: `scripts/kor_evals.py`
(7 golden-case), `scripts/run_live_tests.py --support` (5 scenarier),
`scripts/run_live_leads.py`, och jämföraren `scripts/jamfor_livekorningar.py`.

**Var det måste köras:** DeepSeek får bara se syntetisk data. Spärren mäter
databasen, inte miljönamnet — `har_riktig_kunddata()` returnerar true för
varje **icke-loopback** `DATABASE_URL`.

> **Fynd att åtgärda först:** `snajp-support/.env` står i dag med
> `LLM_PROVIDER=deepseek` **och** en `DATABASE_URL` mot
> `db.eppgmjswfnrfwnqvtrge.supabase.co` — en fjärrvärd. Backenden **vägrar
> starta** i det läget, korrekt. Den frestande "fixen" är att byta provider;
> den rätta är att tömma `DATABASE_URL`. Städa filen.

| Steg | Åtgärd |
|---|---|
| 7.1 | `$env:DATABASE_URL = ""` → MemoryStorage, som `kor_evals.py:29` redan gör i kod. Tenant: Nordlys Handel, 31 KB-artiklar, autoseedad. |
| 7.2 | Runda A, DeepSeek: `LLM_PROVIDER=deepseek`, `MODEL=deepseek-v4-flash`. `kor_evals.py` (7) + `run_live_tests.py --support` (5) = **12 rundor**. |
| 7.3 | Runda B, Gemini: `LLM_PROVIDER=gemini`, `MODEL=gemini-3.6-flash`. **Båda måste bytas** — `MODEL` autokorrigeras bara från ett `gpt-`-namn, annars fäller `llm_provider_fault()`. |
| 7.4 | **Gemini-rundorna kräver B1 först.** Dygnstaket är 20 anrop och 12 rundor är ~84 anrop — fyra gånger ransonen. Utan kopplingen mäter jämförelsen kvoten, inte modellen. Efter B1: takta ändå ~70 s mellan ärenden tills minuttaket är verifierat borta. **OBS: dygnsransonen för 2026-08-28 är förbrukad** — den gick åt när jag mätte nivån (se §1.1). Den återställs vid UTC-midnatt. |
| 7.5 | `jamfor_livekorningar.py` per scenario: eskalering, kategori, KB-träffar, stegantal, tokens, väggtid. |
| 7.6 | Leads-sidan separat: `run_live_leads.py` mot fixturerna `prospects-goteborg.csv` / `prospects-umea.csv` (12 syntetiska bolag, `.example`-domäner) — samma prospekt, båda providers, jämför utkasten. |

**Lucka att täppa till för att jämförelsen ska bli läsbar:** `agent_runs` har
**varken `model` eller `provider`**. Verifierat mot 010/025/027/036. Två körningar
går bara att skilja åt på filnamn. Lägg till kolumnen `model text` — en
migration, ett fält i `log_agent_run`, båda storage-implementationerna.

**Invariant som måste hållas:** `INV-STORE-001` — `MemoryStorage` och
`PostgresStorage` har identiska signaturer. Repot har en dokumenterad
sexmånadersbugg som kom ur precis den driften.

**Regressionsgrind, mätt i dag:**

```
snajp-support : 1445 passed, 4 skipped, 65 s
tests/        :  333 passed, 37 skipped, 19 s
```

---

## 8. Fas 7 — Produktion på main och snajp.se

### 8.1 Den dokumenterade deploy-kedjan för main är i dag FARLIG

Detta är planens allvarligaste fynd. Verifierat med `git rev-list` mot
`origin`-referenser, inte mot den lokala kopian:

```
origin/main..origin/development     : 253
origin/main..origin/railway-main    : 152
origin/railway-main..origin/main    :   0
origin/development..origin/railway-main : 1
```

`origin/main` ligger **152 commits efter** `origin/railway-main` och **noll
före**. Alltså:

> **`git push origin main:railway-main`, som `DEPLOY.md` föreskriver, avvisas
> i dag som non-fast-forward. Tvingas den igenom rullar den tillbaka
> produktionen 152 commits** — och raderar både omläggningen 22 aug och
> hotfixen 25 aug.

Kör den **inte**. `main` är inte längre produktionens källa; `railway-main` är.

Den enda commit produktionen har som `development` saknar är `78c900e`
("produktionen svarade kunder med regelmotorn — gemini fanns inte i koden").
**Jag har verifierat att `development` innehåller hela dess innehåll i utökad
form** — diffen visar att development *lägger till* allt railway-main har,
plus `llm_provider_fault`, `har_riktig_kunddata` och `master_key_fault`.
Att deploya development regresserar alltså inte produktionen.

**Ordningen när den dagen kommer — men se spärren nedan, ingenting av det här körs nu:**

1. `git checkout development && git merge origin/railway-main` — tar in `78c900e`. Konflikt i `llm.py`/`config.py` väntas; lösningen är development-versionen.
2. Testsviterna gröna (§7).
3. `python scripts/railway_migrate.py --env main --apply` — **torrkörning först**.
4. `git push origin development:railway-main` — nu fast-forward, ingen force.
5. Lägg om `main` på samma sätt som `development` (deployment trigger → grenen `main`) och släck tvåstegsfällan för gott.

### 8.1a SPÄRR: ingenting rörs mot produktion

**Antons instruktion 2026-08-28. Gäller hela planen, inte bara det här avsnittet.**

> Push:a eller pull:a ingenting mot produktion. Förbered bara det som går att
> förbereda.

Konkret, det som INTE får köras utan att Anton säger till uttryckligen:

* `git push origin main`, `git push origin main:railway-main`, `git push origin development:railway-main` — någon push som rör `main` eller `railway-main`
* `git pull`/`git fetch` som ändrar de grenarna lokalt, och varje `merge` av `origin/railway-main`
* `python scripts/railway_migrate.py --env main --apply`
* `scripts/railway_provision.py` mot en befintlig miljö (se §8.2 — den återställer providern till den förbjudna)
* Varje skrivande Railway-anrop mot miljön `main`

Läsning är fri: `git log`, `git rev-list`, `/health`-anrop och torrkörningar utan
`--apply` ändrar ingenting och används gärna.

**Det som DÄREMOT går att förbereda nu, utan att röra produktionen:**

| Går att göra | Varför det är ofarligt |
|---|---|
| DNS för `www.snajp.se` (§8.4) | Loopias zon är inte Railway. En CNAME kan sättas innan koden flyttas — den pekar bara på en tjänst som redan står där. |
| Fas 1–6 på `development` | Egen gren, egen miljö, egen deploy sedan 27 aug. |
| Rätta `railway_provision.py` (§8.2) | En kodändring i repot; skriptet körs inte. |
| Rätta `DEPLOY.md` så tvåstegsfällan inte står kvar som en instruktion | Dokumentation, ingen drift. |
| Städa döda arbetsflöden (§8.3) | Tar bort falska gröna signaler; deployar ingenting. |

### 8.2 Kör INTE railway_provision.py mot en befintlig miljö

[scripts/railway_provision.py:319](scripts/railway_provision.py:319) upsertar
`LLM_PROVIDER: "deepseek"` och `MODEL: "deepseek-v4-flash"` på `api` **varje
gång**, även för en redan provisionerad miljö. Mot `main` eller `development`
sätter det den förbjudna providern och tjänsten vägrar starta. Skriptet måste
sluta skriva de två variablerna för en befintlig miljö.

### 8.3 Städa döda och vilseledande kedjor

* `.github/workflows/deploy-production.yml` deployar en Vercel-förhandsvisning på varje push till `main` och blir **grön** — en falsk hälsosignal mot en död stack.
* `.github/workflows/deploy-development.yml` speglar fortfarande till `railway-development`, som ingen läser sedan 27 aug.
* `EMAIL_STUDIO.md:75` innehåller ett **lösenord i klartext** för ett testkonto. Bort, och rotera.

### 8.4 snajp.se

`scripts/loopia_dns.py` finns och är färdigt. Utan API-användare kör det i
kontrolläge och skriver ut vad som ska fyllas i.

**Rättelse på variabelnamnen du skickade:** koden läser
`LOOPIA_API_USER` och `LOOPIA_API_PASSWORD` ur `.env.deploy` — inte
`LOOPIA_USERNAME`/`LOOPIA_PASSWORD`. Användarnamnet `snajp@loopiaapi` stämmer
med formatet. **Lösenordet saknas:** `ditt_api_lösenord` är platshållartexten
ur `DEPLOY.md:369`, inte ett värde.

Båda saknas i `.env.deploy` i dag (verifierat).

Uppgifterna skrivs med [`scripts/loopia_nycklar.py`](scripts/loopia_nycklar.py):

```bash
python scripts/loopia_nycklar.py
```

Det frågar efter användarnamnet, läser lösenordet med `getpass` (ingen eko,
ingen historik) och skriver via `railway_provision.env_set`, som bara skriver
ut nyckelns namn och längd. `--kontroll` visar status utan att skriva något.

**Lösenordet tas medvetet inte som argument.** Ett kommandoradsargument hamnar
i skalets historik och i processlistan och ligger kvar långt efter att fönstret
stängts — samma läckagespärr som CLAUDE.md beskriver.

Verifierat mot en kopia (rör inte den riktiga filen): lösenordet syns inte i
utskriften, befintliga rader bevaras, en befintlig nyckel ersätts i stället för
att dubbleras.

**Apex går inte att peka på Railway** — CNAME får inte samexistera med NS/SOA,
Loopia saknar ALIAS/ANAME, och Railways plan tillåter en egen domän per
tjänst (upptagen av `www`). Kvar: Loopias webbvidarebefordran
`snajp.se → https://www.snajp.se`, som inte finns i LoopiaAPI. **Den punkten
förblir manuell.**

---

## 9. Övrigt jag hittade och som du bör känna till

* **Möjlig hemlighetsexponering.** En av mina utforskande delagenter skrev av misstag ut klartextvärdena för `RENDER_API_KEY`, `PREVIEW_DB_PASSWORD` och `PREVIEW_SUPABASE_ANON_KEY` i sin egen loggutskrift innan den stoppade sig själv. Värdena har inte förts vidare någon annanstans, men de finns i den sessionens logg. **Rekommenderar rotation av alla tre.** `RENDER_API_KEY` låg redan för rotation som `snipe-fek`.
* **Jag förbrukade dygnets Gemini-kvot 2026-08-28.** Nivåmätningen i §1.1 krävde riktiga anrop, och de tog dygnets 20. Eftersom nyckeln delas mellan miljöerna gäller det **även produktionen** — supportagenten i drift faller till fallbacktext resten av UTC-dygnet. Det var priset för att få ett svar som inte var en gissning, men det borde ha varit ditt beslut att ta, inte mitt. Kvoten återställs vid UTC-midnatt.
* **Ingen sändväg finns** — varken IMAP in eller SMTP ut, i någon miljö.
* **`.agent-context/current/`-paketet är en ifylld mall utan innehåll** — alla tre filerna CLAUDE.md pekar på består av HTML-kommentarer med instruktioner till en agent som aldrig fyllde i dem. De ger noll vägledning i dag och kostar en läsning per session.

---

## 10. Ordning och beroenden

```
B1/B2 (betald nivå + juridik)  ─┐
                                ├─→ Fas 6 skarpt i drift ─→ Fas 7 (produktion)
Fas 1 (gör ytorna skarpa)      ─┘
   │
   ├─→ Fas 4 (Email-studio i leaden)     ← behöver Fas 1
   ├─→ Fas 5 (Testchatt)                 ← oberoende
   └─→ Fas 2 (testisolering) ─→ Fas 3 (befordra prospekt)

Fas 6 lokalt (DeepSeek + Gemini mot syntetisk data) går att köra NU,
oberoende av B1 — det är bara drift som blockeras.
```

**Förslag på ordning:** Fas 1 → Fas 2 → Fas 6 lokalt (mäter att Fas 1 gav
effekt) → Fas 4 → Fas 5 → Fas 3 → Fas 7.

**Fas R (tillagd 2026-08-29, Antons beställning):** Redis-arkitekturen —
körningar som överlever deployments (Streams + återtag, INV-JOB-001),
tenant-skopad semantisk svarscache + embeddingcache (INV-CACHE-001,
shadow-läge först), arbetsminne med rullande samtalssummering, och
Redis Cloud/Resend införda som underbiträden i juridikkedjan. Egen plan med
produktdomarna över Redis Iris (Agent Memory, LangCache, Context Retriever):
[2026-08-29-redis-agentarkitektur.md](2026-08-29-redis-agentarkitektur.md).
R0–R4 är oberoende av B1 och byggs i development; R5 (main-provisionering)
lyder under §8.1a-spärren precis som Fas 7:s deploydel.

**Fas 7 är delad i två, och bara den ena är påbörjad:**

* **Förberedelsen** — DNS för `www.snajp.se`, rättningen av
  `railway_provision.py`, rättad `DEPLOY.md`, städade arbetsflöden. Rör inte
  produktionen och görs nu.
* **Själva deployen** — varje push, merge och migration mot `main`/
  `railway-main`. **Spärrad enligt §8.1a.** Kräver att du säger till, och
  först efter B1.
