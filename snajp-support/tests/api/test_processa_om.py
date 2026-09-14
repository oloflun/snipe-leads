"""Omkörning av failade inkorgsmejl + kvotfelets översättning.

Bakgrund, uppmätt 2026-09-05: Geminis kredit tog slut, tre riktiga mail fick
status failed med leverantörens råa faktureringstext i kundens beslutslogg —
och ingen kodväg kunde köra om dem (IMAP hade markerat dem lästa i källan).
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.email_pipeline import processor
from app.email_pipeline.processor import process_email
from app.main import app
from app.storage.memory import MemoryStorage

pytestmark = pytest.mark.anyio

DEMO_KEY = get_settings().snajp_demo_api_key


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _Kvotslut(Exception):
    """Speglar leverantörens 429 utan att importera SDK:n."""

    status_code = 429


async def _sparat_mail(storage, **overrides):
    varden = dict(
        provider="imap",
        provider_message_id=f"test-{id(overrides)}",
        from_email="kund@example.com",
        from_name="Kund Kundsson",
        subject="Var är mitt paket?",
        body_text="Beställde för en vecka sedan och inget har kommit.",
    )
    varden.update(overrides)
    return await storage.save_email(DEFAULT_TENANT_ID, **varden)


async def test_kvotfel_far_svensk_text_i_beslutsloggen(monkeypatch):
    """Rå leverantörstext ('prepayment credits are depleted' + faktureringslänk)
    hör hemma i serverloggen — kundens beslutslogg får det svenska beskedet."""
    storage = MemoryStorage()
    mail = await _sparat_mail(storage)

    async def kvoten_slut(*args, **kwargs):
        raise _Kvotslut("Your prepayment credits are depleted. Please go to AI Studio…")

    monkeypatch.setattr(processor, "_triage_email", kvoten_slut)
    resultat = await process_email(storage, DEFAULT_TENANT_ID, mail)

    assert resultat["action"] == "failed"
    assert "kvot är slut" in resultat["error"]
    assert "prepayment" not in resultat["error"]
    beslut = await storage.list_decisions(DEFAULT_TENANT_ID, mail["id"])
    [failed] = [b for b in beslut if b["event"] == "failed"]
    assert "kvot är slut" in failed["detail"]["error"]
    assert "AI Studio" not in failed["detail"]["error"]


async def test_annat_fel_behaller_sin_text(monkeypatch):
    storage = MemoryStorage()
    mail = await _sparat_mail(storage, provider_message_id="test-2")

    async def spricker(*args, **kwargs):
        raise ValueError("kolumnen finns inte")

    monkeypatch.setattr(processor, "_triage_email", spricker)
    resultat = await process_email(storage, DEFAULT_TENANT_ID, mail)
    assert resultat["error"] == "kolumnen finns inte"


async def test_processa_om_kor_om_ett_failed_mail(monkeypatch):
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        mail = await _sparat_mail(storage, provider_message_id="test-3")

        async def kvoten_slut(*args, **kwargs):
            raise _Kvotslut("depleted")

        monkeypatch.setattr(processor, "_triage_email", kvoten_slut)
        await process_email(storage, DEFAULT_TENANT_ID, mail)
        monkeypatch.undo()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            svar = await client.post(
                f"/api/inbox/{mail['id']}/processa-om", headers={"X-API-Key": DEMO_KEY}
            )
            assert svar.status_code == 200
            assert svar.json()["action"] != "failed"

            # Mailet är inte failed längre — en andra omkörning ska vägras,
            # eftersom den hade skapat ett andra ärende för samma mail.
            igen = await client.post(
                f"/api/inbox/{mail['id']}/processa-om", headers={"X-API-Key": DEMO_KEY}
            )
            assert igen.status_code == 409


async def test_processa_om_okant_mail_ger_404():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            svar = await client.post(
                "/api/inbox/finns-inte/processa-om", headers={"X-API-Key": DEMO_KEY}
            )
            assert svar.status_code == 404
