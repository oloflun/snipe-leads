"""Kvittohanteraren — agenten som läser kundens inkorg och plockar ut kvitton.

Ersätter bokföringsagentens produktyta (2026-09-16). Maskineriet under —
filkontroll, textutvinning, normalisering, verifieringsgrind, SIE-export —
bor kvar i `app/bookkeeping/` och återanvänds härifrån: det är motor, inte
produktlogik, och en andra kopia hade glidit isär vid första ändringen.

Modulerna:
    mejl.py           mejlkonton (mock, Gmail API, Microsoft Graph) — läsning
    tolkning.py       kvittoidentifiering + deterministisk avläsning
    skanning.py       hela kedjan: hämta mejl → identifiera → läs av → spara
    sammanfattning.py periodsummor per kategori + sammanfattningstexten
"""
