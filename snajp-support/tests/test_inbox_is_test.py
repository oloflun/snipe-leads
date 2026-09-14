"""Testmail ska inte blandas med skarpa ärenden utanför demo-/testkonton."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

settings = get_settings()
DEMO = {"X-API-Key": settings.snajp_demo_api_key}
MASTER = {"X-API-Key": settings.snajp_master_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_demo_visar_testmail_i_arenden():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            seeded = await client.post("/api/inbox/mock", headers=DEMO, json={"count": 1})
            assert seeded.status_code == 201
            inbox = await client.get("/api/inbox", headers=DEMO)
            assert inbox.status_code == 200
            kropp = inbox.json()
            assert kropp["visar_test_i_arenden"] is True
            assert any(m.get("is_test") for m in kropp["emails"])


@pytest.mark.anyio
async def test_riktig_kund_doljer_testmail_tills_is_test_sätts():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            skapad = await client.post(
                "/api/keys",
                headers=MASTER,
                json={"tenant_name": "Riktiga Byggbolaget AB", "slug": "riktiga-byggbolaget"},
            )
            assert skapad.status_code == 201
            nyckel = {"X-API-Key": skapad.json()["api_key"]}

            seeded = await client.post("/api/inbox/mock", headers=nyckel)
            assert seeded.status_code == 201

            arenden = await client.get("/api/inbox", headers=nyckel)
            assert arenden.status_code == 200
            kropp = arenden.json()
            assert kropp["visar_test_i_arenden"] is False
            assert kropp["emails"] == []

            testmail = await client.get("/api/inbox?is_test=true", headers=nyckel)
            assert testmail.status_code == 200
            rader = testmail.json()["emails"]
            assert rader
            assert all(m.get("is_test") is True for m in rader)

            flytta = await client.post(
                f"/api/inbox/{rader[0]['id']}/befordra", headers=nyckel
            )
            assert flytta.status_code == 200
            assert flytta.json()["andrad"] is True

            kvar = await client.get("/api/inbox?is_test=true", headers=nyckel)
            ids = {m["id"] for m in kvar.json()["emails"]}
            assert rader[0]["id"] not in ids

            skarpa = await client.get("/api/inbox", headers=nyckel)
            skarpa_ids = {m["id"] for m in skarpa.json()["emails"]}
            assert rader[0]["id"] in skarpa_ids


@pytest.mark.anyio
async def test_get_email_hittar_testmail_som_listan_doljer():
    """get_email måste läsa med is_test=None, annars 404:ar detaljpanelen."""
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        async with _client() as client:
            skapad = await client.post(
                "/api/keys",
                headers=MASTER,
                json={"tenant_name": "Detaljbolaget AB", "slug": "detaljbolaget"},
            )
            nyckel = {"X-API-Key": skapad.json()["api_key"]}
            tenant_id = skapad.json()["tenant_id"]
            await client.post("/api/inbox/mock", headers=nyckel)
            testmail = (await client.get("/api/inbox?is_test=true", headers=nyckel)).json()[
                "emails"
            ]
            assert testmail
            detalj = await client.get(f"/api/inbox/{testmail[0]['id']}", headers=nyckel)
            assert detalj.status_code == 200
            # Storage-sökvägen som föll: list_emails(default False) dolde raden.
            rad = await storage.get_email(tenant_id, testmail[0]["id"])
            assert rad is not None
            assert rad["is_test"] is True
