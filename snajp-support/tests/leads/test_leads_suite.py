"""Leads Suite (plan del F, Fas 10): statuslogg, tidslinje, anteckningar,
uppgifter, sparade vyer, CSV-import och envägssynken till externt CRM.

API:t prövas över HTTP mot appen i minne (MemoryStorage), CRM-synken med
httpx.MockTransport vid nätverksgränsen."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.integrationer import lagring as integrationer
from app.leads import crm_synk
from app.main import app
from app.storage.memory import MemoryStorage

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}
TENANT = "00000000-0000-4000-a000-000000000001"
ANNAN = "00000000-0000-4000-a000-0000000000ff"

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _prospekt(namn: str = "Alfa Bygg AB") -> dict:
    return await app.state.storage.create_prospect(TENANT, company_name=namn, origin="manual")


# -- Statusloggen ---------------------------------------------------------------


async def test_statusbyte_loggas_och_syns_i_tidslinjen():
    async with app.router.lifespan_context(app):
        p = await _prospekt()
        async with _client() as client:
            svar = await client.patch(f"/api/leads/prospects/{p['id']}", headers=DEMO, json={"status": "contacted"})
            assert svar.status_code == 200, svar.text
            # Samma status igen är inget byte och loggas inte.
            await client.patch(f"/api/leads/prospects/{p['id']}", headers=DEMO, json={"status": "contacted"})

            logg = await app.state.storage.list_status_logg(TENANT, prospect_id=p["id"])
            assert [(r["fran"], r["till"], r["kalla"]) for r in logg] == [("new", "contacted", "manuell")]

            linje = (await client.get(f"/api/leads/prospects/{p['id']}/tidslinje", headers=DEMO)).json()["handelser"]
            assert [h["typ"] for h in linje] == ["status", "skapad"]
            assert linje[0]["rubrik"] == "new → contacted"

            lista = (await client.get("/api/leads/prospects", headers=DEMO)).json()["prospects"]
            rad = next(x for x in lista if x["id"] == p["id"])
            assert rad["senaste_handelse_at"] == logg[0]["created_at"]


async def test_kodens_statusbyte_far_kalla_kod():
    storage = MemoryStorage()
    p = await storage.create_prospect(TENANT, company_name="Beta AB")
    await storage.update_prospect(TENANT, p["id"], status="replied")
    [rad] = await storage.list_status_logg(TENANT)
    assert rad["kalla"] == "kod" and rad["till"] == "replied"


# -- Anteckningar, uppgifter, tidslinje ----------------------------------------


async def test_anteckning_och_uppgift_syns_nyast_forst():
    async with app.router.lifespan_context(app):
        p = await _prospekt("Gamma AB")
        async with _client() as client:
            a = await client.post(f"/api/leads/prospects/{p['id']}/anteckningar", headers=DEMO, json={"text": "Ringde VD"})
            assert a.status_code == 201, a.text
            await asyncio.sleep(0.002)
            u = await client.post(
                f"/api/leads/prospects/{p['id']}/uppgifter",
                headers=DEMO,
                json={"titel": "Skicka offert", "forfaller": "2026-10-09"},
            )
            assert u.status_code == 201, u.text
            assert u.json()["uppgift"]["forfaller"] == "2026-10-09"

            linje = (await client.get(f"/api/leads/prospects/{p['id']}/tidslinje", headers=DEMO)).json()["handelser"]
            assert [h["typ"] for h in linje] == ["uppgift", "anteckning", "skapad"]
            assert linje[0]["rubrik"] == "Skicka offert" and linje[0]["klar"] is False
            assert linje[1]["text"] == "Ringde VD"

            tom = await client.post(f"/api/leads/prospects/{p['id']}/anteckningar", headers=DEMO, json={"text": ""})
            assert tom.status_code == 422
            okand = await client.get("/api/leads/prospects/inte-ett-uuid/tidslinje", headers=DEMO)
            assert okand.status_code == 404


async def test_uppgift_klar_satter_klar_at_och_filtreras():
    async with app.router.lifespan_context(app):
        p = await _prospekt("Delta AB")
        async with _client() as client:
            u = (await client.post(
                f"/api/leads/prospects/{p['id']}/uppgifter", headers=DEMO, json={"titel": "Följ upp", "forfaller": None}
            )).json()["uppgift"]
            assert u["klar"] is False and u["klar_at"] is None

            klar = await client.patch(f"/api/leads/uppgifter/{u['id']}", headers=DEMO, json={"klar": True})
            assert klar.status_code == 200, klar.text
            assert klar.json()["uppgift"]["klar"] is True and klar.json()["uppgift"]["klar_at"]

            oppna = (await client.get("/api/leads/uppgifter?oppna=1", headers=DEMO)).json()["uppgifter"]
            assert u["id"] not in [x["id"] for x in oppna]
            alla = (await client.get("/api/leads/uppgifter", headers=DEMO)).json()["uppgifter"]
            assert u["id"] in [x["id"] for x in alla]

            saknas = await client.patch(
                "/api/leads/uppgifter/00000000-0000-4000-a000-00000000abcd", headers=DEMO, json={"klar": True}
            )
            assert saknas.status_code == 404


async def test_mejl_i_tidslinjen():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        p = await _prospekt("Epsilon AB")
        trad = await storage.ensure_outreach_thread(TENANT, prospect_id=p["id"])
        ut = await storage.queue_outreach_message(
            TENANT, thread_id=trad["id"], body="Hej " + "x" * 400, subject="Förslag",
            humanizer_variant="a", scheduled_at=None,
        )
        await storage.mark_outreach_message_sent(TENANT, ut["message"]["id"], "2026-10-01T09:00:00+00:00")
        await storage.record_inbound_reply(TENANT, thread_id=trad["id"], body="Låter bra")
        async with _client() as client:
            linje = (await client.get(f"/api/leads/prospects/{p['id']}/tidslinje", headers=DEMO)).json()["handelser"]
        typer = [h["typ"] for h in linje]
        assert typer.index("mejl_in") < typer.index("mejl_ut")
        mejl_ut = next(h for h in linje if h["typ"] == "mejl_ut")
        assert mejl_ut["rubrik"] == "Förslag" and len(mejl_ut["text"]) == 300


# -- Sparade vyer --------------------------------------------------------------


async def test_vyer_skapas_listas_och_raderas():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            ny = await client.post("/api/leads/vyer", headers=DEMO, json={"namn": "Heta", "filter": {"niva": ["A"]}})
            assert ny.status_code == 201, ny.text
            vy = ny.json()["vy"]
            assert set(vy) == {"id", "namn", "filter", "created_at"} and vy["filter"] == {"niva": ["A"]}

            vyer = (await client.get("/api/leads/vyer", headers=DEMO)).json()["vyer"]
            assert vy["id"] in [v["id"] for v in vyer]

            # En annan tenants vy går inte att radera härifrån.
            frammande = await app.state.storage.create_lead_view(ANNAN, namn="Deras", filter={})
            assert (await client.delete(f"/api/leads/vyer/{frammande['id']}", headers=DEMO)).status_code == 404
            assert await app.state.storage.list_lead_views(ANNAN)

            assert (await client.delete(f"/api/leads/vyer/{vy['id']}", headers=DEMO)).status_code == 204
            assert (await client.delete(f"/api/leads/vyer/{vy['id']}", headers=DEMO)).status_code == 404


# -- Import --------------------------------------------------------------------


async def test_import_skapar_lista_med_kalla_import():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.post(
                "/api/leads/import",
                headers=DEMO,
                json={
                    "titel": "Från HubSpot",
                    "rader": [
                        {"company_name": "Zeta AB", "contact_email": "vd@zeta.se", "contact_phone": "070-1", "status": "Lead"},
                        {"company_name": "Eta AB", "orgnr": "556000-0003", "website": "eta.se"},
                        {"company_name": "  ", "contact_name": "Utan bolag"},
                        {"contact_email": "x@y.se"},
                    ],
                },
            )
            assert svar.status_code == 201, svar.text
            body = svar.json()
            assert body["antal"] == 2 and body["hoppade_over"] == 2
            assert body["list"]["kalla"] == "import" and body["list"]["status"] == "klar"

            detalj = (await client.get(f"/api/leads/listor/{body['list']['id']}", headers=DEMO)).json()
            assert [r["company_name"] for r in detalj["items"]] == ["Zeta AB", "Eta AB"]
            assert detalj["items"][0]["contact_phone"] == "070-1"

            tom = await client.post("/api/leads/import", headers=DEMO, json={"titel": "Tom", "rader": [{"orgnr": "1"}]})
            assert tom.status_code == 422


# -- Automationsinställningarna i config ---------------------------------------


async def test_config_automation_faltvis_och_crm_synk():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            start = (await client.get("/api/leads/config", headers=DEMO)).json()
            assert start["automation"]["per_typ"]["inkorg"]["utkast_auto"] is False
            assert start["crm_synk"] == {"leverantor": None, "integration_id": None}

            await client.put(
                "/api/leads/config", headers=DEMO,
                json={"automation": {"per_typ": {"import": {"uppfoljning_dagar": 0}}}},
            )
            svar = await client.put(
                "/api/leads/config", headers=DEMO,
                json={"automation": {"per_typ": {"import": {"utkast_auto": False}}, "jev_bortval": False}},
            )
            assert svar.status_code == 200, svar.text
            regler = svar.json()["automation"]
            assert regler["per_typ"]["import"] == {"utkast_auto": False, "uppfoljning_dagar": 0}
            assert regler["jev_bortval"] is False

            fel = await client.put("/api/leads/config", headers=DEMO, json={"automation": {"per_typ": {"iris": {"uppfoljning_dagar": 61}}}})
            assert fel.status_code == 422
            okand = await client.put(
                "/api/leads/config", headers=DEMO,
                json={"crm_synk": {"leverantor": "hubspot", "integration_id": "00000000-0000-4000-a000-00000000beef"}},
            )
            assert okand.status_code == 422


# -- CRM-synken ----------------------------------------------------------------


async def _med_crm(storage, leverantor: str) -> None:
    rad = await integrationer.skapa(
        storage, TENANT, typ="http", namn=f"CRM {leverantor}", beskrivning="",
        konfig={}, hemligheter={"api_key": "hemlig-nyckel"},
    )
    await storage.set_agent_settings(
        TENANT, agent_type="leads", settings={"crm_synk": {"leverantor": leverantor, "integration_id": rad["id"]}}
    )


def _mocka(monkeypatch, handler) -> list[httpx.Request]:
    anrop: list[httpx.Request] = []
    original = httpx.AsyncClient

    def _hanterare(request: httpx.Request) -> httpx.Response:
        anrop.append(request)
        return handler(request)

    monkeypatch.setattr(
        crm_synk.httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(_hanterare), **kw)
    )
    return anrop


async def test_hubspot_skapar_bolag_och_anteckning(monkeypatch):
    storage = MemoryStorage()
    await _med_crm(storage, "hubspot")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer hemlig-nyckel"
        if request.url.path.endswith("/companies/search"):
            return httpx.Response(200, json={"results": []})
        if request.url.path.endswith("/objects/companies"):
            return httpx.Response(201, json={"id": "42"})
        return httpx.Response(201, json={"id": "n1"})

    anrop = _mocka(monkeypatch, handler)
    prospect = {"id": "p", "company_name": "Theta AB", "website": "https://www.theta.se/om", "contact_phone": "08-1"}
    await crm_synk.synka_prospekt(storage, TENANT, prospect, handelse="status", text="contacted")

    assert [(r.method, r.url.path) for r in anrop] == [
        ("POST", "/crm/v3/objects/companies/search"),
        ("POST", "/crm/v3/objects/companies"),
        ("POST", "/crm/v3/objects/notes"),
    ]
    bolag = json.loads(anrop[1].content)["properties"]
    assert bolag == {"name": "Theta AB", "domain": "theta.se", "phone": "08-1"}
    notis = json.loads(anrop[2].content)
    assert notis["properties"]["hs_note_body"] == "Snipra: status: contacted"
    assert notis["associations"][0]["to"]["id"] == "42"
    assert notis["associations"][0]["types"][0]["associationTypeId"] == 190


async def test_pipedrive_uppdaterar_befintlig_organisation(monkeypatch):
    storage = MemoryStorage()
    await _med_crm(storage, "pipedrive")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["api_token"] == "hemlig-nyckel"
        if request.url.path.endswith("/organizations/search"):
            return httpx.Response(200, json={"data": {"items": [{"item": {"id": 7}}]}})
        if request.method == "PUT":
            return httpx.Response(200, json={"data": {"id": 7}})
        return httpx.Response(201, json={"data": {"id": 99}})

    anrop = _mocka(monkeypatch, handler)
    await crm_synk.synka_prospekt(
        storage, TENANT, {"id": "p", "company_name": "Iota AB"}, handelse="anteckning", text="Ringde"
    )
    assert [(r.method, r.url.path) for r in anrop] == [
        ("GET", "/v1/organizations/search"),
        ("PUT", "/v1/organizations/7"),
        ("POST", "/v1/notes"),
    ]
    assert json.loads(anrop[2].content) == {"content": "Snipra: anteckning: Ringde", "org_id": 7}


async def test_leverantorens_500_kastar_aldrig(monkeypatch):
    storage = MemoryStorage()
    await _med_crm(storage, "hubspot")
    anrop = _mocka(monkeypatch, lambda request: httpx.Response(500, json={"fel": "nere"}))
    await crm_synk.synka_prospekt(storage, TENANT, {"id": "p", "company_name": "Kappa AB"}, handelse="status")
    assert len(anrop) == 1


async def test_utan_installning_gors_inget_anrop(monkeypatch):
    anrop = _mocka(monkeypatch, lambda request: httpx.Response(200, json={}))
    await crm_synk.synka_prospekt(MemoryStorage(), TENANT, {"company_name": "Lambda AB"}, handelse="status")
    assert anrop == []
