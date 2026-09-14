"""Veckovis utfall för EN kund — underlaget till arbetsytans analysvy.

## Varför endpointen finns

`/dashboard/analytics` renderade `analyticsSeries` ur `lib/mock-data.ts` för
varje inloggad kund: v16-v21, 188 skick, 21 svar, 6 möten. Samma sex veckor
oavsett vem som loggade in, utan en rad som sa att talen var påhittade. En
tabell som är ifylld blir trodd, och den här var ifylld sedan start.

## Vad den INTE gör

Den fyller inte i luckor. Saknar en vecka trafik blir den en rad med nollor —
det är ett mätvärde. Saknas källan helt för ett tal blir det `coverage: false`
och frontenden ritar ett streck i stället för en siffra. Möten är det enda
sådana talet i dag; se ANALYTICS_COVERAGE i storage/base.py för varför.

Tenanten kommer ur `require_tenant`, alltså ur API-nyckeln, aldrig ur ett fält
i anropet. Samma regel som resten av kunddata-endpointsen.
"""

from fastapi import APIRouter, Depends, Query, Request

from .deps import require_tenant

router = APIRouter()


@router.get("/api/analytics/weekly")
async def weekly(
    request: Request,
    weeks: int = Query(default=8, ge=1, le=52),
    tenant: dict = Depends(require_tenant),
) -> dict:
    return await request.app.state.storage.weekly_analytics(
        tenant["tenant_id"], weeks=weeks
    )
