# Snajp CRM och svensk standard

Vad Snajp CRM gör annorlunda än förlagan Twenty CRM, och varför. Skrivet 2026-11-26
för Anton och för den som bygger nästa del. Det går att läsa utan att ha läst något
annat.

Underlaget är researchen i `docs/crm/underlag/svensk-01` till `svensk-04`, Twentys
beskrivning i `twenty-01` och `twenty-03`, `docs/BESLUT.md` och koden som den såg ut
2026-11-26 kväll (senaste commit `577b8737`). Varje rad nedan säger var den kommer
ifrån.

Läget står i sista kolumnen och är ett av tre:

- **byggt**: koden finns. Filen står inom parentes.
- **beslutat, inte byggt**: någon har bestämt det, men koden saknas.
- **föreslås**: ingen har beslutat. Det är researchens eller det här dokumentets förslag.

Vem som beslutat står också där. "Anton" betyder att Anton själv sagt det. "Agentens
val" betyder att en agent valt, oftast efter att Anton bett den göra det den bedömer
bäst, och att Anton kan ändra det. Båda står så i `docs/BESLUT.md`.

En del av koden är inte committad än: migration 164 (affärer, uppgifter, anteckningar,
aktiviteter, bilagor) och `app/crm/objekt.py`. Den räknas som byggd, men den kan ändras
innan den landar.

---

## 1. Det viktigaste först

1. Organisationsnumret är bolagets nyckel, inte namnet eller domänen som i Twenty.
2. En enskild firmas nummer är ett personnummer och sparas aldrig. Bolaget märks i stället.
3. Privatpersoner hoppas över i synken, och sparas de är de alltid "kontakta inte".
4. Telefon lagras i ett format (`+46701234567`), så att samma nummer känns igen överallt.
5. Bolagsform och SNI-kod finns som egna fält, normaliserade som svenska system skriver dem.
6. Affärernas steg är svenska och har sannolikhet i procent. Twentys steg har det inte.
7. Synken tar emot data från tolv system, Fortnox och Visma inräknade, och kunden äger flödet.
8. Det som raderas ligger 30 dagar i en papperskorg och töms sedan på allt utom id och tider.

---

## 2. Ändringarna mot förlagan, område för område

### 2.1 Bolagets identitet

| Förlagan (Twenty) | Snajp CRM | Varför | Läge |
|---|---|---|---|
| Ett bolag känns igen på samma namn eller samma domän (`twenty-01` DM-050). | Källans id först, sedan organisationsnummer, sedan domän och namn, de två sista bara när exakt en post matchar. gmail.com räknas aldrig som bolagsdomän. | Svenska system matchar på organisationsnummer (Lime Go, Upsales, `svensk-03` §0.1). Två "Bygg AB" ska aldrig bli ett bolag. | byggt (`synk.py`, `160_crm_grund.sql`). Agentens val, BESLUT 2026-11-25. |
| Inget fält för organisationsnummer (`twenty-01` DM-050). | Numret lagras `NNNNNN-NNNN`, nyckeln som tio siffror, unik per kund. Kontrollsiffran räknas. `16`-prefix och momsnummer godtas som indata. | Organisationsnumret är svenskarnas nyckel (`svensk-01` §0.1, §1.3). | byggt (`falt.orgnr`, `160_crm_grund.sql`). |
| Saknas. | `19`/`20` framför ett organisationsnummer, och `16` framför ett personnummer, ska nekas i stället för att skalas av. | Kombinationerna finns inte och tyder på fel data (`svensk-01` §0.1, §9.1). | föreslås. Koden skalar av dem i dag (`falt.orgnr`). |
| Inget momsnummer. | `momsnr` kontrolleras: SE, tio siffror, 01 och kontrollsiffra. Utländska nummer godtas till formen. | `svensk-01` §2.1. | byggt (`falt.momsnr`). |
| Saknas. | Momsnumret räknas inte fram ur organisationsnumret som om bolaget vore momsregistrerat. Om det ska kontrolleras sker det mot EU:s VIES. | Formen bevisar inte registrering (`svensk-01` §0.3, §2.2). | föreslås för VIES. Funktionen som räknar fram numret finns men används inte (`falt.momsnr_ur_orgnr`). |
| Ingen bolagsform. | `bolagsform` normaliseras till AB, HB, KB, EF, EK, BRF med flera, ur namn, förkortning eller SCB:s tvåsiffriga kod. Utländska former sparas som de står. | Juridisk form går inte att läsa ur numret (SKV 709, `svensk-01` §1.1, §3). | byggt (`falt.bolagsform`, commit `577b8737`). Agentens val, BESLUT 2026-11-26. |
| Saknas. | Lagra SCB:s kod för juridisk form och visa namnet, i stället för en förkortning i text. | Koden är maskinläsbar och finns i SCB:s register (`svensk-01` §3.1). | föreslås. |
| Enskild firma finns inte som begrepp (`svensk-03` §14). | Bolaget får `enskild_firma = true` och sparas utan nummer. Det känns igen på domän eller namn. | Numret är ägarens personnummer, en personuppgift (IMY via `svensk-02` §1.3). | byggt (`adaptrar.mappa`, `160_crm_grund.sql`). Agentens val, BESLUT 2026-11-23 och 2026-11-25. |
| Ingen SNI-kod. | `sni` tar upp till fem koder utan punkt, huvudnäringen först. Fritext blir ett fältfel. | SCB:s register har fem koder per bolag (`svensk-01` §4.3). | byggt (`falt.sni`, commit `577b8737`). |
| Saknas. | Lagra vilken SNI-version koden hör till (2007 eller 2025) och läs in SCB:s kodlista. | SNI 2025 gäller sedan 8 december 2025. Koden avslöjar inte versionen (`svensk-01` §4.1). | föreslås. |
| Saknas. | Status hos Bolagsverket (konkurs, likvidation, avregistrerat) sätter bolaget som inaktivt. | `svensk-01` §3.2. Leadsregel 19 kastar redan avvecklade bolag. | föreslås. |
| Saknas. | Säteslän och kommunkod lagras som koder och används för länsfördelning, inte postnumret. | Ett postnummer kan beröra flera län (Postnummerrådet, `svensk-01` §5.1, §9.4). | föreslås. |

