"""Kunskapsbasens källa och giltighetstid (migration 117).

Agenten grundar sina svar i det search_kb lämnar ut. En artikel som gått ut
(ett kampanjpris, ett gammalt öppettider-schema) är därför sämre än ingen
artikel: modellen citerar den som om den gällde. Sökningen ska alltså tiga om
den, medan portalens lista visar den så att kunden ser vad som behöver bytas.

Källan (`source_url`) togs redan fram av webbskanningen men tappades vid
sparandet. Den ska nu följa med hela vägen: in via POST /api/kb, ut i listan
och i sökträffen.

Bara MemoryStorage körs här. Postgres-vägens SQL (app/storage/postgres.py,
_sok_vektor och _sok_fulltext) är inte testad mot en riktig databas.
"""

from datetime import date, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app
from app.storage.memory import MemoryStorage

MASTER = {"X-API-Key": get_settings().snajp_master_api_key}
TENANT = "kb-kalla-giltighet"

# Långt från dagsgränsen med flit, så att testet inte beror på tidszonen.
IGAR_FOR_LANGE_SEDAN = date.today() - timedelta(days=30)
LANGT_FRAM = date.today() + timedelta(days=30)


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _tre_artiklar(storage: MemoryStorage) -> None:
    await storage.add_kb_article(
        TENANT, title="Fraktpris kampanj", content="Fraktfritt under kampanjen, frakt noll kronor.",
        category="ovrigt", giltig_till=IGAR_FOR_LANGE_SEDAN,
    )
    await storage.add_kb_article(
        TENANT, title="Fraktpris tills vidare", content="Frakt kostar 49 kronor inom Sverige.",
        category="ovrigt", source_url="https://exempelbolaget.se/frakt",
    )
    await storage.add_kb_article(
        TENANT, title="Fraktpris i vinter", content="Frakt kostar 29 kronor hela vintern.",
        category="ovrigt", giltig_till=LANGT_FRAM,
    )


@pytest.mark.anyio
async def test_utgangen_artikel_doljs_i_sokningen_men_syns_i_listan():
    storage = MemoryStorage()
    await _tre_artiklar(storage)

    traffar = await storage.search_kb(TENANT, "fraktpris frakt", limit=10)
    titlar = {t["title"] for t in traffar}
    assert "Fraktpris kampanj" not in titlar

    lista = await storage.list_kb(TENANT)
    utgangen = next(a for a in lista if a["title"] == "Fraktpris kampanj")
    assert utgangen["giltig_till"] == IGAR_FOR_LANGE_SEDAN.isoformat()


@pytest.mark.anyio
async def test_artikel_utan_datum_och_med_framtida_datum_kommer_tillbaka():
    storage = MemoryStorage()
    await _tre_artiklar(storage)

    titlar = {t["title"] for t in await storage.search_kb(TENANT, "fraktpris frakt", limit=10)}
    assert titlar == {"Fraktpris tills vidare", "Fraktpris i vinter"}


@pytest.mark.anyio
async def test_kallan_foljer_med_i_traffen_och_listan():
    storage = MemoryStorage()
    await _tre_artiklar(storage)

    traff = next(
        t for t in await storage.search_kb(TENANT, "fraktpris frakt", limit=10)
        if t["title"] == "Fraktpris tills vidare"
    )
    assert traff["source_url"] == "https://exempelbolaget.se/frakt"
    # Befintliga nycklar har samma form som förut.
    assert {"id", "title", "content", "category", "similarity"} <= set(traff)

    lista = {a["title"]: a for a in await storage.list_kb(TENANT)}
    assert lista["Fraktpris tills vidare"]["source_url"] == "https://exempelbolaget.se/frakt"
    assert lista["Fraktpris tills vidare"]["giltig_till"] is None
    assert lista["Fraktpris kampanj"]["source_url"] is None


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _nyckel(client, slug: str) -> dict:
    svar = await client.post(
        "/api/keys", headers=MASTER, json={"tenant_name": f"Test {slug}", "slug": slug}
    )
    assert svar.status_code == 201, svar.text
    return {"X-API-Key": svar.json()["api_key"]}


@pytest.mark.anyio
async def test_api_sparar_kalla_och_giltighet():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            nyckel = await _nyckel(client, "kb-kalla-api-ab")
            svar = await client.post(
                "/api/kb",
                headers=nyckel,
                json={
                    "articles": [
                        {
                            "title": "Öppettider sommar",
                            "content": "Vi har sommaröppet 10 till 15 på vardagar.",
                            "source_url": "https://exempelbolaget.se/oppettider",
                            "giltig_till": IGAR_FOR_LANGE_SEDAN.isoformat(),
                        },
                        {
                            "title": "Öppettider",
                            "content": "Vi har öppet 9 till 17 på vardagar.",
                        },
                    ]
                },
            )
            assert svar.status_code == 201, svar.text
            skapad = svar.json()["created"][0]
            assert skapad["source_url"] == "https://exempelbolaget.se/oppettider"
            assert skapad["giltig_till"] == IGAR_FOR_LANGE_SEDAN.isoformat()

            artiklar = {
                a["title"]: a
                for a in (await client.get("/api/kb", headers=nyckel)).json()["articles"]
            }
            # Listan visar även den utgångna, med sina fält.
            assert artiklar["Öppettider sommar"]["source_url"] == "https://exempelbolaget.se/oppettider"
            assert artiklar["Öppettider sommar"]["giltig_till"] == IGAR_FOR_LANGE_SEDAN.isoformat()
            assert artiklar["Öppettider"]["source_url"] is None
            assert artiklar["Öppettider"]["giltig_till"] is None

            # Sökningen som agenten använder lämnar inte ut den utgångna.
            tenant_id = next(
                t["id"] for t in await app.state.storage.list_tenants()
                if t.get("slug") == "kb-kalla-api-ab"
            )
            titlar = {
                t["title"]
                for t in await app.state.storage.search_kb(tenant_id, "öppettider vardagar", limit=10)
            }
            assert titlar == {"Öppettider"}


@pytest.mark.anyio
@pytest.mark.parametrize(
    "nummer,adress",
    list(enumerate([
        "ftp://exempelbolaget.se/fil",
        "javascript:alert(1)",
        "exempelbolaget.se/frakt",
        "https://",
        "https://exempel bolaget.se",
        "https://exempelbolaget.se/" + "a" * 2100,
    ])),
)
async def test_ogiltig_kalla_avvisas(nummer, adress):
    async with app.router.lifespan_context(app):
        async with _client() as client:
            nyckel = await _nyckel(client, f"kb-kalla-ogiltig-{nummer}")
            svar = await client.post(
                "/api/kb",
                headers=nyckel,
                json={
                    "articles": [
                        {
                            "title": "Frakt",
                            "content": "Frakt kostar 49 kronor inom Sverige.",
                            "source_url": adress,
                        }
                    ]
                },
            )
            assert svar.status_code == 422, svar.text
            assert (await client.get("/api/kb", headers=nyckel)).json()["articles"] == []
