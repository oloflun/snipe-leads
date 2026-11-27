# Snajp CRM: designriktning (version 2, 2026-11-26)

Den här filen är kontraktet för CRM-appens gränssnitt. Den ersätter utseendet i
commit `b6c08ef2`, som Anton dömde ut 2026-11-26.

## GODKÄND OCH LÅST (Anton 2026-11-26)

> Perfekt, utseendet och gränssnittet var precis det jag föreställde mig. Lås in precis
> alla delar av det som framtida referens att bygga utifrån.

Version 2 i commit `d438ff84` är referensen. Allt nytt i CRM:et, och allt som flyttas
dit från den nuvarande appen, byggs i den här formen. Det som är låst:

| Del | Var referensen ligger |
|---|---|
| Hur det ser ut | Bilderna i `docs/crm/bilder/app/` (översikt, bolag, panel, personer, synk, utvecklare, palett, mörkt läge, mobil) |
| Riktning och anatomi | Den här filen, avsnitten nedan |
| Tema och tokens | `lib/crm/astryx/snajpTema.ts` (källa) och de byggda `snajp.css`, `snajp.js` |
| Skal | `components/crm/app/CrmRam.tsx` och `crm.css` |
| Verktygslåda | `components/crm/app/kit.tsx`: Postchip, Personchip, Lankpiller, Relationsetikett, Objektikon, Kolumnrubrik, Tabellskelett, Nyckeltalskort. Ny yta importerar härifrån och uppfinner inga egna varianter |
| Sidans ram | `components/crm/app/Sida.tsx`: Sidhuvud, Vyrad, Sida |
| Mönstervyer | Lista med markering och åtgärdsrad: `BolagVy.tsx`. Postens panel: `BolagPanel.tsx`. Formulär med fältfel: `BolagFormular.tsx`. Kort och diagram: `OversiktVy.tsx`. Förlopp och utfall: `SynkVy.tsx` |
| Recept för Astryx | `docs/crm/underlag/astryx-kokbok.md` |
| Mått att hålla | `docs/crm/underlag/twenty-finish.md` |

En ändring av något låst kräver Antons ord. En ny vy som inte går att bygga med
verktygslådan utökar verktygslådan, i samma form.

### Ändringar Anton beställde i samma besked (2026-11-26)

1. **Sidofältet är marinblått (Snajps bläck) i båda lägena.** Det ska inte bli ljust i
   mörkt läge, som railen i version 1 blev. Färgen är fast: `--ink` byter värde i mörkt
   läge och kan därför inte bära den. Sidofältet får egna, fasta tokens.
2. **Snajps logga står i sidofältet.**
3. **Ockra som accent där det passar**, så att varumärket känns igen: det valda i
   sidofältet, loggan, fokus, förlopp och den framhävda rutan.

Det ersätter punkten "Railen i bläck tas bort" under Tema nedan. Resten står kvar:
upphöjt blad, radier, chips, kort, piller, kommandopalett.

**Så är det byggt (2026-11-26, väntar på Antons dom).** Tokens `--rail`, `--rail-2`,
`--rail-text`, `--rail-muted`, `--rail-subtle` och `--rail-ochre` i `app/globals.css` är
fasta i båda lägena. Hela tvätten bakom bladet är marinblå, så att det ljusa bladet med
sitt rundade hörn ligger på samma bläck som navigeringen. Utförandet med bara en marinblå
kolumn prövades och föll: en beige ram på 8 px runt bladet klippte av sidofältet. Loggan
(`Logo tone="paper"`) står överst och leder till översikten, med arbetsyteväxlaren under.
Vald menypost är en platta på 10 procent med en smal ockramarkör mot kanten och ikonen i
ockra. Mobilens toppfält och låda är marinblå. Uppmätt i båda lägena: all text i
sidofältet minst 5,84:1, ikoner och markörer minst 4,07:1. Bilder: `docs/crm/bilder/app/`.

## Antons dom och beställning (2026-11-26, ordagrant i sak)

> De senaste skärmbilderna ser väldigt generiska ut, lika och nästan sämre än den
> nuvarande dashboarden, inte i närheten av den polerade UI:n hos riktiga Twenty, och
> inga tydliga element hämtade från Astryx. Det ser ut som det nuvarande utseendet i
> dashboarden, fast i ett generiskt 00-tals-CRM. Jag förväntar mig en blandning av
> det polerade, Apple-inspirerade utseendet hos Twenty, blandat med mer moderna,
> lekfulla influenser och element från Astryx för lite större och rundade element
> samt mer lekfulla dashboards, kombinerat med enbart färgpaletten och
> serif-rubrikerna från Snajp, och satt ihop med designreglerna från vårt designsystem.

