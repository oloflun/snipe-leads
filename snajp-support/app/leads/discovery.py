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
from . import upptagna

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

#: Rekryteringsplattformar och jobbannonsvärdar. Skild lista från
#: _AGGREGATORER av ett skäl som betyder något: de här ÄR inte register över
#: bolag, de är tredjepartsplattformar som är bolagets ANNONS-yta — och
#: värdnamnet bär ofta bolagets eget namn (`fibio.teamtailor.com`), så
#: namn↔domän-grinden släpper igenom dem.
#:
#: Varför de ändå måste fällas: kundkravet är att kontaktpersonen alltid
#: hämtas från prospektets EGEN sida, där rollerna är aktuella och
#: kontaktvägarna är de bolaget själv vill bli nådd på. En ATS-sida bär
#: rekryterarens formulär, inte bolagets kontaktuppgifter — kontaktskörden
#: skulle skrapa fel yta och hitta ingenting (uppmätt i drift 2026-09-04:
#: `Fibio Nordic AB` fick `fibio.teamtailor.com` och contact_email null).
#:
#: Konsekvensen av att fälla är RÄTT utfall: träffen faller vidare till den
#: namnhärledda HEAD-gissningen, som letar bolagets riktiga domän.
_ANNONSPLATTFORMAR = (
    "teamtailor.com",
    "varbi.com",
    "reachmee.com",
    "jobylon.com",
    "workbuster.com",
    "recman.se",
    "myworkdayjobs.com",
    "greenhouse.io",
    "lever.co",
    "indeed.com",
    "monster.se",
    "arbetsformedlingen.se",
    "blocket.se",
)

_EXEMPEL_TLD = (".example", ".invalid", ".test")

#: Grounded sökning (google_search-verktyget) läser flera sidor innan Gemini
#: svarar och tar regelbundet längre än ett vanligt anrop — produktionsloggen
#: 2026-08-31 visade httpx.ReadTimeout vid 45 s som dödade hela batchkörningen
#: (se hitta_bolag). Anslutningen ska ändå vara snabb; det är LÄSNINGEN som
#: behöver gott om tid.
#:
#: Uppmätt 2026-09-15 mot Vertex med samma målgrupp två gånger i rad: 55 s och
#: 156 s. Med read=90 och tre försök föll en kundkörning efter 4,5 minuter
#: (tre lästimeouter) — och varje omförsök startade om samma långa sökning
#: från noll. Därför: ett generöst lästak, och en LÄSTIMEOUT görs inte om
#: (se _gemini_med_sokning). Anslutningsfel och 5xx är snabba och görs om.
_SOKNING_TIMEOUT = httpx.Timeout(10.0, connect=10.0, read=180.0)
_SOKNING_FORSOK = 3
_SOKNING_BACKOFF_BAS = 2.0  # sekunder, dubblas per omförsök


class DiscoveryError(RuntimeError):
    """Sökningen kunde inte genomföras. Skiljd från 'noll träffar'."""


class _Leverantorssvar(RuntimeError):
    """Leverantörens avvisning, kedjad som ORSAK till ett DiscoveryError.

    Före 2026-09-13 kastades svarskroppen bort vid 4xx, så ett kreditslut i
    sökningen gick inte att klassa: kunden fick "försök igen" och ingen larmades.
    Texten ligger i orsaken och inte i DiscoveryError:s eget meddelande —
    kvotfel.py följer kedjan, och ingen kundväg läser orsaken rakt av.
    """

    def __init__(self, status_code: int, text: str) -> None:
        super().__init__(f"{status_code}: {text}")
        self.status_code = status_code


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
        # Citattecken runt url:en följer med när skrapet innehåller
        # [Kontakt]("https://…") — urljoin gjorde då adressen till
        # https://<domän>/%22https://…%22, en sida som inte finns, och
        # kontaktjakten hämtade tomhet (uppmätt på ekan.com 2026-09-21).
        ravurl = ravurl.strip().strip("\"'")
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
    # Subdomänformen är hela poängen här: `fibio.teamtailor.com` matchar
    # bolagsnamnet men är rekryterarens yta, inte bolagets. Se listans
    # docstring.
    if any(host == p or host.endswith("." + p) for p in _ANNONSPLATTFORMAR):
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
    # De strukturerade fälten (DEL 1.1) saknades här fram till 2026-09-02:
    # en kund som fyllt i ENBART SNI-koder eller regioner fick starta en
    # körning (`_har_sokbar_malgrupp` godkänner sni_codes), men sökprompten
    # sa "(ingen malgrupp ifylld)" — Gemini letade brett över hela webben i
    # stället för i kundens nisch. Nischningen ÄR själva besparingen: en
    # träff utanför målgruppen kostar hela researchvarvet innan grinden
    # fäller den.
    if icp.get("geo"):
        rader.append(
            "- Geografiskt omrade: " + "; ".join(beskriv_region(n) for n in icp["geo"])
        )
    if icp.get("sni_codes"):
        rader.append(
            "- Branschkoder (SNI): " + "; ".join(beskriv_kod(k) for k in icp["sni_codes"])
        )
    if icp.get("exclude_sni"):
        rader.append(
            "- Branschkoder att UNDANTA: "
            + "; ".join(beskriv_kod(k) for k in icp["exclude_sni"])
        )
    if icp.get("exclude_domains"):
        rader.append(
            "- Domaner att aldrig foresla: " + ", ".join(str(d) for d in icp["exclude_domains"])
        )
    storlek = icp.get("size") or {}
    amin = storlek.get("anstallda_min") if isinstance(storlek, dict) else icp.get("anstallda_min")
    amax = storlek.get("anstallda_max") if isinstance(storlek, dict) else icp.get("anstallda_max")
    if amin is not None or amax is not None:
        rader.append(f"- Anstallda: {amin or '?'}–{amax or '?'}")
    return "\n".join(rader) or "(ingen malgrupp ifylld)"


