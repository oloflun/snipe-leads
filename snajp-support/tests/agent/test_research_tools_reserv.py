"""Skrapningens reservväg: när ScrapeGraphAI fallerar hämtas samma registrerade
URL direkt, och en platshållarsida märks upp i stället för att tolkas.

Uppmätt 2026-09-15 i QA-kundens körning: itkonsulterna.se gav "HTTP 502" från
ScrapeGraphAI efter 54 s (sidan svarade på 0,3 s direkt), och
almapropertypartners.se är parkerad hos Loopia. Båda bolagen researchades
utan källmaterial. All HTTP mockas.
"""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.agent import research_tools
from app.agent.leads_context import ResearchContext
from app.agent.research_tools import _hamta_direkt, _scrape_registered_source_impl
from app.config import get_settings
from app.storage.memory import MemoryStorage

TENANT = "tenant-a"
PROSPECT = "prospect-1"
URL = "https://exempelbolaget.se"
_RIKTIG_ASYNC_CLIENT = httpx.AsyncClient

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _fake_sgai_key(monkeypatch):
    monkeypatch.setenv("SCRAPEGRAPHAI_API_KEY", "sgai-test-not-a-real-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def _ctx() -> ResearchContext:
    storage = MemoryStorage()
    await storage.create_prospect_source(
        TENANT,
        prospect_id=PROSPECT,
        source_url=URL,
        source_type="company_website",
        lawful_basis="Publikt tillgänglig",
    )
    return ResearchContext(storage=storage, tenant_id=TENANT, prospect_id=PROSPECT)


def _sgai(*, status="success", error=None, markdown=None, sov=0.0):
    resultat = MagicMock()
    resultat.status = status
    resultat.error = error
    resultat.data = MagicMock()
    resultat.data.results = {"markdown": {"data": markdown or []}}
    klient = MagicMock()

    def scrape(url):
        if sov:
            time.sleep(sov)
        return resultat

    klient.scrape.side_effect = scrape
    return klient


def _mocka_webb(monkeypatch, handler):
    def fabrik(**kwargs):
        return _RIKTIG_ASYNC_CLIENT(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr("app.agent.research_tools.httpx.AsyncClient", fabrik)


_HTML = (
    "<html><head><script>var x = 1;</script><style>p{}</style></head><body>"
    "<h1>IT-Konsulterna</h1><p>Vi är 14 konsulter i Stockholm.</p>"
    '<a href="/kontakt">Kontakta oss</a></body></html>'
)


async def test_502_fran_scrapegraph_ger_direkthamtning(monkeypatch):
    _mocka_webb(monkeypatch, lambda r: httpx.Response(200, text=_HTML, headers={"content-type": "text/html"}))
    ctx = await _ctx()
    with patch("scrapegraph_py.ScrapeGraphAI", return_value=_sgai(status="error", error="HTTP 502")):
        svar = json.loads(await _scrape_registered_source_impl(ctx, URL))

    assert "Vi är 14 konsulter i Stockholm." in svar["content"]
    assert "var x" not in svar["content"], "skript ska inte med i materialet"
    assert "[Kontakta oss](/kontakt)" in svar["content"], "länkar behövs för kontaktupptäckten"
    assert "<untrusted-data-" in svar["content"]
    assert ctx.scraped_sources[0]["via"] == "direkt"


async def test_hangande_scrapegraph_slapper_efter_taket(monkeypatch):
    monkeypatch.setattr(research_tools, "SGAI_TAK_SEKUNDER", 0.05)
    _mocka_webb(monkeypatch, lambda r: httpx.Response(200, text=_HTML, headers={"content-type": "text/html"}))
    ctx = await _ctx()
    start = time.monotonic()
    with patch("scrapegraph_py.ScrapeGraphAI", return_value=_sgai(sov=0.5, markdown=["sent"])):
        svar = json.loads(await _scrape_registered_source_impl(ctx, URL))
    assert time.monotonic() - start < 0.45, "taket ska släppa utan att vänta ut tjänsten"
    assert "14 konsulter" in svar["content"]


async def test_lyckad_scrapegraph_gor_ingen_direkthamtning():
    ctx = await _ctx()
    direkt = AsyncMock(side_effect=AssertionError("ska inte anropas"))
    with (
        patch("scrapegraph_py.ScrapeGraphAI", return_value=_sgai(markdown=["# Exempelbolaget", "Vi säljer skor."])),
        patch("app.agent.research_tools._hamta_direkt", new=direkt),
    ):
        svar = json.loads(await _scrape_registered_source_impl(ctx, URL))
    assert "Vi säljer skor." in svar["content"]
    assert ctx.scraped_sources[0]["via"] == "scrapegraphai"


async def test_bada_vagarna_fallerar_ger_ett_samlat_fel(monkeypatch):
    _mocka_webb(monkeypatch, lambda r: httpx.Response(403, text="nej"))
    ctx = await _ctx()
    with patch("scrapegraph_py.ScrapeGraphAI", return_value=_sgai(status="error", error="HTTP 502")):
        svar = json.loads(await _scrape_registered_source_impl(ctx, URL))
    assert "HTTP 502" in svar["error"]
    assert "HTTP 403" in svar["error"]
    assert ctx.scraped_sources == []


async def test_parkeringssida_markeras_som_platshallare():
    ctx = await _ctx()
    parkerad = [
        "# Parked at Loopia\n\nThis domain has been purchased and parked by a customer of Loopia."
    ]
    with patch("scrapegraph_py.ScrapeGraphAI", return_value=_sgai(markdown=parkerad)):
        svar = json.loads(await _scrape_registered_source_impl(ctx, URL))
    assert svar["content"].startswith("KODNOTERING")
    assert "parkerad domän" in svar["content"]
    assert ctx.scraped_sources[0]["platshallare"] == "parkerad domän"


async def test_direkthamtning_godtar_inte_omdirigering_till_annan_doman(monkeypatch):
    def handler(request):
        if request.url.host == "exempelbolaget.se":
            return httpx.Response(301, headers={"location": "https://home.student.uu.se/edza0987/"})
        return httpx.Response(200, text="<p>Studentsida</p>", headers={"content-type": "text/html"})

    _mocka_webb(monkeypatch, handler)
    text, fel = await _hamta_direkt(URL)
    assert text is None
    assert "annan domän" in fel


async def test_direkthamtning_vagrar_annat_an_webbsidor(monkeypatch):
    _mocka_webb(monkeypatch, lambda r: httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"}))
    text, fel = await _hamta_direkt(URL)
    assert text is None
    assert "inte en webbsida" in fel
