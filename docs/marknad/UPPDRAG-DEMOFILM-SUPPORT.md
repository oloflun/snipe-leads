# Uppdrag: förläng demofilmen med en supportdel

Till agenten (Fable eller Opus) som Sebastian kör. Skrivet 2026-11-26 av sessionen som gjorde
leadsfilmen. Läs det här dokumentet helt, och sedan [`DEMOFILM-LEADS-2026-11-25.md`](DEMOFILM-LEADS-2026-11-25.md),
innan du rör någon fil. Det andra dokumentet beskriver exakt hur leadsdelen gjordes och varje dom Anton
gav på vägen; samma domar gäller supportdelen. Projektet ligger i [`marknad/demofilm/`](../../marknad/demofilm/),
läs dess README.

Det andra dokumentet nämner sökvägar på Antons dator (`D:\snajp-demo\…`, `memory/…`). De finns inte hos
Sebastian och behövs inte: allt som krävs ligger i `marknad/demofilm/`, och reglerna står i det här
dokumentet.

## Beställningen, i Antons ord

> "Jag vill att du skriver ett dokument med UTFÖRLIGA instruktioner där du inte utelämnar något, om exakt
> varje steg för hur vi gick tillväga och mina exakta instruktioner och feedback för att uppnå det
> slutgiltiga resultatet. Utifrån detta, vill jag att du skapar exakta instruktioner för hur nästa agent,
> Fable eller Opus, med enbart Opusagenter, ska förlänga videon med en likadan supportdel som inleds med
> den korta  marknadsföringsteelen som anpassas och breddas på samma sätt:
> https://www.instagram.com/reel/Dfuy2RSyBdw/?cnvx=dnkwd2VwNTkwemVw    , följt av de olika stegen och
> funktionerna med supportagenten med samma fokus på värde för kunden, med de avslutande delarna om
> datasäkerhet och provperiod sist."

> "Sebastian som ska göra arbetet har originalreelen, så det borde förenkla allt"

## Målet

| # | Del | Källa |
|---|---|---|
| 1 | Instagramreelen om Iris, hel | Finns: `public/reel.mp4` (renderas ur `marknad/video`, se README) |
| 2 | "Så här jobbar Iris åt er" och leadsdemons tio steg | Finns: `public/film/01.png`–`10.png` och de första tolv posterna i `src/data/film.json` |
| 3 | Instagramreelen om kundtjänst, anpassad och breddad på samma sätt som Iris-reelen | Ny: Sebastians originalfil |
| 4 | "Så här jobbar supportagenten åt er" och supportagentens steg, med samma fokus på värde för kunden | Ny |
| 5 | Datasäkerhet | Flyttas från efter leadsdelen till här |
| 6 | Vad ni får, nu för båda agenterna | Flyttas och skrivs om |
| 7 | Kostnadsfri pilot i två månader / snajp.se | Flyttas till här |

Datasäkerhet, Vad ni får och piloten står **en gång, sist**. De tas bort efter leadsdelen.

## Regler för hur du arbetar

1. **Bara Opus-agenter** (Antons krav). Delegerar du, använd `Agent` med `model: "opus"`, aldrig Sonnet
   eller Haiku, och kontrollera efteråt vilken modell som gjorde jobbet. Det gäller också agenter som
   startas av dina agenter.
2. **All visuell bedömning gör du själv.** En agent kan ta bilden; bedömningen av hur den ser ut är din.
   Titta på varje bildruta du lämnar ifrån dig.
3. **Ingen kunddata i bild.** Development är en spegel av produktionen. Filma bara `/demo/...` och
   `/forhandsvisning/...` på `https://web-development-6c85.up.railway.app`. Aldrig en inloggad yta.
4. **Leadsdelen är godkänd och ska inte spelas in igen.** Kör inte `rec/record-leads.mjs`: den skriver
   över `public/film/` och hela manuset, och demon kan ha ändrats sedan bilderna togs. Supportdelen spelas
   in med ett eget skript (steg 4).
