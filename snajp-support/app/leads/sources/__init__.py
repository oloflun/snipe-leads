"""Prospektkällor bakom ETT protokoll.

Samma resonemang som LinkedIn-abstraktionen i `PROJECT_KNOWLEDGE.md`: koden
mot en leverantör låser produkten vid leverantörens villkor, priser och
uppsägningstid. Koden mot ett protokoll gör leverantören till ett byte av en
rad i en fabrik.

## Vad som INTE får bli en källa

`allabolag.se`, `hitta.se`, `ratsit.se` och LinkedIn-profiler skrapas inte.
Det bryter mot deras användarvillkor, och en produkt vars datainsamling är
kontraktsbrott går inte att sälja till ett bolag med en juristfunktion. Den
regeln står här, i modulen som definierar vad en källa är, för att nästa
implementation ska möta den innan den skrivs — inte i en handoff som ingen
läser.

Lagliga vägar, i den ordning vi tar dem:

1. **CSV** — vår egen lista, manuellt sammanställd ur bolagens egna publika
   sajter. Det är den enda källan som är påkopplad i dag.
2. **Bolagsverket** — officiellt register, kräver API-licens. Stub.
3. **Allabolag** — har ett betalt API. Att köpa det är lagligt; att skrapa
   sajten är det inte. Stub.
"""

from __future__ import annotations

from .base import Prospect, ProspectSource, SourceError
from .csv_source import CsvSource
from .registry import AllabolagSource, BolagsverketSource

__all__ = [
    "AllabolagSource",
    "BolagsverketSource",
    "CsvSource",
    "Prospect",
    "ProspectSource",
    "SourceError",
]
