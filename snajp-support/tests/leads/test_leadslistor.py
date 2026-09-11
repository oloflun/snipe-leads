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


# -- Listrad → prospekt (bron till Email studio) ----------------------------
#
# Endpointen är LLM-fri: den lyfter en rad in i prospektregistret där
# utkastkedjan, granskningskön och sändvägen redan finns. Testerna vaktar
# tre saker: origin följer listan (send-guardens spärr noll), dedupe mot
# registret (Ur & Penn-dubbletterna, uppmätt 2026-09-06), och proveniensen
# (art. 14: källänken följer med som prospect_source).


class _FakeApp:
    def __init__(self, storage):
        self.state = _AppState()
        self.state.storage = storage


class _FakeRequest:
    def __init__(self, storage):
        self.app = _FakeApp(storage)


async def _lista_med_rad(storage, *, is_test=False, **falt) -> tuple[dict, dict]:
    lista = await storage.create_lead_list(
        TENANT, titel="Bron", icp={}, antal=5, is_test=is_test
    )
    rad = await storage.add_lead_list_item(
        TENANT,
        list_id=lista["id"],
        company_name=falt.pop("company_name", "Nordkap Moduler AB"),
        **{
            "website": "https://nordkapmoduler.se",
            "ort": "Umeå",
            "contact_email": "kundservice@nordkapmoduler.se",
            "contact_level": "role_address",
            "source_name": "jobtech",
            "source_url": "https://arbetsformedlingen.se/annons/1",
            **falt,
        },
    )
    return lista, rad


async def test_listrad_blir_prospekt_med_proveniens():
    from app.api.leads import listrad_till_prospekt

    storage = MemoryStorage()
    lista, rad = await _lista_med_rad(storage)

    svar = await listrad_till_prospekt(
        _FakeRequest(storage), lista["id"], rad["id"], {"tenant_id": TENANT}
    )

    assert svar["skapad"] is True
    p = svar["prospect"]
    assert p["origin"] == "import", "en riktig listas rad ska vara skickbar"
    assert p["contact_email"] == "kundservice@nordkapmoduler.se"
    assert p["website"] == "https://nordkapmoduler.se"
    assert p["ort"] == "Umeå"
    assert p["contact_level"] == "role_address"
    # Art. 14: källänken (annonsen) OCH bolagets egen webb registreras.
    urls = await storage.list_prospect_source_urls(TENANT, p["id"])
    assert "https://arbetsformedlingen.se/annons/1" in urls
    assert "https://nordkapmoduler.se" in urls


async def test_testlistas_rad_far_origin_test():
    from app.api.leads import listrad_till_prospekt

    storage = MemoryStorage()
    lista, rad = await _lista_med_rad(storage, is_test=True)

    svar = await listrad_till_prospekt(
        _FakeRequest(storage), lista["id"], rad["id"], {"tenant_id": TENANT}
    )
    assert svar["prospect"]["origin"] == "test", "spärr noll ska täcka testlistans rader"


async def test_dubbelklick_ateranvander_prospektet():
    from app.api.leads import listrad_till_prospekt

    storage = MemoryStorage()
    lista, rad = await _lista_med_rad(storage)

    första = await listrad_till_prospekt(
        _FakeRequest(storage), lista["id"], rad["id"], {"tenant_id": TENANT}
    )
    andra = await listrad_till_prospekt(
        _FakeRequest(storage), lista["id"], rad["id"], {"tenant_id": TENANT}
    )

    assert andra["skapad"] is False
    assert andra["prospect"]["id"] == första["prospect"]["id"]
    assert len(await storage.list_prospects(TENANT, limit=500)) == 1


async def test_befintligt_prospekt_med_annat_skiftlage_ateranvands():
    from app.api.leads import listrad_till_prospekt

    storage = MemoryStorage()
    befintligt = await storage.create_prospect(TENANT, company_name="NORDKAP MODULER AB")
    lista, rad = await _lista_med_rad(storage)

    svar = await listrad_till_prospekt(
        _FakeRequest(storage), lista["id"], rad["id"], {"tenant_id": TENANT}
    )
    assert svar["skapad"] is False
    assert svar["prospect"]["id"] == befintligt["id"]


