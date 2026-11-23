"""Leads Suite (plan del F, Fas 10): tidslinje, anteckningar, uppgifter,
sparade vyer och CSV-import ovanpå prospektregistret.

Egen modul och inte fler rader i leads.py: det här är CRM-ytan runt
prospektet, inte Iris körningar. Tidslinjen är ingen tabell — den komponeras
här ur det som redan finns (prospektet, statusloggen, mejltråden,
anteckningarna, uppgifterna), så den kan aldrig visa något annat än källorna.
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import date, datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from ..leads import crm_synk, samtal, upptagna
from .deps import kraev_uuid, require_tenant

router = APIRouter()

#: Hur mycket av ett mejl tidslinjen visar. Hela tråden finns i inkorgen.
_MEJLUTDRAG = 300


class AnteckningRequest(BaseModel):
    model_config = {"extra": "forbid"}

    text: str = Field(..., min_length=1, max_length=4000)


class UppgiftRequest(BaseModel):
    model_config = {"extra": "forbid"}

    titel: str = Field(..., min_length=1, max_length=300)
    forfaller: date | None = None


class UppgiftPatchRequest(BaseModel):
    model_config = {"extra": "forbid"}

    klar: bool


class SamtalRequest(BaseModel):
    model_config = {"extra": "forbid"}

    utfall: samtal.Utfall
    aterkom_datum: date | None = None
    anteckning: str | None = Field(default=None, max_length=4000)


class VyRequest(BaseModel):
    model_config = {"extra": "forbid"}

    namn: str = Field(..., min_length=1, max_length=100)
    filter: dict[str, Any] = Field(default_factory=dict)


class Importrad(BaseModel):
    """En CSV-rad efter kolumnmappningen i webbläsaren. `company_name` är
    valfritt HÄR med flit: en rad utan bolagsnamn ska räknas som överhoppad,
    inte fälla hela importen med 422."""

    company_name: str | None = Field(default=None, max_length=200)
    orgnr: str | None = Field(default=None, max_length=200)
    contact_name: str | None = Field(default=None, max_length=200)
    contact_role: str | None = Field(default=None, max_length=200)
    contact_email: str | None = Field(default=None, max_length=200)
    contact_phone: str | None = Field(default=None, max_length=200)
    website: str | None = Field(default=None, max_length=200)
    status: str | None = Field(default=None, max_length=200)
    ort: str | None = Field(default=None, max_length=200)
    #: Avtalets slutdatum (migration 152), `YYYY-MM-DD`. Ett värde som inte
    #: går att tolka blir null — det fäller aldrig importen.
    avtalsslut: Any = None
    #: Filens omappade kolumner, rubrik → värde (152). Överskottet kortas
    #: eller släpps i importera(), aldrig 422.
    extra: dict[str, Any] | None = None


#: En lista bär högst så här många importerade rader, alla delar sammanräknade.
MAX_IMPORTRADER = 5000
#: Importkvittot (lead_lists.importinfo) får vara högst så här stort som JSON.
MAX_IMPORTINFO_BYTE = 20_000
_EXTRA_MAX_NYCKLAR, _EXTRA_MAX_NYCKEL, _EXTRA_MAX_VARDE = 40, 100, 500


class ImportRequest(BaseModel):
    #: Krävs när importen skapar listan; en fortsättning (`list_id`) har redan en.
    titel: str | None = Field(default=None, min_length=1, max_length=200)
    rader: list[Importrad] = Field(..., min_length=1, max_length=MAX_IMPORTRADER)
    #: 'import' = leads från ett annat CRM, att bearbeta. 'crm' = kundens
    #: BEFINTLIGA kunder (migration 098): utesluts av Iris och listbygget och
    #: prospekteras aldrig.
    kalla: Literal["import", "crm"] = "import"
    #: Fortsätt fylla en lista som en tidigare del av samma import skapade.
    list_id: str | None = None
    #: Importens kvitto (152). Sparas på listan; med `list_id` ersätter det det sparade.
    importinfo: dict[str, Any] | None = None
    #: Ta med bolag som redan är leads (prospekt eller i en annan lista).
    ta_med_leads: bool = False


class GranskaRad(BaseModel):
    company_name: str | None = Field(default=None, max_length=200)
    orgnr: str | None = Field(default=None, max_length=200)
    contact_email: str | None = Field(default=None, max_length=200)


class GranskaRequest(BaseModel):
    kalla: Literal["import", "crm"] = "import"
    rader: list[GranskaRad] = Field(..., min_length=1, max_length=MAX_IMPORTRADER)


async def _kraev_prospekt(storage, tenant_id: str, prospect_id: str) -> dict:
    kraev_uuid(prospect_id, "Prospektet")
    prospect = await storage.get_prospect(tenant_id, prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospektet finns inte.")
    return prospect


def _handelse(typ: str, nar: Any, rubrik: str, *, text: str | None = None,
              id: Any = None, klar: bool | None = None) -> dict[str, Any]:
    return {
        "typ": typ,
        "nar": nar.isoformat() if hasattr(nar, "isoformat") else nar,
        "rubrik": rubrik,
        "text": text,
        "id": str(id) if id is not None else None,
        "klar": klar,
    }


def _tidpunkt(nar: Any) -> datetime:
    t = datetime.fromisoformat(str(nar))
    # Naiva tider (äldre rader, testfixturer) tolkas som UTC — annars kan de
    # inte jämföras med resten och hela tidslinjen faller.
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


@router.get("/api/leads/prospects/{prospect_id}/tidslinje")
async def tidslinje(request: Request, prospect_id: str, tenant: dict = Depends(require_tenant)) -> dict:
    """Allt som hänt med bolaget, nyast först. Statusrubriken bär råa
    statusnycklar (`fran → till`) — UI:t översätter, så tidslinjen följer
    språket utan en andra kopia av etiketterna här."""
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    prospect = await _kraev_prospekt(storage, tenant_id, prospect_id)

    handelser = [_handelse("skapad", prospect.get("created_at"), prospect.get("company_name") or "")]
    for rad in await storage.list_status_logg(tenant_id, prospect_id=prospect_id):
        rubrik = f"{rad['fran']} → {rad['till']}" if rad.get("fran") else str(rad["till"])
        handelser.append(_handelse("status", rad["created_at"], rubrik, id=rad["id"]))

    trad = await storage.find_outreach_thread(tenant_id, prospect_id=prospect_id)
    if trad:
        for m in await storage.list_outreach_messages(tenant_id, str(trad["id"])):
            nar = m.get("sent_at") or m.get("created_at")
            if not nar:
                continue  # osänt utkast: ingen händelse än, det bor i Mejlutkast
            handelser.append(
                _handelse(
                    "mejl_in" if m.get("direction") == "inbound" else "mejl_ut",
                    nar,
                    m.get("subject") or "",
                    text=(m.get("body") or "")[:_MEJLUTDRAG] or None,
                    id=m.get("id"),
                )
            )

    for rad in await storage.list_lead_samtal(tenant_id, prospect_id=prospect_id):
        # Rubriken bär utfallets nyckel; UI:t översätter, som för statusen.
        handelser.append(
            _handelse("samtal", rad["created_at"], rad["utfall"], text=rad.get("anteckning"), id=rad["id"])
        )
    for rad in await storage.list_lead_notes(tenant_id, prospect_id):
        handelser.append(_handelse("anteckning", rad["created_at"], "", text=rad["text"], id=rad["id"]))
    for rad in await storage.list_lead_tasks(tenant_id, prospect_id=prospect_id):
        handelser.append(
            _handelse(
                "uppgift", rad["created_at"], rad["titel"],
                text=rad.get("forfaller"), id=rad["id"], klar=bool(rad.get("klar")),
            )
        )

    # reversed före den stabila sorteringen: vid lika tid kommer det som
    # lades till sist i listan (och därmed hände sist) först.
    handelser = sorted(reversed(handelser), key=lambda h: _tidpunkt(h["nar"]), reverse=True)
    return {"handelser": handelser}


@router.post("/api/leads/prospects/{prospect_id}/samtal", status_code=201)
async def nytt_samtal(
    request: Request, prospect_id: str, payload: SamtalRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    """Ringd: sparar utfallet och verkställer det (app/leads/samtal.py)."""
    storage = request.app.state.storage
    prospect = await _kraev_prospekt(storage, tenant["tenant_id"], prospect_id)
    if payload.utfall == "aterkom" and payload.aterkom_datum is None:
        raise HTTPException(status_code=422, detail="Återkom kräver ett datum.")
    rad = await samtal.registrera(
        storage, tenant["tenant_id"], prospect,
        utfall=payload.utfall,
        aterkom_datum=payload.aterkom_datum if payload.utfall == "aterkom" else None,
        anteckning=(payload.anteckning or "").strip() or None,
    )
    return {"samtal": rad}


@router.get("/api/leads/samtal")
async def samtalslista(
    request: Request, lista: Literal["aterkoppling", "ring"] = "aterkoppling", tenant: dict = Depends(require_tenant)
) -> dict:
    """Återkopplingen eller ringlistan, de som ska ringas i dag först."""
    prospekter, alla_samtal, forsta, aterkom = await _samtalsunderlag(request.app.state.storage, tenant["tenant_id"])
    rader = samtal.samtalslista(
        prospekter, alla_samtal, forsta, lista=lista, idag=datetime.now(timezone.utc).date(), aterkom=aterkom
    )
    return {"rader": rader, "ring_idag": sum(1 for r in rader if r["ring_idag"])}


@router.get("/api/leads/samtal/antal")
async def samtalsantal(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    """Hur många som ska ringas i dag i båda listorna — Att göras siffra.

    Att göra hämtade förut båda listorna hela, alltså tenantens prospekt två
    gånger per sidvisning, för att räkna rader. Samma underlag, en läsning."""
    prospekter, alla_samtal, forsta, aterkom = await _samtalsunderlag(request.app.state.storage, tenant["tenant_id"])
    idag = datetime.now(timezone.utc).date()
    return {
        lista: sum(
            1
            for r in samtal.samtalslista(prospekter, alla_samtal, forsta, lista=lista, idag=idag, aterkom=aterkom)
            if r["ring_idag"]
        )
        for lista in ("aterkoppling", "ring")
    }


async def _samtalsunderlag(storage: Any, tenant_id: str) -> tuple[list, list, dict[str, Any], dict[str, Any]]:
    # ponytail: hela tenantens prospekt, samtal och utskick läses och filtreras
    # här; en SQL-vy när en kund har tusentals leads.
    prospekter, alla_samtal, skickade, aterkom = await asyncio.gather(
        storage.list_prospects(tenant_id, limit=20_000),
        storage.list_lead_samtal(tenant_id),
        storage.list_skickade(tenant_id, limit=500),
        _aterkom(storage, tenant_id),
    )
    forsta: dict[str, Any] = {}
    for m in skickade:  # nyast först: den sista vi ser per prospekt är den första
        if m.get("prospect_id"):
            forsta[str(m["prospect_id"])] = m.get("sent_at")
    return prospekter, alla_samtal, forsta, aterkom


async def _aterkom(storage: Any, tenant_id: str) -> dict[str, Any]:
    """Konversationernas återkomdatum (migration 149). Före migrationen i en
    miljö: tomt, och listorna ser ut som förut."""
    try:
        return await storage.aterkom_datum(tenant_id)
    except Exception:  # noqa: BLE001
        return {}


@router.post("/api/leads/prospects/{prospect_id}/anteckningar", status_code=201)
async def ny_anteckning(
    request: Request, prospect_id: str, payload: AnteckningRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    storage = request.app.state.storage
    prospect = await _kraev_prospekt(storage, tenant["tenant_id"], prospect_id)
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Anteckningen är tom.")
    rad = await storage.add_lead_note(tenant["tenant_id"], prospect_id=prospect_id, text=text)
    asyncio.create_task(
        crm_synk.synka_prospekt(storage, tenant["tenant_id"], prospect, handelse="anteckning", text=text)
    )
    return {"anteckning": rad}


@router.post("/api/leads/prospects/{prospect_id}/uppgifter", status_code=201)
async def ny_uppgift(
    request: Request, prospect_id: str, payload: UppgiftRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    storage = request.app.state.storage
    await _kraev_prospekt(storage, tenant["tenant_id"], prospect_id)
    titel = payload.titel.strip()
    if not titel:
        raise HTTPException(status_code=422, detail="Uppgiften saknar titel.")
    rad = await storage.add_lead_task(
        tenant["tenant_id"],
        prospect_id=prospect_id,
        titel=titel,
        forfaller=payload.forfaller.isoformat() if payload.forfaller else None,
    )
    return {"uppgift": rad}


@router.patch("/api/leads/uppgifter/{task_id}")
async def andra_uppgift(
    request: Request, task_id: str, payload: UppgiftPatchRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    kraev_uuid(task_id, "Uppgiften")
    rad = await request.app.state.storage.update_lead_task(tenant["tenant_id"], task_id, klar=payload.klar)
    if not rad:
        raise HTTPException(status_code=404, detail="Uppgiften finns inte.")
    return {"uppgift": rad}


@router.get("/api/leads/uppgifter")
async def lista_uppgifter(request: Request, oppna: bool = False, tenant: dict = Depends(require_tenant)) -> dict:
    return {
        "uppgifter": await request.app.state.storage.list_lead_tasks(tenant["tenant_id"], bara_oppna=oppna)
    }


def _vy(rad: dict) -> dict:
    return {k: rad.get(k) for k in ("id", "namn", "filter", "created_at")}


@router.get("/api/leads/vyer")
async def lista_vyer(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    return {"vyer": [_vy(r) for r in await request.app.state.storage.list_lead_views(tenant["tenant_id"])]}


@router.post("/api/leads/vyer", status_code=201)
async def ny_vy(request: Request, payload: VyRequest, tenant: dict = Depends(require_tenant)) -> dict:
    namn = payload.namn.strip()
    if not namn:
        raise HTTPException(status_code=422, detail="Vyn saknar namn.")
    rad = await request.app.state.storage.create_lead_view(tenant["tenant_id"], namn=namn, filter=payload.filter)
    return {"vy": _vy(rad)}


@router.delete("/api/leads/vyer/{view_id}", status_code=204)
async def radera_vy(request: Request, view_id: str, tenant: dict = Depends(require_tenant)) -> Response:
    kraev_uuid(view_id, "Vyn")
    if not await request.app.state.storage.delete_lead_view(tenant["tenant_id"], view_id):
        raise HTTPException(status_code=404, detail="Vyn finns inte.")
    return Response(status_code=204)


#: Importradens fält som listraden bär. `status` saknar kolumn på
#: lead_list_items och följer inte med; statusen sätts i Snipra efter flytten.
_IMPORTFALT = (
    "company_name", "orgnr", "contact_name", "contact_role", "contact_email", "contact_phone", "website", "ort",
)

#: Skälen en importrad hoppas över, i svarets ordning, med texten i 422:an.
_HOPPSKAL = {
    "utan_bolag": "utan bolagsnamn",
    "dubbletter": "dubbletter",
    "redan_kund": "redan kunder",
    "redan_lead": "redan leads",
    "sparrade": "spärrade adresser",
}
_DATUM = re.compile(r"\d{4}-\d{2}-\d{2}")


def _avtalsslut(varde: Any) -> str | None:
    """`YYYY-MM-DD` som ISO-datum, allt annat null: ett trasigt datum i
    kundens fil ska inte fälla importen."""
    text = str(varde or "").strip()
    if not _DATUM.fullmatch(text):
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def _extra(varde: dict[str, Any] | None) -> dict[str, str] | None:
    """Filens omappade kolumner, kapade: högst 40 nycklar, nyckeln 100 och
    värdet 500 tecken. Tomma värden sparas inte. Den första av två rubriker
    som blir lika efter kapningen vinner."""
    ut: dict[str, str] = {}
    for nyckel, v in (varde or {}).items():
        if len(ut) >= _EXTRA_MAX_NYCKLAR:
            break
        nyckel = str(nyckel).strip()[:_EXTRA_MAX_NYCKEL]
        text = str(v if v is not None else "").strip()[:_EXTRA_MAX_VARDE]
        if nyckel and text and nyckel not in ut:
            ut[nyckel] = text
    return ut or None


async def _uppdelade_upptagna(storage: Any, tenant_id: str, utom_lista: str | None) -> tuple[set[str], set[str]]:
    """(befintliga kunder, redan leads) som bolagsnycklar. Listan importen
    fyller på räknas inte som lead: dess rader är dubbletter (regel b)."""
    kunder: set[str] = set()
    leads: set[str] = set()
    for rad in await storage.lista_upptagna_bolag(tenant_id):
        if utom_lista and str(rad.get("list_id") or "") == utom_lista:
            continue
        (kunder if rad.get("kalla") == "crm" else leads).update(upptagna.bolagsnycklar([rad]))
    return kunder, leads


async def _sparrade_adresser(storage: Any, tenant_id: str) -> set[str]:
    """Adresser som aldrig importeras: kundens egna avregistreringar och de
    med begränsad behandling (GDPR art. 18, migration 124, gäller alla kunder).
    En begränsad adress ska inte lagras på nytt, inte bara inte mejlas."""
    return await storage.list_suppressions(tenant_id) | await storage.list_begransade(tenant_id)


@router.post("/api/leads/import", status_code=201)
async def importera(request: Request, payload: ImportRequest, tenant: dict = Depends(require_tenant)) -> dict:
    """Import av kundens egen fil (ett annat CRM, ett kalkylblad) → en
    leadslista med `kalla='import'`.

    `kalla='import'` hoppar över, och räknar för sig: rader utan bolagsnamn,
    befintliga kunder (en rad i CRM-kundlistan), spärrade adresser, bolag som
    redan är leads (om inte `ta_med_leads`) och dubbletter — i den ordningen
    när flera gäller. En stor fil kommer i delar: den första skapar listan,
    de följande skickar `list_id` och fyller på (högst MAX_IMPORTRADER rader).

    `kalla='crm'`: kundens befintliga kundbas. Den sparas som en egen lista
    som Iris och listbygget utesluter (app/leads/upptagna.py), dubbletter i
    filen slås ihop, och den kan inte flyttas till Iris."""
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]

    if payload.importinfo is not None and (
        len(json.dumps(payload.importinfo, ensure_ascii=False, default=str).encode("utf-8")) > MAX_IMPORTINFO_BYTE
    ):
        raise HTTPException(status_code=422, detail="Importkvittot är för stort (högst 20 kB).")

    lista: dict[str, Any] | None = None
    befintliga: list[dict[str, Any]] = []
    if payload.list_id:
        kraev_uuid(payload.list_id, "Listan")
        lista = await storage.get_lead_list(tenant_id, payload.list_id)
        if not lista:
            raise HTTPException(status_code=404, detail="Listan finns inte.")
        if lista.get("kalla") != payload.kalla:
            raise HTTPException(
                status_code=409, detail="Listan är ingen importerad lista av samma slag och kan inte fyllas på."
            )
        befintliga = await storage.list_lead_list_items(tenant_id, lista["id"], med_flyttade=True)
    elif not (payload.titel or "").strip():
        raise HTTPException(status_code=422, detail="Listan saknar titel.")

    hoppade = dict.fromkeys(_HOPPSKAL, 0)
    kunder: set[str] = set()
    leads: set[str] = set()
    sparr: set[str] = set()
    if payload.kalla == "import":
        kunder, leads = await _uppdelade_upptagna(storage, tenant_id, lista["id"] if lista else None)
        sparr = await _sparrade_adresser(storage, tenant_id)
    # Samma bolag två gånger (två kontaktpersoner, två rader, eller redan i
    # listan från en tidigare del) blir en rad; den första vinner.
    sedda = upptagna.bolagsnycklar(befintliga)

    rader: list[dict[str, Any]] = []
    for rad in payload.rader:
        falt = {f: (str(getattr(rad, f) or "").strip() or None) for f in _IMPORTFALT}
        namn, orgnr = falt["company_name"], falt["orgnr"]
        mejl = (falt["contact_email"] or "").casefold()
        if not namn:
            skal = "utan_bolag"
        elif payload.kalla == "import" and upptagna.upptagen(kunder, namn, orgnr):
            skal = "redan_kund"
        elif payload.kalla == "import" and mejl and mejl in sparr:
            skal = "sparrade"
        elif payload.kalla == "import" and not payload.ta_med_leads and upptagna.upptagen(leads, namn, orgnr):
            skal = "redan_lead"
        elif upptagna.upptagen(sedda, namn, orgnr):
            skal = "dubbletter"
        else:
            skal = None
        if skal:
            hoppade[skal] += 1
            continue
        sedda |= upptagna.bolagsnycklar([falt])
        falt["avtalsslut"] = _avtalsslut(rad.avtalsslut)
        falt["extra"] = _extra(rad.extra)
        rader.append(falt)

    hoppade_over = sum(hoppade.values())
    if len(befintliga) + len(rader) > MAX_IMPORTRADER:
        raise HTTPException(status_code=422, detail="Högst 5 000 rader per lista.")
    if lista is None and not rader:
        skal_text = ", ".join(f"{n} {_HOPPSKAL[k]}" for k, n in hoppade.items() if n)
        raise HTTPException(status_code=422, detail=f"Ingen rad kunde importeras ({skal_text}).")

    if lista is None:
        lista = await storage.create_lead_list(
            tenant_id,
            titel=(payload.titel or "").strip(),
            icp={},
            # ponytail: antal är check-begränsat 1–200 (migration 060), samma tak
            # som kombinerade listor; item_count bär det riktiga antalet.
            antal=min(len(rader), 200),
            kalla=payload.kalla,
            importinfo=payload.importinfo,
        )
    elif payload.importinfo is not None:
        await storage.satt_importinfo(tenant_id, lista["id"], payload.importinfo)
        lista["importinfo"] = payload.importinfo
    for falt in rader:
        await storage.add_lead_list_item(tenant_id, list_id=lista["id"], **falt)
    await storage.set_lead_list_status(tenant_id, lista["id"], status="klar")
    lista["status"] = "klar"
    lista["item_count"] = sum(1 for r in befintliga if r.get("signal") != "flyttad") + len(rader)
    return {"list": lista, "antal": len(rader), "hoppade_over": hoppade_over, "hoppade": hoppade}


@router.post("/api/leads/import/granska")
async def granska_import(request: Request, payload: GranskaRequest, tenant: dict = Depends(require_tenant)) -> dict:
    """Förhandsgranskningen före importen: vilka rader som är befintliga
    kunder, spärrade eller redan leads (samma regler som importera(), kund
    före spärrad före lead). Läser bara, skriver ingenting. En CRM-kundlista
    granskas inte: varje flagga är null."""
    antal = {"kund": 0, "sparrad": 0, "lead": 0}
    if payload.kalla == "crm":
        return {"flaggor": [None] * len(payload.rader), "antal": antal}
    storage = request.app.state.storage
    kunder, leads = await _uppdelade_upptagna(storage, tenant["tenant_id"], None)
    sparr = await _sparrade_adresser(storage, tenant["tenant_id"])
    flaggor: list[str | None] = []
    for rad in payload.rader:
        namn = (rad.company_name or "").strip() or None
        orgnr = (rad.orgnr or "").strip() or None
        mejl = (rad.contact_email or "").strip().casefold()
        if upptagna.upptagen(kunder, namn, orgnr):
            flagga = "kund"
        elif mejl and mejl in sparr:
            flagga = "sparrad"
        elif upptagna.upptagen(leads, namn, orgnr):
            flagga = "lead"
        else:
            flagga = None
        if flagga:
            antal[flagga] += 1
        flaggor.append(flagga)
    return {"flaggor": flaggor, "antal": antal}
