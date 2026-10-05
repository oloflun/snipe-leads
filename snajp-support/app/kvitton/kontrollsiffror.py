"""Kontrollsiffror för numren på ett underlag — kod, inte modellens minne.

Organisationsnummer, bankgiro, plusgiro och OCR bär en Luhn-siffra, IBAN en
mod 97-kontroll. En felläst siffra ger nästan alltid en ogiltig
kontrollsiffra, så kontrollen fångar exakt det fel avläsningen är sämst på:
3 som lästs som 8, 1 som 7.

## Vad kontrollen får användas till

Den får BEKRÄFTA en läsning eller visa att den är fel. Den får aldrig VÄLJA
mellan två läsningar ("3 eller 8 — bara 8 ger giltig siffra, alltså 8"). Det
vore att räkna fram ett värde som inte står på underlaget, och prompten
(avsnitt 3.1) förbjuder det. Ett nummer som inte klarar kontrollen blir
`osäker` med flaggan `oläsligt` — se `granskning.py`.
"""

from __future__ import annotations

import re

NUMMERTYPER = ("orgnummer", "bankgiro", "plusgiro", "ocr", "iban", "momsregnummer")


def _siffror(text: str) -> str:
    return re.sub(r"\D", "", text or "")


def luhn_ok(siffror: str) -> bool:
    if not siffror or not siffror.isdigit():
        return False
    summa = 0
    for i, tecken in enumerate(reversed(siffror)):
        tal = int(tecken)
        if i % 2 == 1:
            tal *= 2
            if tal > 9:
                tal -= 9
        summa += tal
    return summa % 10 == 0


def orgnummer_ok(text: str) -> bool:
    """10 siffror (12 med sekelsiffror för enskild firma), Luhn på de tio sista."""
    s = _siffror(text)
    if len(s) == 12:
        s = s[2:]
    return len(s) == 10 and luhn_ok(s)


def bankgiro_ok(text: str) -> bool:
    s = _siffror(text)
    return len(s) in (7, 8) and luhn_ok(s)


def plusgiro_ok(text: str) -> bool:
    s = _siffror(text)
    return 2 <= len(s) <= 8 and luhn_ok(s)


def ocr_ok(text: str) -> bool:
    s = _siffror(text)
    return 2 <= len(s) <= 25 and luhn_ok(s)


def iban_ok(text: str) -> bool:
    rensad = re.sub(r"\s", "", text or "").upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{8,30}", rensad):
        return False
    flyttad = rensad[4:] + rensad[:4]
    tal = "".join(str(int(t, 36)) for t in flyttad)
    return int(tal) % 97 == 1


def momsregnummer_ok(text: str) -> bool | None:
    """Svenskt momsregistreringsnummer: SE + organisationsnummer + 01.

    None för utländska nummer — deras format varierar per land och prövas
    inte här. None är "går inte att avgöra", inte "fel".
    """
    rensad = re.sub(r"[\s-]", "", text or "").upper()
    if not rensad.startswith("SE"):
        return None
    return bool(re.fullmatch(r"SE\d{10}01", rensad)) and orgnummer_ok(rensad[2:12])


def kontrollera(typ: str, nummer: str) -> bool | None:
    """True/False för en känd typ, None när typen inte kan prövas."""
    typ = (typ or "").strip().lower().replace("-", "").replace("_", "")
    if typ in ("orgnummer", "orgnr", "organisationsnummer"):
        return orgnummer_ok(nummer)
    if typ == "bankgiro":
        return bankgiro_ok(nummer)
    if typ == "plusgiro":
        return plusgiro_ok(nummer)
    if typ in ("ocr", "ocrreferens"):
        return ocr_ok(nummer)
    if typ == "iban":
        return iban_ok(nummer)
    if typ in ("momsregnummer", "momsregnr", "vatnummer"):
        return momsregnummer_ok(nummer)
    return None
