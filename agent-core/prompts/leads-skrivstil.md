# Skrivstil för kalla mejl

> **Om filen:** Regelsetet för HUR ett kallt mejl formuleras: struktur, ordval och meningsbyggnad. VAD mejlet får säga styrs av grundprompten (sanning, källor, kontakt) och kodgrindarna, och de går alltid före den här filen. Filen läggs in i varje utkaststeg: skrivningen, granskningen, humanizern och listutkasten (`app/agent/leads_systemprompt.py:skrivstil`). Ny feedback från Anton eller Sebbe läggs till som en ny omgång under "Feedbackrundor", med datum, och reglerna ovanför justeras i samma ändring. Byggd 2026-10-10 efter Antons genomgång av utkasten i development. Gällande nivå och exempel: `docs/UTKASTKEDJAN-REFERENS-2026-10-16.md` (ändra inget här utan att läsa den).

## Kärnan

Mejlet ska läsas som ett erbjudande som är skrivet just för dem och som är för bra att ignorera, inte som information om en produkt. Mottagaren ska efter första meningen tänka "det där stämmer för oss", efter nästa veta exakt vad de får, och sedan se en enkel väg vidare. Det ska låta som ett vardagligt mejl från en person till en annan, inte som ett utskick. Kort slår utförligt: varje mening som inte gör erbjudandet mer attraktivt stryks.

## Kritiska regler

1. **Börja i deras värld, aldrig i din iakttagelse av dem.** Inte "Jag ser att ni …", "Jag såg att ni …" eller "Ni är specialister på …". Börja i den konkreta sak ur deras verksamhet som produkten bygger vidare på.
2. **Säg aldrig "vi har skapat", "vi har utvecklat" eller "X är en AI-agent som …".** Säg vad agenten gör FÖR DEM: "Vår [agent] [gör konkret sak] åt er, så att ni får mer tid till [deras kärnarbete]."
3. **Nyttan landar i deras arbete, inte i en funktion.** "Så att ni kan lägga tiden på svetsningen" slår "som automatiserar insamling och hantering av kvitton".
4. **Mejlet slutar med en vardaglig inbjudan, aldrig med en order och aldrig med en öppen fråga.** Inbjudan bär villkorens handling (en länk att titta på, eller att de svarar så bokar vi en genomgång) och säger den som man säger det till någon man respekterar: vill de veta mer eller testa själva finns vägen där. En avslutning av formen "Svara X så gör vi Y", och varje citerat kodord att svara med ("svara 'pilot'", "svara 'ja'"), är förbjuden (Anton 2026-10-25): den läses som ett massutskick och kan sänka hela mejlet. En fråga som är lätt att tacka nej till ("Har ni 15 minuter nästa vecka?", "Skulle ni vara intresserade?") är också förbjuden som avslutning.
5. **Inga tankstreck (—) i brödtexten.** Använd punkt, komma eller skriv om meningen. Tankstreck i intervall ("15–20 minuter") är okej.
6. **Ingen hälsningsfras och inget namn sist.** Hälsningen och signaturen läggs på i kod.
7. **Exemplen i den här filen visar formen, aldrig orden.** Återanvänd aldrig en mening, en bild ("pappersjakt") eller en uppmaning ordagrant ur exemplen. Två mejl i samma körning får inte ha samma ingång, samma vinst eller samma uppmaning: hämta bilden ur just deras bransch och arbete.
8. **Ingången leder till just den här agenten.** Erbjuder du Iris (nya kunder) säger ingången vilka kunder de säljer till, så att Iris kan ta fram fler sådana; erbjuder du Supportagenten säger den vad deras kunder hör av sig om. Passar ingången inte agenten: byt ingång, inte agent.

## Strukturen

Korta stycken, en mening per steg och högst 80 ord i brödtexten (form B med frågan: 90), i den här ordningen: ingången och produktmeningen i första stycket, erbjudandet (en eller två korta meningar) och avslutet (en mening). Inga andra meningar och ingen fråga, utom frågan i form B. Formen under "Mejlets form" i ärendet gäller. (Antons förslag 1, 2026-11-06: A låg på median 105 ord, och 57 av 105 öppnade med "Att … är en balansgång".)

