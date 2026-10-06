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


#: Bolagsformer som hör hemma i registret men inte i ett mejl. Utkasten
#: 2026-10-07 hade "Bygg- och renoveringsprojekt i Göteborg – Roy Johnsson
#: Linnéstaden Bygg & Service Aktiebolag" som ämnesrad.
_BOLAGSFORM = r"(?:aktiebolag|ab|\(publ\)|publ|handelsbolag|hb|kommanditbolag|kb)"
_FORM_SIST = re.compile(rf"(?:[\s,]+{_BOLAGSFORM})+\s*$", re.IGNORECASE)
_FORM_FORST = re.compile(r"^(?:ab|aktiebolaget)\s+", re.IGNORECASE)


def _ur_versaler(namn: str) -> str:
    """Registrets VERSALNAMN ("HÄRLANDA FOG & BYGGSERVICE") blir vanlig
    skrift. Bara när hela namnet är versaler; ord på två bokstäver och ord
    med siffror eller bindestreck (förkortningar som "JM", "EK-RA") lämnas."""
    bokstaver = [t for t in namn if t.isalpha()]
    if not bokstaver or not all(t.isupper() for t in bokstaver):
        return namn
    return " ".join(
        o.capitalize() if len(o) > 2 and o.isalpha() else o for o in namn.split(" ")
    )


def kortnamn(namn: str | None) -> str:
    """Namnet ett mejl kallar bolaget: utan bolagsform, i vanlig skrift.
    Blir inget kvar returneras originalet."""
    original = str(namn or "").strip()
    kort = _FORM_FORST.sub("", _FORM_SIST.sub("", original)).strip(" ,")
    return _ur_versaler(kort) if kort else original


def korta_bolagsnamn(text: str, namn: str | None) -> str:
    """Byter bolagets registernamn mot kortnamnet i en färdig text, oavsett
    skiftläge och om bolagsformen står med. Modellen läser registernamnet i
    researchen och skriver det ibland ordagrant trots uppdraget."""
    kort = kortnamn(namn)
    if not text or not kort:
        return text
    monster = re.compile(
        rf"(?:\bab\s+)?(?P<namn>{re.escape(kort)})(?:[\s,]+{_BOLAGSFORM}(?![\wåäö]))*",
        re.IGNORECASE,
    )
    # Modellens egen stavning av namnet står kvar ("Tolered Snickeri & Bygg");
    # bara bolagsformen tas bort, och versaler blir vanlig skrift.
    return monster.sub(lambda m: _ur_versaler(m.group("namn")), text)


def demo() -> None:
    assert kortnamn("Roy Johnsson Linnéstaden Bygg & Service Aktiebolag") == (
        "Roy Johnsson Linnéstaden Bygg & Service"
    )
    assert kortnamn("HÄRLANDA FOG & BYGGSERVICE AB") == "Härlanda Fog & Byggservice"
    assert kortnamn("Volvo AB (publ)") == "Volvo"
    assert kortnamn("AB Volvo") == "Volvo"
    assert kortnamn("EK-RA BYGG & ENTREPRENAD AB") == "EK-RA Bygg & Entreprenad"
    assert kortnamn("AB") == "AB"
    assert korta_bolagsnamn(
        "Hej,\nJag såg att Tolered Snickeri & Bygg AB gör kök.", "Tolered snickeri & bygg AB"
    ) == "Hej,\nJag såg att Tolered Snickeri & Bygg gör kök."
    assert korta_bolagsnamn(
        "Snabb service – Härlanda Fog & Byggservice AB", "HÄRLANDA FOG & BYGGSERVICE AB"
    ) == "Snabb service – Härlanda Fog & Byggservice"
    assert korta_bolagsnamn("Abbe på Volvo Abisko", "Volvo AB") == "Abbe på Volvo Abisko"
    print("kortnamn: ok")

    assert ratta_tilltal("Hej Mikael,\nJag såg", "Jonas Ek") == "Hej Jonas,\nJag såg"
    assert ratta_tilltal("Hej [VD:ns förnamn],\nText", "Anna Berg") == "Hej Anna,\nText"
    assert ratta_tilltal("Hej [VD:ns förnamn],\nText", None) == "Hej,\nText"
    assert ratta_tilltal("Hej Jonas,\nText", "Jonas Ek") == "Hej Jonas,\nText"
    assert ratta_tilltal("Hej,\nText", "Jonas Ek") == "Hej Jonas,\nText"
    assert ratta_tilltal("Jag såg att ni växer.", "Jonas") == "Jag såg att ni växer."
    print("tilltal: ok")


if __name__ == "__main__":
    demo()
