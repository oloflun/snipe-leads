# paket adminlistan

## Bygge
Felrapporterna ligger nu i den befintliga sektionen Fel & eskaleringar (Kunder > Alla kunder), inte i en ny panel. Raden med nyckeltal har fått ett fjärde tal, "Felrapporter, öppna". Det står i samma stil som de tre som fanns, och raden ändrades från grid-cols-3 till grid-cols-2 sm:grid-cols-4. Under listan med de vanligaste felen finns nu underrubriken "Felrapporter" med filterchips: Öppna (förval), Väntar på oss, Väntar på kunden, Klara och Alla. Raderna använder Radlista/Rad och fälls ut med <details>, samma mönster som Händelselista. Varje rad visar ärendenummer, sida, läge, kundens arbetsyta och tid. En rapport från en besökande admin får en tydlig badge. Utfälld visar raden de tre fälten, bilden (om svaret har en data-URL, annars texten "En bild är bifogad men kan inte visas här."), rapportör, arbetsyta, vy och roll, och länken till testversionen. Hela händelsekedjan visas också, med märket "Kunden ser" eller "Bara Snajp" på varje händelse. Under kedjan finns lägesbytena som chips: Vi undersöker, Rättning på gång, Redo att testa, Fråga kunden, Stäng med förklaring, I development och Ute i Snajp. Det läge ärendet redan står i visas inte. Varje byte har ett meddelandefält. Fråga kunden och Stäng kräver ett meddelande, och Redo att testa kräver en https-adress. Bytet skickas som POST /api/admin/plattformsarenden/{id}/status, och raden ersätts direkt med ärendet i svaret. Listan sorteras med det som väntar på oss först, sedan det som väntar på kunden och sist de klara (i_main och stangd). Inom varje grupp står det senast ändrade först. Listan har ett läge för hämtning, ett tomläge, ett tomläge för filtret och ett felläge med "Försök igen". All text finns på svenska och engelska i lib/admin/sprak.ts. Den rena logiken ligger i lib/admin/plattformsarenden.ts och har ett node-test. Förhandsvisningen ligger på /forhandsvisning/felrapporter och svarar på anropen i webbläsaren. Lägesbyten sparas i webbläsarens localStorage och står kvar efter omladdning. BLOCKERANDE: adminproxyn app/api/admin/[...path]/route.ts tar bara emot GET och säger det uttryckligen i en kommentar. Därför fungerar lägesbytet bara i förhandsvisningen tills någon lägger till en POST-väg för just den här sökvägen. Filen ligger utanför mitt paket, så jag har inte rört den.

### Ändrade filer
- C:\Users\Anton L\snipe-leads\components\admin\FelOchEskaleringar.tsx
- C:\Users\Anton L\snipe-leads\lib\admin\sprak.ts

### Nya filer
- C:\Users\Anton L\snipe-leads\components\admin\Felrapporter.tsx
- C:\Users\Anton L\snipe-leads\lib\admin\plattformsarenden.ts
- C:\Users\Anton L\snipe-leads\lib\admin\plattformsarenden.test.ts
- C:\Users\Anton L\snipe-leads\app\forhandsvisning\felrapporter\page.tsx

### Tester
- `node --test lib/admin/plattformsarenden.test.ts` → ℹ pass 9 / ℹ fail 0 (sista raderna: ℹ todo 0, ℹ duration_ms ...); 9 tester: sortering, filter, vantar_pa_kund, krav per åtgärd, validera (inklusive att http och javascript: avvisas), statuskropp, atgarderFor, ersatt
- `python -m pytest tests/invariants/test_inv_copy_001.py -q -p no:cacheprovider` → 4 passed in 2.00s
- `python -m pytest tests/invariants/test_inv_ui_001.py -q -p no:cacheprovider` → 4 passed in 0.87s
- `node node_modules/typescript/bin/tsc -p <scratchpad>/tsconfig.fr.json (tillfällig tsconfig utanför repot som bara tar med de rörda filerna, strict)` → ingen utskrift, alltså inga typfel
- `npx eslint <rörda filer>` → Kördes inte på riktigt: repot saknar eslint.config.* (ESLint 10 kräver det).

