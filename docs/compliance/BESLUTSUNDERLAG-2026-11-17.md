# Beslutsunderlag: EU-compliance inför första kund

Datum: 2026-11-17. Mappen `docs/compliance/` är undantagen från git lokalt, eftersom repot är publikt.

## Läget 2026-11-18

Matriserna i `ramverk/` är omgjorda med samma regler som i går. Kod som bara kör i testmiljön (mergat till `development`, release-PR 60 väntar på din merge) räknas som delvis. Osignerade utkast räknas som delvis. Inget krav blev uppfyllt i dag.

| Ramverk | Uppfyllt | Delvis | Saknas | Ej tillämpligt | Okänt | Krav med ny bevisning |
|---|---|---|---|---|---|---|
| GDPR (19) | 0 → 0 | 16 → 17 | 2 → 1 | 1 → 1 | – | 17 |
| ISO 27001 (119) | 0 → 0 | 71 → 74 | 28 → 25 | 8 → 8 | 12 → 12 | 37 |
| ISO 42001 (70) | 1 → 1 | 53 → 53 | 16 → 16 | 0 → 0 | 0 → 0 | 19 |

Statusändringar: GDPR PR-4 (rätten till begränsning står i policyn i testmiljön, rutin som utkast). ISO 27001 A.5.7, A.8.8 och A.8.16 (Dependabot, kodskanning och hemlighetsskanning påslagna; driftövervakning med provad larmkedja). Alla fyra från saknas till delvis.

**Därför inget uppfyllt.** Det som hänt i drift (TypeSafe stoppad för kundmejl, jobbkön på Railways privata nät, skanningen påslagen, Render och gamla Vercel stängda, övervakningen) tar bort gap men stänger inget krav. Varje krav hänger också på något osignerat, osläppt eller ogjort.

**Fynd i dag som drar åt andra hållet:**
- 68 öppna Dependabot-larm: 10 kritiska, 28 höga. 44 öppna kodskanningslarm, de flesta bedömda som falska men inte avfärdade.
- Övervakningen har gått glest: en schemalagd körning under natten (04:44 UTC), inte en var 15:e minut.
- Postgres har fortfarande en publik TCP-proxy i båda miljöerna.
- GitHubs privata sårbarhetsrapportering är avslagen.
- Ett Vercel-projekt leder fortfarande apexdomänen vidare.

### De tio åtgärder som nu flyttar flest krav

Ordnade efter hur många krav som byter status. Siffran är ungefärlig och räknas över alla tre ramverken.

