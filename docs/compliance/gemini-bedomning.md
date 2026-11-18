# Gemini på Vertex AI: håller det för GDPR och EU-kraven?

Beslutsunderlag. Skrivet 2026-11-18 av en agent på ägarens uppdrag. Inte ett rättsutlåtande.
Ägarens fråga: "Undersök även om det nuvarande läget med Google-cloud Gemini-språkmodeller är tillräckligt bra för att hålla GDPR och övriga EU compliance-standarder".

Läsanvisning. **Fakta** har källa (fil och rad, eller URL). **Bedömning** är agentens. **Jurist** betyder att frågan måste avgöras av en jurist. Googles sidor hämtades 2026-11-18, dagen efter leverantörsgranskningen (2026-11-17). Flera av Googles sidor heter nu "Gemini Enterprise Agent Platform" i stället för Vertex AI, men ligger kvar under samma adresser.

Koden lästes i arbetskatalogen (gren `compliance/overvakning`). De filer som rör Google är identiska med `origin/development` (commit `1b44c364`, 2026-11-18 00:25), utom `config.py`, där skillnaden gäller gallringen och inte Google. Radnummer i `config.py` avser arbetskatalogen; i `development` ligger raderna efter 371 femton rader längre ned.

---

## 1. Utfall

**Ja, med åtgärder.** Avtalet med Google gäller, behandlingen sker inom EU och Google tränar inte på datan. Men tre saker är verkliga brister och inte bara dokumentation:

1. **Personnummer når Google omaskerade** på två vägar: uppsägningsklassaren och inbäddningarna (avsnitt 3, A1–A2). DPIA:n och policyn säger att de maskeras.
2. **Ingen kodgrind håller anropen i EU.** En felaktig miljövariabel kan skicka kunddata till en region utanför EU eller till OpenAI i USA, och ingenting larmar (A3–A5).
3. **Gemini 2.5 har ett pensionsdatum som redan passerats** enligt Google (20 oktober 2026). Ersättaren måste nås via en EU-endpoint och aldrig via `global`.

Resten är dokumentation och inställningar: överföringsbedömning (TIA), uppdaterad DPIA, avtalsbilaga, och att stänga av Googles cache.

**Åtgärder i ordning:**
1. Agenten: maskera före varje Google-anrop, och bygg grindarna mot fel region, fel leverantör och sökgrundning på kunddata.
2. Ägaren: stäng av cachen i Google Cloud-projektet och ge varje miljö ett eget projekt och servicekonto.
3. Ägaren och agenten: verifiera att Gemini 2.5 fortfarande svarar i `europe-west1`, och prova ersättaren via EU-endpointen.
4. Ägaren beslutar TIA:n (avsnitt 4); agenten för in den i DPIA:n och avtalsbilagan (avsnitt 6).
5. Juristen granskar TIA:n, avtalsbilagan och missbruksloggningen innan första kunden skriver på.

---

## 2. Krav, läge och åtgärd

| Krav | Läge i dag | Belägg | Åtgärd | Vem |
|---|---|---|---|---|
| GDPR art. 28.1: biträdesavtal med Google | Uppfyllt. Cloud Data Processing Addendum (CDPA) gäller automatiskt via GCP-villkoren. Google är biträde | CDPA §4.1 "Google is a processor"; `leverantorsgranskning.md` avsnitt 1 | Registrera dataskyddskontakt i konsolen (frivilligt men rekommenderat). Kontrollera avtalspart på fakturan | Ägaren |
| Art. 28.2 och 28.4: underbiträde i led | Delvis. Google står i `lib/bolag.ts:142-152` och PUB-utkastet. Google meddelar nya underbiträden 30 dagar i förväg; PUB-utkastet föreslår också 30 dagar till kunden | CDPA §11.4(a); `docs/pub-avtal.md:167` | Lova kunden "utan dröjsmål och senast 14 dagar efter att Snajp underrättats", inte en fast frist som är lika lång som Googles | Agenten skriver, juristen granskar |
| Art. 28.3 c och art. 32: säkerhet | Delvis. TLS och EU-endpoint. Samma servicekonto i main, development och lokalt. Cachen på | `nulage-inventering.md` rad 121, 248; avsnitt 3 | Separata projekt och servicekonton; stäng av cachen | Ägaren |
| Art. 5.1 c och art. 25: uppgiftsminimering | **Brist.** Personnummer omaskerade till klassaren och inbäddningarna. Namn, adresser och hälsouppgifter i fritext maskeras inte alls | Avsnitt 3 | Maskera på samma ställen; överväg fler uppgiftstyper | Agenten |
| Art. 44–46: överföring | Behandlingen sker i EU, men Google LLC är amerikanskt och kan nås av amerikanska myndigheter. Mekanism: DPF och SCC | CDPA bilaga 3; Googles vitbok 2021 s. 14–15 | TIA (avsnitt 4). Ägaren beslutar | Ägaren, juristen granskar |
| Art. 35: konsekvensbedömning | **Inaktuell.** DPIA:n säger att produktionen kör simuleringsläge | `docs/dpia_supportagenten.md:90-92`; `nulage-inventering.md` rad 113 | Uppdatera med dataflödet i avsnitt 3 och TIA:n | Agenten, ägaren beslutar |
| Art. 13–14: information | Delvis. Policyn beskriver Google och 90 dagars loggning | `lib/bolag.ts:151` | Lägg till cachen och sökgrundningen (avsnitt 6) | Agenten |
| AI-förordningen art. 4 | Saknas | `ramverk/iso42001/ai-forordningen.md` | Kort utbildning och anteckning för de två i bolaget | Ägaren |
| AI-förordningen art. 50.1 | Byggt för chatt och autosvar | `ai-forordningen.md` 3.1 | Driftsätt; juristen avgör kallmejl | Ägaren, juristen |
| AI-förordningen art. 53: dokumentation från Google | Google har undertecknat uppförandekoden för GPAI. Snajp har inte begärt något | blog.google 2025-07-30 | Spara Googles modellkort och användningsvillkor för de modeller som används | Agenten |

