"""Granskningskön: GET delar utkastet i brödtext och svans, PUT sparar
granskarens brödtext men behåller signaturen och den lagstadgade foten."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}
SIG = {"namn": "Sebastian Bergman", "titel": "Snajp Support", "bolag": "Snajp AB"}
FOT = "--\nBolaget AB, org.nr 556000-0000\n\nVill du inte få fler mejl från oss: https://x.se/avregistrera/abc"


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _koa(storage) -> str:
    storage.agent_settings[(DEFAULT_TENANT_ID, "leads")] = {"signatur": dict(SIG)}
    prospekt = await storage.create_prospect(
        DEFAULT_TENANT_ID,
        company_name="Granskbolaget AB",
        contact_name="Elin Ek",
        contact_email="info@granskbolaget.se",
    )
    prospekt["lagesbeskrivning"] = "Bygger ut verkstaden i Umeå."
    trad = await storage.ensure_outreach_thread(DEFAULT_TENANT_ID, prospect_id=prospekt["id"])
    ko = await storage.queue_outreach_message(
        DEFAULT_TENANT_ID,
        thread_id=trad["id"],
        subject="Verkstaden",
        body="Hej Elin!\n\nMed vänliga hälsningar,\nSebastian Bergman\nSnajp Support\n\nSnajp AB\n\n" + FOT,
        humanizer_variant="x",
        scheduled_at="2026-10-07T08:00:00+00:00",
        status="awaiting_review",
    )
    return ko["queue_item"]["id"]


@pytest.mark.anyio
async def test_kon_delar_utkastet_och_put_behaller_svansen():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        item_id = await _koa(storage)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            svar = (await client.get("/api/leads/queue", headers=DEMO)).json()
            post = next(i for i in svar["items"] if i["id"] == item_id)
            assert post["brodtext"] == "Hej Elin!\n\nMed vänliga hälsningar,"
            assert post["svans"].startswith("Sebastian Bergman") and post["svans"].endswith("abc")
            assert post["contact_name"] == "Elin Ek"
            assert post["lagesbeskrivning"] == "Bygger ut verkstaden i Umeå."

            # Brödtexten skrivs om (AI-knappen eller granskaren) — svansen följer med.
            r = await client.put(
                f"/api/leads/queue/{item_id}",
                headers=DEMO,
                json={"subject": "Ny vinkel", "brodtext": "Hej Elin, kort fråga.\n\nHälsningar,"},
            )
            assert r.status_code == 200
            m = storage.outreach_messages[DEFAULT_TENANT_ID][-1]
            assert m["body"].startswith("Hej Elin, kort fråga.\n\nHälsningar,\nSebastian Bergman\n")
            assert m["body"].endswith(FOT)

            # Äldre klient som skickar hela mejlet utan svansen: svansen läggs tillbaka.
            r = await client.put(
                f"/api/leads/queue/{item_id}",
                headers=DEMO,
                json={"subject": "Ny vinkel", "body": "Helt ny text utan signatur."},
            )
            assert r.status_code == 200
            m = storage.outreach_messages[DEFAULT_TENANT_ID][-1]
            # Ingen avslutning i texten: hälsningsfrasen läggs på före signaturen.
            assert m["body"].startswith("Helt ny text utan signatur.\n\nVänliga hälsningar,\nSebastian Bergman")
            assert m["body"].count("Sebastian Bergman") == 1 and m["body"].endswith(FOT)
