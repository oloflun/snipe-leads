"""Batchkörningen ska HITTA bolag mot ICP:t, inte plocka gamla rader ur registret."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.api import leads as leads_api
from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}
FEJKAD = "sk-" + "a" * 37


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def live_llm(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("MODEL", "deepseek-v4-flash")
    monkeypatch.setenv("DEEPSEEK_API_KEY", FEJKAD)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_tom_malgrupp_utan_namn_ger_422(live_llm):
    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.post(
                "/api/leads/runs/batch", headers=DEMO, json={"limit": 3, "is_test": True}
            )
            assert svar.status_code == 422
            assert "söker" in svar.json()["detail"]


@pytest.mark.anyio
async def test_batch_hittar_bolag_och_ignorerar_gamla_rader(live_llm, monkeypatch):
    startade: list[str] = []

    async def _spion(state, job_id, tenant, *, prospect_id, scope, overrides, is_test=False):
        startade.append(prospect_id)

    async def _fynd(icp, antal, *, uteslut_namn=None):
        return [
            {
                "company_name": "Hittat Säljbolag AB",
                "website": "https://hittatsalj.se",
                "orgnr": "556824-9022",
                "ort": "Göteborg",
                "contact_email": "info@hittatsalj.se",
                "anstallda": 22,
            }
        ][:antal]

    monkeypatch.setattr(leads_api, "_run_batch_prospect", _spion)
    monkeypatch.setattr(leads_api, "hitta_bolag", _fynd)

    async with app.router.lifespan_context(app):
        storage = app.state.storage
        gammalt = await storage.create_prospect(
            DEFAULT_TENANT_ID, company_name="E2E Verifiering AB", origin="manual"
        )
        async with _client() as client:
            svar = await client.post(
                "/api/leads/runs/batch",
                headers=DEMO,
                json={
                    "limit": 1,
                    "is_test": True,
                    "overrides": {"industries": ["Säljbolag"], "geography": ["Västra Götaland"]},
                },
            )
            assert svar.status_code == 202, svar.text
            jobb = svar.json()["jobs"]
            assert len(jobb) == 1
            assert jobb[0]["prospect_id"] != gammalt["id"]
            nytt = await storage.get_prospect(DEFAULT_TENANT_ID, jobb[0]["prospect_id"])
            assert nytt["company_name"] == "Hittat Säljbolag AB"
            assert nytt["website"] == "https://hittatsalj.se"
            kallor = await storage.list_prospect_source_urls(
                DEFAULT_TENANT_ID, nytt["id"]
            )
            assert "https://hittatsalj.se" in kallor


@pytest.mark.anyio
async def test_egna_namn_blir_den_har_korningens_prospekt(live_llm, monkeypatch):
    async def _spion(state, job_id, tenant, *, prospect_id, scope, overrides, is_test=False):
        return None

    async def _webb(namn, *, geografi=None):
        return "https://acme.se"

    monkeypatch.setattr(leads_api, "_run_batch_prospect", _spion)
    monkeypatch.setattr(leads_api, "sla_upp_webbplats", _webb)

    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.post(
                "/api/leads/runs/batch",
                headers=DEMO,
                json={"limit": 1, "is_test": True, "company_names": ["Acme Verktyg AB"]},
            )
            assert svar.status_code == 202, svar.text
            pid = svar.json()["jobs"][0]["prospect_id"]
            p = await app.state.storage.get_prospect(DEFAULT_TENANT_ID, pid)
            assert p["company_name"] == "Acme Verktyg AB"
            assert p["website"] == "https://acme.se"
            assert p["origin"] == "test"
