import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_upload_product_marketing_doc_and_read_back_context_pack():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            created = await client.post(
                "/api/leads/context-docs",
                headers=DEMO,
                json={
                    "kind": "product_marketing",
                    "content": "# Nordlys Handel\nSäljer köksredskap online.",
                    "source": "manual",
                },
            )
            assert created.status_code == 201
            assert created.json()["doc"]["version"] == 1

            pack = await client.get("/api/leads/context-pack", headers=DEMO)
            assert pack.status_code == 200
            assert "Nordlys Handel" in pack.json()["context_pack"]
            assert ".agents/product-marketing.md" in pack.json()["context_pack"]


@pytest.mark.anyio
async def test_context_docs_require_a_tenant_key_not_master():
    settings = get_settings()
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.post(
                "/api/leads/context-docs",
                headers={"X-API-Key": settings.snajp_master_api_key},
                json={"kind": "product_marketing", "content": "x"},
            )
            assert response.status_code == 403


@pytest.mark.anyio
async def test_invalid_kind_is_rejected():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.post(
                "/api/leads/context-docs",
                headers=DEMO,
                json={"kind": "not_a_real_kind", "content": "x"},
            )
            assert response.status_code == 422
