# DPIA — supportagenten

> **UTKAST. Inte juridiskt granskat.** Dokumentet ska läsas av jurist och
> beslutas av personuppgiftsansvarig, som för det här flödet är KUNDEN, inte
> Snajp. Ingen del av det får återges för kunder som en färdig bedömning.

Konsekvensbedömning enligt artikel 35. Gäller den automatiska klassificeringen
av inkommande kundmejl, utkastgenereringen, de automatiska svaren och
eskaleringslogiken.

**Status: utkast, internt.** Uppdaterad 2026-11-17.

## Ändringslogg

- **2026-11-17, sent på kvällen:** jobbkön flyttad från Redis Cloud till
  Railways egen Redis efter ägarens beslut samma kväll. Den nås över det
  privata nätverket, och main och development har var sin databas. R8 är
  åtgärdad; kvar är den gamla Redis Cloud-databasen. Flödet, tabellen i
  avsnitt 1, avsnitt 5 och avsnitt 6 är uppdaterade.
- **2026-11-17, kväll:** driftändringar samma dag införda. Kundmejl går inte
  längre till TypeSafe: ägaren beslutade det och inkorgsklassningen via Jev är
  avstängd i main och development (R7, tabellen i avsnitt 1). TLS mot Redis
  och säkerhetskopior gick inte att slå på i nuvarande planer; två vägar
  vardera väntar på ägarens val (R8, R12). Spärren mot AI Studio och den
  kodstyrda AI-upplysningen är byggda men inte driftsatta (R1, R13).
- **2026-11-17:** uppdaterad mot driftläget. Underlag: nulägesinventeringen
  2026-11-17 (internt underlag, inte i repot; avsnitt 2–4 och 7),
  Railways driftkonfiguration och regioner hämtade samma dag
  (internt underlag), `docs/BESLUT.md` och koden på grenen
  `development` (HEAD `545dca1b`). Behandlingen och underbiträdeslistan är
  omskrivna, R1 och R6 är uppdaterade, R7–R13 är nya.
- 2026-08-24: förstautkast.

---

## 0. Behövs en DPIA alls?

Artikel 35.1 kräver en DPIA vid "sannolikt hög risk". Frågan ska ställas, inte
förutsättas.

**Argument för att den behövs:**

- Behandlingen är **systematisk och storskalig** i förhållande till kundens
  hela kundstock. Varje inkommande kundmejl passerar.
- Innehållet är **okontrollerat**. En konsument som skriver till en
  kundtjänst kan skriva vad som helst, inklusive personnummer, hälsouppgifter
  eller uppgifter om någon annan. Vi kan inte styra det och ska inte låtsas
  att vi kan.
- De registrerade är **konsumenter**, alltså den svagare parten, och de har
  inte valt Snajp. De har valt kunden.
- Ny teknik (artikel 35.1) i den mening bestämmelsen avser. Sedan 2026-09-12
  går kundmejlen till en språkmodell i drift, inte bara i prov.

**Argument emot:**

- Ingen automatiserad beslutsfattning med rättslig verkan enligt artikel 22.
  Agenten föreslår och en människa godkänner, utom i de kategorier kunden satt
  till automatiskt svar. Se avsnitt 4.

**Slutsats: DPIA görs.** Två av IMY:s förteckningskriterier är uppfyllda
(storskalighet och sårbara registrerade).

## 1. Behandlingen

| | |
|---|---|
| **Ändamål** | Klassificera inkommande kundmejl (support, lead eller ej relaterat, och ärendekategori), föreslå eller skicka ett svar grundat i kundens kunskapsbas, och lämna över till en människa när underlag saknas |
| **Personuppgiftsansvarig** | Kunden |
| **Personuppgiftsbiträde** | Snajp (enskild firma) |
| **Underbiträden** | Se tabellen nedan |
| **Kategorier av registrerade** | Kundens kunder: konsumenter och företagskontakter. Dessutom personer som nämns i mejlen |
| **Uppgifter** | Avsändarens namn och e-postadress, meddelandets fulla innehåll, bilagor och bilder (beskrivs, lagras inte), agentens svar, beslutslogg |
| **Lagringstid** | Integritetspolicyn anger 24 månader med automatisk gallring. Ingen gallring körs. Se R6 och R10 |
| **Rättslig grund** | Kundens. Normalt fullgörande av avtal eller berättigat intresse |

### Så går ett kundmejl genom systemet i dag

1. Mejlet läses från kundens brevlåda (IMAP eller OAuth) av api-tjänsten i
   Railway-miljön `main`. Inkorgsläsningen körs bara i main
   (`docs/BESLUT.md`, 2026-10-10, rad 2186–2187).
