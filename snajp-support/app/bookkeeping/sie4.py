"""SIE4 — en fil i stället för fem OAuth-flöden.

## Varför SIE4 och inte API-integrationer

Fortnox, Visma, Bokio, Björn Lundén och Dooer importerar alla SIE. Det är den
svenska standarden för att flytta bokföring mellan system, och den är
oberoende av vilket program kunden råkar ha. Fem API-integrationer hade gett
fem app-registreringar, fem OAuth-flöden, fem uppsättningar hemligheter att
rotera — och samma resultat.

Kostnaden är känd och står här: en fil är inte en synk. Ändras något i
kundens system vet vi inte om det. Det är rätt avvägning så länge vi
FÖRESLÅR och människan för in — se modulens plats i flödet.

## Två formatdetaljer som är lätta att få fel

1. **`#TRANS` har ETT belopp, inte debet och kredit.** Debet är positivt,
   kredit negativt. En kolumnuppdelning som i vår egen `Konteringsrad` finns
   inte i formatet, så konverteringen sker här och ingen annanstans.
2. **Filen är CP437-kodad**, deklarerat med `#FORMAT PC8`. UTF-8 ser rätt ut
   i en texteditor och ger å/ä/ö som frågetecken eller importfel i
   mottagarsystemet — alltså ett fel som upptäcks av kunden, inte av oss.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from .math import Konteringsrad, balans
from .kontoplan import KONTOPLAN

#: SIE-typ 4 = transaktioner med verifikationer. 4I är import, 4E export;
#: vi skriver den gemensamma `#SIETYP 4`.
SIETYP = "4"

#: Kontotyp per BAS-kategori. T=tillgång, S=skuld, K=kostnad, I=intäkt.
_KTYP = {
    "tillgang": "T",
    "skuld": "S",
    "eget_kapital": "S",
    "kostnad": "K",
    "intakt": "I",
}

#: Typografiska tecken CP437 inte har, men som slinker in via klipp och klistra
#: ur ett kvitto eller ett bolagsnamn. Översätts hellre än ersätts med "?".
_TYPOGRAFI = str.maketrans(
    {
        "–": "-",  # en dash
        "—": "-",  # em dash
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "…": "...",
        " ": " ",  # hårt blanksteg
    }
)


class SieExportError(RuntimeError):
    """Något som gör filen felaktig hos mottagaren.

    Kastar, till skillnad från verifieringsgrinden: den som når hit har redan
    passerat grinden, så ett fel här är ett programfel och inte något en
    människa ska granska sig ur.
    """


@dataclass(frozen=True)
class Verifikat:
    serie: str
    nummer: str
    datum: date
    text: str
    rader: tuple[Konteringsrad, ...] = field(default_factory=tuple)


def _sanera(text: str) -> str:
    """Text som säkert går att koda i CP437.

    Ordningen spelar roll: typografiska tecken översätts först, sedan NFC-
    normaliseras strängen så att ett dekomponerat "a + ring" blir "å" (som
    CP437 HAR) i stället för att falla på ringen (som den inte har).
    """
    rensad = unicodedata.normalize("NFC", text.translate(_TYPOGRAFI))
    # ponytail: kvarvarande otecknbara tecken blir "?". Alternativet — att
    # kasta — hade gjort ett grekiskt produktnamn i en kvittorad till ett
    # stoppat bokslut. Ett frågetecken i en verifikationstext är synligt och
    # ofarligt; ett stoppat bokslut är varken.
    return rensad.encode("cp437", errors="replace").decode("cp437")


def _falt(text: str) -> str:
    """Ett citerat SIE-fält. Inbäddade citattecken escapas med bakstreck."""
    return '"' + _sanera(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _datum(d: date) -> str:
    return d.strftime("%Y%m%d")


def _belopp(varde: Decimal) -> str:
    """Två decimaler, punkt som decimaltecken, minus för kredit.

    `quantize` och inte formatsträng: ett Decimal med fler decimaler ska
    avrundas enligt vår egen regel, inte enligt f-strängens.
    """
    return f"{varde.quantize(Decimal('0.01')):f}"


def skriv_sie4(
    *,
    foretagsnamn: str,
    orgnr: str,
    rakenskapsar_start: date,
    rakenskapsar_slut: date,
    verifikat: Sequence[Verifikat],
    genererat: date,
    program: str = "Snajp Bokforing",
    version: str = "1.0",
) -> bytes:
    """Hela filen som bytes, CP437-kodad.

    Returnerar bytes och inte str med flit: en `str` hade kunnat skrivas till
    disk med fel kodning av anroparen, och det felet syns inte förrän kunden
    importerar filen.

    Balansen kontrolleras per verifikat FÖRE skrivning. En obalanserad fil
    importeras inte av mottagarsystemet ändå — men den avvisas då med ett
    meddelande på kundens skärm, i deras program, och det är för sent.
    """
    for ver in verifikat:
        if not ver.rader:
            raise SieExportError(f"verifikat {ver.serie}{ver.nummer} har inga rader")
        diff = balans(ver.rader)
        if diff != Decimal(0):
            raise SieExportError(
                f"verifikat {ver.serie}{ver.nummer} balanserar inte: {diff} kr"
            )

    anvanda_konton = sorted({rad.konto for ver in verifikat for rad in ver.rader})

    rader: list[str] = [
        "#FLAGGA 0",
        f"#PROGRAM {_falt(program)} {_falt(version)}",
        "#FORMAT PC8",
        f"#GEN {_datum(genererat)}",
        f"#SIETYP {SIETYP}",
        f"#FNAMN {_falt(foretagsnamn)}",
        f"#ORGNR {_sanera(orgnr)}",
        f"#RAR 0 {_datum(rakenskapsar_start)} {_datum(rakenskapsar_slut)}",
    ]

    for nummer in anvanda_konton:
        konto = KONTOPLAN.get(nummer)
        namn = konto.namn if konto else nummer
        rader.append(f"#KONTO {nummer} {_falt(namn)}")
        if konto:
            rader.append(f"#KTYP {nummer} {_KTYP[konto.typ]}")

    for ver in verifikat:
        rader.append(
            f"#VER {_falt(ver.serie)} {_falt(ver.nummer)} {_datum(ver.datum)} {_falt(ver.text)}"
        )
        rader.append("{")
        for rad in ver.rader:
            # Debet positivt, kredit negativt — se modulens docstring.
            belopp = rad.debet - rad.kredit
            rader.append(f"\t#TRANS {rad.konto} {{}} {_belopp(belopp)}")
        rader.append("}")

    # CRLF: SIE-filer läses av Windows-program, och en fil med bara LF har
    # fällt importen i minst ett av dem.
    return ("\r\n".join(rader) + "\r\n").encode("cp437", errors="replace")
