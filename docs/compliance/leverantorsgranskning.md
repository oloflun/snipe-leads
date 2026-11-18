# Leverantörsgranskning – underbiträden och närliggande leverantörer

Uppdragsgivare: Snajp (enskild firma). Granskningsdatum och hämtdatum för samtliga källor: **2026-11-17**.
Metod: endast läsning av leverantörernas officiella publika sidor (villkor, DPA, underbiträdeslistor, dokumentation, trust center). DPF-status slogs upp direkt i deltagarlistan på dataprivacyframework.gov/list 2026-11-17. Inga konton har skapats och inga avtal har accepterats. Där en uppgift inte gick att belägga står det "ej belagt" och var jag letade.

Förkortningar: DPA = personuppgiftsbiträdesavtal (Data Processing Addendum), SCC = EU:s standardavtalsklausuler (beslut 2021/914), DPF = EU-U.S. Data Privacy Framework, ZDR = zero data retention, PUB = personuppgiftsbiträdesavtal mellan Snajp och kund.

## Sammanfattande tabell

| # | Leverantör | Roll | DPA ingås | Data/region | Tredjeland | Bedömning | Åtgärd i korthet |
|---|---|---|---|---|---|---|---|
| 1 | Google Cloud – Vertex AI | Underbiträde | Automatiskt via GCP-villkoren | EU-multiregion vid europe-west1/-west4/-north1 (inte landsnivå) | DPF (Google LLC aktiv) + SCC | Grön/gul | Aldrig `global`-endpoint; ingen Google Search-grounding på kundmejl |
| 2 | Google AI Studio / Gemini API | Underbiträde (bara betald nivå) | DPA endast för betalda tjänster | Kan cachas "i vilket land som helst" | DPF + SCC | Röd för kundmejl | Stäng av som reserv för kunddata, eller säkerställ betald nivå |
| 3 | Railway | Underbiträde | **Kräver DocuSign-underskrift** | EU West Metal (Amsterdam); moln-"burst" till GCP/AWS förekommer | DPF (aktiv) + SCC | Gul | Signera DPA; begär skriftligt besked om infrastruktur i EU West |
| 4 | Redis Cloud | Underbiträde | Automatiskt via Redis Cloud Agreement §5.3 | GCP europe-west1 (Snajps val) | SCC; Redis EMEA Ltd (UK) | Gul | Verifiera betald plan + TLS påslaget |
| 5 | Resend | Underbiträde | Automatiskt via villkoren | Sändning eu-west-1, **lagring av innehåll och loggar i USA** | DPF ("Re-certification under Review") + SCC | Gul | Redovisa USA-lagring i PUB-bilagan; TIA |
| 6 | ScrapeGraphAI | Underbiträde (leads) | Ingen publicerad DPA, "kontakta oss" | USA | Ej angiven; ej DPF | Gul | Endast betald plan; begär DPA |
| 7 | TypeSafe (Jev) | Underbiträde | Via Master Customer Agreement (inkorporerad) | USA (AWS, Modal, Nebius, CoreWeave m.fl.) | SCC i DPA; **ej DPF** | **Röd** | Stoppa kundmejltext till Jev tills villkor åtgärdats |
| 8 | GitHub | Underbiträde (Actions-synk) | DPA bara för Team/Enterprise/Copilot | Runners i Azure, region ej angiven | DPF (aktiv) + SCC | Gul/röd | Flytta synken från Actions eller kontrollera plan |
| 9a | Supabase | Underbiträde (avvecklas) | Automatiskt via villkoren | eu-west-1 | SCC | Gul | Radera projektet, begär bekräftelse |
| 9b | Render | Underbiträde (avvecklas) | Automatiskt via ToS | ej belagt | DPF (aktiv) + SCC | Gul | Radera tjänster, begär bekräftelse |
| 10a | Loopia | Ansvarig för domän/DNS (biträde för hosting) | PUB-bilaga till allmänna villkor | Sverige | Ingen | Grön | Ingen |
| 10b | Cal.com | Underbiträde (om demobokning) | Gäller alla konton via avtalet | ej belagt | DPF (aktiv) + SCC | Grön/gul | Bara om tjänsten används |
| 10c | Google / Microsoft Entra som inloggning | Självständigt ansvariga | Ingen DPA för inloggningen | EU Data Boundary (Entra) | DPF | Grön | Notera i integritetspolicyn |
| 11 | Trigger.dev Cloud | Underbiträde (Comp) | Automatiskt via användning | Körning kan vara eu-central-1, **lagring påverkas inte av region** | SCC; API Hero Ltd (UK) | Gul | Självhosta eller håll payloads fria från persondata |
| 12 | Vercel AI Gateway | Underbiträde (Comp) | DPA för Pro/Enterprise | Vercel lagrar inte prompts | DPF (aktiv) + SCC | Gul | Pro/credits + slå på ZDR och "Disallow Prompt Training" |
| 13a | OpenAI API | Underbiträde (Comp) | Accepteras genom användning | USA; EU-residens bara för godkända | SCC; ej funnen i DPF | Gul | OK för Comp-data; inte för kunddata |
| 13b | Anthropic API | Underbiträde (Comp) | Inkorporerad i Commercial Terms | USA/global; ingen EU-inferens förstapart | SCC; ej funnen i DPF | Gul | OK för Comp-data; inte för kunddata |
| 14 | Firecrawl | Underbiträde (Comp) | DPA bara Enterprise | USA | Ej angiven; ej funnen i DPF | Gul | Skicka inga persondata; bara publik leverantörsinfo |
| 15 | AWS S3 eu-north-1 | Underbiträde (Comp-filer) | Automatiskt via Service Terms | Vald region | DPF (Amazon.com Inc. aktiv) + SCC | Grön | Ingen |

