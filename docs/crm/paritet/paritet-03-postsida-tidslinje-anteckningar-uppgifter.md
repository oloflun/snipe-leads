# Paritet 03: Postsida, tidslinje, anteckningar och uppgifter

Området är allt som händer när en användare öppnar en enskild post i Twenty: postsidan och sidopanelen, sidlayouten med flikar och widgetar, fältcellerna per fälttyp, relationskort, sammanslagning, tidslinjen, anteckningar, uppgifter, filer, e-post och kalender på posten. I Snajp CRM öppnas bolag och personer i en fast panel från höger (`BolagPanel.tsx`, `PersonPanel.tsx`), och anteckningar, uppgifter, aktiviteter och bilagor finns än så länge bara i API:t (`app/crm/objekt.py`, `app/api/crm_v1_objekt.py`).

241 rader (213 funktioner PS-001 till PS-213 och 28 uppräkningar U-01 till U-28): verifierad 18, byggd 4, delvis 83, inte gjord 125, avstår 11.

## De största luckorna

1. **Anteckningar, uppgifter och filer syns inte på posten.** De finns i API:t med tester, men panelen har inga flikar för dem, och det går inte att skapa en anteckning, bocka av en uppgift eller ladda upp en fil från bolaget eller personen.
2. **Den samlade tidslinjen når inte panelen.** API:t komponerar leads, mejl, samtal och supportärenden på bolaget och personen, men panelens Historik visar bara postens egna ändringar. CRM:ets egna anteckningar, uppgifter, aktiviteter och affärer kommer inte med i tidslinjen alls.
3. **Ingen redigering direkt i fältet.** Varje ändring går genom en dialog. Namnet i rubriken, ett datum eller ett val går inte att ändra på plats, och Enter, Esc och Tab fungerar inte som i Twentys fältceller.
4. **Ingen rik text.** Anteckningar är ren text: inga rubriker, listor, checklistor, länkar, bilder eller omnämnanden med "@".
5. **Ingen helsida för en post.** Posten öppnas bara i panelen, utan brödsmula, bläddring till nästa post, flik i adressen eller posten i webbläsarflikens titel.
6. **Historiken visar inte värdena.** Den säger vilka fält som ändrades men inte från vad till vad, med flit, och den varken grupperas per månad eller går att filtrera.
7. **Ingen sammanslagning av dubbletter.** Dubblettskyddet stoppar nya dubbletter vid skapande och synk, men två befintliga poster går inte att slå ihop.
8. **Relationer går inte att hantera från posten.** Bolagets personer listas, men det går inte att lägga till, koppla loss eller skapa en person därifrån, och en anteckning kan bara peka på ett bolag, en person och en affär.
9. **Ingen e-post eller kalender på posten.** Mejlen bor i Leads konversationer och når posten bara via tidslinjen i API:t; Mejla öppnar en mailto-länk.
10. **Ingen anpassning av postsidan.** Flikar, widgetar och fältgrupper är fasta i koden; Twentys hela layoutredigering finns inte och är inte planerad.

## Rad för rad

