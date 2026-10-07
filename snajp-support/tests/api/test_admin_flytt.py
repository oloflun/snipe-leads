"""Flytta till main (plan del E, migration 085, INV-DATA-003): den enda vägen
från development till main är ett HMAC-signerat paket som mottagaren vägrar i
en spegel. Avsändarsidan ligger bakom masternyckeln; mottagarsidan bakom
signaturen."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.api import admin_flytt
from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("FLYTT_NYCKEL", "test-flyttnyckel-inte-riktig-0000")
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


def _master(client: TestClient) -> dict[str, str]:
    return {"X-API-Key": get_settings().snajp_master_api_key}


def _demo(client: TestClient) -> dict[str, str]:
    return {"X-API-Key": get_settings().snajp_demo_api_key}


def _slug(client) -> str:
    rad = client.get("/api/admin/tenants", headers=_master(client)).json()
    tenants = rad["tenants"] if isinstance(rad, dict) else rad
    return next(t["slug"] for t in tenants if t["id"] == DEFAULT_TENANT_ID)


def test_avsandarsidan_ar_bara_for_masternyckeln(client):
    assert client.get("/api/admin/flytt/status").status_code == 401
    assert client.get("/api/admin/flytt/status", headers=_demo(client)).status_code == 403
    svar = client.get("/api/admin/flytt/status", headers=_master(client))
    assert svar.status_code == 200
    assert svar.json()["spegel"] is None  # minneslagret är ingen spegel
    assert svar.json()["nyckel_konfigurerad"] is True


def test_importera_vagrar_utan_och_med_fel_signatur(client):
    paket = {"version": 1, "fran": "development", "tenant_id": DEFAULT_TENANT_ID, "tenant_slug": "x", "typ": "mejl", "poster": []}
    kropp = json.dumps(paket, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert client.post("/api/admin/flytt/importera", content=kropp, headers={"Content-Type": "application/json"}).status_code == 403
    assert client.post(
        "/api/admin/flytt/importera", content=kropp,
        headers={"Content-Type": "application/json", admin_flytt.SIGNATURHUVUD: "0" * 64},
    ).status_code == 403


def test_importera_vagrar_i_en_spegel(client, monkeypatch):
    async def _spegel():
        return {"environment": "development", "seeded_at": None}

    monkeypatch.setattr(app.state.storage, "spegel_info", _spegel, raising=False)
    paket = {"version": 1, "fran": "development", "tenant_id": DEFAULT_TENANT_ID, "tenant_slug": "x", "typ": "mejl", "poster": []}
    kropp = json.dumps(paket, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sig = admin_flytt.signera(paket, get_settings().flytt_nyckel)
    svar = client.post(
        "/api/admin/flytt/importera", content=kropp,
        headers={"Content-Type": "application/json", admin_flytt.SIGNATURHUVUD: sig},
    )
    assert svar.status_code == 409


async def test_paket_och_import_hela_vagen(client):
    """Mejl: paketet byggs av avsändarsidan, signeras, och importeras
    idempotent — andra gången är kvittot 'redan flyttad'."""
    storage = app.state.storage
    e = await storage.save_email(
        DEFAULT_TENANT_ID, provider="imap", provider_message_id="flytt-1", from_email="kund@exempel.se",
        from_name="Kund", subject="Fråga om garanti", body_text="Hej, gäller garantin?", is_test=True,
    )
    await storage.update_email(DEFAULT_TENANT_ID, e["id"], klass="support", klass_kalla="standard")
    slug = _slug(client)
    svar = client.post("/api/admin/flytt/paket", headers=_master(client), json={"slug": slug, "typ": "mejl", "ids": [e["id"]]})
    assert svar.status_code == 200, svar.text
    paket, signatur = svar.json()["paket"], svar.json()["signatur"]
    assert paket["poster"][0]["provider_message_id"] == "flytt-1" and paket["poster"][0]["klass"] == "support"
    assert signatur == admin_flytt.signera(paket, get_settings().flytt_nyckel)

    # Mottagaren: samma lager → mejlet finns redan → redan flyttad (idempotent).
    kropp = json.dumps(paket, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    ut = client.post("/api/admin/flytt/importera", content=kropp,
                     headers={"Content-Type": "application/json", admin_flytt.SIGNATURHUVUD: signatur})
    assert ut.status_code == 200, ut.text
    assert ut.json()["rader"][0]["resultat"] == "redan_flyttad"

    # Ett nytt provider_message_id importeras på riktigt, med klass och beslutslogg.
    paket["poster"][0]["provider_message_id"] = "flytt-2"
    kropp = json.dumps(paket, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sig = admin_flytt.signera(paket, get_settings().flytt_nyckel)
    ut = client.post("/api/admin/flytt/importera", content=kropp,
                     headers={"Content-Type": "application/json", admin_flytt.SIGNATURHUVUD: sig})
    assert ut.status_code == 200 and ut.json()["importerade"] == 1
    ny = await storage.get_email(DEFAULT_TENANT_ID, ut.json()["rader"][0]["id"])
    assert ny["klass"] == "support"
    assert any(d.get("event") == "importerad" for d in ny.get("decisions") or [])


async def test_korning_importeras_med_prospekt(client):
    storage = app.state.storage
    p = await storage.create_prospect(DEFAULT_TENANT_ID, company_name="Flyttbolaget AB", contact_name="Test Testsson",
                                      contact_email="vd@flyttbolaget.se", origin="test", profil={"contact_phone": "070-1"})
    k = {"mal": 1, "levererade": 1, "undersokta": 1, "pagaende": 0, "klar": True, "jobs": [{"job_id": "j1", "prospect_id": p["id"], "company_name": "Flyttbolaget AB"}], "tratt": []}
    await storage.set_leads_job_status(DEFAULT_TENANT_ID, job_id="batch-flytt", status="completed", scope="batch", korning=k, is_test=True)
    slug = _slug(client)
    svar = client.post("/api/admin/flytt/paket", headers=_master(client), json={"slug": slug, "typ": "korning", "ids": ["batch-flytt"]})
    assert svar.status_code == 200, svar.text
    paket = svar.json()["paket"]
    assert paket["poster"][0]["prospekt"][0]["contact_phone"] == "070-1"

    # Importera som en NY körning (annat job_id) i samma lager: prospektet finns → återanvänds, raden skrivs.
    paket["poster"][0]["korning"]["job_id"] = "batch-flytt-2"
    paket["poster"][0]["ref_id"] = "batch-flytt-2"
    kropp = json.dumps(paket, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sig = admin_flytt.signera(paket, get_settings().flytt_nyckel)
    ut = client.post("/api/admin/flytt/importera", content=kropp,
                     headers={"Content-Type": "application/json", admin_flytt.SIGNATURHUVUD: sig})
    assert ut.status_code == 200, ut.text
    assert ut.json()["rader"][0] == {"ref_id": "batch-flytt-2", "resultat": "importerad", "prospekt": 0}
    rad = await storage.get_leads_korning(DEFAULT_TENANT_ID, "batch-flytt-2")
    assert rad and rad["korning"]["importerad_fran"] == "development"


def test_skicka_utan_mal_ger_503(client):
    slug = _slug(client)
    svar = client.post("/api/admin/flytt/skicka", headers=_master(client), json={"slug": slug, "typ": "mejl", "ids": ["x"]})
    assert svar.status_code == 503


@pytest.mark.anyio
async def test_bedomningen_foljer_med_till_main(client):
    """2026-10-05: create_prospect tar bara grundfälten, så nivå, poäng,
    motivering och webbrevision föll bort och leadet landade obedömt i main."""
    storage = app.state.storage
    p = await storage.create_prospect(DEFAULT_TENANT_ID, company_name="Bedömda Bolaget AB", origin="iris")
    await storage.spara_bedomning(DEFAULT_TENANT_ID, p["id"], bedomning={
        "niva": "A", "score_total": 91, "motivering": "Gammal sajt i målområdet.",
        "score_breakdown": [{"nyckel": "k1", "utfall": "träff"}], "webbrevision": {"modernitet": 3},
    })
    k = {"mal": 1, "levererade": 1, "undersokta": 1, "pagaende": 0, "klar": True,
         "jobs": [{"job_id": "j9", "prospect_id": p["id"]}], "tratt": []}
    await storage.set_leads_job_status(DEFAULT_TENANT_ID, job_id="batch-bed", status="completed", scope="batch", korning=k, is_test=True)
    paket = client.post("/api/admin/flytt/paket", headers=_master(client),
                        json={"slug": _slug(client), "typ": "korning", "ids": ["batch-bed"]}).json()["paket"]
    # Mottagaren: samma lager, så byt namn och job_id för att få en ny rad.
    paket["poster"][0]["korning"]["job_id"] = paket["poster"][0]["ref_id"] = "batch-bed-2"
    paket["poster"][0]["prospekt"][0]["company_name"] = "Bedömda Bolaget Main AB"
    kropp = json.dumps(paket, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    ut = client.post("/api/admin/flytt/importera", content=kropp, headers={
        "Content-Type": "application/json", admin_flytt.SIGNATURHUVUD: admin_flytt.signera(paket, get_settings().flytt_nyckel)})
    assert ut.status_code == 200 and ut.json()["rader"][0]["prospekt"] == 1, ut.text
    ny = next(x for x in await storage.list_prospects(DEFAULT_TENANT_ID, limit=500) if x["company_name"] == "Bedömda Bolaget Main AB")
    assert (ny["niva"], ny["score_total"], ny["motivering"]) == ("A", 91, "Gammal sajt i målområdet.")
    assert ny["webbrevision"] == {"modernitet": 3} and ny["score_breakdown"]


async def test_prospekt_flyttas_enskilt(client):
    """typ='prospekt' (Sebbe 2026-10-06): markerade leads flyttas utan sin
    körning. Dedup på bolagsnamnet — finns bolaget är det redan flyttat."""
    storage = app.state.storage
    p = await storage.create_prospect(
        DEFAULT_TENANT_ID, company_name="Flyttbart AB", contact_name="Vera VD",
        contact_email="vera@flyttbart.example", origin="iris", profil={"ort": "Umeå", "niva": "A"},
    )
    slug = _slug(client)
    svar = client.post("/api/admin/flytt/paket", headers=_master(client),
                       json={"slug": slug, "typ": "prospekt", "ids": [p["id"]]})
    assert svar.status_code == 200, svar.text
    paket, signatur = svar.json()["paket"], svar.json()["signatur"]
    assert paket["poster"][0]["prospekt"][0]["company_name"] == "Flyttbart AB"

    # Samma lager: bolaget finns redan → redan_flyttad (idempotent).
    kropp = json.dumps(paket, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    ut = client.post("/api/admin/flytt/importera", content=kropp,
                     headers={"Content-Type": "application/json", admin_flytt.SIGNATURHUVUD: signatur})
    assert ut.status_code == 200 and ut.json()["rader"][0]["resultat"] == "redan_flyttad"

    # Ett nytt namn importeras på riktigt, med profilen i behåll.
    paket["poster"][0]["prospekt"][0]["company_name"] = "Flyttbart Syd AB"
    kropp = json.dumps(paket, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sig = admin_flytt.signera(paket, get_settings().flytt_nyckel)
    ut = client.post("/api/admin/flytt/importera", content=kropp,
                     headers={"Content-Type": "application/json", admin_flytt.SIGNATURHUVUD: sig})
    assert ut.status_code == 200 and ut.json()["importerade"] == 1, ut.text
    ny = await storage.get_prospect(DEFAULT_TENANT_ID, ut.json()["rader"][0]["id"])
    assert ny["company_name"] == "Flyttbart Syd AB" and ny.get("ort") == "Umeå"


async def test_enskilt_lead_behaller_bedomningen(client):
    """Samma fel som körningsflytten hade 2026-10-05, i den enskilda vägen:
    create_prospect tar bara grundfälten, så bedömningen måste sparas för sig."""
    storage = app.state.storage
    p = await storage.create_prospect(DEFAULT_TENANT_ID, company_name="Enskilt Bedömt AB", origin="iris")
    await storage.spara_bedomning(DEFAULT_TENANT_ID, p["id"], bedomning={
        "niva": "A", "score_total": 88, "motivering": "Nyöppnad butik.", "webbrevision": {"modernitet": 2},
    })
    paket = client.post("/api/admin/flytt/paket", headers=_master(client),
                        json={"slug": _slug(client), "typ": "prospekt", "ids": [p["id"]]}).json()["paket"]
    paket["poster"][0]["prospekt"][0]["company_name"] = "Enskilt Bedömt Main AB"
    kropp = json.dumps(paket, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    ut = client.post("/api/admin/flytt/importera", content=kropp, headers={
        "Content-Type": "application/json", admin_flytt.SIGNATURHUVUD: admin_flytt.signera(paket, get_settings().flytt_nyckel)})
    assert ut.status_code == 200 and ut.json()["importerade"] == 1, ut.text
    ny = await storage.get_prospect(DEFAULT_TENANT_ID, ut.json()["rader"][0]["id"])
    assert (ny["niva"], ny["score_total"], ny["motivering"]) == ("A", 88, "Nyöppnad butik.")
    assert ny["webbrevision"] == {"modernitet": 2}
