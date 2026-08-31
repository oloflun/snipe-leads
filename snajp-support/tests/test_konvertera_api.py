"""HTTP-vägen för testkund → riktigt konto, plus riktningsspärren."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.tenants.konvertera import kontrollera_riktning, kora
from app.config import get_settings

settings = get_settings()
MASTER = {"X-API-Key": settings.snajp_master_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def test_kontrollera_riktning_ar_envags():
    assert kontrollera_riktning("testkund-abcd1234", "livrustning") is None
    assert "inte en testtenant" in kontrollera_riktning("livrustning", "annan")
    assert "är en testtenant" in kontrollera_riktning("testkund-a", "testkund-b")
    assert "samma tenant" in kontrollera_riktning("testkund-a", "testkund-a")


@pytest.mark.anyio
async def test_konvertera_torrkoring_och_apply_i_minne():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        kalla = await storage.create_tenant(slug="testkund-konv01", name="Test Konv")
        mal = await storage.create_tenant(slug="riktig-konv", name="Riktig Konv")
        await storage.add_kb_article(
            kalla["id"],
            title="Öppettider",
            content="Vi har öppet helgfria vardagar.",
            category="ovrigt",
        )

        async with _client() as client:
            torr = await client.post(
                "/api/admin/konvertera",
                headers=MASTER,
                json={"fran": "testkund-konv01", "till": "riktig-konv"},
            )
            assert torr.status_code == 200
            rapport = torr.json()["rapport"]
            assert rapport["apply"] is False
            assert rapport["kunskapsbas"]["fran"] >= 1
            assert all(a.get("title") != "Öppettider" for a in await storage.list_kb(mal["id"]))

            skriv = await client.post(
                "/api/admin/konvertera",
                headers=MASTER,
                json={"fran": "testkund-konv01", "till": "riktig-konv", "apply": True},
            )
            assert skriv.status_code == 200
            titlar = {a["title"] for a in await storage.list_kb(mal["id"])}
            assert "Öppettider" in titlar

        avvisat = await kora(storage, fran="livrustning", till="riktig-konv")
        assert avvisat["ok"] is False
