"""Lagringen för CRM:et (tabellerna crm_*, migration 153).

Egen modul i stället för metoder på Storage-protokollet, i samma mönster som
app/integrationer/lagring.py: Postgres via `storage._scoped(tenant_id)`, så att
RLS gäller, och en dict på minneslagringen i testsviten. Varje fråga bär
dessutom `tenant_id` uttryckligen.

De flesta läsningar och skrivningar går genom fyra allmänna funktioner
(`_in`, `_upp`, `_hamta`, `_valj`) som bara godtar tabeller och kolumner ur
`TABELLER`. Kolumnnamn kommer alltså aldrig från ett anrop, och de två
lagren kan inte glida isär fält för fält.

Läsvägarna tål att tabellerna saknas (42P01): koden får ligga före
migrationen, och då finns helt enkelt inga CRM-poster.
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable

#: Kolumnernas typer där de inte är text. Styr hur värdet skickas till
#: Postgres och hur det läses tillbaka.
_UUID, _JSON, _DATUM, _TID, _TAL, _BOOL = "uuid", "jsonb", "date", "timestamptz", "int", "bool"

TABELLER: dict[str, dict[str, str | None]] = {
    "crm_anslutningar": {
        "id": _UUID, "tenant_id": _UUID, "namn": None, "system": None, "mappning": _JSON,
        "konfliktregel": None, "saknade": None, "standardrelation": None, "aktiv": _BOOL,
        "senaste_synk_at": _TID, "created_at": _TID, "updated_at": _TID,
    },
    "crm_bolag": {
        "id": _UUID, "tenant_id": _UUID, "namn": None, "namnnyckel": None, "orgnr": None,
        "orgnr_nyckel": None, "enskild_firma": _BOOL, "momsnr": None, "bolagsform": None,
        "sni": None, "webbplats": None, "doman": None, "epost": None, "telefon": None,
        "gatuadress": None, "co": None, "postnr": None, "postort": None, "land": None,
        "anstallda": _TAL, "omsattning": _TAL, "relation": None, "kund_sedan": _DATUM,
        "avtalsslut": _DATUM, "ansvarig": None, "kontakta_inte": _BOOL, "extra": _JSON,
        "manuellt_andrade": _JSON, "kalla": None, "prospect_id": _UUID,
        "created_at": _TID, "updated_at": _TID, "raderad_at": _TID,
    },
    "crm_personer": {
        "id": _UUID, "tenant_id": _UUID, "bolag_id": _UUID, "fornamn": None, "efternamn": None,
        "titel": None, "epost": None, "telefon": None, "mobil": None, "rattslig_grund": None,
        "kontakta_inte": _BOOL, "extra": _JSON, "manuellt_andrade": _JSON, "kalla": None,
        "created_at": _TID, "updated_at": _TID, "raderad_at": _TID,
    },
    "crm_externa_id": {
        "id": _UUID, "tenant_id": _UUID, "anslutning_id": _UUID, "objekt": None,
        "externt_id": None, "post_id": _UUID, "innehallshash": None,
        "extern_uppdaterad_at": _TID, "senast_korning": _UUID, "senast_sedd_at": _TID,
        "created_at": _TID,
    },
    "crm_synkkorningar": {
        "id": _UUID, "tenant_id": _UUID, "anslutning_id": _UUID, "lage": None, "status": None,
        "startad_av": None, "totalt": _TAL, "skapade": _TAL, "uppdaterade": _TAL,
        "oforandrade": _TAL, "hoppade": _TAL, "konflikter": _TAL, "borttagna": _TAL,
        "fel": _JSON, "error": None, "created_at": _TID, "updated_at": _TID, "completed_at": _TID,
    },
}

#: Standardvärden som databasen sätter, speglade för minneslagret.
_STANDARD: dict[str, dict[str, Any]] = {
    "crm_anslutningar": {"system": "generisk", "mappning": {}, "konfliktregel": "kallan_vinner",
                         "saknade": "behall", "standardrelation": "kund", "aktiv": True},
    "crm_bolag": {"namnnyckel": "", "enskild_firma": False, "land": "SE", "relation": "kund",
                  "kontakta_inte": False, "extra": {}, "manuellt_andrade": {}, "kalla": "manuell"},
    "crm_personer": {"kontakta_inte": False, "extra": {}, "manuellt_andrade": {}, "kalla": "manuell"},
    "crm_externa_id": {},
    "crm_synkkorningar": {"lage": "delta", "status": "processing", "startad_av": "api", "totalt": 0,
                          "skapade": 0, "uppdaterade": 0, "oforandrade": 0, "hoppade": 0,
                          "konflikter": 0, "borttagna": 0, "fel": []},
}

RAKNARE = ("totalt", "skapade", "uppdaterade", "oforandrade", "hoppade", "konflikter", "borttagna")
#: Så många fel sparas per körning. Resten räknas men skrivs inte ut.
MAX_FEL = 200


class FinnsRedan(ValueError):
    """Ett unikt index sa nej: namnet på anslutningen, organisationsnumret
    eller e-postadressen finns redan hos kunden."""


def nu() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ar_postgres(storage: Any) -> bool:
    return hasattr(storage, "pool") and hasattr(storage, "_scoped")


def _saknar_tabell(fel: BaseException) -> bool:
    return getattr(fel, "sqlstate", None) in ("42P01", "42703")


def _unik_krock(fel: BaseException) -> bool:
    return getattr(fel, "sqlstate", None) == "23505"


def _minne(storage: Any, tabell: str) -> dict[str, dict[str, Any]]:
    if not hasattr(storage, "_crm"):
        storage._crm = {}
    return storage._crm.setdefault(tabell, {})


def _rad(record: Any, tabell: str) -> dict[str, Any] | None:
    if record is None:
        return None
    data = dict(record)
    for kol, typ in TABELLER[tabell].items():
        varde = data.get(kol)
        if varde is None:
            continue
        if typ == _UUID:
            data[kol] = str(varde)
        elif typ in (_TID, _DATUM) and hasattr(varde, "isoformat"):
            data[kol] = varde.isoformat()
        elif typ == _JSON and isinstance(varde, str):
            data[kol] = json.loads(varde)
    data.pop("synk_andrad_at", None)
    return data


def _plats(tabell: str, kol: str, n: int) -> str:
    typ = TABELLER[tabell][kol]
    if typ in (_UUID, _JSON, _DATUM, _TID):
        # Via text: asyncpg kräver annars uuid-, date- och datetime-objekt.
        return f"${n}::text::{typ}"
    return f"${n}"


def _varde(tabell: str, kol: str, varde: Any) -> Any:
    typ = TABELLER[tabell][kol]
    if varde is None:
        return None
    if typ == _JSON:
        return json.dumps(varde, ensure_ascii=False)
    if typ in (_UUID, _DATUM, _TID):
        return varde.isoformat() if isinstance(varde, (date, datetime)) else str(varde)
    return varde


def _kraev(tabell: str, kolumner: Iterable[str]) -> None:
    okanda = [k for k in kolumner if k not in TABELLER[tabell]]
    if okanda:
        raise KeyError(f"{tabell} har inga kolumner {okanda}")


# -- De fyra allmänna funktionerna -------------------------------------------


async def _in(storage: Any, tenant_id: str, tabell: str, falt: dict[str, Any]) -> dict[str, Any]:
    _kraev(tabell, falt)
    falt = {**falt, "tenant_id": tenant_id}
    if _ar_postgres(storage):
        kolumner = list(falt)
        platser = [_plats(tabell, k, i + 1) for i, k in enumerate(kolumner)]
        try:
            async with storage._scoped(tenant_id) as conn:
                rad = await conn.fetchrow(
                    f"insert into {tabell} ({', '.join(kolumner)}) values ({', '.join(platser)}) returning *",
                    *[_varde(tabell, k, falt[k]) for k in kolumner],
                )
        except Exception as fel:
            if _unik_krock(fel):
                raise FinnsRedan(str(fel)) from None
            raise
        return _rad(rad, tabell)
    tid = nu()
    rad = {k: None for k in TABELLER[tabell]}
    rad.update(json.loads(json.dumps(_STANDARD[tabell])))
    rad.update({"id": str(uuid.uuid4())})
    for k in ("created_at", "updated_at", "senast_sedd_at"):
        if k in TABELLER[tabell]:
            rad[k] = tid
    rad.update(json.loads(json.dumps(falt, default=str)))
    _minnets_unika(storage, tabell, rad)
    _minne(storage, tabell)[rad["id"]] = rad
    return dict(rad)


def _minnets_unika(storage: Any, tabell: str, rad: dict[str, Any]) -> None:
    """Minneslagrets motsvarighet till de unika indexen i migration 153."""
    andra = [r for r in _minne(storage, tabell).values()
             if r["tenant_id"] == rad["tenant_id"] and r["id"] != rad["id"]]
    if tabell == "crm_anslutningar":
        krock = any(r["namn"].lower() == rad["namn"].lower() for r in andra)
    elif tabell == "crm_bolag":
        krock = bool(rad.get("orgnr_nyckel")) and not rad.get("raderad_at") and any(
            r.get("orgnr_nyckel") == rad["orgnr_nyckel"] and not r.get("raderad_at") for r in andra)
    elif tabell == "crm_personer":
        krock = bool(rad.get("epost")) and not rad.get("raderad_at") and any(
            (r.get("epost") or "").lower() == rad["epost"].lower() and not r.get("raderad_at")
            for r in andra)
    elif tabell == "crm_externa_id":
        krock = any((r["anslutning_id"], r["objekt"], r["externt_id"])
                    == (rad["anslutning_id"], rad["objekt"], rad["externt_id"]) for r in andra)
    else:
        krock = False
    if krock:
        raise FinnsRedan(tabell)


async def _upp(
    storage: Any, tenant_id: str, tabell: str, rad_id: str, falt: dict[str, Any]
) -> dict[str, Any] | None:
    _kraev(tabell, falt)
    if "updated_at" in TABELLER[tabell] and "updated_at" not in falt:
        falt = {**falt, "updated_at": nu()}
    if not falt:
        return await _hamta(storage, tenant_id, tabell, rad_id)
    if _ar_postgres(storage):
        kolumner = list(falt)
        satser = [f"{k} = {_plats(tabell, k, i + 3)}" for i, k in enumerate(kolumner)]
        try:
            async with storage._scoped(tenant_id) as conn:
                rad = await conn.fetchrow(
                    f"update {tabell} set {', '.join(satser)} "
                    "where tenant_id = $1::text::uuid and id = $2::text::uuid returning *",
                    tenant_id, rad_id, *[_varde(tabell, k, falt[k]) for k in kolumner],
                )
        except Exception as fel:
            if _unik_krock(fel):
                raise FinnsRedan(str(fel)) from None
            raise
        return _rad(rad, tabell)
    rad = _minne(storage, tabell).get(rad_id)
    if not rad or rad["tenant_id"] != tenant_id:
        return None
    ny = {**rad, **json.loads(json.dumps(falt, default=str))}
    _minnets_unika(storage, tabell, ny)
    rad.update(ny)
    return dict(rad)


async def _hamta(storage: Any, tenant_id: str, tabell: str, rad_id: str) -> dict[str, Any] | None:
    rader = await _valj(storage, tenant_id, tabell, lika={"id": rad_id}, limit=1)
    return rader[0] if rader else None


async def _valj(
    storage: Any,
    tenant_id: str,
    tabell: str,
    *,
    lika: dict[str, Any] | None = None,
    bland: dict[str, list[Any]] | None = None,
    levande: bool = False,
    ordning: str = "created_at",
    fallande: bool = False,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Rader där varje `lika`-kolumn har värdet och varje `bland`-kolumn har
    något av värdena. `levande` utesluter mjukt raderade."""
    lika, bland = lika or {}, bland or {}
    _kraev(tabell, [*lika, *bland, ordning])
    if any(not v for v in bland.values()):
        return []
    if _ar_postgres(storage):
        villkor, varden = ["tenant_id = $1::text::uuid"], [tenant_id]
        for kol, varde in lika.items():
            if varde is None:
                villkor.append(f"{kol} is null")
            else:
                varden.append(_varde(tabell, kol, varde))
                villkor.append(f"{kol} = {_plats(tabell, kol, len(varden))}")
        for kol, lista in bland.items():
            varden.append([str(v) for v in lista])
            typ = TABELLER[tabell][kol]
            villkor.append(f"{kol} = any(${len(varden)}::text[]{'::uuid[]' if typ == _UUID else ''})")
        if levande:
            villkor.append("raderad_at is null")
        sql = (f"select * from {tabell} where {' and '.join(villkor)} "
               f"order by {ordning}{' desc' if fallande else ''}, id")
        if limit:
            sql += f" limit {int(limit)}"
        try:
            async with storage._scoped(tenant_id) as conn:
                rader = await conn.fetch(sql, *varden)
        except Exception as fel:
            if _saknar_tabell(fel):
                return []
            raise
        return [_rad(r, tabell) for r in rader]
    ut = []
    for rad in _minne(storage, tabell).values():
        if rad["tenant_id"] != tenant_id or (levande and rad.get("raderad_at")):
            continue
        if any(rad.get(k) != v for k, v in lika.items()):
            continue
        if any(str(rad.get(k)) not in {str(v) for v in lista} for k, lista in bland.items()):
            continue
        ut.append(dict(rad))
    ut.sort(key=lambda r: (r.get(ordning) is None, r.get(ordning) or "", r["id"]), reverse=fallande)
    return ut[:limit] if limit else ut


