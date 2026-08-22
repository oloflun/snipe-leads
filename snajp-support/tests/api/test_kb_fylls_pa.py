"""Kunskapsbasen ska fyllas PÅ, inte hoppas över för att den inte är tom.

`ensure_tenant_kb` avbröt tidigare så fort tenanten hade en enda artikel. En
testarbetsyta som seedats en gång fick därför aldrig artiklar som lades till
senare — och det märktes: facken garanti, utbildning och orderstatus hade en
artikel var, grundningsregeln styrde ärendena till fack med täckning, och två
inkorgar stod tomma i demon medan koden såg riktig ut.
"""

import pytest

from app.kb_articles import KB_ARTICLES
from app.scripts.seed_kb import ensure_tenant_kb
from app.storage.memory import MemoryStorage

#: En EGEN tenant, inte default-tenanten. MemoryStorage förseedar
#: DEFAULT_TENANT_ID med hela KB_ARTICLES i konstruktorn, så ett test som
#: använde den mätte lagringens fixtur i stället för seedningsfunktionen.
TENANT = "00000000-0000-4000-a000-0000000009fa"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_tom_bas_far_alla_artiklar():
    lagring = MemoryStorage()
    antal = await ensure_tenant_kb(lagring, TENANT)
    assert antal == len(KB_ARTICLES)


@pytest.mark.anyio
async def test_andra_korningen_lagger_inte_till_dubbletter():
    lagring = MemoryStorage()
    await ensure_tenant_kb(lagring, TENANT)
    assert await ensure_tenant_kb(lagring, TENANT) == 0
    assert len(await lagring.list_kb(TENANT)) == len(KB_ARTICLES)


@pytest.mark.anyio
async def test_bas_som_saknar_en_artikel_far_just_den():
    """Kärnan: en delvis fylld bas ska kompletteras, inte lämnas som den är."""
    lagring = MemoryStorage()
    for artikel in KB_ARTICLES[:-3]:
        await lagring.add_kb_article(
            TENANT,
            title=artikel["title"],
            content=artikel["content"],
            category=artikel["category"],
            embedding=None,
        )

    assert await ensure_tenant_kb(lagring, TENANT) == 3
    titlar = {a["title"] for a in await lagring.list_kb(TENANT)}
    assert titlar == {a["title"] for a in KB_ARTICLES}


@pytest.mark.anyio
async def test_varje_fack_har_minst_tre_artiklar():
    """Ett fack med en enda artikel är ett fack agenten drar ärenden BORT från.

    Grundningsregeln kräver en träff i basen, och med tunn täckning hamnar
    ärendet i ett fack som har det — inte i det fack det hör hemma i.
    """
    from collections import Counter

    from app.config import CATEGORIES

    antal = Counter(a["category"] for a in KB_ARTICLES)
    for kategori in CATEGORIES:
        assert antal[kategori] >= 3, f"{kategori} har bara {antal[kategori]} artiklar"
