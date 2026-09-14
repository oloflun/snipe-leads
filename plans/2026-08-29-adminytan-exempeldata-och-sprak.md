# Adminytan: exempeldata, tvåspråkighet och läsbara händelsetexter

## Scope

De tre vyerna under `/admin` som en plattformsadmin faktiskt använder —
Översikt, Kunder & Data och Händelser. Uppgiften kom från tre skärmbilder:
kolumner fulla av nollor, engelska flikar över svenska tabellrubriker, och ett
notiscenter som visade leverantörernas råa JSON-fel.

Planen omfattar INTE main-uppdateringen, faktureringen hos Google eller
betalväxeln — de ligger kvar i `plans/2026-08-28-skarpa-korningar-och-produktion.md`.

## Completed

- [x] `lib/admin/exempeldata.ts` — deterministiska exempeltal för arbetsytor helt
      utan aktivitet. Sex profiler (frisk, tung, bara support, bara leads,
      slocknande, nystartad), varje rad märkt `ar_exempel`, avstängbar med
      `NEXT_PUBLIC_ADMIN_EXEMPELDATA=av`.
- [x] Rader med riktig aktivitet lämnas orörda — Nordlys Handel och Snajp ser
      likadana ut med och utan modulen.
- [x] `lib/admin/sprak.ts` + klientkomponenter — hela adminytan byter språk med
      EN/SV-knappen: kolumnrubriker, hälsomotiveringar, statistik, rådgivarens
      frågor och svar, fotnoter, plattformsflikar.
- [x] Språkvalet sparas i `localStorage` (`lib/i18n.tsx`). Det snäppte förut
      tillbaka till svenska vid varje omladdning.
- [x] `lib/admin/handelsetext.ts` — tio tolkare (kvot, saknad modell, behörighet,
      mail, databas, indata, timeout, anslutning, överbelastning, internt fel).
      Råtexten bevaras bakom "Tekniska detaljer".
- [x] Hydreringsfix — klockan läses en gång i server-komponenten och skickas ned
      som `nu: number`; tidszonen spikad till `Europe/Stockholm` i `sprak.ts`.
      Verifierat med Playwright mot tre webbläsartidszoner, med och utan fixen.
- [x] Tokenkostnaden = Googles listpris för `gemini-3.6-flash`, delad i in-
      (7,14 kr) och utpris (35,71 kr) per miljon tokens.
- [x] Exempelraderna räknas med i statistikgrafen; demoytor undantagna oavsett
      märke via `arDemoyta()`.
- [x] Registreringsdatumen sprids jämnt över tolvveckorsfönstret så kurvan fylls.
- [x] Sex commits deployade till `development`, samtliga `SUCCESS`.

## Remaining

- [ ] Sätt om tokenpriserna till 14,29 / 71,43 före 2027-01-01 — Googles
      introduktionspris upphör då.
- [ ] Avgör vad marginalkolumnen ska visa. Vid realistiska volymer är den
      konstant 100 %, och det är en egenskap hos affären snarare än hos koden.

## Deferred

- **Bredare kurva än tolv veckor** — inte efterfrågat, och skulle kräva att
  fönstret i `beraknaKundstatistik` och `SPRIDNING_VECKOR` ändras i takt.
- **Exempeldata i produktionen (`main`)** — modulen är påslagen som default och
  följer med vid nästa main-uppdatering. Om `main` inte ska visa exempeltal
  måste `NEXT_PUBLIC_ADMIN_EXEMPELDATA=av` sättas i den Railway-miljön.

## Blockers

- **Faktureringen hos Google är inte påslagen.** Det gör kostnadstalen till
  listpris i stället för utfall, och det är samma orsak som ger kvotfelen
  (`limit: 20`) i notiscentret. Åtgärdslistan ligger i `docs/JURIDIK_ATGARDER.md`
  och kräver Anton.

## Next Steps

1. Starta om sessionen och bekräfta att `react-components`,
   `next-best-practices` och `impeccable` laddas ur `~\.claude\skills\`.
2. Besluta om exempeldatan ska vara på eller av när `main` uppdateras.
3. Ta ställning till marginalkolumnen när en riktig leverantörsfaktura finns.
