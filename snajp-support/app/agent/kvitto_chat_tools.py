"""Verktygen kvitto-assistenten får, och ingenting mer.

Samma form som `bookkeeping_chat_tools.py`, och av samma skäl (vitlistade
dataset, tenant ur kontexten, varje resultat sparas för INV-BOOK-003).
Verktygen är två: sammanfattningen och kvittolistan. En kvittofråga är
alltid en av dem — "hur mycket la vi på resor i mars?" är sammanfattningen,
"vilka kvitton flaggades?" är listan.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from agents import RunContextWrapper, function_tool

from ..bookkeeping.verifieringsgrind import STATUS_GRANSKA, STATUS_KLAR
from ..kvitton.sammanfattning import (
    KATEGORIGRUPPER,
    bara_utlagg,
    kategorietikett,
    sammanstall,
    summeringstext,
)
from ..storage.base import Storage

TILLATNA_STATUS = (STATUS_KLAR, STATUS_GRANSKA)
MAX_RADER = 50


@dataclass
class KvittoChattContext:
    """`resultat` är turens verktygssvar — hela indata till INV-BOOK-003."""

    storage: Storage
    tenant_id: str
    resultat: list[str] = field(default_factory=list)

    def spara(self, nyttolast: dict[str, Any]) -> str:
        text = json.dumps(nyttolast, ensure_ascii=False, default=str)
        self.resultat.append(text)
        return text


def _datum(rat: str) -> date | None:
    try:
        return date.fromisoformat(rat.strip())
    except (ValueError, AttributeError):
        return None


async def _hamta_kvittosammanfattning_impl(
    ctx: KvittoChattContext, fran: str, till: str
) -> str:
    f, t = _datum(fran), _datum(till)
    if f is None or t is None:
        return ctx.spara({"fel": "Datum ska skrivas som ÅÅÅÅ-MM-DD."})
    if t < f:
        return ctx.spara({"fel": "Slutdatumet ligger före startdatumet."})

    rader = bara_utlagg(
        await ctx.storage.list_bk_underlag(ctx.tenant_id, fran=f, till=t, limit=100_000)
    )
    samman = sammanstall(rader)
    text = summeringstext(samman, f.isoformat(), t.isoformat())
    return ctx.spara(
        {
            **{k: v for k, v in samman.items() if not k.startswith("_")},
            "fran": f.isoformat(),
            "till": t.isoformat(),
            "sammanfattning": text,
        }
    )


@function_tool
async def hamta_kvittosammanfattning(
    ctx: RunContextWrapper[KvittoChattContext], fran: str, till: str
) -> str:
    """Summorna för en period: antal kvitton, totalbelopp, ingående moms,
    summan per kategori och summan per kategorigrupp (per_grupp, till exempel
    "resor" = transport och logi). Samma uträkning som resultatvyn i produkten.

    Args:
        fran: Första dagen i perioden, ÅÅÅÅ-MM-DD.
        till: Sista dagen i perioden, ÅÅÅÅ-MM-DD.
    """
    return await _hamta_kvittosammanfattning_impl(ctx.context, fran, till)


async def _lista_kvitton_impl(
    ctx: KvittoChattContext,
    fran: str,
    till: str,
    status: str | None = None,
    kategori: str | None = None,
) -> str:
    f, t = _datum(fran), _datum(till)
    if f is None or t is None:
        return ctx.spara({"fel": "Datum ska skrivas som ÅÅÅÅ-MM-DD."})
    if status is not None and status not in TILLATNA_STATUS:
        return ctx.spara(
            {"fel": f"Okänd status {status!r}. Tillåtna: {', '.join(TILLATNA_STATUS)}."}
        )

    rader = bara_utlagg(
        await ctx.storage.list_bk_underlag(ctx.tenant_id, fran=f, till=t, limit=100_000)
    )
    if status is not None:
        rader = [r for r in rader if r.get("status") == status]
    if kategori is not None:
        # Ett gruppnamn ("resor") filtrerar på alla gruppens konton; annars
        # hade kategori="biljett" gett taxin och tåget men inte hotellet.
        nycklar = KATEGORIGRUPPER.get(kategori.strip(), (None, (kategori.strip(),)))[1]
        rader = [r for r in rader if (r.get("kategori") or "") in nycklar]

    smalt = [
        {
            "id": r.get("id"),
            "datum": r.get("datum"),
            "motpart": r.get("motpart"),
            "brutto": None if r.get("brutto") is None else f"{r['brutto']:f}",
            "valuta": "SEK" if r.get("brutto") is not None else (r.get("valuta") or "SEK"),
            "belopp_original": r.get("belopp_original"),
            "kategori": r.get("kategori"),
            "kategorietikett": kategorietikett(r.get("kategori")),
            "kalla": r.get("kalla") or "uppladdning",
            "status": r.get("status"),
            "anmarkning": r.get("anmarkning"),
        }
        for r in rader[:MAX_RADER]
    ]
    return ctx.spara({"antal": len(rader), "visade": len(smalt), "kvitton": smalt})


@function_tool
async def lista_kvitton(
    ctx: RunContextWrapper[KvittoChattContext],
    fran: str,
    till: str,
    status: str | None = None,
    kategori: str | None = None,
) -> str:
    """Kvittona i en period, med belopp, kategori, källa och status.

    Args:
        fran: Första dagen, ÅÅÅÅ-MM-DD.
        till: Sista dagen, ÅÅÅÅ-MM-DD.
        status: Valfritt filter: "klar" eller "granska_manuellt".
        kategori: Valfritt kategorifilter, till exempel "biljett" eller
            "representation", eller gruppen "resor" (biljett och kost_och_logi).
    """
    return await _lista_kvitton_impl(ctx.context, fran, till, status, kategori)


#: Ingen av dem skriver, ingen räknar i modellen, ingen tar emot en tenant.
KVITTO_CHATT_TOOLS = [hamta_kvittosammanfattning, lista_kvitton]