### 2.2 Personer och personuppgifter

| Förlagan (Twenty) | Snajp CRM | Varför | Läge |
|---|---|---|---|
| Person med namn, e-post, telefon, titel och LinkedIn (`twenty-01` DM-051). | Förnamn, efternamn, titel, e-post (unik per kund), telefon och mobil. | `160_crm_grund.sql`. | byggt (`160_crm_grund.sql`). |
| Saknas. | Personnummer sparas aldrig, varken på personen eller på ett bolag. | Personuppgift som säljarbetet inte behöver. | byggt (`adaptrar.mappa`). Agentens val, BESLUT 2026-11-23 och 2026-11-25. |
| Privatperson finns inte som begrepp. | Synken hoppar över privatpersoner om inte anslutningen slår på dem. Påslagna sparas de utan personnummer, märks och är alltid "kontakta inte". Databasen tillåter inget annat. | B2B-verktyg. Marknadsföring till konsumenter kräver samtycke och NIX-kontroll. | byggt (`161_crm_beslut.sql`, `synk.py`). Agentens val inom Antons svar, BESLUT 2026-11-26. |
| Ingen rättslig grund. | `rattslig_grund`: avtal, berättigat intresse eller samtycke. | GDPR art. 6 (`svensk-02` §1). | byggt (`160_crm_grund.sql`). |
| Saknas. | Rättslig grund per syfte, med samtyckets källa, datum, text och återkallelse. | SuperOffice gör det. MFL 19 § kräver samtycke för e-post till enskilda firmor (`svensk-02` §5, §9.1). | föreslås. |
| Vem som skapade posten (aktör: import, API, manuell) (`twenty-01` DM-019). | I dag bara `kalla` = manuell eller synk. Förslaget är källans typ, källans namn, insamlingsdatum och datum för art. 14-informationen. | Art. 14.2 f kräver att källan går att ange (`svensk-02` §2.1). | föreslås. |
| En spärrlista styr bara vilka mejl som synkas (`twenty-01` DM-059). | `kontakta_inte` på bolag och person. Adresserna läggs till sändspärren och stoppar också kampanjutskick, och det gäller personerna hos ett märkt bolag. | En märkning som ingen läste var en lucka. | byggt (`lagring.kontakta_inte_adresser`). Agentens val, BESLUT 2026-11-26. |
| Saknas. | Ett utfall gäller åt båda håll: "kontakta inte" på ett lead gäller bolaget i CRM:et, och tvärtom. | Annars ringer en säljare ett bolag som bett att slippa (`utfall.py`). | byggt (`utfall.py`, commit `2b5bce06`). |
| Saknas. | En gemensam spärr för mejl, ringlista, sms, export och webhooks, med orsak och datum, och en händelse ut när någon spärras. | Rätten att invända mot direktmarknadsföring gäller alla system. IMY bötfällde H&M 2023 när invändningar inte nådde alla system (`svensk-02` §0.2, §6.3). | föreslås. |
| Saknas. | NIX-status per nummer, med datum. Ringlistan vägrar nummer som kontrollerats för mer än två månader sedan. | NIX-reglerna (`svensk-02` §6). | föreslås. |
| Mjuk radering med `deletedAt`, återställning och permanent radering (`twenty-01` DM-180 till 182). | Papperskorg i 30 dagar, sedan töms raden på allt utom id och tider. `permanent=true` tömmer direkt. Anteckningar, aktiviteter och bilagor som pekar på posten töms med den. | Papperskorgen får inte bli ett register över borttagna personer. Art. 17. | byggt (`lagring.gor_gravsten`, `lagring.tom_papperskorg`, `164_crm_affarer_uppgifter.sql`). Agentens val, BESLUT 2026-11-25. |
| Saknas. | En adress med begränsad behandling (art. 18) synkas inte in, och posten töms inte. | Den som begärt begränsning har bett oss behålla uppgifterna orörda. | byggt (`synk.py`, `lagring.tom_papperskorg`). |
| Saknas. | Raderingsskriptet tar CRM-tabellerna, men söker bara på e-post. Telefon och organisationsnummer för enskild firma behöver bli sökbara. | Art. 15 och 17 (`svensk-02` §9.2). | byggt för e-post (`scripts/gdpr_radera.py`). Resten föreslås. |