async def _gemini_med_sokning(prompt: str) -> str:
    settings = get_settings()
    modell = settings.model if "gemini" in (settings.model or "").lower() else "gemini-2.5-flash"

    # Vertex AI: bearer-token + annan endpoint; AI Studio: ?key= query-param.
    if settings.google_service_account_json:
        from ..agent.llm import _vertex_token, _vertex_base_url
        import json as _json
        token = _vertex_token(settings)
        info = _json.loads(settings.google_service_account_json)
        project = info["project_id"]
        region = settings.google_cloud_region
        url = (
            f"https://{region}-aiplatform.googleapis.com/v1beta1/"
            f"projects/{project}/locations/{region}/"
            f"publishers/google/models/{modell}:generateContent"
        )
        headers: dict[str, str] = {"Authorization": f"Bearer {token}"}
        params: dict[str, str] = {}
    else:
        nyckel = settings.gemini_api_key or settings.active_llm_key()
        if not nyckel or len(nyckel) < 20:
            raise DiscoveryError("Ingen Gemini-nyckel — sokningen kan inte kora.")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modell}:generateContent"
        headers = {}
        params = {"key": nyckel}

    kropp = {
        # role krävs av Vertex ("Please use a valid role: user, model." -> 400);
        # AI Studio gissade "user" tyst. Uppmätt 2026-09-15: utan den föll
        # varje grounded sökning i Vertex-miljöerna, dolt av att JobTech-
        # källan fyllde körningarna så att sökningen sällan behövdes.
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        # Tänkandet AV. Uppmätt 2026-09-15 mot Vertex med Nordforms prompt:
        # standardtänkande gav timeout efter 300 s respektive 258 s och 1 rad
        # (63 592 tänktokens); thinkingBudget 0 gav 16 s och 9 s med 8
        # användbara rader vardera. Grounded-sökningen behöver söka, inte
        # resonera — tänkandet var hela latensen.
        "generationConfig": {"temperature": 0.2, "thinkingConfig": {"thinkingBudget": 0}},
    }
    svar: httpx.Response | None = None
    for forsok in range(1, _SOKNING_FORSOK + 1):
        sista_forsoket = forsok == _SOKNING_FORSOK
        try:
            async with httpx.AsyncClient(timeout=_SOKNING_TIMEOUT) as client:
                svar = await client.post(url, params=params, headers=headers, json=kropp)
        except httpx.ReadTimeout as fel:
            # Sökningen hann inte svara inom lästaket. Ett omförsök startar
            # samma långa grounded sökning från noll och spräcker kundens
            # väntetid — hellre ett tydligt fel direkt.
            raise DiscoveryError(
                "Sokningen mot Gemini svarade inte i tid — modellen dröjde for lange."
            ) from fel
        except httpx.HTTPError as fel:
            # Basklassen för övriga httpx transportfel (ConnectError m.fl.) —
            # snabba fel där ett nytt försök ofta lyckas.
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
            raise DiscoveryError(f"Sokningen avvisades ({svar.status_code}).") from _Leverantorssvar(
                svar.status_code, svar.text[:500]
            )
        break
    assert svar is not None  # loopen antingen `break`:ar med svar eller kastar
    data = svar.json()
    kandidat = (data.get("candidates") or [{}])[0]
    delar = kandidat.get("content", {}).get("parts", [])
    text = "".join(str(p.get("text") or "") for p in delar)
    # Insynen (Fas 7): prompten, råsvaret och SÖKNINGENS KÄLLADRESSER. De
    # påhittade bolagen 2026-10-05 kom ur det här anropet, och utan källorna
    # går det inte att se om en träff hade en sida bakom sig eller inte.
    from ..agentcore.insyn import logga_anrop

    metadata = kandidat.get("groundingMetadata") or {}
    logga_anrop(
        "sokning",
        prompt=prompt,
        svar=text,
        modell=modell,
        kallor=[
            str((chunk.get("web") or {}).get("uri") or "")
            for chunk in metadata.get("groundingChunks") or []
            if (chunk.get("web") or {}).get("uri")
        ],
        utfall={"sokfragor": metadata.get("webSearchQueries") or []},
    )
    return text


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


