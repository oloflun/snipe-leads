"""Ringlistan och återkopplingen (leadsregel 15 och 17, 2026-10-07).

Utfallet flyttar prospektets status i samma anrop, så att listorna och
mejlflödet aldrig är oense; ej svar och återkom tar fram leadet igen när det
är dags. API:t prövas över HTTP mot appen i minne."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.leads import samtal
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}
TENANT = "00000000-0000-4000-a000-000000000001"

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# -- Rena regler ----------------------------------------------------------------


def test_ej_svar_kommer_tillbaka_efter_tva_arbetsdagar_over_helgen():
    fredag = {"utfall": "ej_svar", "created_at": "2026-10-09T09:00:00+00:00"}
    assert samtal.nasta_samtal(fredag) == date(2026, 10, 13)  # tisdag


def test_helgdag_raknas_inte_som_arbetsdag():
    assert samtal.plus_arbetsdagar(date(2026, 12, 23), 2) == date(2026, 12, 29)


def test_avslutande_utfall_tar_bort_leadet_och_aterkom_galler_sitt_datum():
    assert samtal.nasta_samtal({"utfall": "ej_intresserad", "created_at": "2026-10-08"}) is None
    aterkom = {"utfall": "aterkom", "aterkom_datum": "2026-11-02", "created_at": "2026-10-08"}
    assert samtal.nasta_samtal(aterkom) == date(2026, 11, 2)
    assert samtal.nasta_samtal(None) == date.min


def _p(pid: str, **k) -> dict:
    return {"id": pid, "company_name": pid, "origin": "iris", "status": "contacted", "contact_phone": "031-1", **k}


def test_aterkopplingen_tar_kontaktade_med_telefon_aldst_forst_och_dagens_overst():
    prospekter = [
        _p("ny-kontakt"),
        _p("gammal-kontakt"),
        _p("ringd-igar"),
        _p("utan-telefon", contact_phone=None),
        _p("svarat", status="replied"),
        _p("ring", origin="ring", status="new"),
        _p("arkiverad", arkiverad_at="2026-10-01"),
    ]
    forsta = {
        "ny-kontakt": "2026-10-07T08:00:00+00:00",
        "gammal-kontakt": "2026-09-01T08:00:00+00:00",
        "ringd-igar": "2026-08-01T08:00:00+00:00",
    }
    historik = [{"prospect_id": "ringd-igar", "utfall": "ej_svar", "created_at": "2026-10-07T10:00:00+00:00"}]
    rader = samtal.samtalslista(prospekter, historik, forsta, lista="aterkoppling", idag=date(2026, 10, 8))
    assert [r["prospect_id"] for r in rader] == ["gammal-kontakt", "ny-kontakt", "ringd-igar"]
    assert [r["ring_idag"] for r in rader] == [True, True, False]
    assert rader[2]["nasta"] == "2026-10-09"
    assert rader[0]["kontaktad"] == "2026-09-01"


def test_ringlistan_tar_bara_ringsparet_som_inte_avslutats():
    prospekter = [
        {"id": "a", "origin": "ring", "status": "new", "contact_phone": "08-1", "anstallda": 3},
        {"id": "b", "origin": "ring", "status": "lost", "contact_phone": "08-2"},
        {"id": "c", "origin": "iris", "status": "contacted", "contact_phone": "08-3"},
    ]
    rader = samtal.samtalslista(prospekter, [], {}, lista="ring", idag=date(2026, 10, 8))
    assert [(r["prospect_id"], r["anstallda"]) for r in rader] == [("a", 3)]


# -- Över HTTP ------------------------------------------------------------------


async def _kontaktad(namn: str) -> dict:
    storage = app.state.storage
    p = await storage.create_prospect(
        TENANT, company_name=namn, contact_email=f"info@{namn.lower()}.se", origin="iris",
        profil={"contact_phone": "031-123 45 67"},
    )
    await storage.update_prospect(TENANT, p["id"], status="contacted")
    return p


async def test_ej_intresserad_avslutar_och_stoppar_vantande_utkast():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        p = await _kontaktad("Avslut")
        trad = await storage.ensure_outreach_thread(TENANT, prospect_id=p["id"])
        await storage.queue_outreach_message(
            TENANT, thread_id=trad["id"], body="uppföljning", subject="Ä", humanizer_variant="v1",
            scheduled_at=datetime(2026, 10, 9, 8, tzinfo=timezone.utc), status="awaiting_review",
        )
        async with _client() as client:
            svar = await client.post(
                f"/api/leads/prospects/{p['id']}/samtal", headers=DEMO,
                json={"utfall": "ej_intresserad", "anteckning": "Har redan en lösning"},
            )
            assert svar.status_code == 201, svar.text
            assert (await storage.get_prospect(TENANT, p["id"]))["status"] == "lost"
            assert await storage.get_pending_outreach_message(TENANT, trad["id"]) is None
            linje = (await client.get(f"/api/leads/prospects/{p['id']}/tidslinje", headers=DEMO)).json()["handelser"]
            assert ("samtal", "ej_intresserad") in [(h["typ"], h["rubrik"]) for h in linje]
            lista = (await client.get("/api/leads/samtal", headers=DEMO)).json()["rader"]
            assert p["id"] not in [r["prospect_id"] for r in lista]


async def test_kontakta_inte_sparrar_adressen():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        p = await _kontaktad("Sparr")
        async with _client() as client:
            svar = await client.post(
                f"/api/leads/prospects/{p['id']}/samtal", headers=DEMO, json={"utfall": "kontakta_inte"}
            )
            assert svar.status_code == 201, svar.text
        assert (await storage.get_prospect(TENANT, p["id"]))["status"] == "suppressed"
        assert "info@sparr.se" in await storage.list_suppressions(TENANT)


async def test_aterkom_kraver_datum_och_flyttar_ner_leadet():
    async with app.router.lifespan_context(app):
        p = await _kontaktad("Aterkom")
        async with _client() as client:
            fel = await client.post(f"/api/leads/prospects/{p['id']}/samtal", headers=DEMO, json={"utfall": "aterkom"})
            assert fel.status_code == 422
            ok = await client.post(
                f"/api/leads/prospects/{p['id']}/samtal", headers=DEMO,
                json={"utfall": "aterkom", "aterkom_datum": "2099-01-05"},
            )
            assert ok.status_code == 201, ok.text
            rader = (await client.get("/api/leads/samtal", headers=DEMO)).json()["rader"]
            rad = next(r for r in rader if r["prospect_id"] == p["id"])
            assert (rad["nasta"], rad["ring_idag"], rad["senaste_utfall"]) == ("2099-01-05", False, "aterkom")


async def test_samtal_till_ringlistan_gor_bolaget_kontaktat():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        p = await storage.create_prospect(
            TENANT, company_name="Ringbolaget", origin="ring", contact_name="Eva VD",
            profil={"contact_phone": "08-1", "contact_role": "VD", "anstallda": 4},
        )
        async with _client() as client:
            rader = (await client.get("/api/leads/samtal?lista=ring", headers=DEMO)).json()["rader"]
            assert [r["contact_name"] for r in rader if r["prospect_id"] == p["id"]] == ["Eva VD"]
            await client.post(f"/api/leads/prospects/{p['id']}/samtal", headers=DEMO, json={"utfall": "ej_svar"})
        assert (await storage.get_prospect(TENANT, p["id"]))["status"] == "contacted"


async def test_antalet_ar_samma_som_listornas_ring_idag():
    """Att göra läser /samtal/antal i stället för båda listorna hela."""
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        await _kontaktad("Antal")
        await storage.create_prospect(
            TENANT, company_name="Ringantal", origin="ring", contact_name="Per VD",
            profil={"contact_phone": "08-2", "contact_role": "VD", "anstallda": 3},
        )
        async with _client() as client:
            antal = (await client.get("/api/leads/samtal/antal", headers=DEMO)).json()
            for lista in ("aterkoppling", "ring"):
                fullt = (await client.get(f"/api/leads/samtal?lista={lista}", headers=DEMO)).json()
                assert antal[lista] == fullt["ring_idag"], lista
            assert antal["ring"] >= 1

