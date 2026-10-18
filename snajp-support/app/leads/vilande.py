"""Snajps vilande produkter — backendens spegel av lib/routes.ts: VILANDE_PRODUKTER.

Sebbe 2026-10-17: Kvittohanteraren säljs inte just nu och ska inte finnas i
utkasten. Första mejlen slutade nämna den när den togs ur Snajps produktlista
(scripts/snajp_malgrupp.py), men uppföljningssvepet skrev vidare: det följer
upp tråden, inte produkten, och modellen läser det tidigare mejlet. Main köade
fyra nya kvittouppföljningar på två dygn efter beslutet.

Namnen är Snajps egna produktnamn, inte ett ämne: en kund som säljer
redovisningstjänster och skriver "kvitton" i sina mejl berörs inte. Töm
tuppeln när Kvittohanteraren släpps igen.
"""

from __future__ import annotations

import re

#: Produktnamnens stam, så att "Kvittohanteraren", "vår Kvittohanterare" och
#: "Kvittohanterarens" alla träffar.
VILANDE_PRODUKTSTAMMAR: tuple[str, ...] = ("kvittohanterar",)

_MONSTER = (
    re.compile("|".join(re.escape(s) for s in VILANDE_PRODUKTSTAMMAR), re.IGNORECASE)
    if VILANDE_PRODUKTSTAMMAR
    else None
)


def namner_vilande_produkt(text: str | None) -> bool:
    return bool(_MONSTER and text and _MONSTER.search(text))
