"""Ett modellsvar utan tokenräkning fäller inte agenten (hittat av evalsviten, 2026-11-10).

Två av fyrtio kvitton i evalsvitens första körning mot development gav ett
serverfel. Vertex svarade utan utdata och med `completion_tokens: null`;
Agents SDK:n bygger sin `Usage` av fältet och kastade ett valideringsfel rakt
genom kvittohanteraren. Användaren såg "Något gick fel på vår sida".

Två lager:
1. LLM-klienten fyller i saknade tokenfält med noll, för alla agenter som går
   genom Agents SDK:n (kvittohanteraren, bokföringschatten, onboarding).
2. Kvittohanteraren fångar ett modellfel som inte är kvot: underlaget läses då
   maskinellt och går till granskning, i stället för att begäran faller.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.agent import llm
from app.kvitton import hanterare

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


# -- Klienten --------------------------------------------------------------------


def _klient_som_svarar(usage):
    async def create(*_a, **_k):
        return SimpleNamespace(choices=[], usage=usage)

    completions = SimpleNamespace(create=create)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


async def test_saknade_tokenfalt_blir_noll():
    usage = SimpleNamespace(prompt_tokens=812, completion_tokens=None, total_tokens=None)
    klient = llm._med_hel_anvandning(_klient_som_svarar(usage))

    svar = await klient.chat.completions.create(model="m", messages=[])

    assert (svar.usage.prompt_tokens, svar.usage.completion_tokens, svar.usage.total_tokens) == (812, 0, 812)


async def test_ett_helt_svar_ar_orort_och_inpackningen_ar_idempotent():
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    klient = llm._med_hel_anvandning(llm._med_hel_anvandning(_klient_som_svarar(usage)))

    svar = await klient.chat.completions.create(model="m", messages=[])

    assert (svar.usage.prompt_tokens, svar.usage.completion_tokens, svar.usage.total_tokens) == (10, 5, 15)


async def test_ett_svar_utan_anvandning_alls_gar_igenom():
    klient = llm._med_hel_anvandning(_klient_som_svarar(None))
    assert (await klient.chat.completions.create(model="m", messages=[])).usage is None


def test_huvudklienten_ar_inpackad(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-a-real-credential-000000")
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setattr(llm, "_llm_client", None)
    try:
        klient = llm.get_llm_client()
        assert getattr(klient.chat.completions.create, "_hel_anvandning", False)
    finally:
        monkeypatch.setattr(llm, "_llm_client", None)
        get_settings.cache_clear()


# -- Kvittohanteraren --------------------------------------------------------------


async def test_ett_modellfel_ger_ingen_avlasning_i_stallet_for_att_kasta(monkeypatch):
    from app.agent.step_runner import RunTrace

    async def _trasig(*_a, **_k):
        raise ValueError("1 validation error for Usage: output_tokens")

    monkeypatch.setattr(hanterare.Runner, "run", _trasig)
    monkeypatch.setattr("app.agent.llm.get_agent_model", lambda: "modell")

    trace = RunTrace()
    rat = await hanterare._kor_modellen("system", "användare", SimpleNamespace(), trace)

    assert rat is None, "utan avläsning tar den maskinella läsningen över och raden går till granskning"
    assert trace.steps and trace.steps[-1].escalated is True


async def test_slut_kvot_gar_fortfarande_vidare_till_kvotbeskedet(monkeypatch):
    """Kvot och kredit är inte ett trasigt svar: de ska bli sitt eget besked (api/bookkeeping._kvotsvar)."""
    from app.agent.step_runner import RunTrace

    class _Kvot(Exception):
        status_code = 429

    async def _kvot(*_a, **_k):
        raise _Kvot("Resource has been exhausted (e.g. check quota).")

    monkeypatch.setattr(hanterare.Runner, "run", _kvot)
    monkeypatch.setattr("app.agent.llm.get_agent_model", lambda: "modell")

    with pytest.raises(_Kvot):
        await hanterare._kor_modellen("system", "användare", SimpleNamespace(), RunTrace())
