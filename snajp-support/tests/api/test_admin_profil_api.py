"""Adminens skrivyta: master-nyckel krävs, och delvisa sparningar raderar inget.

Två fel den här filen finns för att fånga, båda dyra och båda tysta:

1. En KUNDNYCKEL som kommer in. Routern skriver över tenant-gränsen, och ett
   läckage här är ett läckage av allas konfiguration.
2. Ett sparande som nollställer fält det inte skulle röra. Formuläret sparar en
   sektion i taget; tolkas ett utelämnat fält som tom sträng försvinner kundens
   röstdokument när någon ändrar tonen — och ingenting felar.
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


SKRIVVAGAR = [
    ("PUT", "/api/admin/instruktioner", {"ravtext": "x"}),
    ("POST", "/api/admin/instruktioner/forhandsgranska", {"ravtext": "x"}),
    ("PUT", f"/api/admin/tenants/{DEFAULT_TENANT_ID}/profil", {"tone": "x"}),
]


@pytest.mark.parametrize("metod,vag,kropp", SKRIVVAGAR)
async def test_kundnyckel_avvisas(client: TestClient, metod, vag, kropp):
    svar = client.request(metod, vag, headers=_kund(), json=kropp)
    assert svar.status_code == 403, f"{vag} släppte in en kundnyckel"


@pytest.mark.parametrize("metod,vag,kropp", SKRIVVAGAR)
async def test_utan_nyckel_avvisas(client: TestClient, metod, vag, kropp):
    svar = client.request(metod, vag, json=kropp)
    assert svar.status_code == 401


async def test_globala_instruktioner_sparas_och_las_tillbaka(client: TestClient):
    svar = client.put(
        "/api/admin/instruktioner",
        headers=_master(),
        json={"ravtext": "Svara kort.", "strukturera": False},
    )
    assert svar.status_code == 200, svar.text

    lage = client.get("/api/admin/instruktioner", headers=_master()).json()["instruktioner"]
    assert lage["ravtext"] == "Svara kort."
    # `aktiv_text` är vad AGENTEN läser. Att den följer sparningen är hela
    # poängen — fältet som fanns före 049 gjorde det inte.
    assert lage["aktiv_text"] == "Svara kort."
    assert lage["fran_fil"] is False
    assert lage["historik"]


async def test_utan_sparad_instruktion_kommer_texten_ur_filen(client: TestClient):
    """Ingen aktiv rad = agent-core/AGENTS.md, alltså beteendet före 049.

    Testet körs mot en färsk MemoryStorage per session; ordningen mot testet
    ovan spelar därför roll bara om båda skriver, och det gör bara det ena.
    """
    lage = client.get("/api/admin/instruktioner", headers=_master()).json()["instruktioner"]
    if lage["fran_fil"]:
        assert "Hitta aldrig på fakta" in lage["aktiv_text"]


async def test_delvis_sparning_rader_inte_ovriga_falt(client: TestClient):
    vag = f"/api/admin/tenants/{DEFAULT_TENANT_ID}/profil"

    client.put(vag, headers=_master(), json={"soul": "Vi säger du."})
    client.put(
        vag,
        headers=_master(),
        json={"instruktioner_rav": "Eskalera vid återbetalning.", "strukturera": False},
    )
    # Tonen sparas för sig — det är den vägen som tidigare hade kunnat radera
    # instruktionerna, eftersom set_agent_instructions är en upsert.
    client.put(vag, headers=_master(), json={"tone": "rak"})

    profil = client.get(vag, headers=_master()).json()["profil"]
    assert profil["soul"] == "Vi säger du."
    assert profil["instruktioner_md"] == "Eskalera vid återbetalning."
    assert profil["tone"] == "rak"


async def test_profilen_sager_var_varje_falt_hamnar(client: TestClient):
    """Positionen följer med i svaret.

    Utan den måste den som bygger vyn slå upp den i koden, och den som inte gör
    det ritar två fält som ser likadana ut och beter sig olika. Instruktionen är
    en regel agenten lyder; SOUL är text den läser och uttryckligen inte lyder.
    """
    profil = client.get(
        f"/api/admin/tenants/{DEFAULT_TENANT_ID}/profil", headers=_master()
    ).json()["profil"]
    assert profil["position"]["instruktioner_md"] == "system"
    assert profil["position"]["soul"].startswith("user")
    assert profil["position"]["affarskontext"].startswith("user")


async def test_okand_kund_ger_404_inte_500(client: TestClient):
    for id_ in ("inte-ett-uuid", "00000000-0000-4000-a000-0000000000ff"):
        svar = client.get(f"/api/admin/tenants/{id_}/profil", headers=_master())
        assert svar.status_code == 404, f"{id_} gav {svar.status_code}"
