# Handoff 2026-11-26: felen från Buddy-demon, Hjälprutan och CRM-sessionen

**Gren:** `development` · **Skriven av:** Claude (sessionen "Demofelen från Buddy-demon",
2026-11-24 kväll till 2026-11-26) · **Status:** committad och pushad till `development`
samma dag som filen skrevs.

Den här filen ska räcka för att en annan agent eller en människa kan ta över utan att läsa
chatthistoriken. Läs den uppifrån och ned. Underlaget ligger bredvid, i
[`handoffs/2026-11-26-buddy-demo/`](handoffs/2026-11-26-buddy-demo/):

| Mapp | Innehåll |
|---|---|
| `utredningar/` | De fem utredningarna till grundorsak (`fynd-*.md`), var och en granskad av en oberoende agent |
| `planer/` | Hjälprutans tre planförslag (`forslag-*.md`), de sex kartorna över befintlig kod (`karta-*.md`, sammanfattade i `kartor-kort.md`) |
| `bygget/` | Byggrapporterna per paket och granskarnas fynd (`bygge-*.md`, `demobygge-kort.md`, `slutpaket-kort.md`) |

Den valda planen för Hjälprutan står i [`docs/PLAN-HJALPRUTAN-2026-11-25.md`](docs/PLAN-HJALPRUTAN-2026-11-25.md)
och återges i sin helhet sist i den här filen (bilaga A).

**Om personuppgifter.** Repot är publikt. Antons bilder visar riktiga prospekts namn,
mejladresser och telefonnummer och svar från riktiga personer. Tolkningen nedan beskriver
vad bilderna visar utan att återge någon av de uppgifterna, och bilderna själva är inte
incheckade.

---

## 1. Antons första meddelande, ordagrant (2026-11-24 kl. 23:48)

Meddelandet kom med 19 skärmbilder, som tolkas i avsnitt 2.

> Vi hade vårt demo med Buddy idag, det gick bra på det stora hela, han tyckte tjänsten verkade intressant och ville testa den, så vi ska göra en riktig onboarding med honom nästa vecka. Men under presentationen så uppstod en del mindre problem: När vi gjort en test-onboarding för deras företag med deras hemsida angiven, så var kunskapsbasen fylld med vad som bara kunde liknas med faktabitar för supportfrågor kring Postnord eller något liknande. Jag har tyvärr ingen skärmbild på hur det såg ut eftersom vi var mitt i presentationen, men försök gärna återskapa det om du kan för att få reda på vad som hände. Kontot är det andra Testkontot för Buddy, med test@testsson.nu, inte se. När vi fyllde i buddy.se igen (som vi redan gjort i onboardingen) och testade om, så hämtade den bitar ur deras information och villkor som verkade korrekt, men allt var väldigt anpassat för supportagenten och hade inte tolkat någon information anpassat för leadsagenten. Dessutom blev första utkastet lite tokigt och sålde in "vår supportagent" istället för deras erbjudande om telefonitjänster, därefter updaterade vi kunskapsbasen och efter det var utkasten anpassade utifrån deras faktiska tjänster, jag vet inte om det har någon korrelation och om den lyckades utläsa något ändå, kolla gärna det, men det behöver reflekteras i kunskapsbasen. Nästa problem var att körningen blev klar under målet och endast levererade 8 av 10, vilket är helt oacceptabelt, Iris får aldrig, under inga omständigheter leverera under beställt antal, i värsta fall får man ta ett av de(mest kvalificerade) bortsorterade bolagen för att fylla ut kvoten, om inga fullt kvalificerade hittas, se till att detta skrivs in i koden och reglerna. En annan sak är att det genererades 30+ till leads i listan som inte hade processats eller efterfrågats i en körning, det är också strängt förbjudet, både att lägga oprocessade leads i listan, samt lägga till fler leads än det som beställts, det är ingen bonus utan äter ofta på kundens budget. Skapa en plan för att lösa det och sätt de agenter som behövs på det. Nästa större problem som vi behöver lösa omgående är att sidan efter presentationen laddade siffrorna och körningar från Admin, kvar i Buddys testkonto, vilket var lite skrämmande, vid flera sidbyten fram till en hard reset, gå till botten och lös det. Även när man backade från inloggat läge dög det upp en errorsida, det får inte hända, är det så att sessionen gått ut ska man komma till inloggningssidan. Men det största och viktigaste som jag vill att du skapar en separat session för: De vill helst inte behöva ladda upp sina kundlistor själva, utan vill ha en API- integration för detta så kunddatan kan synkas och updateras och de kan hantera sina kunder i Snajp. Detta kan medföra stort värde om det görs på rätt sätt, men det är viktigt att det byggs en ordentlig CRM- svit för detta. EFTERSOM att det är helt open-source, MIT och fritt att modifiera och distrubera vill jag att du instruerar den sessionen att logga in i webbläsarpanelen på https://app.twenty.com/  för att att gå igenom hela sidan med reverse-API-engineer, samt läsa av hela https://github.com/twentyhq/twenty  med BÅDE https://github.com/morluto/rea & https://github.com/storytold/craft-anything för att skapa en så komplett version som möjligt. Sedan vill jag att du bygger den kompletta versionen, utan att skära bort några funktioner till att börja med, med arkitektur och struktur från originalet, men anpassat till svensk standard(gör djupgående research på detta och hitta exempel som du inspekterar visuellt), samt ser till att det integrerar felfritt med våra övriga funktioner i Snajp. För all UI, applicera https://github.com/meta/astryx på alla komponenter, med Snajps färger som tema, för att lyfta utseendet över den befintliga dashboarden. Bygg API- integration som går att bygga med åt båda hållen, som våra kunder kan ansluta till och bygga mot i egengjorda CRM:er, och som vi enkelt kan anpassa formatet för inflödet från olika CRM-system för att allt ska synkas perfekt i vårt CRM och synas där, samt vara sammankopplat med alla våra övriga funktioner. Var ambitiös och gör det lilla extra i varje stetg, stanna inte vid en enkel flik i den befintliga dashboarden, det här blir en länk till en separat app som eventuellt kan byggas in eller ersätta den befintliga dashboarden.

### Antons övriga meddelanden under sessionen, ordagrant och i ordning

1. "Gör vad som krävs för att lösa problemet med utrymmet, vi har en extern hårddisk att ladda över till"
2. "Gör det snabbt, se bara till att inte ta bort något."
3. "Ta bort tempmapparna helt, gör det nu"
4. "Ja, gör samtliga" (svar på tre frågor om produktionen: läsa produktionen utan att skriva för
   frågan om admindatan, arkivera de 36 raderna, radera exempelartiklarna i testarbetsytorna)
5. "Om det inte redan är gjort, se till att gamla exempelartiklar tas bort automatiskt när kunskapsbasen fylls på. Ytterligare en sak jag lovade som vi behöver bygga: Vår inbyggda supportagent ska finnas som en chattruta där kunderna kan ge kontext till kunskapsbasen och be om hjälp, men även direkt feedback på fel, vilket skapas som supporttickets och skickas vidare till vår agent och som bygger en spegel med fixen enbart för deras inlogg för att testa innan det pushas vidare, skapa en utförlig plan för detta och bygg det."
6. "Se till att den andra sessionen fortsätter när limiten återställs"
7. "Committa och pusha till development, med en UTFÖRLIG handoff och statusfil med min fullständiga initiala prompt, din tolkning av bilderna samt de fullständiga planfilerna och all informaton nedan i sin helhet: Gör även den nestade sessionen med CRM-bygget självständig." Meddelandet bar
   sessionens egna rapporter. De återges ordagrant i avsnitt 5.

