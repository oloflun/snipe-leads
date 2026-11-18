"""Demon markeras `is_demo` (migration 127) mot en riktig Postgres.

Felet som rättas: `startDemo` uppdaterade `workspaces.is_demo` som snajp_web
utan identitet, och satsen träffade noll rader eftersom tabellen saknar
update-policy. Testet kör samma väg som webben gör nu (identiteten satt i
transaktionen, som `sqlAsUser`, och funktionen `markera_demoarbetsyta()`), och
prövar att dörren är smal: bara ett nyss skapat demokonto, bara den egna tomma
arbetsytan, aldrig utan identitet, och webbens gamla update-rätt är borta.

Körs i CI-jobbet `databas` (.github/workflows/verify.yml). Vägrar allt annat än
en lokal databas utan spegelmarkör. Kontona är syntetiska och raderas efteråt.
"""

from __future__ import annotations

import os
import uuid
from urllib.parse import urlsplit

import asyncpg
import pytest

DSN = os.environ.get("GALLRING_TEST_DSN", "")
WEB_DSN = os.environ.get("GALLRING_TEST_WEB_DSN", "")

pytestmark = pytest.mark.skipif(
    not (DSN and WEB_DSN),
    reason="Kräver GALLRING_TEST_DSN och GALLRING_TEST_WEB_DSN mot en tom testdatabas.",
)

_LOKALA = {"localhost", "127.0.0.1", "::1"}
MARKERA = "select public.markera_demoarbetsyta()"


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _anslut(dsn: str) -> asyncpg.Connection:
    assert urlsplit(dsn).hostname in _LOKALA, "Testet körs bara mot en lokal databas."
    conn = await asyncpg.connect(dsn)
    assert not await conn.fetchval("select to_regclass('public.mirror_meta') is not null")
    return conn


async def _konto(agare, epost: str) -> tuple[str, str]:
    """Ett konto som startDemo skapar det; triggern ger profil och arbetsyta."""
    uid = await agare.fetchval(
        "insert into auth.users (email, encrypted_password, raw_user_meta_data, email_confirmed_at)"
        " values ($1, 'scrypt$1$x$y', jsonb_build_object('full_name', 'Demo'), now()) returning id",
        epost,
    )
    ws = await agare.fetchval("select workspace_id from public.profiles where id = $1", uid)
    assert ws, "triggern on_auth_user_created skapade ingen arbetsyta"
    return str(uid), str(ws)


async def _som_anvandare(web, uid: str | None) -> bool:
    """Samma som `sqlAsUser` i lib/db.ts: identiteten bara i transaktionen."""
    async with web.transaction():
        if uid:
            await web.execute("select set_config('app.user_id', $1, true)", uid)
        return await web.fetchval(MARKERA)


async def _ar_demo(agare, ws: str) -> bool:
    return await agare.fetchval("select is_demo from public.workspaces where id = $1", uuid.UUID(ws))


async def _stada(agare, konton: list[tuple[str, str]]) -> None:
    for uid, ws in konton:
        await agare.execute("delete from public.profiles where id = $1", uuid.UUID(uid))
        await agare.execute("delete from auth.users where id = $1", uuid.UUID(uid))
        await agare.execute("delete from public.workspaces where id = $1", uuid.UUID(ws))


def _demoadress() -> str:
    return f"demo-{uuid.uuid4()}@snajp.se"


@pytest.mark.anyio
async def test_demon_markeras_med_identiteten():
    agare, web = await _anslut(DSN), await _anslut(WEB_DSN)
    konton = []
    try:
        uid, ws = await _konto(agare, _demoadress())
        konton.append((uid, ws))
        assert not await _ar_demo(agare, ws)
        assert await _som_anvandare(web, uid) is True
        assert await _ar_demo(agare, ws)
    finally:
        await _stada(agare, konton)
        await agare.close()
        await web.close()


@pytest.mark.anyio
async def test_gamla_vagen_ar_stangd():
    # Felet: en UPDATE som snajp_web utan identitet. Den ska nu vägras högt
    # i stället för att tyst träffa noll rader.
    web = await _anslut(WEB_DSN)
    try:
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await web.execute(
                "update public.workspaces set is_demo = true"
                " from public.profiles p where workspaces.id = p.workspace_id and p.id = $1",
                uuid.uuid4(),
            )
    finally:
        await web.close()


@pytest.mark.anyio
async def test_dorren_ar_smal():
    agare, web = await _anslut(DSN), await _anslut(WEB_DSN)
    konton = []
    try:
        # Utan identitet: ingenting.
        assert await _som_anvandare(web, None) is False

        # En vanlig kund kan inte märka sin arbetsyta.
        kund = await _konto(agare, f"kund-{uuid.uuid4().hex[:8]}@example.test")
        konton.append(kund)
        assert await _som_anvandare(web, kund[0]) is False
        assert not await _ar_demo(agare, kund[1])

        # Ett gammalt demokonto (äldre än tio minuter): nej.
        gammal = await _konto(agare, _demoadress())
        konton.append(gammal)
        await agare.execute(
            "update auth.users set created_at = now() - interval '11 minutes' where id = $1",
            uuid.UUID(gammal[0]),
        )
        assert await _som_anvandare(web, gammal[0]) is False
        assert not await _ar_demo(agare, gammal[1])

        # En arbetsyta med slug (kopplad till en kund): nej.
        kopplad = await _konto(agare, _demoadress())
        konton.append(kopplad)
        await agare.execute(
            "update public.workspaces set slug = $2 where id = $1",
            uuid.UUID(kopplad[1]), f"test-127-{uuid.uuid4().hex[:8]}",
        )
        assert await _som_anvandare(web, kopplad[0]) is False
        assert not await _ar_demo(agare, kopplad[1])

        # En arbetsyta med en annan medlem: nej.
        delad = await _konto(agare, _demoadress())
        konton.append(delad)
        annan = await _konto(agare, f"annan-{uuid.uuid4().hex[:8]}@example.test")
        konton.append(annan)
        await agare.execute(
            "update public.profiles set workspace_id = $2 where id = $1",
            uuid.UUID(annan[0]), uuid.UUID(delad[1]),
        )
        assert await _som_anvandare(web, delad[0]) is False
        assert not await _ar_demo(agare, delad[1])
    finally:
        await _stada(agare, konton)
        await agare.close()
        await web.close()
