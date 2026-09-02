"""Batchkörningen ska HITTA bolag mot ICP:t, inte plocka gamla rader ur registret."""

import asyncio
import time

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


async def _vanta_jobb(client, job_id: str, *, headers=DEMO) -> dict:
    for _ in range(80):
        data = (await client.get(f"/api/jobs/{job_id}", headers=headers)).json()
        if data["status"] in ("completed", "failed"):
            return data
        await asyncio.sleep(0.05)
    raise AssertionError(f"jobb {job_id} blev aldrig klart")


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
async def test_batch_returnerar_innan_sokningen_ar_klar(live_llm, monkeypatch):
    """Regression: Gemini-sökningen i POST-svaret gjorde att proxyn dog efter
    9 s och Safari visade 'Kunde inte nå servern'."""

    async def _langsam(icp, antal, *, uteslut_namn=None):
        await asyncio.sleep(0.4)
        return [
            {
                "company_name": "Långsamt Hittat AB",
                "website": "https://langsamt.se",
                "orgnr": None,
                "ort": "Göteborg",
                "contact_email": "info@langsamt.se",
                "anstallda": 12,
            }
        ][:antal]

    async def _spion(state, job_id, tenant, *, prospect_id, scope, overrides, is_test=False):
        return None

    monkeypatch.setattr(leads_api, "hitta_bolag", _langsam)
    monkeypatch.setattr(leads_api, "_run_batch_prospect", _spion)

    async with app.router.lifespan_context(app):
        async with _client() as client:
            t0 = time.monotonic()
            svar = await client.post(
                "/api/leads/runs/batch",
                headers=DEMO,
                json={
                    "limit": 1,
                    "is_test": True,
                    "overrides": {"industries": ["Bygg"], "geography": ["Göteborg"]},
                },
            )
            elapsed = time.monotonic() - t0
            assert svar.status_code == 202, svar.text
            assert elapsed < 0.25, f"POST väntade på sökningen ({elapsed:.2f}s)"
            kropp = svar.json()
            assert kropp["fase"] == "soker"
            assert len(kropp["jobs"]) == 1
            assert "prospect_id" not in kropp["jobs"][0]

            klart = await _vanta_jobb(client, kropp["jobs"][0]["job_id"])
            assert klart["status"] == "completed", klart
            barn = klart["result"]["jobs"]
            assert len(barn) == 1
            nytt = await app.state.storage.get_prospect(DEFAULT_TENANT_ID, barn[0]["prospect_id"])
            assert nytt["company_name"] == "Långsamt Hittat AB"


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
            assert svar.json()["fase"] == "soker"
            klart = await _vanta_jobb(client, svar.json()["jobs"][0]["job_id"])
            assert klart["status"] == "completed", klart
            jobb = klart["result"]["jobs"]
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
            klart = await _vanta_jobb(client, svar.json()["jobs"][0]["job_id"])
            assert klart["status"] == "completed", klart
            pid = klart["result"]["jobs"][0]["prospect_id"]
            p = await app.state.storage.get_prospect(DEFAULT_TENANT_ID, pid)
            assert p["company_name"] == "Acme Verktyg AB"
            assert p["website"] == "https://acme.se"
            assert p["origin"] == "test"

@pytest.mark.anyio
async def test_scope_sok_stannar_efter_sokningen_och_koar_ingen_research(live_llm, monkeypatch):
    """Snabbsökningen (scope=sok, 2026-09-02): EN sökning, inga researchjobb.

    Kundkravet "kontaktperson vid funnet lead" avgör listan: en träff utan
    någon kontaktväg alls listas inte som färdigt lead utan räknas i
    `utan_kontakt` — raden finns kvar i registret för komplettering."""
    startade: list[str] = []

    async def _spion(state, job_id, tenant, *, prospect_id, scope, overrides, is_test=False):
        startade.append(prospect_id)

    async def _fynd(icp, antal, *, uteslut_namn=None):
        return [
            {
                "company_name": "Snabbfynd AB",
                "website": "https://snabbfynd.se",
                "ort": "Umeå",
                "contact_name": "Eva Ek",
                "contact_role": "VD",
                "contact_email": "eva.ek@snabbfynd.se",
                "contact_level": "named_role_match",
            },
            {
                "company_name": "Kontaktlöst AB",
                "website": "https://kontaktlost.se",
                "ort": "Luleå",
            },
        ][:antal]

    monkeypatch.setattr(leads_api, "_run_batch_prospect", _spion)
    monkeypatch.setattr(leads_api, "hitta_bolag", _fynd)

    async with app.router.lifespan_context(app):
        async with _client() as client:
            svar = await client.post(
                "/api/leads/runs/batch",
                headers=DEMO,
                json={
                    "limit": 2,
                    "is_test": True,
                    "scope": "sok",
                    "overrides": {"industries": ["Snabbfynd"], "geography": ["Norrland"]},
                },
            )
            assert svar.status_code == 202, svar.text
            assert svar.json()["fase"] == "soker"

            klart = await _vanta_jobb(client, svar.json()["jobs"][0]["job_id"])
            assert klart["status"] == "completed", klart
            resultat = klart["result"]
            assert resultat["fase"] == "klar"
            assert resultat["count"] == 1
            assert resultat["utan_kontakt"] == 1
            assert "jobs" not in resultat
            lead = resultat["prospects"][0]
            assert lead["company_name"] == "Snabbfynd AB"
            assert lead["contact_name"] == "Eva Ek"
            assert lead["contact_level"] == "named_role_match"
            assert startade == [], "scope=sok får aldrig köa research"
