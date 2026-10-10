"""Rangpoängen: hur bra ett GODKÄNT lead är (Sebbe 2026-10-07).

## Varför den finns

Bedömningens poäng (bedomning.bedom) är andelen krav bolaget klarar. Men
varje nej, och varje måste-krav utan belägg, fäller redan bolaget till nivå C
och döljer det. Ett synligt lead har därför klarat allt, och poängen blev 100
(eller 92 när storleken var okänd) för alla 32 synliga leads i Snajps
development. Sorteringen "bästa överst" hade inget att sortera på.

Grinden och rangen är två olika frågor. Grinden (nivå, qualified, icp_fit,
kundens kvalificeringströskel) står orörd. Rangpoängen ersätter bara
`score_total` för ett godkänt lead och mäter det som faktiskt skiljer leads
åt:

  passform  40  Jevs bedömning av hur väl bolaget passar målgruppen (0–3)
  belägg    25  styrkta citat ur bolagets egna sidor, tak 5
  kontakt   20  namngiven persons adress 20, bolagets adress (info@) 8
  tidpunkt  15  signaler att läget är rätt nu (nyheter, annonser), tak 2

Allt läses ur prospektraden, så befintliga leads räknas om utan nya anrop
(scripts/omrakna_rangpoang.py). Ren funktion, inga beroenden.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

VIKT = {"passform": 40, "belagg": 25, "kontakt": 20, "tidpunkt": 15}
BELAGG_TAK = 5
SIGNAL_TAK = 2
#: Jev svarade inte: varken bra eller dåligt, mitt på skalan.
PASSFORM_OKAND = 0.5


def _lista(varde: Any) -> list[Any]:
    if isinstance(varde, str):
        try:
            varde = json.loads(varde)
        except ValueError:
            return []
    return varde if isinstance(varde, list) else []


def _dikt(varde: Any) -> dict[str, Any]:
    if isinstance(varde, str):
        try:
            varde = json.loads(varde)
        except ValueError:
            return {}
    return varde if isinstance(varde, dict) else {}


def _norm(text: str) -> str:
    bas = unicodedata.normalize("NFKD", str(text or "").casefold())
    return "".join(t for t in bas if not unicodedata.combining(t))


def passform(rad: dict[str, Any]) -> float:
    """0–1 ur Jevs triage (skala 0–3), annars mitten."""
    fit = _dikt(rad.get("jev")).get("triage", {}) or {}
    try:
        return max(0.0, min(1.0, float(fit.get("fit")) / 3))
    except (TypeError, ValueError):
        return PASSFORM_OKAND


def antal_belagg(rad: dict[str, Any]) -> int:
    return sum(len(_lista(r.get("belagg"))) for r in _lista(rad.get("score_breakdown")) if isinstance(r, dict))


def namngiven_adress(rad: dict[str, Any]) -> bool:
    """Adressens lokaldel bär ett led ur kontaktpersonens namn — samma
    beviskedja som discovery.person_kontakt_i_text."""
    epost = str(rad.get("contact_email") or "")
    namn = str(rad.get("contact_name") or "")
    if "@" not in epost or not namn.strip():
        return False
    lokal = _norm(epost.split("@", 1)[0])
    return any(len(led) >= 2 and led in lokal for led in re.findall(r"[a-z]+", _norm(namn)))


def rangpoang(rad: dict[str, Any]) -> int:
    """0–100 för ett godkänt lead. Anroparen avgör om raden är godkänd."""
    kontakt = 1.0 if namngiven_adress(rad) else (0.4 if rad.get("contact_email") else 0.0)
    delar = {
        "passform": passform(rad),
        "belagg": min(antal_belagg(rad), BELAGG_TAK) / BELAGG_TAK,
        "kontakt": kontakt,
        "tidpunkt": min(len(_lista(rad.get("signaler"))), SIGNAL_TAK) / SIGNAL_TAK,
    }
    return round(sum(VIKT[k] * v for k, v in delar.items()))


def demo() -> None:
    stark = {
        "jev": {"triage": {"fit": 2.97}},
        "score_breakdown": [{"belagg": [{"citat": "a"}] * 3}, {"belagg": [{"citat": "b"}] * 2}],
        "contact_name": "Anna Lind",
        "contact_email": "anna.lind@bolag.se",
        "signaler": ["Ny lokal", "Rekryterar"],
    }
    svag = {
        "jev": {"triage": {"fit": 2.07}},
        "score_breakdown": [{"belagg": [{"citat": "a"}]}],
        "contact_email": "info@bolag.se",
        "signaler": [],
    }
    assert rangpoang(stark) > 90 > 60 > rangpoang(svag), (rangpoang(stark), rangpoang(svag))
    assert namngiven_adress(stark) and not namngiven_adress(svag)
    assert rangpoang({"jev": '{"triage": {"fit": 3}}', "score_breakdown": "[]"}) == 40


if __name__ == "__main__":
    demo()
    print("ok")
