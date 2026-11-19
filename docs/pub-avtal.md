# Personuppgiftsbiträdesavtal

> **UTKAST 2026-11-17, inte juridiskt granskat.**
>
> Avtalet får inte skrivas under förrän en jurist har läst det, varje
> platshållare är ifylld och varje punkt i listan "Åtgärder som ska vara
> genomförda före avtalets ikraftträdande" (efter Bilaga 2) är avbockad.
> Platshållare står inom hakparentes och börjar med FYLL, så att de går att
> söka fram.
>
> Faktaunderlag: nulägesinventeringen 2026-11-17
> (`docs/compliance/nulage-inventering.md`) och Railways driftuppgifter
> samma dag (`docs/compliance/bevis/`). Mappen är undantagen från git
> lokalt och finns inte i repot. Bilaga 2 tar bara upp skydd som
> inventeringen belägger.

### Öppna frågor till juristen

1. **Ansvarsbegränsning.** Vilket tak är rimligt för ett PUB-avtal, och hur
   förhåller det sig till art. 82 och till sanktionsavgifter enligt art. 83?
   Pilotavtalet begränsar ansvaret till pilotavgiften (§6.1). Gäller det
   också för dataskyddsbrott?
2. **Enskild firma eller aktiebolag.** Snajp är en enskild firma.
   Organisationsnumret är ägarens personnummer, och ägaren svarar personligen
   för avtalets förpliktelser. Ska firman bolagiseras innan första kunden
   skriver under?
3. **Webbpoolen (punkt 14).** Håller gränsdragningen mellan kundens data och
   offentlig bolagsdata, när uppgifterna samlas in under ett uppdrag för en
   kund och sedan används i tjänster till andra kunder? Klausulen är
   preliminär sedan 2026-10-08.
4. **Revisionsrättens omfattning (punkt 11).** Rimlig frekvens, varsel,
   kostnadsfördelning och om en extern revisor ska krävas, för en leverantör
   med en eller två personer.
5. **Fristen för incidentunderrättelse (punkt 9).** Hur många timmar ska
   skrivas in? Pilotavtalet föreslår 24 timmar. Incidentrutinen anger ingen
   siffra, bara "snabbare än 72 timmar".
6. **AI-förordningen (punkt 13).** Snajp tillhandahåller AI-systemet och
   kunden använder det. Är rollfördelningen för art. 50.1 (upplysning om att
   man interagerar med AI) och art. 50.2 (märkning av genererad text) rätt
   beskriven, och hur ska automatiskt skickade mejlsvar behandlas?
7. **Utskick utan mänskligt godkännande.** Pilotavtalet §3.1 säger att inga
   säljmejl skickas utan att en människa hos kunden godkänt dem. Tjänsten har
   i dag ett autopilotläge där leadsagenten skickar utan granskning efter de
   tre första utskicken. Vilken lydelse ska gälla?
8. **Testmiljön som spegel.** Snajps testmiljö (`development`) är en
   fullständig kopia av produktionens data och synkas var tionde minut via
   GitHub Actions på amerikanska servrar. Ryms det inom kundens instruktion
   och kapitel V, eller måste kopian minimeras eller pseudonymiseras först?

---

**Parter**

1. **Snajp (enskild firma)**, organisationsnummer [FYLL: Snajps
   organisationsnummer], [FYLL: Snajps postadress], kontaktadress i
   dataskyddsfrågor [FYLL: Snajps dataskyddsadress, t.ex. integritet@snajp.se]
   ("Snajp" eller "Biträdet").
