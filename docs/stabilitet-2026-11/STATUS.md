# Stabilitetsuppdraget: arbetslogg

Löpande läge för uppdraget "Snajp stabilt, snabbt och agenterna vassa"
(Sebbe 2026-11-09). Fas 0-rapporten ligger i `docs/fas0-2026-11-09/` i
huvudkatalogen (inte incheckad). Besluten står i `docs/BESLUT.md`.

Sebbe 2026-11-10: "kör klart alla faser, du får godkännelse för allt. När du
är klar med ALLT så pushar du." En push till `development` i slutet, inget
till `main` (det är Antons handgrepp).

## Klart

- **Fas 1** (i development, `6df6c2f`): se BESLUT.md 2026-11-09 och 2026-11-10.
- **Fas 2** (commits efter `6df6c2f`, inte pushade):
  - Läcka stängd: jobbsvaret, `/api/leads/runs` och två direkta agentsvar
    lämnade ut stegloggens texter (promptar, SOUL, kundminne, KB,
    webbplatsbedömningen). Gäller produktionen tills nästa release.
  - `utkast_lagen` i en genomläsning (1,8 s → 0,1 s), migration 115 med index.
  - Support: triagens omförsök (71 %) bort med en påminnelserad, klassaren
    samtidigt, KB-sökningarna samtidigt, 20 s per modellanrop, skeden i
    chatten, tätare hämtning.
  - Kvittoskanningen och massutskicken som jobb med förlopp
    (`app/jobs/bakgrund.py`).
- **Fas 3, delar**: injektionsskydd i supporten (ram runt kundens text,
  läckspärr), evalsviterna i `snajp-support/evals/` med körare och mall.
- **Fas 4, delar**: 503 för beroendefel (`tests/kaos/`), `scripts/lasttest.py`.

## Mätningar

- Evalkunder i development: `eval-11100817-1..4` (nycklar i `.env.deploy`,
  `EVAL_DEVELOPMENT_NYCKLAR`; kund 1 har Livrustnings kunskapsbas).
- Före-värden körs mot development medan den kör `6df6c2f`:
  `python -m evals.kor kor --env development --agent <agent> --etikett fore`,
  `python scripts/lasttest.py --env development --etikett fore`.
- Efter pushen: samma med `--etikett efter`, sedan `python -m evals.kor jamfor fore efter`.
- Före pushen: `python scripts/railway_migrate.py --env development` (torrkörning), sedan `--apply` (migration 115).

## Kvar

1. Före-värden för Iris och kvitto (sviterna skrivs), lasttestets före-värde.
2. Fas 3: promptändringar som evalen pekar ut, mätta före och efter.
3. Slutrapport med före/efter och GO/NO-GO, BESLUT.md, sedan push och
   efter-mätning.

## Väntar på människor

- Byt plattformsadminens lösenord (ligger i git-historiken).
- Ny Railway-token i `.env.deploy`.
- Release till main: Antons ord, PR #43. Läckan ovan är ett skäl att inte vänta.
