"""INV-AUDIT-001 + instruktionslagret: AGENTS.md, overlays och pack_version.

Det viktigaste testet här är test_system_prompt_order: ordningen mellan
policy, skill, overlay och utdatakontrakt är inte kosmetisk. Kontraktet måste
ligga SIST och läggas på av kod, annars kan ett tuninglager försvaga det —
och tuninglagren är precis de som är fritt redigerbara utan nyckel.

test_linkedin_ban_is_not_a_python_fstring är vakthunden som håller
tuningytan på ETT ställe. Utan den kryper regler tillbaka in i leads_agent.py
där de är oversionerade och osynliga i pack_version.
"""

from __future__ import annotations

import re
from unittest.mock import patch

import pytest

from app.agentcore import overlays
from app.agentcore.overlays import (
    UnknownOverlayError,
    global_hash,
    load_global_instructions,
    load_overlay,
    overlay_hash,
    pack_version,
)
from app.agentcore.packs import PlaybookStep, RunLedger
from app.agent.step_runner import RunTrace, run_step
from app.config import get_settings


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


class _CapturingLLM:
    def __init__(self):
        self.messages = None
        self.chat = self
        self.completions = self

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        self.messages = messages

        class _Msg:
            content = '{"sources_used": [], "context_refs": []}'
            reasoning_content = None

        class _Choice:
            message = _Msg()

        class _Response:
            choices = [_Choice()]
            usage = None

        return _Response()


async def _run_with(step: PlaybookStep) -> list[dict]:
    llm = _CapturingLLM()
    ledger = RunLedger(satisfied={"offer_selected"})
    with patch("app.agent.step_runner.get_llm_client", return_value=llm):
        await run_step(step, ledger, RunTrace(), task="t", case_context="c")
    return llm.messages


# -- Innehåll och laddning -------------------------------------------------


def test_overlay_files_load():
    assert "LinkedIn" in load_overlay("leads-hard-rules")
    assert "unsupported" in load_overlay("leads-grounding-repair")


def test_global_instructions_load():
    text = load_global_instructions()
    assert "Hitta aldrig på fakta" in text
    # AGENTS.md är opinnad och slår igenom hos alla direkt. Kryper ton och
    # stil in dit har vi byggt en väg att ändra varje kunds agent utan pin.
    assert "hör INTE hemma här" in text


def test_unknown_overlay_fails_at_construction():
    """Fail-fast vid modulimport, alltså i CI — aldrig först i produktion."""
    with pytest.raises(UnknownOverlayError):
        PlaybookStep(skill="mk:cold-email", requires=("x",), overlay="finns-inte")
    with pytest.raises(UnknownOverlayError):
        PlaybookStep(skill="mk:cold-email", requires=("x",), overlay="../../etc/passwd")


# -- Systempromptens ordning ----------------------------------------------


@pytest.mark.anyio
async def test_system_prompt_order():
    messages = await _run_with(
        PlaybookStep(skill="mk:cold-email", requires=("offer_selected",), overlay="leads-hard-rules")
    )
    system = messages[0]["content"]

    i_global = system.index("GLOBALA REGLER")
    i_skill = system.index("styrs av skillen")
    i_overlay = system.index("TILLÄGGSINSTRUKTIONER")
    i_contract = system.index("Svara ENBART med ett JSON-objekt")

    assert i_global < i_skill < i_overlay < i_contract, (
        "Ordningen måste vara policy -> skill -> overlay -> kontrakt. "
        "Kontraktet SIST, annars kan ett tuninglager försvaga det."
    )


@pytest.mark.anyio
async def test_step_without_overlay_has_no_overlay_block():
    messages = await _run_with(PlaybookStep(skill="mk:cold-email", requires=("offer_selected",)))
    assert "TILLÄGGSINSTRUKTIONER" not in messages[0]["content"]
    assert "GLOBALA REGLER" in messages[0]["content"]  # global gäller alltid


