"""Ombedömningen av sparade Iris-leads (2026-10-06).

Torrkörning som default, bara Iris-/testleads med nivå A/B och status Ny/Redo,
bara research (aldrig utkast), och master-nyckeln krävs.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app

MASTER = {"X-API-Key": get_settings().snajp_master_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _kund_med_leads(client) -> tuple[str, str, dict[str, str]]:
    kropp = (await client.post("/api/keys", headers=MASTER,
                               json={"tenant_name": "Ombedömning AB", "slug": "kund-ombedom1"})).json()
    tenant_id = kropp["tenant_id"]
    storage = app.state.storage
    ids: dict[str, str] = {}
    for namn, origin, niva, status in (
        ("Redo A", "iris", "A", "ready"),
        ("Ny B test", "test", "B", "new"),
        ("Kontaktad", "iris", "A", "contacted"),
        ("Bortvald", "iris", "C", "new"),
        ("Import", "import", None, "new"),
    ):
        p = await storage.create_prospect(tenant_id, company_name=namn)
        p.update(origin=origin, niva=niva, status=status)
        ids[namn] = str(p["id"])
    return tenant_id, kropp["api_key"], ids


@pytest.mark.anyio
async def test_torrkorning_listar_bara_ororda_godkanda_iris_leads():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant_id, _, ids = await _kund_med_leads(client)
            with patch("app.api.leads._lagg_prospektjobb", new=AsyncMock()) as kö:
                svar = await client.post(f"/api/admin/tenants/{tenant_id}/leads-ombedom", headers=MASTER, json={})
            assert svar.status_code == 200
            kropp = svar.json()
            assert sorted(l["id"] for l in kropp["leads"]) == sorted([ids["Redo A"], ids["Ny B test"]])
            assert kropp["jobb"] == []
            kö.assert_not_called()


@pytest.mark.anyio
async def test_apply_koar_bara_research_och_testflaggan_foljer_ursprunget():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant_id, _, ids = await _kund_med_leads(client)
            with (
                patch("app.api.leads._require_live_llm"),
                patch("app.api.leads._kraev_leads_budget", new=AsyncMock()),
                patch("app.api.leads._lagg_prospektjobb", new=AsyncMock(return_value=[{"job_id": "j"}])) as kö,
            ):
                svar = await client.post(
                    f"/api/admin/tenants/{tenant_id}/leads-ombedom", headers=MASTER, json={"apply": True}
                )
            assert svar.status_code == 200
            anrop = {a.args[2][0]["company_name"]: a.kwargs for a in kö.await_args_list}
            assert set(anrop) == {"Redo A", "Ny B test"}
            assert all(k["scope"] == "research" for k in anrop.values())
            assert anrop["Redo A"]["is_test"] is False and anrop["Ny B test"]["is_test"] is True


@pytest.mark.anyio
async def test_kundnyckeln_kommer_inte_in():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            tenant_id, nyckel, _ = await _kund_med_leads(client)
            svar = await client.post(
                f"/api/admin/tenants/{tenant_id}/leads-ombedom", headers={"X-API-Key": nyckel}, json={}
            )
            assert svar.status_code == 403
