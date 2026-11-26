"""POST /api/kb/forslag: text ur Hjälprutan som ett väntande förslag i
NYCKELNS egen kunskapsbas (migration 157, planens del 3)."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app

MASTER = {"X-API-Key": get_settings().snajp_master_api_key}
TEXT = "Vi levererar inom tre arbetsdagar till hela Sverige, och frakten är fri över 500 kronor."


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _kund(c, slug: str) -> dict:
    svar = await c.post("/api/keys", headers=MASTER, json={"tenant_name": slug, "slug": slug, "kraver_avtal": False})
    return {"X-API-Key": svar.json()["api_key"]}


@pytest.mark.anyio
async def test_forslaget_hamnar_i_nyckelns_tenant_och_syns_i_listan():
    anvandare = str(uuid.uuid4())
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            a = await _kund(c, "kund-aaaa1111")
            b = await _kund(c, "kund-bbbb2222")

            svar = await c.post(
                "/api/kb/forslag",
                headers={**a, "X-Snajp-User": anvandare},
                json={"title": "Leveranstider", "content": TEXT, "category": "leverans", "kalla": "chatt"},
            )
            assert svar.status_code == 201, svar.text
            forslag = svar.json()
            assert forslag["kalla"] == "chatt"
            assert forslag["status"] == "vantar"
            assert forslag["skanning_id"] is None
            assert forslag["skapad_av"] == anvandare
            assert forslag["category"] == "leverans"

            lista_a = (await c.get("/api/kb/forslag", headers=a)).json()["forslag"]
            assert [(f["id"], f["kalla"]) for f in lista_a] == [(forslag["id"], "chatt")]
            # Den andra kunden ser ingenting, och kunskapsbasen rörs inte förrän
            # kunden lägger till förslaget.
            assert (await c.get("/api/kb/forslag", headers=b)).json()["forslag"] == []
            assert (await c.get("/api/kb", headers=a)).json()["articles"] == []

            # Den vanliga beslutsvägen gör förslaget till en artikel.
            beslut = await c.post(
                "/api/kb/forslag/beslut", headers=a, json={"ids": [forslag["id"]], "beslut": "lagg_till"}
            )
            assert beslut.json()["tillagda"] == [forslag["id"]]
            assert [x["title"] for x in (await c.get("/api/kb", headers=a)).json()["articles"]] == ["Leveranstider"]
            assert (await c.get("/api/kb", headers=b)).json()["articles"] == []


@pytest.mark.anyio
async def test_samma_kontroller_som_ovriga_skrivningar():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            a = await _kund(c, "kund-cccc3333")

            async def post(**kropp):
                return await c.post("/api/kb/forslag", headers=a, json={"kalla": "chatt", **kropp})

            assert (await post(title="Ok", content=TEXT)).status_code == 422  # för kort rubrik
            assert (await post(title="Leverans", content="kort")).status_code == 422
            assert (await post(title="Leverans", content=TEXT, category="hittepa")).status_code == 422
            assert (await c.post(
                "/api/kb/forslag", headers=a, json={"title": "Leverans", "content": TEXT, "kalla": "skanning"}
            )).status_code == 422

            forsta = await post(title="Leveranstider", content=TEXT)
            assert forsta.status_code == 201 and forsta.json()["category"] == "ovrigt"
            # Dubbletten av ett väntande förslag, även med annan form på rubriken.
            assert (await post(title="LEVERANSTIDER.", content=TEXT)).status_code == 409

            await c.post("/api/kb", headers=a, json={"articles": [{"title": "Returer och ångerrätt", "content": TEXT}]})
            assert (await post(title="Returer och ångerrätt", content=TEXT)).status_code == 409
            # Ett X-Snajp-User som inte är ett uuid sparas inte.
            tredje = await c.post(
                "/api/kb/forslag", headers={**a, "X-Snajp-User": "inte-ett-id"},
                json={"title": "Öppettider", "content": TEXT, "kalla": "chatt"},
            )
            assert tredje.status_code == 201 and tredje.json()["skapad_av"] is None
