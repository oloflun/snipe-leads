"""Chatten säger vad agenten gör medan kunden väntar (fas 2, 2026-11-10).

Ett svar är fyra till fem modellanrop i följd och tar omkring tio sekunder.
Under den tiden stod "Agenten arbetar" stilla. Jobbet bär nu vilket skede
agenten är i, och chattfönstret visar det.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.agent.step_runner import RunTrace, run_step
from app.agent.support_agent import run_support_agent
from app.agentcore.packs import PlaybookStep, RunLedger
from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app
from app.storage.memory import MemoryStorage
from tests.agent.test_support_agent_wiring import EXPECTED_ORDER_NORMAL, TENANT, _FakeLLM

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _fake_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _LLM:
    def __init__(self, fore_svar=None):
        self.fore_svar = fore_svar
        self.chat = self
        self.completions = self

    async def create(self, **_k):
        if self.fore_svar:
            self.fore_svar()
        message = type("M", (), {"content": json.dumps({"sources_used": [], "context_refs": []})})()
        usage = type("U", (), {"prompt_tokens": 10, "completion_tokens": 5})()
        return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()


async def _ett_steg(trace: RunTrace, llm: _LLM) -> None:
    with patch("app.agent.step_runner.get_llm_client", return_value=llm):
        steg = PlaybookStep(skill="cs:ticket-triage", requires=("context_pack",))
        await run_step(steg, RunLedger(satisfied={"context_pack"}), trace, task="t", case_context="c")


async def test_steget_meddelar_sig_fore_modellanropet():
    handelser: list[str] = []

    async def _vid_steg(skill: str) -> None:
        handelser.append(f"börjar:{skill}")

    await _ett_steg(RunTrace(vid_steg=_vid_steg), _LLM(fore_svar=lambda: handelser.append("modellen")))

    assert handelser == ["börjar:cs:ticket-triage", "modellen"]


async def test_ett_fel_i_meddelandet_faller_inte_steget():
    async def _trasig(_skill: str) -> None:
        raise ConnectionError("Redis svarade inte")

    trace = RunTrace(vid_steg=_trasig)
    await _ett_steg(trace, _LLM())

    assert trace.skills_used == ["cs:ticket-triage"]


async def test_supportagenten_meddelar_varje_steg_i_ordning():
    sedda: list[str] = []

    async def _forlopp(skill: str) -> None:
        sedda.append(skill)

    with patch("app.agent.step_runner.get_llm_client", return_value=_FakeLLM()), patch(
        "app.agent.support_agent.classify_cancellation_risk", new=AsyncMock(return_value=(0.0, 0.0))
    ):
        await run_support_agent(
            MemoryStorage(), TENANT, message="Vilka betalsätt accepterar ni?", subject="", channel="web",
            customer_email="kund@example.com", customer_name="Test Person", attachments=[], forlopp=_forlopp,
        )

    assert sedda == EXPECTED_ORDER_NORMAL


@pytest.mark.parametrize(
    ("steg", "fas"),
    [
        ("cs:ticket-triage", "laser"),
        ("cs:customer-research", "soker"),
        ("cs:draft-response", "skriver"),
        ("snajp:humanizer-svenska", "skriver"),
        ("cs:customer-escalation", "kontrollerar"),
        ("okant:steg", "arbetar"),
    ],
)
async def test_jobbsvaret_bar_skedet_inte_stegets_namn(steg, fas):
    """Stegens namn är interna; chattfönstret får ett av fyra skeden."""
    async with app.router.lifespan_context(app):
        job_id = await app.state.jobs.create(tenant_id=DEFAULT_TENANT_ID)
        await app.state.jobs.annotate(job_id, steg=steg)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as klient:
            svar = await klient.get(f"/api/jobs/{job_id}", headers={"X-API-Key": get_settings().snajp_demo_api_key})

    kropp = svar.json()
    assert kropp["status"] == "processing" and kropp["fas"] == fas
    assert steg not in svar.text


async def test_ett_jobb_utan_skede_saknar_faltet():
    async with app.router.lifespan_context(app):
        job_id = await app.state.jobs.create(tenant_id=DEFAULT_TENANT_ID)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as klient:
            svar = await klient.get(f"/api/jobs/{job_id}", headers={"X-API-Key": get_settings().snajp_demo_api_key})

    assert "fas" not in svar.json()