Vad som var fel i version 1, uppmätt mot bilderna: en mörk rail och en naken tabell
med text i celler. Inga postchips, inga avatarer, ingen vyrad, ingen översikt, inga
kort, inga diagram, raka små kontroller. Av Astryx syntes bara tabellens ram.

## Riktningen i en mening

Twentys lugna registerprecision på Snajps varma papper, i Astryx mjuka, rundade
ytor: ljus navigering, innehållet som ett upphöjt blad, poster som chips med
avatarer, och en översikt med stora nyckeltal och diagram i ockra, mossa och blått.

Läge: Operate (verktyg som används hundra gånger om dagen). Tier 0: tokens är låsta
i `app/globals.css`. Ingen scrollkoreografi, inga uppräkningsanimationer.

## Referenslås

| Källa | Roll | Vad som tas | Vad som INTE tas |
|---|---|---|---|
| **Twenty** (dominant) | Struktur och finish | Ljus navigering med arbetsyteväxlare och färgade objektikoner. Sidhuvud med objektikon. Vyrad (vy till vänster, Filter, Sortera, Alternativ till höger). Tabell där varje post är ett chip (ikon eller avatar plus namn), länkar är piller, kolumnrubriker har en liten ikon per fälttyp, sista raden är "Lägg till" och foten räknar. Sidopanel till höger med flikar och fält i grupper (ikon, etikett, värde). Dashboard som rutnät av rundade kort. | Twentys kod (AGPL), dess blå accent, Inter 13 px, dess ikonuppsättning och texter. |
| **Astryx** (sekundär) | Form och lekfullhet | `AppShell variant="elevated"`: tvättad bakgrund och innehållet som en upphöjd yta med stort rundat hörn. Pillerformade val (`SegmentedControl`, valda menyposter som mjuka plattor). Större kontroller (36 px). `Avatar`, `Token`, `Badge` som piller, `Card` i färgade varianter, `CommandPalette`, `MetadataList`, `HoverCard`, `StatusDot`, `Kbd`, `TableSelectionToolbar`. | Neutral-temats gråskala och typsnitt. Förhandsutgåvorna (charts, lab). |
| **Snajp** | Färg, rubriker, regler | Hela paletten (`--ink`, `--paper`, `--paper2`, `--ochre`, `--moss`, `--danger`, `--mineral`, `--seal`, `--chart-blue`, `--chart-ramp-1..6`, de dämpade texttokens). Fraunces i rubriker. DESIGN.md:s regler: inga färger utanför tokens, inga kickers, inga versaler som etikett, inga em-streck, ingen kursiv rubrik, tvåspråkigt, 4,5:1, fält 16 px på pekskärm, 44 px tryckytor. | Den mörka railen, den täta 15 px-liggaren och hårlinjeasketismen från dagens arbetsyta. CRM:et är en egen app och får en egen form. |

Aldrig den säkra snittmängden: där källorna drar isär vinner Twenty på struktur,
Astryx på form, Snajp på färg och rubrik.

## Tema (ändringar i `lib/crm/astryx/snajpTema.ts`)

- **Ytor:** tvätten (`--color-background-body`) är `--paper2`, innehållsbladet
  (`--color-background-surface`, `-card`, `-popover`) är `--paper`. Bladet lyfts med
  en hårlinje och en mjuk skugga, inte med en mörk rail.
- **Railen i bläck tas bort.** Ingen `MediaTheme` runt navigeringen. Vald menypost är
  en mjuk platta (`ink/7`) med text i `--ink` och halvfet vikt.
- **Radier (större, Astryx):** inre 6 px, element 10 px, behållare 16 px, sida 24 px.
  Etiketter, tokens och segmentval är helt rundade.
- **Kontroller:** 32 / 36 / 44 px (sm / md / lg) på skrivbord, 36 / 44 / 48 på pekskärm.
- **Text:** 14 px bas på skrivbord (16 på pekskärm under 1024 px), Geist. Fraunces i
  sidrubrik (1,625 rem, normal vikt), i postens namn i panelen (1,375 rem) och i
  nyckeltalens siffror. Paneltitlar i Geist halvfet.
- **Skuggor:** `--shadow-low` är en hårlinje. `--shadow-med` och `-high` är hårlinje
  plus en mjuk, bred skugga i `--seal` med låg alfa (6 till 10 procent), för blad,
  kort som svävar, menyer och dialoger.
