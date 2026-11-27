# Status: hela Snajp i det nya gränssnittet

Uppdateras efter varje arbetspass. Planen: [`PLAN-MIGRERING.md`](PLAN-MIGRERING.md).
Senast uppdaterad: 2026-11-27.

Lägen: **klart** (byggt och verifierat), **pågår**, **väntar** (på kvot eller på Anton),
**inte påbörjat**.

## Fas 0: referensen och Antons ändringar

| Del | Läge | Not |
|---|---|---|
| Version 2 låst som referens | klart | `DESIGN-CRM.md`, minnesanteckning, bilder i `docs/crm/bilder/app/` |
| Antons tretton svar som beslut | klart | `docs/BESLUT.md` 2026-11-26 |
| Sidofältet marinblått i båda lägena | klart | Byggt och granskat i bild 2026-11-26. Väntar på Antons dom |
| Snajps logga i sidofältet | klart | Överst, leder till översikten. Väntar på Antons dom |
| Ockra som accent | klart | Markör och ikon för vald menypost. Väntar på Antons dom |
| Sökikon i mobilens toppfält | klart | Tillbaka i toppfältet (commit `bd1b5b81`) |

## Fas 1: kartläggning av den nuvarande appen

| Område | Läst | Kompletterat | Not |
|---|---|---|---|
| 1 Skal, inloggning, onboarding | klart | klart | `underlag/app-01`, 121 rader (SK). Kompletterat i "Tillägg vid kontrolläsningen" |
| 2 Översikt, Att göra, Lärande | klart | klart | `underlag/app-02`, 85 rader (OV). "Rättat vid kontroll" och stickprov |
| 3 Leads: översikt, pipeline, bolag | klart | klart | `underlag/app-03`, 104 rader (LR) |
| 4 Leads: körningar, listor, källor | klart | klart | `underlag/app-04`, 132 rader (LK) |
| 5 Leads: utkast, konversationer, samtal | klart | klart | `underlag/app-05`, 129 rader (LU). Kompletteringar i avsnitt K |
| 6 Support | klart | klart | `underlag/app-06`, 176 rader (SU). Kompletteringar i avsnitt M. `support-webb` delvis läst |
| 7 Kvitton | klart | klart | `underlag/app-07`, 141 rader (KV). Tillägg 2026-11-26 |
| 8 Inställningar | klart | klart | `underlag/app-08`, 109 rader (IN) |
| 9 Adminytan | klart | klart | `underlag/app-09`, 116 rader (AD) |
| 10 API:t under ytorna | klart | klart | `underlag/app-10`, 179 rader (AP) och 14 sidrader. 266 backendrutter |
| Luckgranskning | klart | | `underlag/app-99`: alla sidor, rutter, ändpunkter, komponenter och menyposter prickade; 14 rader för luckorna (LX), tio motsägelser (E1–E10) |
| Funktionslistan | klart | | `MIGRERING-FUNKTIONSLISTA.md`: 1 306 rader med plats, fas, backend och läge; 23 i fas 3, 480 i fas 4, 803 i fas 5. Navigering, nya mönster, ordningen och sekretessen |

Grinden för fas 1 (varje rutt under `app/` och varje ändpunkt i minst en rad) håller
enligt `app-99`. Kvar att avgöra av Anton: oklarheterna i funktionslistans sista avsnitt,
främst om webbplatsbedömningen grindas per roll eller per arbetsyta (E1). Läckan i
`signal_detalj` (LR-128) och driftdatan i supportöversiktens svar (E3) ska rättas före
fas 4 respektive fas 5.

## Fas 2: Twenty-inventeringen

| Del | Läge | Not |
|---|---|---|
| Områdena 1 till 13 | klart | Lästa och kontrollästa mot källan, 3 666 funktionsrader. Område 13 är handboken som facit (commit `7b9f7b14`) |
| Luckgranskning | klart | Tre granskare (front, server, facit). Fem verkliga luckor, fyllda med egna rader |
| Paritetslistan `PARITET.md` | pågår | Tio av sexton delar har läge (2 581 rader: 83 verifierade, 50 byggda, 480 delvis, 1 856 inte gjorda, 112 avstår). Bara område 12 är kontrollerat. Stoppat av veckogränsen för Opus, som nollställs 2 december |
| rea | klart | 484 operationer ur webbklienten. Servern gav inget |
| craft-anything | klart | Hoppas över enligt Antons svar. Skäl i `docs/BESLUT.md` |

