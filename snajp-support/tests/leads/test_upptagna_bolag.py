"""Iris och leadslistorna hämtar aldrig samma bolag, och kundens CRM-kunder
blir aldrig leads (Sebbes beställning 2026-10-06, migration 098).

Spärren är app/leads/upptagna.py: Iris-prospekt, rader i varje lista och
CRM-kundlistan bildar EN mängd som både Iris och listbygget utesluter."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.api.leads import _run_list_job, _spara_listspar
from app.config import get_settings
from app.jobs.store import MemoryJobStore
from app.leads import upptagna
from app.main import app
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"
DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


# -- Nycklarna ---------------------------------------------------------------


def test_nyckeln_bortser_fran_bolagsform_skiftlage_och_skiljetecken():
    assert upptagna.nyckel("Byggarna Berggren AB") == upptagna.nyckel("byggarna berggren")
    assert upptagna.nyckel("AB Volvo (publ)") == "volvo"
    assert upptagna.nyckel("Smith & Co HB") == upptagna.nyckel("Smith och Co")
    assert upptagna.nyckel("Bygg HB i likvidation") == "bygg"
    # Ett namn som BARA är en bolagsform faller inte ihop till tom sträng.
    assert upptagna.nyckel("AB") == "ab"


def test_orgnr_i_alla_former_ger_samma_nyckel():
    assert upptagna.orgnr_nyckel("556677-8899") == upptagna.orgnr_nyckel("5566778899")
    assert upptagna.orgnr_nyckel("16556677-8899") == "orgnr:5566778899"
    assert upptagna.orgnr_nyckel("123") is None


def test_upptagen_traffar_pa_namn_eller_orgnr():
    sedda = upptagna.bolagsnycklar([{"company_name": "Alfa Bygg AB", "orgnr": "556000-0001"}])
    assert upptagna.upptagen(sedda, "ALFA BYGG")
    assert upptagna.upptagen(sedda, "Helt Annat Namn AB", "5560000001")
    assert not upptagna.upptagen(sedda, "Beta Bygg AB", "556000-0002")


async def test_upptagna_omfattar_prospekt_listrader_och_crm():
    storage = MemoryStorage()
    await storage.create_prospect(TENANT, company_name="Iris Lead AB", origin="manual")
    lista = await storage.create_lead_list(TENANT, titel="Bygg", icp={}, antal=5)
    await storage.add_lead_list_item(TENANT, list_id=lista["id"], company_name="Listbolaget AB")
    crm = await storage.create_lead_list(TENANT, titel="Kunder", icp={}, antal=1, kalla="crm")
    await storage.add_lead_list_item(TENANT, list_id=crm["id"], company_name="Kund AB", orgnr="556111-2222")

    sedda = await upptagna.hamta(storage, TENANT)
    assert upptagna.upptagen(sedda, "Iris Lead")
    assert upptagna.upptagen(sedda, "Listbolaget")
    assert upptagna.upptagen(sedda, "Nytt namn", "5561112222")
    # Annan kund ser inte samma mängd.
    assert await upptagna.hamta(storage, "00000000-0000-4000-a000-0000000000ff") == set()


# -- Listbygget utesluter Iris, andra listor och CRM-kunder -----------------


async def test_listbygget_hoppar_over_iris_prospekt_andra_listor_och_crm_kunder():
    storage = MemoryStorage()
    jobs = MemoryJobStore()
    app_state = SimpleNamespace(storage=storage, jobs=jobs)

    await storage.create_prospect(TENANT, company_name="Iris Lead AB", origin="manual")
    gammal = await storage.create_lead_list(TENANT, titel="Gammal", icp={}, antal=1)
    await storage.add_lead_list_item(TENANT, list_id=gammal["id"], company_name="Redan Listad AB")
    crm = await storage.create_lead_list(TENANT, titel="Kunder", icp={}, antal=1, kalla="crm")
    await storage.add_lead_list_item(TENANT, list_id=crm["id"], company_name="Kunden", orgnr="556111-2222")

    lista = await storage.create_lead_list(TENANT, titel="Ny", icp={"geography": "Umeå"}, antal=10)
    job_id = await jobs.create(tenant_id=TENANT, status="queued")
    traffar = [
        {"company_name": "Iris Lead", "contact_email": "vd@iris.se"},
        {"company_name": "REDAN LISTAD AB", "contact_email": "vd@listad.se"},
        {"company_name": "Kunden Omdöpt AB", "orgnr": "5561112222", "contact_email": "vd@kund.se"},
        {"company_name": "Helt Ny AB", "contact_email": "vd@ny.se"},
    ]
    with (
        patch("app.leads.sources.merinfo.aktiv", return_value=False),
        patch("app.api.leads.hitta_bolag", new=AsyncMock(return_value=traffar)) as sok,
    ):
        await _run_list_job(app_state, {"job_id": job_id, "tenant_id": TENANT, "list_id": lista["id"]})

    # Sökningen fick mängden, så den kan välja andra bolag i stället ...
    uteslut = sok.await_args.kwargs["uteslut_namn"]
    assert upptagna.upptagen(uteslut, "Iris Lead AB") and upptagna.upptagen(uteslut, "Redan Listad AB")
    # ... och det som ändå slank igenom fälls innan raderna skrivs.
    items = await storage.list_lead_list_items(TENANT, lista["id"])
    assert [i["company_name"] for i in items] == ["Helt Ny AB"]


async def test_merinfo_sokningen_far_uteslutningen_i_listlaget():
    storage = MemoryStorage()
    jobs = MemoryJobStore()
    app_state = SimpleNamespace(storage=storage, jobs=jobs)
    await storage.create_prospect(TENANT, company_name="Iris Lead AB", origin="manual")
    lista = await storage.create_lead_list(TENANT, titel="Ny", icp={"industries": ["bygg"]}, antal=3)
    job_id = await jobs.create(tenant_id=TENANT, status="queued")

    with (
        patch("app.leads.sources.merinfo.aktiv", return_value=True),
        patch("app.leads.sources.merinfo.sok", new=AsyncMock(return_value=[])) as sok,
        patch("app.leads.profil.sakerstall_profil", new=AsyncMock(return_value={})),
    ):
        await _run_list_job(app_state, {"job_id": job_id, "tenant_id": TENANT, "list_id": lista["id"]})

    assert sok.await_args.kwargs["lage"] == "lista"
    assert upptagna.upptagen(sok.await_args.kwargs["uteslut"], "Iris Lead")


async def test_merinfo_hoppar_over_upptagna_listrader_pa_orgnr():
    """Registrets listrad bär orgnr: ett bolag i kundens CRM fälls även när
    namnet stavas annorlunda, och utan att bolagssidan hämtas (en betald sida)."""
    from app.leads.sources import merinfo

    lista_md = "listsida"
    hamtade: list[str] = []

    async def _hamta(url, *, fas="bolag"):
        hamtade.append(fas)
        return lista_md if fas == "lista" and hamtade.count("lista") == 1 else None

    rader = [
        {"company_name": "Kunden Omdöpt AB", "orgnr": "556111-2222", "url": "https://www.merinfo.se/foretag/a"},
    ]
    with (
        patch.object(merinfo, "hamta", new=_hamta),
        patch.object(merinfo, "tolka_lista", return_value=rader),
        patch.object(merinfo, "valj_branscher", return_value=["bygg"]),
        patch.object(merinfo, "valj_platser", return_value=[None]),
    ):
        ut = await merinfo.sok({"industries": ["bygg"]}, 1, uteslut={"orgnr:5561112222"}, lage="lista")
    assert ut == []
    assert "bolag" not in hamtade


# -- Iris listspår dubblerar inte listorna ------------------------------------


async def test_listsparet_hoppar_over_bolag_som_redan_star_i_en_lista():
    storage = MemoryStorage()
    gammal = await storage.create_lead_list(TENANT, titel="Utan webbplats, Iris igår", icp={}, antal=1)
    await storage.add_lead_list_item(TENANT, list_id=gammal["id"], company_name="Utan Sajt AB")
    k = {"listspar": [
        {"company_name": "Utan Sajt AB", "signal": "listspar", "signal_detalj": "Ingen webbplats"},
        {"company_name": "Ny Utan Sajt AB", "signal": "listspar", "signal_detalj": "Ingen webbplats"},
        {"company_name": "ny utan sajt", "signal": "listspar", "signal_detalj": "Ingen webbplats"},
    ]}
    await _spara_listspar(storage, TENANT, k)
    items = await storage.list_lead_list_items(TENANT, k["listspar_lista"])
    assert [i["company_name"] for i in items] == ["Ny Utan Sajt AB"]


# -- CRM-kundlistan över HTTP -------------------------------------------------


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_crm_import_sparar_kalla_crm_och_slar_ihop_dubbletter():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.post(
                "/api/leads/import",
                headers=DEMO,
                json={
                    "titel": "Befintliga kunder (CRM)",
                    "kalla": "crm",
                    "rader": [
                        {"company_name": "Kund Ett AB", "contact_name": "Anna"},
                        {"company_name": "kund ett", "contact_name": "Bertil"},
                        {"company_name": "Kund Två AB", "orgnr": "556222-3333"},
                        {"company_name": "Två Omdöpt", "orgnr": "5562223333"},
                    ],
                },
            )
            assert svar.status_code == 201, svar.text
            body = svar.json()
            assert body["list"]["kalla"] == "crm"
            assert body["antal"] == 2 and body["hoppade_over"] == 2

            fel = await client.post("/api/leads/import", headers=DEMO, json={"titel": "x", "kalla": "nagot", "rader": [{"company_name": "A"}]})
            assert fel.status_code == 422


async def test_crm_lista_kan_inte_fa_utkast_processas_eller_kombineras(monkeypatch):
    from app.api import leads as leads_api
    from app.api.schemas import KombineraListorRequest, TillIrisRequest

    storage = MemoryStorage()
    crm = await storage.create_lead_list(TENANT, titel="Kunder", icp={}, antal=1, kalla="crm")
    item = await storage.add_lead_list_item(TENANT, list_id=crm["id"], company_name="Kund AB")
    await storage.set_lead_list_status(TENANT, crm["id"], status="klar")
    annan = await storage.create_lead_list(TENANT, titel="Bygg", icp={}, antal=1)
    await storage.add_lead_list_item(TENANT, list_id=annan["id"], company_name="Bygg AB")
    await storage.set_lead_list_status(TENANT, annan["id"], status="klar")

    monkeypatch.setattr(leads_api, "_require_live_llm", lambda: None)
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(storage=storage, jobs=MemoryJobStore())))
    tenant = {"tenant_id": TENANT, "tenant_name": "Snajp"}

    with pytest.raises(HTTPException) as fel:
        await leads_api.skriv_listutkast_for_listan(req, crm["id"], TillIrisRequest(), tenant)
    assert fel.value.status_code == 409
    with pytest.raises(HTTPException) as fel:
        await leads_api.omprova_listan(req, crm["id"], TillIrisRequest(), tenant)
    assert fel.value.status_code == 409
    with pytest.raises(HTTPException) as fel:
        await leads_api.listrad_till_prospekt(req, crm["id"], item["id"], tenant)
    assert fel.value.status_code == 409
    with pytest.raises(HTTPException) as fel:
        await leads_api.kombinera_leadslistor(
            req, KombineraListorRequest(titel="x", list_ids=[crm["id"], annan["id"]]), tenant
        )
    assert fel.value.status_code == 409
    assert await storage.list_prospects(TENANT) == []


async def test_bolag_som_iris_tar_under_listbygget_och_dubbletter_i_listan_skrivs_aldrig():
    """Antons krav 2026-10-06: inga dubbletter ens när Iris och listbygget
    körs samtidigt. Mängden läses om precis före skrivningen."""
    storage = MemoryStorage()
    jobs = MemoryJobStore()
    app_state = SimpleNamespace(storage=storage, jobs=jobs)
    lista = await storage.create_lead_list(TENANT, titel="Ny", icp={}, antal=10)
    job_id = await jobs.create(tenant_id=TENANT, status="queued")
    traffar = [
        {"company_name": "Samtidig AB", "contact_email": "vd@samtidig.se"},
        {"company_name": "Dubbel AB", "contact_email": "vd@dubbel.se"},
        {"company_name": "DUBBEL AB", "contact_email": "info@dubbel.se"},
    ]

    async def sok(*args, **kwargs):
        # Iris skapar samma bolag medan listans sökning pågår.
        await storage.create_prospect(TENANT, company_name="Samtidig AB", origin="iris")
        return traffar

    with (
        patch("app.leads.sources.merinfo.aktiv", return_value=False),
        patch("app.api.leads.hitta_bolag", new=sok),
    ):
        await _run_list_job(app_state, {"job_id": job_id, "tenant_id": TENANT, "list_id": lista["id"]})

    items = await storage.list_lead_list_items(TENANT, lista["id"])
    assert [i["company_name"] for i in items] == ["Dubbel AB"]


async def test_iris_skapar_aldrig_ett_bolag_som_en_lista_tagit_efter_sokrundan():
    from app.api.leads import _fyll_pa
    from app.leads import korning

    storage = MemoryStorage()
    jobs = MemoryJobStore()
    app_state = SimpleNamespace(storage=storage, jobs=jobs)
    lista = await storage.create_lead_list(TENANT, titel="L", icp={}, antal=1)
    await storage.add_lead_list_item(TENANT, list_id=lista["id"], company_name="Listbolaget AB")
    k = korning.ny_korning(mal=1, scope="research", overrides=None, is_test=True)
    k["kandidater"] = [{"company_name": "Listbolaget", "website": "https://listbolaget.se"}]
    k["rundor"] = korning.MAX_RUNDOR
    batch_id = await jobs.create(tenant_id=TENANT, status="processing")
    await jobs.complete(batch_id, {"korning": k})
    tenant = {"tenant_id": TENANT, "tenant_name": "Test"}
    with patch("app.api.leads._las_korning", new=AsyncMock(return_value=({}, k))), \
         patch("app.api.leads.kontrollera_leads_budget", new=AsyncMock()), \
         patch("app.api.leads._spara_korning", new=AsyncMock()), \
         patch("app.api.leads._styrning", new=AsyncMock(return_value=None)), \
         patch("app.api.leads._lagg_prospektjobb", new=AsyncMock(return_value=[])):
        await _fyll_pa(app_state, tenant, batch_id)
    assert not [p for p in await storage.list_prospects(TENANT) if "Listbolaget" in p["company_name"]]
    assert any(t.get("steg") == "dubblett" for t in k["tratt"])
