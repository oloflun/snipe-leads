"""Snajp CRM API v1: affärer, uppgifter, anteckningar, aktiviteter och bilagor.

Ändpunkterna för de fem objekten från migration 164, på en egen router som
`crm_v1.router` tar med sig sist. Samma kontrakt som resten av API:t: engelska
fältnamn, `kraev(omfang)` på varje väg (omfång, tillägget och taket),
avtalsgrinden på varje skrivning, `Idempotency-Key` på varje POST och samma
felformat. Reglerna bor i `app/crm/objekt.py`; här översätts bara fälten.

Bilagor laddas upp som multipart och laddas ned som en fil, aldrig inuti
JSON. Storleken prövas medan kroppen läses: en för stor kropp avvisas innan
den ligger i minnet.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import Field
from starlette.datastructures import UploadFile

from ..crm import falt, handelser, lagring, objekt
from .crm_v1 import (
    _FALT_UT, _PERMANENT, _Kropp, _avtal, _idempotent, _toms, _ursprung, fel, handelse_ut, kraev,
)
from .deps import kraev_uuid

#: Samma prefix och etikett som crm_v1.router, som tar över vägarna.
router = APIRouter(prefix="/api/crm/v1", tags=["Snajp CRM"])

# -- Fältnamnen ut och in ----------------------------------------------------

_KOPPLING = {"company_id": "bolag_id", "person_id": "person_id", "deal_id": "affar_id"}
_STEG = {"name": "namn", "probability": "sannolikhet", "type": "typ", "color": "farg"}
_AFFAR = {"name": "namn", "company_id": "bolag_id", "person_id": "person_id", "stage_id": "steg_id",
          "amount": "belopp", "currency": "valuta", "probability": "sannolikhet",
          "expected_close_date": "forvantat_avslut", "lost_reason": "forlustorsak",
          "lost_reason_code": "forlustorsak_kod", "owner": "ansvarig", "custom": "extra"}
_UPPGIFT = {"title": "titel", "description": "beskrivning", "status": "status", "due_at": "forfaller_at",
            "owner": "ansvarig", **_KOPPLING}
_ANTECKNING = {"title": "titel", "body": "text", "pinned": "fast", "author": "forfattare", **_KOPPLING}
_AKTIVITET = {"type": "typ", "subject": "rubrik", "body": "text", "occurred_at": "tid",
              "duration_minutes": "varaktighet_min", "outcome": "utfall", "owner": "ansvarig", **_KOPPLING}
_BILAGA = {"filename": "filnamn", "content_type": "typ", "size": "storlek", "uploaded_by": "uppladdad_av",
           "note_id": "anteckning_id", **_KOPPLING}
_KARTA = {"affar": _AFFAR, "uppgift": _UPPGIFT, "anteckning": _ANTECKNING, "aktivitet": _AKTIVITET}

_STEGTYP_UT = {"oppen": "open", "vunnen": "won", "forlorad": "lost"}
_STATUS_UT = {"att_gora": "todo", "pagar": "in_progress", "klar": "done"}
_AKTIVITET_UT = {"samtal": "call", "mote": "meeting", "mejl": "email", "besok": "visit", "ovrigt": "other"}
#: Värden som översätts in, per CRM-fält.
_VARDEN_IN = {"typ": {**{v: k for k, v in _STEGTYP_UT.items()}, **{v: k for k, v in _AKTIVITET_UT.items()}},
              "status": {v: k for k, v in _STATUS_UT.items()},
              "forlustorsak_kod": {v: k for k, v in objekt.FORLUSTORSAKER.items()}}
ForlustorsakKod = Literal["price", "competitor", "timing", "no_need", "no_budget", "no_response", "other"]

# Händelseloggen och historiken visar de nya fälten med API:ts namn. "typ" är
# en aktivitets `type`; en bilaga ändras aldrig fält för fält.
_FALT_UT.update({sv: en for karta in (_AFFAR, _UPPGIFT, _ANTECKNING, _AKTIVITET) for en, sv in karta.items()})
_FALT_UT.update({"position": "position", "avslutad_at": "closed_at", "klar_at": "completed_at",
                 "anteckning_id": "note_id"})


def _tider(rad: dict[str, Any]) -> dict[str, Any]:
    return {"source": rad.get("kalla"), "created_at": rad.get("created_at"), "updated_at": rad.get("updated_at"),
            "deleted_at": rad.get("raderad_at"), "purge_at": _toms(rad)}


def _kopplingar(rad: dict[str, Any]) -> dict[str, Any]:
    return {en: rad.get(sv) for en, sv in _KOPPLING.items()}


def steg_ut(rad: dict[str, Any]) -> dict[str, Any]:
    return {"id": rad["id"], "name": rad["namn"], "position": rad["position"], "probability": rad["sannolikhet"],
            "type": _STEGTYP_UT.get(rad["typ"], "open"), "color": rad.get("farg"),
            "created_at": rad.get("created_at"), "updated_at": rad.get("updated_at")}


def affar_ut(rad: dict[str, Any]) -> dict[str, Any]:
    return {"id": rad["id"], "name": rad.get("namn"), "company_id": rad.get("bolag_id"),
            "person_id": rad.get("person_id"), "stage_id": rad.get("steg_id"), "amount": rad.get("belopp"),
            "currency": rad.get("valuta"), "probability": rad.get("sannolikhet"),
            "expected_close_date": rad.get("forvantat_avslut"), "closed_at": rad.get("avslutad_at"),
            "lost_reason": rad.get("forlustorsak"),
            "lost_reason_code": objekt.FORLUSTORSAKER.get(rad.get("forlustorsak_kod") or ""),
            "owner": rad.get("ansvarig"), "position": rad.get("position"),
            "custom": rad.get("extra") or {}, **_tider(rad)}


def uppgift_ut(rad: dict[str, Any]) -> dict[str, Any]:
    return {"id": rad["id"], "title": rad.get("titel"), "description": rad.get("beskrivning"),
            "status": _STATUS_UT.get(rad.get("status"), "todo"), "due_at": rad.get("forfaller_at"),
            "completed_at": rad.get("klar_at"), "owner": rad.get("ansvarig"), **_kopplingar(rad), **_tider(rad)}


def anteckning_ut(rad: dict[str, Any]) -> dict[str, Any]:
    return {"id": rad["id"], "title": rad.get("titel"), "body": rad.get("text") or "",
            "pinned": bool(rad.get("fast")), "author": rad.get("forfattare"), **_kopplingar(rad), **_tider(rad)}


def aktivitet_ut(rad: dict[str, Any]) -> dict[str, Any]:
    return {"id": rad["id"], "type": _AKTIVITET_UT.get(rad.get("typ"), "other"), "subject": rad.get("rubrik"),
            "body": rad.get("text"), "occurred_at": rad.get("tid"), "duration_minutes": rad.get("varaktighet_min"),
            "outcome": rad.get("utfall"), "owner": rad.get("ansvarig"), **_kopplingar(rad), **_tider(rad)}


def bilaga_ut(rad: dict[str, Any]) -> dict[str, Any]:
    """Metadata, aldrig innehållet: det hämtas från `content_url`."""
    return {"id": rad["id"], "filename": rad.get("filnamn"), "content_type": rad.get("typ"),
            "size": rad.get("storlek"), "uploaded_by": rad.get("uppladdad_av"), **_kopplingar(rad),
            "note_id": rad.get("anteckning_id"),
            "content_url": f"/api/crm/v1/attachments/{rad['id']}/content", **_tider(rad)}


_UT = {"affar": affar_ut, "uppgift": uppgift_ut, "anteckning": anteckning_ut, "aktivitet": aktivitet_ut,
       "bilaga": bilaga_ut}
for _objekt, _form in _UT.items():
    handelser.registrera_form(_objekt, _form)


def _in(objekt_: str, data: dict[str, Any]) -> dict[str, Any]:
    """Anropets engelska fält till CRM:ets. Kroppen är redan prövad mot sin
    modell (`extra="forbid"`), så okända fält når aldrig hit."""
    karta = _KARTA[objekt_] if objekt_ in _KARTA else _STEG
    ut = {karta[en]: varde for en, varde in data.items() if en in karta}
    for sv, oversattning in _VARDEN_IN.items():
        if ut.get(sv) is not None:
            ut[sv] = oversattning.get(ut[sv], ut[sv])
    return ut


# -- Felen -------------------------------------------------------------------

#: Varje regel i app/crm/objekt.py som säger nej, som ett fel i API:ts form.
_FEL = {
    "target_required": lambda: fel(
        422, "target_required", "Link the record to at least one company, person or deal.",
        "Koppla posten till minst ett bolag, en person eller en affär."),
    "company_not_found": lambda: fel(
        422, "company_not_found", "company_id does not point at a company.", "company_id pekar inte på något bolag."),
    "person_not_found": lambda: fel(
        422, "person_not_found", "person_id does not point at a person.", "person_id pekar inte på någon person."),
    "deal_not_found": lambda: fel(
        422, "deal_not_found", "deal_id does not point at a deal.", "deal_id pekar inte på någon affär."),
    "note_not_found": lambda: fel(
        422, "note_not_found", "note_id does not point at a note.", "note_id pekar inte på någon anteckning."),
    "stage_not_found": lambda: fel(
        422, "stage_not_found", "stage_id does not point at a deal stage.", "stage_id pekar inte på något steg."),
    "stage_in_use": lambda: fel(
        409, "stage_in_use", "The stage has deals in it. Move them first.",
        "Steget har affärer i sig. Flytta dem först."),
    "stage_required": lambda: fel(
        409, "stage_required", "There must always be at least one open, one won and one lost stage.",
        "Det måste alltid finnas minst ett öppet, ett vunnet och ett förlorat steg."),
    "file_too_large": lambda: fel(
        413, "file_too_large", f"A file may be at most {objekt.MAX_BILAGA // (1024 * 1024)} MB.",
        f"En fil får vara högst {objekt.MAX_BILAGA // (1024 * 1024)} MB."),
    "storage_quota_exceeded": lambda: fel(
        409, "storage_quota_exceeded",
        f"The workspace has used its {objekt.MAX_BILAGOR_PER_KUND // (1024 * 1024)} MB for attachments. "
        "Deleted files count until the trash is emptied after 30 days: delete with permanent=true to make room.",
        f"Arbetsytan har använt sina {objekt.MAX_BILAGOR_PER_KUND // (1024 * 1024)} MB för bilagor. "
        "Raderade filer räknas tills papperskorgen töms efter 30 dagar: radera med permanent=true för att få plats."),
    "file_type_not_allowed": lambda: fel(
        422, "file_type_not_allowed",
        "The file type is not allowed. Accepted: pdf, png, jpeg, webp, gif, txt, csv, docx, xlsx, pptx.",
        "Filtypen tas inte emot. Tillåtna: pdf, png, jpeg, webp, gif, txt, csv, docx, xlsx, pptx."),
}


def _objektfel(orsak: objekt.ObjektFel, objekt_: str | None = None) -> HTTPException:
    if orsak.kod in _FEL:
        return _FEL[orsak.kod]()
    karta = {**_STEG, **{**_KARTA, "bilaga": _BILAGA}.get(objekt_ or "", {}), "before_id": "before_id",
             "after_id": "after_id", "ids": "ids"}
    tillbaka = {sv: en for en, sv in karta.items()}
    falten = [{"field": tillbaka.get(f["falt"], f["falt"]), "code": f["kod"]} for f in orsak.falt]
    return fel(422, "invalid_fields", "One or more fields could not be interpreted.",
               "Ett eller flera fält gick inte att tolka.", fields=falten)


def _finns_inte() -> HTTPException:
    return fel(404, "not_found", "The record does not exist.", "Posten finns inte.")


def _id(varde: str, vad: str) -> str:
    """Ett id ur sökvägen, i den form databasen lämnar ut (gemener)."""
    return str(uuid.UUID(kraev_uuid(varde, vad)))


# -- Kropparna ---------------------------------------------------------------

StegTyp = Literal["open", "won", "lost"]


class StageIn(_Kropp):
    name: str | None = Field(None, description="Unique per workspace, at most 60 characters. Required when creating.")
    probability: int | None = Field(None, ge=0, le=100, description="Default win probability in percent.")
    type: StegTyp | None = Field(None, description="`open`, `won` or `lost`. Defaults to `open`.")
    color: str | None = Field(None, description="A colour token name, free text.")


class ReorderIn(_Kropp):
    ids: list[str] = Field(description="Every stage id, each once, in the new order.")


class DealIn(_Kropp):
    name: str | None = Field(None, description="Required when creating.")
    company_id: str | None = None
    person_id: str | None = None
    stage_id: str | None = Field(None, description="Defaults to the first open stage. Changing it puts the deal last "
                                 "in the new stage; use POST /deals/{id}/move to place it.")
    amount: int | None = Field(None, ge=0, description="Whole units of `currency` (kronor for SEK).")
    currency: str | None = Field(None, description="ISO 4217. Defaults to SEK.")
    probability: int | None = Field(None, ge=0, le=100, description="Own win probability. `null` uses the stage's.")
    expected_close_date: str | None = Field(None, description="ISO 8601 date.")
    lost_reason: str | None = Field(None, description="Free text, at most 500 characters. The fallback beside "
                                    "`lost_reason_code`, and may be set with any code.")
    lost_reason_code: str | None = Field(
        None, description="Why the deal was lost, from a fixed list: `price`, `competitor`, `timing`, `no_need`, "
        "`no_budget`, `no_response` or `other`. Any other value is refused with `invalid_fields` "
        "(code `forlustorsak_okand`). `null` clears it.")
    owner: str | None = None
    custom: dict[str, Any] | None = Field(None, description="Your own fields, up to 50 scalar values.")


class MoveIn(_Kropp):
    stage_id: str = Field(description="The stage to move the deal to. May be its current stage.")
    before_id: str | None = Field(None, description="Place the deal just before this deal in the stage.")
    after_id: str | None = Field(None, description="Place the deal just after this deal. Without either, last.")


class TaskIn(_Kropp):
    title: str | None = Field(None, description="Required when creating.")
    description: str | None = None
    status: Literal["todo", "in_progress", "done"] | None = Field(
        None, description="Defaults to `todo`. `completed_at` is set when it becomes `done`.")
    due_at: str | None = Field(None, description="ISO 8601 timestamp.")
    owner: str | None = None
    company_id: str | None = None
    person_id: str | None = None
    deal_id: str | None = None


class NoteIn(_Kropp):
    title: str | None = None
    body: str | None = Field(None, description=f"Plain text, at most {objekt.MAX_ANTECKNING} characters.")
    pinned: bool | None = None
    author: str | None = None
    company_id: str | None = None
    person_id: str | None = None
    deal_id: str | None = None


class ActivityIn(_Kropp):
    type: Literal["call", "meeting", "email", "visit", "other"] | None = Field(None, description="Defaults to `other`.")
    subject: str | None = Field(None, description="Required when creating.")
    body: str | None = None
    occurred_at: str | None = Field(None, description="ISO 8601 timestamp. Defaults to now.")
    duration_minutes: int | None = Field(None, ge=0)
    outcome: str | None = None
    owner: str | None = None
    company_id: str | None = None
    person_id: str | None = None
    deal_id: str | None = None


# -- Gemensamt för listor och skrivningar ------------------------------------

_SORTERING = {"updated": "andrad", "-updated": "andrad_fallande", "name": "namn", "due": "forfaller"}
_LIMIT = Query(50, ge=1, le=500)
_CURSOR = Query(None, description="`next_cursor` from the previous page.")
_INCLUDE_DELETED = Query(False, description="Include deleted records (`deleted_at` set).")
_ONLY_DELETED = Query(False, description="The trash: only deleted records that can still be restored.")
_Q = Query(None, max_length=200, description="Free text search.")


def _koppling_filter(company_id: str | None, person_id: str | None, deal_id: str | None = None) -> dict[str, Any]:
    return {"bolag_id": _id(company_id, "Bolaget") if company_id else None,
            "person_id": _id(person_id, "Personen") if person_id else None,
            "affar_id": _id(deal_id, "Affären") if deal_id else None}


async def _lista(request: Request, tenant: dict, objekt_: str, *, limit: int, cursor: str | None, sort: str,
                 include_deleted: bool, only_deleted: bool, q: str | None, lika: dict[str, Any],
                 fore: dict[str, str] | None = None) -> dict:
    try:
        poster, nasta = await lagring.lista_poster(
            request.app.state.storage, tenant["tenant_id"], objekt_, limit=limit, markor=cursor,
            ordning="raderad" if only_deleted else _SORTERING[sort], med_raderade=include_deleted,
            lika=lika, q=q, fore=fore)
    except ValueError:
        raise fel(422, "invalid_parameter", "cursor could not be read.",
                  "cursor gick inte att läsa.") from None
    return {"data": [_UT[objekt_](p) for p in poster], "next_cursor": nasta}


async def _en(request: Request, tenant: dict, objekt_: str, rad_id: str, *, med_raderade: bool = False) -> dict:
    post = await objekt.hamta(request.app.state.storage, tenant["tenant_id"], objekt_, _id(rad_id, "Posten"),
                              med_raderade=med_raderade)
    if post is None:
        raise _finns_inte()
    return _UT[objekt_](post)


async def _skapa(request: Request, tenant: dict, objekt_: str, kropp: _Kropp) -> Response:
    await _avtal(request, tenant)
    falten = _in(objekt_, kropp.model_dump(exclude_unset=True))

    async def arbete():
        try:
            post = await objekt.skapa(request.app.state.storage, tenant["tenant_id"], objekt_, falten, kalla="api",
                                      **_ursprung(request, tenant))
        except objekt.ObjektFel as orsak:
            raise _objektfel(orsak, objekt_) from None
        return 201, _UT[objekt_](post)

    return await _idempotent(request, tenant, arbete)


async def _andra(request: Request, tenant: dict, objekt_: str, rad_id: str, kropp: _Kropp) -> dict:
    await _avtal(request, tenant)
    try:
        post = await objekt.andra(request.app.state.storage, tenant["tenant_id"], objekt_, _id(rad_id, "Posten"),
                                  _in(objekt_, kropp.model_dump(exclude_unset=True)), **_ursprung(request, tenant))
    except objekt.ObjektFel as orsak:
        raise _objektfel(orsak, objekt_) from None
    if post is None:
        raise _finns_inte()
    return _UT[objekt_](post)


async def _radera(request: Request, tenant: dict, objekt_: str, rad_id: str, permanent: bool) -> Response:
    await _avtal(request, tenant)
    if not await objekt.radera(request.app.state.storage, tenant["tenant_id"], objekt_, _id(rad_id, "Posten"),
                               permanent=permanent, **_ursprung(request, tenant)):
        raise _finns_inte()
    return Response(status_code=204)


async def _aterstall(request: Request, tenant: dict, objekt_: str, rad_id: str) -> dict:
    await _avtal(request, tenant)
    try:
        post = await objekt.aterstall(request.app.state.storage, tenant["tenant_id"], objekt_,
                                      _id(rad_id, "Posten"), **_ursprung(request, tenant))
    except objekt.RedanTomd:
        raise fel(410, "permanently_deleted", "The record is permanently deleted and cannot be restored.",
                  "Posten är permanent raderad och går inte att återställa.") from None
    if post is None:
        raise _finns_inte()
    return _UT[objekt_](post)


# -- Affärens steg -----------------------------------------------------------


@router.get("/deal-stages", summary="List deal stages in board order")
async def lista_steg(request: Request, tenant: dict = Depends(kraev("crm:las"))) -> dict:
    """A workspace gets the Swedish default stages the first time they are read:
    Ny, Kvalificerad, Möte bokat, Offert skickad, Förhandling, Vunnen, Förlorad."""
    rader = await objekt.lista_steg(request.app.state.storage, tenant["tenant_id"])
    return {"data": [steg_ut(s) for s in rader]}


@router.post("/deal-stages", status_code=201, summary="Create a deal stage")
async def skapa_steg(request: Request, kropp: StageIn, tenant: dict = Depends(kraev("crm:skriv"))) -> Response:
    """The new stage is placed last. Reorder with POST /deal-stages/reorder."""
    await _avtal(request, tenant)
    falten = _in("steg", kropp.model_dump(exclude_unset=True))

    async def arbete():
        try:
            rad = await objekt.skapa_steg(request.app.state.storage, tenant["tenant_id"], falten)
        except objekt.ObjektFel as orsak:
            raise _objektfel(orsak) from None
        except lagring.FinnsRedan:
            raise fel(409, "conflict", "A stage with this name already exists.",
                      "Det finns redan ett steg med det namnet.") from None
        return 201, steg_ut(rad)

    return await _idempotent(request, tenant, arbete)


@router.post("/deal-stages/reorder", summary="Put the deal stages in a new order")
async def ordna_steg(request: Request, kropp: ReorderIn, tenant: dict = Depends(kraev("crm:skriv"))) -> dict:
    await _avtal(request, tenant)
    try:
        rader = await objekt.ordna_steg(request.app.state.storage, tenant["tenant_id"],
                                        [str(i).lower() for i in kropp.ids])
    except objekt.ObjektFel as orsak:
        raise _objektfel(orsak) from None
    return {"data": [steg_ut(s) for s in rader]}


@router.patch("/deal-stages/{stage_id}", summary="Rename or change a deal stage")
async def andra_steg(request: Request, stage_id: str, kropp: StageIn,
                     tenant: dict = Depends(kraev("crm:skriv"))) -> dict:
    await _avtal(request, tenant)
    try:
        rad = await objekt.andra_steg(request.app.state.storage, tenant["tenant_id"], _id(stage_id, "Steget"),
                                      _in("steg", kropp.model_dump(exclude_unset=True)))
    except objekt.ObjektFel as orsak:
        raise _objektfel(orsak) from None
    except lagring.FinnsRedan:
        raise fel(409, "conflict", "A stage with this name already exists.",
                  "Det finns redan ett steg med det namnet.") from None
    if rad is None:
        raise fel(404, "stage_not_found", "The deal stage does not exist.", "Steget finns inte.")
    return steg_ut(rad)


@router.delete("/deal-stages/{stage_id}", status_code=204, summary="Delete a deal stage")
async def radera_steg(request: Request, stage_id: str, tenant: dict = Depends(kraev("crm:skriv"))) -> Response:
    """Refused with `stage_in_use` while the stage has deals, also deleted
    deals that can still be restored, and with `stage_required` for the last
    open, won or lost stage."""
    await _avtal(request, tenant)
    try:
        fanns = await objekt.ta_bort_steg(request.app.state.storage, tenant["tenant_id"], _id(stage_id, "Steget"))
    except objekt.ObjektFel as orsak:
        raise _objektfel(orsak) from None
    if not fanns:
        raise fel(404, "stage_not_found", "The deal stage does not exist.", "Steget finns inte.")
    return Response(status_code=204)


# -- Affärer -----------------------------------------------------------------


@router.get("/deals", summary="List deals")
async def lista_affarer(
    request: Request, tenant: dict = Depends(kraev("crm:las")),
    limit: int = _LIMIT, cursor: str | None = _CURSOR,
    sort: str = Query("updated", pattern="^(-?updated|name)$",
                      description="`updated` oldest change first, `-updated` newest first, `name` alphabetical."),
    include_deleted: bool = _INCLUDE_DELETED, only_deleted: bool = _ONLY_DELETED, q: str | None = _Q,
    company_id: str | None = None, person_id: str | None = None, stage_id: str | None = None,
    lost_reason_code: ForlustorsakKod | None = Query(None, description="Only deals lost for this reason."),
) -> dict:
    lika = {**_koppling_filter(company_id, person_id), "steg_id": _id(stage_id, "Steget") if stage_id else None,
            "forlustorsak_kod": _VARDEN_IN["forlustorsak_kod"][lost_reason_code] if lost_reason_code else None}
    lika.pop("affar_id")
    return await _lista(request, tenant, "affar", limit=limit, cursor=cursor, sort=sort,
                        include_deleted=include_deleted, only_deleted=only_deleted, q=q, lika=lika)


@router.post("/deals", status_code=201, summary="Create a deal")
async def skapa_affar(request: Request, kropp: DealIn, tenant: dict = Depends(kraev("crm:skriv"))) -> Response:
    """Placed last in its stage. A deal created in a won or lost stage gets
    `closed_at` at once."""
    return await _skapa(request, tenant, "affar", kropp)


@router.get("/deals/board", summary="The deal board: every stage with its deals")
async def tavla(request: Request, tenant: dict = Depends(kraev("crm:las"))) -> dict:
    """Stages in board order, each with its live deals in board order, their
    count and the sum of their amounts. `amount_total` adds amounts as they
    are; `amount_by_currency` keeps the currencies apart."""
    steg = await objekt.tavla(request.app.state.storage, tenant["tenant_id"])
    ut = []
    for s in steg:
        per_valuta: dict[str, int] = {}
        for a in s["affarer"]:
            per_valuta[a.get("valuta") or "SEK"] = per_valuta.get(a.get("valuta") or "SEK", 0) + (a.get("belopp") or 0)
        ut.append({**steg_ut(s), "deals": [affar_ut(a) for a in s["affarer"]], "count": len(s["affarer"]),
                   "amount_total": sum(per_valuta.values()), "amount_by_currency": per_valuta})
    return {"stages": ut}


@router.get("/deals/{deal_id}", summary="Get a deal")
async def hamta_affar(request: Request, deal_id: str, include_deleted: bool = False,
                      tenant: dict = Depends(kraev("crm:las"))) -> dict:
    return await _en(request, tenant, "affar", deal_id, med_raderade=include_deleted)


@router.patch("/deals/{deal_id}", summary="Change a deal")
async def andra_affar(request: Request, deal_id: str, kropp: DealIn, tenant: dict = Depends(kraev("crm:skriv"))) -> dict:
    """Only the fields sent are changed; `null` clears a field."""
    return await _andra(request, tenant, "affar", deal_id, kropp)


@router.post("/deals/{deal_id}/move", summary="Move a deal on the board")
async def flytta_affar(request: Request, deal_id: str, kropp: MoveIn, tenant: dict = Depends(kraev("crm:skriv"))) -> dict:
    """To a stage, before or after another deal in it. Moving into a won or
    lost stage sets `closed_at`; moving back to an open stage clears it."""
    await _avtal(request, tenant)
    try:
        post = await objekt.flytta(
            request.app.state.storage, tenant["tenant_id"], _id(deal_id, "Affären"), kropp.stage_id.strip().lower(),
            fore_id=(kropp.before_id or "").strip().lower() or None,
            efter_id=(kropp.after_id or "").strip().lower() or None, **_ursprung(request, tenant))
    except objekt.ObjektFel as orsak:
        raise _objektfel(orsak, "affar") from None
    if post is None:
        raise _finns_inte()
    return affar_ut(post)


@router.delete("/deals/{deal_id}", status_code=204, summary="Delete a deal")
async def radera_affar(request: Request, deal_id: str, permanent: bool = _PERMANENT,
                       tenant: dict = Depends(kraev("crm:skriv"))) -> Response:
    return await _radera(request, tenant, "affar", deal_id, permanent)


@router.post("/deals/{deal_id}/restore", summary="Restore a deleted deal")
async def aterstall_affar(request: Request, deal_id: str, tenant: dict = Depends(kraev("crm:skriv"))) -> dict:
    return await _aterstall(request, tenant, "affar", deal_id)


@router.get("/deals/{deal_id}/history", summary="What has happened to a deal, newest first")
async def historik_affar(request: Request, deal_id: str, limit: int = Query(100, ge=1, le=500),
                         tenant: dict = Depends(kraev("crm:las"))) -> dict:
    storage = request.app.state.storage
    rad_id = _id(deal_id, "Affären")
    if await objekt.hamta(storage, tenant["tenant_id"], "affar", rad_id, med_raderade=True) is None:
        raise _finns_inte()
    rader = await handelser.for_post(storage, tenant["tenant_id"], "affar", rad_id, limit=limit)
    return {"data": [handelse_ut(r) for r in rader]}


# -- Uppgifter ---------------------------------------------------------------


@router.get("/tasks", summary="List tasks")
async def lista_uppgifter(
    request: Request, tenant: dict = Depends(kraev("crm:las")),
    limit: int = _LIMIT, cursor: str | None = _CURSOR,
    sort: str = Query("updated", pattern="^(-?updated|due)$",
                      description="`updated`, `-updated`, or `due`: earliest due first, tasks without a due date last."),
    include_deleted: bool = _INCLUDE_DELETED, only_deleted: bool = _ONLY_DELETED, q: str | None = _Q,
    company_id: str | None = None, person_id: str | None = None, deal_id: str | None = None,
    status: Literal["todo", "in_progress", "done"] | None = None, owner: str | None = Query(None, max_length=200),
    due_before: str | None = Query(None, description="ISO 8601 timestamp. Only tasks due before it."),
) -> dict:
    lika = {**_koppling_filter(company_id, person_id, deal_id),
            "status": _VARDEN_IN["status"][status] if status else None, "ansvarig": owner}
    try:
        fore = {"forfaller_at": objekt._tid_utc(due_before)} if due_before else None
    except falt.FaltFel:
        raise fel(422, "invalid_parameter", "due_before could not be read.", "due_before gick inte att läsa.") from None
    return await _lista(request, tenant, "uppgift", limit=limit, cursor=cursor, sort=sort,
                        include_deleted=include_deleted, only_deleted=only_deleted, q=q, lika=lika, fore=fore)


@router.post("/tasks", status_code=201, summary="Create a task")
async def skapa_uppgift(request: Request, kropp: TaskIn, tenant: dict = Depends(kraev("crm:skriv"))) -> Response:
    """A task may stand on its own or be linked to a company, a person and a deal."""
    return await _skapa(request, tenant, "uppgift", kropp)


@router.get("/tasks/{task_id}", summary="Get a task")
async def hamta_uppgift(request: Request, task_id: str, include_deleted: bool = False,
                        tenant: dict = Depends(kraev("crm:las"))) -> dict:
    return await _en(request, tenant, "uppgift", task_id, med_raderade=include_deleted)


@router.patch("/tasks/{task_id}", summary="Change a task")
async def andra_uppgift(request: Request, task_id: str, kropp: TaskIn, tenant: dict = Depends(kraev("crm:skriv"))) -> dict:
    return await _andra(request, tenant, "uppgift", task_id, kropp)


@router.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
async def radera_uppgift(request: Request, task_id: str, permanent: bool = _PERMANENT,
                         tenant: dict = Depends(kraev("crm:skriv"))) -> Response:
    return await _radera(request, tenant, "uppgift", task_id, permanent)


@router.post("/tasks/{task_id}/restore", summary="Restore a deleted task")
async def aterstall_uppgift(request: Request, task_id: str, tenant: dict = Depends(kraev("crm:skriv"))) -> dict:
    return await _aterstall(request, tenant, "uppgift", task_id)


# -- Anteckningar ------------------------------------------------------------


@router.get("/notes", summary="List notes")
async def lista_anteckningar(
    request: Request, tenant: dict = Depends(kraev("crm:las")),
    limit: int = _LIMIT, cursor: str | None = _CURSOR,
    sort: str = Query("updated", pattern="^-?updated$"),
    include_deleted: bool = _INCLUDE_DELETED, only_deleted: bool = _ONLY_DELETED, q: str | None = _Q,
    company_id: str | None = None, person_id: str | None = None, deal_id: str | None = None,
) -> dict:
    return await _lista(request, tenant, "anteckning", limit=limit, cursor=cursor, sort=sort,
                        include_deleted=include_deleted, only_deleted=only_deleted, q=q,
                        lika=_koppling_filter(company_id, person_id, deal_id))


@router.post("/notes", status_code=201, summary="Create a note")
async def skapa_anteckning(request: Request, kropp: NoteIn, tenant: dict = Depends(kraev("crm:skriv"))) -> Response:
    """A note is linked to at least one company, person or deal."""
    return await _skapa(request, tenant, "anteckning", kropp)


@router.get("/notes/{note_id}", summary="Get a note")
async def hamta_anteckning(request: Request, note_id: str, include_deleted: bool = False,
                           tenant: dict = Depends(kraev("crm:las"))) -> dict:
    return await _en(request, tenant, "anteckning", note_id, med_raderade=include_deleted)


@router.patch("/notes/{note_id}", summary="Change a note")
async def andra_anteckning(request: Request, note_id: str, kropp: NoteIn,
                           tenant: dict = Depends(kraev("crm:skriv"))) -> dict:
    return await _andra(request, tenant, "anteckning", note_id, kropp)


@router.delete("/notes/{note_id}", status_code=204, summary="Delete a note")
async def radera_anteckning(request: Request, note_id: str, permanent: bool = _PERMANENT,
                            tenant: dict = Depends(kraev("crm:skriv"))) -> Response:
    return await _radera(request, tenant, "anteckning", note_id, permanent)


@router.post("/notes/{note_id}/restore", summary="Restore a deleted note")
async def aterstall_anteckning(request: Request, note_id: str, tenant: dict = Depends(kraev("crm:skriv"))) -> dict:
    return await _aterstall(request, tenant, "anteckning", note_id)


# -- Aktiviteter -------------------------------------------------------------


@router.get("/activities", summary="List logged activities")
async def lista_aktiviteter(
    request: Request, tenant: dict = Depends(kraev("crm:las")),
    limit: int = _LIMIT, cursor: str | None = _CURSOR,
    sort: str = Query("updated", pattern="^-?updated$"),
    include_deleted: bool = _INCLUDE_DELETED, only_deleted: bool = _ONLY_DELETED, q: str | None = _Q,
    company_id: str | None = None, person_id: str | None = None, deal_id: str | None = None,
) -> dict:
    return await _lista(request, tenant, "aktivitet", limit=limit, cursor=cursor, sort=sort,
                        include_deleted=include_deleted, only_deleted=only_deleted, q=q,
                        lika=_koppling_filter(company_id, person_id, deal_id))


@router.post("/activities", status_code=201, summary="Log an activity: a call, meeting, email or visit")
async def skapa_aktivitet(request: Request, kropp: ActivityIn, tenant: dict = Depends(kraev("crm:skriv"))) -> Response:
    """Linked to at least one company, person or deal."""
    return await _skapa(request, tenant, "aktivitet", kropp)


@router.get("/activities/{activity_id}", summary="Get an activity")
async def hamta_aktivitet(request: Request, activity_id: str, include_deleted: bool = False,
                          tenant: dict = Depends(kraev("crm:las"))) -> dict:
    return await _en(request, tenant, "aktivitet", activity_id, med_raderade=include_deleted)


@router.patch("/activities/{activity_id}", summary="Change an activity")
async def andra_aktivitet(request: Request, activity_id: str, kropp: ActivityIn,
                          tenant: dict = Depends(kraev("crm:skriv"))) -> dict:
    return await _andra(request, tenant, "aktivitet", activity_id, kropp)


@router.delete("/activities/{activity_id}", status_code=204, summary="Delete an activity")
async def radera_aktivitet(request: Request, activity_id: str, permanent: bool = _PERMANENT,
                           tenant: dict = Depends(kraev("crm:skriv"))) -> Response:
    return await _radera(request, tenant, "aktivitet", activity_id, permanent)


@router.post("/activities/{activity_id}/restore", summary="Restore a deleted activity")
async def aterstall_aktivitet(request: Request, activity_id: str, tenant: dict = Depends(kraev("crm:skriv"))) -> dict:
    return await _aterstall(request, tenant, "aktivitet", activity_id)


# -- Bilagor -----------------------------------------------------------------

#: Plats för multipartens gränser och rubriker utöver själva filen.
_MULTIPART_MARGINAL = 64 * 1024

_UPPLADDNING = {
    "requestBody": {"required": True, "content": {"multipart/form-data": {"schema": {
        "type": "object", "required": ["file"],
        "properties": {
            "file": {"type": "string", "format": "binary",
                     "description": "At most 10 MB. pdf, png, jpeg, webp, gif, txt, csv, docx, xlsx or pptx."},
            "company_id": {"type": "string"}, "person_id": {"type": "string"},
            "deal_id": {"type": "string"}, "note_id": {"type": "string"},
        }}}}},
}


async def _las_begransat(request: Request) -> None:
    """Läser kroppen och avbryter så snart den är större än en fil får vara.
    Content-Length prövas först; en kropp utan den räknas medan den läses.

    Ett godkänt anrop har som mest två kopior av kroppen i minnet samtidigt
    (bitarna och den sammanfogade kroppen, i ögonblicket de fogas ihop), alltså
    runt 20 MB. Kroppen släpps när formuläret är tolkat (`ladda_upp_bilaga`)."""
    grans = objekt.MAX_BILAGA + _MULTIPART_MARGINAL
    langd = request.headers.get("content-length", "")
    if langd.isdigit() and int(langd) > grans:
        raise _FEL["file_too_large"]()
    delar, storlek = [], 0
    async for bit in request.stream():
        storlek += len(bit)
        if storlek > grans:
            raise _FEL["file_too_large"]()
        delar.append(bit)
    # Starlette läser formuläret härifrån i stället för från nätet.
    request._body = b"".join(delar)


def _bilagans_hash(filnamn: str | None, typ: str | None, innehall: bytes, kopplingar: dict[str, Any]) -> str:
    """Idempotensnyckelns kroppshash för en uppladdning. Multipartens gräns
    slumpas av klienten för varje anrop, så den råa kroppen skiljer sig mellan
    två i övrigt lika försök: hashen räknas på det tolkade innehållet."""
    summa = hashlib.sha256()
    for del_ in (filnamn or "", typ or "", *(f"{k}={v or ''}" for k, v in sorted(kopplingar.items()))):
        summa.update(del_.encode("utf-8") + b"\x00")
    summa.update(innehall)
    return summa.hexdigest()


@router.get("/attachments", summary="List attachments (metadata only)")
async def lista_bilagor(
    request: Request, tenant: dict = Depends(kraev("crm:las")),
    limit: int = _LIMIT, cursor: str | None = _CURSOR,
    sort: str = Query("updated", pattern="^-?updated$"),
    include_deleted: bool = _INCLUDE_DELETED, only_deleted: bool = _ONLY_DELETED, q: str | None = _Q,
    company_id: str | None = None, person_id: str | None = None, deal_id: str | None = None,
    note_id: str | None = None,
) -> dict:
    lika = {**_koppling_filter(company_id, person_id, deal_id),
            "anteckning_id": _id(note_id, "Anteckningen") if note_id else None}
    return await _lista(request, tenant, "bilaga", limit=limit, cursor=cursor, sort=sort,
                        include_deleted=include_deleted, only_deleted=only_deleted, q=q, lika=lika)


@router.post("/attachments", status_code=201, summary="Upload an attachment", openapi_extra=_UPPLADDNING)
async def ladda_upp_bilaga(request: Request, tenant: dict = Depends(kraev("crm:skriv"))) -> Response:
    """`multipart/form-data` with `file` and at least one of `company_id`,
    `person_id`, `deal_id` and `note_id`. At most 10 MB per file and 500 MB
    per workspace. The type must match the file extension."""
    await _avtal(request, tenant)
    await _las_begransat(request)
    try:
        formular = await request.form()
    except Exception:  # noqa: BLE001 — en trasig multipart är anroparens fel, inte vårt
        raise fel(422, "invalid_body", "Send multipart/form-data with a file field.",
                  "Skicka multipart/form-data med fältet file.") from None
    fil = formular.get("file")
    if not isinstance(fil, UploadFile):
        raise fel(422, "invalid_body", "Send multipart/form-data with a file field.",
                  "Skicka multipart/form-data med fältet file.")
    # Formuläret är tolkat (filen ligger i en egen buffert): den råa kroppen behövs inte längre.
    del request._body
    innehall = await fil.read(objekt.MAX_BILAGA + 1)
    kopplingar = {sv: (str(formular.get(en) or "").strip() or None)
                  for en, sv in {**_KOPPLING, "note_id": "anteckning_id"}.items()}
    ursprung = _ursprung(request, tenant)

    async def arbete():
        try:
            post = await objekt.skapa_bilaga(
                request.app.state.storage, tenant["tenant_id"], filnamn=fil.filename, typ=fil.content_type,
                innehall=innehall, kopplingar=kopplingar, uppladdad_av=ursprung["aktor"], kalla="api", **ursprung)
        except objekt.ObjektFel as orsak:
            raise _objektfel(orsak, "bilaga") from None
        return 201, bilaga_ut(post)

    return await _idempotent(request, tenant, arbete,
                             kroppshash=_bilagans_hash(fil.filename, fil.content_type, innehall, kopplingar))


@router.get("/attachments/{attachment_id}", summary="Get an attachment's metadata")
async def hamta_bilaga(request: Request, attachment_id: str, include_deleted: bool = False,
                       tenant: dict = Depends(kraev("crm:las"))) -> dict:
    return await _en(request, tenant, "bilaga", attachment_id, med_raderade=include_deleted)


@router.get("/attachments/{attachment_id}/content", summary="Download an attachment",
            response_class=Response, responses={200: {"content": {"application/octet-stream": {}},
                                                       "description": "The file."}})
async def ladda_ned_bilaga(request: Request, attachment_id: str, tenant: dict = Depends(kraev("crm:las"))) -> Response:
    """Always served as a download (`Content-Disposition: attachment`), never
    shown inline, and not cached."""
    storage = request.app.state.storage
    rad_id = _id(attachment_id, "Bilagan")
    post = await objekt.hamta(storage, tenant["tenant_id"], "bilaga", rad_id)
    innehall = await lagring.bilagans_innehall(storage, tenant["tenant_id"], rad_id) if post else None
    if post is None or innehall is None:
        raise _finns_inte()
    namn = post["filnamn"] or "fil"
    ascii_namn = namn.encode("ascii", "ignore").decode().replace('"', "").replace("\\", "") or "fil"
    return Response(content=innehall, media_type=post["typ"], headers={
        "Content-Disposition": f"attachment; filename=\"{ascii_namn}\"; filename*=UTF-8''{quote(namn)}",
        "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})


@router.delete("/attachments/{attachment_id}", status_code=204, summary="Delete an attachment")
async def radera_bilaga(request: Request, attachment_id: str, permanent: bool = _PERMANENT,
                        tenant: dict = Depends(kraev("crm:skriv"))) -> Response:
    """Restorable for 30 days, then the file is emptied for good."""
    return await _radera(request, tenant, "bilaga", attachment_id, permanent)


@router.post("/attachments/{attachment_id}/restore", summary="Restore a deleted attachment")
async def aterstall_bilaga(request: Request, attachment_id: str, tenant: dict = Depends(kraev("crm:skriv"))) -> dict:
    return await _aterstall(request, tenant, "bilaga", attachment_id)