## Fas 3: CRM-kärnan

| Del | Läge | Not |
|---|---|---|
| Kundsynken in som API | klart | `/api/crm/v1`. 181 tester i minnet och 16 mot Postgres |
| Migrationerna 160 till 168 mot Postgres | klart lokalt | Körda två gånger var mot PGlite (Postgres 17) genom psycopg2, och lagrets frågor prövade där. Inte körda mot Railway. Migration 168 lägger också ett partiellt index på leadsflödets tabell `prospects` (kundens spärrade leads), utan `concurrently`: skrivningar låses kort medan det byggs |
| Databasvägen i drift (asyncpg) | väntar | Hur asyncpg tolkar parametrarna är bara prövat i ett CI-jobb som inte körts, eftersom inget är pushat |
| Körning med inloggning mot den lokala stacken | inte påbörjat | Kräver Docker med Postgres och hela migrationskedjan. Vyerna är bara sedda i förhandsvisningen |
| Gränssnitt: översikt, bolag, personer, synk, utvecklare | klart | Version 2, godkänd |
| Tidigare kunder fria för Iris, uteslutning på nummer | klart | Bara backend, ingen yta behövs. `tests/crm/test_beslut.py` |
| Privatpersoner hoppas över som standard | klart | Migration 161 och växeln på anslutningen. Bilder i `docs/crm/bilder/fas3/` |
| Kontakta inte i CRM:et stoppar utskick | klart | Gäller också kampanjutskick och personerna hos ett märkt bolag |
| Tillägget som grind, fritt under provperiod | klart | `app/crm/tillgang.py`. Helsideläget när tillägget saknas är byggt. Ingen väg förbi för admin |
| Händelselogg, ändringsflöde och historik i postpanelen | klart | Migration 162. Bär fältens namn, aldrig värdena |
| Webhooks ut | klart | Backend och vyn under Utvecklare. Inte kört mot en riktig mottagare |
| Sortering nyast först, papperskorg, krockens id, namn på felrader | klart | Backend och vyer |
| Synkens två nivåer och supportärende | klart | Migration 163 och vyn. En körning med fel blir nu ett plattformsärende av sig själv, med systemet som rapportör, och numret står på körningen (`1a80affb`, `7c7e9907`). Provat mot minneslagret och PGlite, inte mot en riktig databas. Mejlet till Snajp om ett nytt ärende är inte provat mot en riktig mejltjänst |
| Affärer med steg och tavla | klart | Migration 164 (`2fa09eb3`) och vyn Affärer (`7fc9da8b`): tavla med dra och släpp, affärens panel, formulär, papperskorg. Sedd i förhandsvisningen, 1440 ljust och mörkt samt 390. Egna steg (namn, ordning, sannolikhet, typ, nya och borttagna) ändras under Anpassa stegen (`1b51e2e5`) |
| Uppgifter, anteckningar, aktiviteter | klart | Skrivs i historikfliken på bolag, person och affär (`e0a7cd21`), och ändras och tas bort där (`b7e93ea3`). Vyn Uppgifter samlar alla uppgifter, med ansvarig och beskrivning (`0d5257f9`). I den samlade listan väljs bara bolag för en ny uppgift |
| Bilagor | klart | Bilagor i databasen, 10 MB per fil och 500 MB per kund (Antons ja 2026-11-27). Fliken Filer i bolagets och affärens panel och i personens, med en binärsäker väg genom proxyn (`6fbd9c5d`). Proxyvägen är typkontrollerad men inte körd mot backenden |
| Tidslinje mot leads, mejl, samtal och ärenden | klart | `tidslinje.py`, nu också med CRM:ets anteckningar, aktiviteter, uppgifter och affärer, och en tidslinje för affären (`35672915`). Historikfliken i de tre panelerna läser den (`e0a7cd21`). Raderna från Iris leder till leadet och konversationen i Leads (`7509e4c9`). Supportärenden har ingen adress att länka till än |
| Utfall speglas åt båda håll | klart | `utfall.py`. Sätts i historikens skrivyta på ett bolag som är ett lead hos Iris, och läget hos Iris står i bolagets översikt. Ett lead som bett att slippa kontakt spärrar bolagets snabbval. Sett i förhandsvisningen, inte kört mot leadsflödet. Anteckningen sparas nu också vid Vunnen och utan lead, som en aktivitet (`dd0cb8db`) |
| Samlad kundlista, Iris och Egna | klart | `kundlista.py`, `GET /customers`, och väljaren Ursprung i vyn Kund (`b7e93ea3`). Ett vunnet lead för ett bolag märkt Ej aktuell visas inte (väntar på Antons bekräftelse) |
| Svensk standard i koden | pågår | Klart: organisationsnummer, moms, telefon, postnummer, bolagsform, SNI, privatperson, relationen Ej aktuell, förlustorsak ur lista, personens källa och insamlingsdag, spärrlista med NIX-uppladdning. Inte gjort: SEK-format i hela ytan |
| Bolagsuppgifter ur SCB:s företagsregister | klart, utan nyckel | `scb.py`, `/v1/lookup/companies` och `/v1/companies/{id}/enrich`, migration 167 (`05c16340`, `d8a29aaf`), och rutan i fliken Källa samt Hämta ur registret i Nytt bolag (`a0b35b45`). Bara bolagsnivå. **Inte prövat mot SCB:** `SCB_API_NYCKEL` finns inte, och utan den svarar uppslagen 503. Se beslutsloggen om nyckelns villkor |
| Gemensam spärrlista för alla kanaler | klart | Migration 166, `sparr.py`, `/v1/suppressions` (`69b8537e`, `a4e2c742`) och vyn Spärrar (`04badf37`, `b5173b30`). Sändspärren och ringlistorna i leadsflödet läser listan, och kontrollen läser också leadets telefonnummer. 359 tester gröna för CRM, utskick, ringlistor och ärenden. Sedd i förhandsvisningen |
| Tunna webhooks för personer och enskilda firmor | klart | Id, objekt, typ, tid och fältnamn, aldrig posten (`69b8537e`) |
| Hjälprutan i CRM:et | klart | Samma komponent som i arbetsytan, från sidofältets fot (`80db6b8c`). Sedd mot förhandsvisningens svar, inte mot hjälpens backend |
| Sammanställning: vad som ändras mot Twenty och varför | klart | `docs/crm/SVENSK-STANDARD.md`, 81 rader och tio frågor till Anton |
| Bildgranskning av de svenska CRM-systemen | inte påbörjat | Texten finns i `svensk-03` |
| Oberoende granskning av gränssnittet | gjord en gång | Tre granskare på Opus (kod, användbarhet, tillgänglighet) gav 36 fynd på affärstavlan, historiken och filerna, och de som gällde gränssnittet är rättade (`b7e93ea3`). En andra omgång på Spärrar, Uppgifter, stegdialogen och registret gav 40 fynd, rättade i `494eaea4` och i backendbygge 5 (`d005b36f`, `83ed8c57`, migration 168). Inte rättat: kryssrutans tryckyta på telefon, en logg över uppladdningar i API:t, och namnen direkt i svaret från `/tasks` |
| Ett jobb som tömmer papperskorgen | klart | `stadning.py` (`9967d7f1`): ett varv efter uppstart och ett per dygn, en kund i taget, av med `CRM_STADJOBB=0`. Raderar för gott efter 30 dagar, som utlovat i gränssnittet |
| Bolagets affärer i bolagets panel | klart | Raden Affärer i bolagets översikt, med länk till tavlan och Ny affär (`b7e93ea3`) |
| Bild på varje vy i Twentys hostade app | pågår | 17 bilder, mobilvyn gick inte att fånga |
| Testkonton i källsystemen | väntar | Kräver Antons ja per konto |
| Buddy | väntar | Inget avtalsdatum. Körs mot testkonto |