| ID | Funktion | Läge | Var i Snajp, eller varför inte | Fas |
|---|---|---|---|---|
| PS-001 | En post kan öppnas som en egen helsida på en egen adress. | delvis | Adressen `?bolag=<id>` öppnar posten i panelen över listan (`BolagVy.tsx`, `PersonerVy.tsx`). Saknas: en helsida och sidan "ej tillgänglig" för en post som inte finns. | 3 |
| PS-002 | Arbetsflöden och AI-chattrådar har egna specialsidor i stället för den vanliga postsidan. | inte gjord | Snajp CRM har varken arbetsflöden eller AI-chattrådar som objekt. | ej planerad |
| PS-003 | Webbläsarfliken visar postens namn och objektets namn. | inte gjord | Titeln är alltid "Snajp CRM" (`app/crm/layout.tsx`). | 3 |
| PS-004 | Brödsmulan visar objektet, postens namn och var i listan posten ligger (3/120). | inte gjord | Panelen har ingen brödsmula eller position. | 3 |
| PS-005 | Bläddra till föregående och nästa post i den lista man kom ifrån. | inte gjord | Finns inte i panelen. | 3 |
| PS-006 | Gå tillbaka från posten till listan, med den senast visade posten markerad. | delvis | Panelen stängs och listan ligger kvar bakom med raden markerad (`BolagPanel.tsx`, `Drawer hasScrim={false}`, bild `docs/crm/bilder/app/bolag-panel-1440.png`). Saknas: att listan scrollar till posten efter en omladdning. | 3 |
| PS-007 | Postens huvud visar avatar eller logotyp, namnet och när posten skapades. | delvis | Avatar med initialer och färgton, fyrkantig för bolag och rund för personer, och namnet i rubriken (`BolagPanel.tsx`, `PersonPanel.tsx`, bild `bolag-panel-1440.png`). Saknas: "Skapad för X sedan" i huvudet; skapad står som datum i gruppen System. | 3 |
| PS-008 | Klicka på avataren för att ladda upp en ny bild eller logotyp. | inte gjord | Bolag och personer har inget bildfält. | senare |
| PS-009 | Rubriken i sidopanelen länkar till helsidan när namnet inte går att redigera. | inte gjord | Det finns ingen helsida att länka till. | 3 |
| PS-010 | Exportera en enskild post till CSV. | inte gjord | Ingen export till fil i CRM:et. | 3 |
| PS-011 | Postsidan uppdateras direkt när någon annan ändrar posten. | inte gjord | Ingen prenumeration på serverhändelser. Historiken hämtas om bara när posten ändrats i den egna webbläsaren (`Historik.tsx`). | senare |
| PS-012 | En raderad post visas med en banderoll och en knapp för att återställa. | delvis | Raderade poster visas i Papperskorgen med Återställ (`Papperskorg.tsx`). Saknas: att öppna en raderad post och se den med banderoll. | 3 |
| PS-013 | Postsidan har en åtgärdsmeny (favorit, radera, exportera, slå ihop) och knappar i sidfoten. | delvis | Panelen har Redigera i huvudet, snabbvalen Mejla, Ring och Webbplats och Ta bort i foten (`BolagPanel.tsx`, bild `bolag-panel-1440.png`). Saknas: en meny med favorit, export och sammanslagning. | 3 |
| PS-014 | Postsidan byggs av en sidlayout som går att ställa in per objekt. | inte gjord | Panelens innehåll är fast i koden (`BolagPanel.tsx`, `docs/crm/DESIGN-CRM.md` § Postens panel). | ej planerad |
| PS-015 | Fristående sidor byggda med sidlayout, med egen adress och utskrift. | inte gjord | Inga layoutstyrda sidor. | ej planerad |
| PS-016 | Öppna en post i sidopanelen från en lista, ett relationskort eller en sökning. | delvis | Raden i listan, kommandopalettens bolagsträffar, bolagets chip hos en person och personens namn hos ett bolag öppnar posten i panelen (`BolagVy.tsx`, `Kommandopalett.tsx`, `PersonPanel.tsx`, `BolagPanel.tsx`, bild `bolag-panel-1440.png`). Saknas: flik i adressen, och att en ny post öppnas i panelen med namnfältet redo (ny post skapas i en dialog). | 3 |
| PS-017 | På mobil öppnas posten alltid som helsida. | delvis | Samma panel används på mobil med smalare etikettkolumn (`useSmal` i `BolagPanel.tsx`). Saknas: en egen helsida på mobil. | 3 |
| PS-018 | Sidopanelen har en egen historik med Tillbaka och en historikmeny. | delvis | Webbläsarens bakåt följer `?bolag=` eftersom adressen byts utan sidladdning (`BolagVy.tsx`). Saknas: panelens egen stack, Tillbaka-knapp och historikmeny. | 3 |
| PS-019 | Esc och Backsteg går ett steg tillbaka i panelen. | delvis | Esc stänger panelen och dialogerna (Astryx `Drawer`, `onOpenChange` i `BolagPanel.tsx`). Saknas: Backsteg och steg för steg bakåt. | 3 |
| PS-020 | Utvidga sidopanelen till helsida. | inte gjord | Ingen helsida finns. | 3 |
| PS-021 | Ändra sidopanelens bredd genom att dra i kanten, och minnas bredden. | inte gjord | Panelen är fast 520 px (`BolagPanel.tsx`). | senare |
| PS-022 | "Skapa relaterad" från en post: uppgift, anteckning, fil, e-post eller kalenderhändelse. | delvis | API:t skapar uppgift, anteckning, aktivitet och bilaga kopplad till bolag, person eller affär (`crm_v1_objekt.py`: `POST /tasks`, `/notes`, `/activities`, `/attachments`). Saknas: åtgärden i panelen, e-post och kalenderhändelse. | 3 |
| PS-023 | Redigera ett rik text-fält i sidopanelen. | inte gjord | Anteckningar är ren text (`objekt.py`, `_TEXTFALT`), och det finns ingen redigerare i gränssnittet. | 3 |
| PS-024 | "Slå ihop med..." från en post, med sökning efter den andra posten. | inte gjord | Ingen sammanslagning. `docs/crm/SVENSK-STANDARD.md` har inte tagit ställning. | senare |
| PS-025 | Sidopanelen har egna sidor för en post: sammanslagning, mängduppdatering, rik text, formulär, delning, e-post, kalender och inställningar. | delvis | Postpanelen, formulären i dialog (`BolagFormular.tsx`, `PersonFormular.tsx`) och ändring av relation i mängd (`BolagVy.tsx`). Övriga sidor saknas. | 3 |
| PS-026 | Varje objekt har en sidlayout med typ, flikar och standardflik. | inte gjord | Panelernas flikar är fasta i koden. | ej planerad |
| PS-027 | En flik har titel, ikon, position och layoutläge. | inte gjord | Inga inställbara flikar. | ej planerad |
| PS-028 | En widget har titel, typ, konfiguration och villkor för synlighet (26 typer). | inte gjord | Inga widgetar. | ej planerad |
| PS-029 | Widgetar placeras i ett rutnät med tolv kolumner och kontrollerad position. | inte gjord | Inget rutnät på postsidan. | ej planerad |
| PS-030 | Widgetar placeras i en lodrät lista, med höjd efter innehåll eller fyllande. | inte gjord | Inga widgetar. | ej planerad |
| PS-031 | Standard- och minimistorlekar för widgetar i rutnätet. | inte gjord | Inga widgetar. | ej planerad |
| PS-032 | Första fliken kan nålas fast som vänsterkolumn på helsidan. | inte gjord | Ingen helsida och inga inställbara flikar. | ej planerad |
| PS-033 | Vilken flik som öppnas först, och att aktiv flik står i adressen. | delvis | Ett nytt bolag öppnas alltid på Översikt (`BolagPanel.tsx`). Saknas: att minnas senaste flik och flik i adressen. | 3 |
| PS-034 | Flikar som kräver en relation döljs när relationen saknas. | inte gjord | Panelernas flikar är fasta. | ej planerad |
| PS-035 | En widget kan visas eller döljas efter villkor (enhet, posten, funktionsflaggor). | inte gjord | Inga widgetar. | ej planerad |
| PS-036 | En flik med en enda widget visas utan kortram. | inte gjord | Inga widgetar. | ej planerad |
| PS-037 | Flikar förrenderas när musen vilar över dem. | inte gjord | Panelens flikar renderas när de väljs. | ej planerad |
| PS-038 | Varje widget prövar om användaren får läsa objektet och fälten. | inte gjord | CRM:et har ingen behörighet per objekt eller fält, bara nyckelns omfång (`nycklar.py`). | ej planerad |
| PS-039 | Ett enskilt fält kan visas som egen widget i olika visningslägen. | inte gjord | Inga fältwidgetar. | ej planerad |
| PS-040 | Ett relationskort visar de fem första relaterade posterna och "Visa fler". | delvis | Fliken Personer på bolaget visar upp till 100 personer med antalet i fliken (`BolagPanel.tsx`, bild `bolag-panel-1440.png`). Saknas: "Visa fler" och antal i ett widgethuvud. | 3 |
| PS-041 | "Visa alla" leder till den relaterade listan filtrerad på posten. | inte gjord | API:t filtrerar personer på `company_id`, men panelen har ingen länk till en filtrerad lista. | 3 |
| PS-042 | Fältlistan kan visas i grupper eller som en lista, med fält som döljs, flyttas och grupperas. | delvis | Fältlistan står i fasta grupper: Allmänt, Affär, Kontakt och System (`BolagPanel.tsx`, bild `bolag-panel-1440.png`). Saknas: att dölja, flytta och gruppera själv. | ej planerad |
| PS-043 | Relaterade poster visas som tabell eller kanban med egen vy i en widget. | delvis | Bolagets personer visas som en lista i fliken Personer (`BolagPanel.tsx`). Saknas: tabell, kanban och egen vy. | senare |
| PS-044 | Postsidan har widgetar för tidslinje, uppgifter, anteckningar, filer, e-post, kalender, iFrame och rik text. | delvis | Bolagets flik Historik och personens avsnitt Historik visar postens händelser (`Historik.tsx`). Saknas: uppgifter, anteckningar, filer, e-post, kalender, iFrame och rik text i panelen. | 3 |
| PS-045 | Felkoder för layouter i API:t. | inte gjord | Inga layouter i API:t. | ej planerad |
| PS-046 | Att läsa och ändra layouter kräver olika behörighet. | inte gjord | Inga layouter. | ej planerad |
| PS-047 | Återställa en layout, flik eller widget till standard. | inte gjord | Inga layouter. | ej planerad |
| PS-048 | Duplicera layout, flik och widget. | inte gjord | Inga layouter. | ej planerad |
| PS-049 | Spara hela layouten i ett anrop. | inte gjord | Inga layouter. | ej planerad |
| PS-050 | AI-verktyg som kan ändra postsidornas layouter. | inte gjord | Inga layouter och inga AI-agenter i CRM:et. | ej planerad |
| PS-051 | Gå in i ett läge för att anpassa postsidans layout. | inte gjord | Inget anpassningsläge. | ej planerad |
| PS-052 | Anpassningsraden överst med Spara och Avbryt. | inte gjord | Inget anpassningsläge. | ej planerad |
| PS-053 | Avbryt anpassningen och återgå till sparat läge. | inte gjord | Inget anpassningsläge. | ej planerad |
| PS-054 | Spara anpassningen så att den gäller alla poster av objektet. | inte gjord | Inget anpassningsläge. | ej planerad |
| PS-055 | Återställ postsidans layout till standard efter bekräftelse. | inte gjord | Inget anpassningsläge. | ej planerad |
| PS-056 | Lägg till, byt namn på, flytta, duplicera och ta bort flikar. | inte gjord | Panelernas flikar är fasta. | ej planerad |
| PS-057 | Lägg till, flytta, ändra storlek på och ta bort widgetar. | inte gjord | Inga widgetar. | ej planerad |
| PS-058 | Redigera postens namn direkt i rubriken. | delvis | Namnet ändras i dialogen som pennan i huvudet öppnar (`BolagPanel.tsx`, `BolagFormular.tsx`). Saknas: redigering på plats i rubriken. | 3 |
| PS-059 | Fullständigt namn redigeras som förnamn och efternamn, och inklistrat namn delas upp. | delvis | Förnamn och efternamn är två fält i personformuläret (`PersonFormular.tsx`). Saknas: redigering i rubriken och delning av inklistrat namn. | 3 |
| PS-060 | En nyskapad post öppnas med namnfältet redo att skriva i. | delvis | Formuläret för nytt bolag och ny person öppnas med fokus i namnfältet (`BolagFormular.tsx`, `PersonFormular.tsx`). Saknas: att den nya posten öppnas i panelen med rubriken i redigeringsläge. | 3 |
| PS-061 | Gemensamma tangenter i fältinmatningen: Enter sparar, Esc stänger, Tab går till nästa fält. | inte gjord | Fälten redigeras i en dialog, inte i cellen; redigering direkt i cellen är inte byggd. | 3 |
| PS-062 | Fältcellen visar ikon, etikett och värde, och ett tomt fält visar en platshållare. | verifierad | Varje rad har ikon, etikett och värde, tomt värde är "Lägg till" som öppnar redigeringen på fältet, och skelett under laddning (`BolagPanel.tsx`, `PersonPanel.tsx`). Bild: `docs/crm/bilder/app/bolag-panel-1440.png`. | |
| PS-063 | Penna vid hovring för fält med flera värden. | inte gjord | Inga fält med flera värden. | senare |
| PS-064 | E-post, telefon och länk har en andra knapp för att kopiera eller öppna. | delvis | E-post, telefon och webbplats öppnas med mailto, tel och ny flik (`Lankpiller` i `kit.tsx`). Saknas: kopiera som andra åtgärd och val av klickåtgärd per fält. | 3 |
| PS-065 | Alla fält utom namnet kan tömmas. | verifierad | `PATCH` med `null` tömmer ett fält (`crm_v1.py`). Test: `test_andra_och_tom_ett_falt` i `snajp-support/tests/crm/test_api.py`. | |
| PS-066 | Regler för när ett fält eller en post är skrivskyddad. | delvis | En nyckel med läsomfång kan inte skriva, och utan registrerat avtal går det bara att läsa (`nycklar.py`, `tillgang.py`; test `test_en_lasnyckel_laser_men_skriver_inte` i `test_objekt_ovriga.py`, `test_utan_registrerat_avtal_gar_det_att_lasa_men_inte_skriva` i `test_api.py`). Saknas: skrivskydd per fält, per användare och för raderade poster. | senare |
| PS-067 | Fält som användaren inte får läsa visas som spärrade. | inte gjord | Ingen behörighet per fält i CRM:et. | ej planerad |
| PS-068 | Textfält: trimmas när de sparas, och webbadresser i texten blir klickbara. | delvis | Text trimmas och tom text blir tom (`falt.text`). Saknas: klickbara adresser i text och platshållare per fält. | 3 |
| PS-069 | Talfält med decimaler, procent och kort form, formaterat efter användarens talformat. | delvis | Heltal läses i svenskt och engelskt skrivsätt och visas med svensk tusentalsavgränsare (`falt.heltal`, `BolagPanel.tsx`; test `test_heltal_svenska_och_engelska_skrivsatt` i `test_falt_och_adaptrar.py`). Saknas: decimaler, procent och kort form. | senare |
| PS-070 | Beloppsfält med valutakod, kort eller full form och valutaväljare. | delvis | Omsättning i kronor och affärens belopp med valutakod, SEK som standard (`BolagPanel.tsx`, `objekt.py`). Saknas: valutaväljare i gränssnittet och inställbart format. | 3 |
| PS-071 | Datumfält med relativt, användarens eller eget format och kalenderväljare. | delvis | Datum läses i flera skrivsätt och sparas som ISO (`falt.datum`; test `test_datum_blir_iso` i `test_falt_och_adaptrar.py`), visas med `Timestamp` (`BolagPanel.tsx`). Saknas: val av visningsformat per fält. | 3 |
| PS-072 | Fält med datum och tid i användarens tidszon. | delvis | Tidpunkter läses med `falt.tidpunkt` och sparas i UTC (uppgiftens förfallotid, aktivitetens tid i `objekt.py`). Saknas: datum- och tidväljare i gränssnittet. | 3 |
| PS-073 | Ja/nej-fält som växlas med ett klick. | delvis | "Kontakta inte" sätts i formuläret och visas som etikett eller "Får kontaktas" (`BolagFormular.tsx`, `BolagPanel.tsx`). Saknas: växling med ett klick i cellen. | 3 |
| PS-074 | Betygsfält med fem stjärnor. | inte gjord | Inget betygsfält. | senare |
| PS-075 | Enkelvalsfält med färgade etiketter, sökning och nya alternativ från fältet. | delvis | Relationen är ett fast val med färgad etikett (`Relationsetikett` i `kit.tsx`, `Selector` i `BolagFormular.tsx`). Saknas: egna valfält och att lägga till alternativ. | senare |
| PS-076 | Valbara alternativ begränsas efter användarens radnivåbehörighet. | avstår | Enterprise-fil i förlagan. | |
| PS-077 | Flervalsfält med färgade etiketter. | inte gjord | Inga flervalsfält. | senare |
| PS-078 | Fält med flera värden: primärt värde, ytterligare värden och ett tak. | inte gjord | Bolag har en e-post, en telefon och en webbplats; personen har mobil och telefon som två fält. | senare |
| PS-079 | E-postfält med primär och ytterligare adresser. | delvis | En adress per post, kontrollerad och sparad med gemener (`falt.epost`; test `test_epost` i `test_falt_och_adaptrar.py`). Saknas: flera adresser. | senare |
| PS-080 | Telefonfält med landsväljare och kontroll av numret. | delvis | Numret tolkas och sparas som E.164 med Sverige som standard (`falt.telefon`; test `test_telefon_blir_e164` i `test_falt_och_adaptrar.py`). Saknas: landsväljare och flera nummer. | senare |
| PS-081 | Länkfält med etikett, domänkontroll och särskild visning av sociala länkar. | delvis | En webbplats per bolag, normaliserad, med domänen härledd (`falt.webbplats`; test `test_webbplats_och_privata_domaner` i `test_falt_och_adaptrar.py`). Saknas: flera länkar, etiketter och sociala länkar. | senare |
| PS-082 | Listfält med flera textvärden. | inte gjord | Inget listfält. | senare |
| PS-083 | Fullständigt namn där inmatad text delas i förnamn och efternamn. | delvis | Personen har förnamn och efternamn som egna fält (`PersonFormular.tsx`, `crm_v1.py`). Saknas: att en inmatad text delas upp. | 3 |
| PS-084 | Adressfält med delfält, inställbara delfält och standardland. | delvis | Adressen har c/o, gata, postnummer och ort, och postnumret kontrolleras (`BolagPanel.tsx`, `falt.postnr`; test `test_postnummer` i `test_falt_och_adaptrar.py`). Saknas: gata 2, region, land, koordinater och inställbara delfält. | 3 |
| PS-085 | JSON-fält med trädvy och kodruta. | inte gjord | Egna fält (`extra`) tar bara enkla värden. | senare |
| PS-086 | Rik text som fält, redigerad i en blockredigerare. | inte gjord | Ingen rik text; anteckningar är ren text. | 3 |
| PS-087 | Filfält med uppladdning, dra och släpp, namnbyte och ett tak. | delvis | Filer laddas upp som bilagor kopplade till posten, högst 10 MB (`objekt.skapa_bilaga`, `POST /attachments`). Saknas: filfält på posten och uppladdning i gränssnittet. | 3 |
| PS-088 | Filens kategori härleds ur ändelsen och styr ikon och förhandsvisning. | delvis | Ändelsen avgör vilken typ som sparas (`objekt.filtyp`, `TILLATNA_TYPER`). Saknas: kategorier, ikon och förhandsvisning. | 3 |
| PS-089 | Relationsfält: chip som öppnar posten och en sökbar väljare med "Skapa ny". | delvis | Personens bolag visas som chip som öppnar bolaget, och bolaget väljs i en lista i formuläret (`Postchip` i `PersonPanel.tsx`, `Selector` i `PersonFormular.tsx`). Saknas: "Skapa ny" från väljaren. | 3 |
| PS-090 | Relation som kan peka på poster av olika objekt. | delvis | Anteckning, uppgift och aktivitet kan peka på ett bolag, en person och en affär samtidigt (`_KOPPLINGAR` i `objekt.py`). Saknas: en väljare i gränssnittet. | 3 |
| PS-091 | Relationer via ett mellanobjekt som skapas och tas bort automatiskt. | inte gjord | Kopplingarna är kolumner direkt på posten. | ej planerad |
| PS-092 | Fältet "skapad av" visar vem eller vad som skapade posten (tio källor). | delvis | Postens källa (anslutning, API eller Snajp) och händelsernas källa och aktör (`Kallpiller` i `BolagPanel.tsx`, `handelser.KALLOR`, `varifran` i `Historik.tsx`). Saknas: arbetsytemedlem med namn och avatar, och de övriga källorna. | 3 |
| PS-093 | Id visas men redigeras inte, och ordningstal är systemfält. | byggd | Postens id sätts av databasen och kan inte skrivas, och affärens `position` sätts bara av tavlans flytt (`objekt.flytta`, `crm_v1_objekt.py`). | |
| PS-094 | Regler för vad som räknas som ett tomt fält. | verifierad | Saknat värde, tom text och falskt räknas som tomt och visar "Lägg till" (`varde` i `BolagPanel.tsx`). Bild: `docs/crm/bilder/app/bolag-panel-1440.png` (Webbplats och E-post). | |
| PS-095 | Text som klistras in i ett tomt sammansatt fält blir startvärde. | inte gjord | Ingen redigering i cellen. | senare |
| PS-096 | Platshållare som inte lockar fram webbläsarens lösenordshanterare. | inte gjord | Finns inte. | senare |
| PS-097 | Vilka fält som visas i fältlistan och hur relationerna delas upp. | delvis | Fasta fält i fasta grupper (`BolagPanel.tsx`, `PersonPanel.tsx`). Saknas: att alla läsbara fält, också egna fält (`extra`), visas av sig själva. | 3 |
| PS-098 | Relationskortet listar relaterade poster som kan fällas ut. | delvis | Fliken Personer listar bolagets personer med avatar, namn, titel, e-post och telefon, och namnet öppnar personen (`BolagPanel.tsx`). Saknas: att fälla ut en rad. | 3 |
| PS-099 | Lägg till en relaterad post från kortet, befintlig eller ny. | inte gjord | Fliken Personer säger att personer knyts via synken eller API:t (`BolagPanel.tsx`). | 3 |
| PS-100 | Koppla loss eller radera en relaterad post från kortet. | delvis | API:t tömmer personens `company_id` med `PATCH /people/{id}` (`crm_v1.py`). Saknas: åtgärden i kortet. | 3 |
| PS-101 | Postväljare för en post, med sökning och "Lägg till ny". | delvis | Bolaget väljs i en lista i personformuläret (`Selector` i `PersonFormular.tsx`). Saknas: fördröjd sökning, "Inga poster hittades" och "Lägg till ny". | 3 |
| PS-102 | Postväljare för flera poster och flera objekttyper. | inte gjord | Finns inte. | 3 |
| PS-103 | Starta sammanslagning av dubbletter från en lista eller en post. | inte gjord | Ingen sammanslagning. | senare |
| PS-104 | Sammanslagningsvyn med förhandsvisning, en flik per post och inställningar. | inte gjord | Ingen sammanslagning. | senare |
| PS-105 | Välj vilken post som vinner när fälten krockar. | inte gjord | Ingen sammanslagning. Synkens konfliktregel per anslutning gäller källsystemen, inte två poster (`synk.py`). | senare |
| PS-106 | Utför sammanslagningen och öppna den kvarvarande posten. | inte gjord | Ingen sammanslagning. | senare |
| PS-107 | Regler för hur fält och relationer slås ihop. | inte gjord | Ingen sammanslagning. | senare |
| PS-108 | Relaterade poster som skulle bli dubbletter vid flytten raderas i stället. | inte gjord | Ingen sammanslagning. | senare |
| PS-109 | Gränser och fel vid sammanslagning (2 till 9 poster, behörighet, transaktion). | inte gjord | Ingen sammanslagning. | senare |
| PS-110 | Hitta dubbletter efter objektets dubblettkriterier. | delvis | Dubblettskydd när en post skapas eller synkas: bolag på organisationsnummer, entydig domän eller entydigt namn, personer på e-post (`synk.py`; tester `test_tva_kallor_om_samma_bolag_blir_en_post` och `test_utan_orgnr_matchas_bara_pa_entydig_doman_eller_entydigt_namn` i `test_api.py`). Saknas: sökning efter dubbletter bland befintliga poster. | senare |
| PS-111 | Per objekt: öppnas posten i panel, på helsida eller efter användarens val. | avstår | Ersätts av det Snajp redan har: posten öppnas alltid i panelen (`docs/crm/DESIGN-CRM.md` § Postens panel, `BolagPanel.tsx`). | |
| PS-112 | Dela en enskild post med personer eller roller. | avstår | Enterprise-fil i förlagan. | |
| PS-113 | Tidslinjehändelsen som datamodell: tid, typ, ändringar, länkad post och vem som gjorde det. | delvis | Händelseloggen har objekt, post, typ, ändrade fält, källa, aktör och tid (`handelser.py`, migration 162). Saknas: värdena före och efter, och länkad post med cachat namn. | 3 |
| PS-114 | Skapad, ändrad, raderad och återställd loggas på posten, och en ändring bara när något fält faktiskt ändrats. | verifierad | `handelser.logga` från varje skrivväg; oförändrade fält skrivs inte (`objekt._skriv`), och `updated_at` nämns aldrig (`_TYSTA`). Test: `test_varje_skrivning_blir_en_handelse_i_flodet` i `test_handelser_webhooks.py` och `test_affarens_skrivningar_syns_i_flodet_och_historiken` i `test_objekt.py`. | |
| PS-115 | Händelser på relaterade poster ("länkad" och "avlänkad") syns på målposten. | delvis | Bolagets och personens tidslinje komponerar leads, skickade mejl, svar, samtal, statusbyten, anteckningar, uppgifter och supportärenden ur resten av Snajp (`tidslinje.py`; test `test_bolagets_tidslinje_samlar_crm_leads_och_support` i `test_tidslinje.py`). Saknas: CRM:ets egna anteckningar, uppgifter, aktiviteter, affärer och bilagor på posten, och händelserna länkad och avlänkad. | 3 |
| PS-116 | Händelsens tidpunkt tas från källan, till exempel när mejlet togs emot. | byggd | Tidslinjen läses ur källorna vid varje läsning, så mejl får sin sändtid och svar sin mottagningstid (`tidslinje._leads`, `sent_at`). | |
| PS-117 | Ändringar från samma användare inom tio minuter slås ihop till en händelse. | inte gjord | Varje skrivning blir en egen händelse (`handelser.logga`). | senare |
| PS-118 | Händelsetyper kan definieras, slås av och läggas till av appar. | inte gjord | Händelsetyperna är fasta (`handelser.TYPER`, `_TYP_UT` i `crm_v1_tidslinje.py`). | ej planerad |
| PS-119 | Tidslinjen visar bara det användaren får läsa. | delvis | En integrations nyckel får inga utdrag, och prospektet läses med en uttrycklig kolumnlista så att webbplatsbedömningen aldrig följer med (`tidslinje.py`; tester `test_integrationens_nyckel_far_inga_utdrag_men_appen_far_dem` och `test_prospektet_lases_med_en_uttrycklig_kolumnlista` i `test_tidslinje.py`). Saknas: behörighet per fält och per användare. | senare |
| PS-120 | Händelser som länkar till en post rensas när posten raderas permanent. | delvis | Tömning tar med anteckningar, aktiviteter och bilagor som pekar på posten (`lagring.gor_gravsten`; test `test_tomt_bolag_och_tomd_person_tar_med_sig_det_som_pekar_pa_dem` i `test_objekt_ovriga.py`). Händelseloggen står kvar med flit, utan värden (`handelser.py`). | ej planerad |
| PS-121 | Tidslinjen hämtas för posten, nyast först, med "hämta fler". | delvis | `GET /companies/{id}/timeline` och `/people/{id}/timeline` nyast först (`crm_v1_tidslinje.py`; test `test_bolagets_tidslinje_samlar_crm_leads_och_support`), och panelens Historik visar postens egna händelser (`Historik.tsx`). Saknas: den samlade tidslinjen i panelen och "hämta fler". | 3 |
| PS-122 | Händelserna grupperas per månad. | inte gjord | Historiken är en enda lista (`Historik.tsx`). | 3 |
| PS-123 | Händelseraderna formuleras med namn, vad som hände och vem som gjorde det. | delvis | "Telefon och Ort ändrades", "Skapades", "Återställdes" med källan (Synk från anslutningen, API, Appen, Systemet) (`Historik.tsx`). Saknas: personens namn eller "Du", postens namn och raden "länkade en". | 3 |
| PS-124 | En fältändring visas med värdet före, en pil och värdet efter. | delvis | Historiken visar vilka fält som ändrades men aldrig värdena; loggen bär med flit inga värden, så att den inte blir ett register över det som raderats (`handelser.py`, `Historik.tsx`). | senare |
| PS-125 | Varje rad visar relativ tid med exakt tid i verktygstips. | byggd | `Timestamp format="relative"` på varje rad (`Historik.tsx`). | |
| PS-126 | Mejl och kalenderhändelser visas som kort i tidslinjen. | delvis | API-tidslinjen bär skickade mejl och svar med ämne och utdrag (`tidslinje._leads`; test `test_bolagets_tidslinje_samlar_crm_leads_och_support`). Saknas: kort i panelen och kalenderhändelser. | 3 |
| PS-127 | Filtrera tidslinjen på händelsetyp. | inte gjord | Inget filter i API:t eller panelen. | 3 |
| PS-128 | Anteckningen som objekt: titel, rik text, kopplingar, bilagor och händelser. | delvis | Anteckning med titel, text, fäst, författare, koppling till bolag, person och affär, bilagor via `anteckning_id` och händelser (`objekt.py`, migration 164, `crm_v1_objekt.py`; test `test_anteckning_kraver_koppling_och_har_ett_tak` i `test_objekt_ovriga.py`). Saknas: rik text och position. | 3 |
| PS-129 | Uppgiften som objekt: titel, beskrivning, förfallodag, status, ansvarig och kopplingar. | verifierad | Titel, beskrivning, förfallotid, status Att göra, Pågår och Klar, ansvarig, kopplingar och `klar_at` som följer status (`objekt.py`, migration 164). Test: `test_uppgift_star_fri_och_klar_at_foljer_status` i `test_objekt_ovriga.py`. Ansvarig är fritext, inte en användare. | |
| PS-130 | En anteckning eller uppgift kan kopplas till valfritt antal poster av olika objekt. | delvis | En anteckning, uppgift eller aktivitet kan peka på ett bolag, en person och en affär (`_KOPPLINGAR` i `objekt.py`; test `test_en_kund_ser_och_kopplar_aldrig_till_en_annans_poster` i `test_objekt_ovriga.py`). Saknas: flera poster av samma objekt. | 3 |
| PS-131 | När en anteckning eller uppgift raderas eller återställs följer kopplingarna med. | byggd | Kopplingarna är kolumner på posten (migration 164), så `objekt.radera` och `objekt.aterstall` tar dem med. | |
| PS-132 | Skapa en anteckning eller uppgift från en post, kopplad och öppnad direkt. | delvis | API:t skapar dem med `company_id`, `person_id` eller `deal_id` (`POST /notes`, `POST /tasks` i `crm_v1_objekt.py`). Saknas: åtgärden i panelen. | 3 |
| PS-133 | Postens uppgiftsflik grupperad på status, med tomläge och "Ny uppgift". | delvis | API:t listar en posts uppgifter och filtrerar på status (`GET /tasks?company_id=`; test `test_uppgifter_sorteras_pa_forfallodag_och_filtreras` i `test_objekt_ovriga.py`). Saknas: fliken i panelen. | 3 |
| PS-134 | Uppgiftsraden: kryssruta för klar, titel, utdrag, kopplingar och förfallodag i varningsfärg. | inte gjord | Inga uppgifter i gränssnittet. | 3 |
| PS-135 | Uppgiftsvyer: alla, efter status och tilldelade mig. | delvis | API:t filtrerar på status och ansvarig och sorterar på förfallodag (`lista_uppgifter` i `crm_v1_objekt.py`; test `test_uppgifter_sorteras_pa_forfallodag_och_filtreras`). Saknas: vyerna i gränssnittet och kanban. | 3 |
| PS-136 | Postens anteckningsflik med kort, "hämta fler" och antal. | delvis | API:t listar en posts anteckningar med sidindelning (`GET /notes?company_id=`). Saknas: fliken i panelen. | 3 |
| PS-137 | Anteckningens och uppgiftens egen sida med fält och textredigerare. | inte gjord | Inga anteckningar eller uppgifter i gränssnittet. | 3 |
| PS-138 | Länka befintliga anteckningar och uppgifter till en post via en sökbar lista. | delvis | En anteckning eller uppgift kan kopplas om med `PATCH` (`objekt.andra`). Saknas: sökbar lista och flera kopplingar. | 3 |
| PS-139 | Formatering av text: fetstil, kursiv, färg, länk och bubbelmeny. | inte gjord | Anteckningar är ren text. | senare |
| PS-140 | Blocktyper i anteckningar: rubriker, listor, checklistor, tabell, bild och fil. | inte gjord | Anteckningar är ren text. | senare |
| PS-141 | Snedstreckskommando som infogar blocktyper. | inte gjord | Ingen redigerare. | senare |
| PS-142 | Länkar i texten läggs till och redigeras i en länkruta. | inte gjord | Ingen redigerare. | senare |
| PS-143 | Bilder och filer klistras in eller dras in i texten. | inte gjord | Ingen redigerare. Bilagor kan kopplas till en anteckning via API:t (`note_id`). | senare |
| PS-144 | Rik text lagras som dokument och markdown, och äldre format läses in. | inte gjord | Anteckningen lagras som ren text, högst 20 000 tecken (`MAX_ANTECKNING` i `objekt.py`). | senare |
| PS-145 | Omnämnanden med "@" av kollegor och poster. | inte gjord | Ingen redigerare. | senare |
| PS-146 | Bilagan som objekt: fil, namn, typ och koppling till posten. | verifierad | Filnamn, typ, storlek, innehåll, uppladdad av och koppling till bolag, person, affär eller anteckning (`objekt.skapa_bilaga`, `bilaga_ut` i `crm_v1_objekt.py`). Test: `test_bilagan_laddas_upp_listas_utan_innehall_och_laddas_ned` i `test_objekt_ovriga.py`. Kan inte kopplas till en uppgift. | |
| PS-147 | Postens filflik med lista, släppzon och knapp för att välja filer. | delvis | API:t listar en posts bilagor utan innehåll (`GET /attachments?company_id=`). Saknas: fliken i panelen. | 3 |
| PS-148 | Ladda upp en bilaga och koppla den till posten, med behörighetskontroll. | verifierad | `POST /attachments` med multipart, kräver skrivomfång och avtal (`crm_v1_objekt.ladda_upp_bilaga`). Test: `test_bilagan_laddas_upp_listas_utan_innehall_och_laddas_ned` i `test_objekt_ovriga.py`. Bara via API:t. | |
| PS-149 | Byt namn på, ladda ned och radera en bilaga. | delvis | Ladda ned (`GET /attachments/{id}/content`) och radera med 30 dagar i papperskorgen (`DELETE /attachments/{id}`); test `test_bilagan_laddas_upp_listas_utan_innehall_och_laddas_ned`. Saknas: namnbyte och åtgärderna i gränssnittet. | 3 |
| PS-150 | Förhandsvisa filer i en dialog med bläddring mellan filerna. | inte gjord | Filen lämnas alltid ut som nedladdning, aldrig inline (`ladda_ned_bilaga` i `crm_v1_objekt.py`). | senare |
| PS-151 | Bilagornas filkategorier efter ändelse. | delvis | Elva tillåtna ändelser med sina typer (`TILLATNA_TYPER` i `objekt.py`). Saknas: kategorierna. | 3 |
| PS-152 | Direktuppladdning i tre steg med väntande och bekräftade filer. | avstår | Ersätts av det Snajp redan har: uppladdning i ett anrop till databasen (`ladda_upp_bilaga` i `crm_v1_objekt.py`, `crm_bilagor`). | |
| PS-153 | Storleksgränser per fil, kontroll av filnamn och rensning av SVG. | verifierad | Högst 10 MB per fil och 500 MB per kund, filnamnet rensas från sökvägar och styrtecken, och html, skript och svg tas inte emot (`objekt.py`). Test: `test_bilagans_storlek_typ_och_kvot` i `test_objekt_ovriga.py`. | |
| PS-154 | Filer ligger i mappar per syfte med signerade adresser och olika regler för token. | avstår | Gäller Twentys egen fillagring. Ersätts av det Snajp redan har: filen ligger i databasen bakom kundisoleringen och hämtas med kundens nyckel (`crm_bilagor`, `ladda_ned_bilaga`). | |
| PS-155 | Filerna raderas när fältet töms eller posten raderas permanent. | verifierad | En tömd post tar med sina bilagor, och innehållet töms (`lagring.gor_gravsten`). Test: `test_tomt_bolag_och_tomd_person_tar_med_sig_det_som_pekar_pa_dem` i `test_objekt_ovriga.py`. | |
| PS-156 | Lagring på lokal disk eller S3 med kontroll av sökvägar. | avstår | Gäller bara egen drift av Twenty. Snajp lagrar filerna i databasen. | |
| PS-157 | Vilka mejl och möten som visas på en post, också via postens personer. | delvis | Mejl ur leadsflödet visas på bolaget (organisationsnummer eller domän) och på personen (exakt adress) (`tidslinje.py`; test `test_personens_tidslinje_gar_pa_exakt_adress` i `test_tidslinje.py`). Saknas: möten, mejl- och kalendersynk in i CRM:et och manuell länkning. | 4 |
| PS-158 | Postens e-postflik med trådar, delningsnivåer, kanalfilter och tomläge. | inte gjord | Mejlen finns i Leads konversationer, utanför CRM:et. | 4 |
| PS-159 | Skriv e-post från posten i ett skrivfönster med förifyllda mottagare. | delvis | Snabbvalet Mejla öppnar en mailto-länk (`BolagPanel.tsx`, `PersonPanel.tsx`). Saknas: skrivfönster i appen och bilagor. | 4 |
| PS-160 | Postens kalenderflik med händelser per månad. | inte gjord | Ingen kalendersynk. Ett möte kan loggas som aktivitet via API:t (`objekt.AKTIVITETSTYPER`). | senare |
| PS-161 | Skapa en kalenderhändelse från posten, med upprepning och deltagare. | inte gjord | Ingen kalender i CRM:et. | senare |
| PS-162 | Radera en post mjukt, ensam eller i mängd. | verifierad | Radering flyttar posten till papperskorgen i 30 dagar, med bekräftelse, mängdradering och Ångra (`objekt.radera`, `lagring`, `AlertDialog` och `taBort` i `BolagVy.tsx`). Test: `test_radering_ar_mjuk_och_syns_for_den_som_synkar_ut` i `test_api.py`. | |
| PS-163 | Se raderade poster och återställ dem. | verifierad | Papperskorgen som vy med Återställ (`Papperskorg.tsx`) och `only_deleted` i API:t. Test: `test_papperskorgen_visar_det_som_gar_att_aterstalla` i `test_handelser_webhooks.py`. Ingen banderoll på posten. | |
| PS-164 | Radera en post permanent efter bekräftelse, med städning av det som hör till. | verifierad | `DELETE` med `permanent=true` tömmer posten och tar med det som pekar på den, och papperskorgen töms efter 30 dagar (`lagring.gor_gravsten`, `tom_papperskorg`). Test: `test_papperskorgen_aterstaller_och_permanent_radering_tommer` i `test_api.py`. Bara via API:t; papperskorgen i gränssnittet har bara Återställ. | |
| PS-165 | E-postadresser sparas med gemener på alla skrivvägar. | verifierad | `falt.epost`. Test: `test_epost` i `test_falt_och_adaptrar.py`. | |
| PS-166 | Länkar normaliseras, och en ogiltig adress ger fel. | verifierad | `falt.webbplats` normaliserar adressen och härleder domänen. Test: `test_webbplats_och_privata_domaner` i `test_falt_och_adaptrar.py`. | |
| PS-167 | Telefonnummer kontrolleras, med egna felkoder. | verifierad | `falt.telefon` ger E.164 och sparar inte ett nummer utan riktnummer. Tester: `test_telefon_blir_e164` och `test_telefon_utan_riktnummer_sparas_inte` i `test_falt_och_adaptrar.py`. | |
| PS-168 | Övrig typomvandling: tal, tomma id och rik text. | verifierad | Tal och datum omvandlas (`falt.heltal`, `falt.datum`). Tester: `test_heltal_svenska_och_engelska_skrivsatt` och `test_datum_blir_iso` i `test_falt_och_adaptrar.py`. | |
| PS-169 | Widgetinställningar: synlighet, återställ, ersätt och radera widget. | inte gjord | Inga widgetar. | ej planerad |
| PS-170 | Widgetinställningar: flytta upp, ned, till annan flik och lägg till bredvid. | inte gjord | Inga widgetar. | ej planerad |
| PS-171 | En widget kan begränsas till mobil eller dator. | inte gjord | Inga widgetar. | ej planerad |
| PS-172 | Flikinställningar: titel, ikon, placering, duplicera, återställ och radera. | inte gjord | Panelernas flikar är fasta. | ej planerad |
| PS-173 | Widgetväljaren på postsidan: fältgrupp, fält, anteckning, relaterade poster och app-komponenter. | inte gjord | Inga widgetar. | ej planerad |
| PS-174 | Relaterade poster kan visas som tabell, kanban, lista eller kalender. | inte gjord | Bolagets personer visas bara som lista (`BolagPanel.tsx`). Affärernas tavla finns i API:t (`GET /deals/board`) men inte som vy på en post. | ej planerad |
| PS-175 | Inställningar för en fältwidget: fält, visningsläge och redigering. | inte gjord | Inga fältwidgetar. | ej planerad |
| PS-176 | Inställningar för fältlistan: layout, antal synliga fält och nya fält. | inte gjord | Fältlistan är fast. | ej planerad |
| PS-177 | Inställningar för relaterade poster: datakälla, fält, filter, sortering och gruppering. | inte gjord | Inga widgetar. | ej planerad |
| PS-178 | Diagraminställningar i en widget. | inte gjord | Hör till instrumentpanelsområdet; översikten har fasta diagram (`OversiktVy.tsx`). | ej planerad |
| PS-179 | Skapa en post i ett formulär, med "Skapa en till", kortkommandon och fältfel. | delvis | Formulär i dialog med Skapa och Avbryt, fel från API:t vid rätt fält och fokus på första felet (`BolagFormular.tsx`, `PersonFormular.tsx`). Saknas: "Skapa en till", Ctrl/Cmd+Enter och Alt+Enter, och fält styrda av en formulärlayout. | 3 |
| PS-180 | Vilka fält och fälttyper som får finnas i skapaformuläret. | delvis | Formulären har fasta fält per objekt (`BolagFormular.tsx`, `PersonFormular.tsx`). Saknas: regler för vilka fält som får vara med. | ej planerad |
| PS-181 | Standardvärden och inmatningsrutor per fälttyp med felmeddelanden. | delvis | Inmatningsrutor per fält med serverns felkoder översatta vid fältet (`BolagFormular.tsx`, `lib/crm/felkoder.ts`), och en person kan få sitt bolag förvalt (`bolagId` i `PersonFormular.tsx`). Saknas: standardvärde per fält. | 3 |
| PS-182 | Anpassa skapaformuläret: visa, dölja och ordna fälten. | inte gjord | Formulären är fasta. | ej planerad |
| PS-183 | Kompletteringsformulär när en ändring bryter mot en valideringsregel. | avstår | Regelmotorn på servern är Enterprise i förlagan. | |
| PS-184 | Uppdatera flera poster på en gång med bekräftelse och förlopp. | delvis | Relationen ändras på flera bolag i mängd med förlopp och Ångra, och flera bolag raderas på en gång (`andraRelation` och `taBort` i `BolagVy.tsx`, `lib/crm/mangd.ts`). Saknas: valfria fält. | 3 |
| PS-185 | Rik text sparas automatiskt en halv sekund efter senaste ändringen. | inte gjord | Ingen redigerare; formulären sparas med knapp. | senare |
| PS-186 | Samtalsinspelningens AI-sammanfattning som widget. | inte gjord | Ingen samtalsinspelning i CRM:et. | ej planerad |
| PS-187 | Samtalsinspelningens transkript med spelare. | inte gjord | Ingen samtalsinspelning i CRM:et. | ej planerad |
| PS-188 | En e-posttråd som widget, med svar och bilagor. | inte gjord | Trådarna finns i Leads konversationer, utanför CRM:et. | 4 |
| PS-189 | Postens AI-chattrådar som widget. | inte gjord | Inga AI-agenter i CRM:et. | ej planerad |
| PS-190 | Widgetens kort med titel, antal och åtgärder, där appar kan lägga egna kommandon. | inte gjord | Inga widgetar. Panelens flik Personer visar antal (`BolagPanel.tsx`). | ej planerad |
| PS-191 | Sex regelåtgärder skapar tidslinjehändelser: skapad, ändrad, raderad, återställd, länkad och avlänkad. | delvis | Fem händelsetyper: skapad, ändrad, raderad, återställd och tömd (`handelser.TYPER`). Saknas: länkad, avlänkad och regler per källobjekt. | 3 |
| PS-192 | Appar kan skapa egna tidslinjehändelser via API:t. | inte gjord | Händelser skrivs bara av CRM:ets egna skrivvägar. | senare |
| PS-193 | Filens format kontrolleras på innehållet och ska vara tillåtet för mappen. | delvis | Filändelsen ska vara tillåten och den angivna typen ska passa ändelsen (`objekt.filtyp`; test `test_bilagans_storlek_typ_och_kvot` i `test_objekt_ovriga.py`). Saknas: att läsa filens innehåll. | 3 |
| PS-194 | Vem som får ladda upp filer. | verifierad | Uppladdning kräver skrivomfång och registrerat avtal (`kraev("crm:skriv")`, `_avtal` i `crm_v1_objekt.py`). Tester: `test_en_lasnyckel_laser_men_skriver_inte` och `test_skrivningar_kraver_avtalet` i `test_objekt_ovriga.py`. | |
| PS-195 | Filer som pekar på en extern källa och hämtas vid öppning. | inte gjord | Alla filer ligger i databasen. | ej planerad |
| PS-196 | Kortkommandon på och kring postsidan. | delvis | Esc stänger panel och dialog (Astryx `Drawer`, `Dialog`). Saknas: Enter och Tab i fältceller, Backsteg, Ctrl/Cmd+Enter, Alt+Enter, Ctrl/Cmd+O, "/" och "@". | 3 |
| PS-197 | Varje standardobjekt levereras med en färdig postsida. | delvis | Bolag och personer har var sin färdig panel (`BolagPanel.tsx`, `PersonPanel.tsx`). Saknas: postsidor för affär, uppgift, anteckning, aktivitet och bilaga. | 3 |
| PS-198 | Standardflikarna har fasta ikoner och positioner med luckor för egna flikar. | inte gjord | Panelens flikar har ikoner (`BolagPanel.tsx`) men inga positioner eller egna flikar. | ej planerad |
| PS-199 | Företagets och personens postsida har flikarna Hem, Tidslinje, Uppgifter, Anteckningar, Filer, Meddelanden och Kalender. | delvis | Bolaget har flikarna Översikt, Personer, Källa och Historik, och personen har grupperna och Historik i en lista (`BolagPanel.tsx`, `PersonPanel.tsx`). Saknas: uppgifter, anteckningar, filer, meddelanden och kalender, och affärens postsida. | 3 |
| PS-200 | Anteckningens och uppgiftens postsida med olika innehåll på mobil och dator. | inte gjord | Inga anteckningar eller uppgifter i gränssnittet. | 3 |
| PS-201 | Postsidor för kalenderhändelse, samtalsinspelning, lista, kampanj och övriga standardobjekt. | inte gjord | Objekten finns inte i CRM:et. | ej planerad |
| PS-202 | Ett eget objekt får en postsida automatiskt. | inte gjord | Inga egna objekt. | ej planerad |
| PS-203 | Widgetens höjdbeteende har ett standardvärde per typ. | inte gjord | Inga widgetar. | ej planerad |
| PS-204 | Lägg till en post i en relaterad-poster-widget via mellanobjekt. | inte gjord | Inga mellanobjekt eller widgetar. | ej planerad |
| PS-205 | Lägg till en post i en relation i två steg. | inte gjord | Inga nästlade relationer. | ej planerad |
| PS-206 | Vyändringar i en relaterad-poster-widget sparas bara i anpassningsläget. | inte gjord | Inga widgetar. | ej planerad |
| PS-207 | Relaterade poster som lista, kanban eller kalender i en widget. | inte gjord | Inga widgetar. | ej planerad |
| PS-208 | Sökning i relationsväljare: innehåller, utan skiftläge, högst 60 träffar, valda först. | delvis | Fritextsökning med `q` på bolag och personer, som kommandopaletten använder (`lagring.py`, `Kommandopalett.tsx`). Saknas: sökning i relationsväljaren, valda först och taket på 60. | 3 |
| PS-209 | Fältvärden som servern begränsat visas spärrade. | inte gjord | Ingen behörighet per fält i CRM:et. | ej planerad |
| PS-210 | Poster ur flera objekt hämtas i ett enda anrop. | inte gjord | Varje objekt hämtas för sig. | senare |
| PS-211 | Vilka egenskaper på layout, flik och widget som går att ändra. | inte gjord | Inga layouter. | ej planerad |
| PS-212 | Högst en fyllande widget per flik, och den ska ligga sist. | inte gjord | Inga widgetar. | ej planerad |
| PS-213 | Valideringsfel per widgettyp när en widget skapas eller ändras. | inte gjord | Inga widgetar. | ej planerad |
| U-01 | De 25 fälttyperna. | delvis | Fasta fält med egna tolkare: text, organisationsnummer, momsnummer, telefon, e-post, webbplats, postnummer, heltal, datum, tidpunkt, bolagsform och SNI (`falt.py`; tester i `test_falt_och_adaptrar.py`). Saknas: fälttyper att välja för egna fält. | senare |
| U-02 | De 26 widgettyperna. | inte gjord | Inga widgetar. | ej planerad |
| U-03 | De 29 konfigurationstyperna för widgetar. | inte gjord | Inga widgetar. | ej planerad |
| U-04 | Fem sidlayouttyper och tre fliklayoutlägen. | inte gjord | Inga layouter. | ej planerad |
| U-05 | Fem visningslägen för fältwidgeten. | inte gjord | Inga fältwidgetar. | ej planerad |
| U-06 | Fältinställningar som styr visningen (klickåtgärd, datumformat, decimaler med flera). | inte gjord | Fälten har ingen inställning per fält. | senare |
| U-07 | Tio aktörskällor för "skapad av". | delvis | Fyra källor i händelseloggen: API, appen, synk och systemet (`handelser.KALLOR`), och postens källa (`kalla`). Saknas: e-post, kalender, arbetsflöde, agent, import, webhook och app. | 3 |
| U-08 | Tre uppgiftsstatusar: Att göra, Pågår och Klar. | verifierad | `UPPGIFTSSTATUS` i `objekt.py`, ut som `todo`, `in_progress` och `done`. Test: `test_uppgift_star_fri_och_klar_at_foljer_status` i `test_objekt_ovriga.py`. Inga färger. | |
| U-09 | Sex tidslinjeåtgärder. | delvis | Skapad, ändrad, raderad, återställd och tömd (`handelser.TYPER`). Saknas: länkad och avlänkad. | 3 |
| U-10 | De 24 snedstreckskommandona i redigeraren. | inte gjord | Ingen redigerare. | senare |
| U-11 | Tio kortkommandon på och kring postsidan. | delvis | Esc stänger panel och dialog. Övriga saknas (se PS-196). | 3 |
| U-12 | Nio textfärger i rik text. | inte gjord | Ingen rik text. | senare |
| U-13 | Sju behörighetsflaggor som rör området. | delvis | Nyckelns omfång: läsa, skriva, synka och administrera (`nycklar.py`); skriv krävs för uppladdning och läs för nedladdning. Saknas: flaggor per användare för layouter och datamodell. | senare |
| U-14 | Sexton filmappar. | avstår | Gäller Twentys egen fillagring; Snajp lagrar filerna i databasen (`crm_bilagor`). | |
| U-15 | Tjugo förhandsvisbara filändelser. | inte gjord | Ingen förhandsvisning. | senare |
| U-16 | Åtta filkategorier för filfält och åtta för bilagor. | delvis | Elva tillåtna ändelser med typ (`TILLATNA_TYPER` i `objekt.py`). Saknas: kategorierna. | 3 |
| U-17 | Tre filstatusar: väntande, uppladdad och extern. | avstår | Ersätts av uppladdning i ett anrop (`ladda_upp_bilaga` i `crm_v1_objekt.py`); en fil finns eller finns inte. | |
| U-18 | Fyra layouter för relaterade poster. | inte gjord | Inga widgetar. | ej planerad |
| U-19 | Tre val för synlighet per enhet. | inte gjord | Inga widgetar. | ej planerad |
| U-20 | Tjugo fälttyper som får finnas i skapaformuläret. | delvis | Formulären har fasta fält (`BolagFormular.tsx`, `PersonFormular.tsx`). Saknas: fälttyper att välja. | ej planerad |
| U-21 | Tre val för var en post öppnas. | avstår | Ersätts av det Snajp redan har: posten öppnas alltid i panelen (`docs/crm/DESIGN-CRM.md` § Postens panel). | |
| U-22 | 25 färger för valalternativ. | delvis | Relationerna har fasta färgtoner (`Relationsetikett`, `tonklass` i `kit.tsx`). Saknas: val av färg per alternativ. | senare |
| U-23 | Standardkriterier för dubbletter: bolag på namn eller domän, person på namn, LinkedIn eller e-post. | delvis | Bolag matchas på organisationsnummer, entydig domän eller entydigt namn och personer på e-post när de skapas eller synkas (`synk.py`; test `test_utan_orgnr_matchas_bara_pa_entydig_doman_eller_entydigt_namn` i `test_api.py`). Saknas: sökning bland befintliga poster. | senare |
| U-24 | Tre delningsnivåer för en post. | avstår | Enterprise-fil i förlagan. | |
| U-25 | 22 standardlayouter för postsidor. | delvis | Två färdiga paneler, för bolag och för personer (`BolagPanel.tsx`, `PersonPanel.tsx`). | 3 |
| U-26 | Fjorton flikmallar med titel, position och ikon. | inte gjord | Panelens flikar är fasta i koden. | ej planerad |
| U-27 | Höjdbeteende per widgettyp. | inte gjord | Inga widgetar. | ej planerad |
| U-28 | Upprepning av en kalenderhändelse. | inte gjord | Ingen kalender i CRM:et. | senare |
