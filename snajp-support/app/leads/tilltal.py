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
    if not bokstaver or not all(t.isupper() for t in bokstaver) or " " not in namn.strip():
        # Ett ensamt versalord ("XLS", "IKEA") är en förkortning eller ett
        # varumärke, inte registrets versaler.
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


#: Prepositioner där namnet blir "er" ("nytta för X" → "nytta för er").
_PREP_ER = {"hos", "för", "till", "med", "åt", "inom", "av", "om", "på", "från", "mot"}
#: Ord där "som X" syftar på bolaget som ett ett-ord ("företag som ert").
_ETT_ORD = {"företag", "bolag", "byggföretag", "byggbolag", "teknikbolag"}
#: Ord efter vilka namnet står som subjekt ("Jag tror X skulle" → "ni").
_FORE_SUBJEKT = {"att", "tror", "tycker", "och", "men", "när", "eftersom", "då", "så"}


def _pronomen(fore: str) -> tuple[int, str]:
    """(antal tecken att stryka bakåt, ersättning) för ett omnämnande som
    ska bli ni/er, avgjort av texten närmast före namnet. Okänt läge (namnet
    som objekt efter ett verb, "ni har bildat X") blir "företaget": "ni" där
    gav "ni har bildat ni" i utkastet till Vinovo 2026-10-07."""
    pa = re.search(r"\b(?:ni|du)(\s+(?:på|hos|inom)\s+)$", fore, re.IGNORECASE)
    if pa:
        # "ni/du på X hjälper" → "ni/du hjälper": prepositionen stryks med namnet.
        return len(pa.group(1)), ""
    ord_ = re.findall(r"[\wåäöÅÄÖ]+", fore[-40:])
    sista = ord_[-1].lower() if ord_ else ""
    if not fore.strip() or re.search(r"[.!?:\n]\s*$", fore):
        return 0, "Ni"
    if sista == "som":
        return 0, "ert" if len(ord_) > 1 and ord_[-2].lower() in _ETT_ORD else "ni"
    if sista in _PREP_ER:
        return 0, "er"
    if sista in _FORE_SUBJEKT:
        return 0, "ni"
    return 0, "företaget"


