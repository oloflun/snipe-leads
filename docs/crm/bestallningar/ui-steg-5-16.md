# Steg 5.16: `/crm/admin/paket` och `/crm/admin/logg`

Bildernas prefix: `516-`, och de sparas i `docs/crm/bilder/fas5/` (inte fas4: det är det enda
som skiljer fas 5 från den gemensamma beställningen). Läs `git log --oneline -25` och
`ls components/crm/app components/crm/app/*/` först: fas 4 är byggd, och du ÅTERANVÄNDER dess mönster
(läs dem) i stället för att bygga egna: navigeringsregistret (`lib/crm/navigering.ts`), `useSkrivratt()`,
banderollen, utkastredigeraren, tråd- och inkorgsvyn, förhandsgranskningen med versioner, importen i steg,
`Bekraftelse`. Finns ett mönster inte under det namn din beställning nämner: sök efter det (grep på
"NYTT MÖNSTER" i `components/crm/app/`) innan du bygger något.

## Raderna

AD-080 till AD-105, AD-130, AD-131 (`docs/crm/underlag/app-09-adminytan.md`), IN-094, IN-095 (`docs/crm/underlag/app-08-installningar.md`), KV-171, KV-172 (`docs/crm/underlag/app-07-kvitton.md`), LK-134.

## Facit för beteendet (läs, kopiera inte formen)

`app/admin/paket/`, `app/admin/korningar/`, `app/admin/handelser/`, `app/admin/testkorningar/`,
`app/admin/agentanvandning/`, `app/admin/bokforingsanvandning/`, `components/admin/PaketHantering.tsx`,
`PaketOversikt.tsx`, `KorningsOversikt.tsx`, `Handelselista.tsx`, `HandelseOversikt.tsx`,
`Testkorningar.tsx`, `AgentAnvandning.tsx`, `Felrapporter.tsx`.

## Det som ska byggas

1. **Paket och avtal** `/crm/admin/paket`.
2. **Logg** `/crm/admin/logg` med vyerna Körningar, Händelser, Testkörningar och Kostnad, och
   `/crm/admin/logg/[id]` för en körning med **stegspåret** (NYTT MÖNSTER, AD-084: en körnings steg i
   ordning med utfall, grindar och var den stannade; utgå från SynkVy:s förloppsrader).
3. Felrapporterna (AD-130, AD-131) om de hör hit enligt raderna: reglerna i CLAUDE.md "Hjälprutan och
   felrapporter" gäller, och kundens text visas aldrig för en kodande agent.

Commit: `feat(crm): admin paket och logg med stegspar`.
