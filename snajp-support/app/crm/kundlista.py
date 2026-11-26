"""Den samlade kundlistan: egna kunder och Iris kunder i en lista.

Antons svar 2026-11-26: kunderna i CRM:et hålls isär från kunderna som kommit
ur Iris-körningar, men CRM:et förbereds för att visa båda i en samlad lista,
uppdelad på Iris och Egna. "Mer om det senare."

Därför komponeras listan vid läsning, och ingenting flyttas:

- **Egna** är bolagen i CRM:et med relationen kund.
- **Iris** är leads som vunnits (status `won`) och som inte redan är en egen
  kund. Ett lead som delar nyckel med en egen kund visas en gång, som egen, med
  leadets id bredvid.

Ett vunnet lead blir alltså inte ett bolag i CRM:et av sig självt. Det är ett
beslut som återstår, och listan fungerar likadant vilket det än blir.

Prospektet läses med en uttrycklig kolumnlista: bedömningen av bolagets sajt
får aldrig följa med.
"""

from __future__ import annotations

from typing import Any

from ..leads import upptagna
from . import lagring, tidslinje

MAX = 2000
URSPRUNG = ("alla", "egna", "iris")
_FALT = ("id", "company_name", "orgnr", "contact_email", "origin", "created_at")


async def _vunna(storage: Any, tenant_id: str) -> list[dict[str, Any]]:
    if lagring._ar_postgres(storage):
        try:
            async with storage._scoped(tenant_id) as conn:
                rader = await conn.fetch(
                    f"select {', '.join(_FALT)} from prospects where tenant_id = $1::text::uuid "
                    "and status = 'won' and coalesce(origin, '') not in ('example', 'test') "
                    f"order by lower(company_name) limit {MAX}", tenant_id)
        except Exception as fel:
            if lagring._saknar_tabell(fel):
                return []
            raise
        return [{**dict(r), "id": str(r["id"])} for r in rader]
    ut = [{k: p.get(k) for k in _FALT} for p in getattr(storage, "prospects", {}).get(tenant_id, [])
          if p.get("status") == "won" and p.get("origin") not in ("example", "test")]
    return sorted(ut, key=lambda p: str(p.get("company_name") or "").lower())[:MAX]


async def lista(
    storage: Any, tenant_id: str, *, ursprung: str = "alla", q: str | None = None, limit: int = 200
) -> dict[str, Any]:
    """`{"kunder": [...], "antal": {"egna", "iris"}}`, i bokstavsordning."""
    egna = await lagring._valj(storage, tenant_id, "crm_bolag", lika={"relation": "kund"}, levande=True,
                               ordning="namn", limit=MAX)
    per_nyckel = {n: b for b in egna for n in tidslinje.nycklar_for_bolag(b)}
    leadets: dict[str, str] = {}
    iris: list[dict[str, Any]] = []
    for lead in await _vunna(storage, tenant_id):
        nyckel = tidslinje._minnesnyckel(lead)
        bolag = per_nyckel.get(nyckel) if nyckel else None
        if bolag is not None:
            leadets.setdefault(bolag["id"], str(lead["id"]))
            continue
        orgnr = upptagna.orgnr_nyckel(lead.get("orgnr"))
        siffror = orgnr.split(":", 1)[1] if orgnr else None
        iris.append({"ursprung": "iris", "bolag_id": None, "lead_id": str(lead["id"]),
                     "namn": lead.get("company_name"),
                     "orgnr": f"{siffror[:6]}-{siffror[6:]}" if siffror else None,
                     "kund_sedan": None, "privatperson": False})
    rader = [{"ursprung": "egna", "bolag_id": b["id"], "lead_id": leadets.get(b["id"]), "namn": b["namn"],
              "orgnr": b.get("orgnr"), "kund_sedan": b.get("kund_sedan"),
              "privatperson": bool(b.get("privatperson"))} for b in egna]
    antal = {"egna": len(rader), "iris": len(iris)}
    valda = {"alla": rader + iris, "egna": rader, "iris": iris}[ursprung if ursprung in URSPRUNG else "alla"]
    if q and q.strip():
        sok = q.strip().lower()
        valda = [r for r in valda if sok in (r["namn"] or "").lower() or sok in (r["orgnr"] or "").replace("-", "")
                 or sok in (r["orgnr"] or "")]
    valda.sort(key=lambda r: ((r["namn"] or "").lower(), r["ursprung"]))
    return {"kunder": valda[: max(1, min(limit, MAX))], "antal": antal}