| # | Åtgärd | Krav som flyttas | Vem |
|---|---|---|---|
| 1 | Signera ledningssystemet: beslut e (omfång) och a (roller), godkänn P07, P27, policyerna och SoA | cirka 19: 27001 4.3, 4.4, 5.1, 5.2, 5.3, 6.1.3, A.5.1, A.5.2, A.5.4, A.5.12, A.5.13; 42001 4.3, 4.4, 5.1, 5.2, 5.3, A.2.2, A.3.2; GDPR AG-1 | Du; Sebbe signerar a |
| 2 | Fyll i enhetslistan med skärmbilder (`underlag/rutiner/e-enheter.md`) | cirka 10: 27001 A.8.1, A.8.7, A.7.7–A.7.10, A.7.13, A.7.14, A.5.9, A.6.7 | Du och Sebbe |
| 3 | Leverantörerna: signera Railways DPA och beslut f, skicka breven, radera Supabase, Render och Redis Cloud, rotera Render-nyckeln | cirka 10: GDPR AG-2, DS-1; 27001 A.5.19, A.5.20, A.5.22, A.5.23, A.5.26; 42001 A.10.3, 6.3, 8.1 | Du |
| 4 | Konton och lösenord: byt plattformsadminens lösenord, gör åtkomstgenomgången med tvåfaktor (`rutiner/d-…`), besluta repots synlighet | cirka 9: 27001 A.5.15–A.5.18, A.8.2, A.8.4, A.8.5, 7.5.3; 42001 7.5.3 | Du och Sebbe |
| 5 | **Merga PR 60**, och låt sedan en jurist granska PUB-avtalet, policyn, DPIA:n och intresseavvägningen; signera PUB med första kunden | cirka 9: GDPR AG-2, DS-4, LBT-2, LBT-3, PR-7; 27001 A.5.31; 42001 A.5.3, A.10.2, A.8.2 | Du (merge), jurist |
| 6 | Håll utbildningsgenomgången och signera kvittensen (`underlag/utbildning/`) | 7: GDPR DS-3; 27001 7.2, 7.3, A.6.3; 42001 7.2, 7.3, A.4.6 | Du och Sebbe |
| 7 | Håll incidentövningen och bedöm incidentposterna, också TypeSafe-överföringen | 7: GDPR DS-5; 27001 A.5.24, A.5.25, A.5.27, 10.1; 42001 10.2, A.8.4 | Du och Sebbe |
| 8 | Rättighetsrutinen: fyll i och signera, lägg upp loggen, öppna `integritet@`, provkör raderingsskriptet mot lokal stack | 6: GDPR PR-1–PR-6 | Agenten provkör, du resten |
| 9 | Sårbarheterna: åtgärda kritiska och höga beroendelarm, avfärda de falska kodskanningslarmen med motivering, besluta patchtider, slå på privat sårbarhetsrapportering | 6: 27001 A.8.8, A.5.21, A.8.25, A.8.28, A.8.29, A.6.8 | Agenten åtgärdar, du avfärdar och beslutar |
| 10 | **Railway Pro:** slå på säkerhetskopior, signera beslut g, gör ett återställningsprov | 4, alla från saknas: 27001 A.8.13, A.5.29, A.5.30, A.8.14; också gapet i GDPR DS-2 och fyra uppgifter | Du (Pro, beslut), agenten provar |

**Mergen av PR 60** flyttar inget krav ensam. Den tar bort gapet "inte i drift" i ungefär 20 krav: GDPR AG-2, DS-1, DS-2, LBT-2, LBT-3, PR-4, PR-5, PR-6, PR-7; ISO 27001 A.5.26, A.6.8, A.8.10, A.8.11, A.8.26; ISO 42001 7.4, 8.1, A.7.5, A.7.6, A.8.2, A.8.3. Den är förutsättningen för åtgärd 5 och för gallringen, och den kostar dig minst tid av allt i listan. Kontrollera först vilka kunder i main som saknar `policy_url` (PR 60, "Innan mergen").

**Railway Pro** flyttar färre krav, men den är den enda vägen till att kunna återställa produktionsdatabasen (GDPR art. 32.1 c). Inget annat i listan ersätter den.

Underlagen för åtgärd 1–10 står i `underlag/LASMIG.md`.

---

## Underlaget 2026-11-17

Läget i en mening: tre exponeringar behöver åtgärdas i dag, sju gap blockerar första kunden, och valet av väg för Comp AI är ditt.

---

## A. Akut, i dag

**Läget kväll 2026-11-17, efter ditt "Gör alla fyra" och ditt "Ja, flytta" (A3):**