2. **Klassning.** Bara kodreglerna sorterar inkorgen. Inkorgsklassningen via
   TypeSafe (modellen Jev) är avstängd (`INKORG_JEV` av) i både main och
   development sedan 2026-11-17, genom ägarens beslut samma dag. Fram till
   dess gick avsändarens domän, ämnesraden och de första 1 500 tecknen av
   texten till Jev när kodreglerna inte avgjorde, med e-postadresser och
   telefonnummer utbytta (`email_pipeline/klassning.py:157-167`,
   `email_pipeline/processor.py:369`).
3. **Triage och svar.** Personnummer och samordningsnummer maskeras. Sedan går
   ämnesrad och meddelande till Google Vertex AI, `gemini-2.5-flash`,
   regionen `europe-west1` med reserv i `europe-west4` och `europe-north1`
   (`agent/support_agent.py:1215-1220`, `config.py:180-186`). Main och
   development kör `LLM_PROVIDER=gemini`, `MODEL=gemini-2.5-flash` (Railway,
   2026-11-17). Vertex har varit i drift i båda miljöerna sedan 2026-09-12
   (`HANDOFF-2026-09-12-VERTEX-AI.md:19-21`).
4. **Utkast eller automatiskt svar** enligt kundens inställning per kategori.
   Svaret skickas via Resend.
5. **Lagring.** Mejl, svar, beslutslogg och stegloggen med fulla promptar
   sparas i Postgres hos Railway. Pågående jobb, arbetsminne och svarscache
   ligger sedan 2026-11-17 i Railways egen Redis, som api-tjänsten når över
   det privata nätverket. Main och development har var sin Redis-databas.
   Fram till dess låg de i Redis Cloud.
6. **Spegling.** Var tionde minut kopierar ett GitHub Actions-jobb
   produktionsdatabasens rader till development (`.github/workflows/synk.yml`).

### Underbiträden och mottagare

| Leverantör | Vad som går dit | Region | Avtal (DPA/SCC) i repot | Belägg |
|---|---|---|---|---|
| **Railway** | All drift: web, api, support och Postgres med all kunddata, i två miljöer (`main` och `development`). Sedan 2026-11-17 också Redis: pågående chatt- och supportjobb med agentens svar (TTL 1 h), arbetsminne och svarscache, en databas per miljö, nådd över det privata nätverket | Amsterdam (EU), alla tjänster och volymer i båda miljöerna | Ingen bekräftelse | `railway-regioner-2026-11-17.txt`; uppstartsloggen i båda miljöerna 2026-11-17 |
| **Google Cloud, Vertex AI** | Kundmejlens text (personnummer maskerat), chattar, bildbeskrivningar, kunskapsbasens artiklar, utkast | `europe-west1`, reserv `europe-west4` och `europe-north1` | Ingen bekräftelse av Cloud Data Processing Addendum | `config.py:180-186`; `agent/llm.py:24-36`; BESLUT rad 1469-1471 |
| **Google AI Studio** (reservväg) | Samma som ovan, om servicekontot saknas i miljön. En spärr (INV-DATA-004) är byggd 2026-11-17 men inte committad eller driftsatt | Ej angiven | Inget avtal; gratisnivåns villkor | `agent/llm.py:321-336`; `GEMINI_API_KEY` satt i main och development |
| **Resend** | Utgående svar till kundens kunder; studs- och klagomålshändelser | Sändningsdomäner skapas i `eu-west-1`; bolaget är amerikanskt | Ingen bekräftelse | `EMAIL_PROVIDER=resend` i main och development; `sending_domains.py:50` |
| **TypeSafe (api.typesafe.ai), modellen Jev** | Inget sedan 2026-11-17, då inkorgsklassningen stängdes av i båda miljöerna. Före det: kundmejlens ämnesrad och text utan e-postadresser och telefonnummer, plus avsändarens domän. Det som redan skickats ligger kvar hos TypeSafe; radering är inte begärd | USA | DPA inkorporerad i Master Customer Agreement; ej belagt vilka villkor kontot accepterade | `email_pipeline/klassning.py:157-167`; `INKORG_JEV` av i main och development (2026-11-17) |
| **GitHub (Microsoft), Actions** | Produktionsdatabasens rader passerar en GitHub-hostad runner var tionde minut. Hela `.env.deploy` med databaslösenorden ligger som repo-hemligheten `ENV_DEPLOY` | Runnerns region är inte angiven. [FYLL: bekräfta region och överföringsmekanism] | Inget avtal dokumenterat | `.github/workflows/synk.yml:15-44` |
| **Development-miljön** (inte ett eget bolag, men en andra mottagarkrets) | En fullständig spegel av produktionens databas, uppdaterad var tionde minut. Används av utvecklare och AI-kodverktyg | Railway, Amsterdam | – | `CLAUDE.md` ("Development-databasen är en SPEGEL"); `synk.yml` |

**Inte längre underbiträde i drift:**

- **Supabase** är inte driftdatabas. `DATABASE_URL` pekar på Railways
  Postgres i båda miljöerna (Railway, 2026-11-17). Den gamla
  Supabase-databasen i `eu-west-1` innehåller sannolikt historisk kunddata
  från tiden före flytten. [FYLL: beslut om gallring eller dokumentation av
  den gamla databasen]
