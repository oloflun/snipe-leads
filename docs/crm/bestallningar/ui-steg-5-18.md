# Steg 5.18: installera som app, offline, kundens domän

Bildernas prefix: `518-`, och de sparas i `docs/crm/bilder/fas5/` (inte fas4: det är det enda
som skiljer fas 5 från den gemensamma beställningen). Läs `git log --oneline -25` och
`ls components/crm/app components/crm/app/*/` först: fas 4 är byggd, och du ÅTERANVÄNDER dess mönster
(läs dem) i stället för att bygga egna: navigeringsregistret (`lib/crm/navigering.ts`), `useSkrivratt()`,
banderollen, utkastredigeraren, tråd- och inkorgsvyn, förhandsgranskningen med versioner, importen i steg,
`Bekraftelse`. Finns ett mönster inte under det namn din beställning nämner: sök efter det (grep på
"NYTT MÖNSTER" i `components/crm/app/`) innan du bygger något.

## Raderna

SK-001 till SK-010, SK-150 till SK-154, SK-170 till SK-174 (`docs/crm/underlag/app-01-skal-inloggning-onboarding.md`).

## Facit för beteendet (läs, kopiera inte formen)

`components/InstalleraApp.tsx`, `app/manifest.ts`, och det raderna pekar ut.

## Det som ska byggas

Läs raderna först: flera är "ingen egen vy" eller gäller hela appen (manifestet, domänen) och ska då
INTE byggas om, bara redovisas som oförändrade. Bygg det som hör till skalet: Installera som app i
arbetsytemenyn om dagens har det, och offlinebeskedet i CRM:ets form. Rör inte `app/manifest.ts`,
proxyn eller domänhanteringen.

Commit: `feat(crm): installera som app och offlinebesked i skalet`.