| Punkt | Läge | Kvar, och vems |
|---|---|---|
| A1 | Hemlighetsskanning och push-skydd påslagna på repot. Inga larm vid första kontrollen | Skanningen känner bara igen leverantörers nyckelformat, inte vanliga lösenord. Lösenordsbytet och repots synlighet är fortfarande dina |
| A2 | Genomfört och verifierat. `INKORG_JEV` av i `main` och `development` sedan 20:54 UTC; nya deployer uppe, hälsokontrollerna ok. Inkorgen sorteras bara av kodreglerna; Jev finns kvar i leadsdelen | Begära radering hos TypeSafe av kundmejltext som redan skickats (ditt). Bedömning av anmälningsplikt och underrättelse till berörda kunder (ditt). Beslut om leadsdelen |
| A3 | Genomfört och verifierat genom flytten (väg b, ditt "Ja, flytta"). TLS gick inte i Redis Clouds gratisplan, så jobbkön ligger nu på Railways egen Redis. `development` använder sin befintliga Redis-tjänst; i `main` skapades en ny Redis-tjänst med samma image och uppsättning (lösenord, egen volym, Amsterdam, ingen publik adress). `REDIS_URL` på api i båda miljöerna pekar på det privata nätverket. Uppstartsloggen i båda miljöerna visar jobbkö, svarscache, chattström och leadsström mot Redis, hälsokontrollen ok. Pågående jobb och cache i den gamla databasen följde inte med. `scripts/redis_tls_pa.py` är märkt inaktuellt och får inte köras | Radera Redis Cloud-databasen och säg upp kontot (ditt beslut, inte gjort). Ta bort reservvariabeln `REDIS_URL_FORE_FLYTT` på api-tjänsten i båda miljöerna efter några dagar. Bedömningen av tiden med okrypterad trafik (incidentloggen 2026-08-29) är din |
| A4 | Inte genomfört. Railway kräver Pro-planen för både schemalagda och manuella säkerhetskopior av volymer, och kontot ligger på en lägre plan. Produktionsdatabasen har fortfarande ingen kopia | Två vägar, ditt val: (a) Railway Pro med dagliga, veckovisa och månatliga kopior; (b) ett eget schemalagt jobb som dumpar databasen till en lagringsplats i EU. **Rekommendation: uppgradera till Pro**, som också behövs om Comp AI:s images ska hållas privata |

Texten nedan är underlaget som det såg ut före åtgärderna.

### A1. Repot är publikt och plattformsadminens lösenord ligger i historiken

- `oloflun/snipe-leads` är publikt på GitHub. Det går att läsa utan inloggning (kontrollerat 2026-11-17).
- Commit `48120148` (2026-11-09) tog bort plattformsadminens lösenord ur fem skript och två handoffs. Värdet ligger kvar i den publika historiken.
- Repots egna dokument säger öppet att lösenordet inte är bytt (`docs/BESLUT.md`, `docs/stabilitet-2026-11/SLUTRAPPORT.md` rad 173 och 203).
- Följd: vem som helst kan läsa lösenordet och pröva det som plattformsadmin, alltså mot alla kunders data.
- Min skanning av hela historiken hittade inga API-nycklar till leverantörer. Den hittade lösenord i klartext i `scripts/railway_agentsajt.py`, `scripts/railway_bokforing.py`, `scripts/qa_kundresa.mjs`, `scripts/test-auth-flow.mjs` och `scripts/lokal_stack.py`. Listan utan värden: `bevis/historik-hemligheter-2026-11-17.txt`.
- GitHubs hemlighetsskanning är avslagen på repot, trots att den är gratis för publika repon.

**Bara du kan göra:**
1. Byt plattformsadminens lösenord nu, och uppdatera `QA_ADMIN_LOSEN` i `.env.deploy`.
2. Byt `AGENTSAJT_LOSEN` och de övriga lösenord som legat i skripten ovan, om de används i drift.
3. Besluta om repot ska vara privat. Jag har inte ändrat synligheten, eftersom det påverkar funktionen: på gratisplanen slutar grenskyddet på `main` att gälla i ett privat repo, och synken var tionde minut förbrukar de fria Actions-minuterna på ungefär två veckor.

**Jag kan göra på ditt ja:** slå på GitHubs hemlighetsskanning och push-skydd (en inställning, ändrar ingen funktion).

Tills du beslutat om synligheten committar eller pushar jag inget av compliance-arbetet. Utkasten beskriver öppna brister i detalj.

### A2. Kundmejltext går till TypeSafe i USA

