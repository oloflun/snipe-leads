"""Bolagsuppgifter ur SCB:s företagsregister, bara bolagsnivå.

Antons beslut 2026-11-27 (docs/crm/SVENSK-STANDARD.md § 4 fråga 4, svar 10: ja,
bara bolagsnivå). Ett litet gränssnitt: `sla_upp(orgnr)` och `konfigurerad()`.

## Vad registret får ge

Namn, juridisk form, status (verksamt, avregistrerat), SNI, säte (kommun och
län), postadress, antal anställda som storleksklass och reklamspärr. Det är
allt. **Aldrig personer**: inga firmatecknare, ingen styrelse, inga namn på
innehavare. Svaret byggs ur en vitlista av SCB:s fältnamn, så att ett fält
som registret lägger till senare inte följer med av sig självt.

En enskild firma slås inte upp alls: dess nummer är innehavarens personnummer,
och registrets namn och säte är då en fysisk persons namn och folkbokföringsort
(CLAUDE.md, "Leads: källor, filter och kontakter", regel 1 och 6). Detsamma
gäller ett dödsbo, vars namn bär den dödes. Det blir utfallet `InteEttBolag`.

## Tjänsten (läst 2026-11-27)

SCB:s "allmänna företagsregister API" (https://apiafr.scb.se, OpenAPI-specen
under /swagger/v1/swagger.json, öppen att läsa). Avgiftsfritt sedan 26 juni
2025. REST och JSON; nyckeln skickas i `X-API-Key` (specens `securitySchemes`).
Nyckeln är personlig, får inte delas och hämtas i SCB:s Registreringsportal;
de gamla certifikaten gäller inte det nya API:t. Högst 5 anrop per sekund och
nyckel (här hålls anropen isär i processen), 429 med `Retry-After` vid
överlast, och tjänsten är nere 30 minuter från kl. 04.00 varje natt.

Uppslaget är `GET /v1/juridiskaenheter/{peOrgNr}/full`. PeOrgNr är tolv
siffror; för en juridisk person 16 följt av organisationsnumret
(variabelbeskrivningen, sid 19). Kodtabellerna (`/v1/kodtabeller/...`) kräver
nyckeln och är inte lästa: tolkningen av status, storleksklass och reklamspärr
nedan bygger på variabelbeskrivningen (PDF:en), inte på API:ts egna tabeller.

Fel hos SCB blir `RegistretNere` och aldrig ett 500 hos oss. Loggen bär
statuskod och feltyp, aldrig nyckeln, numret eller svaret.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from ..config import get_settings
from ..integrationer import natvakt
from . import falt

logger = logging.getLogger("snajp-support.crm.scb")

TIDSGRANS = 10.0
#: SCB tillåter fem anrop per sekund och nyckel. Anropen från den här
#: processen hålls minst så här långt isär.
_MELLANRUM = 0.25
#: (händelseloopen, låset): ett asyncio-lås hör till en loop.
_las: tuple[Any, asyncio.Lock] | None = None
_senast = 0.0

#: Juridisk form (SCB:s kod) som är en fysisk person eller bär en persons
#: namn: enskild näringsidkare och oskiftat dödsbo. Slås inte upp.
_EJ_BOLAG = frozenset({"10", "91"})

#: Status hos Bolagsverket (variabelbeskrivningen sid 23-25) som betyder att
#: bolaget inte finns kvar: konkurs eller likvidation avslutad, avfört,
#: avregistrerat, upplöst genom fusion, ombildning eller delning.
_AVREGISTRERAD = frozenset({21, 22, 31, 36, 37, 41, 77, 91, *range(50, 65), *range(70, 75)})
#: Företagsstatus i SCB (sid 14).
_FORETAGSSTATUS = {"0": "never_active", "1": "active", "9": "inactive"}

#: Storleksklass anställda (sid 26).
ANSTALLDA_KLASS = {
    "0": None, "1": "0", "2": "1-4", "3": "5-9", "4": "10-19", "5": "20-49", "6": "50-99",
    "7": "100-199", "8": "200-499", "9": "500-999", "10": "1000-1499", "11": "1500-1999",
    "12": "2000-2999", "13": "3000-3999", "14": "4000-4999", "15": "5000-9999", "16": "10000-",
}
#: Reklam (sid 22): 11-13 tar emot reklam, 21-23 har frånsagt sig reklam.
#: Andra värden är inte kända och lämnas som okända (None) med koden bredvid.
_TAR_EMOT_REKLAM = frozenset({11, 12, 13})
_FRANSAGT_REKLAM = frozenset({21, 22, 23})


class InteEttBolag(ValueError):
    """Numret är en enskild firmas eller ett dödsbos: slås inte upp."""


class EjKonfigurerad(RuntimeError):
    """Nyckeln till SCB saknas i miljön (SCB_API_NYCKEL)."""


class RegistretNere(RuntimeError):
    """SCB svarade inte, svarade med fel eller med något som inte gick att läsa."""


@dataclass
class Bolagsuppgifter:
    orgnr: str
    namn: str | None = None
    juridisk_form_kod: str | None = None
    bolagsform: str | None = None
    #: active, inactive, never_active, deregistered eller unknown.
    status: str = "unknown"
    foretagsstatus_kod: str | None = None
    bolagsverket_status_kod: str | None = None
    sni: list[str] = field(default_factory=list)
    sate_kommun: str | None = None
    sate_lan: str | None = None
    gatuadress: str | None = None
    co: str | None = None
    postnr: str | None = None
    postort: str | None = None
    anstallda_klass: str | None = None
    anstallda_text: str | None = None
    #: True: bolaget har frånsagt sig reklam. False: tar emot. None: okänt.
    reklamsparr: bool | None = None
    reklamsparr_kod: int | None = None

    @property
    def avregistrerad(self) -> bool:
        return self.status == "deregistered"


def _nyckel() -> str:
    return (get_settings().scb_api_nyckel or "").strip()


def _bas() -> str:
    return (get_settings().scb_bas_url or "https://apiafr.scb.se").rstrip("/")


def konfigurerad() -> bool:
    return bool(_nyckel())


def _text(varde: Any, max_langd: int = 200) -> str | None:
    if varde is None or isinstance(varde, (dict, list)):
        return None
    return falt.text(str(varde), max_langd=max_langd)


def _heltal(varde: Any) -> int | None:
    try:
        return int(str(varde).strip())
    except (TypeError, ValueError):
        return None


def _status(foretagsstatus: str | None, bolagsverket: str | None) -> str:
    if _heltal(bolagsverket) in _AVREGISTRERAD:
        return "deregistered"
    return _FORETAGSSTATUS.get((foretagsstatus or "").strip(), "unknown")


def _sni(data: dict[str, Any]) -> list[str]:
    grenar = data.get("naringsgrenar")
    if not isinstance(grenar, list):
        grenar = [data.get("primarNaringsgren")] if isinstance(data.get("primarNaringsgren"), dict) else []
    grenar = [g for g in grenar if isinstance(g, dict)]
    grenar.sort(key=lambda g: _heltal(g.get("rangordning")) or 99)
    koder: list[str] = []
    for gren in grenar:
        try:
            kod = falt.sni(_text(gren.get("naringsgren"), 20))
        except falt.FaltFel:
            continue
        if kod and kod not in koder:
            koder.append(kod)
    return koder[: falt.MAX_SNI]


def tolka(orgnr: str, data: dict[str, Any]) -> Bolagsuppgifter:
    """SCB:s svar till bolagsuppgifterna. Bara fälten i vitlistan läses."""
    jurform = _text(data.get("jurform"), 4)
    if jurform and jurform.zfill(2) in _EJ_BOLAG:
        raise InteEttBolag(orgnr)
    adress = data.get("postAdress") if isinstance(data.get("postAdress"), dict) else {}
    try:
        postnr = falt.postnr(_text(adress.get("postNr"), 20))
    except falt.FaltFel:
        postnr = None
    foretagsstatus, bolagsverket = _text(data.get("ftgStat"), 4), _text(data.get("bolStat"), 4)
    klass = _text(data.get("anstKl"), 4)
    reklam = _heltal(data.get("reklamSparrTyp"))
    return Bolagsuppgifter(
        orgnr=orgnr,
        namn=_text(data.get("namn")),
        juridisk_form_kod=jurform.zfill(2) if jurform else None,
        bolagsform=falt.bolagsform(jurform) if jurform else None,
        status=_status(foretagsstatus, bolagsverket),
        foretagsstatus_kod=foretagsstatus,
        bolagsverket_status_kod=bolagsverket,
        sni=_sni(data),
        sate_kommun=_text(data.get("kommunSate"), 100),
        sate_lan=_text(data.get("lanSate"), 100),
        gatuadress=_text(adress.get("gatuAdress")),
        co=_text(adress.get("coAdress")),
        postnr=postnr,
        postort=_text(adress.get("postOrt"), 100),
        anstallda_klass=klass,
        anstallda_text=ANSTALLDA_KLASS.get(klass or ""),
        reklamsparr=True if reklam in _FRANSAGT_REKLAM else False if reklam in _TAR_EMOT_REKLAM else None,
        reklamsparr_kod=reklam,
    )


async def _vanta_pa_tur() -> None:
    global _senast, _las
    loop = asyncio.get_running_loop()
    if _las is None or _las[0] is not loop:
        _las = (loop, asyncio.Lock())
    async with _las[1]:
        vanta = _MELLANRUM - (time.monotonic() - _senast)
        if vanta > 0:
            await asyncio.sleep(vanta)
        _senast = time.monotonic()


async def sla_upp(orgnr: str) -> Bolagsuppgifter | None:
    """Bolagets uppgifter, eller None när registret inte känner numret.

    Kastar `falt.FaltFel` för ett nummer som inte går att läsa, `InteEttBolag`
    för en enskild firma eller ett dödsbo (före något anrop när numret är ett
    personnummer), `EjKonfigurerad` utan nyckel och `RegistretNere` när SCB
    inte svarar som det ska."""
    visning, siffror, enskild = falt.orgnr(orgnr)
    if not siffror:
        raise falt.FaltFel("orgnr_saknas", "")
    if enskild:
        raise InteEttBolag(visning)
    nyckel = _nyckel()
    if not nyckel:
        raise EjKonfigurerad()
    await _vanta_pa_tur()
    try:
        svar = await natvakt.anropa(
            "GET", f"{_bas()}/v1/juridiskaenheter/16{siffror}/full", tidsgrans=TIDSGRANS,
            rubriker={"X-API-Key": nyckel, "Accept": "application/json", "User-Agent": "Snajp-CRM/1"})
    except Exception as fel:  # noqa: BLE001 (nätfel, tidsgräns, nätvaktens nej)
        logger.warning("crm: SCB:s företagsregister svarade inte (%s)", type(fel).__name__)
        raise RegistretNere(type(fel).__name__) from None
    if svar.status == 404:
        return None
    if not svar.ok:
        logger.warning("crm: SCB:s företagsregister svarade HTTP %s", svar.status)
        raise RegistretNere(f"HTTP {svar.status}")
    try:
        data = json.loads(svar.text)
    except ValueError:
        logger.warning("crm: SCB:s företagsregister svarade med något som inte är JSON")
        raise RegistretNere("json") from None
    if isinstance(data, list):
        data = data[0] if data and isinstance(data[0], dict) else None
    if not isinstance(data, dict):
        raise RegistretNere("form")
    return tolka(visning, data)


def nollstall() -> None:
    """Bara för tester."""
    global _senast
    _senast = 0.0
