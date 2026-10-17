"""Webbpoolen: sidbedömningen av varje körnings bolag, fördelad till webbyråerna.

Antons beställning och godkännande 2026-10-08 (plan
`~/.claude/plans/1-exakt-det-r-staged-clock.md`). Varje körning hos varje kund
passerar bolag med webbplats. De bedöms här (webbrevision: akut, dålig, bra,
mycket bra) och fördelas efter län till webbyråkunderna: Alunix för Västra
Götaland och Halland, Umeå Webbdesign för Norrland. Akut och dålig blir
leads; mycket bra blir en inspirationslista; bra fördelas aldrig.

## Varför bara bolagsnivå (INV-SEC-008)

Källkunden är personuppgiftsansvarig för sina leads (pilotavtalet). Det som
lämnar kunden är därför bara offentlig bolagsdata och en mätning av en publik
sajt: namn, orgnr, webbplats, ort, län, SNI och sidbedömningen (`POOLFALT`).
Aldrig kontaktperson, mejl, telefon, kundens utkast eller status, och aldrig
vilken kund som hittade bolaget. Mottagaren söker sin egen kontakt när den
processar om listan. Webbyråkunder är aldrig källa: deras körningar ska inte
gå till en konkurrent.

## Flaggor

WEBBPOOL: osatt = på, tom = av (testsvitens läge, tests/conftest.py).
WEBBPOOL_FORDELNING=1: fördelningen till mottagarna (av som standard; på i
development för test enligt Antons beslut 2026-10-08).
WEBBPOOL_MOTTAGARE: JSON {slug: [länsslug, ...]}.
WEBBPOOL_INSPIRATION: slug som får mycket bra-sajterna från alla län.
WEBBPOOL_UTESLUT: kommaseparerade slugs som aldrig är källa.
WEBBPOOL_DAGSTAK: högst så många bedömningar per dygn och process (300).
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from datetime import UTC, date, datetime, timedelta
from typing import Any

from . import webbrevision
from .webbrevision import doman

logger = logging.getLogger("snajp-support.leads.webbpool")

#: Fälten som får finnas i poolen. Inget annat skrivs (INV-SEC-008).
POOLFALT = ("website", "company_name", "orgnr", "ort", "postnr", "lan", "sni", "webbniva", "webbrevision",
            "forsta_kalla_typ", "bedomd_at")
#: Fält i en kandidat som ALDRIG får nå poolen. Testet läser listan.
PERSONFALT = ("contact_name", "contact_email", "contact_phone", "contact_role", "vd_namn", "personer", "telefon",
              "epost")
FARSK = timedelta(days=30)
LEADNIVAER = ("akut", "dalig")
_dagens: dict[date, int] = {}


def aktiv() -> bool:
    return os.environ.get("WEBBPOOL") != ""


def fordelning_pa() -> bool:
    return os.environ.get("WEBBPOOL_FORDELNING", "").strip().lower() in ("1", "true", "pa", "på")


def mottagare() -> dict[str, list[str]]:
    try:
        data = json.loads(os.environ.get("WEBBPOOL_MOTTAGARE") or "{}")
    except ValueError:
        logger.warning("WEBBPOOL_MOTTAGARE är inte giltig JSON; ingen fördelning.")
        return {}
    return {str(k): [str(x) for x in v] for k, v in data.items() if isinstance(v, list)}


def _dagstak() -> int:
    try:
        return max(0, int(os.environ.get("WEBBPOOL_DAGSTAK") or 300))
    except ValueError:
        return 300


def utesluten_kalla(tenant: dict[str, Any] | None) -> bool:
    """Webbyråer och mottagarna själva är aldrig källa (Antons godkännande
    2026-10-08: en webbyråkunds leads får aldrig gå till en konkurrent)."""
    if not tenant:
        return True
    namn = {str(tenant.get("slug") or ""), str(tenant.get("id") or "")}
    uteslutna = {s.strip() for s in (os.environ.get("WEBBPOOL_UTESLUT") or "").split(",") if s.strip()}
    uteslutna |= set(mottagare()) | ({os.environ["WEBBPOOL_INSPIRATION"]} if os.environ.get("WEBBPOOL_INSPIRATION") else set())
    return bool(namn & uteslutna) or str(tenant.get("segment") or "").casefold() in ("webbyra", "webbyrå")


# -- Hemlig bedömning ----------------------------------------------------------

#: Antons regel 2026-10-08: webbplatsbedömningen är hemlig, bara synlig för
#: Admin, Umeå Webbdesign och Alunix. Slugs i ss_tenants (samma i development
#: och main för Alunix). WEBBBEDOMNING_SYNLIG ersätter listan; mottagarna och
#: inspirationskunden räknas alltid in.
SYNLIGA = ("kund-ea08b974", "kund-362d9dc5")
DOLDA_FALT = ("webbrevision", "webbniva")


def synliga() -> set[str]:
    egen = os.environ.get("WEBBBEDOMNING_SYNLIG")
    slugs = {s.strip() for s in egen.split(",") if s.strip()} if egen is not None else set(SYNLIGA)
    insp = os.environ.get("WEBBPOOL_INSPIRATION")
    return slugs | set(mottagare()) | ({insp} if insp else set())


async def far_se(storage: Any, tenant_id: str | None) -> bool:
    """Får kunden se (och få beräknad) webbplatsbedömningen? Nej vid fel."""
    if not tenant_id:
        return False
    try:
        tenant = await storage.get_tenant(str(tenant_id)) or {}
    except Exception:  # noqa: BLE001 — hellre dold än läckt
        return False
    return bool({str(tenant.get("slug") or ""), str(tenant_id)} & synliga())


def dolj(rad: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in rad.items() if k not in DOLDA_FALT}


# -- Län ---------------------------------------------------------------------

#: Postnummerprefix (två siffror) → län, bara för fördelningens län. Taket:
#: gränsorter kan hamna fel (Åmål 662 är Västra Götaland men saknas här);
#: merinfos län och orten går alltid före.
_POSTNR_LAN: dict[range, str] = {
    range(30, 32): "hallands-lan",
    range(40, 48): "vastra-gotalands-lan",
    range(50, 55): "vastra-gotalands-lan",
    range(80, 83): "gavleborgs-lan",
    range(83, 85): "jamtlands-lan",
    range(85, 90): "vasternorrlands-lan",
    range(90, 94): "vasterbottens-lan",
    range(94, 99): "norrbottens-lan",
}


def lan_ur_postnr(postnr: str | None) -> str | None:
    siffror = "".join(c for c in str(postnr or "") if c.isdigit())
    if len(siffror) < 2:
        return None
    prefix = int(siffror[:2])
    if siffror[:3] in ("434", "439"):  # Kungsbacka och Onsala hör till Halland
        return "hallands-lan"
    return next((lan for omr, lan in _POSTNR_LAN.items() if prefix in omr), None)


@lru_cache(maxsize=1)
def _geoindex() -> tuple[dict[str, str], dict[str, tuple[str, str]]]:
    from .sources.merinfo import _geoindex as bygg

    return bygg()


def lan_for(rad: dict[str, Any]) -> str | None:
    """Länets slug: merinfos län, annars orten (kommunsätet), annars postnumret."""
    from .sources.merinfo import _norm

    lan_index, kommuner = _geoindex()
    if rad.get("lan"):
        slug = lan_index.get(_norm(str(rad["lan"])).strip())
        if slug:
            return slug
    if rad.get("ort"):
        traff = kommuner.get(_norm(str(rad["ort"])).strip())
        if traff:
            return traff[1]
    return lan_ur_postnr(rad.get("postnr"))


# -- Inmatning ---------------------------------------------------------------

def ar_enskild_firma(orgnr: str | None) -> bool:
    """En enskild firmas organisationsnummer är ägarens personnummer (tredje
    siffran är månadens tiotal, 0 eller 1); en juridisk persons är 2 eller
    högre. Enskilda firmor är personuppgifter och hör inte hemma i poolen
    (INV-SEC-008; samma skäl som NIX-spärren i leadsregel 15)."""
    siffror = "".join(c for c in str(orgnr or "") if c.isdigit())[-10:]
    return len(siffror) == 10 and siffror[2] in "01"


def bolagsrad(kandidat: dict[str, Any], kalla_typ: str) -> dict[str, Any] | None:
    """Poolraden för en kandidat, eller None utan webbplats. Bara POOLFALT."""
    webb = kandidat.get("website")
    d = doman(webb)
    if not d or ar_enskild_firma(kandidat.get("orgnr")):
        return None
    return {
        "doman": d,
        "website": webbrevision.startsida(webb),
        "company_name": kandidat.get("company_name"),
        "orgnr": kandidat.get("orgnr"),
        "ort": kandidat.get("ort"),
        "postnr": kandidat.get("postnr"),
        "lan": lan_for(kandidat),
        "sni": kandidat.get("sni"),
        "forsta_kalla_typ": kalla_typ,
    }


def rader_ur_korning(korning: dict[str, Any]) -> list[dict[str, Any]]:
    """Bolagen körningen passerade (korning.pool_in), en rad per domän."""
    return [r for r in (korning.get("webbpool") or {}).values() if isinstance(r, dict) and r.get("doman")]


async def mata_in(storage: Any, korning: dict[str, Any], tenant_id: str) -> list[str]:
    """Lägger körningens bolag i poolen och returnerar domänerna som behöver
    en (ny) bedömning. Kastar aldrig: kroken får inte fälla körningen."""
    if not aktiv():
        return []
    try:
        tenant = next((t for t in await storage.list_tenants() if str(t.get("id")) == str(tenant_id)), None)
        if utesluten_kalla(tenant):
            return []
        rader = rader_ur_korning(korning)
        befintliga = await storage.webbpool_hamta([r["doman"] for r in rader])
        gransen = datetime.now(UTC) - FARSK
        behover: list[str] = []
        for rad in rader:
            await storage.webbpool_spara(rad)
            gammal = befintliga.get(rad["doman"]) or {}
            bedomd = gammal.get("bedomd_at")
            if isinstance(bedomd, str):
                bedomd = datetime.fromisoformat(bedomd)
            if not bedomd or bedomd < gransen:
                behover.append(rad["doman"])
        return behover
    except Exception:  # noqa: BLE001
        logger.exception("Webbpoolens inmatning föll för körningen hos %s.", tenant_id)
        return []


# -- Bedömning ---------------------------------------------------------------

def _farsk(rev: Any, *, bedomd_at: Any = None) -> bool:
    if not isinstance(rev, dict) or not rev.get("webbniva") or rev.get("webbniva") == "okand":
        return False
    tid = bedomd_at or rev.get("bedomd")
    if isinstance(tid, str):
        try:
            tid = datetime.fromisoformat(tid)
        except ValueError:
            return False
    return isinstance(tid, datetime) and tid >= datetime.now(UTC) - FARSK


async def farsk_revision(storage: Any, prospekt: dict[str, Any]) -> dict[str, Any] | None:
    """En bedömning som inte behöver göras om: prospektets egen (från en
    webbpoollista eller en tidigare research) eller poolens för domänen, om
    den är högst 30 dagar gammal. None annars. Kastar aldrig."""
    egen = prospekt.get("webbrevision")
    if _farsk(egen):
        return egen
    d = doman(prospekt.get("website"))
    if not d:
        return None
    try:
        rad = (await storage.webbpool_hamta([d])).get(d) or {}
    except Exception:  # noqa: BLE001 — utan pool görs bedömningen som förut
        return None
    rev = rad.get("webbrevision")
    if not isinstance(rev, dict):
        return None
    rev = {**rev, "webbniva": rad.get("webbniva") or rev.get("webbniva")}
    return rev if _farsk(rev, bedomd_at=rad.get("bedomd_at")) else None


async def bedom_en(rad: dict[str, Any], *, befintlig: dict[str, Any] | None = None) -> dict[str, Any]:
    """Revisionen för en poolrad, samma kedja som research: webbsignal →
    platshållare → webbrevision. Återanvänder en färsk revision (befintlig)."""
    from .platshallare import AVVECKLAT, ar_platshallare
    from .webbsignal import mat_webbplats

    if befintlig and befintlig.get("webbniva"):
        return befintlig
    url = rad["website"]
    fakta = await mat_webbplats(url)
    skal = None if fakta.get("svarar_inte") or fakta.get("http_status") else await ar_platshallare(fakta.get("url") or url)
    if skal == AVVECKLAT:
        return {"webbniva": "avvecklad", "platshallare": skal}
    if skal:
        fakta = {**fakta, "platshallare": skal}
    rev = await webbrevision.revidera(url, fakta)
    return {**rev, "webbniva": rev.get("webbniva") or "okand"}


async def bedom(storage: Any, domaner: list[str], tenant_id: str) -> int:
    """Bedömer domänerna under ett eget kredittak, inom dygnstaket. Antalet
    bedömda. Kastar aldrig."""
    from . import sidhamtning

    if not domaner or not aktiv():
        return 0
    idag = date.today()
    kvar = _dagstak() - _dagens.get(idag, 0)
    if kvar <= 0:
        logger.info("Webbpoolens dygnstak (%s) är nått; %s domäner väntar.", _dagstak(), len(domaner))
        return 0
    domaner = domaner[:kvar]
    rader = await storage.webbpool_hamta(domaner)
    # Två krediter per skärmbild, sju om stealth behövs (webbrevision).
    sidhamtning.starta(storage, tenant_id, tak=webbrevision.STEALTH_KREDITER * len(domaner),
                       webb_tak=2 * len(domaner))
    bedomda = 0
    for d in domaner:
        rad = rader.get(d)
        if not rad:
            continue
        try:
            rev = await bedom_en(rad)
        except Exception:  # noqa: BLE001
            logger.exception("Bedömningen av %s föll.", d)
            continue
        await storage.webbpool_spara({
            "doman": d,
            "webbniva": rev.pop("webbniva"),
            "webbrevision": rev or None,
            "bedomd_at": datetime.now(UTC),
        })
        bedomda += 1
    _dagens[idag] = _dagens.get(idag, 0) + bedomda
    return bedomda


# -- Fördelning --------------------------------------------------------------

def _signal(rad: dict[str, Any]) -> str:
    rev = rad.get("webbrevision") or {}
    niva = {"akut": "Akut", "dalig": "Dålig", "mycket_bra": "Inspiration"}.get(str(rad.get("webbniva")), "")
    detalj = rev.get("platshallare") or (rev.get("brister") or [None])[0]
    m = rev.get("modernitet")
    return " · ".join(str(x) for x in (niva, f"modernitet {m}/10" if m is not None else None, detalj) if x)


async def _veckolista(storage: Any, tenant_id: str, titel: str) -> dict[str, Any]:
    for lista in await storage.list_lead_lists(tenant_id, limit=200):
        if lista.get("titel") == titel and lista.get("kalla") == "webbpool":
            return lista
    ny = await storage.create_lead_list(tenant_id, titel=titel, icp={}, antal=200, kalla="webbpool")
    await storage.set_lead_list_status(tenant_id, ny["id"], status="klar")
    return ny


async def _lagg_i_lista(storage: Any, tenant: dict[str, Any], rader: list[dict[str, Any]], titel: str) -> int:
    from . import upptagna

    tenant_id = str(tenant["id"])
    sedda = await upptagna.hamta(storage, tenant_id)
    nya = []
    for rad in rader:
        if upptagna.upptagen(sedda, rad.get("company_name"), rad.get("orgnr")):
            continue
        sedda |= upptagna.bolagsnycklar([rad])
        nya.append(rad)
    lista = await _veckolista(storage, tenant_id, titel) if nya else None
    for rad in nya:
        await storage.add_lead_list_item(
            tenant_id, list_id=lista["id"], company_name=rad.get("company_name") or rad["doman"],
            website=rad.get("website"), ort=rad.get("ort"), orgnr=rad.get("orgnr"), lan=rad.get("lan"),
            postnr=rad.get("postnr"), webbniva=rad.get("webbniva"), webbrevision=rad.get("webbrevision"),
            source_name="webbpool", signal_detalj=_signal(rad),
        )
    # Även bolag som redan fanns hos mottagaren markeras: de ska inte prövas igen.
    await storage.webbpool_markera_fordelad(tenant_id, [r["doman"] for r in rader], lista["id"] if lista else None)
    return len(nya)


async def fordela(storage: Any) -> dict[str, int]:
    """Fördelar bedömda, ännu ej fördelade bolag till mottagarna. Antalet nya
    listrader per mottagare. Kastar aldrig."""
    if not aktiv() or not fordelning_pa():
        return {}
    ut: dict[str, int] = {}
    try:
        tenants = {k: t for t in await storage.list_tenants() for k in (str(t.get("slug") or ""), str(t["id"]))}
        vecka = date.today().isocalendar()
        for slug, lan in mottagare().items():
            tenant = tenants.get(slug)
            if not tenant:
                logger.warning("Webbpoolens mottagare %s finns inte.", slug)
                continue
            rader = await storage.webbpool_ofordelade(str(tenant["id"]), lan=lan, nivaer=list(LEADNIVAER))
            ut[slug] = await _lagg_i_lista(storage, tenant, rader, f"Webbleads vecka {vecka.week}, {vecka.year}")
        insp = os.environ.get("WEBBPOOL_INSPIRATION")
        if insp and tenants.get(insp):
            alla_lan = sorted({l for v in mottagare().values() for l in v} | set(_POSTNR_LAN.values()))
            rader = await storage.webbpool_ofordelade(str(tenants[insp]["id"]), lan=alla_lan, nivaer=["mycket_bra"])
            ut[f"{insp}:inspiration"] = await _lagg_i_lista(
                storage, tenants[insp], rader, f"Inspiration vecka {vecka.week}, {vecka.year}")
    except Exception:  # noqa: BLE001
        logger.exception("Webbpoolens fördelning föll.")
    return ut


async def efter_korning(storage: Any, korning: dict[str, Any], tenant_id: str) -> None:
    """Hela kedjan efter en körning: in, bedöm, fördela. Startas som en egen
    uppgift (asyncio.create_task) när körningen är klar och kastar aldrig.
    Taket: dör processen mitt i ligger raderna kvar obedömda i poolen och
    plockas upp av nästa körning som passerar samma domän."""
    domaner = await mata_in(storage, korning, tenant_id)
    await bedom(storage, domaner, tenant_id)
    await fordela(storage)


def demo() -> None:
    assert lan_ur_postnr("413 01") == "vastra-gotalands-lan"
    assert lan_ur_postnr("43491") == "hallands-lan"
    assert lan_ur_postnr("903 25") == "vasterbottens-lan"
    assert lan_ur_postnr("111 22") is None
    rad = bolagsrad({"company_name": "X AB", "website": "https://www.x.se/om", "contact_email": "vd@x.se",
                     "vd_namn": "Anna"}, "korning")
    assert rad["doman"] == "x.se" and rad["website"] == "https://www.x.se/"
    assert not set(PERSONFALT) & set(rad)
    assert ar_enskild_firma("820315-1234") and not ar_enskild_firma("556677-8899")
    assert bolagsrad({"company_name": "Kalles", "website": "https://k.se", "orgnr": "8203151234"}, "lista") is None
    print("webbpool: ok")


if __name__ == "__main__":
    demo()