### Ej gjort
- BLOCKERANDE: adminproxyn app/api/admin/[...path]/route.ts tar bara emot GET, med en kommentar om att adminvyn bara läser. Kontraktet säger att adminlistan når backenden genom proxyn, men POST /api/admin/plattformsarenden/{id}/status går inte igenom den i dag och skulle få 405. Det behövs en POST som bara gäller sökvägen plattformsarenden/<id>/status, bakom samma getPlatformAdmin-grind och samma master-nyckel. Alternativet är en server action i lib/actions som komponenten anropar. Filen ligger utanför mitt paket och jag har inte rört den. Kommentaren i proxyn behöver också ändras om POST läggs till där.
- Bilden: kontraktet ger bara har_bild och ingen väg att hämta själva bilden. Komponenten visar bilden om AdminArende-svaret råkar innehålla ett fält bild med en data:image/-URL, annars texten 'En bild är bifogad men kan inte visas här.'. Backendpaketet behöver antingen lägga bild i adminsvaret eller ge en egen väg, till exempel GET /api/admin/plattformsarenden/{id}/bild. Det är en kontraktsfråga till orkestreraren.
- Ingen visuell granskning: uppdraget förbjöd next dev och jag kunde inte rendera ytan på annat sätt. Orkestreraren behöver se förhandsvisningen på desktop och mobil innan något committas.
- Det prioriterade mejlet till Snajp (planens del 5) ingick inte i det här paketet.
- Ingen git add eller commit, och ingen post i docs/BESLUT.md, enligt uppdraget.

### Antaganden
- Den rena logiken ligger i lib/admin/plattformsarenden.ts med testet bredvid, eftersom npm test bara samlar in lib/**/*.test.ts. Det är två nya filer i lib/admin/ utöver sprak.ts.
- Plattformsadmin ser lägena med sina egna ord, inte kundens. Där de skiljer sig: kund_godkand = Kunden godkände, i_development = I development, behover_mer = Väntar på kundens svar, stangd = Stängd. Kundens ord hör hemma i Hjälprutan.
- Kraven: Fråga kunden (behover_mer) och Stäng med förklaring (stangd) kräver ett meddelande, och Redo att testa kräver en https-adress (http och javascript: avvisas). Ett tomt meddelande skickas som null. testversion_url skickas bara med Redo att testa, annars null.
- Sorteringen: öppna ärenden som väntar på Snajp först, sedan behover_mer och redo_att_testa, sist i_main och stangd. Inom varje grupp kommer det senast ändrade (updated_at) först. Filtret körs i klienten över hela listan, så backendens ?status= används inte.
- Antalet öppna (allt utom i_main och stangd) står som fjärde tal i panelens befintliga rad med nyckeltal. Talet blir varningsfärgat när det är större än noll och visar '-' medan listan hämtas.
- Händelsekedjan visas med äldsta händelsen först. En händelse med status visas med lägets namn, annars med fältet typ, och aktor står i metaraden.
- Backendens felmeddelande visas som det kommer (error eller detail). Saknas ett meddelande används den tvåspråkiga reservtexten.

