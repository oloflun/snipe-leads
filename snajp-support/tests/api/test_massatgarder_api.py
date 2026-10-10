"""Massåtgärderna i Iris-listan och listornas Ta bort/Kopiera till kund
(Antons beställning 2026-10-07/08), mot MemoryStorage genom HTTP-lagret."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

import app.api.leads as leads_api
from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}
T = DEFAULT_TENANT_ID

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _klient() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _lead(storage, namn: str, **k) -> dict:
    return await storage.create_prospect(T, company_name=namn, contact_email=f"info@{namn.split()[0].lower()}.se", **k)


async def _utkast(storage, prospect_id: str, *, status: str = "awaiting_review", text: str = "Hej!") -> dict:
    trad = await storage.ensure_outreach_thread(T, prospect_id=prospect_id)
    return await storage.queue_outreach_message(
        T, thread_id=trad["id"], subject="Ämne", body=text, humanizer_variant="v",
        scheduled_at="2026-10-08T08:00:00+00:00", status=status,
    )


async def _skickat(storage, prospect_id: str) -> dict:
    koat = await _utkast(storage, prospect_id, status="queued", text="Skickat mejl")
    await storage.mark_outreach_message_sent(T, koat["message"]["id"], "2026-10-06T09:00:00+00:00")
    await storage.update_send_queue_status(T, koat["queue_item"]["id"], status="sent", gate_checks={})
    return koat


async def test_listan_bar_utkaststatus_och_doljer_ring_och_arkiverade():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        vantar = await _lead(storage, "Vantarbolaget AB")
        await _utkast(storage, vantar["id"])
        godkant = await _lead(storage, "Godkantbolaget AB")
        g = await _utkast(storage, godkant["id"], status="queued")
        await storage.update_send_queue_status(T, g["queue_item"]["id"], status="queued", gate_checks={"approved_by": "human"})
        utan = await _lead(storage, "Utanbolaget AB")
        ring = await _lead(storage, "Ringbolaget AB", origin="ring")
        arkiv = await _lead(storage, "Arkivbolaget AB")
        await storage.arkivera_prospekt(T, [arkiv["id"]], arkivera=True)

        async with _klient() as klient:
            rader = {p["id"]: p for p in (await klient.get("/api/leads/prospects", headers=DEMO)).json()["prospects"]}
            assert ring["id"] not in rader and arkiv["id"] not in rader
            assert rader[vantar["id"]]["utkast_status"] == "vantar" and rader[vantar["id"]]["queue_item_id"]
            assert rader[godkant["id"]]["utkast_status"] == "godkant" and rader[godkant["id"]]["skickas_tidigast"]
            assert rader[utan["id"]]["utkast_status"] == "saknas"

            arkiverade = (await klient.get("/api/leads/prospects?arkiverade=1", headers=DEMO)).json()["prospects"]
            assert [p["id"] for p in arkiverade] == [arkiv["id"]]


async def test_avvisat_utkast_kasseras_och_kan_inte_avvisas_igen():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        lead = await _lead(storage, "Avvisas AB")
        koat = await _utkast(storage, lead["id"])
        trad = await storage.find_outreach_thread(T, prospect_id=lead["id"])
        async with _klient() as klient:
            svar = await klient.post(f"/api/leads/queue/{koat['queue_item']['id']}/reject", headers=DEMO)
            assert svar.status_code == 200
            assert await storage.get_pending_outreach_message(T, trad["id"]) is None
            assert koat["message"]["kasserad_at"]
            igen = await klient.post(f"/api/leads/queue/{koat['queue_item']['id']}/reject", headers=DEMO)
            assert igen.status_code == 409
            lada = (await klient.get(f"/api/leads/prospects/{lead['id']}/utkast", headers=DEMO)).json()
            assert lada["utkast_status"] == "avvisat" and lada["queue_item_id"] is None


async def test_skapa_om_ersatter_det_vantande_utkastet_och_hoppar_over_kontaktade(monkeypatch):
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        lead = await _lead(storage, "Omskrivning AB")
        gammalt = await _utkast(storage, lead["id"], text="gammalt")
        kontaktad = await _lead(storage, "Kontaktad AB")
        await _skickat(storage, kontaktad["id"])
        koade: list[str] = []

        async def fejk_lagg(app_state, tenant, prospects, **kw):
            koade.extend(p["id"] for p in prospects)
            return [{"job_id": f"j-{p['id']}", "prospect_id": p["id"]} for p in prospects]

        monkeypatch.setattr(leads_api, "_require_live_llm", lambda: None)
        monkeypatch.setattr(leads_api, "_lagg_prospektjobb", fejk_lagg)
        async with _klient() as klient:
            svar = await klient.post(
                "/api/leads/prospects/processa-om",
                headers=DEMO,
                json={"prospect_ids": [lead["id"], kontaktad["id"]], "scope": "research_and_draft", "ersatt": True},
            )
        assert svar.status_code == 202, svar.text
        assert koade == [lead["id"]] and svar.json()["hoppade_over"] == [kontaktad["id"]]
        assert gammalt["queue_item"]["status"] == "cancelled" and gammalt["message"]["kasserad_at"]


async def test_skapa_utkast_tar_upp_till_200_leads():
    from app.api.schemas import ProcessaOmRequest

    assert ProcessaOmRequest(prospect_ids=["x"] * 200).ersatt is False
    with pytest.raises(ValueError):
        ProcessaOmRequest(prospect_ids=["x"] * 201)


async def test_arkivera_doljer_stoppar_utkastet_och_aterstall_tar_tillbaka():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        lead = await _lead(storage, "Arkiveras AB")
        koat = await _utkast(storage, lead["id"], status="queued")
        async with _klient() as klient:
            svar = await klient.post("/api/leads/prospects/arkivera", headers=DEMO, json={"ids": [lead["id"]], "arkivera": True})
            assert svar.status_code == 200 and svar.json()["installda_utskick"] == 1
            assert koat["queue_item"]["status"] == "cancelled" and koat["message"]["kasserad_at"]
            synliga = [p["id"] for p in (await klient.get("/api/leads/prospects", headers=DEMO)).json()["prospects"]]
            assert lead["id"] not in synliga

            await klient.post("/api/leads/prospects/arkivera", headers=DEMO, json={"ids": [lead["id"]], "arkivera": False})
            synliga = [p["id"] for p in (await klient.get("/api/leads/prospects", headers=DEMO)).json()["prospects"]]
            assert lead["id"] in synliga


async def test_ta_bort_vagrar_kontaktade_leads_och_raderar_resten():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        okontaktad = await _lead(storage, "Raderas AB")
        await _utkast(storage, okontaktad["id"])
        kontaktad = await _lead(storage, "Behalls AB")
        await _skickat(storage, kontaktad["id"])
        async with _klient() as klient:
            svar = await klient.post(
                "/api/leads/prospects/radera",
                headers=DEMO,
                json={"ids": [okontaktad["id"], kontaktad["id"], "inte-ett-id"]},
            )
        data = svar.json()
        assert data["raderade"] == [okontaktad["id"]]
        assert {"id": kontaktad["id"], "skal": "kontaktad"} in data["vagrade"]
        assert {"id": "inte-ett-id", "skal": "finns_inte"} in data["vagrade"]
        assert await storage.get_prospect(T, okontaktad["id"]) is None
        # Tråden och utkastet följde med (on delete cascade).
        assert await storage.find_outreach_thread(T, prospect_id=okontaktad["id"]) is None
        assert await storage.get_prospect(T, kontaktad["id"]) is not None


async def test_skickat_bar_leadets_status():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        lead = await _lead(storage, "Svarade AB")
        await _skickat(storage, lead["id"])
        await storage.update_prospect(T, lead["id"], status="replied")
        async with _klient() as klient:
            rader = (await klient.get("/api/leads/skickat", headers=DEMO)).json()["skickat"]
        rad = next(r for r in rader if r["prospect_id"] == lead["id"])
        assert rad["status"] == "replied"


async def test_ta_bort_lista_med_raderna_men_inte_en_som_byggs():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        lista = await storage.create_lead_list(T, titel="Gammal lista", icp={}, antal=2, kalla="crm")
        await storage.add_lead_list_item(T, list_id=lista["id"], company_name="Rad AB")
        await storage.set_lead_list_status(T, lista["id"], status="klar")
        byggs = await storage.create_lead_list(T, titel="Pågående", icp={}, antal=2)
        await storage.set_lead_list_status(T, byggs["id"], status="byggs")
        async with _klient() as klient:
            assert (await klient.delete(f"/api/leads/listor/{lista['id']}", headers=DEMO)).status_code == 200
            assert (await klient.delete(f"/api/leads/listor/{lista['id']}", headers=DEMO)).status_code == 404
            assert (await klient.delete(f"/api/leads/listor/{byggs['id']}", headers=DEMO)).status_code == 409
        assert await storage.get_lead_list(T, lista["id"]) is None
        assert await storage.list_lead_list_items(T, lista["id"]) == []


async def test_admin_kopierar_och_flyttar_lista_till_annan_kund():
    master = {"X-API-Key": get_settings().snajp_master_api_key}
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        fran = await storage.get_tenant(T)
        till = await storage.create_tenant(slug="mottagaren", name="Mottagaren AB")
        lista = await storage.create_lead_list(T, titel="Bygg i Norr", icp={"must_have": ["bygg"]}, antal=3)
        for namn, orgnr in (("Fri Bygg AB", "5560000001"), ("Tagen Bygg AB", "5560000002"), ("Ny Bygg AB", None)):
            await storage.add_lead_list_item(T, list_id=lista["id"], company_name=namn, orgnr=orgnr, contact_phone="070-1")
        await storage.set_lead_list_status(T, lista["id"], status="klar")
        # Mottagaren har redan "Tagen Bygg" som prospekt: den raden hoppas över.
        await storage.create_prospect(till["id"], company_name="Tagen Bygg AB")

        async with _klient() as klient:
            assert (await klient.post(
                f"/api/admin/listor/{lista['id']}/till-kund", headers=DEMO,
                json={"fran_tenant": fran["slug"], "till_tenant": "mottagaren"},
            )).status_code == 403
            kopia = await klient.post(
                f"/api/admin/listor/{lista['id']}/till-kund", headers=master,
                json={"fran_tenant": fran["slug"], "till_tenant": "mottagaren", "flytta": False},
            )
            assert kopia.status_code == 200, kopia.text
            k = kopia.json()
            assert (k["kopierade"], k["upptagna"], k["flyttad"]) == (2, 1, False)
            assert await storage.get_lead_list(T, lista["id"]) is not None
            namn = {r["company_name"] for r in await storage.list_lead_list_items(till["id"], k["list"]["id"])}
            assert namn == {"Fri Bygg AB", "Ny Bygg AB"}

            # En flytt till en tredje kund raderar källistan efteråt.
            tredje = await storage.create_tenant(slug="tredje", name="Tredje AB")
            flytt = (await klient.post(
                f"/api/admin/listor/{lista['id']}/till-kund", headers=master,
                json={"fran_tenant": T, "till_tenant": tredje["id"], "flytta": True},
            )).json()
            assert (flytt["kopierade"], flytt["flyttad"]) == (3, True)
            assert await storage.get_lead_list(T, lista["id"]) is None
            assert await storage.list_lead_list_items(T, lista["id"]) == []


async def test_skapa_utkast_koar_inte_ett_lead_som_redan_researchas(monkeypatch):
    """Två Skapa utkast-anrop 27 s isär gav fem leads två jobb och två utkast
    var (development 2026-10-08). Ett lead med ett köat eller pågående
    researchjobb hoppas över och rapporteras i `pagar_redan`."""
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        pagaende = await _lead(storage, "Pågående AB")
        ledig = await _lead(storage, "Ledig AB")
        await storage.set_leads_job_status(
            T, job_id="j-pagar", status="processing", scope="research_and_draft", prospect_id=pagaende["id"]
        )
        koade: list[str] = []

        async def fejk_lagg(app_state, tenant, prospects, **kw):
            koade.extend(p["id"] for p in prospects)
            return [{"job_id": f"j-{p['id']}", "prospect_id": p["id"]} for p in prospects]

        monkeypatch.setattr(leads_api, "_require_live_llm", lambda: None)
        monkeypatch.setattr(leads_api, "_lagg_prospektjobb", fejk_lagg)
        async with _klient() as klient:
            svar = await klient.post(
                "/api/leads/prospects/processa-om",
                headers=DEMO,
                json={"prospect_ids": [pagaende["id"], ledig["id"]], "scope": "research_and_draft"},
            )
            assert svar.status_code == 202, svar.text
            assert koade == [ledig["id"]] and svar.json()["pagar_redan"] == [pagaende["id"]]
            bara = await klient.post(
                "/api/leads/prospects/processa-om",
                headers=DEMO,
                json={"prospect_ids": [pagaende["id"]], "scope": "research_and_draft"},
            )
        assert bara.json()["count"] == 0 and koade == [ledig["id"]]