### 2.3 Format

| Förlagan (Twenty) | Snajp CRM | Varför | Läge |
|---|---|---|---|
| Telefon i tre delar: nummer, landskod och riktnummer, tolkat med libphonenumber (`twenty-01` DM-008). | Ett fält i E.164: `+46701234567`. `070-123 45 67`, `0046…` och `+46 (0)70…` tolkas. | Ett nummer från ett telefonisystem ska matcha samma nummer i en leadslista (`svensk-01` §0.4). | byggt (`falt.telefon`). |
| Saknas. | Appen visar numret i svensk form, `070-123 45 67` och `08-123 456 78`. | Isof:s rekommendation (`svensk-01` §5.3). I dag visas `+46701234567` rakt av. | föreslås (`components/crm/app/kit.tsx`, `Lankpiller`). |
| Saknas. | Anknytningen skiljs från numret: `08-678 55 00 ankn. 123` blir `+4686785500`. | Förut blev den ett längre, felaktigt nummer (`svensk-01` §9.2, §9.3). | byggt (`falt.telefon`). Att spara anknytningen i ett eget fält föreslås. |
| Saknas. | Ett mobilnummer där Excel tappat nollan (`701234567`) räddas. | Samma fil ska ge samma utfall i listimporten och i CRM:et (`svensk-01` §9.2). | byggt (`falt.telefon`). |
| Saknas. | Nummerplanen kontrolleras (078A är mobil sedan 1 oktober 2026, 0783 är järnvägens nät). | `svensk-01` §9.2. | föreslås. |
| Postnummer som fritext (`twenty-01` DM-009). | Fem siffror, lagras och visas `113 91`. `SE-` framför tas bort. | `svensk-01` §5.1. Repot lagrar redan med mellanslag överallt. | byggt (`falt.postnr`). |
| Saknas. | Postnummerområdet kontrolleras: de två första siffrorna ska vara 10 till 98. | `svensk-01` §5.1. `091 00` och `991 00` finns inte. | byggt (`falt.postnr`). |
| Adress med gata, gata 2, ort, postnummer, delstat, land och koordinater (`twenty-01` DM-009). | Gatuadress, c/o, postnummer, postort och land (ISO-kod, Sverige som standard). Ingen delstat. | Svensk adress har c/o men ingen delstat (`svensk-03` §14). | byggt (`160_crm_grund.sql`, `adaptrar.mappa`). |
| Saknas. | Besöksadress och postadress som två adresser. | Postadressen är ofta en box i en annan stad (`svensk-01` §5.2). | föreslås. |
| Datum visas i användarens format eller relativt (`twenty-03` PS-071). | Datum lagras ISO 8601. In tas `31/12/2026`, `31.12.2026`, ISO med klockslag och epoktid. | `svensk-01` §6.1. | byggt (`falt.datum`). |
| Belopp i miljondelar med ISO-valuta (`twenty-01` DM-005). | Belopp i hela kronor som heltal, valuta SEK om inget annat anges. Tavlan summerar per valuta. | `docs/crm/API.md`, avsnittet om affärer. | byggt (`objekt.py`, `164_crm_affarer_uppgifter.sql`). |
| Saknas. | Omsättning visas i kronor med svensk tusentalsavgränsning. | `svensk-01` §6. | byggt (`components/crm/app/BolagPanel.tsx`). |
| Saknas. | Tal som skrivits med det typografiska minustecknet (U+2212) går att läsa in, och decimaler avrundas i stället för att kapas. | Det är vad `Intl` för sv-SE ger (`svensk-01` §6.2, §9.3). | byggt (`falt.heltal`). |
| Namn i två delar, förnamn och efternamn (`twenty-01` DM-010). | Samma. Ett helt namn delas vid första mellanslaget när källan bara har ett fält. | `adaptrar.mappa`. | byggt (`adaptrar.py`). |

