# Svenska CRM-system: objektmodell, termer, vyer, data, GDPR, kopplingar och pris

Underlag för Snajp CRM. Skrivet 2026-11-25 av en läsande agent; ingen befintlig fil är ändrad.

## Hur filen ska läsas

- **[Läst]** = jag har hämtat leverantörens egen sida (eller dess sökresultatutdrag) och återger den. URL står vid varje påstående.
- **[Tredjepart]** = uppgiften kommer från en jämförelsesajt (businesswith.se, G2, Capterra) och ska bekräftas hos leverantören.
- **[Antagande]** = min kunskap eller slutsats, inte belagd i en källa jag läst i dag. Använd inte som facit.
- Priserna är listpriser som de visades 2026-11-25, normalt exklusive moms. De ändras ofta.
- Källsystemens API:er (endpoints, JSON, webhooks) beskrivs INTE här utan i `docs/crm/underlag/svensk-04-kallsystemens-api-for-adaptrar.md` (rubriker på rad 63, 270, 410, 518, 605, 679, 913). Den här filen handlar om hur systemen ser ut och används.
- Två leverantörssajter (lime-technologies.com och support.upsales.com) svarar 403 på skript (curl) men gick att läsa via webbhämtaren; de bör öppnas i en vanlig webbläsare när de ska fotograferas.

## Sammanfattning för byggaren (det viktigaste först)

