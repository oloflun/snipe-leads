"""Regression (2026-10-05): `arbetsyta`-flaggan ska överleva strömvägen.

Rekonstruktionen i hantera_strom_jobb byggde ChatRequest utan fältet, så
arbetsytans sifferblock försvann EXAKT i drift (Redis-strömmen) men aldrig
lokalt (paritetsvägen) — upptäckt i skarptestet mot dev. Testet kör
hanteraren med en payload som bär flaggan och asserterar att
run_support_agent får den.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.api.chat import hantera_strom_jobb
from app.jobs.store import MemoryJobStore
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _AppState:
    def __init__(self):
        self.storage = MemoryStorage()
        self.jobs = MemoryJobStore()


@pytest.mark.anyio
async def test_strompayloadens_arbetsyta_nar_run_support_agent():
    state = _AppState()
    job_id = await state.jobs.create(tenant_id=TENANT)

    fake = AsyncMock(return_value={"reply": "ok", "step_log": []})
    with (
        patch("app.agent.support_agent.run_support_agent", new=fake),
        patch("app.config.Settings.is_simulation", return_value=False),
    ):
        await hantera_strom_jobb(
            state,
            {
                "job_id": job_id,
                "tenant_id": TENANT,
                "message": "Hur många ärenden fick vi i veckan?",
                "customer_email": "agare@example.se",
                "is_test": True,
                "arbetsyta": True,
            },
        )

    assert fake.await_count == 1
    assert fake.await_args.kwargs["arbetsyta"] is True
    assert fake.await_args.kwargs["is_test"] is True
