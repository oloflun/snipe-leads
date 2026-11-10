"""Godkänn och skicka alla som jobb med förlopp (fas 0-fyndet H4, 2026-11-10).

Massutskicket gick igenom alla utkast i en enda begäran. Webbens proxy ger en
POST nio sekunder: med fler än en handfull utkast visade vyn ett fel medan
utskicket gick vidare, och ingen såg hur långt det kommit. Nu startar begäran
ett jobb och svarar direkt; vyn hämtar förloppet (x av y) och utfallet.
"""

from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.leads import scheduler
from app.main import app
from tests.api.test_korningens_utkast import _seeda

pytestmark = pytest.mark.anyio
DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _klient() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _vanta(klient: AsyncClient, job_id: str) -> dict:
    for _ in range(200):
        svar = (await klient.get(f"/api/jobs/{job_id}", headers=DEMO)).json()
        if svar["status"] in ("completed", "failed"):
            return svar
        await asyncio.sleep(0.02)
    raise AssertionError("utskicket blev aldrig klart")


async def test_korningens_utskick_startar_direkt_och_ger_samma_utfall():
    async with app.router.lifespan_context(app):
        await _seeda(app.state.storage)
        async with _klient() as klient:
            start = await klient.post("/api/leads/korningar/korning-1/utkast/skicka-jobb", headers=DEMO)
            assert start.status_code == 202, start.text
            klart = await _vanta(klient, start.json()["job_id"])

    assert klart["status"] == "completed", klart
    utfall = klart["result"]
    assert utfall["skickade"] + utfall["vantar_pa_fonstret"] + len(utfall["stoppade"]) == 1
    assert klart["forlopp"] == {"klara": 1, "totalt": 1}


async def test_forloppet_syns_medan_utskicket_gar(monkeypatch):
    slapp = asyncio.Event()

    async def _langsam(storage, tenant_id, item_id, provider, *, now, **_k):
        await slapp.wait()
        return "sent", None

    monkeypatch.setattr(scheduler, "skicka_godkant", _langsam)
    async with app.router.lifespan_context(app):
        await _seeda(app.state.storage)
        async with _klient() as klient:
            job_id = (await klient.post("/api/leads/korningar/korning-1/utkast/skicka-jobb", headers=DEMO)).json()["job_id"]
            await asyncio.sleep(0.05)
            mitt_i = (await klient.get(f"/api/jobs/{job_id}", headers=DEMO)).json()
            andra = (await klient.post("/api/leads/korningar/korning-1/utkast/skicka-jobb", headers=DEMO)).json()
            slapp.set()
            klart = await _vanta(klient, job_id)

    assert mitt_i["status"] == "processing" and mitt_i["forlopp"] == {"klara": 0, "totalt": 1}
    assert andra["job_id"] == job_id and andra["pagar"] is True, "ett andra klick får samma utskick"
    assert klart["result"]["skickade"] == 1


async def test_okand_korning_ger_404_innan_nagot_startar():
    async with app.router.lifespan_context(app):
        async with _klient() as klient:
            svar = await klient.post("/api/leads/korningar/finns-inte/utkast/skicka-jobb", headers=DEMO)
    assert svar.status_code == 404


async def test_kampanjens_utskick_som_jobb():
    async with app.router.lifespan_context(app):
        async with _klient() as klient:
            start = await klient.post("/api/leads/kampanjer/finns-inte/skicka-jobb", headers=DEMO)
            assert start.status_code == 202, start.text
            klart = await _vanta(klient, start.json()["job_id"])

    assert klart["status"] == "completed"
    assert klart["result"] == {"skickade": 0, "vantar_pa_fonstret": 0, "stoppade": []}
    assert DEFAULT_TENANT_ID
