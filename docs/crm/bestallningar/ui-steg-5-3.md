# Steg 5.3: När agenten får svara själv, och Inkorgar

Bildernas prefix: `53-`, och de sparas i `docs/crm/bilder/fas5/` (inte fas4: det är det enda
som skiljer fas 5 från den gemensamma beställningen). Läs `git log --oneline -25` och
`ls components/crm/app components/crm/app/*/` först: fas 4 är byggd, och du ÅTERANVÄNDER dess mönster
(läs dem) i stället för att bygga egna: navigeringsregistret (`lib/crm/navigering.ts`), `useSkrivratt()`,
banderollen, utkastredigeraren, tråd- och inkorgsvyn, förhandsgranskningen med versioner, importen i steg,
`Bekraftelse`. Finns ett mönster inte under det namn din beställning nämner: sök efter det (grep på
"NYTT MÖNSTER" i `components/crm/app/`) innan du bygger något.

## Raderna

IN-050 till IN-076 (`docs/crm/underlag/app-08-installningar.md`), SU-140 till SU-168 (`docs/crm/underlag/app-06-support.md`).

## Facit för beteendet (läs, kopiera inte formen)

`components/settings/SupportRegler.tsx`, `SupportEskalering.tsx`, `Inkorgar.tsx`, `Vaxel.tsx`.

## Det som ska byggas

1. **När agenten får svara själv** (`kundtjanst`): reglerna, eskaleringen, fritext med
   förhandsgranskning och versioner (IN-061 till IN-063, SU-151, SU-152).
2. **Inkorgar** (`inkorgar`): listan över inkorgar med läge, och **Koppla inkorg** som en stegguide
   (NYTT MÖNSTER, `components/crm/app/Stegguide.tsx`: steg med framsteg, validering per steg, fortsätt
   och tillbaka; IN-072 till IN-075, SU-161 till SU-163). Onboardingen i ett senare steg använder samma.
   **Hemligheter visas aldrig** (app-lösenord, sessionsadressen `…@session.snajp.se`): fältet för ett
   app-lösenord är ett lösenordsfält som aldrig fylls i från svaret.
3. Test av en inkorg och utfallet där testet startades, kvar efter omladdning om backenden bär det.

Slå på sektionerna. Commit: `feat(crm): installningar for supportagentens regler och inkorgar`.
