"""Lagringen för CRM:et (tabellerna crm_*, migration 160).

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
#: Råa bytes (bilagans innehåll). Skickas som `bytes` till asyncpg, läses
#: aldrig i en lista och går aldrig genom JSON i minneslagret.
_BYTES, _FLYT = "bytea", "float"

TABELLER: dict[str, dict[str, str | None]] = {
    "crm_anslutningar": {
        "id": _UUID, "tenant_id": _UUID, "namn": None, "system": None, "mappning": _JSON,
        "konfliktregel": None, "saknade": None, "standardrelation": None, "aktiv": _BOOL,
        "privatpersoner": _BOOL, "senaste_synk_at": _TID, "created_at": _TID, "updated_at": _TID,
    },
    "crm_bolag": {
        "id": _UUID, "tenant_id": _UUID, "namn": None, "namnnyckel": None, "orgnr": None,
        "orgnr_nyckel": None, "enskild_firma": _BOOL, "momsnr": None, "bolagsform": None,
        "sni": None, "webbplats": None, "doman": None, "epost": None, "telefon": None,
        "gatuadress": None, "co": None, "postnr": None, "postort": None, "land": None,
        "anstallda": _TAL, "omsattning": _TAL, "relation": None, "kund_sedan": _DATUM,
        "avtalsslut": _DATUM, "ansvarig": None, "kontakta_inte": _BOOL, "privatperson": _BOOL,
        "extra": _JSON,
        "manuellt_andrade": _JSON, "kalla": None, "prospect_id": _UUID,
        "created_at": _TID, "updated_at": _TID, "raderad_at": _TID,
    },
    "crm_personer": {
        "id": _UUID, "tenant_id": _UUID, "bolag_id": _UUID, "fornamn": None, "efternamn": None,
        "titel": None, "epost": None, "telefon": None, "mobil": None, "rattslig_grund": None,
        "kontakta_inte": _BOOL, "extra": _JSON, "manuellt_andrade": _JSON, "kalla": None,
        # Varifrån uppgiften om personen först kom, och när (GDPR art. 14,
        # migration 165). Inte samma sak som `kalla`, som säger vilken väg
        # posten kom in i Snajp (manuell, api, synk).
        "kalla_typ": None, "kalla_namn": None, "insamlad_at": _TID,
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
        # Rapporten till supporten (migration 163, app/crm/supportrapport.py).
        "supportrapport": _JSON, "support_lamnad_at": _TID, "support_arende": None,
    },
    # Webhooks ut (migration 162). Händelseloggen crm_handelser har löpnummer
    # som id och skrivs i satser: den har egna funktioner i app/crm/handelser.py.
    "crm_webhooks": {
        "id": _UUID, "tenant_id": _UUID, "url": None, "beskrivning": None, "handelser": _JSON,
        "hemlighet": None, "aktiv": _BOOL, "fel_i_rad": _TAL, "senast_ok_at": _TID,
        "senast_fel_at": _TID, "senast_fel": None, "avstangd_av": None,
        "created_at": _TID, "updated_at": _TID,
    },
    "crm_webhook_leveranser": {
        "id": _UUID, "tenant_id": _UUID, "webhook_id": _UUID, "handelsetyp": None, "kropp": _JSON,
        "status": None, "forsok": _TAL, "nasta_forsok_at": _TID, "statuskod": _TAL, "fel": None,
        "created_at": _TID, "updated_at": _TID, "levererad_at": _TID,
    },
    # Affärer, uppgifter, anteckningar, aktiviteter och bilagor (migration 164,
    # reglerna i app/crm/objekt.py).
    "crm_affarssteg": {
        "id": _UUID, "tenant_id": _UUID, "namn": None, "position": _TAL, "sannolikhet": _TAL,
        "typ": None, "farg": None, "created_at": _TID, "updated_at": _TID,
    },
    "crm_affarer": {
        "id": _UUID, "tenant_id": _UUID, "namn": None, "bolag_id": _UUID, "person_id": _UUID,
        "steg_id": _UUID, "belopp": _TAL, "valuta": None, "sannolikhet": _TAL, "forvantat_avslut": _DATUM,
        "avslutad_at": _TID, "forlustorsak": None, "forlustorsak_kod": None, "ansvarig": None, "position": _FLYT, "extra": _JSON,
        "kalla": None, "created_at": _TID, "updated_at": _TID, "raderad_at": _TID,
    },
    "crm_uppgifter": {
        "id": _UUID, "tenant_id": _UUID, "titel": None, "beskrivning": None, "status": None,
        "forfaller_at": _TID, "klar_at": _TID, "ansvarig": None, "bolag_id": _UUID, "person_id": _UUID,
        "affar_id": _UUID, "kalla": None, "created_at": _TID, "updated_at": _TID, "raderad_at": _TID,
    },
    "crm_anteckningar": {
        "id": _UUID, "tenant_id": _UUID, "titel": None, "text": None, "fast": _BOOL, "forfattare": None,
        "bolag_id": _UUID, "person_id": _UUID, "affar_id": _UUID, "kalla": None,
        "created_at": _TID, "updated_at": _TID, "raderad_at": _TID,
    },
    "crm_aktiviteter": {
        "id": _UUID, "tenant_id": _UUID, "typ": None, "rubrik": None, "text": None, "tid": _TID,
        "varaktighet_min": _TAL, "utfall": None, "ansvarig": None, "bolag_id": _UUID, "person_id": _UUID,
        "affar_id": _UUID, "kalla": None, "created_at": _TID, "updated_at": _TID, "raderad_at": _TID,
    },
    "crm_bilagor": {
        "id": _UUID, "tenant_id": _UUID, "filnamn": None, "typ": None, "storlek": _TAL, "innehall": _BYTES,
        "uppladdad_av": None, "bolag_id": _UUID, "person_id": _UUID, "affar_id": _UUID,
        "anteckning_id": _UUID, "kalla": None, "created_at": _TID, "updated_at": _TID, "raderad_at": _TID,
    },
}

#: Standardvärden som databasen sätter, speglade för minneslagret.
_STANDARD: dict[str, dict[str, Any]] = {
    "crm_anslutningar": {"system": "generisk", "mappning": {}, "konfliktregel": "kallan_vinner",
                         "saknade": "behall", "standardrelation": "kund", "aktiv": True,
                         "privatpersoner": False},
    "crm_bolag": {"namnnyckel": "", "enskild_firma": False, "land": "SE", "relation": "kund",
                  "kontakta_inte": False, "privatperson": False, "extra": {}, "manuellt_andrade": {}, "kalla": "manuell"},
    "crm_personer": {"kontakta_inte": False, "extra": {}, "manuellt_andrade": {}, "kalla": "manuell"},
    "crm_externa_id": {},
    "crm_synkkorningar": {"lage": "delta", "status": "processing", "startad_av": "api", "totalt": 0,
                          "skapade": 0, "uppdaterade": 0, "oforandrade": 0, "hoppade": 0,
                          "konflikter": 0, "borttagna": 0, "fel": []},
    "crm_webhooks": {"handelser": ["*"], "aktiv": True, "fel_i_rad": 0},
    "crm_webhook_leveranser": {"status": "vantar", "forsok": 0},
    "crm_affarssteg": {"position": 0, "sannolikhet": 0, "typ": "oppen"},
    "crm_affarer": {"valuta": "SEK", "position": 0.0, "extra": {}, "kalla": "manuell"},
    "crm_uppgifter": {"status": "att_gora", "kalla": "manuell"},
    "crm_anteckningar": {"text": "", "fast": False, "kalla": "manuell"},
    "crm_aktiviteter": {"typ": "ovrigt", "kalla": "manuell"},
    "crm_bilagor": {"kalla": "manuell"},
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


def _urval(tabell: str) -> str:
    """Kolumnerna en läsning hämtar: allt utom råa bytes. En bilagas innehåll
    läses bara av `bilagans_innehall`, aldrig i en lista eller ett svar."""
    if not any(typ == _BYTES for typ in TABELLER[tabell].values()):
        return "*"
    return ", ".join(k for k, typ in TABELLER[tabell].items() if typ != _BYTES)


def _utan_bytes(tabell: str, rad: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in rad.items() if TABELLER[tabell].get(k) != _BYTES}


def _kopia(falt: dict[str, Any]) -> dict[str, Any]:
    """Minneslagrets motsvarighet till en rundtur genom databasen: JSON för
    allt utom bytes, som lagras som de är."""
    return {k: bytes(v) if isinstance(v, (bytes, bytearray, memoryview))
            else json.loads(json.dumps(v, default=str)) for k, v in falt.items()}


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
                    f"insert into {tabell} ({', '.join(kolumner)}) values ({', '.join(platser)}) "
                    f"returning {_urval(tabell)}",
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
    for k in ("created_at", "updated_at", "senast_sedd_at", "nasta_forsok_at"):
        if k in TABELLER[tabell]:
            rad[k] = tid
    rad.update(_kopia(falt))
    _minnets_unika(storage, tabell, rad)
    _minne(storage, tabell)[rad["id"]] = rad
    return _utan_bytes(tabell, rad)


def _minnets_unika(storage: Any, tabell: str, rad: dict[str, Any]) -> None:
    """Minneslagrets motsvarighet till de unika indexen i migration 160."""
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
    elif tabell == "crm_affarssteg":
        krock = any(r["namn"].lower() == rad["namn"].lower() for r in andra)
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
                    f"where tenant_id = $1::text::uuid and id = $2::text::uuid returning {_urval(tabell)}",
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
    ny = {**rad, **_kopia(falt)}
    _minnets_unika(storage, tabell, ny)
    rad.update(ny)
    return _utan_bytes(tabell, rad)


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
        sql = (f"select {_urval(tabell)} from {tabell} where {' and '.join(villkor)} "
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
        ut.append(_utan_bytes(tabell, rad))
    # Talet 0 är ett värde, inte ett tomt: jämförs aldrig mot en sträng.
    ut.sort(key=lambda r: (r.get(ordning) is None, "" if r.get(ordning) is None else r[ordning], r["id"]),
            reverse=fallande)
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
        # Kaskaden i migration 160: källsystemens id följer anslutningen.
        externa = _minne(storage, "crm_externa_id")
        for eid in [k for k, r in externa.items() if r["anslutning_id"] == rad_id]:
            del externa[eid]
    return await _ta_bort(storage, tenant_id, "crm_anslutningar", rad_id)


# -- Bolag och personer ------------------------------------------------------

_OBJEKTTABELL = {"bolag": "crm_bolag", "person": "crm_personer", "affar": "crm_affarer",
                 "uppgift": "crm_uppgifter", "anteckning": "crm_anteckningar",
                 "aktivitet": "crm_aktiviteter", "bilaga": "crm_bilagor"}

#: Per objekt: kolumnen bokstavsordningen går på, och kolumnerna fritextsökningen läser.
_LISTA: dict[str, tuple[str, tuple[str, ...]]] = {
    "bolag": ("namn", ("namn", "orgnr", "orgnr_nyckel", "doman", "postort")),
    "person": ("efternamn", ("fornamn", "efternamn", "epost", "titel")),
    "affar": ("namn", ("namn", "ansvarig", "forlustorsak")),
    "uppgift": ("titel", ("titel", "beskrivning", "ansvarig")),
    "anteckning": ("titel", ("titel", "text")),
    "aktivitet": ("rubrik", ("rubrik", "text", "utfall")),
    "bilaga": ("filnamn", ("filnamn",)),
}
#: Tidpunkten en uppgift utan förfallodag sorteras som: sist.
_ALDRIG = "infinity"


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
    fore: dict[str, str] | None = None,
    tomma: Iterable[str] = (),
) -> tuple[list[dict[str, Any]], str | None]:
    """En sida poster och markören till nästa (None på sista sidan).

    `ordning="andrad"` går i ändringsordning, äldst först: den som synkar ut
    läser tills markören tar slut och börjar nästa gång från sin senaste tid.
    `ordning="andrad_fallande"` är samma ordning baklänges, senast ändrad
    först, för listan i appen. `ordning="namn"` är bokstavsordning.
    `ordning="raderad"` är papperskorgen: bara raderade poster som går att
    återställa, senast raderad först. `ordning="forfaller"` är uppgifternas
    förfallodag, tidigast först och de utan dag sist.

    `fore` är tidskolumner som ska ligga före en tidpunkt (`forfaller_at`
    före `due_before`). En post utan värde i kolumnen kommer inte med.

    `tomma` är kolumner som ska sakna värde (personer utan källa).
    """
    tabell = _OBJEKTTABELL[objekt]
    lika = {k: v for k, v in (lika or {}).items() if v is not None}
    fore = {k: v for k, v in (fore or {}).items() if v is not None}
    tomma = list(tomma)
    _kraev(tabell, [*lika, *fore, *tomma])
    limit = max(1, min(int(limit), 500))
    efter = las_markor(markor)
    namnkol, sokkolumner = _LISTA[objekt]
    korg = ordning == "raderad"
    fallande = ordning in ("andrad_fallande", "raderad")
    tidskolumn = {"andrad": "updated_at", "andrad_fallande": "updated_at", "raderad": "raderad_at",
                  "forfaller": "forfaller_at"}.get(ordning)
    if _ar_postgres(storage):
        villkor, varden = ["tenant_id = $1::text::uuid"], [tenant_id]
        for kol, varde in lika.items():
            varden.append(_varde(tabell, kol, varde))
            villkor.append(f"{kol} = {_plats(tabell, kol, len(varden))}")
        for kol, varde in fore.items():
            varden.append(str(varde))
            villkor.append(f"{kol} < ${len(varden)}::text::timestamptz")
        villkor.extend(f"{kol} is null" for kol in tomma)
        if korg:
            varden.append(GRAVSTEN)
            villkor.append(f"raderad_at is not null and kalla <> ${len(varden)}")
        elif not med_raderade:
            villkor.append("raderad_at is null")
        if andrad_sedan:
            varden.append(andrad_sedan)
            villkor.append(f"updated_at >= ${len(varden)}::text::timestamptz")
        if q:
            varden.append(f"%{q.strip()}%")
            villkor.append("(" + " or ".join(f"{k} ilike ${len(varden)}" for k in sokkolumner) + ")")
        if ordning == "forfaller":
            sortering = f"coalesce(forfaller_at, '{_ALDRIG}'::timestamptz)"
        else:
            sortering = tidskolumn or f"lower(coalesce({namnkol}, ''))"
        hall = " desc" if fallande else ""
        if efter:
            varden.extend(efter)
            typ = "::text::timestamptz" if tidskolumn else ""
            villkor.append(f"({sortering}, id) {'<' if fallande else '>'} "
                           f"(${len(varden) - 1}{typ}, ${len(varden)}::text::uuid)")
        try:
            async with storage._scoped(tenant_id) as conn:
                rader = await conn.fetch(
                    f"select {_urval(tabell)} from {tabell} where {' and '.join(villkor)} "
                    f"order by {sortering}{hall}, id{hall} limit {limit + 1}", *varden)
        except Exception as fel:
            if _saknar_tabell(fel):
                return [], None
            raise
        poster = [_rad(r, tabell) for r in rader]
    else:
        poster = []
        for rad in _minne(storage, tabell).values():
            if rad["tenant_id"] != tenant_id:
                continue
            if korg and (not rad.get("raderad_at") or rad["kalla"] == GRAVSTEN):
                continue
            if not korg and rad.get("raderad_at") and not med_raderade:
                continue
            if any(rad.get(k) != v for k, v in lika.items()):
                continue
            if any(rad.get(k) is not None for k in tomma):
                continue
            if any(not rad.get(k) or _tid(rad[k]) >= _tid(v) for k, v in fore.items()):
                continue
            if andrad_sedan and _tid(rad["updated_at"]) < _tid(andrad_sedan):
                continue
            if q and not any(q.strip().lower() in str(rad.get(k) or "").lower() for k in sokkolumner):
                continue
            nyckel = _sorteringsnyckel(rad, tidskolumn, namnkol)
            if efter and ((nyckel, rad["id"]) >= efter if fallande else (nyckel, rad["id"]) <= efter):
                continue
            poster.append(_utan_bytes(tabell, rad))
        poster.sort(key=lambda r: (_sorteringsnyckel(r, tidskolumn, namnkol), r["id"]), reverse=fallande)
        poster = poster[: limit + 1]
    if len(poster) <= limit:
        return poster, None
    poster = poster[:limit]
    sist = poster[-1]
    return poster, _markor(_sorteringsnyckel(sist, tidskolumn, namnkol), sist["id"])


def _sorteringsnyckel(rad: dict[str, Any], tidskolumn: str | None, namnkol: str) -> str:
    """Värdet en post sorteras och pagineras på. En tom tidpunkt (en uppgift
    utan förfallodag) blir `infinity`, som i Postgres sorterar sist och som
    strängjämförelsen i minneslagret också lägger sist."""
    if tidskolumn:
        return rad.get(tidskolumn) or _ALDRIG
    return (rad.get(namnkol) or "").lower()


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


#: Relationer som INTE spärrar bolaget för Iris och listbygget. Antons svar
#: 2026-11-26: tidigare kunder är fria att bearbeta. Relationen `ej_aktuell`
#: (migration 165, ett bolag som sagt nej eller inte passar) är det inte: den
#: står kvar bland de upptagna.
FRIA_RELATIONER = frozenset({"tidigare_kund"})


def upptagen_rad(bolag: dict[str, Any]) -> dict[str, Any] | None:
    """CRM-bolaget i formen `storage.lista_upptagna_bolag` lämnar, eller None
    när bolaget är fritt att bearbeta.

    Fritt är en tidigare kund, om inte posten säger kontakta inte: den spärren
    går före. Ett bolag med organisationsnummer utesluter på numret
    (`bara_orgnr`, läst av `upptagna.bolagsnycklar`): med en stor kundstock
    fäller namnet annars varje annat bolag som heter likadant. Namnet avgör
    för bolag utan nummer, och mot en kandidat som själv saknar nummer
    (docs/BESLUT.md 2026-11-26).
    """
    if bolag.get("raderad_at") or bolag.get("kalla") == GRAVSTEN:
        return None
    if bolag.get("relation") in FRIA_RELATIONER and not bolag.get("kontakta_inte"):
        return None
    return {"company_name": bolag["namn"], "orgnr": bolag.get("orgnr"), "kalla": "crm", "list_id": None,
            "bara_orgnr": bool(bolag.get("orgnr_nyckel"))}


def far_bearbetas(bolag: dict[str, Any]) -> bool:
    """Får bolaget bearbetas med utskick och Iris från CRM-miljön? Aldrig en
    privatperson, aldrig en post som säger kontakta inte, aldrig en raderad."""
    return not (bolag.get("raderad_at") or bolag.get("privatperson") or bolag.get("kontakta_inte"))


async def upptagna_rader(storage: Any, tenant_id: str) -> list[dict[str, Any]]:
    """Varje CRM-bolag som varken Iris eller en lista får hämta igen."""
    rader = await _valj(storage, tenant_id, "crm_bolag", levande=True)
    return [rad for rad in map(upptagen_rad, rader) if rad]


async def kontakta_inte_adresser(storage: Any, tenant_id: str) -> set[str]:
    """Adresser som aldrig får ett utskick enligt CRM:et: bolag och personer
    märkta kontakta inte (dit hör varje privatperson), och personerna hos ett
    sådant bolag. Sändspärren lägger dem till de avregistrerade, så att de
    gäller också kampanjutskick."""
    if _ar_postgres(storage):
        try:
            async with storage._scoped(tenant_id) as conn:
                rader = await conn.fetch(
                    """select lower(epost) as epost from crm_bolag
                        where tenant_id = $1::text::uuid and raderad_at is null
                          and kontakta_inte and epost is not null
                       union
                       select lower(p.epost) from crm_personer p
                         left join crm_bolag b on b.id = p.bolag_id and b.raderad_at is null
                        where p.tenant_id = $1::text::uuid and p.raderad_at is null and p.epost is not null
                          and (p.kontakta_inte or coalesce(b.kontakta_inte, false))""", tenant_id)
        except Exception as fel:
            if _saknar_tabell(fel):
                return set()
            raise
        return {r["epost"] for r in rader}
    bolag = {b["id"]: b for b in _minne(storage, "crm_bolag").values()
             if b["tenant_id"] == tenant_id and not b.get("raderad_at")}
    ut = {b["epost"].lower() for b in bolag.values() if b.get("kontakta_inte") and b.get("epost")}
    ut |= {p["epost"].lower() for p in _minne(storage, "crm_personer").values()
           if p["tenant_id"] == tenant_id and not p.get("raderad_at") and p.get("epost")
           and (p.get("kontakta_inte") or (bolag.get(p.get("bolag_id")) or {}).get("kontakta_inte"))}
    return ut


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
              "kontakta_inte": False, "privatperson": False, "extra": {}, "manuellt_andrade": {}, "kalla": GRAVSTEN},
    "person": {**{k: None for k in TABELLER["crm_personer"]
                  if k not in ("id", "tenant_id", "created_at", "updated_at", "raderad_at")},
               "kontakta_inte": False, "extra": {}, "manuellt_andrade": {}, "kalla": GRAVSTEN},
}
_BEHALLS = ("id", "tenant_id", "created_at", "updated_at", "raderad_at")
#: Affärer, uppgifter, anteckningar, aktiviteter och bilagor (migration 164).
#: Kolumner som är `not null` får ett tomt värde i stället för null.
_TOMD.update({
    objekt: {**{k: None for k in TABELLER[_OBJEKTTABELL[objekt]] if k not in _BEHALLS}, **tomt, "kalla": GRAVSTEN}
    for objekt, tomt in (
        ("affar", {"namn": "", "valuta": "SEK", "position": 0.0, "extra": {}}),
        ("uppgift", {"titel": "", "status": "att_gora"}),
        ("anteckning", {"text": "", "fast": False}),
        ("aktivitet", {"typ": "ovrigt", "rubrik": ""}),
        ("bilaga", {"filnamn": "", "typ": "", "storlek": 0, "innehall": b""}),
    )
})
# Aktivitetens tidpunkt är en tid, inte innehåll, och kolumnen är `not null`.
_TOMD["aktivitet"].pop("tid")

#: Vad som pekar på ett bolag eller en person och därför töms med det
#: (fritext och filer kan bära personuppgifter), och vad som bara tappar
#: kopplingen (en affär eller en uppgift är kundens egen, inte personens).
_TOMS_MED = ("anteckning", "aktivitet", "bilaga")
_TAPPAR_KOPPLING = ("affar", "uppgift")
_KOPPLING = {"bolag": "bolag_id", "person": "person_id", "affar": "affar_id", "anteckning": "anteckning_id"}


async def gor_gravsten(
    storage: Any, tenant_id: str, objekt: str, rad_id: str, *, via: str = "system", aktor: str | None = None
) -> None:
    """Tömmer posten för gott. Källsystemens id för den glöms, så att en ny
    synk skapar en ny post i stället för att väcka den raderade.

    Kaskaden (GDPR artikel 17): töms ett bolag eller en person, töms också
    anteckningar, aktiviteter och bilagor som pekar på posten, och affärer och
    uppgifter tappar kopplingen. En tömd anteckning tar sina bilagor med sig.
    """
    post = await _hamta(storage, tenant_id, _OBJEKTTABELL[objekt], rad_id)
    if post is None:
        return
    await _upp(storage, tenant_id, _OBJEKTTABELL[objekt], rad_id,
               {**_TOMD[objekt], "raderad_at": post.get("raderad_at") or nu()})
    if objekt in ("bolag", "person"):
        for extern in (await externa_for_poster(storage, tenant_id, objekt, [rad_id])).get(rad_id, []):
            await _ta_bort(storage, tenant_id, "crm_externa_id", extern["id"])
    from . import handelser  # sen import: handelser läser den här modulen

    logg = [handelser.Handelse(objekt, rad_id, "tomd")]
    kolumn = _KOPPLING.get(objekt) if objekt in ("bolag", "person", "anteckning") else None
    if kolumn:
        for beroende in _TOMS_MED:
            tabell = _OBJEKTTABELL[beroende]
            if kolumn not in TABELLER[tabell]:
                continue
            for rad in await _valj(storage, tenant_id, tabell, lika={kolumn: rad_id}):
                if rad.get("kalla") != GRAVSTEN:
                    await gor_gravsten(storage, tenant_id, beroende, rad["id"], via=via, aktor=aktor)
        for beroende in _TAPPAR_KOPPLING if objekt != "anteckning" else ():
            tabell = _OBJEKTTABELL[beroende]
            for rad in await _valj(storage, tenant_id, tabell, lika={kolumn: rad_id}):
                if rad.get("kalla") == GRAVSTEN:
                    continue
                ny = await _upp(storage, tenant_id, tabell, rad["id"], {kolumn: None})
                logg.append(handelser.Handelse(beroende, rad["id"], "andrad", falt=[kolumn], post=ny))
    await handelser.logga(storage, tenant_id, logg, kalla=via, aktor=aktor)


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
    # Bara bolag och personer bär en adress som kan vara begränsad.
    epost = "epost" if "epost" in TABELLER[tabell] else "null::text as epost"
    if _ar_postgres(storage):
        try:
            async with storage._scoped(tenant_id) as conn:
                rader = await conn.fetch(
                    f"select id, {epost} from {tabell} where tenant_id = $1::text::uuid "
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


#: Objekten från migration 164. Deras papperskorgar töms tillsammans, så att
#: löftet om 30 dagar inte hänger på att ännu en post av samma sort raderas.
OBJEKT_164 = ("affar", "uppgift", "anteckning", "aktivitet", "bilaga")


async def tom_papperskorgarna(storage: Any, tenant_id: str) -> int:
    """Tömmer de utgångna posterna för alla fem objekten från migration 164.
    Körs när någon post raderas, när en bilaga laddas upp (innan kvoten
    prövas) och när en synk avslutas."""
    antal = 0
    for objekt in OBJEKT_164:
        antal += await tom_papperskorg(storage, tenant_id, objekt)
    return antal


# -- Bilagornas innehåll -----------------------------------------------------


async def bilagans_innehall(storage: Any, tenant_id: str, rad_id: str) -> bytes | None:
    """Filens bytes. Den enda läsningen som hämtar kolumnen `innehall`."""
    if _ar_postgres(storage):
        try:
            async with storage._scoped(tenant_id) as conn:
                varde = await conn.fetchval(
                    "select innehall from crm_bilagor where tenant_id = $1::text::uuid and id = $2::text::uuid",
                    tenant_id, rad_id)
        except Exception as fel:
            if _saknar_tabell(fel):
                return None
            raise
        return bytes(varde) if varde is not None else None
    rad = _minne(storage, "crm_bilagor").get(rad_id)
    return rad["innehall"] if rad and rad["tenant_id"] == tenant_id else None


async def bilagornas_storlek(storage: Any, tenant_id: str) -> int:
    """Bytes kunden har i bilagor, papperskorgen medräknad: en raderad fil
    ligger kvar tills den töms."""
    if _ar_postgres(storage):
        try:
            async with storage._scoped(tenant_id) as conn:
                return int(await conn.fetchval(
                    "select coalesce(sum(storlek), 0)::bigint from crm_bilagor where tenant_id = $1::text::uuid",
                    tenant_id))
        except Exception as fel:
            if _saknar_tabell(fel):
                return 0
            raise
    return sum(int(r.get("storlek") or 0) for r in _minne(storage, "crm_bilagor").values()
               if r["tenant_id"] == tenant_id)


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
