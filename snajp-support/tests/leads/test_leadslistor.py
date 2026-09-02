"""Leadslistor (tillägget 'leadlists', migration 060): volymkörningen som
bygger granskningsbara listor via discovery-federationen — utan utkast och
utan sändning (INV-SEC-004)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.api.leads import _run_list_job, hantera_leads_jobb
from app.jobs.store import MemoryJobStore
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _AppState:
    pass


_TRAFFAR = [
    {
        "company_name": "Nordkap Moduler AB",
        "website": "https://nordkapmoduler.se",
        "ort": "Umeå",
        "contact_name": None,
        "contact_role": None,
        "contact_email": "kundservice@nordkapmoduler.se",
        "contact_level": "role_address",
        "source_name": "jobtech",
        "source_url": "https://arbetsformedlingen.se/annons/1",
        "signal": "rekryterar",
        "signal_detalj": "Kundtjänstmedarbetare",
    },
    {
        "company_name": "Smålands Stålhallar AB",
        "website": "https://smalandsstalhallar.se",
        "ort": "Värnamo",
        "contact_email": None,
        "contact_level": None,
    },
]


async def _bestall(storage) -> dict:
    return await storage.create_lead_list(
        TENANT, titel="Tillverkare Norrland", icp={"geography": "Umeå"}, antal=25
    )


def _payload(job_id: str, list_id: str) -> dict:
    return {
        "kind": "lista",
        "job_id": job_id,
        "tenant_id": TENANT,
        "tenant_name": "Snajp",
        "list_id": list_id,
        "is_test": True,
    }


async def test_listjobbet_bygger_items_och_markerar_klar():
    storage = MemoryStorage()
    jobs = MemoryJobStore()
    app_state = _AppState()
    app_state.storage = storage
    app_state.jobs = jobs

    lista = await _bestall(storage)
    job_id = await jobs.create(tenant_id=TENANT, status="queued")

    with (
        patch("app.api.leads.hitta_bolag", new=AsyncMock(return_value=_TRAFFAR)) as sok,
        patch(
            "app.leads.discovery.hamta_kontaktvag",
            new=AsyncMock(
                return_value={
                    "contact_email": "info@smalandsstalhallar.se",
                    "contact_level": "role_address",
                }
            ),
        ) as skord,
    ):
        await hantera_leads_jobb(app_state, _payload(job_id, lista["id"]))

    sok.assert_awaited_once()
    # ICP:t som frystes vid beställningen är det som söks — inte dagens.
    assert sok.await_args.args[0] == {"geography": "Umeå"}

    rad = await storage.get_lead_list(TENANT, lista["id"])
    assert rad["status"] == "klar"
    items = await storage.list_lead_list_items(TENANT, lista["id"])
    assert [i["company_name"] for i in items] == [
        "Nordkap Moduler AB",
        "Smålands Stålhallar AB",
    ]
    assert items[0]["item_typ"] == "bolag"
    assert items[0]["source_url"] == "https://arbetsformedlingen.se/annons/1"
    # Kontaktskörden körs BARA för raden utan adress — träff 1 hade redan en.
    skord.assert_awaited_once_with("https://smalandsstalhallar.se")
    assert items[1]["contact_email"] == "info@smalandsstalhallar.se"
    assert items[1]["contact_level"] == "role_address"
    job = await jobs.get(job_id)
    assert job["status"] == "completed"
    assert (await storage.get_leads_job_status(TENANT, job_id)) == "completed"


async def test_atertag_av_klar_lista_dubblerar_inte_raderna():
    storage = MemoryStorage()
    jobs = MemoryJobStore()
    app_state = _AppState()
    app_state.storage = storage
    app_state.jobs = jobs

    lista = await _bestall(storage)
    job_id = await jobs.create(tenant_id=TENANT, status="queued")
    payload = _payload(job_id, lista["id"])

    with (
        patch("app.api.leads.hitta_bolag", new=AsyncMock(return_value=_TRAFFAR)) as sok,
        patch(
            "app.leads.discovery.hamta_kontaktvag",
            new=AsyncMock(return_value={"contact_email": None, "contact_level": None}),
        ),
    ):
        await hantera_leads_jobb(app_state, payload)
        # "Återtaget": samma post igen — liggaren säger completed, ingen sökning.
        await hantera_leads_jobb(app_state, payload)

    assert sok.await_count == 1
    assert len(await storage.list_lead_list_items(TENANT, lista["id"])) == 2


async def test_fallen_sokning_markerar_listan_fel():
    from app.leads.discovery import DiscoveryError

    storage = MemoryStorage()
    jobs = MemoryJobStore()
    app_state = _AppState()
    app_state.storage = storage
    app_state.jobs = jobs

    lista = await _bestall(storage)
    job_id = await jobs.create(tenant_id=TENANT, status="queued")

    with patch("app.api.leads.hitta_bolag", new=AsyncMock(side_effect=DiscoveryError("nere"))):
        await _run_list_job(app_state, _payload(job_id, lista["id"]))

    rad = await storage.get_lead_list(TENANT, lista["id"])
    assert rad["status"] == "fel"
    assert rad["felorsak"]
    assert (await jobs.get(job_id))["status"] == "failed"


async def test_lead_list_status_speglar_checken():
    storage = MemoryStorage()
    lista = await _bestall(storage)
    with pytest.raises(ValueError):
        await storage.set_lead_list_status(TENANT, lista["id"], status="påhittad")
    with pytest.raises(ValueError):
        await storage.add_lead_list_item(
            TENANT, list_id=lista["id"], company_name="X", item_typ="utomjording"
        )
    with pytest.raises(ValueError):
        await storage.create_lead_list(TENANT, titel="För stor", icp={}, antal=500)


async def test_endpoints_over_http(monkeypatch):
    """Hela vägen genom FastAPI-lagret — beställ, lista, hämta. Fanns inte
    från början, och exakt det testet hade fångat `kraev_uuid(list_id)` utan
    sitt andra argument: enhetstesterna anropade jobbfunktionen direkt och
    endpointen small först i pixelgranskningen mot dev (2026-09-02)."""
    from httpx import ASGITransport, AsyncClient

    from app.config import get_settings
    from app.main import app

    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()

    with (
        patch("app.api.leads.hitta_bolag", new=AsyncMock(return_value=_TRAFFAR)),
        patch(
            "app.leads.discovery.hamta_kontaktvag",
            new=AsyncMock(return_value={"contact_email": None, "contact_level": None}),
        ),
    ):
        async with app.router.lifespan_context(app):
            demo_key = get_settings().snajp_demo_api_key
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                svar = await client.post(
                    "/api/leads/listor",
                    headers={"X-API-Key": demo_key},
                    json={"titel": "HTTP-testet", "antal": 5, "is_test": True},
                )
                assert svar.status_code == 202, svar.text
                list_id = svar.json()["list_id"]

                # create_task-vägen (ingen Redis i sviten) — vänta in jobbet.
                import asyncio as _asyncio

                for _ in range(50):
                    lista = (
                        await client.get(
                            f"/api/leads/listor/{list_id}", headers={"X-API-Key": demo_key}
                        )
                    ).json()
                    if lista["list"]["status"] in ("klar", "fel"):
                        break
                    await _asyncio.sleep(0.05)
                assert lista["list"]["status"] == "klar", lista
                assert len(lista["items"]) == 2

                alla = (
                    await client.get("/api/leads/listor", headers={"X-API-Key": demo_key})
                ).json()
                assert any(l["id"] == list_id for l in alla["lists"])

                # Felformat id ska ge 404, aldrig 500 (kraev_uuid-kontraktet).
                fel = await client.get(
                    "/api/leads/listor/inte-ett-uuid", headers={"X-API-Key": demo_key}
                )
                assert fel.status_code == 404, fel.text
    get_settings.cache_clear()


async def test_item_count_i_listvyn():
    storage = MemoryStorage()
    lista = await _bestall(storage)
    await storage.add_lead_list_item(TENANT, list_id=lista["id"], company_name="A")
    await storage.add_lead_list_item(TENANT, list_id=lista["id"], company_name="B")
    rader = await storage.list_lead_lists(TENANT)
    assert rader[0]["item_count"] == 2