- **Redis Cloud (Redis Ltd)** är inte jobbkö sedan 2026-11-17. Fram till dess
  låg pågående jobb, arbetsminne och svarscache där, i `europe-west1`, över
  en okrypterad anslutning och i samma databas för main och development (R8).
  Den gamla databasen har kvar cache och arbetsminne tills livslängden gått ut
  eller databasen raderats. Radering och uppsägning är ägarens beslut och
  inte gjorda.
- **Render** (gamla stacken) har inget belägg för att vara avstängt. Se
  incidentloggen i `INCIDENT_RESPONSE.md`.
- **DeepSeek** spärras vid uppstart i varje miljö med riktig data
  (`config.py:609-700`). `DEEPSEEK_API_KEY` är ändå satt i main och
  development.

## 2. Nödvändighet och proportionalitet

Behandlingen ersätter en manuell genomläsning som ändå sker. Uppgifterna
behandlas alltså inte i högre grad än om en anställd läste inkorgen. Men de
behandlas **automatiskt och samlat**, av flera leverantörer, i två miljöer, och
det är den skillnaden som ska bedömas.

**Uppgiftsminimering, som den faktiskt är implementerad:**

- Bilder lagras inte efter att de beskrivits
  ([`vision.py`](../snajp-support/app/agent/vision.py)).
- Bokföringsagentens originalfiler lagras aldrig, bara en sha256-summa
  ([045](../supabase/migrations/045_bookkeeping.sql)).
- Personnummer och samordningsnummer maskeras före anropet till Vertex
  (`moderation/maskering.py`, `agent/support_agent.py:1215-1220`).
- Kundmejl går inte till TypeSafe sedan 2026-11-17 (R7).
- Ingen kunds data ska vara läsbar för en annan kund: radnivåsäkerhet i
  databasen med approllen `snajp_app` (`ARCHITECTURE_INVARIANTS.md`,
  INV-SEC-001). Verifieringen gjordes mot Supabase 2026-08-07. Ingen
  verifiering mot Railway-produktionen är hittad.

**Det som INTE minimeras:**

- Hela mejltexten går till Vertex. En hälsouppgift i löptext passerar.
- Fram till 2026-11-17 gick mejltexten också till TypeSafe, där bara adresser
  och telefonnummer togs bort. Namn, personnummer och hälsouppgifter
  passerade. Flödet är stoppat (R7).
- Stegloggen sparar hela prompten, alltså den maskerade mejltexten,
  kundminne och kunskapsbas, utan gallring (R10).
- All data finns i två fullständiga kopior: main och development (R9).

## 3. Riskerna

Skala: **sannolikhet** hög, medel eller låg; **konsekvens** hög, medel eller
låg. **Ägare:** Anton (beslut, avtal, konsoler och lösenord), agent (kod och
dokument), jurist (rättslig bedömning).

### R1 — Överföring av okontrollerat innehåll till modelleverantören

**Vad som kan gå fel:** en kund skriver sitt personnummer eller en
hälsouppgift i ett supportmejl. Texten skickas till leverantören. Är
leverantörsavtalet på en nivå som tillåter användning för produktförbättring,
eller behandlas texten utanför EU, har uppgiften lämnat vår kontroll.

**Sannolikhet:** hög att känsliga uppgifter förekommer i texten. Konsumenter
skriver personnummer i kundtjänstmejl.

**Konsekvens:** medel. Huvudvägen går nu till en betald molntjänst i EU, men
avtalet är inte bekräftat (se nedan). Hög om reservvägen till AI Studio används.

**Vad som har ändrats sedan 2026-08-24:** gratisnivån i AI Studio var
grundproblemet. Den 2026-09-12 flyttades chattvägen till Vertex AI (betald
GCP, `europe-west1`) i båda miljöerna
(`HANDOFF-2026-09-12-VERTEX-AI.md:14-21`). Simuleringsläget är borta:
produktionen kör live mot Vertex sedan dess. Main bekräftades på Vertex
`europe-west1` med `gemini-2.5-flash` 2026-10-21 (BESLUT rad 1469-1471), och
driftkonfigurationen 2026-11-17 visar `LLM_PROVIDER=gemini` och
`MODEL=gemini-2.5-flash` i main och development. Anton har avböjt att flytta
behandlingen till Vertex globala ändpunkt, som ligger utanför EU-regionerna
(BESLUT 2026-10-16, rad 2006-2009).

**Befintliga skydd:**
- Vertex i EU-regioner, styrt i kod (`config.py:180-186`).
- Personnummermaskering med datum- och Luhn-kontroll före anropet
  (`moderation/maskering.py`). Originalet ligger kvar i databasen; bara
  prompten bär en maskerad kopia.
- DeepSeek fäller uppstarten där data är riktig (`config.py:609-700`).