async def _ta_bort(storage: Any, tenant_id: str, tabell: str, rad_id: str) -> bool:
    if _ar_postgres(storage):
        async with storage._scoped(tenant_id) as conn:
            svar = await conn.execute(
                f"delete from {tabell} where tenant_id = $1::text::uuid and id = $2::text::uuid",
                tenant_id, rad_id,
            )
        return not str(svar).endswith(" 0")
    rad = _minne(storage, tabell).get(rad_id)
    if not rad or rad["tenant_id"] != tenant_id:
        return False
    del _minne(storage, tabell)[rad_id]
    return True


# -- Anslutningar ------------------------------------------------------------


async def lista_anslutningar(storage: Any, tenant_id: str) -> list[dict[str, Any]]:
    return await _valj(storage, tenant_id, "crm_anslutningar")


async def hamta_anslutning(storage: Any, tenant_id: str, ref: str) -> dict[str, Any] | None:
    """På id eller på namn (utan hänsyn till skiftläge), så att den som
    synkar kan skriva `"connection": "hubspot"` i stället för ett uuid."""
    try:
        uuid.UUID(str(ref))
    except ValueError:
        lagt = str(ref).strip().lower()
        return next((a for a in await lista_anslutningar(storage, tenant_id)
                     if a["namn"].lower() == lagt), None)
    return await _hamta(storage, tenant_id, "crm_anslutningar", str(ref))


