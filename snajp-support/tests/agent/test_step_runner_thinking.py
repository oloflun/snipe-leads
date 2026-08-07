"""Per-steg thinking-override (beslut 2026-08-07): ett steg som deklarerar
sin egen thinking-nivå vinner över den globala defaulten i settings."""

import json

import pytest

from app.agentcore.packs import PlaybookStep, RunLedger
from app.agent.step_runner import RunTrace, run_step
from app.config import get_settings


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _deepseek_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    monkeypatch.setenv("THINKING_MODE", "disabled")  # global default för testet
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _RecordingLLM:
    def __init__(self):
        self.received_extra_body = []
        self.chat = self
        self.completions = self

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        self.received_extra_body.append(kwargs.get("extra_body"))
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
    return llm, trace


@pytest.mark.anyio
async def test_step_without_override_uses_global_disabled_default(monkeypatch):
    step = PlaybookStep(skill="cs:ticket-triage", requires=("context_pack",))
    llm, trace = await _run(step, monkeypatch)

    assert llm.received_extra_body[0] == {"thinking": {"type": "disabled"}}
    assert trace.steps[0].thinking_mode == "disabled"


@pytest.mark.anyio
async def test_step_override_enabled_wins_over_global_disabled_default(monkeypatch):
    step = PlaybookStep(
        skill="cs:customer-escalation", requires=("context_pack",), thinking="enabled"
    )
    llm, trace = await _run(step, monkeypatch)

    # thinking PÅ => inget extra_body skickas (se thinking_kwargs)
    assert llm.received_extra_body[0] is None
    assert trace.steps[0].thinking_mode == "enabled"


@pytest.mark.anyio
async def test_step_override_disabled_matches_explicit_global_enabled(monkeypatch):
    monkeypatch.setenv("THINKING_MODE", "enabled")
    get_settings.cache_clear()
    step = PlaybookStep(skill="cs:ticket-triage", requires=("context_pack",), thinking="disabled")
    llm, trace = await _run(step, monkeypatch)

    assert llm.received_extra_body[0] == {"thinking": {"type": "disabled"}}
    assert trace.steps[0].thinking_mode == "disabled"
