"""Listutkast (Sebbe 2026-10-07): utkast med generellt erbjudande till
listspårets bolag ("Utan webbplats"), sparat på raden och köat först när
kunden lagt in VD:s mejladress — då med signatur och via granskningskön."""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

import app.api.leads as leads_api
from app.config import DEFAULT_TENANT_ID, get_settings
from app.leads.listutkast import _tolka
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_tolka_kraver_amne_och_brodtext():
    assert _tolka('{"subject": "Hej", "body": "Text"}') == {"subject": "Hej", "body": "Text"}
    assert _tolka('```json\n{"subject": "A", "body": "B"}\n```') == {"subject": "A", "body": "B"}
    assert _tolka('{"subject": "", "body": "B"}') is None
    assert _tolka("inte json") is None


async def _vanta_pa_utkast(storage, list_id: str, antal: int) -> list[dict]:
    for _ in range(50):
        rader = await storage.list_lead_list_items(DEFAULT_TENANT_ID, list_id)
        if sum(1 for r in rader if r.get("utkast")) >= antal:
            return rader
        await asyncio.sleep(0.02)
    raise AssertionError("Utkasten skrevs aldrig.")


@pytest.mark.anyio
async def test_skriv_listutkast_och_koa_med_vd_adress(monkeypatch):
    monkeypatch.setattr(leads_api, "_require_live_llm", lambda: None)
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        storage.agent_settings[(DEFAULT_TENANT_ID, "leads")] = {
            "signatur": {"namn": "Sebastian Bergman", "titel": "Snajp Support", "bolag": "Snajp AB"}
        }
        await storage.save_context_doc(
            DEFAULT_TENANT_ID,
            kind="product_marketing",
            content=(
                "Vi hjälper små hantverksbolag i Norrland att få fler kunder. Vår agent hittar bolag "
                "som passar och skriver ett första mejl som ni granskar innan det skickas."
            ),
        )
        lista = await storage.create_lead_list(
            DEFAULT_TENANT_ID, titel="Utan webbplats, Iris 2026-10-07", icp={}, antal=10
        )
        for namn in ("Snickarn i Umeå AB", "Rörfirman Ek AB"):
            await storage.add_lead_list_item(
                DEFAULT_TENANT_ID, list_id=lista["id"], company_name=namn, ort="Umeå", signal="Bygg, 1 anställd"
            )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            svar = await client.post(f"/api/leads/listor/{lista['id']}/utkast", headers=DEMO)
            assert svar.status_code == 202, svar.text
            assert svar.json()["count"] == 2
            rader = await _vanta_pa_utkast(storage, lista["id"], 2)
            for rad in rader:
                assert rad["utkast"]["body"].startswith("Hej,")
                assert rad["utkast"]["subject"]

            # Andra klicket skriver inget nytt: alla rader har redan ett utkast.
            igen = await client.post(f"/api/leads/listor/{lista['id']}/utkast", headers=DEMO)
            assert igen.json()["count"] == 0

            rad = rader[0]
            url = f"/api/leads/listor/{lista['id']}/items/{rad['id']}/koa"
            assert (await client.post(url, headers=DEMO, json={"email": "inte-en-adress"})).status_code == 422
            assert (await client.post(url, headers=DEMO, json={"email": "faktura@snickarn.se"})).status_code == 422

            koat = await client.post(url, headers=DEMO, json={"email": "vd@snickarn.se"})
            assert koat.status_code == 200, koat.text
            queue_item_id = koat.json()["queue_item_id"]

            ko = await storage.list_review_queue(DEFAULT_TENANT_ID)
            post = next(i for i in ko if i["id"] == queue_item_id)
            assert post["prospect_email"] == "vd@snickarn.se"
            assert "Sebastian Bergman" in post["body"]  # signaturen lades på vid köningen

            # Samma rad köas inte två gånger.
            igen_koa = await client.post(url, headers=DEMO, json={"email": "vd@snickarn.se"})
            assert igen_koa.json() == {**igen_koa.json(), "queue_item_id": queue_item_id, "fanns": True}
