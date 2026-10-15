# Skrivstil för kalla mejl

> **Om filen:** Regelsetet för HUR ett kallt mejl formuleras: struktur, ordval och meningsbyggnad. VAD mejlet får säga styrs av grundprompten (sanning, källor, kontakt) och kodgrindarna, och de går alltid före den här filen. Filen läggs in i varje utkaststeg: skrivningen, granskningen, humanizern och listutkasten (`app/agent/leads_systemprompt.py:skrivstil`). Ny feedback från Anton eller Sebbe läggs till som en ny omgång under "Feedbackrundor", med datum, och reglerna ovanför justeras i samma ändring. Byggd 2026-10-10 efter Antons genomgång av utkasten i development.

## Kärnan

Mejlet ska läsas som ett erbjudande som är skrivet just för dem och som är för bra att ignorera, inte som information om en produkt. Mottagaren ska efter första meningen tänka "det där stämmer för oss", efter nästa veta exakt vad de får, och sedan kunna säga ja med ett enda svar eller ett klick. Kort slår utförligt: varje mening som inte gör erbjudandet mer attraktivt stryks.

## Kritiska regler

1. **Börja i deras värld, aldrig i din iakttagelse av dem.** Inte "Jag ser att ni …", "Jag såg att ni …" eller "Ni är specialister på …". Börja i den typ av arbete de gör och vad som brukar skava där.
2. **Säg aldrig "vi har skapat", "vi har utvecklat" eller "X är en AI-agent som …".** Säg vad agenten gör FÖR DEM: "Vår [agent] [gör konkret sak] åt er, så att ni får mer tid till [deras kärnarbete]."
3. **Nyttan landar i deras arbete, inte i en funktion.** "Så att ni kan lägga tiden på svetsningen" slår "som automatiserar insamling och hantering av kvitton".
4. **Mejlet slutar med EN enkel handling, aldrig en öppen fråga.** Mottagaren ska kunna säga ja med ett ord eller ett klick: "Svara 'ja' så skickar jag dem.", "Följ länken och testa utan kostnad: [länk]", "Svara på mejlet så bokar vi en tid." En fråga som är lätt att tacka nej till ("Har ni 15 minuter nästa vecka?", "Skulle ni vara intresserade?", "Vilken väg passar er bäst?") är förbjuden som avslutning.
5. **Inga tankstreck (—) i brödtexten.** Använd punkt, komma eller skriv om meningen. Tankstreck i intervall ("15–20 minuter") är okej.
6. **Ingen hälsningsfras och inget namn sist.** Hälsningen och signaturen läggs på i kod.
7. **Exemplen i den här filen visar formen, aldrig orden.** Återanvänd aldrig en mening, en bild ("pappersjakt") eller en uppmaning ordagrant ur exemplen. Två mejl i samma körning får inte ha samma ingång, samma vinst eller samma uppmaning: hämta bilden ur just deras bransch och arbete.
8. **Problemet i ingången är det som just den här agenten löser.** Erbjuder du Iris (nya kunder) handlar ingången om att hinna hitta nästa kund, inte om förfrågningar som blir liggande; det är Supportagentens problem. Passar ingången inte agenten: byt ingång, inte agent.

## Strukturen

Tre korta stycken och 50–90 ord i brödtexten, i den här ordningen: ingången (en mening, högst två), erbjudandet (två till tre meningar) och handlingen (en mening). Igenkänningsfrågan nedan är valfri och står i så fall direkt efter ingången, aldrig sist.

