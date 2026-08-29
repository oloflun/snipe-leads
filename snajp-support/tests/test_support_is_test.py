"""Fas 2.5 (snipe-vxq) + Fas 6.2: supportens is_test-märkning och run_id i svaret.

Adminytans Testkörningar-flik LOVADE i sin egen beskrivning att körningar
märks `is_test` — men ChatRequest saknade fältet och run_support_agent
trådade det aldrig, så varje admintest räknades som kundvolym i
körningsstatistiken (samma felklass som leads-vägen redan stängt, migration
036). run_id-returen är Testchattens förkrav: utan körnings-id går feedback
(POST /api/agent/feedback) inte att koppla till körningen.

Samma mockmönster som tests/invariants/test_inv_job_001.py: den RIKTIGA
agentkedjan med en kontraktstrogen låtsas-LLM, noll nätverksanrop.
"""

from __future__ import annotations

import json
import re
from unittest.mock import AsyncMock, patch

import pytest

from app.agent.support_agent import run_support_agent
from app.config import get_settings
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"

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


class _KontraktsLLM:
    """Kontraktsenliga svar per skill — kopierat mönster från INV-JOB-001-testet."""

    def __init__(self) -> None:
        self.chat = self
        self.completions = self

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        system = messages[0]["content"]
        skill = re.search(r"styrs av skillen (\S+?),", system).group(1)
        payload = {"sources_used": ["kb-1"], "context_refs": ["context_pack"]}
        payload.update(
            {
                "cs:ticket-triage": {
                    "category": "leverans",
                    "priority": "P3",
                    "sentiment": 0.6,
                    "escalate": False,
                },
                "cs:customer-research": {
                    "findings": "KB täcker frågan.",
                    "confidence": 0.8,
                    "kb_supports_answer": True,
                },
                "cs:draft-response": {"draft": "Leveransen tar 2-4 vardagar."},
                "cs:customer-escalation": {"should_escalate": False, "reason": None},
                "cs:kb-article": {"should_create": False},
                "snajp:humanizer-svenska": {"final_reply": "Leveransen tar 2-4 vardagar."},
            }.get(skill, {})
        )
        message = type("M", (), {"content": json.dumps(payload, ensure_ascii=False)})()
        usage = type("U", (), {"prompt_tokens": 100, "completion_tokens": 20})()
        return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()


def _patchar(llm):
    return (
        patch("app.agent.step_runner.get_llm_client", return_value=llm),
        patch(
            "app.agent.support_agent.classify_cancellation_risk",
            new=AsyncMock(return_value=(0.0, 0.0)),
        ),
    )


async def _kor(storage, *, message: str, is_test: bool):
    return await run_support_agent(
        storage,
        TENANT,
        message=message,
        subject="",
        channel="web",
        customer_email="kund@example.com",
        customer_name="Test Person",
        attachments=[],
        is_test=is_test,
    )


async def test_is_test_foljer_med_till_agent_runs():
    storage = MemoryStorage()
    llm = _KontraktsLLM()
    p1, p2 = _patchar(llm)
    with p1, p2:
        result = await _kor(storage, message="Hur lång är leveranstiden?", is_test=True)

    runs = storage.agent_runs.get(TENANT, [])
    assert len(runs) == 1
    assert runs[0]["is_test"] is True
    # Fas 6.2: run_id i svaret, och det är SAMMA körning som loggades.
    assert result.get("run_id") == runs[0]["id"]


async def test_default_ar_inte_test():
    storage = MemoryStorage()
    llm = _KontraktsLLM()
    p1, p2 = _patchar(llm)
    with p1, p2:
        await _kor(storage, message="Hur lång är leveranstiden?", is_test=False)
    assert storage.agent_runs[TENANT][0]["is_test"] is False


async def test_pahopp_tittar_aldrig_i_cachen(monkeypatch):
    """Härdningen av cachegrinden: ett meddelande påhoppsbedömningen flaggat
    (ska_eskalera) får aldrig ens slå upp i svarscachen — eskaleringsvägen är
    beslutad i kod och en cachad FAQ-replik vore fel svar oavsett likhet."""
    monkeypatch.setenv("SEMANTIC_CACHE", "on")
    get_settings.cache_clear()
    storage = MemoryStorage()
    llm = _KontraktsLLM()

    anrop = {"forbered": 0}

    async def spionerande_forbered(*args, **kwargs):  # pragma: no cover - får aldrig köras
        anrop["forbered"] += 1
        raise AssertionError("forbered anropades för ett flaggat påhopp")

    p1, p2 = _patchar(llm)
    with p1, p2, patch("app.agent.support_agent.svarscache.forbered", new=spionerande_forbered):
        # Samma fras som tests/moderation/test_abuse_gate.py bevisar ger
        # ska_eskalera=True.
        await _kor(storage, message="Fuck you.", is_test=False)

    assert anrop["forbered"] == 0