**Kvarstående delar:**
1. **Avtalet är inte bekräftat.** Det finns ingen bekräftelse i repot av att
   Googles Cloud Data Processing Addendum gäller för projektet.
2. **Samma servicekonto i alla miljöer.** `snajp-vertex` används i main, i
   development och lokalt hos utvecklarna
   (`HANDOFF-2026-09-12-VERTEX-AI.md:41-44`). En läckt nyckel på en
   utvecklardator ger åtkomst till samma projekt som produktionen.
3. **Reservvägen till AI Studio finns kvar.** Saknas servicekontot faller
   klienten tillbaka på `GEMINI_API_KEY` mot `generativelanguage.googleapis.com`
   (`agent/llm.py:321-336`). Nyckeln är satt i main. Den vägen har ingen
   EU-styrning och gratisnivåns villkor. BESLUT 2026-10-21 (rad 1523) säger att
   AI Studio-krediten är slut (402), men det är ingen spärr. En spärr är byggd
   2026-11-17 (INV-DATA-004): tjänsten vägrar starta med gemini utan läsbart
   servicekonto där data är riktig, och varje reservväg till AI Studio vägrar
   själv. Servicekontot i main och development klarar spärren. Den är inte
   committad eller driftsatt.
4. Maskeringen tar inte hälsouppgifter i löptext. Läs inte R1 som löst.

**Föreslagen åtgärd:** bekräfta och arkivera Googles DPA för projektet
`snajp-506221` (Anton). Skapa separata servicekonton för main, development och
lokal utveckling (Anton). Spärra AI Studio-vägen i miljöer med riktig data,
med samma mönster som DeepSeek-spärren (agent). Fyll i Vertex-regionen i
`lib/bolag.ts` och registerförteckningen (agent).

**Ägare:** Anton (avtal, servicekonton), agent (spärr, dokument).

**Status:** delvis åtgärdad. Den tekniska delen är stängd i huvudvägen.
Spärren mot AI Studio är byggd men inte driftsatt. Avtalsdelen och
separationen per miljö är öppna.

### R2 — Ett felaktigt svar går ut i kundens namn

**Vad som kan gå fel:** agenten svarar fel på ett ärende som rör pengar,
returrätt eller garanti.

**Sannolikhet:** medel utan spärrar.

**Befintliga skydd:** grundningsregeln kräver stöd i kunskapsbasen. Saknas
underlag eskalerar ärendet. Sedan 2026-11-16 prövas tal, priser, frister och
webbadresser källa för källa, och nivån Ordagrant bygger svaret i kod ur
kundens egen text (BESLUT 2026-11-16, rad 35-46; Ordagrant är inte standard
än). Utkast kräver mänskligt godkännande enligt kundens inställning per
kategori.

**Kvarstående risk:** låg, men beroende av att kunden inte sätter alla
kategorier till `auto`. Se R4.

**Ägare:** agent. **Status:** åtgärdad i kod, mätningen av Ordagrant återstår.

### R3 — Felaktig kategorisering fördröjer ett brådskande ärende

**Vad som kan gå fel:** ett ärende som borde eskalerats hamnar i fel fack och
blir liggande. Sedan 2026-10-04 kan ett supportmejl också klassas som "lead"
eller "ej relaterat" och styras bort från supportkedjan
(`processor.py:358-374`).

**Befintliga skydd:** eskaleringen är fail-open mot människa vid låg konfidens
eller ord som tyder på en upprörd kund. Sedan 2026-11-17 sorterar bara
kodreglerna; Jev är avstängd i inkorgen (R7). När Jev var påslagen fick den
bara styra bort ett mejl vid konfidens 0,9 eller mer (`klassning.py:44, 185`).
Beslutet loggas med
motivering i `ss_decision_log`.

**Kvarstående risk:** låg. **Ägare:** agent. **Status:** åtgärdad.

### R4 — Kunden sätter kategorier till automatiskt svar

**Vad som kan gå fel:** hela spärren i R2 kringgås av en inställning.

**Befintliga skydd:** defaulten är `draft` för varje kategori. `/villkor`
säger att autonominivån är kundens val och ansvar, med hänvisning till
artikel 22. `AUTO_SEND_MIN_CONFIDENCE` är satt i main.

**Kvarstående risk:** medel, och den ligger hos kunden. Automatiska svar är
också det fall där AI-upplysningen i R13 saknas.

**Ägare:** kunden; agent för texten. **Status:** åtgärdat i villkoren
(ogranskat).

### R5 — Den registrerade vet inte att en AI läser mejlet

**Vad som kan gå fel:** en konsument skriver till en kundtjänst och antar att
en människa läser. Informationsplikten enligt artikel 13 ligger på **kunden**,
som är personuppgiftsansvarig.

**Befintliga skydd:** kravet står i `/villkor` under Kundens ansvar. En
textmall finns ([`kundmall_informationstext.md`](kundmall_informationstext.md)).
Chattwidgeten har en dataskyddsflik (`components/snajp/AgentMenu.tsx`).