async def skapa_anslutning(storage: Any, tenant_id: str, **falt: Any) -> dict[str, Any]:
    return await _in(storage, tenant_id, "crm_anslutningar", falt)


async def uppdatera_anslutning(storage: Any, tenant_id: str, rad_id: str, **falt: Any):
    return await _upp(storage, tenant_id, "crm_anslutningar", rad_id, falt)


async def ta_bort_anslutning(storage: Any, tenant_id: str, rad_id: str) -> bool:
    if not _ar_postgres(storage):
        # Kaskaden i migration 153: källsystemens id följer anslutningen.
        externa = _minne(storage, "crm_externa_id")
        for eid in [k for k, r in externa.items() if r["anslutning_id"] == rad_id]:
            del externa[eid]
    return await _ta_bort(storage, tenant_id, "crm_anslutningar", rad_id)


# -- Bolag och personer ------------------------------------------------------

_OBJEKTTABELL = {"bolag": "crm_bolag", "person": "crm_personer"}


async def skapa_post(storage: Any, tenant_id: str, objekt: str, falt: dict[str, Any]) -> dict[str, Any]:
    return await _in(storage, tenant_id, _OBJEKTTABELL[objekt], falt)


async def uppdatera_post(storage: Any, tenant_id: str, objekt: str, rad_id: str, falt: dict[str, Any]):
    return await _upp(storage, tenant_id, _OBJEKTTABELL[objekt], rad_id, falt)


