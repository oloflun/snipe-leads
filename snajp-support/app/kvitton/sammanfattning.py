"""Kvittosammanfattningen — summor per kategori och texten bredvid resultatet.

## Texten är DETERMINISTISK, inte formulerad av en modell

Sammanfattningen påstår belopp, och ett belopp som en modell formulerat är
ett belopp som kan glida — precis det INV-BOOK-003 finns för att stoppa i
chatten. Här byggs meningarna av kod ur samma summor som tabellen visar, så
texten och tabellen KAN inte säga olika saker. Tråkigare prosa, sannare
produkt.

## En uträkning, tre anropare

API:t (`/api/kvitton/sammanfattning`), skanningen (svaret efter en körning)
och chattverktyget (`hamta_kvittosammanfattning`) läser alla härifrån.
Samma skäl som `bookkeeping/period.py` anger: två uträkningar av samma
siffra blir förr eller senare två olika siffror.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from ..bookkeeping.math import moms_fran_brutto
from ..bookkeeping.verifieringsgrind import STATUS_KLAR

#: Kategorinyckel (kontoplanens) → etikett kunden ser. En okänd nyckel visas
#: som sig själv i stället för att gissas till närmaste etikett.
KATEGORIETIKETTER: dict[str, str] = {
    "drivmedel": "Drivmedel",
    # Etiketter som INTE överlappar. "Resor" och "Resor & logi" lät som samma
    # sak, och en fråga om resor fick taxin och tåget men inte hotellnatten.
    "biljett": "Resor & transport",
    "kost_och_logi": "Logi",
    "representation": "Representation",
    "kontorsmateriel": "Kontorsmateriel",
    "programvara": "Prenumerationer & programvara",
    "it_tjanst": "IT-tjänster",
    "forbrukningsinventarier": "Verktyg & förbrukning",
    "varuinkop": "Varuinköp",
    "mobiltelefon": "Telefoni",
    "datakommunikation": "Datakommunikation",
    "forsakring": "Försäkringar",
    "bankkostnad": "Bankkostnader",
    "annonsering": "Annonsering",
    "lokalhyra": "Lokalhyra",
    "ovrig_extern_kostnad": "Övrigt",
}


def kategorietikett(nyckel: str | None) -> str:
    if not nyckel:
        return "Okategoriserat"
    return KATEGORIETIKETTER.get(nyckel, nyckel)


def _kr(varde: Decimal) -> str:
    return f"{varde:f}"


def _kr_text(varde: Decimal) -> str:
    """Decimal("7817.50") → "7 817,50 kr" — för de byggda meningarna."""
    negativt = varde < 0
    heltal, _, decimaler = f"{abs(varde):.2f}".partition(".")
    grupperat = ""
    for i, tecken in enumerate(reversed(heltal)):
        if i and i % 3 == 0:
            grupperat = " " + grupperat
        grupperat = tecken + grupperat
    return f"{'−' if negativt else ''}{grupperat},{decimaler} kr"


def bara_utlagg(rader: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Kvittona, utan intäkter.

    `bk_underlag` delas med den gamla bokföringsytan, som också bär
    kundfakturor (`riktning="intakt"`). En skickad faktura på 10 000 kr är
    inte ett utlägg, och utan filtret hade den stått som 10 000 kr spenderat.
    Rader utan riktning (flaggade, oavlästa) räknas som kvitton.
    """
    return [r for r in rader if r.get("riktning") != "intakt"]


