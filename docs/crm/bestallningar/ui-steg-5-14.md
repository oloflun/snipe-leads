# Steg 5.14: `/crm/admin` Admin-översikten och plattformsadmin i skalet

Bildernas prefix: `514-`, och de sparas i `docs/crm/bilder/fas5/` (inte fas4: det är det enda
som skiljer fas 5 från den gemensamma beställningen). Läs `git log --oneline -25` och
`ls components/crm/app components/crm/app/*/` först: fas 4 är byggd, och du ÅTERANVÄNDER dess mönster
(läs dem) i stället för att bygga egna: navigeringsregistret (`lib/crm/navigering.ts`), `useSkrivratt()`,
banderollen, utkastredigeraren, tråd- och inkorgsvyn, förhandsgranskningen med versioner, importen i steg,
`Bekraftelse`. Finns ett mönster inte under det namn din beställning nämner: sök efter det (grep på
"NYTT MÖNSTER" i `components/crm/app/`) innan du bygger något.

## Raderna

AD-001 till AD-027, AD-137 till AD-139b (`docs/crm/underlag/app-09-adminytan.md`).

## Facit för beteendet (läs, kopiera inte formen)

`app/admin/page.tsx`, `app/admin/layout.tsx`, `components/admin/AdminShell.tsx`, `Portfoljvy.tsx`,
`KunderOversikt.tsx`, `KostnadOversikt.tsx`, `FelOchEskaleringar.tsx`, `Radgivare.tsx`, `BytKund.tsx`,
`lib/admin/sprak.ts` (adminytans texter: använd den där dagens gör det).

## Det som ska byggas

1. Gruppen **Plattform** i navigeringsregistret, bara plattformsadmin i vyn admin. **Grinden sitter på
   servern** (`getPlatformAdmin`): `app/crm/admin/layout.tsx` gör samma kontroll som `app/admin/layout.tsx`.
   Att menyn döljer posterna är hövlighet, inte grind.
2. **Admin-översikten** `/crm/admin`, byggd som `OversiktVy`: portföljen, kostnaden, fel och
   eskaleringar, och **frågerutan med regelbaserat svar** (AD-026, NYTT MÖNSTER, litet: `TextInput` och
   `Card`).
3. Det som återstår av plattformsadmin i skalet (AD-001 till AD-018) utöver det steg 4.1 byggde: läs
   `Arbetsytemeny.tsx` och `Banderoll.tsx` och bygg bara det som saknas.

Kunddata i bilderna är påhittad (reglerna i den gemensamma beställningen). Commit:
`feat(crm): admin-oversikten och gruppen Plattform`.