5. **En tung process i taget.** Remotion och Chrome tar mycket minne. Kör aldrig två renderingar samtidigt.
   Ligger systemdisken nära full, sätt `DEMOFILM_TEMP` till en mapp på en disk med plats.
6. **Inga commits och ingen push** utan Sebastians ja. Följ projektets regler i `CLAUDE.md`: allt arbete
   till `development`, aldrig `main`.
7. **Skicka aldrig en inaktuell fil** när någon ber om filmen. Säg att den nya renderas och skicka den när
   den är klar och kontrollerad.
8. **Innehållet är Antons beslut.** Sebastian kör arbetet, men domarna nedan är Antons. Det som är
   agentens förslag ska visas för Anton (via Sebastian) innan det betraktas som klart.

## Antons domar som gäller supportdelen

Alla i hans egna ord, ur arbetet med leadsdelen 2026-11-25:

- **Innehållet:** "Visa vad den GÖR, hur ENKELT det är och vad de får för värde av varje funktion." och
  "korta ner de delar som inte är lika centrala, som att förklara exakt var man klickar eller vad varje
  siffra visar."
- **Bildtexten:** "lite större och flytande utan bakgrund, som dyker upp och byts ut mjukt". Motorn gör det
  redan. Två bildtexter får aldrig synas samtidigt.
- **Reelen:** "se till att den inte klipps på samma sätt" (Instagram beskar bilden så att loggan klipptes).
  Hela reelens bild ska synas.
- **Musiken:** version 2-bädden (`public/musik/badd-110bpm.mp3`, 110 BPM). Det lugna spåret dömdes ut som
  "hissmusik" och ska inte användas. Ta inte fram ny musik.
- **Exemplen ska stämma med bildtexten.** I leadsdelen visades ett första mejl där bildtexten talade om
  uppföljning: "mailet läser som ett första mail, inte som uppföljning, du måste byta ut det".
- **Upprepa inte samma sak två gånger:** "Du behöver inte ha två sekvenser om hur man skickar och att man
  kan skicka flera på samma gång".
- **Datasäkerheten:** raden "All drift, lagring av kunddata och behandling i språkmodeller sker inom EU"
  är godkänd. "Både databasen och språkmodellerna" dömdes som "vardagligt och slappt". Nämn inte Amsterdam.
- **Erbjudandet:** "kostnadsfri pilot i 2 månader, inget om någon ytterligare rabatt".

Övriga regler: synlig text säger "supportagent", aldrig "supportbot". Inga tal ur demon som bildtext
och inga påståenden om svarsfrekvens eller andel automatiska svar (marknadsföringslagen; demons tal är
exempeldata). Inga tankstreck och inga utropstecken i bildtexterna. Webbplatsbedömningen visas aldrig.

## Steg 1. Gör i ordning projektet

```bash
git fetch origin
git merge --ff-only origin/development
cd marknad/demofilm
npm install
npx playwright install chromium
```

Rendera Iris-reelen (README, avsnittet Kom igång) till `public/reel.mp4`. Kontrollera sedan att
leadsdelen går att bygga oförändrad:

```bash
node verktyg/tider.mjs
```

Det ska skriva `totalt 2831 rutor, 94.37 s`. Kör `bash bygg.sh` en gång och jämför `out/snajp-demo.mp4`
med leadsfilmen Anton har fått (samma längd, samma bilder). Då vet du att verktygen fungerar på maskinen
innan du ändrar något.

## Steg 2. Lägg in supportreelen, anpassad och breddad på samma sätt

Sebastian har originalreelen. Fråga honom efter, i den här ordningen:
1. **Källprojektet**, om reelen är gjord i Remotion eller Hyperframes. Finns en 4:5-komposition, rendera
   den (som Iris-reelen, `--crf=14 --jpeg-quality=100`) till `public/reel-support.mp4`. 4:5 fyller 864 px av
   filmens bredd; 9:16 bara 608 px.
2. **Originalfilen** (mp4), helst 4:5, annars 9:16. Lägg den som `public/reel-support.mp4`.

