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


@pytest.mark.anyio
async def test_skapa_utkast_kor_iris_research_och_raderna_stannar(monkeypatch):
    """Anton 2026-10-10: listans utkast görs exakt som Iris-leads (research och
    utkast per bolag), raderna stannar i listan och deras bakgrundsprospekt
    syns inte i Iris-tabellen. Förloppet står på listan. Raderna med ett
    gammalt generellt utkast kan fortfarande köas med /koa."""
    monkeypatch.setattr(leads_api, "_require_live_llm", lambda: None)
    koade: list[tuple[list[str], str]] = []

    async def _lagg(_app, _tenant, prospekt, *, scope, **_k):
        koade.append(([p["company_name"] for p in prospekt], scope))
        return []

    monkeypatch.setattr(leads_api, "_lagg_prospektjobb", _lagg)
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
            svar = await client.post(f"/api/leads/listor/{lista['id']}/utkast", headers=DEMO, json={})
            assert svar.status_code == 202, svar.text
            assert svar.json()["count"] == 2
            assert koade == [(["Snickarn i Umeå AB", "Rörfirman Ek AB"], "research_and_draft")]

            rader = await storage.list_lead_list_items(DEFAULT_TENANT_ID, lista["id"])
            assert len(rader) == 2 and all(r["prospect_id"] for r in rader), "raderna stannar och kopplas"
            iris = (await client.get("/api/leads/prospects", headers=DEMO)).json()
            synliga = {p["company_name"] for p in iris.get("prospects", iris if isinstance(iris, list) else [])}
            assert not synliga & {"Snickarn i Umeå AB", "Rörfirman Ek AB"}, "listans leads syns inte i Iris"
            lista_nu = (await client.get(f"/api/leads/listor/{lista['id']}", headers=DEMO)).json()["list"]
            assert lista_nu["processering"]["typ"] == "utkast"
            assert lista_nu["processering"]["totalt"] == 2

            # Rader vars lead redan har ett utkast hoppas över (utkaststatus
            # bär nyckeln `utkast_status`, inte `status`).
            monkeypatch.setattr(
                leads_api.utkaststatus, "per_prospekt",
                lambda _lagen, ids, **_k: {str(i): {"utkast_status": "vantar"} for i in ids},
            )
            await storage.satt_listprocessering(DEFAULT_TENANT_ID, lista["id"], None)
            igen = await client.post(f"/api/leads/listor/{lista['id']}/utkast", headers=DEMO, json={})
            assert igen.status_code == 422, igen.text

            await storage.spara_listutkast(
                DEFAULT_TENANT_ID, str(rader[0]["id"]),
                {"subject": "Fler kunder i Umeå", "body": "Hej,\n\nVi hjälper hantverksbolag i Norrland."},
            )
            rader = await storage.list_lead_list_items(DEFAULT_TENANT_ID, lista["id"])
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
