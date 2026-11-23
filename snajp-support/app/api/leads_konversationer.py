"""Leads › Konversationer (Antons beställning 2026-11-22): listan, tråden,
utkaststudion, stegen och notiserna.

Kunderna köper i första hand de nya konversationerna. Förut låg svaren som
filtret "Svarat" under Inkorg › Skickat, svarsutkasten syntes ingenstans och
ett nytt svar kasserade det väntande utkastet tyst. Här:

* GET  /api/leads/konversationer              listan med räknare per filter
* GET  /api/leads/konversationer/{tråd}        hela tråden, utkastet och loggen
* POST /api/leads/konversationer/{tråd}/last   tråden öppnad: notiserna lästa
* PUT  /api/leads/konversationer/{tråd}/utkast         spara ämne och text
* POST /api/leads/konversationer/{tråd}/utkast/skicka  Godkänn och skicka
* POST /api/leads/konversationer/{tråd}/utkast/kassera
* POST /api/leads/konversationer/{tråd}/utkast/{mejl}/aterstall
* POST /api/leads/konversationer/{tråd}/utkast/generera  Skriv om (bakgrund)
* POST /api/leads/konversationer/{tråd}/steg
* POST /api/leads/konversationer/{tråd}/extern  mejl utanför Snajp, för hand
* GET  /api/leads/notiser, GET /api/leads/notiser/antal, POST /api/leads/notiser/last

En människa godkänner alltid: inget här skickar utan att någon valt Skicka,
och ett utkast som påstår en handling ("jag har skickat en inbjudan") skickas
bara när människan bekräftat att handlingen är gjord.

Webbplatsbedömningen (projektregeln 2026-10-08) finns inte i något svar här:
fälten väljs ett och ett, aldrig prospektets hela rad.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..jobs import bakgrund
from ..leads import konversation
from ..leads.signatur import dela_utkast
from ..leads.signatur import normalisera as normalisera_signatur
from .deps import kraev_uuid, require_tenant

logger = logging.getLogger("snajp-support.leads")

router = APIRouter()

#: Filtren i listan, i den ordning de visas. `att_gora` är standard.
FILTER = ("att_gora", "alla", "utkast", *konversation.STEG)


class UtkastRequest(BaseModel):
    model_config = {"extra": "forbid"}

    subject: str = Field(..., min_length=1, max_length=200)
    brodtext: str = Field(..., min_length=1, max_length=8000)


class SkickaRequest(BaseModel):
    model_config = {"extra": "forbid"}

    #: Människan har kontrollerat att handlingarna utkastet påstår är gjorda.
    bekraftat_handlingar: bool = False


class GenereraRequest(BaseModel):
    model_config = {"extra": "forbid"}

    instruktion: str | None = Field(default=None, max_length=1000)


class StegRequest(BaseModel):
    model_config = {"extra": "forbid"}

    steg: Literal["svarat", "mote", "aterkom", "ej_intresserad", "kontakta_inte"]
    aterkom_datum: date | None = None


class ExternRequest(BaseModel):
    model_config = {"extra": "forbid"}

    riktning: Literal["outbound", "inbound"] = "outbound"
    text: str = Field(..., min_length=1, max_length=8000)
    amne: str | None = Field(default=None, max_length=200)
    tid: datetime | None = None


class LastRequest(BaseModel):
    model_config = {"extra": "forbid"}

    ids: list[str] | None = Field(default=None, max_length=500)


def _iso(varde: Any) -> Any:
    return varde.isoformat() if hasattr(varde, "isoformat") else varde


def _utdrag(text: str | None, langd: int = 220) -> str:
    """Svarets egen text utan citatet, på en rad."""
    from ..leads.konversation import _HUVUD, _SKREV

    rad = str(text or "")
    for huvud in _HUVUD.finditer(rad):
        if _SKREV.search(huvud.group("rad")):
            rad = rad[: huvud.start()]
            break
    rad = " ".join(rad.split())
    return rad[:langd] + ("…" if len(rad) > langd else "")


def _listrad(rad: dict[str, Any], idag: date) -> dict[str, Any]:
    utkast_body = str(rad.get("utkast_body") or "")
    return {
        "thread_id": str(rad["thread_id"]),
        "prospect_id": str(rad["prospect_id"]),
        "company_name": rad.get("company_name"),
        "contact_name": rad.get("contact_name"),
        "contact_email": rad.get("contact_email"),
        "steg": konversation.steg(rad),
        "svarsklass": rad.get("svarsklass"),
        "aterkom_datum": _iso(rad.get("aterkom_datum")),
        "aterkom_forfallet": konversation.aterkom_forfallet(rad, idag),
        "senaste_svar": (
            {"utdrag": _utdrag(rad.get("svar_body")), "tid": _iso(rad.get("svar_at"))} if rad.get("svar_id") else None
        ),
        "utkast": (
            {
                "message_id": str(rad["utkast_id"]),
                "subject": rad.get("utkast_subject"),
                "tid": _iso(rad.get("utkast_at")),
                "flaggat": bool(konversation.handlingspastaenden(dela_utkast(utkast_body, None)[0])),
            }
            if rad.get("utkast_id")
            else None
        ),
        "olasta": int(rad.get("olasta") or 0),
        "antal_meddelanden": int(rad.get("antal_meddelanden") or 0),
        "att_gora": konversation.att_gora(rad, idag),
        "senast": _iso(
            max(
                (t for t in (rad.get("svar_at"), rad.get("senaste_handelse_at"), rad.get("senast_skickat_at"), rad.get("utkast_at")) if t),
                key=lambda t: konversation._som_tid(t),
                default=None,
            )
        ),
    }


@router.get("/api/leads/konversationer")
async def lista(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    """Konversationerna, senast aktiva först, med räknare per filter.
    Filtreringen görs i vyn: listan är kort (de bolag som svarat), och
    räknarna ska stämma med det som visas."""
    idag = datetime.now(timezone.utc).date()
    rader = [_listrad(r, idag) for r in await request.app.state.storage.konversationstradar(tenant["tenant_id"])]
    rader.sort(key=lambda r: konversation._som_tid(r["senast"] or "1970-01-01"), reverse=True)
    antal = {f: 0 for f in FILTER}
    for r in rader:
        antal["alla"] += 1
        antal[r["steg"]] += 1
        antal["att_gora"] += r["att_gora"]
        antal["utkast"] += r["utkast"] is not None
    return {
        "konversationer": rader,
        "antal": antal,
        "sammanfattning": {
            "nya_svar": sum(1 for r in rader if r["olasta"] and r["senaste_svar"]),
            "utkast_vantar": antal["utkast"],
            "moten": antal["mote"],
            "aterkom_idag": sum(1 for r in rader if r["aterkom_forfallet"]),
        },
    }


async def _kraev_trad(storage, tenant_id: str, thread_id: str) -> tuple[dict, dict]:
    kraev_uuid(thread_id, "Konversationen")
    trad = await storage.get_outreach_thread(tenant_id, thread_id)
    if trad is None or not trad.get("prospect_id"):
        raise HTTPException(status_code=404, detail="Konversationen finns inte.")
    prospekt = await storage.get_prospect(tenant_id, str(trad["prospect_id"]))
    if prospekt is None:
        raise HTTPException(status_code=404, detail="Konversationen finns inte.")
    return trad, prospekt


def _meddelande(m: dict[str, Any]) -> dict[str, Any]:
    if m.get("direction") == "inbound":
        typ = "svar"
    elif m.get("sent_at"):
        typ = "skickat"
    elif m.get("kasserad_at"):
        typ = "kasserat"
    else:
        typ = "utkast"
    return {
        "id": str(m["id"]),
        "typ": typ,
        "subject": m.get("subject"),
        "body": m.get("body") or "",
        "tid": _iso(m.get("sent_at") or m.get("created_at")),
        "kasserad_at": _iso(m.get("kasserad_at")),
    }


@router.get("/api/leads/konversationer/{thread_id}")
async def trad(request: Request, thread_id: str, tenant: dict = Depends(require_tenant)) -> dict:
    """Hela konversationen: mejlen i tidsordning (våra, deras, kasserade
    utkast och mejl utanför Snajp), samtalen, händelseloggen och det väntande
    utkastet med det som behöver kontrolleras. Läser bara; att öppna tråden
    markerar notiserna lästa via POST …/last."""
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    trad_rad, prospekt = await _kraev_trad(storage, tenant_id, thread_id)
    meddelanden = await storage.list_outreach_messages(tenant_id, thread_id)
    handelser = await storage.list_handelser(tenant_id, thread_id=thread_id)
    samtal = await storage.list_lead_samtal(tenant_id, prospect_id=str(prospekt["id"]))
    installningar = await storage.get_agent_settings(tenant_id, agent_type="leads")
    sig = normalisera_signatur(installningar.get("signatur"))

    externa = konversation.externa_ur_citat(meddelanden, prospekt_epost=prospekt.get("contact_email"))
    for h in handelser:
        if h.get("typ") == "extern":
            d = h.get("detalj") or {}
            externa.append({
                "nyckel": str(h["id"]), "kalla": "manuell", "riktning": d.get("riktning") or "outbound",
                "avsandare": None, "text": d.get("text") or "", "amne": d.get("amne"),
                "tid": d.get("tid") or _iso(h.get("created_at")), "tid_ur_citat": False,
            })
    externa.sort(key=lambda e: konversation._som_tid(e["tid"]))

    vantande = next(
        (m for m in reversed(meddelanden)
         if m.get("direction") == "outbound" and not m.get("sent_at") and not m.get("kasserad_at")),
        None,
    )
    utkast = None
    if vantande:
        brodtext, svans = dela_utkast(vantande.get("body") or "", sig)
        poster = await storage.list_pending_sends(tenant_id, thread_id)
        utkast = {
            "message_id": str(vantande["id"]),
            "subject": vantande.get("subject") or "",
            "brodtext": brodtext,
            "svans": svans,
            "tid": _iso(vantande.get("created_at")),
            "handlingar": konversation.handlingspastaenden(brodtext),
            "ko_status": poster[-1].get("status") if poster else None,
        }

    rad = {**trad_rad, "status": prospekt.get("status")}
    egna_texter = [m.get("body") or "" for m in meddelanden if m.get("direction") == "outbound" and m.get("sent_at")]
    svar: dict[str, Any] = {
        "trad": {
            "id": str(trad_rad["id"]),
            "prospect_id": str(prospekt["id"]),
            "company_name": prospekt.get("company_name"),
            "contact_name": prospekt.get("contact_name"),
            "contact_role": prospekt.get("contact_role"),
            "contact_email": prospekt.get("contact_email"),
            "contact_phone": prospekt.get("contact_phone"),
            "website": prospekt.get("website"),
            "status": prospekt.get("status"),
            "steg": konversation.steg(rad),
            "svarsklass": trad_rad.get("svarsklass"),
            "aterkom_datum": _iso(trad_rad.get("aterkom_datum")),
        },
        "meddelanden": [_meddelande(m) for m in meddelanden],
        "externa": [{**e, "tid": _iso(e["tid"])} for e in externa],
        "samtal": [
            {"id": str(s["id"]), "utfall": s["utfall"], "anteckning": s.get("anteckning"),
             "aterkom_datum": _iso(s.get("aterkom_datum")), "tid": _iso(s["created_at"])}
            for s in samtal
        ],
        "handelser": [
            {"id": str(h["id"]), "typ": h["typ"], "kalla": h.get("kalla"), "detalj": h.get("detalj") or {},
             "tid": _iso(h["created_at"]), "olast": bool(h.get("notis") and not h.get("last_at"))}
            for h in handelser
        ],
        "utkast": utkast,
        # Dags att höra av sig igen (Återkom eller återkontakten efter ett nej).
        "aterkom_forfallet": konversation.aterkom_forfallet(
            {**rad, "aterkom_datum": trad_rad.get("aterkom_datum")}, datetime.now(timezone.utc).date()
        ),
        "generering": konversation.generering(handelser, nu=datetime.now(timezone.utc)),
        # Ett förslag, aldrig ett stegbyte: säger ett mejl utanför Snajp
        # eller ett skickat mejl att ett möte bokats, frågar vyn om steget.
        "forslag_mote": konversation.steg(rad) != "mote" and konversation.ser_ut_som_bokat_mote(
            [e["text"] for e in externa if e["riktning"] == "outbound"] + egna_texter[-2:]
        ),
    }
    if sig:
        from ..leads.signatur import bygg_signaturtext

        svar["signatur"] = {**sig, "text": bygg_signaturtext(sig)}
    return svar


@router.post("/api/leads/konversationer/{thread_id}/last")
async def last(request: Request, thread_id: str, tenant: dict = Depends(require_tenant)) -> dict:
    storage = request.app.state.storage
    await _kraev_trad(storage, tenant["tenant_id"], thread_id)
    antal = await storage.markera_notiser_lasta(tenant["tenant_id"], thread_id=thread_id)
    return {"lasta": antal, "olasta": await storage.antal_olasta_notiser(tenant["tenant_id"])}


@router.put("/api/leads/konversationer/{thread_id}/utkast")
async def spara_utkast(
    request: Request, thread_id: str, payload: UtkastRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Sparar ämne och brödtext i det väntande utkastet. Signaturen och den
    lagstadgade foten är kodens text och följer med (leads.spara_utkasttext)."""
    from .leads import spara_utkasttext

    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    _, prospekt = await _kraev_trad(storage, tenant_id, thread_id)
    meddelande = await spara_utkasttext(
        storage, tenant_id, thread_id, amne=payload.subject.strip(), text=payload.brodtext.strip()
    )
    await konversation.logga(
        storage, tenant_id, prospect_id=str(prospekt["id"]), thread_id=thread_id, typ="utkast_redigerat",
        kalla="manuell", detalj={"message_id": str(meddelande["id"])},
    )
    return {"message_id": str(meddelande["id"]), "handlingar": konversation.handlingspastaenden(payload.brodtext)}


