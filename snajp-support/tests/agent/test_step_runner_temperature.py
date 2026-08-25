"""Per-steg temperatur (beslut 2026-08-25): formuleringssteg (humanizer,
utkast) deklarerar en varmare temperatur i playbooken; steg utan deklaration
ärver den kalla defaulten 0.3. Samma mönster som thinking-overriden."""

import json

import pytest

from app.agent.step_runner import RunTrace, run_step
from app.agent.support_playbook import SUPPORT_V1
from app.agentcore.packs import PlaybookStep, RunLedger
from app.config import get_settings


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _llm_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _RecordingLLM:
    def __init__(self):
        self.received_temperature = []
        self.chat = self
        self.completions = self

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        self.received_temperature.append(temperature)
        payload = {"sources_used": [], "context_refs": []}
        message = type("M", (), {"content": json.dumps(payload)})()
        usage = type("U", (), {"prompt_tokens": 10, "completion_tokens": 5})()
        return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()


async def _run(step, monkeypatch):
    llm = _RecordingLLM()
    monkeypatch.setattr("app.agent.step_runner.get_llm_client", lambda: llm)
    ledger = RunLedger(satisfied={"context_pack"})
    trace = RunTrace()
    await run_step(step, ledger, trace, task="test", case_context="test")
    return llm


@pytest.mark.anyio
async def test_steg_utan_deklaration_kor_kall_default(monkeypatch):
    step = PlaybookStep(skill="cs:ticket-triage", requires=("context_pack",))
    llm = await _run(step, monkeypatch)

    assert llm.received_temperature[0] == 0.3


@pytest.mark.anyio
async def test_steg_med_deklaration_vinner_over_defaulten(monkeypatch):
    step = PlaybookStep(
        skill="snajp:humanizer-svenska", requires=("context_pack",), temperature=0.7
    )
    llm = await _run(step, monkeypatch)

    assert llm.received_temperature[0] == 0.7


def test_playbooken_varmer_formuleringsstegen_och_inget_annat():
    """Bedömningsstegen (triage, research, eskalering, kb-artikel) ska förbli
    kalla — det är bara stegen vars uppgift ÄR text som får variera."""
    per_skill = {step.skill: step.temperature for step in SUPPORT_V1.steps}

    assert per_skill["cs:draft-response"] == 0.5
    assert per_skill["snajp:humanizer-svenska"] == 0.7
    assert per_skill["cs:ticket-triage"] is None
    assert per_skill["cs:customer-research"] is None
    assert per_skill["cs:customer-escalation"] is None
    assert per_skill["cs:kb-article"] is None
