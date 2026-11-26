# Twentys finish: vad som gör gränssnittet polerat, uppmätt

Underlag för tre byggare av Snajp CRM. Kontraktet är `docs/crm/DESIGN-CRM.md` (version 2,
2026-11-26); den här filen säger vad i Twenty som ger känslan av färdig produkt, med mått,
och sist (avsnitt 9) vilket värde som gäller i Snajp CRM när det sätts i Astryx större former.

Snajp skriver egen kod. Twentys `twenty-front` och `twenty-server` är AGPL och har inte
lästs för att kopiera något. Värden ur MIT-paketet `twenty-ui` anges med sökväg relativt
`D:\snajp-crm-forlaga\twenty\packages\twenty-ui\`. Allt annat är mätt i bilderna eller
hämtat ur våra egna funktionsbeskrivningar (`twenty-02`, `-03`, `-04`, `-10`, `-12`,
`twenty-app-kartlaggning.md`).

## Hur bilderna är mätta

Bilderna i `docs/crm/bilder/twenty/` är 800 × 500 px (04 och 05 är utsnitt, 300 px breda).
De är nedskalade från ett fönster på 1440 × 900 px, faktor 1,8. Två kontroller ger samma
faktor: navigeringen är 122 px i bilden och 220 px enligt förlagans standardbredd (UX-111),
och en tabellrad är 18 px i bilden och 32 px enligt förlagan (twenty-02, Oklarheter). Alla
mått nedan är omräknade till 1440-skala och avrundade till närmaste steg i Twentys 4 px-skala,
om inte "i bilden" står ut. JPEG-komprimeringen suddar hårlinjer, så kantfärger anges ur
token-filerna, inte ur pixlarna.

Twentys grundmått, för att läsa resten:

| Sak | Värde | Källa |
|---|---|---|
| Typsnitt, bas | Inter, 1 rem = 13 px; sm 0,92 rem (12 px), xs 0,85 rem (11 px), lg 1,23 rem (16 px), xl 1,54 rem (20 px) | `design-tokens/font.ts`; 13 px bekräftat i `twenty-app-kartlaggning.md` |
| Vikter | 400, 500, 600; ingen 700 | `design-tokens/font.ts` |
| Textens gråtoner (ljust) | primär gray12 (p3 0,2), sekundär gray11 (0,4), tertiär gray9 (0,6), ljus gray8 (0,7), extra ljus gray7 (0,8) | `design-tokens/font.ts`, `src/theme/constants/GrayScaleLight.ts` |
| Ytor | primär gray1 (vit), sekundär gray2 (0,988), tertiär gray4 (0,945) | `design-tokens/background.ts` |
| Kanter | ljus gray4, medel gray5, stark gray6 (0,839) | `design-tokens/border.ts` |
| Radier | xs 2, sm 4, md 8, lgRound 12, lg 16, xl 20, xxl 40, pill 999 | `design-tokens/border.ts` |
| Avstånd | steg om 4 px, plus 2 och 6 | `design-tokens/spacing.ts` |
| Ikoner | 14 / 16 / 20 / 24 px, linje 1,6 / 2 / 2,5 | `design-tokens/icon.ts` |
| Tabell | cellutfyllnad 8 px, cellmarginal 8 px, kryssrutekolumn 32 px | `design-tokens/table.ts` |
| Tider | 75 / 150 / 300 ms, 1,5 s; bakgrundsövergång 0,1 s ease | `src/theme/constants/ThemeCommon.ts` |
| Skuggor | `light` (två 4 px-skuggor på 4 och 8 % svart), `strong` (16 px på 16 % + 4 px på 8 %) | `design-tokens/boxShadow.ts` |
| Syskonavstånd | 2 px mellan intilliggande rader i menyer | `ThemeCommon.ts` (`betweenSiblingsGap`) |

Det viktigaste i tabellen: **hierarkin bärs av gråton, inte av storlek.** Nästan allt är
13 px. Det som skiljer rubrik, etikett och värde är steget i gråskalan och vikten 500.

## 1. Navigeringen

Bilder: 02, 03, 11 (undermeny), 16 (inställningsläget).

**Bredd och yta.** 220 px (UX-111: dragbar 180 till 350, infälld 48 px med bara ikoner).
Navigeringen ligger på sekundär yta (uppmätt `#f9f9f9`), innehållet bredvid på vit. Det finns
ingen synlig kantlinje mellan dem i bilden; skillnaden är en halv gråton. Innehållet är alltså
redan ett ljusare blad bredvid en tvättad kolumn, bara mycket svagare än Astryx `elevated`.

**Överst (y 0 till 48 px), samma höjd som sidhuvudet:** arbetsyteväxlaren till vänster:
fyrkantig logotyp 16 px med rundat hörn (en grön "S" på tonad platta), arbetsytans namn i
13 px vikt 500, en liten nedåtvinkel i tertiär ton. Till höger två ikonknappar utan ram:
sök och fäll ihop. Raden flukter med sidhuvudets rubrik, så navigering och innehåll delar en
gemensam topplinje.

**Lägesraden (y ≈ 56 till 84 px):** tre lägen, Hem, AI-chatt och Inställningar. Hem är en
platta med ikon och text, de andra två är bara ikoner. Valt läge får plattan, 28 px hög.

**Sektioner.** Sektionsetiketten ("Workspace") står i ungefär 11 till 12 px, tertiär gråton,
gemener med versal begynnelsebokstav, ingen spärrning, ingen linje. Den har cirka 16 px luft
ovanför och 8 px under. I inställningsläget finns tre sektioner: User, Workspace, Other.