Ladda aldrig ned den från Instagram: det är en omkodad kopia, och Instagrams utsnitt är just det Anton inte
ville ha.

"På samma sätt" betyder som Iris-reelen:
- Hela reelens bild syns. Ingen beskärning.
- Den spelas i filmens fulla höjd, 1080 px, mitt i bild, med sitt eget ljud.
- Sidorna fylls genom att reelens yttersta sex pixelkolumner sträcks ut till kanten (`ClipScene` i
  `src/Film.tsx`), så att sidorna följer reelens egen bakgrund. Granska om de utsträckta kolumnerna ser
  rena ut. Ser de randiga ut (troligast med 9:16, där sidorna blir 656 px breda), fyll sidorna med
  reelens bakgrundsfärg i stället och visa Anton båda.

Mät antalet rutor: `ffprobe -v error -count_frames -show_entries stream=nb_read_frames,width,height public/reel-support.mp4`.
Reelen ska ha 30 fps; har den en annan takt, koda om den till 30 fps först.

## Steg 3. Ta reda på vad supportagenten gör i demon

Kör `node rec/utforska-support.mjs` (skärmbilder och sidtext till `explore/support/`), eller delegera till en
Opus-agent som bara läser. En första genomgång 2026-11-26 visade (kontrollera att det stämmer):

| Yta | Adress | Vad som finns |
|---|---|---|
| Kundtjänst › Ärenden | `/demo/support`, fliken Ärenden | Inkorgen sorterad i fack (Teknisk support, Leverans & frakt, Reklamation & retur, Betalning & faktura, Övrigt), status per ärende: Väntar på godkännande, Eskalerat, Autosvar skickat. Exempel: "Var är mitt paket?" (Johan Berg), "Dubbeldragning på kortet" (Sara Nyström, eskalerat), "Trasig vara, kräver återbetalning" (Erik Holm, med bild), "Radera mina uppgifter" (Maria Ek, eskalerat), "Rabattkoden funkar inte?" (Lars Strand, autosvar skickat) |
| Kundtjänst › Kundchatten | `/demo/support`, fliken Kundchatten | "Klicka på en fråga, som kund:" med fem frågor, bland andra "Var är min beställning?" och "Jag vill häva köpet och kräva skadestånd" |
| Kundtjänst › Översikt | `/demo/support` | Nyckeltal och diagram, exempeldata. Talen får inte bli bildtext |
| När agenten får svara själv | `/demo/regler` | Per kategori: Utkast (du godkänner innan det skickas), Auto (agenten väljer själv), Eskalera (går alltid till en människa) |
| Kunskapsbasen | `/forhandsvisning/kunskapsbas` | Artiklar och förslag ur skanningen av sajten, påhittade värden |
| Att göra | `/demo/att-gora` | Eskalerat till dig och Svar att godkänna, samlat för båda agenterna |

Ta reda på innan manuset skrivs: vad som syns när ett ärende öppnas (svarsutkastet, vilken källa i
kunskapsbasen svaret bygger på, knapparna), vad som händer vid Godkänn i demon, vad chatten svarar på
"Var är min beställning?" och på frågan om att häva köpet, och om ett eskalerat ärende visar varför det
gick till en människa.

**Inte med:** Hjälprutan (`/forhandsvisning/hjalpruta`) är Snajps egen support till kunderna, inte produkten
som säljs. Kvitton är vilande och ska inte synas.

## Steg 4. Skriv manuset och spela in

Högst tio steg, två takter vardera. Varje bildtext är en kort mening om vad kunden får eller hur lite den
behöver göra. Ett förslag att utgå från (agentens förslag, inte Antons; kontrollera varje påstående mot
produkten och justera efter steg 3):