- **Accent:** ockra bär fokus, förlopp, det valda i diagram och en enda framhävd ruta
  per sida. Primärknappen är bläck. Ockra som text är alltid `--warning`.
- **Objektfärger** (ikonplattor och diagramserier), bara ur paletten:
  Översikt ockra, Bolag `--chart-blue`, Personer `--moss`, Synk `--seal`,
  Utvecklare `--mineral`. Plattan är färgen med 14 procents alfa, ikonen färgens
  textsäkra ton.
- Mörkt läge och kundpalett ska fortsätta följa med: bara `oklch(var(--token))`.

## Skalet

`AppShell variant="elevated"`, sidnavigering 248 px, hopfällbar.

1. **Överst:** arbetsyteväxlare (rundad fyrkantig avatar i bläck med arbetsytans
   initial, namnet halvfet, vinkel) som öppnar en meny: Till arbetsytan,
   Inställningar. Till höger en ikonknapp som öppnar kommandopaletten.
2. **Sök-rad:** "Sök eller hoppa till" med `Kbd` Ctrl K. Öppnar kommandopaletten.
3. **Arbetsyta:** Översikt, Bolag, Personer. Bara det som finns: inga döda poster.
4. **Data:** Synk, Utvecklare.
5. **Nederst:** ett litet rundat kort med senaste synkens läge (statusprick, anslutning,
   relativ tid, förloppsstapel om en körning pågår). Riktiga data ur `/oversikt`.
   Därunder länken Till arbetsytan.

Kommandopaletten (`CommandPalette`, Ctrl K och Cmd K): Gå till (de fem vyerna), Skapa
(Nytt bolag, Ny anslutning, Ny nyckel), och Bolag (sökning mot `/v1/companies?q=`
medan man skriver, träffar som postchips).

## Sidhuvud och vyrad (alla listvyer)

- Sidhuvud, 64 px: objektets ikonplatta (32 px, radie 10), Fraunces-rubrik, antalet
  som en neutral etikett. Till höger: sidans primära handling (bläck, 36 px) och en
  ikonknapp för fler val där det finns riktiga val.
- Vyrad, 52 px, under en hårlinje: till vänster `SegmentedControl` med vyerna och
  antal i dämpad ton. Till höger sökfält (36 px, 260 px brett, helt rundat) och
  Sortera som ett kompakt val. Bara val som fungerar mot API:t.

## Tabellen (Bolag, Personer, Synk, Utvecklare)

Astryx `Table`, `density="balanced"` (rad cirka 44 px), radavdelare, hover.

- **Kolumnrubrik:** liten dämpad ikon per fälttyp plus rubrik i 13 px halvfet dämpad.
- **Postchip** (första kolumnen): avatar 22 px (fyrkantig med radie 6 för bolag, rund
  för personer; initialer på en platta vars färg väljs ur objektfärgerna med namnets
  hash) plus namn i 14 px halvfet. Hela chipet är en knapp med hover-platta och öppnar
  postens panel. Fokusring i ockra.
- **Länkpiller:** domän, e-post och telefon som piller (`Token`) som går att klicka.
- **Relation:** etikett med statusprick: kund mossa, prospekt ockra, tidigare kund
  mineral, partner och leverantör blå, övrigt grå.
- **Person:** rund avatar 20 px plus namn. **Källa:** piller med kontaktikon.
- **Tal och tider:** tabulära siffror, relativ tid dämpad, fullständig tid i tooltip.
- **Markering:** kryssruta per rad och i huvudet. När något är markerat visas
  `TableSelectionToolbar` med riktiga åtgärder (Bolag: Ändra relation, Ta bort till
  papperskorgen; båda finns i API:t).
- **Fot:** en räknerad som Twentys: antal, och för Bolag andelen kunder.
- **Sista raden:** "Lägg till bolag" med plus, öppnar samma dialog som knappen.
- **Tomläge:** `EmptyState` med ikon, en mening och den primära handlingen.
- **Laddning:** `Skeleton`-rader i tabellens form, inte en naken förloppsstapel.
- **Mobil (under 640 px):** ingen tabell som rullar i sidled. Posterna visas som en
  lista av rader med chip, relation och en dämpad andra rad (ort, ansvarig).

## Postens panel (Bolag)

`Drawer` från höger, 520 px, byggd med `Layout` (huvud, innehåll, fot).

- **Huvud:** avatar 44 px, namnet i Fraunces 1,375 rem, organisationsnummer dämpat,
  relationens etikett. Ikonknappar: Redigera, Stäng.
- **Snabbval:** en rad runda ikonknappar med tooltip för det som finns: Mejla, Ring,
  Öppna webbplatsen. Saknas uppgiften är knappen avstängd med förklaring.
