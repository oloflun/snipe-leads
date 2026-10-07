"""Den enda vägen till en sida utifrån för leads (plan 2026-10-05, fas 2).

Antons fynd 2026-10-04: 109 ScrapeGraph-krediter på en dag, gratispotten slut.
Orsaken var inte priset per anrop utan antalet: merinfo-sidor och webbplatser
hämtades om i varje runda, i varje deploy och i två kodvägar som inte delade
cache, och varje filter kördes efter att sidan redan var betald.

Här samlas därför tre saker som tidigare låg utspridda:

1. **Cache per kund i Postgres** (`leads_sidcache`, migration 093). Överlever
   deployer och delas av merinfo-sökningen och researchen. Ett misslyckande
   cachas också, kortare, så att vi inte betalar för samma fel två gånger.
2. **Gratis först:** en vanlig httpx-hämtning för bolagens egna sajter.
   ScrapeGraph är reserven när sidan inte går att läsa direkt (blockerad,
   tom eller JS-renderad). merinfo blockerar direkthämtning och går därför
   alltid via ScrapeGraph.
3. **Kredittak per körning** (`Skrapkontext`). Räknar betalda anrop per fas
   och vägrar nya när taket är nått, så att en körning aldrig kan tömma
   kontot. Antalet sparas i körningens liggare och visas i Körningar.

Kontexten bärs av en ContextVar: körningen sätter den en gång, och varje
await-kedja under den (även asyncio.gather) ser samma räknare utan att den
skickas genom tio funktionssignaturer. Utan kontext (skript, tester) finns
ingen cache och inget tak — beteendet blir som förut.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger("snajp-support.leads.sidhamtning")

#: Standardtaket för betalda anrop per körning. En Iris-körning med N=5 ska
#: landa under 20 (planens mål); 40 lämnar marginal för en tredje sökrunda.
STANDARD_TAK = 40
#: Tak för ett enskilt researchjobb: startsidan, registersidan och tre
#: kontaktsidor är fem; allt utöver det är ett fel någonstans.
RESEARCH_TAK = 6

#: Livslängd per sorts sida. Listsidor ändras när bolag tillkommer;
#: bolagssidor och sajter sällan.
LIVSLANGD = {
    "lista": timedelta(days=7),
    "bolag": timedelta(days=30),
    "webb": timedelta(days=14),
    "research": timedelta(days=14),
}
FEL_LIVSLANGD = timedelta(days=1)

#: Under så här mycket text räknas en direkthämtning som misslyckad. En
#: JS-renderad sida fångas främst av _JS_SKAL ("Aktivera JavaScript"); gränsen
#: är bara golvet för en tom mall. Små riktiga sajter är korta (Byggarna
#: Berggrens hela startsida är cirka 120 tecken), så den får inte ligga högre.
MIN_TEXT = 40
#: Fel som säger att TJÄNSTEN inte kunde leverera, till skillnad från en sida
#: som inte finns. Fritext från SDK:t, därav mönstret.
_TJANSTEFEL = re.compile(
    r"credit|kredit|quota|kvot|payment|rate limit|\b40[1239]\b|\b429\b|svarade inte inom|API_KEY saknas|unauthori",
    re.IGNORECASE,
)
_JS_SKAL =("enable javascript", "aktivera javascript", "you need to enable", "requires javascript")

# ScrapeGraphs hastighetsgräns (uppmätt 2026-10-01): två samtidiga, en per sekund.
_SEM = asyncio.Semaphore(2)
_SENAST = [0.0]
MIN_INTERVALL_S = 1.0
#: Gemensam paus efter ett 429, för HELA processen. Uppmätt 2026-10-06 23:15:
#: tre samtidiga körningar fick 429 två gånger i sekunden i en halv minut,
#: eftersom varje anrop väntade ut sin egen backoff medan de andra fortsatte
#: hamra. Merinfo-sidorna föll, och körningen slutade med "slut på kandidater"
#: och 0 leads fast registret hade bolag. Nu väntar alla tills pausen är slut,
#: och pausen växer för varje 429 i rad (5, 10, 20, 40, tak 60 s).
_PAUS_TILL = [0.0]
_RAD_429 = [0]
MAX_FORSOK = 7


def _rate_limit(fel: object) -> bool:
    text = str(fel or "").casefold()
    return "rate limit" in text or "429" in text or "too many requests" in text


@dataclass
class Skrapkontext:
    storage: Any = None
    tenant_id: str | None = None
    tak: int = STANDARD_TAK
    #: Betalda ScrapeGraph-anrop per fas (lista, bolag, webb, research).
    anrop: dict[str, int] = field(default_factory=dict)
    cachetraffar: int = 0
    #: Betalda hämtningar som föll på TJÄNSTEN (kredit, kvot, nyckel, tidsgräns),
    #: inte på sidan. Registerkällan läser den för att skilja "listan gick inte
    #: att hämta" från "listan finns inte" (sources/merinfo.py).
    tjanstefel: int = 0

    @property
    def totalt(self) -> int:
        return sum(self.anrop.values())

    @property
    def slut(self) -> bool:
        return self.totalt >= self.tak

    def som_dict(self) -> dict[str, Any]:
        # tjanstefel följer med till liggaren: en körning som slutar utan
        # leads för att hämtningarna föll hos tjänsten ska kunna säga det.
        ut: dict[str, Any] = {**self.anrop, "cache": self.cachetraffar}
        if self.tjanstefel:
            ut["tjanstefel"] = self.tjanstefel
        return ut


_KONTEXT: ContextVar[Skrapkontext | None] = ContextVar("leads_skrapkontext", default=None)


def starta(storage: Any, tenant_id: str, *, tak: int = STANDARD_TAK) -> Skrapkontext:
    """Sätter körningens kontext för den här await-kedjan och returnerar den."""
    kontext = Skrapkontext(storage=storage, tenant_id=tenant_id, tak=max(0, tak))
    _KONTEXT.set(kontext)
    return kontext


def aktuell() -> Skrapkontext | None:
    return _KONTEXT.get()


def summera(fore: dict[str, Any] | None, nytt: Skrapkontext | dict[str, Any] | None) -> dict[str, int]:
    """Lägger nya räknare till körningens tidigare summa (liggaren)."""
    ut = {k: int(v) for k, v in (fore or {}).items() if isinstance(v, (int, float))}
    nytt = nytt.som_dict() if isinstance(nytt, Skrapkontext) else (nytt or {})
    for fas, n in nytt.items():
        ut[fas] = ut.get(fas, 0) + n
    return ut


#: Räknare i `skrap` som inte är betalda anrop.
_EJ_BETALDA = ("cache", "tjanstefel")


def betalda(skrap: dict[str, Any] | None) -> int:
    return sum(int(v) for k, v in (skrap or {}).items() if k not in _EJ_BETALDA and isinstance(v, (int, float)))


def _farsk(rad: dict[str, Any], fas: str) -> bool:
    hamtad = rad.get("hamtad_at")
    if isinstance(hamtad, str):
        hamtad = datetime.fromisoformat(hamtad.replace("Z", "+00:00"))
    if not isinstance(hamtad, datetime):
        return False
    if hamtad.tzinfo is None:
        hamtad = hamtad.replace(tzinfo=timezone.utc)
    livslangd = LIVSLANGD.get(fas, LIVSLANGD["webb"]) if rad.get("innehall") else FEL_LIVSLANGD
    return datetime.now(timezone.utc) - hamtad < livslangd


def _js_skal(text: str) -> bool:
    return len(text) < 400 and any(s in text.casefold() for s in _JS_SKAL)


async def _scrapegraph(url: str) -> tuple[str | None, str | None]:
    """Ett betalt anrop, med väntan vid hastighetsgränsen. Kastar aldrig."""
    from ..agent.research_tools import _hamta_via_scrapegraph
    from ..config import get_settings

    nyckel = get_settings().scrapegraphai_api_key
    if not nyckel:
        return None, "SCRAPEGRAPHAI_API_KEY saknas."
    md, fel = None, None
    for _forsok in range(MAX_FORSOK):
        async with _SEM:
            # Pausen läses INNANFÖR semaforen: ett anrop som väntat på platsen
            # ska se en paus som sattes medan det väntade.
            while (vanta := max(_PAUS_TILL[0], _SENAST[0] + MIN_INTERVALL_S) - time.monotonic()) > 0:
                await asyncio.sleep(vanta)
            _SENAST[0] = time.monotonic()
            md, fel = await _hamta_via_scrapegraph(nyckel, url)
            if md is not None or not _rate_limit(fel):
                _RAD_429[0] = 0
                break
            # Semaforen hålls medan pausen sätts, så att nästa i kön ser den.
            _RAD_429[0] += 1
            paus = min(60.0, 5.0 * 2 ** (_RAD_429[0] - 1))
            _PAUS_TILL[0] = max(_PAUS_TILL[0], time.monotonic() + paus)
            logger.info("ScrapeGraph 429: alla hämtningar pausar %.0f s (%d i rad).", paus, _RAD_429[0])
    return md, fel


def _direkt_forst() -> bool:
    """LEADS_DIREKTHAMTNING: osatt = gratis hämtning först (drift); tom
    sträng = ScrapeGraph först med direkthämtning som reserv (testsviten,
    som annars hade gjort riktiga HTTP-anrop — conftest tömmer variabeln,
    åttonde gången samma läxa)."""
    return os.environ.get("LEADS_DIREKTHAMTNING") != ""


async def hamta(url: str, *, fas: str, direkt: bool) -> tuple[str | None, str | None, str]:
    """(text, fel, via). `via` är cache, direkt, scrapegraphai eller tak.

    `direkt`: sidan får hämtas med en vanlig httpx-förfrågan (bolagens egna
    sajter). merinfo och andra register som blockerar sådan hämtning anges
    med direkt=False och går alltid via ScrapeGraph. Kastar aldrig."""
    from ..agent.research_tools import _hamta_direkt
    from ..config import get_settings

    kontext = aktuell()
    lager = kontext.storage if kontext and kontext.tenant_id else None
    if lager is not None:
        try:
            rad = await lager.get_sidcache(kontext.tenant_id, url)
        except Exception:  # noqa: BLE001 — en trasig cacheläsning kostar bara ett anrop
            logger.exception("Sidcachen gick inte att läsa för %s", url)
            rad = None
        # Ett cachat TJÄNSTEFEL (kredit, kvot, nyckel) säger inget om sidan och
        # ignoreras: rader från före 2026-10-06 bar kreditslutet på en gammal
        # nyckel i ett dygn efter att en ny nyckel med krediter lagts in.
        if rad and _farsk(rad, fas) and (rad.get("innehall") or not _TJANSTEFEL.search(str(rad.get("fel") or ""))):
            kontext.cachetraffar += 1
            return (rad.get("innehall") or None), rad.get("fel"), "cache"

    async def direkthamta() -> tuple[str | None, str | None]:
        text, fel = await _hamta_direkt(url)
        if text and (len(text.strip()) < MIN_TEXT or _js_skal(text)):
            return None, "direkthämtning: för lite text (JS-renderad sida?)"
        return text, fel

    text: str | None = None
    fel: str | None = None
    via = ""
    forst = direkt and _direkt_forst()
    if forst:
        text, fel = await direkthamta()
        via = "direkt"
    if text is None:
        if kontext and kontext.slut:
            fel = "; ".join(filter(None, [fel, f"kredittaket för körningen ({kontext.tak} anrop) är nått"]))
            return None, fel, "tak"
        if kontext and get_settings().scrapegraphai_api_key:
            kontext.anrop[fas] = kontext.anrop.get(fas, 0) + 1
        md, sg_fel = await _scrapegraph(url)
        if md:
            text, fel, via = md, None, "scrapegraphai"
        else:
            if kontext and _TJANSTEFEL.search(str(sg_fel or "")):
                kontext.tjanstefel += 1
            fel = "; ".join(filter(None, [fel, sg_fel]))
            if direkt and not forst and get_settings().scrapegraphai_api_key:
                # Reservvägen (som förut): SAMMA url direkt när tjänsten fallerar.
                text, direkt_fel = await direkthamta()
                if text:
                    fel, via = None, "direkt"
                else:
                    fel = f"{fel} Reservhämtningen gav inget heller: {direkt_fel}."
    # Tjänstefel cachas inte: nästa anrop ska få pröva igen med påfylld kredit.
    if lager is not None and (text or not _TJANSTEFEL.search(str(fel or ""))):
        try:
            await lager.put_sidcache(kontext.tenant_id, url, innehall=text, fel=None if text else fel)
        except Exception:  # noqa: BLE001
            logger.exception("Sidcachen gick inte att skriva för %s", url)
    return text, fel, via
