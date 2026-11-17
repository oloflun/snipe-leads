"""INV-AVTAL-001: en ny tenant kräver signerat avtal om inget annat sägs.

Snajp är personuppgiftsbiträde åt sina kunder (GDPR art. 28) och får inte
behandla en kunds personuppgifter utan biträdesavtal. Grinden fanns sedan
migration 070, men som opt-in: en ny kund fick trafik om ingen kom ihåg att
slå på flaggan. Migration 118 vänder standardvärdet.

Testerna körs utan databas, som resten av sviten:

  * schemat avgörs genom att läsa migrationerna i körordning — det SISTA
    standardvärdet som sätts på ss_tenants.kraver_avtal är det som gäller;
  * migrationen som vänder standardvärdet får inte röra befintliga rader;
  * MemoryStorage speglar databasens standard, och POST /api/keys bär
    standarden fram (eller ett uttryckligt false för test- och interna ytor);
  * grinden vägrar en sådan tenant tills avtalsdatumet är registrerat.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.avtalsgrind import avtal_saknas, nollstall_cache
from app.storage.memory import MemoryStorage

pytestmark = pytest.mark.anyio

MIGRATIONER = Path(__file__).resolve().parents[3] / "supabase" / "migrations"

#: `add column ... kraver_avtal boolean ... default X` eller
#: `alter column kraver_avtal set default X`.
_STANDARD = re.compile(
    r"kraver_avtal\b[^;]*?\b(?:set\s+)?default\s+(true|false)\b", re.IGNORECASE | re.DOTALL
)


def _utan_kommentarer(sql: str) -> str:
    return re.sub(r"--[^\n]*", "", sql)


def _migrationer_i_korordning() -> list[Path]:
    # Samma ordning som scripts/railway_migrate.py: filnamnet sorterat.
    return sorted(MIGRATIONER.glob("*.sql"), key=lambda p: p.name)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _ren_cache():
    nollstall_cache()
    yield
    nollstall_cache()


def test_schemats_standard_ar_att_avtal_kravs():
    sista: tuple[str, str] | None = None
    for fil in _migrationer_i_korordning():
        for traff in _STANDARD.finditer(_utan_kommentarer(fil.read_text(encoding="utf-8"))):
            sista = (fil.name, traff.group(1).lower())
    assert sista is not None, "ingen migration sätter ett standardvärde på kraver_avtal"
    assert sista[1] == "true", (
        f"{sista[0]} lämnar ss_tenants.kraver_avtal med standardvärdet {sista[1]}: "
        "en ny kund får då trafik utan registrerat biträdesavtal"
    )


def test_migrationen_som_vander_standarden_ror_inga_befintliga_rader():
    """Befintliga kunder, demo- och interna tenants behåller sitt värde. En
    update här hade stängt av levande trafik i samma sekund som deployen."""
    vandande = [
        fil
        for fil in _migrationer_i_korordning()
        if re.search(
            r"alter\s+column\s+kraver_avtal\s+set\s+default\s+true",
            _utan_kommentarer(fil.read_text(encoding="utf-8")),
            re.IGNORECASE,
        )
    ]
    assert vandande, "ingen migration vänder standardvärdet till true"
    for fil in vandande:
        sql = _utan_kommentarer(fil.read_text(encoding="utf-8")).lower()
        assert not re.search(r"\bupdate\s+(public\.)?ss_tenants\b", sql), (
            f"{fil.name} skriver om befintliga tenants"
        )


async def test_ny_tenant_utan_uttryckligt_varde_kraver_avtal():
    storage = MemoryStorage()
    tenant = await storage.create_tenant(slug="ny-kund-ab", name="Ny Kund AB")
    assert tenant["kraver_avtal"] is True


async def test_uttryckligt_false_galler_bara_vid_skapandet():
    storage = MemoryStorage()
    test = await storage.create_tenant(slug="eval-1", name="Evalkund", kraver_avtal=False)
    assert test["kraver_avtal"] is False

    # Upserten på slug rör aldrig en befintlig tenants flagga.
    kund = await storage.create_tenant(slug="ny-kund-ab", name="Ny Kund AB")
    igen = await storage.create_tenant(slug="ny-kund-ab", name="Ny Kund AB", kraver_avtal=False)
    assert igen["id"] == kund["id"]
    assert igen["kraver_avtal"] is True


async def test_grinden_vagrar_ny_tenant_tills_avtalet_ar_registrerat():
    storage = MemoryStorage()
    tenant = await storage.create_tenant(slug="ny-kund-ab", name="Ny Kund AB")
    assert await avtal_saknas(storage, tenant["id"]) is True

    await storage.upsert_customer_details(tenant["id"], {"avtal_signerat": "2026-11-17"})
    nollstall_cache()
    assert await avtal_saknas(storage, tenant["id"]) is False


async def test_demo_och_standardtenanten_paverkas_inte():
    """De två inbyggda tenants (demo och Nordlys) skapas inte via
    create_tenant och ska fortsätta svara."""
    from app.config import DEFAULT_TENANT_ID, PUBLIC_DEMO_TENANT_ID

    storage = MemoryStorage()
    assert await avtal_saknas(storage, DEFAULT_TENANT_ID) is False
    assert await avtal_saknas(storage, PUBLIC_DEMO_TENANT_ID) is False


def test_api_nyckelvagen_bar_standarden_och_uttryckligt_false():
    from fastapi.testclient import TestClient

    from app.config import get_settings
    from app.main import app

    master = {"X-API-Key": get_settings().snajp_master_api_key}
    with TestClient(app) as client:
        kund = client.post(
            "/api/keys", headers=master, json={"tenant_name": "Ny Kund AB", "slug": "ny-kund-ab"}
        )
        assert kund.status_code == 201, kund.text
        assert kund.json()["kraver_avtal"] is True

        test = client.post(
            "/api/keys",
            headers=master,
            json={"tenant_name": "Evalkund", "slug": "eval-avtal-1", "kraver_avtal": False},
        )
        assert test.status_code == 201, test.text
        assert test.json()["kraver_avtal"] is False
