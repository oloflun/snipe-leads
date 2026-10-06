"""Kundtjänst › Översikt: aggregeringen och endpointen."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app
from app.support_oversikt import bygg_oversikt

settings = get_settings()
DEMO = {"X-API-Key": settings.snajp_demo_api_key}
MASTER = {"X-API-Key": settings.snajp_master_api_key}

NU = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)


def _mejl(id_, dagar_sedan, status, *, svar_min=None, kategori="leverans", kb=1):
    mottaget = NU - timedelta(days=dagar_sedan)
    return {
        "id": id_,
        "received_at": mottaget.isoformat(),
        "status": status,
        "category": kategori,
        "escalate": status == "escalated",
        "kb_traffar": kb,
        "forsta_svar": (mottaget + timedelta(minutes=svar_min)).isoformat() if svar_min is not None else None,
    }


def test_handrakning():
    underlag = {
        "mejl": [
            _mejl("a", 1, "auto_sent", svar_min=2),
            _mejl("b", 2, "sent", svar_min=90, kategori="betalning"),
            _mejl("c", 3, "escalated", kb=0),
            _mejl("d", 4, "awaiting_approval"),
            _mejl("e", 40, "auto_sent", svar_min=30),  # förra perioden
        ],
        "korningar": {"antal": 6, "tokens_in": 1000, "tokens_out": 200, "cache": 1, "modell": "vertex:gemini"},
        "kb_artiklar": 12,
    }
    forslag = [
        {"id": "s1", "agent_type": "support", "kind": "kb_article", "status": "ny", "title": "Frakt till Åland", "created_at": "x"},
        {"id": "s2", "agent_type": "leads", "kind": "marknadsinsikt", "status": "ny", "title": "inte en lucka"},
    ]
    ut = bygg_oversikt(underlag, forslag, nu=NU)

    nu = ut["nu"]
    assert (nu["inkomna"], nu["auto"], nu["godkant"], nu["manniska"], nu["vantar"]) == (4, 1, 1, 1, 1)
    assert nu["svarstid_median"] == 46  # median av 2 och 90
    assert nu["inom_timme"] == 0.5
    assert nu["kb_traff"] == 0.75
    assert ut["forra"]["inkomna"] == 1 and ut["forra"]["svarstid_median"] == 30

    assert len(ut["veckor"]) == 12
    assert sum(v["inkomna"] for v in ut["veckor"]) == 5

    assert {h["id"]: h["antal"] for h in ut["svarstider"]} == {"15m": 1, "1h": 0, "4h": 1, "24h": 0, "mer": 0}
    assert ut["kategorier"][0] == {"id": "leverans", "antal": 3, "eskalerade": 1}
    assert ut["vantande"]["antal"] == 1
    assert ut["kb_luckor"]["antal"] == 1 and ut["kb_luckor"]["rader"][0]["titel"] == "Frakt till Åland"
    assert ut["drift"]["korningar"] == 6 and ut["drift"]["kb_artiklar"] == 12


def test_tom_kund_ger_nollor_inte_fel():
    ut = bygg_oversikt({"mejl": [], "korningar": {}}, [], nu=NU)
    assert ut["nu"]["inkomna"] == 0
    assert ut["nu"]["svarstid_median"] is None and ut["nu"]["kb_traff"] is None
    assert ut["vantande"] == {"antal": 0, "aldsta": None}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_endpointen_raknar_demons_mejl():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            seeded = await client.post("/api/inbox/mock", headers=DEMO, json={"count": 3})
            assert seeded.status_code == 201
            svar = await client.get("/api/support/oversikt", headers=DEMO)
            assert svar.status_code == 200
            kropp = svar.json()
            assert kropp["nu"]["inkomna"] >= 3
            assert len(kropp["veckor"]) == 12


@pytest.mark.anyio
async def test_riktig_kund_raknar_inte_testmail():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            skapad = await client.post(
                "/api/keys",
                headers=MASTER,
                json={"tenant_name": "Översiktsbolaget AB", "slug": "oversiktsbolaget"},
            )
            assert skapad.status_code == 201
            nyckel = {"X-API-Key": skapad.json()["api_key"]}
            assert (await client.post("/api/inbox/mock", headers=nyckel)).status_code == 201
            kropp = (await client.get("/api/support/oversikt", headers=nyckel)).json()
            assert kropp["nu"]["inkomna"] == 0


@pytest.mark.anyio
async def test_kraver_nyckel():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            assert (await client.get("/api/support/oversikt")).status_code in (401, 403)
