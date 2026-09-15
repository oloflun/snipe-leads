"""Grounded sökning: en lästimeout görs inte om, snabba transportfel görs det.

Uppmätt 2026-09-15 mot Vertex: samma sökning tog 55 s och 156 s. Med tre
försök à 90 s lästimeout föll en kundkörning efter 4,5 minuter, och varje
omförsök startade om samma långa sökning. Formuläret gav upp efter 3 minuter.
"""

from __future__ import annotations

import httpx
import pytest

from app.leads import discovery
from app.leads.discovery import DiscoveryError, _gemini_med_sokning


class _Settings:
    gemini_api_key = "fejk-" + "a" * 20
    model = "gemini-2.5-flash"
    google_service_account_json = ""
    google_cloud_region = "europe-west1"

    def active_llm_key(self) -> str:
        return self.gemini_api_key


class _Svar:
    status_code = 200
    text = ""

    def json(self):
        return {"candidates": [{"content": {"parts": [{"text": "[]"}]}}]}


def _klient(fel_sekvens: list):
    anrop = {"antal": 0}

    class _Klient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, *args, **kwargs):
            anrop["antal"] += 1
            if fel_sekvens:
                raise fel_sekvens.pop(0)
            return _Svar()

    return _Klient, anrop


async def _ingen_paus(*_a, **_k):
    return None


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_lastimeout_gors_inte_om(monkeypatch):
    klient, anrop = _klient([httpx.ReadTimeout("läste inte klart")])
    monkeypatch.setattr(discovery, "get_settings", lambda: _Settings())
    monkeypatch.setattr(discovery.httpx, "AsyncClient", klient)
    monkeypatch.setattr(discovery.asyncio, "sleep", _ingen_paus)

    with pytest.raises(DiscoveryError):
        await _gemini_med_sokning("hitta bolag")
    assert anrop["antal"] == 1, "en lästimeout ska inte starta om samma långa sökning"


@pytest.mark.anyio
async def test_anslutningsfel_gors_om_och_kan_lyckas(monkeypatch):
    klient, anrop = _klient([httpx.ConnectError("nere"), httpx.ConnectError("nere")])
    monkeypatch.setattr(discovery, "get_settings", lambda: _Settings())
    monkeypatch.setattr(discovery.httpx, "AsyncClient", klient)
    monkeypatch.setattr(discovery.asyncio, "sleep", _ingen_paus)

    assert await _gemini_med_sokning("hitta bolag") == "[]"
    assert anrop["antal"] == 3


def test_lastaket_racker_for_uppmatt_sokningstid():
    """156 s uppmätt; taket ska ha marginal men hålla sig under formulärets ~5 min."""
    assert 156 < discovery._SOKNING_TIMEOUT.read <= 240
