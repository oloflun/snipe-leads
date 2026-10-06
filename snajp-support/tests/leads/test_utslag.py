"""Iris kalibreras av kundens egna utslag, aldrig av agentens (fas 9)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.leads.utslag import kalibrering
from app.storage.memory import MemoryStorage

T = "11111111-1111-1111-1111-111111111111"

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _prospekt(s: MemoryStorage, namn: str, motivering: str) -> str:
    p = await s.create_prospect(T, company_name=namn)
    await s.spara_bedomning(T, p["id"], bedomning={"motivering": motivering})
    return p["id"]


async def test_bara_manniskans_utslag_och_aldrig_det_aktuella_bolaget():
    s = MemoryStorage()
    ja = await _prospekt(s, "Kursbolaget AB", "Säljer säkerhetsutbildningar.")
    nej = await _prospekt(s, "Byggfirman AB", "Bygger villor.")
    kod = await _prospekt(s, "Kodstatus AB", "Satt av agenten.")
    aktuellt = await _prospekt(s, "Nytt AB", "Researchas nu.")
    await s.update_prospect(T, ja, status="contacted", status_kalla="manuell")
    await s.update_prospect(T, nej, status="lost", status_kalla="manuell")
    await s.update_prospect(T, kod, status="contacted", status_kalla="kod")
    await s.update_prospect(T, aktuellt, status="won", status_kalla="manuell")

    with patch("app.agent.embeddings.embed_text", new=AsyncMock(return_value=None)):
        block = await kalibrering(s, T, prospect_id=aktuellt, material="Vi håller kurser i HLR.")

    assert "OPÅLITLIGT" in block
    assert "Godkänt (kontaktad): Kursbolaget AB" in block
    assert "Avvisat (förlorad): Byggfirman AB" in block
    assert "Kodstatus" not in block and "Nytt AB" not in block


async def test_mest_lika_utslag_forst():
    s = MemoryStorage()
    lika = await _prospekt(s, "Kursbolaget AB", "kurs")
    olika = await _prospekt(s, "Byggfirman AB", "bygg")
    await s.update_prospect(T, olika, status="lost", status_kalla="manuell")
    await s.update_prospect(T, lika, status="won", status_kalla="manuell")

    async def vektor(text: str):
        return [1.0, 0.0] if "kurs" in text.lower() else [0.0, 1.0]

    with patch("app.agent.embeddings.embed_text", new=vektor):
        block = await kalibrering(s, T, prospect_id="x", material="Kurser i arbetsmiljö")
    assert block.index("Kursbolaget") < block.index("Byggfirman")


async def test_utan_utslag_inget_block():
    assert await kalibrering(MemoryStorage(), T, prospect_id="x", material="text") == ""
