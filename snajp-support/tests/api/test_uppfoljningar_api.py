"""Leads › Uppföljningar och bolagssökningen (app/api/leads_uppfoljningar.py),
mot MemoryStorage genom HTTP-lagret, och fackens rena policy."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.leads_uppfoljningar import fordela, skickade_uppfoljningar
from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}
T = DEFAULT_TENANT_ID
NU = datetime(2026, 11, 23, 9, 0, tzinfo=timezone.utc)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _trad(pid: str, *, skickade: int, dagar_sedan: int, **extra) -> dict:
    return {
        "id": f"t-{pid}", "prospect_id": pid, "company_name": pid, "origin": "iris",
        "outbound_sent_count": skickade, "last_outbound_sent_at": (NU - timedelta(days=dagar_sedan)).isoformat(),
        **extra,
    }


def test_facken_foljer_svepets_policy():
    tradar = [
        _trad("forfallen", skickade=1, dagar_sedan=10),
        _trad("kommande", skickade=2, dagar_sedan=1),
        _trad("vantar", skickade=1, dagar_sedan=10),
        _trad("skrivs", skickade=1, dagar_sedan=10),
        _trad("svarat", skickade=1, dagar_sedan=10, last_inbound_at=NU.isoformat()),
        _trad("klar", skickade=5, dagar_sedan=30),
        _trad("aldrig", skickade=0, dagar_sedan=30),
    ]
    fack = fordela(
        tradar,
        lagen={"vantar": {"antal_osanda": 1, "queue_item_id": "q1", "ko_status": "awaiting_review"}},
        utkastjobb={"skrivs": {"status": "processing"}},
        automation=None,
        now=NU,
    )
    namn = {k: [r["prospect_id"] for r in v] for k, v in fack.items()}
    assert namn["forfallna"] == ["forfallen"]
    assert namn["kommande"] == ["kommande"] and fack["kommande"][0]["nummer"] == 2
    assert namn["vantar"] == ["vantar"] and fack["vantar"][0]["queue_item_id"] == "q1"
    assert namn["skrivs"] == ["skrivs"]
    alla = sum(namn.values(), [])
    assert "svarat" not in alla and "klar" not in alla and "aldrig" not in alla


def test_skickade_numreras_ur_trådens_antal():
    skickat = [
        {"id": "m2", "thread_id": "t", "prospect_id": "p", "sent_at": (NU - timedelta(days=2)).isoformat()},
        {"id": "m3", "thread_id": "t", "prospect_id": "p", "sent_at": (NU - timedelta(days=1)).isoformat()},
    ]
    # Tre skickade i tråden, det första utanför fönstret: m2 är uppföljning 1.
    ut = skickade_uppfoljningar(skickat, {"t": {"outbound_sent_count": 3}}, now=NU)
    assert [(r["message_id"], r["nummer"]) for r in ut] == [("m3", 2), ("m2", 1)]


async def _skickat_lead(storage, namn: str, *, dagar: int = 10) -> dict:
    p = await storage.create_prospect(T, company_name=namn, contact_email=f"vd@{namn.split()[0].lower()}.se")
    trad = await storage.ensure_outreach_thread(T, prospect_id=p["id"])
    koat = await storage.queue_outreach_message(
        T, thread_id=trad["id"], subject="Hej", body="Första mejlet.", humanizer_variant="v",
        scheduled_at=datetime.now(timezone.utc) - timedelta(days=dagar),
    )
    await storage.mark_outreach_message_sent(
        T, koat["message"]["id"], (datetime.now(timezone.utc) - timedelta(days=dagar)).isoformat()
    )
    await storage.update_send_queue_status(T, koat["queue_item"]["id"], status="sent", gate_checks={})
    await storage.update_prospect(T, p["id"], status="contacted")
    return p


async def test_listan_och_skapa_for_markerade():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        forfallen = await _skickat_lead(storage, "Forfallen Bygg AB")
        ny = await storage.create_prospect(T, company_name="Aldrig Kontaktad AB", contact_email="vd@aldrig.se")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as klient:
            lista = (await klient.get("/api/leads/uppfoljningar", headers=DEMO)).json()
            assert forfallen["id"] in [r["prospect_id"] for r in lista["forfallna"]]

            jobb = AsyncMock(return_value=[{"job_id": "j1", "prospect_id": forfallen["id"]}])
            with patch("app.api.leads._lagg_prospektjobb", new=jobb), patch(
                "app.api.leads._require_live_llm", new=lambda: None
            ):
                svar = await klient.post(
                    "/api/leads/uppfoljningar/skapa", headers=DEMO,
                    json={"prospect_ids": [forfallen["id"], ny["id"]]},
                )
            assert svar.status_code == 202, svar.text
            assert svar.json()["count"] == 1 and svar.json()["hoppade"] == {"inget_skickat": [ny["id"]]}
            assert jobb.call_args.kwargs["scope"] == "utkast"
            assert [p["id"] for p in jobb.call_args.args[2]] == [forfallen["id"]]


async def test_bolagssokningen_hittar_aven_kontaktade():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        lead = await _skickat_lead(storage, "Sökbara Snickeri AB")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as klient:
            traffar = (await klient.get("/api/leads/sok", params={"q": "sökbara"}, headers=DEMO)).json()["traffar"]
            assert traffar[0]["id"] == lead["id"] and traffar[0]["skickade"] == 1
            assert "webbrevision" not in str(traffar)
            assert (await klient.get("/api/leads/sok", params={"q": "s"}, headers=DEMO)).json() == {"traffar": []}
