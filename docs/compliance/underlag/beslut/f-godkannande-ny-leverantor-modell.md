## [FYLL: datum] (Anton) — Ingen ny mottagare av kunddata utan signerad checklista

**Bakgrund.** Den 2026-09-30 beslutade Anton att Jev aldrig ska se kundmejl. Ändå stod `INKORG_JEV=auto` i produktionen, och ämnesrad och upp till 1 500 tecken av kundmejl gick till TypeSafe i USA. TypeSafe stod inte i någon underbiträdeslista, och avtalet ger dem en tidsobegränsad rätt att använda härledd data. Ingen vet vem som slog på inställningen, eftersom en miljövariabel kunde ändras utan beslut. Flödet stoppades 2026-11-17.

**Beslut.** Ingen inställning, miljövariabel, kodändring eller integration som skickar kunddata eller andra personuppgifter till en ny mottagare får slås på i en miljö med riktig data (`main` eller `development`) förrän checklistan nedan är ifylld och signerad av Anton. Det gäller också en ny modell hos en leverantör som redan är godkänd, och en befintlig leverantör som ska få en ny sorts data.

**Checklista** (en per leverantör eller modell, sparas i `docs/compliance/loggar/`):

1. **Vad skickas, varifrån:** fält, datatyp och miljö. Brytaren (variabelns namn) och dess standardvärde, som ska vara av.
2. **Avtal:** DPA gäller kontot. Hur den ingicks (automatiskt, signerad, klick) och var kopian ligger, med datum.
3. **Plats:** var data behandlas och lagras. Vid tredjeland: DPF-status uppslagen med datum, annars SCC och en överföringsbedömning.
4. **Villkor:** ingen träning på kunddata, ingen tidsobegränsad rätt till härledd data, känd lagringstid, radering vid avtalets slut.
5. **Säkerhet:** SOC 2- eller ISO 27001-intyg, eller leverantörens säkerhetsbeskrivning, läst.
6. **Förteckningar:** leverantören står i `lib/bolag.ts`, PUB-avtalets Bilaga 3, pilotavtalets Bilaga 1 och registerförteckningen, i samma commit som koden.
7. **Kunderna:** är det ett nytt underbiträde för kunddata har kunderna fått besked i förväg enligt biträdesavtalet, och fristen för invändning har gått ut.
8. **Ny modell:** evalsviten körd före och efter, med resultatet bifogat.
9. **Konsekvensbedömning:** DPIA eller AI-konsekvensbedömning uppdaterad, eller ett skriftligt skäl till varför det inte behövs.
10. **Beslut:** Anton signerar checklistan och skriver en rad i `docs/BESLUT.md` med variabelns namn och värde.

**I praktiken.** Checklistan sammanfattar de sju stegen i G06 och avsnitt 6 i P27; vid en konflikt gäller den striktare. Sebbe och AI-kodverktyg får inte slå på sådana brytare. Den som ser en sådan inställning påslagen utan signerad checklista stänger av den och rapporterar till Anton enligt incidentrutinen. Det som saknas för att regeln ska hålla mekaniskt är en kodspärr som fäller uppstarten när en ej godkänd väg är på, efter mönstret för DeepSeek. Den är inte byggd.

Krav: GDPR AG-2, DS-1; ISO 27001 A.5.19, A.5.20, A.8.9; ISO 42001 A.10.3, 6.3, 8.1.

Datum: ____________________

Anton: ____________________