**Brist:** mallen nämner "[leverantör]" och har inte fyllts i med Google
eller Resend. Onboardingen lämnar inte ut mallen
(`scripts/onboard_tenant.py`).

**Kvarstående risk:** medel, och den är kundens.

**Ägare:** agent (mall och onboarding), kunden (texten på sin sajt).
**Status:** delvis åtgärdad.

### R6 — Överlagring: data ligger kvar för alltid

**Vad som kan gå fel:** kundmejl, svar och loggar ligger kvar utan slut.

**Sannolikhet:** hög. Inget gallras i dag.

**Konsekvens:** medel. Hög som efterlevnadsfråga, eftersom integritetspolicyn
lovar något annat (art. 5.1 a och 13.2 a).

**Befintliga skydd:** gallringsmekanismen finns
([048](../supabase/migrations/048_gallring.sql), [`gallra.py`](../scripts/gallra.py)),
med torrkörning som standard.

**Brister:**
- Integritetspolicyn säger att uppgifterna sparas i 24 månader och att
  "Gallringen är automatiserad och loggas"
  (`app/integritetspolicy/IntegritetspolicySida.tsx:87-89`). Det stämmer inte.
- Inget gallringsjobb är schemalagt. `gallra.py` är "tänkt som ett
  Railway-cronjobb" (rad 25-28), och inget arbetsflöde i `.github/workflows/`
  kör det. Inget belägg för att `--satt-policy` körts för någon kund.
- Gallringen omfattar bara `ss_emails` med kaskad, inte `agent_runs`, chattar,
  kundminne eller kopiorna i development, Redis och den gamla Supabase-databasen.

**Föreslagen åtgärd:** besluta perioden och sätt den per kund (Anton).
Schemalägg gallringen i båda miljöerna och utöka den till `agent_runs` och
chattar (agent). Tills dess: rätta integritetspolicyn så att den säger vad som
faktiskt gäller (agent, med Antons ja).

**Ägare:** Anton (period), agent (jobb och policytext).
**Status:** öppen. [FYLL: beslutad lagringstid för supportdata]

### R7 — TypeSafe fick kundmejlens text utan godkännande

**Vad som gick fel:** fram till 2026-11-17 gick varje nytt kundmejl som
kodreglerna inte sorterade till TypeSafe (`api.typesafe.ai`) för klassning.
Leverantören stod inte i någon underbiträdesförteckning och var aldrig
godkänd. Namn, personnummer och hälsouppgifter i texten passerade, eftersom
bara adresser och telefonnummer togs bort.

**Sannolikhet:** stoppad. Ägaren beslutade 2026-11-17 att kundmejl inte ska gå
till TypeSafe, och `INKORG_JEV` är av i main och development sedan samma kväll.
Nya deployer kom upp och hälsokontrollerna svarar ok. Före stoppet var
`INKORG_JEV=auto` satt i båda miljöerna.

**Konsekvens:** hög. Det var en överföring av kundens kunders uppgifter till
ett underbiträde som kunden inte godkänt (art. 28.2), möjligen till tredje
land (kapitel V).

**Motsägelse i beslutsunderlaget, som ägaren måste avgöra:**
- `leads/jev.py:24-28` anger Antons beslut 2026-09-30: Jev ser aldrig
  kundens egna data, kundmejl eller ärenden.
- `email_pipeline/klassning.py:23-30`, skriven 2026-10-04, hänvisar till
  samma beslut men inför brytaren `INKORG_JEV`, där läget `auto` skickar varje
  nytt kundmejl till Jev, med adresser och telefonnummer borttagna.
- Standardvärdet är `off` (`config.py:343`). Någon har satt `auto` i båda
  miljöerna. Vem och när framgår inte av `docs/BESLUT.md`.

Ägaren avgjorde motsägelsen 2026-11-17: kundmejl går inte till TypeSafe
(`docs/BESLUT.md`).

**Befintliga skydd:** inkorgsklassningen via Jev är avstängd i båda
miljöerna. Inkorgen sorteras bara av kodreglerna. Slås den på igen ska
underbiträdeslistan i `lib/bolag.ts` ändras först.

**Kvarstående:**
1. Kundmejltext som skickades före stoppet ligger kvar hos TypeSafe enligt
   deras villkor. Radering och bekräftelse är inte begärda.
2. Leverantören godkändes aldrig innan den fick kunddata. Bedömning av
   anmälningsplikt och underrättelse till berörda kunder är ägarens
   (incidentloggen, 2026-11-17).
3. TypeSafe används fortfarande i leadsdelen, utan kundmejl (Bilaga 3 i
   PUB-utkastet).

**Ägare:** Anton (radering, bedömning, underrättelse), jurist (bedömning av
överföringen). **Status:** flödet stoppat 2026-11-17; följderna är öppna.

