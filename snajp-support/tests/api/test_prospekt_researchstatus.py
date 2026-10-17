"""Research pågår → Ny (Sebbe 2026-10-07).

Ett Ny-bolag vars researchjobb är köat eller körs listas som `researching`;
när jobbet är klart (eller städat som misslyckat) står det som `new` igen.
Statusen är härledd ur liggaren, så ett lead som kunden redan flyttat rörs
aldrig, och ett rent utkastjobb räknas inte som research.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


async def _status(client, prospect_id: str) -> str | None:
    rader = (await client.get("/api/leads/prospects", headers=DEMO)).json()["prospects"]
    return next((p["status"] for p in rader if p["id"] == prospect_id), None)


@pytest.mark.anyio
async def test_ny_blir_research_pagar_medan_jobbet_lever_och_ny_igen_efterat():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            p = (await client.post("/api/leads/prospects", headers=DEMO, json={"company_name": "Livebolag AB"})).json()[
                "prospect"
            ]
            assert await _status(client, p["id"]) == "new"

            await storage.set_leads_job_status(
                DEFAULT_TENANT_ID, job_id="jobb-research-1", status="queued",
                scope="research_and_draft", prospect_id=p["id"],
            )
            assert await _status(client, p["id"]) == "researching"

            await storage.set_leads_job_status(
                DEFAULT_TENANT_ID, job_id="jobb-research-1", status="processing",
                scope="research_and_draft", prospect_id=p["id"],
            )
            assert await _status(client, p["id"]) == "researching"

            await storage.set_leads_job_status(
                DEFAULT_TENANT_ID, job_id="jobb-research-1", status="completed",
                scope="research_and_draft", prospect_id=p["id"],
            )
            assert await _status(client, p["id"]) == "new"


@pytest.mark.anyio
async def test_kundens_status_och_utkastjobb_rors_inte():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            kontaktad = (
                await client.post("/api/leads/prospects", headers=DEMO, json={"company_name": "Kontaktad AB"})
            ).json()["prospect"]
            await storage.update_prospect(DEFAULT_TENANT_ID, kontaktad["id"], status="contacted")
            await storage.set_leads_job_status(
                DEFAULT_TENANT_ID, job_id="jobb-research-2", status="processing",
                scope="research", prospect_id=kontaktad["id"],
            )

            utkast = (
                await client.post("/api/leads/prospects", headers=DEMO, json={"company_name": "Utkastbolag AB"})
            ).json()["prospect"]
            await storage.set_leads_job_status(
                DEFAULT_TENANT_ID, job_id="jobb-utkast-1", status="processing",
                scope="draft", prospect_id=utkast["id"],
            )

            assert await _status(client, kontaktad["id"]) == "contacted"
            assert await _status(client, utkast["id"]) == "new"