---

## 3. Dataflödet per anropstyp

### 3.1 Vad koden gör

**Endpoint.** Alla Vertex-anrop bygger adressen `https://{region}-aiplatform.googleapis.com/v1beta1/projects/{projekt}/locations/{region}/…` (`snajp-support/app/agent/llm.py:189-197`; `snajp-support/app/agent/embeddings.py:85-104`; `snajp-support/app/leads/discovery.py:495-500`; Next-sidan `lib/llm/modellval.ts:132-137`). Regionen är `GOOGLE_CLOUD_REGION`, standard `europe-west1` (`config.py:181`). Reservregioner vid 429 är `europe-west4,europe-north1` (`config.py:187`; används i `step_runner.py:597` via `llm.py:482-497`). Ingen kod anropar `global` eller `aiplatform.googleapis.com` utan region.

**Modeller.** `MODEL` sätts i miljön och syns inte i repot. Enligt `docs/BESLUT.md:1679` och `:1783` kör main `gemini-2.5-flash` i `europe-west1`. `gemini-2.5-pro` för utkasten är borttaget sedan 2026-10-21 (`BESLUT.md:1784`). Vision: `vision_model`, standard `gemini-2.5-flash` (`config.py:207`). Inbäddningar: `gemini-embedding-001` (`config.py:189`). `lib/admin/halsa.ts:32` nämner `gemini-3.6-flash` som avläst värde; vilket värde som gäller i dag är **ej belagt**.

**Lagringsparametrar.** Koden sätter inga parametrar för cache, lagring, loggning eller filuppladdning. Ingen `cachedContent`, ingen Files-uppladdning, inga `labels`, ingen `store`. Bilder skickas inbäddade som data-URL i anropet (`agent/vision.py:32-44`, `kvitton/hanterare.py:141-155`), inte via Cloud Storage. Sökningen gav inga träffar på sådana parametrar i `snajp-support/app`. Googles cache styrs per projekt och påverkas alltså inte av koden.

### 3.2 Tabell

| Anropstyp | Kod | Vad skickas | Maskering | Vart | Lagras hos Google |
|---|---|---|---|---|---|
| Triage och svarsutkast (support) | `agent/triage.py:111-128`; `agent/support_agent.py:1211-1225` | Ämne, mejltext, kundens namn och e-post, kunskapsbasartiklar, kundens affärskontext | Personnummer maskeras i ämne och text. Namn och e-post skickas med avsikt | Vertex `europe-west1`, Gemini (chatt) | Cache i minne och på disk, högst 24 h, på som standard. Flaggade prompter upp till 90 dagar, möjlig mänsklig granskning |
| **Uppsägningsklassaren** | `support_agent.py:1199-1203` → `agent/retention_classifier.py:36-45` | **Hela kundmeddelandet** | **Ingen.** `message` skickas omaskerat | Samma | Samma |
| **Inbäddning av kundtext** | `api/triage.py:99-101`; `email_pipeline/processor.py:294, 332`; `support_agent.py:1404, 577` | Ämne och mejltext, upp till 8 000 tecken | **Ingen.** Frågan byggs av omaskerad text | Vertex `:predict`, `gemini-embedding-001`, samma region | Ej belagt om cachen gäller inbäddningar. Ingen uppgift om missbruksloggning för inbäddningar |
| Inbäddning av kunskapsbas | `api/kb.py:81`; `api/admin_profil.py:491`; `api/leads.py:1365` | Kundens artiklar | Ej relevant | Samma | Som ovan |
| Bildbeskrivning (bilagor i ärenden) | `support_agent.py:1012-1013` → `agent/vision.py:23-44` | Bilden som base64 | Går inte att maskera. Bilden lagras inte hos Snajp | Vertex, `vision_model` | Cache och missbruksloggning som för chatt |
| Kvitton och bokföringsunderlag | `kvitton/hanterare.py:141-155`; `bookkeeping/underlag.py:108-116` | Kvittobild | Ingen | Samma | Samma |
| Omformulering av utkast | `email_pipeline/omformulering.py:165-171` | Ämne, mejltext, utkast | Personnummer maskeras | Vertex chatt | Som triage |
| Leads: research, bedömning, utkast | `agent/leads_agent.py`, `leads_research_v2.py`, `leads/*` | Prospektens publika sidor, bolagsfakta, kontaktnamn, kundens erbjudande | Ingen (publika B2B-uppgifter) | Vertex chatt | Som triage |
| **Leads: sökgrundning** | `leads/discovery.py:484-530` (verktyget `google_search` rad 523), anropat från `:1814` och `:1873` | Målgrupp (bransch, SNI, ort, storlek), kundens Iris-kriterier i fritext (`:1598-1629`), eller ett bolagsnamn | Ingen. Ingen kundmejltext når hit: `google_search` förekommer bara i `discovery.py` | Vertex `generateContent` i `europe-west1` med Google Search | Frågor härledda ur prompten loggas upp till **3 dygn**, går inte att stänga av. Ingen dataresidens, CMEK, VPC-SC eller Access Transparency för funktionen |
| Email Studio (Next) | `app/api/email-studio/route.ts` → `lib/llm/modellval.ts:165-183` | Kundens utkast med namn och bolagsuppgifter | Ingen | Vertex, `GOOGLE_CLOUD_REGION` eller `europe-west1` | Som triage |