| # | Bildtext | Var |
|---|---|---|
| 1 | Supportagenten svarar ur ert eget material | Kunskapsbasen, en artikel |
| 2 | Varje kundmejl hamnar i rätt fack av sig självt | Ärenden, listan med fack |
| 3 | Svaret är skrivet innan ni har öppnat mejlet | Ärendet "Var är mitt paket?" öppnat, utkastet synligt |
| 4 | Ett klick, så går svaret till kunden | Markören klickar Godkänn |
| 5 | Pengar, juridik och arga kunder går alltid till en människa | Ärendet "Dubbeldragning på kortet", Eskalerat |
| 6 | Ni bestämmer vad agenten får svara på själv | `/demo/regler` |
| 7 | Samma agent svarar i chatten på er sajt | Kundchatten, markören klickar "Var är min beställning?", svaret i bild |
| 8 | Allt som väntar på er samlas på ett ställe | Att göra (valfritt; stryk om filmen blir lång) |

Steg 5 bygger på produktens egen text: "Återbetalningar, fakturafel, juridik, GDPR och arga kunder går
alltid till en människa, med hela historiken bifogad." (`lib/landningssidor.ts`). Skriv inte "dygnet runt"
eller liknande utan belägg i produktens marknadstexter (`components/marketing/copy.ts`,
`lib/landningssidor.ts`).

Rubriken före stegen: "Så här jobbar supportagenten åt er" (1,5 takt).

**Vad ni får** blir gemensamt för båda agenterna. Förslag (agentens, högst sex rader, visa Anton):
- Bolag som passar er målgrupp, med skäl och källor
- Ett första mejl och uppföljning fram till svar eller bokat möte
- Kundmejl sorterade och besvarade ur ert eget material
- Det känsliga går alltid till en människa
- Ni bestämmer vad som går ut utan ert ja

**Datasäkerhet**, ordagrant som Anton godkände den; ändra inte utan hans ja:
- All drift, lagring av kunddata och behandling i språkmodeller sker inom EU
- Varje kunds data är avskild på databasnivå
- Alla underleverantörer står med namn i integritetspolicyn

**Slutkortet:** "Kostnadsfri pilot i två månader", undertext "snajp.se", `invert: true` (mörk bakgrund).

Visa bildtexterna för Sebastian (och Anton) innan du spelar in, men vänta inte på svar; en färdig bild är
lättare att rätta.

### Inspelningsskriptet

Skapa `rec/record-support.mjs`. Utgå från `rec/record-leads.mjs` (samma `still()`, `aim()`, `lagg()` och
`shot()`), men:
1. Skriv bilderna till `public/film/support/NN.png` och sätt `file` i manuset till `support/NN.png`.
   Rör inte `public/film/01.png`–`10.png`.
2. Läs det befintliga `src/data/film.json`. Behåll posterna till och med leadsdelens sista steg ("Hela
   vägen till svar eller bokat möte", fil `10.png`). Ta bort de tre korten efter (Datasäkerhet, Vad ni
   får, piloten).
3. Lägg till: `{ "kind": "clip", "file": "reel-support.mp4", "frames": <antal>, "w": <bredd>, "h": <höjd> }`,
   rubriken, supportstegen, och sist Datasäkerhet (3 takter), Vad ni får (3,5 takter) och piloten (3 takter).
4. Spara en kopia av det gamla manuset som `src/data/film-leads.json` innan du skriver över det.

Använd samma hjälpfunktioner som leadsskriptet: `shot()` med `bars: 2`; `y` för att placera målet i
fönstret; `vila: false` bara där innehållet byts hela tiden; `center: true` och `zoom: 1.12` på
förhandsvisningar utan sidomeny; `anchor: "right"` för en låda som öppnas från höger; `focus` för en fast
inramning. Klicka utan att ta bild där klicket inte är poängen.

Kontrollera för varje steg att det som står i bildtexten faktiskt syns i bilden. Fel från leadsdelen som
inte får upprepas:
- ett exempel som läses som fel sorts sak (ett första mejl under en text om uppföljning);
- en knapp som klickas men inte ändrar något i bild (förhandsvisningar svarar ofta inte på klick);
- en bildtext som påstår något demon inte visar (demons Kör Iris säger "färdiga utkast" men raderna visar
  "Saknas");
