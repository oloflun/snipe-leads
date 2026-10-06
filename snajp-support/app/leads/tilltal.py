"""Hälsningsraden i ett utkast avgörs i kod, inte av modellen.

Mätningen av skillvarianterna 2026-10-06 (`scripts/mat_skillvarianter.py`)
fann "Hej Mikael," i två av femton utkast: namnet stod varken i materialet,
i researchen eller i någon prompt, och faktagrinden släppte igenom det
eftersom den bara kontrollerar kundnamn i fasta ramar och siffror. Tio av
femton bar dessutom grundmallens platshållare "Hej [VD:ns förnamn],"
ordagrant.

Regeln: mejlet går bara till VD med en styrkt adress (Antons regel 3), så
mottagarens namn är känt i kod. Står ett annat namn eller en platshållare i
hälsningen ersätts det med VD:ns förnamn; utan känt namn blir det "Hej,".
"""

from __future__ import annotations

import re

_HALSNING = re.compile(
    r"^(?P<ord>Hej|Hejsan|Hallå|God dag|Bästa|Hello|Hi|Dear)(?P<namn>[ \t]+[^\n,!.]{1,60})?(?P<slut>[,!.]?)[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)


def fornamn(namn: str | None) -> str:
    delar = str(namn or "").strip().split()
    return delar[0] if delar else ""


def ratta_tilltal(body: str, mottagare: str | None) -> str:
    """Första hälsningsraden får mottagarens förnamn, eller inget namn alls."""
    text = body or ""
    traff = _HALSNING.search(text[:400])
    if not traff:
        return text
    namn = (traff.group("namn") or "").strip()
    ratt = fornamn(mottagare)
    if namn and ratt and namn.casefold() == ratt.casefold():
        return text
    ny = f"{traff.group('ord')} {ratt}," if ratt else f"{traff.group('ord')},"
    return text[: traff.start()] + ny + text[traff.end():]


def demo() -> None:
    assert ratta_tilltal("Hej Mikael,\nJag såg", "Jonas Ek") == "Hej Jonas,\nJag såg"
    assert ratta_tilltal("Hej [VD:ns förnamn],\nText", "Anna Berg") == "Hej Anna,\nText"
    assert ratta_tilltal("Hej [VD:ns förnamn],\nText", None) == "Hej,\nText"
    assert ratta_tilltal("Hej Jonas,\nText", "Jonas Ek") == "Hej Jonas,\nText"
    assert ratta_tilltal("Hej,\nText", "Jonas Ek") == "Hej Jonas,\nText"
    assert ratta_tilltal("Jag såg att ni växer.", "Jonas") == "Jag såg att ni växer."
    print("tilltal: ok")


if __name__ == "__main__":
    demo()