### Syns i gränssnittet
- Förhandsvisningen /forhandsvisning/felrapporter (lokalt http://localhost:3000/forhandsvisning/felrapporter) visar sektionen Fel & eskaleringar med fyra påhittade felrapporter: F-0007 Mottaget med bild, F-0006 Redo att testa från en besökande admin med en intern anteckning, F-0005 Väntar på kundens svar och F-0003 Stängd, som bara syns under filtret Klara eller Alla.
- Raden med nyckeltal har fyra tal i stället för tre: två kolumner på mobil, fyra från sm.
- Att se i bild på desktop och mobil: listan, en utfälld rad (fält, bild, metadata, händelsekedjan med märkena Kunden ser och Bara Snajp) och ett lägesbyte. Välj till exempel 'Fråga kunden' och tryck på knappen utan text: valideringsfelet ska visas. Skriv sedan ett meddelande och skicka: läget och händelsen ska uppdateras direkt och stå kvar efter omladdning.
- ?lage=tomt visar tomläget, ?lage=fel visar felläget med Försök igen, och ?lage=nollstall återställer de påhittade rapporterna.
- Samma sektion i den riktiga adminytan finns på Kunder > Alla kunder (components/admin/KunderOversikt.tsx, längst ner till vänster bredvid Provperioder). Där visar den felläget tills backendens GET /api/admin/plattformsarenden svarar.

## Granskning: godkänd=False
- [blockerande] app/api/admin/[...path]/route.ts:55-63 Adminproxyn exporterar bara GET och säger i en kommentar att adminvyn bara läser. Felrapporter.tsx:357 skickar POST /api/admin/plattformsarenden/{id}/status genom proxyn, och den får 405 utanför förhandsvisningen. Krav 3 i uppgiften (lägesbyten, meddelande till kunden, Redo att testa med adress) fungerar alltså inte i den riktiga adminytan. Byggaren har flaggat det korrekt, och filen ligger utanför paketet. Det är en lucka i kontraktet, inte byggarens fel, men funktionen kan inte släppas förrän den är åtgärdad. FÖRSLAG: Orkestreraren lägger till en POST i proxyn som bara släpper igenom sökvägen ['plattformsarenden', <uuid>, 'status'] (vitlista med regex på uuid). Den ska ligga bakom samma getPlatformAdmin()-grind, använda master-nyckeln och skicka vidare JSON-kroppen. Allt annat ska få 404. Kommentaren om att adminvyn bara läser uppdateras i samma commit. Alternativet är en server action i lib/actions med samma två grindar.
- [bor_rattas] components/admin/Felrapporter.tsx:182, 366 Efter ett byte filtreras listan om, och raden försvinner direkt om det nya läget inte passar det valda filtret. Med förvalet Öppna gäller det Stäng med förklaring och Ute i Snajp, och under Väntar på oss även Fråga kunden och Redo att testa. Uppgiften kräver att det nya läget och händelsen visas direkt efter bytet. Admin ser i stället raden försvinna, utan kvitto. FÖRSLAG: Håll en nyss ändrad rad synlig tills filtret byts eller sidan laddas om, till exempel med en mängd 'senastAndrade' i Felrapporter som passarFilter tar hänsyn till. Ett annat sätt är att visa ett kort statusbesked (role=status) med nummer och nytt läge när raden lämnar filtret.
- [bor_rattas] components/admin/Felrapporter.tsx:270-271, 313, 320 Interna värden visas oöversatta i UI: vy ('kund', 'admin'), roll ('agare', 'medlem', 'plattformsadmin'), händelsens typ när status saknas ('anteckning', 'skapad') och aktor. Det bryter mot regeln att all användarvänd text är tvåspråkig, även om INV-COPY-001 inte fångar det eftersom värdena kommer ur data. FÖRSLAG: Lägg in en uppslagning i sprak.ts för kända värden på vy, roll och händelsetyp (frVy_kund, frRoll_agare, frTyp_anteckning och så vidare), med det råa värdet som reserv, i samma stil som statusetikett().
- [notering] components/admin/Felrapporter.tsx:205-206, 249-261 Komponenten läser ett fält 'bild' som inte finns i kontraktets AdminArende. Kontraktet har bara har_bild och ingen väg för att hämta själva bilden. I drift visas därför alltid texten om att en bild är bifogad men inte kan visas. Byggaren har flaggat det. FÖRSLAG: Orkestreraren avgör kontraktet: antingen ett fält bild (data-URL) i adminsvaret för ett enskilt ärende, eller GET /api/admin/plattformsarenden/{id}/bild genom proxyn. Typen AdminArende uppdateras därefter, så att det typlösa uttrycket på rad 205 försvinner.
- [notering] components/admin/Felrapporter.tsx:283-285 testversion_url ur backenden används direkt som href. Klienten validerar https, men kontraktet kräver inte att backenden validerar. React 19 blockerar javascript:-URL:er, så risken är liten, men http och andra scheman kan nå både adminlänken och kundens ruta. FÖRSLAG: Be backendpaketet avvisa allt utom https i POST .../status (422). Alternativt kan komponenten rendera länken bara när arTestadress(url) är sant.
- [notering] lib/admin/plattformsarenden.ts:103; Felrapporter.tsx 304 Sorteringen av ärenden och händelser jämför ISO-strängar med localeCompare. Om backenden blandar 'Z' och '+00:00', eller olika antal decimaler, kan ordningen bli fel. FÖRSLAG: Jämför Date.parse(...) i stället för strängar, eller lås formatet i kontraktet.
- [notering] components/admin/Felrapporter.tsx:135, 212 Underrubriken Felrapporter är en h3 med rubrikPanel, samma stil som radtitlarna i topplistan ovanför. Hierarkin mellan avsnittets rubrik och raderna kan bli svag. Nyckeltalsraden går dessutom till fyra kolumner från sm, i en sektion som på xl är halv bredd. Ingen visuell granskning har gjorts. FÖRSLAG: Orkestreraren granskar /forhandsvisning/felrapporter på desktop (även vid xl, där sektionen är halv bredd) och på mobil: nyckeltalsraden med fyra tal, underrubriken mot topplistan, en utfälld rad och ett lägesbyte med valideringsfel.

### Granskarens tester
- `node --test lib/admin/plattformsarenden.test.ts` → ℹ duration_ms 442.6565 (tests 9, pass 9, fail 0)
- `python -m pytest tests/invariants/test_inv_copy_001.py -q -p no:cacheprovider` → 4 passed in 2.32s
- `python -m pytest tests/invariants/test_inv_ui_001.py -q -p no:cacheprovider` → 4 passed in 1.17s

## Rättning
Jag prövade alla tre fynden mot koden och alla stämde. Fynd 2 och 3 är rättade i paketets filer. Fynd 1 är fortfarande blockerande. Det ligger utanför paketet och står i ej_gjort.

Fynd 2: en rad försvann så fort ett lägesbyte gjorde att den inte längre passade det valda filtret. Nu håller Felrapporter.tsx en mängd 'kvar' med id:n på ärenden som just bytt läge. Listan räknas fram med den nya rena funktionen synligaArenden(arenden, filter, kvar) i lib/admin/plattformsarenden.ts. En nyss ändrad rad står kvar med sitt nya läge och sin nya händelse, och den förblir utfälld eftersom React-nyckeln är densamma. Under metaraden står en tvåspråkig rad (role=status) om att raden ligger kvar tills admin byter filter eller laddar om. Mängden töms när filtret byts.

Fynd 3: interna värden visades oöversatta. Nu går vy, roll, händelsetyp och aktör genom en uppslagning, dataetikett(prefix, värde, locale), med texter i lib/admin/sprak.ts. Ett okänt värde visas som det kom, på samma sätt som för läget. Ordlistan tog jag från den byggda koden, inte från fyndet. vy är egen/admin/demo/kund (lib/snajp/hjalp.ts), roll är owner/member/viewer (profiles.role), typ är skapad/status/kundsvar/utslag (backendens plattformsarenden.py och memory.py) och aktör är kund, plattformsadmin eller admin:<uuid> (admin_plattformsarenden.py). admin:<uuid> visas som 'Plattformsadmin' via aktorNyckel().

Förhandsvisningens påhittade data använde fel ordlista: vy 'admin'/'kund', roll 'agare'/'medlem'/'plattformsadmin' och aktörerna 'anton', 'sebbe' och 'du'. Den har nu backendens värden. localStorage-nyckeln är höjd till v2, så att gamla sparade byten med de gamla värdena inte visas.

### Ändrade filer
- C:\Users\Anton L\snipe-leads\components\admin\Felrapporter.tsx
- C:\Users\Anton L\snipe-leads\lib\admin\sprak.ts
- C:\Users\Anton L\snipe-leads\lib\admin\plattformsarenden.ts
- C:\Users\Anton L\snipe-leads\lib\admin\plattformsarenden.test.ts
- C:\Users\Anton L\snipe-leads\app\forhandsvisning\felrapporter\page.tsx

### Tester
- `node --test lib/admin/plattformsarenden.test.ts (före rättningen, med de två nya testerna)` → Föll som väntat: 'test failed' eftersom synligaArenden och aktorNyckel inte fanns ännu
- `node --test lib/admin/plattformsarenden.test.ts` → ℹ tests 11 / ℹ pass 11 / ℹ fail 0; sista raden: ℹ duration_ms 513.3999
- `python -m pytest tests/invariants/test_inv_copy_001.py -q -p no:cacheprovider` → 4 passed in 2.13s
- `python -m pytest tests/invariants/test_inv_ui_001.py -q -p no:cacheprovider` → 4 passed in 1.24s
- `node node_modules/typescript/bin/tsc -p <scratchpad>\tsconfig.fr.json (tillfällig tsconfig som ärver repots strikta inställningar och bara tar med Felrapporter.tsx, FelOchEskaleringar.tsx, plattformsarenden.ts och förhandsvisningen)` → exit=0, inga typfel

### Ej gjort
- Fynd 1 är kvar och BLOCKERANDE. Det stämmer: app/api/admin/[...path]/route.ts exporterar bara GET (rad 53-60) och har kommentaren 'Ingen POST/PUT/PATCH/DELETE. Adminvyn LÄSER.' Därför får POST /api/admin/plattformsarenden/{id}/status svaret 405 i den riktiga adminytan, och lägesbytena fungerar bara i förhandsvisningen. Filen ligger utanför paketet och jag har inte rört den. Förslaget till orkestreraren är en POST som bara släpper igenom ['plattformsarenden', <uuid>, 'status'] (regex på uuid), bakom samma getPlatformAdmin()-grind och med master-nyckeln, där allt annat får 404. Kommentaren uppdateras i samma commit. Backenden (admin_plattformsarenden.py) läser också en adminrubrik (ADMIN_RUBRIK) för att kunna skriva aktören som admin:<uuid>, så proxyn bör skicka med den rubriken för den inloggade adminen. Annars blir aktören 'plattformsadmin'.
- Bilden: kontraktet har fortfarande bara har_bild och ingen väg att hämta själva bilden. Det är oförändrat sedan förra rapporten och är en kontraktsfråga till orkestreraren.
- Ingen visuell granskning: next dev var förbjudet. Orkestreraren behöver se förhandsvisningen på desktop och mobil före commit.
- Ingen git add eller commit, och ingen post i docs/BESLUT.md, enligt uppdraget.

### Antaganden
- En nyss ändrad rad står kvar tills filtret byts eller sidan laddas om, med en kort tvåspråkig förklaring i metaraden. Efter en omladdning gäller filtret som vanligt, eftersom läget då redan står i databasen.
- Vyn kund betyder adminbesök enligt lib/snajp/hjalp.ts och fick etiketten 'Adminbesök hos kunden'. egen = 'Kundens egen yta', admin = 'Adminytan', demo = 'Demoläget'.
- Rollerna följer profiles.role: owner = Ägare, member = Medlem, viewer = Läsbehörighet.
- Typen 'anteckning' finns inte i backenden i dag. Den används bara i förhandsvisningen för att visa en händelse som bara Snajp ser, och fick en etikett (Intern anteckning) så att den inte syns oöversatt.
- aktör admin:<uuid> visas som 'Plattformsadmin', eftersom ett uuid inte säger läsaren något. Vill man ha namnet behöver backenden skicka det.

### Syns i gränssnittet
- Förhandsvisningen: http://localhost:3000/forhandsvisning/felrapporter. Lägg till ?lage=nollstall första gången, eftersom localStorage-nyckeln nu är v2. ?lage=tomt och ?lage=fel visar tomläget respektive felläget.
- Fynd 2 att se i bild: med filtret Öppna, fäll ut F-0007, välj 'Stäng med förklaring', skriv ett meddelande och skicka. Raden ska stå kvar som Stängd med den nya händelsen, och under metaraden ska det stå 'Ändrad nyss. Raden står kvar tills du byter filter eller laddar om sidan.' Byt filter eller ladda om, så ska raden flytta till Klara.
- Fynd 3 att se i bild: fäll ut F-0006 (besökande admin). Vy ska stå som 'Adminbesök hos kunden' och Roll som 'Ägare'. Händelsekedjan ska visa 'Rapporten skickades' och 'Intern anteckning' (märkt Bara Snajp), och metaraderna ska säga 'Kunden' och 'Plattformsadmin' i stället för råa värden. F-0005 ska visa Roll 'Medlem'. Kontrollera samma sak med engelska som språk.
- Desktop och mobil (375 px): metaraden med förklaringen ska bryta snyggt under rubriken i den utfällda raden.
