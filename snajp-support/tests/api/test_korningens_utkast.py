"""En körnings utkast (Sebbe 2026-10-07): status per lead, "Skriv utkast till
alla som saknar" och "Godkänn och skicka alla" — för körningens leads och
bara dem."""

import pytest
from httpx import ASGITransport, AsyncClient

import app.api.leads as leads_api
from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _seeda(storage) -> dict[str, str]:
    med_utkast = await storage.create_prospect(
        DEFAULT_TENANT_ID, company_name="Utkastbolaget AB", contact_email="info@utkastbolaget.se"
    )
    med_utkast["website"] = "https://utkastbolaget.se"
    utan_utkast = await storage.create_prospect(
        DEFAULT_TENANT_ID, company_name="Saknarbolaget AB", contact_email="info@saknarbolaget.se"
    )
    utan_utkast["website"] = "https://saknarbolaget.se"
    utan_mejl = await storage.create_prospect(DEFAULT_TENANT_ID, company_name="Mejllösa AB")
    utanfor = await storage.create_prospect(
        DEFAULT_TENANT_ID, company_name="Annan körning AB", contact_email="info@annan.se"
    )

    for prospekt in (med_utkast, utanfor):
        trad = await storage.ensure_outreach_thread(DEFAULT_TENANT_ID, prospect_id=prospekt["id"])
        await storage.queue_outreach_message(
            DEFAULT_TENANT_ID, thread_id=trad["id"], subject="Hej", body="Hej!",
            humanizer_variant="x", scheduled_at="2026-10-07T08:00:00+00:00", status="awaiting_review",
        )
    await storage.set_leads_job_status(
        DEFAULT_TENANT_ID, job_id="korning-1", status="completed", scope="batch",
        korning={
            "mal": 3, "levererade": 3, "undersokta": 3, "pagaende": 0, "klar": True, "tratt": [],
            "jobs": [
                {"job_id": "barn-1", "prospect_id": med_utkast["id"], "company_name": "Utkastbolaget AB"},
                {"job_id": "barn-2", "prospect_id": utan_utkast["id"], "company_name": "Saknarbolaget AB"},
                {"job_id": "barn-3", "prospect_id": utan_mejl["id"], "company_name": "Mejllösa AB"},
            ],
        },
    )
    return {"med": med_utkast["id"], "utan": utan_utkast["id"], "mejllos": utan_mejl["id"], "utanfor": utanfor["id"]}


@pytest.mark.anyio
async def test_status_skriv_och_skicka_galler_bara_korningens_leads(monkeypatch):
    async with app.router.lifespan_context(app):
        ids = await _seeda(app.state.storage)
        koade: list[str] = []

        async def fejk_lagg(app_state, tenant, prospects, **kw):
            assert kw["scope"] == "research_and_draft"
            koade.extend(p["id"] for p in prospects)
            return [{"job_id": f"j-{p['id']}", "prospect_id": p["id"]} for p in prospects]

        monkeypatch.setattr(leads_api, "_require_live_llm", lambda: None)
        monkeypatch.setattr(leads_api, "_lagg_prospektjobb", fejk_lagg)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            svar = (await client.get("/api/leads/korningar/korning-1/utkast", headers=DEMO)).json()
            status = {l["prospect_id"]: l for l in svar["leads"]}
            assert ids["utanfor"] not in status
            assert status[ids["med"]]["status"] == "vantar" and status[ids["med"]]["queue_item_id"]
            assert status[ids["utan"]]["status"] == "saknas" and status[ids["utan"]]["kan_mejlas"]
            assert status[ids["mejllos"]]["kan_mejlas"] is False and status[ids["mejllos"]]["notis"]
            assert svar["antal"] == {"vantar": 1, "saknas": 2, "kan_skrivas": 1}

            # Skriv: bara leadet som saknar utkast OCH har en kontaktmejl.
            skriv = await client.post("/api/leads/korningar/korning-1/utkast/skriv", headers=DEMO)
            assert skriv.status_code == 202 and skriv.json()["count"] == 1
            assert koade == [ids["utan"]]

            # Skicka: bara körningens väntande utkast — inte den andra körningens.
            skicka = (await client.post("/api/leads/korningar/korning-1/utkast/skicka", headers=DEMO)).json()
            assert skicka["skickade"] + skicka["vantar_pa_fonstret"] + len(skicka["stoppade"]) == 1
            kvar = await app.state.storage.list_review_queue(DEFAULT_TENANT_ID)
            assert [i["prospect_id"] for i in kvar if i["prospect_id"] in (ids["med"], ids["utanfor"])] in (
                [ids["utanfor"]],
                [ids["med"], ids["utanfor"]],  # en sändspärr kan lägga tillbaka posten för granskning
            )

            assert (await client.get("/api/leads/korningar/finns-inte/utkast", headers=DEMO)).status_code == 404
