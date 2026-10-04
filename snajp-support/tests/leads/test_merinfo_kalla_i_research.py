"""Provkörningen på Alunix 2026-10-04: bolag utan webbplats fick tom research
eftersom merinfos bolagssida aldrig blev en källa. Nu registreras den."""

import pytest

from app.api.leads import _skapa_prospekt_ur_kandidat
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-00000000e0e0"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_merinfosidan_blir_kalla_for_bolag_utan_webbplats():
    storage = MemoryStorage()
    url = "https://www.merinfo.se/foretag/Exempel-Bygg-AB-5560000000/2k1abc"
    p = await _skapa_prospekt_ur_kandidat(
        storage, TENANT,
        {"company_name": "Exempel Bygg AB", "website": None, "source_name": "merinfo", "source_url": url},
        "test",
    )
    assert url in await storage.list_prospect_source_urls(TENANT, p["id"])
