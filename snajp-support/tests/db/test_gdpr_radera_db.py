"""Provkörning av rättighetsskriptet mot en riktig databas (2026-11-18).

`scripts/gdpr_radera.py` (art. 15, 17 och 20) hade aldrig körts mot en
databas: `tests/test_gdpr_radera.py` läser bara migrationerna. Det här testet
kör SKRIPTET SOM DET ÄR, som en process, mot hela migrationskedjan i CI-jobbet
`databastester` (.github/workflows/verify.yml), med en syntetisk person:

1. Sökningen hittar varje tabell i skriptets karta i det riktiga schemat: ingen
   rad säger "FEL: kolumn" eller "okänd tabell".
2. `--export` lämnar ut personens rader som JSON (registerutdraget).
3. `--radera`, med adressen bekräftad på stdin, tar bort personens rader och
   deras kaskad, lämnar spärrlistans rad kvar utan koppling till kontakten,
   och rör inte en annan persons rader i samma kund.

Bara mot en lokal databas utan spegelmarkör, samma vakt som gallringstestet.
Allt testet skapar ligger under en egen kund med unika adresser.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import asyncpg
import pytest

DSN = os.environ.get("GALLRING_TEST_DSN", "")
ROT = Path(__file__).resolve().parents[3]
SKRIPT = ROT / "scripts" / "gdpr_radera.py"

pytestmark = pytest.mark.skipif(not DSN, reason="Kräver GALLRING_TEST_DSN mot en tom testdatabas.")

_LOKALA = {"localhost", "127.0.0.1", "::1"}


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _anslut() -> asyncpg.Connection:
    assert urlsplit(DSN).hostname in _LOKALA, "Provkörningen görs bara mot en lokal databas."
    conn = await asyncpg.connect(DSN)
    spegel = await conn.fetchval("select to_regclass('public.mirror_meta') is not null")
    assert not spegel, "Databasen bär en spegelmarkör — det här är inte en testdatabas."
    return conn


async def _seeda_person(conn, tid, ws, epost: str) -> dict:
    """En person i varje del av kartan som går att seeda utan externa beroenden."""
    ids: dict = {}

    async def val(sql: str, *args):
        return await conn.fetchval(sql, *args)

    ids["mejl"] = await val(
        """insert into ss_emails (tenant_id, provider_message_id, from_email, from_name, body_text)
           values ($1, $2, $3, 'Test Person', 'Hej') returning id""",
        tid, f"gdpr-{uuid.uuid4().hex}", epost,
    )
    await conn.execute(
        "insert into ss_drafts (tenant_id, email_id, content) values ($1, $2, 'Hej Test')",
        tid, ids["mejl"],
    )
    ids["kund"] = await val(
        "insert into ss_customers (tenant_id, name) values ($1, 'Chattkund') returning id", tid
    )
    await conn.execute(
        """insert into ss_customer_identifiers (tenant_id, customer_id, type, value)
           values ($1, $2, 'email', $3)""",
        tid, ids["kund"], epost,
    )
    ids["arende"] = await val(
        "insert into ss_tickets (tenant_id, customer_id, subject) values ($1, $2, 'Fråga') returning id",
        tid, ids["kund"],
    )
    ids["prospekt"] = await val(
        """insert into prospects (tenant_id, company_name, contact_name, contact_email)
           values ($1, 'Påhittat AB', 'Test Testsson', $2) returning id""",
        tid, epost,
    )
    await conn.execute(
        "insert into outreach_threads (tenant_id, prospect_id) values ($1, $2)", tid, ids["prospekt"]
    )
    bolag = await val(
        "insert into companies (workspace_id, name, industry, location) values ($1, 'Bolag AB', 'test', 'Testby') returning id",
        ws,
    )
    ids["kontakt"] = await val(
        """insert into contacts (workspace_id, company_id, full_name, role, email)
           values ($1, $2, 'Kontakt Testsson', 'VD', $3) returning id""",
        ws, bolag, epost,
    )
    ids["sparr"] = await val(
        """insert into suppressions (workspace_id, tenant_id, contact_id, email, reason)
           values ($1, $2, $3, $4, 'avregistrerad') returning id""",
        ws, tid, ids["kontakt"], epost,
    )
    ids["demo"] = await val(
        "insert into demo_requests (namn, epost) values ('Test Person', $1) returning id", epost
    )
    return ids


def _kor(epost: str, *flaggor: str, stdin: str = "") -> subprocess.CompletedProcess:
    miljo = {**os.environ, "DATABASE_URL": DSN, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [sys.executable, str(SKRIPT), "--env", "production", "--epost", epost, *flaggor],
        input=stdin, capture_output=True, text=True, encoding="utf-8", env=miljo, cwd=ROT, timeout=120,
    )


@pytest.mark.anyio
async def test_skriptet_soker_lamnar_ut_och_raderar_mot_hela_schemat():
    conn = await _anslut()
    tid = uuid.uuid4()
    person = f"gdpr.{tid.hex[:8]}@example.com"
    granne = f"granne.{tid.hex[:8]}@example.com"
    try:
        await conn.execute(
            "insert into ss_tenants (id, slug, name) values ($1, $2, 'Rättighetstest')",
            tid, f"gdpr-{tid.hex[:12]}",
        )
        ws = await conn.fetchval(
            "insert into workspaces (name, ss_tenant_id) values ('Rättighetsyta', $1) returning id", tid
        )
        egna = await _seeda_person(conn, tid, ws, person)
        andra = await _seeda_person(conn, tid, ws, granne)

        # 1 och 2: sökning och registerutdrag.
        utdrag = _kor(person, "--export")
        assert utdrag.returncode == 0, utdrag.stderr
        assert "FEL: kolumn" not in utdrag.stdout, utdrag.stdout
        assert "okänd tabell" not in utdrag.stdout, utdrag.stdout
        json_del = utdrag.stdout.split("--- REGISTERUTDRAG (JSON) ---", 1)[1]
        data = json.loads(json_del[: json_del.rindex("}") + 1])
        for tabell in ("ss_emails", "ss_customers", "prospects", "contacts", "suppressions", "demo_requests"):
            assert len(data[tabell]) == 1, (tabell, data.get(tabell))
        assert granne not in json_del

        # 3: radering med fel bekräftelse avbryter utan att radera.
        fel = _kor(person, "--radera", stdin="nagon.annan@example.com\n")
        assert fel.returncode != 0
        assert await conn.fetchval("select count(*) from contacts where id = $1", egna["kontakt"]) == 1

        radering = _kor(person, "--radera", stdin=f"{person}\n")
        assert radering.returncode == 0, radering.stderr + radering.stdout
        assert "Klart." in radering.stdout

        borta = {
            "ss_emails": egna["mejl"],
            "ss_customers": egna["kund"],
            "ss_tickets": egna["arende"],
            "prospects": egna["prospekt"],
            "contacts": egna["kontakt"],
            "demo_requests": egna["demo"],
        }
        for tabell, rad in borta.items():
            assert await conn.fetchval(f"select count(*) from {tabell} where id = $1", rad) == 0, tabell
        assert await conn.fetchval("select count(*) from ss_drafts where email_id = $1", egna["mejl"]) == 0
        assert await conn.fetchval(
            "select count(*) from outreach_threads where prospect_id = $1", egna["prospekt"]
        ) == 0

        # Spärren överlever, utan koppling till den raderade kontakten.
        sparr = await conn.fetchrow("select email, contact_id from suppressions where id = $1", egna["sparr"])
        assert sparr is not None and sparr["email"] == person and sparr["contact_id"] is None

        # Grannen i samma kund är orörd.
        for tabell, nyckel in (("ss_emails", "mejl"), ("ss_customers", "kund"), ("prospects", "prospekt"),
                               ("contacts", "kontakt"), ("suppressions", "sparr"), ("demo_requests", "demo")):
            assert await conn.fetchval(f"select count(*) from {tabell} where id = $1", andra[nyckel]) == 1, tabell
    finally:
        # Raderna står kvar under testets egen kund: databasen är syntetisk
        # och dör med CI-jobbet, och tenant-nycklarna saknar kaskad.
        await conn.close()


APP_DSN = os.environ.get("GALLRING_TEST_APP_DSN", "")


async def _aktiva(conn, epost: str) -> list:
    return await conn.fetch(
        "select id, skal, havd_at, havd_skal from behandlingsbegransningar where lower(email) = lower($1)",
        epost,
    )


@pytest.mark.anyio
@pytest.mark.skipif(not APP_DSN, reason="Kräver GALLRING_TEST_APP_DSN (approllen snajp_app).")
async def test_begransning_av_behandling_mot_hela_schemat():
    """PR-4 (art. 18, migration 124): skriptet sätter och häver markeringen,
    approllen kan läsa den men inte ändra den, och appens egen läsväg
    (PostgresStorage.list_begransade) ser bara aktiva rader."""
    from app.storage.postgres import PostgresStorage

    conn = await _anslut()
    tid = uuid.uuid4()
    person = f"begr.{tid.hex[:8]}@example.com"
    try:
        await conn.execute(
            "insert into ss_tenants (id, slug, name) values ($1, $2, 'Begränsningstest')",
            tid, f"begr-{tid.hex[:12]}",
        )
        utan_skal = _kor(person, "--begransa", "  ")
        assert utan_skal.returncode != 0
        assert await _aktiva(conn, person) == []

        satt = _kor(person.upper(), "--begransa", "Riktigheten prövas")
        assert satt.returncode == 0, satt.stderr + satt.stdout
        assert "Begränsning satt" in satt.stdout
        [rad] = await _aktiva(conn, person)
        assert rad["havd_at"] is None and rad["skal"] == "Riktigheten prövas"

        # En andra begäran är ingen ny rad, och sökningen visar markeringen.
        igen = _kor(person, "--begransa", "Igen")
        assert igen.returncode == 0 and "redan aktiv" in igen.stdout
        assert len(await _aktiva(conn, person)) == 1
        assert "AKTIV sedan" in _kor(person).stdout

        # Approllen läser men skriver inte.
        pool = await asyncpg.create_pool(APP_DSN, min_size=1, max_size=1)
        try:
            assert person in await PostgresStorage(pool).list_begransade(str(tid))
            async with pool.acquire() as app:
                with pytest.raises(asyncpg.InsufficientPrivilegeError):
                    await app.execute(
                        "insert into behandlingsbegransningar (email, skal) values ('x@example.com', 'x')"
                    )
                with pytest.raises(asyncpg.InsufficientPrivilegeError):
                    await app.execute("update behandlingsbegransningar set havd_at = now()")
        finally:
            await pool.close()
        # api:t läser listan (sändningsspärren). Webben läser den inte, och har
        # sedan migration 126 ingen rättighet alls på tabellen (minsta rättighet).
        assert await conn.fetchval(
            "select has_table_privilege('snajp_app', 'public.behandlingsbegransningar', 'select')"
        )
        assert not await conn.fetchval(
            "select has_table_privilege('snajp_web', 'public.behandlingsbegransningar', 'select')"
        )
        for roll in ("snajp_app", "snajp_web"):
            for ratt in ("insert", "update", "delete"):
                assert not await conn.fetchval(
                    "select has_table_privilege($1, 'public.behandlingsbegransningar', $2)", roll, ratt
                ), (roll, ratt)

        # Hävningen kräver bekräftelse; raden står kvar som belägg.
        fel = _kor(person, "--hav-begransning", "Klar", stdin="nagon.annan@example.com\n")
        assert fel.returncode != 0
        assert (await _aktiva(conn, person))[0]["havd_at"] is None

        hav = _kor(person, "--hav-begransning", "Prövningen klar", stdin=f"{person}\n")
        assert hav.returncode == 0, hav.stderr + hav.stdout
        [rad] = await _aktiva(conn, person)
        assert rad["havd_at"] is not None and rad["havd_skal"] == "Prövningen klar"

        pool = await asyncpg.create_pool(APP_DSN, min_size=1, max_size=1)
        try:
            assert person not in await PostgresStorage(pool).list_begransade(str(tid))
        finally:
            await pool.close()

        # En ny begränsning efter en hävd går att sätta, och --radera behåller båda raderna.
        assert _kor(person, "--begransa", "Ny begäran").returncode == 0
        radering = _kor(person, "--radera", stdin=f"{person}\n")
        assert radering.returncode == 0, radering.stderr + radering.stdout
        assert len(await _aktiva(conn, person)) == 2
    finally:
        await conn.close()


def test_begransningen_speglas_till_development_och_synken_stamplar(capsys):
    """Migration 147 (Codex runda 15, 2026-11-20): mot main skriver skriptet
    samma rad i development-spegeln, idempotent; en annan aktiv rad för
    adressen i spegeln står kvar; en hävning häver spegelns aktiva rader; ett
    fel mot spegeln ger kod 3. Synken läser main:s rader och stämplar spegeln.
    Här är "spegeln" samma testdatabas, och allt rullas tillbaka eller städas."""
    import importlib.util
    from datetime import datetime, timezone

    import psycopg2

    assert urlsplit(DSN).hostname in _LOKALA
    sys.path.insert(0, str(ROT / "scripts"))
    spec = importlib.util.spec_from_file_location("gdpr_radera_spegel", SKRIPT)
    gdpr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gdpr)
    import railway_synk  # noqa: E402

    gdpr.begransning_dsn = lambda env: DSN if env == "railway-development" else "fel"
    person = f"spegel.{uuid.uuid4().hex[:8]}@example.com"
    nu = datetime.now(timezone.utc).isoformat()
    rad = {"id": str(uuid.uuid4()), "email": person, "skal": "Riktigheten prövas", "begard_at": nu,
           "havd_at": None, "havd_skal": None, "created_at": nu}

    def rader():
        with psycopg2.connect(DSN) as c, c.cursor() as cur:
            cur.execute("select id::text, havd_at, havd_skal from behandlingsbegransningar "
                        "where lower(email) = lower(%s) order by begard_at", (person,))
            return cur.fetchall()

    try:
        assert gdpr._spegla_till_development(rad, person) == 0
        assert rader() == [(rad["id"], None, None)]
        assert gdpr._spegla_till_development(rad, person) == 0  # idempotent
        assert len(rader()) == 1

        # En annan aktiv rad för adressen (satt direkt i spegeln) står kvar.
        annan = {**rad, "id": str(uuid.uuid4())}
        assert gdpr._spegla_till_development(annan, person) == 0
        assert "egen aktiv begränsning" in capsys.readouterr().out
        assert [r[0] for r in rader()] == [rad["id"]]

        # Main:s hävning häver spegelns aktiva rad, med main:s tid och skäl.
        havd = {**annan, "havd_at": nu, "havd_skal": "Prövningen klar"}
        assert gdpr._spegla_till_development(havd, person) == 0
        tillstand = rader()
        assert all(r[1] is not None and r[2] == "Prövningen klar" for r in tillstand), tillstand
        assert {r[0] for r in tillstand} == {rad["id"], annan["id"]}

        # Ett fel mot spegeln: kod 3 och besked om synken.
        def faller(env):
            raise SystemExit("AVBRYTER: ingen anslutning")
        gdpr.begransning_dsn = faller
        assert gdpr._spegla_till_development(rad, person) == 3
        assert "Synken för över den" in capsys.readouterr().out

        # Synken: läser main:s rader och stämplar spegeln i samma transaktion.
        with psycopg2.connect(DSN) as c:
            cur = c.cursor()
            lasta = railway_synk.las_begransningar(cur)
            assert lasta is not None and any(r["id"] == rad["id"] for r in lasta)
            cur.execute("create table public.mirror_meta (environment text)")
            cur.execute("insert into public.mirror_meta values ('development')")
            assert railway_synk.skriv_begransningar(cur, lasta) == []
            cur.execute("select begransningar_synkade_at is not null from public.mirror_meta")
            assert cur.fetchone()[0]
            # Utan läsbara rader ingen ny stämpel.
            cur.execute("update public.mirror_meta set begransningar_synkade_at = null")
            assert railway_synk.skriv_begransningar(cur, None) == []
            cur.execute("select begransningar_synkade_at from public.mirror_meta")
            assert cur.fetchone()[0] is None
            c.rollback()
    finally:
        with psycopg2.connect(DSN) as c, c.cursor() as cur:
            cur.execute("delete from behandlingsbegransningar where lower(email) = lower(%s)", (person,))