**Poster.** Plattan är 28 px hög och raderna står med 30 px steg (28 + 2 px syskonavstånd).
Ikonen är 16 px och **färgad per objekt** (Companies blå, People blå, Opportunities röd,
Tasks och Notes turkos, Dashboards grå, Workflows orange, Campaigns lila); texten är 13 px
vikt 400. Ikon och text har 8 px mellanrum, och ikonen står cirka 12 px från lådans kant.
Poster med undernivå har en vinkel längst till höger i tertiär ton.

**Vald och hover.** Vald post är en grå platta (`background.transparent.light`, uppmätt
`#efefef`) som går från 7 px till 9 px från kanterna, med radie 4 px (`ListItem`:
`md − 4px`, `src/primitives/navigation/ListItem/ListItem.module.scss`). Texten i vald post
blir primär gråton, övriga poster är sekundär. Hover ger samma platta som vald; övergången är
75 ms. Ingen accentfärg, ingen vänsterstapel, ingen fet text.

**Undernivå (bild 11).** Workflows fälls ut med två barn ("Workflows", "Workflow Runs"),
indragna cirka 24 px, med tunna trädlinjer i ljus gråton från förälderns ikon ned till
barnen. Det valda barnet får plattan; föräldern behåller sin vanliga ton.

**Nederst.** Ett litet vitt kort "Getting started" (cirka 210 × 100 px, 6 px från lådans
kanter, radie 8 px, hårlinje plus mycket lätt skugga): rubrik 13 px vikt 500 med vinkel,
en förloppsstapel 4 px hög och helt rundad i ljus gråton, och en knapp över hela bredden
("Keep Twenty") på tertiär platta. I inställningsläget står i stället raden "Logs" med en
växel. Kortet är det enda upphöjda elementet i lådan.

## 2. Sidhuvud och vyrad

Bilder: 02, 03, 06, 09, 13.

**Sidhuvudet är 48 px** (uppmätt 26 px i bilden; NAV-133 och UX-093 anger 48). Bakgrund
`#fcfcfc`, alltså gray2, en hårsmån mörkare än tabellen under. Till vänster objektets ikon
16 px i objektets färg och namnet i **13 px vikt 500 primär**. Rubriken är alltså inte
större än brödtexten. På en postsida eller dashboard blir rubriken en brödsmula:
"Dashboards / My First Dashboard (1/1)" där föräldern är tertiär och sista ledet primär,
avskilda med ett snedstreck i ljus ton.

Till höger: **en enda fylld knapp** ("+ Create"), 24 px hög (uppmätt 14 px i bilden),
cirka 76 px bred, blå accent med vit text i 13 px vikt 500, radie 4 px, plus-ikon 14 px.
Därefter ikonknappar 24 × 24 px utan ram (Ask AI, ⋮). Knappen är liten; den syns för att
den är det enda färgade på sidan, inte för att den är stor.

**Vyraden är 39 px** (UX-093), vit, utan synlig underlinje i bilden. Vänster: vyikonen
16 px (tabell), vyns namn i 13 px vikt 500 primär, sedan "· 5" i tertiär ton och en liten
nedåtvinkel. Höger: **Filter, Sort, Options som rena textknappar** i 13 px, sekundär ton,
24 px höga, utan ikon och utan ram. Den knapp vars meny är öppen får en ram i stark grå och
radie 4 px (bild 06: Sort), övriga är nakna. Mellan knapparna cirka 4 px.

**Menyerna från vyraden (bild 03, 04, 05).** Rutan är cirka 240 px bred, vit, radie 8 px,
kant medel grå, skugga `strong`, 8 px från utlösaren (UX-099). Rader 32 px med ikon 16 px
och text 13 px; ett värde till höger i tertiär ton ("Table", "Workspace", "7 selected")
följt av en vinkel. Den översta raden är vyns namn som går att redigera. Destruktiva rader
är röda med röd ikon ("Delete view"). En undersida får rubrikrad med tillbaka-vinkel och
titel; valt alternativ har en bock längst till höger (bild 04). Filtermenyn (bild 05) börjar
med en sökruta och delar fälten i "Visible fields" och "Hidden fields", etiketterna i 11 px
tertiär ton.

## 3. Tabellen

Bilder: 02, 09, 10, 11.

**Rader.** Kolumnhuvudet och varje rad är **32 px** (fast, ingen täthetsinställning;
twenty-02 Oklarheter). Tabellen har både vågräta och lodräta hårlinjer i ljus grå (gray4),
så varje cell är en ruta, men linjerna är så ljusa att de knappt syns i bilden: rutnätet
ordnar utan att rita. Ingen randning. Kolumnhuvudet har samma vita yta som raderna.

**Cellmarginal.** 8 px utfyllnad i sidled i varje cell (`design-tokens/table.ts`).
Kryssrutekolumnen är 32 px; första datakolumnen (namn) är cirka 200 px, övriga 150 till
180 px. Längst till höger i huvudet en "+"-kolumn för att lägga till fält.

**Kolumnrubrik.** Fälttypens ikon 16 px (länk för domän, cirkel med person för ägare,
kalender för datum, karta för adress, telefon, mejl) och rubriken i 13 px vikt 400,
**båda i tertiär ton**. Rubriken kortas med ellips ("Domain ..."). Sorterad kolumn får en
pil efter rubriken (bild 11: "Last update ↓"). Rubriken är alltså svagare än datan under,
inte starkare.

