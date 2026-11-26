# Paritet 05: Mejl, kalender, synk och utskick

Området är hur Twenty kopplar användarens egen brevlåda och kalender (Google, Microsoft, IMAP/SMTP/CalDAV), synkar mejl och möten in på personer, bolag och affärer, låter användaren skriva och svara inifrån appen, och skickar kampanjer från verifierade avsändardomäner med avregistrering och mätning, plus systemets egna transaktionsmejl. Snajp CRM har i dag ingen egen mejl- eller kalendersynk och inga utskick: det som finns är tidslinjen som läser Iris mejl och supportens ärenden vid läsning, loggade aktiviteter (samtal, möte, mejl, besök), knappen Mejla som öppnar användarens mejlprogram och att Kontakta inte i CRM:et stoppar Snajps utskick, medan inkorgar, kampanjer, avsändardomäner och avregistrering finns i resten av Snajp och flyttar in i fas 4 och 5.

Antal per läge (347 rader): verifierad 0, byggd 0, delvis 14, inte gjord 317, avstår 16.

## De största luckorna

- Det går inte att koppla sin egen Gmail, Outlook eller IMAP-brevlåda till CRM:et, så mejl man skickar och tar emot hamnar aldrig på personen eller bolaget av sig själva.
- Ingen kalendersynk: möten i Google- eller Microsoft-kalendern syns inte på posterna, och det går inte att boka ett möte med inbjudan från en post.
- Ingen mejlflik på posten: tidslinjens mejl från Iris finns i API:t men visas inte i gränssnittet, och det går inte att öppna en tråd och läsa den.
- Det går inte att skriva eller svara på mejl inifrån CRM:et; knappen Mejla öppnar bara användarens eget mejlprogram.
- Inga kampanjer i CRM:et: listor, massutskick, schemaläggning och resultat per kampanj finns bara under Leads tills fas 4.
- Ingen hantering av avregistrerade och spärrade adresser i CRM:et (studs, klagomål, avregistrering); bara Kontakta inte på bolag och person.
- Inga avsändardomäner med DNS-poster och verifiering i CRM:et; de ligger i Snajps inställningar och flyttar i fas 5.
- Inga personer och bolag skapas ur korrespondens, och det finns ingen spärrlista för vilka adresser som får synkas in.
- Ingen synlighetsnivå per brevlåda för kollegor (bara metadata, ämne eller allt); det enda som finns är att en integrationsnyckel inte får se utdragen.
- Ingen spårning av öppningar och klick i CRM:et och inga leveranshändelser (levererat, studs, klagomål) per mottagare.

## Rad för rad

