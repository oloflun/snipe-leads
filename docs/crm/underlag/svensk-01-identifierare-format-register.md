# Svenska identifierare, format och register för Snajp CRM

Underlag 2026-11-25. Research mot primärkällor (Skatteverket, SCB, PTS,
Postnummerrådet/PostNord, Bolagsverket, EU-kommissionen/VIES, Peppol/Digg,
Isof/Språkrådet) och en genomgång av hur repot gör i dag. Allt som står om
koden har fil:rad. Allt som inte kunde läsas i primärkälla är märkt
**[ej verifierat]** eller **[antagande]**.

Läsordning för den som bygger: avsnitt 0 (beslut att ta), avsnitt 9 (vad i
repot som krockar), avsnitt 8 (fältlistan), avsnitt 10 (färdig kod).

---

## 0. Det viktigaste först

1. **Nyckeln är tio siffror.** Organisationsnummer lagras som `NNNNNNNNNN`
   (ingen bindestreck, inget `16`-prefix) och visas `NNNNNN-NNNN`. SCB:s
   12-siffriga `PeOrgNr` har `16` framför juridiska personers nummer och
   `19`/`20` framför enskilda näringsidkares personnummer (SCB, variabel
   PeOrgNr). `16` + ett personnummer, eller `19`/`20` + ett orgnr, är alltid
   fel och ska nekas, inte tyst skalas av.
2. **Tredje siffran < 2 = personnummer eller samordningsnummer** (enskild
   firma). Det är en personuppgift. Samordningsnummer har dag + 60.
   Juridisk form går **inte** att läsa ur numret (SKV 709): första siffran
   är bara ett gruppnummer. Hämta koden för juridisk form (21, 31, 49 …)
   ur register.
3. **Momsnummer = `SE` + de tio siffrorna + `01`.** Att det går att härleda
   betyder inte att bolaget är momsregistrerat. Det avgör VIES eller SCB:s
   `Momsstatus`.
4. **Telefon lagras i E.164 (`+46701234567`) och visas `070-123 45 67`.**
   Allt annat gör att ett nummer från Buddys telefonisystem inte matchar
   samma nummer i en leadslista. Sedan **2026-10-01 är även 078A (A = 0–2,
   4–9) mobilnummer**, och 0783 är GSM-R (PTS, nummerplanen 2026-05-18).
5. **Postnummer: fem siffror, områden 10–98, visas `NNN NN`.** Ett postnummer
   kan beröra flera län och kommuner (Postnummerrådet): härled aldrig län ur
   postnummer när SCB:s säteskommun finns.
6. **SNI: SNI 2025 gäller sedan 8 december 2025.** Ett bolag kan ha upp till
   fem SNI-koder i SCB:s register, rangordnade (Bransch1 = huvudnäringsgren).
   Lagra lista + version (`sni2007`/`sni2025`), inte en enda sträng.
7. **Gratis registerdata finns nu:** SCB:s företagsregister-API är
   avgiftsfritt sedan 26 juni 2025 (API-nyckel, 5 000 rader/anrop, 5 anrop/s),
   och Bolagsverkets värdefulla datamängder är avgiftsfria. SCB bär dessutom
   **reklamspärr och NIX-markering** per företag, vilket ett CRM med
   ringlistor bör läsa.
8. **sv-SE i `Intl` använder hårt blanksteg (U+00A0) som tusentalsavgränsare
   och U+2212 som minustecken** (uppmätt i Node 24.11.0). Formaterade strängar
   går inte att läsa tillbaka med `Number()`, och tester som jämför mot
   `"1 234,56 kr"` med vanligt mellanslag faller.
9. **Repot har minst nio olika orgnr-normaliseringar** som inte är överens om
   prefix och personnummer, och den nya `app/crm/falt.py` (ocommittad) slår
   ihop telefonanknytningar med numret (`08-678 55 00 ankn. 123` →
   `+4686785500123`). Se avsnitt 9.

---

## 1. Organisationsnummer, personnummer, samordningsnummer

### 1.1 Konstruktion (läst i primärkälla)

Skatteverkets broschyr SKV 709 utgåva 8 (sep 2006), sid 1:

- Tio siffror, som personnummer. **"Den tredje siffran är alltid lägst en
  tvåa"** för att undvika förväxling med personnummer.
- Siffra 1 = **G, gruppnummer**; siffra 2–9 = ordningsnummer; siffra 10 =
  **K, kontrollsiffra**.
- **Juridisk form ingår inte i numret.** Ordagrant: "koden för juridisk form
  inte ingår i ett organisationsnummer. Man kan således inte utläsa den
  juridiska formen av enbart organisationsnumret."
- Numret är beständigt och unikt; två identiska nummer förekommer inte.
- Lagstöd: lag (1974:174) om identitetsbeteckning för juridiska personer m.fl.
- Skatteverkets organisationsnummerregister innehåller: orgnr, namn, adress,
  geografiska koder för säte (län och kommun), kod för juridisk form,
  konkurs-/likvidationsmarkering, tidpunkt för registrering/avregistrering.
  Inga firmatecknare.