- `INKORG_JEV = auto` i produktion. Ämnesrad och upp till 1 500 tecken av kundmejl skickas till TypeSafe AI, Inc. i San Francisco.
- `jev.py` anger ditt beslut 2026-09-30: Jev ser aldrig kundmejl. Vem som slog på `auto` framgår inte.
- Avtalet (kontrollerat i källan): §4.1(c) ger TypeSafe rätt att "in perpetuity" härleda telemetri ur kunddata, och §4.3 låter dem använda den "without restriction". Bolaget finns inte i DPF-listan. Ingen EU-region finns.
- Leverantören saknas i alla underbiträdeslistor.

**Rekommendation:** stäng av (`INKORG_JEV=off` i `main` och `development`). Inkorgen sorterar då med kodreglerna. Leadsdelen påverkas inte. Jag gör det på ditt ja.

### A3. Redis går okrypterat

- `REDIS_URL` börjar på `redis://` i både `main` och `development`, och miljöerna delar samma Redis-databas. Jobbposterna bär agentens svar till kundernas kunder.
- `scripts/redis_tls_pa.py --apply` slår på TLS och byter URL i samma steg. Det har legat som ditt handgrepp sedan 2026-08-29.

**Rekommendation:** kör skriptet, eller ge mig ditt ja så kör jag det och verifierar anslutningen efteråt.

### A4. Produktionsdatabasen har inga säkerhetskopior

- Enligt Railways API (2026-11-17) har produktionens Postgres-volym inget backupschema och ingen sparad kopia. Detsamma gäller testmiljöns volymer. Belägg: `bevis/railway-backuper-2026-11-17.txt`.
- Det enda som liknar en kopia är testmiljön, som synkas från produktionen. Den ligger hos samma leverantör i samma region och skyddar inte mot ett fel som synkas vidare.
- Följd: ett raderat eller förstört schema i produktionen går inte att återställa. GDPR art. 32.1 c kräver förmåga att återställa personuppgifter i rimlig tid.

**Rekommendation:** slå på Railways schemalagda säkerhetskopior för produktionsvolymen (dagligen, veckovis och månadsvis). Det är en inställning och en lagringskostnad. Jag gör det på ditt ja och provar sedan en återställning mot en tom volym.

---

## B. Beslut som bara du kan fatta

| # | Beslut | Min rekommendation |
|---|---|---|
| B1 | Enskild firma eller AB. Org.nr för en enskild firma är ditt personnummer, och det ska stå på sajten, i avtal och i varje utskick | Fråga juristen. Ett AB löser både exponeringen av personnumret och det personliga ansvaret |
| B2 | Gallringsperiod. Integritetspolicyn lovar 24 månader och automatisk gallring, men inget gallringsjobb körs | Bekräfta 24 månader, så bygger jag jobbet och utökar det till leads och agentloggar |
| B3 | Avtalsgrinden som standard för nya kunder (i dag av, så en ny kund får trafik utan signerat avtal) | Ja |
| B4 | AI-upplysning i chatten och i automatiska mejlsvar (AI-förordningen art. 50 gäller sedan 2026-08-02) | Ja, en fast rad som koden lägger till |
| B5 | Förnamnsadresser (`anna@bolaget.se`) räknas i dag som funktionsadresser och får ingen art. 14-information | Räkna dem som personliga. Det ändrar foten i utskicken |
| B6 | Org.nr i kallmejl. E-handelslagen kräver det; spärren kräver sedan 2026-10-10 bara företagsnamn | Fyll i uppgifterna så att foten bär dem. Kravet i spärren kan vara kvar som i dag |
| B7 | Demolänkens spårning per namngiven mottagare. Cookiesidan säger att beteende inte mäts | Informera i policyn och foten, eller ta bort personkopplingen |
| B8 | Reservvägen till Google AI Studio för kunddata | Spärra den i miljöer med riktig data, som DeepSeek |
| B9 | Synken via GitHub Actions bär produktionens persondata genom runners i okänd region. Kontot är Free och täcks inte av GitHubs DPA | Flytta synken till en schemalagd tjänst hos Railway i Amsterdam |
| B10 | Juristgranskning av biträdesavtalet, villkoren, DPIA:n och intresseavvägningen | Boka. Frågorna står överst i `docs/pub-avtal.md` |