**Postchip (första kolumnen).** Uppmätt 20 px högt; logotypen 14 px. Byggt som
`Chip`, `src/primitives/data-display/Chip/Chip.module.scss`: höjd 12 + 2 × 4 = 20 px,
utfyllnad 4 px på båda sidor, 4 px mellan logotyp och namn, radie 4 px, varianten "soft"
med bakgrunden `transparent.light` (uppmätt `#f1f1f1`). Namnet i 13 px vikt 400 primär,
inte fetstil. Bolag har fyrkantig logotyp med 2 till 4 px radie; personer har en
bokstavsavatar på tonad platta (bild 09: "B Brian Chesky", bokstaven i färgens steg 11 på
steg 3). Avatarstorlekar ur `src/primitives/data-display/Avatar/Avatar.module.scss`:
md 16 px (text 12 px), sm 14 px (text 10 px), radie 2 px för kvadrat, 4 px för rundad
kvadrat, 50 % för cirkel. Hover på klickbart chip mörkar plattan ett steg
(`transparent.medium`), tryck ett steg till. Chipet är smalare än cellen: det omsluter sitt
innehåll och resten av cellen är tom.

**Länkpiller.** Domän, mejl och telefon visas som utlinjerade piller: 20 px höga, helt
rundade, 1 px kant i stark grå (gray6), nästan genomskinlig fyllning, 8 px utfyllnad i
sidled, text 13 px i sekundär ton (Chip-varianten "outline"). Långa värden kortas med ellips
inuti pillret ("anthropic...."). Klick öppnar länken i ny flik och räknas inte som klick i
cellen (UX-117).

**Andra celler.** "Skapad av" är ikon plus text utan platta ("System" med kugghjul). Relativ
tid står som ren text i primär ton ("5 minutes ago"). Tom cell är helt tom, inget streck.
Status som tagg (bild 11: "Active" på grön platta i steg 3 med text i steg 11, 20 px hög,
radie 4 px, `src/primitives/data-display/Tag/Tag.module.scss`).

**Kryssrutor.** Rutan är 12 px med 1 px kant (`src/primitives/input/Checkbox/
Checkbox.module.scss`), radie 4 px, centrerad i 32 px-kolumnen. Kanten är sekundär
inverterad grå, så rutan syns tydligt men stilla. Hover ger en platta runt rutan
(`transparent.light`, radie 8 px). Ikryssad ruta fylls med accenten och vit bock;
huvudets ruta blir "delvis" (streck) när bara några rader är valda (UX-027).

**Raden Lägg till.** Direkt under sista raden: "+ Add New" i tertiär ton, plus-ikonen
14 px, texten börjar i namnkolumnens textlinje, 32 px hög. I en grupp heter den "Add new"
och står sist i gruppen; på tavlan "+ New" (VY-134).

**Foten.** En rad 32 px under "Add New": under namnkolumnen "Calculate" med vinkel i
tertiär ton; under varje kolumn som har ett aggregat en etikett i tertiär ton och talet
i primär ton vikt 500: "Count all **5**", "Empty of Linkedin **100%**",
"Not empty of Address **5**". Kolumner utan aggregat är tomma i foten. Etikett och tal
står i samma cellmarginal som datan, så foten läses som en del av tabellen, inte som en
separat ruta.

**Hover och markering.** Hover på en rad ger en mycket svag platta över hela raden
(`transparent.lighter` till `light`); linjerna ändras inte. En vald rad får en svag
accenttonad bakgrund. Varken markeringsläget eller åtgärdsraden för markerade poster finns
i de sjutton bilderna; de beskrivs här ur funktionsunderlaget (VY-128, NAV-065, NAV-069):
när minst en rad är markerad byter sidhuvudets högerdel till åtgärder för markeringen
(radera, exportera, favorit, och fler under ⋮ samt i kommandomenyn), och antalet markerade
styr vilka åtgärder som visas. Tangentbord: x markerar, Shift+x markerar ett intervall,
Ctrl/Cmd+A markerar alla, Escape avmarkerar (VY-127). Byggaren ska fotografera Snajps egen
markering och inte anta att den liknar Twentys.

**Tomläge (bild 10).** Kolumnhuvudet står kvar. Mitt i ytan en illustration (cirka 160 px
bred, isometrisk, blå), rubrik i cirka 16 px vikt 600 primär, en rad i tertiär ton och en
knapp "+ Add a Task" med ram, 24 px hög. Hela gruppen är centrerad i höjdled i ytan under
huvudet.

**Arbetsflödeslistan (bild 11)** visar samma tabell med tal högerställda ("0"),
"Workspace" som grå tagg och en bokstavsavatar på tonad platta före namnet. Raden
"+ New Workflow" står i stället för "Add New".

## 4. Postens sidopanel

Bilder: 06 (panelen), 07 (helsidan, samma innehåll i vänsterkolumnen).

**Bredd.** Uppmätt 222 px i bilden, alltså **400 px**, vilket är förlagans standard
(PS-021: dragbar 320 till 600 px). `twenty-ui` anger 500 px som `sidePanelWidth`
(`src/theme/constants/ThemeCommon.ts`); appen i bilden använder 400. Panelen skjuts in
från höger och listan står kvar till vänster, smalare. Den skiljs från listan med en
hårlinje; ingen skugga syns.

**Huvud, 48 px** (samma höjd och topplinje som sidhuvudet): logotyp 16 px, namnet i
13 px vikt 500 primär, till höger två ikonknappar 24 px (fäll ut till helsida, stäng).
På helsidan (bild 07) är namnet cirka 16 px vikt 600 med en 24 px logotyp.

**Flikar, 40 px** (UX-103: höjd 40, mellanrum 4 px): ikon 16 px plus text 13 px, aktiv
flik i primär ton med en **1 px understrykning i inverterad grå** (nästan svart), övriga i
sekundär ton utan linje (`src/components/navigation/TabButton/TabButton.module.scss`).
Flikar som inte ryms samlas i "+4 More" med vinkel. Under flikraden en hårlinje över hela
bredden.

