"""Batchkörningen ska föra vidare det den tagit emot — och inte krascha.

Tre fel i samma kodväg, alla tysta på var sitt sätt:

 1. `/api/leads/research/step` anropade `build_context_pack(..., overrides=
    overrides)` med en variabel som aldrig bands i funktionen. NameError, 500,
    på varje anrop med skarp nyckel. Sviten var grön eftersom simuleringsläget
    svarar 503 några rader tidigare — grinden nåddes, buggen aldrig.

 2. `_run_batch_prospect` tog emot `overrides` och skickade dem ingenstans.
    Varje jobb kördes mot den SPARADE ICP:n, medan svaret ekade tillbaka
    överskrivningarna som om de gällt. Utfallet såg rimligt ut; det svarade
    bara på fel fråga.

 3. `is_test` nådde aldrig `agent_runs`. Kolumnen finns sedan migration 036
    och båda lagren tar emot parametern, men ingen anropsplats satte den —
    alltså räknades vårt eget provande som kundvolym i portföljvyn, och
    adminytans text om att testkörningar märks var osann.

Testerna mäter vad som KOM FRAM till nästa lager, inte att parametrarna finns.
"""

import pytest

from app.api import leads as leads_api
from app.config import get_settings

FEJKAD_LIVE_NYCKEL = "sk-" + "a" * 37


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def live_llm(monkeypatch):
    """Samma fixtur som tests/api/test_exempelbolag_api.py, av samma skäl."""
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("MODEL", "deepseek-v4-flash")
    monkeypatch.setenv("DEEPSEEK_API_KEY", FEJKAD_LIVE_NYCKEL)
    get_settings.cache_clear()
    assert not get_settings().is_simulation()
    yield
    get_settings.cache_clear()


class _Jobb:
    """Minsta möjliga jobbregister: bara det _run_batch_prospect rör."""

    def __init__(self):
        self.klart = {}
        self.fel = {}

    async def complete(self, job_id, result):
        self.klart[job_id] = result

    async def fail(self, job_id, message):
        self.fel[job_id] = message


class _Tillstand:
    def __init__(self, storage, jobs):
        self.storage = storage
        self.jobs = jobs


@pytest.fixture
def spion(monkeypatch):
    """Fångar vad research-steget och kontextpaketet faktiskt anropades med."""
    sett = {}

    async def falsk_context_pack(storage, tenant_id, *, overrides=None):
        sett["overrides"] = overrides
        return "KONTEXT", ()

    async def falskt_research_steg(storage, tenant_id, **kwargs):
        sett.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(leads_api, "build_context_pack", falsk_context_pack)
    monkeypatch.setattr(
        "app.agent.leads_agent.run_research_step", falskt_research_steg, raising=False
    )
    return sett


TENANT = {"tenant_id": "t-1", "tenant_name": "Provbolaget"}


@pytest.mark.anyio
async def test_batchen_markerar_testkorningar(spion):
    jobb = _Jobb()
    await leads_api._run_batch_prospect(
        _Tillstand(storage=None, jobs=jobb),
        "job-1",
        TENANT,
        prospect_id="p-1",
        scope="research",
        is_test=True,
    )
    assert not jobb.fel, jobb.fel
    assert spion["is_test"] is True, (
        "is_test nådde inte run_research_step — raden i agent_runs blir default false"
    )


@pytest.mark.anyio
async def test_batchen_utan_flaggan_markerar_inte(spion):
    jobb = _Jobb()
    await leads_api._run_batch_prospect(
        _Tillstand(storage=None, jobs=jobb),
        "job-2",
        TENANT,
        prospect_id="p-1",
        scope="research",
    )
    assert spion["is_test"] is False


@pytest.mark.anyio
async def test_batchen_skickar_vidare_overskrivningarna(spion):
    """Fel 2: parametern togs emot men kastades bort."""
    jobb = _Jobb()
    overskrivningar = {"industries": ["Livsmedel"]}
    await leads_api._run_batch_prospect(
        _Tillstand(storage=None, jobs=jobb),
        "job-3",
        TENANT,
        prospect_id="p-1",
        scope="research",
        overrides=overskrivningar,
    )
    assert spion["overrides"] == overskrivningar, (
        "överskrivningarna nådde inte kontextpaketet — körningen gick mot sparad ICP"
    )


@pytest.mark.anyio
async def test_research_step_har_ingen_obunden_variabel(live_llm, spion, monkeypatch):
    """Fel 1: routen kraschade på NameError innan den hann göra något."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async def falskt_prospekt(tenant_id, prospect_id):
        return {"id": prospect_id, "company_name": "Provbolaget AB"}

    async with app.router.lifespan_context(app):
        monkeypatch.setattr(
            app.state.storage, "get_prospect", falskt_prospekt, raising=False
        )
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            svar = await client.post(
                "/api/leads/research/step",
                headers={"X-API-Key": get_settings().snajp_demo_api_key},
                json={"prospect_id": "p-1", "brief": "prov"},
            )

    assert svar.status_code == 200, svar.text