@router.post("/api/leads/konversationer/{thread_id}/utkast/skicka")
async def skicka(
    request: Request, thread_id: str, payload: SkickaRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Godkänn och skicka svarsutkastet, genom samma grindar som
    granskningskön (scheduler.skicka_godkant). Saknar utkastet en aktiv
    köpost (återställt, eller posten inställd) skapas en som väntar på
    granskning, så att godkännandet har något att godkänna."""
    from ..leads.scheduler import skicka_godkant
    from ..leads.send_provider import get_send_provider
    from .leads import _UTFALL_TEXT

    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    _, prospekt = await _kraev_trad(storage, tenant_id, thread_id)
    meddelande = await storage.get_pending_outreach_message(tenant_id, thread_id)
    if meddelande is None:
        raise HTTPException(status_code=409, detail="Konversationen har inget utkast att skicka.")
    installningar = await storage.get_agent_settings(tenant_id, agent_type="leads")
    brodtext, _ = dela_utkast(meddelande.get("body") or "", normalisera_signatur(installningar.get("signatur")))
    handlingar = konversation.handlingspastaenden(brodtext)
    if handlingar and not payload.bekraftat_handlingar:
        raise HTTPException(
            status_code=409,
            detail="Utkastet påstår att något redan är gjort. Kontrollera det och bekräfta innan du skickar.",
        )
    poster = await storage.list_pending_sends(tenant_id, thread_id)
    post = poster[-1] if poster else await storage.ny_granskningspost(
        tenant_id, thread_id, scheduled_at=datetime.now(timezone.utc)
    )
    utfall, skal = await skicka_godkant(
        storage, tenant_id, str(post["id"]), get_send_provider(), now=datetime.now(timezone.utc)
    )
    if utfall == "saknas":
        raise HTTPException(status_code=404, detail="Utkastet finns inte.")
    besked = _UTFALL_TEXT.get(utfall, utfall)
    if skal and utfall in ("blocked", "awaiting_review", "sandfel", "requeued"):
        besked = f"{besked}: {skal}"
    if utfall in ("sent", "requeued"):
        # En återkontakt som gått ut är gjord: datumet tas bort, så att
        # konversationen inte står som "dags" igen. Svarar de nej en andra
        # gång spärras adressen (app/leads/svar.py).
        trad_nu = await storage.get_outreach_thread(tenant_id, thread_id) or {}
        if trad_nu.get("aterkom_datum"):
            await storage.satt_trad_steg(tenant_id, thread_id, steg=trad_nu.get("steg"), aterkom_datum=None)
        await konversation.logga(
            storage, tenant_id, prospect_id=str(prospekt["id"]), thread_id=thread_id, typ="skickat",
            kalla="manuell",
            detalj={"message_id": str(meddelande["id"]), "utfall": utfall, "bekraftat_handlingar": bool(handlingar)},
        )
    return {"utfall": utfall, "besked": besked, "skal": skal}


@router.post("/api/leads/konversationer/{thread_id}/utkast/kassera")
async def kassera(request: Request, thread_id: str, tenant: dict = Depends(require_tenant)) -> dict:
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    _, prospekt = await _kraev_trad(storage, tenant_id, thread_id)
    meddelande = await storage.get_pending_outreach_message(tenant_id, thread_id)
    if meddelande is None:
        raise HTTPException(status_code=409, detail="Konversationen har inget utkast att kassera.")
    for post in await storage.list_pending_sends(tenant_id, thread_id):
        await storage.update_send_queue_status(
            tenant_id, str(post["id"]), status="cancelled",
            gate_checks={"rejected_by": "human", "via": "konversationen"},
        )
    await storage.cancel_pending_sends(tenant_id, thread_id)
    await konversation.logga(
        storage, tenant_id, prospect_id=str(prospekt["id"]), thread_id=thread_id, typ="utkast_kasserat",
        kalla="manuell", detalj={"message_id": str(meddelande["id"]), "orsak": "manuellt"},
    )
    return {"kasserat": str(meddelande["id"])}


@router.post("/api/leads/konversationer/{thread_id}/utkast/{message_id}/aterstall")
async def aterstall(
    request: Request, thread_id: str, message_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    """Tar tillbaka ett kasserat utkast. Ett väntande utkast i tråden
    kasseras först (en tråd har ett nästa steg i taget) och syns då i sin tur
    som kasserat. Det återställda får en ny köpost som väntar på granskning."""
    kraev_uuid(message_id, "Utkastet")
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    _, prospekt = await _kraev_trad(storage, tenant_id, thread_id)
    kandidat = next(
        (m for m in await storage.list_outreach_messages(tenant_id, thread_id) if str(m["id"]) == message_id),
        None,
    )
    if kandidat is None or kandidat.get("direction") != "outbound" or kandidat.get("sent_at") or not kandidat.get("kasserad_at"):
        raise HTTPException(status_code=409, detail="Det här utkastet går inte att återställa.")
    vantande = await storage.get_pending_outreach_message(tenant_id, thread_id)
    await storage.cancel_pending_sends(tenant_id, thread_id)
    if vantande:
        await konversation.logga(
            storage, tenant_id, prospect_id=str(prospekt["id"]), thread_id=thread_id, typ="utkast_kasserat",
            kalla="manuell", detalj={"message_id": str(vantande["id"]), "orsak": "aterstallning"},
        )
    if not await storage.aterstall_utkast(tenant_id, thread_id, message_id):
        raise HTTPException(status_code=409, detail="Det här utkastet går inte att återställa.")
    await storage.ny_granskningspost(tenant_id, thread_id, scheduled_at=datetime.now(timezone.utc))
    await konversation.logga(
        storage, tenant_id, prospect_id=str(prospekt["id"]), thread_id=thread_id, typ="utkast_aterstallt",
        kalla="manuell", detalj={"message_id": message_id},
    )
    return {"aterstallt": message_id}


@router.post("/api/leads/konversationer/{thread_id}/utkast/generera", status_code=202)
async def generera(
    request: Request, thread_id: str, payload: GenereraRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Skriv om: Iris skriver ett nytt svarsutkast i bakgrunden. Förloppet
    står i händelseloggen (generering_startad, sedan utkast eller
    generering_fel), så vyn visar det också efter en omladdning."""
    from .leads import _kraev_leads_budget, _require_live_llm, build_context_pack

    _require_live_llm()
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    _, prospekt = await _kraev_trad(storage, tenant_id, thread_id)
    if konversation.generering(await storage.list_handelser(tenant_id, thread_id=thread_id),
                               nu=datetime.now(timezone.utc))["pagar"]:
        return {"pagar": True}
    await _kraev_leads_budget(storage, tenant_id)
    prospect_id = str(prospekt["id"])
    await konversation.logga(
        storage, tenant_id, prospect_id=prospect_id, thread_id=thread_id, typ="generering_startad",
        kalla="manuell", detalj={"instruktion": (payload.instruktion or "").strip()[:300] or None},
    )

    async def arbete(_forlopp: bakgrund.Forlopp) -> dict[str, Any]:
        from ..leads.svar import generera_svarsutkast

        try:
            context_pack, _ = await build_context_pack(storage, tenant_id)
            skrivet = await generera_svarsutkast(
                storage, tenant_id, thread_id=thread_id, tenant_name=tenant["tenant_name"],
                context_pack=context_pack, instruktion=payload.instruktion,
            )
        except Exception as fel:  # noqa: BLE001 — felet ska stå i konversationen, inte bara i loggen
            logger.exception("Omskrivningen av svarsutkastet i tråd %s föll", thread_id)
            await konversation.logga(
                storage, tenant_id, prospect_id=prospect_id, thread_id=thread_id, typ="generering_fel",
                detalj={"fel": str(fel) if isinstance(fel, ValueError) else bakgrund.ALLMANT_FEL},
            )
            raise
        if skrivet.get("queued"):
            ny = await storage.get_pending_outreach_message(tenant_id, thread_id)
            await konversation.logga(
                storage, tenant_id, prospect_id=prospect_id, thread_id=thread_id, typ="utkast",
                detalj={"message_id": str((ny or {}).get("id") or ""), "omskrivet": True}, last=True,
            )
        else:
            fel = skrivet.get("fel") or (
                "Iris stoppade utkastet: det innehöll påståenden som inte går att belägga. Skriv svaret själv "
                "eller försök igen med ett önskemål."
            )
            await konversation.logga(
                storage, tenant_id, prospect_id=prospect_id, thread_id=thread_id, typ="generering_fel",
                detalj={"fel": fel},
            )
        return {"queued": bool(skrivet.get("queued"))}

    job_id, pagar = await bakgrund.starta(request.app.state, tenant_id, f"konversation:{thread_id}", arbete)
    return {"job_id": job_id, "pagar": True}


@router.post("/api/leads/konversationer/{thread_id}/steg")
async def byt_steg(
    request: Request, thread_id: str, payload: StegRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    trad_rad, prospekt = await _kraev_trad(storage, tenant_id, thread_id)
    if payload.steg == "aterkom" and payload.aterkom_datum is None:
        raise HTTPException(status_code=422, detail="Återkom kräver ett datum.")
    return await konversation.satt_steg(
        storage, tenant_id, thread=trad_rad, prospect=prospekt, nytt=payload.steg,
        aterkom_datum=payload.aterkom_datum,
    )


@router.post("/api/leads/konversationer/{thread_id}/extern", status_code=201)
async def extern(
    request: Request, thread_id: str, payload: ExternRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Ett mejl som skickats eller tagits emot utanför Snajp (Sebastians Gmail)
    och inte syns i något citat: in för hand, så att tråden är hel. Det blir
    ingen rad i outreach_messages; det skickades inte härifrån och ska inte
    räknas som ett utskick (takt, karens, mätning)."""
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    _, prospekt = await _kraev_trad(storage, tenant_id, thread_id)
    tid = payload.tid or datetime.now(timezone.utc)
    if tid.tzinfo is None:
        tid = tid.replace(tzinfo=konversation.STOCKHOLM)
    await storage.logga_handelse(
        tenant_id, prospect_id=str(prospekt["id"]), thread_id=thread_id, typ="extern", kalla="manuell",
        detalj={"riktning": payload.riktning, "text": payload.text.strip(), "amne": (payload.amne or "").strip() or None,
                "tid": tid.astimezone(timezone.utc).isoformat()},
    )
    return {"ok": True}


# -- Notiserna ----------------------------------------------------------------


@router.get("/api/leads/notiser")
async def notiser(request: Request, limit: int = 30, tenant: dict = Depends(require_tenant)) -> dict:
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    rader = await storage.list_notiser(tenant_id, limit=max(1, min(limit, 100)))
    return {
        "notiser": [
            {"id": str(r["id"]), "typ": r["typ"], "tid": _iso(r["created_at"]), "last": bool(r.get("last_at")),
             "thread_id": str(r["thread_id"]) if r.get("thread_id") else None,
             "prospect_id": str(r["prospect_id"]), "company_name": r.get("company_name"),
             "klass": (r.get("detalj") or {}).get("klass"),
             # Svaret var öppnat men obesvarat i brevlådan när utkastet skrevs.
             "oppnat": bool((r.get("detalj") or {}).get("oppnat"))}
            for r in rader
        ],
        "olasta": await storage.antal_olasta_notiser(tenant_id),
    }


@router.get("/api/leads/notiser/antal")
async def notisantal(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    """Räknaren i navigationen. Före migration 149 i en miljö: noll, inte ett fel."""
    try:
        return {"olasta": await request.app.state.storage.antal_olasta_notiser(tenant["tenant_id"])}
    except Exception:  # noqa: BLE001
        logger.exception("Notisräknaren gick inte att läsa")
        return {"olasta": 0}


@router.post("/api/leads/notiser/last")
async def notiser_lasta(request: Request, payload: LastRequest, tenant: dict = Depends(require_tenant)) -> dict:
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    for i in payload.ids or []:
        kraev_uuid(i, "Notisen")
    antal = await storage.markera_notiser_lasta(tenant_id, ids=payload.ids)
    return {"lasta": antal, "olasta": await storage.antal_olasta_notiser(tenant_id)}