---

## 2. Tolkningen av de 19 bilderna

Alla bilder är tagna i Chrome på snajp.se, alltså **produktionen**, den 24 november mellan
cirka 21:30 och 21:35, efter demon. Två konton syns:

- **Buddys riktiga demokonto.** Arbetsytan heter "Buddy", inloggat som test@testsson.nu, med
  bannern "Demo · Du testar Snajp med ett begränsat antal körningar".
- **Testarbetsytan "Testarbetsyta https://buddy.se"**, som plattformsadmin besöker. Bannern
  lyder "Du testar som Testarbetsyta https://buddy.se. Allt du kör här är test och syns inte
  på kundens riktiga profil", med knappen "Tillbaka till adminytan".

I de två fönstren är alltså två olika konton inloggade.

| # | Vad bilden visar | Vad det betyder (med grundorsaken som utredningen fann) |
|---|---|---|
| 1 | Buddys konto, Leads › Körningar: tre körningar från **2026-11-15** (14:13 på 200, 17:16 på 100, 17:37 på 100). Den sista står som "Misslyckades" med 34 av 37 och utfallet "Letar fler bolag". | Buddys konto skapades efter den 15:e. Körningarna är **Snajps egna**, alltså adminarbetsytans. Det här är felet "siffror och körningar från Admin kvar i Buddys konto". Den misslyckade körningen fälldes av städaren utan feltext (se avsnitt 3.6). |
| 2 | Testarbetsytan, Leads › Översikt: 44 leads i listan, 8 utkast att godkänna, 0 skickade. Senaste körningen: "Iris · research och utkast, struktur A · test · 8 av 10 leads klara · **Klar, under målet**" (markerat gult). Senaste utkasten har ämnesrader om abonnemang vid nyrekrytering. | Beställt var 10. Levererat 8, och listan bär 44, alltså 36 för många. Två av demons fel syns i en enda bild. |
| 3 | En leadruta i testarbetsytan, fliken Mejlutkast: ämnet "telefonin när teamet växer". Mejlet säljer Buddys upphandling av företagstelefoni med tre månaders fri support. Stilnoten säger att ingången börjar med en slentrianöppning. Sidfoten har GDPR-raden och avregistreringslänken. | Ett **rätt** utkast: det säljer kundens eget erbjudande. Det skrevs efter att kunskapsbasen fyllts med Buddys fakta. |
| 4 | Ett läkemedelsbolag (poäng 46, "Stark"), mejlutkastet: "**Vår Supportagent svarar på era kundfrågor direkt på webbplatsen**, och ni får 3 månaders fri support." | Det **felaktiga** första utkastet. Det säljer Snajps produkt i stället för Buddys telefoni. Grundorsak: onboardingen skrev aldrig kundens produkter (`settings.produkter`), och modellen tog Snajps Supportagent ur skrivstilens exempel. "3 månaders fri support" kom från Buddys egen sajt, och därför ser det rimligt ut. |
| 5–6 | Två leadrutor där poängen är "…", bedömningen "Researchar", 1–2 källor och "Inget utkast ännu". Den ena har ingen webbplats alls. | Bolag som ligger i leadslistan **utan att vara bedömda**. Det är förbjudet enligt Antons nya regel. |
| 7 | Ett plåtslageri, utkast "abonnemangen vid nyrekrytering": Buddys kostnadsfria upphandling av abonnemang. | Ännu ett rätt utkast efter att kunskapsbasen fyllts på. |
| 8 | Leadslistan: de 8 levererade raderna med poäng 46–70, "Stark", "Väntar på ditt ja", kontaktväg "Tel och mejl". | Det som beställdes, minus två. |
| 9–12 | Resten av listan, uppifrån och ned ("Markera alla (44)"): 36 rader med "Provkörning", status "Ny", ingen poäng, "Inget utkast", kontaktväg bara "Tel". Många är stora kedjor och märkesbolag. | **Ringlistans bolag**, de som bara hade telefon, lagda i leadslistan som leads. Grundorsak: i en provkörning fick de ursprunget `test` och föll därför inte bort ur `listvy.synliga`. Detta är "30+ leads som inte processats eller beställts". |
| 13 | Testarbetsytan, Körningar: 2026-11-24 12:19, test, struktur A, beställt 10, **8 · 118**, "Klar, under målet". Utfallet: 118 undersökta, 621 bortvalda för stora, 548 för små, 72 utan belagd koppling till det kunden säljer → 8 Iris-leads, 36 till ringlistan, 16 ej kvalificerade, 6 sajter utan hittad kontakt. 63 hämtningar föll hos tjänsten. | Körningen tog slut på **räknetaket**, inte på bolag. `TAK_FAKTOR = 12` och `MAX_PER_RUNDA = 8` ger exakt 15 rundor och 120 undersökta för 10 beställda, och då avslutades körningen oavsett hur många som levererats. |
| 14 | Samma översikt som bild 2. | Den kvarstår efter sidbyten. |
| 15 | Adminytan, Leads › Konversationer (`/admin/leads?vy=konversationer`): riktiga svar från prospekt i Snajps egen arbetsyta, inloggad som Snajps adminkonto. | Adminens session är aktiv i **samma webbläsare** som kundkontot. Det är förutsättningen för läckan i bild 1 och 18. |
| 16 | `snajp.se/admin/arbetsyta` visar felsidan "Sidan finns inte" med knappen "Till dashboard". | Felet "backade från inloggat läge och fick en errorsida". Grundorsak: `/admin` saknades i `protectedRoutePrefixes`, så en adminadress utan giltig adminsession blev en 404 i stället för inloggningen. |
| 17 | Adminytans översikt: 38 körningar, 3 552 leads levererade av 4 005, en uppskattad kostnad. | Facit för vad som är **adminens** siffror. |
| 18 | **Buddys konto** (`/dashboard`, test@testsson.nu, Demo-banner): 37 körningar, 3 552 levererade av 4 005, leveransgrad 89 %, samma staplar och fördelning som i bild 17. | Läckan, svart på vitt: en kunds översikt visar plattformens siffror. Grundorsak: skalet (React-kontexten i `DashboardContext`) bar den förra identitetens data över ett konto- eller vybyte, och klienten byggde om sidan utan att servern bekräftade vem som var inloggad. Det försvann först vid en hård omladdning. Revisionsloggen visar adminläsningar under kvarten; varje läsning är inte loggad, så exakt vilken väg som läckte är inte bevisad. Rättningen är byggd så att den gäller oavsett väg. |
| 19 | Buddys konto, detaljen för körningen 2026-11-15 17:16: Snajps eget utkast ("Vår agent Iris finns just nu i en kostnadsfri pilot …") med Snajps grundares signatur, och 1 371 bortvalda (stora fordonsbolag). | Mer av samma läcka: en annan kunds (Snajps) körning med utkast och signatur, synlig för Buddy. |

Bilderna i sammandrag:

