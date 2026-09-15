"""Platshållarsidor känns igen och sorteras bort i discovery.

Texterna är de verkliga sidorna ur QA-kundens körning 2026-09-15:
almapropertypartners.se (parkerad hos Loopia) och itkonsulterna.se
("Under konstruktion"). All HTTP mockas.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.leads import platshallare
from app.leads.platshallare import html_till_text, platshallarskal, utan_platshallare

_RIKTIG_ASYNC_CLIENT = httpx.AsyncClient

LOOPIA = (
    "Parkerad hos Loopia Det här domännamnet är köpt och parkerat av en kund till "
    "Loopia. Använd LoopiaWHOIS för att se domäninnehavarens publika uppgifter."
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.parametrize(
    "text,skal",
    [
        (LOOPIA, "parkerad domän"),
        ("# Parked at Loopia\n\nThis domain has been purchased and parked.", "parkerad domän"),
        ("Under konstruktion", "under konstruktion"),
        ("Denna domän är till salu. Kontakta oss.", "domänen är till salu"),
        ("Welcome to nginx! If you see this page, the nginx web server is installed.", "webbhotellets standardsida"),
    ],
)
def test_platshallare_kanns_igen(text, skal):
    assert platshallarskal(text) == skal


def test_riktig_sida_som_namner_en_markor_ar_ingen_platshallare():
    lang = ("Vi är en redovisningsbyrå i Göteborg med 13 medarbetare. " * 40) + "Vårt nya kontor är under konstruktion."
    assert platshallarskal(lang) is None


@pytest.mark.parametrize("text", ["", None, "Ekord AB — redovisning, lön och rådgivning i Mölndal."])
def test_vanlig_eller_tom_text_ar_ingen_platshallare(text):
    assert platshallarskal(text) is None


def test_adresser_i_bildlankar_raknas_inte_in_i_langden():
    """ScrapeGraphAI:s markdown för Loopia-sidan bär långa bild- och länkadresser."""
    md = "![Under construction](https://static.loopia.se/" + "x" * 3000 + ".webp)\n\n# Parked at Loopia"
    assert platshallarskal(md) == "parkerad domän"


def test_html_till_text_behaller_lankar_och_slanger_skript():
    html = "<script>alert(1)</script><p>Hej &amp; välkommen</p><a href='/om-oss'>Om <b>oss</b></a>"
    text = html_till_text(html)
    assert "alert" not in text
    assert "Hej & välkommen" in text
    assert "[Om oss](/om-oss)" in text


def _mocka_webb(monkeypatch, handler):
    def fabrik(**kwargs):
        return _RIKTIG_ASYNC_CLIENT(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr("app.leads.platshallare.httpx.AsyncClient", fabrik)


@pytest.mark.anyio
async def test_platshallare_for_webbplats_hamtar_och_bedomer(monkeypatch):
    sidor = {
        "almapropertypartners.se": httpx.Response(200, text=f"<p>{LOOPIA}</p>"),
        "fojab.se": httpx.Response(403, text="Forbidden"),
        "ekord.se": httpx.Response(200, text="<h1>Ekord</h1><p>Redovisning i Mölndal.</p>"),
    }

    def handler(request):
        if request.url.host == "nere.se":
            raise httpx.ConnectError("nere")
        return sidor[request.url.host]

    _mocka_webb(monkeypatch, handler)
    assert await platshallare.platshallare_for_webbplats("https://almapropertypartners.se") == "parkerad domän"
    assert await platshallare.platshallare_for_webbplats("https://fojab.se") is None, "403 är inte en platshållare"
    assert await platshallare.platshallare_for_webbplats("https://ekord.se") is None
    assert await platshallare.platshallare_for_webbplats("https://nere.se") is None
    assert await platshallare.platshallare_for_webbplats(None) is None


@pytest.mark.anyio
async def test_utan_platshallare_filtrerar_och_behaller_ordningen(monkeypatch):
    monkeypatch.setenv("LEADS_PLATSHALLARKONTROLL", "1")
    orsaker = {"https://almapropertypartners.se": "parkerad domän", "https://itkonsulterna.se": "under konstruktion"}
    monkeypatch.setattr(platshallare, "platshallare_for_webbplats", AsyncMock(side_effect=lambda u: orsaker.get(u)))
    traffar = [
        {"company_name": "Alma Property Partners", "website": "https://almapropertypartners.se"},
        {"company_name": "Ekord AB", "website": "https://ekord.se"},
        {"company_name": "IT-Konsulterna", "website": "https://itkonsulterna.se"},
        {"company_name": "FOJAB Arkitekter AB", "website": "https://fojab.se"},
    ]
    kvar = await utan_platshallare(traffar)
    assert [t["company_name"] for t in kvar] == ["Ekord AB", "FOJAB Arkitekter AB"]


@pytest.mark.anyio
async def test_kontrollen_ar_avstangd_i_testlage(monkeypatch):
    monkeypatch.setenv("LEADS_PLATSHALLARKONTROLL", "0")
    spion = AsyncMock(return_value="parkerad domän")
    monkeypatch.setattr(platshallare, "platshallare_for_webbplats", spion)
    traffar = [{"company_name": "X", "website": "https://x.se"}]
    assert await utan_platshallare(traffar) == traffar
    spion.assert_not_awaited()


@pytest.mark.anyio
async def test_hitta_bolag_sorterar_bort_platshallare_fran_gemini(monkeypatch):
    from app.leads import discovery

    monkeypatch.setenv("LEADS_PLATSHALLARKONTROLL", "1")
    monkeypatch.setattr("app.leads.sources.standardkallor", lambda: [])
    monkeypatch.setattr(
        platshallare,
        "platshallare_for_webbplats",
        AsyncMock(side_effect=lambda u: "parkerad domän" if "alma" in (u or "") else None),
    )
    gemini = AsyncMock(
        return_value=json.dumps(
            [
                {"company_name": "Alma Property Partners", "website": "https://almapropertypartners.se",
                 "contact_email": "info@almapropertypartners.se", "contact_level": "role_address"},
                {"company_name": "Ekord AB", "website": "https://ekord.se",
                 "contact_email": "info@ekord.se", "contact_level": "role_address"},
            ]
        )
    )
    with patch("app.leads.discovery._gemini_med_sokning", gemini):
        traffar = await discovery.hitta_bolag({"industries": ["redovisningsbyråer"]}, 2)
    assert [t["company_name"] for t in traffar] == ["Ekord AB"]
