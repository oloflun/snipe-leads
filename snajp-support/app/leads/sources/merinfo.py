"""Merinfo som registerkälla, hämtad via ScrapeGraphAI. TILLFÄLLIG.

## Varför den finns, och varför den är tillfällig

Antons arbetsflöde (2026-10-01): leadslistor och Iris-körningar ska börja i
ett REGISTER, inte i jobbannonser. En lista på "bygg i Norrland" ska vara
byggbolag med säte i Norrland — det vet ett register, en annons vet bara att
någon rekryterar. Merinfo har trädet färdigt:

    /sitemap/bransch                                   → bransch
    /sitemap/bransch/<län>/alla-kommuner/<bransch>      → län, dess kommuner
    /<bransch>/<kommun>/foretag/<sida>                  → specifik sökning
    /<bransch>/<län>/foretag/<sida>                     → bred sökning
    /foretag/<Namn>-<orgnr>/<id>                        → bolaget: styrelse,
                                                           telefon, adress,
                                                           anställda, omsättning

merinfos villkor (/villkor, läst 2026-10-01) förbjuder kopiering utan
skriftligt samtycke, och databasen kan omfattas av katalogskyddet i
upphovsrättslagen. Anton har begärt pris på deras API och på allabolags, och
valde den här vägen under tiden — ett affärsbeslut, inte ett kodbeslut. Därför:

* Källan är AV tills `LEADS_MERINFO=scrapegraph` sätts, per miljö.
* Hövlig hämtning: högst två samtidiga anrop, minst en sekund mellan dem,
  och varje sida hämtas en gång per process (cache).
* Byts mot API-hämtaren när avtalet finns. Tolkningen nedan är det enda som
  är bundet till HTML/markdown; urvalet (bransch, geografi, kontaktkrav,
  rangordning) står kvar oförändrat.

## Merinfo är ett filter, inte en kontaktkälla (Anton 2026-10-04)

Merinfo väljer BOLAG på bransch, geografi, storlek och omsättning. Jev
klassar dem mot kundens kriterier som första filter. Merinfos personer och
telefonnummer blir aldrig ett leads kontakt: bolagsnumret går inte att knyta
till en viss person, och styrelseledamöter kontaktas inte.

* Iris (`lage="iris"`): bolagets webbplats letas upp (merinfos fält, annars
  ett uppslag); kontaktperson, roll och händelser hämtas därifrån i
  researchen. Utan webbplats går körningen vidare till nästa bolag.
* Listor (`lage="lista"`): en rad kräver VD:ns mejl eller telefon, och bara
  om uppgiften går att knyta till VD (discovery.hamta_vd_kontakt). VD:ns
  namn kommer från merinfo, uppgiften från bolagets egen webbplats. Merinfos
  personsidor används inte: de är privatpersonsidor (bostad, familj) och
  numren ligger bakom betalvägg (kontrollerat 2026-10-04).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import unicodedata
from pathlib import Path
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import unquote

logger = logging.getLogger("snajp-support.leads.sources.merinfo")

BAS = "https://www.merinfo.se"
TAXONOMI_FIL = Path(__file__).with_name("merinfo_taxonomi.json")

MAX_LISTSIDOR = 40          # per (bransch, plats)
MAX_BOLAGSSIDOR = 90        # tak per körning, oavsett antal



def aktiv() -> bool:
    return os.environ.get("LEADS_MERINFO", "").strip().lower() == "scrapegraph"


# -- Hämtning ---------------------------------------------------------------


async def hamta(url: str, *, fas: str = "bolag") -> str | None:
    """Sidans markdown, eller None. Kastar aldrig. merinfo blockerar
    direkthämtning, så sidan går via ScrapeGraph — genom sidhamtning, som
    cachar per kund och räknar mot körningens kredittak (plan 2026-10-05)."""
    from .. import sidhamtning

    md, fel, _via = await sidhamtning.hamta(url, fas=fas, direkt=False)
    if md is None:
        logger.warning("merinfo: %s gick inte att hämta (%s).", url, fel)
    return md


def listsida_url(bransch: str, plats: str | None, sida: int) -> str:
    return f"{BAS}/{bransch}/{plats}/foretag/{sida}" if plats else f"{BAS}/{bransch}/foretag/{sida}"


# -- Tolkning ---------------------------------------------------------------

_LISTRAD = re.compile(
    r"^#{2,3}\s+\[\s*(?P<namn>.+?)\s*\]\((?P<url>https://www\.merinfo\.se/foretag/[^)\s]+)\)",
    re.MULTILINE,
)
_TEL = re.compile(r"\[\s*(?:__\s*)?(?P<visning>0[\d][\d \-]{5,})\s*\]\(tel:")
_ORGNR_I_URL = re.compile(r"-(\d{10})/[\w-]+/?$")


def _orgnr(tio: str | None) -> str | None:
    return f"{tio[:6]}-{tio[6:]}" if tio and len(tio) == 10 else None


def tolka_lista(md: str) -> list[dict[str, Any]]:
    """Listsidans rader: namn, bolagssida, orgnr och telefon (om listad)."""
    traffar = list(_LISTRAD.finditer(md))
    rader: list[dict[str, Any]] = []
    for i, m in enumerate(traffar):
        slut = traffar[i + 1].start() if i + 1 < len(traffar) else len(md)
        tel = _TEL.search(md, m.end(), slut)
        url = m.group("url")
        orgnr = _ORGNR_I_URL.search(unquote(url))
        rader.append(
            {
                "company_name": m.group("namn").strip(),
                "url": url,
                "orgnr": _orgnr(orgnr.group(1) if orgnr else None),
                "telefon": tel.group("visning").strip() if tel else None,
            }
        )
    return rader


#: Rollerna i beslutsordning. Suppleanter och revisorer är aldrig kontakt.
ROLLORDNING = (
    "verkställande direktör",
    "vd",
    "extern verkställande direktör",
    "innehavare",
    "ordförande",
    "styrelseordförande",
    "komplementär",
    "bolagsman",
    "styrelseledamot",
    "ledamot",
)
_ROLL = re.compile(
    r"^\s*(?P<roll>[A-ZÅÄÖa-zåäö][\wåäöÅÄÖ .\-]{1,45}?):\s*\n\s*\[\s*(?P<namn>[^\]\n]+?)\s*\]\(https://www\.merinfo\.se/person/",
    re.MULTILINE,
)


def _falt(md: str, etikett: str) -> str | None:
    m = re.search(rf"^\s*{etikett}\s*:?\s*\n\s*(?:__\s*)?(?P<v>[^\n]+)", md, re.MULTILINE)
    return m.group("v").strip() if m else None


def _heltal(text: str | None) -> int | None:
    siffror = re.sub(r"[^\d]", "", text or "")
    return int(siffror) if siffror else None


def tolka_bolag(md: str, url: str) -> dict[str, Any]:
    """Bolagssidans fält. Saknade fält blir None, aldrig gissade."""
    namn = re.search(r"^#\s+\[(?P<n>.+?)\]\(", md, re.MULTILINE)
    orgnr = re.search(r"Org\.nr:\s*(\d{6}-\d{4})", md)

    personer = []
    for m in _ROLL.finditer(md):
        roll = m.group("roll").strip()
        if roll.casefold() in ROLLORDNING:
            personer.append((ROLLORDNING.index(roll.casefold()), roll, m.group("namn").strip()))
    personer.sort()

    tel = _TEL.search(md)
    adress = re.search(r"##\s*Adress\s*\n(?P<blk>(?:.*\n){1,6})", md)
    postort = re.search(r"(?P<postnr>\d{3} \d{2})\s+(?P<ort>[^\n\[]+)", adress.group("blk")) if adress else None

    anstallda = re.search(r"Antal anställda:\s*\n\s*(\d[\d ]*)\s*st", md)
    oms = re.search(r"^Omsättning\s+(?P<v>-?[\d ]+)\s*tkr", md, re.MULTILINE)

    epost = _falt(md, "E-post")
    hemsida = _falt(md, "Hemsida")
    hemsida_url = re.search(r"(https?://[^\s\])]+|www\.[^\s\])]+)", hemsida or "")
    sni = re.search(r"^\s*\*\s*(?P<kod>\d{5})\s*\[(?P<namn>[^\]]+)\]", md, re.MULTILINE)
    verksamhet = re.search(r"###\s*Verksamhetsbeskrivning\s*\n\s*(?P<t>[^\n]+)", md)

    return {
        "company_name": namn.group("n").strip() if namn else None,
        "orgnr": orgnr.group(1) if orgnr else None,
        "personer": [{"roll": r, "namn": n} for _, r, n in personer],
        "telefon": tel.group("visning").strip() if tel else None,
        "postnr": postort.group("postnr") if postort else None,
        "ort": (_falt(md, "Kommunsäte") or (postort.group("ort").strip() if postort else None)),
        "lan": _falt(md, "Länssäte"),
        "anstallda": _heltal(anstallda.group(1)) if anstallda else None,
        "omsattning": (_heltal(oms.group("v")) * 1000) if oms and _heltal(oms.group("v")) is not None else None,
        "epost": epost if epost and "@" in epost and "lägg till" not in epost.casefold() else None,
        "website": hemsida_url.group(1) if hemsida_url else None,
        "status": _falt(md, "Status"),
        "bolagsform": _falt(md, "Bolagsform"),
        "sni": sni.group("kod") if sni else None,
        "sni_namn": sni.group("namn").strip() if sni else None,
        "verksamhet": verksamhet.group("t").strip() if verksamhet else None,
        "url": url,
    }


def bolagsfakta_text(md: str, url: str) -> str:
    """Bolagssidan som källmaterial, utan personer och telefonnummer.

    Registret är ett filter, inte en kontaktkälla (Antons regel 1,
    2026-10-04): det som når researchprompten är bolagsfakta, aldrig namn
    eller nummer som modellen kan göra till leadets kontakt."""
    b = tolka_bolag(md, url)
    falt = (
        ("Bolag", b.get("company_name")),
        ("Organisationsnummer", b.get("orgnr")),
        ("Postadress", " ".join(filter(None, [b.get("postnr"), b.get("ort")])) or None),
        ("Antal anställda", b.get("anstallda")),
        ("Omsättning (kr)", b.get("omsattning")),
        ("Bolagsform", b.get("bolagsform")),
        ("Status", b.get("status")),
        ("Bransch", b.get("sni_namn")),
        ("Verksamhet", b.get("verksamhet")),
        ("Webbplats enligt registret", b.get("website")),
    )
    return "\n".join(f"{namn}: {varde}" for namn, varde in falt if varde not in (None, ""))


# -- Trädet (bransch + geografi) ---------------------------------------------

_SITEMAPLANK = re.compile(
    r"\[\s*(?P<namn>[^\]\n]+?)\s*\]\(https://www\.merinfo\.se/sitemap/bransch/(?P<lan>[\w-]+)/alla-kommuner/(?P<slug>[\w-]+)\)"
)
_KOMMUNLANK = re.compile(
    r"\[\s*(?P<namn>[^\]\n]+?)\s*\]\(https://www\.merinfo\.se/byggbranschen/(?P<slug>[\w-]+)/foretag/1\)"
)


async def bygg_taxonomi() -> dict[str, Any]:
    """Läser merinfos sitemap EN gång och skriver trädet till JSON som
    checkas in — körningarna ska inte bero på att sitemapen svarar."""
    topp = await hamta(f"{BAS}/sitemap/bransch")
    if not topp:
        raise RuntimeError("merinfo: sitemapen gick inte att hämta.")
    branscher = {m.group("slug"): m.group("namn") for m in _SITEMAPLANK.finditer(topp) if m.group("lan") == "alla-lan"}
    bygg = await hamta(f"{BAS}/sitemap/bransch/alla-lan/alla-kommuner/byggbranschen") or ""
    lan = {m.group("lan"): m.group("namn") for m in _SITEMAPLANK.finditer(bygg)
           if m.group("lan") != "alla-lan" and m.group("slug") == "byggbranschen"}
    ut_lan = []
    for slug, namn in sorted(lan.items()):
        sida = await hamta(f"{BAS}/sitemap/bransch/{slug}/alla-kommuner/byggbranschen") or ""
        kommuner = {m.group("slug"): m.group("namn") for m in _KOMMUNLANK.finditer(sida) if m.group("slug") != slug}
        ut_lan.append({"slug": slug, "namn": namn, "kommuner": [{"slug": s, "namn": n} for s, n in sorted(kommuner.items())]})
    return {
        "kalla": f"{BAS}/sitemap/bransch",
        "branscher": [{"slug": s, "namn": n} for s, n in sorted(branscher.items())],
        "lan": ut_lan,
    }


_TAXONOMI: dict[str, Any] | None = None


def taxonomi() -> dict[str, Any]:
    global _TAXONOMI
    if _TAXONOMI is None:
        _TAXONOMI = json.loads(TAXONOMI_FIL.read_text(encoding="utf-8"))
    return _TAXONOMI


def _norm(text: str) -> str:
    bas = unicodedata.normalize("NFKD", str(text or "").casefold())
    return "".join(t for t in bas if not unicodedata.combining(t))


_STOPPORD = {
    "och", "med", "av", "for", "inom", "utom", "samt", "via", "annan", "annat", "ovrig", "ovriga",
    "ovrigt", "bolag", "foretag", "branschen", "bransch", "verksamhet", "sverige", "ab", "i", "pa",
}


#: Generiska efterled i sammansättningar: 'byggföretag' handlar om bygg.
_EFTERLED = ("foretagen", "foretag", "bolagen", "bolag", "firmor", "firma", "branschen", "bransch", "verksamhet")


def _stammar(text: str) -> list[str]:
    """Grov svensk stam: ordet utan generiskt efterled, kapat med
    böjningsändelsen. 'konsulter' → 'konsul', 'byggföretag' → 'bygg'.
    Två bokstäver ('it') står kvar."""
    ut = []
    for w in re.findall(r"[a-z0-9]+", _norm(text)):
        for led in _EFTERLED:
            if w.endswith(led) and len(w) - len(led) >= 3:
                w = w[: -len(led)]
                break
        if len(w) >= 2 and w not in _STOPPORD:
            ut.append(w if len(w) <= 4 else w[: max(4, len(w) - 3)])
    return ut


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _norm(text)).strip("-")


def valj_branscher(termer: list[str]) -> list[str]:
    """Kundens branschord → merinfos branschsluggar, en per ord, högst tre.

    Matchningen är ordstammar mot sitemapens namn; vid lika poäng vinner det
    kortaste (bredaste) namnet, så 'Bygg' blir Byggbranschen och inte
    'Byggande av bostadshus och andra byggnader'. Ett ord utan träff
    provas som egen slugg ('golvläggare' → /golvlaggare/…), eftersom
    merinfos listor har finare branscher än sitemapen visar.
    ponytail: stammatchning, inget LLM; byt mot ett modellval när en kund
    beskriver branschen i fraser som ingen stam träffar."""
    ut: list[str] = []
    for term in termer:
        stammar = _stammar(term)
        if not stammar:
            continue
        bast: tuple[float, int, str] | None = None
        for b in taxonomi()["branscher"]:
            ord_ = re.findall(r"[a-z0-9]+", _norm(b["namn"]))
            traff = sum(1 for s in stammar if any(w.startswith(s) or (len(s) >= 4 and s in w) for w in ord_))
            if traff:
                kandidat = (traff / len(stammar), -len(b["namn"]), b["slug"])
                if bast is None or kandidat > bast:
                    bast = kandidat
        # Egen slugg bara för ett branschord, aldrig för en mening: Alunix
        # målgrupp ("Företag med gamla … hemsidor") blev annars en påhittad
        # merinfo-bransch, noll träffar och ett "ärligt nej" i stället för
        # reservkedjan (provkörningen 2026-10-04).
        ensamt_ord = len(re.findall(r"[a-z0-9]+", _norm(term))) <= 2
        slug = bast[2] if bast and bast[0] >= 0.5 else (_slug(term) if ensamt_ord else None)
        if slug and slug not in ut:
            ut.append(slug)
    return ut[:3]


#: Landsdelar och vanliga regionnamn → län. Det är här "flera sammanhängande
#: områden" blir ett bredare filter.
LANDSDELAR: dict[str, tuple[str, ...]] = {
    "norrland": ("norrbottens-lan", "vasterbottens-lan", "jamtlands-lan", "vasternorrlands-lan", "gavleborgs-lan"),
    "norra sverige": ("norrbottens-lan", "vasterbottens-lan", "jamtlands-lan", "vasternorrlands-lan", "gavleborgs-lan"),
    "svealand": ("stockholms-lan", "uppsala-lan", "sodermanlands-lan", "vastmanlands-lan", "orebro-lan", "varmlands-lan", "dalarnas-lan"),
    "malardalen": ("stockholms-lan", "uppsala-lan", "sodermanlands-lan", "vastmanlands-lan", "orebro-lan"),
    "vastsverige": ("vastra-gotalands-lan", "hallands-lan"),
    "vastkusten": ("vastra-gotalands-lan", "hallands-lan"),
    "sydsverige": ("skane-lan", "blekinge-lan"),
    "smaland": ("jonkopings-lan", "kronobergs-lan", "kalmar-lan"),
    "stockholmsomradet": ("stockholms-lan",),
    "storstockholm": ("stockholms-lan",),
    "goteborgsomradet": ("vastra-gotalands-lan",),
    "storgoteborg": ("vastra-gotalands-lan",),
}


def _geoindex() -> tuple[dict[str, str], dict[str, tuple[str, str]]]:
    lan: dict[str, str] = {}
    kommuner: dict[str, tuple[str, str]] = {}
    for l in taxonomi()["lan"]:
        namn = _norm(l["namn"])
        for nyckel in {namn, namn.removesuffix(" lan"), namn.removesuffix("s lan"), l["slug"]}:
            lan[nyckel.strip()] = l["slug"]
        for k in l["kommuner"]:
            kommuner[_norm(k["namn"])] = (k["slug"], l["slug"])
    return lan, kommuner


def valj_platser(termer: list[str]) -> list[str | None] | None:
    """Kundens områden → merinfos platssluggar, enligt Antons regel:

    * inget område                         → [None] (hela Sverige)
    * ett län eller en landsdel            → länen, bred sökning
    * två kommuner                         → två separata sökningar
    * tre eller fler kommuner i samma län  → länet (sammanhängande område)
    * en kommun i ett län som också nämns  → länet täcker den
    * bara okända ord                      → None (anroparen faller tillbaka
      i stället för att söka i hela landet på en felstavning)
    """
    termer = [t for t in (str(x).strip() for x in termer) if t]
    if not termer:
        return [None]
    lan_index, kommun_index = _geoindex()
    lan: list[str] = []
    per_lan: dict[str, list[str]] = {}
    for term in termer:
        hel = _norm(term).strip()
        n = hel.removesuffix(" lan").strip()
        # Kommunen före länet: "Stockholm" är staden, "Stockholms län" länet.
        if n in LANDSDELAR:
            lan += list(LANDSDELAR[n])
        elif hel.endswith(" lan") and (n in lan_index or hel in lan_index):
            lan.append(lan_index.get(hel) or lan_index[n])
        elif n in kommun_index:
            kslug, lslug = kommun_index[n]
            per_lan.setdefault(lslug, [])
            if kslug not in per_lan[lslug]:
                per_lan[lslug].append(kslug)
        elif n in lan_index:
            lan.append(lan_index[n])
        else:
            logger.info("merinfo: området %r känns inte igen.", term)
    for lslug, kslugs in per_lan.items():
        if lslug in lan:
            continue
        if len(kslugs) >= 3:
            lan.append(lslug)
        else:
            lan += kslugs
    platser = list(dict.fromkeys(lan))
    return platser or None


# -- Urval: kontaktkrav, rangordning, sökning ---------------------------------


def _intervall(icp: dict[str, Any], profil: dict[str, Any] | None) -> tuple[int | None, int | None]:
    p = profil or {}
    storlek = icp.get("size") or {}
    lo = p.get("anstallda_min") if p.get("anstallda_min") is not None else storlek.get("anstallda_min")
    hi = p.get("anstallda_max") if p.get("anstallda_max") is not None else storlek.get("anstallda_max")
    return lo, hi


def kontrollera(b: dict[str, Any], icp: dict[str, Any], profil: dict[str, Any] | None) -> str | None:
    """None = kvalificerat för listan. Annars skälet. Bara känd data fäller."""
    from ..forfilter import ar_enskild_firma

    if not b.get("company_name"):
        return "Bolagssidan gick inte att läsa."
    if b.get("status") and "aktiv" not in b["status"].casefold():
        return f"Inte aktivt: {b['status']}."
    if ar_enskild_firma(b.get("orgnr")) or "enskild" in str(b.get("bolagsform") or "").casefold():
        return "Enskild firma: personuppgifter, och e-post kräver förhandssamtycke (MFL 19 §)."
    lo, hi = _intervall(icp, profil)
    antal = b.get("anstallda")
    if isinstance(antal, int):
        if hi is not None and antal > hi:
            return f"För stort: {antal} anställda (högst {hi})."
        if lo is not None and antal < lo:
            return f"För litet: {antal} anställda (minst {lo})."
    text = _norm(f"{b.get('verksamhet') or ''} {b.get('sni_namn') or ''} {b.get('company_name') or ''}")
    for u in [*(icp.get("exclude_industries") or []), *((profil or {}).get("undvik_branscher") or [])]:
        if any(s in text for s in _stammar(u)):
            return f"Bransch kunden undviker: {u}."
    storlek = icp.get("size") or {}
    lo_oms = (profil or {}).get("omsattning_min", storlek.get("omsattning_min"))
    hi_oms = (profil or {}).get("omsattning_max", storlek.get("omsattning_max"))
    oms = b.get("omsattning")
    if isinstance(oms, int):
        if hi_oms is not None and oms > hi_oms:
            return f"För hög omsättning: {oms} kr."
        if lo_oms is not None and oms < lo_oms:
            return f"För låg omsättning: {oms} kr."
    return None


_VD_ROLLER = ("verkställande direktör", "vd", "extern verkställande direktör")


def vd_namn(b: dict[str, Any]) -> str | None:
    """VD enligt registret, eller None. Bara VD, aldrig en ledamot."""
    return next((p["namn"] for p in b.get("personer") or [] if p["roll"].casefold() in _VD_ROLLER), None)


def _kodpoang(b: dict[str, Any], icp: dict[str, Any], profil: dict[str, Any] | None) -> float:
    """Rangordningen utan Jev: hur väl det KÄNDA matchar kundens målgrupp."""
    p = profil or {}
    poang = 0.0
    # Bara bolagsfakta: merinfos kontaktuppgifter väger inte (filter, inte källa).
    poang += 1 if vd_namn(b) else 0
    lo, hi = _intervall(icp, profil)
    if isinstance(b.get("anstallda"), int) and (lo is not None or hi is not None):
        poang += 1
    poang += 1 if b.get("website") else 0
    poang += 0.5 if (b.get("omsattning") or 0) > 0 else 0
    onskat = " ".join([*(icp.get("must_have") or []), *(k.get("text", "") for k in p.get("kriterier") or [])])
    text = _norm(f"{b.get('verksamhet') or ''} {b.get('sni_namn') or ''}")
    poang += min(3, sum(1 for s in set(_stammar(onskat)) if len(s) >= 4 and s in text))
    return poang


def till_kandidat(b: dict[str, Any], icp: dict[str, Any], profil: dict[str, Any] | None) -> dict[str, Any]:
    """Bolagssidan i hitta_bolag-formen, som resten av kedjan redan läser.
    Utan kontakt: den fylls av webbplatsen (Iris) eller VD-kontrollen (lista)."""
    webb = b.get("website")
    if webb and not webb.startswith("http"):
        webb = f"https://{webb}"
    return {
        "company_name": b["company_name"],
        "website": webb,
        "orgnr": b.get("orgnr"),
        "ort": b.get("ort"),
        "postnr": b.get("postnr"),
        "contact_name": None,
        "contact_role": None,
        "contact_phone": None,
        "contact_email": None,
        "contact_level": None,
        "contact_form_url": None,
        "vd_namn": vd_namn(b),
        "anstallda": b.get("anstallda"),
        "omsattning": b.get("omsattning"),
        "sni": b.get("sni"),
        # INV-DATA-001: varifrån uppgiften kom — bolagssidan.
        "source_name": "merinfo",
        "source_url": b.get("url"),
        "signal": "bransch" if b.get("sni_namn") else None,
        "signal_detalj": b.get("sni_namn"),
        "verksamhet": b.get("verksamhet"),
        # Bara för listspåret (Antons beslut 2026-10-05); blir aldrig ett
        # Iris-leads kontakt.
        "_ensam_vd_telefon": ensam_vd_telefon(b),
    }


async def sok(
    icp: dict[str, Any],
    antal: int,
    *,
    uteslut: set[str] | frozenset[str] = frozenset(),
    profil: dict[str, Any] | None = None,
    puls: Callable[[], Awaitable[Any]] | None = None,
    lage: str = "iris",
    listspar: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]] | None:
    """Antons arbetsflöde: bransch → län/kommun → listsidor → bolagssidor →
    filter på bolagsfakta → Jev mot kundens kriterier (första filtret) →
    rangordning → webbplats (Iris) eller VD-kontakt (lista) → de `antal`
    bästa.

    None = målgruppen gick inte att översätta till merinfos träd (anroparen
    faller tillbaka på den gamla kedjan). [] = översatt, men inget bolag
    klarade filtret och steget efter — ett ärligt nej, ingen utfyllnad."""
    p = profil or {}
    branscher = valj_branscher(list(dict.fromkeys([*(icp.get("industries") or []), *(p.get("branscher") or [])])))
    if not branscher and p.get("malgrupp"):
        branscher = valj_branscher([p["malgrupp"]])
    # Regionnycklarna (icp.geo, app/leads/geo.py) är redan kommuner i
    # profilen; utan profil (listjobb som inte kunde läsa den) expanderas de
    # här, annars blev "goteborg" bara staden i stället för området.
    from ..geo import REGIONER

    geo = [
        *(icp.get("geography") or []),
        *(k.namn for n in (icp.get("geo") or []) if n in REGIONER for k in REGIONER[n].kommuner),
        *(p.get("kommuner") or []),
        *(p.get("omraden") or []),
    ]
    platser = valj_platser(list(dict.fromkeys(geo)))
    if not branscher or platser is None:
        logger.info("merinfo: målgruppen gick inte att översätta (branscher=%s, platser=%s).", branscher, platser)
        return None
    sokningar = [(b, pl) for b in branscher for pl in platser][:10]
    from .. import jev, sidhamtning
    from ..forfilter import ar_enskild_firma

    from .. import upptagna

    # Namn och orgnr (app/leads/upptagna.py): Iris-prospekt, listrader och
    # kundens CRM-kunder, så Iris och listorna aldrig hämtar samma bolag.
    sedda = upptagna.nycklar(uteslut)
    rader: list[dict[str, Any]] = []
    aktiva = list(sokningar)
    sida = 1
    gav_rader = False

    async def fyll_rader(behov: int) -> None:
        """Listsidor tills `behov` rader väntar eller listorna är slut. Varje
        listsida är ett betalt anrop: loopen bryts så fort det räcker, i
        stället för att bläddra alla sökningar en sida djupare i onödan."""
        nonlocal sida, gav_rader
        while aktiva and len(rader) < behov and sida <= MAX_LISTSIDOR:
            for s in list(aktiva):
                if len(rader) >= behov:
                    return
                md = await hamta(listsida_url(s[0], s[1], sida), fas="lista")
                if puls:
                    await puls()
                listrader = tolka_lista(md) if md else []
                if not listrader:
                    aktiva.remove(s)
                    continue
                gav_rader = True
                for r in listrader:
                    if upptagna.upptagen(sedda, r["company_name"], r.get("orgnr")):
                        continue
                    sedda.add(upptagna.nyckel(r["company_name"]))
                    # Förfilter utan hämtning: en enskild firma fälls ändå av
                    # kontrollera(), och orgnr står redan på listraden.
                    if ar_enskild_firma(r.get("orgnr")):
                        continue
                    rader.append(r)
            sida += 1

    async def granska(r: dict[str, Any]) -> dict[str, Any] | None:
        md = await hamta(r["url"], fas="bolag")
        if puls:
            await puls()
        if not md:
            return None
        b = tolka_bolag(md, r["url"])
        b["orgnr"] = b["orgnr"] or r["orgnr"]
        return b

    # Jev frågas inte om webbkriterierna här: den har ingen sajt att titta på
    # än, och utslaget räknas i kod ur webbrevisionen under researchen.
    jev_profil = (
        {**profil, "kriterier": [k for k in profil.get("kriterier") or [] if k.get("belagg") != "webbsignal"]}
        if profil else None
    )

    async def ranka(granskade: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rankade: list[tuple[float, dict[str, Any]]] = []
        for b in granskade:
            if kontrollera(b, icp, profil) is not None:
                continue
            k = till_kandidat(b, icp, profil)
            poang = _kodpoang(b, icp, profil)
            if jev_profil and jev.aktiv():
                triage = await jev.triage(
                    jev_profil, k, utdrag="\n".join(filter(None, [b.get("verksamhet"), b.get("sni_namn")])), signaler=[]
                )
                if triage:
                    k["jev_triage"] = triage
                    if triage.get("beslut") == "fall":
                        continue
                    if isinstance(triage.get("fit"), (int, float)):
                        poang += 10 * triage["fit"]
            k["merinfo_poang"] = round(poang, 2)
            rankade.append((poang, k))
        rankade.sort(key=lambda t: t[0], reverse=True)
        return [k for _, k in rankade]

    # I takt med behovet (plan 2026-10-05): bolagssidor för två kandidater per
    # saknat lead åt gången, och fler bara om omgången inte räckte. Tidigare
    # hämtades tre per beställt lead på en gång (upp till 90 sidor), och alla
    # filter kördes först efteråt.
    ut: list[dict[str, Any]] = []
    granskade_n = godkanda_n = 0
    while len(ut) < antal and granskade_n < MAX_BOLAGSSIDOR:
        behov = antal - len(ut)
        omgang = min(behov * 2, MAX_BOLAGSSIDOR - granskade_n)
        await fyll_rader(omgang)
        if not rader:
            break
        batch, rader[:] = rader[:omgang], rader[omgang:]
        granskade_n += len(batch)
        granskade = [b for b in await asyncio.gather(*(granska(r) for r in batch)) if b]
        rankade = await ranka(granskade)
        godkanda_n += len(rankade)
        ut += await _komplettera(rankade, behov, lage=lage, puls=puls, listspar=listspar)
        kontext = sidhamtning.aktuell()
        if kontext and kontext.slut:
            logger.info("merinfo: kredittaket (%d anrop) nått.", kontext.tak)
            break
    if not gav_rader:
        # Ingen sluggkombination gav en enda listrad: branschordet fanns inte
        # som lista hos merinfo. Det är "kunde inte tolka", inte "inga bolag".
        logger.info("merinfo: inga listrader för %s.", sokningar)
        return None
    logger.info(
        "merinfo (%s): %d sökningar, %d bolagssidor granskade, %d efter filter och Jev → %d levereras.",
        lage, len(sokningar), granskade_n, godkanda_n, len(ut),
    )
    return ut


#: Hur många rangordnade bolag som provas per beställt lead i steget efter
#: filtret. Varje prov kan kosta ett webbplatsuppslag (ett grounded anrop).
PROV_PER_LEAD = 4


async def _webbplats(k: dict[str, Any]) -> str | None:
    from .. import discovery

    webb = k.get("website")
    if not webb:
        try:
            webb = await discovery.sla_upp_webbplats(k["company_name"], geografi=k.get("ort"))
        except Exception:  # noqa: BLE001 — ett uppslag får inte fälla körningen
            logger.info("merinfo: webbplatsuppslaget för %s föll.", k["company_name"])
            return None
    if not webb or not discovery.webbplats_ar_bolagets(webb):
        return None
    if not discovery.webbplats_matchar_namn(k["company_name"], webb):
        return None
    return webb if webb.startswith("http") else f"https://{webb}"


def ensam_vd_telefon(b: dict[str, Any]) -> str | None:
    """Registrets telefonnummer när VD är den enda personen i bolaget, annars
    None. Antons beslut 2026-10-05: då tillhör numret i praktiken VD (regel 5),
    och undantaget från regel 1 gäller bara då. Ensam = högst en anställd och
    ingen annan person med roll (suppleanter och revisorer räknas inte; de
    är aldrig kontakt och tolkas inte in i `personer`)."""
    vd = vd_namn(b)
    if not vd or not b.get("telefon"):
        return None
    if not isinstance(b.get("anstallda"), int) or b["anstallda"] > 1:
        return None
    if any(p["namn"].casefold() != vd.casefold() for p in b.get("personer") or []):
        return None
    return b["telefon"]


def _listrad(k: dict[str, Any], skal: str) -> dict[str, Any]:
    """Ett bolag som inte blir ett Iris-lead men hör hemma i en lista, så att
    kunden kan nå det med ett mer generellt erbjudande (Anton 2026-10-05:
    bolag utan sajt är pengar på bordet för en webbyrå)."""
    tel = k.get("_ensam_vd_telefon")
    return {
        **{f: k.get(f) for f in ("company_name", "website", "ort", "orgnr", "source_name", "source_url")},
        "contact_name": k.get("vd_namn") if tel else None,
        "contact_role": "VD" if tel else None,
        "contact_phone": tel,
        "contact_email": None,
        "contact_level": "named_role_match" if tel else None,
        "signal": "listspar",
        "signal_detalj": skal,
    }


async def _komplettera(
    rankade: list[dict[str, Any]], antal: int, *, lage: str, puls: Callable[[], Awaitable[Any]] | None,
    listspar: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Iris: bolag MED webbplats och en VD-kontakt på sajten (regel 3 och 4).
    Lista: bolag där VD:ns mejl eller telefon står på sajten, eller där VD är
    ensam i bolaget och registrets nummer därför är VD:s.

    Iris-kandidater utan sajt, med parkerad domän eller utan VD-kontakt på
    sajten läggs i `listspar` (plan 2026-10-05, fas 3) i stället för att
    kastas, och får ingen dyr research."""
    from .. import discovery
    from ..platshallare import platshallare_for_webbplats

    def till_lista(k: dict[str, Any], skal: str) -> None:
        if listspar is not None:
            listspar.append(_listrad(k, skal))

    ut: list[dict[str, Any]] = []
    for k in rankade[: max(antal, 1) * PROV_PER_LEAD]:
        if len(ut) >= antal:
            break
        if lage == "lista" and not k.get("vd_namn"):
            continue
        webb = await _webbplats(k)
        if puls:
            await puls()
        if not webb:
            if lage == "lista" and k.get("_ensam_vd_telefon"):
                ut.append({**_listrad(k, "Ingen webbplats; VD är ensam i bolaget"), "signal": None})
            else:
                till_lista(k, "Ingen webbplats")  # Anton: "Om det inte finns en hemsida, gå vidare."
            continue
        k = {**k, "website": webb}
        if lage == "iris":
            parkerad = await platshallare_for_webbplats(webb)
            if parkerad:
                till_lista(k, f"Parkerad domän: {parkerad}")
                continue
        kontakt = await discovery.hamta_vd_kontakt(webb, k["vd_namn"]) if k.get("vd_namn") else None
        if not kontakt:
            if lage == "lista" and k.get("_ensam_vd_telefon"):
                ut.append({**_listrad(k, "VD är ensam i bolaget"), "signal": None})
            else:
                till_lista(k, "Ingen VD-kontakt på webbplatsen")
            continue
        k = {**k, **kontakt, "contact_name": k["vd_namn"], "contact_role": "VD",
             "contact_level": "named_role_match"}
        ut.append(k)
    return ut


if __name__ == "__main__":
    import sys

    if sys.argv[1:] == ["taxonomi"]:
        data = asyncio.run(bygg_taxonomi())
        TAXONOMI_FIL.write_bytes(json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8"))
        print(f"{len(data['branscher'])} branscher, {len(data['lan'])} län, "
              f"{sum(len(l['kommuner']) for l in data['lan'])} kommuner -> {TAXONOMI_FIL.name}")
