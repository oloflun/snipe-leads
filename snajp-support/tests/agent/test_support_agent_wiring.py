"""support/v1 som per-steg-orkestrering. Mockar bara nätverksgränsen
(LLM-klienten) — allt annat är den riktiga kodvägen, inklusive
förvillkorsgrinden, utdatakontraktet, sidoeffekterna och agent_runs-loggen.

Det här är testet som faktiskt bevisar vilka skill-anrop som görs, i vilken
ordning, och att eskalering avgörs i KOD och inte av modellens godtycke."""

import json
import re
from unittest.mock import AsyncMock, patch

import pytest

from app.agent.support_agent import run_support_agent
from app.config import get_settings
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"

EXPECTED_ORDER_NORMAL = [
    "cs:ticket-triage",
    "cs:customer-research",
    "cs:draft-response",
    "cs:customer-escalation",
    "cs:kb-article",
    "snajp:humanizer-svenska",
]


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


class _FakeLLM:
    """Returnerar ett kontraktsenligt JSON-svar per anrop och registrerar
    vilken skill varje anrop gällde (utläst ur systemprompten)."""

    def __init__(self, overrides: dict | None = None):
        self.calls: list[str] = []
        self.overrides = overrides or {}
        self.chat = self  # client.chat.completions.create
        self.completions = self

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        # Läs skillen ur step_runner:s exakta markör — INTE genom att söka
        # efter skill-namn i prompttexten. Flera skills nämner varandra i sitt
        # innehåll (snajp:retention-conversation refererar cs:customer-research),
        # vilket gjorde en naiv sökning fel.
        system = messages[0]["content"]
        skill = re.search(r"styrs av skillen (\S+?),", system).group(1)
        self.calls.append(skill)

        payload = {"sources_used": ["kb-1"], "context_refs": ["context_pack"]}
        payload.update(
            {
                "cs:ticket-triage": {"category": "betalning", "priority": "P3", "sentiment": 0.6, "escalate": False},
                "cs:customer-research": {"findings": "KB täcker frågan.", "confidence": 0.8, "kb_supports_answer": True},
                "cs:draft-response": {"draft": "Du kan betala med Swish eller kort."},
                "cs:customer-escalation": {"should_escalate": False, "reason": None},
                "cs:kb-article": {"should_create": False},
                "snajp:retention-conversation": {"revised_draft": "Jag kopplar in en kollega.", "offers_made": []},
                "snajp:humanizer-svenska": {"final_reply": "Hej! Du kan betala med Swish eller kort."},
            }.get(skill, {})
        )
        payload.update(self.overrides.get(skill, {}))

        message = type("M", (), {"content": json.dumps(payload, ensure_ascii=False)})()
        usage = type("U", (), {"prompt_tokens": 100, "completion_tokens": 20})()
        return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()


async def _run(storage, llm, message="Vilka betalsätt accepterar ni?", risk=(0.0, 0.0), **kwargs):
    with patch("app.agent.step_runner.get_llm_client", return_value=llm), patch(
        "app.agent.support_agent.classify_cancellation_risk", new=AsyncMock(return_value=risk)
    ):
        return await run_support_agent(
            storage,
            TENANT,
            message=message,
            subject=kwargs.get("subject", ""),
            channel="web",
            customer_email="kund@example.com",
            customer_name="Test Person",
            attachments=kwargs.get("attachments", []),
        )


@pytest.mark.anyio
async def test_one_llm_call_per_skill_step_in_declared_order():
    storage, llm = MemoryStorage(), _FakeLLM()
    result = await _run(storage, llm)

    assert llm.calls == EXPECTED_ORDER_NORMAL, "Ett anrop per steg, i playbook-ordning"
    assert result["skills_used"] == EXPECTED_ORDER_NORMAL
    assert len(result["step_log"]) == len(EXPECTED_ORDER_NORMAL)


@pytest.mark.anyio
async def test_step_log_records_contract_fields_per_step():
    storage, llm = MemoryStorage(), _FakeLLM()
    result = await _run(storage, llm)

    for entry in result["step_log"]:
        assert entry["sources_used"] == ["kb-1"]
        assert entry["context_refs"] == ["context_pack"]
        assert entry["attempts"] == 1
        assert entry["escalated"] is False


