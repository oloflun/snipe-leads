"""Källfederationen (kostnadsarbetet 2026-09-02): JobTech + nyhets-RSS
FÖRE den grounded Gemini-sökningen, som blir utfyllnad i stället för
förstahandsval.

All HTTP mockas (httpx.MockTransport) — inga nätanrop i sviten.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.leads.discovery import gissa_webbplats_via_head, hitta_bolag
from app.leads.sources import standardkallor
from app.leads.sources.jobtech import JobTechSource
from app.leads.sources.nyheter import NyhetsSource

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


ICP = {
    "industries": ["tillverkning"],
    "geography": "Umeå",
    "roles": ["Kundtjänstchef"],
}


#: De riktiga klasserna, infångade FÖRE monkeypatch — att patcha
#: `modulens httpx.Client` patchar httpx globalt (samma modulobjekt), och en
#: fabrik som själv anropar `httpx.Client` rekurserar då i evighet.
_RIKTIG_CLIENT = httpx.Client
_RIKTIG_ASYNC_CLIENT = httpx.AsyncClient


def _mockad_client(handler):
    """httpx.Client-fabrik med MockTransport, kwargs-kompatibel med källorna."""

    def _fabrik(**kwargs):
        return _RIKTIG_CLIENT(transport=httpx.MockTransport(handler))

    return _fabrik


# --- JobTechSource ----------------------------------------------------------


def _jobtech_svar(hits):
    def handler(request):
        return httpx.Response(200, json={"hits": hits})

    return handler


def test_jobtech_parsar_traffar_och_filtrerar_offentlig_sektor(monkeypatch):
    hits = [
        {
            "employer": {"name": "Nordkap Moduler AB", "url": "https://nordkapmoduler.se"},
            "workplace_address": {"municipality": "Umeå"},
            "webpage_url": "https://arbetsformedlingen.se/annons/1",
            "headline": "Kundtjänstmedarbetare",
            "occupation": {"label": "Kundtjänstmedarbetare"},
        },
        {"employer": {"name": "Umeå kommun"}, "workplace_address": {}},
        {"employer": {"name": "Nordkap Moduler AB"}},  # dublett — ska dedupas
        {"employer": {}},  # namnlös — ska hoppas
    ]
    monkeypatch.setattr(
        "app.leads.sources.jobtech.httpx.Client", _mockad_client(_jobtech_svar(hits))
    )
    traffar = JobTechSource().search(ICP)
    assert [p.company_name for p in traffar] == ["Nordkap Moduler AB"]
    p = traffar[0]
    assert p.website == "https://nordkapmoduler.se"
    assert p.ort == "Umeå"
    assert p.source_name == "jobtech"
    assert p.source_url == "https://arbetsformedlingen.se/annons/1"
    assert p.extra["signal"] == "rekryterar"


# --- NyhetsSource -----------------------------------------------------------


_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
<channel><title>Sök</title>
<item>
  <title>Smålands Stålhallar expanderar till Skåne</title>
  <link>https://www.mynewsdesk.com/se/pressreleases/1</link>
  <dc:creator>Smålands Stålhallar AB</dc:creator>
  <description>Bolaget öppnar nytt platskontor.</description>
</item>
<item>
  <title>Ny färg på vårens kollektion</title>
  <link>https://www.mynewsdesk.com/se/pressreleases/2</link>
  <dc:creator>Modehuset AB</dc:creator>
  <description>Trendspaning utan växtsignal.</description>
</item>
</channel></rss>"""


def test_nyheter_plockar_bara_poster_med_vaxtsignal(monkeypatch):
    def handler(request):
        return httpx.Response(200, text=_RSS)

    monkeypatch.setattr("app.leads.sources.nyheter.httpx.Client", _mockad_client(handler))
    traffar = NyhetsSource().search(ICP)
    assert [p.company_name for p in traffar] == ["Smålands Stålhallar AB"]
    assert traffar[0].extra["signal"] == "bolagsnyhet"


def test_standardkallor_styrs_av_env(monkeypatch):
    monkeypatch.setenv("LEADS_KALLOR", "jobtech")
    kallor = standardkallor()
    assert [k.name for k in kallor] == ["jobtech"]
    monkeypatch.delenv("LEADS_KALLOR")
    assert [k.name for k in standardkallor()] == ["jobtech", "nyheter"]


# --- Webbplatsgissningen ----------------------------------------------------


async def test_gissa_webbplats_via_head_verifierar(monkeypatch):
    def handler(request):
        if request.url.host == "nordkapmoduler.se" and request.url.scheme == "https":
            return httpx.Response(200)
        return httpx.Response(404)

    def _fabrik(**kwargs):
        return _RIKTIG_ASYNC_CLIENT(transport=httpx.MockTransport(handler))

    monkeypatch.setattr("app.leads.discovery.httpx.AsyncClient", _fabrik)
    assert await gissa_webbplats_via_head("Nordkap Moduler AB") == "https://nordkapmoduler.se"
    assert await gissa_webbplats_via_head("Bolag Som Inte Finns AB") is None


# --- Karriärsubdomäner och kontaktskörden -----------------------------------


def test_skala_karriarsubdoman():
    from app.leads.discovery import skala_karriarsubdoman

    assert skala_karriarsubdoman("https://jobb.thalamustech.se") == "https://thalamustech.se"
    assert skala_karriarsubdoman("https://karriar.bigacom.se/ledigt") == "https://bigacom.se"
    assert skala_karriarsubdoman("https://www.willys.se") is None