### 2.4 Affärer och säljprocess

| Förlagan (Twenty) | Snajp CRM | Varför | Läge |
|---|---|---|---|
| Steget är ett val med fem engelska värden, NEW, SCREENING, MEETING, PROPOSAL och CUSTOMER, utan sannolikhet (`twenty-01` DM-052). | Egna steg per kund. Svensk standard: Ny 10 %, Kvalificerad 25, Möte bokat 40, Offert skickad 60, Förhandling 80, Vunnen 100, Förlorad 0. | Svenska system har steg med sannolikhet och avslut som vunnen eller förlorad (`svensk-03` §0.4). | byggt (`objekt.STANDARDSTEG`, `164_crm_affarer_uppgifter.sql`). Agentens val, BESLUT 2026-11-26. |
| Saknas. | Varje steg har en typ: öppen, vunnen eller förlorad. Det finns alltid minst ett av varje, och när affären når vunnen eller förlorad sätts ett avslutsdatum. | Tavlan ska alltid gå att använda. | byggt (`objekt.py`). |
| Saknas. | En förlustorsak som fritext. | `svensk-03` §8 (Pipedrive), §13. | byggt (`164_crm_affarer_uppgifter.sql`). |
| Saknas. | Förlustorsak ur en lista som kunden själv redigerar, med fritext som reserv. | Pipedrive och SuperOffice gör så, och listan går att räkna på (`svensk-03` §3.2, §8). | föreslås. |
| Saknas. | Status "Uppskjuten" med datum för återöppning. | SuperOffice (`svensk-03` §3.2). | föreslås. Inte tagit ställning. |
| Saknas. | Vägt värde (belopp gånger sannolikhet) på tavlan. | Pipedrive, Spiris (`svensk-03` §8, §6). Tavlan summerar i dag bara beloppen (`docs/crm/API.md`). | föreslås. |
| Saknas. | Kundrelation på bolaget: kund, tidigare kund, prospekt, partner, leverantör, övrigt. | Lime Go har ett eget fält för det, skilt från affären (`svensk-03` §0.2). Det styr Iris-uteslutningen. | byggt (`160_crm_grund.sql`). |
| Saknas. | Tidigare kunder är fria för Iris att bearbeta, om inte posten säger "kontakta inte". | Antons svar 2026-11-26. | byggt (`lagring.FRIA_RELATIONER`, `lagring.upptagen_rad`). Anton, BESLUT 2026-11-26. |
| Saknas. | Relationerna "pågående" och "ej aktuell" som Lime Go har. | `svensk-03` §14.1. | föreslås. |
| Saknas. | `kund_sedan` och `avtalsslut` på bolaget. | Avtalsslut är det Buddy vill bearbeta på (BESLUT 2026-11-23). | byggt (`160_crm_grund.sql`). |
| Saknas. | Ett vunnet utfall gör bolaget till kund och sätter "kund sedan". | `utfall.py`. | byggt (`utfall.registrera`). |
| Saknas. | Offert med e-signering (BankID, Oneflow, Scrive). | Svenska köpare väntar sig det (`svensk-03` §13). | föreslås. Förslaget är att vänta: ingen har tagit ställning. |

### 2.5 Synk och integrationer