**1. Ingången: det i deras vardag som produkten tar vid ifrån.** Ingången är en mening om högst 20 ord skriven till dem, med "ni" (eller "du" till en namngiven person) eller deras kunder som subjekt, om det konkreta i deras vardag som produktmeningen tar vid ifrån och som går att anta ur deras verksamhet: för Iris vilka kunder de säljer till eller arbetar åt, så konkret som sajten tillåter (bransch, ort), så att Iris kan ta fram fler sådana; för Supportagenten vad deras kunder (hyresgäster, medlemmar, gäster) hör av sig om, ett eller två konkreta ämnen. Så ser det ut i Antons förslag 1 (påhittade bolag, skriv aldrig av orden):

> Ni lägger de flesta golven åt fastighetsbolag och bostadsrättsföreningar runt Göteborg. Vår agent Iris tar fram fler sådana kunder åt er varje vecka och skriver ett första mejl till varje, som ni godkänner innan det skickas.

> Dina kunder frågar ofta om skötsel och lagning av jeansen långt efter köpet. Vår Supportagent svarar på de frågorna direkt på din webbplats, dygnet runt och utifrån din egen information.

Ingången är aldrig en beskrivning av bolaget. "[Bolaget] erbjuder …", "[Bolaget] arbetar för att …" och "[Bolaget] förvaltar …" återberättar sajten för någon som redan vet vad de gör, och kunde stå överst i vilket mejl som helst (Anton 2026-11-07: "exakt vad vi ville undvika för länge sedan … väldigt opersonligt och mall-aktigt"). En kodgrind fäller bolagets namn i ingångens början. Ingången är heller aldrig en abstrakt utmaning, en balansgång eller en fråga: nyttan bär produktmeningen. Mottagaren ska känna igen sig, aldrig känna sig kritiserad (Anton 2026-10-25): påstå aldrig att de brister, inte hinner eller att något försvinner för dem, och ställ inga krav på dem ("kräver att ni …", "ni behöver …"). Vad deras kunder behöver eller frågar om får ingången säga: det är just det konkreta. Löftet benämns aldrig: skriv aldrig "ert löfte", "något ni står för", "är ert mål" eller "ert kärnuppdrag". Det som bär meningen är konkretionen: deras ord för vilka de arbetar för och vad de gör åt dem. Ingången lovar aldrig en förmåga agenten saknar.

Ingången är aldrig en uppräkning av vad de säljer eller gör. "Med ert breda utbud av fordon, utrustning och service för snöskotrar, motorcyklar och ATV …" och "Med er verksamhet som säljer båtar, motorer och trailers, och med en verkstad …" är sajtens produktlista återberättad, och mottagaren vet redan vad hen säljer. Välj EN sak de lovar, inte allt de har. En detalj ur sortimentet får stå i momentet ("när kundfrågorna om båtar, motorer och trailers blir många"), aldrig som ingångens kärna.

Det som står på deras egen sajt får sägas rakt till dem; det som inte står där får inte gissas ("troligen", "säkert", "brukar" fälls). Aldrig siffror ur registret: antal anställda, platschefer, grundningsår, omsättning eller orten ensam. "Är jag säker på", "kan jag tänka mig" och "vet jag att" är antaganden om dem.

Ingången är heller aldrig en allmän mening med en etikett på, och den börjar aldrig med en slentrianöppning. "För företag som ert …", "När man …, som ni gör", "liksom ni", "den som …", och de öppningar som tog deras plats: "Med er/ert/era …", "När ni …", "Ni som …". Varje sådan mening kunde stå i ett mejl till vilket bolag som helst. En kodgrind fäller dem. Så här skiljer sig de två (verkliga ingångar, oktober 2026):

| Fel | Rätt |
|---|---|
| "För företag som ert, som säljer till andra företag, är det ofta en utmaning att hitta nya kunder." | "Hur hinner du med att ge personlig rådgivning och service genom hela processen, från köp till underhåll, när kundfrågorna om båtar, motorer och trailers blir många?" (Antons bästa utkast, 2026-10-15) |
| "Med ert breda utbud av fordon, utrustning och service för snöskotrar, motorcyklar och ATV uppstår många återkommande kundfrågor." | (rätt ovan och nedan) |
| "Att hjälpa kunder att hitta rätt båt för deras behov är ert löfte, men att svara på återkommande frågor om förmedling och priser tar tid från det arbetet." | (en benämnd "löfte"-mening med en allmän svans: samma mening i fem mejl av elva, 2026-10-15) |
| "När ni säljer snöskotrar, ATV och båtar till både privatpersoner och företag, via butik och webbshop, får ni många frågor." | "Vem hos er svarar på alla kundfrågor om köksdesign och installation, när ni följer kunden genom hela processen från måttagning till färdigt kök?" |

