"""Webbplatsskanningens förslag (migration 121): POST /api/kb/skanna med
`spara`, GET /api/kb/forslag och POST /api/kb/forslag/beslut.

Beställningen (Anton 2026-11-18): skanningen startas automatiskt vid
onboardingen och KOMPLETTERAR kundens egna uppgifter, skriver aldrig över
dem. Testerna nedan låser just det: en artikel kunden redan har ändras aldrig,
ett utkast med samma rubrik som en befintlig artikel föreslås inte, ett
avvisat utkast kommer inte tillbaka vid nästa skanning, och två klick blir
aldrig två artiklar. Inga nätanrop och ingen modell.
"""

from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app import kb_skanning as ks
from app.api.kb import nya_forslag, titelnyckel
from app.config import get_settings
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _utkast(*titlar: str) -> list[dict]:
    return [
        {
            "title": titel,
            "content": f"Text om {titel.lower()}.",
            "category": "allmant",
            "source_url": "https://lingonkudden.se/info",
            "confidence": 0.8,
            "varningar": [],
        }
        for titel in titlar
    ]


def _falsk_skanning(artiklar: list[dict]):
    async def skanna(webbplats, bolagsnamn, anropa, **_):
        return {
            "webbplats": webbplats, "robots": "saknas", "sidor": 4, "lasbara_sidor": 3,
            "blockerade": 0, "artiklar": artiklar, "saknas": [], "anrop": 1, "fel": [],
        }

    return skanna


async def _vanta_klar(c: AsyncClient) -> dict:
    for _ in range(100):
        svar = (await c.get("/api/kb/forslag", headers=DEMO)).json()
        if svar["skanning"] and svar["skanning"]["status"] != "pagar":
            return svar
        await asyncio.sleep(0.02)
    raise AssertionError("skanningen blev aldrig klar")


# --- dubblettfiltret ------------------------------------------------------------


def test_titelnyckel_bortser_fran_skiftlage_och_skiljetecken():
    assert titelnyckel("  Leverans, frakt & RETUR!") == titelnyckel("leverans frakt retur")
    assert titelnyckel("") == ""


def test_nya_forslag_hoppar_over_det_som_redan_finns():
    nya, redan = nya_forslag(_utkast("Öppettider", "Retur", "retur", "Priser"), ["öppettider"])
    assert [f["title"] for f in nya] == ["Retur", "Priser"]
    assert redan == 2


# --- hela flödet ----------------------------------------------------------------


@pytest.mark.anyio
async def test_sparad_skanning_kompletterar_och_skriver_aldrig_over(monkeypatch):
    monkeypatch.setattr(ks, "ar_publik_vard", lambda url: True)
    monkeypatch.setattr(ks, "bygg_anropare", lambda: None)
    monkeypatch.setattr(ks, "skanna", _falsk_skanning(_utkast("Öppettider", "Retur och byte", "Priser")))

    async with app.router.lifespan_context(app):
        storage = app.state.storage
        async with _client() as c:
            # Kundens egen artikel, med en egen text, finns före skanningen.
            egen = await c.post(
                "/api/kb",
                json={"articles": [{"title": "Öppettider", "content": "Kundens egen text.", "category": "allmant"}]},
                headers=DEMO,
            )
            assert egen.status_code == 201, egen.text

            r = await c.post(
                "/api/kb/skanna",
                json={"webbplats": "lingonkudden.se", "spara": True, "startad_av": "onboarding"},
                headers=DEMO,
            )
            assert r.status_code == 202, r.text
            assert r.json()["skanning"]["startad_av"] == "onboarding"

            svar = await _vanta_klar(c)
            skanning = svar["skanning"]
            assert skanning["status"] == "klar"
            assert skanning["forslag"] == 2 and skanning["redan_fanns"] == 1
            titlar = sorted(f["title"] for f in svar["forslag"])
            assert titlar == ["Priser", "Retur och byte"]

            # Lägg till ett, avvisa ett. Två klick på samma blir en artikel.
            retur = next(f for f in svar["forslag"] if f["title"] == "Retur och byte")
            priser = next(f for f in svar["forslag"] if f["title"] == "Priser")
            for _ in range(2):
                b = await c.post(
                    "/api/kb/forslag/beslut", json={"ids": [retur["id"]], "beslut": "lagg_till"}, headers=DEMO
                )
                assert b.status_code == 200, b.text
            a = await c.post(
                "/api/kb/forslag/beslut", json={"ids": [priser["id"]], "beslut": "avvisa"}, headers=DEMO
            )
            assert a.json()["avvisade"] == [priser["id"]]

            artiklar = (await c.get("/api/kb", headers=DEMO)).json()["articles"]
            assert [x["content"] for x in artiklar if x["title"] == "Öppettider"] == ["Kundens egen text."]
            assert sum(1 for x in artiklar if x["title"] == "Retur och byte") == 1
            assert not any(x["title"] == "Priser" for x in artiklar)
            assert (await c.get("/api/kb/forslag", headers=DEMO)).json()["forslag"] == []

            # En ny skanning föreslår varken det tillagda eller det avvisade igen.
            r2 = await c.post("/api/kb/skanna", json={"webbplats": "lingonkudden.se", "spara": True}, headers=DEMO)
            assert r2.status_code == 202, r2.text
            svar2 = await _vanta_klar(c)
            assert svar2["skanning"]["forslag"] == 0 and svar2["skanning"]["redan_fanns"] == 3
            assert svar2["forslag"] == []

        # Städa: minneslagringen delas av testerna i samma process.
        for a in await storage.list_kb(skanning["tenant_id"]):
            await storage.delete_kb_article(skanning["tenant_id"], a["id"])


@pytest.mark.anyio
async def test_en_skanning_i_taget(monkeypatch):
    monkeypatch.setattr(ks, "ar_publik_vard", lambda url: True)
    monkeypatch.setattr(ks, "bygg_anropare", lambda: None)
    slapp = asyncio.Event()

    async def langsam(webbplats, bolagsnamn, anropa, **_):
        await slapp.wait()
        return await _falsk_skanning(_utkast("Leveranstider"))(webbplats, bolagsnamn, anropa)

    monkeypatch.setattr(ks, "skanna", langsam)
    async with app.router.lifespan_context(app):
        async with _client() as c:
            forsta = await c.post("/api/kb/skanna", json={"webbplats": "lingonkudden.se", "spara": True}, headers=DEMO)
            andra = await c.post("/api/kb/skanna", json={"webbplats": "lingonkudden.se", "spara": True}, headers=DEMO)
            assert forsta.status_code == andra.status_code == 202
            assert andra.json()["status"] == "pagar"
            assert andra.json()["skanning"]["id"] == forsta.json()["skanning"]["id"]
            slapp.set()
            await _vanta_klar(c)


@pytest.mark.anyio
async def test_skanning_som_inte_kan_starta_syns_med_skal(monkeypatch):
    monkeypatch.setattr(ks, "ar_publik_vard", lambda url: False)
    async with app.router.lifespan_context(app):
        async with _client() as c:
            r = await c.post("/api/kb/skanna", json={"webbplats": "lingonkudden.se", "spara": True}, headers=DEMO)
            assert r.status_code == 422
            skanning = (await c.get("/api/kb/forslag", headers=DEMO)).json()["skanning"]
    assert skanning["status"] == "fel"
    assert skanning["fel"] == "Webbplatsen hittades inte."
