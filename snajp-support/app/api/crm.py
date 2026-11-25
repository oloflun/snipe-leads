"""Snajp CRM: den interna ytan som bara appen når (/api/crm).

Det publika, versionerade API:t ligger i app/api/crm_v1.py. Här ligger det som
inte hör hemma i en extern integration: att skapa och dra in de nycklar en
integration använder, och översikten appen visar.

Allt här står bakom `require_tenant`, som avvisar nycklar med omfång. En
CRM-nyckel kan alltså inte skapa en ny nyckel åt sig själv.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..crm import lagring, nycklar
from .crm_v1 import korning_ut
from .deps import kraev_uuid, require_tenant

router = APIRouter(prefix="/api/crm")

Omfang = Literal["crm:las", "crm:skriv", "crm:synk", "crm:admin"]


class NyNyckel(BaseModel):
    namn: str = Field(min_length=1, max_length=80)
    omfang: list[Omfang] = Field(min_length=1)


@router.get("/nycklar")
async def lista_nycklar(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    return {"nycklar": await nycklar.lista(request.app.state.storage, tenant["tenant_id"])}


@router.post("/nycklar", status_code=201)
async def skapa_nyckel(request: Request, kropp: NyNyckel, tenant: dict = Depends(require_tenant)) -> dict:
    """Svaret bär nyckeln i klartext, en enda gång."""
    return await nycklar.skapa(request.app.state.storage, tenant["tenant_id"], tenant_namn=tenant["tenant_name"],
                               namn=kropp.namn.strip(), omfang=list(kropp.omfang))


@router.delete("/nycklar/{nyckel_id}", status_code=204)
async def aterkalla_nyckel(request: Request, nyckel_id: str, tenant: dict = Depends(require_tenant)) -> None:
    if not await nycklar.aterkalla(request.app.state.storage, tenant["tenant_id"], kraev_uuid(nyckel_id, "Nyckeln")):
        raise HTTPException(status_code=404, detail="Nyckeln finns inte.")


@router.get("/oversikt")
async def oversikt(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    """Det appen visar överst: hur många bolag och personer som finns, och de
    senaste synkkörningarna med utfall."""
    storage, tenant_id = request.app.state.storage, tenant["tenant_id"]
    return {
        "bolag": await lagring.rakna_poster(storage, tenant_id, "bolag"),
        "personer": (await lagring.rakna_poster(storage, tenant_id, "person"))["alla"],
        "anslutningar": len(await lagring.lista_anslutningar(storage, tenant_id)),
        "korningar": [korning_ut(k) for k in await lagring.lista_korningar(storage, tenant_id, limit=10)],
    }
