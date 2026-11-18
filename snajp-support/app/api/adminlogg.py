"""Åtkomstloggen för master-nyckeln (migration 123, `audit_logs`).

## Varför på ETT ställe

Varje anrop som bär master-nyckeln passerar `deps.require_master_key`, och
det är därifrån `logga_masteranrop` anropas. En logg per endpoint hade
glömts den dag nästa admin-endpoint skrevs; nu är det beroendet som loggar,
och INV-SEC-013 (tests/invariants/test_inv_sec_013.py) fäller en
admin-endpoint som inte går genom det.

## Vad som skrivs

Vem: plattformsadminens användar-id när Next-appen skickat det i
`X-Snajp-Admin` (sätts ur sessionen i app/api/snajp-support/_lib.ts, aldrig
av klienten). Databasfunktionen godtar id:t bara om det står i
`platform_admins`; annars blir raden "master-nyckel" utan person. Ett
förfalskat id kan alltså inte ge en falsk admin, och rubriken ger ingen
behörighet: den läses först EFTER att master-nyckeln godkänts.

När, åtgärd (läsning eller ändring ur HTTP-metoden), kund (`tenant_id` ur
sökvägen eller frågesträngen) och resurs (ruttens MALL och ett id ur
sökvägen). Aldrig frågesträngen, kroppen, svaret eller nyckeln.

## Om skrivningen faller

Anropet går igenom och felet loggas. Att låsa adminytan för att loggtabellen
inte svarar hade gjort en databasstörning till ett driftstopp för den som
ska åtgärda störningen; att det hänt syns i api:ts logg som en varning med
anropets id.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import Request

from ..sparning import anrops_id

logger = logging.getLogger("snajp-support.adminlogg")

#: Rubriken Next-appen sätter med plattformsadminens användar-id.
ADMIN_RUBRIK = "x-snajp-admin"


def _uuid(varde: object) -> str | None:
    if not isinstance(varde, str) or not varde:
        return None
    try:
        return str(UUID(varde))
    except ValueError:
        return None


def beskriv_anrop(request: Request) -> dict:
    """Det som loggas om ett anrop, och inget mer. Ren funktion av anropet."""
    route = request.scope.get("route")
    resurs = getattr(route, "path", None) or request.url.path
    params = dict(request.path_params or {})
    tenant = _uuid(params.get("tenant_id")) or _uuid(request.query_params.get("tenant_id"))
    entity = None
    for namn, varde in params.items():
        if namn != "tenant_id" and _uuid(varde):
            entity = _uuid(varde)
            break
    return {
        "kanal": "master",
        "admin_user_id": _uuid(request.headers.get(ADMIN_RUBRIK)),
        "tenant_id": tenant,
        "metod": request.method,
        "resurs": resurs,
        "entity_id": entity,
        "request_id": anrops_id(),
    }


async def logga_masteranrop(request: Request) -> None:
    """En rad i audit_logs. Kastar aldrig (se modulens docstring)."""
    try:
        rad = beskriv_anrop(request)
        await request.app.state.storage.logga_adminatkomst(**rad)
    except Exception:  # noqa: BLE001 — loggen får aldrig fälla adminanropet
        logger.warning(
            "Åtkomstloggen kunde inte skrivas för %s %s (anrop %s).",
            request.method,
            getattr(request.scope.get("route"), "path", "?"),
            anrops_id(),
            exc_info=True,
        )
