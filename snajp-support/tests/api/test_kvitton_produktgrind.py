"""Backendgrinden på produkträttigheten för kvitto- och bokföringsytan.

Granskningsfynd snipe-h12: /api/kvitton/* och /api/bookkeeping/* krävde bara
en giltig tenantnyckel. Produktgrinden satt enbart i webbens och portalens
proxyer, så en tenant UTAN bookkeeping-paketet men med sin nyckel i handen
nådde motorn direkt mot backenden — obetald användning av den dyraste ytan.

Grinden speglar webbens beteende: 404, inte 403 (ytan ska inte gå att
skilja från en som inte finns), och en tenant utan kopplad arbetsyta
(products = None, t.ex. configfil-kunder) släpps igenom — där är webbens
entitlement-grind fortfarande enda vakten, precis som före den här grinden.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
@pytest.mark.parametrize("vag", ["/api/kvitton", "/api/bookkeeping/underlag"])
async def test_tenant_utan_bookkeeping_far_404(vag):
    async with app.router.lifespan_context(app):
        app.state.storage.tenants[DEFAULT_TENANT_ID]["products"] = ["support", "leads"]
        try:
            async with _client() as client:
                assert (await client.get(vag, headers=DEMO)).status_code == 404
        finally:
            app.state.storage.tenants[DEFAULT_TENANT_ID].pop("products", None)


@pytest.mark.anyio
@pytest.mark.parametrize("vag", ["/api/kvitton", "/api/bookkeeping/underlag"])
async def test_tenant_med_bookkeeping_slapps_in(vag):
    async with app.router.lifespan_context(app):
        app.state.storage.tenants[DEFAULT_TENANT_ID]["products"] = ["bookkeeping"]
        try:
            async with _client() as client:
                assert (await client.get(vag, headers=DEMO)).status_code == 200
        finally:
            app.state.storage.tenants[DEFAULT_TENANT_ID].pop("products", None)


@pytest.mark.anyio
@pytest.mark.parametrize("vag", ["/api/kvitton", "/api/bookkeeping/underlag"])
async def test_tenant_utan_arbetsyta_slapps_in(vag):
    """products = None är "ingen kopplad arbetsyta", inte "inga produkter"."""
    async with app.router.lifespan_context(app):
        assert app.state.storage.tenants[DEFAULT_TENANT_ID].get("products") is None
        async with _client() as client:
            assert (await client.get(vag, headers=DEMO)).status_code == 200