**1. Ingången: deras löfte, och det som hotar det.** Ingången är en mening i andra person ("ni", "er", "era", eller "du" och "din" till en namngiven person) som tar det bolaget självt säger att de står för, och ställer det mot det arbetsmoment agenten löser. Deras löfte är det de lovar sina kunder eller lägger vikt vid, med deras egna ord ur citaten: personlig rådgivning genom hela köpet, att följa kunden från måttagning till färdigt kök, att göra projekten smärtfria, att eleverna blir trygga förare, att beställningar går iväg samma dag. Momentet är det som får det löftet att knaka: kundfrågorna som blir många, nästa uppdrag som ska hittas, kvittona som ska in i bokföringen. Mottagaren ska läsa sitt eget löfte och känna igen problemet i samma mening. Löftet visas med deras ord, det benämns aldrig: skriv aldrig "ert löfte", "något ni står för", "är ert mål" eller "ert kärnuppdrag", och aldrig den allmänna svansen "tar tid från det arbetet" eller "tar tid från er kärnverksamhet". Det som bär meningen är konkretionen: exakt vad de lovar (deras ord) och exakt vad kunderna frågar om eller vad som ska hittas (ur sajten).

Ingången är aldrig en uppräkning av vad de säljer eller gör. "Med ert breda utbud av fordon, utrustning och service för snöskotrar, motorcyklar och ATV …" och "Med er verksamhet som säljer båtar, motorer och trailers, och med en verkstad …" är sajtens produktlista återberättad, och mottagaren vet redan vad hen säljer. Välj EN sak de lovar, inte allt de har. En detalj ur sortimentet får stå i momentet ("när kundfrågorna om båtar, motorer och trailers blir många"), aldrig som ingångens kärna.

Det som står på deras egen sajt får sägas rakt till dem; det som inte står där får inte gissas ("troligen", "säkert", "brukar" fälls). Aldrig siffror ur registret: antal anställda, platschefer, grundningsår, omsättning eller orten ensam. "Är jag säker på", "kan jag tänka mig" och "vet jag att" är antaganden om dem.

Ingången är heller aldrig en allmän mening med en etikett på, och den börjar aldrig med en slentrianöppning. "För företag som ert …", "När man …, som ni gör", "liksom ni", "den som …", och de öppningar som tog deras plats: "Med er/ert/era …", "När ni …", "Ni som …". Varje sådan mening kunde stå i ett mejl till vilket bolag som helst. En kodgrind fäller dem. Så här skiljer sig de två (verkliga ingångar, oktober 2026):

| Fel | Rätt |
|---|---|
| "För företag som ert, som säljer till andra företag, är det ofta en utmaning att hitta nya kunder." | "Hur hinner du med att ge personlig rådgivning och service genom hela processen, från köp till underhåll, när kundfrågorna om båtar, motorer och trailers blir många?" (Antons bästa utkast, 2026-10-15) |
| "Med ert breda utbud av fordon, utrustning och service för snöskotrar, motorcyklar och ATV uppstår många återkommande kundfrågor." | (rätt ovan och nedan) |
| "Att hjälpa kunder att hitta rätt båt för deras behov är ert löfte, men att svara på återkommande frågor om förmedling och priser tar tid från det arbetet." | (en benämnd "löfte"-mening med en allmän svans: samma mening i fem mejl av elva, 2026-10-15) |
| "När ni säljer snöskotrar, ATV och båtar till både privatpersoner och företag, via butik och webbshop, får ni många frågor." | "Vem hos er svarar på alla kundfrågor om köksdesign och installation, när ni följer kunden genom hela processen från måttagning till färdigt kök?" |

Konstruktionen varierar från mejl till mejl: koden tilldelar varje mejl en form (under "Ingångens form i det här mejlet" i ärendet), och den gäller. Alla former bygger på deras löfte; de skiljer sig i hur meningen är byggd. Aldrig samma konstruktion som ett annat mejl i körningen: de ingångar som redan använts står i ärendet under "Ingångar som redan används", och en kodgrind jämför. Låna aldrig ord ur exemplen ovan: en kodgrind jämför ordföljderna.

**Igenkänningen (valfri).** En kort fråga som låter mottagaren känna igen sig själv, och som nämner det konkreta momentet från ingången: "Blir offerterna liggande hos er också?" "Är det kvällarna som går åt till kvittona?" Frågan ersätter varje påstående om deras problem. En allmän fråga som skulle passa i vilket mejl som helst ("Känner ni igen er?") låter som en mall.