def _rena_traffar(
    rader: list[dict[str, Any]], *, uteslut: set[str], tak: int, tillat_utan_webb: bool = False
) -> list[dict[str, Any]]:
    uteslut = upptagna.nycklar(uteslut)
    rena: list[dict[str, Any]] = []
    sedda: set[str] = set()
    for rad in rader:
        if not isinstance(rad, dict):
            continue
        namn = str(rad.get("company_name") or "").strip()
        if not namn or upptagna.upptagen(uteslut, namn, rad.get("orgnr")) or upptagna.nyckel(namn) in sedda:
            continue
        webb = rad.get("website")
        webb = normalisera_webbplats(str(webb)) if webb else None
        if not webbplats_ar_bolagets(webb):
            # Iris-profilen kan sikta på bolag UTAN webbplats (Alunix
            # 2026-09-29: "gamla hemsidor eller ingen sida alls"). Då räcker
            # ett orgnr eller en arbetsadress som identitet.
            epost_rad = str(rad.get("contact_email") or "").strip()
            if not (tillat_utan_webb and (rad.get("orgnr") or ar_arbetsmejl(epost_rad or None))):
                continue
            webb = None
        sedda.add(upptagna.nyckel(namn))

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
                "postnr": str(rad["postnr"]).strip() if rad.get("postnr") else None,
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


#: Subdomäner som pekar på ANNONSEN, inte bolaget. Pixelgranskningen
#: 2026-09-02 av första skarpa leadslistan visade att JobTechs employer.url
#: ofta är jobb.bolaget.se/karriar.bolaget.se — kontaktskörden och skrapet
#: behöver apexdomänen, där kontaktsidan bor.
_KARRIARSUBDOMANER = (
    "jobb.", "job.", "jobs.", "karriar.", "career.", "careers.",
    "ledigajobb.", "rekrytering.", "recruit.",
)


def skala_karriarsubdoman(url: str) -> str | None:
    """https://jobb.bolaget.se -> https://bolaget.se, eller None om URL:en
    inte bär en karriärsubdomän. Ren strängoperation — anroparen
    HEAD-verifierar apexen innan den används."""
    host = urlparse(url).netloc.lower()
    for prefix in _KARRIARSUBDOMANER:
        if host.startswith(prefix):
            return f"https://{host[len(prefix):]}"
    return None


async def _head_ok(url: str) -> bool:
    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0), follow_redirects=False) as client:
        try:
            svar = await client.head(url)
        except httpx.HTTPError:
            return False
        return svar.status_code in (200, 301, 302, 403)


async def hamta_kontaktvag(website: str) -> dict[str, Any]:
    """Kontaktväg ur bolagets EGEN webbplats, helt utan LLM (openleads
    ground-truth-mönster, kostnadsarbetet 2026-09-02): hämta startsidan,
    plocka arbetsmejl ur texten; annars följ upp till två kontakt-/om
    oss-länkar på samma domän och plocka därifrån. Samma verifieringar som
    research-vägen (`plocka_arbetsmejl` tar aldrig en privat adress, aldrig
    en främmande domän). Kastar aldrig — {"contact_email": None,
    "contact_level": None} är ett giltigt utfall."""
    tomt = {"contact_email": None, "contact_level": None}
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(8.0), follow_redirects=True,
            headers={"user-agent": "snajp-leads/1.0 (+https://snajp.se)"},
        ) as client:
            svar = await client.get(website)
            if svar.status_code >= 400:
                return tomt
            material = svar.text
            epost = plocka_arbetsmejl(material, website)
            if not epost:
                for lank in extrahera_kontaktlankar(material, website, tak=2):
                    try:
                        undersida = await client.get(lank)
                    except httpx.HTTPError:
                        continue
                    if undersida.status_code >= 400:
                        continue
                    epost = plocka_arbetsmejl(undersida.text, website)
                    if epost:
                        break
    except httpx.HTTPError:
        return tomt
    if not epost:
        return tomt
    # mailto-länkar bär ibland URL-kodade blanksteg ("mailto:%20info@...") —
    # första skarpa skörden levererade "%20info@bigacom.se" rakt in i
    # tabellen. Avkoda och trimma, och släpp bara igenom adressen om den
    # fortfarande är ett arbetsmejl på bolagets domän efteråt.
    from urllib.parse import unquote

    epost = unquote(epost).strip()
    if not ar_arbetsmejl(epost, webb=website):
        return tomt
    return {"contact_email": epost, "contact_level": "role_address"}


_TELEFON_PA_SIDA = re.compile(r"(?:\+46|0)\s?\d{1,3}(?:[\s\-]?\d{2,3}){2,4}")
_EPOST_PA_SIDA = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def _asci(text: str) -> str:
    import unicodedata

    bas = unicodedata.normalize("NFKD", text.casefold())
    return "".join(t for t in bas if not unicodedata.combining(t))


