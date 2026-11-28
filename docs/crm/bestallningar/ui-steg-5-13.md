# Steg 5.13: `/crm/kvitton`

Bildernas prefix: `513-`, och de sparas i `docs/crm/bilder/fas5/` (inte fas4: det är det enda
som skiljer fas 5 från den gemensamma beställningen). Läs `git log --oneline -25` och
`ls components/crm/app components/crm/app/*/` först: fas 4 är byggd, och du ÅTERANVÄNDER dess mönster
(läs dem) i stället för att bygga egna: navigeringsregistret (`lib/crm/navigering.ts`), `useSkrivratt()`,
banderollen, utkastredigeraren, tråd- och inkorgsvyn, förhandsgranskningen med versioner, importen i steg,
`Bekraftelse`. Finns ett mönster inte under det namn din beställning nämner: sök efter det (grep på
"NYTT MÖNSTER" i `components/crm/app/`) innan du bygger något.

## Raderna

KV-01 till KV-208 (`docs/crm/underlag/app-07-kvitton.md`). Produkten är vilande och syns bara för plattformsadmin: grinden sitter på
servern, gör den inte svagare.

## Facit för beteendet (läs, kopiera inte formen)

`components/kvitton/KvittoYta.tsx`, `KvittoOversikt.tsx`, `KvittoVy.tsx`, `KvittoFlikar.tsx`,
`KvittoChatt.tsx`, `Integritetsnotis.tsx`.

## Det som ska byggas

`/crm/kvitton` med vyerna Översikt och Kvitton: listan, kvittots panel, uppladdning (importmönstret),
exporten, och assistenten i chattvyn från steg 5.8. Gruppen Kvitton i registret, bara plattformsadmin.

Commit: `feat(crm): kvitton i CRM:et (oversikt, kvitton, assistenten)`.
