"""Exempelartiklarna rensas av sig själva (Anton 2026-11-25, planen för
Hjälprutan del 4 och fas 0).

En testarbetsyta kan få Nordlys Handels exempelbas (`ensure_tenant_kb`).
Raderna märks `is_placeholder` och försvinner i samma skrivning som kundens
EGET innehåll kommer in: en artikel kunden lägger till, ett skanningsförslag
eller ett chattförslag kunden godkänner. Ett förslag som bara väntar räcker
inte, då stod basen annars tom.

Snajps egen bas, hjälpens bas och Nordlys egen bas märks aldrig.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.kb_articles import KB_ARTICLES
from app.main import app
from app.scripts.seed_kb import ensure_tenant_kb, seed_tenant
from app.tenants.konvertera import kora
from app.tenants.snajp_hjalp import seed_hjalp

MASTER = {"X-API-Key": get_settings().snajp_master_api_key}
EXEMPELRUBRIK = KB_ARTICLES[3]["title"]  # "Leveranstider och fraktalternativ"
TEXT = "Vi skickar inom två arbetsdagar och frakten är fri över 400 kronor."


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _testyta(c, slug: str) -> tuple[dict, str]:
    svar = await c.post(
        "/api/keys",
        headers=MASTER,
        json={"tenant_name": slug, "slug": slug, "exempel_kb": True, "kraver_avtal": False},
    )
    assert svar.status_code == 201, svar.text
    assert svar.json()["kb_seeded"] == len(KB_ARTICLES)
    return {"X-API-Key": svar.json()["api_key"]}, svar.json()["tenant_id"]


async def _artiklar(c, nyckel: dict) -> list[dict]:
    svar = await c.get("/api/kb", headers=nyckel)
    assert svar.status_code == 200
    return svar.json()["articles"]


@pytest.mark.anyio
async def test_exempelbasen_ar_markt_och_api_t_lamnar_market():
    async with app.router.lifespan_context(app):
        async with _client() as c:
            nyckel, _ = await _testyta(c, "testkund-ex000001")
            artiklar = await _artiklar(c, nyckel)
            assert len(artiklar) == len(KB_ARTICLES)
            assert all(a["is_placeholder"] is True for a in artiklar)


@pytest.mark.anyio
async def test_egen_artikel_tar_bort_exemplen():
    async with app.router.lifespan_context(app):
        async with _client() as c:
            nyckel, _ = await _testyta(c, "testkund-ex000002")
            svar = await c.post(
                "/api/kb",
                headers=nyckel,
                json={"articles": [{"title": "Frakt", "content": TEXT, "category": "leverans"}]},
            )
            assert svar.status_code == 201, svar.text
            artiklar = await _artiklar(c, nyckel)
            assert [(a["title"], a["is_placeholder"]) for a in artiklar] == [("Frakt", False)]


@pytest.mark.anyio
async def test_vantande_forslag_tar_inte_bort_exemplen_men_godkant_gor_det():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        async with _client() as c:
            nyckel, tenant_id = await _testyta(c, "testkund-ex000003")
            skanning = await storage.skapa_kb_skanning(
                tenant_id, webbplats="https://exempel-ab.se", startad_av="onboarding", status="klar"
            )
            await storage.add_kb_forslag(
                tenant_id,
                skanning["id"],
                [{"title": "Våra tjänster", "content": TEXT, "category": "salj", "source_url": None}],
            )
            # Väntande förslag: exemplen står kvar, annars blev basen tom.
            assert len(await _artiklar(c, nyckel)) == len(KB_ARTICLES)

            forslag = (await c.get("/api/kb/forslag", headers=nyckel)).json()["forslag"]
            beslut = await c.post(
                "/api/kb/forslag/beslut",
                headers=nyckel,
                json={"ids": [forslag[0]["id"]], "beslut": "lagg_till"},
            )
            assert beslut.status_code == 200, beslut.text
            assert beslut.json()["tillagda"] == [forslag[0]["id"]]
            assert [a["title"] for a in await _artiklar(c, nyckel)] == ["Våra tjänster"]


@pytest.mark.anyio
async def test_godkant_chattforslag_tar_bort_exemplen():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        async with _client() as c:
            nyckel, tenant_id = await _testyta(c, "testkund-ex000004")
            svar = await c.post(
                "/api/kb/forslag",
                headers=nyckel,
                json={"title": "Öppettider i butiken", "content": TEXT, "category": "ovrigt", "kalla": "chatt"},
            )
            assert svar.status_code == 201, svar.text
            assert len(await _artiklar(c, nyckel)) == len(KB_ARTICLES)

            artikel = await storage.lagg_till_kb_forslag(tenant_id, svar.json()["id"], embedding=None)
            assert artikel is not None
            assert [a["title"] for a in await _artiklar(c, nyckel)] == ["Öppettider i butiken"]


@pytest.mark.anyio
async def test_dubblettkontrollen_bortser_fran_exempelrubriker():
    """En exempelrubrik hindrar aldrig kundens egen artikel med samma rubrik."""
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        async with _client() as c:
            nyckel, tenant_id = await _testyta(c, "testkund-ex000005")
            svar = await c.post(
                "/api/kb/forslag",
                headers=nyckel,
                json={"title": EXEMPELRUBRIK, "content": TEXT, "category": "leverans", "kalla": "chatt"},
            )
            assert svar.status_code == 201, svar.text

            beslut = await c.post(
                "/api/kb/forslag/beslut",
                headers=nyckel,
                json={"ids": [svar.json()["id"]], "beslut": "lagg_till"},
            )
            assert beslut.json()["tillagda"] == [svar.json()["id"]]
            assert beslut.json()["fanns_redan"] == []
            artiklar = await _artiklar(c, nyckel)
            assert [(a["title"], a["is_placeholder"]) for a in artiklar] == [(EXEMPELRUBRIK, False)]
            assert storage is app.state.storage


@pytest.mark.anyio
async def test_skanningen_foreslar_en_exempelrubrik():
    from app.api.kb import _spara_utfall

    async with app.router.lifespan_context(app):
        storage = app.state.storage
        async with _client() as c:
            _, tenant_id = await _testyta(c, "testkund-ex000006")
            skanning = await storage.skapa_kb_skanning(
                tenant_id, webbplats="https://exempel-ab.se", startad_av="onboarding"
            )
            await _spara_utfall(
                storage,
                tenant_id,
                skanning["id"],
                {"artiklar": [{"title": EXEMPELRUBRIK, "content": TEXT, "category": "leverans"}]},
            )
            assert [f["title"] for f in await storage.list_kb_forslag(tenant_id)] == [EXEMPELRUBRIK]


@pytest.mark.anyio
async def test_snajps_hjalpens_och_nordlys_baser_marks_aldrig():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        assert await storage.list_kb(DEFAULT_TENANT_ID)
        assert not any(a.get("is_placeholder") for a in await storage.list_kb(DEFAULT_TENANT_ID))

        await seed_hjalp(storage, slug="snajp-hjalp-exempeltest")
        await seed_tenant(storage, "snajp")
        for tenant in await storage.list_tenants():
            if tenant["slug"] in {"snajp-hjalp-exempeltest", "snajp"}:
                artiklar = await storage.list_kb(tenant["id"])
                assert artiklar
                assert not any(a.get("is_placeholder") for a in artiklar)


@pytest.mark.anyio
async def test_konverteringen_for_inte_med_exemplen():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        kalla = await storage.create_tenant(slug="testkund-ex000007", name="Test Ex")
        mal = await storage.create_tenant(slug="riktig-ex000007", name="Riktig Ex")
        await ensure_tenant_kb(storage, kalla["id"])

        rapport = await kora(storage, fran="testkund-ex000007", till="riktig-ex000007")
        assert rapport["kunskapsbas"]["fran"] == 0

        await kora(storage, fran="testkund-ex000007", till="riktig-ex000007", apply=True)
        assert await storage.list_kb(mal["id"]) == []


@pytest.mark.anyio
async def test_inboxmocken_lagger_inte_tillbaka_exemplen():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        async with _client() as c:
            nyckel, tenant_id = await _testyta(c, "testkund-ex000008")
            demo = {**nyckel, "X-Snajp-Demo": "true"}
            svar = await c.post(
                "/api/kb/forslag",
                headers=nyckel,
                json={"title": "Våra öppettider", "content": TEXT, "category": "ovrigt", "kalla": "chatt"},
            )
            await c.post(
                "/api/kb/forslag/beslut", headers=nyckel, json={"ids": [svar.json()["id"]], "beslut": "lagg_till"}
            )
            # Kunden raderar sin enda artikel: basen är tom men HAR haft eget innehåll.
            (artikel,) = await _artiklar(c, nyckel)
            assert (await c.delete(f"/api/kb/{artikel['id']}", headers=nyckel)).status_code == 200
            assert await _artiklar(c, nyckel) == []

            mock = await c.post("/api/inbox/mock", headers=demo, json={})
            assert mock.status_code == 201, mock.text
            assert mock.json()["kb_seeded"] == 0
            assert await _artiklar(c, nyckel) == []
            assert await ensure_tenant_kb(storage, tenant_id) == 0


@pytest.mark.anyio
async def test_seedningen_fyller_inte_pa_en_bas_med_eget_innehall():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        tenant = await storage.create_tenant(slug="testkund-ex000009", name="Test Ex9")
        await storage.add_kb_article(tenant["id"], title="Frakt", content=TEXT, category="leverans")
        assert await ensure_tenant_kb(storage, tenant["id"]) == 0
        assert [a["title"] for a in await storage.list_kb(tenant["id"])] == ["Frakt"]


def test_migrationen_marker_exakt_de_rubriker_seedningen_skriver():
    """Migration 159 jämför den exakta rubriken: lower() viker inte Å/Ä/Ö
    under C-kollation, så gemenlistan ensam missade tre exempelrader."""
    import re
    from pathlib import Path

    sql = (
        Path(__file__).resolve().parents[3] / "db" / "migrations" / "20261125140000_159_kb_exempel_rensas.sql"
    ).read_text(encoding="utf-8")
    exakt = sql.split("btrim(k.title) in (", 1)[1].split(") or lower", 1)[0]
    assert re.findall(r"'([^']*)'", exakt) == [a["title"] for a in KB_ARTICLES]