### Var supportsystemet kopplar in

CRM:et lämnar ifrån sig en rapport för varje synkkörning som slutar med fel. Sessionen som
bygger supportärendena läser den här och svarar med ärendets nummer:

- `GET /api/admin/crm/supportrapporter?utan_arende=true` (huvudnyckeln): rapporter som inget
  ärende tagit emot än, hos alla kunder, nyast först.
- `GET /api/admin/crm/supportrapporter/{kund}/{körning}`: hela rapporten. Räknare,
  anslutningens inställningar och gällande mappning, antal per felkod och varje felrad
  med kod. Felaktiga värden står med sin form (`99 99 99 9`), aldrig med innehållet.
- `POST /api/admin/crm/supportrapporter/{kund}/{körning}/arende` med `{"nummer": "F-7KQ2"}`:
  numret visas sedan för kunden på körningen.

Sedan 2026-11-27 skapar CRM:et ärendet själv (`supportrapport.py`): systemet är rapportör,
ärendet är internt, och samma anslutning som faller igen lägger en händelse på det öppna
ärendet. De tre vägarna ovan står kvar för de fall där inget ärende gick att skapa (kunden
saknar arbetsyta, eller flaggan `CRM_SUPPORTARENDEN` är av).
Kod: `snajp-support/app/crm/supportrapport.py`, `snajp-support/app/api/admin_crm.py`.