Källa: https://docs.swedenconnect.se/technical-framework/mirror/skv/skv709-8.pdf
(spegel av SKV 709; Skatteverkets egen sida om orgnr:
https://skatteverket.se/foretag/drivaforetag/startaochregistrera/organisationsnummer.4.361dc8c15312eff6fd235d1.html)

### 1.2 Gruppnummer (första siffran)

SKV 709 namnger siffran "gruppnummer" men publicerar ingen tabell i
broschyren. Tabellen nedan finns hos Fortnox och Spiris (sekundärkällor) och
används av repot (`snajp-support/app/leads/orgnr.py:37-44`). **Använd den bara
som ledtext, aldrig för att avgöra juridisk form.**

| Första siffra | Vägledande kategori |
|---|---|
| 2 | Stat, region, kommun, församling |
| 5 | Aktiebolag |
| 6 | Enkelt bolag |
| 7 | Ekonomisk förening, bostadsrättsförening |
| 8 | Ideell förening, stiftelse |
| 9 | Handelsbolag, kommanditbolag |
| 1, 3, 4 | **[ej verifierat]** Ingen primärkälla hittad (ofta uppgivet: 1 dödsbon, 3 utländska). |

Källor: https://www.fortnox.se/fortnox-foretagsguide/ekonomisk-ordlista/organisationsnummer,
https://www.spiris.se/blogg/foretagsstart/vad-ar-organisationsnummer

### 1.3 Kontrollsiffran: Luhn (modulus 10), fullständig algoritm

Samma algoritm som Bankgirot dokumenterar för bankgiro/OCR
(https://www.bankgirot.se/globalassets/dokument/anvandarmanualer/10-modul.pdf).

För de nio första siffrorna d1…d9:

1. Multiplicera d1, d3, d5, d7, d9 med 2 och d2, d4, d6, d8 med 1
   (vikterna 2-1-2-1-2-1-2-1-2 från vänster).
2. Är en produkt tvåsiffrig: ersätt den med summan av sina siffror
   (14 → 1+4 = 5), vilket är samma sak som produkt − 9.
3. Summera allt till S.
4. Kontrollsiffran K = (10 − (S mod 10)) mod 10.

Kontroll av ett helt tiosiffrigt nummer: räkna från höger, dubbla varannan
siffra med start på den **näst sista**, summera; summan ska vara delbar med 10.

**Räknat exempel, Skatteverkets orgnr 202100-5448** (Peppol-adressen
0007:2021005448, se 5.6):

| Siffra | 2 | 0 | 2 | 1 | 0 | 0 | 5 | 4 | 4 |
|---|---|---|---|---|---|---|---|---|---|
| Vikt | 2 | 1 | 2 | 1 | 2 | 1 | 2 | 1 | 2 |
| Produkt | 4 | 0 | 4 | 1 | 0 | 0 | 10 | 4 | 8 |
| Siffersumma | 4 | 0 | 4 | 1 | 0 | 0 | 1 | 4 | 8 |

S = 22, K = (10 − 2) mod 10 = **8** → 202100-544**8**. Stämmer.

Vad kontrollen fångar: en felskriven siffra och de flesta omkastningar av två
grannsiffror (`2021005484` faller, se testvektorerna). Vad den inte fångar:
att numret finns. Det kräver register (avsnitt 7).

### 1.4 Testvektorer (alla körda, avsnitt 10.3)

| Indata | Väntat | Varför |
|---|---|---|
| `202100-5448` | giltigt, grupp 2 | Skatteverket (Peppol-id 0007:2021005448) |
| `202100-6099` | giltigt | Transportstyrelsen (Peppol-id 0007:2021006099) |
| `556824-9022` | giltigt, grupp 5 | Exemplet i repot, `orgnr.py:57` |
| `16202100-5448` | giltigt → `2021005448` | SCB:s PeOrgNr-form |
| `SE202100544801` | giltigt → `2021005448` | momsnummer som indata |
| `202100-5449` | fel kontrollsiffra | en siffra fel |
| `2021005484` | fel kontrollsiffra | två grannsiffror omkastade |
| `172021005448` | okänt prefix | bara 16/18/19/20 finns |
| `161212121212` | fel | 16 + personnummer går inte |
| `192021005448` | fel | sekel + orgnr går inte |
| `121212-1212` | personnummer (nekas som orgnr) | Skatteverkets klassiska testnummer |
| `701063-2391` | samordningsnummer | Skatteverkets eget exempel (dag 63 = 3:e) |

### 1.5 Personnummer och samordningsnummer (enskild firma)

- **Personnummer:** sex siffror födelsetid (ÅÅMMDD), bindestreck,
  tresiffrigt födelsenummer, kontrollsiffra. Bindestrecket byts mot `+` det år
  personen fyller 100. Näst sista siffran är udda för man, jämn för kvinna
  (juridiskt kön). "Antalet födelsenummer är begränsat": den som inte får ett
  kan få ett nummer med närliggande födelsedag, så **validera inte
  födelsedatumet hårt** utöver månad 01–12 och dag 01–31.
  Källa: https://www.skatteverket.se/privat/folkbokforing/personnummer
- **Samordningsnummer:** som personnummer men **dagen + 60** (3 oktober 1970
  → `701063-2391`). Har identitetsnivå (styrkt, sannolik, osäker) och kan bli
  vilande efter fem år. Ersätts av personnummer om personen folkbokförs.
  Källa: https://skatteverket.se/privat/folkbokforing/samordningsnummer
- **12-siffrig form:** SCB skriver `19`/`20` framför (`PeOrgNr`, SCB:s
  variabelbeskrivning sid 19). Repot godtar även `18` (`lib/leads/importvarden.ts:65`).
- **Enskild firma har inget eget organisationsnummer**: näringsidkaren
  identifieras med sitt personnummer (SCB: "För fysiska personer, enskilda
  näringsidkare, motsvaras PeOrgNr av personnumret"). Juridisk form-kod 10
  "Fysiska personer" i SCB:s register.
- **Varför det är en personuppgift:** numret identifierar en fysisk person
  direkt. Därför: egen markering (`enskild_firma = true`), aldrig i URL:er,
  loggar, CSV-export till tredje part eller i webbpoolen; maskeras i
  listvyer. Repot har redan regeln för webbpoolen (`webbpool.py:175-181`) och
  utskick (`forfilter.py:25-34`, marknadsföringslagen 19 §).
- **Allabolag** visar en enskild firmas personnummer med löpnummer efter
  (14 siffror; `allabolag.py:358-364`). Repot för inte numret vidare.

Källa SCB: https://www.scb.se/contentassets/8a8eb5c3d45f461ea93482f8e8d4de4f/variabelbeskrivning-api.pdf

### 1.6 Vem tilldelar (Skatteverket + SKV 709 sid 2)

- **Bolagsverket:** aktiebolag, bostadsrättsföreningar, ekonomiska föreningar,
  handelsbolag, kommanditbolag, europabolag, europakooperativ, bank- och
  försäkringsaktiebolag, sparbanker, utländska företags filialer m.fl.
- **Skatteverket:** enkla bolag, partrederier, ideella föreningar,
  familjestiftelser, övriga stiftelser och fonder, oskiftade dödsbon,
  utländska juridiska personer.
- **SCB:** kommuner, regioner, kommunalförbund, statliga myndigheter,
  allmänna försäkringskassor.
- **Lantmäteriet:** samfällighets- och vägföreningar. **Länsstyrelsen:**
  vattenförbund. **IAF:** arbetslöshetskassor. **Kammarkollegiet:**
  registrerade trossamfund. **Finansinspektionen:** understödsföreningar
  (SKV 709).

---

## 2. Momsregistreringsnummer (VAT-nummer)

### 2.1 Format

- `SE` + tolv siffror, **de två sista alltid `01`**. De tio första är
  organisationsnumret, eller personnumret för en enskild näringsidkare.
  Skrivs utan bindestreck: orgnr 999999-9999 → `SE999999999901`.
  Källor: https://www.skatteverket.se/foretag/moms/saljavarorochtjanster/forsaljningtillandraeulander/kontrolleramomsregistreringsnummervatnummer/momsregistreringsnummer.4.18e1b10334ebe8bc80002649.html
  och Skatteverkets tabell https://www.skatteverket.se/download/18.18e1b10334ebe8bc8000114731/1708608240316/bilaga_9.pdf
  (lästa via sökresultatens utdrag; sidorna själva inte hämtade).
- **Härledning:** `SE{orgnr10}01`. Detta är formen, inte ett bevis på
  momsregistrering. Kanonisk lagring: versaler, inga mellanrum.
- Utländska momsnummer: två bokstäver landskod + landets eget format.
  Skatteverket validerar inte andra länders format; repot säger "kan inte
  avgöras" (`kvitton/kontrollsiffror.py:74-83` returnerar `None`).

### 2.2 VIES-kontroll

- Skatteverket: använd **bara** EU-kommissionens VIES för att visa att en
  köpare var momsregistrerad; bekräftelser från andra webbverktyg godtas inte.
  Telefon 0771-567 567 som alternativ.
  https://www.skatteverket.se/servicelankar/otherlanguages/englishengelska/businessesandemployers/startingandrunningaswedishbusiness/vat/checkingvatnumbers.4.70685bee19c85dd5dd029eb.html
- **SOAP-tjänsten** (WSDL läst):
  https://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl,
  endpoint `https://ec.europa.eu/taxation_customs/vies/services/checkVatService`.
  - `checkVat(countryCode, vatNumber)` → `countryCode, vatNumber, requestDate,
    valid, name?, address?`.
  - `checkVatApprox(countryCode, vatNumber, traderName?, traderCompanyType?,
    traderStreet?, traderPostcode?, traderCity?, requesterCountryCode?,
    requesterVatNumber?)` → samma plus `trader*Match` (1 giltig, 2 ogiltig,
    3 ej behandlad) och `requestIdentifier` (spårbart bevis på kontrollen när
    begärarens eget momsnummer skickas med).
  - Fel (faultstring): `INVALID_INPUT`, `GLOBAL_MAX_CONCURRENT_REQ`,
    `MS_MAX_CONCURRENT_REQ`, `SERVICE_UNAVAILABLE`, `MS_UNAVAILABLE`, `TIMEOUT`.
- **REST:** EU publicerar också ett REST-API under
  `https://ec.europa.eu/taxation_customs/vies/rest-api/…` **[ej verifierat]**,
  dokumentationssidan renderas i JavaScript och gick inte att läsa.
- **Begränsningar att bygga för:**
  1. Tjänsten är beroende av varje lands system; `MS_UNAVAILABLE` och
     `TIMEOUT` är normala. Köa och försök igen, visa aldrig "ogiltigt" för ett
     tekniskt fel.
  2. Namn och adress returneras inte för alla länder (dataskydd). EU:s
     vägledning: myndigheterna bekräftar bara om angivet namn/adress stämmer.
     https://europa.eu/youreurope/vies_en. För Sverige är läget oklart i
     källorna **[ej verifierat]**.
  3. Samtidighetsspärrar (`*_MAX_CONCURRENT_REQ`): kör kontroller seriellt,
     inte i en burst vid en stor kundsynk.
  4. VIES säger bara "giltigt för EU-handel i dag". Spara `requestDate` och
     `requestIdentifier` med resultatet.

---

## 3. Bolagsformer och koder för juridisk form

Två kodsystem finns: **Skatteverkets/SCB:s tvåsiffriga kod för juridisk form**
(maskinläsbar, i SCB:s API och Skatteverkets register) och
**Bolagsverkets organisationsform** (namn som "Aktiebolag", "Handelsbolag").
Lagra koden och visa namnet.

### 3.1 Kod för juridisk form (SCB:s variabelbeskrivning sid 15–17, läst)

| Kod | Juridisk form | Vanlig förkortning |
|---|---|---|
| 10 | Fysiska personer (enskild näringsidkare) | EF |
| 21 | Enkla bolag | – |
| 22 | Partrederier | – |
| 23 | Värdepappersfonder | – |
| 31 | Handelsbolag, kommanditbolag | HB, KB |
| 32 | Gruvbolag | – |
| 41 | Bankaktiebolag | – |
| 42 | Försäkringsaktiebolag | – |
| 43 | Europabolag | SE |
| 49 | Övriga aktiebolag | AB |
| 51 | Ekonomiska föreningar | EK (ek. för.) |
| 53 | Bostadsrättsföreningar | BRF |
| 54 | Kooperativ hyresrättsförening | – |
| 55 | Europakooperativ, grupperingar (EGTS, EEIG) | – |
| 61 | Ideella föreningar | – |
| 62 | Samfälligheter | – |
| 63 | Registrerade trossamfund | – |
| 71 | Familjestiftelser | – |
| 72 | Övriga stiftelser och fonder | – |
| 81 | Statliga enheter | – |
| 82 | Kommuner | – |
| 83 | Kommunalförbund | – |
| 84 | Regioner | – |
| 85 | Allmänna försäkringskassor | – |
| 87 | Offentliga korporationer och anstalter | – |
| 88 | Hypoteksföreningar | – |
| 89 | Regionala statliga myndigheter | – |
| 91 | Oskiftade dödsbon | – |
| 92 | Ömsesidiga försäkringsbolag | – |
| 93 | Sparbanker | – |
| 94 | Understöds-, försäkringsföreningar | – |
| 95 | Arbetslöshetskassor | – |
| 96 | **Utländska juridiska personer** (inkl. filial: se nedan) | – |
| 98 | Övriga svenska juridiska personer enligt särskild lag | – |
| 99 | Juridisk form ej utredd | – |

Samma lista (utom 10 och 23) i SKV 709 sid 3. **Filial:** utländska företags
filialer registreras hos Bolagsverket och får eget orgnr (SKV 709 sid 2);
vilken kod filialen får i SCB-registret framgår inte av de lästa källorna
**[ej verifierat]**, 96 är troligast.

Källa: https://www.scb.se/contentassets/8a8eb5c3d45f461ea93482f8e8d4de4f/variabelbeskrivning-api.pdf

### 3.2 Status hos Bolagsverket (SCB-variabel, sid 23–25, läst)

`0` normalläge; `11–13` ackord; `20` konkurs inledd, `21` konkurs avslutad,
`22` avslutad med överskott, `24` upphävd; `31–35` likvidation (31 avslutad,
32 beslutad, 33 fortsätter, 34 upphör, 35 upphävd); `36`, `37` avfört;
`40–49` fusion; `50–64` avförd/avregistrerad av olika skäl; `70–74` avfört;
`75–78` ombildning; `80–82` företagsrekonstruktion; `85–87` resolution;
`90–91` delning; `99` övertagande pågår. Enheter som inte registreras av
Bolagsverket (t.ex. juridisk form 10) har alltid 0.

**För CRM:et:** lagra koden, visa text, och låt `20`, `32`, `37`, `41`, `51`,
`52` osv. sätta bolaget som inaktivt. Repot gör detta i dag med fritext:
`allabolag._status` (`allabolag.py:334-347`) och regel 19 (avvecklade kastas).

### 3.3 Företagsstatus i SCB (sid 14)

`Företagsstatus`: `0` aldrig verksam, `1` verksam (registrerad för moms,
gruppmoms, F-skatt och/eller som arbetsgivare), `9` ej verksam.

---

## 4. SNI (Standard för svensk näringsgrensindelning)

### 4.1 Vilken version gäller

- **SNI 2025 gäller i samhället från och med 8 december 2025** och ersätter
  SNI 2007 (SCB). UC anger 10 december 2025 kl. 08.00 för sin egen övergång.
- Statistiken går över stegvis 2026 (KRITA april, REGO maj, FoU oktober,
  IT-användning och Företagens ekonomi november); nationalräkenskaperna 2029.
- Företagen kunde själva byta kod på verksamt.se från 27 januari 2025; de som
  inte gjort det fick koden omkodad maskinellt av SCB (Företagarna).
- SCB ansvarar för klassifikationen; **Skatteverket samlar in koderna** och
  aviserar dem till SCB:s företagsregister.

Källor: https://www.scb.se/dokumentation/klassifikationer-och-standarder/standard-for-svensk-naringsgrensindelning-sni/sni-2025/,
https://www.scb.se/dokumentation/klassifikationer-och-standarder/standard-for-svensk-naringsgrensindelning-sni/,
https://www.foretagarna.se/nyheter/riks/2025/januari/27-januari-kan-du-andra-foretagets-sni-kod/,
https://www.uc.se/globalassets/pdfer/sni-codes---faq-eng.docx

### 4.2 Struktur

| Nivå | SNI 2007 | SNI 2025 | Kodform |
|---|---|---|---|
| Avdelning | 21 | 22 | bokstav (A–U i 2007) **[form ej i läst källa]** |
| Huvudgrupp | 88 | 87 | 2 siffror |
| Grupp | 272 | 287 | 3 siffror |
| Undergrupp | 615 | 651 | 4 siffror (= NACE) |
| Detaljgrupp | 821 | 835 | 5 siffror (svensk nivå) |

SNI 2025 är identisk med **NACE Rev. 2.1** på de fyra första nivåerna; den
femte är svensk. Koden skrivs med punkt efter två siffror i SCB:s exempel
(`29.101`, `45.110`), utan punkt i de flesta register (`29101`). Lagra utan
punkt, visa med.

### 4.3 Flera koder per bolag

SCB:s företagsregister har **upp till fem SNI-koder per företag**
(`Bransch1`…`Bransch5`). Bransch1 är huvudnäringsgren (Ng1). Rangordningen
följer den procentuella fördelningen (oftast omsättning per kod); vid lika
andel kommer lägsta koden först; vid tre eller fler koder summeras andelarna
upp till avdelningsnivå först (top-down). Koderna på företagsnivå aggregeras
från arbetsställena med antal anställda som vikt. Notera att SCB:s
variabelbeskrivning (sid 8) fortfarande nämner SNI2007; vilken version API:t
levererar efter 2025-12-08 ska kontrolleras mot svaret **[ej verifierat]**.

### 4.4 Maskinläsbar kodlista

Bara Excel från SCB (ingen CSV eller API på sidan):

- SNI 2025 sv: https://www.scb.se/globalassets/sni-2025.xlsx
- SNI 2025 en: https://www.scb.se/globalassets/sni-2025-eng-251022.xlsx
- SNI 2025 struktur: https://www.scb.se/globalassets/sni-2025-struktur.xlsx
- SNI 2007: https://www.scb.se/contentassets/d43b798da37140999abf883e206d0545/sni2007.xlsx
- Nyckel 2007→2025: https://www.scb.se/contentassets/d43b798da37140999abf883e206d0545/nyckel-sni2007---sni2025.xlsx
- Nyckel 2025→2007: https://www.scb.se/contentassets/d43b798da37140999abf883e206d0545/sni-_2025-sni_2007.xlsx
- Klassifikationsdatabasen (KDB) på metadata.scb.se och SNI-sök
  https://snisok.scb.se/ för uppslag.

Förslag: läs in xlsx en gång till en tabell `sni_koder(version, kod, niva,
benamning_sv, benamning_en, foralder)` i en migration eller ett skript.
Nyckeltabellen är många-till-många: en 2007-kod kan bli flera 2025-koder.

---

## 5. Adress, telefon, betalning, e-faktura, F-skatt

### 5.1 Postnummer (Postnummerrådet 2017, läst)

- **Fem siffror**, skrivs `NNN NN`. Svensk standard **SS 613401** reglerar
  skrivsätt av postnummer och postort vid utskrift (standarden säljs av SIS,
  inte läst).
- Två första siffrorna = **postnummerområde, 10–98** (86 områden; 32, 48, 49
  och 99 används inte för närvarande). 10–19 är Storstockholm, resten numrerat
  söderifrån från 20.
- Administrativa postnummer: **box**, storkund (eget postnummer; adressen skrivs
  då "utan någon form av utdelningsadress", t.ex. `521 81 Falköping`),
  svarspost/frisvar, tävlingspost, poste restante.
- Regler: en postort kan ha många postnummer; **ett postnummer har bara en
  postort**; en gata kan ha flera postnummer; **ett postnummer kan beröra
  flera län, kommuner och församlingar**; ett släckt postnummer vilar minst
  3 år.
- Ändringar träder i kraft **första helgfria måndagen i mars**. Register ska
  uppdateras och använda alla fem siffrorna vid verifiering.

Källa: https://shop-prod.postnord.com/siteassets/pdf/faktablad/postnummersystemet-i-sverige-171213.pdf

### 5.2 Adressens delar

- **Besöksadress mot postadress (utdelningsadress):** SCB har båda per
  arbetsställe (`BesöksAdress`, `BesöksPostNr`, `BesöksPostOrt`) och
  postadress per företag och arbetsställe (`Postadress` = gatunamn,
  gatunummer, gatulittera, gaturest; `PostNr`; `PostOrt`; `COadress`). Box är
  en postadress, aldrig en besöksadress. Repot väljer besöksadressens
  postnummer först eftersom postadressen ofta är en c/o-box i annan stad
  (`allabolag.py:387-388`).
- **c/o:** egen rad/kolumn (SCB `COadress`; PostNord: används när posten går
  till någon annans adress). CRM:et har redan kolumnen `co`
  (`db/migrations/20261125090000_153_crm_grund.sql:85`).
- **Säte:** säteskommun och säteslän per företag, folkbokföringsort för
  enskild näringsidkare (SCB, sid 26). Det är det rätta underlaget för
  länsfördelning, inte postnumret.
- **Läns- och kommunkoder:** län 2 siffror, kommun 4 siffror (län + 2) enligt
  "Rikets indelningar", SCB:s kodnummerordning (SCB sid 17, 26). Lagra
  koden, visa namnet.
- Radordning och versaler: PostNord-sidan om adressering svarade 403 och SS
  613401 är inte fritt tillgänglig. **[antagande]** Svensk praxis: namn,
  ev. c/o, gatuadress eller Box, `NNN NN POSTORT`, landsnamn sist vid
  utlandspost; inga tomrader i adressblocket (PostNord "Skicka rätt" säger nej
  till tomrader).
- `Utskick`-variabeln i SCB (1 OK, 2 postretur, 3 saknas, 4 utländsk) är
  värd att läsa in.

### 5.3 Telefonnummer (PTS, svenska telefoninummerplanen, status 2026-05-18, läst)

- **E.164:** landskod 46 + nationellt signifikant nummer (NDC + SN), högst
  **15 siffror inklusive landskod**, alltså högst 0 + 13 siffror nationellt.
  Prefixen 00 och 0 ingår inte i E.164-numret.
- **264 riktnummerområden.** Nya geografiska nummer är 0 + 9 siffror; äldre
  kan vara kortare. 08 är Stockholm, 031 Göteborg (PTS exempel).
  Nollspärr: abonnentnummer i fasta nätet får inte börja med 0.
- **Mobil:** 070, 072, 073, 076, 079 (0 + 9 siffror) och **från 1 oktober
  2026 även 078A där A = 0–2 och 4–9**. **0783** är mobiltelefoni för
  järnvägskommunikation (GSM-R, 0 + 7 till 0 + 13). **071 0** är mobilt
  bredband (0 + 13), **074** personsökning.
- **Övrigt:** 010 geografiskt oberoende (0 + 9), 020 frisamtal (0 + 6 till
  0 + 9), 077 delad kostnad, 075 personliga nummer, 0900/0939/0944
  betalteletjänster, 099 massanrop. Nummerportabilitet gäller de flesta
  typer: **operatören går inte att läsa ur numret**.
  Källa: https://www.pts.se/contentassets/c67be6d4f65a456d9ed86a2542505b7b/nrplansammanstallning-2026-05-18.pdf
- **Visning (Isof/Språkrådet):** grupper om två eller tre från vänster,
  bindestreck mellan riktnummer och abonnentnummer: `070-123 45 67`,
  `08-123 456 78`, `08-678 55 00`, `031-12 34 56`. "Ingen tvingande regel."
  Myndigheter skriver servicenummer 3+3: `0771-567 567`, `020-567 000`.
  Källa: https://frageladan.isof.se/visasvar.py?svar=61433
- **Internationell visning:** `+46 70 123 45 67`, `+46 8 678 55 00`
  (nollan bort). Skatteverket skriver `+46 8 564 858 70` (SKV 709 sid 4).
- **Riktnummerlängd:** **[antagande, ur minnet]** tresiffriga riktnummer
  (inkl. 0) är 011, 013, 016, 018, 019, 021, 023, 026, 031, 033, 035, 036,
  040, 042, 044, 046, 054, 060, 063, 090; 08 är tvåsiffrigt; övriga
  geografiska är fyrsiffriga (0910 Skellefteå). Ska stämmas av mot PTS
  riktnummerlista innan visningen används i produkt. Lagringen (E.164)
  påverkas inte av felet, bara grupperingen.
- **Anknytning** hör inte till E.164-numret. Lagra separat.

### 5.4 Bankgiro, plusgiro, IBAN

- **Bankgiro:** 7 eller 8 siffror, sista är Luhn-kontrollsiffra (Bankgirot
  FAQ och modulus 10-manualen). Visning `NNN-NNNN` / `NNNN-NNNN` (Bankgirots
  exempel `5555-5551`).
  https://bankgirot.se/en/services/incoming-payments/bankgiro-number/faq,
  https://www.bankgirot.se/globalassets/dokument/anvandarmanualer/10-modul.pdf
- **Plusgiro:** 2–8 siffror med Luhn (repot: `kvitton/kontrollsiffror.py:55-57`)
  **[primärkälla ej läst]**.
- **IBAN SE:** 24 tecken: `SE` + 2 kontrollsiffror (mod 97) + 3 siffror
  bank-id + 17 siffror konto. Visas i fyrgrupper:
  `SE45 5000 0000 0583 9825 7466`. Bankens tresiffriga IBAN-id är inte samma
  sak som clearingnumret. Kontonummeruppbyggnad per bank:
  https://www.bankgirot.se/globalassets/dokument/anvandarmanualer/bankernaskontonummeruppbyggnad_anvandarmanual_sv.pdf
- Ett CRM behöver dessa bara för faktureringsuppgifter. **[antagande]**
  Första versionen klarar sig utan.

### 5.5 Peppol-id och GLN

- Digg rekommenderar **`0007:` + orgnr** som Peppol-id för svenska aktörer;
  GLN (`0088:` + 13 siffror) kan fungera i vissa fall.
  https://peppol.org/learn-more/country-profiles/sweden/
- Regeln **PEPPOL-COMMON-R049** (fatal): svenskt orgnr med schemeID 0007 ska
  vara exakt tio siffror (inga bindestreck, inget SE-prefix).
  https://docs.peppol.eu/tdd/sk/tdd-sk/trn-tdd/businessrule/PEPPOL-COMMON-R049/
- Exempel: Skatteverket `0007:2021005448`
  (https://skatteverket.se/servicelankar/otherlanguages/englishengelska/submittingeinvoicestous.4.7eada0316ed67d728240f4.html),
  Transportstyrelsen `0007:2021006099`.
- **GLN** är 13 siffror med GS1:s mod 10-kontrollsiffra (vikter 3-1 från
  höger) **[primärkälla ej läst]**. Lagra som text, aldrig som tal.
- SFTI-specifika regler för Peppol-id hittades inte.

### 5.6 F-skatt

- SCB:s API har `F-skattstatus`: `0` aldrig registrerad, `1` registrerad,
  `9` avregistrerad (veckovis). Samma struktur för `Momsstatus` (`0`, `1`,
  `3` via representant, `9`) och arbetsgivarstatus.
- Skatteverkets webbtjänst "Hämta företagsinformation" visar om ett företag
  är godkänt för F-skatt, momsregistrerat och arbetsgivare
  (https://skatteverket.se/hamtaforetagsinfo). Ett öppet API för F-skatt per
  bolag hittades inte; Skatteverkets API för det kräver avtal
  **[ej verifierat i detalj]**.
- Skatteverket: individuppgifter är inte öppna data.

---

## 6. Svenska tal-, valuta- och datumformat

### 6.1 Regler

- **Tal:** tusentalsavgränsare som mellanrum i tresiffriga grupper från
  höger, decimalkomma: `1 234,56`. SCB:s skrivhandledning:
  https://www.scb.se/om-scb/scbs-verksamhet/varumarkeshandbok/sa-uttrycker-vi-oss/
- **Valuta:** `1 234,56 kr` (belopp, mellanrum, `kr`); `SEK` i tabeller och
  utlandssammanhang **[antagande, praxis]**.
- **Datum:** ISO 8601 `2026-11-25` i data och tabeller; i löptext
  `25 november 2026`.
- **Klockslag:** 24-timmars. Isof: **punkt är den svenska konventionen
  (`14.30`), kolon (`14:30`) godtas som internationell**.
  https://frageladan.isof.se/visasvar.py?svar=28111. `Intl` ger kolon, se
  nedan.
- **Vecka:** ISO 8601-veckor, måndag först, vecka 1 är veckan med årets första
  torsdag. `Intl` räknar inte ut veckonummer.
- **Räkenskapsår:** **[ej hämtat i denna research]** bokföringslagen
  (1999:1078) 3 kap: 12 månader, kalenderår eller brutet; vid start eller
  omläggning kortare eller längre, högst 18 månader. Fysiska personer har
  kalenderår. Ett CRM som visar omsättning ska visa vilket räkenskapsår
  siffran gäller (SCB: `Omsättning År`).

### 6.2 `Intl` för sv-SE, uppmätt (Node v24.11.0, 2026-11-25)

| Anrop | Resultat | Tecken |
|---|---|---|
| `NumberFormat("sv-SE",{style:"currency",currency:"SEK"}).format(1234.56)` | `1 234,56 kr` | `31 a0 32 33 34 2c 35 36 a0 6b 72` |
| `NumberFormat("sv-SE").format(-1234567.891)` | `−1 234 567,891` | börjar med **U+2212**, grupper med **U+00A0** |
| `{style:"currency",currency:"SEK",maximumFractionDigits:0}` | `1 235 kr` | avrundar |
| `{style:"percent",maximumFractionDigits:1}` på 0.125 | `12,5 %` | mellanrum före % |
| `{notation:"compact"}` på 1234567 | `1,2 mn` | "mn", inte "milj." |
| `DateTimeFormat("sv-SE",{timeZone:"Europe/Stockholm"})` | `2026-11-25` | ISO-form |
| `{dateStyle:"medium"}` | `25 nov. 2026` | |
| `{dateStyle:"long",timeStyle:"short"}` | `25 november 2026 kl. 14:05` | kolon |
| `{dateStyle:"full"}` | `onsdag 25 november 2026` | |
| `toLocaleString("sv-SE",{timeZone:"Europe/Stockholm"})` | `2026-11-25 14:05:00` | |
| `new Intl.Locale("sv-SE").getWeekInfo()` | `{"firstDay":1,"weekend":[6,7]}` | måndag först |
| `Number("1 234,56")` / `parseFloat("1 234,56")` | `NaN` / `1` | går inte att läsa tillbaka |

**Fällorna:**

1. **Hårt blanksteg (U+00A0)** i tusental och före `kr`/`%`. En test som
   jämför mot `"1 234,56 kr"` med vanligt mellanslag faller; en sökning i
   UI:t på "1 234" hittar inget. ICU/CLDR-versioner har bytt mellan U+00A0 och
   U+202F (smalt hårt blanksteg) för vissa språk; jämför därför med
   `.replace(/[  ]/g, " ")` eller `formatToParts`. Repot hanterar
   båda tecknen i `app/crm/falt.py:207` (verifierat med `od -c`).
2. **Minustecknet är U+2212**, inte bindestreck. `app/crm/falt.py:heltal`
   fäller `"−1 234"` som `tal_ogiltigt` (körd prov, avsnitt 9.3).
3. **Klockslag med kolon** fast Isof föredrar punkt. Acceptera, men var
   konsekvent.
4. **Tidszon:** sätt alltid `timeZone: "Europe/Stockholm"` (repot gör det i
   `lib/utils.ts:20-25`); servern på Railway kör UTC.
5. **Läs aldrig tillbaka formaterade tal.** Lagra tal som tal, belopp i öre
   eller `numeric`, datum som `date`/`timestamptz`.

---

## 7. Registerdata

### 7.1 Bolagsverket: värdefulla datamängder (HVD)

Bolagsverkets sidor visar en bildcaptcha för automatiserad hämtning; den har
inte kringgåtts. Uppgifterna nedan är **Bolagsverkets egna texter som de
återges i sökmotorns utdrag** (märkta) eller tredjepartskällor (märkta).

- **Avgiftsfritt och utan avtal** (bolagsverket.se, utdrag): "API för
  värdefulla datamängder" kostar inget och kräver inga avtal, enligt EU:s
  genomförandeförordning om värdefulla datamängder. Avgiftsfriheten gäller
  från **3 februari 2025** (utdrag; nyheten "Avgiftsfri data när Bolagsverket
  och SCB lanserar värdefulla datamängder").
  https://bolagsverket.se/apierochoppnadata/hamtaforetagsinformation/vardefulladatamangder/apiforvardefulladatamangder.5513.html,
  https://bolagsverket.se/apierochoppnadata/nyheterochreleaser/2025/avgiftsfridatanarbolagsverketochscblanserarvardefulladatamangder.5516.html
- **Anslutning** (utdrag): kundanmälan med e-post och telefon, därefter
  tillgång till testmiljön. **Teknik** (tredjepart, **[ej verifierat]**):
  OAuth2 client credentials, token från `portal.api.bolagsverket.se/oauth2/token`,
  data via `POST gw.api.bolagsverket.se/vardefulla-datamangder/v1/organisationer`,
  scope `vardefulla-datamangder:read`.
- **Innehåll** (tredjepart, **[ej verifierat]**): grundläggande uppgifter om
  företag och föreningar (namn, orgnr, registrerad adress, organisationsform,
  status), SNI 2025-koder från SCB, och digitalt inlämnade årsredovisningar
  för aktiebolag sedan 2020. **Nedladdningsbara filer** med samma data,
  avgiftsfria, veckovis (utdrag ur Bolagsverkets avtal).
  https://bolagsverket.se/apierochoppnadata/nedladdningsbarafiler.2517.html
- **Det betalda API:t** "API för att hämta företagsinformation"
  (styrelse, firmatecknare, ärenden, aktiekapital, dokument): anslutningsavgift
  5 000 kr exkl. moms plus månadsavgift efter transaktionsnivå, skriftligt
  avtal; HVD-operationerna räknas inte mot nivån (utdrag ur avtalet
  https://bolagsverket.se/download/18.37b754ba19ceb00666a562d5/1788438045725/avtal-om-tjanst-for-foretagsinformation-via-api-foretag-privat.pdf).
- Enskilda firmor finns i Bolagsverkets register bara om de registrerat
  företagsnamn **[antagande]**.

**Nästa steg för byggaren:** Anton (eller den med Bolagsverket-konto) gör
kundanmälan och hämtar OpenAPI-specen från utvecklarportalen; fältlistan i
avsnitt 8 ska stämmas av mot den.

### 7.2 SCB:s företagsregister (läst)

- **Avgiftsfritt sedan 26 juni 2025** (förordningsändring: SCB "inte längre
  ska ta ut avgifter för uppgifter ur företagsregistret"). REST, JSON,
  **API-nyckel** via SCB:s Registreringsportal (de gamla certifikaten gäller
  inte). Personlig nyckel, får inte delas. **Upp till 5 000 rader per anrop**
  med paginering, **5 anrop per sekund** per nyckel (annars tillfällig
  spärr). Uppdateras varje natt utom natten lördag–söndag; de flesta
  variabler veckovis. **Bara aktuellt läge: ingen historik och inget
  ändringsflöde** (ändringsaviseringen är en betaltjänst).
  https://www.scb.se/vara-tjanster/bestall-data-och-statistik/foretagsregistret/avgiftsfria-uppgifter-i-foretagsregistret/
- **Populationen:** alla juridiska personer, fysiska personer med registrerat
  företagsnamn eller registrerade för moms/F-skatt/som arbetsgivare, och
  dödsbon registrerade för moms eller som arbetsgivare.
- **Variabler som ett CRM vill ha** (variabelbeskrivningen, läst):
  `PeOrgNr`, `Företagsnamn`, `Firma`, `Juridisk form`, `Status hos
  Bolagsverket`, `Företagsstatus`, `Registreringsdatum`, `Startdatum`,
  `Slutdatum`, `Bransch1–5` (SNI), `Storleksklass Anställda` (0 saknas,
  1 = 0, 2 = 1–4, 3 = 5–9, 4 = 10–19, 5 = 20–49, 6 = 50–99, 7 = 100–199,
  8 = 200–499 … 16 = 10000–), `Storleksklass Omsättning` (0 = < 1 tkr …
  12 = > 9 999 999 tkr) och `Omsättning År`, `F-skattstatus`, `Momsstatus`,
  `Arbetsgivarstatus`, `Postadress`, `PostNr`, `PostOrt`, `COadress`,
  `BesöksAdress`, `BesöksPostNr`, `BesöksPostOrt`, `Säte, kommun och län`,
  `Telefon`, `E-post`, `Sektor` (INSEKT 2014), `Ägarkategori` (10 statligt,
  20 kommunalt, 30 regioner, 41 privat utan koncern, 42 privat med koncern,
  50 utländska), `Privat/publikt` (börslista), `CFAR-nummer` (arbetsställets
  id), `Utskick` (postretur).
- **`Reklam`** (sid 22): `11` tar emot reklam, ej telefonspärrat; `12` tar
  emot reklam, telefonnummerspärr telemarketing; `13` tar emot reklam,
  NIX-telefon; `21–23` har frånsagt sig reklam (ej telefonspärr /
  telefonspärr / NIX). SCB: "god marknadsföringssed att inte kontakta dessa
  på de sätt som avsagt sig". **Relevant för ringlistan (regel 15) och för
  Buddy som telefonibolag.**
- Anställda och omsättning är sekretess och finns bara som storleksklasser.

Källa: https://www.scb.se/contentassets/8a8eb5c3d45f461ea93482f8e8d4de4f/variabelbeskrivning-api.pdf

### 7.3 Skatteverket

- Organisationsnummerregistret (avsnitt 1.1) är källan som SCB och
  Bolagsverket aviserar till; SCB aviseras veckovis.
- Öppna data är aggregerade; individuppgifter är inte öppna. F-skatt,
  moms och arbetsgivare per bolag: webbtjänsten "Hämta företagsinformation",
  eller SCB:s statusvariabler. https://www.skatteverket.se/omoss/utvecklingavdigitalatjanster/oppnadatapsidata.4.361dc8c15312eff6fd1736c.html

### 7.4 Kommersiella källor

Inga av dessa publicerar priser. Det som hittades:

| Källa | Vad | Pris | Status i repot |
|---|---|---|---|
| allabolag.se (UC Affärsinformation AB) | Bolagsfakta, bokslut, personer | Inget officiellt utvecklar-API dokumenterat; Anton har begärt pris (`docs/utkast-allabolag-api-forfragan.md:3`, "Ej skickat") | Sidorna läses direkt, hövlig hämtning, cache 7 dygn (`allabolag.py:19-24`); villkoren medger inte fri kopiering |
| merinfo.se | Bolags- och personsidor | Inget API hittat | Blockerar direkthämtning (403), hämtades via ScrapeGraph (`allabolag.py:5-9`) |
| Roaring | API för bolags-, person- och kreditdata i Norden, Bolagsverket-API | "Låg fast avgift + användning" enligt G2, gratis sandbox | Används inte |
| UC | Kreditupplysning, SNI-omkodning | Ej publicerat | Används inte |
| Creditsafe, Dun & Bradstreet (fd Bisnode), Bolagsfakta | Bolags- och kreditdata | **Ej undersökt i denna research** | Används inte |

Källor: https://www.g2.com/products/roaring-api/pricing,
https://developer.roaring.io/docs/apis/se-company-overview-2.0,
https://www.scrapingbee.com/scrapers/allabolag-business-details-api/

**Bedömning [antagande]:** för bolagsnivå (namn, form, status, SNI, adress,
säte, storleksklass, F-skatt/moms, reklamspärr) räcker **SCB:s gratis-API**,
kompletterat med **Bolagsverkets HVD** för organisationsform och
årsredovisningar. Kommersiell källa behövs först för styrelse/VD,
kreditbetyg och bokslutssiffror i kronor. Svenska CRM-system (Lime, Upsales,
SuperOffice) brukar koppla in en av de kommersiella leverantörerna
**[ej verifierat]**.

---

## 8. Fältlista: Företag och Person i ett svenskt CRM

Jämfört med `crm_bolag` och `crm_personer` i den ocommittade migrationen
`db/migrations/20261125090000_153_crm_grund.sql:69-140`. Kolumnen "153" säger
om fältet finns där.

### 8.1 Företag

| Fält | Typ (Postgres) | Validering | Lagring | Visning | 153 |
|---|---|---|---|---|---|
| `orgnr_nyckel` | `text` check `^[0-9]{10}$` | Luhn; prefix 16/18/19/20 bara i rätt kombination | `5568249022` | – | ja (108-110) |
| `orgnr` | `text` | som ovan | `556824-9022` | `556824-9022` | ja |
| `identitetstyp` | `text` (`organisationsnummer`/`personnummer`/`samordningsnummer`/`utlandskt`) | ur tredje och femte siffran | | | nej (153 har boolean `enskild_firma`) |
| `utlandskt_regnr` + `land` | `text`, `char(2)` ISO 3166-1 | fritt | | | delvis (`land` default `SE`) |
| `namn` | `text not null` | trim, inga radbrytningar | registrerat namn | | ja |
| `kortnamn` / `varumarke` | `text` | | | | nej (SCB `Benämning`, allabolag `name` mot `legalName`, `allabolag.py:379-382`) |
| `juridisk_form_kod` | `smallint` | i tabellen 3.1 | `49` | "Aktiebolag" | nej (153 har fritext `bolagsform`) |
| `status_kod` | `smallint` | SCB-koder 3.2 | `0` | "Normalläge"/"Konkurs inledd" | nej |
| `aktiv` | `boolean` | härlett ur status och Företagsstatus | | | nej |
| `momsnr` | `text` | `^SE\d{10}01$` + Luhn, eller EU-form | `SE556824902201` | samma | ja |
| `momsstatus`, `fskatt_status`, `arbetsgivarstatus` | `smallint` | SCB 0/1/3/9 | | "Registrerad för F-skatt" | nej |
| `vies_kontroll` | `jsonb` (`valid`, `requestDate`, `requestIdentifier`) | | | | nej |
| `sni` | `text[]` eller tabell `crm_bolag_sni(bolag_id, version, kod, rang)` | kod finns i `sni_koder` | `{62010,…}` | `62.010 Dataprogrammering` | delvis (153 har en `text`) |
| `sni_version` | `text` (`sni2007`/`sni2025`) | | | | nej |
| `webbplats`, `doman` | `text` | värdnamn med punkt | `bolaget.se` | | ja |
| `epost` | `text` | se `falt.epost` | gemener | | ja |
| `telefon` | `text` | E.164, 8–15 siffror | `+4686785500` | `08-678 55 00` | ja (ej validerad struktur, avsnitt 9) |
| `telefon_ankn` | `text` | 1–6 siffror | | `ankn. 123` | nej |
| `postadress_gata`, `postadress_co`, `postadress_postnr`, `postadress_ort` | `text` | postnr 5 siffror, område 10–98 | `11391` eller `113 91` (välj ett) | `113 91 STOCKHOLM` | delvis (`gatuadress`, `co`, `postnr`, `postort`; en adress) |
| `besoksadress_*` | `text` | som ovan | | | nej |
| `sate_kommunkod`, `sate_lanskod` | `char(4)`, `char(2)` | SCB-kodlista | `0180`, `01` | "Stockholm", "Stockholms län" | nej |
| `anstallda` | `integer` | ≥ 0 | | | ja |
| `anstallda_klass` | `smallint` | SCB 0–16 | | "5–9" | nej |
| `omsattning` | `bigint` (kronor) | | | `1 234 tkr` / `1,2 mn kr` | ja |
| `omsattning_ar` | `smallint` eller `daterange` för räkenskapsåret | | | "2025" | nej |
| `reklamsparr` | `smallint` SCB 11–23 | | | "NIX-telefon" | nej |
| `peppol_id` | `text` | `^0007:\d{10}$` eller `^0088:\d{13}$` | | | nej |
| `gln` | `text` | 13 siffror, GS1-kontroll | | | nej |
| `bankgiro`, `plusgiro` | `text` | Luhn | `55555551` | `5555-5551` | nej (behövs bara för fakturering) |
| `registreringsdatum` | `date` | | ISO | `2026-11-25` | nej |
| `kalla`, `kalla_hamtad_at` | `text`, `timestamptz` | | | "SCB 2026-11-24" | delvis (`kalla`) |
| `relation`, `kund_sedan`, `avtalsslut`, `ansvarig`, `kontakta_inte` | | | | | ja |

### 8.2 Person

| Fält | Typ | Validering | Visning | 153 |
|---|---|---|---|---|
| `fornamn`, `efternamn` | `text` | | "Anna Berg" | ja |
| `titel` | `text` | fritt | | ja |
| `roll_kod` | `text` (`vd`, `agare`, `styrelseordforande`, `ledamot`, `kontakt`) | regel 3: aldrig suppleant/revisor ur registret | | nej |
| `epost` | `text` | gemener | | ja (unik per kund) |
| `telefon`, `mobil` | `text` E.164 | som företag; `mobil` ska vara 07[02369]/078A | `070-123 45 67` | ja |
| `telefon_ankn` | `text` | | | nej |
| `personnummer` | **ska inte finnas** | | | nej (bra) |
| `rattslig_grund` | `text` (`avtal`, `berattigat_intresse`, `samtycke`) | | | ja (143-144) |
| `kontakta_inte`, `reklamsparr`, `nix` | `boolean` | | | delvis |
| `kalla`, `kalla_url` | `text` | regel 3/10: styrkt kontaktuppgift | | delvis |
| `sprak` | `text` (`sv`/`en`) | | | nej |

---

## 9. Hur repot gör i dag (läst kod)

### 9.1 Organisationsnummer: nio normaliseringar

| Ställe | Vad den gör | Avvikelse |
|---|---|---|
| `snajp-support/app/leads/orgnr.py:56-65` `normalisera` | skalar bara `16` | |
| `orgnr.py:82-101` `_strip_sekel` | skalar `19`/`20` | **Död kod på rad 100-101** efter `return` (refererar `_PERSONNUMMER_SVAR` som inte finns); kommentaren säger att personnummer-spärren togs bort medvetet 2026-08-18 |
| `orgnr.py:37-44` `_GRUPPER` | gruppnummer → form | ger sken av juridisk form, vilket SKV 709 säger att numret inte bär |
| `app/leads/upptagna.py:41-46` `orgnr_nyckel` | skalar **vilket** 2-siffrigt prefix som helst vid 12 siffror | `172021005448` blir en giltig nyckel |
| `app/leads/send_guard.py:544-553` `foretagsnyckel` | `re.sub(r"\D","",orgnr)`, **inget prefix skalas** | `16556824-9022` och `556824-9022` ger olika karensnycklar |
| `db/migrations/031_prospect_nischfalt.sql:50-57` genererad `foretagsnyckel` | samma som send_guard, i SQL | samma avvikelse, men nu i databasen |
| `app/leads/forfilter.py:30-34` `ar_enskild_firma` | siffra 3–4 ∈ 01–12 | |
| `app/leads/webbpool.py:175-181` `ar_enskild_firma` | siffra 3 ∈ {0,1} | olika regel än forfilter (ger samma utfall för riktiga nummer) |
| `app/kvitton/kontrollsiffror.py:42-47` `orgnummer_ok` | skalar vilket 12-siffrigt prefix som helst | |
| `lib/leads/importvarden.ts:59-71` `tolkaOrgnr` | SE…01, 16/18/19/20, **nekar personnummer** (rad 68), sparar 8–9 siffror som utländskt (rad 66) | enda stället som nekar enskild firma |
| `app/leads/sources/merinfo.py:159-160, 215` | tar `NNNNNN-NNNN` ur sidan, ingen Luhn | |
| `app/leads/sources/allabolag.py:355-356` | tio siffror → formatera, ingen Luhn; >10 siffror = enskild firma (358-364) | |
| `app/crm/falt.py:64-86` (ocommittad) | Luhn, 16/18/19/20, `enskild` = siffra 3 < 2 | godtar `16`+personnummer och `19`+orgnr; ingen datumkontroll |

**Rekommendation:** en enda Python-funktion (avsnitt 10, `tolka_identitet`)
och en TS-spegel, och en SQL-funktion `orgnr_nyckel(text)` som den genererade
kolumnen i 031 och unika indexet i 153 använder, så att Python och SQL inte
kan räkna olika.

### 9.2 Telefon

- `lib/leads/importvarden.ts:94-112` returnerar svenska nummer **som de
  skrevs** (rad 111); bara `00`/`46` blir `+46` (108-109) och Excels tappade
  nolla läggs tillbaka för mobiler (110). Ingen E.164-lagring.
- `merinfo.py:155` läser bara nummer i nationell form (`0…`) ur sidans
  `tel:`-länkar; `allabolag.py:386` tar `phone` eller `mobile` rått.
- `app/crm/falt.py:115-148` (ocommittad) ger E.164, men (körd prov, 9.3):
  - **anknytning slås ihop med numret:** `08-678 55 00 ankn. 123` →
    `+4686785500123` (giltig längd, fel nummer);
  - **Excels tappade nolla** (`701234567`) fälls som
    `telefon_saknar_riktnummer`, medan `importvarden.ts:110` räddar den:
    samma fil ger olika utfall i lista och CRM;
  - **0783 (GSM-R) godtas** som vilket nummer som helst; ingen
    nummerplanskontroll (07-serie, nollspärr, längd per typ).
- Följd för Buddy: ett telefonibolag matchar samtal mot kunder på nummer.
  Utan en gemensam E.164-normalisering i leads, listor och CRM hittar
  tidslinjen inte samtalen.

### 9.3 Körd prov mot `app/crm/falt.py` (funktionerna extraherade med `ast`, ingen import av appen)

```
telefon '070-123 45 67'          -> +46701234567
telefon '08-678 55 00 ankn. 123' -> +4686785500123      (fel)
telefon '701234567'              -> FaltFel(telefon_saknar_riktnummer)
telefon '+46 (0)70 123 45 67'    -> +46701234567
telefon '0783123456'             -> +46783123456        (GSM-R, inte en kundtelefon)
heltal  '1 234,56 kr'            -> 1234                 (trunkerar, avrundar inte)
heltal  '−1 234' (U+2212, U+00A0) -> FaltFel(tal_ogiltigt)
heltal  '1.234.567'              -> 1234567
postnr  '091 00'                 -> 091 00               (område 09 finns inte)
postnr  '99100'                  -> 991 00               (område 99 används inte)
postnr  'SE-113 91'              -> 113 91
```

### 9.4 Postnummer, län, SNI, belopp

- Postnummer lagras med mellanslag överallt (`allabolag.py:329-331`,
  `merinfo.py:226`, `falt.py:192`), och indexet i 031 slår på
  `left(postnr, 3)` (`031_prospect_nischfalt.sql:63-64`). Konsekvent, men
  utan områdeskontroll (10–98).
- `webbpool.py:140-147` `lan_ur_postnr` härleder län ur postnummerprefix med
  ett undantag för Kungsbacka/Onsala. Postnummerrådet: ett postnummer kan
  beröra flera län. Använd SCB:s säteslän när det finns.
- Län och kommun lagras som merinfos sluggar och namn (`allabolag.py:79-103`,
  `130-144`), inte som SCB-koder. CRM:et bör lagra koden.
- SNI: `merinfo.py:240` läser **bara den första** koden; `allabolag.py:398-401`
  sätter `sni = None` eftersom allabolags branschkoder inte är SNI.
  `crm_bolag.sni` är en `text` (153:79). Ingen version lagras.
- Omsättning: allabolag anger tkr och repot multiplicerar med 1 000
  (`allabolag.py:392-393`, `merinfo.py:252`). SCB ger storleksklass, inte
  belopp. Lagra källa och räkenskapsår bredvid.
- `lib/utils.ts:5-25` formaterar med `Intl` sv-SE och `Europe/Stockholm`
  (bra). `lib/leads/importvarden.ts:171-191` läser datum med dag före månad som
  standard (svenska filer) och Excel-löpnummer.

### 9.5 Det som redan är rätt och ska behållas

- Luhn är korrekt implementerad på alla ställen som har den
  (`orgnr.py:68-79`, `kontrollsiffror.py:28-39`, `importvarden.ts:38-49`
  räknar från vänster, vilket ger samma utfall för tio siffror).
- `kontrollsiffror.py` har bankgiro (7–8 siffror), plusgiro, OCR, IBAN
  (mod 97) och momsnummer (`SE\d{10}01` + Luhn) rätt mot källorna.
- Enskild firma behandlas som personuppgift i webbpool och utskick, och
  `crm_bolag.enskild_firma` + kolumnkommentaren (153:276-278) säger det.
- Registret är filter, inte kontaktkälla (CLAUDE.md regel 1); SCB:s
  `Telefon`/`E-post` per bolag är bolagsnivå och faller under regel 13/15.

---

## 10. Referensimplementation (Python, bara stdlib)

Körd med `python -I -X utf8` (Python 3.14.0) från en tillfällig katalog
utanför repot. Funktionerna returnerar ett `Resultat` (ok, kanoniskt värde,
visning, felkod, info) i stället för att höja, så att en importrad kan bära
sitt fel till granskningen. Inget av koden är incheckat; den är ett facit att
jämföra `app/crm/falt.py` och `lib/leads/importvarden.ts` mot.

### 10.1 `svid.py`

```python
"""Svenska identifierare: validering och normalisering (bara stdlib).

Referensimplementation för Snajp CRM. Varje funktion returnerar ett
`Resultat` i stället för att höja, så att en importrad kan bära sitt fel
vidare till granskningen utan att hela importen faller.

Källor: se docs/crm/underlag/svensk-01-identifierare-format-register.md.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

# ---------------------------------------------------------------- gemensamt


@dataclass(frozen=True)
class Resultat:
    ok: bool
    varde: str | None = None          # kanonisk lagringsform
    visning: str | None = None        # svensk visningsform
    fel: str | None = None            # maskinläsbar felkod
    info: dict = field(default_factory=dict)


def _siffror(ra: object) -> str:
    return "".join(t for t in str(ra or "") if t.isdigit())


def luhn_ok(siffror: str) -> bool:
    """Modulus 10 (Luhn). Räknar från höger: varannan siffra, med start på
    den NÄST sista, dubbleras; tvåsiffriga produkter ersätts med sin
    siffersumma (samma sak som -9); summan ska vara jämnt delbar med 10."""
    if not siffror or not siffror.isdigit():
        return False
    summa = 0
    for i, t in enumerate(reversed(siffror)):
        n = int(t)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        summa += n
    return summa % 10 == 0


def luhn_kontrollsiffra(nio: str) -> int:
    """Kontrollsiffran som gör `nio + k` Luhn-giltig."""
    for k in range(10):
        if luhn_ok(nio + str(k)):
            return k
    raise ValueError(nio)


# ------------------------------------------------- organisationsnummer m.m.

#: Första siffran (gruppnumret) -> grov kategori. Vägledande, INTE juridisk
#: form: SKV 709 säger uttryckligen att juridisk form inte går att utläsa ur
#: numret. Tabellen är den som Fortnox/Spiris m.fl. publicerar.
GRUPPER = {
    "2": "stat, region, kommun eller församling",
    "3": "utländskt företag (förekommer, ej officiellt dokumenterat)",
    "5": "aktiebolag",
    "6": "enkelt bolag",
    "7": "ekonomisk förening eller bostadsrättsförening",
    "8": "ideell förening eller stiftelse",
    "9": "handelsbolag eller kommanditbolag",
}


def tolka_identitet(ra: object) -> Resultat:
    """Organisationsnummer, personnummer eller samordningsnummer.

    Accepterar 'NNNNNN-NNNN', 'NNNNNNNNNN', '16NNNNNNNNNN',
    '19/20ÅÅMMDD-NNNN', 'ÅÅMMDD+NNNN' och momsnummer 'SE NNNNNNNNNN 01'.
    Kanonisk lagring: tio siffror utan bindestreck. Visning: NNNNNN-NNNN.

    info['typ'] är 'organisationsnummer', 'personnummer' eller
    'samordningsnummer'. De två senare är PERSONUPPGIFTER (enskild firma).
    """
    text = str(ra or "").strip()
    if not text:
        return Resultat(False, fel="tomt")
    kompakt = re.sub(r"[\s.]", "", text).upper()
    if re.fullmatch(r"SE\d{10}01", kompakt):
        kompakt = kompakt[2:12]
    hundra = "+" in kompakt  # personnummer för den som fyllt 100
    s = _siffror(kompakt)
    sekel = None
    if len(s) == 12:
        prefix, s = s[:2], s[2:]
        if prefix == "16":
            if s[2] < "2":
                return Resultat(False, fel="16_med_personnummer")
        elif prefix in ("18", "19", "20"):
            sekel = prefix
            if s[2] >= "2":
                return Resultat(False, fel="sekel_med_orgnr")
        else:
            return Resultat(False, fel="okant_prefix")
    if len(s) != 10:
        return Resultat(False, fel="langd")
    if not luhn_ok(s):
        return Resultat(False, fel="kontrollsiffra")

    visning = f"{s[:6]}{'+' if hundra else '-'}{s[6:]}"
    if s[2] >= "2":
        return Resultat(
            True, varde=s, visning=f"{s[:6]}-{s[6:]}",
            info={"typ": "organisationsnummer", "grupp": s[0], "grupptext": GRUPPER.get(s[0])},
        )
    # Fysisk person: ÅÅMMDD, dag + 60 för samordningsnummer.
    manad, dag = int(s[2:4]), int(s[4:6])
    typ = "personnummer"
    if dag > 60:
        typ, dag = "samordningsnummer", dag - 60
    if not 1 <= manad <= 12:
        return Resultat(False, fel="manad")
    ar2 = int(s[:2])
    kandidater = [int(sekel) * 100 + ar2] if sekel else [1900 + ar2, 2000 + ar2, 1800 + ar2]
    if not any(_datum_finns(a, manad, dag) for a in kandidater):
        # Personnummer kan i undantagsfall ha "ogiltigt" datum (brist på
        # födelsenummer ger närliggande dag), men dag 0/32+ är alltid fel.
        if not 1 <= dag <= 31:
            return Resultat(False, fel="dag")
    return Resultat(True, varde=s, visning=visning, info={"typ": typ, "personuppgift": True})


def _datum_finns(ar: int, manad: int, dag: int) -> bool:
    try:
        date(ar, manad, dag)
        return True
    except ValueError:
        return False


def tolka_orgnr(ra: object) -> Resultat:
    """Som tolka_identitet men godtar BARA juridiska personers nummer."""
    r = tolka_identitet(ra)
    if r.ok and r.info.get("typ") != "organisationsnummer":
        return Resultat(False, fel="personnummer", info=r.info)
    return r


def peppol_id(orgnr: object) -> Resultat:
    r = tolka_orgnr(orgnr)
    return Resultat(True, varde=f"0007:{r.varde}", visning=f"0007:{r.varde}") if r.ok else r


# ------------------------------------------------- momsregistreringsnummer


def tolka_momsnr(ra: object) -> Resultat:
    """SE + tio siffror + 01. Tio siffror = orgnr, eller personnummer för
    enskild firma. Kanonisk form: 'SE556824902201' (utan mellanrum)."""
    text = re.sub(r"[\s.\-]", "", str(ra or "")).upper()
    if not text:
        return Resultat(False, fel="tomt")
    if not text.startswith("SE"):
        if re.fullmatch(r"[A-Z]{2}[0-9A-Z+*]{2,12}", text):
            return Resultat(False, fel="utlandskt_ej_provat", info={"land": text[:2]})
        return Resultat(False, fel="format")
    if not re.fullmatch(r"SE\d{12}", text):
        return Resultat(False, fel="format")
    if not text.endswith("01"):
        return Resultat(False, fel="slutar_inte_01")
    r = tolka_identitet(text[2:12])
    if not r.ok:
        return Resultat(False, fel=r.fel)
    return Resultat(True, varde=text, visning=text, info={"identitet": r.info.get("typ")})


def momsnr_ur_orgnr(orgnr: object) -> Resultat:
    r = tolka_identitet(orgnr)
    if not r.ok:
        return r
    v = f"SE{r.varde}01"
    return Resultat(True, varde=v, visning=v, info={"obs": "härlett, inte bevis på momsregistrering"})


# ------------------------------------------------------------ postnummer


def tolka_postnummer(ra: object) -> Resultat:
    """Fem siffror, de två första 10–98 (postnummerområden). Lagring
    'NNNNN', visning 'NNN NN'. 'SE-' och 'S-' framför skalas av."""
    text = str(ra or "").strip().upper()
    text = re.sub(r"^(SE|S)[\s-]?", "", text)
    if not re.fullmatch(r"\d{3}\s?\d{2}", text):
        return Resultat(False, fel="format")
    s = _siffror(text)
    if not 10 <= int(s[:2]) <= 98:
        return Resultat(False, fel="omrade")
    return Resultat(True, varde=s, visning=f"{s[:3]} {s[3:]}", info={"omrade": s[:2]})


# ------------------------------------------------------------ telefonnummer

#: Tresiffriga riktnummer (inkl. 0). Ur minnet, ska stämmas av mot PTS
#: riktnummerlista; 08 är det enda tvåsiffriga. Allt annat geografiskt
#: som börjar på 0[1-6,9] antas ha fyrsiffrigt riktnummer.
_RIKT3 = {
    "011", "013", "016", "018", "019", "021", "023", "026", "031", "033",
    "035", "036", "040", "042", "044", "046", "054", "060", "063", "090",
}
_MOBIL = re.compile(r"7[02369]\d{7}|78[0-24-9]\d{6}")  # 078A gäller fr.o.m. 2026-10-01


def _grupper(sn: str) -> str:
    """Abonnentnummer i grupper om två/tre från vänster (Isof):
    5: 123 45, 6: 12 34 56, 7: 123 45 67, 8: 123 456 78."""
    if len(sn) <= 4:
        return sn
    if len(sn) == 5:
        return f"{sn[:3]} {sn[3:]}"
    if len(sn) == 6:
        return f"{sn[:2]} {sn[2:4]} {sn[4:]}"
    if len(sn) == 7:
        return f"{sn[:3]} {sn[3:5]} {sn[5:]}"
    if len(sn) == 8:
        return f"{sn[:3]} {sn[3:6]} {sn[6:]}"
    return f"{sn[:3]} {_grupper(sn[3:])}"


def tolka_telefon(ra: object, *, standardland: str = "46") -> Resultat:
    """Ett nummer -> E.164 ('+46701234567'), plus svensk visningsform.

    Klarar '070-123 45 67', '+46 (0)70 123 45 67', '0046701234567',
    '46701234567', '701234567' (Excel tappade nollan, bara mobil),
    '08-123 456 78'. Utländska nummer (+47 …) lagras i E.164 utan
    svensk validering. Anknytning ('ankn. 12', 'x12') läggs i info.
    """
    text = str(ra or "").strip()
    if not text:
        return Resultat(False, fel="tomt")
    ankn = None
    m = re.search(r"(?:ankn\.?|anknytning|ext\.?|x)\s*(\d{1,6})\s*$", text, re.IGNORECASE)
    if m:
        ankn, text = m.group(1), text[: m.start()]
    text = text.replace("(0)", "")
    if re.search(r"[A-Za-zÅÄÖåäö]", text):
        text = re.sub(r"^[^\d+]*", "", text)  # "Tel: 08-…", "mobil 070…"
    plus = text.lstrip().startswith("+")
    d = _siffror(text)
    if plus:
        intl = d
    elif d.startswith("00"):
        intl = d[2:]
    elif d.startswith("0"):
        intl = standardland + d[1:]
    elif d.startswith("46") and len(d) >= 10 and d[2] != "0":
        intl = d
    elif len(d) == 9 and _MOBIL.fullmatch(d):
        intl = "46" + d
    else:
        return Resultat(False, fel="saknar_prefix")
    if not 8 <= len(intl) <= 15:  # E.164: högst 15 siffror inkl. landskod
        return Resultat(False, fel="langd")
    info = {"anknytning": ankn} if ankn else {}
    if not intl.startswith("46"):
        return Resultat(True, varde="+" + intl, visning="+" + intl, info={**info, "land": "utlandet"})

    nsn = intl[2:]  # nationellt signifikant nummer, utan nolla
    if nsn.startswith("0"):
        return Resultat(False, fel="nolla_efter_46")
    if not 7 <= len(nsn) <= 13:
        return Resultat(False, fel="langd")
    nat = "0" + nsn
    if nsn[0] == "7":
        if _MOBIL.fullmatch(nsn):
            typ, rikt = "mobil", nat[:3]
        elif nsn.startswith(("710", "783")):
            typ, rikt = "mobilt_bredband_eller_gsmr", nat[:4]
        elif nsn.startswith("74"):
            typ, rikt = "personsokning", nat[:3]
        elif nsn.startswith(("75", "77")):
            typ, rikt = "personligt_eller_delad_kostnad", nat[:4]  # 0771-567 567
        else:
            return Resultat(False, fel="ogiltig_07_serie")
    elif nsn[0] == "8":
        typ, rikt = "geografiskt", "08"
    elif nsn.startswith("10"):
        typ, rikt = "geografiskt_oberoende", "010"
    elif nsn.startswith("20"):
        typ, rikt = "frisamtal", "020"
    elif nsn.startswith("9") and nsn[:3] in ("900", "939", "944"):
        typ, rikt = "betalteletjanst", nat[:4]
    elif nat[:3] in _RIKT3:
        typ, rikt = "geografiskt", nat[:3]
    else:
        typ, rikt = "geografiskt", nat[:4]
    sn = nat[len(rikt):]
    if typ == "geografiskt" and not 5 <= sn.__len__() <= 8:
        return Resultat(False, fel="abonnentnummer_langd")
    if typ == "mobil" and len(nsn) != 9:
        return Resultat(False, fel="langd")
    # Servicenummer (020, 077x) skrivs av myndigheterna 3+3: 0771-567 567.
    grupperat = f"{sn[:3]} {sn[3:]}" if len(sn) == 6 and not typ.startswith("geografiskt") else _grupper(sn)
    visning = f"{rikt}-{grupperat}"
    return Resultat(True, varde="+" + intl, visning=visning, info={**info, "typ": typ, "riktnummer": rikt})


def internationell_visning(e164: str) -> str:
    """'+46701234567' -> '+46 70 123 45 67' (nationell visning utan 0)."""
    r = tolka_telefon(e164)
    if not r.ok or not r.varde.startswith("+46"):
        return e164
    rikt, rest = r.visning.split("-", 1)
    return f"+46 {rikt[1:]} {rest}"


# ------------------------------------------------------------ bankgiro m.m.


def tolka_bankgiro(ra: object) -> Resultat:
    s = _siffror(ra)
    if len(s) not in (7, 8) or not luhn_ok(s):
        return Resultat(False, fel="bankgiro")
    return Resultat(True, varde=s, visning=f"{s[:-4]}-{s[-4:]}")


def tolka_iban_se(ra: object) -> Resultat:
    t = re.sub(r"\s", "", str(ra or "")).upper()
    if not re.fullmatch(r"SE\d{22}", t):
        return Resultat(False, fel="format")
    flyttad = t[4:] + t[:4]
    if int("".join(str(int(c, 36)) for c in flyttad)) % 97 != 1:
        return Resultat(False, fel="kontrollsiffror")
    return Resultat(True, varde=t, visning=" ".join(t[i:i + 4] for i in range(0, 24, 4)))
```

### 10.2 Testvektorer `test_svid.py`

```python
"""Testvektorer för svid.py. Körs med: python -I test_svid.py <katalog-med-svid>"""
import sys

sys.path.insert(0, sys.argv[1])
import svid as S  # noqa: E402

fel = 0
antal = 0


def kolla(namn, faktiskt, vantat):
    global fel, antal
    antal += 1
    ok = faktiskt == vantat
    if not ok:
        fel += 1
    print(f"{'OK ' if ok else 'FEL'} {namn}: {faktiskt!r}" + ("" if ok else f"  (väntat {vantat!r})"))


def r(res):
    return (res.ok, res.varde, res.visning, res.fel)


# --- Luhn och orgnr ---------------------------------------------------------
kolla("luhn Skatteverket 2021005448", S.luhn_ok("2021005448"), True)
kolla("luhn Transportstyrelsen 2021006099", S.luhn_ok("2021006099"), True)
kolla("luhn repo-exempel 5568249022", S.luhn_ok("5568249022"), True)
kolla("kontrollsiffra 202100544?", S.luhn_kontrollsiffra("202100544"), 8)
kolla("orgnr med bindestreck", r(S.tolka_orgnr("202100-5448")), (True, "2021005448", "202100-5448", None))
kolla("orgnr utan bindestreck", r(S.tolka_orgnr("2021005448")), (True, "2021005448", "202100-5448", None))
kolla("orgnr 16-prefix", r(S.tolka_orgnr("16202100-5448")), (True, "2021005448", "202100-5448", None))
kolla("orgnr ur momsnummer", r(S.tolka_orgnr("SE202100544801")), (True, "2021005448", "202100-5448", None))
kolla("orgnr med mellanslag", r(S.tolka_orgnr(" 556824 9022 ")), (True, "5568249022", "556824-9022", None))
kolla("orgnr fel kontrollsiffra", S.tolka_orgnr("202100-5449").fel, "kontrollsiffra")
kolla("orgnr omkastning 2021005484", S.tolka_orgnr("2021005484").fel, "kontrollsiffra")
kolla("orgnr nio siffror", S.tolka_orgnr("20210054").fel, "langd")
kolla("orgnr okänt 12-prefix", S.tolka_orgnr("172021005448").fel, "okant_prefix")
kolla("orgnr 16 + personnummer", S.tolka_orgnr("161212121212").fel, "16_med_personnummer")
kolla("orgnr 19 + orgnr", S.tolka_orgnr("192021005448").fel, "sekel_med_orgnr")
kolla("grupp 2 = offentlig", S.tolka_orgnr("2021005448").info["grupp"], "2")
kolla("grupp 5 = AB", S.tolka_orgnr("5568249022").info["grupptext"], "aktiebolag")

# --- Personnummer och samordningsnummer (enskild firma) ----------------------
kolla("personnummer 121212-1212 nekas som orgnr", S.tolka_orgnr("121212-1212").fel, "personnummer")
kolla("personnummer typ", S.tolka_identitet("19121212-1212").info["typ"], "personnummer")
kolla("personnummer kanon", S.tolka_identitet("19121212-1212").varde, "1212121212")
kolla("personnummer 100+ visning", S.tolka_identitet("121212+1212").visning, "121212+1212")
kolla("samordningsnummer Skatteverkets exempel 701063-2391",
      S.tolka_identitet("701063-2391").info["typ"], "samordningsnummer")
kolla("personnummer månad 13", S.tolka_identitet("121312-1210").ok, False)

# --- Momsnummer ---------------------------------------------------------------
kolla("momsnr ur orgnr", S.momsnr_ur_orgnr("202100-5448").varde, "SE202100544801")
kolla("momsnr med mellanrum", r(S.tolka_momsnr("SE 2021 0054 4801")), (True, "SE202100544801", "SE202100544801", None))
kolla("momsnr gemener", S.tolka_momsnr("se202100544801").ok, True)
kolla("momsnr slutar 02", S.tolka_momsnr("SE202100544802").fel, "slutar_inte_01")
kolla("momsnr fel luhn", S.tolka_momsnr("SE202100544901").fel, "kontrollsiffra")
kolla("momsnr för kort", S.tolka_momsnr("SE2021005448").fel, "format")
kolla("momsnr enskild firma", S.tolka_momsnr("SE121212121201").info["identitet"], "personnummer")
kolla("momsnr utländskt", S.tolka_momsnr("NO123456789MVA").fel, "utlandskt_ej_provat")

# --- Peppol -------------------------------------------------------------------
kolla("peppol 0007", S.peppol_id("202100-5448").varde, "0007:2021005448")

# --- Postnummer ---------------------------------------------------------------
kolla("postnr med mellanslag", r(S.tolka_postnummer("113 91")), (True, "11391", "113 91", None))
kolla("postnr utan mellanslag", S.tolka_postnummer("11391").visning, "113 91")
kolla("postnr SE-prefix", S.tolka_postnummer("SE-113 91").varde, "11391")
kolla("postnr fyra siffror", S.tolka_postnummer("1139").fel, "format")
kolla("postnr område 09", S.tolka_postnummer("091 00").fel, "omrade")
kolla("postnr område 99", S.tolka_postnummer("991 00").fel, "omrade")
kolla("postnr Mullsjö box", S.tolka_postnummer("565 18").info["omrade"], "56")

# --- Telefon ------------------------------------------------------------------
kolla("mobil 070", r(S.tolka_telefon("070-123 45 67")), (True, "+46701234567", "070-123 45 67", None))
kolla("mobil +46 (0)", S.tolka_telefon("+46 (0)70 123 45 67").varde, "+46701234567")
kolla("mobil 0046", S.tolka_telefon("0046701234567").varde, "+46701234567")
kolla("mobil 46 utan plus", S.tolka_telefon("46701234567").varde, "+46701234567")
kolla("mobil Excel tappade nollan", S.tolka_telefon("701234567").varde, "+46701234567")
kolla("mobil 0781 (078A fr.o.m. 2026-10-01)", S.tolka_telefon("0781234567").info["typ"], "mobil")
kolla("0783 är GSM-R, inte mobil", S.tolka_telefon("0783123456").info["typ"], "mobilt_bredband_eller_gsmr")
kolla("Stockholm 8 siffror", r(S.tolka_telefon("08-123 456 78")), (True, "+46812345678", "08-123 456 78", None))
kolla("Stockholm PTS 08-678 55 00", S.tolka_telefon("08-678 55 00").visning, "08-678 55 00")
kolla("Göteborg 031", S.tolka_telefon("031-12 34 56").visning, "031-12 34 56")
kolla("Umeå 090 sju siffror", S.tolka_telefon("090 1234567").visning, "090-123 45 67")
kolla("Skellefteå 0910", S.tolka_telefon("0910-123 45").visning, "0910-123 45")
kolla("Skatteverket 0771-567 567", S.tolka_telefon("0771-567 567").info["typ"], "personligt_eller_delad_kostnad")
kolla("Skatteverket 0771 visning", S.tolka_telefon("0771567567").visning, "0771-567 567")
kolla("frisamtal 020", S.tolka_telefon("020-567 000").info["typ"], "frisamtal")
kolla("frisamtal 020 visning", S.tolka_telefon("020567000").visning, "020-567 000")
kolla("010-nummer", S.tolka_telefon("010-123 45 67").visning, "010-123 45 67")
kolla("anknytning", S.tolka_telefon("08-678 55 00 ankn. 123").info["anknytning"], "123")
kolla("etikett Tel:", S.tolka_telefon("Tel: 08-678 55 00").varde, "+4686785500")
kolla("norskt nummer", r(S.tolka_telefon("+47 22 12 34 56")), (True, "+4722123456", "+4722123456", None))
kolla("för kort", S.tolka_telefon("12345").ok, False)
kolla("46 följt av 0", S.tolka_telefon("+46 070 123 45 67").fel, "nolla_efter_46")
kolla("ogiltig 07-serie 077? nej: 071 1", S.tolka_telefon("0711234567").fel, "ogiltig_07_serie")
kolla("internationell visning", S.internationell_visning("+46701234567"), "+46 70 123 45 67")
kolla("internationell visning 08", S.internationell_visning("+4686785500"), "+46 8 678 55 00")

# --- Bankgiro och IBAN --------------------------------------------------------
bg = "555555" + str(S.luhn_kontrollsiffra("555555"))
kolla("bankgiro 7 siffror visning", S.tolka_bankgiro(bg).visning, f"{bg[:3]}-{bg[3:]}")
kolla("bankgiro Bankgirots exempel 5555-5551?", S.tolka_bankgiro("5555-5551").ok, S.luhn_ok("55555551"))
kolla("IBAN SE exempel", S.tolka_iban_se("SE45 5000 0000 0583 9825 7466").visning, "SE45 5000 0000 0583 9825 7466")
kolla("IBAN fel kontroll", S.tolka_iban_se("SE46 5000 0000 0583 9825 7466").fel, "kontrollsiffror")

print(f"\n{antal - fel}/{antal} gröna")
sys.exit(1 if fel else 0)
```

### 10.3 Utfall

```
OK  luhn Skatteverket 2021005448: True
OK  luhn Transportstyrelsen 2021006099: True
OK  luhn repo-exempel 5568249022: True
OK  kontrollsiffra 202100544?: 8
OK  orgnr med bindestreck: (True, '2021005448', '202100-5448', None)
OK  orgnr utan bindestreck: (True, '2021005448', '202100-5448', None)
OK  orgnr 16-prefix: (True, '2021005448', '202100-5448', None)
OK  orgnr ur momsnummer: (True, '2021005448', '202100-5448', None)
OK  orgnr med mellanslag: (True, '5568249022', '556824-9022', None)
OK  orgnr fel kontrollsiffra: 'kontrollsiffra'
OK  orgnr omkastning 2021005484: 'kontrollsiffra'
OK  orgnr nio siffror: 'langd'
OK  orgnr okänt 12-prefix: 'okant_prefix'
OK  orgnr 16 + personnummer: '16_med_personnummer'
OK  orgnr 19 + orgnr: 'sekel_med_orgnr'
OK  grupp 2 = offentlig: '2'
OK  grupp 5 = AB: 'aktiebolag'
OK  personnummer 121212-1212 nekas som orgnr: 'personnummer'
OK  personnummer typ: 'personnummer'
OK  personnummer kanon: '1212121212'
OK  personnummer 100+ visning: '121212+1212'
OK  samordningsnummer Skatteverkets exempel 701063-2391: 'samordningsnummer'
OK  personnummer månad 13: False
OK  momsnr ur orgnr: 'SE202100544801'
OK  momsnr med mellanrum: (True, 'SE202100544801', 'SE202100544801', None)
OK  momsnr gemener: True
OK  momsnr slutar 02: 'slutar_inte_01'
OK  momsnr fel luhn: 'kontrollsiffra'
OK  momsnr för kort: 'format'
OK  momsnr enskild firma: 'personnummer'
OK  momsnr utländskt: 'utlandskt_ej_provat'
OK  peppol 0007: '0007:2021005448'
OK  postnr med mellanslag: (True, '11391', '113 91', None)
OK  postnr utan mellanslag: '113 91'
OK  postnr SE-prefix: '11391'
OK  postnr fyra siffror: 'format'
OK  postnr område 09: 'omrade'
OK  postnr område 99: 'omrade'
OK  postnr Mullsjö box: '56'
OK  mobil 070: (True, '+46701234567', '070-123 45 67', None)
OK  mobil +46 (0): '+46701234567'
OK  mobil 0046: '+46701234567'
OK  mobil 46 utan plus: '+46701234567'
OK  mobil Excel tappade nollan: '+46701234567'
OK  mobil 0781 (078A fr.o.m. 2026-10-01): 'mobil'
OK  0783 är GSM-R, inte mobil: 'mobilt_bredband_eller_gsmr'
OK  Stockholm 8 siffror: (True, '+46812345678', '08-123 456 78', None)
OK  Stockholm PTS 08-678 55 00: '08-678 55 00'
OK  Göteborg 031: '031-12 34 56'
OK  Umeå 090 sju siffror: '090-123 45 67'
OK  Skellefteå 0910: '0910-123 45'
OK  Skatteverket 0771-567 567: 'personligt_eller_delad_kostnad'
OK  Skatteverket 0771 visning: '0771-567 567'
OK  frisamtal 020: 'frisamtal'
OK  frisamtal 020 visning: '020-567 000'
OK  010-nummer: '010-123 45 67'
OK  anknytning: '123'
OK  etikett Tel:: '+4686785500'
OK  norskt nummer: (True, '+4722123456', '+4722123456', None)
OK  för kort: False
OK  46 följt av 0: 'nolla_efter_46'
OK  ogiltig 07-serie 077? nej: 071 1: 'ogiltig_07_serie'
OK  internationell visning: '+46 70 123 45 67'
OK  internationell visning 08: '+46 8 678 55 00'
OK  bankgiro 7 siffror visning: '555-5552'
OK  bankgiro Bankgirots exempel 5555-5551?: True
OK  IBAN SE exempel: 'SE45 5000 0000 0583 9825 7466'
OK  IBAN fel kontroll: 'kontrollsiffror'

68/68 gröna
```

---

## 11. Öppna frågor och antaganden

1. **Bolagsverkets HVD-fält** kunde inte läsas (captcha). Någon med konto
   behöver hämta OpenAPI-specen från utvecklarportalen.
2. **Riktnummerlistan** (tre- mot fyrsiffriga) är ur minnet; stäm av mot PTS
   innan visningen används.
3. **Vilken SNI-version SCB:s API levererar** efter 2025-12-08.
4. **Gruppnummer 1, 3, 4** saknar primärkälla.
5. **Priser** för Roaring, Creditsafe, UC, D&B och Bolagsfakta är inte
   publicerade; offert krävs.
6. **SS 613401** (adressens skrivsätt) är inte läst; PostNords adresseringssida
   svarade 403.
7. **VIES REST-API** och om Sverige returnerar namn/adress är inte verifierat.
8. Ska `postnr` lagras med eller utan mellanslag? Repot lagrar med
   (`NNN NN`) överallt; behåll det för att slippa migrera, men jämför alltid
   på siffrorna.

---

## 12. Källförteckning

- Skatteverket, SKV 709 utg. 8 "Organisationsnummer" (2006): https://docs.swedenconnect.se/technical-framework/mirror/skv/skv709-8.pdf
- Skatteverket, organisationsnummer: https://skatteverket.se/foretag/drivaforetag/startaochregistrera/organisationsnummer.4.361dc8c15312eff6fd235d1.html
- Skatteverket, personnummer: https://www.skatteverket.se/privat/folkbokforing/personnummer
- Skatteverket, samordningsnummer: https://skatteverket.se/privat/folkbokforing/samordningsnummer
- Skatteverket, momsregistreringsnummer: https://www.skatteverket.se/foretag/moms/saljavarorochtjanster/forsaljningtillandraeulander/kontrolleramomsregistreringsnummervatnummer/momsregistreringsnummer.4.18e1b10334ebe8bc80002649.html
- Skatteverket, Checking VAT numbers: https://www.skatteverket.se/servicelankar/otherlanguages/englishengelska/businessesandemployers/startingandrunningaswedishbusiness/vat/checkingvatnumbers.4.70685bee19c85dd5dd029eb.html
- Skatteverket, e-faktura/Peppol: https://skatteverket.se/servicelankar/otherlanguages/englishengelska/submittingeinvoicestous.4.7eada0316ed67d728240f4.html
- Skatteverket, Hämta företagsinformation: https://skatteverket.se/hamtaforetagsinfo
- SCB, Variabelbeskrivning API, företagsregistret: https://www.scb.se/contentassets/8a8eb5c3d45f461ea93482f8e8d4de4f/variabelbeskrivning-api.pdf
- SCB, Avgiftsfria uppgifter i företagsregistret: https://www.scb.se/vara-tjanster/bestall-data-och-statistik/foretagsregistret/avgiftsfria-uppgifter-i-foretagsregistret/
- SCB, SNI: https://www.scb.se/dokumentation/klassifikationer-och-standarder/standard-for-svensk-naringsgrensindelning-sni/
- SCB, SNI 2025: https://www.scb.se/dokumentation/klassifikationer-och-standarder/standard-for-svensk-naringsgrensindelning-sni/sni-2025/
- SCB, skrivhandledning: https://www.scb.se/om-scb/scbs-verksamhet/varumarkeshandbok/sa-uttrycker-vi-oss/
- Bolagsverket, API för värdefulla datamängder: https://bolagsverket.se/apierochoppnadata/hamtaforetagsinformation/vardefulladatamangder/apiforvardefulladatamangder.5513.html
- Bolagsverket, nyhet om avgiftsfri data: https://bolagsverket.se/apierochoppnadata/nyheterochreleaser/2025/avgiftsfridatanarbolagsverketochscblanserarvardefulladatamangder.5516.html
- Bolagsverket, avtal företagsinformation via API: https://bolagsverket.se/download/18.37b754ba19ceb00666a562d5/1788438045725/avtal-om-tjanst-for-foretagsinformation-via-api-foretag-privat.pdf
- PTS, Svenska telefoninummerplanen, status 2026-05-18: https://www.pts.se/contentassets/c67be6d4f65a456d9ed86a2542505b7b/nrplansammanstallning-2026-05-18.pdf
- Postnummerrådet, Postnummersystemet i Sverige (2017): https://shop-prod.postnord.com/siteassets/pdf/faktablad/postnummersystemet-i-sverige-171213.pdf
- Isof, gruppering av telefonnummer: https://frageladan.isof.se/visasvar.py?svar=61433
- Isof, klockslag: https://frageladan.isof.se/visasvar.py?svar=28111
- EU-kommissionen, VIES WSDL: https://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl
- Your Europe, VIES: https://europa.eu/youreurope/vies_en
- Peppol, Sverige: https://peppol.org/learn-more/country-profiles/sweden/
- Peppol, PEPPOL-COMMON-R049: https://docs.peppol.eu/tdd/sk/tdd-sk/trn-tdd/businessrule/PEPPOL-COMMON-R049/
- Bankgirot, modulus 10: https://www.bankgirot.se/globalassets/dokument/anvandarmanualer/10-modul.pdf
- Bankgirot, bankgironummer FAQ: https://bankgirot.se/en/services/incoming-payments/bankgiro-number/faq
- Bankgirot, kontonummeruppbyggnad: https://www.bankgirot.se/globalassets/dokument/anvandarmanualer/bankernaskontonummeruppbyggnad_anvandarmanual_sv.pdf
- Företagarna, SNI-byte: https://www.foretagarna.se/nyheter/riks/2025/januari/27-januari-kan-du-andra-foretagets-sni-kod/
- Fortnox, organisationsnummer: https://www.fortnox.se/fortnox-foretagsguide/ekonomisk-ordlista/organisationsnummer
- Spiris, organisationsnummer: https://www.spiris.se/blogg/foretagsstart/vad-ar-organisationsnummer
- G2, Roaring: https://www.g2.com/products/roaring-api/pricing
