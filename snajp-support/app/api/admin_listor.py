"""Kopiera eller flytta en leadslista till en annan kund, bakom master-nyckeln.

Antons beställning 2026-10-08: plattformsadmin ska kunna ge en lista som
byggts hos en kund (ofta adminens egen arbetsyta) till en annan kund, som
kopia eller flytt.

## Hur

Listraden och alla dess rader kopieras till målkunden med vanliga,
tenant-skopade skrivningar (RLS gäller varje insert). Rader vars bolag
målkunden redan har — som prospekt, i en annan lista eller i CRM-listan
(app/leads/upptagna.py) — hoppas över och räknas: listor och Iris delar aldrig
bolag, och en kopia får inte bryta den regeln hos mottagaren. Med
`flytta=true` raderas källistan efteråt (raderna följer med via on delete
cascade). Listutkasten (106) följer inte med: de skrevs utifrån källkundens
erbjudande.

Ligger inte i admin.py: den filen skriver inte.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..leads import upptagna
from .deps import kraev_uuid, require_master_key

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_master_key)])

#: Listradens fält som följer med. Samma som Kombinera listor (leads.py).
#: Webbplatsbedömningen (webbrevision, webbniva, lan; migration 108) följer
#: ALDRIG med till en annan kund: den är hemlig och syns bara för Admin,
#: Umeå Webdesign och Alunix (Antons beslut 2026-10-08).
LISTRADSFALT = (
    "item_typ", "company_name", "website", "ort", "contact_name", "contact_role",
    "contact_email", "contact_level", "contact_phone", "orgnr", "source_name",
    "source_url", "signal", "signal_detalj",
)


class TillKundRequest(BaseModel):
    fran_tenant: str = Field(..., min_length=1, max_length=120)
    till_tenant: str = Field(..., min_length=1, max_length=120)
    flytta: bool = False


async def _kund(storage, slug_eller_id: str) -> dict[str, Any]:
    for t in await storage.list_tenants():
        if slug_eller_id in (str(t.get("slug") or ""), str(t.get("id") or "")):
            return t
    raise HTTPException(status_code=404, detail=f"Kunden {slug_eller_id!r} finns inte.")


@router.post("/listor/{list_id}/till-kund")
async def lista_till_kund(request: Request, list_id: str, payload: TillKundRequest) -> dict:
    kraev_uuid(list_id, "Listan")
    storage = request.app.state.storage
    fran = await _kund(storage, payload.fran_tenant)
    till = await _kund(storage, payload.till_tenant)
    if str(fran["id"]) == str(till["id"]):
        raise HTTPException(status_code=422, detail="Listan finns redan hos den kunden.")
    lista = await storage.get_lead_list(str(fran["id"]), list_id)
    if not lista:
        raise HTTPException(status_code=404, detail="Listan finns inte hos kunden.")
    if lista.get("status") != "klar":
        raise HTTPException(status_code=409, detail="Bara en färdig lista kan kopieras eller flyttas.")

    sedda = await upptagna.hamta(storage, str(till["id"]))
    rader: list[dict[str, Any]] = []
    upptagna_bort = 0
    for rad in await storage.list_lead_list_items(str(fran["id"]), list_id):
        if upptagna.upptagen(sedda, rad.get("company_name"), rad.get("orgnr")):
            upptagna_bort += 1
            continue
        # Samma bolag två gånger i källistan blir en rad hos mottagaren.
        sedda |= upptagna.bolagsnycklar([rad])
        rader.append(rad)

    svar: dict[str, Any] = {
        "list": None,
        "kopierade": 0,
        "upptagna": upptagna_bort,
        "flyttad": False,
        "till_tenant": str(till.get("slug") or till["id"]),
    }
    if not rader:
        # Ingen tom lista hos mottagaren, och källan raderas inte för en flytt
        # som inte förde över något.
        return svar

    ny = await storage.create_lead_list(
        str(till["id"]),
        titel=str(lista.get("titel") or "Lista"),
        icp=lista.get("icp") or {},
        antal=max(1, min(len(rader), 200)),
        is_test=bool(lista.get("is_test")),
        kalla=str(lista.get("kalla") or "sok"),
        # Källistorna (082) är källkundens listor; hos mottagaren finns de inte.
        kallistor=None,
        kontaktfilter=lista.get("kontaktfilter"),
    )
    for rad in rader:
        await storage.add_lead_list_item(str(till["id"]), list_id=ny["id"], **{f: rad.get(f) for f in LISTRADSFALT})
    await storage.set_lead_list_status(str(till["id"]), ny["id"], status="klar")
    ny["status"] = "klar"
    svar.update(list=ny, kopierade=len(rader))

    if payload.flytta:
        svar["flyttad"] = await storage.delete_lead_list(str(fran["id"]), list_id)

    await storage.log_platform_event(
        level="info",
        source="admin.lista_till_kund",
        message=(
            f"Lista {'flyttad' if svar['flyttad'] else 'kopierad'} från "
            f"{fran.get('slug')} till {till.get('slug')}: {len(rader)} rader, "
            f"{upptagna_bort} redan upptagna."
        ),
        tenant_id=str(till["id"]),
        detail={"fran_lista": list_id, "ny_lista": ny["id"], "fran_tenant": str(fran["id"])},
    )
    return svar
