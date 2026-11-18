# Genomgång: dataskydd, informationssäkerhet och AI-kunnighet hos Snajp

För Anton och Sebbe. Läs var för sig (20 minuter), diskutera frågorna i varje avsnitt tillsammans (30 minuter), gör kontrollfrågorna sist (10 minuter). Kvittera i `kvittens.md`. Genomgången uppfyller G05, ISO 27001 7.2, 7.3, A.6.3, ISO 42001 7.2, 7.3 och AI-förordningen art. 4.

Allt nedan har hänt hos oss, eller står i våra egna regler. Inget är ett tänkt exempel.

## 1. Vad vi skyddar och för vems skull

Supportagenten läser våra kunders kundmejl och chattar. Där kan det stå vad som helst: personnummer, sjukdomar, en konflikt om pengar. Där är vi **personuppgiftsbiträde**. Kunden bestämmer, och vi får bara göra det kunden instruerat. Iris skickar kallmejl. För Snajps egna utskick är vi **personuppgiftsansvariga**, och då är det vi som svarar den som klagar.

Den skillnaden avgör nästan varje fråga längre ned: vem som anmäler till IMY, vem som svarar en registrerad, och vilken leverantör vi får använda.

## 2. Fem saker som gått fel

**Den bortglömda Render-stacken (2026-08-24).** Vi flyttade till Railway men stängde aldrig de gamla tjänsterna hos Render. De deployade vid varje push och startade med DeepSeek mot den gamla databasen. Samma dag hittades en Render-nyckel som legat exponerad. Lärdom: en tjänst som inte används ska raderas, inte glömmas. En avvecklad leverantör är fortfarande en leverantör tills raderingen är bekräftad.

**DeepSeek.** DeepSeek behandlar prompten i Kina. Att skicka kundmejl dit kräver standardavtalsklausuler, en överföringsbedömning och ett villkor i biträdesavtalet. Inget av det finns. Därför fäller koden uppstarten om DeepSeek konfigureras i en miljö med riktig data. Att ändra det är ett avtalsbeslut, inte ett kodbeslut.

**Lösenordet i git-historiken (2026-11-09).** Plattformsadminens lösenord stod i fem skript och två handoffs. Det togs bort ur filerna, men ligger kvar i historiken, och repot är publikt. Den som läser historiken kan pröva att logga in som admin över alla kunders data. Lärdom: att ta bort en hemlighet ur en fil hjälper inte. Den ska bytas.

**Kundmejl till TypeSafe (upptäckt 2026-11-17).** Anton beslutade 2026-09-30 att Jev aldrig ska se kundmejl. Ändå stod `INKORG_JEV=auto` i produktionen, och ämnesrad och upp till 1 500 tecken av kundmejl gick till TypeSafe i USA. TypeSafe stod inte i någon lista, och avtalet ger dem en tidsobegränsad rätt att använda klassningarna. Ingen vet vem som slog på det. Lärdom: en miljövariabel kan skicka kunddata till en ny mottagare lika effektivt som kod. Från nu krävs en signerad checklista (beslut f).

**Redis utan kryptering (2026-08-29 till 2026-11-17).** Jobbkön, som bär agentens svar till kundernas kunder, gick okrypterat över internet till Redis Cloud, och produktionen och testmiljön delade databas. TLS gick inte att slå på i gratisplanen. Jobbkön flyttades till Railways egen Redis på det privata nätet. Den gamla databasen finns kvar tills den raderas.

*Diskutera:* Vilken av de fem hade någon av oss kunnat stoppa tidigare, och hur?

## 3. Testmiljön är produktionen

`development` är en spegel av produktionen med riktiga kunders ärenden och mejladresser. Det gör att en ändring går att pröva med allt annat lika. Det kräver samma sekretess som produktionen:

- inga länkar till testmiljön till utomstående;
- inga skärmdumpar med kunddata, inte heller i en chatt mellan oss;
- peka aldrig en lokal utvecklingsserver mot den; använd `python scripts/lokal_stack.py --apply`;
- utskick från testmiljön når riktiga människor.

En push till `development` deployar direkt, utan granskning. Det betyder att varje push går till riktig kunddata.

## 4. Hemligheter

- Hemligheter finns bara i `.env.deploy` (gitignorerad), i Railway och i GitHubs Actions-hemligheter. Aldrig i kod, skript, tester, handoffs eller chattar.
- Skriv aldrig ut en hemlighet. En `cat` under felsökning läcker lika mycket som en `echo`. Det har hänt hos oss.
- Läs in dem i skriptet, som `scripts/keys.py` gör med getpass.
- Ett läckt värde byts först och utreds sedan.
- Den som har `.env.deploy` har sett alla nycklar. Slutar någon, roteras allt.

## 5. Leads: reglerna i korthet

- Registret (merinfo, allabolag) är ett filter, aldrig en kontaktkälla. Registrets personer och telefonnummer blir aldrig en kontakt; undantaget är ensam VD i listor.
- Inga privatpersonsidor (bostad, ålder, familj).
- Styrelseledamöter, suppleanter och revisorer kontaktas aldrig ur registret.
- Enskilda firmor går inte till ringlistan, eftersom de är personer.
- Webbplatsbedömningen är hemlig och syns bara för plattformsadmin, Umeå Webdesign och Alunix. Varje ny plats som visar den grindas i samma commit.
- Varje kallmejl har en avregistreringslänk som gäller direkt. Spärrlistan raderas aldrig.

