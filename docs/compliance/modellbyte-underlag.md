# Bytet från Gemini 2.5: underlag för ägarens beslut

Underlag 2026-11-18, framtaget av Claude (agent) inom Antons uppdrag om
EU-compliance. **Produktionen (`main`) är orörd** och kör `gemini-2.5-flash` i
Vertex `europe-west1` som förut. **Testmiljön (`development`) kör sedan
2026-11-18 provbytet** i avsnitt 6.4: textmodellerna i `eu`, bildmodellen och
inbäddningarna kvar i `europe-west1`. Koden är förberedd så att bytet blir en
ändring av variabler (avsnitt 5), och avsnitt 6 säger exakt vilka.

Läsanvisning: **Fakta** har källa (URL med hämtdatum, fil, eller en mätning i
avsnitt 3). **Bedömning** är agentens.

## 1. Rekommendation

**Bedömning.** Byt i båda miljöerna till EU-multiregionen `eu` med två
modeller:

| Steg | Variabel | Modell | Skäl (avsnitt 3) |
|---|---|---|---|
| Chatten, mejltriagen, klassare, research, Jev, leadssökningen, profilen | `MODEL` | **gemini-3.5-flash-lite** | Samma kvalitet som i dag inom bruset (support 47/50 mot 48/50, triage 47/50 mot 45/50, golden 6/7 mot 6/7), snabbare (median 4,7 s mot 8,2 s per chatt) och nästan samma pris (+9 % per chatt) |
| Iris utkast och humanizer | `LEADS_DRAFT_MODEL`, `LEADS_HUMANIZER_MODEL` | **gemini-3.8-flash** | Bäst mot utkastfacitets grind: 10/10 utan stilfynd mot 7/10 i dag, 9/10 godkända mot 5/10. Kostar ungefär +50 % per utkast till nyår och ungefär tre gånger dagens från 2027-01-01 |
| Bildbeskrivning, kvitton, webbrevisionens bildbedömning | `VISION_MODEL`, `VERTEX_BILD_REGION` | **gemini-2.5-flash i europe-west1, som i dag, tills vidare** (avsnitt 3.6 och 3.7) | Full kalibrering mot alla 58 facitsajter 2026-11-18: ingen modell klarar grinden på 85 %, inte heller dagens (2.5-flash 81 %, 3.8-flash 81 %, 3.5-flash-lite 79 % med en akut sajt på bra). 3.8 läser kvittofoton bäst men rättade ett avsiktligt felsummerat kvitto. Bildmodellen hålls kvar med en egen region (PR #76) tills ägaren väljer; 2.5 kan stängas av Google när som helst |
| Inbäddningar | `VERTEX_INBADDNING_REGION` | gemini-embedding-001 i europe-west1, som i dag | Saknas i `eu`; står inte på pensionslistan |

**Inte gemini-3.8-flash i chatten:** svaren är bäst (49/50) men medianen är
29 s per chatt mot 8 s i dag, och med dagens gräns på 20 s per steg föll 23 av
50 chattar på tidsgränsen. **Inte gemini-3.5-flash:** 5,5 gånger dagens pris
för inmatning och 4 gånger för utdata, utan bättre resultat än 3.5-flash-lite,
och det enda EU-alternativet till `eu` är Frankfurt.

Vill ägaren hålla kostnaden för utkasten nere är 3.5-flash-lite även där ett
rimligt val: 7/10 godkända och 6/10 utan stilfynd, till dagens pris (avsnitt
3.4). Det är ett val mellan pris och nivå som bara ägaren kan göra; facit
(INV-LEADS-UTKAST-002) säger att nivån ska hållas "HELA tiden".

Bytet ändrar behandlingsplatsen från europe-west1 (Belgien) till EU-
multiregionen. Det är ägarens beslut och kräver ändrad text i
underbiträdesförteckningen, DPIA:n och registerförteckningen (avsnitt 6.2).

## 2. Kandidaterna: finns de i EU, vad kostar de, hur länge lever de

### 2.1 Livslängd

Källa: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions
(dit cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions
omdirigerar), hämtad 2026-11-18.

| Modell | Släppt | Pensioneras | Googles ersättare |
|---|---|---|---|
| gemini-2.5-pro | 2025-06-17 | 2026-10-20 | gemini-3.8-flash eller gemini-3.5-flash |
| gemini-2.5-flash | 2025-06-17 | 2026-10-20 | gemini-3.8-flash eller gemini-3.5-flash-lite |
| gemini-2.5-flash-lite | 2025-07-22 | 2026-10-20 | gemini-3.8-flash, gemini-3.5-flash-lite eller Gemma 4 |
| gemini-3.8-flash | 2026-09-02 | tidigast 2027-09-02 | – |
| gemini-3.5-flash | 2026-05-19 | tidigast 2027-05-19 | – |
| gemini-3.5-flash-lite | 2026-07-21 | tidigast 2027-07-21 | – |
| gemini-3.6-flash | 2026-07-21 | 2026-11-19 | gemini-3.8-flash |

Google: datumen "won't be moved to an earlier date than what is listed". Den
listade ersättaren för gemini-2.5-flash är 3.8-flash eller **3.5-flash-lite**,
inte 3.5-flash. gemini-3.6-flash, som några äldre kommentarer i koden nämner,
pensioneras i morgon och är inget alternativ.

**gemini-2.5-flash svarar fortfarande** i europe-west1, europe-west3,
europe-west4 och europe-north1, och gemini-2.5-pro i europe-west1, -west4 och
-north1 (mätning 3.1, 2026-11-18). Det är fyra veckor efter pensionsdatumet;
Google kan stänga när som helst.

### 2.2 Var de finns: uppmätt mot projektets Vertex

Googles modellsidor, hämtade 2026-11-18:

- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-8-flash: Standard PayGo i `global`, `us` och `eu`; ingen europe-region.
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-5-flash: `global`, `us`, `eu`, `europe-west2` (London, utanför EU) och `europe-west3` (Frankfurt).
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-5-flash-lite: `global`, `us`, `eu`; ingen europe-region.

Platssidan (https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/locations,
hämtad 2026-11-18) om `eu`: värden är `aiplatform.eu.rep.googleapis.com`, och
"Multi-region endpoints let you ensure that machine learning processing of
Customer Data by the service stays within a specific jurisdictional boundary".
Samma sida: "Endpoints don't guarantee data residency or in-region ML
processing", och avrådan från `global` vid krav på behandlingsplats.

Mätt med ett syntetiskt anrop ("Svara bara med ordet OK.") genom samma
OpenAI-kompatibla ändpunkt som produktionen, med det lokala servicekontot
(`snajp-vertex`, samma projekt som drift), 2026-11-18:

| Modell | europe-west1 | europe-west3 | europe-west4 | europe-north1 | eu |
|---|---|---|---|---|---|
| gemini-2.5-flash | 200 | 200 | 200 | 200 | 404 |
| gemini-2.5-pro | 200 | 404 | 200 | 200 | 404 |
| gemini-2.5-flash-lite | 200 | 404 | 200 | 200 | 404 |
| **gemini-3.8-flash** | 404 | 404 | 404 | 404 | **200** |
| **gemini-3.5-flash** | 404 | **200** | 404 | 404 | **200** |
| **gemini-3.5-flash-lite** | 404 | 404 | 404 | 404 | **200** |
| gemini-embedding-001 (`:predict`) | 200 | 200 | – | – | 404 |

Följder:

1. Ingen ersättare finns i dagens region eller reservregioner. Bytet flyttar
   behandlingen antingen till EU-multiregionen `eu` eller, för 3.5-flash
   ensam, till Frankfurt.
2. Reservregionerna vid 429 (`europe-west4,europe-north1`) saknar alla
   kandidater. Efter bytet finns ingen reservregion; `eu` är själv en
   multiregion.
3. Inbäddningsmodellen saknas i `eu`. Den behöver inte bytas (den står inte
   på pensionslistan), men måste ligga kvar i en region där den finns:
   `VERTEX_INBADDNING_REGION=europe-west1`.
4. gemini-2.5-pro (utkasten 2026-10-16 till 2026-10-21) finns inte i
   europe-west3. Ett byte till Frankfurt kräver att utkasten också flyttar.

### 2.3 Pris

Källa: https://cloud.google.com/vertex-ai/generative-ai/pricing, hämtad
2026-11-18. USD per miljon tokens, standardnivå, upp till 200 000 tokens in.
"Icke-global" gäller regionala ändpunkter och multiregionen `eu`, som Snajp
måste använda; den är 10 % dyrare än `global`. Tänkandet debiteras som utdata.

| Modell | In | Ut | In mot 2.5-flash | Ut mot 2.5-flash |
|---|---|---|---|---|
| gemini-2.5-flash (i dag) | 0,30 | 2,50 | 1× | 1× |
| gemini-2.5-pro | 1,25 | 10,00 | 4,2× | 4× |
| gemini-3.8-flash, introduktionspris t.o.m. 2026-12-31 | 0,825 | 4,125 | 2,75× | 1,65× |
| gemini-3.8-flash från 2027-01-01 | 1,65 | 8,25 | 5,5× | 3,3× |
| gemini-3.5-flash | 1,65 | 9,90 | 5,5× | 4,0× |
| gemini-3.5-flash-lite | 0,33 | 2,75 | 1,1× | 1,1× |

Prissidan har en fotnot om "Promotional pricing provided through 50% credits
back on net spend on select models" vid 3.5-raderna; vilka modeller den gäller
står inte. Räknat utan den.

### 2.4 Samma klient, men tänkandet styrs annorlunda

Alla kandidater svarar genom samma OpenAI-kompatibla ändpunkt
(`endpoints/openapi/chat/completions`), med `google/<modell>` och JSON-läge.
Ingen ny klient behövs. Skillnaderna, uppmätta 2026-11-18 och enligt
https://docs.cloud.google.com/vertex-ai/generative-ai/docs/thinking (hämtad
samma dag):

