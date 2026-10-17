"""Arbetsytans siffror i hjälpchatten (2026-10-05): blocket byggs bara med
`arbetsyta`-flaggan, bär nyckeltalen, och siffrorna överlever faktagrinden
eftersom blocket ingår i grindens källor."""

import pytest

from app.agent.arbetsyta_siffror import bygg_sifferblock
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_sifferblocket_bar_veckor_och_granskningsko():
    storage = MemoryStorage()
    block = await bygg_sifferblock(storage, TENANT)
    assert block.startswith("## Arbetsytans siffror")
    assert "Utkast som väntar på granskning" in block
    # Instruktionen som hindrar extrapolering ska stå kvar.
    assert "extrapolera inte" in block


@pytest.mark.anyio
async def test_sifferblocket_ar_fail_open():
    """En trasig källa får aldrig fälla chatten — blocket byggs utan den."""

    class TrasigStorage(MemoryStorage):
        async def weekly_analytics(self, tenant_id, *, weeks=8):
            raise RuntimeError("databasen ligger nere")

        async def list_review_queue(self, tenant_id, limit=100):
            raise RuntimeError("databasen ligger nere")

        async def get_tenant(self, tenant_id):
            raise RuntimeError("databasen ligger nere")

    block = await bygg_sifferblock(TrasigStorage(), TENANT)
    assert block == ""


@pytest.mark.anyio
async def test_utan_flaggan_byggs_inget_sifferblock():
    """Gatingens backend-halva: run_support_agent bygger blocket BARA när
    `arbetsyta=True` — den publika chatten får aldrig nyckeltalen i
    prompten, oavsett vad en klient skickar till Next-routen (som dessutom
    strippar fältet)."""
    from tests.agent.test_support_eskalering import _LLM, _tur

    storage = MemoryStorage()
    llm = _LLM()
    await _tur(storage, llm, "Vilka betalsätt tar ni?")
    allt = "\n".join(llm.user_by_skill.get("cs:ticket-triage", []))
    assert "Arbetsytans siffror" not in allt


@pytest.mark.anyio
async def test_med_flaggan_ligger_siffrorna_i_kontexten_och_i_faktagrinden():
    from unittest.mock import AsyncMock, patch

    from tests.agent.test_support_eskalering import _LLM

    storage = MemoryStorage()
    llm = _LLM()
    with (
        patch("app.agent.step_runner.get_llm_client", return_value=llm),
        patch(
            "app.agent.support_agent.classify_cancellation_risk",
            new=AsyncMock(return_value=(0.0, 0.0)),
        ),
    ):
        from app.agent.support_agent import run_support_agent

        svar = await run_support_agent(
            storage,
            TENANT,
            message="Hur många ärenden fick vi den här veckan?",
            subject="",
            channel="web",
            customer_email="agare@example.se",
            customer_name="Ägaren",
            attachments=[],
            is_test=True,
            arbetsyta=True,
        )
    allt = "\n".join(llm.user_by_skill.get("cs:ticket-triage", []))
    assert "Arbetsytans siffror" in allt
    assert svar["reply"]
