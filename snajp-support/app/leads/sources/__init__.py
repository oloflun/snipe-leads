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

1. **JobTech/Platsbanken** — Arbetsförmedlingens öppna API. Gratis,
   nyckellöst, avsett för maskinell användning. Jobbannonsen är dessutom
   köpsignalen i sig. Påkopplad via `standardkallor()` sedan 2026-09-02.
2. **Nyhets-RSS** — publika pressflöden (RSS är ett format avsett för
   maskinell prenumeration). Påkopplad via `standardkallor()`.
3. **CSV** — vår egen lista, manuellt sammanställd ur bolagens egna publika
   sajter.
4. **Bolagsverket** — officiellt register, kräver API-licens. Stub.
5. **Allabolag** — har ett betalt API. Att köpa det är lagligt; att skrapa
   sajten är det inte. Stub.
"""

from __future__ import annotations

from .base import Prospect, ProspectSource, SourceError
from .csv_source import CsvSource
from .jobtech import JobTechSource
from .nyheter import NyhetsSource
from .registry import AllabolagSource, BolagsverketSource


def standardkallor() -> list[ProspectSource]:
    """Källorna discovery-federationen kör, i prioritetsordning.

    JobTech först: annonsen är den starkaste signalen och posterna bär oftast
    ort. Nyhetsflödet efter. CSV/registren är INTE med här — CSV kräver en
    konfigurerad fil och registren en licens; de kopplas på där de beställs.
    Env-styrning: LEADS_KALLOR (kommaseparerad delmängd av 'jobtech,nyheter').
    OSATT = båda. TOM STRÄNG = inga alls — det är testsvitens läge
    (tests/conftest.py), eftersom källorna gör riktiga HTTP-anrop och en
    svit som råkar nå internet är en svit vars gröna färg beror på vädret.
    """
    import os

    varde = os.environ.get("LEADS_KALLOR")
    if varde is None:
        varde = "jobtech,nyheter"
    valda = {k.strip() for k in varde.split(",") if k.strip()}
    kallor: list[ProspectSource] = []
    if "jobtech" in valda:
        kallor.append(JobTechSource())
    if "nyheter" in valda:
        kallor.append(NyhetsSource())
    return kallor


__all__ = [
    "AllabolagSource",
    "BolagsverketSource",
    "CsvSource",
    "JobTechSource",
    "NyhetsSource",
    "Prospect",
    "ProspectSource",
    "SourceError",
    "standardkallor",
]
