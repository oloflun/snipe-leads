"""Driftens smala läsväg: vilka migrationer databasen har kört.

docs/compliance/synkflytt-plan.md steg 9 (runbookens steg 10). PR-kontrollen
"releasens migrationer" i .github/workflows/migrera.yml läste förut båda
databasernas liggare över deras publika portar, med superanvändarens lösenord
i GitHub. Den här endpointen ersätter det: GitHub frågar api:t över HTTPS och
får bara migrationernas versioner, inga rader, ingen persondata, och ingen
väg att skriva.

Nyckeln `SCHEMA_LASNYCKEL` är egen och smal (inte masternyckeln): den öppnar
bara den här listan. Utan nyckel i miljön är vägen stängd (404), så att en
miljö där ägaren inte satt den inte svarar alls.
"""
from __future__ import annotations

import hmac

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import get_settings

router = APIRouter(prefix="/api/drift")

NYCKELHUVUD = "X-Schema-Nyckel"


@router.get("/schema")
async def schema(request: Request, x_schema_nyckel: str | None = Header(default=None, alias=NYCKELHUVUD)) -> dict:
    """Migrationsliggarens versioner, sorterade. 404 när nyckeln inte är satt i
    miljön, 401 vid fel eller saknad nyckel."""
    nyckel = get_settings().schema_lasnyckel
    if not nyckel:
        raise HTTPException(status_code=404, detail="Not Found")
    if not x_schema_nyckel or not hmac.compare_digest(
        nyckel.encode("utf-8"), x_schema_nyckel.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Ogiltig nyckel.")
    versioner = await request.app.state.storage.schema_versioner()
    return {"miljo": get_settings().aktiv_miljo() or "", "versioner": sorted(versioner)}