**2. Erbjudandet: vad agenten gör åt dem, vad de vinner och vad de får nu.** Mönster: "Vår [agent] [konkret handling] åt er, så att ni [vinst i deras eget arbete]." Namnge EN agent och EN sak den gör, och gör det FÖRST i stycket, före löftet, garantin eller piloten: mottagaren ska veta vad som lovas innan siffrorna kommer ("Vi lovar att du lägger 50 % mindre tid …" utan att agenten nämnts är ett löfte om ingenting). Knyt gärna tillbaka till deras löfte ur ingången: "Den lämnar över till en människa när den inte säkert kan svara" håller den personliga servicen kvar. Är det avsändaren som gör jobbet (en tjänst som städning, redovisning eller en ny webbplats, inte en agent eller ett verktyg) är subjektet "vi": "Vi sköter bokföringen åt er …", aldrig "Vår löpande redovisning tar …". Vinsten är deras tid, deras kunder eller deras hantverk, aldrig "effektivitet". Säg vinsten med ett verb ur deras arbete ("hinner med ett jobb till", "svarar kunden samma dag"), inte med formeln "lägga tiden på X i stället".

**3. Handlingen.** En mening som säger exakt vad de gör för att få erbjudandet, så enkelt att det kostar mindre att svara ja än att låta bli: svara "ja", följ en länk, vidarebefordra något, eller svara så bokar vi. Den hänger ihop med erbjudandet ("Svara 'ja' så skickar jag de fem bolagen i veckan."). Ingen fråga, ingen press, och ingen länk som inte står i villkoren eller affärskontexten.

Är erbjudandet tydligt i stycke 2 (något gratis, en garanti eller en begränsad plats) bär det mejlet. Erbjudandet sägs konkret med villkorens siffror, inte som "ett kort samtal för att se hur det skulle kunna fungera". Det överlever varje omskrivning: villkorens siffror och produktens namn står kvar oavsett hur ingången skrivs om, och en kodgrind kontrollerar det.

## Ordval

| Skriv inte | Skriv hellre |
|---|---|
| Jag ser att ni … / Jag såg att ni … / För företag som ert … | en iakttagelse om deras sorts verksamhet, byggd på en egenskap ur deras egna ord (se Ingången) |
| Med [antal] anställda / platschefer / sedan [år] … | vem de arbetar för, vad de lägger vikt vid, hur de arbetar |
| Vi har skapat / utvecklat … | Vår [agent] [gör X] åt er … |
| Snajps X är en AI-agent som automatiserar … | Vår X [plockar upp / svarar på / hittar] … åt er |
| effektivisera, effektivitet, optimera | mer tid till [deras arbete], slippa [konkret moment] |
| administrativa uppgifter | kvittona, mejlen, offertförfrågningarna (det konkreta) |
| frigöra tid | få mer tid till [konkret] |
| potentiella kunder | nya kunder |
| Skulle ni vara intresserade av att se hur …? | Svara "ja" så skickar jag … |
| Har ni 15 minuter nästa vecka? | Svara på mejlet så bokar vi en tid. |
| Hör av er om ni vill veta mer. | Följ länken och testa utan kostnad: … |
| lösning, plattform, verktyg | agenten, den, [agentens namn] |
| Många småföretagare upplever att … | För ett litet [bransch]bolag är det ofta … |

"Det ni gör bäst" och "det ni är bäst på" är tillåtna, men en konkret sak är alltid starkare: "mer tid till svetsningen" slår "mer tid till det ni gör bäst".

## Meningsbyggnad

