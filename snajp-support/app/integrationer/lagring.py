"""Lagringen för integrationer (tabell ss_integrations, migration 067).

Egen modul i stället för metoder på Storage-protokollet, i samma mönster som
app/sending_domains.py: Postgres via `storage._scoped(tenant_id)` (RLS gäller)
och en dict på minneslagringen i testsviten.

## Saknad tabell är inget fel för läsvägen

Före migration 067 finns ingen tabell, och support-agenten läser
integrationerna på VARJE ärende. En läsning mot en saknad tabell (42P01)
blir därför en tom lista — agenten beter sig exakt som före funktionen.
Skrivvägen kastar däremot: att spara en integration som inte går att spara
ska synas.

## Hemligheterna

Lagras som EN Fernet-token (`hemligheter_krypterat`) plus namnen i klartext
(`hemlighetsnamn`), så att portalen kan visa vilka nycklar som finns utan att
dekryptera något. Läsvägen till API:t returnerar aldrig token eller värden;
bara `dekryptera_hemligheter` gör det, och den anropas bara när ett anrop
byggs.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from . import hemligheter as hemlig

_KOLUMNER = (
    "id, tenant_id, typ, namn, beskrivning, konfig, hemlighetsnamn, "
    "hemligheter_krypterat, aktiv, created_at, updated_at"
)


class IntegrationFinnsRedan(ValueError):
    pass


def _nu() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rad(record: Any) -> dict[str, Any] | None:
    if record is None:
        return None
    data = dict(record)
    for nyckel in ("id", "tenant_id"):
        if data.get(nyckel) is not None:
            data[nyckel] = str(data[nyckel])
    for nyckel in ("created_at", "updated_at"):
        if hasattr(data.get(nyckel), "isoformat"):
            data[nyckel] = data[nyckel].isoformat()
    if isinstance(data.get("konfig"), str):
        data["konfig"] = json.loads(data["konfig"])
    data["hemlighetsnamn"] = list(data.get("hemlighetsnamn") or [])
    return data


def _ar_postgres(storage: Any) -> bool:
    return hasattr(storage, "pool") and hasattr(storage, "_scoped")


def _saknar_tabell(fel: BaseException) -> bool:
    return getattr(fel, "sqlstate", None) == "42P01"


def _minne(storage: Any) -> dict[str, dict[str, Any]]:
    if not hasattr(storage, "_integrationer"):
        storage._integrationer = {}
    return storage._integrationer


def offentlig(rad: dict[str, Any]) -> dict[str, Any]:
    """Det API:t får lämna ut: aldrig token, aldrig värden."""
    return {
        "id": rad["id"],
        "typ": rad["typ"],
        "namn": rad["namn"],
        "beskrivning": rad.get("beskrivning") or "",
        "konfig": rad.get("konfig") or {},
        "hemligheter": hemlig.maskera_namn({n: "" for n in rad.get("hemlighetsnamn") or []}),
        "aktiv": bool(rad.get("aktiv")),
        "created_at": rad.get("created_at"),
        "updated_at": rad.get("updated_at"),
    }


def dekryptera_hemligheter(rad: dict[str, Any]) -> dict[str, str]:
    return hemlig.dekryptera(rad.get("hemligheter_krypterat"))


async def lista(storage: Any, tenant_id: str, *, bara_aktiva: bool = False) -> list[dict[str, Any]]:
    if _ar_postgres(storage):
        villkor = "tenant_id = $1" + (" and aktiv" if bara_aktiva else "")
        try:
            async with storage._scoped(tenant_id) as conn:
                rader = await conn.fetch(
                    f"select {_KOLUMNER} from ss_integrations where {villkor} order by created_at",
                    tenant_id,
                )
        except Exception as fel:
            if _saknar_tabell(fel):
                return []
            raise
        return [_rad(r) for r in rader]
    rader = [r for r in _minne(storage).values() if r["tenant_id"] == tenant_id]
    if bara_aktiva:
        rader = [r for r in rader if r["aktiv"]]
    return [dict(r) for r in sorted(rader, key=lambda r: r["created_at"])]


async def hamta(storage: Any, tenant_id: str, integration_id: str) -> dict[str, Any] | None:
    if _ar_postgres(storage):
        try:
            async with storage._scoped(tenant_id) as conn:
                rad = await conn.fetchrow(
                    f"select {_KOLUMNER} from ss_integrations where tenant_id = $1 and id = $2::uuid",
                    tenant_id,
                    integration_id,
                )
        except Exception as fel:
            if _saknar_tabell(fel):
                return None
            raise
        return _rad(rad)
    rad = _minne(storage).get(integration_id)
    return dict(rad) if rad and rad["tenant_id"] == tenant_id else None


async def skapa(
    storage: Any,
    tenant_id: str,
    *,
    typ: str,
    namn: str,
    beskrivning: str,
    konfig: dict[str, Any],
    hemligheter: dict[str, str],
    aktiv: bool = True,
) -> dict[str, Any]:
    token = hemlig.kryptera(hemligheter)
    namnlista = sorted(k for k, v in hemligheter.items() if v)
    if _ar_postgres(storage):
        async with storage._scoped(tenant_id) as conn:
            finns = await conn.fetchval(
                "select 1 from ss_integrations where tenant_id = $1 and lower(namn) = lower($2)",
                tenant_id,
                namn,
            )
            if finns:
                raise IntegrationFinnsRedan(f"Det finns redan en integration som heter {namn!r}.")
            rad = await conn.fetchrow(
                f"""
                insert into ss_integrations
                  (tenant_id, typ, namn, beskrivning, konfig, hemlighetsnamn, hemligheter_krypterat, aktiv)
                values ($1, $2, $3, $4, $5::jsonb, $6, $7, $8)
                returning {_KOLUMNER}
                """,
                tenant_id,
                typ,
                namn,
                beskrivning,
                json.dumps(konfig, ensure_ascii=False),
                namnlista,
                token,
                aktiv,
            )
        return _rad(rad)
    minne = _minne(storage)
    if any(r["tenant_id"] == tenant_id and r["namn"].lower() == namn.lower() for r in minne.values()):
        raise IntegrationFinnsRedan(f"Det finns redan en integration som heter {namn!r}.")
    rad = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "typ": typ,
        "namn": namn,
        "beskrivning": beskrivning,
        "konfig": json.loads(json.dumps(konfig)),
        "hemlighetsnamn": namnlista,
        "hemligheter_krypterat": token,
        "aktiv": aktiv,
        "created_at": _nu(),
        "updated_at": _nu(),
    }
    minne[rad["id"]] = rad
    return dict(rad)


def sla_ihop_hemligheter(befintliga: dict[str, str], andringar: dict[str, str | None]) -> dict[str, str]:
    """Ändringar ovanpå befintliga: ett värde sätter, None eller "" tar bort.

    Portalen skickar bara de nycklar någon faktiskt skrivit i — en nyckel som
    inte nämns ligger kvar. Annars hade varje sparning av en URL krävt att
    admin klistrade in alla nycklar igen.
    """
    ut = dict(befintliga)
    for namn, varde in andringar.items():
        if varde in (None, ""):
            ut.pop(namn, None)
        else:
            ut[namn] = str(varde)
    return ut


async def uppdatera(
    storage: Any,
    tenant_id: str,
    integration_id: str,
    *,
    namn: str | None = None,
    beskrivning: str | None = None,
    konfig: dict[str, Any] | None = None,
    aktiv: bool | None = None,
    hemligheter: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """`hemligheter` är den FULLSTÄNDIGA nya uppsättningen (anroparen slår ihop)."""
    befintlig = await hamta(storage, tenant_id, integration_id)
    if befintlig is None:
        return None
    nytt = {
        "namn": namn if namn is not None else befintlig["namn"],
        "beskrivning": beskrivning if beskrivning is not None else befintlig["beskrivning"],
        "konfig": konfig if konfig is not None else befintlig["konfig"],
        "aktiv": aktiv if aktiv is not None else befintlig["aktiv"],
    }
    if hemligheter is not None:
        token = hemlig.kryptera(hemligheter)
        namnlista = sorted(k for k, v in hemligheter.items() if v)
    else:
        token = befintlig.get("hemligheter_krypterat")
        namnlista = befintlig.get("hemlighetsnamn") or []
    if _ar_postgres(storage):
        async with storage._scoped(tenant_id) as conn:
            if nytt["namn"].lower() != befintlig["namn"].lower():
                finns = await conn.fetchval(
                    "select 1 from ss_integrations where tenant_id = $1 and lower(namn) = lower($2) and id <> $3::uuid",
                    tenant_id,
                    nytt["namn"],
                    integration_id,
                )
                if finns:
                    raise IntegrationFinnsRedan(f"Det finns redan en integration som heter {nytt['namn']!r}.")
            rad = await conn.fetchrow(
                f"""
                update ss_integrations
                   set namn = $3, beskrivning = $4, konfig = $5::jsonb, aktiv = $6,
                       hemlighetsnamn = $7, hemligheter_krypterat = $8, updated_at = now()
                 where tenant_id = $1 and id = $2::uuid
                returning {_KOLUMNER}
                """,
                tenant_id,
                integration_id,
                nytt["namn"],
                nytt["beskrivning"],
                json.dumps(nytt["konfig"], ensure_ascii=False),
                nytt["aktiv"],
                namnlista,
                token,
            )
        return _rad(rad)
    minne = _minne(storage)
    if nytt["namn"].lower() != befintlig["namn"].lower() and any(
        r["tenant_id"] == tenant_id and r["namn"].lower() == nytt["namn"].lower() and r["id"] != integration_id
        for r in minne.values()
    ):
        raise IntegrationFinnsRedan(f"Det finns redan en integration som heter {nytt['namn']!r}.")
    rad = minne[integration_id]
    rad.update(nytt)
    rad["konfig"] = json.loads(json.dumps(nytt["konfig"]))
    rad["hemlighetsnamn"] = list(namnlista)
    rad["hemligheter_krypterat"] = token
    rad["updated_at"] = _nu()
    return dict(rad)


async def ta_bort(storage: Any, tenant_id: str, integration_id: str) -> bool:
    if _ar_postgres(storage):
        async with storage._scoped(tenant_id) as conn:
            svar = await conn.execute(
                "delete from ss_integrations where tenant_id = $1 and id = $2::uuid",
                tenant_id,
                integration_id,
            )
        return not str(svar).endswith(" 0")
    minne = _minne(storage)
    rad = minne.get(integration_id)
    if not rad or rad["tenant_id"] != tenant_id:
        return False
    del minne[integration_id]
    return True
