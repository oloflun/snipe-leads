"""Åtkomstloggen (migration 123) mot en riktig Postgres med hela kedjan.

Prövar det minneslagret inte kan: att snajp_app skriver raden genom
logga_adminatkomst men inte kan skriva, ändra eller radera i audit_logs
direkt; att en uppgiven admin bara räknas om den står i platform_admins; att
rader äldre än 365 dagar gallras och att äldre radtyper lämnas; och att
kundbesöket (log_admin_impersonation) skriver i loggen.

Körs i CI-jobbet `databas` (.github/workflows/verify.yml) med samma två
anslutningar som gallringstestet, och vägrar allt annat än en lokal databas
utan spegelmarkör. Alla rader är syntetiska (example.com, påhittade bolag).
"""

from __future__ import annotations

import os
import uuid
from urllib.parse import urlsplit

import asyncpg
import pytest

DSN = os.environ.get("GALLRING_TEST_DSN", "")
APP_DSN = os.environ.get("GALLRING_TEST_APP_DSN", "")

pytestmark = pytest.mark.skipif(
    not (DSN and APP_DSN),
    reason="Kräver GALLRING_TEST_DSN och GALLRING_TEST_APP_DSN mot en tom testdatabas.",
)

_LOKALA = {"localhost", "127.0.0.1", "::1"}
FUNK = "select public.logga_adminatkomst($1, $2::uuid, $3::uuid, $4, $5, $6::uuid, $7)"


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _anslut(dsn: str) -> asyncpg.Connection:
    assert urlsplit(dsn).hostname in _LOKALA, "Testet körs bara mot en lokal databas."
    conn = await asyncpg.connect(dsn)
    assert not await conn.fetchval("select to_regclass('public.mirror_meta') is not null")
    return conn


async def _uppsattning(agare) -> dict:
    tid = uuid.uuid4()
    await agare.execute(
        "insert into ss_tenants (id, slug, name) values ($1, $2, $3)",
        tid, f"adminlogg-{tid.hex[:8]}", "Testbolag Adminlogg",
    )
    admin = await agare.fetchval(
        "insert into auth.users (email) values ($1) returning id",
        f"admin-{tid.hex[:8]}@example.com",
    )
    await agare.execute("insert into platform_admins (user_id) values ($1)", admin)
    return {"tenant": tid, "admin": admin}


async def _stada(agare, u: dict) -> None:
    await agare.execute("delete from audit_logs where tenant_id = $1 or actor_user_id = $2",
                        u["tenant"], u["admin"])
    await agare.execute("delete from platform_admins where user_id = $1", u["admin"])
    await agare.execute("delete from workspaces where ss_tenant_id = $1", u["tenant"])
    await agare.execute("delete from ss_tenants where id = $1", u["tenant"])


@pytest.mark.anyio
async def test_appen_skriver_genom_funktionen_och_admin_provas():
    agare, app = await _anslut(DSN), await _anslut(APP_DSN)
    u = await _uppsattning(agare)
    try:
        assert await app.fetchval(
            FUNK, "master", u["admin"], u["tenant"], "PUT",
            "/api/admin/tenants/{tenant_id}/kunddata", None, "anrop12345678",
        ) is True
        # Ett påhittat admin-id ger en rad utan admin, aldrig en falsk.
        assert await app.fetchval(
            FUNK, "master", uuid.uuid4(), u["tenant"], "GET",
            "/api/admin/tenants/{tenant_id}/runs", None, None,
        ) is False

        rader = await agare.fetch(
            "select action, entity_type, actor_user_id, aktor, kanal, metod, resurs, request_id, "
            "workspace_id from audit_logs where tenant_id = $1 order by created_at, action desc",
            u["tenant"],
        )
        assert len(rader) == 2
        andra = next(r for r in rader if r["metod"] == "PUT")
        las = next(r for r in rader if r["metod"] == "GET")
        assert andra["action"] == "andra" and andra["aktor"] == "plattformsadmin"
        assert andra["actor_user_id"] == u["admin"]
        assert andra["resurs"] == "/api/admin/tenants/{tenant_id}/kunddata"
        assert andra["request_id"] == "anrop12345678"
        assert andra["workspace_id"] is None and andra["kanal"] == "master"
        assert las["action"] == "las" and las["aktor"] == "master-nyckel"
        assert las["actor_user_id"] is None

        # En okänd kund ger en rad utan kund, inte ett fel.
        await app.fetchval(FUNK, "master", None, uuid.uuid4(), "GET", "/api/admin/runs", None, None)
    finally:
        await agare.execute("delete from audit_logs where kanal = 'master' and tenant_id is null "
                            "and resurs = '/api/admin/runs'")
        await _stada(agare, u)
        await agare.close()
        await app.close()


