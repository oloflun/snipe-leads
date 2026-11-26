"""Mot en riktig Postgres, som approllen snajp_app: lagringsmetoderna som
kunddemons rättningar (2026-11-24/25) ändrade eller lade till i postgres.py,
var och en körd mot databasen OCH mot minneslagret med samma utfall.

* Kunskapsbasen (153, 159): kategorin 'salj', `is_placeholder` i list_kb och
  add_kb_article, och exempelrensningen när eget innehåll kommer in
  (add_kb_article, lagg_till_kb_forslag): atomisk, bara den egna kundens
  exempel, aldrig en annan kunds, och ett fel mitt i lämnar exemplen kvar.
* Förslagen (157): kalla 'agent' och 'chatt' utan skanning, villkoren
  ss_kb_forslag_kalla_check och ss_kb_forslag_skanning_kalla_check, och att
  `skapad_av` kommer ut som text, som i minneslagret.
* Påfyllnaden (158): spara_bedomning skriver pafylld/pafylld_skal och nollar
  dem, och listvyns projektioner (LISTKOLUMNER, FORDELNINGSKOLUMNER) går att
  läsa och ger samma synliga leads som minnet.
* Städaren (stada_hangande_leadsjobb): väckbara och vilande körningar står
  kvar, listjobb, klara, pågående och för gamla fälls med HANGFEL_JOBB, en
  annan kunds jobb rörs inte, och väckarens läsning ser den vilande körningen.
* Veckoanalysen: ringlistans bolag (origin 'ring') är inga nya leads.

Plattformsärendena (156) prövas i test_plattformsarenden_db.py, inte här.

Körs i CI-jobbet `databas` (.github/workflows/verify.yml), samma form som
test_kb_forslag_atomisk.py. Vägrar allt annat än en lokal databas utan
spegelmarkör. Allt är syntetiskt och raderas efteråt av ägarrollen.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
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


async def _approll() -> asyncpg.Pool:
    assert urlsplit(APP_DSN).hostname in _LOKALA, "Testet körs bara mot en lokal databas."
    pool = await asyncpg.create_pool(APP_DSN, min_size=1, max_size=2)
    async with pool.acquire() as conn:
        # Radskyddet ska prövas: approllen får inte vara ägare eller kringgå RLS.
        assert await conn.fetchval("select current_user") == "snajp_app"
        assert not await conn.fetchval("select rolbypassrls or rolsuper from pg_roles where rolname = current_user")
    return pool


async def _ny_kund(agare: asyncpg.Connection, prefix: str) -> str:
    tid = uuid.uuid4()
    await agare.execute(
        "insert into ss_tenants (id, slug, name) values ($1, $2, 'Demorättningar')", tid, f"{prefix}-{tid.hex[:12]}"
    )
    return str(tid)


async def _stada(agare: asyncpg.Connection, kunder: list[str]) -> None:
    """Allt kunderna fick, även om testet föll mitt i."""
    if not kunder:
        return
    prospekt = [str(r["id"]) for r in await agare.fetch(
        "select id from prospects where tenant_id = any($1::uuid[])", kunder)]
    jobb = [r["job_id"] for r in await agare.fetch(
        "select job_id from leads_job_ledger where tenant_id = any($1::uuid[])", kunder)]
    await agare.execute("delete from leads_job_ledger where tenant_id = any($1::uuid[])", kunder)
    await agare.execute("delete from prospects where tenant_id = any($1::uuid[])", kunder)
    await agare.execute("delete from ss_kb_forslag where tenant_id = any($1::uuid[])", kunder)
    await agare.execute("delete from ss_kb_skanningar where tenant_id = any($1::uuid[])", kunder)
    await agare.execute("delete from ss_knowledge_base where tenant_id = any($1::uuid[])", kunder)
    await agare.execute(
        """delete from synk_raderingar
            where (tabell = 'prospects' and nyckel = any($1::text[]))
               or (tabell = 'leads_job_ledger' and nyckel = any($2::text[]))""",
        prospekt, jobb,
    )
    await agare.execute("delete from ss_tenants where id = any($1::uuid[])", kunder)


def _minne():
    from app.storage.memory import MemoryStorage

    return MemoryStorage()


def _kb_bild(artiklar: list[dict]) -> list[tuple]:
    return [(a["title"], a["category"], a["is_placeholder"]) for a in artiklar]


# -- Kunskapsbasen: kategorin 'salj' och exempelrensningen (153, 159) ---------


@pytest.mark.anyio
async def test_eget_innehall_rensar_bara_den_egna_kundens_exempel():
    from app.storage.postgres import PostgresStorage

    agare = await _agare()
    kunder: list[str] = []
    pool = None
    try:
        a = await _ny_kund(agare, "dr-a")
        kunder.append(a)
        b = await _ny_kund(agare, "dr-b")
        kunder.append(b)
        pool = await _approll()
        pg = PostgresStorage(pool)
        minne = _minne()

        for lager in (pg, minne):
            for kund in (a, b):
                for titel in ("Så gör du en retur", "Leveranstider och fraktalternativ"):
                    rad = await lager.add_kb_article(
                        kund, title=titel, content="Exempel.", category="ovrigt", is_placeholder=True
                    )
                    assert rad["is_placeholder"] is True
            # En exempelrad rensar inga andra exempel.
            assert len(await lager.list_kb(a)) == 2

        # En kategori databasen avvisar: inget skrivs, och exemplen står kvar
        # (raderingen och insättningen är EN transaktion).
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await pg.add_kb_article(a, title="Fel", content="x", category="okand")
        with pytest.raises(ValueError):
            await minne.add_kb_article(a, title="Fel", content="x", category="okand")
        for lager in (pg, minne):
            assert [p for _, _, p in _kb_bild(await lager.list_kb(a))] == [True, True]

        # Kundens eget innehåll, i kategorin 'salj' (153): exemplen går.
        utfall = {}
        for namn, lager in (("pg", pg), ("minne", minne)):
            rad = await lager.add_kb_article(
                a, title="Vårt erbjudande", content="Fast pris per månad.", category="salj"
            )
            assert rad["is_placeholder"] is False and rad["category"] == "salj"
            utfall[namn] = (_kb_bild(await lager.list_kb(a)), _kb_bild(await lager.list_kb(b)))
        assert utfall["pg"] == utfall["minne"]
        egen, annan = utfall["pg"]
        assert egen == [("Vårt erbjudande", "salj", False)]
        assert [p for _, _, p in annan] == [True, True], "en annan kunds exempel raderades"

        # Ett nytt exempel efter eget innehåll rör inte det egna.
        await pg.add_kb_article(a, title="Om oss", content="Exempel.", category="ovrigt", is_placeholder=True)
        assert [p for _, _, p in _kb_bild(await pg.list_kb(a))] == [False, True]
        assert await agare.fetchval(
            "select count(*) from ss_knowledge_base where tenant_id = $1::uuid and is_placeholder", b
        ) == 2
    finally:
        if pool:
            await pool.close()
        await _stada(agare, kunder)
        await agare.close()


@pytest.mark.anyio
async def test_ett_godkant_forslag_rensar_exemplen_i_samma_transaktion():
    from app.storage.postgres import PostgresStorage

    agare = await _agare()
    kunder: list[str] = []
    pool = None
    try:
        a = await _ny_kund(agare, "dr-fa")
        kunder.append(a)
        b = await _ny_kund(agare, "dr-fb")
        kunder.append(b)
        pool = await _approll()
        pg = PostgresStorage(pool)
        minne = _minne()

        forslag = {}
        felkategori = {}
        for namn, lager in (("pg", pg), ("minne", minne)):
            for kund in (a, b):
                await lager.add_kb_article(
                    kund, title="Så gör du en retur", content="Exempel.", category="ovrigt", is_placeholder=True
                )
            forslag[namn] = await lager.skapa_kb_forslag(
                a, title="Öppettider", content="Vardagar 8–17.", category="ovrigt", kalla="agent",
                kalla_ref="samtal-1",
            )
            # ss_kb_forslag.category saknar villkor, artikeln har det.
            felkategori[namn] = await lager.skapa_kb_forslag(
                a, title="Konstig", content="x", category="okand", kalla="chatt",
            )

        # Ett väntande förslag rör inte exemplen.
        for lager in (pg, minne):
            assert [p for _, _, p in _kb_bild(await lager.list_kb(a))] == [True]

        # Ett fel mitt i transaktionen (inbäddningen kan inte skickas utan
        # vektorkodek): förslaget väntar, ingen artikel, exemplen kvar.
        with pytest.raises(Exception):
            await pg.lagg_till_kb_forslag(a, forslag["pg"]["id"], embedding=[0.1, 0.2])
        assert _kb_bild(await pg.list_kb(a)) == [("Så gör du en retur", "ovrigt", True)]
        assert (await pg.hamta_vantande_kb_forslag(a, forslag["pg"]["id"])) is not None

        # Kategorin databasen avvisar: samma utfall i båda, exemplen kvar.
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await pg.lagg_till_kb_forslag(a, felkategori["pg"]["id"], embedding=None)
        with pytest.raises(ValueError):
            await minne.lagg_till_kb_forslag(a, felkategori["minne"]["id"], embedding=None)
        for namn, lager in (("pg", pg), ("minne", minne)):
            assert [p for _, _, p in _kb_bild(await lager.list_kb(a))] == [True]
            assert await lager.hamta_vantande_kb_forslag(a, felkategori[namn]["id"]) is not None

        utfall = {}
        for namn, lager in (("pg", pg), ("minne", minne)):
            artikel = await lager.lagg_till_kb_forslag(a, forslag[namn]["id"], embedding=None)
            assert artikel is not None
            utfall[namn] = (
                {k: artikel[k] for k in ("title", "category", "source_url", "giltig_till", "is_placeholder")},
                _kb_bild(await lager.list_kb(a)),
                _kb_bild(await lager.list_kb(b)),
                sorted((f["title"], f["status"], f["kalla"]) for f in await lager.list_kb_forslag(a)),
            )
            # Ett andra klick blir ingen andra artikel.
            assert await lager.lagg_till_kb_forslag(a, forslag[namn]["id"], embedding=None) is None
        assert utfall["pg"] == utfall["minne"]
        assert utfall["pg"][1] == [("Öppettider", "ovrigt", False)]
        assert utfall["pg"][2] == [("Så gör du en retur", "ovrigt", True)], "en annan kunds exempel raderades"
    finally:
        if pool:
            await pool.close()
        await _stada(agare, kunder)
        await agare.close()


# -- Förslagens källa (157) ----------------------------------------------------


@pytest.mark.anyio
async def test_forslagens_kalla_och_villkoren_i_157():
    from app.storage.postgres import PostgresStorage

    agare = await _agare()
    kunder: list[str] = []
    pool = None
    try:
        a = await _ny_kund(agare, "dr-ka")
        kunder.append(a)
        b = await _ny_kund(agare, "dr-kb")
        kunder.append(b)
        pool = await _approll()
        pg = PostgresStorage(pool)
        minne = _minne()
        anvandare = str(uuid.uuid4())

        utfall = {}
        for namn, lager in (("pg", pg), ("minne", minne)):
            rader = []
            for kalla, ref in (("agent", "korning-7"), ("chatt", None)):
                f = await lager.skapa_kb_forslag(
                    a, title=f"Från {kalla}", content="Text.", category="salj", kalla=kalla,
                    kalla_ref=ref, skapad_av=anvandare,
                )
                rader.append(f)
            with pytest.raises(ValueError):
                await lager.skapa_kb_forslag(a, title="x", content="x", category="ovrigt", kalla="mejl")
            listan = await lager.list_kb_forslag(a, status="vantar")
            utfall[namn] = sorted(
                (f["title"], f["kalla"], f["kalla_ref"], f["skapad_av"], f["skanning_id"], f["status"],
                 f["varningar"], f["artikel_id"], f["tenant_id"])
                for f in listan
            )
            for f in rader:
                # Samma typ som minnet: text, inte uuid.UUID.
                assert f["skapad_av"] == anvandare, (namn, type(f["skapad_av"]))
                json.dumps(f)
            assert await lager.list_kb_forslag(b) == []
        assert utfall["pg"] == utfall["minne"]

        # Villkoren i databasen, som approllen och i kundens kontext.
        async with pg._scoped(a) as conn:
            with pytest.raises(asyncpg.exceptions.CheckViolationError) as fel:
                await conn.execute(
                    "insert into ss_kb_forslag (tenant_id, title, content, category, kalla) "
                    "values ($1, 'x', 'x', 'ovrigt', 'mejl')", a,
                )
            assert fel.value.constraint_name == "ss_kb_forslag_kalla_check"
        async with pg._scoped(a) as conn:
            with pytest.raises(asyncpg.exceptions.CheckViolationError) as fel:
                await conn.execute(
                    "insert into ss_kb_forslag (tenant_id, title, content, category) "
                    "values ($1, 'x', 'x', 'ovrigt')", a,
                )
            assert fel.value.constraint_name == "ss_kb_forslag_skanning_kalla_check"
        # Radskyddet: ett förslag i en annan kunds namn går inte att lägga.
        async with pg._scoped(a) as conn:
            with pytest.raises(asyncpg.exceptions.InsufficientPrivilegeError):
                await conn.execute(
                    "insert into ss_kb_forslag (tenant_id, title, content, category, kalla) "
                    "values ($1, 'x', 'x', 'ovrigt', 'chatt')", b,
                )
        assert await agare.fetchval("select count(*) from ss_kb_forslag where tenant_id = $1::uuid", b) == 0
    finally:
        if pool:
            await pool.close()
        await _stada(agare, kunder)
        await agare.close()


# -- Påfyllnaden (158), listvyn och veckoanalysen ------------------------------


@pytest.mark.anyio
async def test_pafyllt_lead_listvyn_och_veckoanalysen():
    from app.leads.listvy import FORDELNINGSKOLUMNER, LISTKOLUMNER, synliga
    from app.storage.postgres import PostgresStorage

    agare = await _agare()
    kunder: list[str] = []
    pool = None
    try:
        a = await _ny_kund(agare, "dr-pa")
        kunder.append(a)
        pool = await _approll()
        pg = PostgresStorage(pool)
        minne = _minne()

        utfall = {}
        for namn, lager in (("pg", pg), ("minne", minne)):
            ider = {}
            for bolag, origin in (
                ("Påfyllt AB", "iris"), ("Bortvalt AB", "iris"), ("Kvalificerat AB", "iris"),
                ("Manuellt AB", "manual"), ("Ringbolag AB", "ring"), ("Provbolag AB", "test"),
                ("Exempelbolag AB", "example"),
            ):
                p = await lager.create_prospect(a, company_name=bolag, contact_email=None, origin=origin)
                ider[bolag] = p["id"]

            pafylld = await lager.spara_bedomning(
                a, ider["Påfyllt AB"],
                bedomning={"niva": "C", "qualified": False, "score_total": 41, "pafylld": True,
                           "pafylld_skal": "storlek:anstallda:max:55:49"},
            )
            assert pafylld["pafylld"] is True and pafylld["pafylld_skal"] == "storlek:anstallda:max:55:49"
            # Bedömningen står kvar (Antons regel: leadet behåller sin riktiga bedömning).
            assert pafylld["niva"] == "C" and pafylld["qualified"] is False
            await lager.spara_bedomning(a, ider["Bortvalt AB"], bedomning={"niva": "C", "qualified": False})
            await lager.spara_bedomning(
                a, ider["Kvalificerat AB"], bedomning={"niva": "A", "qualified": True, "score_total": 88}
            )

            lista = await lager.list_prospects(a, kolumner=LISTKOLUMNER)
            fordelning = await lager.list_prospects(a, kolumner=FORDELNINGSKOLUMNER)
            namn_av = {v: k for k, v in ider.items()}

            def _synliga(rader, **kw):
                return sorted(namn_av[str(p["id"])] for p in synliga(rader, tenant_id=a, kopplade=set(), **kw))

            pa = next(p for p in lista if str(p["id"]) == ider["Påfyllt AB"])
            utfall[namn] = {
                "lista": _synliga(lista),
                "bortvalda": _synliga(lista, bortvalda=True),
                "fordelning": _synliga(fordelning),
                "pafylld": (pa["pafylld"], pa["pafylld_skal"]),
                "nya": (await lager.weekly_analytics(a, weeks=1))["weeks"][-1]["new_leads"],
            }

            # Nollningen (api/leads.py när påfyllnaden inte höll): False och "".
            nollad = await lager.spara_bedomning(
                a, ider["Påfyllt AB"], bedomning={"pafylld": False, "pafylld_skal": ""}
            )
            utfall[namn]["nollad"] = (nollad["pafylld"], nollad["pafylld_skal"], nollad["niva"])
            utfall[namn]["efter_nollning"] = _synliga(await lager.list_prospects(a, kolumner=LISTKOLUMNER))

        assert utfall["pg"] == utfall["minne"]
        ut = utfall["pg"]
        assert ut["lista"] == ["Kvalificerat AB", "Manuellt AB", "Påfyllt AB"]
        assert ut["bortvalda"] == ["Bortvalt AB"]
        assert ut["fordelning"] == ut["lista"]
        assert ut["pafylld"] == (True, "storlek:anstallda:max:55:49")
        # iris x3 och manual räknas; ring, test och example gör det inte.
        assert ut["nya"] == 4
        assert ut["nollad"] == (False, "", "C")
        assert ut["efter_nollning"] == ["Kvalificerat AB", "Manuellt AB"]
        # Databasen bär det som skrevs.
        rad = await agare.fetchrow(
            "select pafylld, pafylld_skal from prospects where tenant_id = $1::uuid and company_name = 'Påfyllt AB'", a
        )
        assert (rad["pafylld"], rad["pafylld_skal"]) == (False, "")
    finally:
        if pool:
            await pool.close()
        await _stada(agare, kunder)
        await agare.close()


# -- Städaren och de vilande körningarna -------------------------------------


_IRIS = {"kalla": "iris", "klar": False, "pagaende": 0}

#: namn -> (status, scope, korning, ålder i minuter, förväntat städad)
_JOBB = {
    "vackbar": ("processing", "batch", _IRIS, 10, False),
    "vackbar_pagaende_null": ("processing", "batch", {**_IRIS, "pagaende": None}, 10, False),
    "for_gammal": ("processing", "batch", _IRIS, 25 * 60, True),
    "vilande": ("processing", "batch", {**_IRIS, "vilande": {"sedan": "2026-11-24T00:00:00+00:00", "skal": "uttomt"}},
                25 * 60, False),
    "listjobb": ("processing", "batch", {**_IRIS, "kalla": "lista"}, 10, True),
    "i_research": ("processing", "batch", {**_IRIS, "pagaende": 1}, 10, True),
    "klar": ("processing", "batch", {**_IRIS, "klar": True}, 10, True),
    "koad": ("queued", "batch", _IRIS, 10, True),
    "research_scope": ("processing", "research", _IRIS, 10, True),
    "utan_korning": ("processing", "batch", None, 10, True),
    "farsk": ("queued", "research", None, 1, False),
    "undantagen": ("processing", "research", None, 10, False),
    "pausad": ("processing", "batch", {**_IRIS, "pagaende": 1}, 10, False),
    "eget_fel": ("processing", "research", None, 10, True),
}


@pytest.mark.anyio
async def test_stadaren_later_vackbara_och_vilande_korningar_sta():
    from app.jobs.stadare import HANGFEL_JOBB
    from app.storage.postgres import PostgresStorage

    agare = await _agare()
    kunder: list[str] = []
    pool = None
    try:
        a = await _ny_kund(agare, "dr-sa")
        kunder.append(a)
        b = await _ny_kund(agare, "dr-sb")
        kunder.append(b)
        pool = await _approll()
        pg = PostgresStorage(pool)
        minne = _minne()
        prefix = uuid.uuid4().hex[:8]

        def jid(namn: str) -> str:
            return f"dr-{prefix}-{namn}"

        nu = datetime.now(timezone.utc)
        for lager in (pg, minne):
            for namn, (status, scope, korning, _, _) in _JOBB.items():
                await lager.set_leads_job_status(
                    a, job_id=jid(namn), status=status, scope=scope, korning=korning,
                    error="Eget fel" if namn == "eget_fel" else None,
                )
            await lager.set_korning_styrning(a, jid("pausad"), "paus")
            # En annan kunds lika gamla jobb.
            await lager.set_leads_job_status(b, job_id=jid("annan_kund"), status="processing", scope="research")

        # Åldra raderna: ägaren i databasen, fältet i minnet.
        for namn, (*_, alder, _) in _JOBB.items():
            await agare.execute(
                "update leads_job_ledger set updated_at = now() - make_interval(mins => $2) where job_id = $1",
                jid(namn), alder,
            )
            minne.leads_job_ledger[jid(namn)]["updated_at"] = (nu - timedelta(minutes=alder)).isoformat()
        await agare.execute(
            "update leads_job_ledger set updated_at = now() - interval '10 minutes' where job_id = $1",
            jid("annan_kund"),
        )
        minne.leads_job_ledger[jid("annan_kund")]["updated_at"] = (nu - timedelta(minutes=10)).isoformat()

        stadade = {}
        for namn, lager in (("pg", pg), ("minne", minne)):
            stadade[namn] = sorted(
                await lager.stada_hangande_leadsjobb(a, aldre_an_minuter=5, utom=[jid("undantagen")])
            )
        forvantat = sorted(jid(n) for n, (*_, stadas) in _JOBB.items() if stadas)
        assert stadade["pg"] == forvantat
        assert stadade["minne"] == stadade["pg"]

        # Felet i klartext i liggaren; ett befintligt fel skrivs inte över.
        rader = {r["job_id"]: r for r in await agare.fetch(
            "select job_id, status, error, completed_at from leads_job_ledger where tenant_id = $1::uuid", a)}
        for namn, (status, *_, stadas) in _JOBB.items():
            rad, mrad = rader[jid(namn)], minne.leads_job_ledger[jid(namn)]
            if stadas:
                fel = "Eget fel" if namn == "eget_fel" else HANGFEL_JOBB
                assert (rad["status"], rad["error"]) == ("failed", fel), namn
                assert (mrad["status"], mrad["error"]) == ("failed", fel), namn
                assert rad["completed_at"] is not None
            else:
                assert rad["status"] == mrad["status"] == status, namn

        # En annan kunds jobb rörs inte, och ett andra svep städar inget nytt.
        assert await agare.fetchval(
            "select status from leads_job_ledger where job_id = $1", jid("annan_kund")) == "processing"
        assert minne.leads_job_ledger[jid("annan_kund")]["status"] == "processing"
        assert await pg.stada_hangande_leadsjobb(a, aldre_an_minuter=5, utom=[jid("undantagen")]) == []

        # Väckarens läsning (vack_stillastaende_korningar) ser den vilande
        # och de väckbara körningarna med sitt tillstånd.
        for namn, lager in (("pg", pg), ("minne", minne)):
            pagaende = {
                k["job_id"]: k for k in await lager.list_leads_korningar(a, status="processing", limit=500)
            }
            assert {jid("vilande"), jid("vackbar"), jid("vackbar_pagaende_null")} <= set(pagaende), namn
            assert pagaende[jid("vilande")]["korning"]["vilande"]["skal"] == "uttomt", namn
            assert jid("for_gammal") not in pagaende, namn
    finally:
        if pool:
            await pool.close()
        await _stada(agare, kunder)
        await agare.close()


@pytest.mark.anyio
async def test_andra_korningars_bolag_ger_samma_svar_som_minnet():
    """list_andra_korningars_bolag (2026-11-25): bara namn och org.nr ur kundens
    ANDRA pågående körningar. En vilande körning håller bara sina kandidater,
    en klar och den egna räknas inte, och en annan kunds körning syns aldrig.
    Frågan plockar ut fälten i SQL, så formerna nedan prövar att den tolkar
    `vilande` och `klar` som minneslagret gör (tomt, noll och "false" är falskt)."""
    from app.api import leads as leads_api
    from app.storage.postgres import PostgresStorage

    agare = await _agare()
    kunder: list[str] = []
    pool = None
    try:
        a = await _ny_kund(agare, "dr-ka")
        kunder.append(a)
        b = await _ny_kund(agare, "dr-kb")
        kunder.append(b)
        pool = await _approll()
        pg = PostgresStorage(pool)
        minne = _minne()
        prefix = uuid.uuid4().hex[:8]

        def jid(namn: str) -> str:
            return f"dr-{prefix}-{namn}"

        def korning(namn: str, **extra) -> dict:
            return {
                "kandidater": [{"company_name": f"Kandidat {namn} AB", "orgnr": "5560000001", "tung": "x" * 50}],
                "tratt": [{"namn": f"Tratt {namn} AB", "steg": "jev"}],
                "listspar": [{"company_name": f"Listspar {namn} AB", "orgnr": None}],
                "utslag": [1, 2, 3], "webbpool": {"x": 1},
                **extra,
            }

        former = {
            "aktiv": korning("aktiv"),
            "vilande": korning("vilande", vilande={"skal": "registret"}),
            "vilande_tom": korning("vilandetom", vilande={}),
            "vilande_noll": korning("vilandenoll", vilande=0),
            "vilande_falsk_text": korning("vilandefalsk", vilande="false"),
            "klar": korning("klar", klar=True),
            "klar_noll": korning("klarnoll", klar=0),
            "kandidater_fel_form": {"kandidater": {"company_name": "Fel form AB"}, "tratt": "x", "listspar": None},
            "tom": {},
            "egen": korning("egen"),
        }
        for lager in (pg, minne):
            for namn, k in former.items():
                await lager.set_leads_job_status(a, job_id=jid(namn), status="processing", scope="batch", korning=k)
            await lager.set_leads_job_status(a, job_id=jid("avslutad"), status="completed", scope="batch",
                                             korning=korning("avslutad"))
            await lager.set_leads_job_status(b, job_id=jid("annan_kund"), status="processing", scope="batch",
                                             korning=korning("annankund"))

        def bild(rader: list[dict]) -> dict:
            return {
                r["job_id"]: (
                    bool(r["vilande"]),
                    sorted((x.get("company_name"), x.get("orgnr")) for x in r["kandidater"]),
                    sorted((x.get("company_name"), x.get("orgnr")) for x in r["listspar"]),
                    sorted(str(t) for t in r["tratt"]),
                )
                for r in rader
            }

        fran_pg = await pg.list_andra_korningars_bolag(a, utom=jid("egen"), limit=20)
        fran_minne = await minne.list_andra_korningars_bolag(a, utom=jid("egen"), limit=20)
        assert bild(fran_pg) == bild(fran_minne)

        # Bara namn och org.nr lämnar databasen, aldrig resten av arbetsminnet.
        for rad in fran_pg:
            assert set(rad) == {"job_id", "vilande", "kandidater", "listspar", "tratt"}, rad
            for post in rad["kandidater"] + rad["listspar"]:
                assert set(post) <= {"company_name", "orgnr"}, post

        med = set(bild(fran_pg))
        assert jid("egen") not in med and jid("avslutad") not in med and jid("klar") not in med
        assert jid("annan_kund") not in med
        assert bild(fran_pg)[jid("vilande")] == (True, [("Kandidat vilande AB", "5560000001")], [], [])

        # Samma mängd upptagna bolag genom funktionen som motorn anropar.
        ur_pg = await leads_api._andra_korningars_bolag(pg, a, jid("egen"))
        ur_minne = await leads_api._andra_korningars_bolag(minne, a, jid("egen"))
        assert ur_pg == ur_minne and ur_pg
        # Den andra kunden ser bara sitt eget, och inget av kund a:s.
        assert await pg.list_andra_korningars_bolag(b, utom=jid("ingen"), limit=20) and not (
            await leads_api._andra_korningars_bolag(pg, b, jid("annan_kund"))
        )
    finally:
        if pool:
            await pool.close()
        await _stada(agare, kunder)
        await agare.close()
