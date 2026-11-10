"""Utkastens text läses bara för de leads som visas (fas 2, 2026-11-10).

Fliken Skickat visar de godkända utkast som väntar på sändfönstret, med text.
För att hitta dem lästes texten för VARJE tråd hos kunden (3 184 uppslag hos
den största) och nästan alla kastades. Nu avgörs först vilka som är godkända,
utan text, och texten läses bara för dem.
"""

from __future__ import annotations

import pytest

from app.api import leads as leads_api
from app.storage.memory import MemoryStorage

pytestmark = pytest.mark.anyio
TENANT = "00000000-0000-4000-a000-000000000001"


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _lead(storage: MemoryStorage, namn: str, *, status: str, godkand: bool) -> str:
    p = await storage.create_prospect(TENANT, company_name=namn, contact_email=f"info@{namn.lower()}.example")
    trad = await storage.ensure_outreach_thread(TENANT, prospect_id=p["id"])
    await storage.queue_outreach_message(
        TENANT, thread_id=trad["id"], subject=f"Ämne {namn}", body=f"Text till {namn}",
        humanizer_variant="x", scheduled_at="2026-11-11T08:00:00+00:00", status=status,
    )
    if godkand:
        post = next(q for q in storage.send_queue[TENANT] if q["thread_id"] == trad["id"])
        post["gate_checks"] = {"approved_by": "human"}
    return p["id"]


async def test_urvalet_ger_bara_de_efterfragade_leadsen():
    storage = MemoryStorage()
    a = await _lead(storage, "Alfa", status="queued", godkand=True)
    b = await _lead(storage, "Beta", status="awaiting_review", godkand=False)

    alla = await storage.utkast_lagen(TENANT, med_text=True)
    urval = await storage.utkast_lagen(TENANT, med_text=True, bara=[a])

    assert set(alla) == {a, b}
    assert set(urval) == {a}
    assert urval[a] == alla[a], "urvalet ändrar inte radens innehåll"
    assert await storage.utkast_lagen(TENANT, med_text=True, bara=[]) == {}


async def test_schemalagda_utskick_laser_text_bara_for_de_godkanda():
    storage = MemoryStorage()
    a = await _lead(storage, "Alfa", status="queued", godkand=True)
    await _lead(storage, "Beta", status="awaiting_review", godkand=False)
    await _lead(storage, "Gamma", status="queued", godkand=False)
    anrop: list[dict] = []
    riktig = storage.utkast_lagen

    async def _spion(tenant_id, **k):
        anrop.append(k)
        return await riktig(tenant_id, **k)

    storage.utkast_lagen = _spion  # type: ignore[method-assign]

    rader = await leads_api._schemalagda_utskick(storage, TENANT)

    assert [r["prospect_id"] for r in rader] == [a]
    assert rader[0]["subject"] == "Ämne Alfa" and rader[0]["body"] == "Text till Alfa"
    med_text = [k for k in anrop if k.get("med_text")]
    assert len(med_text) == 1 and med_text[0].get("bara") == [a], "texten ska bara läsas för de godkända"


async def test_utan_godkanda_lases_ingen_text_alls():
    storage = MemoryStorage()
    await _lead(storage, "Beta", status="awaiting_review", godkand=False)
    anrop: list[dict] = []
    riktig = storage.utkast_lagen

    async def _spion(tenant_id, **k):
        anrop.append(k)
        return await riktig(tenant_id, **k)

    storage.utkast_lagen = _spion  # type: ignore[method-assign]

    assert await leads_api._schemalagda_utskick(storage, TENANT) == []
    assert not any(k.get("med_text") for k in anrop)
