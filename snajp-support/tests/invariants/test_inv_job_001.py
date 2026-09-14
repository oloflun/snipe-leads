"""INV-JOB-001 — En chattkörning som avbryts av en omstart fullföljs av
nästa process och lämnar exakt ETT ärende och EN inkommande meddelanderad.

## Buggen den här stänger

POST /api/chat körde agentkedjan som asyncio.create_task i SAMMA process.
Dör processen mitt i körningen (en deploy) hade jobbet ingen väg att komma
vidare: jobbposten blev kvar som "processing" och auto-failades efter 300 s
(app/jobs/store.py, JOB_TIMEOUT_SECONDS) — kunden fick ett fel i stället för
sitt svar, även när ärendet redan hunnit skapas. app/jobs/stream.py
(ChattStrom) gör att en ANNAN process kan ta över körningen via atertag();
det här testet bevisar att övertagandet är IDEMPOTENT — det skapar aldrig
ett andra ärende eller en andra inbound-rad av samma chattmeddelande.

Testet går genom den RIKTIGA hanteraren (app.api.chat.hantera_strom_jobb) —
samma funktion som ChattStrom.worker_loop/atertag anropar i drift — inte en
förenklad genväg. Kraschen sätts i agentkedjan, på steget EFTER
create_ticket+save_message (cs:customer-research, som körs direkt efter
triagen och ärendeskapandet i app/agent/support_agent.py), för att träffa
exakt den kod en riktig produktionskrasch skulle träffa.
"""

from __future__ import annotations

import json
import re
from unittest.mock import AsyncMock, patch

import pytest

from app.api.chat import hantera_strom_jobb
from app.config import get_settings
from app.jobs.store import MemoryJobStore
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"
KUND_EMAIL = "kund@example.com"

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _fake_key(monkeypatch):
    # run_support_agent (den RIKTIGA agentkedjan) krävs — sim_agent har
    # varken aterta eller vid_arende och skulle inte bevisa någonting om
    # INV-JOB-001. Nyckeln är påhittad, klienten mockas nedan — inget
    # nätverksanrop görs (samma mönster som tests/agent/test_support_conversation.py).
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _KraschandeLLM:
    """Kontraktsenliga svar på varje steg UTOM cs:customer-research, som
    kastar så länge `ska_krascha` är sant. Steget ligger direkt efter
    triage/ärendeskapande i support_agent.py, så en krasch där simulerar en
    process som dör efter att ärendet och det inkommande meddelandet redan
    sparats — precis det scenario INV-JOB-001 handlar om."""

    def __init__(self) -> None:
        self.ska_krascha = True
        self.chat = self
        self.completions = self

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        system = messages[0]["content"]
        skill = re.search(r"styrs av skillen (\S+?),", system).group(1)
        if skill == "cs:customer-research" and self.ska_krascha:
            raise RuntimeError("Simulerad processdöd mitt i agentkedjan.")

        payload = {"sources_used": ["kb-1"], "context_refs": ["context_pack"]}
        payload.update(
            {
                "cs:ticket-triage": {
                    "category": "betalning",
                    "priority": "P3",
                    "sentiment": 0.6,
                    "escalate": False,
                },
                "cs:customer-research": {
                    "findings": "KB täcker frågan.",
                    "confidence": 0.8,
                    "kb_supports_answer": True,
                },
                "cs:draft-response": {"draft": "Du kan betala med Swish eller kort."},
                "cs:customer-escalation": {"should_escalate": False, "reason": None},
                "cs:kb-article": {"should_create": False},
                "snajp:humanizer-svenska": {"final_reply": "Du kan betala med Swish eller kort."},
            }.get(skill, {})
        )
        message = type("M", (), {"content": json.dumps(payload, ensure_ascii=False)})()
        usage = type("U", (), {"prompt_tokens": 100, "completion_tokens": 20})()
        return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()


class _AppState:
    pass