### Disken på C: (2026-11-26)

C: var full (0 MB) när affärstavlan skulle committas, och committen föll. Sessionen tog
bort sin egen byggcache (`.next` i det här worktreet, 846 MB) och lade därefter cachen på
D: genom en länk: `.next` pekar på `D:\snajp-crm-next\cache`, och `D:\snajp-crm-next\node_modules`
pekar tillbaka på worktreets paket så att byggstegen hittar dem. C: har omkring 0,8 GB
ledigt (1,6 GB den 27 november), vilket inte räcker för en full `tsc` eller en `next dev` i ett annat worktree.
Två andra byggcachar ligger kvar orörda och går att återskapa: `snipe-leads\.next`
(0,52 GB) och `.claude\worktrees\sharp-hermann-8c9577\.next` (0,5 GB). Mappen
`D:\snajp-crm-next-cache` (255 MB) är en överbliven första variant som gick inte att ta
bort härifrån.

### Det Anton behöver veta om tillägget

Också plattformsadmin möts av "tillägget saknas" i CRM:et för en kund vars provperiod är
slut. Slå på tillägget Snajp CRM på kunden under Admin, kunden, Tillägg. Det slår igenom
inom en minut. Kunderna ser inte tillägget i sin lista förrän CRM:et öppnas för dem.

## Fas 4: Leads i CRM-miljön

Påbörjad 2026-11-27 på Antons ord. Byggs i samma worktree och gren som CRM-kärnan (disken rymmer inte
ett andra worktree med egna paket). Beställningarna för varje steg ligger i sessionens scratchpad
(`ui-gemensamt.md`, `ui-steg-4-*.md`), och arbetsflödet heter `crm-ui-steg`.

En rad per vy, i byggordningen ur funktionslistans avsnitt "Ordningen" (där steg 4.7 här är delat i två och bolagssöket står som eget steg). Raderna i
funktionslistan som hör till vyn står i noten.

