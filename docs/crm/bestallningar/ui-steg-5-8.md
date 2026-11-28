# Steg 5.8: testchatten (chattvyn)

Bildernas prefix: `58-`, och de sparas i `docs/crm/bilder/fas5/` (inte fas4: det är det enda
som skiljer fas 5 från den gemensamma beställningen). Läs `git log --oneline -25` och
`ls components/crm/app components/crm/app/*/` först: fas 4 är byggd, och du ÅTERANVÄNDER dess mönster
(läs dem) i stället för att bygga egna: navigeringsregistret (`lib/crm/navigering.ts`), `useSkrivratt()`,
banderollen, utkastredigeraren, tråd- och inkorgsvyn, förhandsgranskningen med versioner, importen i steg,
`Bekraftelse`. Finns ett mönster inte under det namn din beställning nämner: sök efter det (grep på
"NYTT MÖNSTER" i `components/crm/app/`) innan du bygger något.

## Raderna

SU-007, SU-070 till SU-088 (`docs/crm/underlag/app-06-support.md`).

## Facit för beteendet (läs, kopiera inte formen)

`components/snajp/SupportChat.tsx` (pollningen, skedena, kallstarten, bilagan, tummarna, förslagen,
felbeskeden för människor) och `HjalpRuta.tsx` (bara för att se hur hjälprutan skiljer sig: den går
under SIN EGEN nyckel och rörs inte av dig; se CLAUDE.md "Hjälprutan och felrapporter").

## Det som ska byggas

1. **Chattvyn** (NYTT MÖNSTER, `components/crm/app/Chattvy.tsx`): meddelandebubblor, skeden medan jobbet
   går, kallstart, bild som bilaga, tumme upp och ned, förslag i flödet, felbesked för människor. Byggd
   en gång: Kvittoassistenten i ett senare steg använder samma.
2. `/crm/kundtjanst/testchatt` med posten Testchatt (produkten support, inte för läsroll).

Commit: `feat(crm): testchatten i kundtjanst (chattvyn)`.
