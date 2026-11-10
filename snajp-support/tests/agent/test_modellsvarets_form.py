"""Modellens svar har inte alltid den form koden väntar sig (Fas 0-fyndet H15).

Kontraktet säger ett JSON-objekt med bestämda fält. Modellen svarar ibland
med en lista, ett tal som text eller "false" inom citattecken. Före: en lista
föll supporten på `triage.get`, ett sentiment på exakt 0,0 lästes som 0,5, ett
icke-numeriskt sentiment gav ett undantag, strängen "false" i `escalate`
lämnade över ärendet och `kundfakta` som en enda sträng sparades som en
bokstav per faktum.
"""

from __future__ import annotations

import json

import pytest

from app.agent.support_agent import _normalisera_triage
from app.agentcore.packs import check_output_contract

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


# -- Stegköraren -------------------------------------------------------------


class _LLM:
    """Svarar med samma råtext varje gång."""

    def __init__(self, ratext: str):
        self.ratext = ratext
        self.anrop = 0
        self.chat = self
        self.completions = self

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        self.anrop += 1
        message = type("M", (), {"content": self.ratext})()
        usage = type("U", (), {"prompt_tokens": 10, "completion_tokens": 5})()
        return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()


@pytest.fixture
def _riktig_klient(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def _kor_steg(monkeypatch, klient):
    from app.agent.step_runner import RunTrace, run_step
    from app.agentcore.packs import PlaybookStep, RunLedger

    monkeypatch.setattr("app.agent.step_runner.get_llm_client", lambda: klient)
    steg = PlaybookStep(skill="cs:ticket-triage", requires=("context_pack",))
    spar = RunTrace()
    ut = await run_step(steg, RunLedger(satisfied={"context_pack"}), spar, task="test", case_context="test")
    return ut, spar


@pytest.mark.parametrize("ratext", ["[1, 2]", '"bara text"', "42", "null", "inte json alls"])
async def test_steget_ger_alltid_ett_objekt(monkeypatch, _riktig_klient, ratext):
    ut, spar = await _kor_steg(monkeypatch, _LLM(ratext))

    assert ut == {}
    assert spar.steps[-1].escalated is True, "kontraktsbrottet ska synas i spåret"


async def test_ett_riktigt_objekt_gar_igenom_orort(monkeypatch, _riktig_klient):
    svar = {"sources_used": [], "context_refs": [], "category": "frakt"}
    ut, spar = await _kor_steg(monkeypatch, _LLM(json.dumps(svar)))

    assert ut == svar
    assert spar.steps[-1].escalated is False


# -- Kontraktskontrollen -----------------------------------------------------


def test_kontraktet_tal_referenser_som_inte_ar_text():
    """`set()` över en lista med objekt kastade TypeError."""
    utfall = check_output_contract(
        {"sources_used": [], "context_refs": [{"id": "kb-1"}, "kb-2", 7, None]},
        required_context_refs=("kb-2",),
        already_retried=False,
    )
    assert utfall.verdict == "ok"


def test_kontraktet_tal_referenser_som_inte_ar_en_lista():
    utfall = check_output_contract(
        {"sources_used": [], "context_refs": 5},
        required_context_refs=("kb-2",),
        already_retried=False,
    )
    assert utfall.verdict == "retry" and utfall.missing_refs == ("kb-2",)


# -- Triagens värden ---------------------------------------------------------


@pytest.mark.parametrize(
    ("ratt", "vantat"),
    [
        (0.0, 0.0),
        (0, 0.0),
        (0.2, 0.2),
        ("0.2", 0.2),
        ("0,2", 0.2),
        (1.7, 1.0),
        (-3, 0.0),
        (None, 0.5),
        ("arg", 0.5),
        ([0.1], 0.5),
        (True, 0.5),
        (float("nan"), 0.5),
    ],
)
def test_sentimentet_blir_alltid_ett_tal_mellan_noll_och_ett(ratt, vantat):
    assert _normalisera_triage({"sentiment": ratt})["sentiment"] == vantat


def test_saknat_sentiment_ar_neutralt():
    assert _normalisera_triage({})["sentiment"] == 0.5


@pytest.mark.parametrize(
    ("ratt", "vantat"),
    [(True, True), (False, False), ("true", True), ("false", False), ("Ja", True), ("nej", False),
     ("kanske", None), (1, None), (None, None), ([], None)],
)
def test_ja_nej_falt_blir_riktiga_sanningsvarden(ratt, vantat):
    ut = _normalisera_triage(
        {"escalate": ratt, "ber_om_manniska": ratt, "inom_amnesomradet": ratt, "missforstadd": ratt}
    )
    for falt in ("escalate", "ber_om_manniska", "inom_amnesomradet", "missforstadd"):
        assert ut.get(falt) is vantat, falt


def test_falskt_i_citattecken_lamnar_inte_over():
    """"false" som sträng är sann i Python, och ärendet lämnades över."""
    assert not _normalisera_triage({"escalate": "false"}).get("escalate")


@pytest.mark.parametrize(
    ("ratt", "vantat"),
    [
        ("Kunden heter Anna", ["Kunden heter Anna"]),
        (["  Bokad på HLR 12 mars ", "", None, 7, {"x": 1}, ["y"]], ["Bokad på HLR 12 mars", "7"]),
        (None, []),
        ({"fakta": "x"}, []),
        (5, []),
    ],
)
def test_kundfakta_blir_en_lista_med_text(ratt, vantat):
    assert _normalisera_triage({"kundfakta": ratt})["kundfakta"] == vantat


@pytest.mark.parametrize("ratt", [[1, 2], "text", 5, None])
def test_en_triage_som_inte_ar_ett_objekt_blir_ett_tomt(ratt):
    ut = _normalisera_triage(ratt)
    assert ut["sentiment"] == 0.5 and ut["kundfakta"] == []


def test_ovriga_falt_ror_inte():
    ut = _normalisera_triage({"category": "frakt", "priority": "P2", "sprak": "en", "sokfraga_sv": "frakt"})
    assert (ut["category"], ut["priority"], ut["sprak"], ut["sokfraga_sv"]) == ("frakt", "P2", "en", "frakt")