| Steg | Vy | Läge | Not |
|---|---|---|---|
| 4.1 | Skalets förutsättningar: gruppen Iris, banderollen, notisräknaren, läsroll och kundbesök i `app/crm/layout.tsx` | byggt och granskat, inte kört inloggat | `6c8e0242`, `15968282`. SK-038–SK-045, SK-064, SK-067–SK-079, SK-155–SK-157, AD-005, AD-008–AD-011. Navigeringen är ett register (`lib/crm/navigering.ts`), banderollen bär kundbesök, läsroll, vybyte och demo, klockan öppnar notislistan. SK-039 är halvt: se "Öppet efter 4.1 och 4.2" |
| 4.2 | `/crm/iris/leads` med panelen `?lead=` | byggt och granskat, inte kört inloggat | `07f34196`, `6a017538`, `3b93e04c`. LR-001–LR-075, LR-090–LR-114 utom de som hör till 4.3, 4.9, 4.11 och 4.12. Webbgrinden sitter i `lib/crm/iris/webb.ts`: ytan visar bedömningen bara när svaret bär fälten. `signal_detalj` behövde ingen rättning (se beslutsloggen) |
| 4.3 | Utkastredigeraren och `/crm/iris/utkast` (Att granska, Skickas snart, Skickat) | byggt och granskat, inte kört inloggat | `fb8003e9`, `bf669477`, `c8985e14`. LU-030–LU-070, LU-080–LU-088, LU-150–LU-159, LU-172–LU-183, AP15. Redigeraren (`iris/Utkastredigerare.tsx`) används av utkastvyn, leadets panel och körningens sida. LU-032 och LU-174 hör till Iris-översikten, LU-081 till konversationerna, LU-158 till listorna, LU-179 till inställningarna |
| 4.4 | `/crm/iris/korningar` och `/crm/iris/korningar/[id]`, dialogen Kör Iris | byggt och granskat, inte kört inloggat | `4455670d`, `a92d9d3b`, `c8985e14`. LK-001–LK-057, LK-135–LK-138, OV-031, OV-032, OV-037. Demons exempelkörning (LK-015, LK-130–LK-133) väntar på steg 5.22, adminens testkörningar (LK-016, LK-134) hör till admin-loggen, diagrammen (OV-033–OV-036) till Iris-översikten |
| 4.5 | `/crm/installningar/iris` | byggs 2026-11-27 | LK-060–LK-073, IN-100–IN-112, IN-144 |
| 4.6 | Tråd- och inkorgsvyn och `/crm/iris/konversationer` | byggs 2026-11-27 | LU-001–LU-024, LU-081, LU-089, LU-110–LU-122, OV-105 |
| 4.7 | `/crm/iris/uppfoljningar` | inte påbörjat | LU-100–LU-107 |
| 4.8 | `/crm/iris/samtal` | inte påbörjat | LU-130–LU-138, LU-170, LU-171 |
| 4.9 | `/crm/iris/listor` med import och säljlista | inte påbörjat | LR-120–LR-135, LK-100–LK-118, LK-142–LK-151 |
| 4.10 | `/crm/iris/kampanjer` | inte påbörjat | LU-160–LU-162 |
| 4.11 | `/crm/iris` Iris-översikten | inte påbörjat | LR-020–LR-027, LU-024, LU-032, LU-174 |
| 4.12 | Bolagssöket i kommandopaletten | inte påbörjat | LR-080–LR-082 |

### Öppet efter 4.1 och 4.2

Det här är byggt i kod och sett i förhandsvisningen (påhittad data, anropen besvaras i webbläsaren).
Inget av det är kört inloggat mot en riktig backend.

1. **Läsroll och kundbesök i de äldre vyerna (SK-039).** Hjälparen `useSkrivratt()` finns i `kit.tsx` och
   används av skalet och Iris leads. Bolag, Personer, Affärer, Uppgifter, Synk, Spärrar och Utvecklare
   stänger inte av sina skrivande knappar än: proxyn stoppar skrivningen, men knappen ser tryckbar ut.
   Det är ett eget steg, efter fas 4.
2. **Demoläget med påhittade leads** (LR-009, LR-010, LR-052, LR-095) är inte byggt. Det hör ihop med
   steg 5.22, som väntar på Antons beslut om demon.
3. **Radanimationen när ett lead byter status** (LR-059) är inte byggd.
4. **Notiserna under ett kundbesök.** `POST /leads/notiser/last` skulle svara 422, eftersom proxyn lägger
   till `is_test` och modellen inte tar emot okända fält. Knappen Markera alla som lästa är därför
   avstängd under ett besök, med förklaring.
5. **Ifyllnaden vid Flytta till Iris.** Backenden svarar med meningar i `saknas`, inte med fältnamn, så
   gränssnittet kopplar meningen till fältet efter hur den börjar. Ändras formuleringen i
   `befordran.py:saknade_falt` hamnar meningen i en lista ovanför fälten. En fältnyckel i svaret vore
   säkrare.
6. **Texterna Kontakt och Dataskydd i arbetsytemenyn** är chattens formuleringar och kan behöva egna ord.
7. **Skicka på testytan:** innan rutan är ikryssad står knappen avstängd med texten "Skicka 0 mejl".
   Formuleringen bör bedömas.
