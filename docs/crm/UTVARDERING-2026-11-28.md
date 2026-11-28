# Utvärdering: Snajp CRM, 2026-11-25 till 11-28

Skriven av agenten som drev arbetet. Underlaget är sessionens egna anteckningar, commit-loggen och
arbetsflödenas journaler. Där jag inte vet står det.

## Uppdraget och utfallet i tal

**Beställningen:** en komplett CRM-svit med Twenty som förlaga, som egen app bredvid dagens, med ett
API åt båda håll, i Astryx med Snajps tema. Sedan utökad: hela dagens app in i samma miljö.

| | |
|---|---|
| Tid | Fyra kalenderdygn, i praktiken sönderhackat av användningsgränsen |
| Commits | 73 på en egen gren, inget på `development` |
| Omfång | 526 filer, 93 000 rader, varav 350 filer underlag, bilder och dokument |
| Backend | 99 rutter, nio migrationer, 359 tester gröna |
| Gränssnitt | 45 komponentfiler, 20 vyer och paneler, alla i förhandsvisning |
| Granskning | 122 fynd från oberoende granskare, inget avfärdat, alla rättade utom en handfull öppna |
| Mått mot förlagan | 3 665 rader: 135 verifierade, 78 byggda, 736 delvis, 2 319 inte gjorda, 397 avstår |
| Mått mot dagens app | 1 306 rader: fas 3 klar, fas 4 ungefär halv, fas 5 inte påbörjad |
| Stopp | Användningsgränsen nådd minst fem gånger, veckogränsen för Opus en gång |
| Kostnad per steg i fas 4 | Ungefär 1,07 miljoner subagent-tokens, 265 verktygsanrop och 43 minuter |

**Ärligt omdöme:** kärnan och formen höll. Bredden är halvfärdig, och ingenting är kört mot en riktig
backend. Det sista är den största bristen, och den går tillbaka på ett beslut som aldrig fattades i
början.

## Det som fungerade, och varför

1. **Funktionslistan som mått.** 1 306 rader med ID gjorde "all funktionalitet kvar" kontrollerbart.
   Byggaren redovisar ID för ID, granskaren svarar med ID:n som saknas, statusfilen pekar på spann.
   Utan den hade "klart" varit en känsla.
2. **Designkontraktet med ägarens dom ordagrant.** Efter underkännandet av version 1 skrevs Antons ord
   överst i `DESIGN-CRM.md`, version 2 byggdes ur det, godkändes och låstes. Därefter har ingen byggare
   hittat på en egen form, och varje nytt mönster har lagts under en rubrik märkt "inte sett av Anton än".
3. **Förhandsvisningen utan databas.** En `fetch`-fångare som svarar med påhittad data. Den bar alla
   bilder, all granskning, lägena läsroll och kundbesök i adressen, och till slut en deploy hos Railway
   utan en enda nyckel.
4. **Byggare, granskare, rättare.** Tre agenter i följd med olika uppdrag. Granskaren fick inte röra
   något och skulle ge ett scenario per fynd. Rättaren skulle pröva fyndet mot koden först. 122 fynd,
   inget avfärdat: granskarna hittade riktiga fel (svar som skrevs in i fel utkast, dubbla hämtningar,
   fält som inte följde med det sparade), inte smaksaker.
5. **Rapportens tvingande fält.** `inte_byggda_rader`, `saknas_i_backend`, `inte_verifierat`. De gav
   en samlad lista över elva ställen där backenden saknar något, utan att någon byggt runt det.
6. **Huvudagentens egen bildgranskning.** Varje omgång hittade något: kapade kolumner medan en annan
   hade tomrum, en vyrad på två rader, beslutsknapparna under vecket, fält på olika höjd.
7. **En backend, ett API.** De nya vyerna anropar dagens ändpunkter genom dagens proxy. Därför är
   dagens app orörd, och därför går det att bygga vy för vy.
8. **Beslutsloggen med agentens val märkta.** "Inget av detta är Antons ord" över varje block. Ägaren
   kan vända ett val utan att leta efter var det fattades.
9. **Delade anteckningar utanför repot** för läget mellan sessioner, och en statussida ägaren kan läsa
   på telefonen.
10. **Mönster byggda en gång.** Navigeringsregistret, banderollen, utkastredigeraren, bekräftelsen.
    Steg 4.4 återanvände 4.3:s redigerare utan att bygga något eget.

## Det som inte fungerade, och vad det kostade

1. **Gränssnittet byggdes före en godkänd form.** Version 1 var generisk och underkändes. Kostnad: en
   dag och en hel bygg- och granskningsomgång. Lärdom: tre till fem vyer, ägarens dom, sedan resten.
2. **Förlagan lästes på djupet innan något valdes.** Tretton områden, tre luckgranskningar, sexton
   paritetsdelar, 3 665 rader. Antons sexton ja kom först på tredje dagen. Två tredjedelar av listan
   är fortfarande "inte gjord" och har ingen beställning. Lärdom: bredd först, ägarens val, sedan djup
   bara där det valts.
