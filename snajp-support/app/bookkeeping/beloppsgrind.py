"""INV-BOOK-003: varje krontal i chattsvaret ska komma från ett verktyg.

## Varför grinden finns

Resten av modulen vilar på EN regel: modellen läser, koden räknar. Avläsningen
håller den regeln genom att modellen aldrig får skriva ett belopp på en
debetrad (`kontoplan.bygg_inkopsverifikat`), och periodrapporten håller den
genom att summorna räknas i `math.py`.

Chatten bryter formen: där formulerar modellen ett SVAR i ord, och ord kan
innehålla siffror. Ett svar som lyder "du har 3 120 kr i utgående moms" när
verktyget sa 3 125,00 är en felaktig siffra i en momsdeklaration, levererad med
samma säkra ton som en riktig.

Grinden jämför därför svarets belopp mot de belopp turens verktyg faktiskt
returnerade. Den kontrollerar inte om svaret är RIMLIGT — den kontrollerar om
talen är HÄMTADE. Det är samma sorts fråga som `leads/grounding_gate.py`
ställer om säljmejlens siffror, och implementationen är egen: den här handlar om
kronbelopp med svensk skrivning, inte om påståenden i ett mejl.

## Vad den fångar, och vad den inte fångar

Fångar: belopp med valutamarkör ("1 250 kr", "1250 SEK", "12 kronor") och
belopp skrivna i pengaform ("1 250,00", "1250.00", "12 345").

Fångar INTE, och det är känt och accepterat:

  * Ett tal utan valutamarkör och utan decimaler, t.ex. "momsen är 3125".
    Regeln som skulle fånga det fångar också kontonummer, årtal, antal och
    procentsatser, och en grind som larmar på "konto 2611" lär användaren att
    ignorera den. Systemprompten säger i stället uttryckligen att belopp ska
    skrivas med "kr".
  * Ett tal som RÅKAR finnas i verktygsresultatet av annan anledning.
    Datumet "2026-08-01" bidrar med 2026, så "2026 kr" skulle passera. Att
    plocka isär varje verktygsresultat efter fälttyp hade gjort grinden
    beroende av varje verktygs form, och därmed tyst fel den dag ett verktyg
    ändrar sitt schema.

Taket är alltså detsamma som grounding_gate dokumenterar för sin
kvalificerardrift: grinden är en spärr mot uppfunna tal, inte ett bevis för
korrekthet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

#: Belopp med valutamarkör. Markören är det som gör talet till ett PÅSTÅENDE om
#: pengar, och det är sådana påståenden som måste vara hämtade.
_MED_VALUTA = re.compile(
    r"(?P<tal>\d[\d\s .,]*?)\s*(?:kr\b|kronor\b|SEK\b)",
    re.IGNORECASE,
)

#: Belopp skrivet i pengaform utan markör: tusenavgränsat, eller med exakt två
#: decimaler. "1 250,00", "1250.00", "12 345". Två decimaler är öreskrivning,
#: och tusenavgränsning skriver man sällan om något annat än pengar.
_PENGAFORM = re.compile(
    r"(?<![\d.,])(?:"
    r"\d{1,3}(?:[\s ]\d{3})+(?:[.,]\d{1,2})?"
    r"|\d+[.,]\d{2}"
    r")(?![\d.,])"
)

#: Varje tal alls. Används BARA på verktygsresultat, där allt som står är
#: hämtat per definition.
_TAL = re.compile(r"\d[\d\s ]*(?:[.,]\d+)?")

#: Procent är inte ett belopp. "25 %" ska inte behöva vara grundad.
_PROCENT_EFTER = re.compile(r"\s*%")


@dataclass(frozen=True)
class Belopp:
    """Ett belopp som det STOD, och som det räknas."""

    rat: str
    normaliserat: str
    span: tuple[int, int]


@dataclass(frozen=True)
class Beloppsverdikt:
    ogrundade: tuple[Belopp, ...]

    @property
    def ok(self) -> bool:
        return not self.ogrundade

    def as_report(self) -> list[str]:
        return [
            f"Beloppet {b.rat!r} finns inte i något verktygsresultat från den här turen."
            for b in self.ogrundade
        ]


def normalisera(rat: str) -> str | None:
    """Talet som en kanonisk decimalsträng, eller None om det inte går att läsa.

    Svensk skrivning blandar mellanslag som tusenavgränsare med både komma och
    punkt som decimaltecken, och engelsk gör tvärtom. Regeln nedan är den enda
    som håller för båda utan att gissa: det SISTA separatortecknet är
    decimaltecken om det följs av en eller två siffror, annars är alla
    separatorer tusenavgränsare.

    `Decimal` och inte float — hela modulens premiss.
    """
    text = rat.strip().replace(" ", "").replace(" ", "")
    if not text or not any(c.isdigit() for c in text):
        return None

    sista_sep = max(text.rfind(","), text.rfind("."))
    if sista_sep == -1:
        heltal, decimaler = text, ""
    else:
        svans = text[sista_sep + 1 :]
        if len(svans) in (1, 2) and svans.isdigit():
            heltal, decimaler = text[:sista_sep], svans
        else:
            heltal, decimaler = text, ""

    heltal = heltal.replace(",", "").replace(".", "")
    if not heltal.isdigit():
        return None

    try:
        varde = Decimal(f"{heltal}.{decimaler or '0'}")
    except InvalidOperation:
        return None
    # Två decimaler: 1250 och 1250,00 är samma belopp och ska jämföras lika.
    return str(varde.quantize(Decimal("0.01")))


def _belopp_i_svar(text: str) -> list[Belopp]:
    funna: dict[tuple[int, int], Belopp] = {}

    for match in _MED_VALUTA.finditer(text):
        rat = match.group("tal").strip()
        normaliserat = normalisera(rat)
        if normaliserat is not None:
            funna[match.span("tal")] = Belopp(rat, normaliserat, match.span("tal"))

    for match in _PENGAFORM.finditer(text):
        if _PROCENT_EFTER.match(text, match.end()):
            continue
        # Överlappar den redan ett valutamarkerat fynd är det samma belopp.
        if any(s <= match.start() and match.end() <= e for s, e in funna):
            continue
        normaliserat = normalisera(match.group(0))
        if normaliserat is not None:
            funna[match.span()] = Belopp(match.group(0), normaliserat, match.span())

    return [funna[nyckel] for nyckel in sorted(funna)]


def grundade_belopp(verktygsresultat: list[str]) -> set[str]:
    """Allt som går att läsa som ett tal i turens verktygssvar.

    Generöst med flit: verktygsresultaten är per definition hämtade, och en
    snålare avläsning här hade fällt sanna svar. Grinden ska stoppa uppfunna
    tal, inte försvåra riktiga.
    """
    grundade: set[str] = set()
    for resultat in verktygsresultat:
        for match in _TAL.finditer(resultat or ""):
            normaliserat = normalisera(match.group(0))
            if normaliserat is not None:
                grundade.add(normaliserat)
    return grundade


def check_belopp(svar: str, verktygsresultat: list[str]) -> Beloppsverdikt:
    """INV-BOOK-003. Fäller om svaret bär ett belopp turen inte hämtat."""
    grundade = grundade_belopp(verktygsresultat)
    ogrundade = tuple(b for b in _belopp_i_svar(svar) if b.normaliserat not in grundade)
    return Beloppsverdikt(ogrundade=ogrundade)