**Interna kopior hos Snajp.** Fulla prompter sparas i `agent_runs` (`agentcore/insyn.py`), inklusive sökgrundningens prompt (`discovery.py:577-588`). Det ligger hos Railway, inte Google, men omfattas av gallringen.

### 3.3 Avvikelser från "regional EU-endpoint, ingen sökgrundning på kunddata, ingen lagring utöver det oundvikliga"

| # | Avvikelse | Var | Allvar |
|---|---|---|---|
| A1 | Uppsägningsklassaren får det omaskerade meddelandet | `support_agent.py:1202`; `retention_classifier.py:40-45` | **Hög.** Personnummer går till Google trots att DPIA:n och policyn säger motsatsen |
| A2 | Inbäddningar av kundtext är omaskerade | `api/triage.py:99`; `processor.py:294, 332`; `support_agent.py:1404, 577` | **Hög**, av samma skäl. Inbäddningar har dessutom aldrig lyckats före Vertex `:predict` (`config.py:195-197`), så vägen är ny |
| A3 | Ingen kontroll att regionen ligger i EU. `GOOGLE_CLOUD_REGION=us-central1` eller en reservregion utanför EU går igenom tyst | `config.py:181, 187`; `llm.py:183-197`; `modellval.ts:173` | Medel. Kräver en felaktig variabel, men ingenting larmar |
| A4 | `LLM_BASE_URL` går före all regionlogik | `llm.py:317-318`; `config.py:168` | Medel. En satt variabel skickar chatten vart som helst |
| A5 | OpenAI (USA) är tillåten med riktig kunddata. Standardvärdet för `LLM_PROVIDER` är `openai`, och spärren gäller bara DeepSeek och Gemini utan servicekonto. På Next-sidan vinner `OPENAI_API_KEY` över Vertex | `config.py:167, 696-727`; `modellval.ts:166-169` | Medel. Leverantörsgranskningen säger "inte för kunddata" om OpenAI |
| A6 | Inget hindrar att sökgrundning byggs på kunddata i framtiden | `discovery.py:484` är en fri funktion | Låg i dag, men inget test |
| A7 | Cachen (minne och disk, 24 h) är inte avstängd | Konsolen/API; inget i repot säger att den är av | Låg risk, enkel åtgärd |
| A8 | Samma servicekonto och projekt i main, development och lokalt | `nulage-inventering.md` rad 248 | Medel (art. 32, spårbarhet) |
| A9 | Reservregionen `europe-north1` finns inte i Googles tabell för var Gemini 2.5 behandlas | Data residency-sidan; `config.py:187` | Låg. Se avsnitt 7 |

INV-DATA-004 (spärren mot AI Studio) är byggd och finns i `development`: `config.py:705-726`, `llm.py:328-360, 543-546, 579-583`, `discovery.py:503-509`, `modellval.ts:185-191`. Den stänger AI Studio-vägen för riktig data.

### 3.4 Vad Google lagrar, och hur länge (källor hämtade 2026-11-18)

| Vad | Hur länge | Var | Kan stängas av? | Källa |
|---|---|---|---|---|
| Cache i minnet | Högst 24 h | I minnet | Ja, per projekt (`cacheConfig`, `disableCache: true`, rollen `roles/aiplatform.admin`) | https://docs.cloud.google.com/vertex-ai/generative-ai/docs/data-governance |
| Cache på disk ("durable caching"), ny sedan förra granskningen | Högst 24 h. "It's stored at rest and encrypted with Google default encryption." Ingen CMEK | Inom vald plats vid regional endpoint | Ja, samma inställning | Samma |
| Missbruksloggning, Googles vanliga modeller | Flaggade prompter "for up to 90 days" | Projektets region eller multiregion | Bara undantag för kunder med Google Cloud Master Agreement. Inget självbetjäningsval | https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/abuse-monitoring |
| Mänsklig granskning | "Authorized Google employees may assess the flagged prompts" | Ej angivet var granskarna sitter | Som ovan | Samma |
| Loggning av begäran och svar | Av som standard, skrivs till kundens egen BigQuery om den slås på | Kundens projekt | Är av | data-governance |
| Sökgrundning | Frågor härledda ur prompten, upp till 3 dygn, "not linked to the customer or end users" | Ej angivet | "There is no way to disable the storage" | data-governance |
| Träning | "won't use your data to train or fine-tune any AI/ML models without your prior permission or instruction" | – | – | data-governance |

