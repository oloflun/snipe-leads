"""Körningslistans sammandrag: adminlistorna utan input, output och step_log.

/admin/agentanvandning serialiserade 17,7 MB och /admin/korningar 7,3 MB in i
sidan (uppmätt 2026-10-09) för tabeller som bara läser tokens, kund och tid.
Sammandraget ska bära exakt det listorna läser — och bokföringens
underlag/frågor-delning, som förut lästes ur hela step_log.
"""

import pytest

from app.storage.memory import MemoryStorage


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _logga(storage: MemoryStorage, steg: str) -> None:
    await storage.log_agent_run(
        "t1",
        agent_type="bookkeeping",
        pack_version="v1",
        skills_used=[steg],
        input_text="x" * 5000,
        output_text="y" * 5000,
        step_log=[{"skill": steg, "tokens_in": 10}],
        tokens_in=10,
        tokens_out=5,
        latency_ms=120,
    )


@pytest.mark.anyio
async def test_sammandraget_utelamnar_de_tunga_falten():
    storage = MemoryStorage()
    await _logga(storage, "snajp:bokforing-chatt")
    await _logga(storage, "snajp:kvitto")

    rader = await storage.list_agent_runs_all(agent_type="bookkeeping", sammandrag=True)

    assert len(rader) == 2
    for rad in rader:
        assert "input" not in rad and "output" not in rad and "step_log" not in rad
        assert rad["tokens_in"] == 10 and rad["latency_ms"] == 120
    assert sorted(r["bokforingschatt"] for r in rader) == [False, True]


@pytest.mark.anyio
async def test_utan_sammandrag_ar_raderna_hela():
    storage = MemoryStorage()
    await _logga(storage, "snajp:kvitto")

    (rad,) = await storage.list_agent_runs_all(agent_type="bookkeeping")

    assert rad["step_log"] and rad["input"]
    assert "bokforingschatt" not in rad