Rätt-kolumnen visar konkretionen som skiljer en riktig ingång från en mall. Två av dem är frågor ur tiden före 2026-11-06; i A sägs samma konkretion som ett konstaterande.

Konstruktionen varierar från mejl till mejl: koden tilldelar varje mejl en form (under "Ingångens form i det här mejlet" i ärendet), och den gäller. Alla former konstaterar något ur deras egna ord; de skiljer sig i vad de konstaterar. Aldrig samma konstruktion som ett annat mejl i körningen: de ingångar som redan använts står i ärendet under "Ingångar som redan används", och en kodgrind jämför. Låna aldrig ord ur exemplen ovan: en kodgrind jämför ordföljderna.

**Ingen igenkänningsfråga.** Sedan 2026-11-06 har A ingen fråga efter ingången: en fråga som mejlet själv svarar på i nästa mening läses som ett säljmanus (47 av 105 A-mejl gjorde så). Frågan finns bara i form B, där formen säger var den står.

**2. Produktmeningen och erbjudandet: vad agenten ger just dem, och vad de får nu.** Produktmeningen tar vid där ingången slutar och säger vad agenten ger just dem, med kundens korta utfall (under "Utfallet produktmeningen bygger på") översatt till deras verksamhet: vilka sorters kunder Iris tar fram åt dem, vilka frågor Supportagenten svarar på. Mönster: "Vår [agent] [konkret handling] åt er …". Namnge EN agent och EN sak den gör, och gör det FÖRST, före löftet, garantin eller piloten: mottagaren ska veta vad som lovas innan siffrorna kommer ("Vi lovar att du lägger 50 % mindre tid …" utan att agenten nämnts är ett löfte om ingenting). Knyt gärna tillbaka till deras löfte ur ingången: "Den lämnar över till en människa när den inte säkert kan svara" håller den personliga servicen kvar. Är det avsändaren som gör jobbet (en tjänst som städning, redovisning eller en ny webbplats, inte en agent eller ett verktyg) är subjektet "vi": "Vi sköter bokföringen åt er …", aldrig "Vår löpande redovisning tar …". Vinsten är deras tid, deras kunder eller deras hantverk, aldrig "effektivitet". Säg vinsten med ett verb ur deras arbete ("hinner med ett jobb till", "svarar kunden samma dag"), inte med formeln "lägga tiden på X i stället".

**3. Avslutet.** En vardaglig mening med villkorens handling, sagd som en inbjudan och inte som en order: vill de veta mer eller testa själva finns länken, eller så svarar de på mejlet och vi bokar en genomgång. Ger villkoren två vägar till samma sak får båda stå i samma mening. Aldrig "Svara X så gör vi Y", inget citerat kodord, ingen fråga, ingen press, och ingen länk som inte står i villkoren eller affärskontexten.

Är erbjudandet tydligt i stycke 2 (något gratis, en garanti eller en begränsad plats) bär det mejlet. Erbjudandet sägs konkret med villkorens siffror, inte som "ett kort samtal för att se hur det skulle kunna fungera". Det överlever varje omskrivning: villkorens siffror och produktens namn står kvar oavsett hur ingången skrivs om, och en kodgrind kontrollerar det.

## Ordval

