# Handoff 2026-10-01 — Körningar (del A) och menyn i railen (del G)

**Läge:** två commits på lokala `development`, INTE pushade:
`1e96688` (körningar, migration 080, INV-JOB-003) och `42ae84c` (menyn ned i
railen). Planen för hela beställningen: `plans/2026-10-01-leads-suite-och-korningar.md`.

## Deployordning
1. `python scripts/railway_migrate.py --env development --apply` (torrkörd 2026-10-01: bara 080 väntar)
2. `git push origin development`

Koden skriver `leads_job_ledger.korning` — pushas den FÖRE migrationen faller
varje batchkörning på development.

## Pixelgranskning: INTE gjord, och varför
Maskinen hade 1,4 GB ledigt commit-minne av 39,7 GB (golvet är 4 GB, commit-
krasch 2026-09-28). Det som höll minnet: kunskapsgrafens `recall_daemon.py`
(1,1 GB, sanktionerat jobb), sju inspo-MCP-servrar från andra Claude-sessioner
(~1,5 GB) och Obsidian. Ingen dev-server startades. De 16 UI-ändringarna är
verifierade med `tsc --noEmit` och INV-UI-001, inte med renderade bilder.

**Nästa agent gör detta först**, när `FreeVirtualMemory` ≥ 4 GB (eller efter push,
mot development-URL:en):
- `/dashboard/iris/korningar`: tom-läget, listan med en pågående rad, en
  utfälld rad (levererade + bortvalda), 1440 och 375.
- `/dashboard/iris`: railens fot vid 1440 (BytKund/VyVaxel bara för admin,
  menyn, kontoadress, Logga ut + EN på en rad), toppraden vid 375 (namn,
  Meny, EN, Logga ut).
- Läs varje PNG, rätta, upprepa tills ett helt pass är rent. Bocka A7 och G4.

## Testläge
2 320 backend-tester, 397 rot-tester, tsc ren (2026-10-01).
