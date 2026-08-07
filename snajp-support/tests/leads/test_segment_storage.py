import pytest

from app.storage.memory import MemoryStorage


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _ab_result(tenant_id, segment="utbildning", lever="time_delay", sent=10, replies=2, positive=1):
    return {
        "tenant_id": tenant_id,
        "segment": segment,
        "lever": lever,
        "sent": sent,
        "replies": replies,
        "positive": positive,
    }


@pytest.mark.anyio
async def test_get_segment_ab_aggregate_takes_no_tenant_argument_and_hides_small_segments():
    storage = MemoryStorage()
    storage.ab_results = [_ab_result("t1"), _ab_result("t2")]
    result = await storage.get_segment_ab_aggregate()
    assert result == []


@pytest.mark.anyio
async def test_get_segment_ab_aggregate_returns_aggregate_once_three_tenants_present():
    storage = MemoryStorage()
    storage.ab_results = [_ab_result("t1"), _ab_result("t2"), _ab_result("t3")]
    result = await storage.get_segment_ab_aggregate()
    assert len(result) == 1
    assert result[0]["tenant_count"] == 3
    assert "tenant_id" not in result[0]
