"""Två fynd från kundtestet mot development 2026-09-19.

1. Modellen svarade `draft` som ett OBJEKT. På engelska hoppas humaniseraren
   över, så objektet gick rakt in i strip_markdown -> TypeError, och kunden
   fick ett felmeddelande i stället för ett svar.
2. "Vilka betalsätt har ni?" på svenska hittade inte artikeln
   "Betalningsmetoder vi accepterar" (den svenska stemmern kopplar inte
   betalsät till betalningsmetod), och kunden fick en överlämning på en FAQ.
   Triagens omformulering (sokfraga_sv) söks nu med på svenska också.

Samma fejkmodell som tests/agent/test_support_agent_wiring.py: bara
nätverksgränsen mockas.
"""

from __future__ import annotations

import json
import re
from unittest.mock import AsyncMock, patch

import pytest

from app.agent import support_agent
from app.agent.support_agent import _text, run_support_agent
from app.config import get_settings
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _fejkad_nyckel(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _Fejk:
    def __init__(self, svar: dict):
        self.svar = svar
        self.chat = self
        self.completions = self

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        skill = re.search(r"styrs av skillen (\S+?),", messages[0]["content"]).group(1)
        payload = {"sources_used": ["kb-1"], "context_refs": ["context_pack"], **self.svar.get(skill, {})}
        message = type("M", (), {"content": json.dumps(payload, ensure_ascii=False)})()
        usage = type("U", (), {"prompt_tokens": 10, "completion_tokens": 5})()
        return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()


async def _kor(storage, llm, meddelande):
    with patch("app.agent.step_runner.get_llm_client", return_value=llm), patch(
        "app.agent.support_agent.classify_cancellation_risk", new=AsyncMock(return_value=(0.0, 0.0))
    ):
        return await run_support_agent(
            storage,
            TENANT,
            message=meddelande,
            subject="",
            channel="web",
            customer_email="kund@example.com",
            customer_name="Kim",
            attachments=[],
        )


@pytest.mark.parametrize(
    "varde, vantat",
    [
        ("vanlig text", "vanlig text"),
        ({"text": "i ett objekt"}, "i ett objekt"),
        ({"draft": "under draft"}, "under draft"),
        ({"en": "Short.", "sv": "Den längre svenska texten."}, "Den längre svenska texten."),
        (["Första stycket.", {"text": "Andra stycket."}], "Första stycket.\n\nAndra stycket."),
        (None, ""),
        (42, ""),
    ],
)
def test_text_normaliserar_vad_modellen_an_returnerar(varde, vantat):
    assert _text(varde) == vantat


@pytest.mark.anyio
async def test_draft_som_objekt_pa_engelska_kraschar_inte():
    storage = MemoryStorage()
    llm = _Fejk(
        {
            "cs:ticket-triage": {
                "category": "betalning", "priority": "P3", "sentiment": 0.6, "escalate": False,
                "ber_om_manniska": False, "inom_amnesomradet": True, "missforstadd": False,
                "sprak": "en", "sokfraga_sv": "betalningsmetoder betalsätt",
            },
            "cs:customer-research": {
                "findings": "KB täcker frågan.", "confidence": 0.9,
                "kb_supports_answer": True, "behover_fortydligande": False,
            },
            # Kontraktet säger sträng; modellen gav ett objekt (uppmätt i dev).
            "cs:draft-response": {"draft": {"text": "We accept card, Swish and Klarna.", "language": "en"}},
        }
    )
    resultat = await _kor(storage, llm, "Which payment methods do you accept?")
    assert resultat["reply"] == "We accept card, Swish and Klarna."
    assert "snajp:humanizer-svenska" not in resultat["skills_used"]


@pytest.mark.anyio
async def test_eskaleringsorsak_som_objekt_blir_text():
    storage = MemoryStorage()
    llm = _Fejk(
        {
            "cs:ticket-triage": {
                "category": "betalning", "priority": "P2", "sentiment": 0.2, "escalate": True,
                "ber_om_manniska": False, "inom_amnesomradet": True, "missforstadd": False, "sprak": "sv",
            },
            "cs:customer-research": {"findings": "", "kb_supports_answer": False, "behover_fortydligande": False},
            "cs:draft-response": {"draft": "En kollega tar över."},
            "cs:customer-escalation": {"should_escalate": True, "reason": {"text": "Kunden är missnöjd med en debitering."}},
            "snajp:humanizer-svenska": {"final_reply": "En kollega tar över här i chatten."},
        }
    )
    resultat = await _kor(storage, llm, "Ni har dragit pengar två gånger!")
    assert resultat["escalated"] is True
    assert isinstance(resultat["escalation_reason"], str)


@pytest.mark.anyio
async def test_svensk_fraga_soker_med_triagens_omformulering(monkeypatch):
    sokningar: list[str] = []
    riktig = support_agent._sok_kb

    async def spion(storage, tenant_id, fraga):
        sokningar.append(fraga)
        return await riktig(storage, tenant_id, fraga)

    monkeypatch.setattr(support_agent, "_sok_kb", spion)
    llm = _Fejk(
        {
            "cs:ticket-triage": {
                "category": "betalning", "priority": "P3", "sentiment": 0.6, "escalate": False,
                "ber_om_manniska": False, "inom_amnesomradet": True, "missforstadd": False,
                "sprak": "sv", "sokfraga_sv": "betalningsmetoder betalsätt",
            },
            "cs:customer-research": {"findings": "", "kb_supports_answer": True, "behover_fortydligande": False},
            "cs:draft-response": {"draft": "Kort, Swish och Klarna."},
            "snajp:humanizer-svenska": {"final_reply": "Vi tar kort, Swish och Klarna."},
        }
    )
    await _kor(MemoryStorage(), llm, "Hej! Vilka betalsätt har ni?")
    assert "betalningsmetoder" in sokningar[0]
    assert sokningar[0].startswith("Hej! Vilka betalsätt har ni?")