def vd_uppgift_i_text(text: str, vd_namn: str, website: str) -> dict[str, Any] | None:
    """VD:ns mejl eller telefon ur sidtext, BARA när uppgiften går att knyta
    till VD (Antons regel 2026-10-04: ett nummer som inte kan styrkas tillhöra
    en viss person används inte). Mejl: arbetsmejl på bolagets domän vars
    lokaldel bär VD:ns för- eller efternamn. Telefon: står inom 200 tecken från
    VD:ns fullständiga namn på sidan.
    ponytail: närhet i text, inte DOM-struktur; byt mot en strukturerad
    tolkning om sajter med flera personer per rad ger fel par."""
    led = [d for d in re.findall(r"[a-z]+", _asci(vd_namn)) if len(d) >= 3]
    if len(led) < 2:
        return None
    ren = re.sub(r"<[^>]+>", " ", text)
    ren = re.sub(r"\s+", " ", ren)
    asc = _asci(ren)
    for adress in dict.fromkeys(_EPOST_PA_SIDA.findall(ren)):
        lokal = _asci(adress.split("@")[0])
        if any(d in lokal for d in led) and ar_arbetsmejl(adress, webb=website):
            return {"contact_email": adress, "contact_phone": None}
    fullt = f"{led[0]} {led[-1]}"
    for m in re.finditer(re.escape(fullt), asc):
        # Efter namnet först ("Anna Andersson, VD, 070-…"), sedan närmast före;
        # ett växelnummer längre upp på sidan ska inte vinna (testet).
        efter = _TELEFON_PA_SIDA.search(ren[m.end(): m.end() + 200])
        fore = list(_TELEFON_PA_SIDA.finditer(ren[max(0, m.start() - 80): m.start()]))
        tel = efter or (fore[-1] if fore else None)
        if tel:
            return {"contact_email": None, "contact_phone": tel.group(0).strip()}
    return None


#: Rollen VD i de former den står på svenska sajter ("VD", "vd & grundare",
#: "Verkställande direktör", "CEO").
_VD_ROLL = re.compile(r"(?i)(?<![a-zåäö])(?:vd|verkställande\s+direktör|ceo)(?![a-zåäö])")


def ar_vd(roll: object) -> bool:
    return bool(_VD_ROLL.search(str(roll or "")))


def vd_mottagare(prospekt: dict[str, Any]) -> str | None:
    """Adressen ett Iris-utkast får skickas till, eller None.

    Antons regel 3 (2026-10-04): kontakta bara VD, och bara med en uppgift som
    går att styrka tillhöra VD. Det kräver att rollen är VD och att adressens
    lokaldel bär VD:ns för- eller efternamn på bolagets egen domän, samma krav
    som `vd_uppgift_i_text`. En funktionsadress (info@, rekrytering@) går inte
    att knyta till en person. Provkörningen 2026-10-05 skrev ett utkast till
    rekrytering@ och ett till en inköpschef."""
    namn = str(prospekt.get("contact_name") or "")
    epost = str(prospekt.get("contact_email") or "").strip()
    if not (ar_vd(prospekt.get("contact_role")) and namn and epost):
        return None
    if not ar_arbetsmejl(epost, webb=prospekt.get("website")):
        return None
    led = [d for d in re.findall(r"[a-z]+", _asci(namn)) if len(d) >= 3]
    lokal = _asci(epost.split("@", 1)[0])
    return epost if any(d in lokal for d in led) else None


async def hamta_vd_kontakt(website: str, vd_namn: str) -> dict[str, Any] | None:
    """Startsidan plus upp till tre kontakt-/om oss-sidor; första uppgift som
    går att knyta till VD vinner. Kastar aldrig."""
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(8.0), follow_redirects=True,
            headers={"user-agent": "snajp-leads/1.0 (+https://snajp.se)"},
        ) as client:
            svar = await client.get(website)
            if svar.status_code >= 400:
                return None
            hit = vd_uppgift_i_text(svar.text, vd_namn, website)
            if hit:
                return hit
            for lank in extrahera_kontaktlankar(svar.text, website, tak=3):
                try:
                    undersida = await client.get(lank)
                except httpx.HTTPError:
                    continue
                if undersida.status_code < 400:
                    hit = vd_uppgift_i_text(undersida.text, vd_namn, website)
                    if hit:
                        return hit
    except httpx.HTTPError:
        return None
    return None


def _slugga_bolagsnamn(namn: str) -> str:
    """'Nordkap Moduler AB' -> 'nordkapmoduler' — kandidatdomänens stam."""
    stam = namn.lower()
    for suffix in (" aktiebolag", " ab", " hb", " kb", " i sverige"):
        if stam.endswith(suffix):
            stam = stam[: -len(suffix)]
    ersatt = {"å": "a", "ä": "a", "ö": "o", "é": "e", "ü": "u"}
    stam = "".join(ersatt.get(t, t) for t in stam)
    return re.sub(r"[^a-z0-9]", "", stam)


#: Namnled som inte särskiljer ett bolag — matchar de i domänen bevisar
#: ingenting ("svenska" i svenskabyggab.se pekar inte ut NÅGOT bolag).
_GENERISKA_NAMNLED = frozenset(
    {
        "aktiebolag", "gruppen", "group", "svenska", "sverige", "sweden",
        "nordic", "norden", "holding", "invest", "konsult", "consulting",
        "partner", "partners", "service", "services", "entreprenad",
    }
)