- **Fel 1** (kunskapsbasen, Postnord-faktan) har ingen bild, som Anton skrev. Grundorsaken är
  att testarbetsytor seedas med exempelbolaget "Nordlys Handel"s supportartiklar (paketspårning,
  returer, leveranser), som liknar en logistikfirma. När en kund med egen webbplats onboardas ska
  basen fyllas av skanningen, inte av exemplen.
- **Fel 2–5** syns i bilderna ovan.
- **Utkastet:** att det blev rätt efter påfyllningen stämmer med grundorsaken. När
  kunskapsbasen bar Buddys erbjudande hade modellen något eget att sälja.

---

## 3. Grundorsakerna (utredda, och varje utredning granskad av en oberoende agent)

Fullständiga utredningar: [`handoffs/2026-11-26-buddy-demo/utredningar/`](handoffs/2026-11-26-buddy-demo/utredningar/).

1. **Kunskapsbasen.** Testarbetsytor seedas med exempelbolaget Nordlys Handels artiklar, som
   aldrig rensades när kundens eget innehåll kom in. Skanningen av en webbplats gav bara
   supportfakta, ingen säljfakta som Iris läser. Onboardingen skrev aldrig kundens produkt till
   `settings.produkter`. Utan produkt valde utkastkedjan inget eget erbjudande, och modellen
   lånade Snajps Supportagent ur skrivstilens exempel.
2. **8 av 10.** Räknetaket (`korning.py`: `TAK_FAKTOR = 12`, `MAX_PER_RUNDA = 8`,
   `TOMMA_RUNDOR = 4`) avslutade körningen efter 15 rundor och 120 undersökta. Det var
   `slut_pa_kandidater`, inte brist på bolag. Bekräftat i produktionens liggare.
3. **36 obeställda rader.** Ringlistans bolag fick i provkörningar ursprunget `test` och visades
   därför i leadslistan.
4. **Admindata i kundkontot.** Ett skal som behöll den förra identitetens data över
   identitetsbytet, med adminsessionen aktiv i samma webbläsare. Ingen serverväg som lämnar ut
   en annan kunds data hittades.
5. **Felsidan vid bakåt.** `/admin` saknades i `protectedRoutePrefixes` i `lib/routes.ts`.
6. **"Misslyckades 34/100" den 15:e.** Städaren fällde körningen utan feltext. **Varför den
   tystnade är inte utrett.** Hypotesen att `limit=10` dolde den är motbevisad.

---

## 4. Vad som är byggt

### 4.1 Demorättningarna

- **Beställt antal (CLAUDE.md regel 23).**
  - Räknetaken avslutar inte en körning under målet: de förlängs och loggas.
  - Kvoten fylls på i bestämd ordning (`korning.PAFYLLNADSSTEG`): fallna hämtningar, sajter utan
    hittad kontakt, researchens bortval i rangordning, stegvis vidgad storlek, och sist bolag med
    belagt nej (bakom `PAFYLL_BELAGT_NEJ`).
  - Ett påfyllt lead går hela kedjan och märks "Påfyllt" med skälet. Spärren `far_fyllas_pa`
    hindrar avvecklade bolag, enskilda firmor, Kontakta inte, redan kontaktade, bolag utan
    mottagare, bolag profilen utesluter och ring- eller ej kvalificerade-bolag.
  - Geografin vidgas aldrig. Är allt uttömt blir körningen **vilande** och letar vidare en gång
    per dygn. "Klar, under målet" uppstår inte för nya Iris-körningar.
  - Migration 158 lägger till `pafylld` och `pafylld_skal`.
- **Inga obeställda leads (regel 24).**
  - En provkörnings ringbolag skrivs till listan "Ringlista, Iris <datum>" under Listor.
  - `listvy.synliga` visar aldrig ett obedömt prospekt ur ring- eller provspåret.
  - Veckoanalysen räknar inte ringbolag som nya leads.
- **Identitetsbytet (INV-SEC-014).**
  - Varje svar bär `X-Snajp-Identitet`, och sidan laddar om när den skiljer sig från den
    identitet sidan renderades för.
  - En `BroadcastChannel` varnar andra flikar.
  - In- och utloggning och vybyte öppnar adressen på riktigt (`loggaUtOchOppna`,
    `bytVyOchOppna`, `oppnaEfterIdentitetsbyte`).
- **Bakåtknappen.** `/admin` ligger i `protectedRoutePrefixes`. Utan inloggning leder adressen
  till inloggningen, och en inloggad kund hamnar på dashboarden.
- **Utkastet som sålde Supportagenten.**
  - Onboardingen skriver kundens första produkt.
  - `require_egen_produkt` stoppar utkast utan egen produkt (felkoden `saknar_produkt`).
  - `stilkontroll.snajp_produkt_hos_kund` fäller Snajps produktnamn i en annan kunds utkast.
  - Saknas produktlistan faller `standard.ts` tillbaka på första raden i kundens produkttext.
    Utan det hade nio av tio kunder i produktionen fastnat.
- **Kunskapsbasen.**
  - Skanningen föreslår också säljfakta i kategorin `salj` (migration 153), och kontextpaketet
    ger Iris dem.
  - Exempelartiklarna märks med `is_placeholder` (migration 159) och tas bort automatiskt, i
    samma transaktion, när kundens eget innehåll läggs in.
  - En kund med egen webbplats seedas inte med exempel (`exempel_kb`).

### 4.2 Hjälprutan, fas 1 och 2 (Antons beställning 2026-11-25)

Planen: bilaga A och `docs/PLAN-HJALPRUTAN-2026-11-25.md`.

- **Rutan.** Den ligger under Meny i dashboarden (`components/snajp/HjalpRuta.tsx`), med tre
  avsikter: fråga om Snajp, lär agenten om oss och något är fel.
- **Snajps egen agent.** Den svarar under hjälpens egen nyckel (`SNAJP_KEY_SNAJP_HJALP`, kunden
  `snajp-hjalp`), aldrig under kundens nyckel (INV-HJALP-001 och -002).
- **Kontext till kunskapsbasen.** Kunden skickar ett förslag med källan `chatt` (migration 157)
  till sin egen kunskapsbas, och det läggs bara in efter kundens klick.
- **Felrapporter som ärenden.** De sparas som `plattformsarenden` med händelser (migration 156),
  ett nummer och prioriterat mejl till Snajp. Kunden följer dem under "Mina ärenden". Adminytan
  har listan `Felrapporter` med lägesbyten.
- **Inte byggt.** Fas 3–5 (den kodande agenten, testversionen per kund och automationen) väntar
  på Antons beslut. Se avsnitt 6.

### 4.3 Resterna (2026-11-25, andra rundan)

- **Felkoder i utkastrutorna.**
  - `lib/leads/felkoder.ts` och `error_kod` i `GET /api/jobs/{id}`.
  - Den nya koden `saknar_beskrivning`.
  - Tidsgränstexten är en konstant (`TIDSGRANS_FEL`).
- **Felrapportens bild för plattformsadmin.**
  - Den hämtas med ett klick, en läsning per ärende (`/api/admin/plattformsarenden/{id}/bild`),
    aldrig med listan.
  - Svaret bär `no-store` och `nosniff`, och läsningen ger en rad i åtkomstloggen utan innehåll.
  - Inlämningen tar bara emot PNG, JPEG, WebP och GIF.