| | gemini-2.5-flash | gemini-3.5-flash / -lite | gemini-3.8-flash |
|---|---|---|---|
| Tankebudget 0 (dagens "av") | 0 tänktokens | fungerar, men "deprecated for Gemini 3"; Google varnar för sporadiska 400 | ett av två anrop hängde i 90 s |
| `thinking_level` | 400, stöds inte | MINIMAL ger 0 tänktokens | MINIMAL ger 400; LOW lägst |
| `reasoning_effort: "minimal"` (Email Studio) | 200 | 200 | **400** |
| Grundad sökning (leadssökningen) | söker | 3.5-flash: söker (west3 och eu). 3.5-flash-lite: söker på en fråga om företag i Borlänge, inte på en allmänfråga | söker på frågan om företag (11,5 s), inte på allmänfrågan; budget 0 hängde |

Koden skickar nu rätt form per modell (avsnitt 5). Temperaturen: Google anger
1,0 som standard för 3.x; koden sätter 0,1–0,7 per steg och det är oförändrat.

## 3. Mätningarna

### 3.1 Hur, mot vad och till vilken kostnad

`scripts/mat_modellbyte.py`, lokalt, 2026-11-18. Ingen driftsatt miljö och
ingen databas: allt körs i processen mot MemoryStorage med repots egna
fixturer, och ingen kunddata skickas till någon modell.

| Mätning | Sviten (data) | Kodväg | Bedömning |
|---|---|---|---|
| Support | `evals/support_livrustning.json`, 50 fall, med kunskapsbasens ögonblicksbild `evals/kb/livrustning.json` (pilotkundens publika produktinformation) | `run_support_agent`, kanal web | `evals.bedomning.bedom_support`: utfall, fakta, inga fel, format |
| Golden | `app.agent.evals.SUPPORT_GOLDEN`, 7 fall, Nordlys (syntetisk) | `kor_support_evals` | eskaleringsbeslut, kategori, faktagrind |
| Triage | samma 50 supportfall som inkommande mejl, hela kunskapsbasen som underlag | `triage_email_llm` | eskaleringsbeslutet mot fallets utfall, och svarsutkastet mot `bedom_support` |
| Utkast (Iris) | `evals/iris_utkast.json`, de första 10 av 33 fall (påhittade bolag, `.example`-adresser) | `run_outreach_draft_v2`, struktur A | `bedom_iris` och **stilgrinden som låser facit** (INV-LEADS-UTKAST-002: `stilkontroll.kontrollera` med facitets tillåtna fynd, `amne_fynd`) |

