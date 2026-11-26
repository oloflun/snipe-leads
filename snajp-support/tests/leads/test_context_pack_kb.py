"""Kundens säljfakta ur kunskapsbasen når leadskedjan.

Kunddemon 2026-11-24: leadskedjan läste aldrig kunskapsbasen. Artiklar i
kategorin "salj" som kunden har LAGT TILL står nu i kontextpaketet som ett eget
avsnitt, och därmed i research, utkast och grundningsgrindens underlag.
Supportartiklar och förslag kunden inte lagt till läses aldrig.
"""

import pytest

from app.leads.context_pack import build_context_pack
from app.leads.grounding_gate import build_permitted_facts
from app.storage.memory import MemoryStorage

TENANT = "tenant-kb-salj"
RUBRIK = "Kundens egna fakta ur kunskapsbasen"


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _storage() -> MemoryStorage:
    storage = MemoryStorage()
    await storage.add_kb_article(
        TENANT,
        title="Pris",
        content="Mobil växel från 149 kr per användare och månad.",
        category="salj",
        source_url="https://www.telekunden-exempel.se/priser",
    )
    await storage.add_kb_article(
        TENANT,
        title="Leveranstider",
        content="Vi skickar med PostNord inom 3 arbetsdagar.",
        category="leverans",
    )
    skanning = await storage.skapa_kb_skanning(TENANT, webbplats="https://www.telekunden-exempel.se", startad_av="kund")
    await storage.add_kb_forslag(
        TENANT,
        skanning["id"],
        [
            {
                "title": "Bevis",
                "content": "Över 7777 företag har bytt växel med oss.",
                "category": "salj",
                "source_url": "https://www.telekunden-exempel.se/referenser",
                "confidence": 0.8,
                "varningar": [],
            }
        ],
    )
    return storage


@pytest.mark.anyio
async def test_tillagda_saljartiklar_star_i_kontextpaketet():
    pack, _ = await build_context_pack(await _storage(), TENANT)
    assert RUBRIK in pack
    assert "Mobil växel från 149 kr per användare och månad." in pack


@pytest.mark.anyio
async def test_supportartiklar_och_ej_tillagda_forslag_star_inte_dar():
    pack, _ = await build_context_pack(await _storage(), TENANT)
    assert "PostNord" not in pack
    assert "7777" not in pack


@pytest.mark.anyio
async def test_utan_saljartiklar_inget_avsnitt():
    storage = MemoryStorage()
    await storage.add_kb_article(TENANT, title="Retur", content="Retur inom 30 dagar.", category="retur_reklamation")
    pack, _ = await build_context_pack(storage, TENANT)
    assert RUBRIK not in pack


@pytest.mark.anyio
async def test_saljfaktan_ingar_i_grundningsgrindens_underlag():
    pack, _ = await build_context_pack(await _storage(), TENANT)
    facts = build_permitted_facts(
        context_pack=pack,
        research_evidence=[],
        offer_summary="",
        brief="",
        tenant_name="Telekunden",
        company_name="Prospekt AB",
    )
    # Grinden normaliserar "149 kr" till "149SEK".
    assert "149SEK" in facts.numbers
    assert not any("7777" in n for n in facts.numbers)