---

## C. Handgrepp som bara du kan göra

1. **Railway:** signera DPA:n via DocuSign-länken på `docs.railway.com/enterprise/compliance`. Den gäller inte förrän den är signerad. Begär samtidigt besked om var backuperna ligger.
2. **Bolagsuppgifter:** org.nr, postadress och en dataskyddsadress (`integritet@snajp.se`) i `lib/bolag.ts`.
3. **Render:** stäng tjänsterna och rotera nyckeln. **Supabase:** radera det gamla projektet och begär raderingsbekräftelse.
4. **Google Cloud:** skapa separata servicekonton per miljö. Avtalet gäller automatiskt.
5. **Redis och Resend:** avtalen gäller automatiskt. Ladda ned Resends signerade kopia. Resend lagrar mejlinnehåll och loggar i USA i 30 dagar trots EU-region; det ska godkännas av dig och stå i avtalsbilagan.
6. **ScrapeGraphAI:** kontrollera att planen är betald och begär DPA.

Källor och detaljer per leverantör: `leverantorsgranskning.md`.

---

## D. Comp AI: vilken väg

Repots egna instruktioner ger ingen fungerande installation. API-tjänsten saknas i `docker-compose.yml`, och README säger åt en att redigera filer, vilket du har förbjudit.

| Väg | Vad det kräver | Risk |
|---|---|---|
| 1. Självhosta oförändrat (din instruktion) | Nio nycklar från dig (Trigger.dev, AWS, Vercel AI Gateway, OpenAI, Anthropic, Resend, GitHub), cirka 30–45 dollar i månaden, bygge i GitHub Actions | Två otestade kringgåenden: sessionskakan tappar Secure-flaggan, och certifikatkontrollen mot databasen stängs av över publikt nät. Går inloggningen inte att lösa finns ingen väg utan kodändring. Fem nya amerikanska led |
| 2. Comp AI Cloud | Säljsamtal för pris | Annan kodbas än repot, amerikansk leverantör, okänd kostnad |
| 3. Repots ramverk utan plattformen | Inget från dig | Bryter mot din instruktion att använda hela repot |

**Min rekommendation: väg 3 nu, väg 1 senare om en kund eller revisor kräver plattformen.**

Skälet: plattformen gör er inte compliant. Det gör åtgärderna i A, B och C, och de är desamma oavsett väg. Väg 1 kostar ungefär en timme av dina händer och lägger till brister (okrypterad kontroll mot databasen, kakor utan Secure, fem nya led) i just det register plattformen ska hålla ordning på. Ramverken i repot (GDPR med 19 krav, ISO 27001 med 119 krav, ISO 42001 för AI) går att använda som struktur direkt.

Det är ditt val. Väljer du väg 1 börjar jag med det minsta testet (API, app och proxy) för att bevisa inloggningen innan du skapar alla nycklar. Plan: `driftplan.md`.

**Läge kväll 2026-11-17, väg 1:**
- **Etapp 1 är bevisad.** Det privata repot `oloflun/comp-deploy` bygger alla fyra images (api, app, portal och en omvänd proxy) i GitHub Actions från `trycompai/comp` på en låst commit. Byggena kontrollerar själva att Comp-utcheckningen saknar spårade ändringar, så källkoden är orörd.
- Uppströms egen Dockerfile bygger inte app och portal på den commiten (den kopierar inte in fyra interna paket). Byggrecepten för app och portal ligger därför i pipeline-repot. API:t byggs med uppströms recept oförändrat, på en basimage som bara höjer minnesgränsen under bygget.
- **Etapp 2** kräver ditt Railway-projekt, ett Trigger.dev-konto och en Resend-nyckel, enligt `KONTON-OCH-NYCKLAR.md` i det repot. Imagerna är inte startade.
- **Största osäkerheten är fortfarande inloggningen bakom proxyn.** Den är oprövad tills etapp 2 körs.

