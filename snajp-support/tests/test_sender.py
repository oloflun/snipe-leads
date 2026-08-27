"""Supportsvarens sändväg (email_pipeline/sender.py): 'sent' får aldrig ljuga.

Fyra lägen, fyra sanningar: riktig sändning, simulering, testmejl och
misslyckande. Plus godkännandevägens ordning — misslyckas sändningen ska
utkastet stå kvar som pending och API:t svara 502.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.email_pipeline import sender as sender_modul
from app.email_pipeline.sender import (
    NOT_MOTTAGARE_SAKNAS,
    NOT_SIMULERAT,
    NOT_TESTMEJL,
    SandningsFel,
    skicka_supportsvar,
)
from app.leads.send_provider import LoggingSendProvider
from app.main import app

pytestmark = pytest.mark.anyio

DEMO_KEY = get_settings().snajp_demo_api_key


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _Skickare:
    """Provider som levererar — och minns vad den skickade."""

    levererar = True

    def __init__(self, *, spricker: bool = False):
        self.spricker = spricker
        self.skickade: list[dict] = []

    async def send(self, *, to: str, subject: str, body: str) -> None:
        if self.spricker:
            raise RuntimeError("SMTP nere")
        self.skickade.append({"to": to, "subject": subject, "body": body})


def _mejlrad(**overrides) -> dict:
    rad = {
        "id": "e-1",
        "provider": "imap",
        "from_email": "kund@example.com",
        "subject": "Var är mitt paket?",
    }
    rad.update(overrides)
    return rad


async def test_riktig_sandning_skickar_och_sager_det():
    provider = _Skickare()
    notering = await skicka_supportsvar(_mejlrad(), content="Hej! Svar.", provider=provider)
    assert "kund@example.com" in notering and "SMTP" in notering
    [skickat] = provider.skickade
    assert skickat["to"] == "kund@example.com"
    assert skickat["subject"] == "Re: Var är mitt paket?"


async def test_re_dubbleras_inte():
    provider = _Skickare()
    await skicka_supportsvar(
        _mejlrad(subject="Re: Var är mitt paket?"), content="Svar.", provider=provider
    )
    assert provider.skickade[0]["subject"] == "Re: Var är mitt paket?"


async def test_testmejl_skickas_aldrig():
    """'Hämta testmail' använder verkliga domäner (anna.lindqvist@mail.se) —
    ett godkänt testärende övar flödet, det mejlar inte en främling."""
    provider = _Skickare()
    notering = await skicka_supportsvar(
        _mejlrad(provider="mock"), content="Svar.", provider=provider
    )
    assert notering == NOT_TESTMEJL
    assert provider.skickade == []


async def test_simulering_utan_sandvag():
    notering = await skicka_supportsvar(
        _mejlrad(), content="Svar.", provider=LoggingSendProvider()
    )
    assert notering == NOT_SIMULERAT


async def test_saknad_mottagare_ar_notering_inte_fel():
    provider = _Skickare()
    notering = await skicka_supportsvar(
        _mejlrad(from_email=""), content="Svar.", provider=provider
    )
    assert notering == NOT_MOTTAGARE_SAKNAS
    assert provider.skickade == []


async def test_misslyckad_riktig_sandning_kastar():
    with pytest.raises(SandningsFel):
        await skicka_supportsvar(
            _mejlrad(), content="Svar.", provider=_Skickare(spricker=True)
        )


# -- Godkännandevägen genom API:t --------------------------------------------


async def _skapa_pending_draft(client) -> str:
    """Testmail in → processas → första pending-utkastet."""
    seeded = await client.post(
        "/api/inbox/mock", headers={"X-API-Key": DEMO_KEY}, json={"count": 3}
    )
    assert seeded.status_code in (200, 201)
    inbox = await client.get("/api/inbox", headers={"X-API-Key": DEMO_KEY})
    for mejl in inbox.json()["emails"]:
        draft = (mejl.get("draft") or {})
        if draft.get("status") == "pending":
            return draft["id"]
    raise AssertionError("Inget pending-utkast bland testmejlen.")


async def test_approve_502_och_pending_kvar_nar_sandningen_spricker(monkeypatch):
    """Ordningskontraktet i api/drafts.py: sändning FÖRE status. OBS att
    testmejl normalt aldrig skickas — här tvingas sändvägen att försöka
    genom att mock-spärren i sender anropas med en provider som spricker
    och en mejlrad som inte är mock."""
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            draft_id = await _skapa_pending_draft(client)

            async def spricker(email, *, content, provider=None):
                raise SandningsFel("Svaret kunde inte skickas.")

            # Patcha namnet drafts.py importerade.
            import app.api.drafts as drafts_modul

            monkeypatch.setattr(drafts_modul, "skicka_supportsvar", spricker)

            svar = await client.post(
                f"/api/drafts/{draft_id}/approve",
                headers={"X-API-Key": DEMO_KEY},
                json={},
            )
            assert svar.status_code == 502

            # Utkastet står kvar som pending — inget markerades som skickat.
            inbox = await client.get("/api/inbox", headers={"X-API-Key": DEMO_KEY})
            statusar = {
                (m.get("draft") or {}).get("id"): (m.get("draft") or {}).get("status")
                for m in inbox.json()["emails"]
            }
            assert statusar.get(draft_id) == "pending"


async def test_approve_av_testmejl_skickar_inget_och_sager_det():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            draft_id = await _skapa_pending_draft(client)
            svar = await client.post(
                f"/api/drafts/{draft_id}/approve",
                headers={"X-API-Key": DEMO_KEY},
                json={},
            )
            assert svar.status_code == 200

            # Beslutsloggen ska bära testmejlsnoteringen, inte "skickat".
            inbox = await client.get("/api/inbox", headers={"X-API-Key": DEMO_KEY})
            mejl = next(
                m for m in inbox.json()["emails"]
                if (m.get("draft") or {}).get("id") == draft_id
            )
            detalj = await client.get(
                f"/api/inbox/{mejl['id']}", headers={"X-API-Key": DEMO_KEY}
            )
            noteringar = [
                (d.get("detail") or {}).get("note")
                for d in detalj.json().get("decisions", [])
                if d.get("event") == "approved_and_sent"
            ]
            assert noteringar == [NOT_TESTMEJL]