async def test_hamta_kontaktvag_plockar_arbetsmejl(monkeypatch):
    from app.leads.discovery import hamta_kontaktvag

    sidor = {
        "https://nordkapmoduler.se": '<a href="/kontakt">Kontakta oss</a>',
        "https://nordkapmoduler.se/kontakt": "Mejla oss: kundservice@nordkapmoduler.se",
    }

    def handler(request):
        return httpx.Response(200, text=sidor.get(str(request.url).rstrip("/"), ""))

    def _fabrik(**kwargs):
        return _RIKTIG_ASYNC_CLIENT(transport=httpx.MockTransport(handler))

    monkeypatch.setattr("app.leads.discovery.httpx.AsyncClient", _fabrik)
    kontakt = await hamta_kontaktvag("https://nordkapmoduler.se")
    assert kontakt == {
        "contact_email": "kundservice@nordkapmoduler.se",
        "contact_level": "role_address",
    }


async def test_hamta_kontaktvag_tomt_ar_giltigt(monkeypatch):
    from app.leads.discovery import hamta_kontaktvag

    def handler(request):
        return httpx.Response(200, text="Bara text, ingen adress, inga länkar.")

    def _fabrik(**kwargs):
        return _RIKTIG_ASYNC_CLIENT(transport=httpx.MockTransport(handler))

    monkeypatch.setattr("app.leads.discovery.httpx.AsyncClient", _fabrik)
    assert await hamta_kontaktvag("https://nordkapmoduler.se") == {
        "contact_email": None,
        "contact_level": None,
    }


# --- Federationen i hitta_bolag ---------------------------------------------


class _FejkKalla:
    name = "fejk"

    def __init__(self, prospekt):
        self._prospekt = prospekt

    def search(self, icp):
        return self._prospekt


async def test_fulla_kallor_ger_noll_gemini_anrop(monkeypatch):
    from app.leads.sources.base import Prospect

    kalla = _FejkKalla(
        [
            Prospect(company_name="Nordkap Moduler AB", website="https://nordkapmoduler.se", source_name="jobtech"),
            Prospect(company_name="Smålands Stålhallar AB", website="https://smalandsstalhallar.se", source_name="nyheter"),
        ]
    )
    monkeypatch.setattr("app.leads.sources.standardkallor", lambda: [kalla])
    gemini = AsyncMock()
    with patch("app.leads.discovery._gemini_med_sokning", gemini):
        traffar = await hitta_bolag(ICP, 2)

    gemini.assert_not_awaited()
    assert [t["company_name"] for t in traffar] == [
        "Nordkap Moduler AB",
        "Smålands Stålhallar AB",
    ]
    assert traffar[0]["signal"] == None or "signal" in traffar[0]


async def test_delvisa_kallor_fylls_upp_av_gemini(monkeypatch):
    from app.leads.sources.base import Prospect

    kalla = _FejkKalla(
        [Prospect(company_name="Nordkap Moduler AB", website="https://nordkapmoduler.se", source_name="jobtech")]
    )
    monkeypatch.setattr("app.leads.sources.standardkallor", lambda: [kalla])
    gemini = AsyncMock(
        return_value=json.dumps(
            [
                {
                    "company_name": "Baltic Pump Systems AB",
                    "website": "https://balticpump.se",
                    "contact_email": "info@balticpump.se",
                    "contact_level": "role_address",
                }
            ]
        )
    )
    with patch("app.leads.discovery._gemini_med_sokning", gemini):
        traffar = await hitta_bolag(ICP, 2)

    assert gemini.await_count == 1, "Gemini ska fylla upp EXAKT en gång"
    # Prompten ska be om det som FATTAS, inte hela antalet.
    prompt = gemini.await_args.args[0]
    assert "Hitta 1 RIKTIGA" in prompt
    assert "nordkap moduler ab" in prompt.lower(), "källträffen ska uteslutas ur sökningen"
    assert [t["company_name"] for t in traffar] == [
        "Nordkap Moduler AB",
        "Baltic Pump Systems AB",
    ]


async def test_dod_kalla_faller_inte_korningen(monkeypatch):
    class _Trasig:
        name = "trasig"

        def search(self, icp):
            raise RuntimeError("källan är nere")

    monkeypatch.setattr("app.leads.sources.standardkallor", lambda: [_Trasig()])
    gemini = AsyncMock(return_value="[]")
    with patch("app.leads.discovery._gemini_med_sokning", gemini):
        traffar = await hitta_bolag(ICP, 2)
    assert traffar == []
    assert gemini.await_count == 1


async def test_kalltraff_utan_verifierbar_webbplats_hoppar(monkeypatch):
    from app.leads.sources.base import Prospect

    kalla = _FejkKalla([Prospect(company_name="Spökbolaget AB", source_name="jobtech")])
    monkeypatch.setattr("app.leads.sources.standardkallor", lambda: [kalla])
    with (
        patch("app.leads.discovery.gissa_webbplats_via_head", new=AsyncMock(return_value=None)),
        patch("app.leads.discovery._gemini_med_sokning", new=AsyncMock(return_value="[]")),
    ):
        traffar = await hitta_bolag(ICP, 1)
    assert traffar == [], "utan verifierad egen webbplats finns ingen skrapyta — ingen träff"
