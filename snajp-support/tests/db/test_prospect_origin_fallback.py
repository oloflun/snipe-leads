"""Databasen kan sakna `prospects.origin` — koden ska överleva det, men inte ljuga.

Koden deployas från grenen; migrationerna körs av en människa med
databaslösenordet. De två landar aldrig samtidigt, och `039_prospect_origin`
var oskriven i Railways development-databas i timmar medan koden som använder
kolumnen redan var live.

Två utfall måste hållas isär under den timmen, och det är hela testfilen:

 * **Vanliga prospekt skapas ändå.** En ny kolumn får inte ta ner den
   befintliga pipelinen.
 * **Exempelbolag skapas INTE.** Utan `origin` finns ingen markering, och utan
   markering kan utskicksspärren inte skilja ett påhittat bolag från ett
   riktigt. Ett tyst fallande exempelbolag vore ett mejl som kan gå iväg.

Testerna kör mot en attrapp och inte mot Postgres: det som mäts är GRENEN i
koden, och den går att fastställa utan databas.
"""

from contextlib import asynccontextmanager

import asyncpg
import pytest

from app.storage.postgres import PostgresStorage

TENANT = "11111111-1111-1111-1111-111111111111"


class _FalskConn:
    """Svarar som en databas UTAN kolumnen origin."""

    def __init__(self) -> None:
        self.queries: list[str] = []

    @asynccontextmanager
    async def transaction(self):
        yield

    async def fetchval(self, *args, **kwargs):
        return None

    async def fetchrow(self, query: str, *args):
        self.queries.append(" ".join(query.split()))
        if "origin" in query:
            raise asyncpg.UndefinedColumnError('column "origin" of relation "prospects" does not exist')
        return {
            "id": "22222222-2222-2222-2222-222222222222",
            "tenant_id": args[0],
            "company_name": args[1],
            "contact_name": args[2],
            "contact_email": args[3],
            "status": "new",
        }


class _FalskPool:
    def __init__(self, conn: _FalskConn) -> None:
        self._conn = conn

    @asynccontextmanager
    async def acquire(self):
        yield self._conn


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def lagring():
    conn = _FalskConn()
    return PostgresStorage(_FalskPool(conn)), conn


@pytest.mark.anyio
async def test_vanligt_prospekt_skapas_aven_utan_kolumnen(lagring):
    storage, conn = lagring

    prospect = await storage.create_prospect(TENANT, company_name="Riktiga Bolaget AB")

    assert prospect["company_name"] == "Riktiga Bolaget AB"
    # Två försök: först med kolumnen, sedan utan. Ordningen är poängen —
    # den dagen migrationen ÄR körd tar det första försöket, och fallbacken
    # slutar användas av sig själv utan att någon rör koden.
    assert len(conn.queries) == 2
    assert "origin" in conn.queries[0]
    assert "origin" not in conn.queries[1]


@pytest.mark.anyio
async def test_exempelbolag_vagras_utan_kolumnen(lagring):
    storage, conn = lagring

    with pytest.raises(RuntimeError) as fel:
        await storage.create_prospect(
            TENANT, company_name="Nordvik Bygg AB", origin="example"
        )

    # Felet ska NAMNGE migrationen. "Något gick fel" hade skickat den som läser
    # in i koden i stället för till kommandot som löser det.
    assert "039" in str(fel.value)
    assert "origin" in str(fel.value)
    # Och ingen rad får ha skapats på vägen.
    assert len(conn.queries) == 1


@pytest.mark.anyio
async def test_ingen_annan_ursprungsmarkering_slinker_igenom(lagring):
    # Fallbacken gäller bara 'manual'. Skulle en tredje origin införas (import,
    # crm, …) ska den falla här och inte tyst tappa sin markering.
    storage, _ = lagring

    with pytest.raises(RuntimeError):
        await storage.create_prospect(TENANT, company_name="Importerad AB", origin="import")
