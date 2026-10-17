"""Bakgrundsjobbens tak för samtidiga LLM-anrop (2026-10-09): tio parallella
researchjobb gav Vertex 429 i en minut i sträck och alla föll."""

import asyncio

import pytest

from app.agent import step_runner

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_taket_begransar_samtidiga_anrop(monkeypatch):
    monkeypatch.setattr(step_runner, "_BAKGRUNDSTAK", {})
    monkeypatch.setattr(step_runner.get_settings(), "leads_llm_samtidiga", 2)
    samtidigt = toppen = 0

    async def anrop():
        nonlocal samtidigt, toppen
        async with step_runner._bakgrundstak():
            samtidigt += 1
            toppen = max(toppen, samtidigt)
            await asyncio.sleep(0.02)
            samtidigt -= 1

    await asyncio.gather(*(anrop() for _ in range(8)))
    assert toppen == 2
