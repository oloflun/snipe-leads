"""Leads › Konversationer genom HTTP-lagret, mot MemoryStorage (migration 149).

Fallet är Telecom Buddy hos kunden snajp (main 2026-11-22): två skickade
mejl, svar från prospektet, ett svarsutkast som påstår att en inbjudan är
skickad och som ligger kvar utan aktiv köpost, och ett möte som bokades från
Sebastians Gmail och bara syns i prospektets citat."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

from ..leads.test_konversation import HENRIKS_SVAR, VART_MEJL

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}
T = DEFAULT_TENANT_ID

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _klient() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _buddy(storage) -> tuple[str, str, str]:
    prospekt = await storage.create_prospect(T, company_name="Telecom Buddy AB", contact_email="tomas@buddy.se")
    trad = await storage.ensure_outreach_thread(T, prospect_id=prospekt["id"])
    for dagar in (31, 10):
        koat = await storage.queue_outreach_message(
            T, thread_id=trad["id"], subject="En tanke", body=VART_MEJL, humanizer_variant="v",
            scheduled_at=datetime.now(timezone.utc) - timedelta(days=dagar),
        )
        await storage.mark_outreach_message_sent(
            T, koat["message"]["id"], (datetime.now(timezone.utc) - timedelta(days=dagar)).isoformat()
        )
        await storage.update_send_queue_status(T, koat["queue_item"]["id"], status="sent", gate_checks={})
    await storage.record_inbound_reply(T, thread_id=trad["id"], body=HENRIKS_SVAR)
    await storage.update_prospect(T, prospekt["id"], status="replied")
    utkast = await storage.queue_outreach_message(
        T, thread_id=trad["id"], subject="Re: demo",
        body="Hej Tomas,\n\nTack! Jag har skickat en inbjudan till måndag kl 10.",
        humanizer_variant="v", scheduled_at=datetime.now(timezone.utc), status="awaiting_review",
    )
    # Köposten är inställd men utkastet ligger kvar: det syntes ingenstans.
    await storage.update_send_queue_status(T, utkast["queue_item"]["id"], status="cancelled", gate_checks={})
    await storage.logga_handelse(T, prospect_id=prospekt["id"], thread_id=trad["id"], typ="svar", notis=True)
    return prospekt["id"], trad["id"], utkast["message"]["id"]


async def test_buddy_syns_som_trad_med_redigerbart_utkast():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        pid, tid, mid = await _buddy(storage)
        async with _klient() as klient:
            lista = (await klient.get("/api/leads/konversationer", headers=DEMO)).json()
            rad = next(r for r in lista["konversationer"] if r["thread_id"] == tid)
            assert rad["steg"] == "svarat" and rad["att_gora"] and rad["olasta"] == 1
            assert rad["utkast"]["message_id"] == mid and rad["utkast"]["flaggat"]
            assert rad["senaste_svar"]["utdrag"].startswith("Toppen!")
            assert lista["sammanfattning"]["utkast_vantar"] >= 1

            trad = (await klient.get(f"/api/leads/konversationer/{tid}", headers=DEMO)).json()
            assert trad["utkast"]["handlingar"] == ["Jag har skickat en inbjudan till måndag kl 10"]
            assert [e["avsandare"] for e in trad["externa"]] == ["sebastian@snajp.se"]
            assert trad["forslag_mote"] is True
            assert [m["typ"] for m in trad["meddelanden"]].count("skickat") == 2
            # Webbplatsbedömningen finns inte i konversationen.
            assert "webbrevision" not in str(trad) and "webbniva" not in str(trad)

            sparat = await klient.put(
                f"/api/leads/konversationer/{tid}/utkast", headers=DEMO,
                json={"subject": "Re: demo", "brodtext": "Hej Tomas,\n\nPassar måndag kl 10? Då skickar jag en inbjudan."},
            )
            assert sparat.status_code == 200 and sparat.json()["handlingar"] == []

            lasta = (await klient.post(f"/api/leads/konversationer/{tid}/last", headers=DEMO)).json()
            assert lasta["lasta"] == 1


async def test_skicka_kraver_bekraftelse_och_skapar_kopost():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        pid, tid, mid = await _buddy(storage)
        skicka = AsyncMock(return_value=("sent", None))
        with patch("app.leads.scheduler.skicka_godkant", new=skicka):
            async with _klient() as klient:
                nej = await klient.post(f"/api/leads/konversationer/{tid}/utkast/skicka", headers=DEMO, json={})
                assert nej.status_code == 409
                skicka.assert_not_called()
                ja = await klient.post(
                    f"/api/leads/konversationer/{tid}/utkast/skicka", headers=DEMO,
                    json={"bekraftat_handlingar": True},
                )
        assert ja.status_code == 200 and ja.json()["utfall"] == "sent"
        item_id = skicka.call_args.args[2]
        post = await storage.get_send_queue_item(T, item_id)
        assert post["thread_id"] == tid and post["status"] == "awaiting_review"
        typer = [h["typ"] for h in await storage.list_handelser(T, thread_id=tid)]
        assert "skickat" in typer


async def test_mote_bokat_rakns_som_mote_i_skickat():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        pid, tid, mid = await _buddy(storage)
        async with _klient() as klient:
            svar = await klient.post(f"/api/leads/konversationer/{tid}/steg", headers=DEMO, json={"steg": "mote"})
            assert svar.status_code == 200 and svar.json()["kasserat"] == mid
            skickat = (await klient.get("/api/leads/skickat", headers=DEMO)).json()["skickat"]
            assert {r["status"] for r in skickat if r.get("prospect_id") == pid} == {"meeting"}
            trad = (await klient.get(f"/api/leads/konversationer/{tid}", headers=DEMO)).json()
            assert trad["trad"]["steg"] == "mote" and trad["forslag_mote"] is False
            # Det kasserade utkastet syns och går att återställa.
            kasserat = next(m for m in trad["meddelanden"] if m["id"] == mid)
            assert kasserat["typ"] == "kasserat"
            ater = await klient.post(f"/api/leads/konversationer/{tid}/utkast/{mid}/aterstall", headers=DEMO)
            assert ater.status_code == 200
            assert (await storage.get_pending_outreach_message(T, tid))["id"] == mid
            assert any(p["status"] == "awaiting_review" for p in await storage.list_pending_sends(T, tid))

            aterkom = await klient.post(f"/api/leads/konversationer/{tid}/steg", headers=DEMO, json={"steg": "aterkom"})
            assert aterkom.status_code == 422


async def test_notiserna_och_extern_mejl():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        pid, tid, mid = await _buddy(storage)
        async with _klient() as klient:
            antal = (await klient.get("/api/leads/notiser/antal", headers=DEMO)).json()["olasta"]
            assert antal >= 1
            notiser = (await klient.get("/api/leads/notiser", headers=DEMO)).json()
            egen = next(n for n in notiser["notiser"] if n["thread_id"] == tid)
            assert egen["company_name"] == "Telecom Buddy AB" and egen["last"] is False
            alla = (await klient.post("/api/leads/notiser/last", headers=DEMO, json={})).json()
            assert alla["olasta"] == 0

            ny = await klient.post(
                f"/api/leads/konversationer/{tid}/extern", headers=DEMO,
                json={"riktning": "outbound", "text": "Ringde Tomas, mötet står.", "tid": "2026-11-19T09:00:00+01:00"},
            )
            assert ny.status_code == 201
            trad = (await klient.get(f"/api/leads/konversationer/{tid}", headers=DEMO)).json()
            assert [e["kalla"] for e in trad["externa"]] == ["citat", "manuell"]


async def test_kassera_och_okand_trad():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        pid, tid, mid = await _buddy(storage)
        async with _klient() as klient:
            assert (await klient.post(f"/api/leads/konversationer/{tid}/utkast/kassera", headers=DEMO)).status_code == 200
            assert await storage.get_pending_outreach_message(T, tid) is None
            assert (await klient.post(f"/api/leads/konversationer/{tid}/utkast/kassera", headers=DEMO)).status_code == 409
            okand = "00000000-0000-4000-a000-0000000000ff"
            assert (await klient.get(f"/api/leads/konversationer/{okand}", headers=DEMO)).status_code == 404