- **Hjälpens jobb är låsta till den som startade dem.** Jobb-id:t som klienten får är
  HMAC-signerat med användare och arbetsyta (`lib/snajp/hjalp.ts`, nyckeln härledd ur
  `AUTH_SECRET`). Fel användare, en kollega och ett manipulerat id får samma 404.
- **Vilande körningar läses smalt.** `list_andra_korningars_bolag` ger bara bolagens namn och
  organisationsnummer: cirka 70 ms och 22 KB per läsning, mot 860 ms och 10 MB förut.
- **Två fel som bara syntes mot riktig Postgres.** En okänd kategori gav serverfel; nu kommer ett
  besked, och minneslagret är lika strängt. `skapad_av` kom ut som en databastyp och hade gett
  serverfel i drift.
- **Databastesterna.** `tests/db/test_demorattningar_db.py` har sex tester genom approllen och
  står i CI:s databassteg.

### 4.4 Gjort i produktionen, med Antons "Ja, gör samtliga"

- I testarbetsytan för Buddy-demon: 36 obedömda rader **arkiverade** (inte raderade) och 28
  exempelartiklar raderade. Verifierat efteråt: 8 synliga leads och 15 artiklar.
- **Inte gjort:** en föräldralös testarbetsyta bär fortfarande de 28 exempelartiklarna. Om de ska
  raderas är Antons beslut.
- Development-spegeln är inte rörd.

---

## 5. Sessionens egna rapporter, ordagrant (som Anton skickade tillbaka dem 2026-11-26)

> De fem resterna är byggda och granskade, och granskarnas fynd är rättade. Hela backendsviten körs nu i bakgrunden; när den är klar kör jag rotens tester och typkontrollen och tar bilder av de två synliga ändringarna.
>
> Vad rundan gav
> Ett riktigt fel i databaslagret hittades. Ett kunskapsförslag från hjälpchatten gav tillbaka användarens id i en form som inte går att skicka som svar. I drift hade det blivit ett serverfel; minnestesterna kunde inte se det. Rättat, med ett test som fäller det gamla beteendet.
> Hjälpjobb är låsta till den som startade dem. Jobb-id:t som klienten får är signerat med användare och arbetsyta. Fel användare, en kollega i samma arbetsyta och ett manipulerat id får alla samma "finns inte".
> Felrapportens bild går att öppna i adminytan med ett klick, i den befintliga ärendevyn. Den hämtas aldrig med listan, cachas inte och loggas som en adminläsning utan innehåll. Inlämningen tar nu bara emot PNG, JPEG, WebP och GIF; förut lagrades även SVG.
> Felkoder i utkastrutorna översätts. Den engelska ytan får aldrig backendens svenska text. Jag lade också till en kod för det vanligaste felet, att beskrivningen av vad ni säljer saknas eller är för kort.
> En vilande körning läses inte längre in i sin helhet. Bara bolagens namn och organisationsnummer lämnar databasen. Granskaren mätte en stor vilande körning lokalt: cirka 70 ms och 22 KB per läsning, mot 860 ms och 10 MB förut.
> Varje ändrad databasfråga är körd mot riktig Postgres genom approllen och jämförd med minneslagret. Det är sex nya databastester, som också är tillagda i CI.
> Mitt val som du bör känna till
>
> När ett utkastjobb faller utan känd kod visar den svenska ytan backendens svenska text, och den engelska en allmän text. Granskaren ville ha en allmän text på båda språken. Jag behöll den svenska texten eftersom den bär diagnosen och redan är filtrerad från programfel. Säg till om du vill ha det strängare.
>
> Inte rättat
> Rå feltext visas fortfarande i snabbsöket, i körningsformulärets rader och i utskicksjobben.
> Skälet på ett stoppat utkast visas ordagrant på svenska även i den engelska ytan.
> Adminloggens rad för en bildläsning säger vilket ärende, men inte vilken kund.
>
> Invarianttestet är nu grönt, och loopvaktens tester går gröna var för sig, så felet i helkörningen var tidsberoende under last. Jag kör nu rotens tester, nodetesterna och typkontrollen.
>
> Rotens tester (1 009) och nodetesterna (421) är gröna. Men bara 1,7 GB virtuellt minne är ledigt, för lite för typkontroll och förhandsvisning, så jag ser efter vad som håller minnet.
>
> Din användningsgräns är nådd, så jag stannar här. Resterna är rättade och testerna gröna, men två kontroller återstår innan något bör committas.
>
> Klart
> Migrationerna är prövade mot riktig Postgres, från noll och ovanpå en äldre databas. Databastesterna är gröna i CI:s ordning.
> De fem resterna är rättade och granskade, och granskarnas fynd är åtgärdade. Det gäller felkoderna i utkastrutorna, bilden i felrapporten, ägarkontrollen på hjälpens jobb, läsningen av vilande körningar och databasfrågorna mot riktig Postgres.
> Två fel som bara syntes mot riktig databas är rättade: kunskapsbasens kategorikontroll, och ett kunskapsförslag från chatten som hade gett serverfel i drift.
> Testläget utan den lokala .env:
> Svit	Utfall
> Backend	4 735 gröna, 3 röda vid körningen
> Roten	1 009 gröna
> Nodetester	421 gröna
>
> Av de tre röda är ett rättat efteråt och grönt (det räknade adminvägar, och bildläsningen är en ny). De två andra gäller loopvakten: de är tidsberoende under last och gröna när de körs för sig. Hela backendsviten är inte körd om efter den sista rättningen.
>
> Kvar
> Typkontrollen är inte körd efter dagens ändringar. Bara 1,7 GB virtuellt minne var ledigt, och CRM-sessionens utvecklingsserver kör.
> De två synliga ändringarna är inte sedda i bild: knappen "Visa bilden" i felrapporterna och det fallna utkastjobbets ruta. De ska inte committas förrän någon har tittat på dem, på desktop och mobil.
> docs/BESLUT.md är inte uppdaterad med dagens val.
> Inget är committat eller pushat. Frågan om commit till development står kvar.
> Bör du känna till
> CRM-sessionen kör igen och har en egen utvecklingsserver igång. Jag har inte rört den.
> C: har 2,4 GB ledigt.
> Den lokala Postgres i WSL är stoppad igen och mina engångsdatabaser är borttagna. Databasen railway där är orörd.
> Läget står i .agent-chorus/CHECKPOINT.md, så att nästa session kan ta vid.
>
> Typkontrollen är ren på de 61 ändrade filerna. Bilderna av felrapportens bildvisning är tagna; jag läser dem nu.
>
> Felrapportens bild och felläget ser rätt ut på desktop och mobil. Nu läser jag bilderna av det fallna utkastjobbets ruta.
>
> De två kontroller som återstod är gjorda, och hela backendsviten körs nu om i bakgrunden efter den sista rättningen. Jag rapporterar utfallet när den är klar.
>
> Typkontrollen är ren på alla 61 ändrade och nya TypeScript-filer. Det är en avgränsad körning; hela projektet är inte typkontrollerat efter dagens runda, eftersom minnet inte räckte.
> Felrapportens bild är sedd på desktop och mobil. Bilden öppnas på sin plats under rubriken Bild, och felläget visar "Bilden gick inte att hämta" med Försök igen. Ingen sidscroll, inga sidfel.
> Det fallna utkastjobbets ruta är sedd på desktop och mobil. En känd felkod visas på användarens språk. En okänd kod ger backendens svenska text på svenska och "The draft could not be written." på engelska.
> Dagens val står i docs/BESLUT.md, märkta som mina och inte dina. Läget står i .agent-chorus/CHECKPOINT.md.
>
> CRM-sessionen stannade igen på kvoten. De fyra första vyerna är byggda och committade på grenen claude/snajp-crm-dd0d83, inget är pushat, och jag har inte startat om den.
>
> Inget är committat eller pushat, och frågan om commit till development står kvar.
>
> Hela backendsviten är grön efter den sista rättningen: 4 738 tester, inga röda. Därmed är rundan klar, och allt ligger ocommittat på development.
>
> Verifierat
> Kontroll	Utfall
> Backendens hela svit	4 738 gröna, 0 röda
> Rotens tester	1 009 gröna
> Nodetester	421 gröna
> Databastester mot lokal Postgres, i CI:s ordning	16 + 39 gröna, inga överhoppade; ett tillagt efteråt, grönt
> Migrationerna 153, 156–159	går igenom från noll och ovanpå en äldre databas, och tål två körningar
> Typkontroll	ren på de 61 ändrade och nya filerna
> Bilder, 1280 och 375 pixlar	båda synliga ändringarna sedda, även på engelska
>
> Sviterna är körda med snajp-support/.env undanlagd. Med filen på plats faller minst två tester, eftersom den pekar på en DeepSeek-modell och en gammal Supabase-adress.
>
> Inte gjort
> Hela projektets typkontroll är inte körd efter dagens runda; minnet räckte bara till den avgränsade.
> Migrationerna är inte körda i någon Railway-miljö. De körs av sig själva vid en push till development.
> Hjälprutan svarar "inte påslagen" tills hjälpens kund och nyckel är skapade i miljön.
> Testerna som kör hela flödet i en webbläsare är inte körda.
> Tre mindre rester står i docs/BESLUT.md: rå feltext i snabbsöket, körningsformulärets rader och utskicksjobben; skälet på ett stoppat utkast på svenska i den engelska ytan; och att adminloggen inte säger vilken kunds bild som öppnades.
> Väntar på dig
> Commit till development. Säg till så committar jag. Flera andra sessioners filer ligger i samma arbetskatalog, så jag lägger bara till den här sessionens filer.
> Repot är publikt med docs/compliance/ incheckad. Frågan om det ska göras privat står kvar.
> Mina val från i dag står överst i docs/BESLUT.md, märkta som mina.
> CRM-sessionen står still på kvoten, med fyra vyer committade på grenen claude/snajp-crm-dd0d83.
> C: har omkring 2 GB ledigt.