| Skriv inte | Skriv hellre |
|---|---|
| Jag ser att ni … / Jag såg att ni … / För företag som ert … | en iakttagelse om deras sorts verksamhet, byggd på en egenskap ur deras egna ord (se Ingången) |
| Med [antal] anställda / platschefer / sedan [år] … | vem de arbetar för, vad de lägger vikt vid, hur de arbetar |
| Vi har skapat / utvecklat … | Vår [agent] [gör X] åt er … |
| Snajps X är en AI-agent som automatiserar … | Vår X [plockar upp / svarar på / hittar] … åt er |
| effektivisera, effektivitet, optimera (om arbetet i allmänhet) | mer tid till [deras arbete], slippa [konkret moment]. Undantaget: att agenten effektiviserar prospekteringen eller kundhanteringen får sägas en gång, när kundens instruktion ber om det (Sebbe 2026-10-29) |
| administrativa uppgifter | kvittona, mejlen, offertförfrågningarna (det konkreta) |
| frigöra tid | få mer tid till [konkret] |
| potentiella kunder | nya kunder |
| Skulle ni vara intresserade av att se hur …? | en inbjudan med villkorens väg vidare (länken, eller ett svar så bokar vi) |
| Har ni 15 minuter nästa vecka? | den kostnadsfria genomgången ur villkoren, som ett erbjudande och inte som en fråga |
| Svara "pilot"/"ja" så … | vill ni veta mer eller testa själva: [villkorens länk eller handling] |
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
- **Säker, inte säljig.** Inga superlativ om oss, inga utropstecken, ingen brådska eller knapphet som inte står i villkoren.
- **Vardaglig.** Som ett mejl en person skriver till en annan: enkla ord, ingen kampanjton.
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

**Efter (riktningen, inte orden):**
Ingången säger åt vilka kunder de renoverar enligt sajten. Sedan en mening om att Kvittohanteraren hämtar kvittona från de jobben ur e-posten och lägger dem klara, erbjudandet med villkorens siffror, och sist en vardaglig inbjudan med villkorens väg vidare.

**Före (informerande):**
"Jag ser att ni har hjälpt maskinägare och entreprenörer med hjullastare och grävmaskiner sedan 2014. Många företag i er situation upplever att det tar mycket tid att hitta och kvalificera potentiella kunder manuellt. Snajps AI-agent Iris kan hitta och kvalificera potentiella kunder åt er."

**Efter (riktningen, inte orden):**
Ingången säger att det är entreprenörer och maskinägare de ger service på plats. Sedan en mening om att Iris tar fram fler sådana entreprenörer åt dem, erbjudandet med villkorens siffror, och sist en vardaglig inbjudan med villkorens väg vidare.

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

### Omgång 7 – Anton 2026-10-25

Grundidén i utkasten i produktion var bra, men ingången blev för ofta offensiv: deras eget löfte ställt mot ett misslyckande ("ni lovar …, men frågorna hinner sällan besvaras", "men den tiden försvinner snabbt"). Det kan träffa en öm tå och tas som kritik redan i första meningen. De goda ingångarna beskrev i stället en balansgång i deras sorts arbete, eller något som kan göra det svårt att hinna med det de lägger vikt vid. Varje mejl slutade dessutom med "Svara X så gör vi Y", som läses som botmejl och massutskick och är förbjudet. Avslutet är en vardaglig inbjudan med villkorens väg vidare. Erbjudandet styr hela mejlet, och hos Snajp står piloten i varje mejl. Mejlen A/B-testas: form A rakt på, och form B med en kort fråga om vilket av två moment som tar mest tid för dem. Tonen är vardaglig, som ett mejl från en person till en annan. Sebbes omgång 7 från 2026-10-24 (erbjudandet först i Iris-mejlen, beviset om att Iris skrev mejlet) är återställd.

### Omgång 8 – Sebbe 2026-10-29

Strukturen från omgång 7 står kvar; mejlet till Andreas ("Att identifiera potentiella köpare och bistå i förhandlingar kräver att du kan fokusera på varje affär", sedan frågan om vad som tar mest tid, Iris och piloten) är rätt nivå. Tre saker skavde. Ingången klankade ibland ner på bolaget ("Era kunder förväntar sig snabb och kunnig hjälp …", "När mängden frågor växer tar det tid från …") eller lät säljig och pushande ("Hur ska ni kunna hantera nya kunder samtidigt som ni har mycket jobb"); stilgrinden fäller nu de mönstren som kritik. Mottagaren ska tidigt förstå att agenten gör jobbet enklare: att hitta nya kunder (prospekteringen) för Iris, kundhanteringen för Supportagenten, sagt varmt och kort med en inblick i hur enkelt det är. Att agenten effektiviserar just prospekteringen eller kundhanteringen får därför sägas en gång. Ämnesraderna ("Fokus på varje affär", "Nya kunder med höga krav") sa inget om vinsten; hos en kund med egna ämnesrader per produkt väljs raden i kod ur den listan (`erbjudanden.valj_amne`), annars gäller ämnesregeln ovan. Rabatten i Snajps pilot är "upp till 50 %", och koden sätter tillbaka "upp till" om mejlet tappar det.

