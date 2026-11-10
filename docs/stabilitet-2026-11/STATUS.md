# Stabilitetsuppdraget: arbetslogg

Löpande läge för uppdraget "Snajp stabilt, snabbt och agenterna vassa"
(Sebbe 2026-11-09). Fas 0-rapporten ligger i `docs/fas0-2026-11-09/` i
huvudkatalogen (inte incheckad). Besluten står i `docs/BESLUT.md`.

Sebbe 2026-11-10: "kör klart alla faser, du får godkännelse för allt. När du
är klar med ALLT så pushar du." En push till `development` i slutet, inget
till `main` (det är Antons handgrepp).

## Klart

- **Fas 1** (i development, `6df6c2f`): se BESLUT.md 2026-11-09 och 2026-11-10.
- **Fas 2, läcka hittad på vägen** (`62ea7d5`, inte pushad): jobbsvaret,
  `/api/leads/runs` och två direkta agentsvar lämnade ut stegloggens texter
  (promptar, SOUL, kundminne, KB, webbplatsbedömningen i researchpromptarna).
  Gäller också produktionen tills nästa release.

## Kvar, i ordning

1. Fas 2 läsvägar: `utkast_lagen` utan lateral per tråd, `/skickat` i lätt
   läge, statusloggens max i SQL, smalare prospektlista, proxyns genomsläpp,
   index (migration).
2. Fas 2 support: klassaren parallellt, läsningarna före triagen samtidigt,
   pollningens takt, förlopp i chatten, kortare tidsgräns per steg.
3. Fas 2 jobb: massutskick och kvittoskanning som jobb med förlopp.
4. Fas 3: evalsviter (minst 30 fall per agent), promptar, injektionsskydd.
5. Fas 4: last-, kaos- och regressionstest.
6. Slutrapport med före/efter och GO/NO-GO, sedan push.

## Väntar på människor

- Byt plattformsadminens lösenord (ligger i git-historiken).
- Ny Railway-token i `.env.deploy`.
- Release till main: Antons ord, PR #43.