| Förlagan (Twenty) | Snajp CRM | Varför | Läge |
|---|---|---|---|
| Kopplingar mot mejl och kalender, amerikanskt mönster (`svensk-03` §14, märkt som antagande där). | Inflöde från tolv format: HubSpot, Pipedrive, Lime, Lime Go, Upsales, Salesforce, Twenty, SuperOffice, Dynamics, Fortnox, Visma eEkonomi och ett eget. | Ekonomisystemet är den koppling en svensk köpare frågar efter först (`svensk-03` §0.5). | byggt (`adaptrar.STANDARD`, `160_crm_grund.sql`). |
| Saknas. | Synken är ett anrop kunden gör. Snajp hämtar inget och har ingen nyckel till kundens system. | Inget pollande jobb, ingen hemlighet hos oss. | byggt (`synk.py`). Agentens val, BESLUT 2026-11-25. |
| Saknas. | En standardmappning per system. Kunden lägger sin egen ovanpå, fält för fält. Hur ett värde tolkas avgörs av fältet, inte av mappningen. | Organisationsnumret heter olika hos varje kund (`svensk-04` §0.2). | byggt (`adaptrar.py`). |
| Saknas. | Fortnox och Visma: privatkunder känns igen på `Type` och `IsPrivatePerson` och hoppas över. | Kundregistret innehåller privatpersoner (`svensk-04` §10.7). | byggt (`adaptrar.STANDARD`). |
| Saknas. | Källan vinner som standard. Regeln väljs per anslutning, och fält som ändrats för hand bokförs. | Källan är kundens register. | byggt (`synk.py`). Agentens val, BESLUT 2026-11-25. |
| Saknas. | Konfliktregeln per fält, till exempel att ett organisationsnummer från Fortnox alltid vinner. | `svensk-04` §14.13. | föreslås. |
| Saknas. | Det som försvunnit ur källan: behåll, gör till tidigare kund eller radera, och bara efter en full synk. En full synk utan poster gör ingenting. | Ett tomt svar är oftare ett fel än en tömd kundstock. | byggt (`synk.py`). Agentens val, BESLUT 2026-11-25. |
| Saknas. | Kunden ser synkens fel i enkla ord. Supporten får hela rapporten med koder, där felaktiga värden står med sin form, inte sitt innehåll. | Antons svar 2026-11-26. | byggt (`supportrapport.py`, `163_crm_supportrapport.sql`). |
| Saknas. | Sammanslagna poster i källan pekas om till den post som överlever. | HubSpot byter id vid sammanslagning (`svensk-04` §13.4). I dag syns den förlorande posten som raderad. | föreslås (`docs/crm/API.md`, "Det som inte finns än"). |
| Saknas. | Visma.net får en egen mappning. Den gemensamma följer Visma eEkonomi. | `svensk-04` §11. | föreslås. |
| Webhooks signerade med HMAC (`svensk-04` §7). | Ändringsflöde och webhooks ut, signerade med HMAC och tid, med omförsök och leveranslogg i 30 dagar. | Den som håller en kopia ska få veta när något hänt. | byggt (`webhooks.py`, `handelser.py`, `162_crm_handelser_webhooks.sql`). |
| Saknas. | Vunnen affär blir order eller faktura i Fortnox, som i Upsales. | `svensk-03` §2.6. | föreslås. Inte tagit ställning. |

### 2.6 Språk och ton

| Förlagan (Twenty) | Snajp CRM | Varför | Läge |
|---|---|---|---|
| Etiketter kan översättas per språk, standardspråk engelska (`twenty-01` DM-058, DM-211). | Varje komponent med text finns på svenska och engelska. | Antons regel 2026-10-02, grindad av `INV-COPY-001`. | byggt (`components/crm/app/`, `lib/i18n.tsx`). |
| Engelska fältnamn i API:t. | API:t har engelska fältnamn och fel på båda språken (`message` och `meddelande`). | Den som integrerar sitter oftast med ett engelskt system. | byggt (`crm_v1.py`). Agentens val, BESLUT 2026-11-25. |
| Company, Person, Opportunity. | Bolag, Person, Affär. Tabellerna heter `crm_bolag` och `crm_personer`. | Snajp säger redan bolag, och ordet stämmer med organisationsnumret (`svensk-03` §14.1). | byggt (`160_crm_grund.sql`, `164_crm_affarer_uppgifter.sql`). |
| Saknas. | Felkoder översatta till klartext i appen. | Kunden ska förstå vad som gick fel. | byggt (`lib/crm/felkoder.ts`). |
| Saknas. | Ordlistan i övrigt: kundrelation, förlustorsak, vägt värde, urval för sparad vy som används för utskick, att göra för uppgiftslistan. | `svensk-03` §14.1. | föreslås. |

### 2.7 Dataskydd och drift