async def test_okand_rad_ger_404_inte_500():
    from fastapi import HTTPException

    from app.api.leads import listrad_till_prospekt

    storage = MemoryStorage()
    lista, _ = await _lista_med_rad(storage)

    with pytest.raises(HTTPException) as fel:
        await listrad_till_prospekt(
            _FakeRequest(storage),
            lista["id"],
            "00000000-0000-4000-a000-00000000dead",
            {"tenant_id": TENANT},
        )
    assert fel.value.status_code == 404

    with pytest.raises(HTTPException) as fel:
        await listrad_till_prospekt(
            _FakeRequest(storage), lista["id"], "inte-ett-uuid", {"tenant_id": TENANT}
        )
    assert fel.value.status_code == 404


async def test_rad_fran_annan_tenants_lista_ger_404():
    """Tenantisolering: ett list-id ur en annan kunds arbetsyta ska svara
    404, inte läcka raden. Samma kontrakt som update_customer_contact."""
    from fastapi import HTTPException

    from app.api.leads import listrad_till_prospekt

    storage = MemoryStorage()
    lista, rad = await _lista_med_rad(storage)

    with pytest.raises(HTTPException) as fel:
        await listrad_till_prospekt(
            _FakeRequest(storage),
            lista["id"],
            rad["id"],
            {"tenant_id": "00000000-0000-4000-a000-00000000beef"},
        )
    assert fel.value.status_code == 404


async def test_rad_utan_sajt_far_sajten_uppslagen_och_adressen_skordad():
    """Kundkravet: en kontaktväg per rad. En träff utan sajt ska få sajten
    uppslagen (grounded, EN fråga — bara för rader utan adress) och sedan gå
    genom samma regex-skörd som alla andra. Uppslaget får aldrig fälla
    listan: ett None lämnar raden med streck, inte med fel."""
    storage = MemoryStorage()
    jobs = MemoryJobStore()
    app_state = _AppState()
    app_state.storage = storage
    app_state.jobs = jobs

    lista = await _bestall(storage)
    job_id = await jobs.create(tenant_id=TENANT, status="queued")

    utan_sajt = [{"company_name": "Fjälldata AB", "ort": "Kiruna"}]
    with (
        patch("app.api.leads.hitta_bolag", new=AsyncMock(return_value=utan_sajt)),
        patch(
            "app.leads.discovery.sla_upp_webbplats",
            new=AsyncMock(return_value="https://fjalldata.se"),
        ) as uppslag,
        patch(
            "app.leads.discovery.hamta_kontaktvag",
            new=AsyncMock(
                return_value={"contact_email": "info@fjalldata.se", "contact_level": "role_address"}
            ),
        ),
    ):
        await hantera_leads_jobb(app_state, _payload(job_id, lista["id"]))

    uppslag.assert_awaited_once()
    items = await storage.list_lead_list_items(TENANT, lista["id"])
    assert items[0]["website"] == "https://fjalldata.se"
    assert items[0]["contact_email"] == "info@fjalldata.se"


async def test_misslyckat_sajtuppslag_lamnar_raden_utan_adress_inte_fel():
    storage = MemoryStorage()
    jobs = MemoryJobStore()
    app_state = _AppState()
    app_state.storage = storage
    app_state.jobs = jobs

    lista = await _bestall(storage)
    job_id = await jobs.create(tenant_id=TENANT, status="queued")

    with (
        patch(
            "app.api.leads.hitta_bolag",
            new=AsyncMock(return_value=[{"company_name": "Okänd Industri AB"}]),
        ),
        patch(
            "app.leads.discovery.sla_upp_webbplats",
            new=AsyncMock(side_effect=RuntimeError("kvoten slut")),
        ),
    ):
        await hantera_leads_jobb(app_state, _payload(job_id, lista["id"]))

    rad = await storage.get_lead_list(TENANT, lista["id"])
    assert rad["status"] == "klar", "uppslaget får aldrig fälla listan"
    items = await storage.list_lead_list_items(TENANT, lista["id"])
    assert items[0]["contact_email"] is None
