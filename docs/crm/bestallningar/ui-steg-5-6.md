# Steg 5.6: Plattformen (globala agentinstruktioner, tvåstegsverifiering)

Bildernas prefix: `56-`, och de sparas i `docs/crm/bilder/fas5/` (inte fas4: det är det enda
som skiljer fas 5 från den gemensamma beställningen). Läs `git log --oneline -25` och
`ls components/crm/app components/crm/app/*/` först: fas 4 är byggd, och du ÅTERANVÄNDER dess mönster
(läs dem) i stället för att bygga egna: navigeringsregistret (`lib/crm/navigering.ts`), `useSkrivratt()`,
banderollen, utkastredigeraren, tråd- och inkorgsvyn, förhandsgranskningen med versioner, importen i steg,
`Bekraftelse`. Finns ett mönster inte under det namn din beställning nämner: sök efter det (grep på
"NYTT MÖNSTER" i `components/crm/app/`) innan du bygger något.

## Raderna

IN-130 till IN-137 (`docs/crm/underlag/app-08-installningar.md`), AD-110 till AD-116 (`docs/crm/underlag/app-09-adminytan.md`), SK-048 (`docs/crm/underlag/app-01-skal-inloggning-onboarding.md`).

## Facit för beteendet (läs, kopiera inte formen)

`components/admin/Agentinstruktioner.tsx`, `components/settings/Tvafaktor.tsx`, sidorna under
`app/admin/installningar/`.

## Det som ska byggas

Gruppen Plattformen, BARA för plattformsadmin i vyn admin (grinden sitter på servern: läs hur dagens
sida gör och gör inte svagare). Globala agentinstruktioner med förhandsgranskning och versioner
(`Forhandsgranskning`). Tvåstegsverifiering: **hemligheten och återställningskoderna visas en enda
gång**, aldrig igen, och aldrig i en bild: förhandsvisningens svar bär påhittade värden.

Commit: `feat(crm): plattformens installningar (agentinstruktioner, tvastegsverifiering)`.
