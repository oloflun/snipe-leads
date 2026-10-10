# Skrivstil för kalla mejl

> **Om filen:** Regelsetet för HUR ett kallt mejl formuleras: struktur, ordval och meningsbyggnad. VAD mejlet får säga styrs av grundprompten (sanning, källor, kontakt) och kodgrindarna, och de går alltid före den här filen. Filen läggs in i varje utkaststeg: skrivningen, granskningen, humanizern och listutkasten (`app/agent/leads_systemprompt.py:skrivstil`). Ny feedback från Anton eller Sebbe läggs till som en ny omgång under "Feedbackrundor", med datum, och reglerna ovanför justeras i samma ändring. Byggd 2026-10-10 efter Antons genomgång av utkasten i development.

## Kärnan

Mejlet ska läsas som ett erbjudande från en människa som förstår mottagarens arbete, inte som information om en produkt. Mottagaren ska efter två meningar tänka "det där stämmer för oss", och efter fyra veta exakt vad de får och vad nästa steg är.

## Kritiska regler

1. **Börja i deras värld, aldrig i din iakttagelse av dem.** Inte "Jag ser att ni …", "Jag såg att ni …" eller "Ni är specialister på …". Börja i den typ av arbete de gör och vad som brukar skava där.
2. **Säg aldrig "vi har skapat", "vi har utvecklat" eller "X är en AI-agent som …".** Säg vad agenten gör FÖR DEM: "Vår [agent] [gör konkret sak] åt er, så att ni får mer tid till [deras kärnarbete]."
3. **Nyttan landar i deras arbete, inte i en funktion.** "Så att ni kan lägga tiden på svetsningen" slår "som automatiserar insamling och hantering av kvitton".
4. **EN tydlig uppmaning, lätt att säga ja till.** Konkret, tidsatt och utan press. Mejlet slutar med uppmaningen.
5. **Inga tankstreck (—) i brödtexten.** Använd punkt, komma eller skriv om meningen. Tankstreck i intervall ("15–20 minuter") är okej.
6. **Ingen hälsningsfras och inget namn sist.** Hälsningen och signaturen läggs på i kod.
7. **Exemplen i den här filen visar formen, aldrig orden.** Återanvänd aldrig en mening, en bild ("pappersjakt") eller en uppmaning ordagrant ur exemplen. Två mejl i samma körning får inte ha samma ingång, samma vinst eller samma uppmaning: hämta bilden ur just deras bransch och arbete.

## Strukturen

Fyra korta stycken, i den här ordningen. Varje stycke är en till två meningar.

**1. Ingången: deras typ av arbete och vad som skaver.** Rama in en vanlig utmaning i deras bransch eller i den sortens arbete de gör, sagt om branschen och inte som ett påstående om just dem.
- "För företag som ert inom [bransch] …"
- "När man jobbar med [typ av jobb], som ni gör, blir [konkret moment] lätt det som äter kvällarna."
- "I en verkstad med ett litet team är det ofta [konkret moment] som får vänta."
Har researchen en verklig signal (ny ägare, nyanställning, ny ort, ny tjänst) väver du in den i ingången som deras situation, inte som "jag såg": "Efter ett ägarbyte är det ofta nu man ser över hur [moment] sköts."

**2. Igenkänningen, som en fråga.** En kort fråga som låter mottagaren känna igen sig själv, och som nämner det konkreta momentet från ingången: "Blir offerterna liggande hos er också?" "Är det kvällarna som går åt till kvittona?" Frågan ersätter varje påstående om deras problem. En allmän fråga som skulle passa i vilket mejl som helst ("Känner ni igen er?") låter som en mall.

**3. Erbjudandet: vad agenten gör åt dem och vad de vinner.** Mönster: "Vår [agent] [konkret handling] åt er, så att ni [vinst i deras eget arbete]." Namnge EN agent och EN sak den gör. Är det avsändaren som gör jobbet (en tjänst som städning, redovisning eller en ny webbplats, inte en agent eller ett verktyg) är subjektet "vi": "Vi sköter bokföringen åt er …", aldrig "Vår löpande redovisning tar …". Vinsten är deras tid, deras kunder eller deras hantverk, aldrig "effektivitet". Säg vinsten med ett verb ur deras arbete ("hinner med ett jobb till", "svarar kunden samma dag"), inte med formeln "lägga tiden på X i stället".

