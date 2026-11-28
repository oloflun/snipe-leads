# Steg 5.7: `/crm/kundtjanst` med Översikt och Ärenden (Ärenden, Testmail, Dolda)

Bildernas prefix: `57-`, och de sparas i `docs/crm/bilder/fas5/` (inte fas4: det är det enda
som skiljer fas 5 från den gemensamma beställningen). Läs `git log --oneline -25` och
`ls components/crm/app components/crm/app/*/` först: fas 4 är byggd, och du ÅTERANVÄNDER dess mönster
(läs dem) i stället för att bygga egna: navigeringsregistret (`lib/crm/navigering.ts`), `useSkrivratt()`,
banderollen, utkastredigeraren, tråd- och inkorgsvyn, förhandsgranskningen med versioner, importen i steg,
`Bekraftelse`. Finns ett mönster inte under det namn din beställning nämner: sök efter det (grep på
"NYTT MÖNSTER" i `components/crm/app/`) innan du bygger något.

## Raderna

SU-001 till SU-064 (`docs/crm/underlag/app-06-support.md`), utom SU-007 (testchatten, steg 5.8).

## Facit för beteendet (läs, kopiera inte formen)

`components/snajp/SupportWorkspaceTabs.tsx`, `SupportOversikt.tsx`, `InboxTriage.tsx`, `JournalVy.tsx`,
`Dashboard.tsx`, `AgentMenu.tsx`, och `snajp-support/app/support_oversikt.py` (svarets form).

## Det som ska byggas

1. **Kundtjänstens översikt** `components/crm/app/kundtjanst/KundtjanstOversikt.tsx` på `/crm/kundtjanst`,
   byggd som `OversiktVy`. Talen säger samma sak som ärendelistan och länkar dit.
   **Driftrutan (SU-063):** backenden lämnar i dag `drift` (körningar, tokens, cache, modell) till
   varje kund, och bara vyn är grindad. Om ändpunkten ska grinda är Antons beslut (E3) och inte ditt:
   visa rutan BARA för plattformsadmin i vyn admin, precis som dagens `SupportOversikt` gör, och läs
   aldrig fälten utanför den rutan (utom `drift.kb_artiklar`, som dagens vy visar för alla).
2. **Ärenden** `components/crm/app/kundtjanst/ArendenVy.tsx` på `/crm/kundtjanst/arenden` med vyerna
   Ärenden, Testmail och Dolda. Tråd- och inkorgsvyn från steg 4.6 bär den (lista till vänster, öppen
   tråd till höger, `?arende=<id>` i adressen), och utkastredigeraren från 4.3 bär svaret (SU-021 till
   SU-025): godkänn, redigera, avvisa, skriv om, eskalera, dölj, med förlopp medan agenten skriver.
3. Posterna Översikt och Ärenden i gruppen Kundtjänst (produkten support), och i kommandopaletten.
   En arbetsyta utan produkten: läs SK-062 och OV-016 (säljvy i stället för 404) och gör som raderna säger.

Text säger supportagent, aldrig supportbot. Commit:
`feat(crm): kundtjanst med oversikt och arenden (arenden, testmail, dolda)`.