---

## 6. Läget vid överlämningen

Detaljerat läge per punkt står i [`STATUS.md`](STATUS.md) (posten 2026-11-26).

### Verifierat före commit

| Kontroll | Utfall |
|---|---|
| Backendens hela svit (`cd snajp-support && pytest`, med `snajp-support/.env` undanlagd) | 4 738 gröna, 0 röda |
| Rotens tester (`pytest tests`) | 1 009 gröna |
| Nodetester (`node --test "lib/**/*.test.ts"`) | 421 gröna |
| Databastester mot lokal Postgres 16 i WSL, i CI:s ordning | 16 + 39 gröna, inga överhoppade; plus `test_demorattningar_db.py`, 6 gröna |
| Migrationerna 153 och 156–159 | går igenom från noll (169 migrationer) och ovanpå en databas som stod på 068 (89 ovanpå 117), och tål att köras två gånger |
| Typkontroll | ren på de 61 ändrade och nya TypeScript-filerna (avgränsad tsconfig) |
| Bilder, 1280 och 375 px | varje synlig ändring sedd: felrapportens bild och felläge, det fallna utkastjobbet (svenska, engelska, känd och okänd kod), påfyllt lead, kunskapsbasen, Hjälprutan, körningarna |

### Inte gjort eller inte prövat

- **Hela projektets typkontroll** är inte körd efter andra rundan; minnet räckte bara till den avgränsade.
- **Railway:** pushen till `development` kör migrationerna 153 och 156–159 där
  (`.github/workflows/migrera.yml`). Kontrollera att jobbet `migrera` blev grönt.
- **Hjälprutan svarar "inte påslagen"** tills hjälpens kund och nyckel finns i miljön:
  ```bash
  cd snajp-support && python -m app.tenants.snajp_hjalp
  python scripts/railway_tenantnyckel.py --slug snajp-hjalp --name "Snajp Hjälp" --env development --apply
  ```
- **Testerna som kör hela flödet i en webbläsare** (e2e) är skrivna men inte körda; de kräver den lokala stacken.
- **Den inloggade ytan i drift** är inte provad; bara förhandsvisningarna under `app/forhandsvisning/` är sedda.
- **Varför körningen 2026-11-15 tystnade** är inte utrett.
- **Kvar, mindre:**
  - Rå feltext visas fortfarande i snabbsöket (`LeadsSnabbsok.tsx`), i körningsformulärets rader
    (`LeadsRunForm.tsx`) och i utskicksjobben (`lib/leads/utskicksjobb.ts`).
  - Skälet på ett stoppat utkast (`escalation_reason`) visas på svenska i den engelska ytan.
  - Adminloggens rad för en bildläsning saknar kunden.
  - Agentens föreslagna kort i Hjälprutan är inte byggda.
  - Meta-invariantens regex prövar inte INV-LEADS-* (fanns redan).
- **bd (beads)** används inte: `dolt` saknas på maskinen.

### Val som är agentens, inte Antons (de står i `docs/BESLUT.md`)

1. Sista påfyllnadssteget tar bolag med belagt nej (bakom `PAFYLL_BELAGT_NEJ`). Det upphäver,
   för påfyllda leads, Sebbes krav att bara ett belagt ja blir ett lead.
2. Ett påfyllt lead visar "Påfyllt" i nivåcellen, med skälet under.
3. En vilande autopilotkörning är kundens dagliga försök; autopiloten startar ingen ny bredvid den.
4. En kund som går till `/admin` hamnar på dashboarden i stället för felsidan.
5. Ett fallet utkastjobb utan känd kod visar backendens svenska text på svenska och en allmän
   text på engelska.
6. Hjälpens jobb är signerade med användare och arbetsyta. En admin som byter vy mitt i en fråga
   får "finns inte" på den frågan.

### Väntar på Anton

- **Repot `oloflun/snipe-leads` är publikt**, med `docs/compliance/` (106 filer) incheckad.
  Frågan om det ska göras privat står kvar.
- **Ringlistan i skarpa körningar:** ska den också till Listor, eller bara ligga i Samtal › Ringlista som nu?
- **Hjälprutan fas 3–5:**
  - Dataskyddsbeslutet: får en kodande agent läsa ett avidentifierat underlag, och får en kunds
    arbetsyta kopieras till en testmiljö?
  - Kostnaden för en testmiljö per kund hos Railway.
  - En GitHub-identitet för agenten.
  - Hur mycket kunden ser av ett ärendes läge.
- **Exempelartiklarna** i den föräldralösa testarbetsytan: ska de raderas?
- **Disken:** C: har cirka 2 GB ledigt. Windows Update-cachen (9 GB) går bara att radera, inte flytta.
- **Designhooken** gör `gsap` och `lenis` till `npm link`-länkar som fäller `next dev`. Den bör
  rättas i super-intelligence.

