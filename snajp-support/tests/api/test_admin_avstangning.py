"""Manuell avstängning av en kund — adminens trial-konvertering.

Beslutet 2026-09-20: ingen automatisk konvertering vid trial-slut. I stället
stänger en människa av kontot i admin, med bekräftelse. Avstängningen ÄR
`ss_tenants.active = false`: `validate_api_key` avvisar nycklar för en
inaktiv tenant, så webben, portalen, den publika chatten och alla tre
agenterna låses ute i samma ögonblick — och en återaktivering öppnar dem
igen utan att något raderats.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app

MASTER = {"X-API-Key": get_settings().snajp_master_api_key}
DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _ny_tenant_med_nyckel(client) -> tuple[str, str]:
    svar = await client.post(
        "/api/keys",
        headers=MASTER,
        json={"tenant_name": "Avstängningstest AB", "slug": "kund-avstang1"},
    )
    kropp = svar.json()
    return kropp["tenant_id"], kropp["api_key"]


@pytest.mark.anyio
async def test_avstangning_later_ute_och_ateraktivering_slapper_in():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant_id, nyckel = await _ny_tenant_med_nyckel(client)
            kund = {"X-API-Key": nyckel}
            assert (await client.get("/api/kb", headers=kund)).status_code == 200

            svar = await client.put(
                f"/api/admin/tenants/{tenant_id}/aktiv",
                headers=MASTER,
                json={"active": False, "orsak": "Trial gick ut 2026-11-20, inget avtal."},
            )
            assert svar.status_code == 200
            assert svar.json()["tenant"]["active"] is False

            # Nyckeln är död i samma ögonblick — inte 403/404 utan 401:
            # en avstängd kunds nyckel ska inte gå att skilja från en ogiltig.
            assert (await client.get("/api/kb", headers=kund)).status_code == 401

            svar = await client.put(
                f"/api/admin/tenants/{tenant_id}/aktiv",
                headers=MASTER,
                json={"active": True},
            )
            assert svar.status_code == 200
            assert (await client.get("/api/kb", headers=kund)).status_code == 200


@pytest.mark.anyio
async def test_avstangningen_loggas_med_orsak():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant_id, _ = await _ny_tenant_med_nyckel(client)
            await client.put(
                f"/api/admin/tenants/{tenant_id}/aktiv",
                headers=MASTER,
                json={"active": False, "orsak": "Trialen slut."},
            )
            handelser = [
                e
                for e in app.state.storage.platform_events
                if e.get("source") == "admin.avstangning" and e.get("tenant_id") == tenant_id
            ]
            assert handelser, "avstängningen ska lämna ett spår i platform_events"
            assert handelser[-1]["detail"]["orsak"] == "Trialen slut."


@pytest.mark.anyio
async def test_kraver_masternyckel_och_riktigt_id():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant_id, _ = await _ny_tenant_med_nyckel(client)
            svar = await client.put(
                f"/api/admin/tenants/{tenant_id}/aktiv", headers=DEMO, json={"active": False}
            )
            assert svar.status_code == 403
            svar = await client.put(
                "/api/admin/tenants/inte-ett-uuid/aktiv", headers=MASTER, json={"active": False}
            )
            assert svar.status_code == 404
            svar = await client.put(
                "/api/admin/tenants/00000000-0000-4000-a000-0000000000ff/aktiv",
                headers=MASTER,
                json={"active": False},
            )
            assert svar.status_code == 404