**Fältgrupper.** Först rubriken "Fields" i 13 px vikt 500 primär. Sedan grupperna
(General, Business, Contact, System): grupprubriken i 13 px vikt 400 **tertiär**, med en
uppåtvinkel längst till höger för att fälla ihop. Varje fältrad är 32 px (uppmätt 18 px i
bilden) och har tre delar:

| Del | Bredd och läge | Ton |
|---|---|---|
| Ikon | 16 px, cirka 12 px från panelens kant | ljus (gray8) |
| Etikett | slutar cirka 120 px från kanten, kortas med ellips ("Annual Reven...") | ljus till tertiär |
| Värde | börjar cirka 133 px från panelens kant och fyller resten | primär |

Etikettkolumnen är alltså ungefär en tredjedel av panelen. Tonskillnaden mellan etikett och
värde är tre till fyra steg i gråskalan (gray8 mot gray12), så ögat hoppar till värdena.
Tomt värde visar **fältets eget namn i extra ljus ton** ("Account Owner", "Annual Revenue")
på värdets plats; det är både platshållare och klickyta för att redigera. Ett värde som är
en länk visas som samma piller som i tabellen ("airbnb.com"). Mellan grupperna cirka 8 px
extra luft, inga linjer. `twenty-ui` har samma mönster som komponent: `DetailsRow`
(`src/components/data-display/DetailsRow/DetailsRow.module.scss`) med etikett i tertiär ton,
etikettbredd högst 40 %, radhöjd 24 px och 4 px mellanrum.

**Relationssektioner.** Efter fältgrupperna, avskilda med en hårlinje över hela bredden:
"People", "Opportunities". Rubriken i 13 px vikt 500 primär; till höger två ikonknappar i
ljus ton, ↗ (öppna listan) och penna (ändra kopplingar). Under rubriken de relaterade
posterna som chips (samma 20 px soft-chip som i tabellen, med bokstavsavatar 14 px på
tonad platta). Varje sektion har cirka 16 px utfyllnad uppe och nere.

**Fot, 40 px:** fast längst ned, en hårlinje ovanför, svag grå bakgrund. Högerställt:
⋮ (fler åtgärder), hjärta (favorit) och "Send Email" med kuvertikon som en ljus knapp,
24 px hög (UX-106). Inget vänsterställt.

**Helsidan (bild 07)** delar ytan i en vänsterkolumn cirka 340 px med postens namn,
fältgrupper och relationer, och en högerdel med flikraden (Timeline, Tasks, Notes, Files,
Messages, Calendar). Sidhuvudet bär brödsmulan "Companies / Airbnb (1/5)" och pilar upp
och ned till föregående och nästa post. Tom tidslinje visar illustration, rubrik och en
rad i tertiär ton, centrerat.

## 5. Dashboarden

Bild: 13 (och 14, samma dashboard bakom kommandomenyn).

**Rutnät.** 12 kolumner på dator, 1 på mobil, radhöjd 55 px, marginal 8 px mellan rutor
(DB-116). Standardstorlek för en ny widget 4 × 4 rutor, minst 2 × 2 (DB-010). I bilden står
två kort per rad, alltså 6 kolumner vardera: cirka 590 px breda och cirka 365 px höga
(cirka 6 rader à 55 px plus marginaler). Mellanrummet mellan korten är uppmätt 5 px i
bilden, alltså 8 px. Ytan runt korten är vit och har 8 px marginal mot navigeringen.

**Kort.** Fyllning gray2 (uppmätt `#fcfcfc`), alltså en hårsmån mörkare än sidan; kant 1 px
i medel grå; radie 8 px; ingen skugga (`src/primitives/surfaces/Card/Card.module.scss`:
kant `border-color-medium`, radie `md`). Kortet syns genom kant och halv gråton, inte genom
höjd. Titeln står i övre vänstra hörnet, 13 px vikt 500 primär, cirka 12 px från kortets
kanter. Ingen undertitel, ingen ikon, ingen avdelare under titeln. Ett textkort (vänster
överst) har brödtext i 13 px sekundär ton med radhöjd 1,5 och en understruken länk.

**Ringen ("Deals by Company").**

- Ytterdiameter cirka 266 px i ett 590 px brett kort, centrerad i kortets bredd.
- Ringens tjocklek cirka 30 px, alltså drygt en niondel av diametern; innerradien är cirka
  77 % av ytterradien. Ringen är tunn nog att läsas som en form, inte som en tårta.
- Sektorerna har **raka ändar** och skiljs av ett vitt mellanrum på cirka 2 px.
- Färgerna är **en enda kulör i fyra steg** (orange, från blekt till mättat), inte fyra
  olika kulörer. Största sektorn är mörkast.
- Mitten: totalen i cirka 28 px vikt 500 primär, under den "Total" i 13 px tertiär.
- Förklaringen står **under ringen, vänsterställd**, på en rad: först en bläddrare
  "‹ 1/2 ›" i tertiär ton, sedan per serie en liten fyrkantig färgruta (cirka 6 px) och
  namnet i 12 px sekundär ton, med cirka 40 px mellan posterna.

**Staplarna ("Pipeline Value by Stage").**

- Stående, staplade staplar, cirka 31 px breda, med cirka 100 px mellan kategorierna.
- **Toppen är rundad cirka 4 px, botten rak** mot baslinjen. I en staplad stapel är bara
  översta segmentet rundat.
- En kulör (grön) i tre till fyra steg: serierna skiljs med ljushet, inte med kulör.
- Värdet står ovanför varje stapel i 11 px tertiär ton ("80k", "75k").
- Y-axeln: tal i 11 px tertiär ton ("150k", "100k", "50k", "0"), **ingen axellinje**,
  stödlinjerna är så ljusa att de nästan inte syns (uppmätt 250 av 255 på 252-grundton).
- X-axeln: kategorinamnen i 11 till 12 px tertiär ton, en tunn baslinje.
- Förklaringen som i ringen: under diagrammet, vänsterställd, med bläddrare.

