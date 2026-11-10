"""Supportens svarstid (fas 2, 2026-11-10).

Uppmätt i development (91 körningar): triagesteget gjordes om i 71 % av
anropen, för att svaret saknade bokföringsfälten `sources_used` och
`context_refs`. Uppgiften räknar upp sina egna fält sist i meddelandet, och
modellen följde listan. Varje omförsök är ett helt modellanrop till.

Avhoppsklassaren är ett eget modellanrop som kördes FÖRE triagen, fast dess
resultat inte läses förrän efter researchen. Den går nu samtidigt.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from app.agent.step_runner import RunTrace, run_step
from app.agent.support_agent import run_support_agent
from app.agentcore.packs import PlaybookStep, RunLedger
from app.config import get_settings
from app.storage.memory import MemoryStorage
from tests.agent.test_support_agent_wiring import TENANT, _FakeLLM

pytestmark = pytest.mark.anyio
APP = Path(__file__).resolve().parents[2] / "app"


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


# -- Kontraktspåminnelsen ------------------------------------------------------


class _Fangande:
    def __init__(self):
        self.meddelanden: list[list[dict]] = []
        self.chat = self
        self.completions = self

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        self.meddelanden.append([dict(m) for m in messages])
        message = type("M", (), {"content": json.dumps({"sources_used": [], "context_refs": []})})()
        usage = type("U", (), {"prompt_tokens": 10, "completion_tokens": 5})()
        return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()


async def _kor(**k) -> str:
    klient = _Fangande()
    with patch("app.agent.step_runner.get_llm_client", return_value=klient):
        steg = PlaybookStep(skill="cs:ticket-triage", requires=("context_pack",))
        await run_step(
            steg, RunLedger(satisfied={"context_pack"}), RunTrace(),
            task="Returnera JSON med: category, priority.", case_context="## Ärendet\nHej", **k,
        )
    return klient.meddelanden[0][-1]["content"]


async def test_paminnelsen_star_sist_efter_uppgiften():
    text = await _kor(paminn_om_kontrakt=True)

    from app.agent.step_runner import KONTRAKTSPAMINNELSE

    uppgift = text.index("Returnera JSON med: category, priority.")
    assert text.index("sources_used", uppgift) > uppgift
    assert text.index("context_refs", uppgift) > uppgift
    assert text.endswith(KONTRAKTSPAMINNELSE)


async def test_utan_flaggan_ar_meddelandet_som_forut():
    text = await _kor()

    assert text == "## Ärendet\nHej\n\n## Din uppgift i det här steget\nReturnera JSON med: category, priority."


def test_supportens_steg_bar_paminnelsen():
    kalla = (APP / "agent" / "support_agent.py").read_text(encoding="utf-8")
    assert "steg = partial(run_step, instruktioner=lager_karna, paminn_om_kontrakt=True)" in kalla
    assert "steg_hel = partial(run_step, instruktioner=lager, paminn_om_kontrakt=True)" in kalla


# -- Klassaren går samtidigt ---------------------------------------------------


async def _kor_support(llm, klassare):
    with patch("app.agent.step_runner.get_llm_client", return_value=llm), patch(
        "app.agent.support_agent.classify_cancellation_risk", new=klassare
    ):
        return await run_support_agent(
            MemoryStorage(), TENANT, message="Vilka betalsätt accepterar ni?", subject="",
            channel="web", customer_email="kund@example.com", customer_name="Test Person", attachments=[],
        )


async def test_klassaren_gar_samtidigt_med_triagen():
    """Klassaren väntar på att triagens modellanrop ska ha börjat. I följd
    kunde det aldrig hända: triagen startade först när klassaren var klar."""
    triagen_borjade = asyncio.Event()
    sag_triagen: list[bool] = []

    class _LLM(_FakeLLM):
        async def create(self, **k):
            if re.search(r"styrs av skillen (\S+?),", k["messages"][0]["content"]).group(1) == "cs:ticket-triage":
                triagen_borjade.set()
            return await super().create(**k)

    async def _klassare(_meddelande):
        try:
            await asyncio.wait_for(triagen_borjade.wait(), timeout=1.0)
            sag_triagen.append(True)
        except asyncio.TimeoutError:
            sag_triagen.append(False)
        return 0.0, 0.0

    svar = await _kor_support(_LLM(), _klassare)

    assert sag_triagen == [True]
    assert svar["cancellation_risk"] is False


async def test_klassarens_utslag_nar_fortfarande_beslutet():
    async def _klassare(_meddelande):
        await asyncio.sleep(0.05)
        return 0.9, 0.9

    svar = await _kor_support(_FakeLLM(), _klassare)

    assert svar["cancellation_risk"] is True


async def test_en_trasig_klassare_faller_inte_arendet():
    async def _klassare(_meddelande):
        raise RuntimeError("modellen svarade inte")

    svar = await _kor_support(_FakeLLM(), _klassare)

    assert svar["cancellation_risk"] is False and svar["reply"]


async def test_en_hangd_klassare_ges_upp_efter_chattgransen(monkeypatch):
    """Klassaren hade ingen egen tidsgräns: ett hängt anrop höll chatten i två minuter."""
    monkeypatch.setenv("LLM_TIMEOUT_CHATT_S", "0.1")
    get_settings.cache_clear()

    async def _klassare(_meddelande):
        await asyncio.sleep(30)
        return 0.9, 0.9

    svar = await asyncio.wait_for(_kor_support(_FakeLLM(), _klassare), timeout=5)

    assert svar["cancellation_risk"] is False and svar["reply"]


def test_chattens_tidsgrans_per_modellanrop_ar_tjugo_sekunder():
    """Stegen tar 1–3 s i median och under 10 s i p95 (uppmätt); 45 s var
    längre än kunden väntar, och gränsen följs av ett omförsök."""
    from app.config import Settings

    assert Settings.model_fields["llm_timeout_chatt_s"].default == 20.0
