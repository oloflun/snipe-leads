# Beslutslogg

Varje nytt beslut om produkten skrivs här med beslutsfattarens eget resonemang,
så att skälet går att följa efteråt (Antons regel 2026-10-10). Nyaste överst.
Ett beslut som ersätts stryks inte: det får en rad om vad som ersatte det.

Format: datum, vem, beslutet, resonemanget (så nära beslutsfattarens ord som
möjligt), vad det betyder i koden.

---

## 2026-10-19 (Anton) — Live-skrivning, tydligare studs, inga tekniska referenser i demon

**Beslut.** "Testa göra skuggan i heron svagare, eller skippa den helt. Gör
även animeringarna för rutorna jämnare och mjukare, och gör
studsseffekten/tillbakafjädringen tydligare. Skapa även effekten att texten
skrivs live, för alla omgenereringar/knappval också, ta även bort alla
tekniska referenser, endast korta motiveringar."

**Resonemang (Anton).** Skuggan bakom ingressen syntes som en skugga. Studsen
var för subtil för att märkas. Demons svar ska kännas som att agenten skriver,
och motiveringarna ska läsas av en kund, inte av en utvecklare.

**I koden.** Den ovala mörkningen är borta; på mobil bär ett mjukt mörkare
band i fotot läsbarheten (5,3:1). Fjädern 0.75/0.75 → 0.66/0.95 (studs ~11 px,
mjukare glidning). `LiveText` skriver fram showcase-utkasten när rutan landat;
demons omskrivningar skrivs fram i rutan och panelen visar bara en kort
motivering (marknadssidan; arbetsytan oförändrad). Startsidans exempelmejl
fick egna svar (`lib/data/emails.ts`), förut svarade varje knapp att demot
bara fanns för andra bolag. Prompten ber inte längre modellen hänvisa till
principer och filer, och `utanReferenser` stryker meningar som ändå gör det.
Kvar: de sex /demo-bolagens motiveringar nämner "CTA" och har pilscheman.

## 2026-10-19 (Anton) — Startsidan: ytor glider in på en fjäder, två upprepande sektioner bort

**Beslut.** "Jag vill att själva rutorna rör sig in mjukt på skärmen och att
enbart den beskrivande texten revealas istället, en ruta i taget, inte båda
samtidigt … mjuk och glida in stoppa och studsa tillbaka lite, men väldigt
subtilt, tänk apple." Samma för den stora översikten. "Ta bort sektionen
längre ned med i princip samma punkter, samma sak med den andra sektionen om
Snajp, låt byggt i Göteborg-sektionen vara kvar." Rubriken "Ni ser
resultaten, inte maskineriet." blir "Förvärmda leads, levererade till er."
Hjältens ingress ljusas upp, och mellanrummet mellan löftet och första rutan
stängs.

**Resonemang (Anton).** Rutorna var "laggiga och vibrerar vid scroll, särskilt
om man scrollar fram och tillbaka", och en tonad avtäckning läste inte som att
något kom in på skärmen. "Tre steg" upprepade löftets punkter direkt under
hjälten, och "Vilka är vi" upprepade "Byggt i Göteborg". Ingressen var
"knappt läsbar mot herobilden".

**I koden.** Vibrationen hade en mätbar orsak: `.rise` lade en CSS-transition
på samma `transform` som GSAP skrubbade varje bildruta. Den skrubbade driften
och klippningen är borta; i stället `caseEntry` (`useLandingMotion.ts`,
markup `data-case`/`data-case-box`/`data-case-text`) med Apples fjäder som
GSAP-ease (`gsap.js: spring(0.75, 0.75)`), som spelar en gång och köar ytorna.
Sprängskissens linjer räknas ur perspektivet i stället för fyra
`getBoundingClientRect` per bildruta, och `anticipatePin` är borttagen.
"Tre steg" och "Vilka är vi" är borttagna ur `LandingPhoto.tsx` och copyn
(`steps`, `stepsHeading`, `vilka*`); länken "Läs mer om oss" flyttade till
Byggt i Göteborg. Regeln står i `DESIGN.md` § Ankomstfjädern.

## 2026-10-18 (Sebbe) — Körningar på upp till 200 leads, rullbar leadslista och levande lägesrad

**Beslut.** "Ändra så att man kan söka upp till 200 leads … håller lika bra
kvalitet och att företagen man filtrerar, alla 200 ska vara bra företag …
relativt snabb att hitta alla leads." Vid 50+ leads visas körningens leads i
en låda som går att rulla och dra ut i höjdled, med samma snabbklick per lead
till utkastet som förut. I körningsvyn byter "Researchar" till nya
formuleringar ("Hittar dina nästa kunder…", "Gräver i registren", …) var
tionde sekund, med en diskret intoning.

**Resonemang (Sebbe).** Taket 50 var för lågt för volymkörningar. Kvaliteten
ska inte sänkas med volymen: samma grindar (förfilter, existens, Jev,
bedömning, utkastgrindarna) per bolag som vid 50. Sidan ska inte bli
kilometerlång vid 200 leads, och väntetiden ska kännas levande, inte stå
stilla på ett ord.

**I koden.** `LeadsBatchRequest.limit` le=50 → 200 (`app/api/schemas.py`),
formulärets max/hint (`components/leads/LeadsRunForm.tsx`). Kredittaket
`korning.korningstak` höjt 600 → 2400 så 12 hämtningar/lead gäller även vid
200 — annars hade en 200-körning svalt vid 3/lead; motorns övriga tak
(`TAK_FAKTOR`, `max_rundor`, `TOMMA_RUNDOR`) skalar redan med målet, och
kvalitetsgrindarna är oförändrade per bolag. Rullbara lådan vid 50+ rader:
`KorningensUtkast.tsx` (RULLBAR_FRAN) och `IrisKorningar.tsx:rullbarLista`
(även tratten). Lägesraden: `RoterandeStatus` + fraslistorna i
`IrisKorningar.tsx`, intoningen `@keyframes statusbyte` i `app/globals.css`
(släcks av prefers-reduced-motion).

