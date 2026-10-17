"""Verktygen kvitto-assistenten får, och ingenting mer.

Samma form som `bookkeeping_chat_tools.py`, och av samma skäl (vitlistade
dataset, tenant ur kontexten, varje resultat sparas för INV-BOOK-003).
"Hur mycket la vi på resor i mars?" är sammanfattningen, "vilka kvitton
flaggades?" är listan, "varför är Telia-fakturan prioriterad?" är
`visa_kvitto` (kvittohanterarens granskning fält för fält), "har vi fått
något från Telia?" är `sok_kvitton`, och "vad är omvänd skattskyldighet?" är
kunskapen. Fler verktyg i stället för fler "jag vet inte" — beställningen
2026-10-06 var att agenten ska hitta svaren själv.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from agents import RunContextWrapper, function_tool

from ..bookkeeping.kunskap import KUNSKAP, sok_amne
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

    # Alla rader: sammanstall räknar utläggen och intäkterna (kundfakturorna)
    # var för sig, så en faktura blir aldrig ett utlägg.
    rader = await ctx.storage.list_bk_underlag(ctx.tenant_id, fran=f, till=t, limit=100_000)
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
    "resor" = transport och logi). Under "intakter": kundfakturorna för sig
    (fakturerat totalt, utgående moms, obetalt). Samma uträkning som
    resultatvyn i produkten.

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
            **_granskning_kort(r),
        }
        for r in rader[:MAX_RADER]
    ]
    return ctx.spara({"antal": len(rader), "visade": len(smalt), "kvitton": smalt})


def _granskning_kort(rad: dict[str, Any]) -> dict[str, Any]:
    """Kvittohanterarens granskning (grundprompten, migration 096) i kort form."""
    gr = rad.get("granskning") if isinstance(rad.get("granskning"), dict) else {}
    return {
        "granskningsstatus": rad.get("granskningsstatus"),
        "dokumenttyp": gr.get("dokumenttyp"),
        "flaggor": list(gr.get("flaggor") or []),
    }


async def _visa_kvitto_impl(ctx: KvittoChattContext, kvitto_id: str) -> str:
    rad = None
    try:
        rad = await ctx.storage.get_bk_underlag(ctx.tenant_id, (kvitto_id or "").strip())
    except Exception:  # noqa: BLE001 — ett id som inte är en uuid är ett kvitto som inte finns
        rad = None
    if rad is None:
        return ctx.spara({"fel": "Kvittot finns inte. Hämta id:t med lista_kvitton eller sok_kvitton."})
    gr = rad.get("granskning") if isinstance(rad.get("granskning"), dict) else {}
    falt = gr.get("fält") if isinstance(gr.get("fält"), dict) else {}
    return ctx.spara(
        {
            "id": rad.get("id"),
            "datum": rad.get("datum"),
            "motpart": rad.get("motpart"),
            "brutto": None if rad.get("brutto") is None else f"{rad['brutto']:f}",
            "belopp_original": rad.get("belopp_original"),
            "kategori": rad.get("kategori"),
            "kategorietikett": kategorietikett(rad.get("kategori")),
            "status": rad.get("status"),
            "anmarkning": rad.get("anmarkning"),
            "kalla": rad.get("kalla") or "uppladdning",
            "mejl_amne": rad.get("mejl_amne"),
            **_granskning_kort(rad),
            "klass": gr.get("klass"),
            "intern_notering": gr.get("intern_notering"),
            "kontrollrakningar": gr.get("kontrollräkningar"),
            "moms_per_sats": gr.get("moms_per_sats"),
            # Fält med säkerhet och källa. Personnummer och fullständiga
            # kortnummer extraheras aldrig (grundprompten 8.4), så inget här
            # behöver maskas.
            "falt": {n: p for n, p in falt.items() if isinstance(p, dict) and p.get("värde") is not None},
        }
    )


@function_tool
async def visa_kvitto(ctx: RunContextWrapper[KvittoChattContext], kvitto_id: str) -> str:
    """Allt om ETT kvitto: varje avläst fält med säkerhet och källa,
    flaggorna, kontrollräkningarna och varför det behöver granskas.

    Args:
        kvitto_id: Kvittots id, ur lista_kvitton eller sok_kvitton.
    """
    return await _visa_kvitto_impl(ctx.context, kvitto_id)


async def _sok_kvitton_impl(ctx: KvittoChattContext, fritext: str) -> str:
    ord_ = [o for o in (fritext or "").lower().split() if o]
    if not ord_:
        return ctx.spara({"fel": "Skriv vad du söker efter, till exempel en leverantör."})
    rader = bara_utlagg(await ctx.storage.list_bk_underlag(ctx.tenant_id, limit=100_000))

    def text(r: dict[str, Any]) -> str:
        gr = r.get("granskning") if isinstance(r.get("granskning"), dict) else {}
        falt = gr.get("fält") if isinstance(gr.get("fält"), dict) else {}
        varden = " ".join(str(p.get("värde") or "") for p in falt.values() if isinstance(p, dict))
        return " ".join(
            str(x or "")
            for x in (r.get("motpart"), r.get("mejl_amne"), r.get("filnamn"), r.get("kategori"), varden)
        ).lower()

    traffar = [r for r in rader if all(o in text(r) for o in ord_)]
    smalt = [
        {
            "id": r.get("id"),
            "datum": r.get("datum"),
            "motpart": r.get("motpart"),
            "brutto": None if r.get("brutto") is None else f"{r['brutto']:f}",
            "belopp_original": r.get("belopp_original"),
            "status": r.get("status"),
            **_granskning_kort(r),
        }
        for r in traffar[-MAX_RADER:]
    ]
    return ctx.spara({"sokt": fritext, "antal": len(traffar), "kvitton": smalt})


@function_tool
async def sok_kvitton(ctx: RunContextWrapper[KvittoChattContext], fritext: str) -> str:
    """Sök bland ALLA kvitton oavsett datum: leverantör, fakturanummer,
    ämnesrad eller kategori.

    Args:
        fritext: Det du söker efter, till exempel "telia" eller "48213".
    """
    return await _sok_kvitton_impl(ctx.context, fritext)


async def _sla_upp_kunskap_impl(ctx: KvittoChattContext, amne: str) -> str:
    traff = sok_amne(amne)
    if traff is None:
        return ctx.spara(
            {"hittades": False, "fraga": (amne or "").strip(), "kanda_amnen": sorted(KUNSKAP)}
        )
    return ctx.spara({"amne": traff.id, "rubrik": traff.rubrik, "text": traff.text})


@function_tool
async def sla_upp_kunskap(ctx: RunContextWrapper[KvittoChattContext], amne: str) -> str:
    """Snajps egen förklaring av ett begrepp: momssatser, omvänd
    skattskyldighet, representation, fakturakrav, verifikationer, EU-handel,
    import med mera. Svara ur texten, inte ur minnet.

    Args:
        amne: Ämnet eller frågan, till exempel "representation".
    """
    return await _sla_upp_kunskap_impl(ctx.context, amne)


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
KVITTO_CHATT_TOOLS = [
    hamta_kvittosammanfattning,
    lista_kvitton,
    visa_kvitto,
    sok_kvitton,
    sla_upp_kunskap,
]
