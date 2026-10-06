"""GET /api/support/oversikt — Kundtjänst › Översikt för EN kund.

Talen räknas i `app/support_oversikt.py`; den här filen hämtar bara
underlaget. Tenanten kommer ur API-nyckeln (`require_tenant`), aldrig ur
anropet. Testmail räknas med samma regel som Ärenden (`/api/inbox`):
test- och demokonton ser dem, riktiga kunder gör det inte.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request

from ..support_oversikt import bygg_oversikt, underlagets_start
from .deps import require_tenant
from .inbox import _visar_test_i_arenden

router = APIRouter()


@router.get("/api/support/oversikt")
async def support_oversikt(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    storage = request.app.state.storage
    tid = tenant["tenant_id"]
    nu = datetime.now(timezone.utc)
    is_test = None if await _visar_test_i_arenden(storage, tenant) else False
    underlag = await storage.support_oversikt_underlag(
        tid, sedan=underlagets_start(nu).isoformat(), is_test=is_test
    )
    forslag = await storage.list_agent_suggestions(tid, status="ny", limit=200)
    return bygg_oversikt(underlag, forslag, nu=nu)