Samma inställningar som i drift: `GEMINI_REASONING_EFFORT` osatt (`none`),
svarscachen av, stegens egna temperaturer. Kunskapsbasens sökning i
MemoryStorage är ordöverlapp, så alla kandidater får samma träffar.
Utgångsläget är dagens drift: `gemini-2.5-flash` i alla steg (utkasten på
flash sedan 2026-10-21). gemini-2.5-pro för utkasten mättes också, som
jämförelse. Varje mätning kördes en gång per kandidat. Kostnaden är räknad på
listpriserna i 2.3 och de tokens varje anrop rapporterade, med 10,5 kr per USD.
Hela mätningen kostade omkring 210 kr.

Tillgängligheten i 2.2 och tänkandet i 2.4 är separata, syntetiska prov med
ett fåtal anrop.

### 3.2 Resultat

Godkända fall. Ett fall är godkänt när alla dess kriterier håller.

| Mätning | 2.5-flash (i dag) | 3.8-flash, `eu` | 3.5-flash, `europe-west3` | 3.5-flash-lite, `eu` |
|---|---|---|---|---|
| Support, 50 fall | **48** | 27 (23 föll på tidsgränsen 20 s); **49** med gränsen 120 s | 46 | **47** |
| Golden, 7 fall | 6 (7 i en tidigare körning samma dag) | 5 (2 föll på tidsgränsen) | 6 | 6 |
| Triage, 50 fall | 45 | **49** | **49** | 47 |
| Triage: rätt eskaleringsbeslut | 45 | 50 | 49 | 48 |
| Utkast, 10 fall: godkända enligt `bedom_iris` | 5 | **9** | 0 (hälsningsraden saknas, se 3.4) | 7 |
| Utkast: utan fynd i facitets stilgrind | 7 | **10** | 8 | 6 |
| Utkast: köades (levererat) | 7 | 9 | 10 | 10 |
| Utkast: inga påhittade tal eller fakta | 9 | **10** | **10** | 9 |

Utkasten med gemini-2.5-pro (jämförelse, inte i drift sedan 2026-10-21): 4/10
utan stilfynd, 8/10 utan påhitt, 3,31 kr per utkast. Blandningen
3.5-flash-lite med 3.8-flash för utkast och humanizer: 9/10 godkända, 10/10
utan stilfynd, 10/10 köade, 1,00 kr per utkast.

Latens (median / 90:e percentil, sekunder) och kostnad per enhet:

| | 2.5-flash | 3.8-flash | 3.5-flash | 3.5-flash-lite |
|---|---|---|---|---|
| Supportchatt | 8,2 / 13,7 | 29,0 / 56,9 (gräns 120 s) | 9,6 / 16,2 | **4,7 / 6,6** |
| Triage, per mejl | 2,6 / 3,6 | 5,1 / 14,0 | 2,6 / 4,4 | **1,7 / 2,0** |
| Utkast | 20 / 31 | 33 / 62 | 18 / 27 | 14 / 14 |
| Kr per supportchatt | 0,14 | 0,39 | 0,78 | 0,16 |
| Kr per triagerat mejl | 0,044 | 0,111 | 0,230 | 0,049 |
| Kr per utkast | 0,56 | 0,83 (1,66 från 2027) | 2,24 | 0,52 |

### 3.3 Latensen och kvoten i `eu`

gemini-3.8-flash svarar på ett enkelt anrop med en kunskapsbas på 3 600
tokens på 4–6 s (2.5-flash 2–3 s), men under mätningens last blev anropen i
`eu` sega: enskilda triageanrop tog 220 s, och supportens steg slog i
chattens gräns på 20 s (`LLM_TIMEOUT_CHATT_S`) i 23 av 50 fall. Med gränsen
120 s klarade 3.8 49 av 50, med median 29 s. gemini-3.5-flash i `eu` svarade
429 (kvot eller kapacitet) på tre av tre anrop i ett separat prov, och i
europe-west3 varierade samma anrop mellan 2 och 35 s. 3.5-flash-lite i `eu`
var stabilt snabbt genom hela mätningen.

**Bedömning.** Det är delad kapacitet (Standard PayGo) i ett projekt som också
bär produktionens trafik, mätt en eftermiddag. Det går inte att skilja
modellens egen hastighet från köandet. Det räcker för att inte lägga chatten
på 3.8, och för att kontrollera kvoten före bytet.

### 3.4 Ton och format, läst för hand

Agenten läste 25 av utkasten (alla tio från 3.8-flash, sex från
3.5-flash-lite, fyra från dagens 2.5-flash, tre från 3.5-flash, två från
2.5-pro), ett urval om 12 till 25 supportsvar för 3.8-flash och
3.5-flash-lite, och fyra utvalda fall i alla modeller. Svaren ligger i
`var/modellbyte/*.json` (gitignorerad) på maskinen där mätningen kördes.

- **Support:** alla fyra skriver korrekt, kort svenska utan markdown. 3.8 och
  3.5-flash-lite svarar lika sakligt som i dag; 3.5-flash-lite är kortast.
  Vid "ont i bröstet som strålar ut i armen" skriver 3.5-flash-lite "Ring
  omedelbart 112" och lämnar över; 3.5-flash skriver i stället att den "inte
  har information om specifika nödnummer" och ber kunden kontakta sjukvården,
  vilket är en sämre formulering i ett akut läge. 3.5-flash-lite svarade en gång
  "återbetalningen görs inom 30 dagar" och lämnade sedan över en enkel
  faktafråga (tillåtet i fallet, men onödigt).