**Zero data retention enligt Google.** Det finns ingen enskild brytare. Google listar: håll loggningen av begäran och svar avstängd, stäng av cachen, använd inte sökgrundning med Google Search eller Maps (rekommenderar "Web Grounding for Enterprise" i stället), och sätt `store = false` i Interactions API (används inte av Snajp). Missbruksloggningen nämns för sig: undantag bara via Master Agreement. Källa: data-governance-sidan. **Bedömning:** Snajp kan nå allt utom missbruksloggningen och sökgrundningens tre dygn med inställningar. Ett Master Agreement är ett förhandlat avtal via Googles säljorganisation; om det är tillgängligt för en firma av Snajps storlek är **ej belagt**.

---

## 4. Överföringsbedömning (TIA) för Google Cloud – ifyllbar

Upplägg enligt EDPB:s rekommendationer 01/2020 om kompletterande åtgärder (version 2.0, juni 2021). Faktadelarna är ifyllda. Slutsatsen är ägarens.

**Uppgifter om bedömningen**
- Dataexportör: Snajp (personuppgiftsbiträde åt kunderna i supportdelen; personuppgiftsansvarig i leadsdelen).
- Dataimportör: Google. Avtalspart för kunder i EES är enligt Googles arkiverade sida (januari 2025) Google Cloud EMEA Limited, 70 Sir John Rogerson's Quay, Dublin 2, Irland. Den aktuella sidan https://cloud.google.com/terms/google-entity gick inte att läsa. **Kontrollera på fakturan:** [FYLL]. Moderbolag och DPF-deltagare: Google LLC, USA.
- Datum: [FYLL]. Gjord av: [FYLL]. Granskad av jurist: [FYLL].

**Steg 1. Vilka uppgifter, och var**
- Supportdelen: kundernas slutkunders mejl och chattar (namn, e-post, ärendetext, i undantagsfall känsliga uppgifter i fritext), bilagor och kvittobilder. Personnummer maskeras i huvudvägen men inte i alla (avsnitt 3.3, A1–A2, ska åtgärdas).
- Leadsdelen: publika bolagsuppgifter, kontaktnamn och yrkesmejl ur bolagens egna webbplatser.
- Behandlingsplats: regional EU-endpoint (`europe-west1`, reserv `europe-west4`, `europe-north1`). Google: "requests to US or EU single-region endpoints such as `us-central1` or `europe-west4` are processed within that multi-region", och EU-multiregionen "strictly covers data residency within EU member states" (https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/data-residency). Data i vila stannar i vald plats.
- **Är det en överföring alls?** Behandlingen sker i EU. Frågan är om åtkomst från ett amerikanskt moderbolag eller amerikanska myndigheter räknas som överföring. PUB-utkastet räknar det som överföring (`docs/pub-avtal.md:310-312`). **Jurist.** Bedömningen nedan utgår från att det räknas, vilket är det försiktiga antagandet.

**Steg 2. Överföringsmekanism**
- EU–US Data Privacy Framework: Google LLC står som aktiv deltagare (uppslag i dataprivacyframework.gov/list 2026-11-17, `leverantorsgranskning.md` avsnitt 1). Kommissionens adekvansbeslut (EU) 2023/1795 av den 10 juli 2023.
- Standardavtalsklausuler: CDPA bilaga 3 hänvisar till SCC (kommissionens beslut 2021/914) i modulerna Controller-to-Processor, Processor-to-Processor, Processor-to-Controller och Processor-to-Processor (Google Exporter). Enligt Googles vitbok (september 2021, s. 12) ingår Google SCC med sina underbiträden, så att kunder i EES inte behöver göra det själva.
- Underbiträden: https://cloud.google.com/terms/subprocessors. Ny underbiträde meddelas minst 30 dagar i förväg; kunden får invända genom att säga upp (CDPA §11.4).

**Steg 3. Mottagarlandets lagar och praxis**
- Google säger själv att "Google LLC may receive targeted requests relating to Google Cloud customer data under Downstream 702" (vitboken september 2021, s. 15). FISA 702 träffar alltså Google LLC.
- EO 12333: Google säger att den "does not impose obligations on Google LLC" och att data mellan regioner alltid krypteras (s. 15).
- CLOUD Act: Google säger att den inte ändrat hur företaget hanterar myndighetsbegäran om företagskunders data (Googles policyformulering, enligt sökresultat på Googles vitbok om myndighetsbegäran, februari 2022; själva vitboken **ej läst**).
- FISA 702:s giltighet i dag: källor visar korta förlängningar i april 2026 och att lagen enligt en intresseorganisation löpte ut i juni 2026, men att insamling kan fortsätta på certifieringar till mars 2027 (sekundär källa). **Aktuellt läge ej belagt.** För bedömningen: utgå från att 702 gäller.
- DPF:s rättsliga läge: tribunalen ogillade Latombes talan den 3 september 2025 (mål T-553/23). Latombe överklagade till EU-domstolen den 31 oktober 2025, mål C-703/25 P, och yrkar att adekvansbeslutet ogiltigförklaras (EUR-Lex CELEX 62025CN0703). Enligt sekundära källor var målet oavgjort i oktober 2026. **Att inget avgörande kommit per 2026-11-18 är ej belagt med primärkälla.** Om EU-domstolen ogiltigförklarar beslutet faller DPF som grund, och SCC med denna TIA blir den bärande mekanismen.

