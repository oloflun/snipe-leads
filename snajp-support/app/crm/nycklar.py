"""API-nycklar med omfång (ss_api_keys, migration 160).

Fram till nu fanns en sorts nyckel: kundens egen backendnyckel, som når varje
endpoint. Den går inte att lämna till en extern part. En nyckel som Buddy
lägger i sitt CRM ska bara nå CRM-API:t, gå att namnge och gå att dra in.

Omfången:

    crm:las     läsa bolag, personer och synkens liggare
    crm:skriv   skapa, ändra och ta bort bolag och personer
    crm:synk    starta synkkörningar och skicka satser
    crm:admin   hantera anslutningar och fältmappning
    *           allt (kundens egen backendnyckel; skapas inte här)

`require_tenant` (app/api/deps.py) avvisar en nyckel utan `*` från allt
utanför CRM-API:t. Det är den kontrollen som gör nyckeln ofarlig, inte
prefixet: prefixet `snajp_crm_` är till för den som läser en logg.

Klartexten visas en gång, vid skapandet. Bara sha256-hashen sparas.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

OMFANG = ("crm:las", "crm:skriv", "crm:synk", "crm:admin")
ALLT = "*"
PREFIX = "snajp_crm_"
#: Så många tecken av nyckeln sparas i klartext, för att skilja nycklar åt i listan.
_SYNLIGA = len(PREFIX) + 6


def _ar_postgres(storage: Any) -> bool:
    return hasattr(storage, "pool") and hasattr(storage, "_scoped")


def offentlig(rad: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(rad["id"]),
        "namn": rad.get("namn") or "",
        "prefix": rad.get("key_prefix") or "",
        "omfang": list(rad.get("omfang") or [ALLT]),
        "created_at": _iso(rad.get("created_at")),
        "last_used_at": _iso(rad.get("last_used_at")),
        "revoked_at": _iso(rad.get("revoked_at")),
    }


def _iso(varde: Any) -> str | None:
    return varde.isoformat() if hasattr(varde, "isoformat") else varde


async def skapa(storage: Any, tenant_id: str, *, tenant_namn: str, namn: str, omfang: list[str]) -> dict[str, Any]:
    """Skapar en nyckel. Svaret bär klartexten i `api_key`, en enda gång."""
    okanda = [o for o in omfang if o not in OMFANG]
    if okanda or not omfang:
        raise ValueError(f"omfang ska vara en eller flera av {', '.join(OMFANG)}.")
    ra = PREFIX + secrets.token_hex(20)
    hash_ = hashlib.sha256(ra.encode()).hexdigest()
    if _ar_postgres(storage):
        async with storage._scoped(tenant_id) as conn:
            rad = dict(await conn.fetchrow(
                "insert into ss_api_keys (tenant_id, tenant_name, key_prefix, key_hash, omfang, namn) "
                "values ($1::text::uuid, $2, $3, $4, $5::text[], $6) returning *",
                tenant_id, tenant_namn, ra[:_SYNLIGA], hash_, sorted(set(omfang)), namn))
    else:
        rad = {"id": str(uuid.uuid4()), "tenant_id": tenant_id, "tenant_name": tenant_namn,
               "key_prefix": ra[:_SYNLIGA], "active": True, "omfang": sorted(set(omfang)), "namn": namn,
               "created_at": datetime.now(timezone.utc).isoformat(), "last_used_at": None, "revoked_at": None}
        storage.api_keys[hash_] = rad
    return {**offentlig(rad), "api_key": ra}


async def lista(storage: Any, tenant_id: str) -> list[dict[str, Any]]:
    """Kundens nycklar med omfång. Backendnyckeln (`*`) visas inte: den hör
    till Snajp, inte till en integration."""
    if _ar_postgres(storage):
        try:
            async with storage._scoped(tenant_id) as conn:
                rader = [dict(r) for r in await conn.fetch(
                    "select * from ss_api_keys where tenant_id = $1::text::uuid "
                    "and not ('*' = any(omfang)) order by created_at desc", tenant_id)]
        except Exception as fel:
            if getattr(fel, "sqlstate", None) == "42703":  # kolumnen omfang saknas före 160
                return []
            raise
    else:
        rader = sorted((r for r in storage.api_keys.values()
                        if r["tenant_id"] == tenant_id and ALLT not in (r.get("omfang") or [ALLT])),
                       key=lambda r: r["created_at"], reverse=True)
    return [offentlig(r) for r in rader]


async def aterkalla(storage: Any, tenant_id: str, nyckel_id: str) -> bool:
    """Drar in en nyckel med omfång. Backendnyckeln går inte att dra in här.
    Nyckelcachen töms, så att indragningen gäller direkt i den här processen;
    i en annan process gäller den inom cachens 30 sekunder."""
    if _ar_postgres(storage):
        async with storage._scoped(tenant_id) as conn:
            svar = await conn.execute(
                "update ss_api_keys set active = false, revoked_at = now() "
                "where tenant_id = $1::text::uuid and id = $2::text::uuid "
                "and active and not ('*' = any(omfang))", tenant_id, nyckel_id)
        if hasattr(storage, "_nycklar"):
            storage._nycklar.clear()
        return not str(svar).endswith(" 0")
    for rad in storage.api_keys.values():
        if (rad["id"] == nyckel_id and rad["tenant_id"] == tenant_id and rad["active"]
                and ALLT not in (rad.get("omfang") or [ALLT])):
            rad["active"] = False
            rad["revoked_at"] = datetime.now(timezone.utc).isoformat()
            return True
    return False


def tillater(nyckelns: list[str] | None, kravt: str) -> bool:
    nyckelns = list(nyckelns or [ALLT])
    return ALLT in nyckelns or kravt in nyckelns