### Omgång 11 – Anton 2026-11-06

Struktur B (Sebbe 2026-11-05) var rakare, men A tappade läsaren: median 105 ord, 96 av 105 över formens 90 trots att grinden skrev om långa mejl, 95 av 105 började "Att …", 57 sa "balansgång", 47 ställde frågan om vad som tar mest tid och svarade själva i nästa mening, och alla slutade med två vägar i en lång mening. Antons val av tre förslag: A behåller sin ordning (dem, agenten, erbjudandet, inbjudan) men med en mening per steg och högst 80 ord (förslagets exempel hade 76). Ingången konstaterar en konkret sak om dem som produktmeningen tar vid ifrån, produktmeningen bär kundens korta utfall översatt till dem, piloten står i en eller två korta meningar och inbjudan i en. Ingen fråga i form A, och erbjudandets form B (frågan) är avslagen hos Snajp: A/B-testet är nu struktur A mot struktur B. Anpassningen ligger kvar där den låg: researchen väljer produkten för varje bolag, och ingången och produktmeningen skrivs ur just deras sajt.

### Omgång 12 – Anton 2026-11-07

Provet av förslag 1 gav ingångar som var bolagets verksamhetsbeskrivning i sex av nio ("[Webbutiken] erbjuder naturlig fotvård online med produkter utvalda av en fotterapeut", "[Plattformen] arbetar för att företag ska hantera …", "[Byggfirman] välkomnar frågor om nya projekt"): "exakt vad vi ville undvika för länge sedan", opersonligt och mallaktigt, och strukturen från förslagets exempel var borta. Förbuden mot krav, smicker, utmaningar och balansgång lämnade bara beskrivningen kvar. Ingången säger nu det konkreta i deras vardag som produkten tar vid ifrån och som går att anta ur verksamheten, skrivet till dem: vilka kunder de har (Iris tar fram fler sådana) eller vad deras kunder hör av sig om (Supportagenten svarar på de frågorna), som i förslagets två exempel. Bolagets namn i ingångens början fälls i kod, och bara krav riktade till dem fälls: vad deras kunder behöver får ingången säga.

### Omgång 6 – Anton 2026-10-15

Efter omgång 5 försvann "för företag som ert" och "som ni gör", men "Med er/ert/era …", "När ni …" och "Ni som …" tog deras plats i mejl efter mejl, och ingången blev en uppräkning av bolagets sortiment ("Med ert breda utbud av fordon, utrustning och service för snöskotrar, motorcyklar och ATV …"). Ämnesraderna bar bolagets namn och lät som mallar eller reklam ("Åkes Motor och era kundfrågor", "Pilot för Iris, Törnqvist Etc.", "Båtladan i Gästrikland och livet på sjön"), och ett mejl hälsade "Hej Delsbo," på en ort. Det bästa utkastet var Båtladan: "Hur hinner du med att ge personlig rådgivning och service genom hela processen, från köp till underhåll, när kundfrågorna om båtar, motorer och trailers blir många?" Det tar det bolaget lovar sina kunder och ställer det mot momentet agenten löser, i du-form till en namngiven person, och erbjudandet knyter tillbaka ("lämnar över till en människa när den inte säkert kan svara"). Det är nivån, i varje mejl. Därför: ingången bygger på deras löfte, aldrig på en uppräkning; slentrianöppningarna, uppräkningen, ord lånade ur exemplen, du och ni om samma person och bolagsnamn eller produkt i ämnesraden fälls av stilgrinden; ämnesraden är två till fem ord utan namn; agenten namnges före löftet; och förnamnet i hälsningen väljs mot mejladressen. Omkörningen samma dag visade nästa mall: "… är ert löfte, men att svara på återkommande kundfrågor tar tid från det arbetet" i fem av elva, och formernas exempel kopierade ordagrant. Därför benämns löftet aldrig, svansen "tar tid från det arbetet"/"kärnverksamhet" fälls, formerna bär inga exempelfraser, och två ingångar i samma körning får inte dela en fras om fyra ord.
