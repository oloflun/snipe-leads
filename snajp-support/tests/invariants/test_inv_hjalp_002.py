"""INV-HJALP-002 — hjälpens vägar når bara hjälpens nyckel, och tvärtom.

Plan: docs/PLAN-HJALPRUTAN-2026-11-25.md, del 2 och 5. Tenantgränsen:

1. **Strukturen.** Varje route under `/api/hjalp` och `/api/plattformsarenden`
   har `require_hjalp_tenant` i sitt beroendeträd, och varje route under
   `/api/admin/plattformsarenden` har `require_master_key`. En ny väg med en
   egen grind, eller ingen, fäller här.
2. **Beteendet.** En ANNAN tenants nyckel (demokundens och en nyskapad kunds)
   får 404 på varje hjälpväg; master-nyckeln, som saknar tenant, kommer inte
   in på dem heller. Adminvägarna kräver master-nyckeln.
3. **Domänerna.** `/api/hjalp/samtal` godtar bara `@kund.snajp.se` och avvisar
   marknadssidans `@session.snajp.se`; den anonyma `/api/chat/samtal`
   avvisar fortfarande `@kund.snajp.se`.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient

from app.api.deps import require_master_key
from app.api.hjalp import require_hjalp_tenant
from app.config import get_settings
from app.main import app

MASTER = {"X-API-Key": get_settings().snajp_master_api_key}
DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}
ANNA = str(uuid.uuid4())

RAPPORT = {
    "rapportor_user_id": ANNA,
    "rapportor_namn": None,
    "kund_workspace_id": str(uuid.uuid4()),
    "kund_tenant_slug": "kund-1234abcd",
    "vy": "leads",
    "roll": "owner",
    "besok_av_admin": False,
    "sida": "/dashboard",
    "gjorde": "Klickade",
    "hande": "Inget",
    "vantade": "Något",
    "bild": None,
}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _beroenden(dependant) -> list:
    ut = []
    for dep in dependant.dependencies:
        ut.append(dep.call)
        ut.extend(_beroenden(dep))
    return ut


def _alla_routes() -> list:
    ut = []
    for r in app.routes:
        if isinstance(r, APIRoute):
            ut.append(r)
        elif hasattr(r, "effective_route_contexts"):
            ut.extend(c for c in r.effective_route_contexts() if hasattr(c, "dependant"))
    return ut


def test_varje_hjalpvag_har_hjalpgrinden():
    hjalp = [r for r in _alla_routes() if r.path.startswith(("/api/hjalp", "/api/plattformsarenden"))]
    assert {r.path for r in hjalp} >= {
        "/api/hjalp/samtal",
        "/api/plattformsarenden",
        "/api/plattformsarenden/{arende_id}/svar",
        "/api/plattformsarenden/{arende_id}/utslag",
    }
    utan = [r.path for r in hjalp if require_hjalp_tenant not in _beroenden(r.dependant)]
    assert not utan, f"Hjälpvägar utan require_hjalp_tenant: {utan}"

    admin = [r for r in _alla_routes() if r.path.startswith("/api/admin/plattformsarenden")]
    # Listan, lägesbytet och bildläsningen (2026-11-25). En ny adminväg ska
    # läggas till här med flit, så att den inte tillkommer obemärkt.
    assert sorted(r.path for r in admin) == [
        "/api/admin/plattformsarenden",
        "/api/admin/plattformsarenden/{arende_id}/bild",
        "/api/admin/plattformsarenden/{arende_id}/status",
    ]
    utan = [r.path for r in admin if require_master_key not in _beroenden(r.dependant)]
    assert not utan, f"Adminvägar utan require_master_key: {utan}"


async def _anrop(c, headers: dict) -> list[tuple[str, int]]:
    arende = str(uuid.uuid4())
    return [
        ("POST /api/hjalp/samtal", (await c.post(
            "/api/hjalp/samtal", headers=headers, json={"customer_email": f"{ANNA}@kund.snajp.se"})).status_code),
        ("POST /api/plattformsarenden", (await c.post(
            "/api/plattformsarenden", headers=headers, json=RAPPORT)).status_code),
        ("GET /api/plattformsarenden", (await c.get(
            f"/api/plattformsarenden?rapportor={ANNA}", headers=headers)).status_code),
        ("POST svar", (await c.post(
            f"/api/plattformsarenden/{arende}/svar", headers=headers,
            json={"rapportor_user_id": ANNA, "text": "x"})).status_code),
        ("POST utslag", (await c.post(
            f"/api/plattformsarenden/{arende}/utslag", headers=headers,
            json={"rapportor_user_id": ANNA, "fungerar": True})).status_code),
    ]


@pytest.mark.anyio
async def test_en_annan_tenants_nyckel_far_404_och_hjalpens_nyckel_kommer_in():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            kund = await c.post("/api/keys", headers=MASTER, json={"tenant_name": "Granne AB", "slug": "granne-ab"})
            kund_h = {"X-API-Key": kund.json()["api_key"]}
            # "snajp" (marknadssidans demo) är också en annan kund.
            snajp = await c.post(
                "/api/keys", headers=MASTER, json={"tenant_name": "Snajp", "slug": "snajp", "kraver_avtal": False}
            )
            snajp_h = {"X-API-Key": snajp.json()["api_key"]}

            for namn, h in (("demo", DEMO), ("kund", kund_h), ("snajp", snajp_h)):
                for vag, status in await _anrop(c, h):
                    assert status == 404, f"{namn}: {vag} svarade {status}"

            # Master-nyckeln har ingen tenant och når inte hjälpens vägar.
            for vag, status in await _anrop(c, MASTER):
                assert status == 403, f"master: {vag} svarade {status}"

            hjalp = await c.post(
                "/api/keys",
                headers=MASTER,
                json={"tenant_name": "Snajp Hjälp", "slug": get_settings().hjalp_tenant_slug, "kraver_avtal": False},
            )
            hjalp_h = {"X-API-Key": hjalp.json()["api_key"]}
            utfall = dict(await _anrop(c, hjalp_h))
            assert utfall["POST /api/hjalp/samtal"] == 200
            assert utfall["POST /api/plattformsarenden"] == 201
            assert utfall["GET /api/plattformsarenden"] == 200
            # Okänt ärende för hjälpens nyckel: 404 av ärendet, inte av grinden.
            assert utfall["POST svar"] == 404

            # Adminvägarna kräver master-nyckeln.
            for h in (hjalp_h, kund_h, DEMO):
                assert (await c.get("/api/admin/plattformsarenden", headers=h)).status_code == 403
                assert (await c.post(
                    f"/api/admin/plattformsarenden/{uuid.uuid4()}/status", headers=h, json={"status": "undersoks"}
                )).status_code == 403
            assert (await c.get("/api/admin/plattformsarenden", headers=MASTER)).status_code == 200


@pytest.mark.anyio
async def test_domanerna_halls_isar():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            hjalp = await c.post(
                "/api/keys",
                headers=MASTER,
                json={"tenant_name": "Snajp Hjälp", "slug": get_settings().hjalp_tenant_slug, "kraver_avtal": False},
            )
            h = {"X-API-Key": hjalp.json()["api_key"]}
            sessionen = f"{uuid.uuid4()}@session.snajp.se"
            for adress in (sessionen, "anna@kund.se", f"{ANNA}@kund.snajp.se.evil.se"):
                svar = await c.post("/api/hjalp/samtal", headers=h, json={"customer_email": adress})
                assert svar.status_code == 422, adress
            ok = await c.post("/api/hjalp/samtal", headers=h, json={"customer_email": f"{ANNA}@KUND.snajp.se"})
            assert ok.status_code == 200
            assert ok.json() == {"overlamnad": False, "meddelanden": []}

            # Den anonyma vägen läser aldrig en inloggad kunds hjälpsamtal,
            # inte ens med hjälpens egen nyckel.
            for nyckel in (h, DEMO):
                svar = await c.post(
                    "/api/chat/samtal", headers=nyckel, json={"customer_email": f"{ANNA}@kund.snajp.se"}
                )
                assert svar.status_code == 422