async def test_atertagen_korning_ger_exakt_ett_arende_och_en_inbound_rad():
    storage = MemoryStorage()
    jobs = MemoryJobStore()
    app_state = _AppState()
    app_state.storage = storage
    app_state.jobs = jobs

    llm = _KraschandeLLM()
    job_id = await jobs.create(tenant_id=TENANT)
    payload = {
        "job_id": job_id,
        "tenant_id": TENANT,
        "message": "Vilka betalsätt accepterar ni?",
        "subject": "",
        "channel": "web",
        "customer_email": KUND_EMAIL,
        "customer_name": "Test Person",
        "attachments": [],
        "rate_limit_user": None,
        "rate_limit_is_demo": False,
    }

    with (
        patch("app.agent.step_runner.get_llm_client", return_value=llm),
        patch(
            "app.agent.support_agent.classify_cancellation_risk",
            new=AsyncMock(return_value=(0.0, 0.0)),
        ),
    ):
        # --- Första försöket: kraschar EFTER create_ticket+save_message ---
        await hantera_strom_jobb(app_state, payload)

        job = await jobs.get(job_id)
        assert job["status"] == "failed", "kraschen borde ha märkt jobbet failed, inte tyst svalts"
        assert job.get("ticket_id"), "vid_arende hann aldrig annotera jobbet med ticket_id"
        assert job.get("conversation_id"), "vid_arende hann aldrig annotera jobbet med conversation_id"

        # --- Återtag: SAMMA payload, aterta byggs ur jobbposten i hanteraren ---
        llm.ska_krascha = False
        await hantera_strom_jobb(app_state, payload)

    job = await jobs.get(job_id)
    assert job["status"] == "completed"
    assert job["result"]["ticket_id"] == job["ticket_id"], (
        "återupptagningen borde ha återanvänt SAMMA ticket_id, inte skapat ett nytt"
    )

    customer = await storage.find_or_create_customer(
        TENANT, email=KUND_EMAIL, phone=None, name="Test Person"
    )
    history = await storage.get_customer_history(TENANT, customer["id"])
    assert len(history) == 1, f"exakt ETT ärende förväntades, hittade {len(history)}"

    messages = await storage.get_messages(TENANT, job["conversation_id"])
    inbound = [m for m in messages if m["direction"] == "inbound"]
    assert len(inbound) == 1, f"exakt EN inbound-rad förväntades, hittade {len(inbound)}"


async def test_forsta_forsoket_utan_krasch_skapar_bara_ett_arende():
    """Kontrollfall: en normal (icke-krascha) körning ska INTE ta
    återupptagningsvägen — job.get() har inget ticket_id att hitta, så
    aterta förblir None och create_ticket/save_message körs som vanligt,
    en gång."""
    storage = MemoryStorage()
    jobs = MemoryJobStore()
    app_state = _AppState()
    app_state.storage = storage
    app_state.jobs = jobs

    llm = _KraschandeLLM()
    llm.ska_krascha = False
    job_id = await jobs.create(tenant_id=TENANT)
    payload = {
        "job_id": job_id,
        "tenant_id": TENANT,
        "message": "Vilka betalsätt accepterar ni?",
        "subject": "",
        "channel": "web",
        "customer_email": KUND_EMAIL,
        "customer_name": "Test Person",
        "attachments": [],
        "rate_limit_user": None,
        "rate_limit_is_demo": False,
    }

    with (
        patch("app.agent.step_runner.get_llm_client", return_value=llm),
        patch(
            "app.agent.support_agent.classify_cancellation_risk",
            new=AsyncMock(return_value=(0.0, 0.0)),
        ),
    ):
        await hantera_strom_jobb(app_state, payload)

    job = await jobs.get(job_id)
    assert job["status"] == "completed"

    customer = await storage.find_or_create_customer(
        TENANT, email=KUND_EMAIL, phone=None, name="Test Person"
    )
    history = await storage.get_customer_history(TENANT, customer["id"])
    assert len(history) == 1


async def test_redan_fardigt_jobb_kors_inte_om():
    """Completed-vakten: dör processen i fönstret mellan jobs.complete() och
    XACK ligger posten kvar okvitterad fast svaret redan är levererat. Ett
    återtag av den posten får inte köra om agentkedjan — det hade kostat
    sex-sju LLM-anrop, dubblerat det utgående svaret och skrivit en andra
    agent_runs-rad för samma chattmeddelande."""
    storage = MemoryStorage()
    jobs = MemoryJobStore()
    app_state = _AppState()
    app_state.storage = storage
    app_state.jobs = jobs

    llm = _KraschandeLLM()
    llm.ska_krascha = False
    anrop = {"n": 0}
    _riktiga_create = llm.create

    async def raknande_create(**kwargs):
        anrop["n"] += 1
        return await _riktiga_create(**kwargs)

    llm.create = raknande_create

    job_id = await jobs.create(tenant_id=TENANT)
    payload = {
        "job_id": job_id,
        "tenant_id": TENANT,
        "message": "Vilka betalsätt accepterar ni?",
        "subject": "",
        "channel": "web",
        "customer_email": KUND_EMAIL,
        "customer_name": "Test Person",
        "attachments": [],
        "rate_limit_user": None,
        "rate_limit_is_demo": False,
    }

    with (
        patch("app.agent.step_runner.get_llm_client", return_value=llm),
        patch(
            "app.agent.support_agent.classify_cancellation_risk",
            new=AsyncMock(return_value=(0.0, 0.0)),
        ),
    ):
        await hantera_strom_jobb(app_state, payload)
        anrop_efter_forsta = anrop["n"]
        assert anrop_efter_forsta > 0

        # "Återtaget": samma post en gång till, jobbet redan completed.
        await hantera_strom_jobb(app_state, payload)

    assert anrop["n"] == anrop_efter_forsta, (
        "ett redan färdigt jobb körde agentkedjan igen — completed-vakten i "
        "hantera_strom_jobb saknas eller är trasig"
    )
    customer = await storage.find_or_create_customer(
        TENANT, email=KUND_EMAIL, phone=None, name="Test Person"
    )
    history = await storage.get_customer_history(TENANT, customer["id"])
    assert len(history) == 1
