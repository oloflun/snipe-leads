"""Eskaleringsreglerna: när Iris lämnar över till en människa.

Kunden ställer in dem i leadssajtens Inställningar. De bor i
`agent_configs.settings["eskalering"]` bredvid autonomin och målgruppen, och
verkställs i KOD på två ställen:

  * svarshanteringen (`leads/svar.py`): ett svar om pris eller juridik får
    inget AI-utkast, och ett negativt svar aviserar kunden;
  * batchkörningen (`api/leads.py`, `_run_batch_prospect`): ett kvalificerat
    bolag under träffsäkerhetströskeln får inget automatiskt utkast.

Ämnesdetekteringen är ett ordfilter och inte en modellbedömning. Modellen kan
missa att "vad landar det på per månad?" är en prisfråga, men kan inte prata
bort ett träffat ord: beslutet att lämna över ska inte kunna förhandlas av
innehållet i prospektets mejl, samma princip som påhoppsgrinden.

Lässidan är TOLERANT (okänt eller trasigt i databasen blir standardvärdet),
skrivsidan är strikt (pydantic i `api/schemas.py`). Standardvärdena är den
försiktiga sidan: allt påslaget.
"""

from __future__ import annotations

import re
from typing import Any, TypedDict


class Eskaleringsregler(TypedDict):
    osaker_kvalificering: bool
    #: Träffsäkerhet mot målgruppen i procent, 0–100.
    kvalificeringstroskel: int
    prisfragor: bool
    negativt_svar: bool
    juridik: bool


STANDARD: Eskaleringsregler = {
    "osaker_kvalificering": True,
    "kvalificeringstroskel": 60,
    "prisfragor": True,
    "negativt_svar": True,
    "juridik": True,
}

_BOOLFALT = ("osaker_kvalificering", "prisfragor", "negativt_svar", "juridik")


def normalisera(ratt: Any) -> Eskaleringsregler:
    """Sparat värde → fullständiga regler. Kastar aldrig."""
    regler: Eskaleringsregler = dict(STANDARD)  # type: ignore[assignment]
    if not isinstance(ratt, dict):
        return regler
    for falt in _BOOLFALT:
        if isinstance(ratt.get(falt), bool):
            regler[falt] = ratt[falt]  # type: ignore[literal-required]
    troskel = ratt.get("kvalificeringstroskel")
    if isinstance(troskel, (int, float)) and not isinstance(troskel, bool):
        regler["kvalificeringstroskel"] = max(0, min(100, int(troskel)))
    return regler


def under_troskel(regler: Eskaleringsregler, *, qualified: bool, icp_fit: Any) -> bool:
    """Ska ett kvalificerat bolag lämnas till kunden i stället för att få utkast?

    Ett underkänt bolag hanteras redan av kvalificeringsgrinden; det här
    gäller bara de som passerat den men ligger under kundens egen ribba. En
    saknad icp_fit är inte "under": då finns inget att jämföra, och att
    stoppa på avsaknad hade stoppat varje V1-körning där fältet uteblev.
    """
    if not regler["osaker_kvalificering"] or not qualified:
        return False
    try:
        fit = float(icp_fit)
    except (TypeError, ValueError):
        return False
    return fit * 100 < regler["kvalificeringstroskel"]


#: Ord som gör ett svar till en prisfråga. Böjningarna står utskrivna i
#: stället för som prefix: "pris" som prefix hade träffat "prisma" och
#: "kost" hade träffat "kosta på sig".
_PRIS = re.compile(
    r"\b("
    r"pris|priset|priser|priserna|prisexempel|prisuppgift|prisuppgifter|prislista|"
    r"kostar|kosta|kostnad|kostnaden|kostnader|offert|offerten|rabatt|rabatten|"
    r"avgift|avgiften|budget|budgeten|betala|faktureras|"
    r"kr|kronor|sek|per månad|i månaden"
    r")\b",
    re.IGNORECASE,
)

#: Ord som gör ett svar till en fråga om avtal, juridik eller personuppgifter.
_JURIDIK = re.compile(
    r"\b("
    r"avtal|avtalet|avtalen|kontrakt|kontraktet|villkor|villkoren|avtalsvillkor|"
    r"bindningstid|uppsägning|uppsägningstid|juridisk|juridiska|juridiskt|jurist|"
    r"advokat|gdpr|personuppgift|personuppgifter|personuppgiftsbiträdesavtal|"
    r"biträdesavtal|dataskydd|dataskyddsförordningen|registerutdrag|radera|raderas|"
    r"integritetspolicy|integritetspolicyn"
    r")\b",
    re.IGNORECASE,
)


def amnen_i_svar(text: str) -> set[str]:
    """Vilka eskaleringsämnen ett prospektsvar tar upp: "pris", "juridik"."""
    amnen: set[str] = set()
    if _PRIS.search(text or ""):
        amnen.add("pris")
    if _JURIDIK.search(text or ""):
        amnen.add("juridik")
    return amnen


def aktiva_amnen(regler: Eskaleringsregler, amnen: set[str]) -> list[str]:
    """Ämnena som kundens påslagna regler säger ska lämnas över, i fast ordning."""
    aktiva: list[str] = []
    if regler["prisfragor"] and "pris" in amnen:
        aktiva.append("pris")
    if regler["juridik"] and "juridik" in amnen:
        aktiva.append("juridik")
    return aktiva
