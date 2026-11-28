# Steg 5.4: Kanaler och Integrationer

Bildernas prefix: `54-`, och de sparas i `docs/crm/bilder/fas5/` (inte fas4: det är det enda
som skiljer fas 5 från den gemensamma beställningen). Läs `git log --oneline -25` och
`ls components/crm/app components/crm/app/*/` först: fas 4 är byggd, och du ÅTERANVÄNDER dess mönster
(läs dem) i stället för att bygga egna: navigeringsregistret (`lib/crm/navigering.ts`), `useSkrivratt()`,
banderollen, utkastredigeraren, tråd- och inkorgsvyn, förhandsgranskningen med versioner, importen i steg,
`Bekraftelse`. Finns ett mönster inte under det namn din beställning nämner: sök efter det (grep på
"NYTT MÖNSTER" i `components/crm/app/`) innan du bygger något.

## Raderna

SU-105 till SU-107, SU-212, SU-213 (`docs/crm/underlag/app-06-support.md`), IN-160 till IN-166 (`docs/crm/underlag/app-08-installningar.md`).

## Facit för beteendet

Det här finns i dag bara i backenden och i supportportalen `support-webb/` (läs den för beteendet: den är
en egen liten app, inte en del av Next-appen) och i `components/snajp/IntegrationSection.tsx`. Läs
ändpunkterna i `snajp-support/app/api/` (sök på kanal, integration) och i
`docs/crm/underlag/app-10-api-under-ytorna.md`.

## Det som ska byggas

Två nya sektioner under gruppen Kundtjänst: **Kanaler** (`kanaler`) och **Integrationer**
(`integrationer`). Byggs med listvyn och formulärdialogen. Kanal- och integrationshemligheter visas
aldrig efter att de sparats. Går en ändpunkt inte att nå genom proxyn `/api/snajp-support/...` med
kundens nyckel: bygg inte runt det, redovisa det under `saknas_i_backend` och bygg det som går.

Commit: `feat(crm): installningar for kanaler och integrationer`.