3. **Kvoten styrde arbetet i stället för planen.** Tolv Opus-agenter samtidigt tömde kvoten på en
   timme första dagen. Arbetsflöden avbröts mitt i minst fem gånger, en gång med ocommittat arbete som
   fick prövas och tas om. Lärdom: budget i fas 0, agenter i följd, läget nedskrivet före varje körning.
4. **Ingen testmiljö.** Docker behövdes, disken var full, och frågan till ägaren fick aldrig svar.
   Följden: förhandsvisningens svar är skrivna efter att ha läst backendkoden. Varje fält som heter
   fel syns först mot riktig backend, och det finns tjugo vyer att gå igenom den dagen. Lärdom: lös
   testmiljön i fas 0, eller bygg ett kontraktstest som validerar svaren mot backendens schema.
5. **Maskinens gränser upptäcktes under arbetet.** C: full, byggcachen flyttad till D: mitt i, ingen
   plats för ett andra worktree, full typkontroll omöjlig. Lärdom: mät först.
6. **Beställningarna låg i scratchpaden.** Trettio filer och arbetsflödets skript var en sessionsdöd
   från att försvinna, och de bär absoluta sökvägar dit. De kopierades in i repot sista dagen.
7. **Tvärgående saker kom för sent.** `useSkrivratt` byggdes i steg 4.1, efter sju vyer. De sju har nu
   en egen beställning (5.19). Samma med fokusflytt och uppläsningsregioner, som granskarna fick
   påpeka gång på gång.
8. **Samma layoutfel i flera omgångar.** Kolumnbredder, vyrad, knappar under vecket. De skrevs in som
   regler i den gemensamma beställningen först efter fjärde steget. Lärdom: första gången ett fel syns
   i bild blir det en mätbar regel.
9. **Grenens omfång gled.** Den började som kundsynk och API och bär nu tre lager, varav ett ändrar
   delad backend. Ägaren beskrev den sista dagen som "enbart CRM-delen". Lärdom: säg vad grenen bär i
   varje rapport, och planera lagren som egna grenar från början.
10. **Logik kopierades.** Två funktioner ligger som kopior, eftersom dagens komponenter inte fick
    röras och logiken låg i en komponentfil. Lärdom: gör ett undantag för att flytta ren logik till
    ett delat bibliotek, tidigt och med ägarens ja.
11. **Statussidan genererades ur en kedja av textbyten** mot en äldre version i en annan sessions
    scratchpad. Den höll, men varje uppdatering kunde ha fallit. Lärdom: en datafil i repot.
12. **Paritetslistan åldrades.** Det som byggdes efter läsningen står för lågt, och tolv av sexton
    delar är inte omlästa.
13. **Små saker som tog tid:** heredoc som förstörde `\n` i Python-skript (två gånger), `write_text`
    som gav CRLF, en skärmbild som skrevs över med ett urklipp, `AskUserQuestion` som kraschade hos
    ägaren, och en efterfrågad fil som inte skickades direkt.

## Vad jag skulle göra annorlunda, i ordning

1. **Dag 1, förmiddag:** fas 0. Maskin, kvot, testmiljö, licens, gränser, grenplan. Beställningarna och
   skripten får en mapp i repot.
2. **Dag 1, eftermiddag:** inventera DAGENS app helt (det hårda kravet) och förlagan på bredden. Läsare
   i omgångar om tre.
3. **Dag 2, förmiddag:** verktygslådan med det tvärgående, tre till fem vyer, förhandsvisningen. Visa
   ägaren. Vänta.
4. **Dag 2, eftermiddag:** funktionslistan och förslagen. Ägaren väljer.
5. **Dag 3 och framåt:** kärnans backend, sedan bredden i steg om en vyfamilj, två steg per omgång,
   egen bildgranskning mellan. Första inloggade körningen mot testmiljön så fort första vyn finns,
   inte på slutet.
6. **Varje kväll:** status, beslut, design, anteckning, statussida. Och meningen "grenen bär nu …".

Med den ordningen hade underkännandet kommit dag 2 i stället för dag 2 efter en hel byggomgång, det
djupa läsandet av förlagan hade begränsats till det valda, och de tjugo vyerna hade haft en backend
att svara mot.

## Tal att planera med

- Ett gränssnittssteg (en vyfamilj, 50 till 100 rader): 1 miljon subagent-tokens, 40 till 45 minuter,
  5 till 16 fynd från granskaren, 1 till 3 saker till som huvudagenten ser i bild.
- Huvudagentens del per omgång om två steg: en halvtimme till en timme (rapporter, bilder, rättning,
  kontroller, dokument).
- Ett backendbygge med granskning ur tre vinklar: ungefär samma storlek som ett gränssnittssteg.
- Trettio steg kvar betyder alltså omkring trettio miljoner tokens och ett par arbetsdygn utan stopp.
  Det är talet ägaren behöver för att säga ja eller välja.