- **Mottagaren eller deras arbete är subjekt** i de två första styckena. "Ni", "era kunder", "kvittona", aldrig "vi" eller "jag", och aldrig "man": "man" gör meningen till en sanning om vem som helst.
- **Aktiva verb.** "Agenten svarar på kundmejlen", inte "kundmejlen besvaras automatiskt".
- **Korta meningar, men inte avhuggna.** Högst cirka 20 ord per mening. Hellre två meningar än en med "vilket" och "som" i rad.
- **Variera meningsstarterna.** Aldrig två meningar i rad som börjar med samma ord.
- **Konkreta substantiv.** Kvitton, offerter, samtal efter arbetsdagen, en hjullastare som står. Inga abstrakta ("hantering", "processer", "utmaningar") när ett konkret ord finns.
- **Inga kolon-uppräkningar i löptext, inga "X är det som gör Y"-konstruktioner.**

## Ton

- **Varm och direkt.** Som en kunnig person som pratar med en företagare den respekterar, inte som en broschyr.
- **Säker, inte säljig.** Inga superlativ om oss, inga utropstecken, ingen påhittad brådska eller knapphet.
- **Personlig genom igenkänning, inte genom smicker.** Personligt är att träffa rätt i hur deras arbete ser ut. Att berömma dem ("imponerande", "ett starkt engagemang") är inte personligt.

## Ämnesraden

Två till fem ord som ser ut att komma från en kollega, inte från en säljare: deras löfte eller momentet ur ingången, med små bokstäver efter första ordet. **Aldrig bolagets namn** (Anton 2026-10-15: "nämn INTE företagens namn i ämnesraden"), aldrig vår produkt eller agent, aldrig "Pilot", "Erbjudande" eller produktkategorin, och aldrig samma början som ett annat mejl i körningen. "Kundfrågor för …", "… och era kundfrågor" och "… och livet på sjön" är fel: det första är en mall i varje mejl, det sista ett reklamslagord. Formen:
- "personlig service i högsäsong"
- "frågorna efter köpet"
- "kvittona efter arbetsdagen"
En kodgrind fäller bolagsnamnet, produkten och samma början.

## Gränserna du alltid håller (från grundprompten och grindarna)

- Ingången skrivs till dem i andra person ur det som står på deras egen sajt. Det som inte står där gissas inte: "ni brukar …", "ni har säkert …", "ni lär …" fälls av gissningsgrinden. En allmän mening om branschen ("man", "den som", "företag som ert", "som ni gör") fälls av stilgrinden.
- Inga påhittade siffror, kunder, case eller resultat, inte heller "vi har hjälpt liknande företag".
- Erbjudanden (provperiod, garanti, gratis start) bara om de står i affärskontexten.
- Tilltalet följer grundprompten: namngiven mottagare ger "du", bolagsadress ger "ni", rakt igenom mejlet. Villkoren är skrivna i "ni"-form; till en namngiven mottagare skrivs de om till "du" ("så håller vi en plats åt dig", "tills du gör det"). Ett mejl som säger både "du" och "ni" till samma person fälls av kodgrinden, även "ert"/"era" till en namngiven mottagare ("ditt", "dina").

## Före och efter (verkliga utkast, anonymiserade)

Exemplen visar riktningen. Skriv aldrig av dem (regel 7).

**Före (informerande):**
"Jag såg att ni är specialister på renovering och byggprojekt i Göteborg. Med en anställd kan jag tänka mig att ni hanterar en del administrativt arbete själv, som kvittohantering. Snajp har en AI-agent som går igenom er e-post, hittar kvitton och samlar in de uppgifter som behövs för bokföringen. Skulle ni vilja ta ett kort samtal för att se hur Kvittohanteraren skulle kunna fungera i er verksamhet?"

**Efter:**
"Ert löfte om renoveringar som håller tidplanen hänger på att ni står på bygget, inte vid skrivbordet med kvittona inför bokföringen.

Vår Kvittohanterare hämtar dem ur er e-post och lägger dem klara för bokföringen. Prova den på fem av era kvitton, helt utan kostnad.

Vidarebefordra fem kvitton till [adressen i villkoren], så får ni tillbaka dem färdiga samma dag."