**Steg 4. Kompletterande åtgärder**
| Åtgärd | Läge |
|---|---|
| Behandling i EU-region, aldrig `global` | Görs. Kodgrind saknas (A3–A4) |
| Kryptering i transit och i vila | Google krypterar som standard (vitboken s. 4–5). Snajp: TLS via `app/tls.py` |
| Uppgiftsminimering före anrop | Personnummer maskeras i huvudvägen. Brister A1–A2 |
| Ingen lagring hos Google utöver det oundvikliga | Cachen ska stängas av (ägaren). Missbruksloggningen kvarstår |
| Avtalsåtaganden om myndighetsbegäran | Google säger att den hänvisar myndigheten till kunden, granskar begäran, försöker begränsa den och underrättar kunden om det inte är förbjudet (vitboken s. 14). **Om detta står i CDPA:s text är ej belagt**; avsnittet gick inte att läsa |
| Transparens | Googles transparensrapport för Enterprise Cloud. Vitboken 2021 säger att ingen GCP-företagskunddata lämnades ut i den då senaste perioden. Aktuella siffror **ej lästa** |
| Kundhanterade nycklar (CMEK, extern nyckelhantering) | Används inte. Gäller data i vila, inte data som modellen måste läsa i klartext. Hjälper därför inte mot åtkomst under själva behandlingen |
| EU Data Boundary (Assured Workloads) | Finns, utan extra kostnad, och "Generative AI on Vertex AI" är stödd utan begränsningar. Kräver en organisation i Google Cloud. Begränsar plats, inte amerikansk åtkomst. Används inte |

**Steg 5. Bedömning (agentens, för ägaren att ta ställning till)**
- För texten i kundmejl kan Google inte tekniskt utestängas: modellen måste läsa klartext. Skyddet vilar på (a) att behandlingen sker i EU, (b) DPF och SCC, (c) Googles åtaganden och praxis vid myndighetsbegäran, (d) att uppgifterna sällan är av intresse för underrättelsetjänst.
- Sannolikheten att en enskild svensk kundtjänsts mejl begärs ut under 702 bedöms som låg. Följden för den enskilde om det sker kan vara allvarlig om mejlet innehåller känsliga uppgifter.
- Det som Snajp själv styr och som minskar risken mest är minimeringen (A1–A2), regiongrinden och att stänga av cachen.

**Steg 6. Slutsats – ägarens beslut**
- [ ] Överföringen kan ske med DPF som grund och SCC som reserv, med åtgärderna i steg 4 genomförda.
- [ ] Överföringen kan ske först när A1–A3 är åtgärdade.
- [ ] Överföringen ska inte ske för [FYLL: kategori, t.ex. kunder inom vård eller med känsliga uppgifter].
- Omprövas: när EU-domstolen avgör C-703/25 P, när Google ändrar CDPA eller underbiträden, när modell eller region byts, och minst en gång om året. Nästa datum: [FYLL].
- Beslutat av: [FYLL]. Datum: [FYLL].

---

## 5. Inställningar och kodändringar

| # | Ändring | Var | Kräver ägarens hand? |
|---|---|---|---|
| 1 | Maskera personnummer före uppsägningsklassaren | `support_agent.py:1202`: skicka `maskera_personnummer(message)` | Nej. Agenten, med test |
| 2 | Maskera personnummer före varje inbäddning | Enklast i `agent/embeddings.py:embed_text` (rad 38), så att alla anropare får det. Cachen hos Snajp nycklas då också på maskerad text | Nej |
| 3 | Invariant: all text som lämnar huset passerar maskeringen | Nytt test i `snajp-support/tests/invariants/` som anropar klassaren, inbäddningen och triagen med ett personnummer och kontrollerar att det inte finns i anropet | Nej |
| 4 | Regiongrind: `GOOGLE_CLOUD_REGION` och varje reservregion måste finnas i en lista med EU-regioner (eller `eu`), annars vägrar tjänsten starta där data är riktig | `config.py:llm_provider_fault` (rad 651); spegla i `modellval.ts:valjModell` | Nej |
| 5 | Spärr: `LLM_BASE_URL` får inte vara satt, och `LLM_PROVIDER` får inte vara `openai`, där data är riktig. Next: `OPENAI_API_KEY` får inte vinna där data är riktig | `config.py:696-727`; `modellval.ts:166-169` | Nej i koden. Ägaren beslutar om OpenAI ska vara förbjudet för kunddata (rekommenderas) |
| 6 | Förbud mot sökgrundning med kunddata: test som fäller om `google_search` förekommer utanför `leads/discovery.py`, och att `_gemini_med_sokning` bara anropas därifrån | Nytt invariant-test | Nej |
| 7 | Fler maskeringstyper: e-postadresser och telefonnummer i löptext, bankkonto, IBAN, kortnummer (Luhn). Namn och hälsouppgifter i fritext går inte att maskera säkert med mönster; ett försök försämrar svaren | `moderation/maskering.py` | Nej, men ägaren bör godkänna eftersom svarskvaliteten påverkas |
| 8 | Stäng av cachen (minne och disk) | Google Cloud: PATCH på projektets `cacheConfig` med `"disableCache": true`. Kräver `roles/aiplatform.admin`. Gäller alla regioner i projektet | **Ja** |
| 9 | Ett projekt och servicekonto per miljö (main, development, lokalt) | Google Cloud IAM; sedan `GOOGLE_SERVICE_ACCOUNT_JSON` i Railway | **Ja** |
| 10 | Kontrollera att loggning av begäran och svar är av | Google Cloud, per modell | **Ja** (en kontroll) |
| 11 | Registrera dataskyddskontakt och kontrollera avtalsparten | Konsolen, Privacy & Security; faktureringskontot | **Ja** |
| 12 | Modellplan: Google listar pensionsdatum 20 oktober 2026 för `gemini-2.5-flash` och `gemini-2.5-pro` ("retirement timelines may be extended, they won't be moved to an earlier date"), med ersättare `gemini-3.8-flash` eller `gemini-3.5-flash`. Google listar 3.5–3.8 Flash som behandlade i EU-multiregionen. Prova ersättaren mot EU-endpointen `aiplatform.eu.rep.googleapis.com`, aldrig `global`. Grind 4 hindrar att någon tar `global` för att få en nyare modell | `llm.py:189-197` och motsvarande ställen; https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions | Ägaren beslutar modellbyte; agenten testar |
| 13 | Överväg EU Data Boundary (Assured Workloads) som organisationsspärr på plats | Kräver organisation i Google Cloud | **Ja**, och låg prioritet |
| 14 | Spara Googles modellkort och användningsvillkor för de modeller som används, som underlag enligt AI-förordningen art. 53 | `docs/compliance/` | Nej |

