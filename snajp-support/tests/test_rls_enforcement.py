"""Bevisar att DATABASEN, inte bara appkoden, stoppar en tenant-läcka.

Alla andra isoleringstester kör mot MemoryStorage och bevisar därför bara att
*applikationen* filtrerar rätt. Om någon skriver en ny query och glömmer
`where tenant_id = $1` ska RLS-policyerna i 003/004/006 fånga det. Det är den
egenskapen som testas här — genom att medvetet köra queries UTAN tenant-filter
och kräva att databasen returnerar noll rader ändå.

Kräver en riktig Postgres med migrationerna körda. Sätt TEST_DATABASE_URL till
en ENGÅNGSDATABAS — testerna skriver och raderar data. Peka den ALDRIG mot
produktionsdatabasen.

    $env:TEST_DATABASE_URL = "postgresql://snajp_app:...@localhost:5432/snajp_test"
    python -m pytest tests/test_rls_enforcement.py -v

VIKTIGT om rollen: RLS gäller inte för roller med BYPASSRLS, och Supabases
`postgres`-roll har det. Körs testet som `postgres` kommer det att FALLA — det
är rätt utfall, för då är RLS inert även i drift. Använd den dedikerade
`snajp_app`-rollen (se 008_snajp_app_role.sql).
"""

import os
import uuid

import pytest

asyncpg = pytest.importorskip("asyncpg")

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL saknas — RLS kan bara verifieras mot en riktig Postgres.",
)

TENANT_A = "00000000-0000-4000-a000-00000000aa01"
TENANT_B = "00000000-0000-4000-a000-00000000bb02"


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _connect():
    return await asyncpg.connect(TEST_DATABASE_URL, statement_cache_size=0)


async def _set_tenant(conn, tenant_id: str | None):
    if tenant_id is None:
        await conn.fetchval("select set_config('app.tenant_id', '', true)")
    else:
        await conn.fetchval("select set_config('app.tenant_id', $1, true)", tenant_id)


@pytest.fixture
async def seeded():
    """Två tenants med var sin KB-artikel och var sitt ärende."""
    conn = await _connect()
    tx = conn.transaction()
    await tx.start()
    try:
        for tenant_id, slug in ((TENANT_A, "rls-a"), (TENANT_B, "rls-b")):
            await conn.execute(
                """
                insert into ss_tenants (id, slug, name) values ($1, $2, $2)
                on conflict (id) do nothing
                """,
                tenant_id,
                slug,
            )
        marker = uuid.uuid4().hex
        for tenant_id in (TENANT_A, TENANT_B):
            await _set_tenant(conn, tenant_id)
            await conn.execute(
                """
                insert into ss_knowledge_base (tenant_id, title, content, category)
                values ($1, $2, $3, 'ovrigt')
                """,
                tenant_id,
                f"Hemlighet {marker}",
                f"Innehåll som bara {tenant_id} får se.",
            )
        yield conn, marker
    finally:
        # Rullas alltid tillbaka — testet lämnar inga rader efter sig.
        await tx.rollback()
        await conn.close()


@pytest.mark.anyio
async def test_role_does_not_bypass_rls():
    """Grundförutsättningen: en roll med BYPASSRLS gör alla policyer verkningslösa."""
    conn = await _connect()
    try:
        row = await conn.fetchrow(
            "select current_user as role, rolbypassrls from pg_roles where rolname = current_user"
        )
    finally:
        await conn.close()
    assert not row["rolbypassrls"], (
        f"Rollen {row['role']} har BYPASSRLS — RLS-policyerna gäller inte för den, "
        "så databasen skyddar ingenting. Kör tjänsten som snajp_app "
        "(008_snajp_app_role.sql) i stället."
    )


@pytest.mark.anyio
async def test_query_without_tenant_filter_returns_only_own_rows(seeded):
    """En glömd where-sats ska inte kunna läcka — RLS filtrerar ändå."""
    conn, marker = seeded

    await _set_tenant(conn, TENANT_A)
    rows = await conn.fetch(
        "select tenant_id from ss_knowledge_base where title = $1", f"Hemlighet {marker}"
    )
    assert len(rows) == 1, "Utan tenant-filter i queryn syntes fler än den egna raden."
    assert str(rows[0]["tenant_id"]) == TENANT_A


@pytest.mark.anyio
async def test_reading_other_tenant_explicitly_is_denied(seeded):
    """Även ett medvetet försök att läsa fel tenant_id ska ge noll rader."""
    conn, _ = seeded

    await _set_tenant(conn, TENANT_A)
    rows = await conn.fetch(
        "select id from ss_knowledge_base where tenant_id = $1", TENANT_B
    )
    assert rows == [], "Databasen lämnade ut en annan tenants rader på direkt förfrågan."


@pytest.mark.anyio
async def test_writing_as_another_tenant_is_rejected(seeded):
    """with check ska hindra att en tenant skriver rader åt en annan."""
    conn, _ = seeded

    await _set_tenant(conn, TENANT_A)
    with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
        await conn.execute(
            """
            insert into ss_knowledge_base (tenant_id, title, content, category)
            values ($1, 'Planterad', 'Skriven av fel tenant', 'ovrigt')
            """,
            TENANT_B,
        )


@pytest.mark.anyio
async def test_without_tenant_context_nothing_is_visible(seeded):
    """Utan app.tenant_id (t.ex. en bortglömd _scoped) ska inget synas."""
    conn, marker = seeded

    await _set_tenant(conn, None)
    rows = await conn.fetch(
        "select id from ss_knowledge_base where title = $1", f"Hemlighet {marker}"
    )
    assert rows == [], "Rader syntes utan att app.tenant_id var satt."


@pytest.mark.anyio
async def test_usage_table_is_rls_protected(seeded):
    """ss_usage (006) måste ha samma skydd som resten — det är faktureringsunderlag."""
    conn, _ = seeded

    await _set_tenant(conn, TENANT_A)
    await conn.execute(
        "insert into ss_usage (tenant_id, kind, responses) values ($1, 'chat', 1)", TENANT_A
    )
    await _set_tenant(conn, TENANT_B)
    rows = await conn.fetch("select id from ss_usage where tenant_id = $1", TENANT_A)
    assert rows == [], "Tenant B kunde läsa tenant A:s förbrukning."
