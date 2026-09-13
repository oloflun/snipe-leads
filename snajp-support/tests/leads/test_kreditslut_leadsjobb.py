"""Leads-jobben fäller snabbt och ärligt vid kreditslut — och en misslyckad
lista visar inga skräprader.

Testarens fynd 2026-09-13: "leadsjobb fastnar i 'processing' för evigt
(ligger kvar med 3 skräprader)". Här vaktas felvägarna: varje jobbsort blir
failed med KUNDTEXT_KREDITSLUT (aldrig leverantörens råtext) och larmar oss;
utkaststeget sväljer inte längre råtexten i draft_note; ett listbygge som
faller lämnar noll rader; och en beställning utan sökbar målgrupp avvisas
direkt i stället för att bli en "fel"-lista minuter senare.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.api import leads as leads_api
from app.config import DEFAULT_TENANT_ID, get_settings
from app.jobs.store import MemoryJobStore
from app.kvotfel import KUNDTEXT_KREDITSLUT, KUNDTEXT_KVOT
from app.storage.memory import MemoryStorage

pytestmark = pytest.mark.anyio

TENANT = DEFAULT_TENANT_ID

#: AI Studios uppmätta kredittext (2026-09-08) och Vertex motsvarighet.
KREDITTEXT = (
    "Error code: 429 - [{'error': {'code': 429, 'message': 'Your prepayment "
    "credits are depleted. Please go to AI Studio at https://ai.studio/projects "
    "to manage your project and billing.', 'status': 'RESOURCE_EXHAUSTED'}}]"
)
VERTEX_BILLING = (
    "Error code: 403 - [{'error': {'code': 403, 'message': 'This API method "
    "requires billing to be enabled.', 'status': 'PERMISSION_DENIED', 'details': "
    "[{'reason': 'BILLING_DISABLED'}]}}]"
)


class _Kreditfel(Exception):
    status_code = 429

    def __str__(self) -> str:
        return KREDITTEXT


class _Billingfel(Exception):
    status_code = 403

    def __str__(self) -> str:
        return VERTEX_BILLING


class _Leverantorsfel(Exception):
    """Ett icke-kvotfel från leverantören (500) — råtexten får inte läcka."""

    status_code = 500

    def __str__(self) -> str:
        return "Error code: 500 - [{'error': {'message': 'Internal error encountered.'}}]"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def live_llm(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("MODEL", "deepseek-v4-flash")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-" + "a" * 37)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _app_state():
    return SimpleNamespace(storage=MemoryStorage(), jobs=MemoryJobStore(), leadsstrom=None)


@pytest.fixture
def larm():
    with patch("app.api.leads.larma_kreditslut", new=AsyncMock()) as spion:
        yield spion


@pytest.fixture
def utan_kontextpaket(monkeypatch):
    async def falskt(storage, tenant_id, *, overrides=None):
        return "KONTEXT", ()

    monkeypatch.setattr(leads_api, "build_context_pack", falskt)


# -- Per-prospekt-jobbet ----------------------------------------------------


async def test_research_kreditslut_failar_jobbet_med_kredittext(monkeypatch, larm, utan_kontextpaket):
    app_state = _app_state()
    job_id = await app_state.jobs.create(tenant_id=TENANT, status="queued")

    async def research(*_a, **_k):
        raise _Billingfel()

    monkeypatch.setattr(leads_api, "_valj_leads_kedja", lambda: (research, AsyncMock()))
    await leads_api._run_batch_prospect(
        app_state, job_id, {"tenant_id": TENANT, "tenant_name": "Snajp"},
        prospect_id="p-1", scope="research",
    )

    job = await app_state.jobs.get(job_id)
    assert job["status"] == "failed"
    assert job["error"] == KUNDTEXT_KREDITSLUT, "kredittexten ska stå ensam, utan prospekt-id"
    assert (await app_state.storage.get_leads_job_status(TENANT, job_id)) == "failed"
    larm.assert_awaited_once()
    # Aktivregistret släpps — annars skulle städaren aldrig kunna ta jobbet.
    from app.jobs.stadare import aktiva

    assert job_id not in aktiva()


async def test_utkast_kreditslut_larmar_och_ger_kundsaker_anteckning(
    monkeypatch, larm, utan_kontextpaket
):
    """Researchen är klar, utkastet faller på kredit: jobbet blir completed
    (researchen ÄR sparad), men anteckningen bär den ärliga svenska texten —
    inte f"...: {fel}" med Googles JSON — och vi larmas."""
    app_state = _app_state()
    storage = app_state.storage
    prospekt = await storage.create_prospect(
        TENANT, company_name="Nordkap Moduler AB", contact_email="anna@nordkapmoduler.se"
    )
    job_id = await app_state.jobs.create(tenant_id=TENANT, status="queued")

    async def research(*_a, **_k):
        return {"qualified": True}

    async def utkast(*_a, **_k):
        raise _Kreditfel()

    monkeypatch.setattr(leads_api, "_valj_leads_kedja", lambda: (research, utkast))
    monkeypatch.setattr("app.leads.discovery.ar_arbetsmejl", lambda *a, **k: True)
    monkeypatch.setattr(
        "app.leads.business_context.require_business_context",
        AsyncMock(return_value="Vi säljer moduler."),
    )
    await leads_api._run_batch_prospect(
        app_state, job_id, {"tenant_id": TENANT, "tenant_name": "Snajp"},
        prospect_id=prospekt["id"], scope="research_and_draft",
    )

    job = await app_state.jobs.get(job_id)
    assert job["status"] == "completed"
    note = job["result"]["draft_note"]
    assert KUNDTEXT_KREDITSLUT in note
    assert "prepayment" not in note and "Error code" not in note
    larm.assert_awaited_once()


async def test_utkast_ovrigt_leverantorsfel_lacker_ingen_ratext(monkeypatch, larm, utan_kontextpaket):
    app_state = _app_state()
    storage = app_state.storage
    prospekt = await storage.create_prospect(
        TENANT, company_name="Smålands Stålhallar AB", contact_email="per@stalhallar.se"
    )
    job_id = await app_state.jobs.create(tenant_id=TENANT, status="queued")

    async def research(*_a, **_k):
        return {"qualified": True}

    async def utkast(*_a, **_k):
        raise _Leverantorsfel()

    monkeypatch.setattr(leads_api, "_valj_leads_kedja", lambda: (research, utkast))
    monkeypatch.setattr("app.leads.discovery.ar_arbetsmejl", lambda *a, **k: True)
    monkeypatch.setattr(
        "app.leads.business_context.require_business_context",
        AsyncMock(return_value="Vi säljer stålhallar."),
    )
    await leads_api._run_batch_prospect(
        app_state, job_id, {"tenant_id": TENANT, "tenant_name": "Snajp"},
        prospect_id=prospekt["id"], scope="research_and_draft",
    )

    note = (await app_state.jobs.get(job_id))["result"]["draft_note"]
    assert "Error code" not in note and "Internal error" not in note
    assert "Processa om" in note
    larm.assert_not_awaited()


# -- Utkast- och batchjobben ------------------------------------------------


async def test_utkastjobb_leverantorsfel_ger_fast_mening(monkeypatch, larm, utan_kontextpaket):
    app_state = _app_state()
    job_id = await app_state.jobs.create(tenant_id=TENANT, status="queued")

    async def utkast(*_a, **_k):
        raise _Leverantorsfel()

    monkeypatch.setattr(leads_api, "_valj_leads_kedja", lambda: (AsyncMock(), utkast))
    await leads_api._run_draft_job(
        app_state,
        {
            "job_id": job_id, "tenant_id": TENANT, "tenant_name": "Snajp", "thread_id": "t",
            "prospect_email": "a@b.se", "company_name": "X", "offer_summary": "",
            "brief": "",
        },
    )
    job = await app_state.jobs.get(job_id)
    assert job["status"] == "failed"
    assert job["error"] == leads_api._FEL_INTERNT


async def test_utkastjobb_kreditslut_ger_kredittext(monkeypatch, larm, utan_kontextpaket):
    app_state = _app_state()
    job_id = await app_state.jobs.create(tenant_id=TENANT, status="queued")

    async def utkast(*_a, **_k):
        raise _Kreditfel()

    monkeypatch.setattr(leads_api, "_valj_leads_kedja", lambda: (AsyncMock(), utkast))
    await leads_api._run_draft_job(
        app_state,
        {
            "job_id": job_id, "tenant_id": TENANT, "tenant_name": "Snajp", "thread_id": "t",
            "prospect_email": "a@b.se", "company_name": "X", "offer_summary": "",
            "brief": "",
        },
    )
    assert (await app_state.jobs.get(job_id))["error"] == KUNDTEXT_KREDITSLUT
    larm.assert_awaited_once()


async def test_batchsokningens_discoveryfel_med_kreditorsak_ger_kredittext(monkeypatch, larm):
    from app.leads.discovery import DiscoveryError

    app_state = _app_state()
    job_id = await app_state.jobs.create(tenant_id=TENANT, status="queued")

    async def sokning(*_a, **_k):
        try:
            raise _Kreditfel()
        except _Kreditfel as inre:
            raise DiscoveryError("Sokningen avvisades (429).") from inre

    monkeypatch.setattr(leads_api, "_samla_korningens_prospekt", sokning)
    await leads_api._run_batch(
        app_state,
        {"job_id": job_id, "tenant_id": TENANT, "tenant_name": "Snajp", "scope": "sok"},
    )
    job = await app_state.jobs.get(job_id)
    assert job["status"] == "failed"
    assert job["error"] == KUNDTEXT_KREDITSLUT
    larm.assert_awaited_once()


# -- Listjobbet ---------------------------------------------------------------

_TRAFFAR = [
    {"company_name": "Nordkap Moduler AB", "website": "https://nordkapmoduler.se"},
    {"company_name": "Smålands Stålhallar AB", "website": "https://stalhallar.se"},
    {"company_name": "Ett bolag utan sajt AB"},
]


async def _lista_och_jobb(app_state):
    lista = await app_state.storage.create_lead_list(
        TENANT, titel="Tillverkare", icp={"geography": ["Umeå"]}, antal=10
    )
    job_id = await app_state.jobs.create(tenant_id=TENANT, status="queued")
    payload = {
        "kind": "lista", "job_id": job_id, "tenant_id": TENANT, "tenant_name": "Snajp",
        "list_id": lista["id"], "is_test": True,
    }
    return lista, job_id, payload


async def test_listjobb_kreditslut_i_sokningen(larm):
    app_state = _app_state()
    lista, job_id, payload = await _lista_och_jobb(app_state)

    with patch("app.api.leads.hitta_bolag", new=AsyncMock(side_effect=_Billingfel())):
        await leads_api._run_list_job(app_state, payload)

    rad = await app_state.storage.get_lead_list(TENANT, lista["id"])
    assert rad["status"] == "fel"
    assert rad["felorsak"] == KUNDTEXT_KREDITSLUT
    assert (await app_state.jobs.get(job_id))["error"] == KUNDTEXT_KREDITSLUT
    assert (await app_state.storage.get_leads_job_status(TENANT, job_id)) == "failed"
    larm.assert_awaited_once()


async def test_listjobb_som_faller_mitt_i_lamnar_inga_rader(larm):
    """Felet på rad två fick tidigare rad ett att stå kvar i tabellen. Nu
    skrivs raderna först när hela bygget lyckats — och rader från ett äldre,
    avbrutet försök rensas."""
    app_state = _app_state()
    storage = app_state.storage
    lista, job_id, payload = await _lista_och_jobb(app_state)
    # En skräprad från ett tidigare avbrutet försök (så såg testarens lista ut).
    await storage.add_lead_list_item(TENANT, list_id=lista["id"], company_name="Skräp AB")

    anrop = {"n": 0}

    async def skord(webb):
        anrop["n"] += 1
        if anrop["n"] == 2:
            raise RuntimeError("'NoneType' object is not subscriptable")
        return {"contact_email": "info@nordkapmoduler.se", "contact_level": "role_address"}

    with (
        patch("app.api.leads.hitta_bolag", new=AsyncMock(return_value=_TRAFFAR)),
        patch("app.leads.discovery.hamta_kontaktvag", new=skord),
    ):
        await leads_api._run_list_job(app_state, payload)

    rad = await storage.get_lead_list(TENANT, lista["id"])
    assert rad["status"] == "fel"
    assert rad["felorsak"] == leads_api._FEL_LISTBYGGE
    assert "NoneType" not in rad["felorsak"]
    assert await storage.list_lead_list_items(TENANT, lista["id"]) == []
    larm.assert_not_awaited()


async def test_listjobb_svaljer_inte_kreditslut_i_sajtuppslaget(larm):
    """sla_upp_webbplats fick fela tyst per rad — men ett kreditslut där fäller
    varje återstående rad likadant, och listan hade sett klar ut utan kontakter."""
    app_state = _app_state()
    lista, job_id, payload = await _lista_och_jobb(app_state)

    with (
        patch("app.api.leads.hitta_bolag", new=AsyncMock(return_value=_TRAFFAR)),
        patch(
            "app.leads.discovery.hamta_kontaktvag",
            new=AsyncMock(return_value={"contact_email": None, "contact_level": None}),
        ),
        patch("app.leads.discovery.sla_upp_webbplats", new=AsyncMock(side_effect=_Kreditfel())),
    ):
        await leads_api._run_list_job(app_state, payload)

    rad = await app_state.storage.get_lead_list(TENANT, lista["id"])
    assert rad["status"] == "fel"
    assert rad["felorsak"] == KUNDTEXT_KREDITSLUT
    assert await app_state.storage.list_lead_list_items(TENANT, lista["id"]) == []
    larm.assert_awaited_once()


async def test_listjobb_minutkvot_ger_kvottext_utan_larm(larm):
    class _Minutkvot(Exception):
        status_code = 429

    app_state = _app_state()
    lista, _job_id, payload = await _lista_och_jobb(app_state)
    with patch("app.api.leads.hitta_bolag", new=AsyncMock(side_effect=_Minutkvot("quota"))):
        await leads_api._run_list_job(app_state, payload)
    rad = await app_state.storage.get_lead_list(TENANT, lista["id"])
    assert rad["felorsak"] == KUNDTEXT_KVOT
    larm.assert_not_awaited()


# -- Beställningen: målgruppsgrinden efter sammanslagningen -------------------


def _request(app_state):
    return SimpleNamespace(app=SimpleNamespace(state=app_state))


async def test_bestallning_utan_sokbar_malgrupp_avvisas_med_422(live_llm, monkeypatch):
    from app.api.schemas import LeadsListaRequest

    app_state = _app_state()
    monkeypatch.setattr(leads_api, "_run_list_job", AsyncMock())
    with pytest.raises(HTTPException) as fel:
        await leads_api.bestall_leadslista(
            _request(app_state),
            LeadsListaRequest(titel="Något", antal=5),
            {"tenant_id": TENANT, "tenant_name": "Snajp"},
        )
    assert fel.value.status_code == 422
    assert "söka efter" in fel.value.detail
    # Ingen lista skapades, inget jobb köades.
    assert await app_state.storage.list_lead_lists(TENANT) == []


async def test_bestallning_med_overrides_slas_ihop_och_godtas(live_llm, monkeypatch):
    """Formuläret skickar overrides={'must_have': [titel]} — det ska räcka som
    sökbar målgrupp även när den sparade ICP:n är tom, och frysas på listan."""
    from app.api.schemas import LeadsListaRequest

    app_state = _app_state()
    monkeypatch.setattr(leads_api, "_run_list_job", AsyncMock())
    svar = await leads_api.bestall_leadslista(
        _request(app_state),
        LeadsListaRequest(titel="Inköpschefer", antal=5, overrides={"must_have": ["Inköpschef"]}),
        {"tenant_id": TENANT, "tenant_name": "Snajp"},
    )
    assert svar["status"] == "bestalld"
    lista = await app_state.storage.get_lead_list(TENANT, svar["list_id"])
    assert "Inköpschef" in lista["icp"]["must_have"]
