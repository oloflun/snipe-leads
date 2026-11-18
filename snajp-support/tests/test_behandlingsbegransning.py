"""Begränsning av behandling (GDPR art. 18, migration 124).

En aktiv markering för en adress ska
  1. stoppa varje utskick till adressen i sändningsögonblicket, hos varje kund;
  2. låta ett inkommande mejl från adressen ligga sparat men gå till Att
     hantera, utan klassning, triage eller AI-utkast;
  3. inte gälla längre när den hävts;
och en markering som inte går att läsa ska stoppa, inte släppa igenom.

Databasdelen (tabellen, rättigheterna och skriptet --begransa/--hav-begransning)
provas i tests/db/test_gdpr_radera_db.py mot hela migrationskedjan.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.config import DEFAULT_TENANT_ID
from app.email_pipeline import processor
from app.email_pipeline.processor import process_email
from app.leads.scheduler import process_due_item
from app.storage.memory import MemoryStorage

from tests.leads.test_scheduler import TENANT, WITHIN_WINDOW_UTC, _FakeSendProvider, _seed

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _begransa(storage: MemoryStorage, epost: str, *, havd: bool = False) -> None:
    storage.behandlingsbegransningar.append(
        {
            "email": epost,
            "skal": "Riktigheten prövas",
            "begard_at": datetime(2026, 11, 18, tzinfo=timezone.utc),
            "havd_at": datetime(2026, 11, 19, tzinfo=timezone.utc) if havd else None,
        }
    )


async def test_utskick_till_begransad_adress_blockeras():
    storage = MemoryStorage()
    item_id, thread_id, _ = _seed(storage, scheduled_at=WITHIN_WINDOW_UTC)
    _begransa(storage, "INFO@example.se")  # skiftläget spelar ingen roll
    provider = _FakeSendProvider()

    utfall = await process_due_item(
        storage, TENANT, {"id": item_id, "thread_id": thread_id}, provider, now=WITHIN_WINDOW_UTC
    )

    assert utfall == "blocked"
    assert provider.sent == []
    assert storage.send_queue[TENANT][0]["gate_checks"]["send_guard_regel"] == "begransad_behandling"


async def test_havd_begransning_stoppar_inte():
    storage = MemoryStorage()
    item_id, thread_id, _ = _seed(storage, scheduled_at=WITHIN_WINDOW_UTC)
    _begransa(storage, "info@example.se", havd=True)
    provider = _FakeSendProvider()

    utfall = await process_due_item(
        storage, TENANT, {"id": item_id, "thread_id": thread_id}, provider, now=WITHIN_WINDOW_UTC
    )

    assert utfall == "sent"
    assert [m["to"] for m in provider.sent] == ["info@example.se"]


async def test_olasbar_begransningslista_koar_om_i_stallet_for_att_skicka(monkeypatch):
    storage = MemoryStorage()
    item_id, thread_id, _ = _seed(storage, scheduled_at=WITHIN_WINDOW_UTC)

    async def trasig(tenant_id):
        raise RuntimeError("relation behandlingsbegransningar does not exist")

    monkeypatch.setattr(storage, "list_begransade", trasig)
    provider = _FakeSendProvider()

    utfall = await process_due_item(
        storage, TENANT, {"id": item_id, "thread_id": thread_id}, provider, now=WITHIN_WINDOW_UTC
    )

    assert utfall == "requeued"
    assert provider.sent == []
    assert storage.send_queue[TENANT][0]["gate_checks"]["send_guard_regel"] == "begransning_okand"


async def _sparat_mail(storage: MemoryStorage, fran: str):
    return await storage.save_email(
        DEFAULT_TENANT_ID,
        provider="imap",
        provider_message_id=f"begr-{fran}",
        from_email=fran,
        from_name="Anna Andersson",
        subject="Fråga om min order",
        body_text="Hej, var är mitt paket?",
    )


async def test_inkommande_mejl_fran_begransad_adress_far_ingen_ai(monkeypatch):
    storage = MemoryStorage()
    _begransa(storage, "anna@example.com")
    mail = await _sparat_mail(storage, "Anna@Example.com")

    async def ingen_modell(*args, **kwargs):  # klassning, triage och utkast får inte nås
        raise AssertionError("AI-steget nåddes trots begränsningen")

    monkeypatch.setattr(processor, "klassa", ingen_modell)
    monkeypatch.setattr(processor, "_triage_email", ingen_modell)

    resultat = await process_email(storage, DEFAULT_TENANT_ID, mail)

    assert resultat == {"action": "att_hantera"}
    sparat = await storage.get_email(DEFAULT_TENANT_ID, mail["id"])
    assert sparat is not None and sparat["status"] == "att_hantera"
    assert sparat["body_text"] == "Hej, var är mitt paket?"  # lagras oförändrat
    beslut = await storage.list_decisions(DEFAULT_TENANT_ID, mail["id"])
    assert [b["event"] for b in beslut] == ["begransad_behandling"]


async def test_inkommande_mejl_utan_begransning_gar_vidare(monkeypatch):
    storage = MemoryStorage()
    _begransa(storage, "nagon.annan@example.com")
    mail = await _sparat_mail(storage, "anna@example.com")
    nadde: list[str] = []

    async def klassa(*args, **kwargs):
        nadde.append("klassa")
        return {"klass": "ej_relaterat", "kalla": "regel", "stodrad": None}

    monkeypatch.setattr(processor, "klassa", klassa)

    resultat = await process_email(storage, DEFAULT_TENANT_ID, mail)

    assert nadde == ["klassa"]
    assert resultat == {"action": "ej_relaterat"}