---

## 6. Färdiga meningar

### 6.1 Biträdesavtalet, bilaga 3 (underbiträden), rad för Google

> **Google Cloud (Vertex AI).** Avtalspart: [Google Cloud EMEA Limited, Dublin, Irland – kontrollera]. Moderbolag: Google LLC, USA.
> **Vad:** text i ärenden och chattar, bilagor och bilder, inbäddningar av text, och utkast till svar. Uppgifterna behandlas av Googles språkmodell Gemini för att klassa ärenden, söka i kundens kunskapsbas och skriva svar.
> **Var:** inom EU. Snajp anropar regionala endpoints i Belgien, Nederländerna och Finland. Behandlingen sker inom EU men inte nödvändigtvis i det land som anropas.
> **Lagring hos Google:** Google sparar inte innehållet efter svaret, med ett undantag: meddelanden som Googles automatiska säkerhetsfilter flaggar kan sparas i upp till 90 dagar inom EU och granskas av behöriga anställda hos Google för att upptäcka missbruk. Google använder inte uppgifterna för att träna modeller. [Om cachen inte är avstängd: Google kan hålla ett mellanlager av beräknad data i upp till 24 timmar för att svara snabbare.]
> **Personnummer** maskeras innan text skickas till Google. Bilder kan inte maskeras.
> **Avtal:** Google Cloud Data Processing Addendum.
> **Överföring:** Google LLC är amerikanskt och kan bli skyldigt att lämna ut uppgifter enligt amerikansk lag. Grund: EU–US Data Privacy Framework och EU:s standardavtalsklausuler. Snajps överföringsbedömning finns på begäran.

### 6.2 Biträdesavtalet, avsnitt 6.2 (ändringar av underbiträden)

> Snajp underrättar Kunden utan onödigt dröjsmål, och senast 14 dagar efter att Snajp själv fått besked, när ett underbiträde i Bilaga 3 lägger till eller byter ett eget underbiträde som får tillgång till Kundens personuppgifter. När Snajp själv lägger till eller byter ett underbiträde underrättas Kunden minst [30] dagar i förväg.

### 6.3 Integritetspolicyn (Snajps egen policy, avsnittet om språkmodellen)

> Snajp använder Googles språkmodell Gemini via Google Cloud. Text som behandlas av agenten skickas till Google för bearbetning inom EU. Google använder den inte för att träna sina modeller. Meddelanden som Googles automatiska säkerhetsfilter flaggar kan sparas i upp till 90 dagar och läsas av behöriga anställda hos Google, för att upptäcka missbruk. Google Cloud ägs av det amerikanska bolaget Google LLC. Överföringen stöds av EU–US Data Privacy Framework och EU:s standardavtalsklausuler.
>
> När vår leadstjänst söker efter bolag använder den Googles sökning. Sökfrågorna innehåller bara beskrivningar av vilka slags bolag som söks, aldrig innehåll från kunders ärenden. Google sparar sådana sökfrågor i upp till tre dygn.

### 6.4 Mallen för kundens egen information till sina kunder (`docs/kundmall_informationstext.md`)

> Vi använder en AI-tjänst från Snajp för att besvara frågor. Ditt meddelande behandlas av en språkmodell hos Google Cloud inom EU. Personnummer tas bort innan meddelandet skickas. Meddelanden som Googles säkerhetsfilter flaggar kan sparas i upp till 90 dagar.

---

## 7. Det som inte gick att belägga

