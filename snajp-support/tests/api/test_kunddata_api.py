"""Kundregistret: nyckelgrind, härledda källor, delvisa sparningar, tenant-gräns.

Fyra fel den här filen finns för att fånga:

1. En kundnyckel som kommer in — registret bär fakturaadresser och
   kontaktpersoner för ALLA kunder.
2. Ett härlett värde som ser manuellt ut. Varje fält bär `kalla`, och ett
   fallback-datum som presenteras som bekräftat är ett faktureringsunderlag
   med en gissning i.
3. En delvis sparning som nollställer fält den inte skulle röra — samma
   klass av fel som agentprofilens röstdokument.
4. Ett kontakt-id ur EN kunds lista som muterar en annan kunds rad.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _master() -> dict[str, str]:
    return {"X-API-Key": get_settings().snajp_master_api_key}


def _kund() -> dict[str, str]:
    return {"X-API-Key": get_settings().snajp_demo_api_key}


VAG = f"/api/admin/tenants/{DEFAULT_TENANT_ID}/kunddata"
KONTAKTVAG = f"/api/admin/tenants/{DEFAULT_TENANT_ID}/kontakter"

VAGAR = [
    ("GET", VAG, None),
    ("PUT", VAG, {"telefon": "070-000 00 00"}),
    ("POST", KONTAKTVAG, {"namn": "Test"}),
]


@pytest.mark.parametrize("metod,vag,kropp", VAGAR)
async def test_utan_nyckel_avvisas(client: TestClient, metod, vag, kropp):
    assert client.request(metod, vag, json=kropp).status_code == 401


@pytest.mark.parametrize("metod,vag,kropp", VAGAR)
async def test_kundnyckel_avvisas(client: TestClient, metod, vag, kropp):
    svar = client.request(metod, vag, headers=_kund(), json=kropp)
    assert svar.status_code == 403, f"{vag} släppte in en kundnyckel"


async def test_farsk_kund_har_harledda_kallor(client: TestClient):
    """Utan registerrad: kund_sedan härleds ur tenanten (kalla=system) och
    resten saknas — inget fält får låtsas vara manuellt bekräftat."""
    data = client.get(VAG, headers=_master()).json()["kunddata"]
    assert data["tenant"]["id"] == DEFAULT_TENANT_ID
    assert data["falt"]["kund_sedan"]["varde"] is not None
    assert data["falt"]["kund_sedan"]["kalla"] == "system"
    assert data["falt"]["faktureringsmejl"] == {"varde": None, "kalla": None}
    assert data["kontakter"] == []


async def test_orgnr_harleds_ur_onboardingens_affarskontext(client: TestClient):
    await app.state.storage.save_context_doc(
        DEFAULT_TENANT_ID,
        kind="product_marketing",
        content="Organisationsnummer: 556677-8899\nWebbplats: https://exempel.se",
        source="test",
    )
    falt = client.get(VAG, headers=_master()).json()["kunddata"]["falt"]
    assert falt["orgnr"] == {"varde": "556677-8899", "kalla": "onboarding"}

    # Ett manuellt värde vinner över det härledda.
    client.put(VAG, headers=_master(), json={"orgnr": "111111-2222"})
    falt = client.get(VAG, headers=_master()).json()["kunddata"]["falt"]
    assert falt["orgnr"] == {"varde": "111111-2222", "kalla": "manuell"}


async def test_delvis_sparning_ror_inte_ovriga_falt(client: TestClient):
    svar = client.put(
        VAG,
        headers=_master(),
        json={"faktureringsmejl": "faktura@exempel.se", "avtal_signerat": "2026-08-01"},
    )
    assert svar.status_code == 200, svar.text
    assert svar.json()["sparat"] == ["avtal_signerat", "faktureringsmejl"]

    # Telefon sparas separat — mejlen och avtalet ska stå kvar.
    client.put(VAG, headers=_master(), json={"telefon": "070-123 45 67"})
    falt = client.get(VAG, headers=_master()).json()["kunddata"]["falt"]
    assert falt["faktureringsmejl"]["varde"] == "faktura@exempel.se"
    assert falt["avtal_signerat"]["varde"] == "2026-08-01"
    assert falt["telefon"]["varde"] == "070-123 45 67"

    # Tom sträng nollställer — avtalet går tillbaka till "finns inte".
    client.put(VAG, headers=_master(), json={"avtal_signerat": ""})
    falt = client.get(VAG, headers=_master()).json()["kunddata"]["falt"]
    assert falt["avtal_signerat"] == {"varde": None, "kalla": None}


async def test_trasigt_datum_ger_422_med_faltnamn(client: TestClient):
    svar = client.put(VAG, headers=_master(), json={"avtal_signerat": "igår"})
    assert svar.status_code == 422
    assert "avtal_signerat" in svar.json()["detail"]


async def test_avtalet_syns_i_tenantlistan(client: TestClient):
    client.put(VAG, headers=_master(), json={"avtal_signerat": "2026-08-15"})
    rader = client.get("/api/admin/tenants", headers=_master()).json()["tenants"]
    rad = next(r for r in rader if str(r["id"]) == DEFAULT_TENANT_ID)
    assert rad["avtal_signerat"] == "2026-08-15"
    assert rad["kund_sedan"] is not None
    # Fel & eskaleringar-sektionen läser fältet; saknas det visar vyn noll
    # eskalerade oavsett verklighet.
    assert "escalated" in rad


async def test_kontakter_skapas_uppdateras_och_tas_bort(client: TestClient):
    svar = client.post(
        KONTAKTVAG,
        headers=_master(),
        json={"namn": "Anna Ek", "roll": "Ekonomichef", "mejl": "anna@exempel.se"},
    )
    assert svar.status_code == 200, svar.text
    kontakt = svar.json()["kontakt"]

    # Namnlös kontakt avvisas — en rad utan namn går inte att ringa.
    assert client.post(KONTAKTVAG, headers=_master(), json={"roll": "VD"}).status_code == 422

    # Delvis uppdatering: telefonen sätts, namnet står kvar; tom sträng nollställer rollen.
    svar = client.put(
        f"{KONTAKTVAG}/{kontakt['id']}",
        headers=_master(),
        json={"telefon": "070-111 22 33", "roll": ""},
    )
    uppdaterad = svar.json()["kontakt"]
    assert uppdaterad["namn"] == "Anna Ek"
    assert uppdaterad["telefon"] == "070-111 22 33"
    assert uppdaterad["roll"] is None

    assert (
        client.delete(f"{KONTAKTVAG}/{kontakt['id']}", headers=_master()).status_code == 200
    )
    data = client.get(VAG, headers=_master()).json()["kunddata"]
    assert data["kontakter"] == []


async def test_kontakt_id_ur_annan_kunds_lista_ger_404(client: TestClient):
    """Tenant-gränsen: ett giltigt kontakt-id under FEL kund ska svara 404,
    aldrig uppdatera eller radera raden."""
    kontakt = client.post(
        KONTAKTVAG, headers=_master(), json={"namn": "Anna Ek"}
    ).json()["kontakt"]

    annan = await app.state.storage.create_tenant(slug="kunddata-annan", name="Annan AB")
    fel_vag = f"/api/admin/tenants/{annan['id']}/kontakter/{kontakt['id']}"
    assert client.put(fel_vag, headers=_master(), json={"namn": "Kapad"}).status_code == 404
    assert client.delete(fel_vag, headers=_master()).status_code == 404

    kvar = client.get(VAG, headers=_master()).json()["kunddata"]["kontakter"]
    assert kvar and kvar[0]["namn"] == "Anna Ek"
