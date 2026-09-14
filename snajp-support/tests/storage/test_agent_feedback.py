"""agent_feedback — första kodvägen till en tabell som stått död sedan
migration 010. Minnet speglar Postgres FK och check-villkor uttryckligen."""

import pytest

from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _run(storage) -> str:
    rad = await storage.log_agent_run(
        TENANT,
        agent_type="support",
        pack_version="x:support/v1",
        skills_used=["cs:ticket-triage"],
        input_text="fråga",
        output_text="svar",
        step_log=[],
        tokens_in=10,
        tokens_out=5,
        latency_ms=100,
    )
    return rad["id"]


@pytest.mark.anyio
async def test_feedback_sparas_och_listas_senast_forst():
    storage = MemoryStorage()
    run_id = await _run(storage)
    await storage.save_agent_feedback(TENANT, run_id=run_id, verdict="good")
    await storage.save_agent_feedback(
        TENANT,
        run_id=run_id,
        verdict="bad",
        comment="Fel ton.",
        corrected_output="Så här borde svaret ha låtit.",
    )

    alla = await storage.list_agent_feedback(TENANT)
    assert [r["verdict"] for r in alla] == ["bad", "good"]
    daliga = await storage.list_agent_feedback(TENANT, verdict="bad")
    assert len(daliga) == 1
    assert daliga[0]["corrected_output"] == "Så här borde svaret ha låtit."


@pytest.mark.anyio
async def test_okand_verdict_kastar_som_postgres_check():
    storage = MemoryStorage()
    run_id = await _run(storage)
    with pytest.raises(ValueError):
        await storage.save_agent_feedback(TENANT, run_id=run_id, verdict="utmärkt")


@pytest.mark.anyio
async def test_run_id_som_inte_finns_kastar_som_fk():
    """Minnet speglar FK:n. Utan den här tar minnet emot ett dött run_id
    medan Postgres kastar — halvårsbuggens form."""
    storage = MemoryStorage()
    await _run(storage)
    with pytest.raises(ValueError):
        await storage.save_agent_feedback(
            TENANT, run_id="00000000-0000-4000-a000-00000000dead", verdict="good"
        )