### R8 — Redis utan TLS, delad mellan main och development

**Vad som gick fel, fram till 2026-11-17:** pågående jobb med agentens svar
till kunderna, arbetsminne och svarscache gick okrypterat mellan Railway och
Redis Cloud. Main och development använde samma Redis-databas, så nycklar från
spegelmiljön och produktionen låg i samma lagring.

**Sannolikhet före flytten:** medel. Trafiken gick över publikt nät mellan två
leverantörer (Railway i Amsterdam, Redis Cloud i `europe-west1`).

**Konsekvens:** medel. Uppgifterna har kort livstid (jobbposter TTL 1 h enligt
`JURIDIK_ATGARDER.md:351`), men de är kundsvar i klartext.

**Belägg före flytten:** `REDIS_URL` började med `redis://` och pekade på samma databas i main och development
(Railways driftkonfiguration 2026-11-17, internt underlag). TLS konstaterades
avstängt 2026-08-29 (`HANDOFF-2026-08-29-REDIS-OCH-FASERNA.md:112-115`). Ingen
`rediss://` finns i appkoden.

**Skydd före flytten:** Redis-databasen låg i EU. Lösenordsskydd.

**Varför TLS inte slogs på:** Redis Cloud-databasen låg på gratisplanen, och
den planen saknar TLS-stöd. Skriptet `scripts/redis_tls_pa.py` byter dessutom
bara adressen i development; det är inaktuellt och får inte köras.

**Åtgärd 2026-11-17:** två vägar fanns: (a) en betald plan hos Redis Cloud
och sedan krypterad anslutning, eller (b) jobbkön flyttad till Railways egen
Redis på det privata nätverket. Ägaren valde (b) samma kväll
(`docs/BESLUT.md`). Development använder sin befintliga Redis-tjänst hos
Railway. I main skapades en ny Redis-tjänst hos Railway med samma uppsättning
(lösenord, egen volym, Amsterdam, ingen publik adress). Api-tjänsten i båda
miljöerna når Redis över det privata nätverket. Uppstartsloggen i båda
miljöerna visar att jobbkön, svarscachen, chattströmmen och leadsströmmen kör
mot Redis, och hälsokontrollen svarar ok. Trafiken går alltså inte längre över
publikt nät, och main och development har var sin databas. Pågående jobb och
cache i den gamla databasen följde inte med.

**Kvarstående:** den gamla Redis Cloud-databasen har kvar cache och
arbetsminne från tiden före flytten, tills livslängden gått ut eller databasen
raderats. Att radera den och säga upp kontot är ägarens beslut och inte gjort.
Den gamla adressen ligger kvar i en reservvariabel på api-tjänsten, så att
flytten går att backa; den tas bort när flytten fått gå några dagar.

**Ägare:** Anton (radering av den gamla databasen), agent (reservvariabeln).
**Status:** åtgärdad 2026-11-17 genom flytten; kvar är den gamla databasen.
Incidentloggen har en post.

### R9 — Development är en fullständig spegel av produktionen

**Vad som kan gå fel:** all kunddata finns i en andra miljö med fler
åtkomstvägar och svagare skydd än produktionen.

**Sannolikhet:** hög att uppgifterna läses av fler än produktionen kräver.
Utvecklare och AI-kodverktyg läser development-databasen i arbetet (till
exempel räkningar i BESLUT 2026-11-16, rad 83-89, och 2026-11-15, rad 147-150).

**Konsekvens:** hög. Spegeln innehåller kundmejl, ärenden och kontaktuppgifter
för alla kunder.

**Belägg:**
- Synken kopierar main till development var tionde minut via GitHub Actions
  (`.github/workflows/synk.yml:1-17`; BESLUT 2026-10-17, rad 1855-1860). Data
  passerar en GitHub-hostad runner. Hela `.env.deploy` ligger som
  repo-hemligheten `ENV_DEPLOY` (`synk.yml:34-39`). Synkloggen sparas som
  artefakt i 14 dagar (`synk.yml:45-50`); vad den innehåller är inte
  kontrollerat.
- Kundernas integrationsnycklar ligger i klartext i development (BESLUT rad
  390 och 433-434).
- Development har en nyckel som skriver till produktionens api
  (`FLYTT_MAL_URL` pekar på main, `FLYTT_NYCKEL` är satt; BESLUT rad 430-434).
- Fram till 2026-11-17 var `INKORG_JEV=auto` satt också i development, så
  Provsortera där skickade kundmejltext till TypeSafe (`api/inbox.py:515-530`).
  Den är av sedan dess (R7).

**Befintliga skydd:**
- Development skickar inga leadsutskick så länge spegeln står i läget
  `envags` (`leads/scheduler.py:655-672, 730-734`; BESLUT 2026-10-17, rad
  1862-1866, och 2026-11-16, rad 134-135). Om markören är satt just nu är inte
  kontrollerat här.
