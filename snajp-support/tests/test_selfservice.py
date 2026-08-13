"""Self-service-onboarding: en kund sätter upp sin egen arbetsyta.

Bevisar att flödet fungerar UTAN seed-script och utan .env-redigering, och att
den nya tenanten är isolerad från den befintliga från första sekunden.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app

settings = get_settings()
DEMO_KEY = settings.snajp_demo_api_key
MASTER_KEY = settings.snajp_master_api_key


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _onboard(client, name: str) -> dict:
    """Samma väg som Next-proxyn går: master-nyckel → ny tenant + nyckel."""
    response = await client.post(
        "/api/keys", headers={"X-API-Key": MASTER_KEY}, json={"tenant_name": name}
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.anyio
async def test_onboarding_creates_isolated_tenant():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant = await _onboard(client, "Fjällrävens Sport AB")
            key = {"X-API-Key": tenant["api_key"]}

            # Egen tenant, egen nyckel, egen tom kunskapsbas.
            assert tenant["tenant_id"] != DEMO_KEY
            assert tenant["api_key"].startswith("snajp_live_")
            kb = (await client.get("/api/kb", headers=key)).json()
            assert kb["articles"] == []

            # Egen profil, inte demo-tenantens.
            me = (await client.get("/api/tenant", headers=key)).json()
            assert me["name"] == "Fjällrävens Sport AB"
            assert me["system_prompt_extra"] is None

            # Noll förbrukning innan något körts.
            usage = (await client.get("/api/usage", headers=key)).json()
            assert usage["responses"] == 0
            assert usage["total_tokens"] == 0

            # Onboarding-checklistan säger att arbetsytan inte är klar ännu.
            status = (await client.get("/api/onboarding/status", headers=key)).json()
            assert status["ready"] is False


@pytest.mark.anyio
async def test_tenant_sets_own_tone_and_prompt():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant = await _onboard(client, "Skogsro Möbler")
            key = {"X-API-Key": tenant["api_key"]}

            updated = await client.put(
                "/api/tenant",
                headers=key,
                json={
                    "company_name": "Skogsro Möbler AB",
                    "tone": "varm och personlig",
                    "system_prompt_extra": "Vi tillverkar handgjorda möbler i furu.",
                },
            )
            assert updated.status_code == 200
            assert updated.json()["tone"] == "varm och personlig"

            # Inställningen ligger kvar och påverkar INTE demo-tenanten.
            demo = (await client.get("/api/tenant", headers={"X-API-Key": DEMO_KEY})).json()
            assert demo["system_prompt_extra"] is None
            assert demo["tone"] is None


@pytest.mark.anyio
async def test_tenant_manages_own_kb_without_seed_script():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant = await _onboard(client, "Nordvik Cykel")
            key = {"X-API-Key": tenant["api_key"]}

            created = await client.post(
                "/api/kb",
                headers=key,
                json={
                    "articles": [
                        {
                            "title": "Fraktvillkor",
                            "content": "Vi skickar med DHL inom två arbetsdagar.",
                            "category": "leverans",
                        }
                    ]
                },
            )
            assert created.status_code == 201
            article_id = created.json()["created"][0]["id"]

            # Redigera.
            edited = await client.put(
                f"/api/kb/{article_id}",
                headers=key,
                json={"content": "Vi skickar med PostNord inom tre arbetsdagar."},
            )
            assert edited.status_code == 200
            assert "PostNord" in edited.json()["content"]

            # Ändringen syns i listan.
            listed = (await client.get("/api/kb", headers=key)).json()["articles"]
            assert listed[0]["content"].startswith("Vi skickar med PostNord")

            # Radera.
            deleted = await client.delete(f"/api/kb/{article_id}", headers=key)
            assert deleted.status_code == 200
            assert (await client.get("/api/kb", headers=key)).json()["articles"] == []


@pytest.mark.anyio
async def test_tenant_issues_and_revokes_own_keys():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant = await _onboard(client, "Havsbris Fisk")
            key = {"X-API-Key": tenant["api_key"]}

            # Egen nyckel utan master-nyckel.
            created = await client.post(
                "/api/keys/self", headers=key, json={"label": "Webhook"}
            )
            assert created.status_code == 201
            new_key = created.json()["api_key"]

            # Den nya nyckeln pekar på SAMMA tenant.
            assert (
                (await client.get("/api/tenant", headers={"X-API-Key": new_key})).json()["id"]
                == (await client.get("/api/tenant", headers=key)).json()["id"]
            )

            # Listan visar prefix men aldrig nyckeln eller hashen.
            keys = (await client.get("/api/keys", headers=key)).json()["keys"]
            assert len(keys) == 2
            serialized = str(keys)
            assert new_key not in serialized
            assert "key_hash" not in serialized

            # Återkallad nyckel slutar fungera direkt.
            revoked = await client.delete(
                f"/api/keys/{created.json()['id']}", headers=key
            )
            assert revoked.status_code == 200
            denied = await client.get("/api/tenant", headers={"X-API-Key": new_key})
            assert denied.status_code == 401


@pytest.mark.anyio
async def test_tenant_cannot_revoke_another_tenants_key():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            a = await _onboard(client, "Alfa Handel")
            b = await _onboard(client, "Beta Handel")

            key_a = {"X-API-Key": a["api_key"]}
            key_b = {"X-API-Key": b["api_key"]}

            created = await client.post("/api/keys/self", headers=key_a, json={})
            key_id = created.json()["id"]

            # Tenant B får 404 — inte 403: nyckelns existens ska inte läcka.
            stolen = await client.delete(f"/api/keys/{key_id}", headers=key_b)
            assert stolen.status_code == 404

            # Och A:s nyckel fungerar fortfarande.
            still_valid = await client.get(
                "/api/tenant", headers={"X-API-Key": created.json()["api_key"]}
            )
            assert still_valid.status_code == 200


@pytest.mark.anyio
async def test_master_key_cannot_read_tenant_settings_or_usage():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            master = {"X-API-Key": MASTER_KEY}
            assert (await client.get("/api/tenant", headers=master)).status_code == 403
            assert (await client.get("/api/usage", headers=master)).status_code == 403
            assert (await client.get("/api/keys", headers=master)).status_code == 403
