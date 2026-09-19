"""Avtalsgrinden (migration 070): en tenant med kraver_avtal vägras tills
avtal_signerat bär ett datum — och ingen annan påverkas.

Mot MemoryStorage av samma skäl som test_rate_limit_db: metoderna finns i
båda lagren, och grinden själv är lagringsoberoende.
"""

from __future__ import annotations

import pytest

from app.avtalsgrind import avtal_saknas, nollstall_cache
from app.storage.memory import MemoryStorage

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def storage():
    return MemoryStorage()


@pytest.fixture(autouse=True)
def _ren_cache():
    nollstall_cache()
    yield
    nollstall_cache()


async def _tenant(storage, *, kraver_avtal: bool) -> str:
    tenant = await storage.create_tenant(slug="livrustning", name="Livrustning AB")
    tenant["kraver_avtal"] = kraver_avtal
    return tenant["id"]


async def test_tenant_utan_krav_slapper_igenom(storage):
    tenant_id = await _tenant(storage, kraver_avtal=False)
    assert await avtal_saknas(storage, tenant_id) is False


async def test_krav_utan_registrerat_avtal_vagras(storage):
    tenant_id = await _tenant(storage, kraver_avtal=True)
    assert await avtal_saknas(storage, tenant_id) is True


async def test_registrerat_avtal_oppnar(storage):
    tenant_id = await _tenant(storage, kraver_avtal=True)
    await storage.upsert_customer_details(tenant_id, {"avtal_signerat": "2026-09-19"})
    nollstall_cache()  # 60-sekunderscachen håller annars kvar det gamla avgörandet
    assert await avtal_saknas(storage, tenant_id) is False


async def test_avgorandet_cachas(storage):
    """Två anrop i rad gör EN läsning — chatten frågar per meddelande."""
    tenant_id = await _tenant(storage, kraver_avtal=True)
    assert await avtal_saknas(storage, tenant_id) is True
    # Ett nytt avtal utan cache-nollställning syns inte direkt: det är
    # cachens kontrakt (högst en minut gammalt avgörande), inte en bugg.
    await storage.upsert_customer_details(tenant_id, {"avtal_signerat": "2026-09-19"})
    assert await avtal_saknas(storage, tenant_id) is True


async def test_lagringsfel_slapper_igenom(storage):
    """Fail-open: en trasig läsning får inte bli ett felaktigt 'avtal saknas'."""

    class TrasigStorage:
        async def get_tenant(self, tenant_id):
            raise RuntimeError("databasen är nere")

    assert await avtal_saknas(TrasigStorage(), "vilken-som-helst") is False


async def test_okand_tenant_slapper_igenom(storage):
    """En tenant utan rad (t.ex. demo-uuid:n i MemoryStorage) har inget krav."""
    assert await avtal_saknas(storage, "00000000-0000-4000-a000-00000000dead") is False


async def test_chatten_svarar_403_utan_avtal():
    """Hela vägen genom API:t: grinden sitter FÖRE jobbskapandet, och kunden
    får den vänliga meningen — inte ett tekniskt fel."""
    from httpx import ASGITransport, AsyncClient

    from app.avtalsgrind import KUNDTEXT_AVTAL
    from app.config import DEFAULT_TENANT_ID, get_settings
    from app.main import app

    async with app.router.lifespan_context(app):
        app.state.storage.tenants[DEFAULT_TENANT_ID]["kraver_avtal"] = True
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                svar = await client.post(
                    "/api/chat",
                    headers={"X-API-Key": get_settings().snajp_demo_api_key},
                    json={"message": "Hej!"},
                )
            assert svar.status_code == 403
            assert svar.json()["detail"] == KUNDTEXT_AVTAL
        finally:
            app.state.storage.tenants[DEFAULT_TENANT_ID].pop("kraver_avtal", None)