| Förlagan (Twenty) | Snajp CRM | Varför | Läge |
|---|---|---|---|
| Saknas i underlaget. | Varje CRM-tabell har radskydd per kund i databasen, också händelser, webhooks och bilagor. | En kund ska aldrig se en annans data. | byggt (`160`, `162`, `164` i `db/migrations/`). |
| Saknas. | CRM-tabellerna speglas inte till development. | Development är en spegel av produktionen; CRM:et väntar på beslut om det. | byggt (`160_crm_grund.sql`, kommentaren). Agentens val, BESLUT 2026-11-25. |
| Saknas i det lästa underlaget. | CRM-koden anropar ingen språkmodell. DeepSeek får aldrig se kunddata. | Tredjelandsöverföring utan avtal (`CLAUDE.md`, beslut 2026-08-24). | byggt (inga modellanrop i `app/crm/`). Anton, 2026-08-24. |
| Saknas. | En integrations nyckel får veta att ett mejl eller en anteckning finns på tidslinjen, inte vad som skrevs. | Dataminimering. | byggt (`tidslinje.py`). |
| Saknas. | Webbplatsbedömningen följer aldrig med i kundlistan eller tidslinjen. Prospektet läses med en uttrycklig kolumnlista. | Antons beslut 2026-10-08 om att bedömningen är hemlig. | byggt (`kundlista.py`, `tidslinje.py`). |
| Saknas. | Gallras inte efter 24 månader som leads. Personer utan någon händelse på 24 månader läggs i en lista som kunden tar ställning till. Allt raderas när avtalet upphör. | Kunden är personuppgiftsansvarig och Snajp biträde. Att tyst radera en kunds register är ett större fel än att behålla det. | beslutat, inte byggt. Agentens val, BESLUT 2026-11-26. Ingen kod hittad för listan eller raderingen vid avtalsslut. |
| Saknas. | Skrivande anrop stoppas tills biträdesavtalet är registrerat. | Avtalsgrinden (`INV-AVTAL-001`). | byggt (`crm_v1.py`, `_avtal`). |
| Saknas. | Biträdesavtalet tar upp CRM:et, webhooks som kundens instruktion och hur radering och spärr förs vidare. | Avtalet saknar CRM (`docs/JURIDIK_ATGARDER.md` punkt 22, `svensk-02` §2.3). | föreslås. Öppen fråga i BESLUT 2026-11-25. |
| Saknas. | Händelseloggen säger vilka fält som ändrades, aldrig värdena. Ett felaktigt organisationsnummer skrivs aldrig i synkens fellogg. | En logg som överlever en radering får inte bli ett register över det som raderats. | byggt (`handelser.py`, `adaptrar.mappa`, `supportrapport.form`). |
| Saknas. | En webhook-leverans bär hela posten och sparas 30 dagar. Raderingsskriptet hittar en person där. | `docs/crm/API.md`, `scripts/gdpr_radera.py`. | byggt (`webhooks.py`, `162_crm_handelser_webhooks.sql`). |
| Saknas. | Logg per API-nyckel: vilken nyckel, vad, hur många poster och när, utan personuppgifter. | Efter en läckt nyckel måste vi kunna säga vad den nådde (`svensk-02` §7). | föreslås. |
| Saknas. | Nycklar med omfång (läsa, skriva, synka, administrera) som bara når CRM-API:t. | En nyckel i kundens CRM ska inte nå resten av Snajp. | byggt (`160_crm_grund.sql`, `app/api/deps.py`). Agentens val, BESLUT 2026-11-25. |
| Saknas. | CRM:et är ett tillägg, fritt under provperioden. Grinden sitter i backenden. | Anton beslutade tillägget. Agenten lade grinden i backenden eftersom API:t inte passerar webben. | byggt (`tillgang.py`, `161_crm_beslut.sql`). Anton och agentens val, BESLUT 2026-11-26. |
| Saknas. | En post för CRM:et i registerförteckningen. | Art. 30 (`svensk-02` §7). | föreslås. |

---

## 3. Vad de svenska systemen gör som förlagan inte gör

Bara det som researchen belägger (`svensk-03`). För varje punkt: tar efter, avstår
eller har inte tagit ställning.

### Lime Go och Lime CRM

- Fält för organisationsnummer, och uppslag av bolaget i Dun & Bradstreets databas med
  nattlig uppdatering (`svensk-03` §1.1, §1.4). Tar efter numret. Har inte tagit
  ställning till uppslag ur register (fråga 4).
- Kundrelation med fem värden, skild från affären (§1.1). Tar efter med sex egna värden.
  Pågående och ej aktuell saknas (fråga 9).
- Fortnox- och Visma-koppling som tillägg, och kundnumret i ekonomisystemet som andra
  nyckel (§1.4, §1.6). Tar efter inåt: kundnumret är Fortnox-postens id. Har inte tagit
  ställning till flödet utåt (fråga 8).
- Radering genom anonymisering på ett slutdatum, och en portal där den registrerade
  hämtar sina uppgifter (§1.5). Tar efter tömningen efter 30 dagar. Har inte tagit
  ställning till utdrag åt den registrerade.
- Koncernstruktur och karta (§1.3, §1.4). Har inte tagit ställning.
- Tidslinjen visar historik, mejl, dokument och ärenden i ett flöde (§1.1). Tar efter:
  tidslinjen samlar CRM, leads och support (`tidslinje.py`).

### Upsales