- **Flikar:** Översikt, Personer (antal), Källa.
- **Översikt:** fält i grupper som `MetadataList`: Allmänt, Affär, Kontakt, System.
  Varje rad: liten ikon, etikett dämpad till vänster, värde till höger. Tomt värde
  visas som dämpad text "Lägg till" som öppnar redigeringen på det fältet.
- **Personer:** rader med rund avatar, namn, titel och piller för e-post och telefon.
- **Källa:** anslutning som piller, externt id i kodstil, senast sedd.
- **Redigera:** dialog med fälten (namn, organisationsnummer, relation, webbplats,
  e-post, telefon, ansvarig, adress, kund sedan, avtalsslut, kontakta inte) som
  sparar med `PATCH /v1/companies/{id}`. Fel från API:t visas vid rätt fält.

### Historik (tillagt 2026-11-26, inte sett av Anton än)

Fliken Historik är postens hela tidslinje, i bolagets, personens och affärens panel
(`Tidslinje.tsx`). En komponent, ingen flik till för anteckningar eller uppgifter.

- **Skrivytan** överst: små sekundära knappar (Anteckning, Uppgift, Aktivitet, och Utfall
  för ett bolag som är ett lead hos Iris). Ett tryck öppnar formuläret på samma plats, i en tvättad ruta med 16 px radie
  (`.crm-skrivyta`), med Avbryt och Spara nere till höger.
- **Att göra:** öppna uppgifter som rader med kryssruta, titel och förfallodag till
  höger (passerad dag i varningsfärg, och utsagt för skärmläsare). En öppen uppgift står
  bara här, och i flödet först när den är klar.
- **Flödet:** `ol.crm-tidslinje`, en rad per händelse: ikonplatta 24 px i radens ton,
  meningen i 0,875 rem, utdrag i dämpad brödtext (högst fyra rader), och sist en dämpad
  rad med detalj, källa och tid. Källan skrivs bara när den är känd.

## Affärstavlan (tillagt 2026-11-26, inte sett av Anton än)

Vyn Affärer (`AffarerVy.tsx`) är en tavla inuti bladet, med samma sidhuvud och vyrad som
listorna. Antalet i sidhuvudet är öppna affärer. Vyraden bär Tavla och Papperskorg, och
öppet och viktat värde i räknefotens stil.

- **Kolumnen** (`.crm-tavla-kolumn`): 288 px, 16 px radie, tvättad yta. Huvud: prick i
  stegets ton (öppet blått, vunnet mossa, förlorat mineral), namnet i Geist halvfet,
  antal som neutral etikett och summan dämpad till höger.
- **Kortet** (`.crm-tavla-kort`): blad med hårlinje och 12 px radie. Namnet i Geist
  halvfet, den ansvarigas avatar uppe till höger, bolaget som lugnt postchip, och en rad
  med beloppet till vänster och väntat avslut till höger.
- **Dra och släpp:** kolumnen under pekaren tonas ockra, och en 3 px ockralinje visar
  platsen. På telefon står stegen under varandra utan dragning.
- **Affärens panel** har bolagets form: steget som väljare överst i gruppen Affär.
- **Stegen på tavlan** (`Stegdialog.tsx`, tillagt 2026-11-27): knappen Anpassa stegen i
  sidhuvudet öppnar en dialog med en rad per steg (`.crm-stegrad`): flyttknappar upp och
  ned, namnet, sannolikheten med procenttecken i fältets högerkant, typen med stegets
  prick, och papperskorgen. Hårlinje mellan raderna. Felet står vid radens namn, och
  regeln som gäller hela tavlan i en ruta överst. På telefon står namnet för sig överst.

## Uppgifter (tillagt 2026-11-27, inte sett av Anton än)

Vyn Uppgifter (`UppgifterVy.tsx`) är en listvy som de andra: sidhuvud med Ny uppgift,
vyraden Att göra, Försenade och Klara, och sökfältet till höger.

- **Raden:** kryssruta, titeln i Geist halvfet med beskrivningen dämpad under, posterna
  uppgiften hör till som lugna chip (bolag eller person, och affären med sin ikonplatta),
  förfallodagen och den ansvariga. En passerad dag står i varningsfärg med egen ikon,
  dagens dag halvfet som "I dag".
- **Klar** stryker titeln och byter kolumnen Förfaller mot när den blev klar.
- **Telefon:** en rad per uppgift med kryssrutan till vänster, och dag och poster under
  titeln. Chippen bryter rad i stället för att kapas.

