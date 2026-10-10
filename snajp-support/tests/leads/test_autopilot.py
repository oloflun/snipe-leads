"""Iris autopilot (Anton 2026-10-10): en körning per vardag och kund, bara
när både miljöns flagga och kundens inställning är på."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.jobs.store import MemoryJobStore
from app.leads import autopilot, automation
from app.storage.memory import MemoryStorage

PA = automation.normalisera({"autopilot": {"pa": True, "leads_per_dag": 7}})
TISDAG_09 = datetime(2026, 10, 13, 7, 0, tzinfo=timezone.utc)  # 09:00 svensk tid


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_normalisera_autopilot():
    assert automation.normalisera(None)["autopilot"] == {"pa": False, "leads_per_dag": 10}
    assert automation.normalisera({"autopilot": {"pa": True, "leads_per_dag": 500}})["autopilot"] == {
        "pa": True, "leads_per_dag": 50}


def test_ska_kora_en_gang_per_vardag():
    assert autopilot.ska_kora(PA, [], TISDAG_09)
    assert not autopilot.ska_kora(automation.normalisera(None), [], TISDAG_09)
    lordag = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)
    assert not autopilot.ska_kora(PA, [], lordag)
    tidigt = datetime(2026, 10, 13, 3, 0, tzinfo=timezone.utc)  # 05:00 svensk tid
    assert not autopilot.ska_kora(PA, [], tidigt)
    idag = [{"status": "completed", "created_at": TISDAG_09.isoformat(), "korning": {"autopilot": True}}]
    assert not autopilot.ska_kora(PA, idag, TISDAG_09)
    manuell = [{"status": "completed", "created_at": TISDAG_09.isoformat(), "korning": {}}]
    assert autopilot.ska_kora(PA, manuell, TISDAG_09)


@pytest.mark.anyio
async def test_svep_kraver_miljoflaggan(monkeypatch):
    storage = MemoryStorage()
    tenant = (await storage.list_tenants())[0]
    await storage.set_agent_settings(
        tenant["id"], agent_type="leads", settings={"automation": {"autopilot": {"pa": True, "leads_per_dag": 7}}}
    )
    koade: list[dict] = []

    class Strom:
        async def enqueue(self, post):
            koade.append(post)

    app_state = SimpleNamespace(storage=storage, jobs=MemoryJobStore(), leadsstrom=Strom())
    monkeypatch.delenv("LEADS_AUTOPILOT", raising=False)
    assert await autopilot.svep(app_state, nu=TISDAG_09) == []
    monkeypatch.setenv("LEADS_AUTOPILOT", "1")
    startade = await autopilot.svep(app_state, nu=TISDAG_09)
    assert len(startade) == 1 and koade[0]["limit"] == 7 and koade[0]["autopilot"] is True
    assert koade[0]["scope"] == "research_and_draft"
