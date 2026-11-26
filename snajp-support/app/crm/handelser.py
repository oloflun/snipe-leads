"""Händelseloggen (crm_handelser, migration 162): en rad per skrivning.

Tre läsare delar på den:

- ändringsflödet (`GET /api/crm/v1/changes`), för den som håller en kopia i fas,
- postens tidslinje, som visar vad som hänt med ett bolag eller en person,
- webhooks ut (`app/crm/webhooks.py`), som får varje händelse lagd i sin kö.

Loggen bär VILKA fält som ändrades, aldrig värdena. Den överlever en radering,
och ska därför inte kunna bli ett register över det som raderades.

Varje skrivväg i `app/crm/synk.py` slutar med `logga`.
En skrivning som inte loggas syns varken i flödet eller hos den som
prenumererar, så det är skrivvägens ansvar och inte anroparens.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from . import lagring

TYPER = ("skapad", "andrad", "raderad", "aterstalld", "tomd")
KALLOR = ("api", "app", "synk", "system")

#: Objektens namn i det publika API:t. Nya objekt läggs till här när de byggs.
OBJEKT_UT = {"bolag": "company", "person": "person", "affar": "deal", "uppgift": "task",
             "anteckning": "note", "aktivitet": "activity", "bilaga": "attachment"}
TYP_UT = {"skapad": "created", "andrad": "updated", "raderad": "deleted",
          "aterstalld": "restored", "tomd": "purged"}

#: Hur en post skrivs ut i en webhook. API-lagret registrerar sina funktioner
#: (`registrera_form`), så att loggen inte behöver känna API:ts fältnamn.
_FORM: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}


def registrera_form(objekt: str, form: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
    _FORM[objekt] = form


@dataclass
class Handelse:
    objekt: str
    post_id: str
    typ: str
    #: Fälten som ändrades, med CRM:ets egna namn. Tomt för skapad och raderad.
    falt: list[str] = field(default_factory=list)
    #: Posten som den ser ut efter skrivningen. Går med i en webhook, sparas inte i loggen.
    post: dict[str, Any] | None = None


def handelsetyp(objekt: str, typ: str) -> str:
    """`company.updated`, `person.deleted` och så vidare."""
    return f"{OBJEKT_UT.get(objekt, objekt)}.{TYP_UT[typ]}"


def _minne(storage: Any) -> list[dict[str, Any]]:
    if not hasattr(storage, "_crm_handelser"):
        storage._crm_handelser = []
    return storage._crm_handelser


async def logga(
    storage: Any, tenant_id: str, handelser: list[Handelse], *, kalla: str, aktor: str | None = None
) -> None:
    """Skriver händelserna i en sats och lägger dem i kön hos kundens webhooks."""
    handelser = [h for h in handelser if h.typ in TYPER]
    if not handelser:
        return
    if lagring._ar_postgres(storage):
        try:
            async with storage._scoped(tenant_id) as conn:
                await conn.executemany(
                    "insert into crm_handelser (tenant_id, objekt, post_id, typ, falt, kalla, aktor) "
                    "values ($1::text::uuid, $2, $3::text::uuid, $4, $5::text::jsonb, $6, $7)",
                    [(tenant_id, h.objekt, h.post_id, h.typ, json.dumps(sorted(set(h.falt))), kalla, aktor)
                     for h in handelser])
        except Exception as fel:
            # Koden får ligga före migrationen: då finns ingen logg att skriva i.
            if not lagring._saknar_tabell(fel):
                raise
            return
    else:
        minne = _minne(storage)
        for h in handelser:
            minne.append({"id": len(minne) + 1, "tenant_id": tenant_id, "objekt": h.objekt,
                          "post_id": h.post_id, "typ": h.typ, "falt": sorted(set(h.falt)),
                          "kalla": kalla, "aktor": aktor, "created_at": lagring.nu()})
    from . import webhooks  # sen import: webhooks läser den här modulen

    await webhooks.koa(storage, tenant_id, [
        (handelsetyp(h.objekt, h.typ), _data(h)) for h in handelser])


def _data(h: Handelse) -> dict[str, Any]:
    """Det en webhook bär om händelsen. En tömd post lämnar bara sitt id."""
    data: dict[str, Any] = {"object": OBJEKT_UT.get(h.objekt, h.objekt), "id": h.post_id}
    form = _FORM.get(h.objekt)
    if h.post is not None and form is not None and h.typ != "tomd":
        data["record"] = form(h.post)
    return data


def _rad(rad: Any) -> dict[str, Any]:
    data = dict(rad)
    data["post_id"] = str(data["post_id"])
    if isinstance(data.get("falt"), str):
        data["falt"] = json.loads(data["falt"])
    if hasattr(data.get("created_at"), "isoformat"):
        data["created_at"] = data["created_at"].isoformat()
    data.pop("tenant_id", None)
    return data


async def flode(
    storage: Any, tenant_id: str, *, efter: int = 0, limit: int = 200, objekt: str | None = None
) -> tuple[list[dict[str, Any]], int]:
    """Händelser med löpnummer över `efter`, äldst först, och löpnumret att
    fråga från nästa gång. Löpnumret står still när inget nytt hänt, så att
    den som läser kan fråga om med samma värde."""
    limit = max(1, min(int(limit), 1000))
    efter = max(0, int(efter))
    if lagring._ar_postgres(storage):
        villkor, varden = ["tenant_id = $1::text::uuid", "id > $2"], [tenant_id, efter]
        if objekt:
            varden.append(objekt)
            villkor.append(f"objekt = ${len(varden)}")
        try:
            async with storage._scoped(tenant_id) as conn:
                rader = await conn.fetch(
                    "select id, objekt, post_id, typ, falt, kalla, aktor, created_at from crm_handelser "
                    f"where {' and '.join(villkor)} order by id limit {limit}", *varden)
        except Exception as fel:
            if lagring._saknar_tabell(fel):
                return [], efter
            raise
        ut = [_rad(r) for r in rader]
    else:
        ut = [_rad(h) for h in _minne(storage)
              if h["tenant_id"] == tenant_id and h["id"] > efter and (not objekt or h["objekt"] == objekt)][:limit]
    return ut, (ut[-1]["id"] if ut else efter)


async def for_post(
    storage: Any, tenant_id: str, objekt: str, post_id: str, *, limit: int = 100
) -> list[dict[str, Any]]:
    """Postens egna händelser, nyast först. Tidslinjens underlag."""
    limit = max(1, min(int(limit), 500))
    if lagring._ar_postgres(storage):
        try:
            async with storage._scoped(tenant_id) as conn:
                rader = await conn.fetch(
                    "select id, objekt, post_id, typ, falt, kalla, aktor, created_at from crm_handelser "
                    "where tenant_id = $1::text::uuid and objekt = $2 and post_id = $3::text::uuid "
                    f"order by id desc limit {limit}", tenant_id, objekt, post_id)
        except Exception as fel:
            if lagring._saknar_tabell(fel):
                return []
            raise
        return [_rad(r) for r in rader]
    traffar = [_rad(h) for h in _minne(storage)
               if h["tenant_id"] == tenant_id and h["objekt"] == objekt and h["post_id"] == post_id]
    return traffar[::-1][:limit]