**Före (informerande):**
"Jag ser att ni har hjälpt maskinägare och entreprenörer med hjullastare och grävmaskiner sedan 2014. Många företag i er situation upplever att det tar mycket tid att hitta och kvalificera potentiella kunder manuellt. Snajps AI-agent Iris kan hitta och kvalificera potentiella kunder åt er."

**Efter:**
"Ni lovar entreprenörerna service på plats inom ett dygn, och de dagarna går sällan att lägga på att leta upp nästa entreprenör att sälja till.

Vår agent Iris hittar dem åt er. Ni får fem entreprenörer som passar er, med kontaktperson och ett färdigt första mejl till var och en, utan kostnad.

Svara 'ja' så skickar jag dem i veckan."

## Feedbackrundor

### Omgång 1 – Anton 2026-10-10

Utkasten var anpassade efter varje bolag men kändes platta, nästan informerande. Beställningen: gör varje erbjudande mer attraktivt, tryck på vad vi gör för dem, och avsluta med en tydlig uppmaning. Inte "Jag ser att ni är …" utan "För företag som ert inom [bransch]" eller "När man jobbar med [typ av jobb] som ni, uppstår ofta …" / "Kan det här vara tidskrävande?". Inte "vi har skapat" utan "vår [agent] hjälper er med [specifikt] så att ni får mer tid till det ni gör bäst". Det vi säger är korrekt; det är strukturen, ordvalen och meningsbyggnaden som ska kännas verkligt personliga.

### Omgång 2 – provkörningen av erbjudandena 2026-10-10

72 utkast (fyra säljare, tre mottagare, sex erbjudanden) i `scripts/prova_erbjudanden.py`. Exemplens ord gick rakt in i mejlen: "Känner ni igen er?" stod i 67 av 72, "lägga tiden på … i stället" i 37 och "det är sällan X som … Det är att …" i 18, och en granskare läste just de raderna som mall. Igenkänningsfrågan ska därför nämna det konkreta momentet, vinsten sägas med ett verb ur deras arbete, och exemplen ovan är omskrivna utan de tre greppen.

Varv 2 av samma prov: 42 av 54 mejl från säljare av tjänster (webbyrå, redovisning, städning) gjorde tjänsten till subjekt ("Vår löpande redovisning tar bokföring åt er"), och omdömet läste det som maskinöversatt. Mönstret "Vår [agent]" gäller agenter och verktyg; en tjänst säger "vi". Uppmaningen var fortfarande densamma i upp till elva mejl ("Har ni 15 minuter nästa vecka?", "Vilken väg passar er bäst?"), så den ska bära en detalj ur mottagarens situation.

### Omgång 3 – Anton 2026-10-10

Exemplen var fortfarande för utdragna och informativa, utan ett tillräckligt erbjudande. Grundkänslan i varje mejl, oavsett erbjudande: attraktivt, perfekt just för dem, det löser deras problem och är för bra att ignorera. Mejlen ska vara kortare (tre stycken, 50–90 ord) och erbjudandet tydligt och konkret. De slutade alla med en öppen fråga som är lätt att tacka nej till; nu slutar de med en enkel handling med litet motstånd: följ länken och testa utan kostnad, svara 'ja' så skickar vi, eller svara så bokar vi ett möte. Kärnerbjudandena är tre: något gratis att testa (fem kvalificerade leads, fem färdiga kvitton, en demolänk för supporten), en garanti med konkreta siffror och förlängd provperiod om de inte nås, och en begränsad pilot med rabatt. Exempel: https://claude.ai/artifact/AvqAtFiVf7h3Rupe5E6Ryz.

### Omgång 4 – Anton 2026-10-12