8. **Inte sett i bild:** vybytets förlopp i banderollen, felrutan i panelens flikar när ett lead inte går
   att hämta, och fokusflytten efter statusbyte med tangentbordet. Lästa i koden.

### Öppet efter 4.3 och 4.4

1. **Styrningen av en vilande körning är byggarens val, inte Antons.** Pausa visas inte för en körning
   som vilar (letar vidare en gång per dygn), eftersom Återuppta väcker motorn direkt, utanför vilans
   takt. Avbryt står kvar. Dagens app visar Pausa även då. Anton bör bekräfta.
2. **Logik som är kopierad.** `delaMejl` och `forstaMening` ligger som kopior i `lib/crm/iris/mejl.ts`,
   eftersom dagens komponenter inte får röras och originalen ligger i `components/leads/`. Vid växlingen
   (fas 6) ska en av dem bort.
3. **Uppföljningarnas förlopp minns webbläsaren.** Det finns ingen ändpunkt som listar pågående
   uppföljningsjobb, så vyn sparar i `localStorage` vilka leads den följer och läser läget per lead. På
   en annan enhet syns förloppet först när uppföljningen står under Att granska.
4. **Inte sett i bild:** loggan i signaturen, mörkt läge på telefon, Tillbaka till Iris och en lyckad
   Ändra tid, och utkastet för ett lead utanför köns 200 nyaste på körningens sida. Läsroll och
   kundbesök är sedda av orkestratorn i 1440 för Utkast och Körningar.
5. **Kapplöpningarna** (byte av post medan AI:n svarar, två svar i fel ordning) är rättade i koden och
   lästa, men inte framkallade med fördröjda svar i webbläsaren.

### Saknas i backenden (samlat under fas 4, inget är byggt runt)

Gränssnittet visar det backenden svarar. Det här är ställen där ett fält eller en ändpunkt hade gjort
ytan bättre. Inget av det stoppar bygget, och inget är ändrat i `snajp-support/`.

| Vad | Följden i gränssnittet i dag |
|---|---|
| `befordra` svarar med meningar i `saknas`, inte med fältnamn | meningen kopplas till fältet efter hur den börjar |
| `processa-om` tar inget önskemål (bara konversationens `/utkast/generera` gör det) | fältet för önskemål visas bara där ytan tar emot det |
| Handlingskontrollen (`handlingar`) finns bara för konversationens svarsutkast | kön och leadets utkast har ingen kontroll av påståenden |
| Email Studio saknar åtgärden "längre" som AP15 nämner | åtta åtgärder, inte nio |
| Kön listar bara utkast som väntar på granskning | ett stoppat utkast syns med sitt skäl i leadets panel, inte i Att granska |
| Ingen ändpunkt listar pågående uppföljningsjobb | förloppet minns webbläsaren (punkt 3 ovan) |
| Ingen `GET /leads/queue/{id}` | utkastet på körningens sida byggs ur körningens svar, och AI-hjälpen saknar bolagets bakgrund för utkast utanför köns 200 nyaste |
| `GET /leads/korningar/{id}/utkast` bär inte `pafylld` och `pafylld_skal` | hela leadslistan hämtas för att märka påfyllda leads |
| En körning med egna bolag har inget motortillstånd i liggaren | körningens sida kan inte lista bolagen och hänvisar till Leads |
| Sammanfattningen och trattens steg och skäl är bara på svenska | de visas som de står även på engelska |
| `POST /leads/notiser/last` tar inte `is_test` | Markera alla som lästa är avstängd under kundbesök |

## Fas 5: resten av appen