---

## A. Underbiträden i Snajps drift

### 1. Google Cloud – Vertex AI (Gemini 2.5 Flash/Pro, embeddings, vision)

- **Juridisk person:** Google Cloud Platform Terms of Service med Google; DPF-registrerad som Google LLC, Mountain View, CA. Kontraherande enhet för EES-kunder anges i villkoren (ej närmare utläst här). Ej belagt i denna granskning vilken Google-enhet som står på Snajps faktura; kontrollera i faktureringskontot.
- **Roll:** Underbiträde.
- **DPA:** Cloud Data Processing Addendum, https://cloud.google.com/terms/data-processing-addendum, senast ändrad 23 oktober 2025 (versionshistorik längst ned på sidan).
  **Hur den ingås: automatiskt.** GCP-villkoren §5.2 säger att Google behandlar kunddata "in accordance with the Cloud Data Processing Addendum", och definitionen "URL Terms" omfattar addendumet (https://cloud.google.com/terms, hämtad 2026-11-17). Google beskriver dessutom en frivillig väg i konsolen för att granska och acceptera samt registrera dataskyddsombud och EU-representant (https://support.google.com/cloud/answer/6329727). Det är inte nödvändigt för att DPA:n ska gälla men rekommenderas så att Google har rätt kontakt vid incidenter.
- **Underbiträden:** https://cloud.google.com/terms/subprocessors. Google ska meddela minst 30 dagar innan ett nytt underbiträde börjar behandla kunddata (DPA §11.4).
- **Region:** Data i vila stannar i vald region (https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/data-residency). För ML-behandling har Gemini 2.5 Flash och 2.5 Pro bock för **EU-multiregion**. Sidan säger att bocken för EU-multiregion också gäller när man anropar en EU-endpoint i en enskild region som stöds, och att EU-multiregionen omfattar EU:s medlemsstater, inte UK och Schweiz. Europe-west4 och europe-north1 har ingen landsbock för Gemini 2.5. Behandlingen sker alltså inom EU men inte nödvändigtvis i Belgien eller Nederländerna. Platssidan säger uttryckligen att endpoints "don't guarantee data residency or in-region ML processing" (https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/locations). En `global`-endpoint kan behandla data var som helst i världen.
- **Grounding with Google Search:** Google lagrar loggar med frågor som härletts ur prompten i upp till tre dygn, och det går inte att stänga av (https://docs.cloud.google.com/vertex-ai/generative-ai/docs/data-governance). Använd det aldrig på kundmejltext.
- **Träning:** Ingen träning på kunddata utan tillstånd (data-governance-sidan ovan).
- **Cache:** Cachen ligger bara i minnet och raderas inom 24 timmar. Den kan stängas av per projekt med `disableCache: true` via `cacheConfig`, vilket kräver rollen `roles/aiplatform.admin` (samma källa).
- **Missbruksövervakning:** För kunder under online-villkoren loggas bara prompts som flaggats av automatiska säkerhetsklassare. De sparas upp till 90 dagar i projektets region eller multiregion och kan granskas av människor. Undantag finns bara för kunder med Google Cloud Master Agreement; något självbetjäningsalternativ för att stänga av loggningen är inte beskrivet (https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/abuse-monitoring).
- **Överföring:** DPF, där Google LLC står som aktiv i EU-U.S., Swiss-U.S. och UK Extension (dataprivacyframework.gov/list, uppslag 2026-11-17). DPA:n hänvisar även till SCC med modulerna C2P, P2P och P2C samt till en "Alternative Transfer Solution".
- **Intyg:** DPA:ns bilaga nämner ISO 27001/27017/27018. Ett aktuellt SOC 2-intyg och en trust center-URL har inte kontrollerats i denna granskning (ej belagt).
- **Bedömning: grön/gul.** Avtalet är på plats automatiskt och behandlingen sker inom EU vid regionala EU-endpoints. Gult gäller tre konfigurationskrav: anropa aldrig `global`, använd ingen Google Search-grounding på kunddata och överväg att stänga av cachen. Flaggade prompts kan sparas upp till 90 dagar, och det ska stå i PUB-bilagan.

### 2. Google AI Studio / Gemini API (generativelanguage.googleapis.com) – reservväg

- **Villkor:** https://aistudio.google.com/docs/terms (ai.google.dev/gemini-api/terms omdirigerar dit), i kraft 23 mars 2026.
- **Gratisnivå:** Google använder innehållet för att förbättra produkter och ML-teknik, och mänskliga granskare kan läsa in- och utdata. Villkoren säger "Do not submit sensitive, confidential, or personal information to the Unpaid Services."
- **Betald nivå:** Prompts och svar används inte för att förbättra produkterna. De behandlas enligt DPA:n för produkter där Google är personuppgiftsbiträde, och loggas en begränsad tid för att upptäcka policyöverträdelser. Data kan cachas i alla länder där Google har anläggningar. En nivå räknas som betald bara när API:t nås via ett Cloud-projekt med aktivt faktureringskonto.
- **EES:** Den som gör API-klienter tillgängliga för användare i EES, Schweiz eller UK får bara använda betalda tjänster.
- **Grounding med Google Search:** Prompt, kontext och utdata sparas 30 dagar, oavsett betald eller gratis nivå.
- **Bedömning: röd för kundmejl.** Det finns ingen regional kontroll ("any country"), och skyddet beror på att faktureringen är aktiv. Föreslagen åtgärd: ta bort AI Studio som reserv för kunddata och låt reserven vara Vertex i en annan EU-region. Om vägen ska finnas kvar måste nyckeln höra till ett faktureringsaktiverat Cloud-projekt, och det ska stå i PUB-bilagan att behandlingen inte är EU-bunden.

### 3. Railway (railway.com)

- **Juridisk person:** Railway Corporation, 548 Market St PMB 68956, San Francisco, CA 94104 (DPA Exhibit B, https://railway.com/legal/dpa).
- **Roll:** Underbiträde (all drift och Postgres).
- **DPA:** https://railway.com/legal/dpa. Inget versionsdatum anges. **Den ingås inte automatiskt.** Kunden fyller i ett DocuSign-formulär och DPA:n blir bindande när Railway har undertecknat. Compliance-sidan har länken "Sign Railway's DPA" (https://docs.railway.com/enterprise/compliance).
- **Underbiträden:** https://trust.railway.com/item/subprocessors listar bara Fathom Analytics, Cloudflare, Causal, Customer.io och Stripe. Ändamål och platser står inte på den publika sidan.
- **Infrastruktur, en avvikelse att följa upp:**
  - DPA:ns Exhibit C säger att plattformen körs på Google Cloud Platform.
  - Regionsidan anger "EU West Metal – Amsterdam (`europe-west4-drams3a`)" (https://docs.railway.com/reference/deployment-regions). Railway Metal beskrivs som egen hårdvara i egna datacenter (https://docs.railway.com/platform/railway-metal).
  - Railways blogg 2 juni 2026 säger att 40 % av arbetslasterna låg på moln-"burst" och att värdarna nu är multimoln över GCP, AWS och Metal (https://blog.railway.com/p/railway-metal-gen-2).
  - En Railway-anställd skrev i forumet att man "bursted back onto the cloud on AWS and GCP" i början av 2026 (https://station.railway.com/community/what-we-know-so-far-may-19th-2026-86354cdd).
  - GCP och AWS saknas ändå på den publika underbiträdeslistan. Det är **ej belagt** om Snajps tjänster och volymer i EU West ligger på Metal eller i ett publikt moln, och om moln-burst i så fall sker inom EU.
- **Volymer och backuper:** Volymer följer tjänstens region. Backuper sparas 6 dagar (dagliga), 27 dagar (veckovisa) och 89 dagar (månadsvisa) (https://docs.railway.com/reference/backups). Var backuperna lagras är **ej belagt**; regions- och backupsidorna säger ingenting. DPA:n säger att kunddata säkerhetskopieras dagligen "across multiple sites and regions".
- **Kryptering:** DPA Exhibit C säger "Databases are encrypted at rest", TLS och WireGuard.
- **Överföring:** DPF i första hand, annars SCC modul 1–3 med irländsk rätt (DPA §9). Railway Corporation står som aktiv i EU-U.S., Swiss-U.S. och UK Extension (uppslag 2026-11-17).
- **Intyg:** Compliance-sidan anger SOC 2 Type II och SOC 3. Rapporterna finns i https://trust.railway.com (SOC 3 publikt). Inget ISO 27001.
- **Bedömning: gul.** DPA:n gäller inte förrän ägaren har signerat den. Ägaren bör också begära skriftligt besked om underliggande infrastruktur för EU West och backupernas plats, eftersom den publika listan inte nämner GCP eller AWS.

### 4. Redis Cloud (Redis Ltd)

- **Juridisk person (avtalspart):** För kunder i Europa är det Redis EMEA Ltd., Bridge House, 4 Borough High Street, London SE1 9QQ, UK. Engelsk rätt gäller (Redis Cloud Agreement §10.11(c), https://redis.io/legal/cloud-tos/, uppdaterad 15 maj 2026). Koncernen har också Redis Ltd. (Tel Aviv) och Redis Inc. (San Francisco).
- **Roll:** Underbiträde.
- **DPA:** https://redis.io/legal/data-processing-addendum-dpa/, uppdaterad 26 mars 2025. **Den ingås automatiskt.** Cloud Agreement §5.3 säger att DPA:n "applies to Personal Data … contained in Customer Data" när GDPR gäller. Avtalet anger inte uttryckligen om gratisnivån omfattas: Free trials är "Evaluation Services" (§2.8).
- **Underbiträden:** https://redis.io/legal/subprocessors/ (uppdaterad 22 juni 2026). För Snajp är molnleverantören Google den relevanta. Övriga på listan är Redis interna verktyg, till exempel Salesforce, Zendesk, OpenAI och Anthropic. Ändringar meddelas 5 dagar i förväg.
- **Region:** GCP europe-west1, enligt Snajps konfiguration.
- **TLS:** TLS finns för betalda Essentials-planer och Pro men inte för Free Essentials. TLS är inte påslaget som standard (https://redis.io/docs/latest/operate/rc/security/database-security/tls-ssl/).
- **Överföring:** SCC modul 2/3, UK-tillägg och schweiziska SCC. Adekvansbeslut får användas (DPA bilaga 1 §5). DPF nämns inte, och sökningen på "Redis" gav ingen träff i DPF-listan.
- **Radering:** Ingen tidsgräns anges. Kunden kan själv ta bort data, och Redis får behålla loggar och backuper (DPA §10).
- **Intyg:** Trust center https://trust.redis.io listar SOC 2 Type 2 och ISO 27001, enligt sökresultatets sammanfattning. Rapporterna har inte lästs här.
- **Bedömning: gul.** Avtalet är på plats automatiskt. Ägaren behöver verifiera att databasen ligger på en betald plan och att TLS är påslaget. Med Free-plan finns ingen TLS och avtalsskyddet är oklart.

### 5. Resend (resend.com)

- **Juridisk person:** Plus Five Five, Inc. ("Resend"), 2261 Market Street #5039, San Francisco, CA 94114 (https://resend.com/legal/dpa, uppdaterad 2025-12-31).
- **Roll:** Underbiträde för kunders utskick och personuppgiftsansvarig för egna kontouppgifter. För Snajps egna kallmejl är Resend Snajps biträde.
- **DPA: automatiskt.** Den blir bindande "upon Customer entering into the Agreement". En signerad kopia finns i Resends dashboard.
- **Underbiträden:** https://resend.com/legal/subprocessors (uppdaterad 5 nov 2026). Alla är i USA, bland andra AWS (hosting och utskick), Anthropic, **TypeSafe AI, Inc. ("AI services")**, PlanetScale, Supabase och Vercel. Ändringar meddelas 14 dagar i förväg.
- **Region:** Den valda regionen styr bara varifrån mejlen skickas. Resends regionsida säger "All account data, including email metadata, logs, and API records, is stored in the United States" (https://resend.com/docs/dashboard/domains/regions). GDPR-sidan säger att det inte finns någon inställning som flyttar lagrad data till EU (https://resend.com/security/gdpr).
- **Lagringstid:** Mejl- och loggdata sparas 30 dagar på Free, Pro och Scale. Enterprise har "flexible retention". Vid uppsägning raderas data inom 90 dagar och backuper inom 7 dagar. Enskilda skickade mejl kan raderas via support (https://resend.com/security).
- **Överföring:** Resend anger DPF-certifiering, och SCC modul 1–3 gäller oberoende av den. I DPF-listan står Resend (San Francisco) som **"Active – Re-certification under Review"** för EU-U.S. och UK Extension (uppslag 2026-11-17).
- **Intyg:** SOC 2 Type II, inget ISO 27001 (https://resend.com/security).
- **Bedömning: gul.** Avtalet är på plats, men mejlinnehåll och loggar lagras i USA trots eu-west-1. Det ska stå i PUB-bilagan, och en överföringsbedömning (TIA) behövs. Resend anlitar dessutom TypeSafe som underbiträde, se punkt 7.

### 6. ScrapeGraphAI (scrapegraphai.com)

- **Juridisk person:** ScrapeGraphAI, Inc. Adress och registreringsland anges inte i villkoren (https://scrapegraphai.com/terms, uppdaterade 4 juni 2026). Tillämplig lag är lagen där bolaget är etablerat, utan närmare angivelse.
- **Roll:** Underbiträde för Snajps leadsdel (Snajp är ansvarig). Tjänsten hämtar publika webbsidor, som kan innehålla namn och kontaktuppgifter till exempelvis VD.
- **DPA:** Ingen publicerad. Villkoren §8 hänvisar till kontakt vid behov av DPA, enterprise-villkor eller underbiträdesuppgifter.
- **Träning:** Data från gratisplanen får användas för forskning och modellträning (§9). Betalda planer används inte för träning som standard.
- **Region:** Integritetspolicyn (uppdaterad 15 mars 2024) säger att data överförs till och behandlas i USA (https://scrapegraphai.com/privacy). Överföringsmekanism anges inte, och sökningen på "ScrapeGraph" gav ingen träff i DPF-listan.
- **Underbiträden och lagringstid:** Ej belagt. Ingen lista finns, och lagringstid för resultat och skärmbilder anges inte.
- **Intyg:** Ej belagt. Inget trust center hittades.
- **Bedömning: gul.** Data är publik B2B-information med låg känslighet, men avtal saknas. Ägaren bör se till att planen är betald och begära DPA via kontaktvägen i villkoren.

### 7. TypeSafe (api.typesafe.ai) – modellen Snajp kallar "Jev"

Detta är den viktigaste okända punkten, och den är nu i huvudsak belagd.

- **Juridisk person:** TypeSafe AI, Inc., 255 California St, Suite 1300, San Francisco, CA. Användarvillkoren (https://typesafe.ai/legal/terms, uppdaterade 19 sep 2026) styrs av Delawares lag. Master Customer Agreement (https://typesafe.ai/legal/mca, uppdaterat 23 sep 2026) styrs av Kaliforniens lag med JAMS-skiljeförfarande i San Francisco. Inkorporeringsstat anges inte.
- **Roll:** Underbiträde. Kundmejltext utan adresser skickas för klassning.
- **DPA:** https://typesafe.ai/legal/data-processing, uppdaterad 24 april 2026. TypeSafes dokumentation listar DPA, MCA och integritetspolicy som bolagets juridiska dokument (https://docs.typesafe.ai/legal).
  **Hur den ingås:** MCA säger att DPA:n är "incorporated herein by reference". MCA godkänns genom klick, genom en beställning som hänvisar till den, eller genom att använda eller betala för tjänsterna. Det är **ej belagt** vilka villkor Snajps konto faktiskt accepterade vid registreringen i console.typesafe.ai.
- **Innehåll i DPA:n:** TypeSafe är biträde och behandlar endast enligt kundens instruktioner. Ändringar av underbiträden meddelas i förväg, med 15 dagars invändningsrätt. Incidenter anmäls inom 72 timmar. Granskning får ske en gång per år. Överföring sker med SCC modul 2 (och 3), med irländsk rätt och UK-tillägg. Lagringstiden är "as long as necessary taking into account the purpose of the Processing". **Radering vid avtalets slut regleras inte i DPA:n.**
- **Träning:** MCA säger att TypeSafe inte tar med Customer Data i träningsdata utan kundens förhandsgodkännande. Integritetspolicyn säger "We will not train or fine tune any artificial intelligence or machine learning models on your prompts or other Input."
- **Telemetri, det allvarligaste villkoret:** MCA §4.1(c) ger TypeSafe en tidsobegränsad rätt ("in perpetuity") att ur Customer Data härleda "Telemetry". Telemetri definieras som bland annat "technical logs, hashes, summary statistics and classifications, metrics, and learnings". Enligt §4.3 får TypeSafe behandla telemetri "without restriction, including to improve the Services", och rätten fortsätter efter avtalets slut (§10.4). Klassningar av kundmejl kan därmed få användas av TypeSafe för egna syften utan tidsgräns. Det är svårt att förena med ett biträdes skyldighet att bara behandla enligt instruktion (GDPR art. 28.3 a).
- **Lagringstid:**
  - Integritetspolicyn säger att data sparas "for as long as reasonably necessary … or otherwise in support of our business or commercial purposes" (https://typesafe.ai/legal/privacy-policy, uppdaterad 19 nov 2025).
  - Enterprise-kunder kan fråga om ZDR via supportformulär (https://docs.typesafe.ai/legal).
  - Vercels ZDR-sida citerar TypeSafes juridiska policy: prompts sparas inte längre än vad som krävs för att generera Output (https://vercel.com/docs/ai-gateway/capabilities/zdr). Det citatet hittades inte i TypeSafes egna dokument.
- **Region:** "The Services are hosted in the United States." Integritetspolicyn konstaterar att EES- och UK-användare överför personuppgifter till USA.
- **Underbiträden:** https://trust.typesafe.ai/subprocessors (läst i webbläsare 2026-11-17):
  - AWS (USA): lagring och behandling för live-anrop
  - Modal, Nebius och CoreWeave (USA): prompts behandlas men lagras inte
  - Microsoft Azure och Google Cloud Platform ("Worldwide")
  - Cloudflare (Worldwide)
  - Stripe (USA)
  Nebius och CoreWeave lades till 3 oktober 2026.
- **DPF:** Sökningarna på "TypeSafe" och "Typesafe AI" gav ingen träff i DPF-listan 2026-11-17. Överföringen vilar alltså helt på SCC. Någon publicerad TIA eller kompletterande åtgärder finns inte.
- **Intyg:** Trust center https://trust.typesafe.ai listar "SOC 2 Type II – 2026" och kontroller som "Customer data deleted upon leaving". Rapporten är inte publik och har inte lästs.
- **Övrigt:** TypeSafe står som underbiträde hos Resend och (enligt sökresultat) Render. Det finns ett trust center men ingen EU-region.
- **Bedömning: röd.** Kundmejltext behandlas i USA utan DPF. Telemetrivillkoret ger en tidsobegränsad rätt att använda klassningar och "learnings" för egna syften. Lagringstiden är obestämd, och ZDR finns bara på begäran för Enterprise. **Förslag:** stoppa kundmejltext till Jev i produktion och klassa med Vertex Gemini i EU, som redan är godkänt. Om Jev ska behållas krävs fyra saker: (1) skriftlig bekräftelse på att MCA och DPA gäller Snajps konto, (2) ett tillägg som undantar Customer Personal Data från §4.1(c) och §4.3 eller bekräftar att telemetrin är anonym, (3) ZDR, och (4) en egen TIA.

### 8. GitHub (Microsoft)

- **Juridisk person:** GitHub, Inc., San Francisco. DPF-registrerad som "GitHub", aktiv i EU-U.S., Swiss-U.S. och UK Extension (uppslag 2026-11-17).
- **Roll:** Underbiträde för källkod och Actions-runners som var tionde minut kör en synk där produktionens persondata passerar. Hemligheter ligger som Actions-secrets.
- **DPA:** GitHub Data Protection Agreement, version oktober 2025 (https://github.com/customer-terms/github-data-protection-agreement). Den "forms part of the GitHub Customer Agreement". Online Services definieras som tjänster som tillhandahålls "under a written and executed agreement". Sidan med kundavtal listar DPA:n för **GitHub Enterprise Cloud, GitHub Enterprise (Unified), GitHub Teams och GitHub Copilot** (https://github.com/customer-terms). De vanliga användarvillkoren (Terms of Service) nämner ingen DPA (https://docs.github.com/en/site-policy/github-terms/github-terms-of-service). **Free-planen täcks alltså inte enligt de publika källorna.** Det är ej belagt hur Team-planens självbetjäning knyts till Customer Agreement.
- **Underbiträden:** https://github.com/subprocessors
- **Runners:** De körs i Azure, och vissa Linux-runners i AWS eller Azure. Region anges inte och kan inte väljas på github.com (https://docs.github.com/en/actions/concepts/runners/github-hosted-runners). EU-dataresidens med Actions-data i regionen finns bara för GitHub Enterprise Cloud med data residency (GHE.com) (https://docs.github.com/en/enterprise-cloud@latest/admin/data-residency/about-storage-of-your-data-with-data-residency).
- **Överföring:** DPF och/eller SCC (DPA §7.B). Integritetspolicyn säger att data kan behandlas i USA och andra länder.
- **Bedömning: gul (röd om kontot är Free).** Persondata som passerar runners i okänd region, eventuellt utan DPA, är svårt att försvara. **Rekommendation:** flytta synkjobbet från GitHub Actions till en schemalagd tjänst i Railway EU West, så att persondata aldrig når GitHub. Om synken måste ligga kvar: kontrollera planen och se till att den omfattas av DPA:n (Team eller Enterprise), och dokumentera överföringen.

### 9. Supabase och Render (avvecklas)

**Supabase**
- **Avtal:** Supabase Pte. Ltd., 65 Chulia Street #38-02/03, OCBC Centre, Singapore. DPA: https://supabase.com/legal/dpa. Den kompletterar villkoren och accepteras automatiskt: "acceptance of the Agreement shall have the same effect as signing the SCCs" (klausul 12.2). Överföring sker med SCC modul 2/3, UK- och schweiziskt tillägg. DPF nämns inte, och sökningen gav ingen träff.
- **Radering:** Kunddata raderas inom 30 dagar efter att ett projekt raderats, och raderade projekt går inte att återställa (https://supabase.com/legal/privacy-resources/data-residency-and-transfers-faq). Efter avtalsslut kan kunden begära ut data inom 30 dagar (DPA 11.2). Någon automatisk raderingsbekräftelse beskrivs inte; FAQ:n hänvisar till privacy@supabase.io.
- **Bedömning: gul tills raderat.** Projektets radering är ägarens handgrepp. Agenten skriver aldrig till Supabase.

**Render**
- **Avtal:** Render Services, Inc., 525 Brannan St, San Francisco. DPA (senast ändrad 19 december 2024, https://render.com/dpa) "supplements the Render Terms of Service". SCC anses undertecknade genom avtalet, alltså automatiskt. Överföring sker i första hand med DPF och annars med SCC. Render står som aktiv i DPF-listan.
- **Radering:** "at Customer's choice, Company shall return or delete Customer's Personal Data" (DPA §2.4), utan tidsangivelse.
- **Underbiträden:** Trust center https://trust.render.com. Enligt sökresultat finns bland andra AWS, GCP, Cloudflare, ClickHouse, Anthropic och TypeSafe AI.
- **Bedömning: gul tills raderat.** Ägaren raderar tjänster och databaser och begär skriftlig bekräftelse av raderingen.

### 10. Leverantörer runt omkring

- **Loopia (Loopia AB, Västerås):** DNS och domän. Loopia är personuppgiftsansvarig för domänregistreringen. Där Loopia är biträde regleras det i bilagan "Personuppgiftsbiträdesavtal" till de allmänna villkoren, som gäller automatiskt med avtalet (https://www.loopia.se/om-loopia/dataskydd/skyldigheter/). Underbiträden publiceras på Loopias dataskyddssida (https://www.loopia.se/om-loopia/dataskydd/personuppgifter/). Ingen tredjelandsöverföring är känd. **Grön.**
- **Cal.com (Cal.com, Inc., San Francisco):** DPA https://cal.com/dpa gäller alla konton och planer som styrs av avtalet. Den använder SCC modul 2/3 och DPF. Cal.com, Inc står som aktiv i DPF-listan (EU-U.S. och UK). Underbiträden finns på https://trust.cal.com. Var data lagras är ej belagt. **Grön/gul**; relevant bara om tjänsten används för demobokning, där Snajp är ansvarig.
- **Google och Microsoft Entra ID som inloggning:** Leverantören autentiserar sina egna användare som självständigt ansvarig och lämnar namn och e-post till Snajp via OIDC. Ingen DPA behövs för själva inloggningen; det ska framgå av Snajps integritetspolicy. Entra ID lagrar och behandlar för EU-kunder det mesta inom EU Data Boundary, med angivna undantag (https://learn.microsoft.com/en-us/entra/fundamentals/data-storage-eu). Microsoft Corporation och Google LLC är aktiva i DPF. **Grön.**

## C. Kedjan bakom Comp AI Community Edition (självhostad)

Innehållet här är Snajps styrdokument, personalens namn och e-post och leverantörslistor. Det är inte kunders kunddata, så risknivån är lägre.

### 11. Trigger.dev Cloud
- **Juridisk person:** API Hero Ltd, med handelsnamnet Trigger.dev. Adress anges inte i DPA:n (https://trigger.dev/legal/dpa, uppdaterad 23 dec 2025).
- **DPA:** Den gäller automatiskt "By using the Trigger.dev Service or entering into an Agreement".
- **Överföring:** SCC och UK-tillägg. DPF är inte relevant för ett brittiskt bolag; UK är avsändarland.
- **Underbiträden:** https://trigger.dev/legal/subprocessors (13 okt 2026). Nästan alla finns i USA: AWS, ClickHouse, PlanetScale, Axiom, Sentry, OpenAI, Anthropic med flera.
- **Region:** Enligt dokumentationen (sökresultat, https://trigger.dev/docs/triggering) styr vald region bara var körningen sker och inte var payload, output, taggar eller loggar lagras. Lagringsplats är **ej belagd**.
- **Intyg:** SOC 2 Type II enligt sökresultat och trust center https://security.trigger.dev. Rapporten är inte läst.
- **Bedömning: gul.** Självhosta Trigger.dev, eller håll persondata ur task-payloads och loggar.

### 12. Vercel AI Gateway
- **Avtal:** Vercel Inc. DPA: https://vercel.com/legal/dpa (uppdaterad 17 mars 2026, i kraft 31 mars 2026). Den blir bindande när kunden ingår avtalet. Omfattningen anges som **Enterprise- och Pro-planer**; Hobby nämns inte. Överföring sker med SCC och UK IDTA. Vercel Inc. står som aktiv i DPF-listan.
- **Underbiträden:** https://security.vercel.com
- **Lagring:** Gatewayen sparar inte prompts eller svar, utan bara metadata som modell, tokens och kostnad (https://vercel.com/docs/ai-gateway/capabilities/zdr, uppdaterad 22 sep 2026).
- **Vidareförmedling:** Modelleverantörerna får data. ZDR mot leverantörerna kräver Pro, Enterprise eller köpta credits. Det slås på teamvis (0,10 USD per 1 000 anrop) eller per anrop (gratis). "Disallow Prompt Training" är en separat inställning. Verktyg som leverantören kör, till exempel webbsök och grounding, omfattas inte av ZDR.
- **Bedömning: gul.** Kräver Pro eller köpta credits och att både ZDR och Disallow Prompt Training slås på.

### 13. OpenAI API och Anthropic API

**OpenAI**
- **Avtal:** DPA https://openai.com/policies/data-processing-addendum/ (uppdaterad 1 dec 2025, gäller från 1 jan 2026). Den införlivas i tjänsteavtalet och godkänns genom klick på beställningsformuläret eller genom användning. Avtalspart för EES är OpenAI Ireland Ltd. Överföring sker med SCC modul 2/3. Sökningarna "OpenAI" och "OpenAI OpCo" gav ingen träff i DPF-listan.
- **Träning och lagring:** Ingen träning på API-data utan opt-in. Missbruksloggar sparas upp till 30 dagar. ZDR och Modified Abuse Monitoring kräver förhandsgodkännande (https://developers.openai.com/api/docs/guides/your-data).
- **EU-residens:** Europaregion (eu.api.openai.com) finns, men tillgången styrs av OpenAIs säljteam och gäller bara nya projekt (https://developers.openai.com/api/docs/guides/data-residency, https://help.openai.com/en/articles/10503543-data-residency-for-the-openai-api).

**Anthropic**
- **Avtal:** Commercial Terms (i kraft 17 juni 2025) med Anthropic Ireland, Limited för EES. DPA:n är "incorporated into these Terms by reference" (https://www.anthropic.com/legal/commercial-terms). DPA https://www.anthropic.com/legal/data-processing-addendum gäller från 24 feb 2025, med SCC modul 2/3 och UK- och schweiziskt tillägg. Underbiträden finns på https://www.anthropic.com/subprocessors. Sökningarna "Anthropic" och "Anthropic PBC" gav ingen träff i DPF-listan.
- **Träning och lagring:** Ingen träning på kundinnehåll. In- och utdata raderas inom 30 dagar. Flaggat innehåll kan sparas upp till 2 år och klassificeringspoäng upp till 7 år (https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data).
- **EU-residens:** Ingen EU-inferens i förstapartens API enligt sökresultat; där finns `inference_geo` med us eller global. EU-inferens finns via Bedrock eller Vertex (https://claude.com/regional-compliance).

**Bedömning för båda: gul.** Godtagbart för Comp-innehåll, men inte för kunders kunddata.

### 14. Firecrawl
- **Juridisk person:** SideGuide Technologies Inc. (d/b/a Firecrawl), ett Delaware-bolag (https://www.firecrawl.dev/privacy-policy, reviderad 26 dec 2024).
- **Lagring:** Servrarna står i USA. Personuppgifter sparas tills någon skriftligt begär radering.
- **DPA:** Enligt Firecrawls egna sidor (sökresultat) finns DPA och ZDR bara för Enterprise, och någon EU-residens erbjuds inte.
- **DPF:** Sökningen på "SideGuide" gav ingen träff.
- **Bedömning: gul.** Använd bara för publik leverantörsinformation och skicka inga personuppgifter.

### 15. AWS S3 (eu-north-1, Stockholm)
- **DPA:** AWS GDPR DPA ingår i AWS Service Terms och gäller automatiskt för alla kunder. SCC gäller automatiskt vid överföring till tredjeland (https://aws.amazon.com/compliance/gdpr-center/, https://aws.amazon.com/service-terms/).
- **Region och DPF:** Data stannar i vald region. Amazon.com, Inc. står som aktiv i DPF med 5 täckta bolag (uppslag 2026-11-17).
- **Bedömning: grön.**

---

## Kräver ägarens hand (i prioritetsordning)

1. **TypeSafe/Jev:** Besluta om stopp för kundmejltext till Jev tills villkoren är lösta. Om Jev ska behållas: skicka en skriftlig begäran till privacy@typesafe.ai (adressen anges i integritetspolicyn) och be om fyra saker: (a) bekräftelse att MCA och DPA gäller kontot, (b) ett tillägg som undantar personuppgifter från telemetrilicensen §4.1(c)/§4.3, (c) ZDR och en raderingstid, (d) SOC 2-rapporten. Ägaren skriver och undertecknar själv.
2. **Railway:** Signera DPA:n via DocuSign-länken "Sign Railway's DPA" på https://docs.railway.com/enterprise/compliance. Begär samtidigt skriftligt besked om underliggande infrastruktur och backupplats för EU West, eftersom GCP och AWS saknas i den publika underbiträdeslistan.
3. **GitHub:** Kontrollera vilken plan kontot har. Är det Free omfattas det inte av DPA:n; besluta då att flytta synken (se konfigurationslistan) eller uppgradera till en plan som DPA:n täcker.
4. **Google AI Studio:** Bekräfta att reservnyckeln hör till ett faktureringsaktiverat Cloud-projekt, eller besluta att ta bort reserven för kunddata.
5. **Supabase:** Radera det gamla projektet i dashboarden och mejla privacy@supabase.io för skriftlig raderingsbekräftelse. Data raderas inom 30 dagar.
6. **Render:** Radera tjänster och databaser och begär skriftlig bekräftelse enligt DPA §2.4.
7. **ScrapeGraphAI:** Kontrollera att planen är betald och begär DPA via kontaktvägen i villkoren §8.
8. **Google Cloud (valfritt men rekommenderat):** Registrera kontaktuppgifter för dataskydd, och vid behov EU-representant, under Privacy & Security / Legal & Compliance i konsolen.
9. **Vercel (Comp):** Om AI Gateway ska användas krävs Pro eller köpta credits. Slå sedan på "Zero Data Retention" och "Disallow Prompt Training" i AI Gateway Settings.
10. **Resend:** Inget klick krävs, eftersom DPA:n gäller automatiskt; ladda ned den signerade kopian ur dashboarden till registret. Godkänn att mejlinnehåll lagras i USA (beslut plus TIA).

## Rekommenderade konfigurationsändringar

1. Skicka inte kundmejltext till TypeSafe. Klassa med Vertex Gemini i europe-west1 med reserv i europe-west4 eller europe-north1.
2. Vertex: anropa bara regionala EU-endpoints, aldrig `global`. Lägg en kodgrind som fäller anrop till `global`. Använd ingen "Grounding with Google Search" på kundmejltext. Överväg att stänga av cachen per projekt (`cacheConfig.disableCache=true`).
3. Ta bort AI Studio (generativelanguage.googleapis.com) som reservväg för kunddata, eller kör den bara med faktureringsaktiverad nyckel och dokumentera att behandlingen inte är EU-bunden.
4. Flytta den tiominutersvisa synken från GitHub Actions till en schemalagd tjänst i Railway EU West, så att persondata inte passerar GitHubs runners. Håll Actions-secrets till ett minimum.
5. Redis: säkerställ betald plan och slå på TLS, och överväg mutual TLS.
6. Resend: överväg Enterprise för kortare lagringstid, och skriv i PUB-bilagan att innehåll och loggar lagras i USA i 30 dagar.
7. Comp AI: självhosta Trigger.dev eller håll persondata ur payloads. Kör AI-anrop via Vercel AI Gateway med ZDR och Disallow Prompt Training. Använd Firecrawl bara för publik information. Använd S3 i eu-north-1.
8. Uppdatera PUB-bilagans underbiträdeslista med de bekräftade regionerna ovan, inklusive att Resend och Render själva anlitar TypeSafe AI.