---

## 2026-10-18 (Anton) — Startsidan: Dygnets dygnsljus, mjuka övergångar, isärtagen översikt, fetare serif

**Beslut.** Startsidan behålls som den är (hjälten, bilderna, alla sektioner,
uppdelningen Leads/Support, de konstruerade produktytorna) och får ovanpå det:
Dygnets dynamiska dygnsbakgrund som börjar i soluppgång under hjälten och blir
varmvit längst ned, vackra övergångar och effekter mellan alla sektioner, en
enstaka dynamisk bild av dashboarden där elementen delas upp som i
Isärtagning men utan lutning, texten (inte rubriken) från "Varför Snajp finns"
på /vart-team under "Byggt i Göteborg", och ett fetare serif-typsnitt som inte
är Fraunces. "Gör allt detta mjukt."

**Resonemang (Anton).** Av de fem koncepten på boarden kom nummer 1 (Dygnet)
närmast estetiskt; i stället för fem nya koncept ska den riktiga sidan ta över
Dygnets ljus och ambitionsnivån i rörelsen, med befintligt innehåll.

**I koden.** `components/marketing/useLandingMotion.ts` (GSAP 3.15 + Lenis via
repots `gsap.js`/`smooth-scroll.js`, dynamiskt importerade eftersom de rör
`window` vid import): dörren, ljusmotorn (mark `--ground` + fyra ljusrutor i
multiply, hål för hjälten och produktytorna), radmaskade rubriker, klippta
avtäckningar, parallax, ord som fylls av skrollen, ritade sektionslinjer och
den pinnade sprängskissen. `components/marketing/DashboardIsar.tsx`: översikten
(demo, exempeldata) i fyra delar ur samma skärmdump. `LandingPhoto.tsx` bär
`data-mo`-markörer och `key` per produkt+språk på rubriker som SplitText
spaltar.

*Agentens val, att pröva (Anton):* serifen är **Source Serif 4** (variabel vikt
200–900, optisk storlek, äkta kursiv): lägre kontrast än Fraunces och
Newsreader, så den bär vikt över hjältefotot. Den är scopad till
marknadssidan via klassen `serif-fet`; appytorna behåller Fraunces tills Anton
säger annat. Inga nya foton lades till: beställningen tillät det men krävde det
inte, och sprängskissen använder produktens egen yta. Lenis lever kvar i
sessionen efter att man lämnat startsidan (en skrollägare, som husets regel
säger); inre skrollytor i demon behöver `data-lenis-prevent` om de visar sig
fastna. Den gamla `.rise`-avslöjningen (useReveal) används inte längre på
startsidan; klasserna står kvar och är verkningslösa där.