- Matchar bolag på exakt namn eller organisationsnummer (§2.4). Tar efter, med numret
  före namnet och namnet bara när det är entydigt.
- Steg med sannolikhet som kunden ändrar (§2.2). Tar efter.
- Bolagsdata som skriver över det användaren angett (§2.4). Avstår: källan är kundens
  register, och en handändring kan skyddas per anslutning.
- Vunnen affär blir order eller faktura i Fortnox (§2.6). Har inte tagit ställning.

### SuperOffice

- Status Öppen, Såld, Förlorad och Uppskjuten (§3.2). Tar efter de tre första. Har inte
  tagit ställning till Uppskjuten (fråga 10).
- Rättslig grund och samtyckeskälla per syfte på varje person (§3.5). Tar efter delvis:
  en grund per person, utan syfte och källa (fråga 2).
- Urval, statiska och dynamiska, för utskick (§3.3). Har inte tagit ställning.
- Sammanslagning av bolag med val av primär post (§3.4). Har inte tagit ställning för
  användaren. Synken slår aldrig ihop på namn.
- Röd markering av affärer med förfallna aktiviteter (§3.2). Har inte tagit ställning.

### Membrain

- Ringlistor och ring direkt från CRM:et (§4). Tar efter genom leadsflödets ringlista
  och utfall som gäller åt båda håll (`utfall.py`).
- Offertkonfigurator och e-signering (§4). Har inte tagit ställning.

### Fortnox

- Kundregister med privatkunder märkta (`svensk-04` §10). Tar efter: de hoppas över.
- Offert och order (`svensk-03` §5). Har inte tagit ställning.

### Spiris (fd Visma Spcs)

- Affärsmöjlighet med sannolikhet på en tavla med egna steg (§6). Tar efter.
- Varje affär ska ha en tidsbestämd aktivitet (§6). Har inte tagit ställning. Uppgifter
  kan kopplas till en affär, men det krävs inte (`objekt.py`).
- Offert i versioner med BankID-signering, och vunnen affär blir projekt (§6). Har inte
  tagit ställning.

---

## 4. Det som inte är avgjort

Frågor till Anton, de viktigaste först.

**1. En gemensam spärr för alla kanaler?**
För: IMY:s beslut mot H&M visar att en invändning ska nå alla system, och i dag finns
tre spärrar som inte känner till varandra (`svensk-02` §3.2). Emot: arbete i mejl,
ringlista, export och webhooks samtidigt. Förslag: ja, en spärr med kanal, orsak och
datum, och en händelse ut när någon spärras.

**2. Ska varje person bära källa och insamlingsdatum?**
För: art. 14 kräver att källan går att ange, och "offentliga företagsuppgifter" täcker
inte en adress från bolagets egen sajt (`svensk-02` §2.1). Emot: fler fält i synken.
Förslag: ja, källans typ, källans namn och insamlingsdatum. Samtycke per syfte väntar.

**3. Webhooks med hela posten, eller bara id och typ?**
För tunna händelser: en felriktad webhook läcker mindre, och en radering eller
begränsning som skett efteråt respekteras när mottagaren hämtar posten (`svensk-02`
§8.2). För hela posten: enklare för mottagaren, och så är det byggt (`docs/crm/API.md`).
Förslag: tunna händelser för personer och enskilda firmor, hela posten för bolag.

**4. Ska bolag berikas ur SCB:s företagsregister?**
För: avgiftsfritt sedan juni 2025, och ger juridisk form, status, SNI, säte och
reklamspärr per bolag (`svensk-01` §7.2). En svensk säljare väntar sig att skriva ett
nummer och få resten. Emot: nyckeln är personlig och får inte delas, och leadsregel 1
säger att registret är ett filter. Bolagsnivå bryter inte mot den. Förslag: ja, bara
bolagsnivå, aldrig personer.

**5. Får CRM-data någonsin nå en språkmodell?**
För: sammanfattningar på tidslinjen. Emot: biträdesavtalet och registerförteckningen
måste ändras, och CRM:et anropar ingen modell i dag (`svensk-02` §11, A4). Förslag:
bara som kundval, och bara i EU.

**6. Vem tvättar mot NIX?**
För att Snajp gör det: kunden slipper. Det kostar ungefär 5 000 kr en gång plus 13 till
17 öre per nummer, och Snajp blir biträde även där (`svensk-02` §6.2). För att kunden
gör det: inget avtal för oss. Förslag: kunden tvättar själv och laddar upp utfallet tills
efterfrågan finns.

**7. Ska ringlistan ta enskilda firmor som NIX-reglerna tillåter?**
För: NIX tillåter samtal om yrkesrollen till momsregistrerade näringsidkare (`svensk-02`
§6.1). Emot: dagens totalspärr (leadsregel 15) är enkel och säker. Förslag: behåll
spärren.

