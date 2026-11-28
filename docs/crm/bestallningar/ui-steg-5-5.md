# Steg 5.5: Team, Plan och fakturering, Tillägg, Notiser, Tema, Dataskydd, Kvitton

Bildernas prefix: `55-`, och de sparas i `docs/crm/bilder/fas5/` (inte fas4: det är det enda
som skiljer fas 5 från den gemensamma beställningen). Läs `git log --oneline -25` och
`ls components/crm/app components/crm/app/*/` först: fas 4 är byggd, och du ÅTERANVÄNDER dess mönster
(läs dem) i stället för att bygga egna: navigeringsregistret (`lib/crm/navigering.ts`), `useSkrivratt()`,
banderollen, utkastredigeraren, tråd- och inkorgsvyn, förhandsgranskningen med versioner, importen i steg,
`Bekraftelse`. Finns ett mönster inte under det namn din beställning nämner: sök efter det (grep på
"NYTT MÖNSTER" i `components/crm/app/`) innan du bygger något.

## Raderna

IN-080 till IN-095, IN-120 till IN-125, IN-143, IN-145 (`docs/crm/underlag/app-08-installningar.md`). IN-083 (rollbyte i Team) saknar ändpunkt
enligt underlaget: kontrollera i koden, och bygg det bara om ändpunkten finns.

## Facit för beteendet (läs, kopiera inte formen)

`components/settings/TeamSettings.tsx`, `PlanSettings.tsx`, `AddonSettings.tsx`, `NotisSettings.tsx`,
`TemaSettings.tsx`, `components/crm/app/Tillagg.tsx` (CRM-tilläggets egen sektion, finns redan).

## Det som ska byggas

Gruppen Kontot i inställningsskalet, en komponent per sektion. Team: bjud in, ta bort, roller, och
läsrollens begränsning. Plan och fakturering: det dagens sida visar, och **inga betalningar eller
planbyten utförs av gränssnittet utan att dagens sida gör exakt samma sak** (samma serveråtgärd).
Tillägg: dagens `AddonSettings` och CRM-tilläggets sektion i samma lista, inte två listor. Notiser.
Tema (ljust, mörkt, följer systemet: läs hur `CrmRam` byter tema i dag). Dataskydd (IN-143: ny sektion,
läs raden för vad den ska visa). Kvitton (bara med produkten).

Commit: `feat(crm): installningar for kontot (team, plan, tillagg, notiser, tema, dataskydd)`.
