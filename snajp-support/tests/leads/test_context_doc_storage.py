import pytest

from app.storage.memory import MemoryStorage

TENANT_A = "tenant-a"
TENANT_B = "tenant-b"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_save_and_get_latest_context_doc_round_trips():
    storage = MemoryStorage()
    await storage.save_context_doc(TENANT_A, kind="product_marketing", content="v1")
    doc = await storage.save_context_doc(TENANT_A, kind="product_marketing", content="v2")
    latest = await storage.get_latest_context_doc(TENANT_A, kind="product_marketing")
    assert latest["content"] == "v2"
    assert latest["version"] == 2
    assert doc["version"] == 2


@pytest.mark.anyio
async def test_list_context_docs_filters_by_kind():
    storage = MemoryStorage()
    await storage.save_context_doc(TENANT_A, kind="product_marketing", content="pm")
    await storage.save_context_doc(TENANT_A, kind="customer_research", content="cr")
    only_pm = await storage.list_context_docs(TENANT_A, kind="product_marketing")
    assert len(only_pm) == 1
    assert only_pm[0]["content"] == "pm"
    all_docs = await storage.list_context_docs(TENANT_A)
    assert len(all_docs) == 2


@pytest.mark.anyio
async def test_context_docs_are_isolated_per_tenant():
    storage = MemoryStorage()
    await storage.save_context_doc(TENANT_A, kind="product_marketing", content="A:s data")
    await storage.save_context_doc(TENANT_B, kind="product_marketing", content="B:s data")
    a_docs = await storage.list_context_docs(TENANT_A)
    b_docs = await storage.list_context_docs(TENANT_B)
    assert [d["content"] for d in a_docs] == ["A:s data"]
    assert [d["content"] for d in b_docs] == ["B:s data"]


@pytest.mark.anyio
async def test_get_latest_context_doc_returns_none_when_missing():
    storage = MemoryStorage()
    assert await storage.get_latest_context_doc(TENANT_A, kind="retention_playbook") is None
