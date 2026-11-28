# Steg 4.9: `/crm/iris/listor` med import och säljlista

Bildernas prefix: `49-`. Läs `git log --oneline -15` först: stegen före ditt är byggda, och du återanvänder deras komponenter (läs dem) i stället för att bygga egna.

## Raderna

LR-120 till LR-135 (`docs/crm/underlag/app-03-leads-oversikt-pipeline-bolag.md`, avsnitt G), LK-100 till LK-118 och
LK-142 till LK-151 (`docs/crm/underlag/app-04-leads-korningar-listor-kallor.md`, avsnitten F och G).

**Det här steget rör webbplatsbedömningen mer än något annat.** Läs funktionslistans avsnitt "Sekretess"
i sin helhet och CLAUDE.md om webbpoolen (leadsregel 20) innan du skriver en rad. Signalen på en
webbpoolsrad (`signal_detalj`) ÄR bedömningen. Visa webbnivå, län, signalens detalj, filter och sortering
på dem BARA när svaret bär fälten. CSV-exporten och kopieringen till en annan kund bär dem aldrig
(`snajp-support/app/api/admin_listor.py: LISTRADSFALT`). Ta bild med och utan fälten.

## Facit för beteendet (läs, kopiera inte formen)

`components/leads/LeadslistorView.tsx`, `ImportLista.tsx`, `Saljlista.tsx`, `CrmKundlista.tsx`,
`lib/leads/importfil.ts`, `importmallar.ts`, `importrader.ts` (IMPORTERAS, byggs inte om).

## Det som ska byggas

1. `components/crm/app/iris/ListorVy.tsx` på `/crm/iris/listor` med vyerna Listor och Säljlista.
   Lista, kombinera, filtrera, sortera, öppna en rad som lead (`LeadPanel`), utkast för listan med
   bestående förlopp, Processa om, CSV, och för plattformsadmin kopiera eller flytta till en annan kund.
2. **Uppladdning och import i steg** (NYTT MÖNSTER, `components/crm/app/Importguide.tsx`), en gång, så
   att Kundtjänst och Kvitton kan använda samma: fil in (dra och släpp, välj), kolumnkoppling med
   förslag, värdekontroll, granskning mot kunder, leads och spärrar, import i satser med förlopp och
   kvitto. Tolkningen kommer ur `lib/leads/import*.ts`.
3. **Säljlistan** med redigerbara celler (NYTT MÖNSTER om det behövs): status, anteckning och datum
   direkt i tabellen, med varning för dubbletter. Grindad på tillägget `leadlists`.
4. Posten Listor i gruppen Iris, och Importera lista i kommandopaletten.

Commit: `feat(crm): Iris listor med import i steg och saljlista`.
