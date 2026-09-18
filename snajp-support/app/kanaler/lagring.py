"""Lagringen för kanaler (migration 067): anslutningar, kontakter, dubblettspärr.

Samma mönster som app/integrationer/lagring.py: Postgres via
`storage._scoped(tenant_id)`, en dict på minneslagringen i testsviten, och en
saknad tabell (migrationen ej körd) läses som "inga anslutningar".
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from ..integrationer import hemligheter as hemlig

_ANSLUTNING = (
    "id, tenant_id, kanal, namn, extern_id, konfig, hemlighetsnamn, "
    "hemligheter_krypterat, aktiv, created_at, updated_at"
)
_KONTAKT = "id, tenant_id, anslutning_id, customer_id, extern_anvandare, adress, visningsnamn, created_at, updated_at"


class AnslutningFinnsRedan(ValueError):
    pass


def _nu() -> datetime:
    return datetime.now(timezone.utc)


def _rad(record: Any) -> dict[str, Any] | None:
    if record is None:
        return None
    data = dict(record)
    for nyckel in ("id", "tenant_id", "anslutning_id", "customer_id"):
        if data.get(nyckel) is not None:
            data[nyckel] = str(data[nyckel])
    for nyckel in ("created_at", "updated_at"):
        if hasattr(data.get(nyckel), "isoformat"):
            data[nyckel] = data[nyckel].isoformat()
    for nyckel in ("konfig", "adress"):
        if isinstance(data.get(nyckel), str):
            data[nyckel] = json.loads(data[nyckel])
    if "hemlighetsnamn" in data:
        data["hemlighetsnamn"] = list(data.get("hemlighetsnamn") or [])
    return data


def _ar_postgres(storage: Any) -> bool:
    return hasattr(storage, "pool") and hasattr(storage, "_scoped")


def _saknar_tabell(fel: BaseException) -> bool:
    return getattr(fel, "sqlstate", None) == "42P01"


def _minne(storage: Any, namn: str) -> dict[Any, dict[str, Any]]:
    if not hasattr(storage, namn):
        setattr(storage, namn, {})
    return getattr(storage, namn)


def offentlig(rad: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": rad["id"],
        "kanal": rad["kanal"],
        "namn": rad.get("namn") or "",
        "extern_id": rad["extern_id"],
        "konfig": rad.get("konfig") or {},
        "hemligheter": hemlig.maskera_namn({n: "" for n in rad.get("hemlighetsnamn") or []}),
        "aktiv": bool(rad.get("aktiv")),
        "created_at": rad.get("created_at"),
        "updated_at": rad.get("updated_at"),
    }


def dekryptera_hemligheter(rad: dict[str, Any]) -> dict[str, str]:
    return hemlig.dekryptera(rad.get("hemligheter_krypterat"))


# -- Anslutningar -----------------------------------------------------------


async def lista_anslutningar(storage: Any, tenant_id: str) -> list[dict[str, Any]]:
    if _ar_postgres(storage):
        try:
            async with storage._scoped(tenant_id) as conn:
                rader = await conn.fetch(
                    f"select {_ANSLUTNING} from ss_channel_connections where tenant_id = $1 order by created_at",
                    tenant_id,
                )
        except Exception as fel:
            if _saknar_tabell(fel):
                return []
            raise
        return [_rad(r) for r in rader]
    rader = [r for r in _minne(storage, "_kanalanslutningar").values() if r["tenant_id"] == tenant_id]
    return [dict(r) for r in sorted(rader, key=lambda r: r["created_at"])]


async def hamta_anslutning(storage: Any, tenant_id: str, anslutning_id: str) -> dict[str, Any] | None:
    if _ar_postgres(storage):
        try:
            async with storage._scoped(tenant_id) as conn:
                rad = await conn.fetchrow(
                    f"select {_ANSLUTNING} from ss_channel_connections where tenant_id = $1 and id = $2::uuid",
                    tenant_id,
                    anslutning_id,
                )
        except Exception as fel:
            if _saknar_tabell(fel):
                return None
            raise
        return _rad(rad)
    rad = _minne(storage, "_kanalanslutningar").get(anslutning_id)
    return dict(rad) if rad and rad["tenant_id"] == tenant_id else None


async def skapa_anslutning(
    storage: Any,
    tenant_id: str,
    *,
    kanal: str,
    namn: str,
    extern_id: str,
    konfig: dict[str, Any],
    hemligheter: dict[str, str],
    aktiv: bool = True,
) -> dict[str, Any]:
    token = hemlig.kryptera(hemligheter)
    namnlista = sorted(k for k, v in hemligheter.items() if v)
    if _ar_postgres(storage):
        try:
            async with storage._scoped(tenant_id) as conn:
                rad = await conn.fetchrow(
                    f"""
                    insert into ss_channel_connections
                      (tenant_id, kanal, namn, extern_id, konfig, hemlighetsnamn, hemligheter_krypterat, aktiv)
                    values ($1, $2, $3, $4, $5::jsonb, $6, $7, $8)
                    returning {_ANSLUTNING}
                    """,
                    tenant_id,
                    kanal,
                    namn,
                    extern_id,
                    json.dumps(konfig, ensure_ascii=False),
                    namnlista,
                    token,
                    aktiv,
                )
        except Exception as fel:
            if getattr(fel, "sqlstate", None) == "23505":
                raise AnslutningFinnsRedan(
                    f"{kanal} med id {extern_id} är redan ansluten (här eller hos en annan kund)."
                ) from fel
            raise
        return _rad(rad)
    minne = _minne(storage, "_kanalanslutningar")
    if any(r["kanal"] == kanal and r["extern_id"] == extern_id for r in minne.values()):
        raise AnslutningFinnsRedan(f"{kanal} med id {extern_id} är redan ansluten (här eller hos en annan kund).")
    nu = _nu().isoformat()
    rad = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "kanal": kanal,
        "namn": namn,
        "extern_id": extern_id,
        "konfig": json.loads(json.dumps(konfig)),
        "hemlighetsnamn": namnlista,
        "hemligheter_krypterat": token,
        "aktiv": aktiv,
        "created_at": nu,
        "updated_at": nu,
    }
    minne[rad["id"]] = rad
    return dict(rad)


async def uppdatera_anslutning(
    storage: Any,
    tenant_id: str,
    anslutning_id: str,
    *,
    namn: str | None = None,
    konfig: dict[str, Any] | None = None,
    aktiv: bool | None = None,
    hemligheter: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    befintlig = await hamta_anslutning(storage, tenant_id, anslutning_id)
    if befintlig is None:
        return None
    nytt = {
        "namn": namn if namn is not None else befintlig.get("namn") or "",
        "konfig": konfig if konfig is not None else befintlig.get("konfig") or {},
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
            rad = await conn.fetchrow(
                f"""
                update ss_channel_connections
                   set namn = $3, konfig = $4::jsonb, aktiv = $5, hemlighetsnamn = $6,
                       hemligheter_krypterat = $7, updated_at = now()
                 where tenant_id = $1 and id = $2::uuid
                returning {_ANSLUTNING}
                """,
                tenant_id,
                anslutning_id,
                nytt["namn"],
                json.dumps(nytt["konfig"], ensure_ascii=False),
                nytt["aktiv"],
                namnlista,
                token,
            )
        return _rad(rad)
    rad = _minne(storage, "_kanalanslutningar")[anslutning_id]
    rad.update(nytt)
    rad["hemlighetsnamn"] = list(namnlista)
    rad["hemligheter_krypterat"] = token
    rad["updated_at"] = _nu().isoformat()
    return dict(rad)


async def ta_bort_anslutning(storage: Any, tenant_id: str, anslutning_id: str) -> bool:
    if _ar_postgres(storage):
        async with storage._scoped(tenant_id) as conn:
            svar = await conn.execute(
                "delete from ss_channel_connections where tenant_id = $1 and id = $2::uuid",
                tenant_id,
                anslutning_id,
            )
        return not str(svar).endswith(" 0")
    minne = _minne(storage, "_kanalanslutningar")
    rad = minne.get(anslutning_id)
    if not rad or rad["tenant_id"] != tenant_id:
        return False
    del minne[anslutning_id]
    kontakter = _minne(storage, "_kanalkontakter")
    for nyckel in [k for k, v in kontakter.items() if v["anslutning_id"] == anslutning_id]:
        del kontakter[nyckel]
    return True


# -- Dubblettspärr ----------------------------------------------------------


async def markera_sett(storage: Any, tenant_id: str, anslutning_id: str, extern_meddelande_id: str) -> bool:
    """True första gången ett meddelande-id ses, False vid en omsändning."""
    if _ar_postgres(storage):
        async with storage._scoped(tenant_id) as conn:
            ny = await conn.fetchval(
                """
                insert into ss_channel_inbound_seen (anslutning_id, extern_meddelande_id, tenant_id)
                values ($1::uuid, $2, $3)
                on conflict do nothing
                returning 1
                """,
                anslutning_id,
                extern_meddelande_id,
                tenant_id,
            )
        return bool(ny)
    sett = _minne(storage, "_kanal_sett")
    nyckel = (anslutning_id, extern_meddelande_id)
    if nyckel in sett:
        return False
    sett[nyckel] = {"tenant_id": tenant_id, "seen_at": _nu()}
    return True


async def stada_sett(storage: Any, tenant_id: str, *, dagar: int = 14) -> None:
    """Meta och Slack skickar om i högst några dygn; äldre spärrar är döda."""
    grans = _nu() - timedelta(days=dagar)
    if _ar_postgres(storage):
        async with storage._scoped(tenant_id) as conn:
            await conn.execute(
                "delete from ss_channel_inbound_seen where tenant_id = $1 and seen_at < $2",
                tenant_id,
                grans,
            )
        return
    sett = _minne(storage, "_kanal_sett")
    for nyckel in [k for k, v in sett.items() if v["tenant_id"] == tenant_id and v["seen_at"] < grans]:
        del sett[nyckel]


# -- Kontakter --------------------------------------------------------------


async def hamta_kontakt(
    storage: Any, tenant_id: str, anslutning_id: str, extern_anvandare: str
) -> dict[str, Any] | None:
    if _ar_postgres(storage):
        async with storage._scoped(tenant_id) as conn:
            rad = await conn.fetchrow(
                f"""
                select {_KONTAKT} from ss_channel_contacts
                where tenant_id = $1 and anslutning_id = $2::uuid and extern_anvandare = $3
                """,
                tenant_id,
                anslutning_id,
                extern_anvandare,
            )
        return _rad(rad)
    rad = _minne(storage, "_kanalkontakter").get((anslutning_id, extern_anvandare))
    return dict(rad) if rad and rad["tenant_id"] == tenant_id else None


async def spara_kontakt(
    storage: Any,
    tenant_id: str,
    *,
    anslutning_id: str,
    customer_id: str,
    extern_anvandare: str,
    adress: dict[str, Any],
    visningsnamn: str | None,
) -> dict[str, Any]:
    """Upsert: adressen (Teams serviceUrl, Slack-tråd) uppdateras vid varje
    meddelande, så att ett senare medarbetarsvar går till rätt ställe."""
    if _ar_postgres(storage):
        async with storage._scoped(tenant_id) as conn:
            rad = await conn.fetchrow(
                f"""
                insert into ss_channel_contacts
                  (tenant_id, anslutning_id, customer_id, extern_anvandare, adress, visningsnamn)
                values ($1, $2::uuid, $3::uuid, $4, $5::jsonb, $6)
                on conflict (anslutning_id, extern_anvandare) do update
                  set customer_id = excluded.customer_id,
                      adress = excluded.adress,
                      visningsnamn = coalesce(excluded.visningsnamn, ss_channel_contacts.visningsnamn),
                      updated_at = now()
                returning {_KONTAKT}
                """,
                tenant_id,
                anslutning_id,
                customer_id,
                extern_anvandare,
                json.dumps(adress, ensure_ascii=False),
                visningsnamn,
            )
        return _rad(rad)
    kontakter = _minne(storage, "_kanalkontakter")
    nyckel = (anslutning_id, extern_anvandare)
    nu = _nu().isoformat()
    befintlig = kontakter.get(nyckel)
    rad = {
        "id": (befintlig or {}).get("id") or str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "anslutning_id": anslutning_id,
        "customer_id": customer_id,
        "extern_anvandare": extern_anvandare,
        "adress": dict(adress),
        "visningsnamn": visningsnamn or (befintlig or {}).get("visningsnamn"),
        "created_at": (befintlig or {}).get("created_at") or nu,
        "updated_at": nu,
    }
    kontakter[nyckel] = rad
    return dict(rad)


async def senaste_kontakt(
    storage: Any, tenant_id: str, customer_id: str, *, kanal: str
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Kundens senast använda kontakt i kanalen, med sin (aktiva) anslutning."""
    if _ar_postgres(storage):
        try:
            async with storage._scoped(tenant_id) as conn:
                rad = await conn.fetchrow(
                    f"""
                    select {', '.join('k.' + c.strip() for c in _KONTAKT.split(','))}
                    from ss_channel_contacts k
                    join ss_channel_connections a on a.id = k.anslutning_id
                    where k.tenant_id = $1 and k.customer_id = $2::uuid and a.kanal = $3 and a.aktiv
                    order by k.updated_at desc
                    limit 1
                    """,
                    tenant_id,
                    customer_id,
                    kanal,
                )
        except Exception as fel:
            if _saknar_tabell(fel):
                return None
            raise
        kontakt = _rad(rad)
    else:
        anslutningar = _minne(storage, "_kanalanslutningar")
        kandidater = [
            k
            for k in _minne(storage, "_kanalkontakter").values()
            if k["tenant_id"] == tenant_id
            and k["customer_id"] == customer_id
            and (anslutningar.get(k["anslutning_id"]) or {}).get("kanal") == kanal
            and (anslutningar.get(k["anslutning_id"]) or {}).get("aktiv")
        ]
        kontakt = dict(max(kandidater, key=lambda k: k["updated_at"])) if kandidater else None
    if kontakt is None:
        return None
    anslutning = await hamta_anslutning(storage, tenant_id, kontakt["anslutning_id"])
    if anslutning is None or not anslutning.get("aktiv"):
        return None
    return kontakt, anslutning
