# Steg 5.9: `/crm/kundtjanst/overlamnade`

Bildernas prefix: `59-`, och de sparas i `docs/crm/bilder/fas5/` (inte fas4: det är det enda
som skiljer fas 5 från den gemensamma beställningen). Läs `git log --oneline -25` och
`ls components/crm/app components/crm/app/*/` först: fas 4 är byggd, och du ÅTERANVÄNDER dess mönster
(läs dem) i stället för att bygga egna: navigeringsregistret (`lib/crm/navigering.ts`), `useSkrivratt()`,
banderollen, utkastredigeraren, tråd- och inkorgsvyn, förhandsgranskningen med versioner, importen i steg,
`Bekraftelse`. Finns ett mönster inte under det namn din beställning nämner: sök efter det (grep på
"NYTT MÖNSTER" i `components/crm/app/`) innan du bygger något.

## Raderna

SU-100 till SU-110, SU-207 till SU-211, SU-218 (`docs/crm/underlag/app-06-support.md`).

## Facit för beteendet

Supportportalen `support-webb/` (en egen liten app: läs den för beteendet) och ändpunkterna den anropar
i `snajp-support/app/api/`. Portalen lever kvar: du rör den inte.

## Det som ska byggas

Vyn Överlämnade på `/crm/kundtjanst/overlamnade`: chattar som supportagenten lämnat över till en
människa, i tråd- och inkorgsvyn, med svar som medarbetare, ta över, lämna tillbaka och avsluta som
raderna beskriver. Når en ändpunkt inte genom proxyn med kundens nyckel (portalen kan ha en egen
inloggning): bygg inte runt det, redovisa exakt vilken ändpunkt och vilken nyckel den kräver under
`saknas_i_backend`, och bygg det som går.

Commit: `feat(crm): overlamnade chattar i kundtjanst`.
