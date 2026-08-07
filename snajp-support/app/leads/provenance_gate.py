"""Proveniensgrinden (Del A6, Del F, INV-DATA-001/002).

INV-DATA-001 (varje faktum har källa, datum och laglig grund) verkställs
redan av databasen: prospect_sources.source_url/retrieved_at/lawful_basis
är NOT NULL (migration 010). Den här modulen täcker det databasen INTE kan
uttrycka som en enkel CHECK — ordningen mellan käll-raderna för ETT
prospekt (INV-DATA-002): LinkedIn får aldrig vara den FÖRSTA källan, bara
verifiering av något redan hittat via en annan väg.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


class ProvenanceGateError(RuntimeError):
    pass


@dataclass(frozen=True)
class SourceRecord:
    source_type: str
    retrieved_at: datetime


def check_provenance(sources: list[SourceRecord]) -> None:
    """Kastar ProvenanceGateError om prospektet saknar källor helt
    (INV-DATA-001 kan inte vara sant för ett faktum utan källa) eller om
    den TIDIGAST hämtade källan är LinkedIn (INV-DATA-002)."""
    if not sources:
        raise ProvenanceGateError(
            "Ett prospekt utan någon registrerad källa kan inte godkännas (INV-DATA-001)."
        )
    earliest = min(sources, key=lambda s: s.retrieved_at)
    if earliest.source_type == "linkedin":
        raise ProvenanceGateError(
            "INV-DATA-002: LinkedIn kan inte vara ett prospekts FÖRSTA källa — "
            "bara verifiering av ett prospekt redan hittat via en annan väg "
            "(company_website, public_news, business_register, job_signal, ...)."
        )