- Inkorgsläsning, uppföljningar och autopilot körs bara i main (BESLUT
  2026-10-10, rad 2186-2187).
- Projektreglerna förbjuder att peka en lokal utvecklingsserver mot development
  och kräver samma sekretess som för produktionen (`CLAUDE.md`).
- Sökmotorindexering av development är avstängd (`app/robots.ts`).

**Föreslagen åtgärd:** Anton beslutar om spegeln ska minimeras eller
pseudonymiseras (till exempel maskerade mejladresser och mejltexter). Kryptera
kundnycklarna i development (agent, kräver migration). Ge AI-kodverktyg en
uttalad regel för vad de får läsa ur spegeln (Anton). Beskriv spegeln i
registerförteckningen och PUB-utkastet (agent).

**Ägare:** Anton (beslut), agent (genomförande). **Status:** öppen.

### R10 — Fulla promptar med persondata i `agent_runs`, utan gallring

**Vad som kan gå fel:** varje modellanrop bokförs med hela prompten och
svaret. Det blir en andra, sökbar kopia av kundmejlen (maskerade på
personnummer), kundminne och kunskapsbas, utan slutdatum.

**Sannolikhet:** hög. **Konsekvens:** medel.

**Belägg:** `agentcore/insyn.py:56-85` sparar `user_message` (prompten) och
`raw_output` (upp till 60 000 tecken). `agent/step_runner.py:373` gör samma
sak för stegen. Gallringen i migration 048 rör inte tabellen. Fram till
2026-11-10 lämnades samma stegtexter ut i jobbsvaret (se incidentloggen).

**Befintliga skydd:** stegtexterna lämnas inte längre ut till kunden
(`api/stegtexter.py`). RLS per kund.

**Föreslagen åtgärd:** gallra `agent_runs` efter en kort, beslutad period, och
överväg att spara bara metadata efter en vecka (Anton beslutar perioden, agent
bygger). [FYLL: lagringstid för stegloggar]

**Ägare:** Anton, agent. **Status:** öppen.

### R11 — Gallringen körs inte trots att policyn lovar 24 månader

Se R6. Risken står som egen punkt eftersom den är ett felaktigt löfte till de
registrerade, inte bara en överlagring. Integritetspolicyn är publik och
beskriver en automatiserad, loggad gallring som inte finns.

**Sannolikhet:** säker (pågående). **Konsekvens:** medel.
**Föreslagen åtgärd:** rätta policytexten eller schemalägg gallringen före
första betalande kund. **Ägare:** Anton beslutar, agent genomför.
**Status:** öppen.

### R12 — Ingen dokumenterad backup- och återställningsrutin

**Vad som kan gå fel:** en databas går förlorad eller skadas, och kundmejl och
ärenden kan inte återställas (art. 32.1 c). Det motsatta problemet finns också:
okända säkerhetskopior lever kvar efter gallring.

**Sannolikhet:** låg till medel. 2026-10-17 kraschade development-databasen när
volymen blev full under synken (BESLUT rad 1872-1875).

**Konsekvens:** hög.

**Belägg:** inget belägg hittat för backuprutin, PITR eller återställningsprov
i `DEPLOY.md`, `docs/` eller `scripts/`. Pilotavtalets "[X] dagar" för
säkerhetskopior är oifyllt (`docs/pilotavtal.md:132-133`). Synken sparade en
kopia före första synken (BESLUT rad 2218).

**Varför det inte åtgärdades 2026-11-17:** Railway kräver Pro-planen för både
schemalagda och manuella säkerhetskopior av volymer, och kontot ligger på en
lägre plan. Produktionsdatabasen har fortfarande ingen säkerhetskopia.

**Föreslagen åtgärd, två vägar (ägaren har inte valt):**
- (a) Uppgradera Railway till Pro och slå på dagliga, veckovisa och månatliga
  kopior.
- (b) Ett eget schemalagt jobb som tar en databasdump till en lagringsplats i
  EU.

Oavsett väg: dokumentera rutinen och gör ett återställningsprov mot en lokal
stack (agent). [FYLL: backupintervall och lagringstid för säkerhetskopior]

**Ägare:** Anton (val av väg), agent. **Status:** öppen.

### R13 — AI-förordningen art. 50: ingen kodstyrd AI-upplysning

**Vad som kan gå fel:** en konsument får ett automatiskt mejlsvar eller ett
chattsvar utan att få veta att det kommer från ett AI-system. Art. 50.1 gäller
från 2026-08-02 och kräver upplysning när det inte är uppenbart.

**Sannolikhet:** hög i läget `auto` och i chatten. **Konsekvens:** medel.

**Belägg:** systemprompten säger "Du behöver inte inleda varje svar med att du
är en AI-assistent, men du får aldrig påstå eller antyda att du är en
människa" (`agent/support_systemprompt.py:159-162`). Det är en instruktion
till modellen, inte en spärr. Ingen kodstyrd AI-rad i chattens första svar
eller i automatiskt skickade mejlsvar är hittad. Widgetens meny talar om
"Snajp-agenten" (`components/snajp/AgentMenu.tsx`).

