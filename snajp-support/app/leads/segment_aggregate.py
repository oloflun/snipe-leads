"""G11: segmentaggregatet — den ENDA avsiktliga vägen över en tenantgräns.

Ren Python-implementation av exakt samma logik som SQL-funktionen
segment_ab_aggregate() (migration 013) — testbar utan en riktig databas.
Produktionsvägen går alltid genom SQL-funktionen (SECURITY DEFINER, körs
med en roll som har BYPASSRLS) eftersom det uttryckligen är det enda
stället i hela kodbasen som avsiktligt korsar tenantgränsen (Del G11). Den
här modulen finns för att kunna bevisa gränsvärdena (< 3 tenants ->
osynligt, ingen prospekt-/mejldata i utdatan) utan att seeda tre
tenants worth av data i en riktig databas för varje testkörning.
"""

from __future__ import annotations

from dataclasses import dataclass

MIN_TENANTS_PER_SEGMENT = 3


@dataclass(frozen=True)
class AbResultRow:
    """En rad ur ab_results, sedd genom tenant/erbjudande/variant-kedjan.
    Medvetet INGA fält för prospekt, kundnamn, mejltext eller
    erbjudandetexter — de finns inte i indatan, så de kan inte läcka ut."""

    tenant_id: str
    segment: str
    lever: str
    sent: int
    replies: int
    positive: int


@dataclass(frozen=True)
class SegmentAggregateRow:
    """Utdatan. Inget tenant_id-fält alls (G11: "den vyn har inget
    tenant_id att filtrera på") — strukturellt omöjligt att spåra tillbaka
    till en enskild kund från den här typen."""

    segment: str
    lever: str
    tenant_count: int
    sent: int
    replies: int
    positive: int


def compute_segment_aggregate(rows: list[AbResultRow]) -> list[SegmentAggregateRow]:
    """Grupperar per (segment, lever), summerar, och släpper grupper med
    färre än MIN_TENANTS_PER_SEGMENT distinkta tenants HELT — inte döljer
    dem bakom en flagga en anroparen skulle kunna ignorera."""
    groups: dict[tuple[str, str], list[AbResultRow]] = {}
    for row in rows:
        groups.setdefault((row.segment, row.lever), []).append(row)

    result: list[SegmentAggregateRow] = []
    for (segment, lever), group_rows in groups.items():
        tenant_ids = {r.tenant_id for r in group_rows}
        if len(tenant_ids) < MIN_TENANTS_PER_SEGMENT:
            continue
        result.append(
            SegmentAggregateRow(
                segment=segment,
                lever=lever,
                tenant_count=len(tenant_ids),
                sent=sum(r.sent for r in group_rows),
                replies=sum(r.replies for r in group_rows),
                positive=sum(r.positive for r in group_rows),
            )
        )
    return result