- markören som täcker knappens text (`aim()` lägger den bredvid).

## Steg 5. Tidslinje och ljud

Inget i motorn eller ljudet behöver skrivas om:
- `layout()` i `src/Film.tsx` och `verktyg/tider.mjs` startar om takträkningen vid varje klipp, så att
  avsnittet efter supportreelen börjar på musikens första slag.
- `verktyg/ljud.mjs` lägger varje klipps eget ljud där klippet ligger och bädden i varje avsnitt mellan
  klippen (flera kopior med övertoning på taktgräns om avsnittet är längre än 61 s), tonar ut bädden en
  sekund före nästa klipp och 3,3 s i slutet. Det är provat mot leadsfilmen: ljudet blev identiskt.

Kör `node verktyg/tider.mjs` efter inspelningen och kontrollera att supportreelen och musikavsnitten
ligger där du väntar dig. Mät ljudnivån per avsnitt på den färdiga filen
(`ffmpeg -ss <från> -to <till> -i out/snajp-demo.mp4 -af ebur128 -f null -`). Leadsfilmen ligger på −18 till
−19 LUFS. Sticker supportreelen ut, justera dess nivå i `ljud.mjs` (ett `volume=` i klippets kedja).

## Steg 6. Granska med egna ögon

Före fullrenderingen:
1. `npx tsc --noEmit -p tsconfig.json`.
2. En stillbild per scen: `node verktyg/stills.mjs explore/stills <rutor…>`, med rutan
   `start + min(längd − 45, 95)` ur `verktyg/tider.mjs`. Faller den med "Timed out … connect to the
   browser", kör igen; det är maskinens belastning.
3. Kontaktark: numrera om till `s01.jpeg …` och kör
   `ffmpeg -framerate 1 -i s%02d.jpeg -vf "scale=960:540,tile=2x3:padding=8:color=white" ark-%d.png`.
   Läs varje ark.
4. Kontrollera: att supportreelen syns hel och att sidorna ser rena ut; att bildtexten aldrig täcker det
   den handlar om; att markören landar bredvid knappens text; att inga tal visas som om de vore resultat;
   att varje exempel säger samma sak som bildtexten.
5. Textbytena: rendera åtta rutor över ett byte och kontrollera att två texter aldrig syns samtidigt.
6. Övergångarna in i och ut ur supportreelen.

## Steg 7. Rendera och leverera

1. `bash bygg.sh` (i bakgrunden; 15–25 minuter för en film på 2,5–3 minuter). Det kontrollerar att
   klippen finns och att `tider.mjs` och `Film.tsx` räknar lika, renderar i delar med upp till fyra försök
   per del, bygger ljudet, och skriver `out/snajp-demo.mp4`, `out/snajp-demo-mobil.mp4` (under 30 MB) och
   `out/kontaktark.png`.
2. Kontrollera: antalet rutor (skrivs ut) ska vara lika med `node verktyg/tider.mjs --totalt`; läs
   kontaktarket; mät ljudnivån per avsnitt.
3. Ge Sebastian mobilversionen att skicka till Anton, och fullversionen.
4. Skriv i svaret vad som inte är kontrollerat, till exempel att ingen har lyssnat på ljudet.
5. Skriv ett dokument för supportdelen på samma sätt som `DEMOFILM-LEADS-2026-11-25.md`: varje dom från
   Anton ordagrant, varje version, varje fel och hur det löstes.
6. Commit efter Sebastians ja: `marknad/demofilm/` (utan `out/`, `tmp/`, `explore/`, reelerna) och
   dokumenten.

## Frågor, bara om det behövs

- Till Sebastian: originalreelen eller källprojektet (steg 2).
- Till Anton, via Sebastian: om Vad ni får ska vara gemensamt eller ett per agent; om Datasäkerhet behöver
  en rad till för kundtjänsten (kundmejl innehåller personuppgifter om kundens kunder); ändra inte texten
  utan hans ja.