| ID | Funktion | Läge | Var i Snajp, eller varför inte | Fas |
|---|---|---|---|---|
| MK-A01 | Ansluta ett Google-konto (Gmail och Google Kalender) med OAuth och en inställningsguide efteråt. | inte gjord | CRM:et har ingen kontokoppling. Snajp kopplar inkorgar med IMAP och applösenord, aldrig OAuth (funktionslistan IN-074). | ej planerad |
| MK-A02 | Ansluta ett Microsoft-konto (Outlook och Microsoft-kalendern) med OAuth. | inte gjord | Ingen OAuth-koppling mot e-post i CRM:et eller i resten av Snajp. | ej planerad |
| MK-A03 | Kontrollera att alla begärda behörigheter beviljats vid anslutningen, och skapa bara de kanaler som tjänsten tillåter. | inte gjord | Hör till OAuth-anslutningen, som saknas. | ej planerad |
| MK-A04 | Kräva en särskild behörighet i rollen för att få ansluta konton. | inte gjord | CRM:et har bara omfång på API-nycklar (`app/crm/nycklar.py`), inga roller per användare. | 5 |
| MK-A05 | Slå av enskilda leverantörer (Gmail, Google-kalender, Microsoft-post, Microsoft-kalender) för hela installationen. | avstår | Gäller bara egen drift av Twenty: serverflaggor för den som kör sin egen installation. | |
| MK-A06 | Ansluta en egen server med IMAP för inkommande, SMTP för utgående och CalDAV för kalender. | inte gjord | Snajp kopplar en inkorg med IMAP under inställningarna (`snajp-support/app/email_pipeline/connectors/imap.py`, IN-074), utanför CRM:et. CalDAV finns inte alls. | 5 |
| MK-A07 | Validera serveruppgifterna (värd, port, lösenord) och vägra interna nätadresser. | inte gjord | Finns inte i CRM:et; inkorgskopplingen i resten av Snajp flyttar i fas 5. | 5 |
| MK-A08 | Prova anslutningen innan kontot sparas, med begripliga felbesked per fel. | inte gjord | Snajps inkorgskoppling provar inloggningen innan något sparas (IN-074), men den nås inte från CRM:et. | 5 |
| MK-A09 | Spara eller uppdatera ett IMAP/SMTP/CalDAV-konto och starta synken direkt. | inte gjord | Inkorgen sparas i Snajps inställningar (`ss_mailboxes`), inte i CRM:et. | 5 |
| MK-A10 | Visa ett IMAP-kontos inställningar för redigering, aldrig lösenordet. | inte gjord | Finns inte i CRM:et. | 5 |
| MK-A11 | Återansluta ett konto med samma adress och starta om dess kanaler. | inte gjord | Hör till OAuth-anslutningen, som saknas. | ej planerad |
| MK-A12 | Hålla en lista per användare över konton som måste återanslutas, för en uppmaning i gränssnittet. | inte gjord | Ingen kontokoppling i CRM:et. | ej planerad |
| MK-A13 | Hämta kontots e-postalias så att egna meddelanden känns igen och kan skickas från alias. | inte gjord | Ingen kontokoppling i CRM:et. | ej planerad |
| MK-A14 | Förnya åtkomstnyckeln automatiskt, under lås så att samtidiga förnyelser inte krockar. | inte gjord | Hör till OAuth-anslutningen, som saknas. | ej planerad |
| MK-A15 | Klassa leverantörens förnyelsefel som permanenta (kräver återanslutning) eller tillfälliga. | inte gjord | Hör till OAuth-anslutningen, som saknas. | ej planerad |
| MK-A16 | Spara kontots senaste autentiseringsfel och senaste lyckade förnyelse. | inte gjord | Ingen kontokoppling i CRM:et. | 5 |
| MK-A17 | Låta ett konto vara personligt eller delat i arbetsytan, med regler för vem som får administrera det. | inte gjord | Ingen kontokoppling i CRM:et; inkorgar i resten av Snajp är kundens. | 5 |
| MK-A18 | Lista användarens anslutna konton utan nycklar och lösenord. | inte gjord | Finns inte i CRM:et. | 5 |
| MK-A19 | Koppla från ett konto: stoppa synken, radera nycklarna och behålla importerad data. | inte gjord | Finns inte i CRM:et. | 5 |
| MK-A20 | Radera ett konto tillsammans med dess kanaler och den synkade datan. | inte gjord | Finns inte i CRM:et. | 5 |
| MK-A21 | Flytta en medlems konton till en efterträdare när medlemmen lämnar arbetsytan. | inte gjord | Ingen kontokoppling och ingen sådan överlämning. | ej planerad |
| MK-A22 | Lagra nycklar och lösenord krypterade i vila. | inte gjord | CRM:et lagrar inga brevlådeuppgifter; API-nycklarna är en annan sak (`app/crm/nycklar.py`). | 5 |
| MK-A23 | Starta kanalernas synk när användaren slutfört inställningsstegen. | inte gjord | Ingen mejl- eller kalendersynk i CRM:et. | ej planerad |
| MK-A24 | Bara riktiga brevlådor kan anslutas, inte alias som vidarebefordrar; obegränsat antal konton per användare. | inte gjord | Ingen kontokoppling i CRM:et. | 5 |
| MK-A25 | Tillåta anslutning till interna servrar genom en serverinställning. | avstår | Gäller bara egen drift av Twenty. | |
| MK-A26 | Skicka användaren till inställningarna med felet synligt när OAuth-återkomsten misslyckas. | inte gjord | Hör till OAuth-anslutningen, som saknas. | ej planerad |
| MK-A27 | Hålla reda på kontots leverantörstyp (Google, Microsoft, IMAP, delad inkorg, app och inloggningstyperna). | inte gjord | Ingen kontokoppling i CRM:et. | ej planerad |
| MK-A28 | Microsoft-kontot kräver licens och läs- och skrivbehörighet för post och kalender. | inte gjord | Hör till Microsoft-anslutningen, som saknas. | ej planerad |
| MK-A29 | Serverns OAuth-uppsättning för synk (API:er, återanropsadresser, Pub/Sub). | avstår | Gäller bara egen drift av Twenty. | |
| MK-B01 | Mejlkanalens typer: vanlig brevlåda, delad inkorg, sms och app-kanal. | inte gjord | Inga mejlkanaler i CRM:et. | ej planerad |
| MK-B02 | Synlighet per mejlkanal för kollegor: bara metadata, även ämnet, eller allt. | inte gjord | Inga mejlkanaler i CRM:et. Det närmaste är att en integrationsnyckel inte får utdragen på tidslinjen (se MK-F03). | ej planerad |
| MK-B03 | Synlighet per kalenderkanal: bara tid och deltagare, eller hela händelsen. | inte gjord | Ingen kalendersynk i CRM:et. | ej planerad |
| MK-B04 | Skapa personer automatiskt ur mejl, med policy för skickat, mottaget eller inget. | inte gjord | CRM:ets personer kommer från källsystemens synk och från formuläret (`app/crm/synk.py`), aldrig ur korrespondens. | ej planerad |
| MK-B05 | Skapa personer automatiskt ur kalendern, med policy för deltagare och organisatör. | inte gjord | Ingen kalendersynk i CRM:et. | ej planerad |
| MK-B06 | Hoppa över adresser hos gratisleverantörer när kontakter skapas. | inte gjord | Ingen automatisk kontaktskapelse i CRM:et. | ej planerad |
| MK-B07 | Hoppa över gruppmejl och utskickslistor, med radering eller import i efterhand när valet ändras. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-B08 | Hoppa över privata kalenderhändelser. | inte gjord | Ingen kalendersynk i CRM:et. | ej planerad |
| MK-B09 | Slå på och av synken per kanal. | inte gjord | Ingen mejl- eller kalendersynk i CRM:et (källsystemens anslutningar i Synk är en annan sak). | ej planerad |
| MK-B10 | Välja att synka alla mappar eller bara valda mappar. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-B11 | Slå på och av synken för enskilda mappar, med import i efterhand. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-B12 | Neka ändrade kanalinställningar medan listhämtning med väntande åtgärder pågår. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-B13 | Bestämma vem som får ändra en kanals inställningar. | inte gjord | Inga kanaler och inga roller per användare i CRM:et. | ej planerad |
| MK-B14 | Lista användarens mejlkanaler, kalenderkanaler och mappar. | inte gjord | Inga kanaler i CRM:et. | ej planerad |
| MK-B15 | Visa importförloppet i procent under den första mejlimporten. | inte gjord | Synkvyn visar förlopp för källsystemens körningar (`components/crm/app/SynkVy.tsx`), men det finns ingen mejlimport. | ej planerad |
| MK-B16 | Arbetsytans val att också synka interna mejl mellan kollegor. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-B17 | Det som aldrig synkas: gruppmejl, uteslutna mappar, privata och interna händelser. | inte gjord | Ingen mejl- eller kalendersynk i CRM:et. | ej planerad |
| MK-B18 | App-ägda meddelandekanaler där en installerad app läser in och skickar meddelanden. | inte gjord | CRM:et har inga appar från tredje part. | ej planerad |
| MK-C01 | Mejlsynkens stadier, från väntar på konfiguration via listhämtning och import till klar eller misslyckad. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C02 | Mejlsynkens status som användaren ser: ej synkad, pågår, aktiv, saknar behörighet, okänt fel. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C03 | Schemalagd listhämtning från brevlådan var femte minut. | inte gjord | Ingen mejlsynk i CRM:et; Snajps inkorg hämtas av en egen poller utanför CRM:et (`app/email_pipeline/poller.py`). | 5 |
| MK-C04 | Listhämtningen: mappar, ändringslistor med synkmarkör, kö för import och borttagning av det som försvunnit. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C05 | Schemalagd import av köade meddelanden varje minut. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C06 | Importera en sats meddelanden och gå tillbaka till väntan när sista satsen är klar. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C07 | Strypa och vänta exponentiellt vid tillfälliga fel, och ge upp efter fem försök. | inte gjord | Ingen mejlsynk i CRM:et. Strypningen i CRM:et gäller API-anrop och webhooks, inte brevlådor. | ej planerad |
| MK-C08 | Klassa synkfel: saknad behörighet, ogiltigt certifikat, ogiltig synkmarkör, okänt fel. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C09 | Starta om kanaler med okänt fel automatiskt var 30:e minut. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C10 | Hitta synkar som fastnat i mer än 30 minuter och lägga tillbaka dem. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C11 | Filtrera bort kalenderinbjudningar, avregistreringsmejl, spärrade, interna och gruppmejl före sparning. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C12 | Känna igen gruppmejl på huvuden och avsändaradresser som noreply och info@. | inte gjord | Snajps inkorgsklassning känner igen avsändare som noreply (`app/email_pipeline/klassning.py`), utanför CRM:et. | 5 |
| MK-C13 | Känna igen avregistreringsadresser på orden unsubscribe, unsub och opt-out. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C14 | Inte importera vissa bilagor (winmail.dat, .ics, kalendertyper, inbäddade bilder) och strypa bilagehämtningen. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C15 | Lagra ett meddelande en gång även när flera kollegors brevlådor har det. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C16 | Samla meddelanden i trådar efter leverantörens tråd-id eller References och In-Reply-To. | inte gjord | Trådar finns i Leads konversationer, och tidslinjen länkar till dem (`app/crm/tidslinje.py`, länktypen konversation), men CRM:et trådar inget själv. | 4 |
| MK-C17 | Synka utkast och följa upp när ett utkast senare skickas. | inte gjord | Ingen mejlsynk i CRM:et. Tidslinjen visar med flit aldrig osända utkast (`app/crm/tidslinje.py`). | ej planerad |
| MK-C18 | Importera eller ta bort en mapps meddelanden i efterhand när mappen slås på eller av. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C19 | Synka mapplistan från leverantören och utesluta papperskorg, skräppost och Gmails kategorier. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C20 | Leverantörsspecifika satsgränser för Gmail, Microsoft och IMAP. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C21 | Skicka synkstatusen live till kontoägarens öppna sidor. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C22 | Städa bort meddelanden och trådar som inte längre hör till någon kanal när kanal eller konto raderas. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C23 | Räkna kanaler per synkstatus för drift och larm. | avstår | Gäller bara egen drift av Twenty: övervakning av den egna serverns synkjobb. | |
| MK-C24 | Synktakt: ungefär var femte minut efter första importen, cirka 400 meddelanden per minut. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C25 | Importera vidarebefordrad post till delad inkorg direkt, och slänga det leverantören dömt som skräppost. | inte gjord | Ingen delad inkorg i CRM:et. Snajps supportinkorg hämtar med IMAP i stället för vidarebefordran. | 5 |
| MK-C26 | Klippa bort citerad historik ur brödtexten, på många språk. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C27 | Känna igen citat i HTML-mejl och sanera HTML innan det blir text. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C28 | Satsstorleken för import är en serverinställning. | avstår | Gäller bara egen drift av Twenty. | |
| MK-C29 | Känna igen standardmappar (inkorg, utkast, skickat, papperskorg, skräppost) per leverantör. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C30 | Importera bilagor från synkade mejl, styrt av en funktionsflagga. | inte gjord | Ingen mejlsynk i CRM:et. Bilagor kan laddas upp för hand (`app/crm/objekt.py`), men aldrig ur mejl. | ej planerad |
| MK-C31 | Översätta Gmails fel till synkens felklasser. | inte gjord | Ingen Gmail-koppling. | ej planerad |
| MK-C32 | Översätta Microsoft Graphs fel till synkens felklasser. | inte gjord | Ingen Microsoft-koppling. | ej planerad |
| MK-C33 | Översätta IMAP-serverns fel till synkens felklasser. | inte gjord | Snajps IMAP-koppling har egen felhantering (`app/email_pipeline/connectors/imap.py`), utanför CRM:et. | 5 |
| MK-C34 | Klassa nätverksfel som tillfälliga och strypa dem. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-C35 | Tolka ett Gmail-meddelande: huvuden, mottagare, tid, brödtext och etiketter. | inte gjord | Ingen Gmail-koppling. | ej planerad |
| MK-C36 | Avgöra om ett meddelande är utgående eller inkommande utifrån avsändaren. | inte gjord | Tidslinjen läser riktningen som Leads redan sparat på meddelandet (`app/crm/tidslinje.py`, `direction`), men CRM:et avgör den inte själv. | 4 |
| MK-C37 | Gmail med valda mappar: vilka etiketter som söks och utesluts. | inte gjord | Ingen Gmail-koppling. | ej planerad |
| MK-C38 | IMAP: inkrementell synk per mapp med UID, UIDVALIDITY och MODSEQ. | inte gjord | Snajps inkorg sparar senaste UID och UIDVALIDITY (migration 150, `ss_mailboxes.imap_last_uid`), utanför CRM:et. | 5 |
| MK-C39 | IMAP: mottagningstid ur datumhuvudet, annars serverns datum. | inte gjord | Finns inte i CRM:et. | 5 |
| MK-C40 | IMAP: hitta Skickat-mappen och alltid synka den. | inte gjord | Snajp lägger kopior i Skickat (`app/email_pipeline/skickatkopia.py`), utanför CRM:et. | 5 |
| MK-C41 | Microsoft: bara filbilagor och oföränderliga id. | inte gjord | Ingen Microsoft-koppling. | ej planerad |
| MK-C42 | Felhantering när Googles alias hämtas. | inte gjord | Ingen Google-koppling. | ej planerad |
| MK-C43 | Spara kontoägare och adress på kopplingen mellan meddelande och kanal. | inte gjord | Inga kanaler i CRM:et. | ej planerad |
| MK-D01 | Kalenderhändelsens fält (titel, tid, heldag, inställd, plats, beskrivning, konferenslänk) kopplade till deltagare och till person, bolag och affär. | delvis | En aktivitet av typen möte har rubrik, text, tidpunkt, varaktighet, utfall, ansvarig och koppling till bolag, person eller affär (`crm_aktiviteter` i migration 164, `app/crm/objekt.py`; prövas i `test_aktiviteter_loggas_sorteras_och_filtreras`, `snajp-support/tests/crm/test_objekt_ovriga.py`). Saknas: synkade händelser, slut, heldag, plats, konferenslänk och deltagare. | ej planerad |
| MK-D02 | Mötesdeltagare med e-post, namn, organisatör och svarsstatus, kopplade till person. | inte gjord | Ingen kalendersynk; en loggad aktivitet har inga deltagare. | ej planerad |
| MK-D03 | Kalendersynkens stadier och status. | inte gjord | Ingen kalendersynk i CRM:et. | ej planerad |
| MK-D04 | Schemalagd listhämtning och import för kalendern, med strypning och omstart. | inte gjord | Ingen kalendersynk i CRM:et. | ej planerad |
| MK-D05 | Filtrera bort spärrade, inställda, privata och interna kalenderhändelser. | inte gjord | Ingen kalendersynk i CRM:et. | ej planerad |
| MK-D06 | Dela samma möte som en post när det finns i flera kollegors kalendrar. | inte gjord | Ingen kalendersynk i CRM:et. | ej planerad |
| MK-D07 | Skriva om en händelse bara när något faktiskt ändrats. | inte gjord | Ingen kalendersynk i CRM:et. | ej planerad |
| MK-D08 | Importera återkommande händelser 90 dagar framåt och hämta fler när horisonten närmar sig. | inte gjord | Ingen kalendersynk i CRM:et. | ej planerad |
| MK-D09 | Dölja titel och beskrivning för kollegor när kalenderns synlighet är bara metadata. | inte gjord | Ingen kalendersynk i CRM:et. | ej planerad |
| MK-D10 | Lista möten på en person, ett bolag eller en affär, med sökning och sidindelning. | delvis | API:t listar loggade aktiviteter per bolag, person eller affär med sidindelning och fritextsökning (`GET /v1/activities`, `snajp-support/app/api/crm_v1_objekt.py:lista_aktiviteter`; prövas i `test_aktiviteter_loggas_sorteras_och_filtreras`). Saknas: filter på typen möte, synkade händelser och deltagare. | ej planerad |
| MK-D11 | Skapa en kalenderhändelse från en post, med gäster, tidszon, videomöte och inbjudningar. | inte gjord | Bara att logga ett möte i efterhand som aktivitet (`POST /v1/activities`); ingen bokning hos någon kalender. | ej planerad |
| MK-D12 | Återkommande händelse vid skapande (dagligen, veckovis, månadsvis, årligen, slut på datum eller antal). | inte gjord | Ingen kalenderbokning i CRM:et. | ej planerad |
| MK-D13 | Skicka inbjudan som iCal via kontots SMTP för CalDAV-konton. | inte gjord | Ingen kalenderbokning i CRM:et. | ej planerad |
| MK-D14 | Koppla händelsen automatiskt till posten den skapades från, så att den syns på tidslinjen. | inte gjord | En aktivitet kopplas till sin post men står inte på postens tidslinje (`app/crm/tidslinje.py` läser bara postens egna händelser, Iris och supporten). | ej planerad |
| MK-D15 | Städa bort kalenderdata när kanal eller konto raderas. | inte gjord | Ingen kalendersynk i CRM:et. | ej planerad |
| MK-D16 | Låta spärrlistan radera eller återimportera kalenderhändelser i efterhand. | inte gjord | Ingen kalendersynk och ingen spärrlista för import. | ej planerad |
| MK-D17 | Synka primärkalendern hos Google och Microsoft, och alla kalendrar hos CalDAV inom ett tidsfönster. | inte gjord | Ingen kalendersynk i CRM:et. | ej planerad |
| MK-D18 | Översätta leverantörens händelse (inställd, privat, heldag, konferens, svarsstatus). | inte gjord | Ingen kalendersynk i CRM:et. | ej planerad |
| MK-D19 | Känna igen lokaler och resurser bland deltagarna. | inte gjord | Ingen kalendersynk i CRM:et. | ej planerad |
| MK-D20 | Klassa CalDAV-serverns fel. | inte gjord | Ingen CalDAV-koppling. | ej planerad |
| MK-D21 | Högst 100 deltagare när en kalenderhändelse skapas. | inte gjord | Ingen kalenderbokning i CRM:et. | ej planerad |
| MK-D22 | Skapa händelse i Google Kalender med Google Meet och inbjudningar. | inte gjord | Ingen Google-koppling. | ej planerad |
| MK-D23 | Skapa händelse i Microsoft-kalendern med Teams. | inte gjord | Ingen Microsoft-koppling. | ej planerad |
| MK-D24 | Skapa händelse via CalDAV med iCal-fil och inbjudan via SMTP. | inte gjord | Ingen CalDAV-koppling. | ej planerad |
| MK-D25 | Två felbesked när en händelse inte kan skapas. | inte gjord | Ingen kalenderbokning i CRM:et. | ej planerad |
| MK-D26 | Tolka CalDAV-händelser ur iCal. | inte gjord | Ingen CalDAV-koppling. | ej planerad |
| MK-D27 | Hämta kommande förekomster av återkommande Google-serier bortom horisonten. | inte gjord | Ingen Google-koppling. | ej planerad |
| MK-E01 | Mejldeltagare med roll (från, till, kopia, dold kopia, svarsadress), namn och kopplad person. | inte gjord | Ingen mejlsynk i CRM:et; tidslinjen bär bara rubrik, utdrag och kontaktnamn för Iris mejl. | ej planerad |
| MK-E02 | Matcha deltagare mot personer på e-post, skiftlägesokänsligt, först primär och sedan övriga adresser. | delvis | Tidslinjen knyter Iris mejl, samtal och supportens ärenden till en person på exakt e-postadress, utan hänsyn till versaler (`app/crm/tidslinje.py:for_person`; prövas i `test_personens_tidslinje_gar_pa_exakt_adress`, `snajp-support/tests/crm/test_tidslinje.py`). Saknas: ytterligare adresser per person, matchning mot medarbetare och mot synkade mejl. | ej planerad |
| MK-E03 | Koppla om deltagare när en person skapas eller byter e-post, och koppla bort när personen raderas. | delvis | Tidslinjen komponeras vid läsning, så en ny eller ändrad adress gäller direkt utan omkoppling (`app/crm/tidslinje.py`). Saknas: lagrade deltagarkopplingar för synkade mejl och möten. | ej planerad |
| MK-E04 | Matcha app-kanalers deltagare mot telefon, länk eller textfält på personen. | inte gjord | CRM:et har inga app-kanaler. | ej planerad |
| MK-E05 | Koppla tråd och möte automatiskt till personen, personens bolag och personens affärer. | delvis | Bolagets tidslinje samlar bolagets leads (på organisationsnummer eller domän) och supportärenden från bolagets personer (`app/crm/tidslinje.py:for_bolag`; prövas i `test_bolagets_tidslinje_samlar_crm_leads_och_support`). Saknas: affärer, manuella kopplingar och synkade mejl och möten. | 4 |
| MK-E06 | Avgöra vilka mejldeltagare som blir kontakter (inte utkast, inte egna adresser, inte gratis- eller gruppadresser). | inte gjord | Ingen automatisk kontaktskapelse i CRM:et. | ej planerad |
| MK-E07 | Avgöra vilka mötesdeltagare som blir kontakter. | inte gjord | Ingen kalendersynk i CRM:et. | ej planerad |
| MK-E08 | Hoppa över egna adresser, medarbetare och kollegor på samma domän när kontakter skapas. | inte gjord | Ingen automatisk kontaktskapelse i CRM:et. | ej planerad |
| MK-E09 | Återanvända befintlig person, även raderad, och fylla i tomt namn. | inte gjord | Synken återanvänder en befintlig person på e-post (`app/crm/synk.py`), men inget skapas ur korrespondens. | ej planerad |
| MK-E10 | Härleda för- och efternamn ur visningsnamnet eller adressens lokaldel. | inte gjord | Ingen automatisk kontaktskapelse i CRM:et. | ej planerad |
| MK-E11 | Skapa bolag från arbetsdomänen och koppla personen dit. | inte gjord | Tidslinjen hittar ett bolags leads på domänen när numret saknas, men inget bolag skapas ur en adress. | ej planerad |
| MK-E12 | En lista över gratisleverantörers domäner avgör vad som inte är en arbetsdomän. | delvis | `app/crm/falt.py:doman_ar_privat` med Snajps lista över privata domäner (gmail.com, telia.com och liknande, `app/leads/discovery.py:_PRIVATA_DOMÄNER`); prövas i `test_webbplats_och_privata_domaner`, `snajp-support/tests/crm/test_falt_och_adaptrar.py`. Saknas: listan är några dussin domäner, förlagans drygt 16 000. | ej planerad |
| MK-E13 | Skapa kontakter i satser om 100 och tåla krockar vid samtidig import. | inte gjord | Ingen automatisk kontaktskapelse i CRM:et. | ej planerad |
| MK-E14 | Spärrlista med adresser och domäner (även underdomäner) som aldrig importeras. | inte gjord | Ingen import ur mejl. Kontakta inte i CRM:et stoppar utskick, inte import (se MK-I15). | ej planerad |
| MK-E15 | Spärrlistan personlig eller för hela arbetsytan, med behörighet och dubblettskydd. | inte gjord | Ingen spärrlista för import. | ej planerad |
| MK-E16 | Ny spärr raderar redan importerat, borttagen spärr importerar om. | inte gjord | Ingen spärrlista för import. | ej planerad |
| MK-E17 | Lägga till och ta bort spärrar från gränssnittet. | inte gjord | Ingen spärrlista för import. | ej planerad |
| MK-F01 | Lista mejltrådar för en person, ett bolag eller en affär, nyast först och sidindelat. | delvis | Bolagets och personens tidslinje listar Iris skickade mejl, uppföljningar och svar nyast först (`GET /v1/companies/{id}/timeline` och `/people/{id}/timeline`, `snajp-support/app/api/crm_v1_tidslinje.py`; prövas i `test_bolagets_tidslinje_samlar_crm_leads_och_support`). Saknas: användarens egna mejl, affärer, sidindelning med markör och totalt antal. | 4 |
| MK-F02 | Trådens sammanfattning: ämne, början av senaste meddelandet, tid, antal meddelanden och deltagare, läst eller oläst. | delvis | Varje mejl på tidslinjen bär ämne, utdrag om 280 tecken, tid och länk till konversationen (`app/crm/tidslinje.py:_post`). Saknas: sammanfattning per tråd, antal, deltagare och lästillstånd. | 4 |
| MK-F03 | Tillämpa kanalens synlighet på trådar och meddelanden, så att kollegor bara ser det de får. | delvis | En integrationsnyckel får veta att ett mejl finns men inte vad som skrevs (`med_text=False` i `app/crm/tidslinje.py`; prövas i `test_integrationens_nyckel_far_inga_utdrag_men_appen_far_dem`). Saknas: synlighetsnivåer per brevlåda för kollegor. | ej planerad |
| MK-F04 | Söka bland trådarna på en post med fritext i ämnet. | inte gjord | Tidslinjen har ingen sökning. | 4 |
| MK-F05 | Filtrera postens trådar efter kanal. | inte gjord | Tidslinjen bär källan (crm, iris, support) men API:t filtrerar inte på den. | 4 |
| MK-F06 | Stänga uppmaningen om ett konto som behöver återanslutas. | inte gjord | Ingen kontokoppling i CRM:et. | ej planerad |
| MK-F07 | Lagra trådens koppling till person, bolag och affär, automatisk eller manuell. | inte gjord | Tidslinjen räknar fram kopplingen vid läsning och lagrar ingen; manuella kopplingar finns inte. | 4 |
| MK-F08 | Skicka ett nytt mejl inifrån appen från ett anslutet konto, med kopia, dold kopia, bilagor och målpost. | delvis | Knappen Mejla i postpanelen öppnar användarens eget mejlprogram och är avstängd för Kontakta inte och privatpersoner (`components/crm/app/BolagPanel.tsx`, `PersonPanel.tsx`, `mailto:`). Saknas: att skicka från CRM:et; Snajp skickar i dag bara Iris godkända utkast under Leads. | 4 |
| MK-F09 | Spara det skickade mejlet i kanalen, radera utkast och bilagefiler och koppla tråden till målposten. | inte gjord | Inget skickas från CRM:et. | 4 |
| MK-F10 | Svara i en tråd med korrekta trådhuvuden så att svaret hamnar i samma tråd. | inte gjord | Svar i trådar finns i Leads konversationer, utanför CRM:et. | 4 |
| MK-F11 | Skicka via respektive leverantör (Gmail, Microsoft, SMTP) och avgöra vilka konton som kan skicka. | inte gjord | Snajps utskick går över SMTP eller Resend utanför CRM:et (`app/email_pipeline/sender.py`), inte via användarens egen brevlåda. | 4 |
| MK-F12 | Skapa utkast hos leverantören och skicka det senare. | inte gjord | Snajps utkast lever i Snajp och godkänns av en människa under Leads, inte hos leverantören. | 4 |
| MK-F13 | Skicka från en delad inkorg, med krav på verifierad domän och högst 200 mottagare per dygn. | inte gjord | Ingen delad inkorg i CRM:et. | 5 |
| MK-F14 | Skriva mejl från kommandomenyn och svara från en öppnad tråd. | inte gjord | Kommandopaletten navigerar och söker bolag och personer (`components/crm/app/Kommandopalett.tsx`), men har inget mejlkommando. | 4 |
| MK-F15 | Mejl och kalender finns bara på person, bolag och affär, inte på egna objekt. | delvis | Tidslinjen med mejl finns på bolag och person (`snajp-support/app/api/crm_v1_tidslinje.py`). Saknas: affär. | 4 |
| MK-F17 | Serverns kontroll av mottagare: högst 100 och varje adress giltig. | inte gjord | Inget skickas från CRM:et. | 4 |
| MK-F18 | Skicka via SMTP med kopia i Skickat, och utkast i utkastmappen via IMAP. | inte gjord | Snajp lägger en kopia i kundens Skickat via IMAP (`app/email_pipeline/skickatkopia.py`), utanför CRM:et. | 5 |
| MK-F16 | Skicka mejl som ett steg i ett arbetsflöde. | inte gjord | CRM:et har inga arbetsflöden (se paritet 06). | ej planerad |
| MK-F19 | Räkna ut vilka som ska få svaret (svarsadress, avsändare, egna mottagare). | inte gjord | Inget svar skickas från CRM:et. | 4 |
| MK-F20 | Öppna ett befintligt meddelande, till exempel ett utkast, förifyllt i redigeraren. | inte gjord | Ingen mejlredigerare i CRM:et; utkasten redigeras under Leads. | 4 |
| MK-F21 | Rubrik på tråd och möte i listorna beroende på synlighet. | inte gjord | Ingen mejl- eller kalenderlista i CRM:ets gränssnitt. | 4 |
| MK-F22 | Mata in mottagare som inklistrad text med "Namn <adress>" och markera ogiltiga. | inte gjord | `app/crm/falt.py:epost` tolkar "Namn <adress>" för fältet e-post, men det finns inget mottagarfält. | 4 |
| MK-F23 | Ställa app-kanalens avsändare först när man svarar i en app-tråd. | inte gjord | CRM:et har inga app-kanaler. | ej planerad |
| MK-G01 | Prenumerera på ändringsnotiser hos Google och Microsoft per kanal. | inte gjord | Ingen mejl- eller kalendersynk i CRM:et. | ej planerad |
| MK-G02 | Prenumerationens status per kanal (väntar, aktiv, misslyckad, utgången). | inte gjord | Ingen mejl- eller kalendersynk i CRM:et. | ej planerad |
| MK-G03 | Ta anspråk på att skapa en prenumeration utan dubbletter. | inte gjord | Ingen mejl- eller kalendersynk i CRM:et. | ej planerad |
| MK-G04 | Förnya prenumerationer som går ut inom ett dygn, varje timme. | inte gjord | Ingen mejl- eller kalendersynk i CRM:et. | ej planerad |
| MK-G05 | Felhantering för prenumerationer. | inte gjord | Ingen mejl- eller kalendersynk i CRM:et. | ej planerad |
| MK-G06 | Återkalla prenumerationer vid frånkoppling, ägarbyte eller radering. | inte gjord | Ingen mejl- eller kalendersynk i CRM:et. | ej planerad |
| MK-G07 | Låta prenumerationerna följa arbetsytans aktivering. | inte gjord | Ingen mejl- eller kalendersynk i CRM:et. | ej planerad |
| MK-G08 | En notis från leverantören väcker synken direkt, deduplicerat per kanal. | inte gjord | Ingen mejl- eller kalendersynk i CRM:et. | ej planerad |
| MK-G09 | Låta den schemalagda synken ta över när webhookspåret inte synkat på en timme. | inte gjord | Ingen mejl- eller kalendersynk i CRM:et. | ej planerad |
| MK-G10 | Engångskommando som skapar prenumerationer för redan anslutna konton. | avstår | Gäller bara egen drift av Twenty: ett administrativt kommando vid uppgradering. | |
| MK-G11 | Ta emot och verifiera notiser från Gmail (Pub/Sub) och Google Kalender. | inte gjord | Ingen Google-koppling. | ej planerad |
| MK-G12 | Ta emot och verifiera notiser från Microsoft Graph. | inte gjord | Ingen Microsoft-koppling. | ej planerad |
| MK-G13 | Synk som utlöses av en notis, för mejl och kalender. | inte gjord | Ingen mejl- eller kalendersynk i CRM:et. | ej planerad |
| MK-G14 | Ta emot och verifiera webhookar från utskicksleverantören (Amazon SES, Resend). | inte gjord | Snajp tar emot Resends signerade webhookar för domäner, studs och klagomål (`snajp-support/app/api/sending_domains_api.py`), utanför CRM:et. CRM:ets egna webhooks går ut, inte in. | 4 |
| MK-G15 | Ta emot post till delade inkorgar via leverantörens webhook. | inte gjord | Ingen delad inkorg; Snajps inkorg hämtas med IMAP. | ej planerad |
| MK-G16 | Leveranshändelser för utskick, där hård studs och klagomål spärrar adressen. | inte gjord | Snajp spärrar adressen vid studs och klagomål på leadsutskick (`sending_domains_api.py:webhook_emails`, sändspärrens regel 5e), utanför CRM:et. | 4 |
| MK-G17 | Spara leverantörens paus eller återupptagning av arbetsytans sändning. | inte gjord | Finns inte i Snajp. | ej planerad |
| MK-H01 | Skapa en e-postkanal (delad adress) under inställningarna, i tre steg: ta emot, svara, kampanjer. | inte gjord | Ingen delad inkorg i CRM:et. Snajps supportinkorg kopplas med IMAP i inställningarna, inte genom vidarebefordran. | 5 |
| MK-H02 | En privat vidarebefordringsadress per kanal. | inte gjord | Snajp tar inte emot post genom vidarebefordran. | ej planerad |
| MK-H03 | Ta emot vidarebefordrad post och koppla den till rätt person och bolag. | inte gjord | Snajp tar inte emot post genom vidarebefordran. | ej planerad |
| MK-H04 | Guider för vidarebefordran från Microsoft 365, Google Workspace och andra. | inte gjord | Snajp tar inte emot post genom vidarebefordran. | ej planerad |
| MK-H05 | Lägga till avsändardomän ur e-postkanalens adress, en domän per arbetsyta. | inte gjord | Snajp har avsändardomän per kund (`POST /api/sending-domain`, `snajp-support/app/api/sending_domains_api.py`), utanför CRM:et. | 5 |
| MK-H06 | Visa DNS-posterna (DKIM, SPF, MX, DMARC, avregistreringsvärd) med kopieringsknappar. | inte gjord | Finns inte i CRM:et; avsändardomänen ligger i resten av Snajp. | 5 |
| MK-H07 | Verifiera domänen för hand och automatiskt, med statusarna väntar, verifierad, misslyckad, tillfälligt fel. | inte gjord | Snajp verifierar för hand och via Resends domänwebhook (`POST /api/sending-domain/verify`, `/api/webhooks/resend/domains`), utanför CRM:et. | 5 |
| MK-H08 | Svara från den delade adressen när domänen är verifierad. | inte gjord | Ingen delad inkorg i CRM:et. | 5 |
| MK-H09 | Spärra kampanjer tills både domänen och avregistreringslänken är verifierade. | inte gjord | Inga kampanjer i CRM:et. | 4 |
| MK-H10 | Den delade inkorgen skapas som delat konto och kanal med fasta standardval. | inte gjord | Ingen delad inkorg genom vidarebefordran. | ej planerad |
| MK-H11 | Byta visningsnamn och ta bort en delad inkorg, med städning av avsändardomänen. | inte gjord | Ingen delad inkorg genom vidarebefordran. | ej planerad |
| MK-H12 | Delade inkorgar kräver Enterprise-licens i egen drift med SES. | avstår | Enterprise-fil i förlagan (`email-group-access.service.ts`), och gäller bara egen drift. | |
| MK-H13 | Avsändardomänens tillstånd: domänstatus, leverantörsstatus, avregistreringsvärdens status och status per DNS-post. | inte gjord | Snajps avsändardomän har egen status (`app/sending_domains.py`), utanför CRM:et. | 5 |
| MK-H14 | Registrera, lista, verifiera och ta bort avsändardomän, globalt unik och kontrollerad varje timme. | inte gjord | Snajp skapar, läser och verifierar (`sending_domains_api.py`), utanför CRM:et. | 5 |
| MK-H15 | Föreslå en DMARC-post när domänen saknar en. | inte gjord | Finns inte i CRM:et. | 5 |
| MK-H16 | Avregistreringsvärd på kundens egen domän (links.domän) med certifikat. | avstår | Enterprise-fil i förlagan (`unsubscribe-hostname.service.ts`). Snajps avregistreringssida ligger på Snajps egen domän (`/avregistrera/[token]`). | |
| MK-H17 | Leverantörsdrivrutiner för utskick med begripliga felbesked. | inte gjord | Snajp använder Resend för avsändardomäner (`app/sending_domains.py`), utanför CRM:et. | 5 |
| MK-H19 | Amazon SES-drivrutinens DNS-poster, märkning och felklasser. | avstår | Ersätts av Resend, som Snajp redan använder (`snajp-support/app/sending_domains.py`). | |
| MK-H20 | Resend-drivrutinens statusöversättning och sändningsberedskap. | inte gjord | Snajps Resend-koppling (`app/sending_domains.py`) ligger utanför CRM:et. | 5 |
| MK-H21 | Vidarebefordringsadressens form och källor för inkommande post. | inte gjord | Snajp tar inte emot post genom vidarebefordran. | ej planerad |
| MK-H18 | Kräva en verifierad avsändardomän för att skicka från en adress. | inte gjord | Finns inte i CRM:et; avsändardomänen ligger i resten av Snajp. | 5 |
| MK-I01 | Kampanjfunktionen slås på per arbetsyta och kräver behörighet för att skicka. | inte gjord | Kampanjer finns under Leads (`snajp-support/app/api/leads_kampanjer.py`, LU-160), inte i CRM:et. | 4 |
| MK-I02 | Bygga en mottagarlista med medlemmar, även från personens fält. | inte gjord | Listor finns under Leads, och CRM-kundlistan kan vara en kampanjs mottagare (`leads_kampanjer.py`), men listor byggs inte i CRM:et. | 4 |
| MK-I03 | Skapa en kampanj med namn, avsändare, lista, ämne och automatiskt sparat utkast. | inte gjord | Under Leads (`POST /api/leads/kampanjer`, LU-160). | 4 |
| MK-I04 | Skriva kampanjmejlet i en blockredigerare med kolumner, knappar, bilder och egen HTML. | inte gjord | Snajps kampanjer är ren text med en hälsning (`leads_kampanjer.py`); ingen blockredigerare. | ej planerad |
| MK-I05 | Personalisera med variabler ur personens fält i ämne, text och länkar. | inte gjord | Snajps kampanj sätter bara "Hej {förnamn}," (`leads_kampanjer.py`), under Leads. | 4 |
| MK-I06 | Skicka testmejl till valfri mottagare. | inte gjord | Finns inte i CRM:et. | 4 |
| MK-I07 | Skicka nu eller schemalägga, med en sammanfattning av vilka som hoppas över och varför. | inte gjord | Snajps kampanjer skickas efter godkännande under Leads (`POST /api/leads/kampanjer/{id}/skicka-jobb`, LU-162). | 4 |
| MK-I08 | Kontrollera kampanjen igen när den schemalagda tiden är inne. | inte gjord | Inga kampanjer i CRM:et. | 4 |
| MK-I09 | Kampanjstatus: utkast, schemalagd, skickas, skickad, skickad med fel, avbruten. | inte gjord | Kampanjens förlopp räknas under Leads (`storage.kampanjens_poster`, LU-161). | 4 |
| MK-I10 | Avbryta en schemalagd eller pågående kampanj. | inte gjord | Inga kampanjer i CRM:et. | 4 |
| MK-I11 | Duplicera en kampanj till ett nytt utkast. | inte gjord | Inga kampanjer i CRM:et. | 4 |
| MK-I12 | Resultat per kampanj: skickade, levererade, studsade, klagomål, misslyckade, överhoppade. | inte gjord | Utfall per kampanj räknas under Leads (`GET /api/leads/kampanjer`, LU-161). | 4 |
| MK-I13 | Högst 1 000 kampanjmejl per dag och arbetsyta. | inte gjord | Snajps sändspärr har egna volymgränser per kund (`app/leads/scheduler.py:_kundens_volym`), utanför CRM:et. | 4 |
| MK-I14 | Ett mejl per person även om personen står två gånger i listan. | inte gjord | Inga kampanjer i CRM:et. | 4 |
| MK-I15 | Hoppa över den som studsat, klagat eller avregistrerat sig i senare utskick. | delvis | Kontakta inte på bolag och person i CRM:et läggs till sändspärrens spärrlista och gäller också kampanjutskick (`app/crm/lagring.py:kontakta_inte_adresser`, `app/leads/scheduler.py`; prövas i `test_kontakta_inte_i_crm_stoppar_leadet_och_sparrar_adressen`, `snajp-support/tests/crm/test_utfall_kundlista.py`). Saknas i CRM:et: studs, klagomål och avregistrering, som Snajps spärrlista under Leads håller (`storage.add_suppression`). | 4 |
| MK-I16 | Avregistreringslänk och en-klicks-avregistrering i varje kampanj. | inte gjord | Varje Snajp-utskick bär en avregistreringslänk och lagstadgad fot (`app/leads/utskicksfot.py`, LU-140), utanför CRM:et. | 4 |
| MK-I17 | Avregistreringsämnen, publika eller privata, som mottagaren kan välja bort. | inte gjord | Snajps avregistrering gäller allt; inga ämnen. | ej planerad |
| MK-I18 | Avregistreringssidan med en knapp, eller kryssrutor per ämne, och återprenumeration. | inte gjord | Snajps publika sida `/avregistrera/[token]` (`app/avregistrera/[token]/page.tsx`, LU-141) ligger utanför CRM:et och saknar ämnen och återprenumeration. | 5 |
| MK-I19 | En kampanj med ämne hoppar bara över dem som lämnat ämnet eller allt. | inte gjord | Inga avregistreringsämnen. | ej planerad |
| MK-I20 | Lista avregistrerade med omfattning, skäl och datum, med sök och filter. | inte gjord | Finns inte i CRM:et. | 4 |
| MK-I21 | AI-assistenten bygger lista och kampanjutkast men kan aldrig skicka. | inte gjord | Iris skriver utkast som en människa godkänner, under Leads (leadsregel 17), inte i CRM:et. | 4 |
| MK-I23 | Kampanjens fält och räknare (skickade, levererade, klick, öppningar med flera). | inte gjord | Kampanjer under Leads har namn, ämne, text och utfall (`leads_kampanjer.py`); inget i CRM:et. | 4 |
| MK-I24 | Lista och listmedlem som egna objekt. | inte gjord | Listor finns under Leads, inte som CRM-objekt. | 4 |
| MK-I25 | Avregistrera sig genom att mejla en särskild adress med token. | inte gjord | Snajp spärrar den som svarar att den inte vill bli kontaktad (`storage.add_suppression`, LU-119), utanför CRM:et. | 4 |
| MK-I26 | Signerad avregistreringstoken som gäller två år, en-klicks-POST och anropsgräns. | inte gjord | Snajps token och sida (`public.avregistrera_via_token`, LU-141, LU-182) ligger utanför CRM:et. | 5 |
| MK-I27 | Mottagaren kan välja bort spårning av öppningar och klick. | inte gjord | Snajp spårar ingen öppning; demolänkens klick registreras utan ett sådant val. | ej planerad |
| MK-I28 | Spärrposter med skäl och källa, där studs och klagomål aldrig kan tas bort. | inte gjord | Snajps spärrlista (`storage.add_suppression`, LU-142) ligger under Leads, utan vy i CRM:et. | 4 |
| MK-I29 | Hantera avregistreringsämnen via API. | inte gjord | Inga avregistreringsämnen. | ej planerad |
| MK-I30 | Förhandsvisa mottagarna och hindren före sändning (utan e-post, spärrade, dubbletter). | inte gjord | Sändspärrens skäl visas per utkast under Leads (LU-055, LU-057), inte i CRM:et. | 4 |
| MK-I31 | Villkoren för att en kampanj ska kunna skickas, med ett felmeddelande per brist. | inte gjord | Inga kampanjer i CRM:et. | 4 |
| MK-I32 | Plan- och kreditvillkor för sändning, och pris per tusen mejl. | inte gjord | Twentys molnfakturering; Snajp tar inte betalt per mejl. | ej planerad |
| MK-I33 | En leveransrad per mottagare med tillstånd, skäl och tidpunkter. | inte gjord | Varje utskick är ett eget utkast i Leads; inget i CRM:et. | 4 |
| MK-I34 | Sändning i satser om 50 med anspråk, omförsök och återhämtning. | inte gjord | Inga kampanjer i CRM:et. | 4 |
| MK-I35 | Slutstatus skickad eller skickad med fel, och avbrott som hoppar över resten. | inte gjord | Inga kampanjer i CRM:et. | 4 |
| MK-I36 | Statistik per kampanj med öppnings- och klickfrekvens, avstämd varje timme. | inte gjord | Inga kampanjer i CRM:et. | 4 |
| MK-I37 | Spåra klick och öppningar och sortera bort skannrar och botar. | inte gjord | Snajp spårar demolänkens klick och besök och märker skannrar (`app/prova/[token]/route.ts`, BESLUT 2026-11-15), utanför CRM:et; öppningar spåras inte. | 4 |
| MK-I38 | Skriva om varje mottagares mejl med spårlänkar och spårpixel före sändning. | avstår | Enterprise-fil i förlagan (`campaign-tracking-content.service.ts`). | |
| MK-I39 | Validera personaliseringsvariabler och fylla dem per mottagare. | inte gjord | Inga kampanjer i CRM:et. | 4 |
| MK-I40 | Lägga till upp till 50 000 personer i en lista som bakgrundsjobb. | inte gjord | CRM:et har markering av flera rader (`components/crm/app/BolagVy.tsx`, `PersonerVy.tsx`) men ingen åtgärd som lägger dem i en lista. | 4 |
| MK-I41 | Duplicera en lista med medlemmar. | inte gjord | Inga listor i CRM:et. | 4 |
| MK-I42 | Testmejl via API och AI-verktyg för kampanjer. | inte gjord | Inga kampanjer i CRM:et. | 4 |
| MK-I43 | Behörigheter för att läsa, skriva och skicka kampanjer. | inte gjord | CRM:ets nycklar har omfången läsa, skriva, synka och administrera (`app/crm/nycklar.py`), inget för utskick. | 5 |
| MK-I44 | Hastighets- och dagsgränser för all e-postsändning. | inte gjord | Snajps sändspärr har volymgränser per kund (`app/leads/scheduler.py`), utanför CRM:et. | 4 |
| MK-I45 | Testmejlets indata och kontroller. | inte gjord | Inga kampanjer i CRM:et. | 4 |
| MK-I46 | Kampanjens bakgrundsjobb med omförsök och återhämtning. | inte gjord | Inga kampanjer i CRM:et. | 4 |
| MK-I22 | Leveransråd i produkten (klagomål, studs, uppvärmning av ny domän). | inte gjord | Finns inte i CRM:et. | ej planerad |
| MK-I47 | Spara kampanjutkast, bara i status utkast och med kontroll av variablerna. | inte gjord | Inga kampanjer i CRM:et. | 4 |
| MK-I48 | Serverns kontroller vid skicka nu eller schemaläggning, med skydd mot ändrat antal mottagare. | inte gjord | Inga kampanjer i CRM:et. | 4 |
| MK-I49 | Huvudena List-Unsubscribe och en-klicks-avregistrering och en avregistreringsrad i varje mejl. | inte gjord | Snajps utskick bär avregistreringsfot (`app/leads/utskicksfot.py`), utanför CRM:et. | 4 |
| MK-I50 | Leverantörens paus slår igenom på arbetsytans avsändardomäner. | inte gjord | Finns inte i Snajp. | ej planerad |
| MK-I51 | Städa avsändardomänerna hos leverantören när arbetsytan raderas. | inte gjord | Finns inte i CRM:et. | 5 |
| MK-I52 | Föreslå sändningstid en timme fram, avrundat till halvtimme. | inte gjord | Inga kampanjer i CRM:et. | 4 |
| MK-J01 | Samtalsinspelning som eget objekt med status, filer, transkription och sammanfattning. | inte gjord | Inga inspelningar. Samtal loggas som aktivitet med utfall (`app/crm/objekt.py`), utan inspelning. | ej planerad |
| MK-J02 | Inspelningar skapas av appar, som stämplas på dem. | inte gjord | CRM:et har inga appar från tredje part. | ej planerad |
| MK-J03 | Hitta inspelningen för ett möte och visa den i kalenderlistan. | inte gjord | Inga inspelningar och ingen kalenderlista. | ej planerad |
| MK-J04 | Hämta de senaste 100 mejlen direkt vid anslutning så att användaren ser något genast. | inte gjord | Snajps inkorg har en tillbakablick vid första synken (`imap_tillbakablick_dagar` i `snajp-support/app/config.py`, BESLUT 2026-11-23), utanför CRM:et. | 5 |
| MK-J05 | Föreslå kollegor att bjuda in utifrån gemensamma möten i kalendern. | inte gjord | Ingen kalendersynk. | ej planerad |
| MK-K01 | Systemets egen e-postsändning med köade omförsök. | avstår | Ersätts av Snajps gemensamma sändning av transaktionsmejl (`lib/mail.ts:skickaTransaktionsmail`), som CRM:et delar inloggning med. | |
| MK-K02 | Gemensam layout för transaktionsmejl, översatt till drygt 30 språk med mottagarens språk per mejl. | inte gjord | Snajps transaktionsmejl (`lib/mail.ts`) hör till inloggning och inställningar utanför CRM:et. | 5 |
| MK-K03 | Inbjudan till arbetsytan med knapp för att acceptera. | inte gjord | Teaminbjudningar finns i Snajps inställningar (`lib/actions/team.ts`), inte i CRM:et. | 5 |
| MK-K04 | Verifiera e-postadressen vid registrering och vid byte, med begränsning av antal förfrågningar. | inte gjord | Hör till Snajps registrering och kontoinställningar utanför CRM:et. | 5 |
| MK-K05 | Mejl för att återställa eller sätta lösenord. | avstår | Ersätts av Snajps inloggning, som CRM:et delar (`lib/reset-token.ts`, `lib/mail.ts`). | |
| MK-K06 | Avisering när lösenordet ändrats. | inte gjord | Hör till Snajps kontoinställningar utanför CRM:et. | 5 |
| MK-K07 | Mejl för att validera en godkänd åtkomstdomän. | inte gjord | Snajp har ingen automatisk anslutning på domän. | ej planerad |
| MK-K08 | Varning om pausad arbetsyta och besked om raderad. | inte gjord | Finns inte i Snajp. | ej planerad |
| MK-K09 | Faktureringsaviseringar om förnyelse och provperiod. | inte gjord | Finns inte i CRM:et; CRM:ets provperiod styrs av tillägget (`app/crm/tillgang.py`) utan mejl. | ej planerad |
| MK-K10 | Säkerhetsaviseringar för tvåstegsverifiering. | inte gjord | Snajp har tvåstegsverifiering (BESLUT, migration 140), men aviseringarna hör till inloggningen utanför CRM:et. | 5 |
| MK-K11 | Avisering när serveradministratörens behörighet ändrats. | avstår | Gäller bara egen drift av Twenty: serveradministration av den egna installationen. | |
| MK-K12 | Testmejl för serverns e-postinställning. | avstår | Gäller bara egen drift av Twenty. | |
| MK-K13 | Avsändare, verifieringskrav och inbjudningsgränser för systemmejl som serverinställningar. | avstår | Gäller bara egen drift av Twenty: serverinställningar. | |
| MK-L01 | Kontolistan i inställningarna med leverantör, adress, status och tomt läge med tre anslutningsknappar. | inte gjord | CRM:et har inga inställningssidor för konton; Snajps inkorgar listas i inställningarna utanför CRM:et. | 5 |
| MK-L02 | Sammanvägd synkstatus per konto i listan, uppdaterad live. | inte gjord | Finns inte i CRM:et. | 5 |
| MK-L03 | Radmeny per konto: slutför, inställningar, återanslut, koppla från, radera. | inte gjord | Finns inte i CRM:et. | 5 |
| MK-L04 | Konfigurationsguide i steg efter OAuth. | inte gjord | Ingen OAuth-anslutning. | ej planerad |
| MK-L05 | Mejlinställningar per kanal: synlighet, kontaktskapelse, uteslutningar, paus och mappar. | inte gjord | Inga mejlkanaler i CRM:et. | ej planerad |
| MK-L06 | Mappträd med sök, markera alla och delvis markerat läge. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-L07 | Kalenderinställningar per kanal. | inte gjord | Ingen kalendersynk i CRM:et. | ej planerad |
| MK-L08 | Formulär för IMAP, SMTP och CalDAV, där lösenordet behålls om fältet lämnas tomt. | inte gjord | Snajps formulär för att koppla inkorg (IN-074) ligger utanför CRM:et; CalDAV saknas. | 5 |
| MK-L09 | Personlig spärrlista i kontoinställningarna. | inte gjord | Ingen spärrlista för import. | ej planerad |
| MK-L10 | Inställningar för kommunikation på arbetsytenivå: e-postkanaler, interna mejl, spärrlista, spårning, avregistrering. | inte gjord | Finns inte i CRM:et. | 5 |
| MK-L11 | Detaljsida för en e-postkanal med vidarebefordringsadress, avsändarnamn och DNS-poster. | inte gjord | Finns inte i CRM:et; avsändardomänen ligger i resten av Snajp. | 5 |
| MK-L12 | Avregistreringsinställningar: spärrade adresser, ämnen och förhandsvisning av sidan. | inte gjord | Finns inte i CRM:et. | 4 |
| MK-L13 | Appinställningar på kontosidan för appar som använder kontot. | inte gjord | CRM:et har inga appar från tredje part. | ej planerad |
| MK-L14 | Avsändarval vid skrivande, med markering av konton som saknar behörighet att skicka. | inte gjord | Inget skickas från CRM:et. | 4 |
| MK-M01 | Mejlfliken på en post med trådlista, förhandsvisning, lad-, fel- och tomlägen och kanalfilter. | inte gjord | Postpanelens historik visar bara CRM:ets egna ändringar (`components/crm/app/Historik.tsx`); tidslinjen med Iris mejl finns i API:t men inte i gränssnittet. | 3 |
| MK-M02 | Öppna en tråd i sidopanelen med alla meddelanden, bilagor och hopfälld citathistorik. | inte gjord | Trådar läses i Leads konversationer, inte i CRM:et. | 4 |
| MK-M03 | Länka befintliga mejltrådar manuellt till en post. | inte gjord | Inga manuella trådkopplingar. | ej planerad |
| MK-M04 | Skriva mejl från en post med standardmottagare, avsändarval, mottagarchips, förslag och högst 100 mottagare. | delvis | Knappen Mejla i bolagets och personens panel öppnar användarens mejlprogram till postens adress (`components/crm/app/BolagPanel.tsx`, `PersonPanel.tsx`); syns på `docs/crm/bilder/app/bolag-panel-1440.png`. Saknas: redigerare, avsändarval, mottagarfält och sändning från CRM:et. | 4 |
| MK-M05 | Ladda upp bilagor och bilder till mejl, med storleksgräns och fel per fil. | delvis | CRM:et tar emot bilagor på poster med gräns för storlek, typ och kvot (`app/crm/objekt.py`; prövas i `test_bilagans_storlek_typ_och_kvot`, `snajp-support/tests/crm/test_objekt_ovriga.py`). Saknas: bilagor i mejl och uppladdning i gränssnittet. | 4 |
| MK-M06 | Svara i en tråd med rätt konto, och öppna användarens mejlprogram som reserv. | inte gjord | Inga trådar i CRM:et. Mejla-knappen öppnar mejlprogrammet men inte som svar i en tråd. | 4 |
| MK-M07 | Chattrådar från app-kanaler med reaktioner, bilagor och live-uppdatering. | inte gjord | CRM:et har inga app-kanaler. | ej planerad |
| MK-M08 | Kalenderfliken på en post, grupperad per månad och dag med deltagare och tomt läge. | inte gjord | Ingen kalenderflik; loggade möten (aktiviteter) visas inte heller i gränssnittet än. | 3 |
| MK-M09 | Länka befintliga kalenderhändelser manuellt till en post. | inte gjord | Ingen kalendersynk. | ej planerad |
| MK-M10 | Skapa kalenderhändelse från en post i gränssnittet, med gäster, upprepning och förhandskrav. | inte gjord | Ingen kalenderbokning; ett möte kan bara loggas i efterhand via API:t. | ej planerad |
| MK-M11 | Kampanjredigeraren med avsändare, lista, ämne, blocktext och variabelväljare. | inte gjord | Inga kampanjer i CRM:et; kampanjer skapas under Leads. | 4 |
| MK-M13 | Två redigerarprofiler, en för kampanjer och en för vanliga mejl. | inte gjord | Ingen mejlredigerare i CRM:et. | ej planerad |
| MK-M12 | Knappar och besked för att skicka, schemalägga, boka om, avbryta och testa en kampanj. | inte gjord | Inga kampanjer i CRM:et. | 4 |
| MK-M14 | Standardtider i händelseredigeraren (nästa halvtimme, 60 minuter, heldag). | inte gjord | Ingen kalenderbokning. | ej planerad |
| MK-M15 | Standardslut för upprepning (tionde förekomsten eller tio gånger). | inte gjord | Ingen kalenderbokning. | ej planerad |
| MK-M16 | Vilka konton som kan skapa händelser, och när en händelse räknas som passerad. | inte gjord | Ingen kalenderbokning. | ej planerad |
| MK-M17 | Gruppera chattmeddelanden per avsändare och dag. | inte gjord | CRM:et har inga app-kanaler. | ej planerad |
| MK-N01 | En app kan registrera en egen meddelandeleverantör med sänd- och läst-funktioner. | inte gjord | CRM:et har inga appar från tredje part. | ej planerad |
| MK-N02 | Skicka och markera som läst genom appens funktioner, med översatta fel. | inte gjord | CRM:et har inga appar från tredje part. | ej planerad |
| MK-N03 | Synlighet måste anges när en app skapar en kanal. | inte gjord | CRM:et har inga appar från tredje part. | ej planerad |
| MK-N04 | Riktning, dubbletter och trådning för app-meddelanden. | inte gjord | CRM:et har inga appar från tredje part. | ej planerad |
| MK-N05 | Mappar för app-kanaler. | inte gjord | CRM:et har inga appar från tredje part. | ej planerad |
| MK-N06 | Markera tråd som läst hos leverantören när ägaren öppnar den. | inte gjord | CRM:et har inga appar från tredje part. | ej planerad |
| MK-N07 | Svar med upp till 20 bilagor i en app-kanal. | inte gjord | CRM:et har inga appar från tredje part. | ej planerad |
| MK-N08 | Åtkomst, pausning och avveckling av app-kanaler. | inte gjord | CRM:et har inga appar från tredje part. | ej planerad |
| MK-O01 | Uppräkningen av kontoleverantörer (sju värden). | inte gjord | Ingen kontokoppling i CRM:et. | ej planerad |
| MK-O02 | Uppräkningen av mejlkanaltyper (fyra värden). | inte gjord | Inga mejlkanaler i CRM:et. | ej planerad |
| MK-O03 | Synlighetsnivåerna för mejl- och kalenderkanal. | inte gjord | Inga kanaler i CRM:et. | ej planerad |
| MK-O04 | Policyerna för automatisk kontaktskapelse ur mejl och kalender. | inte gjord | Ingen automatisk kontaktskapelse. | ej planerad |
| MK-O05 | Mappolicyn: alla eller valda mappar. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-O06 | Väntande åtgärder för gruppmejl och mappar. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-O07 | Synkstadierna för mejl och kalender (åtta var). | inte gjord | Ingen mejl- eller kalendersynk i CRM:et. | ej planerad |
| MK-O08 | Synkstatusarna för mejl och kalender (fem). | inte gjord | Ingen mejl- eller kalendersynk i CRM:et. | ej planerad |
| MK-O09 | Deltagarrollerna i mejl (från, till, kopia, dold kopia, svarsadress). | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-O10 | Svarsstatus för mötesdeltagare (fyra). | inte gjord | Ingen kalendersynk i CRM:et. | ej planerad |
| MK-O11 | Webhookprenumerationens status och kanaltyp. | inte gjord | Ingen mejl- eller kalendersynk i CRM:et. | ej planerad |
| MK-O12 | E-postoperationerna skicka och utkast per leverantör. | inte gjord | Inget skickas från CRM:et. | 4 |
| MK-O13 | Anslutningssäkerhet för IMAP och SMTP (ingen, STARTTLS, SSL/TLS). | inte gjord | Snajps inkorgskoppling ligger utanför CRM:et. | 5 |
| MK-O14 | De fem standardmapparna. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-O15 | Gmail-etiketterna som utesluts (sju). | inte gjord | Ingen Gmail-koppling. | ej planerad |
| MK-O16 | Gruppadressmönstren (fyra noreply-varianter och femton prefix). | inte gjord | Snajps inkorgsklassning känner igen maskinadresser (`app/email_pipeline/klassning.py`), utanför CRM:et. | 5 |
| MK-O17 | Massutskickshuvudena (List-Unsubscribe, List-Id, Precedence, Auto-Submitted). | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-O18 | Bilagorna som inte importeras (fem). | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-O19 | Leverantörernas skräppostdomar (tre huvuden). | inte gjord | Ingen delad inkorg genom vidarebefordran. | ej planerad |
| MK-O20 | Kampanjstatusarna (sex). | inte gjord | Inga kampanjer i CRM:et. | 4 |
| MK-O21 | Leveranstillstånden (fem). | inte gjord | Inga kampanjer i CRM:et. | 4 |
| MK-O22 | Skälen för överhoppad leverans (tre). | inte gjord | Inga kampanjer i CRM:et. | 4 |
| MK-O23 | Skälen för misslyckad leverans (tolv). | inte gjord | Inga kampanjer i CRM:et. | 4 |
| MK-O24 | Leverantörsutfallen (levererad, mjuk och hård studs, klagomål, avvisad, renderingsfel). | inte gjord | Snajp tar emot studs och klagomål från Resend (`sending_domains_api.py`), utanför CRM:et. | 4 |
| MK-O25 | Spärrskälen, källorna och de hårda skälen. | inte gjord | Snajps spärrlista ligger under Leads. | 4 |
| MK-O26 | Avregistreringsämnets synlighet, publik eller privat. | inte gjord | Inga avregistreringsämnen. | ej planerad |
| MK-O27 | Avsändardomänens statusar och DNS-posttyperna. | inte gjord | Snajps avsändardomän ligger utanför CRM:et. | 5 |
| MK-O28 | Utskicksdrivrutinerna, sändningsslagen och drivrutinerna för systemmejl. | inte gjord | Snajp använder Resend och SMTP utanför CRM:et. | 5 |
| MK-O29 | Samtalsinspelningens statusar. | inte gjord | Inga inspelningar. | ej planerad |
| MK-O30 | Frekvenser och veckodagar för återkommande händelser. | inte gjord | Ingen kalenderbokning. | ej planerad |
| MK-O31 | Felkoderna för e-postverifiering (åtta). | inte gjord | Hör till Snajps registrering utanför CRM:et. | 5 |
| MK-O32 | Transaktionsmejlens mallar (sjutton). | inte gjord | Snajps transaktionsmejl (`lib/mail.ts`) ligger utanför CRM:et. | 5 |
| MK-O33 | De schemalagda jobben i området (tretton). | inte gjord | Ingen mejl- eller kalendersynk och inga kampanjer i CRM:et. | ej planerad |
| MK-O34 | Funktionsflaggorna som rör området (sex). | inte gjord | Ingen mejl- eller kalendersynk i CRM:et. | ej planerad |
| MK-O35 | Serverinställningarna för området (48). | avstår | Gäller bara egen drift av Twenty. | |
| MK-O36 | Felkoderna för utskick och avsändardomäner (femton). | inte gjord | Inga kampanjer eller avsändardomäner i CRM:et; CRM:ets felkoder (`lib/crm/felkoder.ts`) rör annat. | 4 |
| MK-O37 | Felklasserna och nätverkskoderna i mejlsynkens drivrutiner. | inte gjord | Ingen mejlsynk i CRM:et. | ej planerad |
| MK-O38 | Felklasserna i kalendersynkens drivrutiner. | inte gjord | Ingen kalendersynk i CRM:et. | ej planerad |
| MK-O39 | De permanenta autentiseringsfelen hos Google och Microsoft. | inte gjord | Ingen OAuth-anslutning. | ej planerad |
| MK-O40 | Felklasserna vid skapande av kalenderhändelse. | inte gjord | Ingen kalenderbokning. | ej planerad |
| MK-O41 | Återanslutningslistorna per användare (två). | inte gjord | Ingen kontokoppling i CRM:et. | ej planerad |
| MK-O42 | Språken för transaktionsmejl (34). | inte gjord | Snajp är svenska och engelska (`lib/i18n.tsx`); transaktionsmejlen ligger utanför CRM:et. | 5 |
| MK-O43 | IMAP-serversvar som räknas som tillfälliga vid inloggning. | inte gjord | Snajps IMAP-koppling ligger utanför CRM:et. | 5 |
