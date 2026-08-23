"""BAS-kontoplanen som DATA, och verifikatbygget som KOD.

## Arbetsdelningen

Modellen väljer KATEGORI ("det här är ett drivmedelskvitto"). Koden slår upp
kontot och bygger konteringsraderna. Följden är att verifikatet balanserar av
konstruktion — det finns ingen kodväg där modellen får skriva ett belopp på en
debetrad. Samma princip som `leads_tools.py`: modellen väljer vad, koden gör.

## Om delmängden

ponytail: ~30 konton för enskild firma och litet AB, inte hela BAS (drygt
tusen konton). Kategorierna nedan täcker det ett litet bolags kvittohög
faktiskt innehåller. Taket är känt: saknas en kategori ska den LÄGGAS TILL som
en datarad här — den ska inte gissas fram av modellen vid körning, och
`foresla_konto` returnerar därför None i stället för ett närliggande konto.

Kontonumren och kontonamnen följer BAS-kontoplanens standarduppställning.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .math import Konteringsrad, moms_fran_brutto, netto_fran_brutto, till_decimal, till_momssats


@dataclass(frozen=True)
class Konto:
    nummer: str
    namn: str
    #: "tillgang" | "skuld" | "eget_kapital" | "intakt" | "kostnad"
    typ: str


KONTOPLAN: dict[str, Konto] = {
    k.nummer: k
    for k in (
        # Tillgångar
        Konto("1510", "Kundfordringar", "tillgang"),
        Konto("1910", "Kassa", "tillgang"),
        Konto("1930", "Företagskonto / checkräkningskonto", "tillgang"),
        # Eget kapital (enskild firma)
        Konto("2010", "Eget kapital", "eget_kapital"),
        Konto("2013", "Egna uttag", "eget_kapital"),
        Konto("2018", "Egna insättningar", "eget_kapital"),
        # Skulder och moms
        Konto("2440", "Leverantörsskulder", "skuld"),
        Konto("2611", "Utgående moms på försäljning inom Sverige, 25 %", "skuld"),
        Konto("2621", "Utgående moms på försäljning inom Sverige, 12 %", "skuld"),
        Konto("2631", "Utgående moms på försäljning inom Sverige, 6 %", "skuld"),
        Konto("2641", "Ingående moms", "tillgang"),
        Konto("2650", "Redovisningskonto för moms", "skuld"),
        # Intäkter
        Konto("3001", "Försäljning inom Sverige, 25 % moms", "intakt"),
        Konto("3002", "Försäljning inom Sverige, 12 % moms", "intakt"),
        Konto("3003", "Försäljning inom Sverige, 6 % moms", "intakt"),
        Konto("3004", "Försäljning inom Sverige, momsfri", "intakt"),
        # Kostnader
        Konto("4010", "Inköp av material och varor", "kostnad"),
        Konto("5010", "Lokalhyra", "kostnad"),
        Konto("5410", "Förbrukningsinventarier", "kostnad"),
        Konto("5420", "Programvaror", "kostnad"),
        Konto("5611", "Drivmedel för personbilar", "kostnad"),
        Konto("5810", "Biljetter", "kostnad"),
        Konto("5831", "Kost och logi i Sverige", "kostnad"),
        Konto("5910", "Annonsering", "kostnad"),
        Konto("6071", "Representation, avdragsgill", "kostnad"),
        Konto("6110", "Kontorsmateriel", "kostnad"),
        Konto("6212", "Mobiltelefon", "kostnad"),
        Konto("6230", "Datakommunikation", "kostnad"),
        Konto("6310", "Företagsförsäkringar", "kostnad"),
        Konto("6540", "IT-tjänster", "kostnad"),
        Konto("6570", "Bankkostnader", "kostnad"),
        Konto("6990", "Övriga externa kostnader", "kostnad"),
        # Resultat
        Konto("8999", "Årets resultat", "eget_kapital"),
    )
}

#: Kategori -> kostnadskonto. Kategorinamnen är det modellen får välja bland,
#: och de är medvetet vardagliga: modellen ska känna igen ett kvitto, inte
#: kunna BAS utantill.
KOSTNADSKATEGORIER: dict[str, str] = {
    "varuinkop": "4010",
    "lokalhyra": "5010",
    "forbrukningsinventarier": "5410",
    "programvara": "5420",
    "drivmedel": "5611",
    "biljett": "5810",
    "kost_och_logi": "5831",
    "annonsering": "5910",
    "representation": "6071",
    "kontorsmateriel": "6110",
    "mobiltelefon": "6212",
    "datakommunikation": "6230",
    "forsakring": "6310",
    "it_tjanst": "6540",
    "bankkostnad": "6570",
    "ovrig_extern_kostnad": "6990",
}

#: Momssats -> konto för UTGÅENDE moms (försäljning).
UTGAENDE_MOMSKONTO: dict[Decimal, str] = {
    Decimal("0.25"): "2611",
    Decimal("0.12"): "2621",
    Decimal("0.06"): "2631",
}

#: Momssats -> intäktskonto.
FORSALJNINGSKONTO: dict[Decimal, str] = {
    Decimal("0.25"): "3001",
    Decimal("0.12"): "3002",
    Decimal("0.06"): "3003",
    Decimal("0"): "3004",
}

#: All ingående moms samlas på ett konto, oavsett sats. Det är BAS-praxis och
#: inte en förenkling från vår sida.
INGAENDE_MOMSKONTO = "2641"


class OkantKontoError(KeyError):
    """En kategori eller ett konto som inte finns i delmängden ovan.

    Kastas hellre än att falla tillbaka på ett närliggande konto: ett kvitto
    på fel konto är svårare att upptäcka än ett kvitto som stannade i kön.
    """


def foresla_konto(kategori: str) -> str | None:
    """Kostnadskontot för en kategori, eller None.

    None och inte en gissning — se OkantKontoError ovan. Anroparen (grinden)
    gör None till `granska_manuellt`.
    """
    return KOSTNADSKATEGORIER.get(kategori)


def kontonamn(nummer: str) -> str:
    konto = KONTOPLAN.get(nummer)
    if konto is None:
        raise OkantKontoError(f"konto {nummer} finns inte i kontoplanen")
    return konto.namn


def bygg_inkopsverifikat(
    *,
    brutto: object,
    momssats: object,
    kategori: str,
    betalkonto: str = "1930",
    text: str = "",
) -> list[Konteringsrad]:
    """Ett kvitto: kostnad + ingående moms i debet, betalning i kredit.

    Balanserar av konstruktion — kreditsidan är bruttot, debetsidan är netto
    plus den moms som räknats UR samma brutto. Se `netto_fran_brutto` för
    varför den subtraktionen inte får bli en egen division.
    """
    konto = foresla_konto(kategori)
    if konto is None:
        raise OkantKontoError(f"kategori {kategori!r} saknas i KOSTNADSKATEGORIER")
    if betalkonto not in KONTOPLAN:
        raise OkantKontoError(f"betalkonto {betalkonto} finns inte i kontoplanen")

    b = till_decimal(brutto, falt="brutto")
    sats = till_momssats(momssats)
    moms = moms_fran_brutto(b, sats)
    netto = netto_fran_brutto(b, sats)

    rader = [Konteringsrad(konto, debet=netto, text=text or kontonamn(konto))]
    if moms:
        rader.append(Konteringsrad(INGAENDE_MOMSKONTO, debet=moms, text="Ingående moms"))
    rader.append(Konteringsrad(betalkonto, kredit=b, text=kontonamn(betalkonto)))
    return rader


def bygg_forsaljningsverifikat(
    *,
    brutto: object,
    momssats: object,
    mottagarkonto: str = "1930",
    text: str = "",
) -> list[Konteringsrad]:
    """En faktura eller ett kontantköp: betalning i debet, intäkt och
    utgående moms i kredit."""
    if mottagarkonto not in KONTOPLAN:
        raise OkantKontoError(f"mottagarkonto {mottagarkonto} finns inte i kontoplanen")

    b = till_decimal(brutto, falt="brutto")
    sats = till_momssats(momssats)
    moms = moms_fran_brutto(b, sats)
    netto = netto_fran_brutto(b, sats)
    intaktskonto = FORSALJNINGSKONTO[sats]

    rader = [Konteringsrad(mottagarkonto, debet=b, text=kontonamn(mottagarkonto))]
    rader.append(Konteringsrad(intaktskonto, kredit=netto, text=text or kontonamn(intaktskonto)))
    if moms:
        rader.append(
            Konteringsrad(UTGAENDE_MOMSKONTO[sats], kredit=moms, text="Utgående moms")
        )
    return rader
