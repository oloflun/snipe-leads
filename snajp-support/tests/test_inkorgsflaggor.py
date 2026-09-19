"""Inkorgsflaggorna (migration 071): offert-/prisförfrågan, utbildnings-
intresse och den manuella hanterad-markeringen.

Livrustnings hela tratt är "kontakta oss för offert" — flaggan är pilotens
viktigaste sorteringssignal och får inte bero på vilket fack triagen valde.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.email_pipeline.flaggor import ar_offertforfragan, ar_utbildningsintresse
from app.email_pipeline.processor import process_email
from app.main import app
from app.storage.memory import MemoryStorage

pytestmark = pytest.mark.anyio

DEMO_KEY = get_settings().snajp_demo_api_key


@pytest.fixture
def anyio_backend():
    return "asyncio"


# -- Vokabulären ------------------------------------------------------------


def test_offertord_traffar():
    assert ar_offertforfragan("Offertförfrågan", "")
    assert ar_offertforfragan("", "Vad kostar en säkerhetsdag för 40 personer?")
    assert ar_offertforfragan("", "Kan ni skicka ett prisförslag?")
    assert ar_offertforfragan("", "vad skulle det landa på för oss?")


def test_offert_traffar_inte_pa_slump():
    assert not ar_offertforfragan("Fråga om intyg", "När kommer mitt utbildningsintyg?")
    # "prisad" är inte "pris" — ordgränsen ska hålla.
    assert not ar_offertforfragan("", "Er instruktör var mycket prisad av personalen.")


def test_utbildningsord_traffar():
    assert ar_utbildningsintresse("HLR för personalen", "")
    assert ar_utbildningsintresse("", "Vi vill boka en säkerhetsdag i höst.")
    assert ar_utbildningsintresse("", "Har ni kurser i första hjälpen?")


def test_modellens_bedomning_racker_utan_nyckelord():
    triage = {"offertforfragan": True, "utbildningsintresse": False, "category": "ovrigt"}
    assert ar_offertforfragan("Hej", "Hur mycket för 40 pers?", triage)
    assert not ar_utbildningsintresse("Hej", "Hur mycket for 40 pers?", triage)


def test_facket_utbildning_raknas_alltid():
    triage = {"category": "utbildning"}
    assert ar_utbildningsintresse("Hej", "…", triage)


# -- Genom pipelinen --------------------------------------------------------


async def test_klassificeringen_bar_flaggorna():
    storage = MemoryStorage()
    mail = await storage.save_email(
        DEFAULT_TENANT_ID,
        provider="imap",
        provider_message_id="flagg-1",
        from_email="peter@example.com",
        from_name="Peter",
        subject="Offert på HLR-utbildning",
        body_text="Vad kostar en HLR-utbildning för hela personalen?",
    )
    await process_email(storage, DEFAULT_TENANT_ID, mail)

    sparat = await storage.get_email(DEFAULT_TENANT_ID, mail["id"])
    klass = sparat["classification"]
    assert klass["offertforfragan"] is True
    assert klass["utbildningsintresse"] is True


async def test_vanligt_mail_far_inga_flaggor():
    storage = MemoryStorage()
    mail = await storage.save_email(
        DEFAULT_TENANT_ID,
        provider="imap",
        provider_message_id="flagg-2",
        from_email="kund@example.com",
        from_name="Kund",
        subject="Var är mitt paket?",
        body_text="Beställde för en vecka sedan och inget har kommit.",
    )
    await process_email(storage, DEFAULT_TENANT_ID, mail)

    sparat = await storage.get_email(DEFAULT_TENANT_ID, mail["id"])
    klass = sparat["classification"]
    assert klass["offertforfragan"] is False
    assert klass["utbildningsintresse"] is False


# -- Hanterad-markeringen ---------------------------------------------------


async def test_hanterad_stamplar_och_angrar():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        mail = await storage.save_email(
            DEFAULT_TENANT_ID,
            provider="imap",
            provider_message_id="hanterad-1",
            from_email="kund@example.com",
            from_name="Kund",
            subject="Fråga",
            body_text="En fråga.",
        )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            svar = await client.post(
                f"/api/inbox/{mail['id']}/hanterad", headers={"X-API-Key": DEMO_KEY}
            )
            assert svar.status_code == 200
            assert svar.json()["hanterad_at"]

            # Stämpeln syns i listan — det är den kolumn UI:t sorterar på.
            lista = await client.get(
                "/api/inbox", headers={"X-API-Key": DEMO_KEY}, params={"is_test": "false"}
            )
            rad = next(e for e in lista.json()["emails"] if e["id"] == mail["id"])
            assert rad["hanterad_at"]

            angrat = await client.post(
                f"/api/inbox/{mail['id']}/hanterad",
                headers={"X-API-Key": DEMO_KEY},
                json={"hanterad": False},
            )
            assert angrat.status_code == 200
            assert angrat.json()["hanterad_at"] is None


async def test_hanterad_okant_mail_ger_404():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            svar = await client.post(
                "/api/inbox/finns-inte/hanterad", headers={"X-API-Key": DEMO_KEY}
            )
            assert svar.status_code == 404
