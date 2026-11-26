# Demofilmen om Snajp Leads: så gjordes den, steg för steg

Skriven 2026-11-26 av Claude (Fable 5.2, sessionen som gjorde filmen) på Antons beställning. Dokumentet
beskriver hela arbetet 2026-11-25: varje instruktion och dom från Anton i hans egna ord, varje version
av filmen, varje tekniskt val, varje fel som uppstod och hur det löstes. Det är underlaget för nästa
steg, supportdelen, som beskrivs i [`UPPDRAG-DEMOFILM-SUPPORT.md`](UPPDRAG-DEMOFILM-SUPPORT.md).

`memory/…` betyder `C:\Users\Anton L\.claude\projects\C--Users-Anton-L-snipe-leads\memory\`.

Där det står **Antons ord** är det ordagrant citerat, med hans stavning. Där det står **min tolkning**
eller **mitt val** är det agentens, inte Antons, och kan ändras av honom.

---

## 1. Resultatet

| | |
|---|---|
| Fullversion | `brag-output/leads-demo/snajp-leads-demo.mp4`, 1920×1080, 30 fps, h264 crf 20 + aac 192k, 94,37 s, 31 MB |
| Mobilversion | `brag-output/leads-demo/snajp-leads-demo-mobil.mp4`, samma bild omkodad crf 27 + aac 128k, 11 MB |
| Projektet i repot, fristående | [`marknad/demofilm/`](../../marknad/demofilm/) (källkod, manus, bilder, typsnitt, musik; verktygen med relativa sökvägar). Det är det som ska användas framåt |
| Orörd kopia av källfilerna och slutfilen | `D:\snajp-demo\leads-version-2026-11-25\` (Antons dator) |
| Arbetsmappen där filmen gjordes | `D:\snajp-demo\` (Antons dator, inte i git, ligger på D: eftersom C: är nästan full) |

Avsnitt 4 beskriver arbetsmappen på D: som den användes 2026-11-25. I `marknad/demofilm/` heter
motsvarande filer `rec/record-leads.mjs`, `src/`, `verktyg/render-parts.mjs`, `verktyg/stills.mjs`,
`verktyg/tider.mjs`, `verktyg/ljud.mjs` (ljudmixen ur `bygg.sh`, nu för valfritt antal klipp) och `bygg.sh`.
Ljudet från `verktyg/ljud.mjs` är provat mot leadsfilmens och blev identiskt.

Mobilversionen finns för att `SendUserFile` bara når mobilen/Remote Control upp till 30 MB.
Fullversionen (31 MB) syns bara i skrivbordsappen.

### Filmens innehåll i ordning

Bildrutor vid 30 fps. Scenerna överlappar 20 rutor (övertoningen).

| Start (ruta / s) | Längd | Typ | Innehåll |
|---|---|---|---|
| 0 / 0,0 | 795 rutor | Klipp | Instagramreelen "Iris från körning till svar", 4:5, hel höjd, mitt i bild, eget ljud |
| 775 / 25,8 | 1,5 takt | Rubrik | Så här jobbar Iris åt er |
| 880 / 29,3 | 2 takter | Steg 01 | Ni beskriver er drömkund en enda gång |
| 1011 / 33,7 | 2 takter | Steg 02 | Ett klick, sedan gör Iris jobbet |
| 1142 / 38,1 | 2 takter | Steg 03 | Iris hittar bolagen, läser på och skriver mejlen |
| 1273 / 42,4 | 2 takter | Steg 04 | Ni får bolagen rankade efter hur väl de passar |
| 1404 / 46,8 | 2 takter | Steg 05 | Varje bolag kommer med skäl, citat och källa |
| 1535 / 51,2 | 2 takter | Steg 06 | Mejlet utgår från något som hänt hos just dem |
| 1666 / 55,5 | 2 takter | Steg 07 | Vill ni ändra texten räcker ett klick |
| 1797 / 59,9 | 2 takter | Steg 08 | Inget går ut förrän ni har sagt ja |
| 1927 / 64,2 | 2 takter | Steg 09 | Uteblir svaret följer Iris upp av sig själv |
| 2058 / 68,6 | 2 takter | Steg 10 | Hela vägen till svar eller bokat möte |
| 2189 / 73,0 | 3 takter | Rubrik med rader | Datasäkerhet |
| 2386 / 79,5 | 3,5 takter | Rubrik med rader | Vad ni får |
| 2615 / 87,2 | 3 takter | Slutkort, mörkt | Kostnadsfri pilot i två månader / snajp.se |
| slut 2831 / 94,37 | | | |

En takt är 2,18 s (110 BPM, fyra slag). Varje demosteg är två takter, cirka 4,4 s.

### Texterna på korten, exakt

**Datasäkerhet**
- All drift, lagring av kunddata och behandling i språkmodeller sker inom EU
- Varje kunds data är avskild på databasnivå
- Alla underleverantörer står med namn i integritetspolicyn

**Vad ni får**
- Bolag som passar er målgrupp, med skäl och källor
- Ett första mejl till varje bolag, skrivet på svenska
- Uppföljning fram till svar eller bokat möte
- Ni godkänner varje mejl innan det skickas

**Slutkortet:** "Kostnadsfri pilot i två månader", under det "snajp.se" i ockra, på mörk (ink) bakgrund.

### Vad som visas i varje steg

| Steg | Var det är fotat | Vad som händer i bild |
|---|---|---|
| 01 | `/demo/installningar` | Iris-profilen, markören på målgruppen |
| 02 | `/demo/leads`, panelen Hitta bolag | Markören klickar på Kör Iris |
| 03 | samma | Körningens tre steg, steg 2 "Läser sajterna och hittar kontakten" aktivt |
| 04 | `/demo/leads`, listan Iris-leads | Markören klickar på Hammarnäs Bygg Sverige AB (poäng 91, Stark) |
| 05 | Leadets låda, fliken Bedömning | Markören på "källa" vid citatet "Har precis flyttat till en större lokal." |
| 06 | Lådan, fliken Mejlutkast | Mejlet "Den nya lokalen hos Hammarnäs", Hej Sara, gratulationen till den nya lokalen |
| 07 | `/demo/leads`, Senaste utkasten, utkastet "Hjärtstartare på listan?" öppnat | Markören klickar på Kortare |
| 08 | samma, efter Kortare | Förklaringen "Kortare: gratulationen är borta …", markören klickar Godkänn och skicka |
| 09 | `/forhandsvisning/konversationer`, fliken Uppföljningar, Läs öppnat | Uppföljningen "Om mitt förra mejl", uppföljning 1 av 3: "Jag skrev förra veckan om frågorna som kommer efter kl. 17. Är det något ni vill titta på?" |
| 10 | Samma sida, fliken Konversationer | Bara trådens huvud: Fiktiv Telefoni AB, Steg: Svarat, frågan "Är mötet bokat?" och knappen Markera Möte bokat. Inget mejl i bild |

---

## 2. Antons instruktioner och domar, i ordning och ordagrant

### 2.1 Beställningen

> **Antons ord:** "Hej, jag vill att du skapar en interaktiv click- through demo-video för Snajp på samma
> sätt som vi gjorde för WMS:et. Fokusera på leadsdelen"

"Samma sätt som WMS:et" är filmen i `D:\wms-presentation\` (källkod i `D:\wms-presentation\video\src\Film.tsx`,
inspelningsriggen i `warehouse-handy-next\.claude\worktrees\wms-completion\docs\presentation\production\rec\lib.mjs`).
Metoden: Playwright styr den riktiga appen och tar en skarp bild per steg plus klickpunkten; Remotion
animerar bilderna med en kamera som åker in, en markör som glider dit och klickar, och en bildtext.

### 2.2 Datasäkerheten

> **Antons ord** (kom medan agenten startade, som avbrott): "Se till att få med datasäkerhet också, att
> all data lagras i EU"

**Mitt val i första versionen:** jag skrev inte "all data" eftersom `lib/bolag.ts` och
`docs/JURIDIK_ATGARDER.md` då sa att Resend lagrar mejlinnehåll i USA 30 dagar, och att Jev (TypeSafe) och
ScrapeGraphAI ligger i USA. Första kortet hade fyra rader: databasen och driften i Amsterdam inom EU,
språkmodellen inom EU, avskild kunddata, underleverantörerna i integritetspolicyn.

> **Antons ord:** "Fortsätt, ändra inget på sajten gällande EU- formuleringen"

> **Antons ord:** "Det räcker med "i Eu", utan Amsterdam, väv ihop både det om speåkmodellerna och
> databasen till en och samma punkt, att allt lagras och hanteras inom EU.  Jev och Scrapegraph används
> inte längre, du kan kontrollera det. Resend behandlar inte kunddata på det sättet."

Kontrollen jag gjorde:
- **Jev:** stämmer. `docs/BESLUT.md` 2026-11-23: `JEV_MOTOR=gemini` är standard, Jevs frågor besvaras av
  Flash-Lite på Vertex i EU. TypeSafe går bara att välja uttryckligen (`snajp-support/app/config.py`).
- **ScrapeGraph:** ligger kvar i koden: skärmbilden i `snajp-support/app/leads/webbrevision.py` och
  reservhämtningen av bolags sidor i `snajp-support/app/leads/sidhamtning.py`. Krediten är slut sedan
  2026-10-15, så inget går dit i dag.

Raden blev "Allt lagras och hanteras inom EU, både databasen och språkmodellerna". Domen över den:

> **Antons ord:** ""Både databasen och språkmodellerna" läses som vardagligt och slappt, gör det mer
> professionellt, som All drift och lagring av kunddata samt språkmodeller sker inom EU."

Raden blev "All drift, lagring av kunddata och behandling i språkmodeller sker inom EU". I Vad ni får
stod först "Drift, lagring och språkmodeller inom EU"; raden togs bort i slutversionen när
uppföljningsraden kom in, så att listan inte upprepar Datasäkerhet.

### 2.3 Integritetspolicyn (ändrad på sajten, på Antons uttryckliga beställning)

> **Antons ord:** "Ändra Scrapegraphs roll i integritetspolicyn till så minimal som möjligt om ens
> nämnvärd, den ser inte eller hanterar några kunddata, den ligger endast som ett eget steg för
> webbplatsbedömning, den samlar inte in kunddata eftersom att ingen av de prospekten ännu är en kund och
> den data den hanterar lagras inte på det sättet"

Gjort i `lib/bolag.ts` (`UNDERLEVERANTORER`, ScrapeGraphAI): ändamålet är nu "Skärmbilder och hämtning
av bolags publika webbplatser. Behandlar inga kunduppgifter." (svenska och engelska),
`uppdaterad.integritetspolicy` satt till 2026-11-25. Beslutet står överst i `docs/BESLUT.md` med Antons
resonemang. Språkgrinden `tests/invariants/test_inv_copy_001.py` gick igenom.

Mina val, som Anton kan ändra: posten står kvar (koden kan fortfarande anropa tjänsten); texten nämner
inte webbplatsbedömningen (den är hemlig enligt CLAUDE.md); avtalsutkasten `docs/pub-avtal.md`,
`docs/pilotavtal.md` och `docs/registerforteckning.md` är inte ändrade.

**Status:** ocommittat. Anton har fått frågan om commit men inte svarat. Arbetskatalogen har över 140
ocommittade filer från en annan session (Hjälprutan); en commit ska bara ta `lib/bolag.ts` och den egna
posten i `docs/BESLUT.md`.

### 2.4 Erbjudandet

> **Antons ord:** "Erbjudandet att avsluta med är, kostnadsfri pilot i 2 månader, inget om någon
> ytterligare rabatt"

Slutkortet: "Kostnadsfri pilot i två månader" och "snajp.se". Inget pris, ingen rabatt, inget annat.

### 2.5 Bildtexten

> **Antons ord:** "Gör texten lite större och flytande utan bakgrund, som dyker upp och byts ut mjukt"

Före: först en mörk platta som flöt över bilden, sedan (mitt val) ett mörkt band under bilden. Efter:
- Ingen platta. Skärmbilden tonar ut i sidans egen pappersfärg (`#f6f3ed`) de sista 96 px ovanför ett
  168 px högt fält längst ned, och texten står fritt där.
