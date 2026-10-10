"""Existensgrinden: ett bolag som inte går att styrka blir aldrig ett lead.

## Varför den finns

Provkörningen 2026-10-05 (Snajp, utan filter) gav tre bolag som inte finns:
"Exempel E-handel AB", "Detaljhandel Design AB" och "Byggmästarna i Göteborg
AB", med påhittade domäner. De kom ur den grounded Gemini-sökningen, som var
enda källan i körningen, och ingenting mellan sökningen och utkastet
kontrollerade att bolaget eller domänen fanns: en domän som inte svarar
räknades som "inte parkerad" och behölls.

## Vad den kräver

Ett bolag ur registret (merinfo) är en registerrad och går vidare. Varje
annan kandidat måste styrkas av sin egen webbplats:

  1. startsidan svarar, och
  2. bolagsnamnet står på sidan, eller domänen bär namnet
     (`discovery.webbplats_matchar_namn`).

En sajt som svarar men blockerar hämtningen (401/403/429) finns bevisligen,
så där räcker det att domänen bär namnet.

## Fäller vid osäkerhet

Tvärtom mot förfiltret, där okänt aldrig fäller. Skälet är vad felet kostar:
ett riktigt bolag som faller här kommer tillbaka i nästa körning, ett påhittat
bolag som går igenom får ett mejl skrivet i kundens namn.

Grinden mäter ingenting själv. Den läser `webbsignal.mat_webbplats`, som
körningen ändå anropar en gång per kandidat. Är mätningen avstängd
(`matt: False`, testsvitens läge) släpps kandidaten igenom.
"""

from __future__ import annotations

import re
from typing import Any

from .discovery import _slugga_bolagsnamn, webbplats_matchar_namn

#: Källor vars rader är registerutdrag och därför inte behöver styrkas.
REGISTERKALLOR = frozenset({"merinfo"})

#: Servern finns men släpper inte in en vanlig hämtning.
_BLOCKERAD = frozenset({401, 403, 429})

_ERSATT = {"å": "a", "ä": "a", "ö": "o", "é": "e", "ü": "u"}


def _slugga_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", "".join(_ERSATT.get(t, t) for t in (text or "").lower()))


def styrk(kandidat: dict[str, Any], fakta: dict[str, Any]) -> str | None:
    """None = bolaget går att styrka. Annars skälet, på svenska."""
    if (kandidat.get("kalla") or kandidat.get("source_name")) in REGISTERKALLOR:
        return None
    if fakta.get("matt") is False:
        return None
    namn = str(kandidat.get("company_name") or "")
    webb = str(kandidat.get("website") or "")
    if not webb:
        return "Bolaget gick inte att styrka: varken webbplats eller registerutdrag."
    if fakta.get("svarar_inte"):
        return "Bolaget gick inte att styrka: webbplatsen svarar inte."
    domanen_bar_namnet = webbplats_matchar_namn(namn, webb)
    status = fakta.get("http_status")
    if status:
        if status in _BLOCKERAD and domanen_bar_namnet:
            return None
        return f"Bolaget gick inte att styrka: webbplatsen svarade med fel ({status})."
    slug = _slugga_bolagsnamn(namn)
    # Under fyra tecken är slugen för kort för att bevisa något som delsträng
    # ("ab", "it") — då får domänen avgöra ensam.
    star_pa_sidan = len(slug) >= 4 and slug in _slugga_text(fakta.get("sidtext") or fakta.get("utdrag") or "")
    if star_pa_sidan or domanen_bar_namnet:
        return None
    return "Bolaget gick inte att styrka: bolagsnamnet står inte på webbplatsen."


def demo() -> None:
    sajt = {"matt": True, "sidtext": "Välkommen till Prestigo Bygg & Måleri i Göteborg"}
    assert styrk({"company_name": "Prestigo", "website": "https://prestigo.se"}, sajt) is None
    # Påhittat bolag: domänen finns inte.
    dod = {"matt": True, "svarar_inte": True}
    assert styrk({"company_name": "Detaljhandel Design AB", "website": "https://detaljhandeldesign.se"}, dod)
    # Domänen finns men tillhör någon annan.
    annan = {"matt": True, "sidtext": "Köp cyklar billigt hos Cykelhuset"}
    assert styrk({"company_name": "Exempel E-handel AB", "website": "https://cykelhuset.se"}, annan)
    # Registerbolag styrks av registret, också utan webbplats.
    assert styrk({"company_name": "Lilla Bygg AB", "source_name": "merinfo"}, dod) is None
    # Blockerad hämtning: servern finns, domänen bär namnet.
    assert styrk({"company_name": "Countivo AB", "website": "https://countivo.se"}, {"matt": True, "http_status": 403}) is None
    assert styrk({"company_name": "Countivo AB", "website": "https://countivo.se"}, {"matt": True, "http_status": 404})
    # Mätningen avstängd (testsviten): grinden kan inte veta, och fäller inte.
    assert styrk({"company_name": "X AB", "website": "https://x.se"}, {"matt": False}) is None
    assert styrk({"company_name": "X AB"}, {"matt": True})
    print("existens: ok")


if __name__ == "__main__":
    demo()