def webbplats_matchar_namn(namn: str, url: str) -> bool:
    """Hör domänen rimligen till bolagsnamnet? Deterministisk heuristik.

    Bakgrund (pixelbesiktningen 2026-09-02): JobTech-annonsens arbetsgivar-URL
    togs rakt av som bolagets webbplats, och "Mickes fönsterputs och städ AB"
    fick optimaltrappstadning.se på sin rad. Annonsören och arbetsgivaren är
    inte alltid samma part, och en rad vars webbplats inte hör till bolaget
    förgiftar allt nedströms — kontaktskörden plockar då NÅGONS adress, bara
    inte prospektets (värre än ingen adress alls).

    Tre vägar till match, alla på asciifierade stammar utan skiljetecken:
      1. hela namnslugen ⊂ domänstammen ("smalandsstalhallar" ⊂ dito),
      2. domänstammen ⊂ namnslugen (kortformer: willys.se för "WiLLY:S AB"),
      3. ett SÄRSKILJANDE namnled på ≥5 tecken ⊂ domänstammen
         ("thalamus" ⊂ "thalamustech").
    Golvet på 5 tecken i väg 3 är inte godtyckligt: "städ" (4) ligger som
    delsträng i "trappstädning", och det var exakt den falska matchning
    grinden ska fälla. Korta äkta varumärken (IKEA) räddas av väg 1/2.

    Medvetet INTE använd på Gemini-utfyllnadens träffar: där har modellen
    sökuppdraget "bolagets egen officiella sajt" och ett legitimt varumärke
    kan heta något annat än bolaget (Fritidsfabriken ↔ annat AB-namn) —
    grinden här gäller KÄLLDATA som aldrig gjort det anspråket.
    """
    stam = _host(url).split(".", 1)[0]
    if not stam:
        return False
    slug = _slugga_bolagsnamn(namn)
    # Exakt likhet räddar korta äkta varumärken (ikea.se för "IKEA AB");
    # substrängsvägarna kräver ≥5 tecken av samma skäl som namnleden i väg 3
    # — "stad" (slugen av "Städ AB") ligger mitt i "optimaltrappstadning".
    if slug and slug == stam:
        return True
    if len(slug) >= 5 and slug in stam:
        return True
    if len(stam) >= 5 and stam in slug:
        return True
    ersatt = {"å": "a", "ä": "a", "ö": "o", "é": "e", "ü": "u"}
    for led in re.split(r"[^a-zA-Zåäöéü0-9]+", namn.lower()):
        led = "".join(ersatt.get(t, t) for t in led)
        if len(led) >= 5 and led not in _GENERISKA_NAMNLED and led in stam:
            return True
    return False


async def gissa_webbplats_via_head(namn: str) -> str | None:
    """Gissar https://<slug>.se och verifierar med en HEAD-request
    (opengtm-mönstret: acceptera 200/301/302/403, HTTPS först).

    Poängen är att den GROUNDED sökningen (`sla_upp_webbplats`, ett
    Gemini-anrop per namn) bara ska behöva köras när den här gratisvägen
    inte träffar — kostnadsarbetet 2026-09-02. En felgissning fastnar i
    verifieringen: svarar domänen inte finns ingen träff att råka spara.
    """
    slug = _slugga_bolagsnamn(namn)
    if len(slug) < 3:
        return None
    kandidater = (f"https://{slug}.se", f"https://www.{slug}.se", f"http://{slug}.se")
    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0), follow_redirects=False) as client:
        for url in kandidater:
            try:
                svar = await client.head(url)
            except httpx.HTTPError:
                continue
            if svar.status_code in (200, 301, 302, 403):
                slutlig = url
                if svar.status_code in (301, 302):
                    plats = svar.headers.get("location") or ""
                    # Följ bara en redirect till SAMMA stam — en parkerad
                    # domän som pekar mot en aggregator är ingen träff.
                    # Stammen ska stå i VÄRDNAMNET, inte var som helst i
                    # URL:en: edza.se pekade 2026-09-15 mot
                    # home.student.uu.se/edza0987, som "EdZa AB" fick som
                    # webbplats eftersom slugen stod i sökvägen.
                    if plats.startswith("http") and slug in _host(plats).replace("-", ""):
                        slutlig = plats
                    elif not plats.startswith("/"):
                        continue
                try:
                    return normalisera_webbplats(slutlig)
                except Exception:  # noqa: BLE001 — en ogiltig URL är ingen träff
                    continue
    return None