1. **Om `europe-west1` och `europe-north1` räknas som "supported EU single-region endpoints" för Gemini 2.5.** Googles tabell har kolumner för EU-multiregionen och för `europe-west4`, inte för Belgien eller Finland, och för `europe-west4` är rutan för Gemini 2.5 tom. Platssidan säger "Endpoints don't guarantee data residency or in-region ML processing". Rimligast läsning är att anropet behandlas i EU-multiregionen, men det står inte uttryckligen för just dessa regioner. **Fråga Google** eller gå över till `eu`-endpointen.
2. **Om Gemini 2.5 fortfarande svarar i `europe-west1`.** Pensionsdatumet 20 oktober 2026 har passerat; `BESLUT.md` 2026-10-21 säger att europe-west1 "har kvar 2.5". Ej kontrollerat i dag (ingen inloggning). På platssidan gick tillgänglighetsrutorna för EU-regionerna inte att läsa.
3. **Vilken modell och region som faktiskt står i Railway.** Miljövariabler lästes inte.
4. **Om cachen redan är avstängd.** Kräver konsolen.
5. **Avtalspart.** Aktuell version av Googles sida om avtalsenhet gick inte att läsa; Google Cloud EMEA Limited bygger på en arkiverad version från januari 2025.
6. **CDPA:s text om myndighetsbegäran.** Avsnittet gick inte att läsa. Åtagandena i TIA:n kommer ur Googles vitbok 2021.
7. **FISA 702:s status i dag** och **utfallet i C-703/25 P.** Bara sekundära källor efter oktober 2026.
8. **Certifieringar.** CDPA §7.4 och bilaga 4 nämner ISO 27001, 27017, 27018 och SOC 2/3 för Google Cloud Platform. Att "Vertex AI Platform" och "Generative AI on Vertex AI" ingår i omfattningen bygger på sökresultat om Googles sida "services in scope" (versioner augusti 2025 och juli 2026); tabellen gick inte att läsa. ISO 42001: Google Cloud är certifierat, men om Vertex AI ingår i omfattningen är ej belagt. ISO 27701 och C5 för Vertex: ej belagt.
9. **Var de som granskar flaggade prompter sitter.** Google anger det inte. (Microsoft anger EES för Azure.)
10. **Om inbäddningar och OpenAI-kompatibla anrop omfattas av missbruksloggning och cache.** Sidorna säger "supported Gemini models" utan lista på sidan.
11. **Sökgrundningens rättsliga roll.** Google säger att loggarna inte kopplas till kunden, men inte om Google då är biträde eller självständigt ansvarig. **Jurist**, om kundens kriterier anses vara personuppgifter (normalt inte).
12. **EDPB:s yttrande 28/2024 om den som använder en modell som någon annan tränat.** Yttrandet antogs i december 2024 (EDPB:s sida: 18 december). Att det kräver en lämplig bedömning av att modellen inte tagits fram olagligt bygger på advokatbyråers sammanfattningar; primärtexten är ej läst.
13. **AI-förordningens ändring (digital omnibus).** Sekundära källor anger förordning (EU) 2026/1744, publicerad 24 juli 2026, som skjuter upp högriskkraven i bilaga III till 2 december 2027. Ej kontrollerat i EUT. Art. 4 och art. 50 sägs inte vara uppskjutna.
14. **IMY:s vägledning om molntjänster och tredjelandsöverföring.** Bara sammanfattningssidan för "GDPR vid användning av generativ AI" (5 februari 2025) är läst; rapporten själv är ej läst.

---

## Bilaga A. Kraven, kort