async def hamta_post(
    storage: Any, tenant_id: str, objekt: str, rad_id: str, *, med_raderade: bool = False
) -> dict[str, Any] | None:
    rad = await _hamta(storage, tenant_id, _OBJEKTTABELL[objekt], rad_id)
    return None if rad and rad.get("raderad_at") and not med_raderade else rad


async def hitta_poster(
    storage: Any, tenant_id: str, objekt: str, kolumn: str, varden: Iterable[Any], *, med_raderade: bool = False
) -> list[dict[str, Any]]:
    """Poster där `kolumn` har något av värdena. Synkens uppslag i en fråga
    per sats i stället för en per post."""
    lista = sorted({str(v) for v in varden if v})
    return await _valj(storage, tenant_id, _OBJEKTTABELL[objekt], bland={kolumn: lista},
                       levande=not med_raderade)


def _markor(nyckel: str, rad_id: str) -> str:
    return base64.urlsafe_b64encode(json.dumps([nyckel, rad_id]).encode()).decode().rstrip("=")


def las_markor(markor: str | None) -> tuple[str, str] | None:
    if not markor:
        return None
    try:
        nyckel, rad_id = json.loads(base64.urlsafe_b64decode(markor + "=" * (-len(markor) % 4)))
        uuid.UUID(rad_id)
        return str(nyckel), rad_id
    except (ValueError, TypeError):
        raise ValueError("markor") from None


