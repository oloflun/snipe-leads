"""Webbpoolen (plan 2026-10-08): in, bedöm, fördela efter län, bara bolagsnivå."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.leads import korning, webbpool
from app.storage.memory import MemoryStorage

MIGRATION = Path(__file__).resolve().parents[3] / "supabase/migrations/20261008150000_108_webbpool.sql"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def pool_pa(monkeypatch):
    monkeypatch.setenv("WEBBPOOL", "1")
    monkeypatch.setenv("WEBBPOOL_FORDELNING", "1")
    monkeypatch.setenv("WEBBPOOL_MOTTAGARE", json.dumps({
        "alunix": ["vastra-gotalands-lan", "hallands-lan"],
        "umea-webbdesign": ["vasterbottens-lan", "norrbottens-lan"],
    }))
    monkeypatch.setenv("WEBBPOOL_INSPIRATION", "alunix")


def test_lanet_ur_merinfo_orten_och_postnumret():
    assert webbpool.lan_for({"lan": "Västra Götalands län"}) == "vastra-gotalands-lan"
    assert webbpool.lan_for({"ort": "Umeå"}) == "vasterbottens-lan"
    assert webbpool.lan_for({"postnr": "434 91"}) == "hallands-lan"
    assert webbpool.lan_for({"postnr": "111 22"}) is None


def test_inv_sec_008_inga_personuppgifter_i_poolen():
    """Kandidatens kontaktfält når aldrig poolraden, och tabellen har inga
    kolumner för dem eller för vilken kund som hittade bolaget."""
    kandidat = {"company_name": "X AB", "website": "https://x.se", "contact_name": "Anna", "contact_email": "a@x.se",
                "contact_phone": "070", "vd_namn": "Anna", "tenant_id": "t1"}
    rad = webbpool.bolagsrad(kandidat, "korning")
    assert set(rad) <= {"doman", *webbpool.POOLFALT}
    sql = MIGRATION.read_text(encoding="utf-8")
    tabell = re.search(r"create table if not exists public\.webbpool \((.*?)\n\);", sql, re.S).group(1)
    kolumner = {rad.split()[0] for rad in tabell.strip().splitlines()}
    assert kolumner == {"doman", "created_at", "sedd_at", *webbpool.POOLFALT}
    assert not kolumner & {*webbpool.PERSONFALT, "tenant_id"}


def test_webbyraer_och_mottagare_ar_aldrig_kalla(pool_pa):
    assert webbpool.utesluten_kalla({"id": "1", "slug": "alunix"})
    assert webbpool.utesluten_kalla({"id": "2", "slug": "annan", "segment": "webbyra"})
    assert not webbpool.utesluten_kalla({"id": "3", "slug": "redovisning"})


@pytest.mark.anyio
async def test_hela_kedjan_fordelar_efter_lan_en_gang(pool_pa, monkeypatch):
    storage = MemoryStorage()
    kalla = await storage.create_tenant(slug="redovisning", name="Källa")
    alunix = await storage.create_tenant(slug="alunix", name="Alunix")
    umea = await storage.create_tenant(slug="umea-webbdesign", name="Umeå Webbdesign")

    k: dict = {}
    for kand in (
        {"company_name": "Gbg Bygg AB", "website": "https://www.gbgbygg.se/om", "ort": "Göteborg", "contact_email": "vd@gbgbygg.se"},
        {"company_name": "Umeå Golv AB", "website": "https://umeagolv.se", "postnr": "903 25"},
        {"company_name": "Snygg AB", "website": "https://snygg.se", "ort": "Göteborg"},
        {"company_name": "Proffs AB", "website": "https://proffs.se", "ort": "Mölndal"},
        {"company_name": "Malmö AB", "website": "https://malmo.se", "postnr": "211 20"},
    ):
        korning.pool_in(k, kand)

    nivaer = {"gbgbygg.se": "akut", "umeagolv.se": "dalig", "snygg.se": "mycket_bra", "proffs.se": "bra",
              "malmo.se": "dalig"}

    async def bedom_en(rad, befintlig=None):
        return {"webbniva": nivaer[rad["doman"]], "modernitet": 3, "brister": ["Liten text"]}

    monkeypatch.setattr(webbpool, "bedom_en", bedom_en)
    await webbpool.efter_korning(storage, k, kalla["id"])

    def rader(tenant):
        return [i for i in storage.lead_list_items if i["tenant_id"] == tenant["id"]]

    assert {r["company_name"] for r in rader(alunix)} == {"Gbg Bygg AB", "Snygg AB"}
    assert {r["company_name"] for r in rader(umea)} == {"Umeå Golv AB"}
    assert all(not r.get("contact_email") and r["source_name"] == "webbpool" for r in rader(alunix))
    gbg = next(r for r in rader(alunix) if r["company_name"] == "Gbg Bygg AB")
    assert gbg["webbniva"] == "akut" and gbg["lan"] == "vastra-gotalands-lan" and gbg["website"] == "https://www.gbgbygg.se/"
    titlar = {lista["titel"] for lista in await storage.list_lead_lists(alunix["id"])}
    assert any(t.startswith("Webbleads vecka") for t in titlar) and any(t.startswith("Inspiration") for t in titlar)

    # En andra körning med samma bolag fördelar ingenting nytt.
    await webbpool.efter_korning(storage, k, kalla["id"])
    assert len(rader(alunix)) == 2 and len(rader(umea)) == 1


@pytest.mark.anyio
async def test_mottagarens_egen_korning_matas_inte_in(pool_pa):
    storage = MemoryStorage()
    alunix = await storage.create_tenant(slug="alunix", name="Alunix")
    k: dict = {}
    korning.pool_in(k, {"company_name": "Gbg Bygg AB", "website": "https://gbgbygg.se", "ort": "Göteborg"})
    assert await webbpool.mata_in(storage, k, alunix["id"]) == []
    assert storage.webbpool == {}


@pytest.mark.anyio
async def test_fordelningen_ar_av_utan_flaggan(pool_pa, monkeypatch):
    monkeypatch.setenv("WEBBPOOL_FORDELNING", "")
    assert await webbpool.fordela(MemoryStorage()) == {}


@pytest.mark.anyio
async def test_farsk_bedomning_ateranvands_gammal_gors_om():
    """Processa om på en webbpoollista: listans sidkritik blir researchens
    underlag i stället för en ny, betald bedömning (plan 2026-10-08)."""
    from datetime import UTC, datetime, timedelta

    storage = MemoryStorage()
    farsk = {"webbniva": "akut", "platshallare": "parkerad domän", "bedomd": datetime.now(UTC).isoformat()}
    assert await webbpool.farsk_revision(storage, {"website": None, "webbrevision": farsk}) == farsk
    gammal = {**farsk, "bedomd": (datetime.now(UTC) - timedelta(days=40)).isoformat()}
    assert await webbpool.farsk_revision(storage, {"website": None, "webbrevision": gammal}) is None
    await storage.webbpool_spara({"doman": "x.se", "website": "https://x.se/", "webbniva": "dalig",
                                  "webbrevision": {"modernitet": 4}, "bedomd_at": datetime.now(UTC)})
    rev = await webbpool.farsk_revision(storage, {"website": "https://www.x.se/kontakt"})
    assert rev == {"modernitet": 4, "webbniva": "dalig"}


@pytest.mark.anyio
async def test_bedomningen_ar_hemlig_utom_for_webbyraerna(monkeypatch):
    """Antons regel 2026-10-08: bara Admin, Alunix och Umeå Webbdesign ser
    webbplatsbedömningen."""
    monkeypatch.delenv("WEBBBEDOMNING_SYNLIG", raising=False)
    monkeypatch.delenv("WEBBPOOL_MOTTAGARE", raising=False)
    monkeypatch.delenv("WEBBPOOL_INSPIRATION", raising=False)
    storage = MemoryStorage()
    alunix = await storage.create_tenant(slug="kund-ea08b974", name="Alunix workspace")
    annan = await storage.create_tenant(slug="redovisning", name="Annan")
    assert await webbpool.far_se(storage, alunix["id"])
    assert not await webbpool.far_se(storage, annan["id"])
    assert not await webbpool.far_se(storage, None)
    rad = {"company_name": "X", "webbrevision": {"modernitet": 3}, "webbniva": "dalig"}
    assert webbpool.dolj(rad) == {"company_name": "X"}


@pytest.mark.anyio
async def test_postgres_sparar_bedomningen_med_update_inte_upsert():
    """Livetestet 2026-10-08: en upsert utan website föll på NOT NULL innan
    konflikten avgjordes. En bedömning på en befintlig rad är en UPDATE."""
    from app.storage.postgres import PostgresStorage

    sql: list[str] = []

    class Conn:
        async def execute(self, q, *args):
            sql.append(q)

    class Acquire:
        async def __aenter__(self):
            return Conn()

        async def __aexit__(self, *a):
            return False

    class Pool:
        def acquire(self):
            return Acquire()

    storage = PostgresStorage.__new__(PostgresStorage)
    storage.pool = Pool()
    await storage.webbpool_spara({"doman": "x.se", "webbniva": "dalig", "webbrevision": {"modernitet": 4}})
    await storage.webbpool_spara({"doman": "x.se", "website": "https://x.se/"})
    assert sql[0].startswith("update webbpool") and "insert" in sql[1]
