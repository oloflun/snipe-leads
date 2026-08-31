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

import json
import logging
import re
from typing import Any
from urllib.parse import urlparse

import httpx

from ..config import get_settings

logger = logging.getLogger("snajp-support.leads-discovery")

LAGLIG_GRUND_EGEN_WEBB = (
    "Berättigat intresse för B2B-prospektering mot bolagets egna publika "
    "webbplats (GDPR art. 6.1 f)."
)

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


class DiscoveryError(RuntimeError):
    """Sökningen kunde inte genomföras. Skiljd från 'noll träffar'."""


def _host(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


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
    async with httpx.AsyncClient(timeout=45.0) as client:
        svar = await client.post(url, params={"key": nyckel}, json=kropp)
    if svar.status_code >= 400:
        raise DiscoveryError(f"Sokningen avvisades ({svar.status_code}).")
    data = svar.json()
    delar = (
        (data.get("candidates") or [{}])[0]
        .get("content", {})
        .get("parts", [])
    )
    return "".join(str(p.get("text") or "") for p in delar)


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
        rena.append(
            {
                "company_name": namn,
                "website": webb,
                "orgnr": str(rad["orgnr"]).strip() if rad.get("orgnr") else None,
                "ort": str(rad["ort"]).strip() if rad.get("ort") else None,
                "contact_email": str(rad["contact_email"]).strip() if rad.get("contact_email") else None,
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
    prompt = (
        "Hitta {antal} RIKTIGA svenska aktiebolag som matchar malgruppen nedan. "
        "Anvand sokning. Hitta inte pa bolag. Returnera ENBART en JSON-lista:\n"
        '[{{"company_name":"...","website":"https://...","orgnr":null,"ort":"...","contact_email":null,"anstallda":null}}]\n'
        "website MÅSTE vara bolagets egen officiella sajt, inte allabolag/hitta/ratsit/"
        "linkedin. orgnr bara om det star pa bolagets egen sajt. contact_email bara "
        "info@/kontakt@ pa samma doman.\n\n"
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