@pytest.mark.anyio
async def test_appen_kan_inte_skriva_om_loggen():
    agare, app = await _anslut(DSN), await _anslut(APP_DSN)
    u = await _uppsattning(agare)
    try:
        await app.fetchval(FUNK, "master", u["admin"], u["tenant"], "GET", "/api/admin/usage", None, None)
        for sats in (
            "insert into audit_logs (action, entity_type, kanal) values ('las', 'admin_api', 'master')",
            "update audit_logs set aktor = 'nagon annan'",
            "delete from audit_logs",
        ):
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await app.execute(sats)
        assert await agare.fetchval(
            "select count(*) from audit_logs where tenant_id = $1", u["tenant"]
        ) == 1
    finally:
        await _stada(agare, u)
        await agare.close()
        await app.close()


@pytest.mark.anyio
async def test_gallringen_tar_bara_aldre_atkomstrader():
    agare, app = await _anslut(DSN), await _anslut(APP_DSN)
    u = await _uppsattning(agare)
    try:
        gammal = await agare.fetchval(
            "insert into audit_logs (action, entity_type, kanal, tenant_id, created_at) "
            "values ('las', 'admin_api', 'master', $1, now() - interval '400 days') returning id",
            u["tenant"],
        )
        ung = await agare.fetchval(
            "insert into audit_logs (action, entity_type, kanal, tenant_id, created_at) "
            "values ('las', 'admin_api', 'master', $1, now() - interval '300 days') returning id",
            u["tenant"],
        )
        ws = await agare.fetchval(
            "insert into workspaces (name, ss_tenant_id) values ('Testyta', $1) returning id", u["tenant"]
        )
        # En äldre radtyp (utan kanal) rörs inte, hur gammal den än är.
        aldre_typ = await agare.fetchval(
            "insert into audit_logs (workspace_id, action, entity_type, created_at) "
            "values ($1, 'konto', 'workspace', now() - interval '900 days') returning id",
            ws,
        )
        await app.fetchval(FUNK, "master", None, u["tenant"], "GET", "/api/admin/usage", None, None)
        kvar = {r["id"] for r in await agare.fetch(
            "select id from audit_logs where id = any($1::uuid[])", [gammal, ung, aldre_typ]
        )}
        assert gammal not in kvar
        assert ung in kvar and aldre_typ in kvar
    finally:
        await agare.execute("delete from audit_logs where workspace_id in "
                            "(select id from workspaces where ss_tenant_id = $1)", u["tenant"])
        await _stada(agare, u)
        await agare.close()
        await app.close()


@pytest.mark.anyio
async def test_kundbesoket_skrivs_i_atkomstloggen():
    agare = await _anslut(DSN)
    u = await _uppsattning(agare)
    slug = f"besok-{u['tenant'].hex[:8]}"
    try:
        await agare.execute(
            "insert into workspaces (name, slug, ss_tenant_id) values ('Besöksyta', $1, $2)",
            slug, u["tenant"],
        )
        async with agare.transaction():
            await agare.execute("select set_config('app.user_id', $1, true)", str(u["admin"]))
            await agare.execute("select public.log_admin_impersonation($1)", slug)
        rad = await agare.fetchrow(
            "select action, kanal, aktor, actor_user_id, resurs from audit_logs "
            "where tenant_id = $1 and kanal = 'kundbesok'",
            u["tenant"],
        )
        assert rad is not None
        assert rad["action"] == "oppna" and rad["aktor"] == "plattformsadmin"
        assert rad["actor_user_id"] == u["admin"]
        assert rad["resurs"] == f"arbetsyta:{slug}"

        # Den som inte är admin ger ingen rad.
        async with agare.transaction():
            await agare.execute("select set_config('app.user_id', $1, true)", str(uuid.uuid4()))
            await agare.execute("select public.log_admin_impersonation($1)", slug)
        assert await agare.fetchval(
            "select count(*) from audit_logs where tenant_id = $1 and kanal = 'kundbesok'", u["tenant"]
        ) == 1
    finally:
        await agare.execute("delete from platform_events where tenant_id = $1", u["tenant"])
        await _stada(agare, u)
        await agare.close()
