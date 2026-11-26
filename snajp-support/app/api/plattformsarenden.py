"""Plattformsärendena: kundens felrapporter ur Hjälprutan (migration 156).

Plan: docs/PLAN-HJALPRUTAN-2026-11-25.md, del 5.

Varje väg här kräver HJÄLPENS nyckel (`hjalp.require_hjalp_tenant`); en annan
tenants nyckel får 404. Next-servern anropar efter att ha byggt identiteten ur
sessionen: rapportör, arbetsyta, kund, vy, roll och besöket kommer därifrån,
aldrig ur klientens kropp. Det här lagret litar alltså på Next för VEM, men
filtrerar själv på rapportören i varje läsning och skrivning, så att en
felaktig eller förfalskad parameter bara kan nå den rapportörens egna ärenden.

Felrapporten går ett eget flöde och inte genom agentens eskalering: en
eskalering tystar chatten, och kunden ska kunna fortsätta fråga medan felet
rättas.

Kunden ser bara händelser märkta `synlig_for_kund`. Adminvyn
(admin_plattformsarenden.py) ser allt.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from ..notifications.prioriterat_mejl import skicka_felrapport
from ..storage.base import PLATTFORMSARENDE_VANTAR_PA_KUND
from .chat import MAX_ATTACHMENT_BYTES
from .deps import kraev_uuid
from .hjalp import require_hjalp_tenant
from .schemas import (
    PlattformsarendeRequest,
    PlattformsarendeSvarRequest,
    PlattformsarendeUtslagRequest,
)

router = APIRouter()
logger = logging.getLogger("snajp-support.plattformsarenden")

#: Mejlen om nya rapporter körs efter svaret, så att kunden får sitt nummer
#: direkt även när mejlvägen är långsam. Referenserna håller uppgifterna vid
#: liv (asyncio.create_task är svag).
_pagaende: set[asyncio.Task] = set()


# -- Formerna ut ---------------------------------------------------------------


def kundvy(arende: dict[str, Any]) -> dict[str, Any]:
    """Det rapportören ser: läget, sitt eget första fält och de händelser som
    är märkta för kunden. Inga interna anteckningar, ingen aktör."""
    return {
        "id": arende["id"],
        "nummer": arende["nummer"],
        "status": arende["status"],
        "sida": arende["sida"],
        "gjorde": arende["gjorde"],
        "created_at": arende["created_at"],
        "updated_at": arende["updated_at"],
        "vantar_pa_kund": arende["status"] in PLATTFORMSARENDE_VANTAR_PA_KUND,
        "testversion_url": arende.get("testversion_url"),
        "handelser": [
            {"tid": h["tid"], "typ": h["typ"], "status": h.get("status"), "meddelande": h.get("meddelande")}
            for h in arende.get("handelser") or []
            if h.get("synlig_for_kund")
        ],
    }


def adminvy(arende: dict[str, Any]) -> dict[str, Any]:
    """Plattformsadminens vy: allt i kundvyn, hela kontexten och alla
    händelser. Bilden själv följer inte med, bara att den finns."""
    vy = kundvy(arende)
    vy.update(
        {
            "rapportor_user_id": arende["rapportor_user_id"],
            "rapportor_namn": arende.get("rapportor_namn"),
            "kund_workspace_id": arende["kund_workspace_id"],
            "kund_tenant_slug": arende["kund_tenant_slug"],
            "vy": arende["vy"],
            "roll": arende["roll"],
            "besok_av_admin": bool(arende.get("besok_av_admin")),
            "hande": arende["hande"],
            "vantade": arende.get("vantade") or "",
            "har_bild": bool(arende.get("har_bild")),
            "handelser": [
                {
                    "tid": h["tid"],
                    "typ": h["typ"],
                    "status": h.get("status"),
                    "meddelande": h.get("meddelande"),
                    "synlig_for_kund": bool(h.get("synlig_for_kund")),
                    "aktor": h.get("aktor"),
                }
                for h in arende.get("handelser") or []
            ],
        }
    )
    return vy


# -- Kontrollerna --------------------------------------------------------------


#: De bildformat en felrapport får bära. Samma mönster som adminytans
#: bildläsning (admin_plattformsarenden.BILD).
_BILDFORMAT = re.compile(r"data:image/(?:png|jpeg|webp|gif);base64,[A-Za-z0-9+/=]+")


def _validera_bild(bild: str | None) -> str | None:
    """Samma kontroll som chattens bilagor (chat._validate_attachments)."""
    if bild is None or not bild.strip():
        return None
    if not bild.startswith("data:image/"):
        raise HTTPException(status_code=422, detail="Endast bilder (data:image/...) stöds.")
    if len(bild) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=422, detail="Bilden är för stor (max ~4 MB).")
    # Samma fyra format som Next-lagret släpper in (lib/snajp/hjalp.ts:renBild)
    # och som adminytans bildläsning lämnar ut. En SVG kan bära skript och
    # ska inte ens lagras (granskningen 2026-11-25).
    if not _BILDFORMAT.fullmatch(bild):
        raise HTTPException(status_code=422, detail="Bilden måste vara PNG, JPEG, WebP eller GIF.")
    return bild


def _rapportor(varde: str) -> str:
    """Rapportörens id ur frågesträngen eller kroppen. Ett id som inte är ett
    uuid kan inte äga något ärende: 422, så att Next-felet syns i loggen."""
    from uuid import UUID

    try:
        return str(UUID(varde))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=422, detail="rapportor måste vara ett uuid.") from None


async def _forklara_nej(storage, arende_id: str, rapportor: str) -> HTTPException:
    """Varför en villkorad ändring inte gick igenom: 404 för ett ärende som
    inte finns eller inte är rapportörens (de ska inte gå att skilja åt), 409
    när ärendet är hans men står i fel läge."""
    arende = await storage.hamta_plattformsarende(arende_id)
    if not arende or arende["rapportor_user_id"] != rapportor:
        return HTTPException(status_code=404, detail="Ärendet finns inte.")
    return HTTPException(status_code=409, detail="Ärendet står inte i det läget längre.")


async def _mejla_ny_rapport(nummer: str, arende_id: str, tenant_id: str) -> None:
    try:
        await skicka_felrapport(nummer=nummer, arende_id=arende_id, tenant_id=tenant_id)
    except Exception:  # noqa: BLE001 — mejlet får aldrig fälla ärendet
        logger.warning("Mejlet om felrapport %s kunde inte skickas.", nummer, exc_info=True)


# -- Vägarna -------------------------------------------------------------------


@router.post("/api/plattformsarenden", status_code=201)
async def skapa_arende(
    request: Request, payload: PlattformsarendeRequest, tenant: dict = Depends(require_hjalp_tenant)
) -> dict:
    """Sparar felrapporten och kvitterar med ett nummer. Mejlet till Snajp
    går efter svaret och bär bara numret och en länk."""
    falt = payload.model_dump()
    falt["bild"] = _validera_bild(payload.bild)
    arende = await request.app.state.storage.skapa_plattformsarende(falt)
    uppgift = asyncio.create_task(_mejla_ny_rapport(arende["nummer"], arende["id"], tenant["tenant_id"]))
    _pagaende.add(uppgift)
    uppgift.add_done_callback(_pagaende.discard)
    return {
        "id": arende["id"],
        "nummer": arende["nummer"],
        "status": arende["status"],
        "created_at": arende["created_at"],
    }


@router.get("/api/plattformsarenden")
async def lista_arenden(
    request: Request, rapportor: str, tenant: dict = Depends(require_hjalp_tenant)
) -> dict:
    """Rapportörens egna ärenden, nyast först. Filtret sitter här och i
    lagringens fråga; en annan användare i samma arbetsyta ser ingenting."""
    arenden = await request.app.state.storage.list_plattformsarenden(rapportor_user_id=_rapportor(rapportor))
    return {"arenden": [kundvy(a) for a in arenden]}


@router.post("/api/plattformsarenden/{arende_id}/svar")
async def svara_pa_arende(
    request: Request,
    arende_id: str,
    payload: PlattformsarendeSvarRequest,
    tenant: dict = Depends(require_hjalp_tenant),
) -> dict:
    """Kundens svar när Snajp behöver mer. Bara i läget behover_mer; ärendet
    går tillbaka till undersoks med svaret som händelse."""
    kraev_uuid(arende_id, "Ärendet")
    rapportor = _rapportor(payload.rapportor_user_id)
    storage = request.app.state.storage
    arende = await storage.andra_plattformsarende(
        arende_id,
        status="undersoks",
        kraver_status=("behover_mer",),
        rapportor_user_id=rapportor,
        handelse={"typ": "kundsvar", "meddelande": payload.text.strip(), "synlig_for_kund": True, "aktor": "kund"},
    )
    if arende is None:
        raise await _forklara_nej(storage, arende_id, rapportor)
    return kundvy(arende)


@router.post("/api/plattformsarenden/{arende_id}/utslag")
async def utslag_pa_arende(
    request: Request,
    arende_id: str,
    payload: PlattformsarendeUtslagRequest,
    tenant: dict = Depends(require_hjalp_tenant),
) -> dict:
    """Kundens svar på "Fungerade det?". Bara i läget redo_att_testa. Ja ger
    kund_godkand (information, aldrig ett godkännande som släpper något), nej
    ger rattning_pagar med kommentaren som händelse och samma nummer."""
    kraev_uuid(arende_id, "Ärendet")
    rapportor = _rapportor(payload.rapportor_user_id)
    kommentar = (payload.kommentar or "").strip() or None
    storage = request.app.state.storage
    arende = await storage.andra_plattformsarende(
        arende_id,
        status="kund_godkand" if payload.fungerar else "rattning_pagar",
        kraver_status=("redo_att_testa",),
        rapportor_user_id=rapportor,
        handelse={"typ": "utslag", "meddelande": kommentar, "synlig_for_kund": True, "aktor": "kund"},
    )
    if arende is None:
        raise await _forklara_nej(storage, arende_id, rapportor)
    return kundvy(arende)
