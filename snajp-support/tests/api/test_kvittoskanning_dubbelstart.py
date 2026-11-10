"""Två skanningar samtidigt blir en (Fas 0-fyndet H3, 2026-11-09).

Skanningen läser inkorgen och sparar kvitton i en enda begäran. Ett
dubbelklick, eller ett nytt klick efter att proxyn gett upp, startade en
andra skanning över samma mejl medan den första ännu inte hunnit spara: båda
såg mejlet som oläst och kvittot sparades två gånger.
"""

from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

import app.api.kvitton as kvitton_api
from app.config import get_settings
from app.kvitton.skanning import Skanningsresultat
from app.main import app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def _raknad_skanning(monkeypatch):
    for namn, varde in {
        "KVITTO_MEJL_LEVERANTOR": "mock", "KVITTO_MEJL_TENANT": "", "DATABASE_URL": "",
        "REDIS_URL": "", "GEMINI_API_KEY": "", "OPENAI_API_KEY": "",
    }.items():
        monkeypatch.setenv(namn, varde)
    get_settings.cache_clear()
    anrop: list[int] = []

    async def _skanna(storage, tenant_id, konto, **_k):
        anrop.append(1)
        await asyncio.sleep(0.2)
        return Skanningsresultat()

    monkeypatch.setattr(kvitton_api, "skanna_inkorg", _skanna)
    yield anrop
    get_settings.cache_clear()


def _klient() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_tva_samtidiga_skanningar_laser_inkorgen_en_gang(_raknad_skanning):
    nyckel = {"X-API-Key": get_settings().snajp_demo_api_key}
    async with app.router.lifespan_context(app):
        async with _klient() as klient:
            forsta, andra = await asyncio.gather(
                klient.post("/api/kvitton/skanna", headers=nyckel),
                klient.post("/api/kvitton/skanna", headers=nyckel),
            )

    assert forsta.status_code == 200 and andra.status_code == 200, (forsta.text, andra.text)
    assert len(_raknad_skanning) == 1, "inkorgen får bara läsas en gång"
    assert forsta.json()["genomlasta"] == andra.json()["genomlasta"] == 0


async def test_en_ny_skanning_efter_att_den_forsta_ar_klar_kors(_raknad_skanning):
    """Vakten gäller bara medan skanningen pågår: listan i svaret ska vara
    färsk, inte en halv minut gammal."""
    nyckel = {"X-API-Key": get_settings().snajp_demo_api_key}
    async with app.router.lifespan_context(app):
        async with _klient() as klient:
            await klient.post("/api/kvitton/skanna", headers=nyckel)
            await klient.post("/api/kvitton/skanna", headers=nyckel)

    assert len(_raknad_skanning) == 2
