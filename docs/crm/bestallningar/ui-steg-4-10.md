# Steg 4.10, 4.11 och 4.12: kampanjer, Iris-översikten och bolagssöket

Bildernas prefix: `410-`. Läs `git log --oneline -15` först: stegen före ditt är byggda, och du återanvänder deras komponenter (läs dem) i stället för att bygga egna.

## Raderna

LU-160 till LU-162 (kampanjer, `docs/crm/underlag/app-05-leads-utkast-konversationer-samtal.md` avsnitt J),
LR-020 till LR-027 (`docs/crm/underlag/app-03-leads-oversikt-pipeline-bolag.md` avsnitt B), LU-024, LU-032, LU-174
(översiktens kort), och LR-080 till LR-082 (bolagssöket, avsnitt D).

## Facit för beteendet (läs, kopiera inte formen)

`components/leads/Kampanjer.tsx`, `IrisErbjudanden.tsx`, `LeadsOversikt.tsx`, `LeadsDiagram.tsx`,
`BolagsSok.tsx`, `LeadsSnabbsok.tsx`.

## Det som ska byggas

1. `components/crm/app/iris/KampanjerVy.tsx` på `/crm/iris/kampanjer` med vyerna Kampanjer och
   Erbjudanden.
2. **Iris-översikten** `components/crm/app/iris/IrisOversikt.tsx` på `/crm/iris`, byggd som
   `OversiktVy`: nyckeltal, tratten, körningarna, utkast att granska, svar. **Talen ska säga samma sak
   som listorna** (LR-021): varje tal länkar till vyn som visar raderna bakom det, och räknas på samma
   sätt. Inga två tal som säger nästan samma sak (CLAUDE.md, regeln 2026-11-24).
3. **Bolagssöket i kommandopaletten** (`Kommandopalett.tsx`): gruppen Leads med träffar ur samma
   ändpunkt som dagens sök, som öppnar leadets panel.
4. Posterna Översikt (först i gruppen Iris) och Kampanjer.

Commit: `feat(crm): Iris oversikt, kampanjer och bolagssok i paletten`.
