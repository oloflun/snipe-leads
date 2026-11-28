# Steg 5.10: `/crm/att-gora`

Bildernas prefix: `510-`, och de sparas i `docs/crm/bilder/fas5/` (inte fas4: det är det enda
som skiljer fas 5 från den gemensamma beställningen). Läs `git log --oneline -25` och
`ls components/crm/app components/crm/app/*/` först: fas 4 är byggd, och du ÅTERANVÄNDER dess mönster
(läs dem) i stället för att bygga egna: navigeringsregistret (`lib/crm/navigering.ts`), `useSkrivratt()`,
banderollen, utkastredigeraren, tråd- och inkorgsvyn, förhandsgranskningen med versioner, importen i steg,
`Bekraftelse`. Finns ett mönster inte under det namn din beställning nämner: sök efter det (grep på
"NYTT MÖNSTER" i `components/crm/app/`) innan du bygger något.

## Raderna

OV-060 till OV-079 (`docs/crm/underlag/app-02-oversikt-att-gora-larande.md`), KV-170 (`docs/crm/underlag/app-07-kvitton.md`).

## Facit för beteendet (läs, kopiera inte formen)

`components/leads/AttGora.tsx` och det den hämtar.

## Det som ska byggas

**Kö med grupper och åtgärd i raden** (NYTT MÖNSTER, `components/crm/app/Ko.tsx`): flera köer på en sida
(per agent), räknare och åldershinkar ovanför, åtgärd direkt i raden (godkänn, bocka av, ta över) och
detaljen i en panel: leadets panel, utkastredigeraren och ärendets tråd, som redan finns. Vyn
`/crm/att-gora` med posten Att göra i gruppen Arbetsyta, med räknare (lägg räknaren i navigeringsregistret
som notisräknaren). Kvittons kö (KV-170) bara när produkten finns.

Commit: `feat(crm): att gora som en ko over Iris och kundtjanst`.
