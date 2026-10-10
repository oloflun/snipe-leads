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

**1. Ingången: deras typ av arbete och vad som skaver.** Rama in en vanlig utmaning i deras bransch eller i den sortens arbete de gör, sagt om branschen och inte som ett påstående om just dem.
- "För företag som ert inom [bransch] …"
- "När man jobbar med [typ av jobb], som ni gör, blir [konkret moment] lätt det som äter kvällarna."
- "I en verkstad med ett litet team är det ofta [konkret moment] som får vänta."
Har researchen en verklig signal (ny ägare, nyanställning, ny ort, ny tjänst) väver du in den i ingången som deras situation, inte som "jag såg": "Efter ett ägarbyte är det ofta nu man ser över hur [moment] sköts."

**Igenkänningen (valfri).** En kort fråga som låter mottagaren känna igen sig själv, och som nämner det konkreta momentet från ingången: "Blir offerterna liggande hos er också?" "Är det kvällarna som går åt till kvittona?" Frågan ersätter varje påstående om deras problem. En allmän fråga som skulle passa i vilket mejl som helst ("Känner ni igen er?") låter som en mall.

**2. Erbjudandet: vad agenten gör åt dem, vad de vinner och vad de får nu.** Mönster: "Vår [agent] [konkret handling] åt er, så att ni [vinst i deras eget arbete]." Namnge EN agent och EN sak den gör. Är det avsändaren som gör jobbet (en tjänst som städning, redovisning eller en ny webbplats, inte en agent eller ett verktyg) är subjektet "vi": "Vi sköter bokföringen åt er …", aldrig "Vår löpande redovisning tar …". Vinsten är deras tid, deras kunder eller deras hantverk, aldrig "effektivitet". Säg vinsten med ett verb ur deras arbete ("hinner med ett jobb till", "svarar kunden samma dag"), inte med formeln "lägga tiden på X i stället".

**3. Handlingen.** En mening som säger exakt vad de gör för att få erbjudandet, så enkelt att det kostar mindre att svara ja än att låta bli: svara "ja", följ en länk, vidarebefordra något, eller svara så bokar vi. Den hänger ihop med erbjudandet ("Svara 'ja' så skickar jag de fem bolagen i veckan."). Ingen fråga, ingen press, och ingen länk som inte står i villkoren eller affärskontexten.

Är erbjudandet tydligt i stycke 2 (något gratis, en garanti eller en begränsad plats) bär det mejlet. Erbjudandet sägs konkret med villkorens siffror, inte som "ett kort samtal för att se hur det skulle kunna fungera".

## Ordval

| Skriv inte | Skriv hellre |
|---|---|
| Jag ser att ni … / Jag såg att ni … | För företag som ert … / När man jobbar med … |
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

- **Mottagaren eller deras arbete är subjekt** i de två första styckena. "Ni", "man", "kvittona", "kunderna", aldrig "vi" eller "jag".
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

Kort, om deras arbete eller vinsten för dem, med bolagets namn när det får plats. Aldrig produktkategorin och aldrig "Kvittohantering för X".
- "Mer tid till svetsningen, [namn]"
- "Kvällarna efter jobbet, [namn]"
- "Nya kunder till [namn] utan mer säljtid"

## Gränserna du alltid håller (från grundprompten och grindarna)

- Ingången om branschen sägs om branschen ("man", "företag som ert"), aldrig som en gissning om dem. "Ni brukar …", "ni har säkert …", "ni lär …" fälls av gissningsgrinden.
- Inga påhittade siffror, kunder, case eller resultat, inte heller "vi har hjälpt liknande företag".
- Erbjudanden (provperiod, garanti, gratis start) bara om de står i affärskontexten.
- Tilltalet följer grundprompten: namngiven mottagare ger "du", bolagsadress ger "ni". Exemplen ovan är skrivna i "ni"-form.

## Före och efter (verkliga utkast, anonymiserade)

Exemplen visar riktningen. Skriv aldrig av dem (regel 7).

**Före (informerande):**
"Jag såg att ni är specialister på renovering och byggprojekt i Göteborg. Med en anställd kan jag tänka mig att ni hanterar en del administrativt arbete själv, som kvittohantering. Snajp har en AI-agent som går igenom er e-post, hittar kvitton och samlar in de uppgifter som behövs för bokföringen. Skulle ni vilja ta ett kort samtal för att se hur Kvittohanteraren skulle kunna fungera i er verksamhet?"

**Efter:**
"När man driver ett byggföretag med ett litet team blir kvittona i mejlen ett kvällsjobb inför varje bokföring.

Vår Kvittohanterare hämtar dem ur er e-post och lägger dem klara för bokföringen. Prova den på fem av era kvitton, helt utan kostnad.

Vidarebefordra fem kvitton till [adressen i villkoren], så får ni tillbaka dem färdiga samma dag."

**Före (informerande):**
"Jag ser att ni har hjälpt maskinägare och entreprenörer med hjullastare och grävmaskiner sedan 2014. Många företag i er situation upplever att det tar mycket tid att hitta och kvalificera potentiella kunder manuellt. Snajps AI-agent Iris kan hitta och kvalificera potentiella kunder åt er."

**Efter:**
"För ett företag som säljer maskiner till entreprenörer kommer de bästa affärerna ofta från företag man aldrig hunnit kontakta.

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