- Geist 60 px, vikt 560, bläckfärg `#10171e`, vänsterställd 72 px från kanten.
- In: från ruta 12 till 34 tonar den in, glider upp 14 px och går från 6 px oskärpa till skarp.
- Ut: rutorna `dur−33` till `dur−20` tonar den ut, glider upp 10 px och blir 4 px oskarp, så att den är
  borta innan bilderna tonar över i varandra.

Första versionen av bytet lät gammal och ny text ligga på varandra under övertoningen, vilket gav en
halv sekund oläsbar text. **Regeln nu: en bildtext i taget.** Granska alltid bytet bildruta för bildruta.

### 2.6 Uppföljningen i stället för en extra sändningssekvens

> **Antons ord:** "Du behöver inte ha två sekvenser om hur man skickar och att man kan skicka flera på
> samma gång, visa istället uppföljningen och hur Iris automatiskt följer upp och kan driva till första
> svar eller hela vägen till möte beroende på vad man vill."

Massgodkännandet ("Godkänn och skicka alla", bekräftelserutan) togs bort. Uppföljning och väg till möte
kom in. Demon (`/demo`) saknar flikarna Konversationer och Uppföljningar, så de fotades i
förhandsvisningen `/forhandsvisning/konversationer` (påhittade bolag, anropen besvaras i webbläsaren).