async def lista_poster(
    storage: Any,
    tenant_id: str,
    objekt: str,
    *,
    limit: int = 50,
    markor: str | None = None,
    ordning: str = "andrad",
    andrad_sedan: str | None = None,
    med_raderade: bool = False,
    lika: dict[str, Any] | None = None,
    q: str | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    """En sida poster och markören till nästa (None på sista sidan).

    `ordning="andrad"` går i ändringsordning, äldst först: den som synkar ut
    läser tills markören tar slut och börjar nästa gång från sin senaste tid.
    `ordning="namn"` är för listan i appen.
    """
    tabell = _OBJEKTTABELL[objekt]
    lika = {k: v for k, v in (lika or {}).items() if v is not None}
    _kraev(tabell, lika)
    limit = max(1, min(int(limit), 500))
    efter = las_markor(markor)
    namnkol = "namn" if objekt == "bolag" else "efternamn"
    sokkolumner = (("namn", "orgnr", "orgnr_nyckel", "doman", "postort") if objekt == "bolag"
                   else ("fornamn", "efternamn", "epost", "titel"))
    if _ar_postgres(storage):
        villkor, varden = ["tenant_id = $1::text::uuid"], [tenant_id]
        for kol, varde in lika.items():
            varden.append(_varde(tabell, kol, varde))
            villkor.append(f"{kol} = {_plats(tabell, kol, len(varden))}")
        if not med_raderade:
            villkor.append("raderad_at is null")
        if andrad_sedan:
            varden.append(andrad_sedan)
            villkor.append(f"updated_at >= ${len(varden)}::text::timestamptz")
        if q:
            varden.append(f"%{q.strip()}%")
            villkor.append("(" + " or ".join(f"{k} ilike ${len(varden)}" for k in sokkolumner) + ")")
        sortering = "updated_at" if ordning == "andrad" else f"lower(coalesce({namnkol}, ''))"
        if efter:
            varden.extend(efter)
            typ = "::text::timestamptz" if ordning == "andrad" else ""
            villkor.append(f"({sortering}, id) > (${len(varden) - 1}{typ}, ${len(varden)}::text::uuid)")
        try:
            async with storage._scoped(tenant_id) as conn:
                rader = await conn.fetch(
                    f"select * from {tabell} where {' and '.join(villkor)} "
                    f"order by {sortering}, id limit {limit + 1}", *varden)
        except Exception as fel:
            if _saknar_tabell(fel):
                return [], None
            raise
        poster = [_rad(r, tabell) for r in rader]
    else:
        def nyckel(r: dict[str, Any]) -> str:
            return r["updated_at"] if ordning == "andrad" else (r.get(namnkol) or "").lower()

        poster = []
        for rad in _minne(storage, tabell).values():
            if rad["tenant_id"] != tenant_id or (rad.get("raderad_at") and not med_raderade):
                continue
            if any(rad.get(k) != v for k, v in lika.items()):
                continue
            if andrad_sedan and _tid(rad["updated_at"]) < _tid(andrad_sedan):
                continue
            if q and not any(q.strip().lower() in str(rad.get(k) or "").lower() for k in sokkolumner):
                continue
            if efter and (nyckel(rad), rad["id"]) <= efter:
                continue
            poster.append(dict(rad))
        poster.sort(key=lambda r: (nyckel(r), r["id"]))
        poster = poster[: limit + 1]
    if len(poster) <= limit:
        return poster, None
    poster = poster[:limit]
    sist = poster[-1]
    return poster, _markor(sist["updated_at"] if ordning == "andrad" else (sist.get(namnkol) or "").lower(),
                           sist["id"])


def _tid(varde: str) -> datetime:
    tid = datetime.fromisoformat(str(varde).replace("Z", "+00:00"))
    return tid if tid.tzinfo else tid.replace(tzinfo=timezone.utc)


async def rakna_poster(storage: Any, tenant_id: str, objekt: str) -> dict[str, int]:
    """Antal levande poster, för bolag även per relation."""
    tabell = _OBJEKTTABELL[objekt]
    if _ar_postgres(storage):
        grupp = "relation" if objekt == "bolag" else "'alla'"
        try:
            async with storage._scoped(tenant_id) as conn:
                rader = await conn.fetch(
                    f"select {grupp} as grupp, count(*)::int as antal from {tabell} "
                    "where tenant_id = $1::text::uuid and raderad_at is null group by 1", tenant_id)
        except Exception as fel:
            if _saknar_tabell(fel):
                return {"alla": 0}
            raise
        ut = {r["grupp"]: r["antal"] for r in rader}
    else:
        ut: dict[str, int] = {}
        for rad in _minne(storage, tabell).values():
            if rad["tenant_id"] == tenant_id and not rad.get("raderad_at"):
                grupp = rad["relation"] if objekt == "bolag" else "alla"
                ut[grupp] = ut.get(grupp, 0) + 1
    ut["alla"] = sum(v for k, v in ut.items() if k != "alla") if objekt == "bolag" else ut.get("alla", 0)
    return ut


async def upptagna_rader(storage: Any, tenant_id: str) -> list[dict[str, Any]]:
    """Varje levande CRM-bolag i formen `storage.lista_upptagna_bolag` lämnar:
    det som finns i kundens CRM ska varken Iris eller en lista hämta igen."""
    rader = await _valj(storage, tenant_id, "crm_bolag", levande=True)
    return [{"company_name": r["namn"], "orgnr": r.get("orgnr"), "kalla": "crm", "list_id": None}
            for r in rader]


async def kundadresser(storage: Any, tenant_id: str) -> set[str]:
    """E-postadresserna till kundens befintliga kunder enligt CRM:et: bolagets
    egen adress och personernas, där bolaget har relationen kund. Sändspärren
    (app/leads/send_guard.py regel 3) läser dem: en befintlig kund ska inte få
    ett kallmejl."""
    if _ar_postgres(storage):
        try:
            async with storage._scoped(tenant_id) as conn:
                rader = await conn.fetch(
                    """select lower(epost) as epost from crm_bolag
                        where tenant_id = $1::text::uuid and raderad_at is null
                          and relation = 'kund' and epost is not null
                       union
                       select lower(p.epost) from crm_personer p
                         join crm_bolag b on b.id = p.bolag_id
                        where p.tenant_id = $1::text::uuid and p.raderad_at is null and p.epost is not null
                          and b.raderad_at is null and b.relation = 'kund'""", tenant_id)
        except Exception as fel:
            if _saknar_tabell(fel):
                return set()
            raise
        return {r["epost"] for r in rader}
    kunder = {b["id"]: b for b in _minne(storage, "crm_bolag").values()
              if b["tenant_id"] == tenant_id and not b.get("raderad_at") and b["relation"] == "kund"}
    ut = {b["epost"].lower() for b in kunder.values() if b.get("epost")}
    ut |= {p["epost"].lower() for p in _minne(storage, "crm_personer").values()
           if p["tenant_id"] == tenant_id and not p.get("raderad_at") and p.get("epost")
           and p.get("bolag_id") in kunder}
    return ut


# -- Papperskorgen -----------------------------------------------------------

#: En raderad post går att återställa så här länge. Sedan töms den.
PAPPERSKORG_DAGAR = 30
GRAVSTEN = "gravsten"

#: Vad som blir kvar av en tömd post: id, kund och tider. Allt annat nollas,
#: så att papperskorgen inte blir ett register över borttagna personer.
_TOMD: dict[str, dict[str, Any]] = {
    "bolag": {**{k: None for k in TABELLER["crm_bolag"]
                 if k not in ("id", "tenant_id", "created_at", "updated_at", "raderad_at")},
              "namn": "", "namnnyckel": "", "enskild_firma": False, "land": "SE", "relation": "ovrigt",
              "kontakta_inte": False, "extra": {}, "manuellt_andrade": {}, "kalla": GRAVSTEN},
    "person": {**{k: None for k in TABELLER["crm_personer"]
                  if k not in ("id", "tenant_id", "created_at", "updated_at", "raderad_at")},
               "kontakta_inte": False, "extra": {}, "manuellt_andrade": {}, "kalla": GRAVSTEN},
}


async def gor_gravsten(storage: Any, tenant_id: str, objekt: str, rad_id: str) -> None:
    """Tömmer posten för gott. Källsystemens id för den glöms, så att en ny
    synk skapar en ny post i stället för att väcka den raderade."""
    post = await _hamta(storage, tenant_id, _OBJEKTTABELL[objekt], rad_id)
    if post is None:
        return
    await _upp(storage, tenant_id, _OBJEKTTABELL[objekt], rad_id,
               {**_TOMD[objekt], "raderad_at": post.get("raderad_at") or nu()})
    for extern in (await externa_for_poster(storage, tenant_id, objekt, [rad_id])).get(rad_id, []):
        await _ta_bort(storage, tenant_id, "crm_externa_id", extern["id"])


async def tom_papperskorg(
    storage: Any, tenant_id: str, objekt: str, *, dagar: int = PAPPERSKORG_DAGAR,
    undanta: Iterable[str] = (),
) -> int:
    """Tömmer poster som legat raderade längre än `dagar`. Körs när något
    raderas och när en synk avslutas; högst 200 poster per varv. Adresserna i
    `undanta` (begränsad behandling, art. 18) töms inte: den som begärt
    begränsning har bett oss behålla uppgifterna orörda."""
    undanta = {str(a).casefold() for a in undanta}
    tabell = _OBJEKTTABELL[objekt]
    grans = datetime.now(timezone.utc) - timedelta(days=dagar)
    if _ar_postgres(storage):
        try:
            async with storage._scoped(tenant_id) as conn:
                rader = await conn.fetch(
                    f"select id, epost from {tabell} where tenant_id = $1::text::uuid "
                    "and raderad_at < $2 and kalla <> $3 limit 200", tenant_id, grans, GRAVSTEN)
        except Exception as fel:
            if _saknar_tabell(fel):
                return 0
            raise
        kandidater = [(str(r["id"]), r["epost"]) for r in rader]
    else:
        kandidater = [(r["id"], r.get("epost")) for r in _minne(storage, tabell).values()
                      if r["tenant_id"] == tenant_id and r.get("raderad_at") and r["kalla"] != GRAVSTEN
                      and _tid(r["raderad_at"]) < grans][:200]
    utgangna = [rad_id for rad_id, epost in kandidater if (epost or "").casefold() not in undanta]
    for rad_id in utgangna:
        await gor_gravsten(storage, tenant_id, objekt, rad_id)
    return len(utgangna)


# -- Källsystemens id --------------------------------------------------------


async def externa_for_kalla(
    storage: Any, tenant_id: str, anslutning_id: str, objekt: str, externa_id: Iterable[str]
) -> dict[str, dict[str, Any]]:
    rader = await _valj(storage, tenant_id, "crm_externa_id",
                        lika={"anslutning_id": anslutning_id, "objekt": objekt},
                        bland={"externt_id": sorted({str(e) for e in externa_id if e})})
    return {r["externt_id"]: r for r in rader}


async def externa_for_poster(
    storage: Any, tenant_id: str, objekt: str, post_id: Iterable[str]
) -> dict[str, list[dict[str, Any]]]:
    rader = await _valj(storage, tenant_id, "crm_externa_id", lika={"objekt": objekt},
                        bland={"post_id": sorted({str(p) for p in post_id if p})})
    ut: dict[str, list[dict[str, Any]]] = {}
    for rad in rader:
        ut.setdefault(rad["post_id"], []).append(rad)
    return ut


async def satt_externt_id(
    storage: Any, tenant_id: str, *, befintlig: dict[str, Any] | None, **falt: Any
) -> dict[str, Any]:
    falt["senast_sedd_at"] = nu()
    if befintlig:
        return await _upp(storage, tenant_id, "crm_externa_id", befintlig["id"], falt)
    return await _in(storage, tenant_id, "crm_externa_id", falt)


async def externa_ej_sedda(
    storage: Any, tenant_id: str, anslutning_id: str, objekt: str, korning_id: str
) -> list[dict[str, Any]]:
    """Poster från källan som den här fulla synken inte nämnde."""
    rader = await _valj(storage, tenant_id, "crm_externa_id",
                        lika={"anslutning_id": anslutning_id, "objekt": objekt})
    return [r for r in rader if r.get("senast_korning") != korning_id]


# -- Synkens liggare ---------------------------------------------------------


async def skapa_korning(storage: Any, tenant_id: str, **falt: Any) -> dict[str, Any]:
    return await _in(storage, tenant_id, "crm_synkkorningar", falt)


async def hamta_korning(storage: Any, tenant_id: str, rad_id: str) -> dict[str, Any] | None:
    return await _hamta(storage, tenant_id, "crm_synkkorningar", rad_id)


async def lista_korningar(storage: Any, tenant_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
    return await _valj(storage, tenant_id, "crm_synkkorningar", ordning="created_at",
                       fallande=True, limit=max(1, min(limit, 200)))


async def rakna_korning(
    storage: Any, tenant_id: str, rad_id: str, delta: dict[str, int], fel: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Lägger satsens utfall på körningen. I Postgres som en enda uppdatering,
    så att två satser i samma körning inte skriver över varandras räkning."""
    delta = {k: int(v) for k, v in delta.items() if k in RAKNARE and v}
    if _ar_postgres(storage):
        satser = [f"{k} = {k} + {v}" for k, v in delta.items()]
        satser.append(
            f"fel = case when jsonb_array_length(fel) >= {MAX_FEL} then fel "
            "else (select coalesce(jsonb_agg(e), '[]'::jsonb) from "
            f"(select e from jsonb_array_elements(fel || $3::text::jsonb) e limit {MAX_FEL}) s) end")
        async with storage._scoped(tenant_id) as conn:
            rad = await conn.fetchrow(
                f"update crm_synkkorningar set {', '.join(satser)}, updated_at = now() "
                "where tenant_id = $1::text::uuid and id = $2::text::uuid returning *",
                tenant_id, rad_id, json.dumps(fel, ensure_ascii=False))
        return _rad(rad, "crm_synkkorningar")
    rad = _minne(storage, "crm_synkkorningar").get(rad_id)
    if not rad or rad["tenant_id"] != tenant_id:
        return None
    for k, v in delta.items():
        rad[k] += v
    rad["fel"] = (rad["fel"] + json.loads(json.dumps(fel, default=str)))[:MAX_FEL]
    rad["updated_at"] = nu()
    return dict(rad)


async def avsluta_korning(
    storage: Any, tenant_id: str, rad_id: str, *, status: str, error: str | None = None, borttagna: int = 0
) -> dict[str, Any] | None:
    if borttagna:
        await rakna_korning(storage, tenant_id, rad_id, {"borttagna": borttagna}, [])
    return await _upp(storage, tenant_id, "crm_synkkorningar", rad_id,
                      {"status": status, "error": error, "completed_at": nu()})


# -- Idempotens --------------------------------------------------------------

_IDEMPOTENS_TIMMAR = 24


async def las_idempotens(storage: Any, tenant_id: str, nyckel: str) -> dict[str, Any] | None:
    grans = datetime.now(timezone.utc) - timedelta(hours=_IDEMPOTENS_TIMMAR)
    if _ar_postgres(storage):
        try:
            async with storage._scoped(tenant_id) as conn:
                rad = await conn.fetchrow(
                    "select vag, kroppshash, statuskod, svar from crm_idempotens "
                    "where tenant_id = $1::text::uuid and nyckel = $2 and created_at > $3",
                    tenant_id, nyckel, grans)
        except Exception as fel:
            if _saknar_tabell(fel):
                return None
            raise
        if rad is None:
            return None
        data = dict(rad)
        data["svar"] = json.loads(data["svar"]) if isinstance(data["svar"], str) else data["svar"]
        return data
    rad = _minne(storage, "crm_idempotens").get(f"{tenant_id}:{nyckel}")
    return dict(rad) if rad and _tid(rad["created_at"]) > grans else None


async def spara_idempotens(
    storage: Any, tenant_id: str, nyckel: str, *, vag: str, kroppshash: str, statuskod: int, svar: Any
) -> None:
    if _ar_postgres(storage):
        async with storage._scoped(tenant_id) as conn:
            await conn.execute(
                "delete from crm_idempotens where tenant_id = $1::text::uuid "
                f"and created_at < now() - interval '{_IDEMPOTENS_TIMMAR} hours'", tenant_id)
            await conn.execute(
                "insert into crm_idempotens (tenant_id, nyckel, vag, kroppshash, statuskod, svar) "
                "values ($1::text::uuid, $2, $3, $4, $5, $6::text::jsonb) "
                "on conflict (tenant_id, nyckel) do update set vag = excluded.vag, "
                "kroppshash = excluded.kroppshash, statuskod = excluded.statuskod, "
                "svar = excluded.svar, created_at = now()",
                tenant_id, nyckel, vag, kroppshash, statuskod, json.dumps(svar, ensure_ascii=False))
        return
    _minne(storage, "crm_idempotens")[f"{tenant_id}:{nyckel}"] = {
        "tenant_id": tenant_id, "vag": vag, "kroppshash": kroppshash, "statuskod": statuskod,
        "svar": json.loads(json.dumps(svar, default=str)), "created_at": nu(),
    }