def ett_bolagsnamn(subject: str, body: str, namn: str | None) -> tuple[str, str]:
    """Bolagsnamnet står EN gång i hela mejlet (Sebbe 2026-10-07: "Brainy
    Energy Group Nordic" stod fyra gånger i ett mejl på sex meningar).

    Står namnet i ämnesraden blir varje omnämnande i brödtexten ni/er; annars
    behålls det första i brödtexten. Ägandeform ("Vinovos") lämnas, eftersom
    er/ert/era kräver ordets genus. Kortar namnet först (korta_bolagsnamn),
    annars blev "Investbygg Sverige AB" till "ni AB"."""
    kort = kortnamn(namn)
    if not body or not kort:
        return subject, body
    subject, body = korta_bolagsnamn(subject or "", namn), korta_bolagsnamn(body, namn)
    # Ägandeform ("EC:s", "Volvo's") räknas inte, men ett kolon gör det:
    # ämnet "EC Utbildning: nya LIA-företag" missades annars.
    monster = re.compile(
        rf"(?<![\wåäöÅÄÖ]){re.escape(kort)}(?![\wåäöÅÄÖ])(?![:'’]s\b)", re.IGNORECASE
    )
    behall = 0 if monster.search(subject or "") else 1
    delar: list[str] = []
    pos = 0
    for i, traff in enumerate(monster.finditer(body)):
        if i < behall:
            continue
        fore = "".join(delar) + body[pos : traff.start()]
        stryk, ersatt = _pronomen(fore)
        delar = [fore[: len(fore) - stryk] + ersatt]
        pos = traff.end()
    ny = "".join(delar) + body[pos:]
    # "Prestigo är verksamt" blev "ni är verksamt": predikatet följer ni.
    ny = re.sub(r"\b([Nn]i är) verksamt\b", r"\1 verksamma", ny)
    return subject, ny


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

    brod = (
        "Hej Tomas,\n\nJag såg att Brainy Energy utvecklar energilösningar.\n\n"
        "Snajp hjälper företag som Brainy Energy att hitta kunder.\n\n"
        "Jag tror att Brainy Energy skulle ha nytta av leads. Brainy Energy är rätt."
    )
    _, ny = ett_bolagsnamn("Energilösningar", brod, "Brainy Energy AB")
    assert ny == (
        "Hej Tomas,\n\nJag såg att Brainy Energy utvecklar energilösningar.\n\n"
        "Snajp hjälper företag som ert att hitta kunder.\n\n"
        "Jag tror att ni skulle ha nytta av leads. Ni är rätt."
    ), ny
    _, ny = ett_bolagsnamn("Leads för Brainy Energy", brod, "Brainy Energy AB")
    assert "Brainy Energy" not in ny and ny.startswith("Hej Tomas,\n\nJag såg att ni utvecklar")
    _, ny = ett_bolagsnamn("Ämne", "Jag såg X. Jag såg att ni på XLS hjälper och nytta för XLS.", "XLS AB")
    assert ny == "Jag såg X. Jag såg att ni på XLS hjälper och nytta för er.", ny
    _, ny = ett_bolagsnamn("XLS", "Jag såg att ni på XLS hjälper.", "XLS AB")
    assert ny == "Jag såg att ni hjälper.", ny
    _, ny = ett_bolagsnamn("Ämne", "Volvo och Volvos lastbilar.", "Volvo AB")
    assert ny == "Volvo och Volvos lastbilar.", "ägandeform lämnas"
    # De tre fynden i torrkörningen mot de riktiga utkasten 2026-10-07.
    amne, ny = ett_bolagsnamn(
        "Nya uppdrag – Investbygg Sverige AB",
        "Jag såg att Investbygg Sverige AB tar uppdrag. Jag tror Investbygg Sverige AB vill.",
        "Investbygg Sverige AB",
    )
    assert (amne, ny) == ("Nya uppdrag – Investbygg Sverige", "Jag såg att ni tar uppdrag. Jag tror ni vill."), ny
    _, ny = ett_bolagsnamn("Leads för Countivo", "Jag såg att du på Countivo erbjuder redovisning.", "Countivo")
    assert ny == "Jag såg att du erbjuder redovisning.", ny
    _, ny = ett_bolagsnamn("Vinovo och er etablering", "Jag såg att ni nyligen bildat Vinovo med målet.", "Vinovo AB")
    assert ny == "Jag såg att ni nyligen bildat företaget med målet.", ny
    _, ny = ett_bolagsnamn("EC Utbildning: nya LIA-företag", "Jag såg att EC Utbildning växer.", "EC Utbildning AB")
    assert ny == "Jag såg att ni växer.", ny
    _, ny = ett_bolagsnamn("Ämne", "EC:s kurser och EC.", "EC AB")
    assert ny == "EC:s kurser och EC.", "ägandeform räknas inte"
    _, ny = ett_bolagsnamn("Prestigo och nya projekt", "Jag ser att Prestigo är verksamt i Göteborg.", "Prestigo")
    assert ny == "Jag ser att ni är verksamma i Göteborg.", ny
    print("ett bolagsnamn: ok")

    assert ratta_tilltal("Hej Mikael,\nJag såg", "Jonas Ek") == "Hej Jonas,\nJag såg"
    assert ratta_tilltal("Hej [VD:ns förnamn],\nText", "Anna Berg") == "Hej Anna,\nText"
    assert ratta_tilltal("Hej [VD:ns förnamn],\nText", None) == "Hej,\nText"
    assert ratta_tilltal("Hej Jonas,\nText", "Jonas Ek") == "Hej Jonas,\nText"
    assert ratta_tilltal("Hej,\nText", "Jonas Ek") == "Hej Jonas,\nText"
    assert ratta_tilltal("Jag såg att ni växer.", "Jonas") == "Jag såg att ni växer."
    print("tilltal: ok")


if __name__ == "__main__":
    demo()