**Linjen ("Revenue Timeline").** Tunn linje (cirka 1,5 px) i en blek rosa, ingen fyllning
under, inga punkter. Här syns rutnätet i båda riktningarna, mycket ljust. X-etiketterna
lutar 45 grader när de inte ryms.

**Sidhuvudet på dashboarden.** Brödsmulan "Dashboards / My First Dashboard (1/1)", till
höger "Edit" med penna som ljus knapp 24 px, och ikonknappar för kommandomeny, favorit och
föregående/nästa. Edit växlar till redigeringsläge där korten kan dras och ändras i storlek.

## 6. Kommandomenyn

Bild: 14.

**Var.** Ctrl+K eller Cmd+K öppnar den **som en panel till höger**, på samma plats och i
samma bredd som postpanelen (cirka 400 px), inte som en dialog mitt på skärmen. Sidan till
vänster blir smalare men täcks inte och dimmas inte. Panelen har en hårlinje mot sidan.

**Huvud, 48 px:** själva sökfältet utan ram, platshållaren "Type anything..." i ljus ton,
och ett stängkryss längst till höger. Under det en hårlinje.

**Grupper.** Ordningen följer sammanhanget: först den aktuella posten ("Selection: My
First Dashboard"), sedan objektet ("Object: Dashboards"), sedan "Ask & find", "Create
record", "Workspace", "Go to" (twenty-app-kartlaggning). Gruppens rubrikrad har en ikon
eller avatar (en bokstavsavatar för posten och arbetsytan, förstoringsglas, plus), text i
13 px vikt 500 primär, och en hårlinje under. Cirka 8 px luft ovanför varje grupp.

**Rader, 32 px** (uppmätt 18 px i bilden). Varje kommando har sin ikon i en **liten grå
ruta** (cirka 20 px, radie 4 px, ikonen 14 till 16 px; jfr `TintedIconTile`,
`src/components/data-display/TintedIconTile/TintedIconTile.module.scss`: 16 px, radie
`sm`), etiketten i 13 px vikt 400 sekundär ton. Till höger ett kortkommando i tertiär ton
("/", "@") och en vinkel när raden öppnar en undersida. Markerad rad (tangentbord eller
hover) är en grå platta (uppmätt `#f5f5f5`) med 4 px radie, 8 px indragen från panelens
kanter. Rubrikraden markeras aldrig. En tunn rullningslist syns längst till höger.

**Beteende** (NAV-055, NAV-058): skriv för att filtrera (skiftläges- och accentokänsligt,
matchar även kortkommandot), pilar flyttar markeringen, Enter kör, Escape tömmer först
sökningen, sedan går tillbaka en sida, sedan stänger. Backsteg i tomt fält går tillbaka.

## 7. Tavlan (kanban)

Bild: 08.

**Kolumner.** 200 px breda (uppmätt 111 px steg i bilden; VY-149: standard 200, dragbar
150 till 400). Kolumnerna skiljs av en lodrät hårlinje i ljus grå som går hela höjden;
ingen kolumnbakgrund, ingen ram runt kolumnen.

**Kolumnhuvud,** cirka 32 px: stegets namn som **tagg** (20 px hög, radie 4 px, färgens
steg 3 som platta och steg 11 som text: New röd, Screening lila, Meeting blå, Proposal
grön, Customer gul), och direkt efter, 8 px bort, kolumnens summa i tertiär ton ("80k").
Inget antal-märke, ingen meny synlig utan hover.

**Kort.** Cirka 185 px brett (8 px luft mot kolumnlinjerna), fyllning gray2, kant 1 px i
ljus grå, radie 4 till 8 px, ingen skugga i vila. Utfyllnad cirka 8 px. 8 px mellan korten.

- Kortets huvud: bokstavsavatar 14 px på tonad platta och postens namn i 13 px **vikt
  500** primär, kortat med ellips.
- Därefter en rad per fält, cirka 24 px höga, **utan etiketter**: bara fältets ikon 16 px i
  ljus ton och värdet. Belopp och datum som ren text i primär ton, relationer som samma
  soft-chip som i tabellen (bolagets logotyp, personens bokstavsavatar).
- Under sista kortet "+ New" i tertiär ton.

Utan etiketter blir kortet en lista av värden som ikonerna förklarar. Det är det som gör
korten korta.

## 8. Tjugo detaljer som gör att det känns färdigt

Varje punkt går att mäta i en skärmbild av Snajp CRM.

1. **En enda storlek på text.** Data, etiketter, rubriker i sidhuvud och panel, knappar och
   menyrader är alla 13 px. Bara tomlägets rubrik och helsidans postnamn är större.
2. **Hierarki med gråton.** Primär, sekundär och tertiär text ligger på p3-ljushet 0,2,
   0,4 och 0,6: varje steg är ett lika stort hopp, och sekundär text är alltid exakt ett
   steg ljusare än den text den beskriver.
3. **Etiketter är svagare än värden.** Kolumnrubriker och panelens fältetiketter står två
   till tre steg ljusare än datan, med ikonen i samma ton som etiketten.
4. **Vikt 500 är den enda betoningen.** Ingen 700 någonstans. 500 används för sidrubrik,
   vyns namn, gruppnamn, kortets namn och talet i foten; allt annat är 400.
5. **Ikoner är 16 px överallt där text är 13 px**, 14 px inne i chips och taggar, och de
   står alltid 8 px från sin text.
6. **Hover är en platta, inte en färg.** En grå platta med 4 px radie (`transparent.light`)
   för menyposter, chips, kryssrutor och knappar; tryck mörkar ett steg till. Övergången är
   0,1 s på bakgrunden och inget annat rör sig.
7. **Plattan är indragen.** Vald navigationspost och markerad kommandorad slutar 7 till
   9 px från kanterna, så plattan svävar i sin kolumn och rör aldrig kanten.
8. **Allt ligger på 4 px-steg:** 28 px menypost, 32 px tabellrad och menyrad, 40 px flikrad,
   48 px sidhuvud. Syskonrader har 2 px mellan sig.
9. **Gemensam topplinje.** Arbetsyteväxlaren, sidhuvudets rubrik och sidopanelens huvud
   har samma höjd (48 px) och samma mittlinje i höjdled, tvärs över tre ytor.
10. **En färgad knapp per sida.** "Create" är det enda fyllda; Filter, Sort och Options är
    naken text som får en ram först när deras meny är öppen.
11. **Färg betyder objekt.** Färg finns bara i objektikoner, taggar, avatarplattor och
    diagram. Ytor, linjer och text är grå.
12. **Chips är innehållsbreda.** Ett postchip eller ett länkpiller omsluter sin text med
    4 respektive 8 px utfyllnad; det sträcks aldrig till cellens bredd.
13. **Två sorters piller med olika uppgift:** soft-chip (grå platta, 4 px radie) för poster
    man öppnar, utlinjerat piller (helt rundat, 1 px kant) för länkar som lämnar appen.
14. **Avatarplattan bär namnets färg.** Bokstaven står i färgens steg 11 på samma färgs
    steg 3, och färgen väljs deterministiskt ur namnet, så samma person har samma färg i
    tabell, panel, kort och kommandomeny.
15. **Linjerna är nästan osynliga.** Tabellens rutnät, kortens kant och panelens avdelare
    är gray4 till gray5 på vitt; de ordnar, men ögat ser dem inte förrän det letar.
16. **Tomt värde visar fältets namn** i extra ljus ton på värdets plats, i stället för ett
    streck eller "Tom". Platshållaren är samtidigt redigeringsytan.
17. **Foten talar i ord:** "Count all 5", "Empty of Linkedin 100%", med etiketten tertiär
    och talet primärt i vikt 500, i samma cellmarginal som raderna ovanför.
18. **Panelens fältrader är ett tredjedelsrutnät:** ikon och etikett i första tredjedelen
    (cirka 120 px av 400), värdet från 133 px, varje rad 32 px.
19. **Diagrammen är enfärgade ramper.** En kulör i fyra steg, ringens sektorer skilda av
    2 px vitt, staplar med 4 px rundad topp och rak botten, värden i 11 px tertiär ton ovanför,
    ingen axellinje, stödlinjer på gränsen till osynliga, förklaringen under och till vänster.
20. **Sekundärt öppnas åt höger.** Post, kommandomeny och AI delar samma panel om 400 px
    till höger. Listan täcks aldrig och dimmas aldrig, så användaren tappar inte sin plats.

## 9. Så översätts det till Snajp CRM

Regeln från kontraktet: där källorna drar isär vinner **Twenty på struktur, Astryx på
form, Snajp på färg och rubrik**. Twentys proportioner och tonsteg behålls, men varje mått
skalas upp till Astryx större former: bas 14 px (16 px på pekskärm under 1024 px),
kontroller 32 / 36 / 44 px, radier 6 (inre) / 10 (element) / 16 (behållare) / 24 (sida).
Omräkningen är ungefär × 1,1 för text, × 1,35 för höjder och × 1,5 för radier: Snajp blir
luftigare och rundare än Twenty, men lika lugnt.

### Grundöversättning

| Twenty | Snajp CRM | Kommentar |
|---|---|---|
| Inter 13 px, 400/500 | Geist 14 px (16 på pekskärm), 400/500; Fraunces bara i sidrubrik, postnamn i panelen och nyckeltal | Kontraktet: Fraunces i rubriker, Geist halvfet i paneltitlar |
| Primär text gray12 | `--ink` | |
| Sekundär gray11 | `--ink2` för värden som ska läsas, `--ink-muted` för sekundär text | |
| Tertiär gray9 och ljus gray8 | `--ink-muted` (etiketter, kolumnrubriker) och `--ink-subtle` (ikoner, platshållare) | Twentys tertiära ton når inte 4,5:1 på vitt; Snajps dämpade tokens gör det och ska mätas i båda lägena |
| Yta vit / gray2 | Bladet `--paper`, tvätten `--paper2` | Skillnaden blir tydligare än Twentys halva gråton, vilket är avsikten (Astryx `elevated`) |
| Hover `transparent.light` | `ink/5` | Lika svag som Twenty i förhållande till ytan |
| Vald `transparent.light` | `ink/7` (kontraktet) | |
| Tryck `transparent.medium` | `ink/10` | |
| Kanter gray4/gray5 | `ink/8` (hårlinjer i tabell och panel), `ink/12` (kort, fält) | Skuggan `--shadow-low` är en hårlinje |
| Radie 4 / 8 / 12 / 16 | 6 / 10 / 16 / 24 | |
| Ikon 16 px, linje 2 (14 px, 1,6) | 16 px med linje 1,75 i tabell, panel och menyer; 18 px i navigeringen; 14 px i chips och piller | Linjen tunnas något för att följa Geist |
| Fokus: blå ring | Ockra, 2 px, 2 px avstånd | Kontraktet och DESIGN.md |
| Tider 75 / 150 / 300 ms | Bakgrundsövergång 100 ms; menyer och paneler `--dur-short` (180 ms) med `--ease-out`; inga uppräkningar | Läge Operate |

### Punkt för punkt

**1. Navigeringen.**
- Bredd **248 px** (Twenty 220), hopfällbar. Yta `--paper2`, utan rail i bläck.
- Arbetsyteväxlaren i en rad som flukter med sidhuvudet: avatar **28 px**, radie 6, i
  `--ink` med initialen i `--paper`; namnet 14 px vikt 600; vinkel 16 px `--ink-subtle`;
  till höger ikonknapp 32 px (kommandopaletten).
- Sök-raden: 36 px, radie 10, `ink/5`-platta, "Sök eller hoppa till" i `--ink-muted`,
  `Kbd` Ctrl K till höger.
- Poster: platta **36 px** (Twenty 28), 2 px mellan raderna (radsteg 38 px), radie **10**,
  indragen 8 px från lådans kanter, ikon 18 px, 10 px mellan ikon och text, text 14 px.
  Ikonen står på objektets färgade platta enligt kontraktet (14 procents alfa).
- Vald: `ink/7`, text `--ink` vikt 600 (kontraktet; Twenty byter bara ton). Hover: `ink/5`.
  Övriga poster: text `--ink2`, vikt 400.
- Sektionsetikett ("Arbetsyta", "Data"): 12 px vikt 500 `--ink-muted`, versal bara på
  första bokstaven, 20 px luft ovanför och 6 px under.
- Nederst: synkkortet, radie **16**, 8 px från lådans kanter, utfyllnad 12 px,
  `--paper` med `--shadow-low`; statusprick 8 px, rubrik 13 px vikt 500, tid i `--ink-muted`,
  förloppsstapel 4 px helt rundad i ockra på `ink/8`. Därunder länken Till arbetsytan som
  vanlig post.

**2. Sidhuvud och vyrad.**
- Sidhuvud **64 px** (Twenty 48). Ikonplatta 32 px radie 10, 12 px till rubriken.
  Rubriken i Fraunces 1,625 rem normal vikt: här avviker Snajp medvetet från Twentys
  13 px-rubrik. Antalet som neutral etikett (helt rundad, 22 px, 12 px vikt 500).
- Primärknappen **36 px**, radie 10, `--ink` med `--paper`-text, 14 px vikt 500, ikon 16 px,
  utfyllnad 14 px i sidled. Fler-knappen 36 × 36 px utan fyllning. Fortfarande bara **en**
  fylld knapp per sida.
- Vyrad **52 px** (Twenty 39) under en hårlinje `ink/8`. `SegmentedControl` 36 px helt
  rundad, segment med antal i `--ink-muted`. Sökfält 36 px, 260 px brett, helt rundat.
  Sortera 32 px. Knappar som Twentys Filter/Sort är text i `--ink2` vikt 500 som får platta
  `ink/5` vid hover och ram `ink/12` när menyn är öppen.
- Menyer från vyraden: 240 px breda, radie **16**, `--shadow-med`, 8 px från utlösaren,
  rader 36 px med radie 10, värden till höger i `--ink-muted`, destruktiv rad i `--danger`.

**3. Tabellen.**
- Rad **44 px** (`density="balanced"`; Twenty 32). Kolumnhuvud 40 px. Både vågräta och
  lodräta hårlinjer i `ink/6` till `ink/8`, ingen randning.
- Cellutfyllnad **12 px** i sidled (Twenty 8).
- Kolumnrubrik: ikon 14 px `--ink-subtle` plus rubrik 13 px vikt 600 `--ink-muted`
  (kontraktet; Twenty har 400). Rubriken ska fortfarande vara svagare i ton än datan.
- Kryssrutekolumn 44 px, rutan 16 px, radie 6 (inre), kant `ink/30`; hover ger platta
  `ink/5` med radie 10 runt rutan; ikryssad fylls med `--ink` och bock i `--paper`,
  huvudets ruta "delvis" med streck.
- Postchip: höjd **30 px**, utfyllnad 4 px vänster och 8 px höger, 8 px mellan avatar och
  namn, radie **6**, platta `ink/5` som blir `ink/8` vid hover och `ink/12` vid tryck.
  Avatar **22 px** (bolag radie 6, personer runda), initialer 11 px vikt 600 i färgens
  textsäkra ton på färgen med 14 procents alfa, färgen ur objektfärgerna med namnets hash.
  Namnet 14 px vikt 600 `--ink` (kontraktet). Innehållsbrett, aldrig cellbrett.
- Länkpiller (`Token`): **26 px**, helt rundat, 1 px kant `ink/14`, fyllning `--paper`,
  utfyllnad 10 px, ikon 14 px, text 13 px `--ink2`; kortas med ellips vid 200 px.
- Relation: helt rundad etikett 24 px med statusprick 8 px enligt kontraktets färger.
- Tal och tider tabulära; relativ tid i `--ink-muted`.
- Hover på rad: `ink/3` över hela raden. Markerad rad: `ochre/8` plus kryssrutan.
  När något är markerat: `TableSelectionToolbar` (helt rundad, `--shadow-med`, 44 px,
  "3 markerade" till vänster, åtgärderna som 32 px-knappar).
- Raden "Lägg till bolag": 44 px, plus 16 px och text i `--ink-muted`, i namnkolumnens
  textlinje; hover `ink/3`.
- Fot: 40 px, etikett i `--ink-muted`, talet i `--ink` vikt 600 tabulärt
  ("73 bolag", "46 är kunder, 63 %"), i samma cellutfyllnad som raderna.

**4. Postens panel.**
- Bredd **520 px** (Twenty 400, alltså × 1,3). `Drawer` från höger med `--shadow-high`
  och radie 24 på den fria kanten mot innehållet; listan täcks inte mer än panelens bredd.
- Huvud: avatar 44 px, namnet i Fraunces 1,375 rem, organisationsnummer i 13 px
  `--ink-muted`, relationsetiketten. Ikonknappar 36 px för Redigera och Stäng.
- Snabbval: runda ikonknappar 36 px med 8 px mellanrum, `ink/5`-platta.
- Flikar **44 px**, ikon 16 px plus text 14 px, aktiv flik `--ink` med 2 px understrykning
  i ockra (Astryx `TabList`), övriga `--ink-muted`; hårlinje `ink/8` under raden.
- Fältgrupper (`MetadataList`): grupprubrik 13 px vikt 600 `--ink-muted`; rader **40 px**
  (Twenty 32). Ikon 16 px `--ink-subtle`, etikett 14 px `--ink-muted` i en kolumn om
  **160 px** (en knapp tredjedel av 520, som hos Twenty), värdet `--ink` från 176 px.
  Tomt värde: "Lägg till" i `--ink-subtle`, klickbart med hover-platta `ink/5` radie 6.
  16 px luft mellan grupperna, inga linjer.
- Relationssektioner (fliken Personer): rader 52 px med rund avatar 28 px, namn 14 px
  vikt 600, titel 13 px `--ink-muted`, piller för mejl och telefon.
- Fot 64 px, hårlinje ovanför, åtgärder högerställda som 36 px-knappar.

**5. Översikten (dashboarden).**
- Rutnät 12 kolumner med **16 px** mellanrum (Twenty 8) och 24 px marginal mot bladets
  kant. Nyckeltalen 4 × 3 kolumner; ring och synklista 6 + 6; orter och senast ändrade
  6 + 6. En kolumn under 640 px.
- Kort: radie **16** (Twenty 8), utfyllnad 20 px, `--paper` på bladet med kant `ink/8` och
  `--shadow-low`, ingen skugga i vila. Titel 14 px Geist vikt 600 `--ink` i övre vänstra
  hörnet, inget under den. Det framhävda kortet (Att rätta) har ockratonad platta.
- Nyckeltal: etikett 13 px `--ink-muted` överst, talet Fraunces 2,5 rem tabulärt, rad under
  i 13 px `--ink-muted`.
- Ringen: ytterdiameter 200 px, **innerradie 68 %** av ytterradien (tjockare och lekfullare
  än Twentys 77 %), sektorer med 2 graders mellanrum och **6 px rundade hörn** (Astryx form;
  Twenty har raka ändar). Färgerna är kontraktets relationsfärger, inte en ramp, eftersom
  sektorerna betyder olika saker. Mitten: totalen i Fraunces 2 rem, "bolag" i 13 px
  `--ink-muted`. Förklaringen under ringen, vänsterställd, prick 8 px och namn 13 px `--ink2`
  med talet i `--ink` vikt 600.
- Liggande staplar (orter): stapel 12 px hög och **helt rundad** (radie 6), spår `ink/6`
  bakom, ockra för den största och `--chart-ramp` för resten. Namnet till vänster 14 px
  `--ink2`, talet till höger tabulärt `--ink` vikt 600. Ingen axel, inga stödlinjer.
- Står stående staplar någon gång: bredd 28 till 36 px, radie 6 i toppen och rak botten
  som hos Twenty, värde ovanför i 12 px `--ink-muted`, axeltal 12 px `--ink-subtle`, ingen
  axellinje, stödlinjer `ink/6`.
- Senaste synkarna och senast ändrade: listrader 44 px med statusprick eller postchip, tid
  i `--ink-muted` till höger.

**6. Kommandopaletten.**
- Placering enligt kontraktet: Astryx `CommandPalette` som dialog, inte Twentys högerpanel.
  Från Twenty tas raden, grupperna och tangentbordet.
- Bredd **640 px**, radie **16**, `--shadow-high`, överst i fönstret (cirka 15 % ned).
- Sökfältet 52 px utan ram, 16 px text, platshållaren i `--ink-subtle`; hårlinje under.
- Grupper: Gå till, Skapa, Bolag. Gruppetikett 12 px vikt 500 `--ink-muted`, ingen linje,
  8 px luft ovanför.
- Rader **40 px**, radie 10, indragna 8 px. Ikonen i en ruta 24 px radie 6 med `ink/6`
  (som Twentys grå ruta), etikett 14 px `--ink2`, kortkommando som `Kbd` till höger.
  Markerad rad `ink/7`. Bolagsträffar som postchips.
- Beteende som Twenty: filtrera medan man skriver (accentokänsligt), pilar, Enter,
  Escape tömmer först och stänger sedan.

**7. Tavlan.** Finns inte i kontraktet för version 2. Om den byggs: kolumn 272 px (Twenty
200 × 1,35), kolumnhuvud 44 px med etikett helt rundad 24 px och summan i `--ink-muted`;
kort i `--paper` med kant `ink/8`, radie **10**, utfyllnad 12 px, 8 px mellan korten,
`--shadow-med` bara medan kortet dras; kortets namn 14 px vikt 600, fältrader 28 px utan
etiketter med ikon 16 px `--ink-subtle`, och "+ Ny" i `--ink-muted` under sista kortet.

**8. De tjugo detaljerna i Snajp.** Allt i listan ovan gäller med dessa byten: 14 px i
stället för 13; vikt 600 i stället för 500 där kontraktet säger halvfet, annars 500;
Snajps tre dämpade texttoner i stället för Twentys gråskala; hover-platta med radie 6 i
inre element och 10 i menyrader; 36 / 44 / 40 / 64 px i stället för 28 / 32 / 40 / 48;
en fylld knapp per sida i bläck; färg bara i objektplattor, etiketter, avatarer och
diagram; ockra för fokus, val och det framhävda kortet. Det som **inte** byts: att text är
nästan en enda storlek, att etiketter är svagare än värden, att chips är innehållsbreda,
att linjerna är så svaga att de bara ordnar, att tomma värden säger vad som saknas och
att sekundärt innehåll öppnas åt höger utan att dölja listan.