**Föreslagen åtgärd:** en fast AI-rad, byggd i kod, i chattens första svar och
i varje automatiskt skickat mejlsvar (agent). Jurist bedömer om ett utkast som
en människa godkänt också omfattas, och vem av Snajp (leverantör) och kunden
(tillhandahållare) som bär skyldigheten.

**Läge 2026-11-17:** AI-upplysningen i chatt och automatiska mejl är byggd
(INV-AI-001) men inte committad eller driftsatt.

**Ägare:** agent, jurist. **Status:** öppen tills spärren är driftsatt.

## 4. Artikel 22 — automatiserat beslutsfattande

Artikel 22 gäller beslut som "enbart" grundas på automatisk behandling och som
har rättsliga följder eller på liknande sätt i betydande grad påverkar
personen.

**Bedömning: artikel 22 är inte tillämplig**, av två skäl som båda måste
gälla:

1. Utkast kräver mänskligt godkännande enligt kundens inställning per
   kategori. Den mänskliga inblandningen är reell, inte en formalitet.
2. Att besvara en supportfråga har inte rättslig verkan och påverkar inte i
   betydande grad.

**Men punkt 1 beror på en inställning kunden kan ändra** (R4). Sätter kunden
en kategori till `auto` blir behandlingen helt automatisk i den kategorin, och
då ska bedömningen göras om för de ärenden som rör pengar, returer eller
avtal. Klassningen i R3 avgör dessutom automatiskt om ett mejl alls når
supportkedjan; den har ingen rättslig verkan men ska nämnas för juristen.

## 5. Samlad bedömning

Med åtgärderna i avsnitt 3 bedöms restrisken som **acceptabel för R2, R3 och
R5**.

**Restrisken är inte acceptabel i dag för R7, R9 och R11**, och **inte
fastställd för R1**:

- **R7** var en pågående överföring av kundmejltext till ett underbiträde som
  aldrig godkänts. Flödet stoppades 2026-11-17; kvar är det som redan
  skickats och bedömningen av följderna.
- **R1** är tekniskt flyttad till en betald tjänst i EU, men avtalet är inte
  bekräftat och reservvägen till gratisnivån finns kvar.
- **R9** gäller säkerheten kring hela kunddatan, inte ett enskilt flöde.
  R8 hörde hit fram till 2026-11-17, då jobbkön flyttades till Railways
  privata nätverk; kvar är att radera den gamla Redis Cloud-databasen.
- **R11** är ett felaktigt löfte i en publicerad text.

Förhandssamråd med IMY enligt artikel 36 bedöms **inte** krävas, förutsatt att
R1 och R7 stängs. Krävs ett samråd är det kunden som ska begära det, i egenskap
av personuppgiftsansvarig.

## 6. Öppna punkter

- [ ] R1: Googles DPA bekräftad för projektet; separata servicekonton per
      miljö; AI Studio-vägen spärrad där data är riktig
- [x] R1: chattvägen flyttad från AI Studios gratisnivå till Vertex
      `europe-west1` (2026-09-12)
- [ ] R6/R11: retentionsperiod beslutad, gallring schemalagd, policytexten
      sann. [FYLL: lagringstid]
- [x] R7: Anton avgjorde motsägelsen 2026-11-17; `INKORG_JEV` av i main och
      development
- [ ] R7: radering begärd hos TypeSafe; anmälningsplikt och underrättelse
      bedömda
- [x] R8: jobbkön flyttad till Railways egen Redis över det privata
      nätverket, en databas per miljö (väg b, ägarens val 2026-11-17)
- [ ] R8: den gamla Redis Cloud-databasen raderad och kontot uppsagt
      (ägarens beslut); reservvariabeln med den gamla adressen borttagen
- [ ] R9: beslut om minimering av development-spegeln; kundnycklar krypterade
- [ ] R10: lagringstid för `agent_runs` beslutad och gallrad
- [ ] R12: backup- och återställningsrutin dokumenterad och provad (väg a
      eller b, ägarens val)
- [ ] R13: kodstyrd AI-upplysning i chatt och automatiska mejlsvar (byggd,
      inte driftsatt)
- [ ] Underbiträdeslistan i `lib/bolag.ts`, registerförteckningen och
      pilotavtalets Bilaga 1 rättad mot tabellen i avsnitt 1
- [ ] Railways och Resends DPA bekräftade
- [x] R4: kundens ansvar för autonominivån inskrivet i villkoren
- [x] R5: textmall till kunden för deras egen informationstext
- [ ] R5: mallen ifylld med de faktiska leverantörerna och utlämnad vid
      onboarding
- [x] Maskering av personnummer före modellanropet till Vertex
- [ ] Läst av jurist
- [ ] Beslutad av kunden som personuppgiftsansvarig
