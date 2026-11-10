# Stabilitetsuppdraget: arbetslogg

Uppdraget "Snajp stabilt, snabbt och agenterna vassa" (Sebbe 2026-11-09) är
genomfört i fyra faser och ligger i `development` (`8f23e29` och den commit som
bär slutrapporten). Inget är släppt till `main`.

- **Slutrapporten:** [`SLUTRAPPORT.md`](SLUTRAPPORT.md), med före och efter,
  ändringar per fas, det som inte är gjort, risker, driftguide och GO/NO-GO.
- **Besluten:** `docs/BESLUT.md`, 2026-11-09 och 2026-11-10 (tre poster).
- **Mätresultaten:** `eval/` (före och efter per agent) och `last/`.
- **Mätinstrumenten:** `snajp-support/evals/` (README där) och
  `scripts/lasttest.py`.

## Läget i development

- Migration 115 (index) är körd mot development. Main saknar den, så
  speglingen står still tills releasen.
- Evalkunder: sex `eval-…` plus kvittohanterarens. Nycklarna står i
  `.env.deploy` (`EVAL_DEVELOPMENT_NYCKLAR`, första är supportens;
  `EVAL_DEVELOPMENT_IRISNYCKLAR`; `EVAL_DEVELOPMENT_KVITTONYCKEL`).

## Väntar på människor

- Release till main: Antons ord, PR #43. Produktionen lämnar ut agentens
  promptar i jobbsvaret tills dess (slutrapporten 5.1).
- Före mergen: `python scripts/railway_migrate.py --env main --apply`.
- Byt plattformsadminens lösenord (ligger i git-historiken).
- Kontrollera `AGENTSAJT_LOSEN` för supportportalen i Railway.
- Ny Railway-token i `.env.deploy`.
- Besluten i slutrapportens avsnitt 6.
