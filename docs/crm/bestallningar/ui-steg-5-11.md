# Steg 5.11: `/crm/larande`

Bildernas prefix: `511-`, och de sparas i `docs/crm/bilder/fas5/` (inte fas4: det är det enda
som skiljer fas 5 från den gemensamma beställningen). Läs `git log --oneline -25` och
`ls components/crm/app components/crm/app/*/` först: fas 4 är byggd, och du ÅTERANVÄNDER dess mönster
(läs dem) i stället för att bygga egna: navigeringsregistret (`lib/crm/navigering.ts`), `useSkrivratt()`,
banderollen, utkastredigeraren, tråd- och inkorgsvyn, förhandsgranskningen med versioner, importen i steg,
`Bekraftelse`. Finns ett mönster inte under det namn din beställning nämner: sök efter det (grep på
"NYTT MÖNSTER" i `components/crm/app/`) innan du bygger något.

## Raderna

OV-080 till OV-091 (`docs/crm/underlag/app-02-oversikt-att-gora-larande.md`).

## Facit för beteendet (läs, kopiera inte formen)

`components/leads/AgentLarande.tsx`.

## Det som ska byggas

Vyn Lärande på `/crm/larande`: förslagen från båda agenterna, godkänn och avvisa, förhandsgranskning av
vad som ändras (`Forhandsgranskning`), historik. Posten läggs i registret i gruppen Arbetsyta. I dag
ligger Lärande utanför menyn: läs raden för vem som ska se den, och gör som i dag.

Commit: `feat(crm): larande i CRM:et`.