---

## E. Gjort hittills (inget committat)

Rättelse: rubriken sa tidigare att ingen driftmiljö var ändrad. I kväll ändrades driften efter dina ja: `INKORG_JEV` av i båda miljöerna, hemlighetsskanningen och push-skyddet påslagna, jobbköns adress bytt i båda miljöerna, och en ny Redis-tjänst skapad i produktionen (A1–A3).

- Nulägesinventering med 29 gap: `nulage-inventering.md`.
- Leverantörsgranskning av 15 leverantörer med källor: `leverantorsgranskning.md`, `leverantorer.json`.
- Verifierat i driften: Railway kör i Amsterdam; Redis utan TLS; `INKORG_JEV=auto` (`bevis/`).
- Utkast till biträdesavtal: `docs/pub-avtal.md`.
- Uppdaterade utkast: `docs/dpia_supportagenten.md`, `docs/intresseavvagning_kallmejl.md`, incidentloggen i `INCIDENT_RESPONSE.md`.
- Kod: personnummer maskeras före TypeSafe (`snajp-support/app/leads/jev.py`, 24 tester gröna). Villkoren beskriver utskicksspärren korrekt (`app/villkor/VillkorSida.tsx`).
- Onboardingen har juridiska steg: `docs/pilot_onboarding.md`.

Inte gjort: typkontrollen (`tsc`) kördes inte, för lite minne. `bd` går inte att använda, `dolt` saknas.

## F. Gjort efter första versionen av underlaget

- Underbiträdeslistorna stämmer med driften på fyra ställen: `lib/bolag.ts`, `docs/pub-avtal.md` Bilaga 3, `docs/pilotavtal.md` Bilaga 1, `docs/registerforteckning.md`.
- `docs/JURIDIK_ATGARDER.md` är omskriven till dagens läge.
- Raderingsskriptet `scripts/gdpr_radera.py` täcker dagens tabeller och har ett test som hindrar att det halkar efter. Det är aldrig kört mot en databas.

## G. GDPR-ramverket ur Comp AI, kört mot Snajp

Mappen `ramverk/gdpr/` innehåller matrisen för alla 19 krav, de sex policyerna ur ramverkets mallar, de 15 uppgifterna och en importfil för plattformens API.

- **Status:** 0 krav uppfyllda, 16 delvis, 2 saknas (intern säkerhetspolicy med utbildning; rätten till begränsning), 1 ej tillämpligt (EU-representant, eftersom Snajp är etablerat i Sverige).
- **Dataskyddsombud:** krävs inte i dag enligt bedömningen i `ramverk/gdpr/matris.md`. Du behöver besluta den och skriva in den i `docs/BESLUT.md`.
- **Inga uppgifter går att stänga med befintligt bevis.** Skälet är genomgående detsamma: utkast som inte är granskade, skript som inte är körda och beslut som inte är fattade.
- **De sex policyerna är utkast** som du ska godkänna. Avstegen från mallarna (som förutsätter ett större bolag) står som undantag i varje policy.

Det som flyttar flest krav till uppfyllt är punkterna i A, B och C ovan.

## H. ISO 27001-ramverket ur Comp AI, kört mot Snajp

Mappen `ramverk/iso27001/` innehåller matrisen för alla 119 krav, ett utkast till Statement of Applicability, 20 policyer utöver de sex från GDPR, uppgifterna och en importfil.

- **Status:** 0 krav uppfyllda, 71 delvis, 28 saknas, 8 ej tillämpliga (fysiska kontroller för egna lokaler), 12 okända tills du lämnat uppgifter.
- **Tre nya fynd, kontrollerade mot källorna:**
  - Produktionsdatabasen har en publik TCP-port mot internet påslagen hos Railway (lösenordsskyddad). Synken från GitHub Actions använder den. Flyttas synken till Railway kan porten stängas.
  - De interna larmen är troligen inte aktiva: inga variabler för larmens sändväg är satta i någon miljö.
  - Arbetsflödet `keep-backend-awake.yml` pingade den avvecklade Render-tjänsten var tionde minut på vardagar och höll den vid liv. Jag har tagit bort filen i arbetskatalogen (ocommittat).
