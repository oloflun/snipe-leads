"""Kontolägets skrivväg (PUT /api/admin/tenants/{id}/status, migration 080).

Tre saker som får kosta pengar om de går sönder tyst:

1. Spärren och etiketten säger olika saker — en 'pausad' kund vars nycklar
   fortfarande fungerar, eller en 'aktiv' som är utelåst.
2. En kundnyckel som kommer åt skrivningen.
3. Ett läge utanför värdemängden som smyger ned i databasen.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _master() -> dict[str, str]:
    return {"X-API-Key": get_settings().snajp_master_api_key}


def _kund() -> dict[str, str]:
    return {"X-API-Key": get_settings().snajp_demo_api_key}


VAG = f"/api/admin/tenants/{DEFAULT_TENANT_ID}/status"


async def test_kundnyckel_avvisas(client: TestClient):
    svar = client.put(VAG, headers=_kund(), json={"status": "pausad"})
    assert svar.status_code == 403


async def test_utan_nyckel_avvisas(client: TestClient):
    svar = client.put(VAG, json={"status": "pausad"})
    assert svar.status_code == 401


@pytest.mark.parametrize(
    "status,aktiv", [("pausad", False), ("avstangd", False), ("aktiv", True)]
)
async def test_status_och_sparr_skrivs_tillsammans(client: TestClient, status, aktiv):
    svar = client.put(VAG, headers=_master(), json={"status": status, "orsak": "test"})
    assert svar.status_code == 200
    tenant = svar.json()["tenant"]
    assert tenant["status"] == status
    assert tenant["active"] is aktiv


async def test_paus_later_sig_oppnas_igen(client: TestClient):
    client.put(VAG, headers=_master(), json={"status": "pausad", "orsak": "sommaruppehåll"})
    svar = client.put(VAG, headers=_master(), json={"status": "aktiv"})
    assert svar.json()["tenant"]["active"] is True
    # Städa: lämna default-tenanten aktiv för resten av sviten.


async def test_okant_lage_avvisas_fore_databasen(client: TestClient):
    svar = client.put(VAG, headers=_master(), json={"status": "vilande"})
    assert svar.status_code == 422


async def test_okand_kund_ger_404(client: TestClient):
    svar = client.put(
        "/api/admin/tenants/00000000-0000-0000-0000-000000000000/status",
        headers=_master(),
        json={"status": "pausad"},
    )
    assert svar.status_code == 404


async def test_gamla_aktivvagen_haller_etiketten_i_synk(client: TestClient):
    """Avstängning via PUT /aktiv (Avstangning-komponenten) ska sätta status
    till 'avstangd' — spärren och avsikten får aldrig säga olika saker."""
    vag_aktiv = f"/api/admin/tenants/{DEFAULT_TENANT_ID}/aktiv"
    svar = client.put(vag_aktiv, headers=_master(), json={"active": False, "orsak": "test"})
    assert svar.status_code == 200
    assert svar.json()["tenant"]["status"] == "avstangd"
    svar = client.put(vag_aktiv, headers=_master(), json={"active": True})
    assert svar.json()["tenant"]["status"] == "aktiv"
