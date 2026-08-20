"""Vem som får en kunskapsbas, och vem som inte får någon.

Isoleringen per tenant var byggd — varje läsning och skrivning i `kb.py` är
skopad på `tenant_id`, och migration 040 ger varje testarbetsyta en egen
tenant. Det som saknades var att basen någonsin FYLLDES, och att den inte
fylldes med fel bolags text.

Två fel vaktas här, och de drar åt olika håll:

 1. **Tom bas.** `ensure_tenant_kb()` anropades från exakt ett ställe:
    "Hämta testmail". En testarbetsyta som började i leads-vyn eller i chatten
    hade alltså aldrig någon bas, grundningsregeln krävde en träff, och agenten
    eskalerade allt. Det ser ut som en trasig produkt.

 2. **Fel bolags bas.** `KB_ARTICLES` är Nordlys Handels e-handelsartiklar. En
    RIKTIG kund som tryckte på samma knapp fick dem inlagda i sin egen
    grundningskälla. Grundningsgrinden ser en träff — den kan inte se att
    artikeln kom från fel företag, och det är exakt den korsning egna tenants
    finns för att stoppa.

Ett test som bara mätte (1) hade gjort (2) värre.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app

MASTER = {"X-API-Key": get_settings().snajp_master_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _skapa_tenant(client, slug: str) -> dict:
    svar = await client.post(
        "/api/keys", headers=MASTER, json={"tenant_name": f"Test {slug}", "slug": slug}
    )
    assert svar.status_code == 201, svar.text
    return svar.json()


@pytest.mark.anyio
async def test_testarbetsyta_far_kunskapsbas_vid_skapandet():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            skapad = await _skapa_tenant(client, "testkund-a1b2c3d4")

            assert skapad["kb_seeded"] > 0

            kb = await client.get("/api/kb", headers={"X-API-Key": skapad["api_key"]})
            assert kb.status_code == 200
            assert len(kb.json()["articles"]) == skapad["kb_seeded"]


@pytest.mark.anyio
async def test_riktig_kund_far_inga_frammande_artiklar():
    """Den viktigare av de två. Ett annat bolags villkor i kundens bas är ett
    trovärdigt men felaktigt svar, vilket är sämre än inget svar alls."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            skapad = await _skapa_tenant(client, "riktig-kund-ab")

            assert skapad["kb_seeded"] == 0

            kb = await client.get("/api/kb", headers={"X-API-Key": skapad["api_key"]})
            assert kb.json()["articles"] == []


@pytest.mark.anyio
async def test_testmail_seedar_inte_en_riktig_kunds_bas():
    """`X-Snajp-Demo` saknas → ingen seedning, och endpointen SÄGER att basen
    är tom i stället för att lämna kunden med sex röda rader att tolka."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            skapad = await _skapa_tenant(client, "riktig-kund-cd")
            nyckel = {"X-API-Key": skapad["api_key"]}

            svar = await client.post("/api/inbox/mock", headers=nyckel)
            assert svar.status_code == 201, svar.text
            kropp = svar.json()

            assert kropp["kb_seeded"] == 0
            assert kropp["kb_tom"] is True
            assert (await client.get("/api/kb", headers=nyckel)).json()["articles"] == []


@pytest.mark.anyio
async def test_testmail_seedar_en_testarbetsyta():
    """Rubriken som sätter gränsen: samma knapp, samma tenantprefix, men
    headern kommer ur `workspaces.is_demo` via proxyn och kan inte sättas av en
    klient."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            # Egen slug som INTE börjar på testkund-, så att seedningen i
            # /api/keys inte gör provet grönt av fel skäl.
            skapad = await _skapa_tenant(client, "demo-arbetsyta-ef")
            nyckel = {"X-API-Key": skapad["api_key"]}
            assert skapad["kb_seeded"] == 0

            svar = await client.post(
                "/api/inbox/mock", headers={**nyckel, "X-Snajp-Demo": "true"}
            )
            assert svar.status_code == 201, svar.text
            kropp = svar.json()

            assert kropp["kb_seeded"] > 0
            assert kropp["kb_tom"] is False


@pytest.mark.anyio
async def test_seedningen_ar_idempotent():
    """Ett omtag ska inte dubblera basen. `ensure_tenant_kb` lämnar en tenant
    som redan har artiklar orörd."""
    async with app.router.lifespan_context(app):
        async with _client() as client:
            skapad = await _skapa_tenant(client, "testkund-99887766")
            nyckel = {"X-API-Key": skapad["api_key"]}
            forst = len((await client.get("/api/kb", headers=nyckel)).json()["articles"])

            svar = await client.post(
                "/api/inbox/mock", headers={**nyckel, "X-Snajp-Demo": "true"}
            )
            assert svar.json()["kb_seeded"] == 0

            efter = len((await client.get("/api/kb", headers=nyckel)).json()["articles"])
            assert efter == forst
