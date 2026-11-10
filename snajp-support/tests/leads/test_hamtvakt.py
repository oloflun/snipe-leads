"""Leadshämtarna når bara det publika nätet (Fas 0, 2026-11-09).

Iris hämtar bolagens webbplatser från VÅR server. Adressen kommer ur
registret, ur en sökning eller från kunden själv (ett prospekt som läggs till
för hand), och en sida kan omdirigera vart som helst. Utan spärr gick det att
peka hämtningen mot molnets metadatatjänst eller en intern Railway-adress och
få svaret inläst i researchen. Kundens integrationer har haft spärren sedan
tidigare (app/integrationer/natvakt.py); leadshämtarna hade ingen.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from app.integrationer import natvakt
from app.leads import hamtvakt

pytestmark = pytest.mark.anyio
APP = Path(__file__).resolve().parents[2] / "app"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def dns(monkeypatch):
    """Värdnamn → adresser, utan riktig DNS. Okända namn är publika."""
    tabell: dict[str, list[str]] = {}

    async def _upplos(vard: str, port: int) -> list[str]:
        return tabell.get(vard, ["93.184.216.34"])

    monkeypatch.setattr(natvakt, "upplos", _upplos)
    return tabell


@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/latest/meta-data/",
        "http://localhost:8000/api/admin/tenants",
        "http://127.0.0.1:8080/",
        "http://10.0.0.5/",
        "https://[::1]/",
        "http://snipe-leads.railway.internal:8080/api/admin/tenants",
        "http://intranat/",
        "ftp://exempel.se/fil",
        "file:///etc/passwd",
        "http://anvandare:losen@exempel.se/",
    ],
)
async def test_interna_och_udda_adresser_sparras(dns, url):
    with pytest.raises(natvakt.NatvaktError):
        await hamtvakt.kontrollera(url)


@pytest.mark.parametrize("url", ["https://exempel.se/", "http://exempel.se/kontakt", "https://www.exempel.se:8443/"])
async def test_publika_webbplatser_slapps_igenom_aven_utan_tls(dns, url):
    await hamtvakt.kontrollera(url)  # ska inte kasta


async def test_namn_som_pekar_pa_ett_internt_nat_sparras(dns):
    dns["snall.exempel.se"] = ["10.0.0.7"]
    with pytest.raises(natvakt.NatvaktError):
        await hamtvakt.kontrollera("https://snall.exempel.se/")


async def test_omdirigering_till_en_intern_adress_foljs_inte(dns):
    """Spärren gäller varje hopp, inte bara den adress vi började på."""
    sedda: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sedda.append(str(request.url))
        if request.url.host == "exempel.se":
            return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data/"})
        return httpx.Response(200, text="hemligt")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True, event_hooks=hamtvakt.krokar()
    ) as klient:
        with pytest.raises(httpx.HTTPError):
            await klient.get("https://exempel.se/")

    assert sedda == ["https://exempel.se/"], "den interna adressen fick aldrig anropas"


async def test_sparren_ar_ett_vanligt_natfel_for_anroparna(dns):
    """Hämtarna fångar httpx.HTTPError och går vidare; spärren ska hamna där."""
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200)), event_hooks=hamtvakt.krokar()
    ) as klient:
        with pytest.raises(httpx.ConnectError):
            await klient.get("http://127.0.0.1:8080/")


@pytest.mark.parametrize(
    ("fil", "antal"),
    [
        ("leads/discovery.py", 4),
        ("leads/platshallare.py", 1),
        ("leads/webbsignal.py", 1),
        ("leads/webbrevision.py", 1),
        ("agent/research_tools.py", 1),
    ],
)
def test_hamtarna_ar_inkopplade(fil, antal):
    kalla = (APP / fil).read_text(encoding="utf-8")
    assert kalla.count("event_hooks=hamtvakt.krokar()") >= antal, fil