async def _sok_registrerade_kallor(
    icp: dict[str, Any], antal: int, uteslut: set[str]
) -> list[dict[str, Any]]:
    """Federationen (kostnadsarbetet 2026-09-02): deterministiska källor
    FÖRE den grounded Gemini-sökningen. openleads-mönstret — källor med tak,
    dedup på namn, och LLM:en får bara fylla upp det som fattas.

    Källfel fäller aldrig körningen: en källa som inte svarar hoppas över
    (Gemini-utfyllnaden tar vid), och sökningen körs i en tråd eftersom
    källprotokollet är synkront (se sources/base.py).
    """
    from .platshallare import ar_platshallare
    from .sources import standardkallor

    traffar: list[dict[str, Any]] = []
    sedda = upptagna.nycklar(uteslut)
    for kalla in standardkallor():
        if len(traffar) >= antal:
            break
        try:
            kandidater = await asyncio.to_thread(kalla.search, icp)
        except Exception as fel:  # noqa: BLE001 — en död källa fäller inte kedjan
            logger.warning("Källan %s svarade inte: %s", kalla.name, fel)
            continue
        for p in kandidater:
            nyckel = upptagna.nyckel(p.company_name)
            if nyckel in sedda:
                continue
            webb = p.website
            if webb:
                try:
                    webb = normalisera_webbplats(webb)
                except Exception:  # noqa: BLE001 — trasig käll-URL, gissa i stället
                    webb = None
                if webb and not webbplats_ar_bolagets(webb):
                    webb = None
                if webb and not webbplats_matchar_namn(p.company_name, webb):
                    # Käll-URL:en (t.ex. annonsens arbetsgivarlänk) hör inte
                    # ihop med bolagsnamnet — annonsören är inte alltid
                    # arbetsgivaren. Släng den och låt namngissningen ta vid;
                    # dess kandidat är namnhärledd och matchar per
                    # konstruktion. Se webbplats_matchar_namn.
                    logger.info(
                        "Källan %s gav %s en webbplats som inte matchar namnet (%s) — förkastas.",
                        p.source_name,
                        p.company_name,
                        webb,
                    )
                    webb = None
                if webb:
                    # Annonskällor pekar ofta på jobb./karriar.-subdomänen —
                    # kontaktsidan bor på apexen. Byt bara om apexen svarar.
                    apex = skala_karriarsubdoman(webb)
                    if apex and await _head_ok(apex):
                        webb = apex
            if not webb:
                webb = await gissa_webbplats_via_head(p.company_name)
            if not webb:
                # Utan verifierad egen webbplats finns ingen skrapyta och
                # ingen kontaktväg — träffen är inte användbar som lead.
                continue
            orsak = await ar_platshallare(webb)
            if orsak:
                # Kontrollen sitter FÖRE räkningen, så nästa kandidat tar
                # platsen i stället för att den blir tom (2026-09-15).
                logger.info(
                    "Källan %s gav %s en platshållarsida (%s) — nästa kandidat tar platsen.",
                    p.source_name,
                    p.company_name,
                    orsak,
                )
                sedda.add(nyckel)
                continue
            sedda.add(nyckel)
            traffar.append(
                {
                    "company_name": p.company_name,
                    "website": webb,
                    "orgnr": p.orgnr,
                    "ort": p.ort,
                    "contact_name": None,
                    "contact_role": None,
                    "contact_email": p.contact_email,
                    "contact_level": "role_address" if p.contact_email else None,
                    "contact_form_url": None,
                    "anstallda": p.anstallda,
                    # Signalen (rekryterar/bolagsnyhet) + annons-/nyhets-URL:en
                    # följer med till research-steget som trigger-underlag och
                    # till INV-DATA-001:s "varifrån kom uppgiften".
                    "source_name": p.source_name,
                    "source_url": p.source_url,
                    "signal": p.extra.get("signal"),
                    "signal_detalj": p.extra.get("annons_titel") or p.extra.get("nyhet_titel"),
                }
            )
            if len(traffar) >= antal:
                break
    return traffar


