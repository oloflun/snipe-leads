"""Hitta riktiga bolag som matchar ett ICP.

Batchkörningen researchar ETT prospekt i taget. Utan det här steget måste
kunden själv skriva in namn — vilket är en funktion, inte kedjan. Kedjan är
ICP → urval → källa → research → utkast.

Sökningen går mot Googles sökindex via Gemini (google_search-verktyget).
Det är sökning, inte skrapning av allabolag/hitta/ratsit — de sajterna får
inte bli källa (se app/leads/sources/__init__.py). Träffen ska vara bolagets
EGNA webbplats, som sedan registreras i prospect_sources och skrapas av den
befintliga researchvägen.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from ..config import get_settings

logger = logging.getLogger("snajp-support.leads-discovery")

LAGLIG_GRUND_EGEN_WEBB = (
    "Berättigat intresse för B2B-prospektering mot bolagets egna publika "
    "webbplats (GDPR art. 6.1 f)."
)

#: Fallback-trappan (kundkrav, ordagrant): "försök ALLTID hitta en
#: kontaktperson som är NÄRMAST önskemålet ... i värsta fall officiell
#: kontakt-mail, men ALLTID kontaktuppgifter." Ordningen är prioritet, inte
#: alternativ — modellen ska stanna vid FÖRSTA nivån den kan verifiera, inte
#: hitta på för att nå en högre. Samma ordning står i prompten i
#: `hitta_bolag` nedan; ändra båda om du ändrar den ena.
KONTAKTNIVAER = ("named_role_match", "named_other", "role_address", "contact_form")

_AGGREGATORER = (
    "allabolag.se",
    "hitta.se",
    "ratsit.se",
    "merinfo.se",
    "proff.se",
    "linkedin.com",
    "facebook.com",
    "wikipedia.org",
    "eniro.se",
    "121.nu",
    "bolagsverket.se",
    "google.com",
    "google.se",
)

_EXEMPEL_TLD = (".example", ".invalid", ".test")

#: Grounded sökning (google_search-verktyget) läser flera sidor innan Gemini
#: svarar och tar regelbundet längre än ett vanligt anrop — produktionsloggen
#: 2026-08-31 visade httpx.ReadTimeout vid 45 s som dödade hela batchkörningen
#: (se hitta_bolag). Anslutningen ska ändå vara snabb; det är LÄSNINGEN som
#: behöver gott om tid.
_SOKNING_TIMEOUT = httpx.Timeout(10.0, connect=10.0, read=90.0)
_SOKNING_FORSOK = 3
_SOKNING_BACKOFF_BAS = 2.0  # sekunder, dubblas per omförsök


class DiscoveryError(RuntimeError):
    """Sökningen kunde inte genomföras. Skiljd från 'noll träffar'."""


def _host(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


#: Publika konsumentdomäner. En adress här är ALDRIG ett arbetsmejl, oavsett
#: vad bolagets sajt eller modellen påstår. Speglar prospect_quality_gate
#: plus de vanliga nordiska/US-varianterna som densamma listan missat.
_PRIVATA_DOMÄNER = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "yahoo.com",
        "yahoo.se",
        "hotmail.com",
        "hotmail.se",
        "outlook.com",
        "outlook.se",
        "icloud.com",
        "me.com",
        "mac.com",
        "live.se",
        "live.com",
        "msn.com",
        "aol.com",
        "proton.me",
        "protonmail.com",
        "telia.com",
        "bredband.net",
        "spray.se",
    }
)

_EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)

#: Lokaldelar som är officiell kontakt eller nära en beslutsroll. Ordningen
#: är rank, inte filter — en namngiven chef@ slår info@.
_ROLL_LOKALDELAR = (
    "vd",
    "ceo",
    "chef",
    "sales",
    "salj",
    "info",
    "kontakt",
    "hello",
    "hej",
    "mail",
    "office",
)


def ar_privat_epost(epost: str | None) -> bool:
    """True för gmail/hotmail/icloud och motsvarande — aldrig mottagare."""
    if not epost or "@" not in epost:
        return False
    return epost.rsplit("@", 1)[-1].strip().lower().lstrip("www.") in _PRIVATA_DOMÄNER


def ar_arbetsmejl(epost: str | None, *, webb: str | None = None) -> bool:
    """Inte privat. Om webbplatsen är känd ska adressen ligga på samma domän."""
    if not epost or "@" not in epost or ar_privat_epost(epost):
        return False
    if not webb:
        return True
    bolag = _host(webb) if "://" in webb or webb.startswith("www.") else _host("https://" + webb)
    if not bolag:
        return True
    doman = epost.rsplit("@", 1)[-1].strip().lower().lstrip("www.")
    return doman == bolag or doman.endswith("." + bolag) or bolag.endswith("." + doman)


def plocka_arbetsmejl(
    material: str,
    webb: str | None,
    *,
    onskad_roll: str | None = None,
) -> str | None:
    """Första arbetsmejlen som FAKTISKT står i underlaget. Hitta aldrig på.

    Prioritet: lokaldel som liknar den sökta rollen, sedan info/kontakt/hej,
    sedan övriga adresser på bolagets egen domän. En privat adress hoppas
    över även om den står först på sidan.
    """
    if not material:
        return None
    sedda: list[str] = []
    for match in _EMAIL_RE.finditer(material):
        epost = match.group(0).rstrip('.,;:)>"\'')
        if not ar_arbetsmejl(epost, webb=webb):
            continue
        nyckel = epost.lower()
        if nyckel not in sedda:
            sedda.append(nyckel)
    if not sedda:
        return None
    roll = (onskad_roll or "").casefold()

    def rank(epost: str) -> tuple[int, int]:
        lokal = epost.split("@", 1)[0].casefold()
        if roll and roll[:4] in lokal:
            return (0, 0)
        for i, delnamn in enumerate(_ROLL_LOKALDELAR):
            if delnamn in lokal:
                return (1, i)
        return (2, 0)

    sedda.sort(key=rank)
    return sedda[0]


#: Rankning för kontaktlänksökning (kundkrav: agenten måste HITTA "om oss"
#: eller "kontakt" av sig själv i stället för att bara läsa startsidan).
#: Lägre tal = bättre — en riktig kontaktsida slår en om-oss-sida som i sin
#: tur slår en ren personallista, samma princip som KONTAKTNIVAER ovan.
#: Både svenska och engelska varianter, eftersom en del bolag bara har en
#: engelsk sajt.
_KONTAKTLANK_NYCKELORD: tuple[tuple[str, int], ...] = (
    ("kontakta-oss", 0),
    ("kontakta_oss", 0),
    ("kontaktaoss", 0),
    ("kontakt", 0),
    ("contact-us", 0),
    ("contactus", 0),
    ("contact", 0),
    ("om-oss", 1),
    ("om_oss", 1),
    ("omoss", 1),
    ("about-us", 1),
    ("aboutus", 1),
    ("about", 1),
    ("team", 2),
    ("medarbetare", 2),
    ("personal", 2),
    ("ledning", 2),
    ("styrelse", 2),
)

#: Markdown-länk `[text](url)` — ScrapeGraphAI-svaret är normalt markdown.
_MD_LANK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\)")
#: Rå `<a href="...">text</a>` — en del sidor kommer tillbaka som HTML-
#: fragment i markdownfältet i stället för konverterat markdown.
_HTML_LANK_RE = re.compile(
    r'<a\b[^>]*?href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL
)
_TAGG_RE = re.compile(r"<[^>]+>")


def _kontaktlank_rank(text: str, path: str) -> int | None:
    """Lägsta (bästa) rank bland nyckelorden som träffar antingen länktexten
    eller url-pathen, eller None om ingen träffar alls."""
    mal = f"{path} {text}".casefold()
    bast: int | None = None
    for nyckelord, rank in _KONTAKTLANK_NYCKELORD:
        if nyckelord in mal and (bast is None or rank < bast):
            bast = rank
    return bast


def extrahera_kontaktlankar(material: str, webbplats: str, *, tak: int = 3) -> list[str]:
    """Plockar ut de `tak` bästa länkarna på BOLAGETS EGEN domän som
    sannolikt leder till en kontakt- eller om-oss-sida, ur redan skrapat
    material (markdown- eller HTML-länkar).

    Det här är svaret på kundens rotorsak: `_gather_registered_sources`
    registrerade tidigare BARA startsidan (se `_registrera_webb` i
    app/api/leads.py), och en kontaktperson under "om oss" eller "kontakt"
    hämtades då aldrig — `_uppgradera_kontakt` hade inget att hitta i.

    Samma-domän-kravet är inte kosmetiskt: en länk ut ur underlaget är precis
    den okontrollerade skrapningen G4/allowlisten finns för att förhindra
    (se `_rena_kontaktformular` ovan för samma resonemang på ett annat
    fält). Länkar registreras ALDRIG härifrån — den här funktionen bara
    FÖRESLÅR kandidater; anroparen registrerar dem i prospect_sources innan
    de går genom den befintliga allowlist-skrapningen.
    """
    if not material or not webbplats:
        return []
    bas = webbplats if "://" in webbplats else "https://" + webbplats
    doman = _host(bas)
    if not doman:
        return []

    par: list[tuple[str, str]] = []
    for text, url in _MD_LANK_RE.findall(material):
        par.append((text, url))
    for url, text in _HTML_LANK_RE.findall(material):
        par.append((_TAGG_RE.sub(" ", text), url))

    kandidater: list[tuple[int, int, str]] = []  # (rank, ordning, url)
    sedda: set[str] = set()
    for ordning, (text, ravurl) in enumerate(par):
        ravurl = ravurl.strip()
        if not ravurl or ravurl.lower().startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        try:
            resolved = urljoin(bas, ravurl)
            normaliserad = normalisera_webbplats(resolved)
        except Exception:  # noqa: BLE001 — en trasig länk hoppas bara över
            continue
        if not normaliserad or normaliserad in sedda:
            continue
        host = _host(normaliserad)
        if host != doman and not host.endswith("." + doman):
            continue
        rank = _kontaktlank_rank(_TAGG_RE.sub(" ", text), urlparse(normaliserad).path)
        if rank is None:
            continue
        sedda.add(normaliserad)
        kandidater.append((rank, ordning, normaliserad))

    kandidater.sort(key=lambda k: (k[0], k[1]))
    return [url for _, _, url in kandidater[:tak]]


def webbplats_ar_bolagets(url: str | None) -> bool:
    """True om URL:en kan vara ett bolags egen sajt, inte ett register eller exempel."""
    if not url:
        return False
    raw = url.strip()
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False
    host = _host(raw)
    if any(host == a or host.endswith("." + a) for a in _AGGREGATORER):
        return False
    if any(host.endswith(tld) for tld in _EXEMPEL_TLD):
        return False
    return "." in host


def normalisera_webbplats(url: str) -> str:
    raw = url.strip()
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    parsed = urlparse(raw)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"


def _plocka_json(text: str) -> list[dict[str, Any]]:
    """Tar ut en JSON-lista ur modellsvaret, med eller utan kodstaket."""
    if not text:
        return []
    text = text.strip()
    staket = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if staket:
        text = staket.group(1)
    else:
        start = text.find("[")
        slut = text.rfind("]")
        if start == -1 or slut <= start:
            return []
        text = text[start : slut + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _icp_som_text(icp: dict[str, Any]) -> str:
    rader = []
    for nyckel, etikett in (
        ("industries", "Branscher"),
        ("exclude_industries", "Undvik"),
        ("geography", "Geografi"),
        ("roles", "Beslutsfattare att na"),
        ("must_have", "Signaler som kravs"),
        ("deal_breakers", "Diskvalificerar"),
    ):
        varde = icp.get(nyckel) or []
        if varde:
            rader.append(f"- {etikett}: {', '.join(str(v) for v in varde)}")
    storlek = icp.get("size") or {}
    amin = storlek.get("anstallda_min") if isinstance(storlek, dict) else icp.get("anstallda_min")
    amax = storlek.get("anstallda_max") if isinstance(storlek, dict) else icp.get("anstallda_max")
    if amin is not None or amax is not None:
        rader.append(f"- Anstallda: {amin or '?'}–{amax or '?'}")
    return "\n".join(rader) or "(ingen malgrupp ifylld)"


async def _gemini_med_sokning(prompt: str) -> str:
    settings = get_settings()
    nyckel = settings.gemini_api_key or settings.active_llm_key()
    if not nyckel or len(nyckel) < 20:
        raise DiscoveryError("Ingen Gemini-nyckel — sokningen kan inte kora.")
    modell = settings.model if "gemini" in (settings.model or "").lower() else "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modell}:generateContent"
    kropp = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.2},
    }
    svar: httpx.Response | None = None
    for forsok in range(1, _SOKNING_FORSOK + 1):
        sista_forsoket = forsok == _SOKNING_FORSOK
        try:
            async with httpx.AsyncClient(timeout=_SOKNING_TIMEOUT) as client:
                svar = await client.post(url, params={"key": nyckel}, json=kropp)
        except httpx.HTTPError as fel:
            # Basklassen för httpx transportfel — täcker ReadTimeout,
            # ConnectError m.fl. utan att räkna upp varje underklass.
            if sista_forsoket:
                raise DiscoveryError(
                    "Sokningen mot Gemini svarade inte i tid — natverket eller "
                    "modellen dröjde for lange."
                ) from fel
            await asyncio.sleep(_SOKNING_BACKOFF_BAS * (2 ** (forsok - 1)))
            continue
        if svar.status_code >= 500:
            if sista_forsoket:
                raise DiscoveryError(f"Sokningen misslyckades ({svar.status_code}).")
            await asyncio.sleep(_SOKNING_BACKOFF_BAS * (2 ** (forsok - 1)))
            continue
        if svar.status_code >= 400:
            # 4xx är ett avvisat anrop (fel nyckel, ogiltig modell, kvot) — det
            # blir inte bättre av att upprepas, så inget nytt försök här.
            raise DiscoveryError(f"Sokningen avvisades ({svar.status_code}).")
        break
    assert svar is not None  # loopen antingen `break`:ar med svar eller kastar
    data = svar.json()
    delar = (
        (data.get("candidates") or [{}])[0]
        .get("content", {})
        .get("parts", [])
    )
    return "".join(str(p.get("text") or "") for p in delar)


def _giltig_kontaktniva(rad: dict[str, Any], *, har_epost: bool) -> str | None:
    """Normaliserar modellens `contact_level` mot KONTAKTNIVAER.

    Litar INTE blint på strängen modellen skickar — en hallucinerad nivå
    ("verified"/"confirmed") ska inte kunna få ett gissat namn att se ut som
    en namngiven träff i UI:t. Faller tillbaka på ett konservativt gissat
    värde utifrån vilka fält som faktiskt finns, i stället för att kasta hela
    raden — trappan ska vara ärlig, inte perfekt."""
    niva = str(rad.get("contact_level") or "").strip().lower()
    if niva in KONTAKTNIVAER:
        # En påstådd namngiven träff utan namn är motsägelsen trappan finns
        # för att förhindra — nedgraderas till vad fälten faktiskt visar.
        if niva in ("named_role_match", "named_other") and not str(rad.get("contact_name") or "").strip():
            niva = ""
        elif niva == "contact_form" and har_epost:
            niva = ""
    else:
        niva = ""
    if niva:
        return niva
    # Modellen glömde nivån (eller den blev nedgraderad ovan) — härled den
    # konservativt av vad raden faktiskt innehåller. Aldrig högre än vad
    # fälten bär belägg för.
    if str(rad.get("contact_name") or "").strip() and har_epost:
        return "named_other"
    if har_epost:
        return "role_address"
    if rad.get("contact_form_url"):
        return "contact_form"
    return None


def _rena_kontaktformular(url: object, *, webb: str | None) -> str | None:
    """Kontaktformuläret måste ligga på SAMMA domän som bolagets webbplats —
    annars är det inte trappans sista steg, det är en okontrollerad länk ut
    ur underlaget (samma resonemang som `webbplats_ar_bolagets`)."""
    if not url or not webb:
        return None
    raw = str(url).strip()
    if not raw:
        return None
    try:
        normaliserad = normalisera_webbplats(raw)
    except Exception:  # noqa: BLE001 — ett trasigt url-fält ska inte fälla raden
        return None
    if _host(normaliserad) != _host(webb):
        return None
    return normaliserad


def _rena_traffar(rader: list[dict[str, Any]], *, uteslut: set[str], tak: int) -> list[dict[str, Any]]:
    rena: list[dict[str, Any]] = []
    sedda: set[str] = set()
    for rad in rader:
        if not isinstance(rad, dict):
            continue
        namn = str(rad.get("company_name") or "").strip()
        if not namn or namn.casefold() in uteslut or namn.casefold() in sedda:
            continue
        webb = rad.get("website")
        webb = normalisera_webbplats(str(webb)) if webb else None
        if not webbplats_ar_bolagets(webb):
            continue
        sedda.add(namn.casefold())

        # Kontaktfälten är ALLA valfria på radnivå — company_name och website
        # är de enda hårda kraven (oförändrat). En rad med kontaktuppgifter
        # men utan t.ex. orgnr eller ort ska aldrig kastas här; det var precis
        # den bristen som gjorde att en träff med bara e-post ändå försvann
        # om något annat fält saknades i en tidigare version.
        epost = str(rad["contact_email"]).strip() if rad.get("contact_email") else None
        if epost and ar_privat_epost(epost):
            # Privat gmail/hotmail är inte en mottagare. Hellre tomt — Fas B
            # plockar arbetsmejlet ur skrapet — än att spara en olaglig kanal.
            epost = None
        kontaktnamn = str(rad["contact_name"]).strip() if rad.get("contact_name") else None
        kontaktroll = str(rad["contact_role"]).strip() if rad.get("contact_role") else None
        kontaktformular = _rena_kontaktformular(rad.get("contact_form_url"), webb=webb)
        niva = _giltig_kontaktniva(rad, har_epost=bool(epost))
        # En pastadd "contact_form"-niva utan en giltig (samma-domän) URL bar
        # inget belagg alls — samma nedgradering som _giltig_kontaktniva redan
        # gor for en namngiven traff utan namn.
        if niva == "contact_form" and not kontaktformular:
            niva = None
        # contact_form_url ska bara synas när det FAKTISKT är trappans sista
        # utväg — annars kan en form-URL vid sidan av en riktig adress läsas
        # som att adressen är osäker, vilket är precis den otydlighet nivå-
        # fältet finns för att undvika.
        if niva != "contact_form":
            kontaktformular = None

        rena.append(
            {
                "company_name": namn,
                "website": webb,
                "orgnr": str(rad["orgnr"]).strip() if rad.get("orgnr") else None,
                "ort": str(rad["ort"]).strip() if rad.get("ort") else None,
                "contact_name": kontaktnamn,
                "contact_role": kontaktroll,
                "contact_email": epost,
                "contact_level": niva,
                "contact_form_url": kontaktformular,
                "anstallda": rad.get("anstallda") if isinstance(rad.get("anstallda"), int) else None,
            }
        )
        if len(rena) >= tak:
            break
    return rena


async def hitta_bolag(
    icp: dict[str, Any],
    antal: int,
    *,
    uteslut_namn: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Returnerar upp till `antal` riktiga bolag. Tom lista = inga verifierbara traffar."""
    if antal <= 0:
        return []
    uteslut = {n.casefold() for n in (uteslut_namn or set()) if n}
    roller = [str(r).strip() for r in (icp.get("roles") or []) if str(r).strip()]
    roll_text = (
        ", ".join(roller)
        if roller
        else "en beslutsfattare (VD, grundare eller motsvarande — malgruppen "
        "angav ingen specifik roll)"
    )
    # Kundkrav, ordagrant: "forsok ALLTID hitta en kontaktperson som ar
    # NARMAST onskemalet, det viktiga ar att det kommer fram, i varsta fall
    # officiell kontakt-mail, men ALLTID kontaktuppgifter." Kontaktuppgift ar
    # darfor ett KRAV har, inte ett tillval som i den gamla prompten — och
    # trappan nedan ger modellen en konkret lagsta niva att falla tillbaka pa
    # i stallet for att lamna faltet null nar en namngiven person inte gar
    # att verifiera.
    prompt = (
        "Hitta {antal} RIKTIGA svenska aktiebolag som matchar malgruppen nedan. "
        "Anvand sokning. Hitta inte pa bolag och hitta inte pa personer.\n\n"
        "KONTAKTUPPGIFT AR OBLIGATORISKT for varje bolag du returnerar — inte "
        "ett tillval. Folj den har prioritetsordningen och stanna vid FORSTA "
        "nivan du kan verifiera i sokresultatet. Hitta ALDRIG pa for att na en "
        "hogre niva; en gissad kontakt ar varre an ingen:\n"
        f"  1. En NAMNGIVEN person i rollen '{roll_text}', hittad pa bolagets "
        "egen sajt (om oss/ledning/kontakt) eller i en kalla som namnger "
        'personen. contact_level="named_role_match", fyll i contact_name, '
        "contact_role och contact_email om den star pa sajten.\n"
        "  2. Om ingen i den sokta rollen gar att verifiera: nagon ANNAN "
        'namngiven beslutsfattare pa bolagets sajt. contact_level="named_other".\n'
        "  3. Om ingen namngiven person gar att verifiera: en ROLLBASERAD "
        "adress pa bolagets EGEN doman — info@, kontakt@, hej@ eller sales@. "
        'contact_level="role_address", contact_name lamnas null.\n'
        "  4. Om INGEN namngiven person gaar att verifiera men en officiell "
        "kontaktadress star pa sajten (info@, kontakt@, hej@ pa bolagets EGEN "
        'doman): contact_level="role_address". En kontaktformular-URL far folja '
        "med som metadata men ersatter ALDRIG en e-postadress. Returnera inte "
        "ett bolag utan contact_email om adressen star nagonstans pa den egna "
        "sajten. Privat gmail/hotmail/icloud ar FORBUDET.\n\n"
        "Returnera ENBART en JSON-lista:\n"
        '[{{"company_name":"...","website":"https://...","orgnr":null,"ort":"...",'
        '"contact_name":null,"contact_role":null,"contact_email":null,'
        '"contact_level":null,"contact_form_url":null,"anstallda":null}}]\n'
        "website MÅSTE vara bolagets egen officiella sajt, inte allabolag/hitta/ratsit/"
        "linkedin. orgnr bara om det star pa bolagets egen sajt. contact_email och "
        "contact_form_url MASTE vara pa samma doman som website.\n\n"
        f"Malgrupp:\n{_icp_som_text(icp)}\n"
        f"Uteslut dessa namn: {', '.join(sorted(uteslut)) or '(inga)'}\n"
    ).format(antal=antal)
    try:
        text = await _gemini_med_sokning(prompt)
    except DiscoveryError:
        logger.warning("Discovery-sokningen misslyckades.")
        raise
    return _rena_traffar(_plocka_json(text), uteslut=uteslut, tak=antal)


async def sla_upp_webbplats(company_name: str, *, geografi: str | None = None) -> str | None:
    """Officiell webbplats for ett namngivet bolag, eller None."""
    namn = company_name.strip()
    if not namn:
        return None
    var = f" i {geografi}" if geografi else " i Sverige"
    prompt = (
        f"Vad ar den officiella webbplatsen for det svenska bolaget {namn}{var}? "
        "Svara med en JSON-lista med ETT objekt: "
        '[{"company_name":"...","website":"https://..."}]. '
        "Bara bolagets egen sajt, inte allabolag/hitta/ratsit. Om du inte kan "
        "verifiera, returnera []."
    )
    try:
        text = await _gemini_med_sokning(prompt)
    except DiscoveryError:
        return None
    rena = _rena_traffar(_plocka_json(text), uteslut=set(), tak=1)
    return rena[0]["website"] if rena else None
