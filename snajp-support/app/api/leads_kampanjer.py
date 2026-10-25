"""Kampanjer: massutskick till befintliga listor (Antons beställning 2026-10-25).

En kampanj är ett namn, en ämnesrad och en text. Varje mottagare får "Hej
{förnamn}," (eller "Hej,") och sedan texten, utan research och utan modell.
Mottagarna är en befintlig leadslista, även CRM-kundlistan, eller en körnings
leads. Utkasten köas till granskning genom samma väg som listans utkast
(`_queue_outreach_draft_impl`: textkvalitet, signatur, lagstadgad fot och
språkgrind) och märks med kampanjen (migration 114). Sändspärren släpper då
utkasten till kundens egna kunder, avregistreringen gäller som förut, och
utfallet räknas per kampanj. "Skicka alla" går genom samma sändspärrar som ett
enskilt godkännande.

Definitionen står i leads-inställningarna (`settings.kampanjer`). Förloppet
räknas ur databasen (`storage.kampanjens_poster`), så det syns efter en
omladdning (Antons regel 2026-10-10). Inställningarna skrivs två gånger per
kampanj, vid start och vid slut, och båda gångerna läses de om först.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from ..leads import utkaststatus
from .deps import kraev_uuid, require_tenant

logger = logging.getLogger("snajp-support.api.kampanjer")
router = APIRouter()

#: Mottagare per kampanj. Volymtaket i sändspärren (regel 5) sprider ändå
#: utskicken över dagar; taket här skyddar köningen.
MAX_MOTTAGARE = 1000
#: Står en kampanj som "pågår" så här länge efter starten dog processen mitt i.
_AVBRUTEN_EFTER = timedelta(minutes=30)
_UPPTAGNA = ("vantar", "godkant", "koad")


class KampanjRequest(BaseModel):
    model_config = {"extra": "forbid"}

    namn: str = Field(min_length=1, max_length=80)
    amne: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=3000)
    list_id: str | None = None
    job_id: str | None = None

    @model_validator(mode="after")
    def _en_kalla(self) -> "KampanjRequest":
        if bool(self.list_id) == bool(self.job_id):
            raise ValueError("Välj en lista eller en körning som mottagare.")
        return self


def _kampanjer(settings: dict) -> list[dict]:
    return [k for k in settings.get("kampanjer") or [] if isinstance(k, dict) and k.get("id")]


async def _spara_kampanj(storage, tenant_id: str, kampanj: dict) -> None:
    """Läser om inställningarna och byter bara kampanjens post: en skrivning
    mitt i en annan ändring ska inte radera den."""
    settings = await storage.get_agent_settings(tenant_id, agent_type="leads")
    ovriga = [k for k in _kampanjer(settings) if k["id"] != kampanj["id"]]
    await storage.set_agent_settings(
        tenant_id, agent_type="leads", settings={**settings, "kampanjer": [kampanj, *ovriga][:50]}
    )


def _utfall(poster: list[dict]) -> dict:
    return {
        "koade": len(poster),
        "vantar": sum(1 for p in poster if p.get("status") == "awaiting_review"),
        "skickade": sum(1 for p in poster if p.get("sent_at")),
        "svar": sum(1 for p in poster if p.get("svar")),
        "stoppade": sum(1 for p in poster if p.get("status") == "blocked"),
    }


def _med_lage(kampanj: dict, now: datetime) -> dict:
    if kampanj.get("status") == "pagar":
        try:
            startad = datetime.fromisoformat(str(kampanj.get("skapad")))
        except ValueError:
            startad = now
        if now - startad > _AVBRUTEN_EFTER:
            return {**kampanj, "status": "avbruten"}
    return kampanj


async def _mottagare(storage, tenant_id: str, payload: KampanjRequest) -> tuple[list[dict], str, bool]:
    """(prospekt, källans namn, is_test). En lista lyfts in i prospektregistret
    på samma sätt som listans utkast (`_befordra_listrad`); en körning ger sina
    leads, inte de bortvalda."""
    from .leads import _befordra_listrad

    if payload.list_id:
        kraev_uuid(payload.list_id, "listan")
        lista = await storage.get_lead_list(tenant_id, payload.list_id)
        if not lista:
            raise HTTPException(status_code=404, detail="Listan finns inte.")
        if lista.get("kalla") == "saljlista":
            raise HTTPException(status_code=409, detail="Säljlistan bearbetas i säljlistan, inte i en kampanj.")
        rader = [r for r in await storage.list_lead_list_items(tenant_id, payload.list_id) if (r.get("company_name") or "").strip()]
        prospekt = [(await _befordra_listrad(storage, tenant_id, lista, r))[0] for r in rader[:MAX_MOTTAGARE]]
        return prospekt, str(lista.get("titel") or "Lista"), bool(lista.get("is_test"))
    rad = await storage.get_leads_korning(tenant_id, payload.job_id)
    if rad is None:
        raise HTTPException(status_code=404, detail="Körningen finns inte.")
    ids = list(dict.fromkeys(j["prospect_id"] for j in ((rad.get("korning") or {}).get("jobs") or []) if j.get("prospect_id")))
    prospekt = [p for pid in ids[:MAX_MOTTAGARE] if (p := await storage.get_prospect(tenant_id, pid)) and p.get("niva") != "C"]
    datum = str(rad.get("created_at") or "")[:10]
    return prospekt, f"Körningen {datum}".strip(), bool(rad.get("is_test"))


async def _kor_kampanj(storage, tenant_id: str, kampanj: dict, prospekt: list[dict], is_test: bool) -> None:
    """Köar kampanjens utkast, ett per mottagare med en mejladress. Hoppar
    över de utan säljbar adress och de som redan har ett utkast som väntar
    (köningen hade annars ersatt det)."""
    from ..agent.leads_context import OutreachContext
    from ..agent.leads_tools import _queue_outreach_draft_impl
    from ..leads.discovery import mottagare
    from ..leads.listutkast import HUMANIZER

    hoppade: dict[str, int] = {}

    def hoppa(skal: str) -> None:
        hoppade[skal] = hoppade.get(skal, 0) + 1

    try:
        lagen = utkaststatus.per_prospekt(await storage.utkast_lagen(tenant_id), [p["id"] for p in prospekt])
        sedda: set[str] = set()
        for p in prospekt:
            epost = mottagare(p)
            if not epost:
                hoppa("ingen mejladress")
                continue
            if epost.casefold() in sedda:
                continue
            sedda.add(epost.casefold())
            if (lagen.get(str(p["id"])) or {}).get("utkast_status") in _UPPTAGNA:
                hoppa("har redan ett utkast som väntar")
                continue
            trad = await storage.ensure_outreach_thread(tenant_id, prospect_id=p["id"])
            ctx = OutreachContext(
                storage=storage, tenant_id=tenant_id, thread_id=trad["id"], prospect_email=epost, is_test=is_test
            )
            # Hälsningsraden avgörs vid köningen (halsning.normalisera_utkast):
            # förnamnet när kontakten är styrkt, annars "Hej,".
            svar = json.loads(await _queue_outreach_draft_impl(
                ctx, subject=kampanj["amne"], body=f"Hej,\n\n{kampanj['text'].strip()}",
                language_state=trad.get("language_state") or "sv", humanizer_variant=HUMANIZER,
                force_review=True, kampanj_id=kampanj["id"],
            ))
            if not svar.get("queued"):
                hoppa(str(svar.get("error") or "kunde inte köas")[:120])
        kampanj = {**kampanj, "status": "klar", "hoppade": hoppade}
    except Exception as fel:  # noqa: BLE001 — utfallet ska stå på kampanjen, inte försvinna i loggen
        logger.exception("Kampanjen %s föll", kampanj["id"])
        kampanj = {**kampanj, "status": "fel", "hoppade": hoppade, "fel": str(fel)[:300]}
    await _spara_kampanj(storage, tenant_id, kampanj)


@router.get("/api/leads/kampanjer")
async def lista_kampanjer(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    """Kampanjerna med utfall, och de listor och körningar som kan vara mottagare."""
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    settings = await storage.get_agent_settings(tenant_id, agent_type="leads")
    now = datetime.now(timezone.utc)
    kampanjer = []
    for k in _kampanjer(settings):
        try:
            utfall = _utfall(await storage.kampanjens_poster(tenant_id, k["id"]))
        except Exception:  # noqa: BLE001 — migration 114 saknas: visa kampanjen utan utfall
            logger.exception("Kampanjens utfall kunde inte läsas")
            utfall = None
        kampanjer.append({**_med_lage(k, now), "utfall": utfall})
    listor = [
        {"id": str(l["id"]), "titel": l.get("titel"), "kalla": l.get("kalla"), "antal": l.get("item_count") or 0}
        for l in await storage.list_lead_lists(tenant_id)
        if l.get("kalla") != "saljlista"
    ]
    korningar = [
        {"job_id": r["job_id"], "datum": str(r.get("created_at") or "")[:16], "levererade": (r.get("korning") or {}).get("levererade")}
        for r in (await storage.list_leads_korningar(tenant_id))[:20]
    ]
    return {"kampanjer": kampanjer, "listor": listor, "korningar": korningar}


@router.get("/api/leads/kampanjer/{kampanj_id}")
async def hamta_kampanj(request: Request, kampanj_id: str, tenant: dict = Depends(require_tenant)) -> dict:
    """En kampanj med en rad per mottagare."""
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    kampanj = next((k for k in _kampanjer(await storage.get_agent_settings(tenant_id, agent_type="leads")) if k["id"] == kampanj_id), None)
    if kampanj is None:
        raise HTTPException(status_code=404, detail="Kampanjen finns inte.")
    poster = await storage.kampanjens_poster(tenant_id, kampanj_id)
    return {**_med_lage(kampanj, datetime.now(timezone.utc)), "utfall": _utfall(poster), "poster": poster}


@router.post("/api/leads/kampanjer", status_code=202)
async def skapa_kampanj(request: Request, payload: KampanjRequest, tenant: dict = Depends(require_tenant)) -> dict:
    """Skapar kampanjen och köar dess utkast i bakgrunden. Svarar direkt;
    förloppet läses med GET."""
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    prospekt, kallnamn, is_test = await _mottagare(storage, tenant_id, payload)
    if not prospekt:
        raise HTTPException(status_code=422, detail="Källan har inga bolag att skicka till.")
    kampanj = {
        "id": str(uuid.uuid4()),
        "namn": payload.namn.strip(),
        "amne": payload.amne.strip(),
        "text": payload.text.strip(),
        "kalla": {"list_id": payload.list_id, "job_id": payload.job_id, "namn": kallnamn},
        "skapad": datetime.now(timezone.utc).isoformat(),
        "status": "pagar",
        "totalt": len(prospekt),
    }
    await _spara_kampanj(storage, tenant_id, kampanj)
    uppgift = asyncio.create_task(_kor_kampanj(storage, tenant_id, kampanj, prospekt, is_test))
    # Referensen hålls tills uppgiften är klar; annars kan den skräpsamlas mitt i.
    _uppgifter.add(uppgift)
    uppgift.add_done_callback(_uppgifter.discard)
    return {**kampanj, "utfall": None}


_uppgifter: set[asyncio.Task] = set()


@router.post("/api/leads/kampanjer/{kampanj_id}/skicka")
async def skicka_kampanj(request: Request, kampanj_id: str, tenant: dict = Depends(require_tenant)) -> dict:
    """Godkänn och skicka kampanjens väntande utkast, genom samma väg som ett
    enskilt klick (scheduler.skicka_godkant): tidsgrinden, språkgrinden och de
    sex sändspärrarna. I tur och ordning, inte parallellt."""
    from ..leads.scheduler import skicka_godkant
    from ..leads.send_provider import get_send_provider

    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    provider = get_send_provider()
    utfall: list[dict] = []
    for post in await storage.kampanjens_poster(tenant_id, kampanj_id):
        if post.get("status") != "awaiting_review" or not post.get("queue_item_id"):
            continue
        res, skal = await skicka_godkant(storage, tenant_id, post["queue_item_id"], provider, now=datetime.now(timezone.utc))
        utfall.append({"company_name": post.get("company_name"), "utfall": res, "skal": skal})
    return {
        "skickade": sum(1 for u in utfall if u["utfall"] == "sent"),
        "vantar_pa_fonstret": sum(1 for u in utfall if u["utfall"] == "requeued"),
        "stoppade": [{"company_name": u["company_name"], "skal": u["skal"]} for u in utfall if u["utfall"] not in ("sent", "requeued")],
    }
