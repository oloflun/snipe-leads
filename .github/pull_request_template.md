## Vad och varför

<!-- Vad ändras, och varför. Länka beslut i docs/BESLUT.md om ett nytt beslut fattas. -->

## Säkerhet och dataskydd

<!-- Kryssa i minst en rad. CI fäller PR:en annars (INV-PROC-001, scripts/pr_granskning.py). -->

- [ ] Ändringen rör inte persondata, åtkomst och behörighet, hemligheter, nätverk, loggning eller beroenden.
- [ ] Ändringen rör något av det ovan, och skyddet står nedan (test, invariant eller grind som fäller).
- [ ] Ändringen visar eller skickar vidare webbplatsbedömningen, och den är grindad i samma commit (CLAUDE.md).

Skydd och test:

## AI-påverkan

<!-- Kryssa i minst en rad. -->

- [ ] Ingen prompt, modell, modellvariabel, region, autonominivå eller AI-grind ändras.
- [ ] Något av det ändras, och mätningen före och efter står nedan (evalsvit, facit eller provkörning i development).

Mätning:

## Verifiering

<!-- Vilka tester som kördes, lokalt och i CI. -->
