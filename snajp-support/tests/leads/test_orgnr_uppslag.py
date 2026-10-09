"""Org.nr ur bolagets egen webbplats (Sebbe 2026-10-09): leads från den gamla
sökkedjan saknade org.nr och kunde inte flyttas över från en provkörning."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.leads import orgnr_uppslag, sidhamtning
from app.leads.orgnr_uppslag import entydigt, hitta_orgnr, orgnr_i_text
from app.main import app

pytestmark = pytest.mark.anyio
DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_bara_uttryckligt_org_nr_med_giltig_kontrollsiffra():
    assert orgnr_i_text("Bygg AB · Org.nr: 556824-9022 · Göteborg") == {"556824-9022"}
    assert orgnr_i_text("Organisationsnummer 5568249022") == {"556824-9022"}
    assert orgnr_i_text("orgnr 556824 9022") == {"556824-9022"}
    # Tio siffror utan etikett (telefon, bankgiro) är inget org.nr.
    assert orgnr_i_text("Ring 556824-9022 eller bankgiro 5568249022") == set()
    # Fel kontrollsiffra.
    assert orgnr_i_text("Org.nr 556824-9023") == set()


def test_personnummer_hamtas_aldrig():
    """En enskild firmas org.nr är ägarens personnummer: en känslig
    personuppgift som aldrig ska hamna i prospektets org.nr-fält."""
    assert orgnr_i_text("Snickarfirma Nils · Org.nr 811218-9876") == set()


def test_tva_olika_nummer_ger_inget_hellre_an_fel_bolag():
    sidor = ["Org.nr 556824-9022", "Webbyrå Exempel AB, org.nr 556036-0793"]
    assert entydigt(sidor) is None
    assert entydigt(["Org.nr 556824-9022", "Org nr 556824-9022"]) == "556824-9022"


async def test_hitta_orgnr_laser_kontaktsidan_nar_startsidan_saknar_det(monkeypatch):
    sajt = {
        "https://bygg.se": "Välkommen till Bygg AB. [Kontakt](/kontakt)",
        "https://bygg.se/kontakt": "Bygg AB, Storgatan 1. Org.nr 556824-9022",
    }
    lasta: list[str] = []

    async def fejk(url, *, fas, direkt, betald=True, utan_cache=False):
        lasta.append(url)
        assert betald is False, "uppslaget betalar aldrig för ScrapeGraph"
        return sajt.get(url.rstrip("/")), None, "direkt"

    monkeypatch.setattr(sidhamtning, "hamta", fejk)
    assert await hitta_orgnr("bygg.se") == "556824-9022"
    assert lasta[0] == "https://bygg.se"


async def test_befordra_slar_upp_saknat_org_nr_pa_sajten(monkeypatch):
    async def fejk(url, *, fas, direkt, betald=True, utan_cache=False):
        return ("Kålltorps Bygg · Org.nr 556824-9022" if "kalltorpsbygg.se" in url else None), None, "direkt"

    monkeypatch.setattr(sidhamtning, "hamta", fejk)
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        prospekt = await storage.create_prospect(
            DEFAULT_TENANT_ID,
            company_name="Kålltorps Bygg",
            contact_email="info@kalltorpsbygg.se",
            origin="test",
            profil={"website": "https://kalltorpsbygg.se"},
        )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            svar = await client.post(f"/api/leads/prospects/{prospekt['id']}/befordra", headers=DEMO)
        assert svar.status_code == 200, svar.text
        body = svar.json()
        assert body["orgnr_hamtat"] is True and body["prospect"]["origin"] == "manual"
        assert (await storage.get_prospect(DEFAULT_TENANT_ID, prospekt["id"]))["orgnr"] == "556824-9022"


async def test_befordra_utan_org_nr_pa_sajten_sager_det(monkeypatch):
    async def fejk(url, *, fas, direkt, betald=True, utan_cache=False):
        return "Ingen bolagsinfo här.", None, "direkt"

    monkeypatch.setattr(sidhamtning, "hamta", fejk)
    async with app.router.lifespan_context(app):
        prospekt = await app.state.storage.create_prospect(
            DEFAULT_TENANT_ID,
            company_name="Bygg Vision Göteborg AB",
            contact_email="info@byggvision.se",
            origin="test",
            profil={"website": "https://byggvision.se"},
        )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            svar = await client.post(f"/api/leads/prospects/{prospekt['id']}/befordra", headers=DEMO)
        assert svar.status_code == 422
        assert "inte heller på bolagets webbplats" in svar.json()["detail"]["message"]


def test_modulen_anvander_bara_gratis_hamtning():
    assert "betald=False" in open(orgnr_uppslag.__file__, encoding="utf-8").read()