- **Utkast, 3.8-flash:** alla tio börjar "Hej," på egen rad, har en konkret
  ingång om deras kunders frågor och inga påhitt. De liknar varandra: nio av tio
  slutar med nästan samma två meningar ("Tjänsten kostar en fast
  månadsavgift." och "Vill ni veta mer är det bara att svara …"), och
  stilgrindens jämförelse mot de andra utkasten (`mot_andra`) fäller nio av tio
  på `samma_fras` eller `samma_uppmaning` (i dag sju av tio). Två
  ingångar beskriver bolaget ("Ni servar bergvärmepumpar …", "Ni bygger
  altaner …"), det omgång 12 vill undvika. Två lägger bolagsnamnet sist i en
  mening ("… genomgång för Fyrisdalens Tandvård").
- **Utkast, 3.5-flash-lite:** något fler mallingångar (`slentrian_ingang`,
  `uppraknad_ingang`), och en ingång börjar med liten bokstav efter hälsningen
  ("ni utför service …"). Minst lika varandra (3/10 med likhetsfynd).
- **Utkast, 3.5-flash och 2.5-pro:** brödtexten saknar hälsningsraden i
  resultatet, därav 0/10 i `bedom_iris`; med hälsningsregeln bortsedd håller
  3.5-flash skrivreglerna i 9/10. Ämnesrader med liten första bokstav finns
  hos alla modeller, också dagens 2.5-flash.

### 3.5 Kvoten i `eu`, kontrollerad 2026-11-18 (efter PR #74)

**Kvotlistan.** Servicekontot (`snajp-vertex`) får läsa Service Usage API
(`consumerQuotaMetrics` för `aiplatform.googleapis.com`, 398 metriker); Cloud
Quotas API är inte aktiverat i projektet (403). Det finns ingen regional kvot
för gemini-3.5-flash-lite eller gemini-3.8-flash i `eu`. De enda posterna för
modellerna är globala: 50 M inmatade tokens per minut och 5 000 M per dygn per
basmodell (`*-qcd`), standardvärdet. **Bedömning:** Standard PayGo för 3.x går
på Googles delade kapacitet (dynamisk kvot), så ett 429 beror på kapaciteten i
`eu` just då, inte på en projektgräns som går att läsa av. Därför gjordes
också ett lasttest.

**Lasttestet.** Korta syntetiska supportfrågor (inga kunddata), alla samtidigt,
mot `aiplatform.eu.rep.googleapis.com` med samma OpenAI-kompatibla ändpunkt och
tankenivå som koden (MINIMAL för 3.5-flash-lite, LOW för 3.8-flash):

| Modell | Samtidiga anrop | 429 | Median | 90:e percentil | Max |
|---|---|---|---|---|---|
| gemini-3.5-flash-lite | 20 | 0 % | 1,3 s | 1,4 s | 1,5 s |
| gemini-3.5-flash-lite | 40 | 0 % | 0,9 s | 1,0 s | 1,1 s |
| gemini-3.8-flash | 20 | 0 % | 10,2 s | 26,5 s | 27,4 s |
| gemini-3.8-flash | 40 | 0 % | 4,6 s | 11,3 s | 12,7 s |

Kvoten håller: 0 av 60 anrop per modell fick 429. 3.8-flash är fortfarande
långsam och ojämn under samtidig last (avsnitt 3.3), vilket talar för att
hålla den borta från chatten.

### 3.6 Bildmodellen (`VISION_MODEL`), mätt 2026-11-18

Två mätningar, lokalt, med repots egna fixturer. Ingen kunddata, ingen
driftsatt miljö och ingen databas. Mätskripten ligger inte i repot (de är
tunna skal kring produktionens funktioner, beskrivna nedan).

**Webbplatsbedömningen mot webbfacit.** Samma kedja som
`scripts/kalibrera_webbrevision.py` (webbsignal, platshållare,
`webbrevision.revidera`) och samma räkning: rätt sammanslaget (akut+dålig mot
bra+mycket bra), grind 85 % och ingen akut sajt på bra. Det fanns inga sparade
skärmbilder, så mätningen gjordes på ett **urval om 30 av facitets 58 sajter**
(jämnt fördelat över nivåerna i facitets ordning). Skärmbilden, PageSpeed och
sidmätningen hämtades en gång och sparades, och varje modell bedömde exakt
samma bilder (stealth-omtaget vid skymd ruta fick därför ingen ny bild för
kandidaterna; det inträffade inte för baslinjen). 50 ScrapeGraph-krediter.

| | 2.5-flash, `europe-west1` (i dag) | 3.8-flash, `eu` | 3.5-flash-lite, `eu` |
|---|---|---|---|
| Rätt sammanslaget, körning 1 | 25/30 (83 %) | 24/30 (80 %) | 25/30 (83 %) |
| Rätt sammanslaget, körning 2 | 26/30 (87 %) | 24/30 (80 %) | 25/30 (83 %) |
| Exakt rätt nivå | 16–17/30 | 16/30 | 19/30 |
| Akut på bra | 0 | 0 | 0 |
| Grinden (85 %) | underkänd / godkänd | **underkänd** | **underkänd** |
| Median per bildbedömd sajt | 16 s (ur cache) | 8,6 s | 1,2 s |

Felen:

- **Alla tre:** sagobetong.se står som avvecklad i facit men svarar nu 503 och
  blir akut i koden, före bildmodellen. Det är facit som åldrats, inte
  modellen. Räknat utan den: 2.5-flash 25–26/29 (86–90 %), 3.8-flash 24/29
  (83 %), 3.5-flash-lite 25/29 (86 %).
- **3.8-flash** är systematiskt strängare: fem sajter som facit kallar bra
  (kaminbutiken, bovikmarin, svenskparkering, bjorkmansmaleri,
  hunnebosjomack) fick 4–5, alltså dålig. Samma utfall i båda körningarna.
  I drift skulle de hamna i webbpoolen som dåliga sajter (regel 20), en
  felaktig lead till webbyråerna.
- **3.5-flash-lite** gör samma två fel som dagens modell på bra-sidan, sätter
  renovering-goteborg (dålig) på bra som 2.5-flash, och gav ett oläsbart svar
  två gånger på carauto.se (nivå okänd).

**Kvittoavläsningen.** Kvittosvitens 40 syntetiska kvitton
(`evals/kvitto.json`) skickas av evalkörningen som PDF med textlager, och då
används aldrig bildmodellen. För att mäta den renderades kvittotexterna som
bilder i två varianter, *skärmdump* (skarp PNG) och *foto* (nedskalad, lutad
2,5°, oskarp, JPEG kvalitet 55 på grå bakgrund), och lästes av produktionens
`kvitton.hanterare._las_bild` med produktionens `BILDPROMPT`. Avskriften
lästes sedan av den deterministiska tolken (`tolka_deterministiskt`), och
fälten (brutto eller utländskt belopp, momssats, datum) jämfördes med samma
tolk på originaltexten. Det mäter bara bildsteget; agentsteget (`MODEL`)
prövas inte här.

| | 2.5-flash (i dag) | 3.8-flash | 3.5-flash-lite |
|---|---|---|---|
| Skärmdump: kvitton med alla fält rätt | 40/40 | 40/40 | 39/40 |
| Foto: kvitton med alla fält rätt | 36/40 | **38/40** | 31/40 |
| Foto: fält rätt | 94/98 | 96/98 | 89/98 |
| Latens, median foto | 3,1 s | 5,7 s | 1,0 s |
| Kostnad för 80 bilder | 1,58 kr | 3,51 kr | 0,79 kr |

- **2.5-flash** tappade totalbeloppet i fyra foton (tolken fann inget belopp,
  fallet hade gått till granskning).
- **3.8-flash** läste bäst, men i `nara-dubblett-drivmedel-793` står
  "Totalt 793,00" medan raden och momsen summerar till 798,00 (avsiktligt i
  sviten). 3.8 skrev 798,00 på båda raderna: den rättade kvittot i stället för
  att skriva av det, trots att prompten säger ordagrant. Det är det farligaste
  felet av alla i mätningen, eftersom det ser rätt ut.
- **3.5-flash-lite** tappar kolumnerna i foton: belopp och rubriker hamnar på
  var sin rad, och tolken tar fel belopp (2 140 kr blev 428 kr, 2 375 kr blev
  1 900 kr) eller inget alls. En LLM-tolk efter avskriften kan rädda en del,
  det mättes inte.

**Bedömning.** Ingen kandidat klarar webbgrinden som skriptet räknar den, och
urvalet är för litet för att skilja dem åt (skillnaden mellan 3.5-flash-lite
och dagens modell är ett fall). 3.5-flash-lite är närmast dagens nivå på
webben, 3.8-flash bäst på kvitton men med ett rättat belopp. En bildmodell
behövs ändå, eftersom bildklienten anropas i `GOOGLE_CLOUD_REGION` och 2.5
saknas i `eu`. Det avgörande nästa steget är kalibreringen på alla 58 sajter
för 3.5-flash-lite och 3.8-flash (omkring 60 ScrapeGraph-krediter till, med
skärmbilderna från urvalet återanvända), och ett beslut om vilken svaghet som
väger tyngst: fel webbnivå eller fel kvittobelopp.

### 3.7 Full webbkalibrering, alla 58 facitsajter (2026-11-18)

Samma kedja och räkning som 3.6 (`scripts/kalibrera_webbrevision.py`: rätt
sammanslaget, grind 85 % och ingen akut sajt på bra), nu på **alla 58 sajter**
i `tests/leads/fixtures/webbfacit_2026-10-08.json`. Varken grinden eller facit
är ändrade. Urvalets 30 sajter återanvände sina sparade skärmbilder; de övriga
hämtades en gång under baslinjens körning (2.5-flash) och sparades, och
3.8-flash och 3.5-flash-lite bedömde exakt samma bilder utan nya hämtningar.
Stealth-omtaget vid skymd ruta hämtades därför bara där baslinjen begärde det.
Kostnad: 57 ScrapeGraph-krediter (tak 70) och omkring 10 kr i Vertex (tak 50).

| | 2.5-flash, `europe-west1` (i dag) | 3.8-flash, `eu` | 3.5-flash-lite, `eu` |
|---|---|---|---|
| Rätt sammanslaget, alla 58 | 47/58 (81,0 %) | 47/58 (81,0 %) | 46/58 (79,3 %) |
| Rätt sammanslaget, utan sagobetong.se | 47/57 (82,5 %) | 47/57 (82,5 %) | 46/57 (80,7 %) |
| Exakt rätt nivå (alla 58) | 36 | 36 | 39 |
| Akut på bra | 0 | 0 | **1** (alvegardens.se) |
| Grinden (85 %), med och utan sagobetong | underkänd | underkänd | underkänd (också på akut på bra) |
| Bra kallad dålig/akut | 4 | **9** | 4 |
| Dålig kallad bra | 5 | **0** | 4 (plus akut på bra) |
| Ingen nivå (oläsbart svar eller ingen bild) | 1 | 1 | 2 |
| Median per bildbedömd sajt | 16,9 s | 8,0 s | 1,3 s |
| Vertex-kostnad för körningen | 4,08 kr | 2,59 kr | 0,59 kr |

sagobetong.se står som avvecklad i facit men svarar 503 och blir akut i koden
före bildmodellen, i alla tre. Det är facit som åldrats; räknat utan den
ändras inget utfall.

**Felen per modell.**

- **2.5-flash** felar åt båda håll: fem dåliga sajter blev bra
  (renovering-goteborg, plums, goteborgsmaklarna, nikitek, kungstensglas) och
  fyra bra blev dåliga eller akuta (kaminbutiken, bjorkmansmaleri, wigson,
  ak-centralen som akut), driftteknik fick ingen nivå.
- **3.8-flash** felar bara åt det stränga hållet: nio sajter som facit kallar
  bra blev dåliga (kaminbutiken, bjorkmansmaleri, bovikmarin, svenskparkering,
  hunnebosjomack, vigab, bjorlandamarin, futurenautic, wigson). Ingen dålig
  sajt blev bra. I drift hade de nio hamnat i webbpoolen som dåliga sajter
  (regel 20), en falsk lead till webbyråerna, men ingen dålig sajt hade
  missats.
- **3.5-flash-lite** gör samma blandade fel som dagens modell och sätter en
  akut sajt (alvegardens.se) på bra, vilket grinden underkänner för sig.

**Bedömning.** Grinden på 85 % klaras inte av någon modell på hela facit,
inte heller av den som kör i dag; urvalet i 3.6 (83–87 % för 2.5-flash) var
alltså gynnsamt. Mellan modellerna är skillnaden i träffar ett fall. Det som
skiljer är felens riktning: 3.8 är jämnt för sträng, 2.5 och 3.5-flash-lite
felar åt båda håll, och 3.5-flash-lite gör det enda fel grinden räknar som
allvarligast. Som bildmodell efter 2.5 är 3.8-flash därför den rimligaste
kandidaten för webbedömningen, med en kalibrering av prompten mot den stränga
sidan (bra-sajterna). Det och kvittofelet i 3.6 är ägarens val; grinden och
facit är inte ändrade. Tills dess ligger bildmodellen kvar på 2.5-flash i
europe-west1 med `VERTEX_BILD_REGION` (avsnitt 6.4).

Mätskript (ej i repot, tunna skal kring produktionens funktioner): samma som i
3.6 med en kreditspärr som läser ScrapeGraph-saldot före varje ny skärmbild.

## 4. Kostnad per månad vid dagens volym

**Volymen repot känner till.** Leads: 58 körningar på 14 dygn drog 165 M
tokens, 96 % inmatning, uppmätt i development-spegeln (som också räknar mains
körningar) 2026-10-20 (`docs/BESLUT.md` 2026-10-20). Det är ungefär 354 M
tokens i månaden. Ett utkast i mätningen läste 158 000 tokens med 2.5-flash,
samma storlek som "~150 k per lead" i drift, så utkasten är huvuddelen av
leadsens tokens. Supporten och triagen har ingen uppmätt månadsvolym i repot;
de anges per 1 000. Vertex-fakturan för 6–20 oktober var 1 419 kr, varav 1 116
kr för 2.5-pro (`BESLUT.md` 2026-10-21), alltså omkring 300 kr på 15 dygn
utan pro.

**Räknat så här.** Dagens kostnad med listpris: 340 M in × 0,30 USD + 14 M ut
× 2,50 USD = 137 USD, cirka 1 440 kr i månaden. Kandidaterna skalas med den
uppmätta kostnaden per utkast mot dagens (avsnitt 3.2), eftersom den fångar
både priset, tänkandet och hur många omskrivningsvarv grinden kräver. 10,5 kr
per USD.

| Upplägg | Leads per månad | Mot i dag | Per 1 000 supportchattar | Per 1 000 triagerade mejl |
|---|---|---|---|---|
| I dag: 2.5-flash överallt | ~1 440 kr | – | 140 kr | 44 kr |
| **Rekommendationen:** 3.5-flash-lite + 3.8-flash för utkasten, till 2026-12-31 | ~2 150–2 600 kr | +700–1 150 kr | 160 kr | 49 kr |
| Rekommendationen från 2027-01-01 (3.8 dubblar priset) | ~4 300–4 900 kr | +2 900–3 500 kr | 160 kr | 49 kr |
| 3.5-flash-lite överallt | ~1 340 kr | −100 kr | 160 kr | 49 kr |
| 3.8-flash överallt, till 2026-12-31 | ~2 150 kr | +700 kr | 390 kr | 111 kr |
| 3.5-flash överallt | ~5 800 kr | +4 400 kr | 780 kr | 230 kr |

Spannet för rekommendationen kommer från två mätningar av utkasten: 3.8 i
alla steg (1,50 gånger dagens kostnad per utkast) och 3.8 bara i utkast och
humanizer (1,81 gånger, i en körning med fler omtag). Bildmodellen och
inbäddningarna ingår inte; inbäddningarna är oförändrade.

**Taket.** Leadsbudgeten är 150 M tokens per dygn och kund
(`LEADS_DAILY_TOKEN_BUDGET`, räknat som ~60 USD på flash). Med 3.8 i utkasten
blir samma tak ungefär 90–110 USD per dygn till nyår och 180–200 USD därefter.
Taket räknas i tokens, så det behöver inte ändras för att fungera, men
beloppet det skyddar blir större.

## 5. Vad som är förberett i koden (PR:en med det här underlaget)

Inga standardvärden och inga värden i drift är ändrade.

| Ändring | Var | Varför |
|---|---|---|
| `eu` på listan över tillåtna Vertex-regioner, med värden `aiplatform.eu.rep.googleapis.com` (`vertex_vard`) | `config.py`, `lib/llm/modellval.ts` (`vertexVard`, `EU_REGIONER`) | 3.8-flash och 3.5-flash-lite finns i EU bara där. `us` och `global` står fortfarande aldrig med (INV-DATA-006) |
| `VERTEX_INBADDNING_REGION` (tom = huvudregionen, som förut), kontrollerad mot samma EU-lista vid uppstart | `config.py`, `agent/embeddings.py`, `agent/llm.py` | gemini-embedding-001 saknas i `eu` |
| Tänkandet per modell: "none" blir tankebudget 0 på 2.5, MINIMAL på 3.5, LOW på 3.8; "minimal" blir "low" på 3.8 | `agent/llm.py` (`gemini_tank_kwargs`, `lagsta_tankniva`), `step_runner.py`, `leads/profil.py`, `leads/discovery.py` (`_sokningens_tankande`), Email Studio (`lagstaTankande`) | Budgeten är avvecklad för 3.x; 3.8 avvisar MINIMAL |
| Kontrollen mot fel modellfamilj gäller `LEADS_DRAFT_MODEL`, `LEADS_HUMANIZER_MODEL`, `IRIS_PROFIL_MODEL` och `VISION_MODEL`, inte bara `MODEL` | `config.py:llm_provider_fault` | Ett felstavat namn i ett stegfält gav förut 404 först hos en kund. gemini-3.x godtas överallt (prefixet `gemini`) |
| Mätverktyget | `scripts/mat_modellbyte.py` | Samma sviter, lokalt, mot vilken kandidat som helst |

Tester: `snajp-support/tests/agent/test_modellbyte_gemini3.py` (standardvärdena
orörda, gemini-3.x godtas i varje fält, fel familj fälls, tänkandet per modell,
värden och inbäddningsregionen), `tests/invariants/test_inv_data_006.py` (`eu`
godtas med sin värd, `us` aldrig, inbäddningsregionen utanför EU fäller
uppstarten), `lib/llm/modellval.test.ts`.

## 6. Så görs bytet, och så backas det

Förutsättning: den här PR:en är mergad till `development` och, för main,
med i en release (bytet kräver koden i avsnitt 5: utan den avvisar uppstarten
`eu`, och Email Studio faller på 3.8).

### 6.1 Variablerna

Tjänsten `api` (Python) läser alla; tjänsten `web` (Next, Email Studio) läser
`MODEL` och `GOOGLE_CLOUD_REGION`. Värdena nedan är rekommendationen i
avsnitt 1; byt modellnamnen om ägaren väljer annat.

| Variabel | Tjänst | I dag (osatt = kodens standard) | Efter bytet |
|---|---|---|---|
| `GOOGLE_CLOUD_REGION` | api, web | osatt (`europe-west1`) | `eu` |
| `VERTEX_RESERVREGIONER` | api | osatt (`europe-west4,europe-north1`) | tom (ingen reserv: kandidaterna finns inte i reservregionerna, inte heller i europe-west3; en tom lista betyder att 429 väntas ut i huvudregionen, `step_runner.py`) |
| `VERTEX_INBADDNING_REGION` | api | osatt (= regionen) | `europe-west1` (inbäddningsmodellen saknas i `eu`; samma modell som i dag) |
| `VERTEX_BILD_REGION` | api | osatt (= regionen) | `europe-west1` så länge `VISION_MODEL` är gemini-2.5-flash (PR #76); tom om bildmodellen blir en 3.x-modell |
| `MODEL` | api, web | `gemini-2.5-flash` | `gemini-3.5-flash-lite` (web: Email Studio) |
| `VISION_MODEL` | api | osatt (`gemini-2.5-flash`) | `gemini-2.5-flash` med `VERTEX_BILD_REGION=europe-west1` tills ägaren valt bildmodell (avsnitt 3.7); därefter den valda 3.x-modellen |
| `LEADS_DRAFT_MODEL`, `LEADS_HUMANIZER_MODEL` | api | osatta (ärver `MODEL`) | `gemini-3.8-flash` (eller osatta, då ärver de 3.5-flash-lite, avsnitt 1) |
| `IRIS_PROFIL_MODEL` | api | osatt (ärver `MODEL`) | oförändrad |
| `GEMINI_REASONING_EFFORT` | api | osatt (`none`) | oförändrad; koden översätter `none` per modell |
| `LLM_TIMEOUT_CHATT_S` | api | osatt (20 s) | oförändrad om `MODEL` blir 3.5-flash-lite; höj till 60 om `MODEL` blir 3.8-flash (avsnitt 3.3) |

Uppstarten fäller tjänsten högljutt om en region inte står på EU-listan eller
om ett modellnamn hör till fel leverantör (INV-DATA-006, `llm_provider_fault`),
så ett felskrivet värde ger en misslyckad deploy, inte tyst fel behandling.

### 6.2 Ordningen

1. **Ägaren:** godkänn behandlingsplatsen `eu` (EU-multiregionen i stället
   för Belgien) och uppdatera underbiträdesraden (bilaga 3), DPIA:n och
   registerförteckningen från "europe-west1" till "EU (Vertex multiregion eu)".
   `gemini-bedomning.md` avsnitt 6 har meningarna; bara platsen ändras.
2. **Ägaren:** kontrollera kvoten för gemini-3.x i `eu` i Google Cloud-konsolen
   (IAM och administration > Kvoter, filter "generate_content" och regionen
   `eu`). Mätningen fick 429 för gemini-3.5-flash i `eu` och långa väntetider
   för 3.8 (avsnitt 3.3). *Gjort 2026-11-18 (avsnitt 3.5): ingen regional
   kvot finns för 3.x i `eu` (delad kapacitet), och 0 av 60 samtidiga anrop
   per modell fick 429.*
3. **development:** sätt variablerna i 6.1 på `api` och `web` i miljön
   `development` (Railway). En deploy startar av sig själv. Kontrollera att
   båda tjänsterna startar (`/health/ready` på api).
4. **Mät i development** med repots evalsviter mot den driftsatta miljön,
   samma som före varje modelländring (`snajp-support/evals/README.md`):
   `python -m evals.kor kor --env development --agent alla --etikett efter-modellbyte`
   och `python -m evals.kor jamfor <före> efter-modellbyte`. Läs ett urval av
   utkasten och supportsvaren själv. Kör en Iris-körning på fem leads och läs
   utkasten (`scripts/granska_utkast.py --slug snajp --visa 5`), och en
   leadssökning: den grundade sökningen är inte mätt här (avsnitt 8).
5. **Ägaren:** godkänn main efter mätningen. Release-PR `development` → `main`
   (bär koden), därefter samma variabler på `api` och `web` i `main`.
6. Följ felloggen och Vertex-kostnaden i Google Cloud första dygnet.

### 6.3 Backa

Ta bort variablerna som sattes i 6.1 (eller sätt tillbaka de gamla värdena) på
`api` och `web` i den miljö som ska backas. Railway deployar om, och tjänsten
kör gemini-2.5-flash i europe-west1 igen, så länge Google låter 2.5 svara.
Koden behöver inte backas: med standardvärdena beter den sig som före PR:en
(testet `test_standardvardena_ar_ororda`, och tänkandet för 2.5 är oförändrat).
Kunskapsbasens vektorer påverkas inte åt något håll, eftersom
inbäddningsmodellen och dess region är desamma.

Efter att Google stängt 2.5 finns ingen väg tillbaka till 2.5; backningen
blir då ett byte till en annan 3.x-modell.

### 6.4 Provbytet i development, gjort 2026-11-18

Efter att PR #76 (`VERTEX_BILD_REGION`) deployats i development (api-deploy
`9c890642`, "Application startup complete") sattes på `api` och `web` i
miljön `development`, aldrig i `main`:

| Variabel | Värde |
|---|---|
| `GOOGLE_CLOUD_REGION` | `eu` |
| `VERTEX_RESERVREGIONER` | tom |
| `VERTEX_INBADDNING_REGION` | `europe-west1` |
| `VERTEX_BILD_REGION` | `europe-west1` |
| `VISION_MODEL` | `gemini-2.5-flash` |
| `MODEL` | `gemini-3.5-flash-lite` |
| `LEADS_DRAFT_MODEL`, `LEADS_HUMANIZER_MODEL` | `gemini-3.8-flash` |

`web` läser bara `MODEL` och `GOOGLE_CLOUD_REGION`; resten är satta där för
att de två tjänsterna ska bära samma värden. Utkasten fick 3.8-flash eftersom
underlaget visar att 3.5-flash-lite brister där (6/10 utan stilfynd mot 7/10
i dag, 3.8 10/10, avsnitt 3.2).

**Kontrollen.** Deployerna `e3d7a4f0` (api) och `011553ce` (web) blev
SUCCESS. Api:ns startlogg: "riktig agent aktiv (provider=gemini,
modell=gemini-3.5-flash-lite)" och "Application startup complete", utan
`llm_provider_fault`. Två syntetiska supportfrågor genom `POST /api/chat` mot
demotenanten (Nordlys Handel, syntetisk) med demonyckeln, `is_test`, kanal
web och en påhittad sessionsadress:

- En textfråga om leveranstider: klar på 7,2 s (10,7 s före bytet), rätt
  kategori, ingen eskalering. Loggen: chattanropen till
  `aiplatform.eu.rep.googleapis.com/.../locations/eu/...` (200) och
  inbäddningarna till `europe-west1-aiplatform.googleapis.com/.../gemini-embedding-001:predict` (200).
- En fråga med en syntetisk bild (en ritad PNG): klar på 10,6 s, kategori
  retur_reklamation. Bildbeskrivningen gick till
  `europe-west1-aiplatform.googleapis.com/.../locations/europe-west1/...` (200),
  resten till `eu`. Svaret hade ett stavfel ("behandlla"), att följa i
  mätningen i 6.2 punkt 4.

Inga fel om modell eller region i api-loggen. Inga mejl skickades, inga
utkast godkändes och ingen leadskörning startades; Iris-utkasten med 3.8 och
den grundade leadssökningen med 3.5-flash-lite är alltså inte prövade i
development än (6.2 punkt 4).

## 7. Risker

| Risk | Bedömning | Motåtgärd |
|---|---|---|
| Google stänger 2.5 innan bytet är gjort | Pensionsdatumet har passerat; en stängning ger 404 på varje anrop i båda miljöerna, och chatten, triagen och Iris står still | Gör bytet i development snarast; koden är klar |
| Behandlingsplatsen ändras från europe-west1 till EU-multiregionen | Fortfarande EU enligt Google; platssidan säger samtidigt att ändpunkter inte garanterar behandlingsplats. Dataskyddsbedömningen (avsnitt 7 punkt 1) föreslår själv `eu` | Ägaren godkänner och uppdaterar dokumenten (6.2 punkt 1) |
| Kapacitet och kvot i `eu` | 429 för 3.5-flash i `eu` i provet; 3.8-flash i `eu` gav sega svar under last (avsnitt 3.3). Ingen reservregion finns för 3.x i EU | Kontrollera kvoten före bytet; Provisioned Throughput finns för `eu` om delad kapacitet inte räcker |
| Priset på 3.8-flash dubblas 2027-01-01 | Introduktionspriset gäller sex veckor | Räknat in i avsnitt 4 |
| Utkasten låter mer lika varandra med 3.8 | Alla tio provutkast slutar med nästan samma två meningar (avsnitt 3.4). Stilgrindens `samma_fras` prövar mot kön och kan fälla dem i drift | Läs fem utkast i development (6.2 punkt 4) |
| Den grundade leadssökningen | Båda kandidaterna sökte på en syntetisk fråga om företag, men hoppade över sökningen på en allmänfråga som 2.5-flash sökte på. Bara två anrop per modell | Mät en leadssökning i development; sökmodellen är `MODEL` |
| Temperaturen | Google anger 1,0 som standard för 3.x; koden kör lägre per steg | Oförändrat; inga avvikelser syntes i mätningen |
| Ett gemensamt servicekonto och projekt för drift och mätning | Mätningen här drog på samma projekts kvot som produktionen (A8 i dataskyddsbedömningen) | Separata projekt per miljö är ägarens åtgärd sedan tidigare |

## 8. Det som inte mättes

- **Researchen, Jev och leadssökningen** (grundad Google-sökning). Ingen av
  dem har en låst svit som går att köra utan nätverk mot riktiga sajter.
  Sökningen provades med ett anrop per modell (avsnitt 2.4).
- **Kvittohanteraren och bildmodellen.** Bildsteget mättes 2026-11-18
  (avsnitt 3.6) och webbplatsbedömningen på alla 58 facitsajter (3.7).
  Kvittosvitens hela kedja (uppladdning, agent, status) kördes inte; i
  development ligger bildmodellen kvar på 2.5-flash, så den prövar inget nytt.
- **Email Studio.** Bara att anropet tar den nya tankeformen (test).
- **Spridningen.** Varje mätning kördes en gång per kandidat. Golden-svitens
  sju fall gav 7/7 och 6/7 för samma modell i två körningar samma dag, så en
  skillnad på ett eller två fall är inom bruset.
- **Volymen i supporten.** Repot har ingen uppmätt månadsvolym för chatt och
  triage, bara för leads (avsnitt 4).
- **Ingen mätning gjordes mot main**, och ingen kunddata användes. Mätningarna
  i avsnitt 3 kördes lokalt mot MemoryStorage med repots fixturer; mot
  development gjordes bara de två syntetiska anropen i 6.4, inte evalsviterna
  i 6.2 punkt 4.
