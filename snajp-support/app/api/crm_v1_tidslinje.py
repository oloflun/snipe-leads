"""Snajp CRM: postens tidslinje i det publika API:t (/api/crm/v1).

Egen fil för att `crm_v1.py` inte ska växa sig oläslig. Routern inkluderas
därifrån, så specifikationen och grindarna är desamma.

Tidslinjen komponeras vid läsning ur CRM:ets händelser, leadsflödet och
supporten (app/crm/tidslinje.py). Appen (kundens egen nyckel) får utdrag ur
mejl, samtal och anteckningar. En integrations nyckel får veta att något hänt
och var det finns, men inte vad som skrevs.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from ..crm import lagring, tidslinje
from .deps import kraev_uuid

_TYP_UT = {
    "post_skapad": "record_created", "post_andrad": "record_updated", "post_raderad": "record_deleted",
    "post_aterstalld": "record_restored", "post_tomd": "record_purged",
    "lead_skapad": "lead_created", "status": "lead_status", "mejl_skickat": "email_sent",
    "uppfoljning_skickad": "followup_sent", "svar": "reply_received", "steg": "conversation_stage",
    "mote_bokat": "meeting_booked", "overlamnat": "handed_over", "samtal": "call",
    "anteckning": "note", "uppgift": "task", "supportarende": "support_ticket",
}
_LANK_UT = {"lead": "lead", "konversation": "conversation", "arende": "ticket"}
_DETALJ_UT = {"fran": "from", "till": "to", "ursprung": "origin", "klass": "reply_class", "nummer": "number",
              "utfall": "outcome", "aterkom": "call_back_on", "klar": "done", "forfaller": "due",
              "kanal": "channel", "kategori": "category", "status": "status", "prioritet": "priority",
              "via": "source", "aktor": "actor"}


def tidslinjepost_ut(post: dict[str, Any], falt_ut: dict[str, str]) -> dict[str, Any]:
    data = {_DETALJ_UT[k]: v for k, v in post["detalj"].items() if k in _DETALJ_UT}
    if post["detalj"].get("falt"):
        data["fields"] = [falt_ut.get(f, f) for f in post["detalj"]["falt"]]
    return {"key": post["nyckel"], "type": _TYP_UT.get(post["typ"], post["typ"]), "at": post["tid"],
            "origin": post["kalla"], "title": post["rubrik"], "text": post["text"], "data": data,
            "link": {"kind": _LANK_UT.get(post["lank"]["typ"], post["lank"]["typ"]), "id": post["lank"]["id"]}
            if post["lank"] else None}


def koppla(kraev, fel, falt_ut: dict[str, str]) -> APIRouter:
    """Bygger ändpunkterna med `crm_v1`s egna grindar, på en ny router. Anropas
    från `crm_v1.py`, så att grindarna inte kan glida isär."""
    router = APIRouter()

    async def _linje(request: Request, tenant: dict, objekt: str, rad_id: str, limit: int) -> dict:
        storage = request.app.state.storage
        post = await lagring.hamta_post(storage, tenant["tenant_id"], objekt, kraev_uuid(rad_id, "Posten"))
        if post is None:
            raise fel(404, "not_found", "The record does not exist.", "Posten finns inte.")
        bygg = tidslinje.for_bolag if objekt == "bolag" else tidslinje.for_person
        # Kundens egen nyckel är appen. En nyckel med omfång är en integration.
        med_text = "*" in tenant.get("omfang", ["*"])
        poster = await bygg(storage, tenant["tenant_id"], post, limit=limit, med_text=med_text)
        return {"data": [tidslinjepost_ut(p, falt_ut) for p in poster]}

    @router.get("/companies/{company_id}/timeline", summary="Everything that has happened with a company, newest first")
    async def tidslinje_bolag(request: Request, company_id: str, limit: int = Query(200, ge=1, le=500),
                              tenant: dict = Depends(kraev("crm:las"))) -> dict:
        """The record's own changes, together with what has happened elsewhere
        in Snajp: Iris leads for the same organisation number (emails sent,
        replies, calls, status changes, notes, tasks) and support tickets from
        the company's people. Composed when read; nothing is copied.

        Drafts that were never sent are not history and are left out. Support
        tickets carry subject, channel and status, never the messages. A key
        with scopes gets no excerpts (`text` is null): it learns that
        something happened and where, not what was written."""
        return await _linje(request, tenant, "bolag", company_id, limit)

    @router.get("/people/{person_id}/timeline", summary="Everything that has happened with a person, newest first")
    async def tidslinje_person(request: Request, person_id: str, limit: int = Query(200, ge=1, le=500),
                               tenant: dict = Depends(kraev("crm:las"))) -> dict:
        """Matched on the person's exact email address: leads where the person
        is the contact, and the person's own support tickets."""
        return await _linje(request, tenant, "person", person_id, limit)

    return router