**Rättningar samma dag efter Antons första titt** ("dashboarden vibrerar och
hackar och hoppar åt sidan", "bakgrunden helt borta", "lägg till text",
"animationer för showcase-rutorna"): dygnet sträcks över hela sidan och når
varmvitt först vid priset (det nådde vitt redan vid demon); marken ritas på
ett eget fast lager i stället för en variabel på roten (en variabel räknade
om stilen för hela sidan varje bildruta); sprängskissens kamera drar sig inte
längre tillbaka (skalan .94 flyttade översikten 35 px i sidled och lästes som
ett hopp), ljusets hål har decimaler (hela pixlar gav kanter som hoppade) och
delarna är egna hål. Sektionen fick en rubrik och en ingress: **ny copy, inte
godkänd av Anton än** ("Hela dagen på *en skärm*." / "Översikten visar vad
agenterna gjort: körningar, levererade leads, det som väntar på en människa
och vad det kostat. Varje del uppdateras medan Iris arbetar."). Showcase-
rutorna (ProduktBilder) fick liv: delarna kommer i berättelsens ordning när
figuren avtäcks och utkasten skriver sig själva uppifrån; bara element
animeras, aldrig textnoder, eftersom React äger texten.

**Andra varvet samma dag** ("det ser fortfarande för jävligt ut": rubriker
och showcase-delar osynliga, dashboarden hackar, ingen tydlighet):

- *Avslöjandena är idempotenta.* Första versionen byggde varje avslöjande som
  en `gsap.from` med engångs-ScrollTrigger, skapad om i SplitTexts `onSplit`;
  varje omspaltning (fontbyte, storleksändring, dev-serverns hot reload) dolde
  redan visade element igen utan att en ny trigger spelade dem. Nu döljs ett
  element högst en gång och visas av `play()`, som stämplar `data-rv="1"` och
  är en no-op andra gången; ScrollTrigger, en IntersectionObserver och en
  timer kan alla kalla den. Verifierat i riktig Chromium 1920 med hjulet hela
  vägen ned: 0 dolda element.
- *Hackandet var mätt, inte gissat.* Bildrutetider i riktig Chromium med GPU:
  allt på 31 % tappade bildrutor (p95 50 ms); utan multiply-blandningen
  0,8 % (p95 17 ms). Dygnet-konceptet självt låg på stadiga 30 fps med samma
  teknik. Ljuslagret ligger nu under innehållet (ogenomskinliga ytor täcker
  det, inga hål), komponeras med vanlig alfa (rutorna målas i markens färg i
  stället för multiply), rutorna skalas med transform i stället för att byta
  bredd, och oskärpan byts i steg om 3 px. Resultat: p95 17 ms, 0,9–2 %
  över 33 ms, allt på. Lenis vaktar dessutom mot en andra instans vid hot
  reload (`smooth-scroll.js`).
- *Sprängskissen fick avsikt.* Texten står inne i det pinnade blocket till
  höger om bilden (rälen sitter till vänster: linjer från vänster försvann mot
  den), tre förklaringar tänds i tur med en ritad linje och en prick vid sin
  del, grundbilden byts mot en förblurrad tvilling (oskärpa rastrerad en gång),
  och kameran drar sig inte tillbaka. Förklaringarnas ord är produktens egna
  paneltitlar; rubrik, ingress och förklaringar är ny copy att godkänna.
- *Showcase-rutorna rör sig.* Figurerna glider mjukt mot sidan medan de
  passerar (den andra lite senare än den första), avtäcks nedifrån med en
  liten skalning, och delarna inne i ytan kommer i berättelsens ordning.

---

## 2026-10-17 (Anton) — Main blir sanningen efter första synken; körningar i development flyttas aktivt

**Beslut.** Alla körningar från development följer med till main, utom de som
är märkta som testkörningar. "Datan måste speglas sömlöst. När vi fått över
alla körningar från development blir main sanningen och synkar till
development, och körningar gjorda i development behöver flyttas aktivt enligt
tidigare principer." Ersätter tvåvägssynken (2026-10-10, nedan).

**Resonemang (Anton).** Se citatet. Development går tillbaka till att vara en
spegel av produktionen, med den skillnaden att körningarna som gjorts där
fram till releasen följer med en gång.

**I koden.** `scripts/railway_synk.py`: `--apply --forsta` för över allt
åt båda hållen med development som vinnare (som förut) och sätter
`mirror_meta.lage = 'envags'`. Därefter skriver synken bara till development:
main vinner varje skillnad, raderingar i main slår igenom, och rader som bara
finns i development står kvar tills de flyttas med Byt kund → Flytta till main
(`admin_flytt`). Provkörningar synkas aldrig.

*Agentens tolkning, att pröva (Anton):* development skickar inga utskick i det
här läget (`scheduler.skickas_har`, `utskick_bara_i_main`). En spegelrad som
development skickade hade fått tillbaka main:s status vid nästa synk och kunnat
gå ut en gång till. "Godkänn och skicka" i development svarar att utskicket görs
i main efter en flytt. Det ersätter "det måste gå att skicka utskick från
development också" (2026-10-10). Första synken skriver om `godkand_i` från
development till main på de köade utkasten (193 st., godkända 2026-10-12–16),
så att main skickar dem när sändfönstret öppnar måndag 08:00. Provmejl
påverkas inte.

*Att veta (agenten):* första försöket fyllde development-databasens volym
(500 MB, skapad på provplanen) när synken kopierade tabellerna, och Postgres
kraschade. Volymerna i båda miljöerna är nu 5 000 MB (Hobby-planens tak), utan
kostnad utöver använt utrymme.

## 2026-10-17 (Sebbe) — Duo i fokus, ingen Trio; Kvittohanteraren blir tillägg till Support

**Beslut.** "Ta bort den från marknadssidorna och priserna också. Det ska vara
en tilläggstjänst till supporten. Main fokus är att det ska finnas Snajp duo,
inte trio."

**Resonemang.** Följer beslutet nedan samma dag: Kvittohanteraren ska inte
säljas än. När den kommer tillbaka är den ett tillägg till Support, inte ett
eget paket, och paketet Snajp säljer är Duo.

**I koden.** `lib/pricing.ts`: paketen är Support, Leads och Duo; Trio och
"Snajp Kvitton" (2 690 kr) är borttagna, liksom kampanjen à 999 kr.
`KVITTO_TILLAGG` beskriver tillägget (kräver Support, pris inte satt). Adminens
paketflik har en kryssruta för tillägget; det skrivs som produkten
`bookkeeping` bredvid paketets, så en kund som hade Trio läses som Duo +
tillägget utan migration (intäktsberäkningen räknar dem som Duo tills
tillägget har ett pris). Marknadssidorna: produktväxeln och demopanelerna
visar bara Leads och Support (`saljbaraProdukter`), `/kvitton` och
`/bokforing` leder till `/support`, demolänken, FAQ-frågan om kvitton och
"alla tre agenterna" är borta, och Snajps supportchatt (`snajp_kb.py`) säger
tre paket. Kvittosidans texter och demo står kvar i koden för en lansering.
Användarvillkoren (`/villkor`) är inte ändrade.

## 2026-10-17 (Sebbe) — Kvittoagenten står på is: mörklagd för kunder, borta ur utkasten

**Beslut.** "Kvittoagenten ska inte vara i fokus för Snajp att sälja. Den ska
vara mörk till vänster i menyn på arbetsytan och som kund ska man inte kunna
klicka in på den. Den ska inte heller finnas med i utkasten. Vi i admin ska
absolut kunna använda den." Utkast som bara handlar om kvittoagenten tas bort;
utkast som också nämner en annan agent behålls, kvittotexten redigeras bort
och utkastet skickas.

**Resonemang.** Snajp ska inte sälja Kvittohanteraren än, utan hålla den på
is ett tag till. Kunden ska ändå kunna se att den finns ("man ska ändå kunna
se att det står Kvitto"), men inte öppna den.

**I koden.** `VILANDE_PRODUKTER = ["bookkeeping"]` i `lib/routes.ts`.
Kundens `products` filtreras i `resolveDashboardState` (admin behåller dem),
så menyn, `WorkspaceSection`, Att göra och kvittoproxyn säger samma sak.
Railen ritar posten som ett mörklagt `<span>` utan länk ("Kommer snart"),
och en kund som skriver adressen landar på översikten. Demon gör likadant.
Plattformsadmin når Kvitton som förut via adminytan. Kunder som har paketet i
databasen (Umeå Webbdesign och Alunix i main) behåller det där: det är
visningen som pausas, inte avtalet. Snajps Iris i development: Kvittohanteraren
borttagen ur produkterna, erbjudandevillkoren, segmenten och affärskontexten
(`scripts/snajp_malgrupp.py`), och Iris-instruktionen säger att kvitton och
bokföring aldrig nämns. 12 osända utkast som bara sålde Kvittohanteraren
avvisades (sju godkända som väntade på sändfönstret, fem i granskningen), och
uppföljningen till Investbygg fick ordet "kvittoredovisning" borttaget och
godkändes. Main hade inga kvittoutkast. Släpps igen genom att tömma listan och
lägga tillbaka produkten i `snajp_malgrupp.py`. Marknadssidorna, priserna och
supportchattens kunskapsbas säljer den fortfarande; de är inte ändrade.

Tillägg 2026-10-18: uppföljningssvepet i main skrev ändå nya
kvittouppföljningar (fyra på två dygn), eftersom det följer upp tråden och
modellen läser det tidigare mejlet. En tråd vars utgående mejl nämner en
vilande produkt följs inte längre upp (`app/leads/vilande.py`, kontrollen i
`follow_up_generator._en_uppfoljning` före modellanropen).

## 2026-10-17 (Sebbe) — Utkastkedjan köar den renaste versionen, inte den sista

**Beslut.** "Ja, kolla varför mallorden överlever grinden." Utredningen gav
rotorsaken, och fixen är att varje humaniserad version prövas av stilgrinden
och att den med minst fynd köas.

**Resonemang.** Skarpa provet på fem Snajp-leads köade "kräver fullt fokus"
(Nordic Express) och "tar tid från att" (Moogio). Stegloggen visade att båda
gått alla omskrivningsvarv och att frasen kom in i en omskrivning eller i den
sista humaniseringen, som aldrig prövades. Över 250 körningar: 194 gick alla
varv, 96 köades med kvarvarande fynd, och 60 av dem hade en tidigare version
med färre. En omskrivning kan alltså göra mejlet sämre, och kedjan behöll
ändå den sämre.

**I koden.** `run_outreach_draft_v2`: urvalet bland de humaniserade
versionerna. Kvar: omskrivningen själv skriver in nya mallord (45 av 250 har
fynd även med urvalet), och det är en promptfråga för nästa runda enligt
referensens avsnitt 8.

## 2026-10-17 (Sebbe) — Skapa om utkast skriver bara utkastet, ur sparad research

**Beslut.** "Bygg skapa om bara utkast utan ny research." Knapparna Skapa
utkast och Skapa om utkast i Iris-listan skriver nu ett nytt mejl ur leadets
sparade research i stället för att köra hela kedjan igen.

**Resonemang.** Öppen punkt i utkastreferensen (avsnitt 8.5 och 9): när 104
utkast skrevs om med Skapa om 2026-10-16 researchades bolagen om, och 23 föll
till nivå C på en ny bedömning av ett bolag som redan var godkänt. En
omskrivning av mejlet ska inte kunna ändra bedömningen, och den ska inte
betala för sidhämtning och research en gång till.

**I koden.** `scope="utkast"` på `POST /api/leads/prospects/processa-om`.
Underlaget läses av `app/leads/sparad_research.py` ur bolagets senaste
`leads_research`-körning: posten `underlag:utkast` som researchsteget skriver
sedan i dag, annars (äldre körningar) ur stegets utdata med citaten
verifierade mot källmaterialet i samma logg. Bedömningen läses ur
prospektraden och skrivs aldrig om; ett bolag utan sparad research får hela
kedjan som förut. Raden visar "Skriver utkast…" medan jobbet går, och skälet
står kvar på raden om inget utkast blev av (liggarens `error`). Processa om i
registret och kontaktjakten kör fortfarande full research.
`scripts/omskriv_utkast.py` skriver bara utkasten som standard
(`--med-research` för den gamla vägen). Ingen migration.

## 2026-10-17 (Anton) — Nivån från 2026-10-16 låses som referens

**Beslut.** "Lås in detta på samma sätt som tidigare i projektdokumentationen,
i en separat fil med exempel på outputen och exakt vad som ändrades från den
tidigare versionen och varför, se till att referera till det för nya frågor
kring output och utkast."

**I koden.** `docs/UTKASTKEDJAN-REFERENS-2026-10-16.md` är gällande referens
(den från 2026-10-12 står kvar som historik och pekar dit). Sju verkliga utkast
är facit i `tests/leads/fixtures/utkastfacit_2026-10-16.json`, låst av
INV-LEADS-UTKAST-002. Projektets CLAUDE.md och skrivstilens huvud pekar på
referensen för varje fråga om utkastens output. I samma ändring: "Hej
Brobergs," (bolagets första ord som förnamn) ger nu "Hej,".

## 2026-10-16 (Claude, på Antons beställning) — Utkasten skrivs med gemini-2.5-pro

**Beslut.** Utkast- och humanizerstegen i Iris kedja körs på `gemini-2.5-pro`
i Vertex `europe-west1` i development (`LEADS_DRAFT_MODEL`,
`LEADS_HUMANIZER_MODEL`). Research, Jev och övriga steg kör kvar på
`gemini-2.5-flash`.

**Resonemang.** Antons krav 2026-10-15: utkasten ska ligga på Christoffer-nivån
"HELA tiden". Med flash föll ingångarna tillbaka i nya mallord ("är ert löfte,
men … tar tid från det arbetet") även efter grindens två omskrivningsvarv; med
pro blev ingångarna konkreta och skrivna till bolaget. Kostnaden är ungefär
fyra gånger flash per utkaststeg och 5–8 minuter per utkast.

**Inte gjort, Antons beslut:** de nyare modellerna (`gemini-3.1-pro-preview`,
`gemini-3.8-flash`) finns bara på Vertex globala endpoint, inte i
`europe-west1`. Att flytta behandlingen ut ur EU-regionen är en
dataskyddsfråga och görs inte utan Anton. Main har inte fått modellbytet.

## 2026-10-15 (Claude, på Antons beställning) — Registret hämtas från allabolag; körningen ger inte upp under beställt antal

**Beslut.** Iris-körningar och listor ska leverera beställt antal. Registrets
sidor hämtas därför från allabolag.se, direkt och utan ScrapeGraph; urvalet
(kontroll, Jev, kontaktsökning, fördelning, listspår) är detsamma.

**Resonemang.** ScrapeGraph-kontot har en kredit kvar (gratisplanen slut,
verifierat 2026-10-15) och merinfo blockerar direkthämtning, så varje list- och
bolagssida föll och körningarna slutade på 4 och 8 leads av 50. allabolags
sökresultatsida går att hämta direkt och bär allt urvalet läser. Samma
affärsbeslut som för merinfo gäller: hövlig hämtning tills ett API-avtal finns
(prisförfrågan till allabolag).

**I koden.** `sources/allabolag.py` (sökning, geofilter, tolkning, cache),
vald i `merinfo.sok` med `LEADS_REGISTER` (osatt = allabolag när
`LEADS_MERINFO=scrapegraph`). Taken höjda för allabolag (600 bolag, 40 sidor per
sökning), kredittaket stoppar inte registret. Registret är fortfarande ett
filter: sökträffens kontaktperson blir aldrig en kontakt, och
ensam-VD-undantaget (regel 7) gäller inte allabolag-rader eftersom en sökträff
bara visar en person.

Antons beställning samma dag: "vi slutar inte förrän vi levererat det beställda
antalet PROCESSADE leads … var noga med att inte generera dubletter eller att
alla agenter söker igenom samma företag … de ska sorteras bort som bortvalda
och periodiskt blandas in". Därför också: körningen granskar upp till 12 bolag
per beställt lead (var 4) och har så många sökrundor att de ryms (50 → 75, var
11, vilket gav högst 88 bolag); den slutar när fyra rundor i rad inte gett en
ny kandidat. Bortval ur avslutade körningar (Jev, existens, research,
storlek/bransch, inte "utanför målområdet") står sig i 30 dagar och blandas
sedan in igen (`api/leads.py:_nyligen_bortvalda`). Efter första "Insufficient
credits" pausas betalda ScrapeGraph-anrop i tio minuter och räknas inte mot
taket (`sidhamtning._KREDIT_SLUT_TILL`): 350 misslyckade anrop stoppade
Göteborgskörningen. Fixturen är avidentifierad (inga personnamn, nummer eller
adresser).

Första körningen med allabolag (2026-10-15 22:00) avbröts efter några minuter:
bolag utan webbplats blev Iris-leads på registrets bolags-e-post (regel 13) och
föll i researchen på "Inget källmaterial" (9 av 11), och registrets hemsida var
ibland kedjans (giganten.se, elon.se, mio.se). Därför kräver Iris nu en
webbplats (regel 10; bolaget går annars till listspåret som "Utan webbplats"),
och en hemsida vars domän inte bär bolagets namn måste ha namnet på startsidan.

## 2026-10-15 (Anton) — Utkasten tillbaka till Christoffer-nivån; inga bolagsnamn i ämnesraden

**Beslut.** "Det första utkastet med Christoffer var det bästa (även om
ämnesraden var ren smörja) och det är den nivån och anpassningen jag förväntar
mig." Ämnesraden nämner INTE bolagets namn. Hälsningen får inte bära fel namn
("jag tror inte han som har Åkes Motor heter Delsbo"). Kvaliteten ska ligga på
den nivån hela tiden och bli bättre.

**Resonemang (Anton).** "Nu har du bytt ut 'för företag som ert' eller 'som ni
gör' till 'med er/ert/era', 'när ni', till en generisk upprabbling av deras
verksamhet, samt pinsamma ämnesrader." Båtladan-utkastet ("Hur hinner du med
att ge personlig rådgivning och service genom hela processen, från köp till
underhåll, när kundfrågorna om båtar, motorer och trailers blir många?") tar
det bolaget lovar sina kunder och ställer det mot momentet agenten löser; de
andra räknade upp sortimentet.

**I koden.** Ingången bygger på bolagets löfte (skrivstilen omgång 6,
grundmallen, personaliseringssteget, fyra nya ingångsformer utan "Med er",
"Ni" och "Era"). Stilgrinden fäller `slentrian_ingang`, `uppraknad_ingang`,
`kopierat_exempel` (fyra särskiljande ord i rad ur skrivstilens exempel),
`du_och_ni`, `agent_efter_loftet` och i ämnesraden `namn_i_amnet`,
`produkt_i_amnet`, `samma_amne`, `langt_amne`; fynden ger en omskrivning före
humanizern. `tilltal.amne_utan_namn` lyfter ut namnet som sista nät.
Förnamnet väljs mot mejladressen (`halsning.fornamn`: "Delsbo Magnus" med
magnus@ blir Magnus). Facit reviderat: Båtladan in, sex ut till `ersatta`
(Med er-öppning, uppräkning, eller agenten nämnd först efter löftet), och
ämnesraderna borttagna ur facit eftersom alla bar namnet.

## 2026-10-12 (Anton) — Utkasten är perfekta: kedjan låses som referens

*Delvis ersatt 2026-10-15: facit reviderat och ämnesraden utan bolagsnamn (se ovan).*

**Beslut.** "Alla utkast är perfekta nu, lås in detta och dokumentera exakta
upplägget, strukturen och vad du ändrade för att komma hit, lägg det i
projektmappen som referens för utkastsförbättring."

**I koden.** Tolv verkliga utkast ur Snajps granskningskö är facit
(`snajp-support/tests/leads/fixtures/utkastfacit_2026-10-12.json`), låsta av
INV-LEADS-UTKAST-001 (`tests/leads/test_utkastfacit_2026_10_12.py`): varje
facitutkast passerar stilgrinden, har ingången i andra person utan "man",
erbjudandet kvar och en handling sist; facitutkasten börjar olika; de
utpekade felen fälls fortfarande. Referensen med kedjan steg för steg,
strukturen, fel/rätt-tabellen, ändringarna och arbetsgången för vidare
förbättring: `docs/UTKASTKEDJAN-REFERENS.md`. Facitet ändras bara när Anton
godkänt nya referenser.

## 2026-10-12 (Anton) — Första utkastet ska vara det personliga, säljande utkastet; Tillbaka till Iris skriver inte om

**Beslut.** Utkastkedjan ska ge referenskvaliteten på första försöket för
varje lead: en ingång som bygger på en förståelse av verksamheten, inte på
uppräknade fakta som antal anställda och inte på samma mallfras för alla;
erbjudandet intakt; varken för kortfattat eller opersonligt. "Flytta
tillbaka" till Iris ska inte automatiskt skriva om leadsen, och alla tak på
antal markerade rader i listorna tas bort.

**Resonemang (Anton).** Två utkastkedjor följdes steg för steg (Fiskebäck
Byggservice, Härlanda Fog & Byggservice). Det platta första utkastet rabblade
registerfakta ("Med fem platschefer … är jag säker på att") eller öppnade med
"För företag som ert, som …": samma uppbyggnad för alla, opersonligt och
spammigt. Personalisera blev mer personligt men mindre säljande och tappade
erbjudandet. Förbättra blev kortare och rakare med kärnerbjudandet kvar, men
opersonligt. Först en andra Personalisera landade: det starka erbjudandet kvar
och en rimlig personalisering byggd enbart på en förståelse för verksamheten.
De ingångar som känns skrivna för varje bolag är byggda på något ur bolagets
egna ord och är inte byggda likadant. Flytta tillbaka ska inte processa om
alla; det är upp till användaren vad han vill göra, och ett tak på 50 (eller
något annat tak) hör inte hemma i någon lista.

**I koden.** Ingångens mallfraser är borta ur skrivstilen
(`agent-core/prompts/leads-skrivstil.md`, omgång 4) och grundmallen
(`leads-systemprompt.md` § 10.2); ingången bygger på en egenskap ur citaten,
och körningens redan använda ingångar läggs i ärendet. Stilgrinden
(`app/leads/stilkontroll.py`) fäller mallingång, siffror i ingången,
antaganden om mottagaren, tappat erbjudande (villkorens siffror och
produktens namn) och samma konstruktion som ett annat mejl, och
`run_outreach_draft_v2` skriver om en gång före humanizern när något fälls.
`POST /api/leads/queue/tillbaka-till-iris` avbryter bara utkasten; de
request-scheman som bar `max_length` (tillbaka till Iris, schemalägg,
processa om, flytt till main, massåtgärder) har inget tak, och
granskningskön hämtar upp till 1000 poster. Produktnamnets kortform ("Iris")
räknas som träff i produktmatchningen.

*Att veta (agenten):* de 27 av 100 Snajp-leads som saknade utkast efter
omkörningen 2026-10-11 föll i researchen som nivå C: 21 på produktmatchningen
("ingen av kundens produkter passar" eller "behovet kunde inte beläggas med
ett citat") och 6 på kriterierna om B2B- respektive B2C-kunder. Före
omkörningen var de nivå B, bara för att produktgrinden då inte såg
produktlistan.

*Utfallet 2026-10-12 (agenten):* omkörningen genom den nya kedjan gav 92 av
100 nya utkast i granskningskön (de 73 gamla godkända avbröts, inget skickat).
Två fel på vägen rättades i samma natt: profilen kompilerades om till tre
produktbundna måste-kriterier (ett bundet kriterium gäller nu bara den valda
produkten), och ett uppfyllt bundet kriterium härleder produkten när modellen
lämnar fältet tomt. Åtta faller fortfarande som nivå C efter tre försök: DS
Flexhal, Nyströms Byggtjänst, Solega, Z Marktjänst (B2B för Iris ej styrkt
med citat), Fiive, SafeTeam (B2C för Supportagenten ej styrkt), Simmis (behov
utan citat) och STINAB (modellen uteslöt bolaget som offentlig sektor fast
det bygger åt offentlig sektor). Anton avgör: lämna, Processa om, eller mjuka
upp profilens produktbundna kriterier till bör. `LEADS_DAILY_TOKEN_BUDGET` på
api i development höjdes 8 M → 32 M för natten och står kvar tills Anton
återställer den. Uppföljning: garanti- och pilotmejlen bör namnge agenten i
stycke 2 före löftet, och du/ni-blandning ska fällas av stilgrinden.

*Tillägg samma förmiddag (Anton):* "som ni gör", "som ert" och "för företag
som ert" stod kvar i nästan varje ingång; de ska anpassas på riktigt som i
referenserna, direkt i kedjan, så som en extra runda Personalisera gjorde.
**Resonemanget:** grinden fångade bara "För företag som ert" i meningens
början, och modellen skrev en allmän "när man …"-mening om branschen och
hängde på etiketten. De goda ingångarna är skrivna till mottagaren i andra
person om det som står på deras sajt. **I koden (`dda1531`):** stilgrinden
fäller etiketterna var de än står i ingången och allmänna ingångar ("man",
"den som", "ett företag som"); kedjan har ett obligatoriskt
personaliseringssteg som skriver om enbart ingången i andra person med en
detalj ur citaten, före humanizern; ingångsformerna, skrivstilen och
grundmallen säger detsamma. **Utfall:** alla 100 omkörda; 20 var redan
godkända och skickade 08:34 i den gamla stilen; 76 av de 80 övriga har nya
utkast utan etikett eller "man" i ingången; 4 faller på hårda kriterier (DS
Flexhal, Nyströms Byggtjänst, Z Marktjänst, SafeTeam). Budgeten i
development står på 48 M.

## 2026-10-10 (Anton) — Org.nr stoppar inte utskick; utskick går från development

**Beslut.** Tvåvägssynken gäller bara körningar och ärenden i databasen;
funktioner och andra ändringar stannar i development tills de pushas. Syftet är
att pålitligt kunna testa nya funktioner mot samma data. Org.nr-regeln får inte
blockera utskick, och det måste gå att skicka utskick från development också.

**I koden.** Regel 1 kräver bara företagsnamnet i sidfoten; org.nr och
postadress tas med när kundregistret har dem (`leads_tools.lagstadgad_fot`,
`utskicksfot.bygg_fot`). Varje godkänt utkast bär miljön där det godkändes
(`gate_checks.godkand_i`) och skickas bara därifrån (`scheduler.skickas_har`),
så att synken aldrig ger ett dubbelutskick. Äldre godkännanden utan miljö och
autonoma utskick skickas av main. Uppföljningssvepet, inkorgsläsningen och
autopiloten körs bara i main.

*Att veta (agenten):* e-handelslagen kräver organisationsnummer i
information från en näringsidkare. Ett utskick utan org.nr går nu ut; regeln
kräver det inte längre.

## 2026-10-10 (Anton) — Tvåvägssynk mellan development och main

*Ersatt 2026-10-17: main är sanningen efter första synken (se ovan).*

**Beslut.** Slå på och testa utskicken även i main. Allt speglas utom
specifika testkörningar, markerade som Provkörningar, som går att flytta över
till main. Alla övriga körningar och supportärenden speglas åt båda hållen med
det senaste tillägget som sanning. Vid första synken ska development vara
sanningen.

**Resonemang (Anton).** Det är en ändring från tidigare men en nödvändig sådan
för att kunna testa pålitligt.

**Fynd när beslutet genomfördes.** Den nattliga envägsspeglingen hade inte
speglat något sedan 2026-10-04: development låg på migration 110 och main på
102, skriptet avbröt, och GitHub visade grönt eftersom `tee` dolde felkoden.
Miljöerna hade glidit isär i sex dygn. Main hade under tiden fått produktions-
data som development saknade (15 kundmejl, 6 ärenden, 7 prospekt).

**I koden.** `scripts/railway_synk.py` (var tionde minut, `.github/workflows/
synk.yml`), migration 111 (`synk_andrad_at` och `synk_raderingar`).
*Agentens tolkning av "development är sanningen":* vid första synken vinner
development varje rad som finns i båda och skiljer sig, och allt som bara finns
i development kopieras till main. Det som bara finns i main raderas inte utan
kopieras till development, eftersom det är kundmejl och ärenden som annars
hade gått förlorade. En kopia av varje synkad tabell sparas före första synken.
Uppföljningar, inkorgsläsning och autopilot sker bara i main; utskick i den
miljö där utkastet godkändes (se beslutet ovan).

## 2026-10-10 (Anton) — Listornas leads stannar i listan; Flytta till Iris tas bort

**Beslut.** Alla leads från listor stannar i sina listor. Varje rad går att
klicka på och öppnar samma information och utkast som ett Iris-lead, med exakt
samma upplevelse. Knappen Flytta till Iris tas bort helt; kvar finns Processa om
och Skapa utkast, och båda går att köra på enskilda markerade rader eller alla.

**Resonemang (Anton).** Vår styrka är att alltid leverera högkvalitativa leads
och utkast. Även om listformatet låter användaren generera utkast för flera
hundra leads på en gång ska alla anpassas på exakt samma sätt som vanliga
Iris-leads. Flytta till Iris skulle göra Iris överfull och svårnavigerad, och
fungerade bara som ett stopp mellan ännu en utkastgranskning och utskicket.

**I koden.** Migration 110: `lead_list_items.prospect_id` kopplar raden till ett
bakgrundsprospekt (detaljvyn, researchen och utkastet går genom det), och
Iris-tabellen visar inte listkopplade prospekt (`GET /api/leads/prospects`).
`POST /api/leads/listor/{id}/utkast` kör samma research och utkast som Iris
(en körning med `kalla='lista'`, syns i Körningar). `till-iris` är borttagen.
De generella listutkasten (Sebbe 2026-10-07, `app/leads/listutkast.py`)
ersätts av detta.

## 2026-10-10 (Anton) — Processa om är en noggrannare omsökning

**Beslut.** Processa om anpassar en färdig lista, från en misslyckad körning
eller en annan användare, där leadsen ofta har bristfällig information. Den gör
om informationshämtningen i en noggrannare sökning och sveper bara källor som
förra agenten inte använde, så att så många källor som möjligt täcks. Hos
Alunix och Umeå Webbdesign hämtar Processa om även webbplatsinformationen på
nytt och förbereder underlag för utkast med erbjudande om hemsidor.

**Resonemang (Anton).** Det finns alltid kontaktinformation, det gäller bara
att leta tillräckligt. 200 bolag i dag blev ej kvalificerade och lämnades på
bordet för att de saknade hemsida eller lättillgänglig kontaktinformation.

**I koden.** `app/leads/omprova.py:sok` med källorna register, katalog
(hitta.se), webbplats och webbuppslag; prövade källor sparas i
`lead_list_items.kallor` (migration 110). Webbyråerna: `webbpool.bedom_en`.
Raderna uppdateras på plats, inget flyttas.

## 2026-10-10 (Anton) — Varje funktion har ett sätt att följa flödet

**Beslut.** Bygg alltid ett sätt att följa flödet för varje funktion. Fråga
alltid om det ska vara synligt för kund när det är tveksamt.

**Resonemang (Anton).** Processa om visade bara ett meddelande om att listan
processades, men det fanns inget sätt att följa aktiviteten eller veta om det
lyckades. Det ska lösas enkelt och tydligt i den befintliga miljön, inte i
ytterligare en flik om det inte är absolut nödvändigt.

**I koden.** `lead_lists.processering` (migration 110) bär förloppet för
Processa om och Skapa utkast och visas i listan, även efter en omladdning.
Regeln står i projektets CLAUDE.md.

## 2026-10-10 (Anton) — Kontaktuppgifter ur företagskatalogerna

**Beslut.** Leta i fler källor innan ett bolag blir ej kvalificerat. Hitta.se
och Eniro är där de flesta bolag fyller i sina uppgifter.

**Resonemang (Anton).** Norrtech i Skellefteå AB och Örnbergs Plåtslageri blev
"Inget kontaktsätt" respektive "Ingen namngiven VD" fast telefon, e-post och
webbplats stod öppet i katalogen och i Googles sammanfattning.

**I koden.** `app/leads/katalog.py`: hitta.se slås upp på org.nr (gratis, en
förfrågan per bolag) före webbplatsvalet i körningen och i Processa om.
Katalogens e-post är bolagsnivå (regel 13) och ger också webbplatsen via
domänen. Katalogens telefon räknas som bolagets publicerade nummer, som
sajtens, och kräver därför ingen VD i registret (`merinfo.fordela`).

*Bekräftat av Anton 2026-10-10:* regel 15 krävde en namngiven VD för
registrets nummer. Ett nummer bolaget själv publicerar i katalogen räknas som
sajtens nummer och kräver ingen VD. Så hamnar Örnbergs (070-numret, ingen VD i
registret) på ringlistan.

*Eniro:* inte inkopplad. Eniro svarar 403 på en ärlig bot-identitet och visar
numret först efter ett klick ("Visa nummer"); via ScrapeGraph kom varken
telefon eller e-post med. Vi maskerar oss inte som webbläsare.

*Gemini med Google-sökning och URL-kontext* provades för kontaktuppgifter
(Vertex, EU-regioner): 2.5-flash bytte till ett annat bolag när det sökta inte
hittades, 2.5-pro och 3.6-flash (3.6 finns bara på Vertex globala ändpunkt,
utanför EU-regionerna) gav inga träffar. För bolagshändelser och nyheter gav
2.5-flash användbara svar med länkar på bolagets egen sajt, men utan
sökkällor och med gissade datum: varje händelse måste styrkas genom att länken
hämtas innan den används.

## 2026-10-10 (Anton) — Iris sköter leads helt automatiskt inom kontots spärr

**Beslut.** Automatiseringen av leadskörningar, utkast, uppföljning och svar på
mejl ska slås på och skötas helt automatiskt av Iris, utifrån spärren som är
satt i kontot (första utkast, första mejl eller till bokat möte).

**Läget när beslutet togs (uppmätt i Railway och databasen 2026-10-10).**
Svaren hanteras redan automatiskt (inkorgen läses var femte minut i båda
miljöerna). Uppföljningar skrivs automatiskt men alltid som utkast till
granskning. Inget skickades av sig självt: `SEND_QUEUE_POLL_SECONDS` var inte
satt i någon miljö, så spärren avgjorde ingenting. Schemalagda leadskörningar
fanns inte. Bara kontot Snajp hade en spärr satt (`meeting`, till bokat möte,
som i koden beter sig som första mejl eftersom ett bokat möte kräver
överlämning); övriga stod på standard (utkast).

**I koden.** `app/leads/autopilot.py`: en Iris-körning per vardag från 06:00
med kundens `automation.autopilot.leads_per_dag` (standard 10, tak 50), när
både miljöns `LEADS_AUTOPILOT=1` och kundens `automation.autopilot.pa` är på.

*Väntar på Antons ja (agentens avgränsning):* att slå på `LEADS_AUTOPILOT`
och `SEND_QUEUE_POLL_SECONDS` i main. Development är en spegel med riktiga
kunders data och ska inte skicka mejl på egen hand till riktiga bolag; där
slås bara körningarna på, så att flödet går att följa utan utskick.

## 2026-10-10 (Anton) — Köade mejl kan skickas tidigare eller flyttas

**Beslut.** Det ska gå att markera och manuellt skicka mejl tidigare, eller
ändra den schemalagda tiden för ett eller flera mejl i kön utan att ändra
standarden.

**I koden.** Skicka nu går samma väg som Godkänn och skicka. Ändra tid:
`POST /api/leads/queue/schemalagg`; en vald tid utanför sändfönstret (vardagar
08–16) går ut när fönstret öppnar.

*Antons svar 2026-10-10:* "Gå direkt. Vanliga funktionen för att skicka
utkasten går via kön, men från kön kan man välja att skicka direkt." Skicka nu
(`POST /api/leads/queue/{id}/skicka-nu`) går därför förbi tidsgrinden och
regel 5a (kontorstid). Språkgrinden, suppression, karens, volymtak och
avsändaruppgifterna gäller fortfarande. Godkänn och skicka följer fönstret.
