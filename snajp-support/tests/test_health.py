"""Health-endpoints: driftläget ska gå att läsa av utan att gissa.

`/health/ready` svarade tidigare alltid `{"status": "ok"}`. En tjänst utan
LLM-nyckel och utan databas rapporterade sig alltså som frisk, vilket gör
readiness till dekoration.

Testerna nedan mäter KONTRAKTET, inte ett antaget tillstånd. Skälet är
konkret: sviten körs både i CI (ingen `.env`, alltså degraderat) och lokalt
med riktiga nycklar och `DATABASE_URL` satt (alltså inte degraderat). Ett test
som hårdkodar `degraded is True` går sönder av att miljön blir BÄTTRE, och den
sortens test lär man sig att ignorera.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_liveness_ar_billig_och_alltid_ok():
    """Renders health check pollar den här. Den får aldrig falla för att en
    nyckel saknas — då tas en fungerande tjänst ner av sin egen mätning."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.get("/health/live")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}


async def test_readiness_bar_hela_kontraktet():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.get("/health/ready")
            body = response.json()

    for field in ("status", "degraded", "storage", "mode", "warnings"):
        assert field in body, f"{field} saknas — vyn som läser readiness kan inte visa den."

    # Den bärande invarianten: flaggan och listan får aldrig säga olika saker.
    assert body["degraded"] == bool(body["warnings"])
    assert body["mode"] in ("simulation", "live")


async def test_degraderat_lage_ger_200_inte_503():
    """En tjänst utan nycklar fungerar — med simulerade svar. Att svara 503 där
    hade fått Render att ta ner en fullt användbar demo."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_simuleringslage_syns_i_varningarna():
    """Villkorat på faktiskt läge i stället för antaget: körs sviten med en
    riktig nyckel ska det INTE varnas, och med en platshållare ska det varnas."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            body = (await client.get("/health/ready")).json()

    if get_settings().is_simulation():
        assert body["mode"] == "simulation"
        assert any("LLM" in warning for warning in body["warnings"])
    else:
        assert body["mode"] == "live"
        assert not any("LLM" in warning for warning in body["warnings"])


async def test_otillganglig_lagring_ger_503():
    """Det ENDA tillstånd som ska ge 503. Framkallas med flit — annars är
    503-grenen kod som aldrig körts."""

    class TrasigLagring:
        name = "trasig"

        async def get_channel_config(self, *_args, **_kwargs):
            raise RuntimeError("anslutningen dog")

    async with app.router.lifespan_context(app):
        riktig = app.state.storage
        app.state.storage = TrasigLagring()
        try:
            async with _client() as client:
                response = await client.get("/health/ready")
        finally:
            app.state.storage = riktig

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["degraded"] is True
    assert any("Lagringen svarar inte" in warning for warning in body["warnings"])


async def test_cors_ar_av_som_default():
    """CORS behövs inte för vår frontend (proxyn anropar server-side). Att den
    är av som default är en säkerhetsegenskap, inte en glömska."""
    assert get_settings().allowed_origins == ""

    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.get(
                "/health/live", headers={"Origin": "https://angripare.example"}
            )

    assert "access-control-allow-origin" not in {k.lower() for k in response.headers}