> **Antons ord:** "Det exempelmailet läser som ett första, byt ut det, och skriv om det exempel jag gav om
> datahanteringen
> Som sagt, mailet läser som ett första mail, inte som uppföljning, du måste byta ut det"

Felet: i Konversationer öppnar tråden på sitt **första** mejl ("Frågor om telefoni och drift tar tid
från teamet …"), som syntes i bild under uppföljningstexten. Rättning:
- Steg 09 öppnar **Läs** på det väntande uppföljningsutkastet i fliken Uppföljningar ("Om mitt förra
  mejl", uppföljning 1 av 3), ett mejl som tydligt hänvisar till ett tidigare.
- Steg 10 är inramat så att bara trådens huvud syns (fast kamerapunkt `focus: { x: 1314, y: 0 }`, zoom
  1,65). Inget mejl i bild alls.
- Ingen markör klickar på "Markera Möte bokat": förhandsvisningen ändrar inte tråden när man klickar, så
  bilden skulle säga emot sig själv.

### 2.7 Musiken, första gången

> **Antons ord:** "Lägg även till den lugna musiken som valdes bort i den förra marknadsföringsvideon
> till Linkedin"

Lades in: `brag-output/musik/lugn.mp3` (61 s), tre varv med 4 s övertoning. Agenten borde ha påmint om
att samma spår dömts ut 2026-11-15 (`memory/brag-video-baslinje.md`) och gjorde det inte.

### 2.8 Mobilversionen

> **Antons ord:** "Skicka den färdiga mobilversionen"

Den färdiga versionen höll på att renderas. Den gamla filen i mappen skickades **inte**; agenten sa att
den var inaktuell och skickade den nya när den var klar och kontrollerad. Gör alltid så.

### 2.9 Den stora omarbetningen

Anton skickade en skärmbild av Instagramreelens slutbild (`snajp.ai`, "Kalla samtal på fredag
eftermiddag? Nej …"), där Instagram har beskurit bilden så att loggan klipps upptill.

> **Antons ord:** "Musiken låter väldigt mycket som hissmusik och passar inte för detta formatet heller,
> det är för mycket bas och musiken blir distraherande istället för engagerande. Försök behålla samma
> tempo men gör den mer upbeat ändå med högre, ljusare och energiska toner, försök hitta exempel på vad
> som används i andra produktdemos, ge mig några korta samples först. Eller vet du vad, spara det enbart
> som feedback och använd musiken som vi valde att gå vidare med för den videon, för att spara tid och
> resurser. Försök även korta ner de delar som inte är lika centrala, som att förklara exakt var man
> klickar eller vad varje siffra visar. Visa vad den GÖR, hur ENKELT det är och vad de får för värde av
> varje funktion. Inled även videon med den första instagramvideon:
> https://www.instagram.com/reel/Dfaukc1JjVD/?evlk=dzFha2ZrcWYwYzBx  och se till att den inte klipps på
> samma sätt, innan du går vidare med den fördjupade demon."

Vad som gjordes:
1. **Musikdomen sparades som feedback**, inget nytt spår togs fram: `memory/brag-video-baslinje.md`
   (domen och riktningen för ett framtida spår: samma tempo, ljusare och mer energiskt, mindre bas,
   korta prov till Anton först) och ny `memory/produktdemo-visa-vardet.md`.
2. **Musiken blev "den vi valde att gå vidare med":** version 2-bädden, `brag-output/musik/forra-versionen.mp3`
   (samma spår som `snajp-bed-lyria-110bpm.mp3`), 110 BPM, 61 s.
3. **Manuset kortades från 25 steg till 10**, och varje bildtext skrevs om till vad Iris gör eller vad
   kunden får. Struket: tidslinjen, poängförklaringen, "Ämnesrad och text går att ändra direkt",
   "Skickade mejl följs i samma lista", "Ni ser vad som väntar, vad som skrivs och vad som är dags",
   "Ni bestämmer hur långt Iris ska gå", Att göra, Listor, bilden av integritetspolicyn, rubrikkorten
   mellan avsnitten.
4. **Reelen lades först, obeskuren.** Min tolkning av "se till att den inte klipps på samma sätt": hela
   reelens bild ska synas, inte Instagrams beskurna utsnitt. Reelen (4:5, 1080×1350) visas i filmens
   fulla höjd, 864 px bred, mitt i bild. Sidorna fylls genom att reelens yttersta sex pixelkolumner
   sträcks ut till kanten, så att en mörk scen får mörka sidor och det ljusa slutkortet ljusa. (Första
   försöket var en uppförstorad oskarp kopia bakom; den drog in paneler och loggan i sidorna och
   förkastades.)

### 2.10 Övriga meddelanden

- "Try again" (när inspelningen fastnat på en skärmbild som aldrig blev klar; andra körningen gick).
- "Fortsätt" (två gånger, efter avbrott i sessionen).

---

## 3. Versionerna

| Version | Längd | Innehåll | Antons dom |
|---|---|---|---|
| 1 | 2:16 | 23 steg ur `/demo`, kort om datasäkerhet (Amsterdam), Vad ni får, pilot. Bildtext på mörk platta, sedan mörkt band | Texten ska vara större och flytande; datasäkerheten ska säga EU |
| 2 | 2:16 | Flytande bildtext, mjukt byte | (textbytet grumligt, rättat av agenten) |
| 3 | 2:26 | Massgodkännandet bort, uppföljningsdel in, lugn musik, ny EU-rad | Mejlet läses som ett första mejl; EU-raden slapp |
| 4 | 2:26 | Riktigt uppföljningsmejl, tråden utan mejl, professionell EU-rad | Musiken är hissmusik; för många förklarande steg; reelen ska in först |
| 5 (slutlig) | 1:34 | Reelen först, 10 steg om värde, version 2-musiken, klipp på takten | (inte bedömd än) |

---

## 4. Tekniken

### 4.1 Mappar och verktyg

| Sökväg | Vad |
|---|---|
| `D:\snajp-demo\rec\record-leads.mjs` | Inspelningen: Playwright mot den levande dev-miljöns publika `/demo` och `/forhandsvisning/...`. Skriver `public/film/NN.png` och `video/src/data/film.json` |
| `D:\snajp-demo\rec\explore*.mjs` | Utforskningsskript (skärmbilder och sidtext till `D:\snajp-demo\explore\`) |
| `D:\snajp-demo\video\` | Remotion-projektet. `src/Film.tsx` (motorn), `src/Root.tsx`, `src/data/film.json` (manuset) |
| `D:\snajp-demo\video\node_modules` | Junction till `C:\Users\Anton L\warehouse-handy-next\.claude\worktrees\wms-completion\docs\presentation\production\video\node_modules` (Remotion 4.0.535). Skapa med PowerShell `New-Item -ItemType Junction`; `mklink` från bash gav en trasig målväg |
| `D:\snajp-demo\video\render-parts.mjs` | Renderar i delar (`ONLY_PART`, `PART_SIZE=500`), sätter ihop med ffmpeg concat |
| `D:\snajp-demo\video\stills.mjs` | `node stills.mjs <mapp> <ruta> [<ruta> …]` renderar enskilda bildrutor för granskning |
| `D:\snajp-demo\video\bygg.sh` | Hela bygget: delar med upp till fyra försök var, ljudmixen, slutfilen, mobilfilen, kopian till `brag-output/leads-demo/` och ett kontaktark |
| `D:\snajp-demo\reel\` | Kopia av `marknad/video` (Instagramreelen om Iris, Remotion 4.0.541) med egna `node_modules` (`npm ci --cache D:/npm-cache`) |
| `D:\snajp-demo\reel\rendera-4x5.mjs` | Renderar reelens komposition `Flode-4x5` till `D:\snajp-demo\public\reel.mp4` (crf 14) |
| `D:\snajp-demo\public\` | Filmens publicDir: `film/` (stegen), `fonts/` (Fraunces, Geist ur `D:\brag-snajp\brag-output\composition\assets\fonts`), `reel.mp4` |
| `D:\snajp-demo\out\` | `parts/`, `stum.mp4`, `ljud.wav`, `snajp-leads-demo*.mp4`, loggar |

Playwright laddas via `createRequire("C:/Users/Anton L/warehouse-handy-next/.claude/worktrees/wms-completion/package.json")("@playwright/test")`.
Webbläsaren för Remotion: `C:/Users/Anton L/AppData/Local/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-win64/chrome-headless-shell.exe`.

### 4.2 Inspelningen (`record-leads.mjs`)

- Fönster 1280×720 med `deviceScaleFactor 1.5`, så varje bild blir 1920×1080 och skarp.
- `still()` tar skärmbilder tills två i rad är identiska, så att ingen animation fångas mitt i. Gäller
  inte steg där innehållet byts hela tiden (Kör Iris-stegen byts var 900 ms): där används `vila: false`.
- `shot(caption, { target, click, y, vila, bars, center, zoom, anchor, focus })`: `y` skrollar målet till
  den höjden i fönstret; `click` klickar efter bilden; `bars` är längden i takter.
- `aim()`: vid klick landar markörens spets till höger om och under mitten, så att knappens text syns;
  utan klick landar den strax under första raden av texten den pekar på.
- Många klick görs **utan** bild (öppna Kör Iris-panelen, Visa i listan, öppna utkastet). Bara steg som
  bär en egen poäng fotas.
- Demons lista spelar upp en körning när sidan laddas ("Research pågår"). Vänta tills den texten är borta
  innan något fotas.
- Demons Kör Iris-körning ger rader med utkast "–" och kontaktväg "Saknas", trots att texten säger "tre
  nya företag med färdiga utkast". Bildtexten undviker därför att påstå färdiga utkast i det steget.

### 4.3 Motorn (`Film.tsx`)

- Typer: `Shot` (skärmbild med markör, `bars`), `Title` (rubrik, ev. `sub`, `lines`, `invert`), `Clip`
  (en färdig film som spelas hel: `file`, `frames`, `w`, `h`).
- **Takten:** `BAR = 60/110 × 4 × 30 = 65,45` rutor, `BEAT0 = 17` (bäddens första slag efter 0,56 s),
  `FADE = 20`. `layout(items)` lägger varje övertonings mitt på ett taktslag. Ett `Clip` nollställer
  räkningen: bädden antas börja där klippet lämnar över.
- **Kameran:** åker in från helbild (rutor 20–84) till zoom 1,25 med vänsterkanten vid sidomenyn
  (`SIDEBAR = 390`), toppankrad så att sidhuvudet aldrig klipps, och glider långsamt resten av tiden.
  `center` ramar in sidans mitt (förhandsvisningar utan sidomeny), `anchor: "right"` landar i lådan till
  höger, `focus` ger en fast punkt.
- **Markören:** glider från förra stegets punkt (rutor 38–84), klickar vid ruta 92 med en ockra ring.
- **Övergångar:** mellan två skärmbilder en vanlig övertoning; in i och ut ur rubriker och klipp en
  "dip" genom pappersfärgen med en heltäckande färgad yta (CSS-opacitet på hela scenen gjorde text fetare
  på vissa rutor).
- **Rubrikkort:** Fraunces 600 (100 px utan rader, 76 px med), rader i Geist 46 px med ockra punkt och
  `textWrap: balance`. `invert` ger mörk bakgrund och ockra undertext.
- **Klippet:** se 2.9 punkt 4.

### 4.4 Ljudet (`bygg.sh`)

- Under reelen: reelens eget syntetiserade ljud (`marknad/video/ljud/gor_ljud.py`, 120 BPM).
- Från ruta 775 (25,833 s): `forra-versionen.mp3` två gånger med 4,273 s övertoning (26 takter = 56,727 s
  mellan starterna, så att skarven ligger på en taktgräns), intoning 0,35 s, uttoning de sista 3,3 s,
  volym 0,82, `amix normalize=0`, `alimiter limit=0.89`.
- Uppmätt: cirka −19 LUFS under reelen, −18 i demon, −19 i slutet.
- **Inte kontrollerat:** ingen har lyssnat. Övergången vid 0:26, skarven vid cirka 1:23, och att klippen
  upplevs ligga på takten. Reelen har annan puls (120) än bädden (110).

### 4.5 Rendering och fallgropar

| Problem | Orsak | Lösning |
|---|---|---|
| "Chrome ran out of memory" | Hela filmen i en process | Rendera i delar om 500 rutor, en process per del |
| "Timed out after 25000 ms while trying to connect to the browser" | C: nästan full och maskinen belastad av andra sessioner | `TEMP`/`TMP` till `D:\snajp-demo\tmp\temp`, upp till fyra försök per del |
| C: fylldes av renderingar | Remotion lämnar `remotion-v4.0.535-assets*`, `react-motion-render*`, `puppeteer_dev_chrome_profile-*` i TEMP | 714 MB rensade 2026-11-25; med TEMP på D: händer det inte igen |
| Kopieringen hängde | `cp -r` följde `node_modules`-länken | Kopiera aldrig mappar med `node_modules` |
| ffmpeg: "globbing is not supported" | Windows-bygget saknar glob | Numrera om filerna och använd `s%02d.jpeg` |
| ffmpeg: "Unrecognized option 'vsync'" | Nyare ffmpeg | `-fps_mode passthrough` |
| Python via heredoc förstörde escapes | Se `memory/heredoc-forstor-escapes.md` | Skriv skript till fil eller använd Edit |

### 4.6 Granskningen

Varje version granskades med egna ögon (CLAUDE.md: titta alltid själv):
- `stills.mjs` renderar en bildruta per scen, vid `start + min(längd − 45, 95)`, där markören har landat
  och bildtexten syns.
- Kontaktark med ffmpeg `tile` (2×3 eller 5×4) som läses som bild.
- Textbytet granskas bildruta för bildruta (8 rutor över ett byte).
- Den färdiga filen: `ffprobe -count_frames`, ljudnivå per avsnitt med `ebur128`, kontaktark ur själva
  mp4-filen.

---

## 5. Regler som gällde och gäller

- **Ingen kunddata i bild.** Development är en spegel av produktionen. Filma bara `/demo` och
  `/forhandsvisning/...` (exempeldata), aldrig en inloggad yta.
- **Webbplatsbedömningen visas aldrig** (webbrevision, webbnivå, betyg).
- **Inga påståenden om svarsfrekvens** (marknadsföringslagen, `marknad/video/README.md`). Siffror i demon
  är exempeldata och ska inte bli bildtexter.
- **Synlig text säger supportagent, aldrig supportbot** (`memory/supportagent-inte-supportbot.md`).
- **Musiken:** version 2-bädden; `lugn.mp3` är dömd två gånger (`memory/brag-video-baslinje.md`).
- **Innehållet:** vad funktionen gör, hur enkelt det är, vad kunden får; inte var man klickar eller vad
  en siffra betyder (`memory/produktdemo-visa-vardet.md`).
- **Erbjudandet:** kostnadsfri pilot i två månader, inget om rabatt.
- **Remotions licens:** fri upp till tre anställda; större bolag behöver företagslicens före kommersiell
  användning.

## 6. Öppet

- Antons dom över version 5.
- Commit av integritetspolicyn (`lib/bolag.ts`, `docs/BESLUT.md`), väntar på hans ja.
- Ingen har lyssnat på ljudet.
- Demons Kör Iris-rader visar "Saknas" som kontaktväg trots att panelen säger "färdiga utkast": en sak i
  själva demon, inte i filmen.
