"""INV-SEC-001, plan Verifiering ('Isolering (G1/G2): ... direkt mot
databasen ... Måste ge noll rader, inte filtrerade rader'). Kör mot en
riktig databas — hoppas över utan DATABASE_URL. I CI körs det i jobbet
`databastester` (.github/workflows/verify.yml) mot hela migrationskedjan.

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
        customer_id = str(uuid.uuid4())
        ticket_id = str(uuid.uuid4())

        tx = conn.transaction()
        await tx.start()
        try:
            # Två egna kunder i samma transaktion som rullas tillbaka, så att
            # testet går mot en tom databas också: CI-jobbet `databastester`
            # reser kedjan från noll och har inga kunder (2026-11-18). Förut
            # hoppades testet över där, och RLS prövades aldrig i CI.
            tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
            for tid in (tenant_a, tenant_b):
                await conn.execute(
                    "insert into ss_tenants (id, slug, name) values ($1, $2, $3)",
                    tid, f"rls-{tid.hex[:12]}", "RLS-isoleringstest",
                )

            # Scopa till tenant A INNAN seedningen. Utan den här raden kan
            # testet bara köras som en roll med BYPASSRLS — alltså precis den
            # roll vars frånvaro testet finns för att bevisa. Kört som
            # snajp_app föll insert:en på WITH CHECK-policyn i stället för att
            # mäta något, vilket är varför det aldrig gick att lita på.
            await conn.execute("select set_config('app.tenant_id', $1, true)", str(tenant_a))

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
