"""Snajp CRM i det publika API:t: den gemensamma spärren (migration 166).

En invändning mot direktmarknadsföring gäller i varje kanal (app/crm/sparr.py).
Här läggs, listas och hävs spärrar, kunden laddar upp utfallet av sin egen
NIX-tvätt, och vem som helst med läsrätt kan fråga om en kontakt är spärrad.

Routern byggs av `koppla(crm_v1)` och läggs till därifrån, så grindarna
(nyckel, omfång, tillägg, tak, avtal) är desamma som för resten av API:t.

Svaret på en kontroll säger vilken källa som spärrade, aldrig vad den visste.
En webhook om en spärr bär aldrig värdet eller anteckningen.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from ..crm import handelser, sparr

_KANAL_UT = {"mejl": "email", "telefon": "phone", "alla": "all"}
_KANAL_IN = {v: k for k, v in _KANAL_UT.items()}
_SLAG_UT = {"epost": "email", "telefon": "phone", "doman": "domain", "orgnr": "org_number"}
_SLAG_IN = {v: k for k, v in _SLAG_UT.items()}
_ORSAK_UT = {"invandning": "objection", "avregistrering": "unsubscribe", "nix": "nix",
             "kunden_bad": "customer_request", "studs": "bounce", "annat": "other"}
_ORSAK_IN = {v: k for k, v in _ORSAK_UT.items()}
_KALLA_UT = {"app": "app", "api": "api", "utfall": "outcome", "import": "import", "synk": "sync"}
_GRIND_UT = {"sparrlistan": "suppression_list", "posten": "record", "avregistrerad": "unsubscribed",
             "lead": "lead"}
#: Fältnamnen i ett fel, CRM:ets till API:ts.
_FALT_UT = {"channel": "channel", "kind": "kind", "value": "value", "reason": "reason", "note": "note",
            "source": "source", "values": "values", "org_number": "org_number", "email": "email",
            "phone": "phone"}

Kanal = Literal["email", "phone", "all"]
Slag = Literal["email", "phone", "domain", "org_number"]
Orsak = Literal["objection", "unsubscribe", "nix", "customer_request", "bounce", "other"]


def _varde_ut(rad: dict[str, Any]) -> str:
    """Organisationsnumret visas NNNNNN-NNNN, som på bolaget."""
    varde = rad["varde"]
    return f"{varde[:6]}-{varde[6:]}" if rad["slag"] == "orgnr" else varde


def sparr_ut(rad: dict[str, Any]) -> dict[str, Any]:
    return {"id": rad["id"], "channel": _KANAL_UT[rad["kanal"]], "kind": _SLAG_UT[rad["slag"]],
            "value": _varde_ut(rad), "reason": _ORSAK_UT.get(rad["orsak"], "other"), "note": rad.get("anteckning"),
            "source": _KALLA_UT.get(rad["kalla"], rad["kalla"]), "company_id": rad.get("bolag_id"),
            "person_id": rad.get("person_id"), "created_at": rad.get("created_at"),
            "lifted_at": rad.get("havd_at"), "lifted_by": rad.get("havd_av")}


def sparr_last(rad: dict[str, Any]) -> dict[str, Any]:
    """Det en webhook bär om spärren: aldrig värdet, aldrig anteckningen.
    Mottagaren hämtar spärren med sin nyckel om den behöver adressen."""
    return {"id": rad["id"], "channel": _KANAL_UT[rad["kanal"]], "kind": _SLAG_UT[rad["slag"]],
            "reason": _ORSAK_UT.get(rad["orsak"], "other"), "source": _KALLA_UT.get(rad["kalla"], rad["kalla"]),
            "created_at": rad.get("created_at"), "lifted_at": rad.get("havd_at")}


handelser.registrera_form("sparr", sparr_last)


class _Kropp(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SuppressionIn(_Kropp):
    channel: Kanal = Field(..., description="`email`, `phone` or `all` (every channel).")
    kind: Slag = Field(..., description="What `value` is. An email or domain block belongs to `email` or "
                       "`all`, a phone block to `phone` or `all`; an organisation number blocks the "
                       "company in any channel.")
    value: str = Field(..., max_length=320, description="Stored normalised: email and domain in lower "
                       "case, phone as E.164, organisation number as NNNNNN-NNNN.")
    reason: Orsak = Field(..., description="`objection` is GDPR art. 21, `nix` a hit in your NIX check.")
    note: str | None = Field(None, max_length=500, description="Never sent in a webhook or written to a log.")


class ImportIn(_Kropp):
    channel: Kanal
    reason: Orsak
    values: list[str] = Field(..., description=f"At most {sparr.MAX_IMPORT} per call.")
    kind: Slag | None = Field(None, description="Without it: a value with @ is an email, otherwise a domain "
                              "on `email` and a phone number on `phone` and `all`.")


class CheckIn(_Kropp):
    channel: Kanal = Field(..., description="`all` asks whether anything blocks in any channel.")
    email: str | None = Field(None, max_length=320)
    phone: str | None = Field(None, max_length=40)
    org_number: str | None = Field(None, max_length=40)


def koppla(v1: Any) -> APIRouter:
    """Bygger ändpunkterna med `crm_v1`s egna grindar, på en ny router."""
    router = APIRouter(prefix=v1.router.prefix, tags=v1.router.tags)
    kraev, fel = v1.kraev, v1.fel

    def _ogiltig(orsak: sparr.OgiltigSparr) -> Exception:
        return fel(422, "invalid_fields", "One or more fields could not be interpreted.",
                   "Ett eller flera fält gick inte att tolka.",
                   fields=[{"field": _FALT_UT.get(orsak.falt, orsak.falt), "code": orsak.kod}])

    @router.get("/suppressions", summary="List suppressions, newest first")
    async def lista(
        request: Request, tenant: dict = Depends(kraev("crm:las")),
        limit: int = Query(50, ge=1, le=500), cursor: str | None = Query(None),
        channel: Kanal | None = Query(None, description="Only suppressions in exactly this channel."),
        applies_to: Literal["email", "phone"] | None = Query(
            None, description="The suppressions that block this channel: its own and those in `all`. "
            "Not together with `channel`."),
        reason: Orsak | None = Query(None),
        q: str | None = Query(None, max_length=200, description="Part of the value."),
        include_lifted: bool = Query(False, description="Lifted suppressions are kept as a record but no "
                                     "longer block anything."),
        only_lifted: bool = Query(False, description="Only lifted suppressions, most recently lifted first. "
                                  "`include_lifted` then has no effect."),
    ) -> dict:
        """The suppression list. Records marked do-not-contact, unsubscribed
        addresses and leads that asked not to be contacted also block, but are
        not listed here: ask `POST /suppressions/check`."""
        if channel and applies_to:
            raise fel(422, "invalid_parameter", "Use channel or applies_to, not both.",
                      "Ange channel eller applies_to, inte båda.")
        try:
            rader, nasta = await sparr.lista(
                request.app.state.storage, tenant["tenant_id"], limit=limit, markor=cursor,
                kanal=_KANAL_IN[channel] if channel else None, orsak=_ORSAK_IN[reason] if reason else None,
                q=q, med_havda=include_lifted, bara_havda=only_lifted,
                galler_i=_KANAL_IN[applies_to] if applies_to else None)
        except ValueError:
            raise fel(422, "invalid_parameter", "cursor could not be read.", "cursor gick inte att läsa.") from None
        return {"data": [sparr_ut(r) for r in rader], "next_cursor": nasta}

    @router.post("/suppressions", status_code=201, summary="Block an email, domain, phone number or organisation number")
    async def skapa(request: Request, kropp: SuppressionIn, tenant: dict = Depends(kraev("crm:skriv"))) -> Response:
        """201 with the new suppression, or 200 with the one that already blocks
        the same value in the same channel. Sends `suppression.created`."""
        await v1._avtal(request, tenant)
        ursprung = v1._ursprung(request, tenant)

        async def arbete():
            try:
                rad, skapad = await sparr.lagg_till(
                    request.app.state.storage, tenant["tenant_id"], kanal=_KANAL_IN[kropp.channel],
                    slag=_SLAG_IN[kropp.kind], varde=kropp.value, orsak=_ORSAK_IN[kropp.reason],
                    anteckning=kropp.note, kalla=ursprung["via"], **ursprung)
            except sparr.OgiltigSparr as orsak:
                raise _ogiltig(orsak) from None
            return (201 if skapad else 200), sparr_ut(rad)

        return await v1._idempotent(request, tenant, arbete)

    @router.post("/suppressions/import", summary="Add many suppressions in one call, e.g. your NIX check")
    async def importera(request: Request, kropp: ImportIn, tenant: dict = Depends(kraev("crm:skriv"))) -> Response:
        """Upload the outcome of your own NIX check with `channel: phone,
        reason: nix`. `added + already_blocked + len(invalid)` is the number of
        values sent; a duplicate within the call counts as already blocked.
        `invalid` gives the position and the reason, never the value."""
        await v1._avtal(request, tenant)
        if len(kropp.values) > sparr.MAX_IMPORT:
            raise fel(422, "too_many_items", f"At most {sparr.MAX_IMPORT} values per call.",
                      f"Högst {sparr.MAX_IMPORT} värden per anrop.")

        async def arbete():
            try:
                svar = await sparr.importera(
                    request.app.state.storage, tenant["tenant_id"], kanal=_KANAL_IN[kropp.channel],
                    orsak=_ORSAK_IN[kropp.reason], varden=kropp.values,
                    slag=_SLAG_IN[kropp.kind] if kropp.kind else None, **v1._ursprung(request, tenant))
            except sparr.OgiltigSparr as orsak:
                raise _ogiltig(orsak) from None
            return 200, {"added": svar["tillagda"], "already_blocked": svar["redan_sparrade"],
                         "invalid": [{"index": o["index"], "code": o["kod"]} for o in svar["ogiltiga"]]}

        return await v1._idempotent(request, tenant, arbete)

    @router.delete("/suppressions/{suppression_id}", status_code=204, summary="Lift a suppression")
    async def hav(request: Request, suppression_id: str, tenant: dict = Depends(kraev("crm:skriv"))) -> Response:
        """The suppression stays as a record with `lifted_at`, and no longer
        blocks. Lifting it again changes nothing. Sends `suppression.lifted`."""
        await v1._avtal(request, tenant)

        def finns_inte() -> Exception:
            return fel(404, "suppression_not_found", "The suppression does not exist.", "Spärren finns inte.")

        # Ett felformat id och ett id som inte finns ger samma svar, med samma kod.
        try:
            sparr_id = str(UUID(suppression_id))
        except (ValueError, AttributeError, TypeError):
            raise finns_inte() from None
        rad = await sparr.hav(request.app.state.storage, tenant["tenant_id"], sparr_id,
                              **v1._ursprung(request, tenant))
        if rad is None:
            raise finns_inte()
        return Response(status_code=204)

    @router.post("/suppressions/check", summary="Is a contact blocked anywhere in Snajp?")
    async def kontrollera(request: Request, kropp: CheckIn, tenant: dict = Depends(kraev("crm:las"))) -> dict:
        """Reads every source together: the suppression list (including domain
        and `all` blocks), records marked do-not-contact (every private person
        is), unsubscribed addresses (email only) and leads that asked not to be
        contacted, matched on email, organisation number or phone number.
        `sources` says which ones blocked: `suppression_list`,
        `record`, `unsubscribed`, `lead`. Nothing about the contact is returned."""
        try:
            svar = await sparr.ar_sparrad(request.app.state.storage, tenant["tenant_id"], epost=kropp.email,
                                          telefon=kropp.phone, orgnr=kropp.org_number,
                                          kanal=_KANAL_IN[kropp.channel])
        except sparr.OgiltigSparr as orsak:
            raise _ogiltig(orsak) from None
        return {"blocked": svar["sparrad"], "sources": [_GRIND_UT[k] for k in svar["kallor"]],
                "suppression_ids": svar["sparr_id"]}

    return router