### Miljön på maskinen

- **`snajp-support/.env`** pekar på `LLM_PROVIDER=deepseek`, en DeepSeek-modell och en gammal
  Supabase-adress. Med den på plats vägrar appen starta i tester som når en fjärrdatabas, och två
  tester faller. Lägg filen åt sidan när sviten körs, eller rätta den.
- **Postgres 16 finns i WSL-Ubuntu.** Starta med
  `wsl -d Ubuntu-24.04 -u root -- service postgresql start`. Databasen `railway` där är en gammal
  lokal stack (migration 068) och ska inte röras; pröva i en engångsdatabas.
- **Flyttat till `D:\C-flyttat`** med länkar kvar: npm-cachen, pnpm, ms-playwright och flera
  mappar under `AppData`.

---

## 7. CRM-sessionen

Sessionen **"Snajp CRM: komplett svit efter Twenty, med API"** startades på Antons order den
24 november och arbetar i ett eget worktree på grenen `claude/snajp-crm-dd0d83`. Den rör inget
av det som står ovan. Den 26 november gjordes den **självständig**: den är lyft ur den här
sessionen och fick besked att fortsätta på egen hand, och att återuppta arbetet själv när
användningsgränsen återställs.

Dess senaste rapporter:

- **Kundsynken in** är byggd och testad (`1cc6ff4d`), och Astryx är installerat (`55100dd1`).
- **Fyra vyer** är byggda med Astryx, typkontrollerade och kontrastmätta (`b6c08ef2`).
- **Gränssnittet är ombyggt** efter Antons dom: ny översikt, ljus navigering, postchips, paneler
  och kommandopalett (`d438ff84`). Det väntar på Antons bedömning.
- **Inventeringen av Twentys källkod** är inte klar; sista delen var inte startad.
- **Ingenting är pushat**, och vyerna är bara körda mot efterbildade svar.
- **Licensen:** Twenty är i huvudsak AGPLv3, inte MIT. MIT gäller bara `twenty-ui`,
  `twenty-shared`, SDK:erna och `twenty-apps`, och filer märkta Enterprise är kommersiella. Valet
  mellan egen kod med MIT-paketen och en AGPL-fork som separat tjänst är Antons.

---

## Bilaga A. `docs/PLAN-HJALPRUTAN-2026-11-25.md` i sin helhet (som den låg vid commit)

### Plan: Hjälprutan, felrapporter och testversion per kund

Skriven 2026-11-25 efter Antons beställning samma dag. Underlaget är sex
kartläggningar av det som redan finns och tre oberoende arkitekturförslag
(säkerhet först, minsta helhet först, kundens upplevelse först). Den här planen
är sammanvägningen. Varje val som är Antons står under "Kräver Anton", med det
förval bygget utgår från tills han säger annat.

#### Beställningen

> Vår inbyggda supportagent ska finnas som en chattruta där kunderna kan ge
> kontext till kunskapsbasen och be om hjälp, men även direkt feedback på fel,
> vilket skapas som supporttickets och skickas vidare till vår agent och som
> bygger en spegel med fixen enbart för deras inlogg för att testa innan det
> pushas vidare.

Samma dag: gamla exempelartiklar ska tas bort automatiskt när kunskapsbasen
fylls på.

#### Vad kunden får

En ingång, tre ärenden, ett förlopp.

- **Ingången** är knappen Meny i sidomenyns fot och i mobilraden. Där står i dag
  "Anmäl felaktigt svar", som bara öppnar ett mejl. Den raden blir "Hjälp och
  fel" och öppnar Hjälprutan: ett ark förankrat i sidomenyn på desktop, full
  höjd på mobil. Ingen flytande bubbla och ingen ny panel ovanpå sidorna.
- **Fråga om Snajp.** Snajps egen supportagent svarar ur Snajps kunskapsbas om
  produkten.
- **Lär agenten om oss.** Kunden skriver eller klistrar in text om sitt företag.
  Rutan visar exakt den rubrik och text som sparas, kunden kan ändra, och ett
  klick lägger artikeln i kundens egen kunskapsbas.
- **Något är fel.** Ett kort i samtalet med tre fält: vad gjorde du, vad hände,
  vad väntade du dig, plus valfri bild. Under fälten står öppet vad som skickas
  med (sidan, tiden, rollen). Rapporten kvitteras direkt med ett ärendenummer.
- **Mina ärenden.** En flik i samma ruta visar varje felrapport och var den står.
  Det finns kvar efter omladdning och på andra enheter. Samma händelser når
  appens befintliga notiscenter, så det blir ingen andra klocka.

Kunden ser sex lägen och två sidolägen. De interna stegen (gren, ändringsbegäran,
bygge) syns bara för plattformsadmin.

| Kunden ser | Betyder |
|---|---|
| Mottaget | Rapporten är sparad hos Snajp |
| Vi undersöker | En människa hos Snajp har läst den |
| Rättning på gång | Rättningen tas fram |
| Redo att testa | Testversionen är byggd; knappen "Öppna testversionen" och frågan "Fungerade det?" |
| Godkänd, granskas av oss | Kunden svarade ja; Snajp granskar innan något går ut |
| Ute i Snajp | Rättningen ligger i produktionen; testversionen är borttagen |
| Behöver mer från dig | Snajp har en fråga; svarsfält i kortet |
| Stängd med förklaring | Inte ett fel, eller går inte att rätta; en människa har skrivit varför |

Svarar kunden nej på "Fungerade det?" går ärendet tillbaka till Rättning på
gång med kundens kommentar och samma ärendenummer.

#### Det som redan finns och återanvänds

- `components/snajp/SupportChat.tsx` är chattkomponenten på fyra ställen
  (marknadssidan, kundens länk, widgeten, testchatten). Den har fasvisning,
  pollning, felhantering och ett kort för kunskapsbasartiklar.
- `components/snajp/AgentMenu.tsx` är redan hjälp- och felingången, monterad i
  `components/AppShell.tsx`.
- Backendens chattväg `POST /api/chat` (`snajp-support/app/api/chat.py`) svarar
  med ett jobb som klienten pollar. Ingen tokenströmning finns och ingen byggs.
- Snajp finns som kund hos sig själv (`lib/tenants/snajp.ts`,
  `snajp-support/app/tenants/snajp_kb.py`), men nås i dag bara anonymt från
  marknadssidan.
- Kunskapsbasens förslagslista (`components/settings/WebbplatsForslag.tsx`,
  tabellen `ss_kb_forslag`) och regeln att en människa lägger till varje artikel
  (INV-LEARN-001).
- Adminytans `components/admin/FelOchEskaleringar.tsx` och det prioriterade
  mejlet utan kundtext (`snajp-support/app/notifications/prioriterat_mejl.py`).
- Spegelns spärrar: en databas märkt `mirror_meta` med läget `envags` stoppar
  utskick, inkorg och autopilot med kod som redan finns.
- Skripten mot Railway (`scripts/railway.py`, `scripts/railway_provision.py`)
  och inkapslingen av opålitlig text
  (`snajp-support/app/leads/untrusted_content.py`).
- Kolumnen `ss_knowledge_base.is_placeholder` finns sedan juli men ingen kod
  läser eller skriver den.

