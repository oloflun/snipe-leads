"""Support-agentens regler per kund: GET/PUT /api/support/config.

Tenant-skopat. Samma mönster som /api/leads/config: läsningen normaliserar
tolerant, skrivningen är strikt (pydantic) och slår ihop fältvis så att ett
formulär inte nollar ett annat. Värdena bor i agent_configs.settings för
agent_type "support" — se app/agent/support_regler.py för vad de betyder.
"""

from fastapi import APIRouter, Depends, Request

from ..agent import support_regler
from ..cache import versioner
from .deps import require_tenant
from .schemas import SupportConfigRequest

router = APIRouter()


def _svar(installningar: support_regler.SupportInstallningar) -> dict:
    return {
        **installningar,
        # Valen att välja MELLAN, så att ett formulär kan renderas utan en
        # egen kopia av listorna — två kopior driver isär.
        "options": {
            "tonlage": list(support_regler.TONLAGEN),
            "faktakontroll": list(support_regler.FAKTAKONTROLL),
            "utanfor_amnet": list(support_regler.UTANFOR_AMNET_VAL),
            "max_misslyckade_tak": support_regler.MAX_MISSLYCKADE_TAK,
            "amnesomrade_tak": support_regler.AMNESOMRADE_TAK,
        },
        "orsaker": support_regler.ORSAKER,
    }


@router.get("/api/support/config")
async def get_support_config(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    settings = await request.app.state.storage.get_agent_settings(
        tenant["tenant_id"], agent_type="support"
    )
    return _svar(support_regler.normalisera(settings))


@router.put("/api/support/config")
async def put_support_config(
    request: Request, payload: SupportConfigRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    storage = request.app.state.storage
    current = await storage.get_agent_settings(tenant["tenant_id"], agent_type="support")
    merged = dict(current)
    if payload.eskalering is not None:
        merged["eskalering"] = support_regler.normalisera_eskalering(
            {
                **support_regler.normalisera_eskalering(current.get("eskalering")),
                **payload.eskalering.model_dump(exclude_none=True),
            }
        )
    for falt in ("tonlage", "faktakontroll", "amnesomrade"):
        varde = getattr(payload, falt)
        if varde is not None:
            merged[falt] = varde.strip() if isinstance(varde, str) else varde

    saved = await storage.set_agent_settings(
        tenant["tenant_id"], agent_type="support", settings=merged
    )
    # Svarscachen (INV-CACHE-001) nycklar på konfigversionen: ett nytt
    # tonläge eller en ny faktakontroll gör varje cachat svar inaktuellt.
    await versioner.bumpa_config(tenant["tenant_id"])
    return _svar(support_regler.normalisera(saved))
