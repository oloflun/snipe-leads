# Steg 5.19: läsroll och kundbesök i de äldre CRM-vyerna (SK-039)

Bildernas prefix: `519-`, och de sparas i `docs/crm/bilder/fas5/` (inte fas4: det är det enda
som skiljer fas 5 från den gemensamma beställningen). Läs `git log --oneline -25` och
`ls components/crm/app components/crm/app/*/` först: fas 4 är byggd, och du ÅTERANVÄNDER dess mönster
(läs dem) i stället för att bygga egna: navigeringsregistret (`lib/crm/navigering.ts`), `useSkrivratt()`,
banderollen, utkastredigeraren, tråd- och inkorgsvyn, förhandsgranskningen med versioner, importen i steg,
`Bekraftelse`. Finns ett mönster inte under det namn din beställning nämner: sök efter det (grep på
"NYTT MÖNSTER" i `components/crm/app/`) innan du bygger något.

## Raderna

SK-039 (`docs/crm/underlag/app-01-skal-inloggning-onboarding.md`) och funktionslistans avsnitt "Sekretess", punkt 6 och 7.

## Läget

`useSkrivratt()` i `components/crm/app/kit.tsx` ger `{ far, skal }`. Skalet och Iris-vyerna använder
den. De äldre vyerna gör det INTE: `BolagVy`, `BolagPanel`, `BolagFormular`, `PersonerVy`, `PersonPanel`,
`PersonFormular`, `AffarerVy`, `AffarPanel`, `AffarFormular`, `Stegdialog`, `UppgifterVy`, `SynkVy`,
`SparrarVy`, `UtvecklareVy`, `Webhooks`, `Tidslinje`, `Bilagor`, `Papperskorg`, `Registret`, `Kundlista`,
`Tillagg`. Proxyn stoppar läsrollens skrivningar, men knapparna ser tryckbara ut och anropet faller på 403.

## Det som ska byggas

Gå igenom varje fil ovan och varje skrivande handling i den (skapa, ändra, ta bort, ångra, ladda upp,
importera, köra synk, skapa nyckel, dra kort på tavlan, redigera i raden). Stäng av den med `far` och
ge förklaringen `skal`, på samma sätt som `LeadsVy` gör (läs den). Göm inte knappen. Dra-och-släpp på
tavlan stängs av helt för den som inte får skriva. Ändra ingenting annat i filerna.

Bilder: `?roll=lasare` och `?besok=1` i förhandsvisningen på Bolag, en panel, Affärer, Uppgifter, Synk,
Spärrar och Utvecklare.

Commit: `fix(crm): lasroll och kundbesok stanger av skrivande knappar i de aldre vyerna`.
