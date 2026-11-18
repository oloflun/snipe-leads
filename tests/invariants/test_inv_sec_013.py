"""INV-SEC-013 — Varje admin- och master-endpoint skriver i åtkomstloggen.

Loggen skrivs på ett ställe: `deps.require_master_key` anropar
`adminlogg.logga_masteranrop`, som skriver en rad i `audit_logs` (migration
123). Testet fäller därför på två sätt:

1. **Strukturen.** Varje route under `/api/admin` och `/api/keys` i den
   riktiga appen har `require_master_key` i sitt beroendeträd. En ny
   admin-endpoint som får en egen grind, eller ingen, fäller här i stället för
   att tyst gå ologgad. Undantaget är flyttmottagningen, som saknar
   master-nyckel med flit (HMAC mellan miljöerna); flytten startas av
   `/api/admin/flytt/skicka`, som loggas.
2. **Beteendet.** Ett riktigt anrop med master-nyckeln mot minneslagret ger
   en rad med vem, åtgärd, kund och ruttens mall, och raden bär varken
   frågesträngen eller nyckeln.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "snajp-support"))

from fastapi.routing import APIRoute  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.api.deps import require_master_key  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402

#: Admin-vägar UTAN master-nyckel, med skäl. Allt annat ska loggas.
UNDANTAG = {
    ("POST", "/api/admin/flytt/importera"): "HMAC-signerat paket mellan miljöerna; "
    "flytten startas och loggas av /api/admin/flytt/skicka.",
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
    """Varje route med path, methods och dependant. FastAPI 0.139 lägger
    inkluderade routrar som `_IncludedRouter`, vars routes (med routerns
    prefix och beroenden) nås genom `effective_route_contexts()`."""
    ut = []
    for r in app.routes:
        if isinstance(r, APIRoute):
            ut.append(r)
        elif hasattr(r, "effective_route_contexts"):
            ut.extend(c for c in r.effective_route_contexts() if hasattr(c, "dependant"))
    return ut


def _adminroutes() -> list:
    return [
        r
        for r in _alla_routes()
        if r.path.startswith("/api/admin") or r.path == "/api/keys"
    ]


def test_det_finns_adminroutes_att_prova():
    # Ett tomt urval hade gjort resten av testet meningslöst grönt.
    assert len(_adminroutes()) >= 20


def test_varje_adminroute_gar_genom_require_master_key():
    saknar = []
    for route in _adminroutes():
        for metod in route.methods:
            if (metod, route.path) in UNDANTAG:
                continue
            if require_master_key not in _beroenden(route.dependant):
                saknar.append(f"{metod} {route.path}")
    assert not saknar, (
        "De här admin-endpointsen går inte genom require_master_key och skriver "
        "därför ingen rad i åtkomstloggen (audit_logs, INV-SEC-013): "
        + ", ".join(sorted(saknar))
    )


def test_require_master_key_anropar_loggen():
    kalla = (ROOT / "snajp-support" / "app" / "api" / "deps.py").read_text(encoding="utf-8")
    kropp = kalla.split("async def require_master_key", 1)[1].split("\nasync def ", 1)[0]
    assert "logga_masteranrop(request)" in kropp


@pytest.mark.anyio
async def test_ett_masteranrop_ger_en_rad_utan_innehall():
    master = get_settings().snajp_master_api_key
    tenant = str(uuid.uuid4())
    admin = str(uuid.uuid4())
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        fore = len(storage.adminlogg)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as klient:
            await klient.get(
                f"/api/admin/tenants/{tenant}/runs?hemlig=fragestrang",
                headers={"X-API-Key": master, "X-Snajp-Admin": admin},
            )
            # Utan master-nyckel: ingen rad (anropet nekas före loggen).
            await klient.get(f"/api/admin/tenants/{tenant}/runs")
        rader = storage.adminlogg[fore:]

    assert len(rader) == 1, rader
    rad = rader[0]
    assert rad["kanal"] == "master"
    assert rad["admin_user_id"] == admin
    assert rad["tenant_id"] == tenant
    assert rad["metod"] == "GET"
    assert rad["resurs"] == "/api/admin/tenants/{tenant_id}/runs"
    allt = repr(rad)
    assert "hemlig" not in allt and "fragestrang" not in allt
    assert master not in allt