@pytest.mark.anyio
async def test_overlay_text_actually_reaches_the_prompt():
    messages = await _run_with(
        PlaybookStep(skill="mk:cold-email", requires=("offer_selected",), overlay="leads-hard-rules")
    )
    assert "Producera ALDRIG LinkedIn-kopia" in messages[0]["content"]


@pytest.mark.anyio
async def test_overlay_is_recorded_in_the_step_log():
    """INV-AUDIT-001: skill-namnet ensamt räcker inte när tuninglagret är
    fritt redigerbart — revisionsloggen måste säga vilken overlay som formade
    steget."""
    llm = _CapturingLLM()
    trace = RunTrace()
    step = PlaybookStep(
        skill="mk:cold-email", requires=("offer_selected",), overlay="leads-hard-rules"
    )
    with patch("app.agent.step_runner.get_llm_client", return_value=llm):
        await run_step(step, RunLedger(satisfied={"offer_selected"}), trace, task="t", case_context="c")

    entry = trace.as_log()[0]
    assert entry["overlay"] == "leads-hard-rules"
    assert entry["overlay_chars"] > 100
    assert entry["global_chars"] > 100


# -- Versionering ----------------------------------------------------------


def test_pack_version_carries_all_three_hashes():
    version = pack_version("leads/outreach-v1")
    prefix, _, playbook = version.rpartition(":")
    assert playbook == "leads/outreach-v1"
    parts = prefix.split("+")
    assert len(parts) == 3, f"pack_version saknar ett lager: {version}"
    assert all(parts), "en tom hash betyder att ett lager inte lästes"


def test_overlay_hash_changes_when_a_file_changes(tmp_path, monkeypatch):
    """Utan det här är overlay-hashen dekoration: den skulle stå kvar
    oförändrad medan tuninglagret ändrats, och pack_version skulle ljuga."""
    monkeypatch.setattr(overlays, "OVERLAYS_ROOT", tmp_path)
    overlays.cache_clear()
    (tmp_path / "a.md").write_text("original", encoding="utf-8")
    before = overlay_hash()

    overlays.cache_clear()
    (tmp_path / "a.md").write_text("ändrad", encoding="utf-8")
    after = overlay_hash()

    assert before != after
    overlays.cache_clear()


def test_global_hash_changes_when_agents_md_changes(tmp_path, monkeypatch):
    target = tmp_path / "AGENTS.md"
    monkeypatch.setattr(overlays, "AGENTS_MD", target)
    overlays.cache_clear()
    target.write_text("regel ett", encoding="utf-8")
    before = global_hash()

    overlays.cache_clear()
    target.write_text("regel ett och två", encoding="utf-8")
    assert global_hash() != before
    overlays.cache_clear()


# -- Vakthunden ------------------------------------------------------------


def test_linkedin_ban_is_not_a_python_fstring():
    """Regeln bor i agent-core/overlays/leads-hard-rules.md. Kryper den
    tillbaka in i koden blir den oversionerad, osynlig i pack_version, och
    duplicerad mot overlayen — och duplicerad tuning divergerar."""
    from pathlib import Path

    source = Path(__file__).resolve().parents[2] / "app" / "agent" / "leads_agent.py"
    text = source.read_text(encoding="utf-8")
    hits = [
        line.strip()
        for line in text.splitlines()
        if "LinkedIn" in line and not line.strip().startswith("#")
    ]
    assert not hits, (
        "LinkedIn-regeln finns som kod i leads_agent.py igen: "
        f"{hits}. Lägg den i agent-core/overlays/leads-hard-rules.md i stället."
    )


def test_hard_rules_overlay_is_bound_to_every_outreach_step():
    from app.leads.outreach_playbook import OUTREACH_V1

    missing = [s.skill for s in OUTREACH_V1.steps if s.overlay != "leads-hard-rules"]
    assert not missing, f"Steg utan hårda regler: {missing}"