1. **Bolaget är navet, och organisationsnumret är svenskarnas nyckel.** Lime Go har fältet `organizationNumber` och slår upp bolag på namn, `registrationNumber` och ort, först i kundens egna bolag och sedan i Bisnode/D&B-databasen (https://lime-go.readme.io/docs/organizations). Upsales matchar bolagsdata "på exakt företagsnamn eller organisationsnummer" (support.upsales.com, sökutdrag, se §2.4). HubSpot är motsatsen: amerikanskt, deduplicerar bolag på **domännamn** och bara vid import, inte via API (https://knowledge.hubspot.com/records/deduplication-of-records). Snajps utkast `crm_bolag.orgnr_nyckel` med unikt index per tenant (`db/migrations/20261125090000_153_crm_grund.sql:75,113-115`) följer den svenska modellen; `doman` finns som sekundär nyckel (rad 81, 117).
2. **Kundrelation är ett eget begrepp på bolaget, skilt från affären.** Lime Go har fem värden: `NO_RELATION`, `WORKING_ON_IT`, `IS_A_CUSTOMER`, `WAS_A_CUSTOMER`, `BEEN_IN_TOUCH` (https://lime-go.readme.io/docs/organizations). Det är just det fält Snajp behöver för att utesluta befintliga kunder ur Iris. Snajps utkast har `relation in ('kund','tidigare_kund','prospekt','partner','leverantor','ovrigt')` (`…_153_crm_grund.sql:91,105-107`).
3. **Bolagsdata ingår i priset hos de svenska leverantörerna.** Lime Go: "Obegränsad tillgång till nordisk företagsdata" redan i Starter, data från Dun & Bradstreet, uppdaterad varje natt (https://www.lime-technologies.com/sv/lime-go/priser/, https://faq.lime-go.com/en/questions-and-answers-faq/company-data/how-often-is-the-company-data-updated-in-lime-go). Upsales: "Company Data Hub" och gratisvarianten "Prospecting BASIC". En svensk säljare förväntar sig att skriva in ett orgnr eller ett namn och få resten ifyllt.
4. **Säljprocessen heter olika saker men har samma form:** steg med sannolikhet, vägt värde, vunnen/förlorad, förlustorsak. HubSpots svenska standardsteg: "Möte inbokat (20%)", "Kvalificerad att köpa (40%)", "Presentation inbokad (60%)", "Beslutsfattare köpt in (80%)", "Kontrakt skickat (90%)", "Stängd och vunnen", "Stängd och förlorad" (https://knowledge.hubspot.com/sv/object-settings/set-up-and-customize-pipelines). SuperOffice har statusarna Öppen, Såld, Förlorad, Uppskjuten (https://docs.superoffice.com/sv/sale/learn/index.html).
5. **Ekonomisystemskopplingen är den integration en svensk köpare frågar efter först.** Lime Go säljer "ERP Standard (Visma och Fortnox)" som tillägg för 999 kr/mån (https://www.lime-technologies.com/sv/lime-go/priser/). Fortnox listar 53 CRM-kopplingar i sin integrationskatalog (https://www.fortnox.se/integrationer/kategorier/crm). Kundnumret i ekonomisystemet är en andra nyckel bredvid orgnr: Lime Go skapar dubbletter när namn, orgnr och ort stämmer men kundnumret skiljer (https://faq.lime-go.com/en/questions-and-answers-faq/integrations:-erp/how-are-branch-companiesgroup-companies-matched).
6. **GDPR marknadsförs som funktion: rättslig grund per person och syfte, export, anonymisering.** SuperOffice dokumenterar rättslig grund och samtyckeskälla per syfte (https://docs.superoffice.com/en/security/privacy/consent-management). Lime Go anonymiserar på ett slutdatum och exporterar till Excel (https://www.lime-technologies.com/en/products/lime-go/features/gdpr-functionality/). Snajps utkast har `crm_personer.rattslig_grund in ('avtal','berattigat_intresse','samtycke')` (`…_153_crm_grund.sql:132,142-144`) men inget syfte, ingen källa och inget datum.
7. **Prisnivån:** Lime Go 400–900 kr/användare/mån (paket), Lime CRM från ca 650 kr [Tredjepart], SuperOffice 45–160 €, Pipedrive 14–79 €, Salesforce Starter 250 kr / Pro 1 000 kr, Membrain 490–890 kr, Spiris Tid & Projektplanering 419 kr/mån plus användarlicenser. Se §10.3.

---

## 1. Lime Technologies: Lime Go och Lime CRM

Lime Technologies (Lund) säljer två produkter: **Lime Go**, standardiserat SaaS-CRM för säljteam med inbyggd bolagsdatabas, och **Lime CRM**, konfigurerbart CRM för större kunder och branschlösningar.

### 1.1 Objektmodell och termer

**Lime Go [Läst]** (API-dokumentationen, engelska fältnamn):
- **Organization** (UI: Företag): fält `id`, `name`, `city`, `email`, `dateLastModified`, `phoneNumber`, `organizationNumber`, `responsibleCoworker`, `customFields`, `integrationId`, `temperature`, `customerRelation`, `tags`, `employees`, `deals`; sökexemplet använder också `turnover` och `numberOfEmployees` (https://lime-go.readme.io/docs/organizations).
- **customerRelation** (relation): `NO_RELATION` (ingen kontakt än), `WORKING_ON_IT` (något pågår, t.ex. bokat möte eller skapad affär), `IS_A_CUSTOMER` (affär gjord), `WAS_A_CUSTOMER` (var kund men räknas inte längre), `BEEN_IN_TOUCH` (lead som inte blev affär, ingen framtida affär väntas) (samma URL).
- **Person**: `name`, `phoneNumber`, `employerName`, `employer`, `customFields` (https://lime-go.readme.io/docs/persons, sökutdrag).
- **Deal** (UI: Affär): `id`, `name`, `customerName`, `status`, `source`, `tags`, `responsibleCoworker`, `customFields`, `Customer`, `value`; statusvärdena hämtas via GraphQL-introspektion, enda exemplet är `ORDER` (https://lime-go.readme.io/reference/deals).
- **Coworker** = användare/medarbetare (`responsibleCoworker`).
- Övriga funktioner med svenska namn från funktionssidan: "Företagsdata", "Nordiska beslutsfattare", "Kunder och kontaktpersoner", "Historiknoteringar och dokumentlagring", "Lead historik", "Smart uppföljning" (med "att göra-lista"), "Offerthantering", "Google maps kartfunktion", "GDPR-funktioner" (https://www.lime-technologies.com/sv/lime-go/funktioner/).
- **[Antagande]** UI-etiketterna för relationen på svenska är ungefär "Ingen relation", "Jobbar på det", "Är kund", "Har varit kund", "Varit i kontakt". Jag hittade ingen offentlig källa som bekräftar dem; fotografera Lime Go innan termerna kopieras.

**Lime CRM [Läst, delvis]**:
- Levereras "utan datamodell"; databasen innehåller bara det som behövs för att starta, och kundens typer läggs på (Lime-jobbannons, sökutdrag via https://jobs.lime-technologies.com/?p=1615).
- Kärnmodellen ("Lime Core") har limetypes `company`, `person`, `history`, `helpdesk`, `document`, `coworker`. `history` har fältet `type` med option `comment`; `helpdesk.statuscolor` har `finished`, `ongoing`, `new`; `person` har `firstname`, `lastname`, `email`, `phone`, `mobilephone`, `inactive` (https://lime-addon-field-crm.readthedocs-hosted.com/en/latest/required-tables/).
- Tidslinjen heter **Activities**: "a timeline, showing everything that has happened on a record", med historiknoteringar, e-post, dokument och ärenden; tre visningstyper `Standard` (anteckningar), `Minimal` (systemhändelser, statusbyten) och `Emphasized` (externa meddelanden som e-post och chatt); relaterade poster visas som "chips" (https://platform.docs.lime-crm.com/en/latest/configuration/webclient/activities).
- Samtalsintegrationer skriver en **History**-post med `date`, `person`, `company`, `note`, `type` = `comment`, och matchar kontakt på e-post före `mobilephone` före `phone` (https://www.dstny.se/partnerhelp/lime-crm-dstny-conversational-intelligence).

### 1.2 Säljprocess
- Lime Go: affärer med status; ingen offentlig lista över standardsteg hittad. **[Antagande]** UI-stegen i Lime Go är ungefär "Kontakt", "Behov", "Offert", "Förhandling", "Order"/"Vunnen", "Förlorad".
- Lime Go-FAQ: "Ändras värdet på en vunnen affär i Lime Go om man ändrar värdet på ordern i affärssystemet?" visar att vunna affärer kan skapas från ekonomisystemets order (sökutdrag, faq.lime-go.com).

### 1.3 Vyer
- Lime CRM: tidslinje (Activities) per post, listor och kort (se 1.1). Lime Go har kartfunktion (Google Maps) (https://www.lime-technologies.com/sv/lime-go/funktioner/).

### 1.4 Bolagsdata och dubbletter
- Data från **Dun & Bradstreet** (fd Bisnode); Lime Go uppdateras mot D&B varje natt, kreditbetyg kvartalsvis (https://faq.lime-go.com/en/questions-and-answers-faq/company-data/how-often-is-the-company-data-updated-in-lime-go).
- API:t kan slå upp på Bisnode-id: `externalKeyName = __bisnodeid` (https://lime-go.readme.io/docs/organizations).
- Omfång enligt marknadsföring: "3,7 miljoner uppdaterade nordiska företagsdata" respektive "1.8 million updated company profiles" på olika sidor (sökutdrag från lime-technologies.com). Siffrorna motsäger varandra.
- Paketnivåer: Starter "Obegränsad tillgång till nordisk företagsdata"; Grow + "Tillgång till beslutsfattare för en nordisk marknad"; Business + "Nyckeltal, kreditvärdighet & kunddashboard" och "Koncernstruktur på företag" (https://www.lime-technologies.com/sv/lime-go/priser/).
- Dubbletter vid ERP-synk: samma namn, orgnr och ort men olika kundnummer ger två företagskort, inte sammanslagning; matcha därför på namn, orgnr, ort och kundnummer (ERP-id) (https://faq.lime-go.com/en/questions-and-answers-faq/integrations:-erp/how-are-branch-companiesgroup-companies-matched).

### 1.5 GDPR
- Lime Go: samtyckestyper som administratören definierar (syfte, t.ex. nyhetsbrev), "GDPR portal" där den registrerade exporterar sina uppgifter (Excel), radering genom **anonymisering** på ett satt slutdatum (https://www.lime-technologies.com/en/products/lime-go/features/gdpr-functionality/).

### 1.6 Integrationer
- Lime Go: "Öppet API och Zapier integrationer" i alla planer; "ERP Standard (Visma och Fortnox)" 999 kr/mån, "ERP Premium (Visma och Fortnox)" 1 499 kr/mån; "Chat (Lime Connect)" från 899 kr/mån (https://www.lime-technologies.com/sv/lime-go/priser/).
- Lime CRM ERP-lista: Fortnox, Visma eEkonomi, Visma Administration, Visma.net, Visma Business, Visma Global, Visma Nova, **BL Administration** (Björn Lundén), Business Central, Navision, Finance & Operations, Xledger, Monitor, Maconomy, Exact Online, Tripletex, Uniconta, PowerOffice Go, e-conomic, iFenix; kunder synkas och fakturor visas i Lime (https://www.lime-technologies.com/lime-crm/solutions/erp).
- Telavox: klick-för-att-ringa och uppslag av inkommande samtal mot personens nummer; tillägget är markerat som utfasat för gamla Telavox Desktop (https://docs.lime-crm.com/_export/xhtml/addons/telavox/start, https://www.lime-technologies.com/en/products/lime-crm/integrations/telavox/).
- E-signering: Oneflow ("data is pushed back to Lime CRM once a contract has been signed", https://oneflow.com/integrations/lime-crm/), GetAccept (tvåvägs, help.getaccept.com, sökutdrag), Scrive (https://www.scrive.com/ratkaisut/integraatiot/area/crm).
- HubSpot-synk: "Lime CRM data sync", en- eller tvåvägs (https://ecosystem.hubspot.com/no/marketplace/listing/limecrm-data-sync).

### 1.7 Pris
- Lime Go (årsvis): Starter 1 200 kr/mån för 3 användare (≈400 kr/anv), Grow 2 699 kr/mån för 4 (≈675), Business 4 499 kr/mån för 5 (≈900), Enterprise "Kontakta oss"; "Tilläggslicens" 399 kr/mån; kvartalsvis ca 20 % dyrare (https://www.lime-technologies.com/sv/lime-go/priser/). Per-användarpriset är min division.
- Lime CRM: "från 650 kr per användare och månad" [Tredjepart] (https://businesswith.se/system/lime-crm/); danska prissidan: Start 400 DKK, Business 600 DKK, Enterprise 1 000 DKK per användare/mån (https://www.lime-technologies.com/da/pris, sökutdrag).

---

## 2. Upsales

Svenskt (Stockholm) B2B-CRM, numera "AI-drivet CRM för B2B-företag, byggt på Nordens mest kompletta företagsdata" (Upsales egen text i Fortnox katalog, https://www.fortnox.se/integrationer/kategorier/crm).

### 2.1 Objektmodell och termer
- Svenska termer på Upsales svenska sida: "företag", "kontakter", "affärer", "företagsdata" (https://upsales.com/sv/). API:t har `accounts`, `contacts`, `opportunities`, `orders`, `appointments`, `activities` samt orderstegen (`/api/v2/accounts` m.fl., se svensk-04 rad 605–678; sökutdrag från https://pipedream.com/apps/upsales).
- **Möjlighet (opportunity) och Order** är samma objekt i olika steg: en möjlighet blir order vid 100 % (se 2.2). **[Antagande]** UI-flikar på svenska: Företag, Kontakter, Pipeline/Möjligheter, Order, Aktiviteter, Möten, Kampanjer.
- Upsales använder "journey status" (kundresestatus) på bolag och kontakter; vid sammanslagning behålls huvudpostens värde (support.upsales.com, sökutdrag, artikel 360038888513).

### 2.2 Säljprocess
- Standardsteg med sannolikhet [Läst, sökutdrag]: "Fallback (5%)", "Prospect 1 (25%)", "Prospect 2 (50%)", "Verbal agreement (90%)", "Closed order (100%)"; stegen och procenten kan ändras i inställningarna; vissa fält är obligatoriska från "Stage 2" eftersom stegen används i prognoser (https://support.upsales.com/hc/en-us/articles/5951002703889-Q-How-do-users-choose-the-probability-for-an-opportunity-stage).
- Prognoser: https://support.upsales.com/hc/en-us/articles/11331108129425-Upsales-Forecasting.

### 2.3 Vyer
- Marknadsförs: "sales board", rapportcenter, pipeline-rekommendationer, riskanalys (https://upsales.com/sv/).

### 2.4 Bolagsdata och dubbletter
- Tre prospekteringsprodukter: **Company Data Hub** (svenska leads, AI-rekommendationer, tillväxtsignaler), **Prospecting BASIC** (gratis grundversion) och **Bisnode** (Sverige, Danmark, Finland, Norge); segmentering på bransch, omsättning, bolagsform, ort och storlek (support.upsales.com artikel 360013701773/360001685828, sökutdrag).
- Automatisk uppdatering av företagsinfo: bara vid exakt träff på företagsnamn eller organisationsnummer; vid konflikt vinner Company Data Hub och skriver över det användaren angett; varje matchat bolag drar "tokens" (https://support.upsales.com/hc/en-us/articles/12016823691281-Automatic-update-of-company-info, sökutdrag; sidan ger 403 för skript).
- Dubbletter: Upsales föreslår dubbletter; administratören slår ihop, ignorerar eller raderar. Vid sammanslagning blir ett bolag primärt och tar över det sekundäras data (artiklar 360038888513, 360008474514, sökutdrag).

### 2.5 GDPR
- Upsales är personuppgiftsbiträde; kunden ansvarar för information och samtycke (https://www.upsales.com/product-privacy-policy/). Hjälpcentret har "Managing GDPR, PII & sensitive data" och "How to anonymise contact data" (https://support.upsales.com/hc/en-us/articles/13437423763089, sökutdrag). Ett inbyggt fält för rättslig grund kunde jag inte bekräfta.

### 2.6 Integrationer
- Fortnox: "vunna affärer i Upsales blir automatiskt order eller faktura i Fortnox" (https://www.fortnox.se/integrationer/integration/upsales-nordic-ab/upsales, sökutdrag).
- Oneflow (möjlighets-, kontakt- och företagsfält till avtalet, produkter till produkttabellen, https://oneflow.com/integrations/upsales/), Scrive, GetAccept (se 1.6).
- Telavox–Upsales: ingen träff hos Telavox (https://telavox.com/integrations/).

### 2.7 Pris
- Ingen offentlig prislista (`https://upsales.com/sv/priser` gav 404). G2 anger £49/användare/mån [Tredjepart] (https://www.g2.com/products/upsales-sales-and-marketing-platform/pricing). 14 dagars gratis test (https://upsales.com/sv/).

---

## 3. SuperOffice

Norskt CRM, stort i Norden, fullt svenskt gränssnitt och svensk dokumentation på docs.superoffice.com/sv.

### 3.1 Objektmodell och termer [Läst]
- **Företag** ("Företag: Alla"), **Kontakt**, **Projekt**, **Dokument**, **Kalender**, **Val/Urval**, **Navigator** (https://docs.superoffice.com/sv/learn/basics/index.html).
- **Företagskort** och **Kontaktkort**; relationer mellan poster med kolumnerna "Från - fullständigt namn", "Relation", "Till - fullständigt namn", "Kommentar"; relationstyper i "Inställningar och Underhåll" under "Allmänt - Relation" (https://docs.superoffice.com/sv/learn/basics/relations.md).
- **Försäljning** och **Försäljningskortet** med flikarna Försäljning (titel, fas, belopp), Detaljer (total kostnad, vinst, konkurrent), Mer (anpassade fält), Anteckningar, Länkar; detaljkort för aktiviteter, säljguide, intressenter och offert; fältet "Nästa aktivitet" (https://docs.superoffice.com/sv/sale/learn/index.html).
- **Aktiviteter** = följ upp/möten/uppgifter, dokument och e-post som aktiviteter (https://docs.superoffice.com/sv/learn/basics/activity.md, länk från grundsidan).
- **Begäran** (Request) = supportärende i SuperOffice Service (nämns i sammanslagningsdokumentet: "Contacts and related requests are moved").

### 3.2 Säljprocess [Läst]
- Status: **Öppen, Såld, Förlorad, Uppskjuten**; vid Uppskjuten öppnas fälten "Återöppningsdatum" och "Orsak (uppskjuten)" (https://docs.superoffice.com/sv/sale/learn/index.html). API-enum: `Open`, `Sold`, `Lost`, `Stalled` (https://docs.superoffice.com/en/database/tables/enums/salestatus.md).
- Faser ("Sale - Stage") administreras i "Settings and maintenance" → "Lists"; varje fas har en sannolikhet i procent som visas på försäljningskortet; faser kopplas till försäljningstyper ("sale types") och säljguider (https://docs.superoffice.com/en/sale/admin/sale-stage.html).
- Röda försäljningar har förfallna aktiviteter eller datum (https://docs.superoffice.com/sv/sale/learn/index.html).

### 3.3 Vyer [Läst]
- Försäljningsskärmen: vänsterpanel med fastnålade urval och sökfält, huvudområde i **tavlevy eller listvy** eller kortet, sidopanel med förhandsvisning av kopplat företag; exempel på fastnålat urval: "Min öppna försäljning"; kalendervy över ej slutförda försäljningar (https://docs.superoffice.com/sv/sale/learn/index.html).
- **Urval**: "Statiskt urval" (manuellt tillagda medlemmar), "Dynamiskt urval" (sparad sökning som körs när urvalet öppnas), "Kombinerat urval" (två urval, kräver Growth); flik "Kriterier"; flik "Utskick"; "Uppgiftsmeny" för massåtgärder (e-post, massredigera, export) (https://docs.superoffice.com/sv/search-options/selection/learn/index.html). Det är SuperOffice motsvarighet till sparade vyer och målgrupper.

### 3.4 Bolagsdata och dubbletter
- Sammanslagning: välj "To company", källbolaget raderas; kontakter och begäranden flyttas; "Merge identical contacts" slår ihop kontakter med exakt samma för-, mellan- och efternamn; aktiviteter flyttas; projekt- och statiska urvalsmedlemskap följer med; "Replace empty fields with values from the source company"; kräver rättigheten "Can manage (move and merge) entities"; ångra nämns inte (https://docs.superoffice.com/en/company/learn/merge-companies.html).
- Bolagsdata kommer via appar i SuperOffice App Store (t.ex. Visma-, Fortnox-, kreditupplysningsappar) **[Antagande om vilka dataleverantörer]**.

### 3.5 GDPR [Läst]
- Varje **syfte** på en person ska ha dokumenterad **rättslig grund** och **samtyckeskälla** (var, när, av vem); utskick kan begränsas till personer med uttryckligt samtycke eller prenumeration; ny person får ofta tom rättslig grund för syftet "Sales and service", standardvärde kan sättas (https://docs.superoffice.com/en/security/privacy/consent-management, https://docs.superoffice.com/en/security/privacy/learn/edit-legal-base.html). SuperOffice kopplar funktionerna till de åtta rättigheterna i GDPR (https://community.superoffice.com/en/learning/best-practices-tips/gdpr/8-privacy-rights).

### 3.6 Integrationer
- Visma Administration via partner (https://www.spiris.se/integrationer/partner/superoffice-crm2-op), Visma.net via "Visma Link for SuperOffice" 49 €/site/mån (https://appstore.superoffice.com/infobridge-software-b-v-/visma-link-for-superoffice), Fortnox via "ConnectERP for Fortnox" och "Fortnox by Syncify" (https://appstore.superoffice.com/superoffice-as/connecterp-for-fortnox). Telavox visar kundinformation vid inkommande samtal (https://telavox.com/integrations/). Oneflow, Scrive, GetAccept (se 1.6).

### 3.7 Pris [Läst]
- Starter från 45 €, Core 65 €, Growth 95 €, Plus 130 €, Super 160 € per användare/mån; "Built-in GDPR tools", "API access and custom integrations", "ERP integration" för vissa ERP (https://www.superoffice.com/pricing/feature-list/). Säljguide, intressenter och offert kräver "Sales Premium" eller Growth (https://docs.superoffice.com/sv/sale/learn/index.html).

---

## 4. Membrain

Svenskgrundat, processdrivet säljsystem för komplex B2B-försäljning.

- **Objekt**: "Companies & Contacts", säljprocess per möjlighet ("Make your sales process come to life in each opportunity"), anpassningsbara processer för prospektering, säljaffärer och kundtillväxt (https://www.membrain.com/pricing). Recensenter beskriver **Sales Project** (säljprojekt) som arbetsenheten i "Active Pipeline" [Tredjepart] (https://www.g2.com/products/membrain/features).
- **Funktioner på svenska** [Tredjepart]: kontakt- och prospekthantering, pipelinehantering, lead scoring, offertkonfigurator (CPQ), digital signering och avtalshantering, ringlistor, "Ringa direkt från CRM (click-to-call)", säljdashboards, kundhälsa (health score) (https://businesswith.se/system/membrain/).
- **Pris [Läst]**: Prospecting 490 kr, Active Pipeline 690 kr, Account Growth 890 kr per användare/mån, Elevate 890 kr per coach/mån; tillägg Tickets 290 kr, Flows 190 kr, Content Hub 120 kr; API+ 4 990 kr, Automation+ 2 990 kr, Insight Engine från 1 990 kr (https://www.membrain.com/pricing).

---

## 5. Fortnox (Offert & Order, kundregistret, CRM-katalogen)

Fortnox har inget fullt CRM. Det som finns är **kundregister**, **artikelregister** och tillägget **Offert & Order**.

- Offert & Order [Läst]: skicka **offerter** till befintliga och potentiella kunder, skapa **orderbekräftelse** från accepterad offert, skicka via e-post, följa status, fakturera från order, samla ordrar på en faktura, RUT/ROT-beräkning, **restorder**, artikelregister med kundprislistor och lager; tillägg som beställs i kassan, inget pris på sidan (https://www.fortnox.se/produkt/offert-orderprogram).
- CRM-katalogen listar 53 kopplingar, bl.a. Upsales, Lime CRM, Lime Go, Sellfinity, HubSpot (två leverantörer), Pipedrive (Cloudify), Salesforce (Cloudity), Efficy/webCRM, CRMdata ("enkelt, prisvärt CRM med inbyggd svensk företagsdata"), Kundly CRM, Rekyl CRM, D365 CE (https://www.fortnox.se/integrationer/kategorier/crm). Rubriken för kategorin: "Låt CRM-system och säljstöd dela information med ditt Fortnox. Synka kunder, offert och order och fakturera direkt från Fortnox." (sökutdrag, samma URL).
- **[Antagande, se svensk-04]** Fortnox kundpost har kundnummer, organisationsnummer/personnummer, momsregistreringsnummer (VAT-nummer) och kundtyp företag/privat; det är fälten en svensk köpare väntar sig att se speglade i CRM:et.

## 6. Visma / Spiris

- **Visma Spcs heter Spiris sedan 2025**, samma bolag och orgnr; **Visma eEkonomi säljs i Sverige som "Bokföring & Fakturering"** (https://www.spiris.se/nyhetsrum/visma-spcs-byter-namn-till-spiris, https://developer.vismaonline.com/changelog/weve-changed-our-name-visma-spcs-is-now-spiris). Ett svenskt CRM bör därför skriva både "Spiris" och "Visma eEkonomi" i kopplingslistan.
- **CRM:et heter "Supereffektivt säljstöd och CRM-system"** och ingår i **Tid & Projektplanering** (fd Visma Tid Smart/Pro) [Läst]: **affärsmöjlighet** med värde och **sannolikhet**, **säljpipe** som Kanban-tavla med egna namngivna **stadier**, varje affärsmöjlighet ska ha en tidsbestämd **aktivitet** för uppföljning, **offert** i versioner med digital signering med **BankID**, vunnen affärsmöjlighet blir **projekt** (https://www.spiris.se/ekonomiplattform/tid-projektplanering/crm-saljstod).
- Pris [Läst]: Tid 269 kr/mån, Tid & Projektplanering 419 kr/mån; användarlicenser Light 49, Basic 129/139, Standard 199/259, Total 269/419 kr; e-signering från 16 kr/st; SMS-påminnelse 1 kr/sms (samma URL).
- Integrationer: Bokföring & Fakturering eller Visma Administration, API, löneunderlag (samma URL).
- "Visma Sales" som fristående produkt hittade jag inte på svenska marknaden. Spiris Byråstöd/Visma Advisor är CRM för redovisningsbyråer (https://www.visma.com/trust-centre-products/spiris-byrastodvisma-advisor).

## 7. HubSpot (som svenska småföretag möter det)

- **Objekt [Läst]**: Företag, Kontakter, Affärer, Ärenden (supportpipelinen heter "Ärende") (https://knowledge.hubspot.com/sv/object-settings/set-up-and-customize-pipelines).
- **Standardsteg för affärer [Läst]**: "Möte inbokat (20%)", "Kvalificerad att köpa (40%)", "Presentation inbokad (60%)", "Beslutsfattare köpt in (80%)", "Kontrakt skickat (90%)", "Stängd och vunnen (100%, vunnen)", "Stängd och förlorad (0%, förlorad)" (samma URL). Annan svensk hjälpartikel skriver "Avslutad – vunnen" (https://knowledge.hubspot.com/sv/get-started/generate-sales) — HubSpots svenska är maskinöversatt och inte konsekvent.
- **Vyer [Läst]**: "Sparade vyer" i tavla eller tabellvy; delning **Privat, Team, Alla, Anpassad**; behörigheter Ägare, Medarbetare, Medlem; "Avancerade filter" och snabbfilter (https://knowledge.hubspot.com/sv/records/create-and-manage-saved-views).
- **Dubbletter [Läst]**: företag jämförs på domännamn, företagsnamn, land/region, telefonnummer, bransch; kontakter på förnamn, efternamn, e-post, IP-land, telefon, postnummer, företagsnamn; Professional/Enterprise krävs; sammanslagning kan inte ångras (https://knowledge.hubspot.com/sv/records/manage-duplicate-records). Automatisk deduplicering av bolag sker på "Company domain name", och inte för bolag skapade via API (https://knowledge.hubspot.com/records/deduplication-of-records).
- **GDPR [Läst, sökutdrag]**: kontaktegenskapen "Legal basis for processing contact's data" (avtal, berättigat intresse, samtycke) (https://knowledge.hubspot.com/sv/contacts/how-can-i-track-lawful-basis-of-processing-in-hubspot).
- **Svenska fält**: inget orgnr, inget SNI, ingen bolagsform inbyggt; svenska kunder lägger till egna egenskaper eller appar (Creditsafe kräver "Business Intelligence Plus", https://ecosystem.hubspot.com/sv/marketplace/listing/creditsafe). **[Antagande]** baserat på HubSpots standardegenskaper.
- **Integrationer**: Fortnox via Resultify eller Cloudify (https://www.fortnox.se/integrationer/kategorier/crm), Telavox-app 12 $/mån (https://ecosystem.hubspot.com/marketplace/apps/flow-business-communications-196800), Oneflow kräver Sales Professional (https://ecosystem.hubspot.com/marketplace/listing/oneflow).
- **Pris [Tredjepart/sökutdrag]**: gratis för upp till 2 användare; Sales Hub Starter anges till 7 $/plats/mån på hubspot.com i sökutdraget, med 20 $ i samma kolumn (troligen månads- respektive årsfakturering, ej bekräftat) (https://www.hubspot.com/pricing/sales). Svensk kronprislista kunde inte hämtas (hubspot.se svarar inte).

## 8. Pipedrive

- **Objekt [Läst]**: **Personer**, **Organisationer**, **Affärer** (https://support.pipedrive.com/sv/article/merge-duplicates); leads heter **prospekt** och inkorgen **Prospektinkorgen** på marknadssidan (https://www.pipedrive.com/sv/features/manage-leads-deals).
- **Säljprocess [Läst]**: **faser** i en **pipeline**; **fassannolikhet** och **affärssannolikhet** (affärens vinner); **stagnation** (affär för länge i samma fas, antal dagar) (https://support.pipedrive.com/sv/article/how-can-i-customize-my-pipeline-stages); sannolikhet 0–100, vägt värde visas när man håller över affärens värde (https://support.pipedrive.com/sv/article/how-can-i-set-deal-probability); utfall **Vunnen**/**Förlorad**, affärskort visar titel, kontakt, värde, etikett, ägare (https://support.pipedrive.com/sv/article/pipeline-view).
- **Förlustorsak [Läst]**: fritext som standard, fördefinierade under "Företagsinställningar > Förlorade skäl", högst 100 (https://support.pipedrive.com/sv/article/lost-reasons).
- **Standardfaser [Antagande]**: på engelska "Qualified", "Contact Made", "Demo Scheduled", "Proposal Made", "Negotiations Started"; Pipedrives egen svenska blogg råder att döpa faser efter konkreta händelser som "Möte bokat" och "Förslag skickat" (https://pipedrive.com/sv/blog/forsaljningspipeline, sökutdrag).
- **Dubbletter [Läst]**: "Verktyg och appar" → sammanfoga dubbletter, välj primär post, "Förhandsgranska", kan inte delas igen; manuellt via "Mer (...)" → "Sammanfoga" (https://support.pipedrive.com/sv/article/merge-duplicates).
- **Pris [Läst]**: Lite 14 €, Growth 39 €, Premium 59 €, Ultimate 79 € per användarplats/mån vid årsfakturering, exkl. moms, 14 dagars test (https://www.pipedrive.com/sv/pricing).

## 9. Salesforce (Starter/Pro Suite för småföretag)

- **Pris [Läst]**: Starter Suite 250 kr/användare/mån (månads- eller årsfakturering), Pro Suite 1 000 kr/användare/mån (årsavtal); Starter innehåller "Inbyggda säljflöden och leadsdirigering", e-postkampanjer och Slack; Pro lägger till offerter och prognoser (https://www.salesforce.com/se/small-business/pricing/).
- **Termer**: marknadssidan använder "leads", "pipeline", "affärsfaser", "kundcase" (https://www.salesforce.com/se/small-business/starter/). **[Antagande]** Det svenska gränssnittet: Konton, Kontakter, Leads, Affärsmöjligheter, Fas, Uppgifter, Rapporter, Instrumentpaneler; jag har inte kunnat bekräfta etiketterna i en källa.
- **Bolagsdata**: Roaring.io säljer app för Salesforce och Dynamics 365 med nordisk bolagsdata och bevakning (https://www.roaring.io/products/salesforce-application); Creditsafe har integration mot Salesforce, Dynamics, HubSpot (https://www.creditsafe.com/global/en/Integration/crm-integration.html).

---

## 10. Jämförelse i tabellform

### 10.1 Centrala begrepp per system

| Begrepp | Lime Go | Lime CRM | Upsales | SuperOffice | Pipedrive (sv) | HubSpot (sv) | Spiris T&P |
|---|---|---|---|---|---|---|---|
| Bolag | Företag (`organization`) | Företag (`company`) | Företag (`account`) | Företag | Organisation | Företag | Kund |
| Person | Person | Person | Kontakt | Kontakt | Person | Kontakt | Kontakt |
| Affär | Affär (`deal`) | Affär (konfig.) | Möjlighet → Order | Försäljning | Affär | Affär | Affärsmöjlighet |
| Händelse | Historik | Historik (`history`), tidslinje "Activities" | Aktivitet, möte | Aktivitet | Aktivitet | Aktivitet | Aktivitet |
| Uppgift | Att göra | Att göra [Antagande] | Uppgift/aktivitet [Antagande] | Följ upp/uppgift | Aktivitet | Uppgift | Aktivitet |
| Ärende | – (Lime Connect chatt) | Ärende (`helpdesk`) | – | Begäran (Service) | – | Ärende | – |
| Urval | Filter/listor | Filter | Filter | Urval (statiskt, dynamiskt, kombinerat) | Filter | Sparad vy | – |
| Relation/status | `customerRelation` (5 värden) | konfig. | journey status | kategori/relation | – | livscykelfas | – |

### 10.2 Inbyggda svenska fält

| Fält | Lime Go | Upsales | SuperOffice | HubSpot | Pipedrive |
|---|---|---|---|---|---|
| Orgnr | Ja, `organizationNumber` [Läst] | Ja, matchnyckel [Läst, sökutdrag] | **[Antagande]** Ja, "Org.nr" på företagskortet | Nej, egen egenskap | Nej, eget fält |
| Momsnr | via ERP-synk [Antagande] | via ERP-synk [Antagande] | [Antagande] | Nej | Nej |
| SNI/bransch | via D&B [Antagande om fältnamn] | Ja, segmentering på bransch [Läst] | [Antagande] | "Bransch" (amerikansk lista) | Nej |
| Omsättning | `turnover` [Läst] | Ja [Läst] | [Antagande] | "Annual revenue" | Nej |
| Antal anställda | `numberOfEmployees` [Läst] | Ja ("Company size") [Läst] | [Antagande] | "Number of employees" | Nej |
| Bolagsform | via D&B [Antagande] | Ja ("Corporate form") [Läst] | [Antagande] | Nej | Nej |
| Koncernmoder | Ja, "Koncernstruktur på företag" (Business) [Läst] | [Antagande] | relation mellan företag [Läst] | "Parent company" | Nej |
| Kreditbetyg | Ja (Business), kvartalsvis [Läst] | [Antagande] | via app | via Creditsafe-app | Nej |

### 10.3 Pris per användare och månad (listpris, exkl. moms)

| System | Billigast | Dyrast | Källa |
|---|---|---|---|
| Lime Go | ≈400 kr (Starter, 3 anv. för 1 200 kr) | ≈900 kr (Business) | lime-technologies.com/sv/lime-go/priser/ |
| Lime CRM | ≈650 kr [Tredjepart] | – | businesswith.se |
| Upsales | ej publicerat (£49 enligt G2) | – | g2.com |
| SuperOffice | 45 € | 160 € | superoffice.com/pricing/feature-list/ |
| Membrain | 490 kr | 890 kr | membrain.com/pricing |
| Pipedrive | 14 € | 79 € | pipedrive.com/sv/pricing |
| HubSpot Sales Hub | 0 (2 anv.) | Starter 7–20 $ (sökutdrag) | hubspot.com/pricing/sales |
| Salesforce | 250 kr | 1 000 kr | salesforce.com/se/small-business/pricing/ |
| Spiris Tid & Projektplanering | 419 kr/mån + licens 49–419 kr | – | spiris.se |

---

## 11. Integrationer som en svensk köpare väntar sig

| Kategori | Vad som är belagt | Källa |
|---|---|---|
| Ekonomisystem | Fortnox (alla svenska CRM i katalogen), Visma eEkonomi/Bokföring & Fakturering, Visma Administration, Visma.net, **BL Administration** (Björn Lundén) | fortnox.se/integrationer/kategorier/crm; lime-technologies.com/lime-crm/solutions/erp |
| Mönster för ERP-synk | kunder synkas tvåvägs med kundnummer; vunnen affär → order/faktura; fakturor visas på bolaget | Upsales/Fortnox-sidan; Lime ERP-sidan; Lime Go-FAQ |
| Telefoni | Telavox: klick-för-att-ringa, uppslag på inkommande nummer, för SuperOffice, Lime, Pipedrive, HubSpot | telavox.com/integrations/ |
| Telefoni, övrigt | Dstny (fd Telia Touchpoint-segmentet [Antagande]) skriver samtalssammanfattningar till Lime-historik | dstny.se/partnerhelp/lime-crm-dstny-conversational-intelligence |
| E-signering | Oneflow (Lime CRM, Upsales, SuperOffice, HubSpot), Scrive (Lime CRM, SuperOffice, Upsales, Pipedrive, Salesforce CPQ), GetAccept (Lime, HubSpot, Upsales, SuperOffice) | oneflow.com/integrations/…; scrive.com/…/area/crm; help.getaccept.com |
| BankID | Signering av offert med BankID i Spiris | spiris.se/…/crm-saljstod |
| Bolagsdata | Dun & Bradstreet (Lime Go, Upsales "Bisnode"), Roaring (Salesforce, Dynamics), Creditsafe (HubSpot, Salesforce, Dynamics) | se §1.4, §2.4, §9 |
| Automation | Zapier i Lime Go alla planer | lime-technologies.com/sv/lime-go/priser/ |
| Ej belagt här | Microsoft 365/Outlook, Google Workspace, Teams, Soluno, 46elks, UC, Make | **[Antagande]** Outlook-/Gmail-tillägg och kalendersynk är standard hos alla ovan; ej verifierat i källa i dag |

---

## 12. URL:er med stora produktskärmbilder (för fotografering)

Kontrollerade 2026-11-25 med curl (HTTP-kod och antal `<img>`-taggar i HTML). Sidor markerade 403 blockerar skript men lästes med webbhämtaren; öppna dem i vanlig webbläsare.

| # | System | URL | Svar | Vad bilden visar |
|---|---|---|---|---|
| 1 | Pipedrive | https://support.pipedrive.com/sv/article/pipeline-view | 200, 16 img | Pipeline-vyn med faser, affärskort, gif där affär dras mellan faser och markeras Vunnen/Förlorad, filtermenyn. |
| 2 | Pipedrive | https://support.pipedrive.com/sv/article/how-can-i-customize-my-pipeline-stages | 200, 12 img | Redigering av pipelinefaser, fassannolikhet och stagnation. |
| 3 | Pipedrive | https://support.pipedrive.com/sv/article/deal-detail-view | 200, 16 img | Affärens detaljvy med sammanfattningspanel och tidslinje (titel enligt URL, bilder ej granskade). |
| 4 | Pipedrive | https://support.pipedrive.com/sv/article/lost-reasons | 200, 5 img | Dialogen för förlustorsak och inställningen "Förlorade skäl". |
| 5 | Pipedrive | https://support.pipedrive.com/sv/article/merge-duplicates | 200, 7 img | Sammanfogning av dubbletter med förhandsgranskning. |
| 6 | Pipedrive | https://www.pipedrive.com/sv/features/manage-leads-deals | 200, 22 img | Marknadsbilder av Prospektinkorgen och affärshantering. |
| 7 | HubSpot | https://knowledge.hubspot.com/sv/object-settings/set-up-and-customize-pipelines | 200, 8 img | Gif där affärssteg läggs till med sannolikhet; editor för villkorlig steglogik. |
| 8 | HubSpot | https://knowledge.hubspot.com/sv/records/create-and-manage-saved-views | 200, 7 img | Gif av affärer i tavelvy som filtreras och sparas som vy. |
| 9 | HubSpot | https://knowledge.hubspot.com/sv/records/view-and-filter-records | 200, 10 img | Postindex (tabell) med filter och vyflikar. |
| 10 | HubSpot | https://knowledge.hubspot.com/sv/records/manage-duplicate-records | 200, 15 img | Dialog för sammanslagning av enskilda och bulkdubbletter. |
| 11 | HubSpot | https://knowledge.hubspot.com/sv/deals/create-deals | 200, 11 img | Formuläret "Skapa affär" och affärsposten. |
| 12 | HubSpot | https://knowledge.hubspot.com/sv/contacts/how-can-i-track-lawful-basis-of-processing-in-hubspot | 200, 8 img | Egenskapen för rättslig grund på kontakten. |
| 13 | HubSpot | https://www.hubspot.com/products/crm | 200, 62 img | Marknadsbilder av CRM-översikten. |
| 14 | SuperOffice | https://docs.superoffice.com/sv/sale/learn/index.html | 200, 7 img | Försäljningsskärmen i tavlevy, försäljningskortet med detaljkort, kalendervyn. |
| 15 | SuperOffice | https://docs.superoffice.com/sv/search-options/selection/learn/index.html | 200, 5 img | Urval av försäljningar grupperat med summerade belopp. |
| 16 | SuperOffice | https://docs.superoffice.com/sv/company/learn/index.html | 200, 5 img | Företagskortet (titel enligt URL, bilder ej granskade). |
| 17 | SuperOffice | https://docs.superoffice.com/sv/learn/basics/index.html | 200, 6 img | Grundvyerna Företag, Kontakt, Navigator. |
| 18 | SuperOffice | https://docs.superoffice.com/en/company/learn/merge-companies.html | 200, 5 img | Dialogen "Merge companies". |
| 19 | SuperOffice | https://docs.superoffice.com/en/security/privacy/learn/edit-legal-base.html | 200, 13 img | Redigering av rättslig grund och samtyckeskälla per syfte. |
| 20 | SuperOffice | https://docs.superoffice.com/en/sale/learn/update.html | 200, 7 img | Uppdatering av försäljning, status Stalled/Uppskjuten. |
| 21 | Lime CRM | https://platform.docs.lime-crm.com/en/latest/configuration/webclient/activities | 200, 11 img | Tidslinjen "Activities" med Standard-, Minimal- och Emphasized-poster och chips. |
| 22 | Lime Go | https://www.lime-technologies.com/sv/lime-go/priser/ | 403 för skript, läst | Prisplaner och tilläggslista (inga stora produktbilder). |
| 23 | Lime Go | https://www.lime-technologies.com/en/products/lime-go/use-cases/manage-customers/ | 403 för skript | Kundhantering i Lime Go (ej granskad; GDPR-sidan saknade produktbilder enligt webbhämtaren). |
| 24 | Upsales | https://upsales.com/sv/ | 200, 7 img | Marknadsbilder av AI-insikter och säljtavla. |
| 25 | Upsales | https://support.upsales.com/hc/en-us/articles/5951002703889-Q-How-do-users-choose-the-probability-for-an-opportunity-stage | 403 för skript och webbhämtare | Inställning av sannolikhet per steg. Öppna manuellt. |
| 26 | Spiris | https://www.spiris.se/ekonomiplattform/tid-projektplanering/crm-saljstod | 200, 24 img | Kanban-tavla för affärsmöjligheter och offert med BankID-signering. |
| 27 | Fortnox | https://www.fortnox.se/produkt/offert-orderprogram | 200, 13 img | Offert- och orderflödet i Fortnox. |
| 28 | Salesforce | https://www.salesforce.com/se/small-business/starter/ | 200, 31 img | Tre skärmbilder per område: pipeline med affärsfaser, servicekonsol, segment. |
| 29 | Membrain | https://www.membrain.com/ | 200, 19 img | Processdriven pipeline och säljprojekt. |
| 30 | Pipedrive | https://www.pipedrive.com/sv | 200, 48 img | Startsidans produktbilder av pipeline-tavlan. |

Sidor som gav 404 och inte ska användas: `pipedrive.com/sv/features/sales-pipeline`, `knowledge.hubspot.com/sv/records/use-the-board-view`, `upsales.com/product/advanced-order-logic`, `upsales.com/sv/priser`.

---

## 13. Det här väntar sig en svensk säljare av ett CRM

1. **Skriv orgnr, få bolaget.** Namn, adress, bolagsform, SNI/bransch, omsättning, antal anställda, VD och koncernmoder fylls i från en registerkälla och hålls uppdaterade (Lime Go nattligen, Upsales Company Data Hub).
2. **Orgnr som unik nyckel**, med varning för dubblett innan posten sparas, och sammanslagning med val av primär post (Upsales, SuperOffice, Pipedrive, HubSpot har alla det).
3. **En tydlig kundrelation på bolaget**: kund, tidigare kund, prospekt, pågående, ej aktuell. Den styr listor och utskick (Lime Go `customerRelation`).
4. **Ansvarig säljare per bolag** (`responsibleCoworker`) och "Mina"-vyer: "Min öppna försäljning", "Mina företag" (SuperOffice fastnålade urval, HubSpot privat/team-vyer).
5. **Pipeline som tavla med egna steg**, sannolikhet per steg, värde i kronor, vägt värde, vunnen/förlorad och **förlustorsak från lista**.
6. **Varje affär har en nästa aktivitet**; affärer utan eller med förfallen aktivitet markeras röda (SuperOffice, Spiris).
7. **Historik/tidslinje på bolaget och personen** där samtal, mejl, möten, anteckningar, dokument, offerter och ärenden syns i en ström.
8. **Urval/sparade vyer** som kan delas, användas för utskick och massåtgärder (SuperOffice statiskt/dynamiskt urval).
9. **Fortnox- eller Visma-koppling**: kunder med kundnummer, vunnen affär → order/faktura, fakturor och obetalt synligt på bolaget.
10. **Telefoni**: klick-för-att-ringa och kundkort som öppnas vid inkommande samtal (Telavox).
11. **Offert med e-signering** via Oneflow, Scrive, GetAccept eller BankID.
12. **GDPR inbyggt**: rättslig grund per person och syfte, samtyckeskälla och datum, export av registerutdrag, anonymisering/gallring med slutdatum, spärr "kontakta inte".
13. **Svenska format**: kronor med mellanslag som tusentalsavgränsare och komma som decimaltecken, datum ÅÅÅÅ-MM-DD, postnummer "123 45", telefon +46/07x, orgnr "556677-8899".
14. **Svenskt språk i hela gränssnittet** och svensk support (Upsales marknadsför median 3 minuters svarstid, https://upsales.com/sv/).
15. **Pris per användare och månad i kronor**, med årsavtal; listpriset för svenska alternativ ligger på 400–900 kr.

## 14. Det här skiljer mot en amerikansk förlaga som Twenty CRM

**[Antagande om Twenty]**: Twentys datamodell beskrivs i `docs/crm/underlag/twenty-app-kartlaggning.md` och svensk-04 §7 (rad 794 och framåt); jämförelsen nedan bygger på det generella amerikanska mönstret (HubSpot, Salesforce), inte på en ny läsning av Twenty.

| Område | Amerikansk förlaga | Svenskt CRM |
|---|---|---|
| Bolagsnyckel | domännamn (HubSpot deduplicerar på "Company domain name") | organisationsnummer; domän som andranyckel |
| Personnyckel | e-post | e-post, men personen hör till ett bolag med orgnr; telefon matchas vid samtal |
| Bolagsfält | Employees, ARR, Address (US), LinkedIn, Ideal Customer Profile | orgnr, momsnr, bolagsform (AB, HB, KB, EF), SNI, omsättning i kr, antal anställda, koncernmoder, kreditbetyg, län/kommun, F-skatt [Antagande om de två sista] |
| Enskild firma | finns inte som begrepp | eget fall: orgnr = personnummer, persondata, NIX/ringspärr (Snajps utkast har `enskild_firma`, `…_153_crm_grund.sql:76`) |
| Relation | lifecycle stage (subscriber, lead, MQL, SQL, opportunity, customer) | kundrelation (kund, tidigare kund, prospekt, pågående, ej aktuell) |
| Säljsteg | engelska, ofta Qualified/Meeting/Proposal/Customer | svenska, avslut med "Vunnen"/"Förlorad"/"Uppskjuten", förlustorsak |
| Belopp | USD, punkt som decimal | SEK, "12 500 kr", komma som decimal, moms (25 %) separat |
| Adress | street, city, state, zip | gatuadress, c/o, postnummer (5 siffror "123 45"), postort, land |
| Vyer | tabell + kanban, "Favorites" | lista, tavla, kalender, karta (Lime Go), **urval** (statiskt/dynamiskt) för utskick |
| Register | Clearbit/Apollo-berikning | Bolagsverket/SCB via D&B, Roaring, Creditsafe, UC |
| Kopplingar | Gmail, Google Calendar, Slack, Stripe, Zapier | Fortnox, Visma/Spiris, BL Administration, Outlook/Teams, Telavox, Oneflow/Scrive, BankID |
| GDPR | e-post-opt-out, "Do not contact" | rättslig grund per syfte, samtyckeskälla, registerutdrag, gallring/anonymisering, NIX-spärr för telefonförsäljning till enskilda |

### 14.1 Förslag på svensk term per centralt begrepp

| Engelska (Twenty) | Förslag | Skäl och belägg |
|---|---|---|
| Company | **Bolag** (UI), "Företag" som synonym i sök | Lime/HubSpot/SuperOffice säger "Företag"; Snajp säger redan "bolag" och tabellen heter `crm_bolag` (`…_153_crm_grund.sql:69`). "Bolag" är kortare och stämmer med orgnr-tänket. |
| Person | **Person** | Lime, Pipedrive; "Kontakt" (Upsales, SuperOffice, HubSpot) kan användas för rollen i ett bolag. Tabellen heter `crm_personer` (rad 122). |
| Opportunity | **Affär** | Lime Go, Pipedrive, HubSpot. "Affärsmöjlighet" (Spiris) är längre; "Försäljning" (SuperOffice) krockar med rapportbegreppet. |
| Task | **Att göra** (lista), **uppgift** (enskild) | Lime Go "att göra-lista"; Snajp har redan "Återkoppling" för samtal. |
| Note | **Anteckning** | SuperOffice "Anteckningar"; Lime "historiknotering". |
| Workflow | **Automatisering** | Pipedrive/Salesforce marknadssidor; "flöde" kan vara synonym. |
| View | **Vy**; sparad vy = **urval** när den används för utskick | HubSpot "Sparade vyer", SuperOffice "Urval". |
| Pipeline stage | **Steg** (i en **säljprocess**/pipeline) | HubSpot "affärssteg", Pipedrive "fas", Spiris "stadium". "Steg" är kortast och tydligast. |
| Record | **Post** | HubSpot "poster", SuperOffice "post". |
| Workspace | **Konto** (kundens CRM) | Det är tenanten; "arbetsyta" är ovant för säljare. |
| Member | **Användare** (eller **medarbetare** som ansvarig) | Lime "coworker"; licenser säljs "per användare". |
| Role | **Roll** och **behörighet** | SuperOffice "funktionell rättighet". |
| Favorite | **Fastnålad** / **Mina favoriter** | SuperOffice "fastnålade urval". |
| Timeline | **Historik** (på kortet), tidslinje i dokumentation | Lime "Historik", Lime CRM "Activities". |
| Webhook | **Webhook** (behålls), förklarat som "händelseavisering" | Teknisk term, inget svenskt CRM översätter den. |
| API key | **API-nyckel** | Etablerat. |
| (extra) Customer relation | **Kundrelation** med värdena Kund, Tidigare kund, Prospekt, Pågående, Ej aktuell | Lime Go `customerRelation`; Snajps utkast saknar "pågående" och "ej aktuell" (`…_153_crm_grund.sql:107`). |
| (extra) Lost reason | **Förlustorsak** | Pipedrive "Förlorade skäl"; SuperOffice "Orsak". |
| (extra) Weighted value | **Vägt värde** | Pipedrive. |
| (extra) Owner | **Ansvarig** | Lime `responsibleCoworker`, Snajps `ansvarig` (rad 94). |

## 15. Luckor och vad som bör verifieras visuellt

- Lime Go:s svenska UI-etiketter för relation, affärssteg och historiktyper (inga offentliga källor; fotografera inloggad Lime Go-demo).
- Upsales svenska fältetiketter och standardsteg på svenska (hjälpcentret är engelskt och blockerar skript).
- SuperOffice företagskortets exakta fält (Org.nr, Kategori, Kod, Nummer, Ansvarig) — inte bekräftade i läst källa.
- Pipedrives svenska standardfaser och Salesforce svenska objektnamn.
- HubSpot SEK-priser (hubspot.se svarar inte, hubspot.com-sidan renderas med JavaScript).
- Telefoni utöver Telavox/Dstny (Telia Touchpoint, Soluno, 46elks) och Microsoft 365/Google-kopplingar: inte belagda i dag.
