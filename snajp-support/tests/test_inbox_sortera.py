"""Provsortera (Anton 2026-10-04): förslag utan skrivning, tillämpning med källa."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, PUBLIC_DEMO_TENANT_ID, get_settings
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_provsortera_skriver_bara_vid_tillampa():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            svar = await client.post(
                "/api/inbox/ingest", headers=DEMO,
                json={"from": "info@butik.se", "subject": "Vårt nyhetsbrev v40", "body": "Erbjudanden"},
            )
            assert svar.status_code == 201, svar.text
            eid = svar.json()["email_id"]
            storage = app.state.storage
            tid = next([t for t in (DEFAULT_TENANT_ID, PUBLIC_DEMO_TENANT_ID) if await storage.get_email(t, eid)].__iter__())
            # Som ett mejl standardvägen släppt in i supportkedjan.
            await storage.update_email(tid, eid, klass="support", klass_kalla="standard", status="escalated")

            prov = await client.post("/api/inbox/sortera", headers=DEMO, json={"email_ids": [eid]})
            assert prov.status_code == 200, prov.text
            assert prov.json()["forslag"] == [
                {"email_id": eid, "nuvarande": "support", "klass": "ej_relaterat", "kalla": "regel", "jev": None, "hoppad": False}
            ]
            orord = await storage.get_email(tid, eid)
            assert orord["klass"] == "support" and orord["status"] == "escalated"

            skarp = await client.post("/api/inbox/sortera", headers=DEMO, json={"email_ids": [eid], "tillampa": True})
            assert skarp.status_code == 200
            rad = await storage.get_email(tid, eid)
            assert (rad["klass"], rad["klass_kalla"], rad["status"]) == ("ej_relaterat", "regel", "ej_relaterat")


@pytest.mark.anyio
async def test_tillampa_ror_inte_mejl_som_pipelinen_inte_slappt():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            svar = await client.post(
                "/api/inbox/ingest", headers=DEMO,
                json={"from": "info@butik.se", "subject": "Vårt nyhetsbrev v41", "body": "Erbjudanden"},
            )
            eid = svar.json()["email_id"]
            storage = app.state.storage
            tid = next([t for t in (DEFAULT_TENANT_ID, PUBLIC_DEMO_TENANT_ID) if await storage.get_email(t, eid)].__iter__())
            await storage.update_email(tid, eid, klass="support", klass_kalla="standard", status="processing")
            skarp = await client.post("/api/inbox/sortera", headers=DEMO, json={"email_ids": [eid], "tillampa": True})
            assert skarp.json()["forslag"][0]["hoppad"] is True
            assert (await storage.get_email(tid, eid))["klass"] == "support"
