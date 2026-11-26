"""Mot en riktig Postgres, som approllen snajp_app: Hjälprutans lagring
(migration 156 och 157, PostgresStorage-sektionen "Hjälprutan").

* Plattformsärendena nås bara utan tenant-kontext: en kundskopad anslutning
  ser inga ärenden och kan inte skriva några.
* Den villkorade updaten i `andra_plattformsarende` ger None i fel läge och
  för en annan rapportör, och skriver då ingen händelse.
* Ett förslag med kalla 'chatt' får sakna skanning, ett med kalla
  'skanning' får det inte (villkoret i 157).

Körs i CI-jobbet `databas` (.github/workflows/verify.yml), samma form som
test_kb_forslag_atomisk.py. Vägrar allt annat än en lokal databas utan
spegelmarkör. Allt är syntetiskt och raderas efteråt av ägarrollen.
"""

from __future__ import annotations

import os
import uuid
from urllib.parse import urlsplit

import asyncpg
import pytest

DSN = os.environ.get("GALLRING_TEST_DSN", "")
APP_DSN = os.environ.get("GALLRING_TEST_APP_DSN", "")
_LOKALA = {"localhost", "127.0.0.1", "::1"}

pytestmark = pytest.mark.skipif(
    not (DSN and APP_DSN),
    reason="Kräver GALLRING_TEST_DSN och GALLRING_TEST_APP_DSN mot en tom testdatabas.",
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _agare() -> asyncpg.Connection:
    assert urlsplit(DSN).hostname in _LOKALA, "Testet körs bara mot en lokal databas."
    conn = await asyncpg.connect(DSN)
    assert not await conn.fetchval("select to_regclass('public.mirror_meta') is not null")
    return conn


def _falt(rapportor: str) -> dict:
    return {
        "rapportor_user_id": rapportor,
        "rapportor_namn": "Test Testsson",
        "kund_workspace_id": str(uuid.uuid4()),
        "kund_tenant_slug": "kund-test",
        "vy": "leads",
        "roll": "agare",
        "besok_av_admin": False,
        "sida": "/leads",
        "gjorde": "Klickade på Kör Iris",
        "hande": "Inget hände",
        "vantade": "En körning",
        "bild": None,
    }


@pytest.mark.anyio
async def test_arendena_nas_bara_utan_tenantkontext():
    from app.storage.postgres import PostgresStorage

    agare = await _agare()
    tid = uuid.uuid4()
    await agare.execute(
        "insert into ss_tenants (id, slug, name) values ($1, $2, 'Hjälptest')", tid, f"hj-{tid.hex[:12]}"
    )
    pool = await asyncpg.create_pool(APP_DSN, min_size=1, max_size=1)
    arende_id = None
    try:
        lager = PostgresStorage(pool)
        arende = await lager.skapa_plattformsarende(_falt(str(uuid.uuid4())))
        arende_id = arende["id"]
        assert arende["nummer"].startswith("F-") and arende["status"] == "mottagen"
        assert [h["typ"] for h in arende["handelser"]] == ["skapad"]
        assert arende["har_bild"] is False

        async with lager._scoped(str(tid)) as conn:
            assert await conn.fetchval("select count(*) from plattformsarenden") == 0
            assert await conn.fetchval("select count(*) from plattformsarende_handelser") == 0
        with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
            async with lager._scoped(str(tid)) as conn:
                await conn.execute(
                    """
                    insert into plattformsarenden
                      (nummer, rapportor_user_id, kund_workspace_id, kund_tenant_slug, vy, roll, sida, gjorde, hande)
                    values ('F-ZZZZ', $1, $1, 'x', 'x', 'x', '/', 'x', 'x')
                    """,
                    uuid.uuid4(),
                )
        # Approllen får inte radera ärenden (156 tar bort rätten).
        async with pool.acquire() as conn:
            with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
                await conn.execute("delete from plattformsarenden where id = $1::uuid", arende_id)
    finally:
        await pool.close()
        if arende_id:
            await agare.execute("delete from plattformsarenden where id = $1::uuid", arende_id)
        await agare.execute("delete from ss_tenants where id = $1", tid)
        await agare.close()


@pytest.mark.anyio
async def test_villkorad_andring_i_fel_lage_ger_none_och_ingen_handelse():
    from app.storage.postgres import PostgresStorage

    agare = await _agare()
    pool = await asyncpg.create_pool(APP_DSN, min_size=1, max_size=1)
    rapportor = str(uuid.uuid4())
    arende_id = None
    try:
        lager = PostgresStorage(pool)
        arende = await lager.skapa_plattformsarende(_falt(rapportor))
        arende_id = arende["id"]
        handelse = {"typ": "utslag", "meddelande": None, "synlig_for_kund": True, "aktor": "kund"}

        # Fel läge: ärendet är mottaget, inte redo att testa.
        assert await lager.andra_plattformsarende(
            arende_id, status="kund_godkand", handelse=handelse,
            kraver_status=("redo_att_testa",), rapportor_user_id=rapportor,
        ) is None

        satt = await lager.andra_plattformsarende(
            arende_id, status="redo_att_testa",
            handelse={"typ": "status", "meddelande": "Prova nu", "synlig_for_kund": True, "aktor": "plattformsadmin"},
            testversion_url="https://test.exempel.se", satt_testversion=True,
        )
        assert satt and satt["status"] == "redo_att_testa"
        assert satt["testversion_url"] == "https://test.exempel.se"

        # Rätt läge men en annan rapportör.
        assert await lager.andra_plattformsarende(
            arende_id, status="kund_godkand", handelse=handelse,
            kraver_status=("redo_att_testa",), rapportor_user_id=str(uuid.uuid4()),
        ) is None

        godkand = await lager.andra_plattformsarende(
            arende_id, status="kund_godkand", handelse=handelse,
            kraver_status=("redo_att_testa",), rapportor_user_id=rapportor,
        )
        assert godkand and godkand["status"] == "kund_godkand"
        # Ett andra klick går inte igenom.
        assert await lager.andra_plattformsarende(
            arende_id, status="kund_godkand", handelse=handelse,
            kraver_status=("redo_att_testa",), rapportor_user_id=rapportor,
        ) is None

        assert [h["typ"] for h in godkand["handelser"]] == ["skapad", "status", "utslag"]
        assert await agare.fetchval(
            "select count(*) from plattformsarende_handelser where arende_id = $1::uuid", arende_id
        ) == 3
        egna = await lager.list_plattformsarenden(rapportor_user_id=rapportor)
        assert [a["id"] for a in egna] == [arende_id]
        assert await lager.list_plattformsarenden(rapportor_user_id=str(uuid.uuid4())) == []
    finally:
        await pool.close()
        if arende_id:
            await agare.execute("delete from plattformsarenden where id = $1::uuid", arende_id)
        await agare.close()


@pytest.mark.anyio
async def test_bilden_lases_bara_per_arende_och_oskopat():
    from app.storage.postgres import PostgresStorage

    bild = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    agare = await _agare()
    tid = uuid.uuid4()
    await agare.execute(
        "insert into ss_tenants (id, slug, name) values ($1, $2, 'Bildtest')", tid, f"bt-{tid.hex[:12]}"
    )
    pool = await asyncpg.create_pool(APP_DSN, min_size=1, max_size=1)
    ider: list[str] = []
    try:
        lager = PostgresStorage(pool)
        rapportor = str(uuid.uuid4())
        med = await lager.skapa_plattformsarende({**_falt(rapportor), "bild": bild})
        utan = await lager.skapa_plattformsarende(_falt(rapportor))
        ider = [med["id"], utan["id"]]

        # Listor och uppslag bär aldrig bilden, bara att den finns.
        assert med["har_bild"] is True and "bild" not in med
        for arende in await lager.list_plattformsarenden(rapportor_user_id=rapportor):
            assert "bild" not in arende
        assert "bild" not in (await lager.hamta_plattformsarende(med["id"]))

        assert await lager.hamta_plattformsarende_bild(med["id"]) == bild
        assert await lager.hamta_plattformsarende_bild(utan["id"]) is None
        assert await lager.hamta_plattformsarende_bild(str(uuid.uuid4())) is None
        assert await lager.hamta_plattformsarende_bild("inte-ett-uuid") is None

        # En kundskopad anslutning ser inte ens raden (radskyddet i 156).
        async with lager._scoped(str(tid)) as conn:
            assert await conn.fetchval(
                "select bild from plattformsarenden where id = $1::uuid", med["id"]
            ) is None
    finally:
        await pool.close()
        for arende_id in ider:
            await agare.execute("delete from plattformsarenden where id = $1::uuid", arende_id)
        await agare.execute("delete from ss_tenants where id = $1", tid)
        await agare.close()


@pytest.mark.anyio
async def test_forslag_ur_chatten_far_sakna_skanning_men_inte_skanningens():
    from app.storage.postgres import PostgresStorage

    agare = await _agare()
    tid = uuid.uuid4()
    await agare.execute(
        "insert into ss_tenants (id, slug, name) values ($1, $2, 'KB-chatt')", tid, f"kc-{tid.hex[:12]}"
    )
    pool = await asyncpg.create_pool(APP_DSN, min_size=1, max_size=1)
    try:
        lager = PostgresStorage(pool)
        anvandare = str(uuid.uuid4())
        forslag = await lager.skapa_kb_forslag(
            str(tid), title="Leveranstid", content="Två till tre arbetsdagar.",
            category="ovrigt", kalla="chatt", skapad_av=anvandare,
        )
        assert forslag["kalla"] == "chatt" and forslag["status"] == "vantar"
        assert forslag["skanning_id"] is None and str(forslag["skapad_av"]) == anvandare
        assert str(forslag["tenant_id"]) == str(tid)

        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await lager.skapa_kb_forslag(
                str(tid), title="Retur", content="Trettio dagar.", category="ovrigt", kalla="skanning",
            )
        # Rader som fanns före 157 får källan skanning.
        assert await agare.fetchval(
            "select column_default from information_schema.columns "
            "where table_name = 'ss_kb_forslag' and column_name = 'kalla'"
        ) == "'skanning'::text"
    finally:
        await pool.close()
        await agare.execute("delete from ss_kb_forslag where tenant_id = $1", str(tid))
        await agare.execute("delete from ss_tenants where id = $1", tid)
        await agare.close()