| Steg | Vy | Läge | Not |
|---|---|---|---|
| 5.1 | Inställningsskalet `/crm/installningar` | inte påbörjat | IN-001–IN-018 |
| 5.2 | Inställningar: Företaget, Vad ni säljer, Kunskapsbas, Så ska agenten låta | inte påbörjat | IN-012, IN-020–IN-042, SU-120–SU-133, IN-146 |
| 5.3 | Inställningar: När agenten får svara själv, Inkorgar | inte påbörjat | IN-050–IN-076, SU-140–SU-168 |
| 5.4 | Inställningar: Kanaler, Integrationer (nya ytor) | inte påbörjat | SU-105–SU-107, SU-212, SU-213, IN-160–IN-166 |
| 5.5 | Inställningar: Team, Plan och fakturering, Tillägg, Notiser, Tema, Dataskydd, Kvitton | inte påbörjat | IN-080–IN-095, IN-120–IN-125, IN-143, IN-145. IN-083 saknar ändpunkt |
| 5.6 | Inställningar: Plattformen (instruktioner, tvåstegsverifiering) | inte påbörjat | IN-130–IN-137, AD-110–AD-116, SK-048 |
| 5.7 | `/crm/kundtjanst` med Översikt, Ärenden, Testmail, Dolda | inte påbörjat | SU-001–SU-064. Driftdatan (E3) grindas i backenden först |
| 5.8 | `/crm/kundtjanst/testchatt` (chattvyn) | inte påbörjat | SU-007, SU-070–SU-088 |
| 5.9 | `/crm/kundtjanst/overlamnade` | inte påbörjat | SU-100–SU-110, SU-207–SU-211, SU-218. Beslut om portalen väntar på Anton |
| 5.10 | `/crm/att-gora` | inte påbörjat | OV-060–OV-079, KV-170 |
| 5.11 | `/crm/larande` | inte påbörjat | OV-080–OV-091 |
| 5.12 | `/crm` Översikt utökad med agentavsnitt och Kom igång | inte påbörjat | OV-020–OV-048, OV-101, SU-126, SU-190, AD-138 |
| 5.13 | `/crm/kvitton` (Översikt, Kvitton, assistenten) | inte påbörjat | KV-01–KV-208. Vilande, bara plattformsadmin |
| 5.14 | `/crm/admin` Admin-översikt | inte påbörjat | AD-020–AD-027 |
| 5.15 | `/crm/admin/kunder` och `/crm/admin/kunder/[id]` (fyra flikar) | inte påbörjat | AD-030–AD-077, LK-126, LK-127 |
| 5.16 | `/crm/admin/paket` | inte påbörjat | AD-100–AD-105, IN-094, IN-095, KV-171 |
| 5.17 | `/crm/admin/logg` och `/crm/admin/logg/[id]` | inte påbörjat | AD-080–AD-094, AD-130, AD-131, LK-134, KV-172 |
| 5.18 | Plattformsadmin i skalet: Byt kund, Admin/Demo, driftkort | inte påbörjat | AD-001–AD-018, AD-137–AD-139b |
| 5.19 | `/login` och `/auth/reset` i CRM:ets form | inte påbörjat | SK-020–SK-037, SK-130–SK-138, SK-175–SK-188 |
| 5.20 | `/onboarding` i CRM:ets form | inte påbörjat | SK-110–SK-127, SU-190–SU-192 |
| 5.21 | Installera som app, offline, kundens domän | inte påbörjat | SK-001–SK-010, SK-150–SK-154, SK-170–SK-174 |
| 5.22 | Luckorna: demon, Duo-demon, demobokningen | inte påbörjat | LX-001–LX-015. Väntar på Antons beslut |

## Fas 6: växlingen

Inte påbörjat.

## Befintliga filer som ändrats utanför CRM:ets egna mappar

| Fil | Ändring | Commit |
|---|---|---|
| `app/globals.css` | Tailwinds grundstilar i kaskadlagret `tw-base` | e86d6675 |
| `lib/routes.ts`, `proxy.ts`, `lib/i18n.tsx`, `components/AppShell.tsx` | Rutten `/crm`, menyposten för plattformsadmin | e86d6675 |
| `tests/invariants/test_inv_ui_001.py` | `app/crm` och `components/crm/app` i grindens lista | e86d6675 |
| `snajp-support/app/api/deps.py`, `main.py`, `storage/*.py`, `leads/scheduler.py` | Nycklar med omfång, CRM-bolag som upptagna, kundadresser i sändspärren | 1cc6ff4d |
| `scripts/gdpr_radera.py`, `.github/workflows/verify.yml` | CRM-tabellerna i raderingen och i databastesterna | 1cc6ff4d |

## Kvoten

Veckokvoten 64 procent 2026-11-26. Se planens avsnitt 5.
