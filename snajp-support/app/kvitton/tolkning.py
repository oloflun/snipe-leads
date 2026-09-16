"""Kvittoidentifiering och den deterministiska avläsningen.

## Två lägen, samma kontrakt

Avläsningen av ett kvitto görs normalt av modellen (`las_underlag` i
`agent/bookkeeping_agent.py` — dubbelläsning, grind, verifikat). Utan
LLM-nyckel (simuleringsläge, lokala körningar, testsviten) används i stället
`tolka_deterministiskt` här: rena regexar över mejltexten. Båda vägarna
returnerar RÅA fält som sedan går genom `normalisera_falt` och
verifieringsgrinden — grinden är alltid densamma, bara läsaren byts.

Regexläsaren gissar aldrig: hittas inget totalbelopp UTELÄMNAS fältet och
grinden skickar kvittot till manuell granskning. Samma regel som modellens
systemprompt ställer.

## Valutan

Ett kvitto i utländsk valuta (USD, EUR, GBP) läses av men RÄKNAS INTE OM —
en växelkurs vi hittar på är ett belopp vi hittar på. Beloppet utelämnas ur
SEK-fälten, valutan och originalbeloppet sparas, och kvittot flaggas för
manuell granskning med en anmärkning som säger varför. Valutaavgörandet
körs av koden även när MODELLEN läst kvittot — se `valutaspärr`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .mejl import Mejl

#: Ord som gör ett mejl till en kvittokandidat. Medvetet brett — kandidaten
#: går vidare till avläsning, och ett mejl utan belopp faller där i stället.
_KVITTOORD = re.compile(
    r"(?i)\b(kvitto|receipt|faktura|invoice|orderbekräftelse|order confirmation"
    r"|betalning|payment|betalt|paid|tack för ditt köp|thank you for your purchase"
    r"|prenumeration|subscription)\b"
)

#: Beloppsraden. Kräver en etikett FÖRE talet — ett årtal eller ett
#: ordernummer ska inte kunna bli ett totalbelopp.
#:
#: `\b` före etiketten är inte kosmetik: utan den matchade "total" inuti
#: "Subtotal", och kvittots delsumma blev dess totalbelopp. Talet är
#: strukturerat (tusengrupper + högst två decimaler) i stället för "siffror
#: och skiljetecken i valfri ordning", som gjorde "1,245.00" till 1.245.
_BELOPP = re.compile(
    r"(?i)\b(att betala|amount due|totalt|total|summa|amount)\b\s*[:=]?\s*"
    r"(?:(\$|€|£|sek|usd|eur|gbp)\s*)?"
    r"(\d{1,3}(?:[  .,]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
    r"(?:\s*(kr|sek|usd|eur|gbp|€|\$|£))?"
)

#: Etiketternas företräde när ett kvitto bär flera: det som ska betalas slår
#: totalen, och totalen slår en summa (som ofta är en delsumma eller en rad).
_ETIKETTRANG = {
    "att betala": 3,
    "amount due": 3,
    "totalt": 2,
    "total": 2,
    "summa": 1,
    "amount": 1,
}

#: Valutamarkörer var som helst i texten. Träffar något av dem och det valda
#: beloppet saknar ett uttryckligt "kr"/"SEK" behandlas kvittot som utländskt
#: — "Amount: 45.00 / Currency: USD" har valutan på en ANNAN rad än beloppet.
_UTLANDSK_MARKOR = re.compile(r"(?i)(€|\$|£|\b(?:eur|usd|gbp)\b)")

_MOMS = re.compile(r"(?i)(?:moms|vat|tax)\D{0,10}(25|12|6|0)\s*%")

_DATUM = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")

_BETALD = re.compile(
    r"(?i)\b(betalt|betald|betalt med kort|kortköp|swish|kontant|paid|autogiro"
    r"|dras via|charged)\b"
)
_OBETALD = re.compile(r"(?i)\b(förfallodatum|att betala senast|betalningsvillkor|due date)\b")

#: Nyckelord → kategori (nycklarna i bookkeeping/kontoplan.KOSTNADSKATEGORIER).
#: Ordningen spelar roll: första träffen vinner, så de specifika står först.
_KATEGORIORD: tuple[tuple[str, str], ...] = (
    (r"(?i)\b(diesel|bensin|drivmedel|tankning|liter)\b", "drivmedel"),
    (r"(?i)\b(taxi|tåg|biljett|resa|flyg|sl-|buss|train|flight)\b", "biljett"),
    (r"(?i)\b(hotell|vistelse|natt|logi|rum|hotel)\b", "kost_och_logi"),
    (r"(?i)\b(restaurang|bistro|lunch|middag|servering|café|cafe)\b", "representation"),
    (r"(?i)\b(kontorsvaror|kopieringspapper|pärmar|toner|kontorsmateriel)\b", "kontorsmateriel"),
    (r"(?i)\b(prenumeration|subscription|licens|seat|molnlagring|saas|programvara)\b", "programvara"),
    (r"(?i)\b(borrmaskin|verktyg|bitssats|förbrukning)\b", "forbrukningsinventarier"),
    (r"(?i)\b(parkering|parking)\b", "ovrig_extern_kostnad"),
)

_UTLANDSK = {"$": "USD", "€": "EUR", "£": "GBP", "usd": "USD", "eur": "EUR", "gbp": "GBP"}


def valutaspärr(falt: dict, text: str) -> tuple[dict, str, str | None, str]:
    """Ta bort SEK-beloppet ur fälten när kvittot är i utländsk valuta.

    Gäller BÅDA läsvägarna. Modellen skriver av totalbeloppet som det står,
    alltså blir "$45.00" brutto 45.00 — och det hade räknats som 45 kronor i
    summan. Valutan avgörs här av koden ur samma text, och beloppet flyttas
    till originalfältet i stället för att räknas om med en påhittad kurs.

    Returnerar (fält, valuta, originalbelopp, anmärkning).
    """
    avlast = tolka_deterministiskt(text)
    if avlast.valuta == "SEK":
        return falt, "SEK", None, ""
    rensat = {k: v for k, v in falt.items() if k not in ("brutto", "momssats")}
    return rensat, avlast.valuta, avlast.belopp_original, avlast.anmarkning


def ar_kvittokandidat(mejl: Mejl) -> bool:
    """Om mejlet ser ut att bära ett kvitto, en faktura eller ett utlägg.

    Ett nyhetsbrev som råkar nämna ordet "betalning" utan någon beloppsrad
    går vidare — och faller sedan i avläsningen på att belopp saknas. Hellre
    en kandidat för mycket än ett kvitto som aldrig lästes.
    """
    samlat = f"{mejl.amne}\n{mejl.text}"
    return bool(_KVITTOORD.search(samlat))


@dataclass(frozen=True)
class DeterministiskAvlasning:
    """Råa fält + valutainformationen som SEK-fälten inte kan bära."""

    falt: dict
    #: "SEK" när beloppet är svenskt. Annars valutakoden, och då är
    #: `belopp_original` satt och `falt` saknar brutto.
    valuta: str
    belopp_original: str | None
    anmarkning: str


def _normalisera_tal(rat: str) -> str:
    """"1 245,00" → "1245.00", "1,245.00" → "1245.00", "1.245,00" → "1245.00".

    Det SISTA skiljetecknet är decimaltecken om det följs av en eller två
    siffror; allt annat är tusenavskiljare. Ett ensamt skiljetecken följt av
    exakt tre siffror ("1.245") är en tusengrupp, inte 1,245 kronor.
    """
    rensad = rat.replace(" ", "").replace(" ", "").strip()
    sista = max(rensad.rfind(","), rensad.rfind("."))
    if sista == -1:
        return rensad
    decimaler = rensad[sista + 1 :]
    heltal = re.sub(r"[.,]", "", rensad[:sista])
    if len(decimaler) in (1, 2):
        return f"{heltal}.{decimaler}"
    return f"{heltal}{decimaler}"


def _valj_beloppstraff(text: str) -> re.Match[str] | None:
    """Beloppet kvittot faktiskt handlar om, eller None.

    Ett tal utan decimaler OCH utan valutamarkör räknas inte — "Summa 3
    artiklar" är ett antal, inte 3 kronor. Bland giltiga träffar vinner
    högst rang, och vid lika rang den sista (totalen står under raderna).
    """
    kandidater = []
    for träff in _BELOPP.finditer(text):
        etikett, prefix, tal, suffix = träff.groups()
        har_decimaler = bool(re.search(r"[.,]\d{1,2}$", tal))
        if not har_decimaler and not prefix and not suffix:
            continue
        kandidater.append((_ETIKETTRANG[etikett.lower()], träff.start(), träff))
    if not kandidater:
        return None
    return max(kandidater, key=lambda k: (k[0], k[1]))[2]


def tolka_deterministiskt(mejl_text: str, *, avsandare: str = "") -> DeterministiskAvlasning:
    """Regexavläsningen. Utelämnar hellre än gissar — se modulens docstring."""
    falt: dict = {}
    valuta = "SEK"
    belopp_original: str | None = None
    anmarkningar: list[str] = []

    träff = _valj_beloppstraff(mejl_text)
    if träff:
        _, prefix, tal, suffix = träff.groups()
        normaliserat = _normalisera_tal(tal)
        markorer = [m.lower() for m in (prefix, suffix) if m]
        uttryckligen_sek = any(m in ("kr", "sek") for m in markorer)
        utlandsk = next((_UTLANDSK[m] for m in markorer if m in _UTLANDSK), None)
        if utlandsk is None and not uttryckligen_sek:
            global_markor = _UTLANDSK_MARKOR.search(mejl_text)
            if global_markor:
                utlandsk = _UTLANDSK[global_markor.group(1).lower()]
        if utlandsk:
            valuta = utlandsk
            belopp_original = f"{normaliserat} {utlandsk}"
            # Utan slutpunkt: anmärkningar fogas ihop med "; " och bäddas in
            # i assistentens svar — en punkt inuti leden gav ".);".
            anmarkningar.append(
                f"Beloppet är i {utlandsk} ({normaliserat}) och har inte räknats om "
                "till kronor, granska och för in det omräknade beloppet"
            )
        else:
            falt["brutto"] = normaliserat
    else:
        anmarkningar.append("Inget totalbelopp gick att läsa ur mejlet")

    moms = _MOMS.search(mejl_text)
    if moms and valuta == "SEK":
        falt["momssats"] = moms.group(1)

    datum = _DATUM.search(mejl_text)
    if datum:
        falt["datum"] = datum.group(1)

    if avsandare.strip():
        falt["motpart"] = avsandare.strip()
    else:
        # Uppladdad fil — ingen avsändare. Första raden som inte är en
        # dokumentrubrik och inte bär siffror är nästan alltid butiksnamnet.
        # Heuristik, inte gissning i grindens mening: fel butiksnamn är
        # synligt och rättbart, ett påhittat belopp är det inte.
        for rad in mejl_text.splitlines():
            rensad = rad.strip()
            if not rensad or re.search(r"\d", rensad):
                continue
            if re.match(r"(?i)^(kvitto|receipt|faktura|invoice|orderbekräftelse)\b", rensad):
                continue
            falt["motpart"] = rensad
            break

    # Kvitton är utlägg — riktningen är alltid kostnad i den här produkten.
    falt["riktning"] = "kostnad"

    if _OBETALD.search(mejl_text):
        falt["betalstatus"] = "obetald"
    elif _BETALD.search(mejl_text):
        falt["betalstatus"] = "betald"

    for monster, kategori in _KATEGORIORD:
        if re.search(monster, mejl_text):
            falt["kategori"] = kategori
            break

    return DeterministiskAvlasning(
        falt=falt,
        valuta=valuta,
        belopp_original=belopp_original,
        anmarkning="; ".join(anmarkningar),
    )
