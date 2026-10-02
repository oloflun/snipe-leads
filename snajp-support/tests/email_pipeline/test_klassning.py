"""Klassningen av inkommande mejl (plan del D, migration 084): support, lead
eller ej relaterat — kodregler först, Jev bara när den är säker, annars
standard. Jev och LLM är stubbade; lagret är MemoryStorage."""

from __future__ import annotations

import pytest

from app.email_pipeline import klassning
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-00000000d0d0"
pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _mejl(fran: str, amne: str = "Fråga", text: str = "Hej, en fråga om ordern."):
    return {"id": "e1", "from_email": fran, "from_name": None, "subject": amne, "body_text": text}


async def test_avregistrerad_avsandare_ar_ej_relaterat():
    storage = MemoryStorage()
    await storage.add_suppression(TENANT, email="spam@exempel.se", reason="avregistrerad")
    ut = await klassning.klassa(storage, TENANT, _mejl("Spam@Exempel.se"))
    assert ut["klass"] == "ej_relaterat" and ut["kalla"] == "regel"


async def test_nyhetsbrev_och_noreply_ar_ej_relaterat():
    storage = MemoryStorage()
    assert (await klassning.klassa(storage, TENANT, _mejl("info@x.se", amne="Vårt nyhetsbrev v40")))["klass"] == "ej_relaterat"
    assert (await klassning.klassa(storage, TENANT, _mejl("noreply@bank.se", amne="Kontoutdrag")))["klass"] == "ej_relaterat"


async def test_prospektets_adress_och_doman_ar_lead():
    storage = MemoryStorage()
    p = await storage.create_prospect(
        TENANT, company_name="Alfa Bygg AB", contact_email="vd@alfabygg.se", origin="import",
        profil={"website": "https://www.alfabygg.se"},
    )
    trad = await storage.ensure_outreach_thread(TENANT, prospect_id=p["id"])
    ut = await klassning.klassa(storage, TENANT, _mejl("vd@alfabygg.se"))
    assert ut["klass"] == "lead" and ut["prospect_id"] == p["id"] and ut["thread_id"] == str(trad["id"])
    # Annan adress på samma domän → samma prospekt (granskningsfokus 4).
    ut2 = await klassning.klassa(storage, TENANT, _mejl("ekonomi@alfabygg.se"))
    assert ut2["klass"] == "lead" and ut2["prospect_id"] == p["id"]
    # Gratisdomän matchar aldrig på domän.
    p2 = await storage.create_prospect(TENANT, company_name="Beta", contact_email="beta@gmail.com", origin="import")
    assert p2
    assert (await klassning.klassa(storage, TENANT, _mejl("annan@gmail.com")))["klass"] == "support"


async def test_brevladans_syfte_leads_ger_lead():
    storage = MemoryStorage()
    ut = await klassning.klassa(storage, TENANT, _mejl("ny@kund.se"), syfte="leads")
    assert ut["klass"] == "lead" and ut["kalla"] == "syfte"


async def test_jev_avgor_bara_nar_den_ar_saker(monkeypatch):
    storage = MemoryStorage()
    monkeypatch.setattr(klassning.jev, "aktiv", lambda: True)

    async def _saker(state, fragor):
        return {"klass": {"choice": "lead", "confidence": 0.95}}

    async def _osaker(state, fragor):
        return {"klass": {"choice": "ej_relaterat", "confidence": 0.6}}

    monkeypatch.setattr(klassning.jev, "fraga", _saker)
    ut = await klassning.klassa(storage, TENANT, _mejl("ny@kund.se"))
    assert ut["klass"] == "lead" and ut["kalla"] == "jev"
    monkeypatch.setattr(klassning.jev, "fraga", _osaker)
    ut = await klassning.klassa(storage, TENANT, _mejl("ny@kund.se"))
    assert ut["klass"] == "support" and ut["kalla"] == "standard"

    async def _faller(state, fragor):
        raise RuntimeError("nere")

    monkeypatch.setattr(klassning.jev, "fraga", _faller)
    assert (await klassning.klassa(storage, TENANT, _mejl("ny@kund.se")))["klass"] == "support"


async def test_standard_ar_support():
    storage = MemoryStorage()
    ut = await klassning.klassa(storage, TENANT, _mejl("kund@foretag.se"))
    assert ut == {"klass": "support", "kalla": "standard", "stodrad": None, "prospect_id": None, "thread_id": None}


async def test_lagret_bar_klass_och_filtrerar():
    """update_email(klass=…) och list_emails(klass=…) i minneslagret — samma
    kontrakt som Postgres (INV-STORE-001)."""
    storage = MemoryStorage()
    e = await storage.save_email(
        TENANT, provider="mock", provider_message_id="m1", from_email="vd@alfabygg.se",
        from_name="VD", subject="Svar", body_text="Ja tack", received_at=None,
    )
    await storage.update_email(TENANT, e["id"], klass="lead", klass_kalla="regel", status="lead")
    rader = await storage.list_emails(TENANT, klass="lead", is_test=None)
    assert [r["id"] for r in rader] == [e["id"]] and rader[0]["klass_kalla"] == "regel"
    assert await storage.list_emails(TENANT, klass="support", is_test=None) == []