- **Uppgifter som bara du har** (behövs för de 12 okända kraven): tvåfaktorinloggning per konto och person (GitHub, Railway, Google Cloud, Redis, Resend, Loopia, Gmail), vem som har vilken roll i varje tjänst, datorernas diskkryptering och skärmlås, lösenordshanterare, var `.env.deploy` förvaras, och Sebbes avtal (form, sekretess, om den gäller efter att han slutat). Hela listan står sist i `ramverk/iso27001/matris.md`.
- **De tio åtgärder som flyttar flest krav** står också där. Överst: att du godkänner omfattning, policyer och SoA, och att konton och åtkomster inventeras.

**ISO 42001 (AI-ledningssystem) är också kört:** mappen `ramverk/iso42001/`. 1 av 70 krav uppfyllt, 53 delvis, 16 saknas. Kartläggningen mot AI-förordningen står i `ramverk/iso42001/ai-forordningen.md`: supportagenten är begränsad risk enligt art. 50, inte högrisk; Iris begränsad eller minimal; Jev minimal. AI-kunnighet enligt art. 4 saknas.

## I. Byggt som ocommittade ändringar, för din granskning

- **AI-upplysning (AI-förordningen art. 50):** "AI-assistent" i chattens huvud och en fast rad i mejl som skickas utan granskning. Invariant INV-AI-001.
- **Avtalsgrinden som standard** för kunder som läggs upp manuellt (migration 118, INV-AVTAL-001). Provflödet för självregistrerade kunder är oförändrat; se den öppna frågan i `docs/BESLUT.md`.
- **Spärr mot Google AI Studio där data är riktig** (INV-DATA-004): tjänsten vägrar starta med gemini utan läsbart servicekonto, och varje reservväg till AI Studio vägrar själv. Servicekontot i `main` och `development` är kontrollerat och klarar spärren. Beslutet står i `docs/BESLUT.md` 2026-11-17.
- **Personlig adress (B5):** en mottagaradress räknas som personlig när lokaldelen inte är en känd funktionsadress (`FUNKTIONSADRESSER` i `snajp-support/app/leads/sources/base.py`, avdelningsorden i `discovery.AVDELNINGSORD`). `anna@` och `andersson@` får den fullständiga foten med art. 14-information; `vd@` och `ceo@` räknas som personliga. Poängsättning och rollkoppling behåller det gamla avgörandet (`epost_bar_namnform`), så rangordningen ändras inte. INV-LEADS-UTKAST-002 orört och grönt. Test: `tests/leads/test_personlig_adress.py`. Följd vid driftsättning: köade utkast till namnadresser får den fullständiga foten, och en kund utan `policy_url` får dem stoppade av regel 2 tills den är ifylld. Beslutet står i `docs/BESLUT.md` 2026-11-17.
- **Pipeline för Comp AI** i det privata repot `oloflun/comp-deploy`. Etapp 1 är bevisad (se D). Etapp 2 och 3 kräver konton och nycklar från dig: `KONTON-OCH-NYCKLAR.md` i det repot.
- **Första bygget (utan nycklar) föll, och det säger något om väg 1:** repots egen Dockerfile går inte att bygga för app och portal på den låsta commiten. Den kopierar inte in fyra interna paket som appen och portalen beror på (kontrollerat i klonen). API:t fick slut på minne på en privat körmaskin (8 GB). Din instruktion "ändra inte repot" och "följ repots instruktioner" går alltså inte att uppfylla samtidigt. Jag behåller källkoden orörd och lägger byggrecepten i pipeline-repot. Bygget är nu grönt för alla fyra images (se D).
