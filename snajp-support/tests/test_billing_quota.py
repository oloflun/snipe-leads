"""Kvot och abonnemang.

Det viktigaste testet här är att en förbrukad kvot ger ett VÄNLIGT SVAR, inte
ett fel. En kund som slagit i taket ska få veta det på svenska och få sitt
ärende omhändertaget av en människa — inte se en krasch, och absolut inte ett
påhittat svar.
"""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.billing.plans import get_plan, quota_state
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
    response = await client.post(
        "/api/keys", headers={"X-API-Key": MASTER_KEY}, json={"tenant_name": name}
    )
    assert response.status_code == 201
    return response.json()


async def _chat(client, key: str, message: str, email: str) -> dict:
    headers = {"X-API-Key": key}
    response = await client.post(
        "/api/chat", headers=headers, json={"message": message, "customer_email": email}
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    for _ in range(50):
        job = (await client.get(f"/api/jobs/{job_id}", headers=headers)).json()
        if job["status"] == "completed":
            return job["result"]
        assert job["status"] != "failed", job
        await asyncio.sleep(0.05)
    raise AssertionError("Jobbet blev aldrig klart.")


# -- Rena beräkningar --------------------------------------------------------


def test_quota_state_thresholds():
    # Bas har 500 svar/månad.
    assert quota_state("bas", 0)["warn"] is False
    assert quota_state("bas", 399)["warn"] is False
    assert quota_state("bas", 400)["warn"] is True  # exakt 80 %
    assert quota_state("bas", 499)["exceeded"] is False
    assert quota_state("bas", 500)["exceeded"] is True
    assert quota_state("bas", 500)["warn"] is False  # slut, inte "nästan slut"
    assert quota_state("bas", 600)["remaining"] == 0


def test_unknown_plan_falls_back_to_free_not_unlimited():
    """En okänd nivå ska ge LÄGSTA kvoten, aldrig obegränsat."""
    plan = get_plan("nivå-som-inte-finns")
    assert plan.id == "free"
    assert quota_state("nivå-som-inte-finns", 50)["exceeded"] is True


def test_internal_plan_is_unlimited():
    state = quota_state("intern", 999_999)
    assert state["cap"] is None
    assert state["exceeded"] is False


# -- Genom API:t -------------------------------------------------------------


@pytest.mark.anyio
async def test_new_tenant_starts_on_free_plan():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant = await _onboard(client, "Kvot Test AB")
            key = {"X-API-Key": tenant["api_key"]}

            body = (await client.get("/api/billing/subscription", headers=key)).json()
            assert body["plan"]["id"] == "free"
            assert body["quota"]["cap"] == 50
            assert body["quota"]["used"] == 0
            assert body["quota"]["exceeded"] is False


@pytest.mark.anyio
async def test_exceeded_quota_answers_kindly_instead_of_failing():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant = await _onboard(client, "Slut Kvot AB")
            tenant_key = tenant["api_key"]

            # Sätt taket till noll genom att lägga tenanten på en nivå och
            # bränna kvoten: enklast är att flytta perioden framåt är inte
            # möjligt, så vi fyller free-kvoten (50) direkt i lagringen.
            storage = app.state.storage
            await storage.log_usage(
                tenant["tenant_id"], kind="chat", simulated=True, responses=50
            )

            result = await _chat(client, tenant_key, "Var är mitt paket?", "k@example.com")

            # Jobbet lyckas — det är inte ett fel att kvoten är slut.
            assert result["quota_exceeded"] is True
            assert result["escalated"] is True
            assert "abonnemang" in result["reply"].lower()
            # Och agenten hittar inte på ett svar.
            assert result["kb_sources"] == []


@pytest.mark.anyio
async def test_warning_appears_at_eighty_percent():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant = await _onboard(client, "Varning AB")
            storage = app.state.storage
            # 40 av 50 = 80 %.
            await storage.log_usage(
                tenant["tenant_id"], kind="chat", simulated=True, responses=40
            )

            result = await _chat(
                client, tenant["api_key"], "Hur lång är garantin?", "k@example.com"
            )
            assert result.get("quota_warning") is not None
            assert result["quota_warning"]["warn"] is True
            # Svaret levereras fortfarande — varning är inte blockering.
            assert "quota_exceeded" not in result
            assert result["reply"]


@pytest.mark.anyio
async def test_demo_tenant_is_never_quota_blocked():
    """Demon får aldrig sluta fungera för att någon kört slut på en kvot."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            body = (
                await client.get(
                    "/api/billing/subscription", headers={"X-API-Key": DEMO_KEY}
                )
            ).json()
            assert body["plan"]["id"] == "intern"
            assert body["quota"]["cap"] is None


@pytest.mark.anyio
async def test_tenant_cannot_upgrade_itself():
    """Nivån får bara ändras av Stripe-webhooken, aldrig av kunden."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant = await _onboard(client, "Fuskare AB")
            key = {"X-API-Key": tenant["api_key"]}

            attempt = await client.put(
                "/api/billing/subscription", headers=key, json={"plan_id": "pro"}
            )
            assert attempt.status_code == 403

            body = (await client.get("/api/billing/subscription", headers=key)).json()
            assert body["plan"]["id"] == "free"


@pytest.mark.anyio
async def test_webhook_sync_updates_plan_and_is_isolated():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            a = await _onboard(client, "Alfa Abonnemang")
            b = await _onboard(client, "Beta Abonnemang")

            synced = await client.put(
                "/api/billing/subscription",
                headers={"X-API-Key": MASTER_KEY},
                json={
                    "tenant_id": a["tenant_id"],
                    "plan_id": "plus",
                    "status": "active",
                    "stripe_customer_id": "cus_test_alfa",
                },
            )
            assert synced.status_code == 200

            body_a = (
                await client.get(
                    "/api/billing/subscription", headers={"X-API-Key": a["api_key"]}
                )
            ).json()
            body_b = (
                await client.get(
                    "/api/billing/subscription", headers={"X-API-Key": b["api_key"]}
                )
            ).json()

            assert body_a["plan"]["id"] == "plus"
            assert body_a["quota"]["cap"] == 2000
            # Tenant B påverkas inte av tenant A:s uppgradering.
            assert body_b["plan"]["id"] == "free"


@pytest.mark.anyio
async def test_webhook_can_find_tenant_by_stripe_customer():
    """Stripe skickar kundid, inte tenant_id — uppslaget måste fungera."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant = await _onboard(client, "Uppslag AB")
            await client.put(
                "/api/billing/subscription",
                headers={"X-API-Key": MASTER_KEY},
                json={
                    "tenant_id": tenant["tenant_id"],
                    "stripe_customer_id": "cus_lookup_1",
                    "plan_id": "bas",
                    "status": "active",
                },
            )

            # Andra anropet saknar tenant_id — bara kundid, som från Stripe.
            second = await client.put(
                "/api/billing/subscription",
                headers={"X-API-Key": MASTER_KEY},
                json={"stripe_customer_id": "cus_lookup_1", "status": "past_due"},
            )
            assert second.status_code == 200
            assert second.json()["tenant_id"] == tenant["tenant_id"]

            body = (
                await client.get(
                    "/api/billing/subscription", headers={"X-API-Key": tenant["api_key"]}
                )
            ).json()
            assert body["status"] == "past_due"
            # Nivån ska INTE ha nollats av en statusuppdatering.
            assert body["plan"]["id"] == "bas"


@pytest.mark.anyio
async def test_unknown_stripe_customer_is_rejected():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            response = await client.put(
                "/api/billing/subscription",
                headers={"X-API-Key": MASTER_KEY},
                json={"stripe_customer_id": "cus_finns_inte", "status": "active"},
            )
            assert response.status_code == 404
