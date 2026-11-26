"""Fälten i CRM:et efter svensk standard: en funktion per fält, en sanning.

Leads-koden normaliserar organisationsnummer på sex olika sätt som inte är
överens om sekelprefix och personnummer (docs/crm/underlag/snajp-01, avsnitt
5). CRM:et har en: `orgnr`. Den ger tio siffror utan bindestreck som nyckel,
formen NNNNNN-NNNN för visning, och säger om numret är en enskild firmas
personnummer.

Varje funktion tar vad källsystemet råkar skicka (sträng, tal, None) och ger
ett rent värde eller None. Ett värde som inte går att tolka höjer `FaltFel`
med en kod som API:t lämnar ut. Synken hoppar då över fältet, inte posten:
en kund med ett felskrivet telefonnummer ska fortfarande bli en kund.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from urllib.parse import urlparse

from ..leads import orgnr as _orgnr
from ..leads.discovery import _PRIVATA_DOMÄNER
from ..leads.upptagna import nyckel as namnnyckel

__all__ = [
    "FaltFel",
    "bolagsform",
    "datum",
    "doman_ar_privat",
    "epost",
    "heltal",
    "momsnr",
    "momsnr_ur_orgnr",
    "namnnyckel",
    "orgnr",
    "postnr",
    "sni",
    "sni_visning",
    "telefon",
    "text",
    "webbplats",
]


class FaltFel(ValueError):
    """Ett värde som inte går att tolka. `kod` är maskinläsbar och stabil."""

    def __init__(self, kod: str, varde: object = None) -> None:
        super().__init__(kod)
        self.kod = kod
        self.varde = varde


def text(varde: object, *, max_langd: int = 500) -> str | None:
    if varde is None:
        return None
    ut = re.sub(r"\s+", " ", str(varde)).strip()
    return ut[:max_langd] or None


# -- Organisationsnummer och momsnummer -------------------------------------

_MOMS_SE = re.compile(r"^SE(\d{10})01$")
_SEKEL = ("16", "18", "19", "20")


def orgnr(varde: object) -> tuple[str | None, str | None, bool]:
    """(visning, nyckel, enskild_firma).

    Godtar `556824-9022`, `5568249022`, `16556824-9022`, `SE556824902201` och
    en enskild firmas personnummer med eller utan sekel. Kontrollsiffran
    räknas med Luhn. Tredje siffran under 2 betyder personnummer: funktionen
    säger det, och anroparen avgör vad som sparas. CRM:et sparar det inte
    (`adaptrar.mappa`, beslutet 2026-11-23 om listimporten).
    """
    ra = text(varde, max_langd=40)
    if not ra:
        return None, None, False
    kompakt = re.sub(r"[\s.\-–]", "", ra).upper()
    moms = _MOMS_SE.match(kompakt)
    siffror = moms.group(1) if moms else kompakt
    if not siffror.isdigit():
        raise FaltFel("orgnr_ogiltigt", ra)
    if len(siffror) == 12 and siffror[:2] in _SEKEL:
        siffror = siffror[2:]
    if len(siffror) != 10:
        raise FaltFel("orgnr_fel_langd", ra)
    if not _orgnr._luhn_stammer(siffror):
        raise FaltFel("orgnr_kontrollsiffra", ra)
    return f"{siffror[:6]}-{siffror[6:]}", siffror, int(siffror[2]) < 2


def momsnr_ur_orgnr(nyckel: str | None) -> str | None:
    """Svenskt momsregistreringsnummer: SE, organisationsnumret och 01."""
    return f"SE{nyckel}01" if nyckel else None


_MOMS_EU = re.compile(r"^[A-Z]{2}[A-Z0-9+*]{2,12}$")


def momsnr(varde: object) -> str | None:
    ra = text(varde, max_langd=40)
    if not ra:
        return None
    kompakt = re.sub(r"[\s.\-]", "", ra).upper()
    if kompakt.startswith("SE"):
        traff = _MOMS_SE.match(kompakt)
        if not traff or not _orgnr._luhn_stammer(traff.group(1)):
            raise FaltFel("momsnr_ogiltigt", ra)
        return kompakt
    if not _MOMS_EU.match(kompakt):
        raise FaltFel("momsnr_ogiltigt", ra)
    return kompakt


# -- Bolagsform och bransch --------------------------------------------------

#: SCB:s och Skatteverkets tvåsiffriga kod för juridisk form till den
#: förkortning svenska system visar (docs/crm/underlag/svensk-01, avsnitt 3.1).
#: Juridisk form går INTE att läsa ur organisationsnumret (SKV 709), så den
#: kommer alltid från källan.
_FORM_FOR_KOD = {
    "10": "EF", "21": "Enkelt bolag", "31": "HB", "41": "AB", "42": "AB", "43": "SE", "49": "AB",
    "51": "EK", "53": "BRF", "61": "Ideell förening", "62": "Samfällighet", "63": "Trossamfund",
    "71": "Stiftelse", "72": "Stiftelse", "81": "Stat", "82": "Kommun", "83": "Kommunalförbund",
    "84": "Region", "91": "Dödsbo", "93": "Sparbank", "96": "Utländskt bolag",
}
_FORM_FOR_NAMN = {
    "ab": "AB", "aktiebolag": "AB", "aktiebolag publ": "AB", "ab publ": "AB", "publikt aktiebolag": "AB",
    "privat aktiebolag": "AB", "bankaktiebolag": "AB", "forsakringsaktiebolag": "AB", "ovriga aktiebolag": "AB",
    "limited company": "AB", "limited liability company": "AB",
    "hb": "HB", "handelsbolag": "HB", "kb": "KB", "kommanditbolag": "KB",
    "ef": "EF", "enskild firma": "EF", "enskild naringsidkare": "EF", "enskild naringsverksamhet": "EF",
    "fysisk person": "EF", "sole proprietorship": "EF", "sole trader": "EF",
    "ek": "EK", "ek for": "EK", "ekonomisk forening": "EK",
    "brf": "BRF", "bostadsrattsforening": "BRF",
    "ideell forening": "Ideell förening", "stiftelse": "Stiftelse", "samfallighet": "Samfällighet",
    "kommun": "Kommun", "region": "Region", "filial": "Filial", "se": "SE", "europabolag": "SE",
    "enkelt bolag": "Enkelt bolag",
}
_TECKEN = str.maketrans("åäöé", "aaoe")


def bolagsform(varde: object) -> str | None:
    """Bolagsformen som svenska system skriver den: AB, HB, KB, EF, EK, BRF.

    Godtar namnet (`Aktiebolag`, `Enskild firma`), förkortningen och SCB:s
    tvåsiffriga kod (`49`). En form som inte känns igen sparas som den står:
    `GmbH` och `Ltd` är inga fel, bara inga svenska former.
    """
    ra = text(varde, max_langd=60)
    if not ra:
        return None
    if ra.isdigit():
        return _FORM_FOR_KOD.get(ra.zfill(2), ra)
    nyckel = re.sub(r"[^a-z0-9 ]+", " ", ra.casefold().translate(_TECKEN))
    return _FORM_FOR_NAMN.get(re.sub(r"\s+", " ", nyckel).strip(), ra)


#: Så många koder bär SCB:s företagsregister per bolag (Bransch1 till Bransch5).
MAX_SNI = 5


def sni(varde: object) -> str | None:
    """SNI-koder utan punkt, huvudnäringen först, åtskilda med komma.

    `62.010`, `62010` och `62 010` är samma kod. Flera koder godtas, åtskilda
    med komma, semikolon eller snedstreck, och högst fem sparas, som i SCB:s
    register. Två till fem siffror per kod: två är huvudgruppen, fem
    detaljgruppen. Vilken version koden hör till (SNI 2007 eller SNI 2025, som
    gäller sedan 8 december 2025) går inte att läsa ur koden och sägs inte här.
    """
    ra = text(varde, max_langd=200)
    if not ra:
        return None
    koder: list[str] = []
    for del_ in re.split(r"[,;/|]", ra):
        kod = re.sub(r"[\s.]", "", del_)
        if not kod:
            continue
        if not (kod.isdigit() and 2 <= len(kod) <= 5):
            raise FaltFel("sni_ogiltig", ra)
        if kod not in koder:
            koder.append(kod)
    return ",".join(koder[:MAX_SNI]) or None


def sni_visning(kod: str | None) -> str:
    """`62010` skrivs `62.010`, som i SCB:s egna exempel."""
    kod = (kod or "").strip()
    return f"{kod[:2]}.{kod[2:]}" if kod.isdigit() and len(kod) > 2 else kod


# -- Kontaktvägar ------------------------------------------------------------


def telefon(varde: object, *, land: str = "SE") -> str | None:
    """E.164. `070-123 45 67` och `0046 70 123 45 67` blir `+46701234567`.

    Ett nummer utan landskod tolkas som svenskt när posten är svensk, annars
    lämnas det som det skrevs med ett plus framför bara om det redan fanns.
    """
    ra = text(varde, max_langd=40)
    if not ra:
        return None
    # "08-123 456 78 (vxl)" och "070 123 45 67 / 08 12 34 56": första numret gäller.
    forsta = re.split(r"[/;,]|\b(?:eller|or)\b", ra)[0]
    plus = forsta.strip().startswith("+")
    siffror = re.sub(r"\D", "", forsta)
    if not siffror:
        raise FaltFel("telefon_ogiltig", ra)
    if plus:
        pass
    elif siffror.startswith("00"):
        siffror = siffror[2:]
    elif siffror.startswith("0") and land == "SE":
        siffror = "46" + siffror[1:]
    elif land == "SE" and siffror.startswith("46") and len(siffror) >= 10:
        pass
    elif land == "SE" and 7 <= len(siffror) <= 9:
        # Abonnentnummer utan riktnummer går inte att ringa: det sparas inte.
        raise FaltFel("telefon_saknar_riktnummer", ra)
    else:
        raise FaltFel("telefon_saknar_landskod", ra)
    # Svenska nummer skrivs ibland +46 (0)70: nollan efter landskoden ska bort.
    if siffror.startswith("460"):
        siffror = "46" + siffror[3:]
    if not 8 <= len(siffror) <= 15:
        raise FaltFel("telefon_ogiltig", ra)
    return "+" + siffror


_EPOST = re.compile(r"^[^@\s<>,;]+@[^@\s<>,;]+\.[a-z]{2,}$", re.I)


def epost(varde: object) -> str | None:
    ra = text(varde, max_langd=320)
    if not ra:
        return None
    # "Anna Berg <anna@bolaget.se>" förekommer i exporter.
    inom = re.search(r"<([^>]+)>", ra)
    adress = (inom.group(1) if inom else ra).strip().lower().removeprefix("mailto:")
    if not _EPOST.match(adress):
        raise FaltFel("epost_ogiltig", ra)
    return adress


def webbplats(varde: object) -> tuple[str | None, str | None]:
    """(adress, domän). `www.bolaget.se/om-oss` ger domänen `bolaget.se`."""
    ra = text(varde, max_langd=500)
    if not ra:
        return None, None
    url = ra if "://" in ra else f"https://{ra}"
    vard = (urlparse(url).hostname or "").lower().removeprefix("www.")
    if "." not in vard or " " in vard:
        raise FaltFel("webbplats_ogiltig", ra)
    return url, vard


def doman_ar_privat(doman: str | None) -> bool:
    """gmail.com, telia.com och liknande säger ingenting om vilket bolag det är."""
    return bool(doman) and doman.lower() in _PRIVATA_DOMÄNER


def postnr(varde: object, *, land: str = "SE") -> str | None:
    ra = text(varde, max_langd=20)
    if not ra:
        return None
    if land != "SE":
        return ra.upper()
    siffror = re.sub(r"\D", "", ra.upper().removeprefix("SE"))
    if len(siffror) != 5:
        raise FaltFel("postnr_ogiltigt", ra)
    return f"{siffror[:3]} {siffror[3:]}"


# -- Tal och datum -----------------------------------------------------------


def heltal(varde: object) -> int | None:
    """`1 234`, `1,234.00`, `1.234,50` och 1234.0 blir 1234."""
    if varde is None or isinstance(varde, bool):
        return None
    if isinstance(varde, (int, float)):
        return int(varde)
    ra = text(varde, max_langd=40)
    if not ra:
        return None
    kompakt = re.sub(r"[\s  ]|kr|sek", "", ra, flags=re.I)
    # Sista skiljetecknet följt av en eller två siffror är decimaler.
    kompakt = re.sub(r"[.,]\d{1,2}$", "", kompakt)
    kompakt = re.sub(r"[.,]", "", kompakt)
    if not re.fullmatch(r"-?\d+", kompakt):
        raise FaltFel("tal_ogiltigt", ra)
    return int(kompakt)


_DATUMFORMAT = ("%Y-%m-%d", "%Y%m%d", "%d/%m/%Y", "%d.%m.%Y", "%Y/%m/%d", "%d-%m-%Y")


def datum(varde: object) -> str | None:
    """ISO 8601-datum. Godtar ISO med klockslag, svenska och europeiska
    skrivsätt och epoktid i millisekunder (HubSpot)."""
    if varde is None or isinstance(varde, bool):
        return None
    if isinstance(varde, datetime):
        return varde.date().isoformat()
    if isinstance(varde, date):
        return varde.isoformat()
    if isinstance(varde, (int, float)) or re.fullmatch(r"\d{11,13}", str(varde).strip()):
        tal = float(varde)
        return datetime.fromtimestamp(tal / 1000 if tal > 1e11 else tal, tz=timezone.utc).date().isoformat()
    ra = text(varde, max_langd=40)
    if not ra:
        return None
    try:
        return datetime.fromisoformat(ra.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        pass
    for fmt in _DATUMFORMAT:
        try:
            return datetime.strptime(ra, fmt).date().isoformat()
        except ValueError:
            continue
    raise FaltFel("datum_ogiltigt", ra)


def tidpunkt(varde: object) -> str | None:
    """ISO 8601 med tidszon, för källsystemets "senast ändrad"."""
    if varde is None or isinstance(varde, bool) or varde == "":
        return None
    try:
        if isinstance(varde, (int, float)) or re.fullmatch(r"\d{10,13}", str(varde).strip()):
            tal = float(varde)
            return datetime.fromtimestamp(tal / 1000 if tal > 1e11 else tal, tz=timezone.utc).isoformat()
        tid = datetime.fromisoformat(str(varde).strip().replace("Z", "+00:00"))
    except (ValueError, OverflowError, OSError):
        raise FaltFel("tidpunkt_ogiltig", varde) from None
    return (tid if tid.tzinfo else tid.replace(tzinfo=timezone.utc)).isoformat()