#### Arkitekturen

##### 1. Hjälprutan (Next)

- `AgentMenu` öppnar `components/snajp/HjalpRuta.tsx` (ny, tunn behållare med
  flikarna Samtal och Mina ärenden). Samtalet är `SupportChat` i ett nytt läge,
  `hjalpMode`, som hämtar historiken från servern i stället för webbläsarens
  minne.
- Tomt läge: en rad om vad rutan gör och tre startval. Kunden kan också skriva
  fritt. Agenten får föreslå rätt kort ("Det låter som ett fel. Vill du anmäla
  det?"), men ärendet skapas alltid av kundens klick, aldrig av modellens
  klassning.
- All text är tvåspråkig via `lib/i18n.tsx`. En förhandsvisning utan databas
  läggs under `app/forhandsvisning/hjalpruta/` så att varje läge går att se i
  bild på desktop och mobil.

##### 2. Vägen till Snajps egen agent

- Nya inloggade vägar under `app/api/snajp-support/hjalp/`: chatt, jobb, samtal,
  ärenden. Alla kräver session (`getWorkspaceContext`), så INV-SEC-010 håller.
- De använder **hjälpens egen nyckel**, aldrig kundens och aldrig
  `proxyAsTenant`. Hjälpen får en egen kund i systemet, `snajp-hjalp`, skild
  från `snajp` som marknadssidans anonyma demo använder. Skäl: en anstormning
  på marknadssidan ska inte stänga kundernas hjälp, och den anonyma vägen ska
  inte kunna nå kundernas samtal ens med rätt adress.
- Servern skriver om anropet: avsändaren blir `<användar-id>@kund.snajp.se`
  (den domänen avvisas redan av den anonyma vägen), namnet tas ur profilen,
  `arbetsyta` tas alltid bort (annars hamnar Snajps egna nyckeltal i svaret)
  och `is_test` är falskt. Från klienten tas bara texten och sidans sökväg.
- Backend: `POST /api/hjalp/samtal` läser tillbaka samtalet och godtar bara
  `@kund.snajp.se`.
- Snajps kunskapsbas fylls på med produkthjälp för den inloggade ytan. I dag
  finns en enda sådan artikel, och utan fler svarar agenten svagt.

##### 3. Kontext till kundens kunskapsbas

- Allt skrivs i **kundens** kund i systemet, genom kundens egen väg
  (`proxyAsTenant` mot `/api/kb`), efter kundens klick. Snajps agent skriver
  aldrig över gränsen mellan kunder.
- Nytt: `POST /api/kb/forslag` med källan `chatt`, så att text ur samtalet kan
  bli ett förslag som syns både i rutan och i den befintliga förslagslistan,
  med en etikett som säger var det kom ifrån.
- Läsrollen ser kortet med knappen avstängd och en förklaring. En
  plattformsadmin som besöker kunden skriver testmärkt, som i dag.

##### 4. Exempelartiklarna rensas av sig själva

- `is_placeholder` börjar användas. Bara seedningen
  (`snajp-support/app/scripts/seed_kb.py`) sätter den.
- Rensningen ligger i lagringslagret: varje väg som lägger in kundens eget
  innehåll (`add_kb_article`, `lagg_till_kb_forslag`) raderar kundens
  exempelrader i samma transaktion. Då gäller den alla vägar, även framtida.
- Eget innehåll är en artikel kunden lagt till eller ett förslag kunden godkänt.
  Att skanningen lämnat förslag räcker inte: då står basen annars tom tills
  kunden godkänt något.
- En additiv migration märker de exempelrader som redan finns i testarbetsytor.
  Snajps egen bas och den riktiga demokunden Nordlys märks aldrig.

##### 5. Felrapporten som ärende

- Felrapporten går ett eget, strukturerat flöde och inte genom agentens
  eskalering. En eskalering tystar chatten i upp till 24 timmar, och kunden
  ska kunna fortsätta fråga medan felet rättas.
- Ny tabell `plattformsarenden` och händelseloggen `plattformsarende_handelser`.
  Rapportör, arbetsyta, kund, vy, roll och om det är en besökande admin sätts
  på servern ur sessionen. Klienten skickar bara sökvägen, de tre fälten och
  eventuell bild.
- Förloppet ligger i databasen, inte i jobbminnet (som lever en timme). Därför
  finns det kvar efter omladdning.
- Kunden ser bara sina egna rapporter. En annan användare i samma arbetsyta ser
  dem inte utan Antons beslut.
- Snajps sida: listan i `FelOchEskaleringar` med rapportör, arbetsyta, sida och
  hela kedjan, plus ett prioriterat mejl med länk och utan kundtext.

##### 6. Den kodande agenten, bakom en människa

- Ingen automatisk vidarekoppling från kundens text till en agent som skriver
  kod. Anton eller Sebbe läser rapporten och trycker "Skicka till agenten".
- Först görs ett **arbetsunderlag**: sida, steg, förväntat, faktiskt och
  eventuellt händelse-id. Ett modellsteg utan verktyg (Vertex i EU, den modell
  som redan är godkänd för kunddata) förifyller det, kundens text kapslas som
  opålitlig, och en människa godkänner. Underlaget bär inga namn, adresser,
  kunddata eller bilder.
- Agenten är `scripts/felrapport_agent.py`. Den hämtar godkända underlag,
  arbetar i en egen arbetskopia från `origin/development` utan `.env.deploy`,
  utan Railway-nyckel och utan databas, verifierar mot `scripts/lokal_stack.py`
  och förhandsvisningar, och öppnar en ändringsbegäran mot `development` från
  grenen `fix/arende-<8 tecken>`.
- Agenten har en **egen GitHub-identitet** som bara får skriva innehåll och
  öppna ändringsbegäran. Den kan inte slå ihop, inte ändra arbetsflöden och
  inte nå hemligheter. `scripts/pr_granskning.py` fäller en sådan gren som rör
  `.github/`, `CODEOWNERS`, `db/migrations/`, `lib/auth*`, `proxy.ts` eller
  `scripts/railway*` utan Antons märkning.
- Repot är publikt. Gren, commit och ändringsbegäran bär därför bara
  ärendenumret och en teknisk sammanfattning, aldrig kundens ord.
- Körs för hand per ärende tills flödet är bevisat, sedan som fönsterlös
  schemalagd uppgift.

##### 7. Testversionen ("spegeln") bara för kundens inlogg

- En egen miljö hos Railway, `forhand`, med fyra tjänster (webb, api, databas,
  Redis), skapad tom av `scripts/railway_forhandsmiljo.py`. Den klonas aldrig
  från en befintlig miljö: en klon ärver mejltjänster, flyttvägar och synkjobb.
  Variablerna skrivs ur en vitlista, med egna hemligheter.
- Databasen byggs från noll per ärende och fylls av ett utdrag som bara
  innehåller **den kundens** arbetsyta. Development kopieras aldrig: den bär
  alla kunders data.
- Databasen märks `envags`, så utskick, inkorg och autopilot är avstängda av
  kod som redan finns.
- Inloggningen är stängd för alla utom kundens arbetsyta och plattformsadmin
  (variabeln `SPEGEL_ARBETSYTOR`, kontrollerad vid inloggning och i
  `getWorkspaceContext`). Saknas värdet släpps ingen in. Kontoskapande och
  inloggning via Google är avstängda där.
- Kunden kommer in med en **signerad engångslänk** ur rutan. Inga lösenord
  lämnar produktionen.
- Testversionen öppnas i en ny flik, eftersom den ligger på en annan adress.
  Det är det enda stället där regeln om ingen ny flik viker. Svaret på
  "Fungerade det?" lämnas alltid i den vanliga appens ruta.
- Första steget är en miljö och en kö: ett ärende i taget. En miljö per ärende
  är nästa steg med samma skript, när kön blir en flaskhals.
- Efter kundens svar, eller senast efter sju dagar, töms miljön.

##### 8. Vidare till development och main

- Kundens ja är information. Det ersätter aldrig granskningen.
- Anton eller Sebbe granskar och slår ihop ändringsbegäran till `development`.
- Till `main` går rättningen som alltid: release med Antons uttryckliga ord och
  hans handgrepp.

#### Hotbilden och vad som begränsar skadan

| Hot | Spärr |
|---|---|
| Kundens text styr en agent med skrivrätt i repot | Texten passerar ett steg utan verktyg och en människa innan agenten ser något; agenten kan bara öppna en ändringsbegäran |
| En felaktig eller elak rättning körs mot kunddata | Testversionens databas innehåller bara den rapporterande kundens rader och kan inte skicka mejl |
| Testversionen läcker | Den exponerar bara den kundens data, och bara för den kundens inlogg |
| Kunddata hamnar på GitHub | Felrapporten lagras bara i Snajps databas; GitHub får ärendenummer och teknisk text |
| Snajps agent skriver i fel kunds kunskapsbas | Kunskapsbasen skrivs bara genom kundens egen väg efter kundens klick |
| Snajps egna tal visas för kunden | `arbetsyta` sätts aldrig på hjälpchatten; statiskt test vaktar det |
| En besökande admin ser ut att vara kunden | Rapportören är alltid den inloggades eget id; besöket lagras för sig |
| Hjälpen stängs av trafik på marknadssidan | Egen kund i systemet med egna tak |

#### Faserna

Varje fas går att bygga, testa och visa för sig.

| Fas | Innehåll | Klart när | Kräver Anton |
|---|---|---|---|
| 0 | Exempelartiklarna rensas när eget innehåll läggs in | Tester visar att varje väg för eget innehåll tar bort exemplen i samma transaktion, att Snajps och Nordlys baser aldrig märks, och Kunskapsbas är sedd i bild | Nej |
| 1 | Hjälprutan med Fråga och Lär agenten | En inloggad testkund får svar ur Snajps kunskapsbas, ser samtalet efter omladdning och i en ny flik, och lägger till en artikel i sin egen bas från rutan; bilder på desktop och mobil | En nyckel för `snajp-hjalp` i Railway |
| 2 | Felrapport som ärende, Mina ärenden, adminlistan | En rapport syns direkt som Mottaget, finns kvar efter omladdning, syns i adminytan med full kontext; admin byter läge och kunden ser det; en annan användare ser den inte | Nej |
| 3 | Arbetsunderlaget och den kodande agenten | Ett påhittat fel i en förhandsvisning går från godkänt underlag till öppen ändringsbegäran utan fler handgrepp än startkommandot, och begäran bär ingen kundtext | Ja: GitHub-identitet, dataskyddsbeslutet |
| 4 | Testversionen och kundens svar | Miljön byggs från rättningens gren med bara testkundens arbetsyta; testkunden kommer in via länken, en annan kund nekas; ett utkast går inte att skicka där; kundens ja syns i ärendet och miljön töms | Ja: kostnaden hos Railway, läsrollen i produktionen |
| 5 | Automatiken | Tio riktiga felrapporter har gått hela kedjan med människan som enbart godkännare, byggtid och kostnad är uppmätta, och Anton har skriftligt släppt det manuella steget | Ja |

Fas 0 till 2 byggs direkt. Fram till att fas 3 och 4 är klara sköts rättningen
och testversionen av en människa bakom samma lägen, så kundens vy behöver inte
byggas om.

#### Kräver Anton

Bygget utgår från förvalet tills han säger annat.

1. **Repot är publikt.** `oloflun/snipe-leads` är publikt på GitHub, och
   `docs/compliance/` med 106 filer ligger incheckad. `docs/BESLUT.md` säger att
   repot är privat. Ska det bli privat igen? Planen håller i båda fallen, men
   det här bör avgöras oavsett.
2. **Den kodande agenten och dataskyddet.** Får agenten (Anthropic) läsa det
   avpersonifierade, människogodkända underlaget? Förval: ja, och inget annat.
   Då ska underbiträdet in i förteckningen i samma ändring. Det hänger ihop med
   delmålet om språkmodell-leverantören.
3. **Kundens data i testversionen.** Får en kunds arbetsyta kopieras till en
   egen miljö hos Railway? Förval: ja, bara den kundens rader, noterat i
   registerförteckningen.
4. **Kostnad.** Testmiljön kostar hos Railway. Uppskattat 10 till 15 dollar i
   månaden om den står hela tiden; inte uppmätt. Betalning och planbyte är
   Antons handgrepp.
5. **Konton och hemligheter.** En GitHub-identitet för agenten, en nyckel för
   `snajp-hjalp`, och inloggningen för läsrollen som gör kundutdraget.
6. **Hur mycket kunden ser.** Förval: de sex lägena ovan, inga interna steg.
7. **Vem som ser en rapport.** Förval: bara den som skrev den.
8. **Kundens ja.** Förval: information, aldrig ett godkännande som släpper något.

#### Risker

- **Tiden.** Nästa kund onboardas inom en vecka. Fas 0 till 2 hinns; fas 3 och
  4 hänger på beslut och konton. Säg det rakt till kunden: de första veckorna
  sköts rättning och testversion med en människa i ledet.
- **Snajps kunskapsbas är tunn.** Utan produkthjälp svarar Fråga svagt.
- **Kundutdraget är ny kod mot produktionsdata** med en roll som går förbi
  radspärrarna. Urvalet testas mot en påhittad databas med två kunder, och
  första körningen är en torrkörning som bara räknar rader.
- **Vitlistan för testmiljöns variabler.** Brister den kan riktiga mejl gå ut.
  Det testas uttryckligen.
- **Maskinens minne.** Den kodande agenten får inte köra samtidigt som de
  nattliga jobben.

#### Avvisat

- **En flytande chattbubbla.** Bryter mot regeln om att bygga in i befintlig
  yta, och Meny är redan hjälpingången.
- **Återanvända testchatten.** Den går till kundens agent och kunskapsbas och
  skickar med arbetsytans tal.
- **Felrapport som GitHub-ärende.** Repot är publikt.
- **Agenten i GitHub Actions.** Arbetsflödena står still och exponerar
  hemligheter för grenar.
- **Agenten med Antons egen GitHub-inloggning.** Den går förbi alla grenskydd.
- **Testversion som kopia av development.** Den bär alla kunders data.
- **Funktionsflagga per arbetsyta i produktionen.** Då måste rättningen släppas
  till main innan kunden testat, vilket vänder på ordningen.
- **Låta modellen ensam avgöra att något är en felrapport.** Ärendet skapas av
  kundens klick.
- **Samma lösenord i testversionen.** Då lämnar lösenordens kontrollsummor
  produktionen.