def sammanstall(rader: list[dict[str, Any]]) -> dict[str, Any]:
    """Summorna över en lista kvitton (bk_underlag-rader).

    Bara rader med status "klar" räknas in i beloppen — ett flaggat kvitto
    står i granskningsräkningen i stället för att bidra med ett osäkert tal.
    Samma regel som `berakna_period` följer. Intäkter räknas aldrig, se
    `bara_utlagg`.
    """
    rader = bara_utlagg(rader)
    klara = [r for r in rader if r.get("status") == STATUS_KLAR]
    granska = [r for r in rader if r.get("status") != STATUS_KLAR]

    totalt = Decimal("0")
    moms = Decimal("0")
    per_kategori: dict[str, dict[str, Any]] = {}
    storsta: dict[str, Any] | None = None

    for rad in klara:
        brutto = rad.get("brutto")
        sats = rad.get("momssats")
        if brutto is None:
            continue
        totalt += brutto
        if sats is not None:
            moms += moms_fran_brutto(brutto, sats)
        nyckel = rad.get("kategori") or ""
        post = per_kategori.setdefault(
            nyckel,
            {"kategori": nyckel, "etikett": kategorietikett(nyckel), "antal": 0, "summa": Decimal("0")},
        )
        post["antal"] += 1
        post["summa"] += brutto
        if storsta is None or brutto > storsta["brutto"]:
            storsta = {"motpart": rad.get("motpart") or rad.get("filnamn"), "brutto": brutto}

    kategorier = sorted(per_kategori.values(), key=lambda p: p["summa"], reverse=True)

    return {
        "antal": len(rader),
        "antal_klara": len(klara),
        "antal_granska": len(granska),
        "totalt": _kr(totalt),
        "moms": _kr(moms),
        "per_kategori": [
            {**p, "summa": _kr(p["summa"])} for p in kategorier
        ],
        "storsta": (
            {"motpart": storsta["motpart"], "brutto": _kr(storsta["brutto"])}
            if storsta
            else None
        ),
        # Kvar som Decimals för textbygget nedan — API-lagret tar bort fältet.
        "_totalt": totalt,
        "_moms": moms,
        "_kategorier": kategorier,
    }


def summeringstext(samman: dict[str, Any], fran: str, till: str) -> str:
    """Meningarna bredvid resultatrutan. Byggda av kod — se modulens docstring."""
    antal = samman["antal"]
    if antal == 0:
        return (
            f"Inga kvitton hittades för perioden {fran} till {till}. "
            "Kör en skanning av inkorgen, eller ladda upp ett kvitto manuellt."
        )

    klara = samman["antal_klara"]
    granska = samman["antal_granska"]
    totalt: Decimal = samman["_totalt"]
    kategorier = samman["_kategorier"]

    delar: list[str] = []
    delar.append(
        f"Agenten hittade {antal} kvitto{'n' if antal != 1 else ''} i perioden "
        f"{fran} till {till}"
        + (
            f", varav {klara} lästes av komplett på totalt {_kr_text(totalt)}."
            if granska
            else f", totalt {_kr_text(totalt)}."
        )
    )

    if kategorier:
        toppar = kategorier[:2]
        namn = " och ".join(p["etikett"].lower() for p in toppar)
        delar.append(
            f"Mest pengar gick till {namn} "
            f"({', '.join(_kr_text(p['summa']) for p in toppar)})."
        )

    moms: Decimal = samman["_moms"]
    if moms:
        delar.append(f"Den ingående momsen i de avlästa kvittona är {_kr_text(moms)}.")

    if granska:
        delar.append(
            f"{granska} kvitto{'n' if granska != 1 else ''} flaggades för manuell "
            "granskning — otydligt belopp, utländsk valuta eller en möjlig dubblett. "
            "De räknas inte in i summorna förrän du godkänt dem."
        )

    return " ".join(delar)


# -- Svarsmotorn utan modell -------------------------------------------------
#
# Simuleringsläget (ingen LLM-nyckel) ska ändå ge ett användbart samtal: svaren
# byggs av kod ur samma summor som tabellen visar, så varje tal är grundat per
# konstruktion — INV-BOOK-003 uppfyllt av att det inte finns någon modell som
# kan hitta på. Frågan tolkas grovt (månad + kategori); allt annat besvaras med
# periodens sammanfattning. Det är demons och den lokala stackens läge — i
# drift svarar den riktiga agenten i kvitto_agent.py.