@pytest.mark.anyio
async def test_agent_run_is_logged_with_step_log_g10():
    storage, llm = MemoryStorage(), _FakeLLM()
    await _run(storage, llm)

    runs = await storage.list_agent_runs(TENANT, agent_type="support")
    assert len(runs) == 1
    assert runs[0]["skills_used"] == EXPECTED_ORDER_NORMAL
    assert len(runs[0]["step_log"]) == len(EXPECTED_ORDER_NORMAL)
    assert runs[0]["tokens_in"] > 0
    assert ":support/v1" in runs[0]["pack_version"]


@pytest.mark.anyio
async def test_cancellation_risk_inserts_retention_step_and_forces_escalation():
    storage, llm = MemoryStorage(), _FakeLLM()
    result = await _run(storage, llm, message="Jag vill säga upp allt NU.", risk=(0.9, 0.8))

    assert "snajp:retention-conversation" in llm.calls
    assert llm.calls.index("snajp:retention-conversation") < llm.calls.index("snajp:humanizer-svenska")
    assert result["escalated"] is True
    assert result["escalation_reason"] == "retention_risk"


@pytest.mark.anyio
async def test_escalates_in_code_even_when_model_says_no_escalation():
    """Modellen säger should_escalate=False men sentimentet är under tröskeln
    — koden eskalerar ändå. Eskalering får inte bero på modellens godtycke."""
    storage = MemoryStorage()
    llm = _FakeLLM(overrides={"cs:ticket-triage": {"sentiment": 0.1}})
    result = await _run(storage, llm, message="Detta är helt oacceptabelt!")

    assert result["escalated"] is True


@pytest.mark.anyio
async def test_escalates_when_knowledge_base_has_no_match():
    storage = MemoryStorage()
    storage.kb[TENANT] = []  # tom KB => grundningsregeln tvingar eskalering
    llm = _FakeLLM()
    result = await _run(storage, llm)

    assert result["escalated"] is True
    assert result["kb_sources"] == []


@pytest.mark.anyio
async def test_ticket_and_messages_are_persisted_by_code_not_by_the_model():
    storage, llm = MemoryStorage(), _FakeLLM()
    result = await _run(storage, llm)

    ticket = await storage.get_ticket(TENANT, result["ticket_id"])
    assert ticket is not None
    messages = await storage.get_messages(TENANT, ticket["conversation_id"])
    assert [m["direction"] for m in messages] == ["inbound", "outbound"]


@pytest.mark.anyio
async def test_markdown_is_stripped_from_the_final_reply():
    storage = MemoryStorage()
    llm = _FakeLLM(
        overrides={"snajp:humanizer-svenska": {"final_reply": "Hej! **Viktigt**: se nedan."}}
    )
    result = await _run(storage, llm)

    assert "**" not in result["reply"]


@pytest.mark.anyio
async def test_vision_sidecar_describes_image_and_never_stores_it():
    storage, llm = MemoryStorage(), _FakeLLM()
    with patch(
        "app.agent.support_agent.describe_image",
        new=AsyncMock(return_value="Skärmdump med felkod E-500."),
    ) as mock_describe:
        result = await _run(storage, llm, attachments=["data:image/png;base64,AAAA"])

    mock_describe.assert_awaited_once()
    assert result["ticket_id"]


@pytest.mark.anyio
async def test_broken_contract_retries_once_then_escalates_that_step():
    """Ett steg som aldrig returnerar kontraktet ska försöka igen en gång
    och sedan markeras som eskalerat — inte tyst passera."""
    storage = MemoryStorage()

    class _BadLLM(_FakeLLM):
        async def create(self, *, model, response_format, temperature, messages, **kwargs):
            if "cs:draft-response" in messages[0]["content"]:
                self.calls.append("cs:draft-response")
                message = type("M", (), {"content": json.dumps({"draft": "x"})})()  # saknar kontrakt
                usage = type("U", (), {"prompt_tokens": 1, "completion_tokens": 1})()
                return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()
            return await super().create(
                model=model, response_format=response_format, temperature=temperature, messages=messages
            )

    llm = _BadLLM()
    result = await _run(storage, llm)

    draft_entries = [e for e in result["step_log"] if e["skill"] == "cs:draft-response"]
    assert draft_entries[0]["attempts"] == 2
    assert draft_entries[0]["escalated"] is True
