"""Demovyns skrivningar stannar i demokontot.

Vyväxeln Admin / Demo (lib/vy.ts) låter en plattformsadmin skriva i demokontot
från sin egen inloggning: kunskapsbas, röstdokument, målgrupp och regler. Det
är hela poängen med vyn — man ska kunna visa en kund hur inställningarna
fungerar och faktiskt ändra dem medan man visar.

Därmed blir frågan "vart tar de skrivningarna vägen" en säkerhetsfråga och inte
en detalj. Filen mäter det som faktiskt kan gå fel: att en skrivning gjord med
demonyckeln syns för någon annan tenant.

Kompletterar tests/test_tenant_isolation.py, som mäter LÄSNING av ärenden.
Här mäts SKRIVNING av de fyra instruktionsytorna, eftersom det är de vyväxeln
öppnar och de som inte fanns när den filen skrevs.

Kör i minne. Kostar ingenting, och kräver ingen databas.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app

settings = get_settings()
DEMO = {"X-API-Key": settings.snajp_demo_api_key}
MASTER = {"X-API-Key": settings.snajp_master_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _annan_tenant(client) -> dict:
    """En helt annan kund, skapad genom samma väg som en riktig onboarding."""
    svar = await client.post(
        "/api/keys", headers=MASTER, json={"tenant_name": "Granne Bygghandel AB"}
    )
    assert svar.status_code == 201, svar.text
    return {"X-API-Key": svar.json()["api_key"]}


@pytest.mark.anyio
async def test_kunskapsbasen_delas_inte():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            granne = await _annan_tenant(client)

            titel = "Hemlig demoartikel om fraktfritt"
            skriven = await client.post(
                "/api/kb",
                headers=DEMO,
                json={
                    "articles": [
                        {
                            "title": titel,
                            "category": "leverans",
                            "content": "Fri frakt over 499 kronor inom Sverige, 2-4 vardagar.",
                        }
                    ]
                },
            )
            assert skriven.status_code == 201, skriven.text

            egna = await client.get("/api/kb", headers=DEMO)
            assert titel in {a["title"] for a in egna.json()["articles"]}

            # Grannens bas ska vara orörd. Det är den här riktningen som gör
            # skada: en artikel som läcker hit blir ETT ANNAT BOLAGS villkor,
            # presenterade som grannens egna svar till grannens kund — och
            # grundningsgrinden ser bara en träff, aldrig vems.
            grannens = await client.get("/api/kb", headers=granne)
            assert titel not in {a["title"] for a in grannens.json()["articles"]}


@pytest.mark.anyio
async def test_rostdokumentet_delas_inte():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            granne = await _annan_tenant(client)

            rost = "Vi skriver lugnt och konkret. Inga utropstecken."
            skriven = await client.put("/api/leads/soul", headers=DEMO, json={"content": rost})
            assert skriven.status_code == 200, skriven.text

            assert (await client.get("/api/leads/soul", headers=DEMO)).json()["content"] == rost
            assert (await client.get("/api/leads/soul", headers=granne)).json()["content"] != rost


@pytest.mark.anyio
async def test_malgruppen_delas_inte():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            granne = await _annan_tenant(client)

            skriven = await client.put(
                "/api/leads/config",
                headers=DEMO,
                json={"autonomy": "draft", "icp": {"industries": ["Hotell och konferens"]}},
            )
            assert skriven.status_code == 200, skriven.text

            egen = (await client.get("/api/leads/config", headers=DEMO)).json()
            assert "Hotell och konferens" in egen["icp"]["industries"]

            grannens = (await client.get("/api/leads/config", headers=granne)).json()
            assert "Hotell och konferens" not in (grannens["icp"].get("industries") or [])


@pytest.mark.anyio
async def test_affarskontexten_delas_inte():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            granne = await _annan_tenant(client)

            text = "Vad vi saljer: inredning och utemiljo for foretag."
            skriven = await client.post(
                "/api/leads/context-docs",
                headers=DEMO,
                json={"kind": "product_marketing", "content": text, "source": "test"},
            )
            assert skriven.status_code in (200, 201), skriven.text

            egna = await client.get("/api/leads/context-docs?kind=product_marketing", headers=DEMO)
            assert text in {d["content"] for d in egna.json()["docs"]}

            grannens = await client.get(
                "/api/leads/context-docs?kind=product_marketing", headers=granne
            )
            assert text not in {d["content"] for d in grannens.json()["docs"]}


@pytest.mark.anyio
async def test_reglerna_delas_inte():
    async with app.router.lifespan_context(app):
        async with _client() as client:
            granne = await _annan_tenant(client)

            skriven = await client.put(
                "/api/rules", headers=DEMO, json={"category": "orderstatus", "mode": "auto"}
            )
            assert skriven.status_code == 200, skriven.text

            def lage(kropp: dict) -> str | None:
                for regel in kropp["rules"]:
                    if regel["category"] == "orderstatus":
                        return regel["mode"]
                return None

            assert lage((await client.get("/api/rules", headers=DEMO)).json()) == "auto"
            # Grannen står kvar på förvalet. Ett fack som tyst blir `auto` för
            # alla är skillnaden mellan ett utkast en människa läser och ett
            # svar som redan gått iväg.
            assert lage((await client.get("/api/rules", headers=granne)).json()) == "draft"
