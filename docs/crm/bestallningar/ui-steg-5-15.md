# Steg 5.15: `/crm/admin/kunder` och kundens sida (fyra flikar)

Bildernas prefix: `515-`, och de sparas i `docs/crm/bilder/fas5/` (inte fas4: det är det enda
som skiljer fas 5 från den gemensamma beställningen). Läs `git log --oneline -25` och
`ls components/crm/app components/crm/app/*/` först: fas 4 är byggd, och du ÅTERANVÄNDER dess mönster
(läs dem) i stället för att bygga egna: navigeringsregistret (`lib/crm/navigering.ts`), `useSkrivratt()`,
banderollen, utkastredigeraren, tråd- och inkorgsvyn, förhandsgranskningen med versioner, importen i steg,
`Bekraftelse`. Finns ett mönster inte under det namn din beställning nämner: sök efter det (grep på
"NYTT MÖNSTER" i `components/crm/app/`) innan du bygger något.

## Raderna

AD-030 till AD-077 (`docs/crm/underlag/app-09-adminytan.md`), LK-126, LK-127 (`docs/crm/underlag/app-04-leads-korningar-listor-kallor.md`).

## Facit för beteendet (läs, kopiera inte formen)

`app/admin/kunder/`, `components/admin/Kundtabell.tsx`, `KundHuvud.tsx`, `Kundprofil.tsx`, `Kunddata.tsx`,
`Tillaggsvaljare.tsx`, `OppnaArbetsyta.tsx`, `KonverteraTestkund.tsx`, `Avstangning.tsx`,
`FlyttTillMain.tsx`, och `components/admin/insyn/*` (flödeskartan, lagerstapeln, källmatrisen, KB-provet).

## Det som ska byggas

1. **Kunder** `/crm/admin/kunder` som listvy.
2. **Kundens sida** `/crm/admin/kunder/[id]` med flikarna Agentprofil och tillägg, Uppgifter och
   kontakter, Underlag och flöde, Flytt till main (`?flik=`).
3. **Flödeskarta och lagerstapel** (NYTT MÖNSTER, AD-070 till AD-076): playbooks som banor med steg och
   kodgrindar, promptens lager, källmatris. Ren SVG i tokens, ingen förebild i Astryx.
4. **Farliga handlingar** (avstängning, konvertera testkund, flytt till main, kopiera lista till kund):
   samma serveråtgärder som dagens, alltid genom `Bekraftelse` med vad som händer i klartext, och
   förlopp och utfall där handlingen startades. **Kopiering av en lista till en annan kund bär aldrig
   webbplatsbedömningen** (`LISTRADSFALT` i backenden): gränssnittet lägger inte till något fält.

Commit: `feat(crm): admin kunder och kundens sida med fyra flikar`.
