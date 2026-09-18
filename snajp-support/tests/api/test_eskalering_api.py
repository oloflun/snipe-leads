"""Eskaleringsreglerna i backenden: sparas i leads-konfigurationen och
verkställs före utkastet i batchkörningen.

Kör i minne. Svarshanteringens del prövas i tests/leads/test_svar.py.
"""

from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.jobs.store import MemoryJobStore
from app.leads.eskalering import STANDARD
from app.main import app
from app.storage.memory import MemoryStorage

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}
TENANT = "00000000-0000-4000-a000-000000000001"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_reglerna_sparas_faltvis_och_overlever_andra_formular():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            start = (await client.get("/api/leads/config", headers=DEMO)).json()
            assert start["eskalering"] == STANDARD, "Utan sparat värde gäller standarden."

            svar = await client.put(
                "/api/leads/config",
                headers=DEMO,
                json={"eskalering": {"prisfragor": False, "kvalificeringstroskel": 75}},
            )
            assert svar.status_code == 200, svar.text
            assert svar.json()["eskalering"]["prisfragor"] is False

            # En växel skickar bara sitt fält: det tidigare sparade står kvar.
            await client.put("/api/leads/config", headers=DEMO, json={"eskalering": {"juridik": False}})
            # Autonomiformuläret i huvudappen skickar inte eskalering alls.
            await client.put("/api/leads/config", headers=DEMO, json={"autonomy": "draft"})

            regler = (await client.get("/api/leads/config", headers=DEMO)).json()["eskalering"]
            assert regler["prisfragor"] is False
            assert regler["juridik"] is False
            assert regler["kvalificeringstroskel"] == 75
            assert regler["negativt_svar"] is True


@pytest.mark.anyio
async def test_ogiltiga_varden_avvisas():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            for kropp in (
                {"eskalering": {"kvalificeringstroskel": 101}},
                {"eskalering": {"okant_falt": True}},
            ):
                svar = await client.put("/api/leads/config", headers=DEMO, json=kropp)
                assert svar.status_code == 422, (kropp, svar.text)


async def _kor_batch(monkeypatch, *, regler: dict | None, icp_fit: float) -> tuple[dict, list]:
    from app.api import leads as leads_api

    storage = MemoryStorage()
    if regler is not None:
        await storage.set_agent_settings(TENANT, agent_type="leads", settings={"eskalering": regler})
    prospekt = await storage.create_prospect(
        TENANT, company_name="Tröskel AB", contact_email="anna@troskel.se"
    )
    utkast: list = []

    async def _research(*args, **kwargs):
        return {"qualified": True, "icp_fit": icp_fit, "stopped_early": None}

    async def _utkast(*args, **kwargs):
        utkast.append(kwargs)
        return {"queued": True}

    monkeypatch.setattr(leads_api, "_valj_leads_kedja", lambda: (_research, _utkast))
    jobs = MemoryJobStore()
    job_id = await jobs.create(tenant_id=TENANT)
    await leads_api._run_batch_prospect(
        SimpleNamespace(storage=storage, jobs=jobs),
        job_id,
        {"tenant_id": TENANT, "tenant_name": "Snajp"},
        prospect_id=prospekt["id"],
        scope="research_and_draft",
    )
    jobb = await jobs.get(job_id)
    return (jobb or {}).get("result") or {}, utkast


@pytest.mark.anyio
async def test_bolag_under_troskeln_far_inget_automatiskt_utkast(monkeypatch):
    resultat, utkast = await _kor_batch(monkeypatch, regler={"kvalificeringstroskel": 60}, icp_fit=0.45)
    assert resultat.get("stopped_early") == "under_troskel", resultat
    assert "60 procent" in resultat.get("draft_note", "")
    assert utkast == [], "Ett utkast skrevs trots att bolaget låg under tröskeln."


@pytest.mark.anyio
async def test_avstangd_troskelregel_stoppar_inget(monkeypatch):
    resultat, _ = await _kor_batch(
        monkeypatch, regler={"osaker_kvalificering": False}, icp_fit=0.45
    )
    assert resultat.get("stopped_early") is None, resultat
