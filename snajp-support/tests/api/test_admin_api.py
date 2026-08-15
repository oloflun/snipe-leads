"""Admin master control: cross-tenant-läsning bakom master-nyckeln.

Två saker som måste hålla samtidigt, och som drar åt olika håll:

1. Master-nyckeln SKA se över alla tenants här. Det är hela poängen med
   routern — require_tenant avvisar den mot kunddata, rätt designat, så
   överblicken behöver en egen väg.
2. En KUNDNYCKEL får aldrig komma in. Routern är den enda platsen i tjänsten
   där tenant-gränsen är öppen, och en läcka här är en läcka av allt.
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


def _master(client: TestClient) -> dict[str, str]:
    return {"X-API-Key": get_settings().snajp_master_api_key}


def _demo(client: TestClient) -> dict[str, str]:
    return {"X-API-Key": get_settings().snajp_demo_api_key}


ADMIN_PATHS = [
    "/api/admin/tenants",
    "/api/admin/runs",
    "/api/admin/events",
    "/api/admin/usage",
]


@pytest.mark.parametrize("path", ADMIN_PATHS)
def test_utan_nyckel_ar_admin_stangt(client, path):
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("path", ADMIN_PATHS)
def test_kundnyckel_slipper_inte_in(client, path):
    """Den enda plats i tjänsten där tenant-gränsen är öppen. En kundnyckel
    här hade betytt att varje kund kunde läsa varje annan kunds körningar."""
    assert client.get(path, headers=_demo(client)).status_code == 403


@pytest.mark.parametrize("path", ADMIN_PATHS)
def test_masternyckeln_kommer_in(client, path):
    assert client.get(path, headers=_master(client)).status_code == 200


def test_tenantlistan_bar_nyckeltal(client):
    body = client.get("/api/admin/tenants", headers=_master(client)).json()
    assert body["tenants"], "Minst demo-tenanten ska finnas."
    row = body["tenants"][0]
    for field in ("id", "slug", "name", "tickets", "runs", "tokens_in", "tokens_out"):
        assert field in row, f"{field} saknas — admin-översikten har inget att visa i kolumnen."


def test_okand_korning_ger_404_inte_tom_kropp(client):
    """Tom kropp hade lästs som 'körningen finns men är tom', vilket är en
    annan sak än att id:t är fel."""
    response = client.get(
        "/api/admin/runs/00000000-0000-0000-0000-000000000000", headers=_master(client)
    )
    assert response.status_code == 404


def test_korningar_gar_att_filtrera_pa_typ(client):
    response = client.get(
        "/api/admin/runs", params={"agent_type": "leads_research"}, headers=_master(client)
    )
    assert response.status_code == 200
    assert all(run["agent_type"] == "leads_research" for run in response.json()["runs"])


def test_notiscentret_filtrerar_pa_niva(client):
    response = client.get(
        "/api/admin/events", params={"level": "error"}, headers=_master(client)
    )
    assert response.status_code == 200
    assert all(event["level"] == "error" for event in response.json()["events"])


def test_kundens_utkast_gar_via_samma_granskningsko(client):
    """Admin har ingen egen, andra sanning om vad som väntar på godkännande."""
    response = client.get(
        f"/api/admin/tenants/{DEFAULT_TENANT_ID}/drafts", headers=_master(client)
    )
    assert response.status_code == 200
    assert "queue" in response.json()
