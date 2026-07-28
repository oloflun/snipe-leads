"""Kunskapsbassökning: långa mail måste kunna matcha lika bra som korta frågor.

Regression: poängen normaliserades tidigare mot HELA frågans längd, vilket gjorde
att ett fullängds kundmail nästan aldrig fick träff — grundningsregeln eskalerade
då varje ärende, trots att svaret fanns i kunskapsbasen.
"""

import pytest

from app.config import DEFAULT_TENANT_ID
from app.storage.memory import MemoryStorage


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_long_email_matches_like_short_question():
    storage = MemoryStorage()

    kort = await storage.search_kb(DEFAULT_TENANT_ID, "garanti batteribyte")
    langt = await storage.search_kb(
        DEFAULT_TENANT_ID,
        "Hej! Vi köpte vår hjärtstartare för ungefär tre år sedan och nu har den "
        "börjat varna för batteriet. Jag undrar om ett batteribyte täcks av "
        "garantin eller om vi får betala för det själva. Tacksam för svar. "
        "Med vänliga hälsningar, Johan",
    )

    assert kort, "kort fråga ska ge träff"
    assert langt, "långt mail med samma innebörd ska också ge träff"
    assert any("aranti" in a["title"] for a in langt)


@pytest.mark.anyio
async def test_invoice_email_finds_payment_article():
    storage = MemoryStorage()
    träffar = await storage.search_kb(
        DEFAULT_TENANT_ID,
        "Fråga om faktura och referens. Vi fick fakturan men vår inköpsreferens "
        "saknas, vilket gör att den fastnar i vårt system. Kan ni skicka en ny "
        "med referens INK-2291?",
    )
    assert träffar
    assert any(a["category"] == "betalning" for a in träffar)


@pytest.mark.anyio
async def test_irrelevant_question_still_returns_nothing():
    """Taket får inte göra sökningen så generös att allt matchar."""
    storage = MemoryStorage()
    assert await storage.search_kb(DEFAULT_TENANT_ID, "Har ni öppet på midsommarafton?") == []


@pytest.mark.anyio
async def test_similarity_is_capped_at_one():
    storage = MemoryStorage()
    for article in await storage.search_kb(DEFAULT_TENANT_ID, "garanti garantitid garantivillkor"):
        assert 0 < article["similarity"] <= 1.0