Två utkastkedjor i development (Fiskebäck Byggservice, Härlanda Fog & Byggservice) följdes steg för steg. Första utkastet rabblade registerfakta som ingång ("Med fem platschefer och en etablerad verksamhet … är jag säker på att") eller öppnade som en mall ("För företag som ert, som säljer till andra företag, är det ofta en utmaning att hitta nya kunder"): samma konstruktion i mejl efter mejl, opersonligt och spammigt. Personalisera gjorde mejlet mer personligt men mindre säljande och tappade erbjudandet (ingen "fem leads utan kostnad", bara "skulle ni vilja se ett par exempel?"). Förbättra blev kortare och rakare med kärnerbjudandet kvar, men opersonligt. Först en andra Personalisera landade: det starka erbjudandet kvar, och en ingång som bygger på en förståelse av verksamheten ("med fokus på nära relationer med beställare och fastighetsägare", "med både privatpersoner och företag som kunder") utan att räkna upp självklara fakta som antal anställda. Det som skiljer de goda ingångarna från de dåliga är att de är byggda på en egenskap ur bolagets egna ord, och att de inte är byggda likadant. Beställningen: det första utkastet ska landa där för varje lead. Därför är ingångens mallfraser borta ur filen och grundmallen, ingången bygger på en egenskap ur citaten, konstruktionen varierar (de redan använda ingångarna i körningen står i ärendet), och en stilgrind i kod (`app/leads/stilkontroll.py`) fäller mallingång, siffror i ingången, antaganden om mottagaren, ett tappat erbjudande och samma konstruktion som ett annat mejl, med en omskrivning före humanizern.

### Omgång 5 – Anton 2026-10-12, samma natt

Efter omkörningen stod "som ni gör", "som ert" eller "för företag som ert" fortfarande i nästan varje ingång: grinden fångade bara "För företag som ert" i meningens början, och modellen skrev i stället en allmän "när man …"-mening och hängde på etiketten. Skillnaden mot de goda ingångarna (Witekk, Tingstad, Consenso) är att de är skrivna till mottagaren, i andra person, om det som står på deras sajt. Beställningen: anpassa på riktigt, direkt i kedjan, så som en extra runda Personalisera gjorde i granskningen. Därför: ingången skrivs i andra person ur citaten (avsnittet ovan och tabellen), stilgrinden fäller etiketterna var de än står i ingången och "man"/"den som"/"ett företag som", och kedjan har ett obligatoriskt personaliseringssteg som skriver om enbart ingången före humanizern.

### Omgång 6 – Anton 2026-10-15

Efter omgång 5 försvann "för företag som ert" och "som ni gör", men "Med er/ert/era …", "När ni …" och "Ni som …" tog deras plats i mejl efter mejl, och ingången blev en uppräkning av bolagets sortiment ("Med ert breda utbud av fordon, utrustning och service för snöskotrar, motorcyklar och ATV …"). Ämnesraderna bar bolagets namn och lät som mallar eller reklam ("Åkes Motor och era kundfrågor", "Pilot för Iris, Törnqvist Etc.", "Båtladan i Gästrikland och livet på sjön"), och ett mejl hälsade "Hej Delsbo," på en ort. Det bästa utkastet var Båtladan: "Hur hinner du med att ge personlig rådgivning och service genom hela processen, från köp till underhåll, när kundfrågorna om båtar, motorer och trailers blir många?" Det tar det bolaget lovar sina kunder och ställer det mot momentet agenten löser, i du-form till en namngiven person, och erbjudandet knyter tillbaka ("lämnar över till en människa när den inte säkert kan svara"). Det är nivån, i varje mejl. Därför: ingången bygger på deras löfte, aldrig på en uppräkning; slentrianöppningarna, uppräkningen, ord lånade ur exemplen, du och ni om samma person och bolagsnamn eller produkt i ämnesraden fälls av stilgrinden; ämnesraden är två till fem ord utan namn; agenten namnges före löftet; och förnamnet i hälsningen väljs mot mejladressen. Omkörningen samma dag visade nästa mall: "… är ert löfte, men att svara på återkommande kundfrågor tar tid från det arbetet" i fem av elva, och formernas exempel kopierade ordagrant. Därför benämns löftet aldrig, svansen "tar tid från det arbetet"/"kärnverksamhet" fälls, formerna bär inga exempelfraser, och två ingångar i samma körning får inte dela en fras om fyra ord.