**8. Ska synken mot Fortnox och Visma gå åt båda håll?**
För: vunnen affär som blir order är det svenska köpare väntar sig (`svensk-03` §11).
Emot: Buddys system är inte känt, och Fortnox händelser kommer över en långlivad
anslutning som kräver en egen process (`svensk-04` §10.7). Förslag: bara in tills
första kunden med Fortnox finns.

**9. Ska kundrelationen få "pågående" och "ej aktuell"?**
För: Lime Go har dem, och "ej aktuell" skiljer ett nej från ett prospekt (`svensk-03`
§14.1). Emot: prospekt och affärens steg täcker pågående. Förslag: lägg till "ej
aktuell", vänta med "pågående".

**10. Förlustorsak ur lista, och status Uppskjuten?**
För: en lista går att räkna på, och Uppskjuten finns i SuperOffice (`svensk-03` §3.2,
§8). Emot: fritexten räcker för få affärer. Förslag: lista med fritext som reserv.
Uppskjuten väntar.

---

## 5. Det som inte är gjort i researchen

**Inte belagt eller inte undersökt.**

- Bildgranskningen av de svenska systemen är inte gjord. `svensk-03` §12 listar 30
  sidor med skärmbilder, och flera är märkta "bilder ej granskade".
- Svenska etiketter i Lime Go, Upsales, Pipedrive och Salesforce är antaganden, inte
  lästa (`svensk-03` §15).
- Jämförelsen med Twenty i `svensk-03` §14 bygger på det amerikanska mönstret, inte på
  en ny läsning av Twenty.
- Bolagsverkets fria datamängder gick inte att läsa (bildcaptcha). Fältlistan är inte
  avstämd (`svensk-01` §7.1, §11).
- Vilken SNI-version SCB:s API levererar är inte kontrollerat (`svensk-01` §11).
- Listan över tre- och fyrsiffriga riktnummer är skriven ur minnet (`svensk-01` §5.3).
- Standarden för adressers skrivsätt (SS 613401) är inte läst, och PostNords sida
  svarade 403 (`svensk-01` §5.2).
- EU:s REST-API för VIES, och om Sverige returnerar namn och adress, är inte
  verifierat (`svensk-01` §2.2).
- EDPB:s riktlinjer 1/2024 version 2 är inte lästa i fulltext. Ingenting i `svensk-02`
  är prövat av jurist, och nio frågor står kvar till jurist (`svensk-02` §11, J1 till J9).
- Fältnamn för Upsales, Visma.net och Fortnox `Type` och `WWW` är antagna eller
  sekundära (`svensk-04` §5, §10.3, §11.2). En testkörning mot riktiga konton saknas.
- Priser för Roaring, Creditsafe, UC och Dun & Bradstreet är inte publicerade
  (`svensk-01` §7.4).
- Telefoni utöver Telavox och Dstny, och kopplingar till Microsoft 365 och Google, är
  inte belagda (`svensk-03` §11).

**Där underlaget och koden säger olika.** Koden gäller för vad som är byggt.

- Underlagen hänvisar till migration 153. Den heter 160 sedan development fick en egen
  153 (BESLUT 2026-11-26).
- `svensk-02` §9.3 säger att webhooks saknas. De finns sedan migration 162.
- `svensk-02` §0.3 säger att en raderad post lämnas ut hel. Det gäller fortfarande under
  papperskorgens 30 dagar, men sedan töms raden, och `permanent=true` tömmer direkt.
- `svensk-02` §9.2 säger att raderingsskriptet saknar CRM-tabellerna. De finns där nu,
  men bara med e-post som nyckel.
- `svensk-01` §9.3 kallar `app/crm/falt.py` ocommittad. Den är committad. De fyra fel
  provet visade (anknytning, tappad nolla, postnummerområde, minustecknet U+2212) är
  rättade 2026-11-26 och har ett eget test (`tests/crm/test_falt_och_adaptrar.py`).
  Det femte, att 0783 (järnvägens nät) godtas som vilket nummer som helst, står kvar.
- `svensk-01` §8.1 säger att `sni` är en enda text. Den är fortfarande text, men bär nu
  upp till fem koder åtskilda med komma.
- `svensk-04` §15 säger att Lime Go saknas bland systemen. Den finns nu, i
  `adaptrar.SYSTEM` och i databasens villkor.
- Bolagsform och SNI byggdes i commit `577b8737`. Valet att lagra förkortningen i stället
  för SCB:s kod står nu i `docs/BESLUT.md` 2026-11-26, som agentens val.