def _reserver(antal: int) -> int:
    """Extra rader att be Gemini om: hälften av det som fattas, minst 2 och
    högst 5. De täcker det som faller i platshållarfiltret och i
    `_rena_traffar`; överskottet kapas bort."""
    return min(5, max(2, (antal + 1) // 2))


def _profil_som_soktext(profil: dict[str, Any] | None, ring: int) -> str:
    """Iris-profilens sökledtrådar (app/leads/profil.py) — det som gjorde
    att Alunix körning 2026-09-29 letade fel: fokus, område och kriterier
    fanns bara i kundens fritext och nådde aldrig sökningen."""
    if not profil:
        return ""
    rader = []
    if profil.get("malgrupp"):
        rader.append(f"- Malgrupp: {profil['malgrupp']}")
    if profil.get("egen_bransch"):
        rader.append(f"- OBS: {profil['egen_bransch']} ar SALJARENS egen bransch, inte malgruppens.")
    ringar = profil.get("geo_prioritet") or []
    if ringar:
        aktuell = ringar[min(ring, len(ringar) - 1)]
        px = ", ".join(f"{p}xx" for p in aktuell.get("postnr_prefix") or [])
        rader.append(
            f"- Borja i: {aktuell['etikett']}" + (f" (postnummer {px})" if px else "")
            + (" — om det inte racker, fortsatt utat i narliggande omraden." if ring < len(ringar) - 1 else "")
        )
    omrade = [*(profil.get("kommuner") or []), *(profil.get("omraden") or [])]
    if omrade:
        rader.append("- Bolaget MASTE ligga i: " + ", ".join(omrade))
    for k in profil.get("kriterier") or []:
        rader.append(f"- {'Krav' if k.get('krav') == 'maste' else 'Helst'}: {k['text']}")
    for u in profil.get("uteslut") or []:
        rader.append(f"- Uteslut: {u['text']}")
    if profil.get("utan_webbplats"):
        rader.append(
            "- Bolag UTAN egen webbplats ingar i malgruppen: satt website null och ange orgnr, "
            "ort, postnr och en officiell kontakt-e-post om den finns i ett offentligt register."
        )
    return "Iris-profil (kundens egna kriterier):\n" + "\n".join(rader) + "\n"


def _bolagsnyckel(rad: dict[str, Any]) -> set[str]:
    """Nycklar som identifierar samma bolag i register och signalkälla:
    orgnr (siffror), bolagsnamn (casefold), sajtens värd."""
    nycklar: set[str] = set()
    orgnr = "".join(ch for ch in str(rad.get("orgnr") or "") if ch.isdigit())
    if orgnr:
        nycklar.add(f"orgnr:{orgnr}")
    namn = str(rad.get("company_name") or "").casefold().strip()
    if namn:
        nycklar.add(f"namn:{namn}")
    webb = str(rad.get("website") or "").casefold()
    webb = re.sub(r"^https?://(www\.)?", "", webb).split("/")[0]
    if webb:
        nycklar.add(f"webb:{webb}")
    return nycklar


def _med_signaler(register: list[dict[str, Any]], signaler: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Registerrader med en signalträff får signalen och går först; ordningen
    inom grupperna behålls (registret är redan rangordnat)."""
    if not signaler:
        return register
    per_nyckel: dict[str, dict[str, Any]] = {}
    for s in signaler:
        for n in _bolagsnyckel(s):
            per_nyckel.setdefault(n, s)
    med: list[dict[str, Any]] = []
    utan: list[dict[str, Any]] = []
    for rad in register:
        traff = next((per_nyckel[n] for n in _bolagsnyckel(rad) if n in per_nyckel), None)
        if traff:
            rad = {
                **rad,
                "signal": traff.get("signal") or rad.get("signal"),
                "signal_detalj": traff.get("signal_detalj") or rad.get("signal_detalj"),
                "signal_kalla": traff.get("source_url"),
            }
            med.append(rad)
        else:
            utan.append(rad)
    return med + utan


#: Så många uteslutna namn som skrivs in i sökprompten. En uppladdad
#: CRM-lista kan bära tusentals; resten fälls av _rena_traffar efteråt.
PROMPT_UTESLUT_TAK = 150


def _uteslut_i_prompt(uteslut: set[str]) -> str:
    namn = upptagna.bara_namn(uteslut)[:PROMPT_UTESLUT_TAK]
    # Prompten går genom str.format: klamrar i ett bolagsnamn får inte tolkas.
    return (", ".join(namn) or "(inga)").replace("{", "{{").replace("}", "}}")


async def hitta_bolag(
    icp: dict[str, Any],
    antal: int,
    *,
    uteslut_namn: set[str] | None = None,
    profil: dict[str, Any] | None = None,
    ring: int = 0,
    listspar: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Returnerar upp till `antal` riktiga bolag. Tom lista = inga verifierbara traffar.

    `listspar` (plan 2026-10-05): registerkällan lägger där de bolag som inte
    blir Iris-leads men hör hemma i en lista (ingen sajt, parkerad domän,
    ingen VD-kontakt på sajten).

    Sedan 2026-09-02 är den grounded Gemini-sökningen UTFYLLNAD, inte
    förstahandsval: de registrerade källorna (JobTech-annonser, nyhets-RSS —
    gratis, deterministiska, signalrika) körs först, och Gemini söker bara
    efter det som fattas upp till `antal`. Max ETT grounded sökanrop per
    körning, som förr.
    """
    if antal <= 0:
        return []
    uteslut = upptagna.nycklar(uteslut_namn or ())
    # Prompten får namnen som de skrevs, inte jämförelsenycklarna: "Nordkap
    # Moduler AB" säger modellen mer än "nordkap moduler".
    prompt_namn = {n.casefold() for n in (uteslut_namn or ()) if n}

    # Registerkällan först (merinfo via ScrapeGraphAI, TILLFÄLLIG tills ett
    # API-avtal finns, se sources/merinfo.py). Bara när LEADS_MERINFO är
    # satt. Färre träffar än beställt levereras som de är: utfyllnaden nedan
    # saknar telefon och skulle bryta kontaktkravet. None betyder att
    # målgruppen inte gick att översätta till merinfos träd, och då tar den
    # gamla kedjan vid.
    from .sources import merinfo

    if merinfo.aktiv():
        fran_register = await merinfo.sok(icp, antal, uteslut=uteslut, profil=profil, listspar=listspar)
        if fran_register is not None:
            # Register ∩ signaler (plan del C, 2026-10-02): annons- och
            # nyhetskällorna avgör inte urvalet, de rankar det. Ett
            # registerbolag med en signal går först; en signalträff utanför
            # registret är inte målgruppen och faller. Körs bara när kunden
            # kräver signaler, som den gamla kedjan.
            signaler = await _sok_registrerade_kallor(icp, antal, uteslut) if icp.get("must_have") else []
            return _med_signaler(fran_register, signaler)[:antal]

    from .platshallare import utan_platshallare

    # Parkerade domäner och "under konstruktion" tas bort INNAN de tar en
    # plats (se leads/platshallare.py) — och platsen fylls på: källslingan
    # hoppar till nästa kandidat, och Gemini ombeds om reserver i samma
    # anrop. Uppmätt 2026-09-15: filtret utan påfyllning gav 4 bolag när
    # kunden beställt 5.
    # Annons- och nyhetskällorna fyllde Alunix körning 2026-09-29 med
    # 700-mannabolag och bemanningsföretag — de hittar bolag som REKRYTERAR,
    # vilket bara är en signal när kunden uttryckligen kräver den. Med en
    # profil körs de därför bara när "Signaler som krävs" är ifyllt.
    kor_kallor = profil is None or bool(icp.get("must_have"))
    fran_kallor = await _sok_registrerade_kallor(icp, antal, uteslut) if kor_kallor else []
    if len(fran_kallor) >= antal:
        return fran_kallor[:antal]
    uteslut = uteslut | {upptagna.nyckel(t["company_name"]) for t in fran_kallor}
    prompt_namn |= {t["company_name"].casefold() for t in fran_kallor}
    antal_kvar = antal - len(fran_kallor)
    # Reserverna ryms i SAMMA sökanrop — taket på ett grounded anrop per
    # körning står kvar.
    antal_begart = antal_kvar + _reserver(antal_kvar)
    # Sökningen ska hitta BOLAG, ingenting annat. Före 2026-10-06 krävde
    # prompten en kontaktuppgift för varje bolag ("OBLIGATORISKT") och bad om
    # ort och antal anställda. Under det trycket fyllde modellen i fälten
    # själv: tre bolag som inte finns, med gissade info@-adresser, och ort och
    # storlek som ekade målgruppens filter och gav poäng 100. Antons regler
    # 2026-10-04 gäller i stället: bara VD, och bara en uppgift som går att
    # styrka. Kontakten, orten och storleken hämtas därför ur bolagets egna
    # sidor i researchen, och fälten nedan följer inte med till prospektet
    # (api/leads.py, _skapa_prospekt_ur_kandidat). Rollerna i kundens filter
    # hör inte heller hemma här: "Platschef" drog sökningen mot byggbolag.
    offentligt = (
        ""
        if (profil or {}).get("offentlig_sektor")
        else "Bara PRIVATA bolag: inga kommuner, regioner, myndigheter, statliga "
        "eller kommunala bolag och inga skolor.\n"
    )
    prompt = (
        "Hitta upp till {antal} RIKTIGA svenska bolag som matchar malgruppen nedan. "
        "Anvand sokning.\n\n"
        "Varje bolag MASTE komma ur ett sokresultat du faktiskt fatt. Hitta "
        "ALDRIG pa ett bolagsnamn eller en webbadress, och fyll ALDRIG ut listan "
        "for att na antalet. Farre bolag an begart ar ett korrekt svar, och en "
        "tom lista [] ar ett korrekt svar nar sokningen inte gav nagot.\n"
        f"{offentligt}\n"
        "Returnera ENBART en JSON-lista:\n"
        '[{{"company_name":"...","website":"https://...","orgnr":null}}]\n'
        "website MASTE vara bolagets egen officiella sajt sa som den star i "
        "sokresultatet, inte allabolag/hitta/ratsit/linkedin och inte en adress "
        "du satt ihop av bolagsnamnet. orgnr bara om det star pa bolagets egen "
        "sajt. Ange inga kontaktpersoner, e-postadresser, orter eller antal "
        "anstallda: de hamtas fran bolagets sajt i nasta steg.\n\n"
        f"Malgrupp:\n{_icp_som_text({**icp, 'roles': []})}\n"
        f"{_profil_som_soktext(profil, ring)}"
        f"Uteslut dessa namn: {_uteslut_i_prompt(prompt_namn)}\n"
    ).format(antal=antal_begart)
    try:
        text = await _gemini_med_sokning(prompt)
    except DiscoveryError:
        if fran_kallor:
            # Källträffarna är redan verifierade — en fallen utfyllnad ska
            # inte kasta bort dem. Färre än beställt är ett giltigt utfall.
            logger.warning("Discovery-utfyllnaden misslyckades — levererar källträffarna.")
            return fran_kallor
        logger.warning("Discovery-sokningen misslyckades.")
        raise
    utan_webb = bool(profil and profil.get("utan_webbplats"))
    rena = _rena_traffar(_plocka_json(text), uteslut=uteslut, tak=antal_begart, tillat_utan_webb=utan_webb)
    # En platshållarsida ("under konstruktion") ÄR målgruppen när kunden
    # söker bolag utan fungerande webbplats — den mäts av webbsignal i stället.
    if not utan_webb:
        rena = await utan_platshallare(rena)
    # Märks som sökträffar: allt på raden är modellens påstående tills
    # existensgrinden (leads/existens.py) och researchen styrkt det. Kontakten
    # följer därför inte med till prospektet (api/leads.py), och ort och
    # storlek räknas inte som fakta i bedömningen (leads/bedomning.py).
    return fran_kallor + [{**rad, "kalla": "gemini"} for rad in rena[:antal_kvar]]


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
