"""Plattformsadminens sida av felrapporterna ur Hjälprutan (migration 156).

Plan: docs/PLAN-HJALPRUTAN-2026-11-25.md, del 5. Listan visas i adminytans
`FelOchEskaleringar` genom den befintliga adminproxyn
(app/api/admin/[...path]/route.ts).

Samma grind som övriga /api/admin-vägar: `require_master_key` på routern, och
därmed åtkomstloggen (adminlogg.py, INV-SEC-013).

Varje statusbyte skrivs som en händelse. Statusen själv är ett av kundens
lägen och syns för kunden; `meddelande_till_kund` står i samma händelse. stangd
och behover_mer kräver ett meddelande: kunden ska få veta varför ärendet
stängdes och vad Snajp behöver.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from .adminlogg import ADMIN_RUBRIK, _uuid
from .deps import kraev_uuid, require_master_key
from .plattformsarenden import adminvy
from .schemas import PlattformsarendeStatus, PlattformsarendeStatusRequest

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_master_key)])

#: Lägena som kräver ett meddelande till kunden.
KRAVER_MEDDELANDE = ("stangd", "behover_mer")

#: Lägena där testversionen inte längre finns (planens del 7: den töms efter
#: kundens svar eller när rättningen nått produktionen).
UTAN_TESTVERSION = ("i_main", "stangd")

#: Bildformaten inlämningen släpper igenom (lib/snajp/hjalp.ts:renBild, samma
#: mönster). Bara de lämnas ut: en lagrad rad med en annan typ, till exempel
#: SVG som kan bära skript, visas aldrig i adminytan.
BILD = re.compile(r"data:image/(?:png|jpeg|webp|gif);base64,[A-Za-z0-9+/=]+")

#: Bilden kan visa kunddata: den får inte sparas av en mellanhand eller
#: webbläsaren, och typen ska inte gissas om.
BILDHUVUDEN = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}


@router.get("/plattformsarenden")
async def lista_plattformsarenden(
    request: Request, status: PlattformsarendeStatus | None = None
) -> dict:
    arenden = await request.app.state.storage.list_plattformsarenden(status=status)
    return {"arenden": [adminvy(a) for a in arenden]}


@router.get("/plattformsarenden/{arende_id}/bild")
async def hamta_bild(request: Request, arende_id: str) -> JSONResponse:
    """Kundens bild till ett ärende, på adminens begäran och aldrig i listan.

    Svaret är JSON med bilden som data-URL, eftersom adminproxyn läser
    backendens svar som JSON. Åtkomstloggen skriver en rad utan innehåll
    (routerns `require_master_key`, INV-SEC-013); bilden loggas inte här."""
    kraev_uuid(arende_id, "Ärendet")
    bild = await request.app.state.storage.hamta_plattformsarende_bild(arende_id)
    if not bild:
        raise HTTPException(status_code=404, detail="Ärendet har ingen bild.", headers=BILDHUVUDEN)
    if not BILD.fullmatch(bild):
        raise HTTPException(status_code=415, detail="Bilden har ett format som inte visas.", headers=BILDHUVUDEN)
    return JSONResponse({"bild": bild}, headers=BILDHUVUDEN)


@router.post("/plattformsarenden/{arende_id}/status")
async def byt_status(request: Request, arende_id: str, payload: PlattformsarendeStatusRequest) -> dict:
    kraev_uuid(arende_id, "Ärendet")
    meddelande = (payload.meddelande_till_kund or "").strip() or None
    if payload.status in KRAVER_MEDDELANDE and not meddelande:
        raise HTTPException(
            status_code=422, detail="Skriv ett meddelande till kunden när ärendet stängs eller behöver mer."
        )
    admin = _uuid(request.headers.get(ADMIN_RUBRIK))
    satt_testversion = payload.testversion_url is not None or payload.status in UTAN_TESTVERSION
    arende = await request.app.state.storage.andra_plattformsarende(
        arende_id,
        status=payload.status,
        handelse={
            "typ": "status",
            "meddelande": meddelande,
            "synlig_for_kund": True,
            "aktor": f"admin:{admin}" if admin else "plattformsadmin",
        },
        testversion_url=None if payload.status in UTAN_TESTVERSION else payload.testversion_url,
        satt_testversion=satt_testversion,
    )
    if arende is None:
        raise HTTPException(status_code=404, detail="Ärendet finns inte.")
    return adminvy(arende)
