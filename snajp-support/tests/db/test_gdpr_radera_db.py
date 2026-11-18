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
