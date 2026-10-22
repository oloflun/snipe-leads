"""allabolag.se som registerkälla: hämtningen bakom merinfo.sok.

## Varför den finns (2026-10-15)

ScrapeGraph-kontot har en kredit kvar (gratisplanen slut, verifierat
2026-10-15), och merinfo blockerar direkthämtning (403). Varje list- och
bolagssida föll därför på "Insufficient credits", och körningarna slutade
långt under beställt antal (4 och 8 av 50). Antons beställning: leverera
beställt antal.

allabolag går att hämta direkt med en vanlig webbläsarförfrågan, och
sökresultatsidan bär hela träffen som JSON i `<script id="__NEXT_DATA__">`
(`props.pageProps.hydrationData.searchStore.companies`): 25 bolag per sida
med orgnr, adress, län och kommun, anställda, omsättning, hemsida,
bolagstelefon och -e-post, bransch och en kontaktperson med roll. Det är
allt urvalet i merinfo.sok läser, så ingen bolagssida behövs per bolag och
ingen hämtning kostar en kredit.

Samma affärsbeslut som för merinfo gäller: allabolags villkor medger inte
fri kopiering, och Anton har begärt pris på deras API
(docs/utkast-allabolag-api-forfragan.md). Därför hövlig hämtning (högst två
samtidiga, minst en sekund mellan anropen, sidcachen per kund i sju dygn),
och den här modulen byts mot API-hämtaren när avtalet finns. Bara
`tolka_sida`/`tolka_traff` är bundna till sidans form.

## Filtret, inte kontakten (Antons regel 1, 2026-10-04)

Registret väljer bolag. Kontaktpersonen på sökträffen blir aldrig ett leads
kontakt: den förs in i `personer` som i merinfo, och nedströms läses den
bara av `merinfo.vd_namn` (regel 15). Ensam-VD-undantaget (regel 7) kräver
att VD är den ENDA personen med roll, och en sökträff visar bara en person,
så det undantaget gäller inte allabolag-rader (merinfo.ensam_vd_telefon).

## Geofiltren (uppmätta 2026-10-15)

`county=<län utan "län">` ("Västerbotten", "Västra Götaland") och
`municipality=<kommun>` ("Umeå", "Mölndal") filtrerar; `page=<n>` bläddrar.
Upprepas en parameter (county=A&county=B) gäller bara den första, och
"A,B" ger noll träffar: varje län och kommun är därför en egen sökning.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

logger = logging.getLogger("snajp-support.leads.sources.allabolag")

BAS = "https://www.allabolag.se"
SOKADRESS = f"{BAS}/bransch-s%C3%B6k"

#: Sidor per (term, plats). allabolag bläddrar till 400 sidor à 25 bolag;
#: 40 sidor är 1 000 bolag per sökning, långt mer än en körning granskar.
MAX_LISTSIDOR = 40
#: Bolag som granskas (filter + Jev) per körning. Merinfos tak (90) var
#: satt efter betalda bolagssidor; här är listan gratis och bolagssidan
#: behövs inte, så en körning på 50 leads får bläddra hundratals bolag.
MAX_BOLAG = 600
#: Sökningar (term × plats). Varje kommun är en egen sökning (se modulens
#: docstring), så Göteborgsområdet ensamt är sju.
MAX_SOKNINGAR = 30

#: Breda B2B-sökord när kunden inte har någon bransch (merinfo.BRED_B2B:
#: företagstjänster, bygg, grossister). allabolags egna branschnamn, valda
#: 2026-10-15 på träffantal i Västerbotten: Konsulter 2 557, Byggmästare
#: 4 987, Grossister 1 193, Producenter 1 988. "Företagstjänster" gav 5.
BRED_B2B = ("Konsulter", "Byggmästare", "Grossister", "Producenter")

#: merinfos länsslugg → allabolags county-värde (länsnamnet utan "län" och
#: genitiv-s). Uppmätt 2026-10-15; "Västerbottens län" som värde ger noll.
LAN: dict[str, str] = {
    "blekinge-lan": "Blekinge",
    "dalarnas-lan": "Dalarna",
    "gavleborgs-lan": "Gävleborg",
    "gotlands-lan": "Gotland",
    "hallands-lan": "Halland",
    "jamtlands-lan": "Jämtland",
    "jonkopings-lan": "Jönköping",
    "kalmar-lan": "Kalmar",
    "kronobergs-lan": "Kronoberg",
    "norrbottens-lan": "Norrbotten",
    "orebro-lan": "Örebro",
    "ostergotlands-lan": "Östergötland",
    "skane-lan": "Skåne",
    "sodermanlands-lan": "Södermanland",
    "stockholms-lan": "Stockholm",
    "uppsala-lan": "Uppsala",
    "varmlands-lan": "Värmland",
    "vasterbottens-lan": "Västerbotten",
    "vasternorrlands-lan": "Västernorrland",
    "vastmanlands-lan": "Västmanland",
    "vastra-gotalands-lan": "Västra Götaland",
}

#: Cachenyckelns version: cachen bär den TOLKADE sidan (bolagslistan), inte
#: HTML-sidan (600 kB). Ändras tolkningen, höj versionen.
_CACHEVERSION = "#allabolag-v1"

_HEADERS = {
    # En vanlig webbläsare: allabolag svarar en tom skalsida på botsträngar.
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0 Safari/537.36"
    ),
    "accept": "text/html,application/xhtml+xml",
    "accept-language": "sv-SE,sv;q=0.9,en;q=0.5",
}
_TIMEOUT_S = 30.0

# Hövlig hämtning, som merinfo-kedjan: två samtidiga, en per sekund.
_SEM = asyncio.Semaphore(2)
_SENAST = [0.0]
MIN_INTERVALL_S = 1.0


# -- Geografi och sökord -------------------------------------------------------


@lru_cache(maxsize=1)
def _lan_namn() -> dict[str, str]:
    """allabolags county → länsnamnet i merinfos form ("Västerbottens län"),
    som webbpool.lan_for och kontrollen nedströms jämför mot."""
    from .merinfo import taxonomi

    namn = {l["slug"]: l["namn"] for l in taxonomi()["lan"]}
    return {county: namn[slug] for slug, county in LAN.items() if slug in namn}


@lru_cache(maxsize=1)
def _kommunnamn() -> dict[str, str]:
    """merinfos kommunslugg → kommunens namn, som allabolags municipality."""
    from .merinfo import taxonomi

    return {k["slug"]: k["namn"] for l in taxonomi()["lan"] for k in l["kommuner"]}


#: Skiljetecken mellan områden i samma fält ("Göteborg & Umeå", "Borås, Alingsås").
_OMRADESDELARE = re.compile(r"\s*(?:&|\+|/|;|,|\boch\b|\band\b)\s*", re.IGNORECASE)
_PARENTES = re.compile(r"(?P<yttre>[^()]*?)\s*\((?P<inre>[^()]+)\)\s*")


def valj_filter(termer: list[str], *, regioner: list[str] | tuple[str, ...] = ()) -> list[str | None] | None:
    """Kundens område → allabolags geofilter, ett per sökning:
    "county=Västerbotten", "municipality=Mölndal", eller None (hela landet).

    Samma tolkning av orden som merinfo.valj_platser (län, landsdelar som
    "Norrland", vardagsnamn och felstavningar), med en skillnad: kommuner
    slås inte ihop till sitt län. Hos merinfo var varje sökning en betald
    listsida och tre kommuner blev länet; här är sökningen gratis, och
    Göteborg + Mölndal ska vara just de två kommunerna, inte hela Västra
    Götaland (Antons beställning 2026-10-15). En kommun i ett län som också
    nämns täcks av länet.

    `regioner`: nycklar ur app/leads/geo.py REGIONER ("goteborg", "umea"),
    som blir sina kommuner. None = bara okända ord (anroparen faller
    tillbaka, som i merinfo)."""
    from ..geo import REGIONER
    from .merinfo import LANDSDELAR, ORTALIAS, _geoindex, _narmaste, _norm

    termer = [t for t in (str(x).strip() for x in termer) if t]
    termer += [k.namn for n in regioner if n in REGIONER for k in REGIONER[n].kommuner]
    if not termer:
        return [None]
    lan_index, kommun_index = _geoindex()
    kommunnamn = _kommunnamn()
    lan: list[str] = []
    kommuner: list[tuple[str, str]] = []

    def tolka(term: str) -> bool:
        hel = _norm(term).strip()
        n = ORTALIAS.get(hel.removesuffix(" lan").strip(), hel.removesuffix(" lan").strip())
        if n not in LANDSDELAR and n not in kommun_index and n not in lan_index and not hel.endswith(" lan"):
            gissning = _narmaste(n, kommun_index) or _narmaste(n, lan_index)
            if gissning:
                logger.info("allabolag: området %r tolkas som %r.", term, gissning)
                n = gissning
        if n in LANDSDELAR:
            lan.extend(LANDSDELAR[n])
        elif hel.endswith(" lan") and (n in lan_index or hel in lan_index):
            lan.append(lan_index.get(hel) or lan_index[n])
        elif n in kommun_index:
            kommuner.append(kommun_index[n])
        elif n in lan_index:
            lan.append(lan_index[n])
        else:
            return False
        return True

    # Kundens fritext bär ofta flera områden i ett fält: main 2026-10-22,
    # "Göteborg & Norrland (Umeå)" gav None och hela registret föll bort, så
    # körningen hängde på den öppna sökningen. Varje del tolkas för sig, och
    # en parentes preciserar: "Norrland (Umeå)" är Umeå, med Norrland som
    # reserv om parentesen inte är en ort.
    for term in termer:
        for del_ in _OMRADESDELARE.split(term):
            del_ = del_.strip()
            if not del_:
                continue
            m = _PARENTES.fullmatch(del_)
            if m:
                if not (tolka(m.group("inre")) or tolka(m.group("yttre"))):
                    logger.info("allabolag: området %r känns inte igen.", del_)
            elif not tolka(del_):
                logger.info("allabolag: området %r känns inte igen.", del_)
    ut = [f"county={LAN[l]}" for l in dict.fromkeys(lan) if l in LAN]
    ut += [
        f"municipality={kommunnamn[k]}"
        for k, l in dict.fromkeys(kommuner)
        if l not in lan and k in kommunnamn
    ]
    return list(dict.fromkeys(ut)) or None


def geofilter(plats: str | None) -> tuple[str, str] | None:
    """("county", "Västerbotten") ur "county=Västerbotten". Ett fritt namn
    ("Umeå", "Västerbottens län") tolkas med valj_filter när det ger exakt
    ett filter. None = hela landet."""
    if not plats:
        return None
    nyckel, _, varde = plats.partition("=")
    if nyckel in ("county", "municipality") and varde:
        return nyckel, varde
    filter_ = valj_filter([plats]) or []
    if len(filter_) != 1 or filter_[0] is None:
        raise ValueError(f"allabolag: {plats!r} är inte ett entydigt område ({filter_}).")
    return geofilter(filter_[0])


def valj_termer(termer: list[str], *, malgrupp: str | None = None) -> list[str]:
    """Kundens branschord → allabolags sökord (q), högst fyra.

    allabolags sökning matchar branschnamn, bolagsnamn och beskrivning, så
    kundens ord används som de står. Fraser delas som i merinfo
    ("e-utbildning & möblerfirmor" är två branscher), en mening eller en
    del längre än två ord används aldrig som sökord, och ett generiskt efterled stryks
    ("byggföretag" → "bygg"). Ord om VEM kunden säljer till ("B2B") är
    inget sökord. Tom lista = inget gick att använda (anroparen avgör om
    det blir den breda sökningen)."""
    from .merinfo import _EFTERLED, _EJ_SLUGG, _delfraser, _norm, _slug

    def ord_ur(fraser: list[str]) -> list[str]:
        ut: list[str] = []
        # En fras som går att dela söks bara i sina delar: "e-utbildning &
        # möblerfirmor" som ett sökord matchar ingenting.
        # En mening (fler än fem ord) är en målgruppsbeskrivning, inte en
        # bransch: "Företag med gamla och dåligt underhållna hemsidor" (Alunix)
        # gav annars sökorden "Företag med gamla" och "dåligt underhållna
        # hemsidor". Merinfo-kedjan gjorde samma avgränsning (valj_branscher).
        delade: list[str] = []
        for f in fraser:
            if len(str(f).split()) > 5:
                continue
            delar = _delfraser([f])
            delade += delar[1:] if len(delar) > 1 else delar
        for fras in delade:
            fras = re.sub(r"\s+", " ", str(fras)).strip(" .")
            ord_ = fras.split(" ")
            if not fras or len(ord_) > 2:
                continue
            slug = _slug(fras)
            if not slug or slug in _EJ_SLUGG or set(slug.split("-")) <= _EJ_SLUGG:
                continue
            if len(ord_) == 1:
                for led in _EFTERLED:
                    if _norm(fras).endswith(led) and len(fras) - len(led) >= 3:
                        fras = fras[: -len(led)]
                        break
            if fras.casefold() not in {u.casefold() for u in ut}:
                ut.append(fras)
        return ut

    ut = ord_ur(termer)
    if not ut and malgrupp:
        ut = ord_ur([malgrupp])
    return ut[:4]


def sokadress(term: str, plats: str | None, sida: int) -> str:
    param: dict[str, str] = {"q": term}
    geo = geofilter(plats)
    if geo:
        param[geo[0]] = geo[1]
    if sida > 1:
        param["page"] = str(sida)
    return f"{SOKADRESS}?{urlencode(param, quote_via=quote)}"


# -- Tolkning -----------------------------------------------------------------

_NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(?P<json>.*?)</script>', re.DOTALL)


def _text(v: object) -> str | None:
    s = str(v).strip() if v is not None else ""
    return s or None


def _heltal(v: object) -> int | None:
    """"12" → 12. Ett intervall ("1-4") eller skräp blir None: okänt, aldrig
    gissat (kontrollera fäller bara på känd data)."""
    s = str(v).strip() if v is not None else ""
    return int(s) if re.fullmatch(r"-?\d+", s) else None


def _postnr(adress: object) -> str | None:
    siffror = re.sub(r"\D", "", str((adress or {}).get("zipCode") or "")) if isinstance(adress, dict) else ""
    return f"{siffror[:3]} {siffror[3:]}" if len(siffror) == 5 else None


def _status(t: dict[str, Any]) -> str | None:
    """Status i merinfos ordalydelse: None för ett aktivt bolag (allabolag
    sätter ingen status på aktiva sökträffar), annars anmärkningen
    ("Konkurs inledd", "Likvidation beslutad"), som kontrollera fäller."""
    anm = [_text(s.get("desc")) for s in t.get("statusRemarks") or [] if isinstance(s, dict)]
    anm = [a for a in anm if a]
    if anm:
        return "; ".join(dict.fromkeys(anm))
    status = t.get("status")
    if isinstance(status, dict):
        if str(status.get("statusCode") or status.get("status") or "").upper() == "ACTIVE":
            return "Aktiv"
        return _text(status.get("description")) or _text(status.get("statusCode"))
    return _text(status)


def tolka_traff(t: dict[str, Any], url: str) -> dict[str, Any]:
    """En sökträff i exakt merinfo.tolka_bolag-formen. Saknade fält blir
    None, aldrig gissade. `url` är sökadressen, för träffar utan orgnr."""
    from .merinfo import ROLLORDNING

    siffror = re.sub(r"\D", "", str(t.get("orgnr") or ""))
    orgnr = f"{siffror[:6]}-{siffror[6:]}" if len(siffror) == 10 else None
    bolagsform = _text((t.get("companyType") or {}).get("name")) if isinstance(t.get("companyType"), dict) else None
    if len(siffror) > 10:
        # En enskild näringsidkare har inget eget organisationsnummer:
        # allabolag visar ägarens personnummer med ett löpnummer efter
        # (14 siffror, uppmätt 2026-10-15). Personnumret förs inte vidare
        # (merinfo maskerar det också), men formen är känd: enskild firma,
        # som kontrollera och fördelningen fäller (NIX, MFL 19 §).
        bolagsform = bolagsform or "Enskild firma"

    personer = []
    kp = t.get("contactPerson")
    if isinstance(kp, dict) and kp.get("type") in (None, "Person") and _text(kp.get("name")) and _text(kp.get("role")):
        roll = _text(kp["role"])
        if roll.casefold() in ROLLORDNING:
            personer.append({"roll": roll, "namn": _text(kp["name"])})

    lage = t.get("location") if isinstance(t.get("location"), dict) else {}
    county = _text(lage.get("county"))
    oms = _heltal(t.get("revenue"))
    epost = _text(t.get("email"))
    bransch = t.get("currentIndustry") if isinstance(t.get("currentIndustry"), dict) else {}
    return {
        # Namnet bolaget visar ("Sandströms Schakt AB") före det registrerade
        # ("… Aktiebolag"): det är så bolaget skriver sig på sin sajt, där
        # namnkontrollen och orgnr-uppslaget jämför (uppmätt 2026-10-15).
        "company_name": _text(t.get("name")) or _text(t.get("legalName")),
        "orgnr": orgnr,
        "personer": personer,
        # Bolagets nummer i katalogen (bolagsnivå), som merinfos listnummer.
        "telefon": _text(t.get("phone")) or _text(t.get("mobile")),
        # Besöksadressen först: postadressen är ofta en c/o-box i en annan stad.
        "postnr": _postnr(t.get("visitorAddress")) or _postnr(t.get("postalAddress")),
        "ort": _text(lage.get("municipality")),
        "lan": _lan_namn().get(county) if county else None,
        "anstallda": _heltal(t.get("employees") if t.get("employees") is not None else t.get("numberOfEmployees")),
        # allabolag anger omsättningen i tkr, merinfo-formen i kronor.
        "omsattning": oms * 1000 if oms is not None else None,
        "epost": epost if epost and "@" in epost else None,
        "website": _text(t.get("homePage")),
        "status": _status(t),
        "bolagsform": bolagsform,
        # allabolags branschkoder är katalogens egna, inte SNI: koden lämnas
        # tom och branschnamnet står som sni_namn (det kontrollen läser).
        "sni": None,
        "sni_namn": _text(bransch.get("name")),
        "verksamhet": _text(t.get("description")) or _text(bransch.get("description")),
        # allabolag.se/<orgnr> leder till bolagets sida (uppmätt 2026-10-15).
        "url": f"{BAS}/{siffror}" if orgnr else url,
    }


def tolka_sida(html: str, url: str) -> dict[str, Any] | None:
    """{"hits", "pages", "bolag"} ur sökresultatsidan, eller None när sidan
    inte bär sökresultatet (en annan sida, en spärr, en ändrad form)."""
    m = _NEXT_DATA.search(html or "")
    if not m:
        return None
    try:
        data = json.loads(m.group("json"))
        traffar = data["props"]["pageProps"]["hydrationData"]["searchStore"]["companies"]
    except (ValueError, KeyError, TypeError):
        return None
    if not isinstance(traffar, dict) or not isinstance(traffar.get("companies"), list):
        return None
    return {
        "hits": _heltal(traffar.get("hits")) or 0,
        "pages": _heltal(traffar.get("pages")) or 0,
        "bolag": [tolka_traff(t, url) for t in traffar["companies"] if isinstance(t, dict)],
    }


# -- Hämtning -----------------------------------------------------------------


async def _hamta_html(url: str) -> tuple[str | None, str | None]:
    """Sidans HTML, rå. research_tools._hamta_direkt gör om HTML till text
    och kapar den, och då försvinner __NEXT_DATA__; därför en egen hämtning.
    Ett försök till efter fem sekunder vid 429 eller serverfel. Kastar aldrig."""
    import httpx

    from ...tls import ssl_kontext

    fel: str | None = None
    for forsok in range(2):
        async with _SEM:
            while (vanta := _SENAST[0] + MIN_INTERVALL_S - time.monotonic()) > 0:
                await asyncio.sleep(vanta)
            _SENAST[0] = time.monotonic()
            try:
                async with httpx.AsyncClient(
                    verify=ssl_kontext(), timeout=_TIMEOUT_S, follow_redirects=True, headers=_HEADERS
                ) as klient:
                    svar = await klient.get(url)
            except httpx.HTTPError as e:
                fel = f"allabolag: {type(e).__name__}"
                continue
        if svar.status_code == 429 or svar.status_code >= 500:
            fel = f"allabolag: HTTP {svar.status_code}"
            if forsok == 0:
                await asyncio.sleep(5)
            continue
        if svar.status_code >= 400:
            return None, f"allabolag: HTTP {svar.status_code}"
        return svar.text, None
    return None, fel


async def hamta_sida(url: str) -> tuple[dict[str, Any] | None, str | None]:
    """Den tolkade sökresultatsidan, via sidcachen per kund (samma lager och
    livslängd som merinfos listsidor, sidhamtning.LIVSLANGD["lista"]).
    Hämtningen är gratis och räknas därför inte mot körningens kredittak.
    Med direkthämtningen av (LEADS_DIREKTHAMTNING tom, testsviten) läses
    bara cachen. Fel cachas inte: nästa försök kostar inget. Kastar aldrig."""
    from .. import sidhamtning

    kontext = sidhamtning.aktuell()
    lager = kontext.storage if kontext and kontext.tenant_id else None
    nyckel = url + _CACHEVERSION
    if lager is not None:
        try:
            rad = await lager.get_sidcache(kontext.tenant_id, nyckel)
        except Exception:  # noqa: BLE001 — en trasig cacheläsning kostar bara en hämtning
            logger.exception("Sidcachen gick inte att läsa för %s", url)
            rad = None
        if rad and rad.get("innehall") and sidhamtning._farsk(rad, "lista"):
            try:
                data = json.loads(rad["innehall"])
                kontext.cachetraffar += 1
                return data, None
            except ValueError:
                pass
    if not sidhamtning._direkt_forst():
        return None, "direkthämtning avstängd"
    html, fel = await _hamta_html(url)
    if html is None:
        logger.warning("allabolag: %s gick inte att hämta (%s).", url, fel)
        return None, fel
    data = tolka_sida(html, url)
    if data is None:
        logger.warning("allabolag: %s bar inget sökresultat.", url)
        return None, "allabolag: sidan bar inget sökresultat"
    if lager is not None:
        try:
            await lager.put_sidcache(
                kontext.tenant_id, nyckel, innehall=json.dumps(data, ensure_ascii=False), fel=None
            )
        except Exception:  # noqa: BLE001
            logger.exception("Sidcachen gick inte att skriva för %s", url)
    return data, None


async def sok_sida(term: str, plats: str | None, sida: int) -> list[dict[str, Any]] | None:
    """En sökresultatsida som bolag i merinfo.tolka_bolag-formen. [] = inga
    (fler) träffar, None = sidan gick inte att hämta. `plats` är ett filter
    ur valj_filter ("county=Västerbotten") eller ett entydigt områdesnamn."""
    url = sokadress(term, plats, sida)
    data, _fel = await hamta_sida(url)
    if data is None:
        return None
    if data.get("pages") and sida > data["pages"]:
        return []
    return list(data.get("bolag") or [])


async def orgnr_traffar(namn: str) -> list[dict[str, str | None]] | None:
    """Namnsökningen i orgnr_uppslag.valj_traff-formen: {namn, orgnr, ort}.
    Enskilda firmor får orgnr None (personnumret förs inte vidare)."""
    bolag = await sok_sida(namn, None, 1)
    if bolag is None:
        return None
    return [{"namn": b["company_name"], "orgnr": b["orgnr"], "ort": b["ort"]} for b in bolag]


# -- Självkontroll ----------------------------------------------------------------

FIXTUR = Path(__file__).resolve().parents[3] / "tests" / "leads" / "fixtures" / "allabolag_redovisning_molndal_2026-10-15.html"
FIXTUR_URL = f"{SOKADRESS}?q=redovisning&municipality=M%C3%B6lndal"


def demo() -> None:
    """Översättningen mot en sparad riktig sida (redovisning i Mölndal,
    hämtad 2026-10-15). Kör: python -m app.leads.sources.allabolag"""
    from .merinfo import ensam_vd_telefon, kontrollera, vd_namn

    data = tolka_sida(FIXTUR.read_text(encoding="utf-8"), FIXTUR_URL)
    assert data and data["hits"] == 29 and data["pages"] == 2 and len(data["bolag"]) == 25, data and data["hits"]
    per_namn = {b["company_name"]: b for b in data["bolag"]}
    nycklar = set(next(iter(per_namn.values())))
    assert all(set(b) == nycklar for b in data["bolag"])

    a = per_namn["Account i Mölndal AB"]
    assert a["orgnr"] == "556477-7083" and a["website"] == "http://www.revisorn.com"
    assert (a["anstallda"], a["omsattning"]) == (4, 5_185_000)
    assert (a["ort"], a["lan"], a["postnr"]) == ("Mölndal", "Västra Götalands län", "431 67")
    assert a["epost"] and a["telefon"] and a["url"] == f"{BAS}/5564777083"
    assert vd_namn(a) is None, "en ordförande är aldrig VD"

    vd = per_namn["Lindome Lön och Redovisning AB"]
    assert vd["personer"][0]["roll"] == "Verkställande direktör" and vd_namn(vd)
    assert ensam_vd_telefon({**vd, "anstallda": 1}) is None, "regel 7 kräver hela personlistan"

    ef = per_namn["RÅD & REDOVISNING, ANNA EXEMPEL"]
    assert ef["orgnr"] is None and ef["bolagsform"] == "Enskild firma"
    assert "Enskild firma" in (kontrollera(ef, {}, None) or "")
    assert per_namn["Axblom & Thöresson redovisning aktiebolag"]["anstallda"] is None  # "1-4"
    assert per_namn["ALERT REDOVISNING HANDELSBOLAG"]["orgnr"] == "916843-9314"
    # Postadressen när besöksadressen saknas.
    assert per_namn["POP Redovisning och Revision AB"]["postnr"] == "431 34"

    assert valj_filter(["Göteborg", "Mölndal"]) == ["municipality=Göteborg", "municipality=Mölndal"]
    assert valj_filter(["Norrland"]) == [
        "county=Norrbotten", "county=Västerbotten", "county=Jämtland", "county=Västernorrland", "county=Gävleborg",
    ]
    assert valj_filter(["Västerbottens län", "Umeå"]) == ["county=Västerbotten"]
    assert valj_filter([], regioner=["goteborg"])[:2] == ["municipality=Göteborg", "municipality=Mölndal"]
    assert valj_filter([]) == [None] and valj_filter(["Atlantis"]) is None
    assert valj_termer(["Byggföretag", "B2B"]) == ["Bygg"]
    assert valj_termer(["e-utbildning & möblerfirmor"]) == ["e-utbildning", "möbler"]
    assert sokadress("båt", "county=Västerbotten", 2) == f"{SOKADRESS}?q=b%C3%A5t&county=V%C3%A4sterbotten&page=2"
    print(f"allabolag: {len(data['bolag'])} träffar översatta, geofilter och sökord stämmer.")


if __name__ == "__main__":
    demo()