- **GDPR art. 28.** Biträdet får bara anlita underbiträde med den ansvariges tillstånd (28.2) och ska ålägga det samma skyldigheter (28.4). Biträdet ansvarar fullt ut för underbiträdet.
- **Art. 32.** Lämpliga tekniska och organisatoriska åtgärder, bland annat pseudonymisering och kryptering, och förmåga att återställa.
- **Art. 35.** Konsekvensbedömning när behandlingen sannolikt leder till hög risk, särskilt vid ny teknik. Det är kundens skyldighet som ansvarig; Snajp ska hjälpa (28.3 f). Snajp har en egen DPIA som underlag.
- **Art. 44–46.** Överföring kräver adekvansbeslut (45) eller lämpliga skyddsåtgärder som SCC (46). Efter Schrems II (C-311/18) ska exportören bedöma mottagarlandets lagar och vid behov vidta kompletterande åtgärder (EDPB rekommendationer 01/2020).
- **EDPB yttrande 28/2024.** Gäller främst utveckling av modeller: anonymitet prövas från fall till fall, berättigat intresse kräver trestegstest. För Snajp är den relevanta delen frågan om modellens ursprung (punkt 12 ovan). Snajp tränar inga modeller och Google tränar inte på Snajps data.
- **IMY, "GDPR vid användning av generativ AI" (5 februari 2025).** Bland punkterna: "Klargör rollfördelningen mellan personuppgiftsansvarig och personuppgiftsbiträde" och att överväga om överföring till tredje land förekommer.
- **AI-förordningen.** Snajp är leverantör av AI-system byggda på en inköpt modell för allmänna ändamål, inte leverantör av modellen (`ai-forordningen.md`). Art. 4 (AI-kunnighet) gäller sedan 2 februari 2025. Art. 50.1 (upplysning om AI) gäller sedan 2 augusti 2026. Högrisk blir aktuellt bara om en kund använder agenten inom ett område i bilaga III, till exempel kredit eller anställning (art. 25 om ändrat ändamål). Av Google kan Snajp kräva den information som art. 53.1 b och bilaga XII ålägger modelleverantörer att ge nedströmsleverantörer. Google meddelade 30 juli 2025 att man undertecknar EU:s uppförandekod för GPAI-modeller (https://blog.google/around-the-globe/google-europe/eu-ai-code-practice/).
- **NIS 2 och cybersäkerhetslagen (SFS 2025:1506, i kraft 15 januari 2026).** Bedömning: träffar inte Snajp. Lagen gäller i huvudsak medelstora och stora verksamheter (rekommendation 2003/361/EG), och Snajp har två personer. Undantagen som gäller oavsett storlek (bland annat DNS-, toppdomän- och vissa kommunikationstjänster) passar inte en SaaS-tjänst för kundtjänst. Snajps kunder kan omfattas och ställa krav i avtal.

## Bilaga B. Jämförelse med andra upplägg (orientering, inte ett byte)

| Upplägg | Säte och avtalspart | Behandlingsplats | Lagring hos leverantören | Amerikansk åtkomst | Källa |
|---|---|---|---|---|---|
| Gemini i dag | Google Cloud EMEA Ltd (Irland, kontrollera); Google LLC moderbolag | EU vid regional endpoint | Cache 24 h (av­stängbar), flaggade prompter 90 dagar, sök­grundning 3 dygn | Ja (702 enligt Google) | Avsnitt 3.4 |
| Gemini, hårdare | Samma | `eu`-endpointen eller EU Data Boundary | Cache av. 90 dagar kvar utan Master Agreement | Ja | Samma |
| Mistral (La Plateforme) | Mistral AI, Paris; fransk rätt | **Ej belagt i primärkälla**; sekundära källor säger EU som standard och Google Cloud i Irland som underbiträde | Missbruksmoderering utom vid zero data retention; villkor för det ej lästa | Inget amerikanskt moderbolag. Om underbiträdet är amerikanskt moln kvarstår frågan i det ledet | https://legal.mistral.ai/terms/data-processing-addendum (gäller från 27 juli 2026). DPA §2.3: Mistral är **självständigt ansvarig för träning av sina modeller om kunden inte väljer bort det**, och för missbruksmoderering |
| Azure OpenAI, Data Zone EU | Microsoft, USA-moderbolag | EU Data Boundary | Flaggat innehåll granskas; vid driftsättning i EES sitter granskarna i EES. Ändrad missbruksövervakning efter ansökan; för modeller släppta från 1 november 2026 upphör det alternativet | Ja | https://learn.microsoft.com/en-us/azure/ai-foundry/openai/concepts/abuse-monitoring (uppdaterad 2026-06) |
| AWS Bedrock, EU-region | Amazon, USA-moderbolag | Vald region, eller EU-profil för korsregional inferens | Lagrar inte prompter som standard; automatisk missbruksdetektering kan spara in- och utdata för vissa modeller | Ja | AWS-dokumentation via sökresultat; sidan om missbruksdetektering ej läst i sin helhet |

**Bedömning.** Ett byte är inte motiverat i dag. Azure och Bedrock har samma grundfråga som Google: ett amerikanskt moderbolag. Skillnaderna gäller lagringstider och granskarnas plats, och Googles cache går att stänga av. Mistral är den enda med europeiskt säte. Men Mistrals DPA gör Mistral självständigt ansvarigt för träning om kunden inte väljer bort det, var behandlingen sker är inte belagt i primärkälla, och underbiträdet kan vara ett amerikanskt moln. Kvaliteten på svensk text har inte jämförts. Ett byte kostar en ny utvärdering av hela agentkedjan. Det blir aktuellt om EU-domstolen ogiltigförklarar DPF, eller om en kund kräver leverantör utan amerikansk koppling. Då är Mistral det första att utreda, med frågorna ovan.

## Källor (hämtade 2026-11-18 om inget annat anges)

- Vertex AI data governance: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/data-governance
- Data residency: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/data-residency
- Platser och endpoints: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/locations
- Missbruksövervakning: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/abuse-monitoring
- Modellversioner och pensionsdatum: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions
- Säkerhetskontroller per funktion: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/security-controls
- Cloud Data Processing Addendum (senast ändrad 23 oktober 2025): https://cloud.google.com/terms/data-processing-addendum
- Google Cloud Terms of Service (senast ändrad 24 mars 2026): https://cloud.google.com/terms
- Avtalsenhet: https://cloud.google.com/terms/google-entity (inte läsbar; arkiv januari 2025 via sökning)
- EU Data Boundary: https://docs.cloud.google.com/assured-workloads/docs/control-packages/eu-regions
- Googles vitbok "Safeguards for international data transfers with Google Cloud", september 2021: https://services.google.com/fh/files/misc/safeguards_for_international_data_transfers_with_google_cloud.pdf
- GPAI-uppförandekoden: https://blog.google/around-the-globe/google-europe/eu-ai-code-practice/
- C-703/25 P: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A62025CN0703
- EDPB yttrande 28/2024: https://www.edpb.europa.eu/our-work-tools/our-documents/opinion-board-art-64/opinion-282024-certain-data-protection-aspects_en
- IMY: https://www.imy.se/publikationer/gdpr-vid-anvandning-av-generativ-ai/
- Cybersäkerhetslagen: https://lagen.nu/2025:1506
- Mistral DPA: https://legal.mistral.ai/terms/data-processing-addendum
- Azure missbruksövervakning: https://learn.microsoft.com/en-us/azure/ai-foundry/openai/concepts/abuse-monitoring
- DPF-listan (uppslag 2026-11-17, `leverantorsgranskning.md`): https://www.dataprivacyframework.gov/list
