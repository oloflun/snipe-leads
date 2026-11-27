"""Snajp CRM i det publika API:t: tidslinjen, utfallen och den samlade kundlistan.

Det som knyter CRM-posten till resten av Snajp. Egen fil för att `crm_v1.py`
inte ska växa sig oläslig. Routern byggs av `koppla(crm_v1)` och inkluderas
därifrån, så grindarna (nyckel, omfång, tillägg, tak, avtal) är desamma.

- Tidslinjen komponeras vid läsning ur CRM:ets händelser, leadsflödet och
  supporten (app/crm/tidslinje.py). Appen (kundens egen nyckel) får utdrag ur
  mejl, samtal och anteckningar. En integrations nyckel får veta att något hänt
  och var det finns, men inte vad som skrevs.
- Ett utfall som sätts på bolaget verkställs också på bolagets leads, och
  leadens läge läses tillbaka på posten (app/crm/utfall.py).
- Kundlistan visar egna kunder och Iris kunder i en lista (app/crm/kundlista.py).
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from ..crm import kundlista, lagring, objekt, tidslinje, utfall
from .deps import kraev_uuid

_TYP_UT = {
    "post_skapad": "record_created", "post_andrad": "record_updated", "post_raderad": "record_deleted",
    "post_aterstalld": "record_restored", "post_tomd": "record_purged",
    "lead_skapad": "lead_created", "status": "lead_status", "mejl_skickat": "email_sent",
    "uppfoljning_skickad": "followup_sent", "svar": "reply_received", "steg": "conversation_stage",
    "mote_bokat": "meeting_booked", "overlamnat": "handed_over", "samtal": "call",
    "anteckning": "note", "uppgift": "task", "supportarende": "support_ticket",
    "aktivitet": "activity", "affar_skapad": "deal_created", "affar_avslutad": "deal_closed",
}
_LANK_UT = {"lead": "lead", "konversation": "conversation", "arende": "ticket",
            "anteckning": "note", "uppgift": "task", "aktivitet": "activity", "affar": "deal"}
_DETALJ_UT = {"fran": "from", "till": "to", "ursprung": "origin", "klass": "reply_class", "nummer": "number",
              "utfall": "outcome", "aterkom": "call_back_on", "klar": "done", "forfaller": "due",
              "kanal": "channel", "kategori": "category", "status": "status", "prioritet": "priority",
              "via": "source", "aktor": "actor",
              "slag": "activity_type", "resultat": "result", "minuter": "duration_minutes", "ansvarig": "owner",
              "forfattare": "author", "fast": "pinned", "belopp": "amount", "valuta": "currency",
              "forlustorsak": "lost_reason", "forlustorsak_kod": "lost_reason_code"}
_AKTIVITET_UT = {"samtal": "call", "mote": "meeting", "mejl": "email", "besok": "visit", "ovrigt": "other"}

_UTFALL_UT = utfall.UTFALL_API
_UTFALL_IN = {v: k for k, v in _UTFALL_UT.items()}
_URSPRUNG_IN = {"all": "alla", "own": "egna", "iris": "iris"}
_URSPRUNG_UT = {"egna": "own", "iris": "iris"}


class OutcomeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal["no_answer", "call_back", "not_interested", "do_not_contact", "meeting_booked", "won"]
    call_back_on: date | None = Field(None, description="Required with `call_back`.")
    note: str | None = Field(None, max_length=2000)


def tidslinjepost_ut(post: dict[str, Any], falt_ut: dict[str, str]) -> dict[str, Any]:
    data = {_DETALJ_UT[k]: v for k, v in post["detalj"].items() if k in _DETALJ_UT}
    if "activity_type" in data:
        data["activity_type"] = _AKTIVITET_UT.get(data["activity_type"], "other")
    if "lost_reason_code" in data:
        data["lost_reason_code"] = objekt.FORLUSTORSAKER.get(data["lost_reason_code"], "other")
    if post["detalj"].get("falt"):
        data["fields"] = [falt_ut.get(f, f) for f in post["detalj"]["falt"]]
    return {"key": post["nyckel"], "type": _TYP_UT.get(post["typ"], post["typ"]), "at": post["tid"],
            "origin": post["kalla"], "title": post["rubrik"], "text": post["text"], "data": data,
            "link": {"kind": _LANK_UT.get(post["lank"]["typ"], post["lank"]["typ"]), "id": post["lank"]["id"]}
            if post["lank"] else None}


def _lead_ut(lead: dict[str, Any]) -> dict[str, Any]:
    return {"id": lead["id"], "name": lead["namn"], "status": lead["status"], "created_at": lead["created_at"]}


def iris_ut(lage: dict[str, Any]) -> dict[str, Any]:
    senaste = lage.get("senaste")
    return {"leads": [_lead_ut(lead) for lead in lage["leads"]],
            "latest": _lead_ut(senaste) if senaste else None,
            "outcome": _UTFALL_UT.get(lage["utfall"]) if lage["utfall"] else None,
            "do_not_contact": lage["kontakta_inte"]}


def koppla(v1: Any) -> APIRouter:
    """Bygger ändpunkterna med `crm_v1`s egna grindar, på en ny router. `v1` är
    modulen `crm_v1` själv: härifrån importeras den inte, eftersom den
    inkluderar den här routern."""
    router = APIRouter(prefix=v1.router.prefix, tags=v1.router.tags)
    kraev, fel = v1.kraev, v1.fel

    async def _post(request: Request, tenant: dict, objekt: str, rad_id: str) -> dict[str, Any]:
        post = await lagring.hamta_post(request.app.state.storage, tenant["tenant_id"], objekt,
                                        kraev_uuid(rad_id, "Posten"))
        if post is None:
            raise fel(404, "not_found", "The record does not exist.", "Posten finns inte.")
        return post

    async def _linje(request: Request, tenant: dict, objekt: str, rad_id: str, limit: int) -> dict:
        post = await _post(request, tenant, objekt, rad_id)
        bygg = {"bolag": tidslinje.for_bolag, "person": tidslinje.for_person, "affar": tidslinje.for_affar}[objekt]
        # Kundens egen nyckel är appen. En nyckel med omfång är en integration.
        med_text = "*" in tenant.get("omfang", ["*"])
        poster = await bygg(request.app.state.storage, tenant["tenant_id"], post, limit=limit, med_text=med_text)
        return {"data": [tidslinjepost_ut(p, v1._FALT_UT) for p in poster]}

    @router.get("/companies/{company_id}/timeline", summary="Everything that has happened with a company, newest first")
    async def tidslinje_bolag(request: Request, company_id: str, limit: int = Query(200, ge=1, le=500),
                              tenant: dict = Depends(kraev("crm:las"))) -> dict:
        """The record's own changes, the work linked to it here (notes,
        activities, tasks and deals), together with what has happened elsewhere
        in Snajp: Iris leads for the same organisation number (emails sent,
        replies, calls, status changes, notes, tasks) and support tickets from
        the company's people. Composed when read; nothing is copied. `origin`
        says where an entry lives: `crm`, `iris` or `support`.

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

    @router.get("/deals/{deal_id}/timeline", summary="Everything that has happened with a deal, newest first")
    async def tidslinje_affar(request: Request, deal_id: str, limit: int = Query(200, ge=1, le=500),
                              tenant: dict = Depends(kraev("crm:las"))) -> dict:
        """The deal's own changes and the notes, activities and tasks linked to
        it. Leads and support tickets belong to the company and the person."""
        return await _linje(request, tenant, "affar", deal_id, limit)

    @router.get("/companies/{company_id}/iris", summary="The company's leads in Iris and what they mean here")
    async def iris_bolag(request: Request, company_id: str, tenant: dict = Depends(kraev("crm:las"))) -> dict:
        """`do_not_contact` is true when the record says so OR when one of the
        company's leads has asked not to be contacted: that outcome always
        wins over a value here that would reopen the lead. `leads` are oldest
        first; `latest` is the most recently created lead (same shape as a
        row in `leads`), or null."""
        bolag = await _post(request, tenant, "bolag", company_id)
        return iris_ut(await utfall.iris_lage(request.app.state.storage, tenant["tenant_id"], bolag))

    @router.post("/companies/{company_id}/outcome", summary="Set an outcome on a company and on its leads")
    async def satt_utfall(request: Request, company_id: str, kropp: OutcomeIn,
                          tenant: dict = Depends(kraev("crm:skriv"))) -> dict:
        """The outcome is carried out in the leads flow as well, by the same
        functions a call from the call list uses: pending sends are stopped,
        the lead changes status, and `do_not_contact` blocks the address.
        `won` makes the company a customer. A company without a lead only
        gets the change on the record itself."""
        await v1._avtal(request, tenant)
        bolag = await _post(request, tenant, "bolag", company_id)
        try:
            svar = await utfall.registrera(
                request.app.state.storage, tenant["tenant_id"], bolag, utfall=_UTFALL_IN[kropp.outcome],
                aterkom_datum=kropp.call_back_on, anteckning=kropp.note, **v1._ursprung(request, tenant))
        except utfall.OgiltigtUtfall:
            raise fel(422, "call_back_date_required", "call_back needs call_back_on.",
                      "Återkom kräver ett datum i call_back_on.") from None
        return {"company": v1.bolag_ut(svar["bolag"]), "lead_ids": svar["leads"]}

    @router.get("/customers", summary="Your own customers and the ones Iris has won, in one list")
    async def kunder(
        request: Request, tenant: dict = Depends(kraev("crm:las")),
        origin: Literal["all", "own", "iris"] = Query("all", description="`own` are the companies you keep here "
                                                      "with the relation customer. `iris` are leads Iris has won."),
        q: str | None = Query(None, max_length=200),
        limit: int = Query(200, ge=1, le=2000),
    ) -> dict:
        """Composed when read: a won lead is not copied into the register. A
        lead that is the same company as one of your own customers is listed
        once, as `own`, with `lead_id` beside it."""
        svar = await kundlista.lista(request.app.state.storage, tenant["tenant_id"],
                                     ursprung=_URSPRUNG_IN[origin], q=q, limit=limit)
        return {"data": [{"origin": _URSPRUNG_UT[r["ursprung"]], "company_id": r["bolag_id"], "lead_id": r["lead_id"],
                          "name": r["namn"], "org_number": r["orgnr"], "customer_since": r["kund_sedan"],
                          "private_person": r["privatperson"]} for r in svar["kunder"]],
                "counts": {"own": svar["antal"]["egna"], "iris": svar["antal"]["iris"]}}

    return router
