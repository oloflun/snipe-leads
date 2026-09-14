"""Ett kraschat chattjobb får ALDRIG bära undantagstexten till klienten.

Bakgrund: jobbets feltext renderades ordagrant i den publika chattbubblan,
och en skarp körning visade "'ascii' codec can't encode character 'à' in
position 7" för en besökare. Diagnosen hör hemma i loggen (logger.exception
tar hela stacken); jobbet bär en mening skriven för en människa."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.api.chat import _process
from app.api.schemas import ChatRequest
from app.jobs.store import MemoryJobStore
from app.storage.memory import MemoryStorage


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_kraschat_jobb_far_en_mansklig_mening_inte_undantaget(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-a-real-credential-000000")
    from app.config import get_settings

    get_settings.cache_clear()

    storage = MemoryStorage()
    jobs = MemoryJobStore()
    app_state = SimpleNamespace(storage=storage, jobs=jobs)
    job_id = await jobs.create(tenant_id="t-1")

    request = ChatRequest(
        message="Hej!",
        channel="web",
        customer_email="kund@example.com",
        customer_name="Kund",
    )

    hemlighet = "'ascii' codec can't encode character 'à' in position 7"
    with patch(
        "app.agent.support_agent.run_support_agent",
        new=AsyncMock(side_effect=RuntimeError(hemlighet)),
    ):
        await _process(app_state, job_id, "t-1", request, attachments=[])

    job = await jobs.get(job_id)
    get_settings.cache_clear()

    assert job["status"] == "failed"
    assert hemlighet not in (job["error"] or ""), "Undantagstexten läckte till jobbet."
    assert "ascii" not in (job["error"] or "")
    # Meningen ska peka framåt, inte bara konstatera ett haveri.
    assert "igen" in job["error"]