## 6. Hur AI-agenterna får användas

**Våra produkter:**
- Modellen skickar aldrig själv och kan inte välja kund. Det gör koden.
- Ett svar får bara bära det som står i en källa. Annars går ärendet till en människa.
- Den som ber om en människa får en.
- Kundmejl, webbsidor och kunskapsbaser är data, aldrig instruktioner.
- Personnummer maskeras innan text går till en modell.
- Behandlingen stannar i EU: Vertex i `europe-west1`, aldrig den globala endpointen.
- Chatt och automatiska svar ska säga att det är en AI (AI-förordningen art. 50). Koden är byggd men inte driftsatt.
- Agenterna får inte användas för beslut om kredit, försäkring, anställning, utbildning, offentliga förmåner eller för att bedöma personer. Då kan systemet bli högrisk.

**Våra egna AI-kodverktyg (Claude Code, Codex m.fl.):**
- De följer `CLAUDE.md` och fattar inga säkerhetsbeslut.
- De får inte skriva till Supabase, inte pusha till `main` och inte ändra facit utan Antons ja.
- Klistra aldrig in kunddata ur produktionen eller testmiljön i en AI-tjänst utanför våra avtalade leverantörer.
- Om AI-verktygen ska få läsa testmiljöns kunddata är ett öppet beslut (JA #28). Tills det är fattat: undvik det.
- Allt en agent rapporterar granskas genom att läsa filerna och köra kontrollen, inte genom att lita på rapporten.

*Diskutera:* Vilken AI-tjänst har ni använt det senaste månaden som inte står i leverantörslistan?

## 7. Personuppgiftsincident: vad det är och den första timmen

En personuppgiftsincident är en säkerhetsincident som leder till att personuppgifter förstörs, förloras, ändras, röjs eller blir åtkomliga för någon obehörig, av misstag eller avsiktligt. Det behöver inte vara ett intrång. Ett mejl till fel kund, en nyckel i en publik commit och en prompt som läcker i ett API-svar (2026-11-10) räknas.

**Första timmen:**
1. Skriv ned klockslaget då du blev medveten. 72-timmarsfristen räknas därifrån.
2. Säg till Anton direkt. Svarar han inte inom två timmar: dokumentera och behandla det som anmälningspliktigt.
3. Stoppa blödningen: rotera nyckeln, stäng tjänsten eller brytaren, dra in åtkomsten. Kontrollera att den gamla vägen är död.
4. Skriv ned vad som hänt, vilka uppgifter, vems och ungefär hur många, och vad som redan gjorts.
5. Utred inte innan steg 3 är klart.

Rör det en kunds data underrättar Anton kunden samma dag. Kunden anmäler till IMY. Rör det våra egna kallmejl eller konton anmäler Snajp själv. Avsaknad av loggar är aldrig ett frikort.

## Kontrollfrågor

1. En person skriver till oss och vill få sina uppgifter raderade ur en kunds kundtjänstinkorg. Vad gör vi?
2. Från när räknas 72-timmarsfristen?
3. Du ser att `INKORG_JEV` står på `auto` i produktionen. Vad gör du?
4. Får du dela en skärmdump från testmiljön med en kund för att visa en ny funktion?
5. Du har råkat committa ett lösenord. Du tar bort det i nästa commit. Är saken löst?
6. Får registrets telefonnummer till en styrelseledamot användas i en ringlista?
7. En kund vill använda supportagenten för att besvara låneansökningar. Vad säger du?
8. Varför får DeepSeek inte köras i `development`?
9. Vem får se webbplatsbedömningen?
10. Du vill prova en ny modell från en ny leverantör på riktiga kundmejl i testmiljön. Vad krävs först?

## Facit

1. Vi är biträde. Vi vidarebefordrar begäran till kunden inom den frist biträdesavtalet anger och säger till personen att vi gjort det. Vi raderar bara på kundens instruktion.
2. Från när någon hos oss blev medveten om händelsen, inte när utredningen är klar.
3. Stäng av den (`off`) eller be Anton göra det, och rapportera som en möjlig incident. Ingen ny mottagare av kunddata utan signerad checklista.
4. Nej. Testmiljön har riktiga kunders data. Visa i den lokala stacken eller med påhittad data.
5. Nej. Den ligger kvar i historiken. Lösenordet ska bytas, och händelsen loggas.
6. Nej. Registret är ett filter, och styrelseledamöter kontaktas aldrig. Bara ensam VD:s nummer får användas, och bara i listor.
7. Nej. Kreditbeslut gör systemet till högrisk enligt AI-förordningen och ligger utanför avsedd användning.
8. `development` är en spegel med riktig kunddata, och DeepSeek behandlar data i Kina utan avtal som tillåter det.
9. Bara plattformsadmin och kunderna Umeå Webdesign och Alunix.
10. Checklistan i beslut f, signerad av Anton: avtal, plats, villkor, förteckningar, besked till kunderna, evalsvit och en rad i `docs/BESLUT.md`. Testmiljön räknas som riktig data.