2. **[FYLL: kundens firma]**, organisationsnummer [FYLL: kundens
   organisationsnummer], [FYLL: kundens postadress], kontaktperson för
   avtalet [FYLL: namn och e-postadress] ("Kunden" eller "den
   Personuppgiftsansvarige").

## 1. Bakgrund och avtalets förhållande till huvudavtalet

1.1 Parterna har ingått [FYLL: huvudavtalets namn och datum, t.ex.
pilotavtal daterat ÅÅÅÅ-MM-DD] ("Huvudavtalet"). Enligt Huvudavtalet
tillhandahåller Snajp en eller flera av följande tjänster: supportagenten, som
läser och besvarar Kundens inkommande kundmejl och chattar; leadsagenten, som
tar fram B2B-prospekt och skickar utskick i Kundens namn; och
kvittohanteraren, som läser av kvitton ("Tjänsten").

1.2 När Snajp levererar Tjänsten behandlar Snajp personuppgifter för Kundens
räkning. Detta avtal reglerar den behandlingen enligt artikel 28 i
dataskyddsförordningen (EU) 2016/679 ("GDPR").

1.3 Detta avtal är en integrerad del av Huvudavtalet. Det ersätter §5 i
pilotavtalet. Vid motstridighet gäller detta avtal före Huvudavtalet i frågor
om behandling av personuppgifter.

1.4 Bilagorna ingår i avtalet:
- Bilaga 1: Instruktion för behandlingen
- Bilaga 2: Tekniska och organisatoriska säkerhetsåtgärder
- Bilaga 3: Underbiträden

## 2. Definitioner

2.1 Begrepp som definieras i GDPR har samma betydelse i detta avtal, bland
annat personuppgifter, behandling, personuppgiftsansvarig,
personuppgiftsbiträde, registrerad, personuppgiftsincident och tredjeland.

2.2 Dessutom gäller:
- **Kundens data:** de personuppgifter Snajp behandlar för Kundens räkning
  enligt Bilaga 1.
- **Underbiträde:** ett annat personuppgiftsbiträde som Snajp anlitar och som
  behandlar Kundens data.
- **Inställningarna:** de val Kunden gör i Tjänstens gränssnitt, se punkt 3.2.
- **Autonominivå:** regeln per ärendekategori som avgör om ett svar blir ett
  utkast som en människa godkänner (*utkast*), skickas direkt (*auto*) eller
  alltid går till en människa (*eskalera*).
- **Modelleverantör:** ett underbiträde som tillhandahåller den språkmodell
  som bearbetar text och bilder i Tjänsten.

## 3. Behandling endast på dokumenterade instruktioner (art. 28.3 a)

3.1 Snajp behandlar Kundens data endast enligt Kundens dokumenterade
instruktioner. Det gäller också överföring till tredjeland. Undantag gäller
bara om unionsrätten eller svensk rätt kräver behandlingen. Snajp informerar
då Kunden om kravet innan behandlingen sker, om lagen inte förbjuder det.

3.2 Kundens instruktioner är:
1. detta avtal med Bilaga 1;
2. Inställningarna i Tjänsten, bland annat:
   - autonominivån per ärendekategori;
   - kunskapsbasen och svarsreglerna;
   - målgruppskriterierna för leadsagenten (bransch, geografi, storlek),
     avsändaridentitet och utskicksläge;
   - vilka kanaler och integrationer som är påslagna (punkt 15);
   - lagringstiden enligt Kundens gallringspolicy i Tjänsten;
3. skriftliga instruktioner som Kundens kontaktperson eller en annan av Kunden
   utsedd person lämnar via e-post till [FYLL: Snajps adress för
   instruktioner].

3.3 En ändring av Inställningarna gäller som ny instruktion från den stund
Kunden gör den. Snajp sparar uppgift om när autonominivån för en kategori
ändrats.

3.4 Anser Snajp att en instruktion strider mot GDPR eller annan
dataskyddslag, informerar Snajp Kunden utan dröjsmål. Snajp får avvakta med
att följa instruktionen tills Kunden bekräftat eller ändrat den.

3.5 Snajp behandlar inte Kundens data för egna ändamål. Undantaget i punkt 14
gäller uppgifter som enligt den punkten inte är Kundens data.

## 4. Sekretess (art. 28.3 b)

4.1 Endast personer som behöver Kundens data för att leverera, underhålla
eller felsöka Tjänsten får åtkomst. Åtkomsten begränsas till det som behövs
för uppgiften.

4.2 Varje person som har åtkomst, anställd eller uppdragstagare, ska ha åtagit
sig skriftlig tystnadsplikt eller omfattas av lagstadgad tystnadsplikt.
Åtagandet gäller även efter att uppdraget upphört.

4.3 Snajp för en förteckning över vilka personer som har åtkomst till Kundens
data. I dag är det [FYLL: namn eller roller för de personer som har åtkomst].
Kunden får del av förteckningen på begäran.

## 5. Säkerhet (art. 28.3 c och art. 32)

5.1 Snajp vidtar de tekniska och organisatoriska åtgärder som anges i
Bilaga 2. Åtgärderna ska ge en säkerhetsnivå som är lämplig med hänsyn till
risken, behandlingens art och att Kundens data kan innehålla känsliga
uppgifter i fritext.

5.2 Snajp får ändra åtgärderna i Bilaga 2, men en ändring får inte sänka den
samlade skyddsnivån. Väsentliga ändringar meddelas Kunden skriftligt.

5.3 Snajp behandlar inte Kundens data i Tjänsten innan avtalet är undertecknat
av båda parter.

## 6. Underbiträden (art. 28.2 och 28.4, art. 28.3 d)

6.1 Kunden ger genom detta avtal ett allmänt skriftligt förhandstillstånd till
att Snajp anlitar underbiträden. De underbiträden som anlitas när avtalet
ingås står i Bilaga 3 och godkänns genom avtalet.

6.2 Snajp underrättar Kunden skriftligt minst [FYLL: antal dagar, förslag 30]
dagar innan ett underbiträde läggs till eller byts ut. Underrättelsen anger
underbiträdets namn, vilka uppgifter det får, var behandlingen sker och vilken
överföringsmekanism som används.

6.3 Kunden får invända mot ändringen inom fristen. Invänder Kunden på skälig
grund och kan parterna inte enas, får Kunden säga upp Huvudavtalet och detta
avtal till den dag ändringen skulle börja gälla, utan kostnad för den del av
avtalstiden som inte har löpt.

6.4 Snajp ingår skriftliga avtal med varje underbiträde. Avtalen ska ålägga
underbiträdet samma skyldigheter som Snajp har enligt detta avtal, särskilt
tillräckliga garantier för lämpliga tekniska och organisatoriska åtgärder.

6.5 Snajp ansvarar fullt ut mot Kunden för att underbiträdena fullgör sina
skyldigheter.

6.6 Kunden får på begäran ta del av de delar av underbiträdesavtalen som rör
dataskydd.

## 7. Bistånd med de registrerades rättigheter (art. 28.3 e)

7.1 Snajp hjälper Kunden att besvara begäranden från registrerade om
tillgång, rättelse, radering, begränsning, dataportabilitet och invändning
enligt kapitel III i GDPR. Hjälpen ges genom lämpliga tekniska och
organisatoriska åtgärder, så långt det är möjligt med hänsyn till
behandlingens art.

7.2 Tar en registrerad kontakt med Snajp direkt, vidarebefordrar Snajp
begäran till Kunden inom [FYLL: antal arbetsdagar, förslag 2] arbetsdagar.
Snajp besvarar inte begäran själv, om inte Kunden instruerar Snajp att göra
det.

7.3 På Kundens begäran tar Snajp fram ett utdrag med de uppgifter Tjänsten
lagrar om en viss e-postadress, eller raderar dem, inom [FYLL: antal dagar,
förslag 10] dagar. Spärrlistan för utskick behålls även efter radering, så
att personen inte kontaktas igen.

7.4 Avregistreringar från leadsagentens utskick registreras direkt i
Tjänsten och gäller alla framtida utskick från Kunden.

## 8. Bistånd med säkerhet, konsekvensbedömning och förhandssamråd (art. 28.3 f)

8.1 Med hänsyn till behandlingens art och den information Snajp har, hjälper
Snajp Kunden att fullgöra skyldigheterna i artiklarna 32 till 36:
1. **Säkerhet (art. 32):** Snajp lämnar den information om Tjänstens skydd som
   Kunden behöver för sin egen riskbedömning.
2. **Incidenter (art. 33 och 34):** enligt punkt 9.
3. **Konsekvensbedömning (art. 35):** Snajp lämnar en beskrivning av
   behandlingen, dataflödet, underbiträdena och de risker Snajp själv har
   identifierat. Snajp delar sin egen konsekvensbedömning av supportagenten
   när den är uppdaterad.
4. **Förhandssamråd (art. 36):** Snajp lämnar det underlag Kunden behöver om
   Kunden måste samråda med Integritetsskyddsmyndigheten.

8.2 Bistånd som går utöver det Snajp normalt tillhandahåller ersätts enligt
[FYLL: timpris eller hänvisning till Huvudavtalets prislista].

## 9. Personuppgiftsincidenter (art. 33)

9.1 Snajp underrättar Kunden utan onödigt dröjsmål efter att Snajp fått
kännedom om en personuppgiftsincident som rör Kundens data, och senast inom
[FYLL: antal timmar, pilotavtalet föreslår 24] timmar.

9.2 Underrättelsen går till [FYLL: kundens adress för incidentunderrättelser]
och innehåller, så långt det är känt:
1. när incidenten upptäcktes;
2. vad som hände;
3. vilka kategorier av uppgifter och registrerade som berörs, och ungefär hur
   många;
4. troliga konsekvenser;
5. vilka åtgärder Snajp har vidtagit eller föreslår.

9.3 Information som inte finns vid första underrättelsen lämnas så snart den
finns. Snajp väntar inte med underrättelsen tills utredningen är klar.

9.4 Det är Kunden som anmäler till Integritetsskyddsmyndigheten och informerar
de registrerade. Snajp anmäler inte en incident som rör Kundens data för
Kundens räkning, om inte Kunden begär det.

9.5 Snajp dokumenterar varje incident i sin incidentlogg och följer sin
incidentrutin (Bilaga 2, punkt G).

## 10. Radering och återlämnande när avtalet upphör (art. 28.3 g)

10.1 När Huvudavtalet upphör lämnar Snajp på Kundens begäran, inom 14 dagar,
en export av Kundens data i maskinläsbart format: kunskapsbas, ärenden och
svar, prospekt och leadslistor (CSV eller JSON) samt bokföringsunderlag (SIE4
där det finns). Begäran ska göras senast [FYLL: antal dagar] dagar efter att
avtalet upphört.

10.2 Senast 30 dagar efter att avtalet upphört raderar Snajp Kundens data ur
Tjänsten. Raderingen omfattar alla miljöer där uppgifterna finns, även
testmiljön och cache. Snajp bekräftar raderingen skriftligt.

10.3 Säkerhetskopior: [FYLL: om och hur säkerhetskopior tas, hur länge de
sparas och när Kundens data senast är borta ur dem]. Fram till dess skyddas
uppgifterna i säkerhetskopior enligt detta avtal och används inte för något
annat än återställning.

10.4 Uppgifter i jobbkön och cachen raderas automatiskt när deras livslängd
löper ut (Bilaga 2, punkt E).

10.5 Snajp får behålla uppgifter längre bara om unionsrätten eller svensk rätt
kräver det. Snajp informerar då Kunden om vilka uppgifter det gäller och
varför.

10.6 Spärrlistan för utskick (punkt 7.3) raderas tillsammans med övriga
uppgifter, om inte Kunden instruerar annat.

## 11. Information och granskning (art. 28.3 h)

11.1 Snajp ger Kunden tillgång till all information som behövs för att visa
att skyldigheterna i artikel 28 och i detta avtal är uppfyllda.

11.2 Kunden, eller en oberoende granskare som Kunden utser och som har
tystnadsplikt, får granska Snajps efterlevnad. Granskning ska aviseras
skriftligt minst [FYLL: antal dagar] dagar i förväg och görs högst
[FYLL: antal gånger] gång per år, utom efter en personuppgiftsincident eller
om en tillsynsmyndighet kräver det.

11.3 Granskningen ska genomföras så att den inte stör driften och inte ger
tillgång till andra kunders data. Varje part står för sina egna kostnader,
[FYLL: kostnadsfördelning om granskningen kräver mer än X timmar av Snajps
tid].

11.4 Snajp informerar Kunden om en tillsynsmyndighet begär information om
behandlingen av Kundens data, om det inte är förbjudet enligt lag.

## 12. Överföring till tredjeland

12.1 Kundens data behandlas inom EU/EES. Det gäller lagring, drift och
bearbetning i språkmodeller.

12.2 Överföring till tredjeland, eller åtkomst från tredjeland, får ske bara
1. till ett underbiträde i Bilaga 3 där överföringen och mekanismen anges,
   och
2. med stöd av en giltig mekanism enligt kapitel V i GDPR: beslut om adekvat
   skyddsnivå (till exempel EU–US Data Privacy Framework för certifierade
   mottagare) eller EU-kommissionens standardavtalsklausuler, med en
   dokumenterad bedömning av överföringen och de kompletterande åtgärder som
   behövs.

12.3 Ett underbiträde som är etablerat utanför EU/EES räknas som en
överföring även om lagringen sker inom EU/EES, om underbiträdet kan få
åtkomst till uppgifterna. Bilaga 3 anger för varje underbiträde vad som
gäller.

12.4 Språkmodeller som behandlar Kundens data utanför EU/EES utan en giltig
mekanism används inte för Kundens data.

## 13. Språkmodeller och AI

13.1 **Ingen träning.** Kundens data används inte för att träna, finjustera
eller på annat sätt förbättra språkmodeller, varken Snajps eller
modelleverantörernas. Snajp anlitar bara modelleverantörer på villkor som
förbjuder sådan användning.

13.2 **Vilka som får innehållet.** Den text, de bilder och de bilagor Tjänsten
bearbetar skickas till de modelleverantörer som anges i Bilaga 3, och inga
andra. Personnummer i inkommande text maskeras innan texten går till
modelleverantören (Bilaga 2, punkt B). Andra känsliga uppgifter i fritext,
till exempel hälsouppgifter, maskeras inte.

13.3 **Modellen styr inte utskicken.** Det är Tjänstens kod som skickar mejl,
aldrig språkmodellen. Modellen kan inte välja vilken kunds data den arbetar
med (Bilaga 2, punkt B).

13.4 **Autonominivån och art. 22.** Tjänsten levereras med mänsklig granskning
påslagen för alla ärendekategorier. Kunden kan ställa om enskilda kategorier
till *auto*. Då upphör den mänskliga granskningen för de kategorierna. Kunden
ansvarar för att bedöma om ett automatiskt svar är ett beslut som enbart
grundas på automatiserad behandling enligt artikel 22, och för att ha rättslig
grund och information till de registrerade som stämmer med det valet.

13.5 **Information till Kundens kunder.** Kunden informerar sina egna kunder
om att ärenden behandlas med hjälp av AI, enligt artikel 13. Snajp
tillhandahåller en textmall. Texten på Kundens webbplats är Kundens ansvar.

13.6 **Märkning av AI-genererade svar (AI-förordningen (EU) 2024/1689,
art. 50).** Parterna fördelar ansvaret så här:
1. Snajp tillhandahåller AI-systemet och ansvarar för att det är utformat så
   att den som skriver till Kundens chatt eller får ett automatiskt skickat
   svar får veta att svaret kommer från ett AI-system, om det inte är
   uppenbart (art. 50.1). Snajp ansvarar också för den tekniska märkningen av
   genererad text enligt art. 50.2, i den mån den gäller Tjänsten.
2. Kunden använder AI-systemet. Kunden tar inte bort eller döljer den
   upplysning Tjänsten lägger till, och ansvarar för den information Kunden
   själv lämnar till sina kunder.
3. Ett svar som en människa hos Kunden har granskat och godkänt räknas som
   Kundens eget svar.

## 14. Leadsagenten och Snajps egen behandling av bolagsdata

14.1 **Utskick i Kundens namn.** Leadsagentens utskick skickas i Kundens namn
och för Kundens räkning. Kunden är personuppgiftsansvarig för behandlingen av
mottagarnas och kontaktpersonernas uppgifter. Kunden ansvarar för
1. rättslig grund för utskicken, inklusive intresseavvägning när den grunden
   är berättigat intresse;
2. att utskicken följer marknadsföringslagen och lagen om elektronisk
   kommunikation;
3. att uppgifterna som identifierar Kunden som avsändare är korrekta;
4. innehållet i utskick som Kunden har godkänt.

14.2 Snajp ansvarar för att Tjänstens sändspärrar fungerar som de är
beskrivna i Bilaga 2, punkt D. Bland annat lägger Tjänsten in avregistrering
och, när adressen är personlig, information enligt artikel 14 i varje
utskick.

14.3 **Källor.** På Kundens instruktion hämtar leadsagenten uppgifter ur
offentliga bolagsregister och från bolagens egna webbplatser. Registrens
uppgifter om enskilda personer används inte som kontaktuppgifter. Enskilda
firmor sållas bort innan något utskick görs.

14.4 **Snajps egen behandling av offentlig bolagsdata** *(preliminär lydelse
2026-10-08, ej juridiskt granskad; samma lydelse som pilotavtalet klausul
5.2a)*. Uppgifter om juridiska personer som är offentliga (bolagsnamn,
organisationsnummer, webbplats, ort och län, bransch) samt Snajps egen
bedömning av ett bolags publika webbplats är inte Kundens data i avtalets
mening. Snajp får använda dem för egna ändamål, även i tjänster till andra
kunder. Snajp är då självständigt ansvarig, och behandlingen omfattas inte av
detta avtal. Det gäller aldrig
1. personuppgifter (kontaktpersoner, e-postadresser, telefonnummer);
2. enskilda firmor;
3. Kundens utkast, anteckningar eller status;
4. uppgiften om att just Kunden har bearbetat ett visst bolag.

## 15. Kanaler och integrationer som Kunden själv slår på

15.1 Kunden kan koppla Tjänsten till egna konton hos andra leverantörer, till
exempel:
- e-post via IMAP, Gmail eller Microsoft 365;
- Meta (WhatsApp och Messenger), Slack och Microsoft Teams;
- HubSpot och Pipedrive;
- Kundens egna MCP- eller HTTP-integrationer.

15.2 När Kunden slår på en sådan integration instruerar Kunden Snajp att
hämta uppgifter från, eller lämna uppgifter till, det kontot. Leverantören av
kontot är Kundens egen leverantör och mottagare på Kundens instruktion. Den
är inte Snajps underbiträde och står inte i Bilaga 3.

15.3 Kunden ansvarar för sitt avtal med den leverantören, för de uppgifter
som finns hos den och för att integrationen har stöd i Kundens egen
behandling. Snajp ansvarar för behandlingen fram till att uppgifterna lämnat
Tjänsten och från att de kommit in i den.

15.4 Nycklar och åtkomsttoken som Kunden lämnar för integrationerna lagras
krypterade (Bilaga 2, punkt C).

## 16. Ansvar

16.1 Varje part ansvarar för skada som parten orsakar genom att bryta mot
detta avtal eller mot GDPR, enligt artikel 82 i GDPR.

16.2 Ansvarsbegränsningen i Huvudavtalet gäller också detta avtal, med de
undantag som anges där. Snajps sammanlagda ansvar enligt detta avtal är
begränsat till [FYLL: belopp eller beräkningsgrund, t.ex. avgifterna under
de senaste tolv månaderna]. Begränsningen gäller inte vid uppsåt eller grov
vårdslöshet.

16.3 Har en part betalat skadestånd eller sanktionsavgift för skada som helt
eller delvis beror på den andra parten, har den rätt att kräva den andra
parten på motsvarande del.

## 17. Avtalstid och upphörande

17.1 Avtalet gäller från att båda parter undertecknat det och så länge Snajp
behandlar Kundens data, även efter att Huvudavtalet upphört och fram till att
radering enligt punkt 10 är bekräftad.

17.2 Punkterna 4 (sekretess), 10 (radering) och 16 (ansvar) gäller även efter
att avtalet i övrigt upphört.

## 18. Ändringar

18.1 Ändringar och tillägg ska vara skriftliga och undertecknade av båda
parter. Undantag är ändringar av Inställningarna (punkt 3.3), ändringar av
Bilaga 2 enligt punkt 5.2 och ändringar av Bilaga 3 enligt punkt 6.

18.2 Ändras dataskyddslagstiftningen eller en tillsynsmyndighets praxis så att
avtalet behöver anpassas, ska parterna förhandla om ändringen i god tro.

## 19. Tillämplig lag och tvist

19.1 Svensk rätt gäller för avtalet.

19.2 Tvister avgörs av allmän domstol med [FYLL: tingsrätt] som första
instans.

---

Ort och datum ______________________

**Snajp (enskild firma)**

______________________
[FYLL: namnförtydligande]

**[FYLL: kundens firma]**

______________________
[FYLL: namnförtydligande och befattning]

---

## Bilaga 1: Instruktion för behandlingen

### 1. Ändamål

Snajp behandlar Kundens data enbart för att leverera Tjänsten enligt
Huvudavtalet:
1. **Supportagenten:** läsa, klassificera och besvara inkommande kundmejl och
   chattar, föreslå svar ur Kundens kunskapsbas, skicka svar enligt
   autonominivån och lämna över ärenden till Kundens personal.
2. **Leadsagenten:** ta fram B2B-prospekt efter Kundens kriterier, hitta
   kontaktvägar på bolagens egna webbplatser, skriva utkast och skicka utskick
   i Kundens namn, hantera svar, avregistreringar och Kundens ringlista.
3. **Kvittohanteraren:** läsa av kvitton ur Kundens kopplade mejlkonto och
   uppladdade filer och föreslå kontering.
4. Drift, felsökning, säkerhet och support för Tjänsten.

### 2. Kategorier av registrerade

1. Kundens kunder och andra som skriver till Kundens kundtjänst, chatt eller
   kanaler. Det kan vara konsumenter.
2. Kontaktpersoner hos bolag som leadsagenten tar fram åt Kunden, och
   mottagare av Kundens utskick.
3. Personer som förekommer i Kundens kvitton och bokföringsunderlag.
4. Kundens anställda och andra användare av Tjänsten hos Kunden, i den mån
   deras uppgifter förekommer i ärenden, utkast och loggar.

### 3. Kategorier av personuppgifter

1. Namn, e-postadress, telefonnummer och, i förekommande fall, titel och
   arbetsgivare.
2. Innehållet i meddelanden, chattar och bilagor.
3. Bilder och kvitton. Originalfilen till ett kvitto sparas inte, bara en
   kontrollsumma och de avlästa uppgifterna.
4. Uppgifter om prospekt: kontaktperson, roll, kontaktvägar och information
   från bolagets egen webbplats.
5. Ärendehistorik, klassificeringar, utkast, godkännanden och Tjänstens
   steglogg över hur ett svar togs fram.
6. Avregistreringar och spärrlista.

**Känsliga uppgifter.** Kundens kunder kan skriva vad som helst i fritext.
Kundens data kan därför innehålla uppgifter som omfattas av artikel 9
(till exempel hälsa), artikel 10 eller personnummer, utan att Snajp eller
Kunden begärt dem. Personnummer maskeras innan texten går till
modelleverantören. Andra känsliga uppgifter maskeras inte. Kunden ska ta
hänsyn till detta i sin egen riskbedömning och i valet av autonominivå.

### 4. Behandlingens art

Insamling via Kundens kanaler och integrationer, lagring, strukturering,
klassificering och textgenerering med språkmodell, sökning i kunskapsbasen,
hämtning av publika webbsidor, utskick av e-post, synkronisering till Kundens
CRM, export och radering.

### 5. Lagringstid

Kundens data sparas så länge Kunden bestämmer i sin gallringspolicy i
Tjänsten, dock längst [FYLL: lagringsperiod, beslutas av ägaren; ska stämma
med gallringsjobbet och integritetspolicyn]. Spärrlistan för utskick sparas
så länge avtalet gäller. Vid avtalets upphörande gäller punkt 10.

### 6. Var behandlingen sker

Se Bilaga 3.

---

## Bilaga 2: Tekniska och organisatoriska säkerhetsåtgärder

Bilagan tar bara upp åtgärder som är belagda i nulägesinventeringen
2026-11-17. Det som saknas eller inte är verifierat står i listan efter
bilagan.

### A. Åtkomst och separation mellan kunder

1. Varje kunds data ligger i en egen avgränsning i databasen, med
   radnivåsäkerhet (RLS). Applikationen ansluter med en databasroll som inte
   kan kringgå radnivåsäkerheten.
2. Språkmodellens verktyg saknar parametrar för vilken kund de gäller.
   Modellen kan därför inte välja att läsa en annan kunds data.
3. Oinloggade användare skickas till inloggningen. Administrativa sidor är
   stängda för den som inte är plattformsadministratör.
4. Applikationen och databasen kommunicerar över driftleverantörens privata
   nätverk.

### B. Språkmodeller och automatiska utskick

1. Personnummer i inkommande text känns igen (datum- och kontrollsiffra) och
   maskeras innan texten skickas till modelleverantören.
2. Text från externa källor (kundmejl, webbsidor) läggs in i modellens
   instruktioner som opålitlig text inom avgränsade ramar, som skydd mot
   promptinjektion.
3. Språkmodellen kan inte skicka något. Utskick görs bara av Tjänstens kod,
   efter Tjänstens kontroller.
4. Leadsagentens hämtning av webbsidor är begränsad till det publika
   internet.
5. Uppstarten stoppas om en modelleverantör som Snajp spärrat för riktig data
   (DeepSeek) konfigureras i en miljö med riktig kunddata.
6. Bilder bearbetas till en textbeskrivning. Originalfilen till ett kvitto
   sparas inte.

### C. Kryptering och hemligheter

1. Utgående anrop till modelleverantören och till e-postleverantören går över
   HTTPS.
2. Nycklar och token som Kunden lämnar för sina integrationer krypteras med
   en separat nyckel innan de lagras.
3. Filer med hemligheter hålls utanför versionshanteringen. Tjänsten startar
   inte om huvudnyckeln har sitt standardvärde.
4. Jobbkön och cachen nås över driftleverantörens privata nätverk.

### D. Utskick från leadsagenten

1. Varje utskick kontrolleras i sändögonblicket mot spärrlistan,
   avsändarnamn, avregistreringslänk och policylänk.
2. Avregistrering sker med en länk, gäller alla framtida utskick från Kunden
   och kontrolleras vid varje utskick.
3. Information enligt artikel 14 läggs in i utskick till personliga adresser.
4. Ett bolag kontaktas inte igen inom 90 dagar. Befintliga kunder till Kunden
   kontaktas inte.
5. Volymtak: upptrappning från 20 utskick per dag, högst 100 per dag och
   kund, ett i minuten. Utskick bara vardagar 08 till 17.
6. Utskicken stoppas automatiskt om andelen klagomål överstiger 0,1 procent
   eller andelen studsar 3 procent.
7. De tre första utskicken för en ny kund granskas av en människa.
8. Enskilda firmor sållas bort före research och utskick.

### E. Lagring och radering

1. Uppgifter i jobbkön och cachen har automatisk livslängd. Agentens svar på
   pågående jobb sparas högst en timme.
2. Det finns verktyg för registerutdrag och radering per e-postadress, som
   behåller spärrlistan.

### F. Spårbarhet

1. Varje anrop får ett spårnings-id som följer med i svar och loggar.
2. Tjänsten loggar varje agentkörning steg för steg och varje beslut om
   klassificering och utskick.

### G. Organisation och utveckling

1. Snajp har en skriftlig incidentrutin: vem som bedömer, vad som
   dokumenteras direkt, att läckta nycklar roteras först och att Kunden
   underrättas utan onödigt dröjsmål.
2. Ändringar i koden går igenom automatiska tester och kontroller av
   säkerhetsregler innan de når produktion. Produktionsgrenen är skyddad och
   kräver granskning av en utsedd ägare.
3. Testmiljön indexeras inte av sökmotorer.

### Åtgärder som ska vara genomförda före avtalets ikraftträdande

Det här är brister som inventeringen visar. Ingen av dem får beskrivas som
genomförd i avtalet förrän den är det. Bocka av med datum och belägg.

- [ ] **Jobbkön skyddad i transit.** Jobbkön nåddes med `redis://` utan TLS
      från både produktion och testmiljö, mot en gemensam databas på Redis
      Clouds gratisplan, som saknar TLS-stöd. Ägaren valde 2026-11-17 att
      flytta jobbkön till Railways egen Redis i stället för en betald plan.
  - [x] Jobbkön flyttad till Railways egen Redis, nådd över det privata
        nätverket, med var sin databas för produktion och testmiljö.
        Verifierad i uppstartsloggen i båda miljöerna 2026-11-17.
  - [ ] Den gamla Redis Cloud-databasen raderad, så att rad 3 i Bilaga 3 kan
        strykas. Ägarens beslut, inte gjort.
- [ ] **TLS mot databasen** verifierad, eller dokumenterat att trafiken bara
      går över Railways privata nätverk.
- [ ] **Säkerhetskopiering och återställning.** Inget belägg för backup,
      återställning till tidpunkt eller återställningsprov. Fyll i punkt 10.3
      först när rutinen finns. Står kvar: Railway kräver Pro-planen för
      säkerhetskopior av volymer, och kontot ligger på en lägre plan.
      Produktionsdatabasen har ingen säkerhetskopia. Två vägar, ägaren har
      inte valt: (a) Railway Pro med dagliga, veckovisa och månatliga kopior,
      eller (b) ett eget schemalagt jobb som tar en databasdump till en
      lagringsplats i EU.
- [ ] **Kryptering i vila** hos Railway dokumenterad.
- [ ] **Gallring i drift.** Inget gallringsjobb är schemalagt, ingen period är
      satt för någon kund, och gallringen omfattar bara supportmejl, inte
      leads, agentloggar, chattar eller kampanjer. Integritetspolicyn påstår
      i dag 24 månaders automatisk gallring.
- [ ] **Radering och registerutdrag** utökade till tabeller som tillkommit
      efter 2026-08-25 (ringlista, listor, CRM, demolänkar, kundminne,
      kvitton, kampanjer) och provkörda.
- [ ] **Kundnycklar krypterade i testmiljön.** De ligger i klartext där.
- [ ] **Radnivåsäkerheten verifierad mot Railway-produktionen.** Den manuella
      verifieringen gjordes mot den gamla Supabase-databasen.
- [ ] **Avtalsgrinden påslagen** för Kunden (`kraver_avtal`). Den är av som
      standard i drift, så en ny kund får trafik utan undertecknat avtal.
      Grinden som standard för manuellt upplagda kunder (INV-AVTAL-001) är
      byggd 2026-11-17 men inte committad eller driftsatt.
- [ ] **AI-upplysning i kod** i chatten och i automatiskt skickade mejlsvar
      (punkt 13.6). Byggd 2026-11-17 (INV-AI-001) men inte committad eller
      driftsatt.
- [ ] **Reservvägen till Google AI Studio** spärrad i miljöer med riktig data,
      på samma sätt som DeepSeek-spärren. Spärren (INV-DATA-004) är byggd
      2026-11-17 men inte committad eller driftsatt; i drift ligger vägen
      kvar.
- [ ] **Separata servicekonton** för Vertex AI per miljö. I dag används samma
      konto i produktion, testmiljö och lokalt hos utvecklare.
- [ ] **Avtal med underbiträdena** tecknade och kontrollerade, inklusive att
      modelleverantörerna inte tränar på Kundens data (punkt 13.1). Fyll i
      Bilaga 3.
- [ ] **Beslut om TypeSafe och ScrapeGraphAI** (Bilaga 3). För TypeSafe är
      kundmejlen beslutade och genomförda: ägaren beslutade 2026-11-17 att
      kundmejl inte går dit, och inkorgsklassningen är avstängd i båda
      miljöerna. Kvar: begära radering av den kundmejltext som redan
      skickats, och beslut om leadsdelen. ScrapeGraphAI är inte beslutad.
- [ ] **Beslut om testmiljön.** Den är en fullständig kopia av produktionens
      data, synkas via GitHub Actions, och utkast kan skickas därifrån.
      Minimera, pseudonymisera eller ta upp den uttryckligen i avtalet.
- [ ] **Beslut om utvecklarverktyg med AI** som läser testmiljöns kunddata.
      Antingen stoppas det, eller tas leverantören upp i Bilaga 3.
- [ ] **Gamla stacken avvecklad:** Render-tjänsterna stängda, Render-nyckeln
      roterad, den gamla Supabase-databasens historiska kunddata bedömd och
      gallrad, och de två öppna incidentposterna från 2026-08-24 bedömda.
- [ ] **Plattformsadminlösenordet bytt.** Det har legat i skript och
      historik.
- [ ] **Tystnadsförbindelser** undertecknade av alla som har åtkomst
      (punkt 4.2).
- [ ] **Dataskyddsadress** inrättad (integritet@), så att punkt 3.2 och 7.2
      har en riktig adress.

---

## Bilaga 3: Underbiträden

Läget 2026-11-17. Behandlingsplats för Railway är hämtad ur Railway samma
dag. Avtal, överföringsmekanism och övriga behandlingsplatser kommer ur
leverantörsgranskningen 2026-11-17, som bygger på leverantörernas publicerade
villkor, DPA:er och dokumentation och på deltagarlistan för EU-U.S. Data
Privacy Framework (DPF) samma dag.

| # | Underbiträde | Tjänst | Vilka uppgifter | Behandlingsplats | Avtal | Överföringsmekanism |
|---|---|---|---|---|---|---|
| 1 | Google Cloud, Vertex AI ([FYLL: avtalspart enligt Googles avtal, se faktureringskontot]) | Språkmodell (Gemini), inbäddningar, bildtolkning och grundad webbsökning | Kundmejl och chattar med maskerade personnummer, bilder och kvitton, research om prospekt (sidtext, kontaktnamn), utkast. Den grundade sökningen får sökfrågor med bolagskriterier, inte kundmejl | Anrop till europe-west1 (Belgien), reserv europe-west4 (Nederländerna) och europe-north1 (Finland). Behandlingen sker inom EU (Googles EU-multiregion), inte nödvändigtvis i det land som anropas. Meddelanden som Googles säkerhetsfilter flaggar kan sparas upp till 90 dagar i samma region eller multiregion och granskas av människor. Grundad webbsökning: Google sparar sökfrågor härledda ur prompten i upp till tre dygn | Cloud Data Processing Addendum (version 23 oktober 2025). Gäller automatiskt via Google Cloud-villkoren §5.2. Registrering av dataskyddskontakt i konsolen är frivillig och inte gjord | DPF (Google LLC aktiv 2026-11-17) och SCC (moduler C2P, P2P, P2C) enligt DPA:n |
| 2 | Railway (Railway Corporation, San Francisco) | Drift av applikationen, databasen (Postgres), bakgrundsjobb, jobbkö och cache (Redis, sedan 2026-11-17) | Alla Kundens data. Jobbkön och cachen nås över Railways privata nätverk, med en egen databas per miljö. Finns i två miljöer: produktion och en testmiljö som är en fullständig kopia av produktionen (se listan efter Bilaga 2) | Amsterdam (Railway-regionen `ams`, EU West) för samtliga tjänster och volymer i båda miljöerna, hämtat 2026-11-17. Om EU West körs på Railways egen hårdvara eller i ett publikt moln är ej belagt. Säkerhetskopior sparas upp till 89 dagar; var de lagras är ej belagt ([FYLL: Railways skriftliga besked om infrastruktur och backupplats]) | Railways DPA. DPA signeras via DocuSign, ännu inte signerad 2026-11-17. Den gäller inte förrän Railway har undertecknat | Enligt DPA:n DPF i första hand (Railway Corporation aktiv 2026-11-17), annars SCC modul 1–3. Gäller först när DPA:n är signerad |
| 3 | Redis Cloud (avtalspart Redis EMEA Ltd, London), avvecklas | Tidigare jobbkö och cache. Används inte i driften sedan 2026-11-17, då jobbkön flyttades till Railway (rad 2). Raden stryks när databasen är raderad | Inga nya uppgifter sedan flytten. Kvar finns svarscache och arbetsminne från tiden före, tills livslängden gått ut eller databasen raderats. Pågående jobb lever högst en timme | Google Cloud europe-west1 (Belgien). Anslutningen saknade TLS medan databasen användes | Redis DPA (version 26 mars 2025). Gäller automatiskt via Redis Cloud Agreement §5.3. Avtalet anger inte om gratisnivån omfattas ([FYLL: bekräfta betald plan]) | SCC modul 2/3 med UK-tillägg. Avtalsparten finns i Storbritannien. Redis finns inte i DPF-listan |
| 4 | Resend (Plus Five Five, Inc., San Francisco) | Utgående e-post och leveransrapporter (studs, klagomål) | Supportsvar till Kundens kunder, Kundens utskick från leadsagenten, mottagaradresser och innehåll | Mejlen skickas från eu-west-1 (Irland). Mejlinnehåll, metadata och loggar lagras i USA i 30 dagar. Ingen inställning flyttar lagringen till EU. Resend anlitar i sin tur bland andra AWS och TypeSafe AI, Inc. i USA | Resends DPA (version 2025-12-31). Gäller automatiskt med avtalet. En signerad kopia finns i Resends dashboard och är inte nedladdad | DPF (Resend står som "Active – Re-certification under Review" 2026-11-17) och SCC modul 1–3 oberoende av DPF. Överföringsbedömning (TIA) är inte gjord |
| 5 | GitHub, Inc. (Microsoft), GitHub Actions | Synkronisering från produktion till testmiljö var tionde minut (bara i den riktningen sedan 2026-10-17), samt körning av databasmigreringar | Produktionens data passerar den GitHub-hostade körmaskinen vid varje synk | GitHub-hostade körmaskiner i Azure (vissa i AWS). Region anges inte och kan inte väljas: USA eller andra länder | GitHub Data Protection Agreement gäller bara Team, Enterprise och Copilot. Kontot har Free-planen och omfattas inte enligt GitHubs publika villkor | Ingen avtalad. Med DPA: DPF (GitHub aktiv 2026-11-17) och/eller SCC |
| 6 | TypeSafe AI, Inc. (api.typesafe.ai), modellen Jev | Klassning av prospekt under leadsresearch | Prospektets publika bolagsuppgifter (namn, ort, webbplats, antal anställda), Kundens målgruppskriterier och erbjudande, och utdrag ur bolagets egen sida respektive researchsammanfattningen med e-postadresser, telefonnummer och personnummer bortfiltrerade. Personnamn och roller filtreras inte bort, så kontaktpersoners namn kan följa med i utdraget, och en enskild firmas namn kan vara en persons namn. Kundens kundmejl går inte hit sedan 2026-11-17: ägaren beslutade det och inkorgsklassningen är avstängd i både produktion och testmiljö. Kundmejltext som skickades före dess ligger kvar hos TypeSafe | USA. Lagring och behandling hos AWS (USA); Modal, Nebius och CoreWeave (USA) behandlar utan att lagra; Azure, Google Cloud och Cloudflare anges som "Worldwide". Lagringstiden är obestämd | DPA (version 24 april 2026) inkorporerad i Master Customer Agreement, som godkänns genom klick eller användning. Ej belagt vilka villkor kontot accepterade. MCA §4.1(c) och §4.3 ger TypeSafe en tidsobegränsad rätt att använda telemetri härledd ur kunddata. Radering vid avtalets slut regleras inte | SCC modul 2 (och 3) med UK-tillägg enligt DPA:n. TypeSafe finns inte i DPF-listan. Ingen publicerad TIA |
| 7 | ScrapeGraphAI, Inc. | Hämtning och skärmbilder av publika webbsidor under leadsresearch | Prospekts publika sidor (kontakt och om oss: namn, titlar, arbetsmejl) och skärmbilder | USA, enligt leverantörens integritetspolicy. Lagringstid och underbiträden är ej belagda | Ingen publicerad DPA; villkoren §8 hänvisar till kontakt. Gratisplanens data får användas för modellträning, betalda planers inte ([FYLL: bekräfta betald plan]) | Ingen angiven. ScrapeGraphAI finns inte i DPF-listan |

**Anmärkning om rad 6 och 7.** Granskningen bedömde TypeSafe som röd för
kundmejl: texten behandlas i USA utan DPF, telemetrivillkoret ger en
tidsobegränsad rätt att använda klassningar för egna syften, och
lagringstiden är obestämd. Ägaren beslutade 2026-11-17 att kundmejl inte ska
gå till TypeSafe, och inkorgsklassningen (`INKORG_JEV`) är avstängd i båda
miljöerna sedan samma dag. Kvar är leadsdelen. TypeSafe står ändå kvar som
underbiträde: Kundens data omfattar enligt Bilaga 1 kontaktpersoner hos
prospekten och uppgifter från bolagens egna webbplatser, och utdragen till
Jev kan bära kontaktpersoners namn och roller. Ägaren ska besluta om
leadsdelen. Ska Jev behållas krävs skriftlig bekräftelse att MCA och DPA
gäller kontot, ett tillägg som undantar personuppgifter från
telemetrilicensen, nollagring och en egen TIA; annars stängs Jev av i
leadsdelen och raden stryks. Radering av den kundmejltext som redan skickats
är inte begärd. ScrapeGraphAI bedöms som gul: uppgifterna är publik
B2B-information med låg känslighet, men avtal saknas. Kräver betald plan och
en begärd DPA. Beslutar ägaren att stänga av en leverantör för kunddata,
stryks raden och avstängningen verifieras i drift.

**Anmärkning om rad 5.** Synken innebär att produktionens personuppgifter
behandlas i en region som GitHub inte anger, var tionde minut, utan att
GitHubs DPA gäller för kontots plan. Granskningen bedömer det som rött så
länge kontot har Free-planen. Rekommendationen är att flytta synken till en
schemalagd tjänst hos Railway i Amsterdam, så att persondata aldrig når
GitHub. Raden kan strykas först när synken inte längre bär persondata.

**Inte underbiträden enligt detta avtal:**
- Kundens egna leverantörer för kanaler och integrationer (punkt 15).
- Offentliga källor som leadsagenten läser (bolagsregister, bolagens
  webbplatser, platsannonser, pressmeddelanden). De tar inte emot Kundens
  data.
- Google AI Studio. Vägen finns kvar i driften som reserv. En spärr är byggd
  men inte driftsatt (listan efter Bilaga 2). Den får inte användas för
  Kundens data.