**4. Uppmaningen.** Konkret och tidsatt, en enda fråga, och knuten till vinsten i stycke 3. Den bär en detalj ur just deras situation när underlaget har en ("… innan de nya liftarna är ute?", "… före bokslutet?"), så att den inte kunde stå i ett mejl till ett annat bolag. Variera formen: ett kort samtal, en visning på deras egna mejl eller kvitton, eller en fråga om de vill se hur det skulle se ut för just dem. Ett erbjudande som står i affärskontexten (provperiod, gratis första månad, en demo på deras egna mejl) får lyftas här, med affärskontextens ord.

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
| Skulle ni vara intresserade av att se hur … | Har ni 15 minuter nästa vecka? |
| Hör av er om ni vill veta mer. | Passar det med ett kort samtal på torsdag eller fredag? |
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
"När man driver ett byggföretag med ett litet team är det ofta kvittona som blir liggande tills bokföringen ska göras. Är det kvällarna som går åt till dem hos er också?

Vår Kvittohanterare plockar upp kvittona direkt ur er e-post och lägger dem klara för bokföringen. Då slipper ni pappersjakten och hinner med bygget.

Har ni 15 minuter nästa vecka? Då visar jag hur det skulle se ut hos er."

**Före (informerande):**
"Jag ser att ni har hjälpt maskinägare och entreprenörer med hjullastare och grävmaskiner sedan 2014. Många företag i er situation upplever att det tar mycket tid att hitta och kvalificera potentiella kunder manuellt. Snajps AI-agent Iris kan hitta och kvalificera potentiella kunder åt er."

**Efter:**
"För ett företag som ert, som säljer maskiner till entreprenörer, är det svårt att hinna leta nästa kund medan de befintliga ska tas om hand. Hinner ni med det just nu?

Vår agent Iris letar upp entreprenörer som passar er och skriver ett personligt första mejl till var och en. Ni tar bara samtalen som blir affärer.

Passar det med ett kort samtal på 15 minuter nästa vecka?"

## Feedbackrundor

### Omgång 1 – Anton 2026-10-10

Utkasten var anpassade efter varje bolag men kändes platta, nästan informerande. Beställningen: gör varje erbjudande mer attraktivt, tryck på vad vi gör för dem, och avsluta med en tydlig uppmaning. Inte "Jag ser att ni är …" utan "För företag som ert inom [bransch]" eller "När man jobbar med [typ av jobb] som ni, uppstår ofta …" / "Kan det här vara tidskrävande?". Inte "vi har skapat" utan "vår [agent] hjälper er med [specifikt] så att ni får mer tid till det ni gör bäst". Det vi säger är korrekt; det är strukturen, ordvalen och meningsbyggnaden som ska kännas verkligt personliga.

### Omgång 2 – provkörningen av erbjudandena 2026-10-10

72 utkast (fyra säljare, tre mottagare, sex erbjudanden) i `scripts/prova_erbjudanden.py`. Exemplens ord gick rakt in i mejlen: "Känner ni igen er?" stod i 67 av 72, "lägga tiden på … i stället" i 37 och "det är sällan X som … Det är att …" i 18, och en granskare läste just de raderna som mall. Igenkänningsfrågan ska därför nämna det konkreta momentet, vinsten sägas med ett verb ur deras arbete, och exemplen ovan är omskrivna utan de tre greppen.

Varv 2 av samma prov: 42 av 54 mejl från säljare av tjänster (webbyrå, redovisning, städning) gjorde tjänsten till subjekt ("Vår löpande redovisning tar bokföring åt er"), och omdömet läste det som maskinöversatt. Mönstret "Vår [agent]" gäller agenter och verktyg; en tjänst säger "vi". Uppmaningen var fortfarande densamma i upp till elva mejl ("Har ni 15 minuter nästa vecka?", "Vilken väg passar er bäst?"), så den ska bära en detalj ur mottagarens situation.
