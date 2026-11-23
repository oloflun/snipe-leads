"""Tvåstegsverifieringens lagring (migration 128) mot en riktig Postgres.

Databasen ser aldrig hemligheten i klartext, så här prövas det databasen
ansvarar för: att bara plattformsadmin kan rulla in och bara sin egen rad, att
ett tidssteg och en återställningskod förbrukas EN gång (också samtidigt), att
avstängning kräver en nyss godkänd kod, och att approllerna inte når tabellerna
annat än genom funktionerna. Koden, kryptot och spärren prövas i
lib/auth/*.test.ts.

Körs i CI-jobbet `databas` (.github/workflows/verify.yml). Vägrar allt annat än
en lokal databas utan spegelmarkör. Kontona är syntetiska och raderas efteråt.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from urllib.parse import urlsplit

import asyncpg
import pytest

DSN = os.environ.get("GALLRING_TEST_DSN", "")
APP_DSN = os.environ.get("GALLRING_TEST_APP_DSN", "")
WEB_DSN = os.environ.get("GALLRING_TEST_WEB_DSN", "")

pytestmark = pytest.mark.skipif(
    not (DSN and APP_DSN and WEB_DSN),
    reason="Kräver GALLRING_TEST_DSN, GALLRING_TEST_APP_DSN och GALLRING_TEST_WEB_DSN mot en tom testdatabas.",
)

_LOKALA = {"localhost", "127.0.0.1", "::1"}
BLOB = "v1." + "a" * 40  # krypterad i webben; databasen bryr sig inte om innehållet
HASHAR = [f"{i:064x}" for i in range(1, 4)]


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _anslut(dsn: str) -> asyncpg.Connection:
    assert urlsplit(dsn).hostname in _LOKALA, "Testet körs bara mot en lokal databas."
    conn = await asyncpg.connect(dsn)
    assert not await conn.fetchval("select to_regclass('public.mirror_meta') is not null")
    return conn


async def _konto(agare, admin: bool) -> str:
    uid = await agare.fetchval(
        "insert into auth.users (email, encrypted_password, email_confirmed_at)"
        " values ($1, 'scrypt$1$x$y', now()) returning id",
        f"tvafaktor-{uuid.uuid4().hex[:10]}@example.test",
    )
    if admin:
        await agare.execute("insert into public.platform_admins (user_id) values ($1)", uid)
    return str(uid)


async def _stada(agare, konton: list[str]) -> None:
    for uid in konton:
        u = uuid.UUID(uid)
        ws = await agare.fetchval("select workspace_id from public.profiles where id = $1", u)
        await agare.execute("delete from public.platform_admins where user_id = $1", u)
        await agare.execute("delete from public.profiles where id = $1", u)
        await agare.execute("delete from auth.users where id = $1", u)
        if ws:
            await agare.execute("delete from public.workspaces where id = $1", ws)


async def _som(web, uid: str | None, sats: str, *args):
    """Som `sqlAsUser` i lib/db.ts: identiteten bara i transaktionen."""
    async with web.transaction():
        if uid:
            await web.execute("select set_config('app.user_id', $1, true)", uid)
        return await web.fetchval(sats, *args)


async def _las(web, uid: str):
    return await web.fetchrow("select * from public.tvafaktor_las($1::uuid)", uuid.UUID(uid))


async def _aktivt_konto(agare, web) -> str:
    uid = await _konto(agare, admin=True)
    assert await _som(web, uid, "select public.tvafaktor_paborja($1)", BLOB) is True
    assert await _som(web, uid, "select public.tvafaktor_aktivera($1::bigint, $2::text[], $3::text)", 1000, HASHAR, BLOB) is True
    return uid


@pytest.mark.anyio
async def test_inrullning_bara_for_plattformsadmin_och_egen_rad():
    agare, web = await _anslut(DSN), await _anslut(WEB_DSN)
    konton = []
    try:
        kund = await _konto(agare, admin=False)
        admin = await _konto(agare, admin=True)
        konton += [kund, admin]

        assert await _som(web, kund, "select public.tvafaktor_paborja($1)", BLOB) is False
        assert await _som(web, None, "select public.tvafaktor_paborja($1)", BLOB) is False
        assert await _las(web, kund) is None

        assert await _som(web, admin, "select public.tvafaktor_paborja($1)", BLOB) is True
        rad = await _las(web, admin)
        assert rad["aktiv"] is False and rad["hemlighet"] == BLOB and rad["koder_kvar"] == 0

        # Utan identitet eller med fel identitet aktiveras ingenting.
        akt = "select public.tvafaktor_aktivera($1::bigint, $2::text[], $3::text)"
        assert await _som(web, None, akt, 1000, HASHAR, BLOB) is False
        assert await _som(web, kund, akt, 1000, HASHAR, BLOB) is False
        assert await _som(web, admin, akt, 1000, HASHAR, BLOB) is True
        rad = await _las(web, admin)
        assert rad["aktiv"] is True and rad["senaste_steg"] == 1000 and rad["koder_kvar"] == 3

        # En aktiv rad skrivs inte över av en ny inrullning, och aktiveras inte två gånger.
        assert await _som(web, admin, "select public.tvafaktor_paborja($1)", "v1." + "b" * 40) is False
        assert (await _las(web, admin))["hemlighet"] == BLOB
        assert await _som(web, admin, akt, 2000, HASHAR, BLOB) is False

        # Ogiltiga hashar vägras högt.
        with pytest.raises(asyncpg.RaiseError):
            await _som(web, admin, akt, 1, ["inte-en-hash"], BLOB)
    finally:
        await _stada(agare, konton)
        await agare.close()
        await web.close()


@pytest.mark.anyio
async def test_tidssteget_forbrukas_en_gang():
    agare, web = await _anslut(DSN), await _anslut(WEB_DSN)
    konton = []
    try:
        uid = await _aktivt_konto(agare, web)
        konton.append(uid)
        steg = "select public.tvafaktor_anvand_steg($1::uuid, $2::bigint)"
        u = uuid.UUID(uid)
        assert await web.fetchval(steg, u, 1000) is False, "steget från aktiveringen är förbrukat"
        assert await web.fetchval(steg, u, 999) is False, "äldre steg"
        assert await web.fetchval(steg, u, 1001) is True
        assert await web.fetchval(steg, u, 1001) is False, "samma kod igen (återspelning)"

        # Två samtidiga inloggningar med samma kod: bara en går igenom.
        web2 = await _anslut(WEB_DSN)
        try:
            svar = await asyncio.gather(web.fetchval(steg, u, 1002), web2.fetchval(steg, u, 1002))
        finally:
            await web2.close()
        assert sorted(svar) == [False, True]
    finally:
        await _stada(agare, konton)
        await agare.close()
        await web.close()


@pytest.mark.anyio
async def test_aterstallningskoden_forbrukas_en_gang():
    agare, web = await _anslut(DSN), await _anslut(WEB_DSN)
    konton = []
    try:
        uid = await _aktivt_konto(agare, web)
        konton.append(uid)
        kod = "select public.tvafaktor_anvand_aterstallningskod($1::uuid, $2)"
        u = uuid.UUID(uid)
        assert await web.fetchval(kod, u, HASHAR[0]) is True
        assert await web.fetchval(kod, u, HASHAR[0]) is False
        assert await web.fetchval(kod, u, "f" * 64) is False, "okänd kod"
        assert (await _las(web, uid))["koder_kvar"] == 2
    finally:
        await _stada(agare, konton)
        await agare.close()
        await web.close()


@pytest.mark.anyio
async def test_avstangning_kraver_en_nyss_godkand_kod():
    agare, web = await _anslut(DSN), await _anslut(WEB_DSN)
    konton = []
    try:
        uid = await _aktivt_konto(agare, web)
        annan = await _konto(agare, admin=True)
        konton += [uid, annan]
        av = "select public.tvafaktor_avaktivera()"
        u = uuid.UUID(uid)

        # Ingen godkänd kod de senaste två minuterna: vägras.
        await agare.execute(
            "update public.tvafaktor set senast_verifierad_at = now() - interval '3 minutes' where user_id = $1", u
        )
        assert await _som(web, uid, av) is False
        assert (await _las(web, uid))["aktiv"] is True
        # Någon annans identitet tar inte bort raden.
        assert await _som(web, annan, av) is False
        assert await _las(web, uid) is not None

        # En godkänd kod (nytt tidssteg) öppnar för avstängning.
        assert await web.fetchval("select public.tvafaktor_anvand_steg($1::uuid, $2::bigint)", u, 5000) is True
        assert await _som(web, uid, av) is True
        assert await _las(web, uid) is None
        assert await agare.fetchval(
            "select count(*) from public.tvafaktor_aterstallningskoder where user_id = $1", u
        ) == 0
    finally:
        await _stada(agare, konton)
        await agare.close()
        await web.close()


@pytest.mark.anyio
async def test_approllerna_nar_inte_tabellerna():
    web, app = await _anslut(WEB_DSN), await _anslut(APP_DSN)
    try:
        for conn in (web, app):
            for fraga in (
                "select count(*) from public.tvafaktor",
                "select count(*) from public.tvafaktor_aterstallningskoder",
                "delete from public.tvafaktor",
                "update public.tvafaktor set aktiverad_at = null",
                "insert into public.tvafaktor_aterstallningskoder (user_id, kod_hash) values (gen_random_uuid(), 'x')",
            ):
                with pytest.raises(asyncpg.InsufficientPrivilegeError):
                    await conn.execute(fraga)
        # api:t har ingen anledning att röra tvåfaktorn alls.
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await app.fetchval("select * from public.tvafaktor_las(gen_random_uuid())")
    finally:
        await web.close()
        await app.close()


@pytest.mark.anyio
async def test_kontot_raderas_med_sin_tvafaktor():
    agare, web = await _anslut(DSN), await _anslut(WEB_DSN)
    try:
        uid = await _aktivt_konto(agare, web)
        await _stada(agare, [uid])
        u = uuid.UUID(uid)
        assert await agare.fetchval("select count(*) from public.tvafaktor where user_id = $1", u) == 0
        assert await agare.fetchval(
            "select count(*) from public.tvafaktor_aterstallningskoder where user_id = $1", u
        ) == 0
    finally:
        await agare.close()
        await web.close()


@pytest.mark.anyio
async def test_aktiveringen_galler_bara_den_verifierade_hemligheten():
    """Migration 132 (Codex runda 3, 2026-11-19): koden prövades mot hemlighet A,
    men en ny inrullning hann byta raden till B. Aktiveringen med A vägras och
    raden står kvar påbörjad med B; med B går den igenom."""
    agare, web = await _anslut(DSN), await _anslut(WEB_DSN)
    konton = []
    try:
        uid = await _konto(agare, admin=True)
        konton.append(uid)
        hemlighet_b = "v1." + "b" * 40
        akt = "select public.tvafaktor_aktivera($1::bigint, $2::text[], $3::text)"

        assert await _som(web, uid, "select public.tvafaktor_paborja($1)", BLOB) is True
        # Den parallella inrullningen byter hemlighet efter att A lästs och prövats.
        assert await _som(web, uid, "select public.tvafaktor_paborja($1)", hemlighet_b) is True

        assert await _som(web, uid, akt, 1000, HASHAR, BLOB) is False
        rad = await _las(web, uid)
        assert rad["aktiv"] is False and rad["hemlighet"] == hemlighet_b and rad["koder_kvar"] == 0

        assert await _som(web, None, akt, 1000, HASHAR, hemlighet_b) is False
        assert await _som(web, uid, akt, 1000, HASHAR, hemlighet_b) is True
        rad = await _las(web, uid)
        assert rad["aktiv"] is True and rad["hemlighet"] == hemlighet_b and rad["koder_kvar"] == 3

        with pytest.raises(asyncpg.RaiseError):
            await _som(web, uid, akt, 1000, HASHAR, None)
    finally:
        await _stada(agare, konton)
        await agare.close()
        await web.close()


@pytest.mark.anyio
async def test_en_gammal_paborjad_inrullning_kan_inte_aktiveras():
    """Migration 148 (Codex runda 15, 2026-11-20): webben kräver lösenordet
    innan en inrullning påbörjas, och den påbörjade raden gäller i femton
    minuter. En äldre rad aktiveras inte, inte ens med rätt hemlighet och kod;
    en ny påbörjan (med lösenordet igen) öppnar fönstret på nytt."""
    agare, web = await _anslut(DSN), await _anslut(WEB_DSN)
    konton = []
    try:
        uid = await _konto(agare, admin=True)
        konton.append(uid)
        akt = "select public.tvafaktor_aktivera($1::bigint, $2::text[], $3::text)"
        assert await _som(web, uid, "select public.tvafaktor_paborja($1)", BLOB) is True
        await agare.execute(
            "update public.tvafaktor set uppdaterad_at = now() - interval '16 minutes' where user_id = $1",
            uuid.UUID(uid))
        assert await _som(web, uid, akt, 1000, HASHAR, BLOB) is False
        assert (await _las(web, uid))["aktiv"] is False

        assert await _som(web, uid, "select public.tvafaktor_paborja($1)", BLOB) is True
        assert await _som(web, uid, akt, 1000, HASHAR, BLOB) is True
        assert (await _las(web, uid))["aktiv"] is True
    finally:
        await _stada(agare, konton)
        await agare.close()
        await web.close()

@pytest.mark.anyio
async def test_konto_utan_losenord_kan_inte_aktivera():
    """Migration 140 (Codex runda 8, 2026-11-19): ett konto från Google eller
    Microsoft saknar lösenord. Efter aktiveringen hade OAuth nekats och
    lösenordsvägen saknats, så aktiveringen vägras högt och raden står kvar
    påbörjad. Versionen med två argument, utan hemlighetsprövning, finns inte
    längre."""
    agare, web = await _anslut(DSN), await _anslut(WEB_DSN)
    konton = []
    try:
        uid = await _konto(agare, admin=True)
        konton.append(uid)
        await agare.execute("update auth.users set encrypted_password = null where id = $1", uuid.UUID(uid))
        akt = "select public.tvafaktor_aktivera($1::bigint, $2::text[], $3::text)"

        assert await _som(web, uid, "select public.tvafaktor_paborja($1)", BLOB) is True
        with pytest.raises(asyncpg.RaiseError, match="kraver_losenord"):
            await _som(web, uid, akt, 1000, HASHAR, BLOB)
        rad = await _las(web, uid)
        assert rad["aktiv"] is False and rad["koder_kvar"] == 0

        # Med ett lösenord går samma inrullning igenom.
        await agare.execute("update auth.users set encrypted_password = 'scrypt$1$x$y' where id = $1", uuid.UUID(uid))
        assert await _som(web, uid, akt, 1000, HASHAR, BLOB) is True

        assert await agare.fetchval(
            "select to_regprocedure('public.tvafaktor_aktivera(bigint, text[])') is null"
        ), "versionen med två argument ska vara borttagen"
    finally:
        await _stada(agare, konton)
        await agare.close()
        await web.close()


@pytest.mark.anyio
async def test_avbryt_rör_aldrig_ett_aktiverat_skydd():
    """Migration 131 (Codex runda 2, 2026-11-19): `tvafaktor_avbryt_inrullning`
    raderar bara en påbörjad rad. Direkt efter aktiveringen, när
    `tvafaktor_avaktivera()` själv hade godtagit raderingen, står skyddet kvar."""
    agare, web = await _anslut(DSN), await _anslut(WEB_DSN)
    konton = []
    try:
        aktiv = await _aktivt_konto(agare, web)
        konton.append(aktiv)
        avbryt = "select public.tvafaktor_avbryt_inrullning()"
        assert await _som(web, aktiv, avbryt) is False
        assert (await _las(web, aktiv))["aktiv"] is True
        assert await _som(web, None, avbryt) is False

        paborjad = await _konto(agare, admin=True)
        konton.append(paborjad)
        assert await _som(web, paborjad, "select public.tvafaktor_paborja($1)", BLOB) is True
        assert await _som(web, paborjad, avbryt) is True
        assert await _las(web, paborjad) is None
    finally:
        await _stada(agare, konton)
        await agare.close()
        await web.close()
