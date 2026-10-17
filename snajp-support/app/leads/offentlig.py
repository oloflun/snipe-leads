"""Offentlig sektor och skolor är inte målgruppen, om kunden inte sagt det.

## Varför

Provkörningen 2026-10-05 (Snajp, B2B) gav "Yrkeshögskolan Umeå Kommun"
(umea.se), "Umeå Folkhögskola", "Folkuniversitetet i Umeå" och "Hermods Komvux
i Umeå" som leads. Antons regel 2026-10-06: undvik statliga företag och
kommuner helt, bara privata bolag, om kunden inte uttryckligen nämner dem som
sin målgrupp. Skolor är inte utbildnings- och kursFÖRETAG.

## Två lager

Här ligger det som går att se på KÄND data utan att läsa en sida:
organisationsnumrets första siffra, registrets bolagsform och bolagsnamnet.
Gränsfallen (ett privat bolag som driver en skola, ett statligt ägt
aktiebolag) syns inte här. De bedöms av researchen mot standarduteslutningen
`UTESLUTNING`, som profilen bär och som kräver ett ordagrant citat för att
fälla (app/leads/profil.py).

Profilflaggan `offentlig_sektor` stänger av båda lagren. Den sätts bara när
kunden själv pekat ut offentlig sektor eller skolor som målgrupp.
"""

from __future__ import annotations

import re
from typing import Any

from .orgnr import normalisera

#: Standarduteslutningen i varje profil utan `offentlig_sektor`.
UTESLUTNING = (
    "Offentlig sektor eller skola: kommun, region, myndighet, statligt eller "
    "kommunalt ägt bolag, grundskola, gymnasium, komvux, folkhögskola, "
    "universitet eller högskola"
)

_BOKSTAV = "a-zåäöé"

#: Namnord som pekar ut en offentlig organisation eller en skola. Varje mönster
#: är avgränsat så att det inte träffar inuti ett annat ord: "kommun" får inte
#: träffa "Kommunikation", och "skola" står inte här alls ("Trafikskola",
#: "Ridskola" och "Business School" är privata företag).
_NAMNORD = re.compile(
    rf"(?<![{_BOKSTAV}])(?:"
    rf"kommun(?:en|ens|s)?"
    rf"|landsting(?:et|ets)?"
    rf"|länsstyrelse(?:n|ns)?"
    rf"|myndighet(?:en|ens)?"
    rf"|komvux"
    rf"|folkuniversitetet"
    rf"|universitet(?:et|ets)?"
    rf"|[{_BOKSTAV}]*folkhögskola(?:n|ns)?"
    rf"|[{_BOKSTAV}]*högskola(?:n|ns)?"
    rf"|[{_BOKSTAV}]*gymnasi(?:um|et|eskola|eskolan)"
    rf"|grundskola(?:n|ns)?"
    rf")(?![{_BOKSTAV}])",
    re.IGNORECASE,
)
#: "Region Västerbotten" — bara som första ord, så att "Bygg i Region Syd AB"
#: inte träffas.
_REGION_FORST = re.compile(r"^\s*[Rr]egion\s+[A-ZÅÄÖ]")

#: Bolagsformer som är privata företag. Allt annat registret anger (kommun,
#: region, stiftelse, ideell förening, trossamfund) faller. Tom bolagsform
#: fäller inte: okänt är inte fel.
_PRIVATA_FORMER = ("aktiebolag", "handelsbolag", "kommanditbolag", "ekonomisk förening", "enskild")


def offentlig_eller_skola(kandidat: dict[str, Any]) -> str | None:
    """Skälet när kandidaten är offentlig sektor eller en skola, annars None."""
    siffror = normalisera(kandidat.get("orgnr"))
    # Första siffran 2 = stat, region, kommun eller församling (Skatteverkets
    # gruppnummer). Privata juridiska personer börjar på 5, 7, 8 eller 9.
    if len(siffror) == 10 and siffror[0] == "2":
        return "Offentlig sektor: organisationsnumret tillhör stat, region eller kommun."
    form = str(kandidat.get("bolagsform") or "").casefold().strip()
    if form and not any(p in form for p in _PRIVATA_FORMER):
        return f"Inte ett privat bolag: {kandidat.get('bolagsform')}."
    namn = str(kandidat.get("company_name") or "")
    traff = _NAMNORD.search(namn)
    if traff:
        return f"Offentlig sektor eller skola: namnet innehåller \"{traff.group(0)}\"."
    if _REGION_FORST.search(namn):
        return "Offentlig sektor: namnet börjar med \"Region\"."
    return None


def demo() -> None:
    for namn in (
        "Yrkeshögskolan Umeå Kommun",
        "Umeå Folkhögskola",
        "Folkuniversitetet i Umeå",
        "Hermods Komvux i Umeå",
        "Göteborgs universitet",
        "Region Västerbotten",
        "Umeå kommuns bostadsbolag",
        "Polhemsgymnasiet",
    ):
        assert offentlig_eller_skola({"company_name": namn}), namn
    for namn in (
        "Medlearn i Umeå",
        "Stay Alive AB",
        "Bra Kommunikation AB",
        "Norrlands Trafikskola AB",
        "IHM Business School",
        "Bygg i Region Syd AB",
        "Countivo",
    ):
        assert offentlig_eller_skola({"company_name": namn}) is None, namn
    assert offentlig_eller_skola({"company_name": "X", "orgnr": "212000-2627"})
    assert offentlig_eller_skola({"company_name": "X AB", "orgnr": "556824-9022"}) is None
    assert offentlig_eller_skola({"company_name": "X", "bolagsform": "Ideell förening"})
    assert offentlig_eller_skola({"company_name": "X AB", "bolagsform": "Aktiebolag"}) is None
    print("offentlig: ok")


if __name__ == "__main__":
    demo()