## Spärrar (tillagt 2026-11-27, inte sett av Anton än)

Vyn Spärrar (`SparrarVy.tsx`) ligger under Data. Sidhuvud: Kontrollera (spöke), Ladda upp
lista (sekundär) och Ny spärr (primär). Vyraden: Alla, Mejl, Telefon och Hävda.

- **Raden:** slagets ikon (kuvert, glob, lur, nummertecken) och värdet i Geist halvfet,
  kanalen som etikett (Alla kanaler i varningsfärg, en kanal neutral), orsaken med
  anteckningen dämpad under, källan, när, och knappen Häv.
- **Hävda** stryker värdet och byter kolumnen Tillagd mot Hävd. Ingen knapp.
- **Räknefoten** säger vad listan inte visar (poster märkta Kontakta inte,
  avregistreringar, leads), och bär länken till den senaste uppladdningens utfall.
- **Uppladdningen** visar förlopp i rutan och slutar i ett utfall: en ruta med antalen,
  och raderna som inte gick att läsa med radnummer, värdet i kodstil och skälet.
- **Kontrollen** svarar i en ruta under fältet: grön när inget spärrar, varningsfärg med
  källan när något gör det.

## Översikten (`/crm`, ny startsida)

Twentys dashboardrutnät i Astryx kort (`Grid` plus `Card`, radie 16, luftig marginal).
Allt är riktiga tal ur API:t; förhandsvisningen har påhittade bolag.

1. **Rubrik:** "Översikt" i Fraunces. Ingen ingress.
2. **Nyckeltal, fyra kort:** Bolag, Kunder, Personer, Att rätta. Etikett i 13 px
   dämpad överst, talet i Fraunces 2,5 rem med tabulära siffror, en dämpad rad under
   (till exempel "46 av 73 är kunder"). Kortet Att rätta är det enda framhävda:
   ockratonad platta (`Card variant="yellow"`), och länkar till Synk.
3. **Bolag per relation:** ring med totalen i mitten och förklaring under, som Twentys,
   i objektfärgerna. Exakta tal ur `/oversikt`.
4. **Senaste synkarna:** de fem senaste körningarna som rader: statusprick,
   anslutning, utfall i klartext, relativ tid. En pågående körning har förloppsstapel.
5. **Störst orter:** liggande staplar med rundade ändar för de sex vanligaste orterna.
   Räknas ur högst 500 hämtade bolag; är registret större står det i kortets fot.
6. **Senast ändrade:** fem bolag som postchips med relation och tid. Öppnar panelen.

Diagram ritas med `recharts` (finns redan i repot) eller ren SVG, i tokens. Läs
`Skill(dataviz)` först. Astryx egna diagram är förhandsutgåvor och används inte.

## Det som inte får hända

- Ingen färg utanför tokens, i någon fil. Ingen `#`-färg, ingen `rgb()`.
- Inga påhittade tal i appen. Förhandsvisningens data är märkt som exempel i koden,
  aldrig i gränssnittet som riktiga kunder.
- Ingen menypost, knapp eller flik som inte gör något.
- Inga kickers, versaler som etikett, spärrad text, em-streck eller kursiva rubriker
  (INV-UI-001). Varje synlig sträng på svenska och engelska (INV-COPY-001).
- `xstyle` kräver StyleX-kompilatorn, som Snajp inte kör. Använd komponenternas egna
  props, `className` och `style`, eller en omslutande `div` med Tailwind-klasser som
  läser Snajps tokens (`bg-paper2`, `text-ink-muted`, `border-ink/12`).
- Dialog och Drawer byggs med `Layout` (huvud, innehåll, fot), aldrig `padding={0}`.
- Astryx rot-tema tar bort `<html data-theme>`: `TemaVakt` i `CrmRam.tsx` ska stå kvar.

## Klart när

Varje punkt granskas i bild av huvudsessionen, inte av den som byggt.

1. Skalet, Översikt, Bolag (lista, markering, panel med tre flikar, redigering),
   Personer, Synk och Utvecklare finns i förhandsvisningen `/forhandsvisning/crm/...`
   och under `/crm/...`.
2. Bilder i 1440 och 390 px, ljust och mörkt, av varje vy och av öppen panel, öppen
   kommandopalett, markerade rader och en dialog med fältfel.
3. Lägsta textkontrast 4,5:1 i båda lägena, uppmätt.
4. Avgränsad typkontroll ren. INV-UI-001 och INV-COPY-001 gröna.
5. Sidan går inte att förväxla med version 1: postchips, avatarer, upphöjt blad,
   pillerval, kort och diagram syns vid första ögonkastet.