_MANADER = {
    "januari": 1, "februari": 2, "mars": 3, "april": 4, "maj": 5, "juni": 6,
    "juli": 7, "augusti": 8, "september": 9, "oktober": 10, "november": 11,
    "december": 12,
}

#: Frågeord → kategorinycklar. Grovt med flit — träffar inget ord svarar vi
#: med helheten i stället för att gissa fel kategori. "Resor" i vardagligt
#: tal är både resan och hotellet, så ordet täcker båda kontona; den som
#: frågar om transport eller logi specifikt får bara det.
_FRAGEKATEGORIER: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("resor", ("biljett", "kost_och_logi")),
    ("resa", ("biljett", "kost_och_logi")),
    ("transport", ("biljett",)),
    ("taxi", ("biljett",)),
    ("tåg", ("biljett",)),
    ("hotell", ("kost_och_logi",)),
    ("logi", ("kost_och_logi",)),
    ("representation", ("representation",)),
    ("restaurang", ("representation",)),
    ("lunch", ("representation",)),
    ("kontorsmaterial", ("kontorsmateriel",)),
    ("kontorsmateriel", ("kontorsmateriel",)),
    ("prenumeration", ("programvara",)),
    ("programvara", ("programvara",)),
    ("drivmedel", ("drivmedel",)),
    ("bensin", ("drivmedel",)),
    ("diesel", ("drivmedel",)),
)


def tolka_period_ur_fraga(
    fraga: str, *, standard_fran: str, standard_till: str, ar: int
) -> tuple[str, str]:
    """"…på resor i mars?" → (2026-03-01, 2026-03-31). Hittas ingen månad
    används standardperioden. Året är innevarande — samma antagande som
    chattprompten ber modellen skriva ut."""
    saenkt = fraga.lower()
    for namn, manad in _MANADER.items():
        if namn in saenkt:
            from calendar import monthrange

            sista = monthrange(ar, manad)[1]
            return f"{ar}-{manad:02d}-01", f"{ar}-{manad:02d}-{sista:02d}"
    return standard_fran, standard_till


def svara_utan_modell(
    fraga: str, rader: list[dict[str, Any]], fran: str, till: str
) -> str:
    """Ett grundat svar utan modellanrop. Se kommentaren ovan."""
    saenkt = fraga.lower()
    rader = bara_utlagg(rader)
    samman = sammanstall(rader)

    if any(ord_ in saenkt for ord_ in ("granska", "flagga", "dubblett", "manuell")):
        granska = [r for r in rader if r.get("status") != STATUS_KLAR]
        if not granska:
            return "Inga kvitton väntar på granskning i perioden — allt lästes av komplett."
        punkter = "; ".join(
            f"{r.get('motpart') or r.get('filnamn')} ({(r.get('anmarkning') or 'saknar fält').rstrip('. ')})"
            for r in granska[:5]
        )
        return (
            f"{len(granska)} kvitto{'n' if len(granska) != 1 else ''} väntar på "
            f"granskning: {punkter}. De räknas inte in i summorna förrän du godkänt dem."
        )

    for ord_, nycklar in _FRAGEKATEGORIER:
        if ord_ in saenkt:
            träffar = [
                r
                for r in rader
                if r.get("status") == STATUS_KLAR and (r.get("kategori") or "") in nycklar
            ]
            summa = sum((r["brutto"] for r in träffar if r.get("brutto") is not None), Decimal("0"))
            etikett = " och ".join(kategorietikett(n).lower() for n in nycklar)
            if not träffar:
                return (
                    f"Jag hittar inga avlästa kvitton inom {etikett} i perioden "
                    f"{fran} till {till}."
                )
            exempel = ", ".join(
                f"{r.get('motpart')} ({_kr_text(r['brutto'])})"
                for r in träffar[:3]
                if r.get("brutto") is not None
            )
            return (
                f"Inom {etikett} finns {len(träffar)} kvitto"
                f"{'n' if len(träffar) != 1 else ''} i perioden {fran} till {till}, "
                f"totalt {_kr_text(summa)}: {exempel}."
            )

    return summeringstext(samman, fran, till)

