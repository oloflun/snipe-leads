# Leadslistor skilda från Iris + CRM-kundlistor

## Scope
- Iris och leadslistorna hämtar aldrig samma bolag (Sebbe 2026-10-06).
- Kunder och Snajp-admin laddar upp sin befintliga CRM-kundlista under Leads › Listor, nåbart från översikten; de bolagen blir aldrig leads.

## Completed
- [x] Gemensam uteslutningsmängd `snajp-support/app/leads/upptagna.py` (orgnr eller namn utan bolagsform).
- [x] Iris-sökningen, körningsloopen, listbygget (merinfo + discovery) och listspåret läser mängden.
- [x] `kalla='crm'` på lead_lists (migration 098), import med `kalla`, dubbletter sammanslagna.
- [x] 409 på till-iris, prospektbefordran och kombinera för CRM-listor; knapparna dolda i UI:t.
- [x] `CrmKundlista.tsx` i Leads › Listor (även utan listtillägg), `?crm=1`, länk på översikten.
- [x] `demoAnpassa` behåller frågesträngen.
- [x] Tester: 10 nya, backend 2668 gröna, rotinvarianter gröna, tsc rent; sett i /demo 800 + 375 px, sv + en.
- [x] Commit `b57316f` pushad till development, 098 körd mot development, PR #31 uppdaterad, torrkörning mot main.

## In Progress
- [ ] Migrationerna 096–098 mot main — väntar på Antons godkännande.

## Remaining
- [ ] Prova CRM-uppladdningen med en syntetisk CSV på en testtenant (UI-flödet ej klickat).
- [ ] Antons merge av PR #31.

## Deferred
- Listbygget begränsat till bolag som underkänts för Iris — väntar på Sebbes besked.
- Fler än 2 000 rader per uppladdning.

## Blockers
- Antons ord för migrationerna mot main (CLAUDE.md §8.1a).

## Next Steps
- När Anton sagt ja: `python scripts/railway_migrate.py --env main --apply`, sedan hans merge.
- Syntetisk CSV-prov på development med en testtenant.
