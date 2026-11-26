"""Hjälpens kunskapsbas (app/tenants/snajp_hjalp.py) seedas utan dubbletter."""

import pytest

from app.api.kb import titelnyckel
from app.config import KB_CATEGORIES, get_settings
from app.storage.memory import MemoryStorage
from app.tenants import snajp_hjalp
from app.tenants.snajp_kb import KB_ARTICLES as SNAJP_KB


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_artiklarna_ar_hela_och_unika():
    rubriker = [a["title"] for a in snajp_hjalp.KB_ARTICLES]
    assert len({titelnyckel(r) for r in rubriker}) == len(rubriker), "två artiklar med samma rubrik"
    for artikel in snajp_hjalp.KB_ARTICLES:
        # Samma gränser som en artikel genom POST /api/kb (schemas.KbArticle).
        assert 3 <= len(artikel["title"]) <= 200
        assert 10 <= len(artikel["content"]) <= 8000
        assert artikel["category"] in KB_CATEGORIES
        assert "supportbot" not in artikel["content"].lower()
    # Snajps artiklar följer med, utom den med den gamla menyn.
    assert "Hitta rätt på arbetsytan" not in rubriker
    assert {a["title"] for a in SNAJP_KB} - {"Hitta rätt på arbetsytan"} <= set(rubriker)
    for rubrik in ("Så kör du Iris", "Så godkänner du ett utkast", "Så lägger du till en produkt",
                   "Så lägger du till kunskap i kunskapsbasen",
                   "Rapportera ett fel i Snajp, och vad som händer sedan"):
        assert rubrik in rubriker


@pytest.mark.anyio
async def test_seedningen_ar_idempotent_och_ager_bara_sina_rubriker():
    storage = MemoryStorage()
    forsta = await snajp_hjalp.seed_hjalp(storage)
    assert forsta == {"tillagda": len(snajp_hjalp.KB_ARTICLES), "bytta": 0}

    tenant = await storage.create_tenant(slug=get_settings().hjalp_tenant_slug, name="x")
    assert tenant["kraver_avtal"] is False  # intern tenant: avtalsgrinden av
    assert tenant["name"] == snajp_hjalp.HJALP_TENANT_NAME

    assert await snajp_hjalp.seed_hjalp(storage) == {"tillagda": 0, "bytta": 0}
    artiklar = await storage.list_kb(tenant["id"])
    assert len(artiklar) == len(snajp_hjalp.KB_ARTICLES)

    # En egen artikel rörs inte; en ändrad filartikel byts utan dubblett.
    await storage.add_kb_article(tenant["id"], title="Egen anteckning", content="Lagd för hand av Snajp.",
                                 category="ovrigt", embedding=None)
    andrad = next(a for a in artiklar if a["title"] == "Så kör du Iris")
    await storage.delete_kb_article(tenant["id"], andrad["id"])
    await storage.add_kb_article(tenant["id"], title="Så kör du Iris", content="Gammal text som ska bytas.",
                                 category="teknisk_support", embedding=None)
    assert await snajp_hjalp.seed_hjalp(storage) == {"tillagda": 0, "bytta": 1}
    rubriker = [a["title"] for a in await storage.list_kb(tenant["id"])]
    assert rubriker.count("Så kör du Iris") == 1
    assert "Egen anteckning" in rubriker
    assert len(rubriker) == len(snajp_hjalp.KB_ARTICLES) + 1


@pytest.mark.anyio
async def test_hjalpen_ar_inte_marknadssidans_snajp():
    storage = MemoryStorage()
    await snajp_hjalp.seed_hjalp(storage)
    snajp = await storage.create_tenant(slug="snajp", name="Snajp")
    hjalp = await storage.create_tenant(slug=get_settings().hjalp_tenant_slug, name="x")
    assert snajp["id"] != hjalp["id"]
    assert await storage.list_kb(snajp["id"]) == []
