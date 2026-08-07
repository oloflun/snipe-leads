"""INV-SEC-001, plan Verifiering ('Isolering (G1/G2): ... direkt mot
databasen ... Måste ge noll rader, inte filtrerade rader'). Kör mot en
riktig databas — hoppas över utan DATABASE_URL (samma mönster som CI utan
en riktig Postgres-instans skulle behöva).

Manuellt verifierat en gång direkt mot produktions-Supabase 2026-08-07 via
en transaktion som rullades tillbaka (ingen data lämnades kvar): som
snajp_app-rollen, scopad till Nordlys Handels tenant_id, gav en direkt
id-läsning av ett Livrustnings-ärende 0 rader trots att raden fanns i
samma transaktion. Det här testet gör samma verifiering repeterbart.
"""

import os
import uuid

import asyncpg
import pytest

DATABASE_URL = os.environ.get("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="Kräver en riktig Postgres-anslutning (DATABASE_URL)."
)


@pytest.mark.anyio
async def test_snajp_app_role_cannot_read_another_tenants_ticket_by_direct_id():
    """Skapar en tillfällig kund + ärende för tenant A i en transaktion som
    ALLTID rullas tillbaka, försöker läsa den — som snajp_app, scopad till
    tenant B — och kräver noll rader. Rör aldrig riktig data."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        tenants = await conn.fetch("select id, slug from ss_tenants order by slug limit 2")
        if len(tenants) < 2:
            pytest.skip("Kräver minst två tenants i databasen för ett meningsfullt test.")
        tenant_a, tenant_b = tenants[0]["id"], tenants[1]["id"]

        customer_id = str(uuid.uuid4())
        ticket_id = str(uuid.uuid4())

        tx = conn.transaction()
        await tx.start()
        try:
            await conn.execute(
                "insert into ss_customers (id, tenant_id, name) values ($1, $2, 'RLS-isoleringstest')",
                customer_id,
                tenant_a,
            )
            await conn.execute(
                """insert into ss_tickets (id, tenant_id, customer_id, subject, category)
                   values ($1, $2, $3, 'RLS-isoleringstest', 'ovrigt')""",
                ticket_id,
                tenant_a,
                customer_id,
            )

            await conn.execute("set local role snajp_app")
            await conn.execute("select set_config('app.tenant_id', $1, true)", str(tenant_b))

            leaked = await conn.fetchval(
                "select count(*) from ss_tickets where id = $1", ticket_id
            )
            assert leaked == 0, (
                "snajp_app scopad till fel tenant kunde läsa ett annat tenants ärende "
                "direkt på id — RLS läcker."
            )
        finally:
            await tx.rollback()  # ALDRIG lämna testdata i en riktig databas
    finally:
        await conn.close()
