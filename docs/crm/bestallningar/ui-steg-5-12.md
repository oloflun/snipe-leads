# Steg 5.12: `/crm` Översikt utökad med agentavsnitten och Kom igång

Bildernas prefix: `512-`, och de sparas i `docs/crm/bilder/fas5/` (inte fas4: det är det enda
som skiljer fas 5 från den gemensamma beställningen). Läs `git log --oneline -25` och
`ls components/crm/app components/crm/app/*/` först: fas 4 är byggd, och du ÅTERANVÄNDER dess mönster
(läs dem) i stället för att bygga egna: navigeringsregistret (`lib/crm/navigering.ts`), `useSkrivratt()`,
banderollen, utkastredigeraren, tråd- och inkorgsvyn, förhandsgranskningen med versioner, importen i steg,
`Bekraftelse`. Finns ett mönster inte under det namn din beställning nämner: sök efter det (grep på
"NYTT MÖNSTER" i `components/crm/app/`) innan du bygger något.

## Raderna

OV-020 till OV-048, OV-101 (`docs/crm/underlag/app-02-oversikt-att-gora-larande.md`), SU-126, SU-190 (`docs/crm/underlag/app-06-support.md`), AD-138 (`docs/crm/underlag/app-09-adminytan.md`).

## Facit för beteendet (läs, kopiera inte formen)

`components/dashboard/StartView.tsx`, `OversiktPaneler.tsx`, `KomIgang.tsx`, `AgentLast.tsx`,
`Aktivitet.tsx`, `Analys.tsx`, och `components/crm/app/OversiktVy.tsx` (den du bygger IN i).

## Det som ska byggas

CRM:ets översikt (`OversiktVy`) utökas: agenternas avsnitt (Iris, supportagenten), Kom igång, veckans
utfall. **Detta är steget där regeln "byggs in, aldrig ovanpå" avgör allt** (CLAUDE.md 2026-11-24): hör
ett tal till de befintliga nyckeltalen står det där, hör en lista till de befintliga panelerna får den
samma huvud, plats i rutnätet och röst. Två rader tal i två stilar, eller två tal som säger nästan samma
sak, är fel. Varje tal länkar till vyn som visar raderna bakom det och räknas på samma sätt som där.
Driftkorten (AD-138) bara när svaret bär dem.

Commit: `feat(crm): oversikten bar agenterna och kom igang`.
