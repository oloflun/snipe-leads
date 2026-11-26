"""Snajp CRM: det publika API:t, version 1 (/api/crm/v1).

API:t kunden bygger mot från sitt eget CRM. Det är versionerat och skilt från
den interna ytan, som får fortsätta ändras fritt. Fältnamnen är engelska,
eftersom den som integrerar oftast sitter med ett engelskt system på andra
sidan. Felmeddelanden lämnas på engelska och svenska.

    X-API-Key          nyckel med omfång (app/crm/nycklar.py) eller kundens egen
    Idempotency-Key    valfri på varje POST: samma nyckel ger samma svar i ett dygn
    cursor / limit     sidindelning på varje lista
    429 + Retry-After  600 anrop per minut och kund

Två vägar in för kunddata:

1. `POST /sync/companies` och `/sync/people`: en sats i källsystemets eget
   format, tolkad av anslutningens fältmappning. Varje anrop är en körning i
   liggaren.
2. `POST /sync/runs` → satser → `/complete`: en full synk i flera satser. Bara
   den kan avgöra vad som försvunnit ur källan.

Dessutom vanlig läsning och skrivning av enskilda bolag och personer, med
CRM:ets egna fältnamn.

Varje endpoint kräver sitt omfång. Skrivvägarna står bakom avtalsgrinden:
kundens kundregister är personuppgifter, och dem behandlar Snajp bara med ett
registrerat avtal (INV-AVTAL-001).
"""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from ..avtalsgrind import avtal_saknas
from ..crm import adaptrar, falt, handelser, lagring, nycklar, supportrapport, synk, tillgang, webhooks
from ..integrationer import hemligheter
from .deps import kraev_uuid, require_crm_nyckel
from .rate_limit import RateLimitExceededError, RateLimitRule, SlidingWindowRateLimiter

router = APIRouter(prefix="/api/crm/v1", tags=["Snajp CRM"])

VERSION = "1.0.0"
MAX_SATS = 500
MAX_KROPP = 8 * 1024 * 1024
_TAK = RateLimitRule(max_requests=600, window_seconds=60)
_begransare = SlidingWindowRateLimiter()


def nollstall_tak() -> None:
    """Bara för tester."""
    _begransare._hits.clear()


def fel(status: int, kod: str, en: str, sv: str, **mer: Any) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": kod, "message": en, "meddelande": sv, **mer})


def tillagg_saknas() -> HTTPException:
    return fel(403, "addon_missing",
               "Snajp CRM is an add-on that is not enabled for this workspace. Contact Snajp.",
               "Snajp CRM är ett tillägg som inte är påslaget för arbetsytan. Kontakta Snajp.")


def kraev(omfang: str):
    """Dependency: giltig nyckel med omfånget, tillägget påslaget, inom taket."""

    async def _beroende(request: Request, response: Response, tenant: dict = Depends(require_crm_nyckel)) -> dict:
        if not nycklar.tillater(tenant.get("omfang"), omfang):
            raise fel(403, "scope_missing", f"The key lacks the scope {omfang}.",
                      f"Nyckeln saknar omfånget {omfang}.", scope=omfang)
        # CRM:et är ett tillägg, fritt under provperioden (app/crm/tillgang.py).
        if not await tillgang.har_tillgang(request.app.state.storage, tenant["tenant_id"]):
            raise tillagg_saknas()
        try:
            _begransare.check(f"crm:{tenant['tenant_id']}", _TAK)
        except RateLimitExceededError:
            raise HTTPException(
                status_code=429,
                detail={"code": "rate_limited", "message": "Too many requests. Retry in a minute.",
                        "meddelande": "För många anrop. Försök igen om en minut."},
                headers={"Retry-After": "60", "X-RateLimit-Limit": str(_TAK.max_requests),
                         "X-RateLimit-Remaining": "0"},
            ) from None
        kvar = _TAK.max_requests - len(_begransare._hits[f"crm:{tenant['tenant_id']}"])
        response.headers["X-RateLimit-Limit"] = str(_TAK.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(kvar, 0))
        return tenant

    return _beroende


def _ursprung(request: Request, tenant: dict) -> dict[str, Any]:
    """Vem som skrev, för händelseloggen. Kundens egen nyckel (omfång *) är
    appen, och webben skickar då användarens id i X-Snajp-User. En nyckel med
    omfång är en integration."""
    if "*" in tenant.get("omfang", ["*"]):
        anvandare = (request.headers.get("X-Snajp-User") or "").strip()[:80]
        return {"via": "app", "aktor": f"anvandare:{anvandare}" if anvandare else None}
    return {"via": "api", "aktor": f"nyckel:{tenant.get('nyckel_id') or ''}"}


async def _avtal(request: Request, tenant: dict) -> None:
    if await avtal_saknas(request.app.state.storage, tenant["tenant_id"]):
        raise fel(403, "agreement_missing",
                  "The data processing agreement is not registered yet. Contact Snajp.",
                  "Personuppgiftsbiträdesavtalet är inte registrerat än. Kontakta Snajp.")


# -- Fältnamnen ut och in ----------------------------------------------------

_RELATION_UT = {"kund": "customer", "tidigare_kund": "former_customer", "prospekt": "prospect",
                "partner": "partner", "leverantor": "supplier", "ovrigt": "other"}
_RELATION_IN = {v: k for k, v in _RELATION_UT.items()}
_GRUND_UT = {"avtal": "contract", "berattigat_intresse": "legitimate_interest", "samtycke": "consent"}
_GRUND_IN = {v: k for k, v in _GRUND_UT.items()}

_BOLAG = {"name": "namn", "org_number": "orgnr", "vat_number": "momsnr", "legal_form": "bolagsform",
          "sni_code": "sni", "website": "webbplats", "email": "epost", "phone": "telefon",
          "employees": "anstallda", "revenue_sek": "omsattning", "relation": "relation",
          "customer_since": "kund_sedan", "contract_end": "avtalsslut", "owner": "ansvarig",
          "do_not_contact": "kontakta_inte", "private_person": "privatperson"}
_ADRESS ={"street": "gatuadress", "co": "co", "postal_code": "postnr", "city": "postort", "country": "land"}
_PERSON = {"first_name": "fornamn", "last_name": "efternamn", "title": "titel", "email": "epost",
           "phone": "telefon", "mobile": "mobil", "legal_basis": "rattslig_grund",
           "do_not_contact": "kontakta_inte", "company_id": "bolag_id"}


def _externa(rader: list[dict[str, Any]], anslutningar: dict[str, str]) -> list[dict[str, Any]]:
    return [{"connection": anslutningar.get(r["anslutning_id"], r["anslutning_id"]),
             "id": r["externt_id"], "last_seen_at": r.get("senast_sedd_at")} for r in rader]


def bolag_ut(rad: dict[str, Any], externa: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    ut = {"id": rad["id"], **{en: rad.get(sv) for en, sv in _BOLAG.items()}}
    ut["relation"] = _RELATION_UT.get(rad.get("relation"), "other")
    ut["domain"] = rad.get("doman")
    ut["address"] = {en: rad.get(sv) for en, sv in _ADRESS.items()}
    ut["sole_proprietor"] = bool(rad.get("enskild_firma"))
    ut["private_person"] = bool(rad.get("privatperson"))
    ut["custom"] = rad.get("extra") or {}
    ut["source"] = rad.get("kalla")
    ut["external_ids"] = externa or []
    ut.update(created_at=rad.get("created_at"), updated_at=rad.get("updated_at"), deleted_at=rad.get("raderad_at"))
    ut["purge_at"] = _toms(rad)
    return ut


def _toms(rad: dict[str, Any]) -> str | None:
    """När en raderad post töms för gott: trettio dagar efter raderingen."""
    if not rad.get("raderad_at") or rad.get("kalla") == lagring.GRAVSTEN:
        return None
    return (lagring._tid(rad["raderad_at"]) + timedelta(days=lagring.PAPPERSKORG_DAGAR)).isoformat()


def person_ut(rad: dict[str, Any], externa: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    ut = {"id": rad["id"], **{en: rad.get(sv) for en, sv in _PERSON.items()}}
    ut["legal_basis"] = _GRUND_UT.get(rad.get("rattslig_grund"))
    ut["custom"] = rad.get("extra") or {}
    ut["source"] = rad.get("kalla")
    ut["external_ids"] = externa or []
    ut.update(created_at=rad.get("created_at"), updated_at=rad.get("updated_at"), deleted_at=rad.get("raderad_at"))
    ut["purge_at"] = _toms(rad)
    return ut


handelser.registrera_form("bolag", bolag_ut)
handelser.registrera_form("person", person_ut)

#: CRM:ets fältnamn till API:ts, för fälten som nämns i händelseloggen.
_FALT_UT = {**{sv: en for en, sv in _BOLAG.items()}, **{sv: en for en, sv in _PERSON.items()},
            **{sv: f"address.{en}" for en, sv in _ADRESS.items()}, "extra": "custom"}


def handelse_ut(rad: dict[str, Any]) -> dict[str, Any]:
    return {"seq": rad["id"], "object": handelser.OBJEKT_UT.get(rad["objekt"], rad["objekt"]), "id": rad["post_id"],
            "type": handelser.TYP_UT[rad["typ"]], "fields": [_FALT_UT.get(f, f) for f in rad.get("falt") or []],
            "source": rad.get("kalla"), "actor": rad.get("aktor"), "at": rad.get("created_at")}


def _in(objekt: str, kropp: dict[str, Any]) -> dict[str, Any]:
    """Anropets engelska fält till CRM:ets. Okända fält avvisas, så att ett
    stavfel inte tyst blir ett tappat värde."""
    karta = _BOLAG if objekt == "bolag" else _PERSON
    ut: dict[str, Any] = {}
    for namn, varde in kropp.items():
        if namn in karta:
            ut[karta[namn]] = varde
        elif namn == "address" and objekt == "bolag":
            for del_, v in (varde or {}).items():
                if del_ not in _ADRESS:
                    raise fel(422, "unknown_field", f"Unknown field address.{del_}.", f"Okänt fält address.{del_}.")
                ut[_ADRESS[del_]] = v
        elif namn == "custom":
            ut["extra"] = varde or {}
        else:
            raise fel(422, "unknown_field", f"Unknown field {namn}.", f"Okänt fält {namn}.")
    if ut.get("relation") is not None:
        ut["relation"] = _RELATION_IN.get(ut["relation"], ut["relation"])
    if ut.get("rattslig_grund") is not None:
        ut["rattslig_grund"] = _GRUND_IN.get(ut["rattslig_grund"], ut["rattslig_grund"])
    return ut


def _ogiltig(orsak: synk.OgiltigPost) -> HTTPException:
    tillbaka = {**{sv: en for en, sv in _BOLAG.items()}, **{sv: en for en, sv in _PERSON.items()},
                **{sv: f"address.{en}" for en, sv in _ADRESS.items()}}
    falten = [{"field": tillbaka.get(f["falt"], f["falt"]), "code": f["kod"]} for f in orsak.fel]
    return fel(422, "invalid_fields", "One or more fields could not be interpreted.",
               "Ett eller flera fält gick inte att tolka.", fields=falten)


# -- Kropparna (för OpenAPI) -------------------------------------------------


class _Kropp(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Address(_Kropp):
    street: str | None = Field(None, description="Street address. Gatuadress.")
    co: str | None = Field(None, description="c/o line.")
    postal_code: str | None = Field(None, description="Postal code. Swedish codes are stored as `NNN NN`.")
    city: str | None = Field(None, description="Postort.")
    country: str | None = Field(None, description="ISO 3166-1 alpha-2. Defaults to SE.")


Relation = Literal["customer", "former_customer", "prospect", "partner", "supplier", "other"]
SystemNamn = Literal.__getitem__(adaptrar.SYSTEM)


class CompanyIn(_Kropp):
    name: str | None = Field(None, description="Company name. Required when creating.")
    org_number: str | None = Field(
        None, description="Swedish organisationsnummer. `556036-0793`, `5560360793`, `16556036-0793` "
        "and `SE556036079301` are all accepted. The check digit is verified. Unique per customer: "
        "posting an existing number updates that company.")
    vat_number: str | None = Field(None, description="Momsregistreringsnummer, e.g. `SE556036079301`.")
    legal_form: str | None = Field(None, description="Bolagsform, e.g. AB.")
    sni_code: str | None = Field(None, description="SNI industry code.")
    website: str | None = None
    email: str | None = Field(None, description="The company's own address (info@, kontakt@).")
    phone: str | None = Field(None, description="Stored as E.164. `08-123 456 78` becomes `+46812345678`.")
    address: Address | None = None
    employees: int | None = None
    revenue_sek: int | None = Field(None, description="Annual revenue in SEK.")
    relation: Relation | None = Field(None, description="Defaults to `customer`.")
    customer_since: str | None = Field(None, description="ISO 8601 date.")
    contract_end: str | None = Field(None, description="ISO 8601 date. Avtalsslut.")
    owner: str | None = Field(None, description="Account owner in your organisation.")
    do_not_contact: bool | None = None
    private_person: bool | None = Field(
        None, description="The customer is a private person, not a company. No personal identity number "
        "is stored, and the record is always `do_not_contact`: it is left out of every send, list and Iris run.")
    custom: dict[str, Any] | None = Field(None, description="Your own fields, up to 50 scalar values.")


class PersonIn(_Kropp):
    first_name: str | None = None
    last_name: str | None = None
    title: str | None = None
    email: str | None = Field(None, description="Unique per customer: posting an existing address updates that person.")
    phone: str | None = None
    mobile: str | None = None
    company_id: str | None = Field(None, description="Id of a company in Snajp CRM.")
    legal_basis: Literal["contract", "legitimate_interest", "consent"] | None = Field(
        None, description="GDPR article 6 basis for holding the person.")
    do_not_contact: bool | None = None
    custom: dict[str, Any] | None = None


class ConnectionIn(_Kropp):
    name: str | None = Field(None, description="Your name for the source, e.g. `hubspot`. Unique.")
    system: SystemNamn | None = Field(None, description="Selects the default field mapping.")
    mapping: dict[str, Any] | None = Field(
        None, description="Overrides on top of the system's default mapping, per object and target field. "
        "See GET /connections/systems for the defaults and the format.")
    conflict_rule: Literal["source_wins", "snajp_wins", "newest_wins"] | None = None
    missing_records: Literal["keep", "mark_former_customer", "delete"] | None = Field(
        None, description="What a completed full sync does with records the source no longer has.")
    default_relation: Relation | None = None
    include_private_persons: bool | None = Field(
        None, description="Off by default: records the source marks as private persons are skipped "
        "(`reason: privatperson`). Turn it on to store them, marked `private_person` and `do_not_contact`.")
    active: bool | None = None


class RunIn(_Kropp):
    connection: str = Field(description="Connection id or name.")
    mode: Literal["delta", "full"] = "delta"


class Batch(_Kropp):
    connection: str | None = Field(None, description="Connection id or name. Required on /sync/companies and /sync/people.")
    items: list[dict[str, Any]] = Field(description=f"Records in the source system's own format. At most {MAX_SATS}.")


class Preview(_Kropp):
    object: Literal["company", "person"] = "company"
    items: list[dict[str, Any]]
    mapping: dict[str, Any] | None = Field(None, description="Try a mapping without saving it.")


_KONFLIKT = {"source_wins": "kallan_vinner", "snajp_wins": "snajp_vinner", "newest_wins": "nyast_vinner"}
_SAKNADE = {"keep": "behall", "mark_former_customer": "tidigare_kund", "delete": "ta_bort"}
_OBJEKT = {"company": "bolag", "person": "person", "companies": "bolag", "people": "person"}


def anslutning_ut(rad: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": rad["id"], "name": rad["namn"], "system": rad["system"], "mapping": rad.get("mappning") or {},
        "conflict_rule": next(k for k, v in _KONFLIKT.items() if v == rad["konfliktregel"]),
        "missing_records": next(k for k, v in _SAKNADE.items() if v == rad["saknade"]),
        "default_relation": _RELATION_UT.get(rad["standardrelation"], "customer"),
        "include_private_persons": bool(rad.get("privatpersoner")),
        "active": bool(rad["aktiv"]), "last_sync_at": rad.get("senaste_synk_at"),
        "created_at": rad.get("created_at"), "updated_at": rad.get("updated_at"),
    }


def korning_ut(rad: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": rad["id"], "connection_id": rad.get("anslutning_id"), "mode": rad["lage"], "status": rad["status"],
        "started_by": rad["startad_av"],
        "counts": {"total": rad["totalt"], "created": rad["skapade"], "updated": rad["uppdaterade"],
                   "unchanged": rad["oforandrade"], "skipped": rad["hoppade"], "conflicts": rad["konflikter"],
                   "removed": rad["borttagna"]},
        "errors": rad.get("fel") or [], "error": rad.get("error"),
        # Samma fel i enkla ord, för den som inte ska behöva läsa koder.
        "issues": [{"kind": r["sort"], "object": handelser.OBJEKT_UT.get(r["objekt"], r["objekt"]),
                    "field": _FALT_UT.get(r["falt"], r["falt"]) if r["falt"] else None, "count": r["antal"]}
                   for r in supportrapport.enkelt(rad)],
        # Satt när körningen hade fel: rapporten har då gått vidare till Snajps support.
        "support": ({"forwarded_at": rad["support_lamnad_at"], "ticket": rad.get("support_arende")}
                    if rad.get("support_lamnad_at") else None),
        "created_at": rad.get("created_at"), "updated_at": rad.get("updated_at"),
        "completed_at": rad.get("completed_at"),
    }


_STATUS_UT = {"skapad": "created", "uppdaterad": "updated", "oforandrad": "unchanged", "hoppad": "skipped",
              "konflikt": "conflict", "raderad": "removed"}


def _sats_ut(svar: dict[str, Any], korning: dict[str, Any] | None) -> dict[str, Any]:
    s = svar["summering"]
    return {
        "run": korning_ut(korning) if korning else None,
        "counts": {"total": s.get("totalt", 0), "created": s.get("skapade", 0), "updated": s.get("uppdaterade", 0),
                   "unchanged": s.get("oforandrade", 0), "skipped": s.get("hoppade", 0),
                   "conflicts": s.get("konflikter", 0), "removed": s.get("borttagna", 0)},
        "items": [{"index": p["index"], "status": _STATUS_UT[p["status"]], "id": p["id"],
                   "external_id": p["externt_id"],
                   **({"reason": p["orsak"]} if p.get("orsak") else {}),
                   **({"conflicting_id": p["krockar_med"]} if p.get("krockar_med") else {}),
                   **({"kept_fields": p["behallna_falt"]} if p.get("behallna_falt") else {}),
                   **({"field_errors": p["faltfel"]} if p.get("faltfel") else {})}
                  for p in svar["poster"]],
    }


# -- Idempotens --------------------------------------------------------------


async def _idempotent(request: Request, tenant: dict, arbete) -> Response:
    """Kör `arbete` (→ (statuskod, svar)) högst en gång per Idempotency-Key.

    Samma nyckel med samma kropp ger det sparade svaret tillbaka. Samma nyckel
    med en annan kropp är ett fel hos anroparen och avvisas, i stället för att
    tyst ge svaret på ett annat anrop.
    """
    nyckel = (request.headers.get("Idempotency-Key") or "").strip()
    if len(nyckel) > 200:
        raise fel(422, "idempotency_key_too_long", "Idempotency-Key is at most 200 characters.",
                  "Idempotency-Key får vara högst 200 tecken.")
    storage = request.app.state.storage
    if not nyckel:
        status, svar = await arbete()
        return JSONResponse(svar, status_code=status)
    kroppshash = hashlib.sha256(await request.body()).hexdigest()
    vag = f"{request.method} {request.url.path}"
    sparad = await lagring.las_idempotens(storage, tenant["tenant_id"], nyckel)
    if sparad:
        if sparad["vag"] != vag or sparad["kroppshash"] != kroppshash:
            raise fel(422, "idempotency_key_reused",
                      "This Idempotency-Key was used for a different request.",
                      "Den här Idempotency-Key har använts för ett annat anrop.")
        return JSONResponse(sparad["svar"], status_code=sparad["statuskod"],
                            headers={"Idempotent-Replayed": "true"})
    status, svar = await arbete()
    await lagring.spara_idempotens(storage, tenant["tenant_id"], nyckel, vag=vag, kroppshash=kroppshash,
                                   statuskod=status, svar=svar)
    return JSONResponse(svar, status_code=status)


# -- Nyckeln själv -----------------------------------------------------------


@router.get("/me", summary="The key in use")
async def jag(tenant: dict = Depends(kraev("crm:las"))) -> dict:
    """Which customer the key belongs to, its scopes and the rate limit."""
    return {"tenant": tenant["tenant_name"], "scopes": tenant.get("omfang", ["*"]),
            "rate_limit": {"requests": _TAK.max_requests, "window_seconds": int(_TAK.window_seconds)},
            "api_version": VERSION}


# -- Bolag och personer ------------------------------------------------------


_ORDNING = {"updated": "andrad", "-updated": "andrad_fallande", "name": "namn"}


async def _lista(request: Request, tenant: dict, objekt: str, *, limit: int, cursor: str | None,
                 sort: str, updated_since: str | None, include_deleted: bool, q: str | None,
                 lika: dict[str, Any], only_deleted: bool = False) -> dict:
    storage = request.app.state.storage
    try:
        if updated_since:
            updated_since = lagring._tid(updated_since).isoformat()
        poster, nasta = await lagring.lista_poster(
            storage, tenant["tenant_id"], objekt, limit=limit, markor=cursor,
            ordning="raderad" if only_deleted else _ORDNING[sort], andrad_sedan=updated_since,
            med_raderade=include_deleted, lika=lika, q=q)
    except ValueError:
        raise fel(422, "invalid_parameter", "cursor or updated_since could not be read.",
                  "cursor eller updated_since gick inte att läsa.") from None
    externa = await lagring.externa_for_poster(storage, tenant["tenant_id"], objekt, [p["id"] for p in poster])
    namn = {a["id"]: a["namn"] for a in await lagring.lista_anslutningar(storage, tenant["tenant_id"])} if externa else {}
    ut = bolag_ut if objekt == "bolag" else person_ut
    return {"data": [ut(p, _externa(externa.get(p["id"], []), namn)) for p in poster], "next_cursor": nasta}


async def _en(request: Request, tenant: dict, objekt: str, rad_id: str, *, med_raderade: bool = False) -> dict:
    storage = request.app.state.storage
    post = await lagring.hamta_post(storage, tenant["tenant_id"], objekt, kraev_uuid(rad_id, "Posten"),
                                    med_raderade=med_raderade)
    if post is None:
        raise fel(404, "not_found", "The record does not exist.", "Posten finns inte.")
    externa = await lagring.externa_for_poster(storage, tenant["tenant_id"], objekt, [post["id"]])
    namn = {a["id"]: a["namn"] for a in await lagring.lista_anslutningar(storage, tenant["tenant_id"])} if externa else {}
    return (bolag_ut if objekt == "bolag" else person_ut)(post, _externa(externa.get(post["id"], []), namn))


async def _skapa(request: Request, tenant: dict, objekt: str, kropp: BaseModel) -> Response:
    await _avtal(request, tenant)
    storage = request.app.state.storage
    falten = _in(objekt, kropp.model_dump(exclude_unset=True))

    async def arbete():
        try:
            if objekt == "person" and falten.get("bolag_id"):
                await _kraev_bolag(storage, tenant, falten["bolag_id"])
            post, skapad = await synk.skapa(storage, tenant["tenant_id"], objekt, falten, kalla="api",
                                            **_ursprung(request, tenant))
        except synk.OgiltigPost as orsak:
            raise _ogiltig(orsak) from None
        except lagring.FinnsRedan:
            raise await _krock(storage, tenant, objekt, falten) from None
        return (201 if skapad else 200), (bolag_ut if objekt == "bolag" else person_ut)(post)

    return await _idempotent(request, tenant, arbete)


async def _krock(storage: Any, tenant: dict, objekt: str, falten: dict[str, Any], egen: str | None = None) -> HTTPException:
    """409, med id på posten som redan har numret eller adressen när den går
    att peka ut. Utan det kunde anroparen se att något krockade men inte med vad."""
    annan = None
    try:
        if objekt == "bolag" and falten.get("orgnr"):
            traffar = await lagring.hitta_poster(storage, tenant["tenant_id"], "bolag", "orgnr_nyckel",
                                                 [falt.orgnr(falten["orgnr"])[1]])
        elif objekt == "person" and falten.get("epost"):
            traffar = await lagring.hitta_poster(storage, tenant["tenant_id"], "person", "epost",
                                                 [falt.epost(falten["epost"])])
        else:
            traffar = []
        annan = next((t["id"] for t in traffar if t["id"] != egen), None)
    except falt.FaltFel:
        pass
    return fel(409, "conflict", "Another record already has this organisation number or email.",
               "En annan post har redan det här organisationsnumret eller den här adressen.",
               **({"conflicting_id": annan} if annan else {}))


async def _kraev_bolag(storage: Any, tenant: dict, bolag_id: str) -> None:
    if await lagring.hamta_post(storage, tenant["tenant_id"], "bolag", kraev_uuid(str(bolag_id), "Bolaget")) is None:
        raise fel(422, "company_not_found", "company_id does not point at a company.",
                  "company_id pekar inte på något bolag.")


async def _andra(request: Request, tenant: dict, objekt: str, rad_id: str, kropp: BaseModel) -> dict:
    await _avtal(request, tenant)
    storage = request.app.state.storage
    falten = _in(objekt, kropp.model_dump(exclude_unset=True))
    try:
        if objekt == "person" and falten.get("bolag_id"):
            await _kraev_bolag(storage, tenant, falten["bolag_id"])
        post = await synk.andra(storage, tenant["tenant_id"], objekt, kraev_uuid(rad_id, "Posten"), falten,
                                **_ursprung(request, tenant))
    except synk.OgiltigPost as orsak:
        raise _ogiltig(orsak) from None
    except lagring.FinnsRedan:
        raise await _krock(storage, tenant, objekt, falten, rad_id) from None
    if post is None:
        raise fel(404, "not_found", "The record does not exist.", "Posten finns inte.")
    return (bolag_ut if objekt == "bolag" else person_ut)(post)


async def _radera(request: Request, tenant: dict, objekt: str, rad_id: str, permanent: bool) -> Response:
    await _avtal(request, tenant)
    try:
        fanns = await synk.radera(request.app.state.storage, tenant["tenant_id"], objekt,
                                  kraev_uuid(rad_id, "Posten"), permanent=permanent, **_ursprung(request, tenant))
    except synk.BegransadBehandling:
        raise fel(409, "processing_restricted",
                  "Processing of this address is restricted (GDPR article 18). The record can be "
                  "deleted but not emptied until the restriction is lifted.",
                  "Behandlingen av adressen är begränsad (GDPR artikel 18). Posten kan raderas men "
                  "inte tömmas förrän begränsningen hävts.") from None
    if not fanns:
        raise fel(404, "not_found", "The record does not exist.", "Posten finns inte.")
    return Response(status_code=204)


async def _aterstall(request: Request, tenant: dict, objekt: str, rad_id: str) -> dict:
    await _avtal(request, tenant)
    storage = request.app.state.storage
    try:
        post = await synk.aterstall(storage, tenant["tenant_id"], objekt, kraev_uuid(rad_id, "Posten"),
                                    **_ursprung(request, tenant))
    except synk.RedanTomd:
        raise fel(410, "permanently_deleted", "The record is permanently deleted and cannot be restored.",
                  "Posten är permanent raderad och går inte att återställa.") from None
    except lagring.FinnsRedan:
        raderad = await lagring.hamta_post(storage, tenant["tenant_id"], objekt, rad_id, med_raderade=True) or {}
        raise await _krock(storage, tenant, objekt, raderad, rad_id) from None
    if post is None:
        raise fel(404, "not_found", "The record does not exist.", "Posten finns inte.")
    return (bolag_ut if objekt == "bolag" else person_ut)(post)


_PERMANENT = Query(False, description="Empty the record at once instead of keeping it restorable for 30 days.")


_LISTPARAMETRAR = dict(
    limit=Query(50, ge=1, le=500),
    cursor=Query(None, description="`next_cursor` from the previous page."),
    sort=Query("updated", pattern="^(-?updated|name)$",
               description="`updated` lists in change order, oldest first (use it when syncing out). "
               "`-updated` lists the most recently changed first. `name` is alphabetical."),
    updated_since=Query(None, description="ISO 8601 timestamp. Only records changed at or after it."),
    include_deleted=Query(False, description="Include deleted records (`deleted_at` set). Use it when syncing out."),
    q=Query(None, max_length=200, description="Free text search."),
    only_deleted=Query(False, description="The trash: only deleted records that can still be restored, "
                       "most recently deleted first. `purge_at` says when each is emptied for good."),
)


@router.get("/companies", summary="List companies")
async def lista_bolag(
    request: Request, tenant: dict = Depends(kraev("crm:las")),
    limit: int = _LISTPARAMETRAR["limit"], cursor: str | None = _LISTPARAMETRAR["cursor"],
    sort: str = _LISTPARAMETRAR["sort"], updated_since: str | None = _LISTPARAMETRAR["updated_since"],
    include_deleted: bool = _LISTPARAMETRAR["include_deleted"], q: str | None = _LISTPARAMETRAR["q"],
    only_deleted: bool = _LISTPARAMETRAR["only_deleted"],
    relation: Relation | None = None,
    org_number: str | None = Query(None, description="Exact organisationsnummer, any accepted format."),
) -> dict:
    lika: dict[str, Any] = {"relation": _RELATION_IN.get(relation) if relation else None}
    if org_number:
        try:
            lika["orgnr_nyckel"] = falt.orgnr(org_number)[1]
        except falt.FaltFel:
            return {"data": [], "next_cursor": None}
    return await _lista(request, tenant, "bolag", limit=limit, cursor=cursor, sort=sort,
                        updated_since=updated_since, include_deleted=include_deleted, q=q, lika=lika,
                        only_deleted=only_deleted)


@router.post("/companies", status_code=201, summary="Create a company, or update it by organisation number")
async def skapa_bolag(request: Request, kropp: CompanyIn, tenant: dict = Depends(kraev("crm:skriv"))) -> Response:
    """201 when created. 200 when a company with the same organisation number
    already existed and was updated instead: one company, one record."""
    return await _skapa(request, tenant, "bolag", kropp)


@router.get("/companies/{company_id}", summary="Get a company")
async def hamta_bolag(request: Request, company_id: str, include_deleted: bool = False,
                      tenant: dict = Depends(kraev("crm:las"))) -> dict:
    return await _en(request, tenant, "bolag", company_id, med_raderade=include_deleted)


@router.patch("/companies/{company_id}", summary="Change a company")
async def andra_bolag(request: Request, company_id: str, kropp: CompanyIn,
                      tenant: dict = Depends(kraev("crm:skriv"))) -> dict:
    """Only the fields sent are changed; `null` clears a field. Fields changed
    here count as edited by hand when the connection's conflict rule is applied."""
    return await _andra(request, tenant, "bolag", company_id, kropp)


@router.delete("/companies/{company_id}", status_code=204, summary="Delete a company")
async def radera_bolag(request: Request, company_id: str, permanent: bool = _PERMANENT,
                       tenant: dict = Depends(kraev("crm:skriv"))) -> Response:
    """The record can be restored for 30 days and is then emptied. What stays,
    readable with `include_deleted=true`, is its id and `deleted_at`."""
    return await _radera(request, tenant, "bolag", company_id, permanent)


@router.post("/companies/{company_id}/restore", summary="Restore a deleted company")
async def aterstall_bolag(request: Request, company_id: str, tenant: dict = Depends(kraev("crm:skriv"))) -> dict:
    return await _aterstall(request, tenant, "bolag", company_id)


@router.get("/people", summary="List people")
async def lista_personer(
    request: Request, tenant: dict = Depends(kraev("crm:las")),
    limit: int = _LISTPARAMETRAR["limit"], cursor: str | None = _LISTPARAMETRAR["cursor"],
    sort: str = _LISTPARAMETRAR["sort"], updated_since: str | None = _LISTPARAMETRAR["updated_since"],
    include_deleted: bool = _LISTPARAMETRAR["include_deleted"], q: str | None = _LISTPARAMETRAR["q"],
    only_deleted: bool = _LISTPARAMETRAR["only_deleted"],
    company_id: str | None = None,
) -> dict:
    lika = {"bolag_id": kraev_uuid(company_id, "Bolaget") if company_id else None}
    return await _lista(request, tenant, "person", limit=limit, cursor=cursor, sort=sort,
                        updated_since=updated_since, include_deleted=include_deleted, q=q, lika=lika,
                        only_deleted=only_deleted)


@router.post("/people", status_code=201, summary="Create a person, or update by email")
async def skapa_person(request: Request, kropp: PersonIn, tenant: dict = Depends(kraev("crm:skriv"))) -> Response:
    return await _skapa(request, tenant, "person", kropp)


@router.get("/people/{person_id}", summary="Get a person")
async def hamta_person(request: Request, person_id: str, include_deleted: bool = False,
                       tenant: dict = Depends(kraev("crm:las"))) -> dict:
    return await _en(request, tenant, "person", person_id, med_raderade=include_deleted)


@router.patch("/people/{person_id}", summary="Change a person")
async def andra_person(request: Request, person_id: str, kropp: PersonIn,
                       tenant: dict = Depends(kraev("crm:skriv"))) -> dict:
    return await _andra(request, tenant, "person", person_id, kropp)


@router.delete("/people/{person_id}", status_code=204, summary="Delete a person")
async def radera_person(request: Request, person_id: str, permanent: bool = _PERMANENT,
                        tenant: dict = Depends(kraev("crm:skriv"))) -> Response:
    """Use `permanent=true` when the person has asked to be erased (GDPR article 17)."""
    return await _radera(request, tenant, "person", person_id, permanent)


@router.post("/people/{person_id}/restore", summary="Restore a deleted person")
async def aterstall_person(request: Request, person_id: str, tenant: dict = Depends(kraev("crm:skriv"))) -> dict:
    return await _aterstall(request, tenant, "person", person_id)


# -- Historik och ändringsflöde ----------------------------------------------


async def _historik(request: Request, tenant: dict, objekt: str, rad_id: str, limit: int) -> dict:
    storage = request.app.state.storage
    if await lagring.hamta_post(storage, tenant["tenant_id"], objekt, kraev_uuid(rad_id, "Posten"),
                                med_raderade=True) is None:
        raise fel(404, "not_found", "The record does not exist.", "Posten finns inte.")
    rader = await handelser.for_post(storage, tenant["tenant_id"], objekt, rad_id, limit=limit)
    return {"data": [handelse_ut(r) for r in rader]}


@router.get("/companies/{company_id}/history", summary="What has happened to a company, newest first")
async def historik_bolag(request: Request, company_id: str, limit: int = Query(100, ge=1, le=500),
                         tenant: dict = Depends(kraev("crm:las"))) -> dict:
    """Each write as an event: who or what changed the record, and which
    fields. The values themselves are not kept in the log."""
    return await _historik(request, tenant, "bolag", company_id, limit)


@router.get("/people/{person_id}/history", summary="What has happened to a person, newest first")
async def historik_person(request: Request, person_id: str, limit: int = Query(100, ge=1, le=500),
                          tenant: dict = Depends(kraev("crm:las"))) -> dict:
    return await _historik(request, tenant, "person", person_id, limit)


@router.get("/changes", summary="Everything that has changed, in order")
async def andringar(
    request: Request, tenant: dict = Depends(kraev("crm:las")),
    cursor: int = Query(0, ge=0, description="`next_cursor` from your previous call. 0 reads from the beginning."),
    limit: int = Query(200, ge=1, le=1000),
    object: Literal["company", "person"] | None = Query(None, description="Only this kind of record."),
) -> dict:
    """One feed for every object. Each write has a sequence number; read until
    the list is empty and keep `next_cursor`. Asking again with the same
    cursor returns only what has happened since. An event says which record
    and which fields changed: fetch the record to get the values."""
    rader, nasta = await handelser.flode(request.app.state.storage, tenant["tenant_id"], efter=cursor, limit=limit,
                                         objekt=_OBJEKT.get(object) if object else None)
    return {"data": [handelse_ut(r) for r in rader], "next_cursor": nasta}


# -- Webhooks ----------------------------------------------------------------


class WebhookIn(_Kropp):
    url: str | None = Field(None, description="A public https address. Required when creating.")
    events: list[str] | None = Field(
        None, description="Event types to receive, e.g. `company.updated`. `*` (the default) is all of them. "
        "GET /webhooks/events lists them.")
    description: str | None = Field(None, max_length=200)
    active: bool | None = Field(None, description="Turning a disabled webhook on again resets its failure count.")


_LEVERANSSTATUS = {"vantar": "pending", "levererad": "delivered", "misslyckad": "failed"}


def webhook_ut(rad: dict[str, Any], hemlighet: str | None = None) -> dict[str, Any]:
    ut = {"id": rad["id"], "url": rad["url"], "description": rad.get("beskrivning"),
          "events": rad.get("handelser") or ["*"], "active": bool(rad["aktiv"]),
          "consecutive_failures": rad.get("fel_i_rad") or 0, "last_success_at": rad.get("senast_ok_at"),
          "last_failure_at": rad.get("senast_fel_at"), "last_error": rad.get("senast_fel"),
          "disabled_reason": rad.get("avstangd_av"),
          "created_at": rad.get("created_at"), "updated_at": rad.get("updated_at")}
    if hemlighet:
        ut["secret"] = hemlighet
    return ut


def leverans_ut(rad: dict[str, Any]) -> dict[str, Any]:
    return {"id": rad["id"], "event": rad["handelsetyp"], "status": _LEVERANSSTATUS[rad["status"]],
            "attempts": rad["forsok"], "status_code": rad.get("statuskod"), "error": rad.get("fel"),
            "next_attempt_at": rad.get("nasta_forsok_at") if rad["status"] == "vantar" else None,
            "created_at": rad.get("created_at"), "delivered_at": rad.get("levererad_at"),
            "payload": {"id": rad["id"], **(rad.get("kropp") or {})}}


def _webhookfel(orsak: webhooks.WebhookFel) -> HTTPException:
    return fel(422, orsak.kod, str(orsak), str(orsak))


async def _webhook(request: Request, tenant: dict, webhook_id: str) -> dict[str, Any]:
    rad = await webhooks.hamta(request.app.state.storage, tenant["tenant_id"], kraev_uuid(webhook_id, "Webhooken"))
    if rad is None:
        raise fel(404, "webhook_not_found", "The webhook does not exist.", "Webhooken finns inte.")
    return rad


@router.get("/webhooks/events", summary="The event types a webhook can subscribe to")
async def webhookhandelser(tenant: dict = Depends(kraev("crm:las"))) -> dict:
    return {"events": [h for h in webhooks.HANDELSETYPER if h != "ping"], "signature_header": "X-Snajp-Signature"}


@router.get("/webhooks", summary="List webhooks")
async def lista_webhooks(request: Request, tenant: dict = Depends(kraev("crm:admin"))) -> dict:
    return {"data": [webhook_ut(w) for w in await webhooks.lista(request.app.state.storage, tenant["tenant_id"])]}


@router.post("/webhooks", status_code=201, summary="Create a webhook")
async def skapa_webhook(request: Request, kropp: WebhookIn, tenant: dict = Depends(kraev("crm:admin"))) -> dict:
    """The response carries `secret`, once. Every delivery is signed with it:
    `X-Snajp-Signature: t=<unix time>,v1=<hex>` where `v1` is HMAC-SHA256 over
    `"{t}.{body}"`. Reject deliveries older than five minutes."""
    await _avtal(request, tenant)
    if not kropp.url:
        raise fel(422, "invalid_url", "url is required.", "url krävs.")
    try:
        rad, hemlighet = await webhooks.skapa(request.app.state.storage, tenant["tenant_id"], url=kropp.url,
                                              handelser=kropp.events, beskrivning=kropp.description)
    except webhooks.WebhookFel as orsak:
        raise _webhookfel(orsak) from None
    except hemligheter.IngenNyckelError:
        raise fel(503, "webhooks_unavailable", "Webhooks cannot be created right now. Contact Snajp.",
                  "Webhooks går inte att skapa just nu. Kontakta Snajp.") from None
    return webhook_ut(rad, hemlighet)


@router.get("/webhooks/{webhook_id}", summary="Get a webhook")
async def hamta_webhook(request: Request, webhook_id: str, tenant: dict = Depends(kraev("crm:admin"))) -> dict:
    return webhook_ut(await _webhook(request, tenant, webhook_id))


@router.patch("/webhooks/{webhook_id}", summary="Change a webhook")
async def andra_webhook(request: Request, webhook_id: str, kropp: WebhookIn,
                        tenant: dict = Depends(kraev("crm:admin"))) -> dict:
    await _avtal(request, tenant)
    rad = await _webhook(request, tenant, webhook_id)
    data = kropp.model_dump(exclude_unset=True)
    try:
        ny = await webhooks.andra(request.app.state.storage, tenant["tenant_id"], rad["id"], url=data.get("url"),
                                  handelser=data.get("events"), beskrivning=data.get("description"),
                                  aktiv=data.get("active"))
    except webhooks.WebhookFel as orsak:
        raise _webhookfel(orsak) from None
    return webhook_ut(ny or rad)


@router.delete("/webhooks/{webhook_id}", status_code=204, summary="Delete a webhook and its delivery log")
async def radera_webhook(request: Request, webhook_id: str, tenant: dict = Depends(kraev("crm:admin"))) -> Response:
    rad = await _webhook(request, tenant, webhook_id)
    await webhooks.ta_bort(request.app.state.storage, tenant["tenant_id"], rad["id"])
    return Response(status_code=204)


@router.post("/webhooks/{webhook_id}/test", status_code=202, summary="Send a ping to the webhook")
async def prova_webhook(request: Request, webhook_id: str, tenant: dict = Depends(kraev("crm:admin"))) -> dict:
    """Queues a `ping` delivery. Read the outcome under the webhook's deliveries."""
    rad = await _webhook(request, tenant, webhook_id)
    return leverans_ut(await webhooks.prova(request.app.state.storage, tenant["tenant_id"], rad["id"]))


@router.get("/webhooks/{webhook_id}/deliveries", summary="The delivery log, newest first")
async def lista_leveranser(request: Request, webhook_id: str, limit: int = Query(50, ge=1, le=200),
                           tenant: dict = Depends(kraev("crm:admin"))) -> dict:
    """Kept for 30 days. A failed delivery is retried seven times over about
    a day, and can then be sent again by hand."""
    rad = await _webhook(request, tenant, webhook_id)
    rader = await webhooks.leveranser(request.app.state.storage, tenant["tenant_id"], rad["id"], limit=limit)
    return {"data": [leverans_ut(r) for r in rader]}


@router.post("/webhooks/{webhook_id}/deliveries/{delivery_id}/retry", status_code=202,
             summary="Send a delivery again")
async def skicka_om_leverans(request: Request, webhook_id: str, delivery_id: str,
                             tenant: dict = Depends(kraev("crm:admin"))) -> dict:
    rad = await _webhook(request, tenant, webhook_id)
    ny = await webhooks.skicka_om(request.app.state.storage, tenant["tenant_id"], rad["id"],
                                  kraev_uuid(delivery_id, "Leveransen"))
    if ny is None:
        raise fel(404, "delivery_not_found", "The delivery does not exist.", "Leveransen finns inte.")
    return leverans_ut(ny)


# -- Anslutningar och fältmappning -------------------------------------------


@router.get("/connections/systems", summary="Supported source systems and their default mappings")
async def system(tenant: dict = Depends(kraev("crm:las"))) -> dict:
    """The default mapping per system, and the target fields a mapping can
    point at. A connection's own `mapping` is laid on top, field by field."""
    return {"systems": [{"system": s, "mapping": adaptrar.STANDARD[s]} for s in adaptrar.SYSTEM],
            "target_fields": {"company": [*adaptrar.BOLAGSFALT, "externt_id", "uppdaterad", "raderad", "hoppa_over", "extra"],
                              "person": [*adaptrar.PERSONFALT, "externt_id", "uppdaterad", "raderad", "hoppa_over", "extra"]}}


@router.get("/connections", summary="List connections")
async def lista_anslutningar(request: Request, tenant: dict = Depends(kraev("crm:las"))) -> dict:
    return {"data": [anslutning_ut(a) for a in
                     await lagring.lista_anslutningar(request.app.state.storage, tenant["tenant_id"])]}


def _anslutningsfalt(kropp: ConnectionIn) -> dict[str, Any]:
    data = kropp.model_dump(exclude_unset=True)
    ut: dict[str, Any] = {}
    if "name" in data:
        namn = (data["name"] or "").strip()
        if not 1 <= len(namn) <= 80:
            raise fel(422, "invalid_fields", "name must be 1 to 80 characters.", "name ska vara 1 till 80 tecken.")
        ut["namn"] = namn
    if data.get("system"):
        ut["system"] = data["system"]
    if "mapping" in data:
        try:
            ut["mappning"] = adaptrar.validera_mappning(data["mapping"])
        except adaptrar.MappningsFel as orsak:
            raise fel(422, "invalid_mapping", str(orsak), str(orsak)) from None
    if data.get("conflict_rule"):
        ut["konfliktregel"] = _KONFLIKT[data["conflict_rule"]]
    if data.get("missing_records"):
        ut["saknade"] = _SAKNADE[data["missing_records"]]
    if data.get("default_relation"):
        ut["standardrelation"] = _RELATION_IN[data["default_relation"]]
    if data.get("include_private_persons") is not None:
        ut["privatpersoner"] = data["include_private_persons"]
    if data.get("active") is not None:
        ut["aktiv"] = data["active"]
    return ut


@router.post("/connections", status_code=201, summary="Create a connection")
async def skapa_anslutning(request: Request, kropp: ConnectionIn, tenant: dict = Depends(kraev("crm:admin"))) -> dict:
    falten = _anslutningsfalt(kropp)
    if not falten.get("namn"):
        raise fel(422, "invalid_fields", "name is required.", "name krävs.")
    try:
        rad = await lagring.skapa_anslutning(request.app.state.storage, tenant["tenant_id"], **falten)
    except lagring.FinnsRedan:
        raise fel(409, "conflict", "A connection with this name already exists.",
                  "Det finns redan en anslutning med det namnet.") from None
    return anslutning_ut(rad)


async def _anslutning(request: Request, tenant: dict, ref: str) -> dict[str, Any]:
    rad = await lagring.hamta_anslutning(request.app.state.storage, tenant["tenant_id"], ref)
    if rad is None:
        raise fel(404, "connection_not_found", "The connection does not exist.", "Anslutningen finns inte.")
    return rad


@router.get("/connections/{connection}", summary="Get a connection")
async def hamta_anslutning(request: Request, connection: str, tenant: dict = Depends(kraev("crm:las"))) -> dict:
    rad = await _anslutning(request, tenant, connection)
    return {**anslutning_ut(rad),
            "effective_mapping": adaptrar.gallande_mappning(rad["system"], rad.get("mappning"))}


@router.patch("/connections/{connection}", summary="Change a connection or its mapping")
async def andra_anslutning(request: Request, connection: str, kropp: ConnectionIn,
                           tenant: dict = Depends(kraev("crm:admin"))) -> dict:
    rad = await _anslutning(request, tenant, connection)
    try:
        ny = await lagring.uppdatera_anslutning(request.app.state.storage, tenant["tenant_id"], rad["id"],
                                                **_anslutningsfalt(kropp))
    except lagring.FinnsRedan:
        raise fel(409, "conflict", "A connection with this name already exists.",
                  "Det finns redan en anslutning med det namnet.") from None
    return anslutning_ut(ny)


@router.delete("/connections/{connection}", status_code=204, summary="Delete a connection")
async def radera_anslutning(request: Request, connection: str, tenant: dict = Depends(kraev("crm:admin"))) -> Response:
    """The companies and people stay. The source system's ids for them are forgotten."""
    rad = await _anslutning(request, tenant, connection)
    await lagring.ta_bort_anslutning(request.app.state.storage, tenant["tenant_id"], rad["id"])
    return Response(status_code=204)


@router.post("/connections/{connection}/preview", summary="Try a mapping without writing anything")
async def forhandsgranska(request: Request, connection: str, kropp: Preview,
                          tenant: dict = Depends(kraev("crm:las"))) -> dict:
    """Shows what a batch WOULD do: which records are created, updated or
    skipped, and which fields could not be interpreted. Nothing is stored."""
    rad = await _anslutning(request, tenant, connection)
    if len(kropp.items) > 50:
        raise fel(422, "too_many_items", "Preview takes at most 50 items.", "Förhandsgranskningen tar högst 50 poster.")
    try:
        egen = adaptrar.validera_mappning(kropp.mapping) if kropp.mapping is not None else rad.get("mappning")
    except adaptrar.MappningsFel as orsak:
        raise fel(422, "invalid_mapping", str(orsak), str(orsak)) from None
    regler = adaptrar.gallande_mappning(rad["system"], egen)
    objekt = _OBJEKT[kropp.object]
    svar = await synk.synka_sats(request.app.state.storage, tenant["tenant_id"], rad, {"id": None}, objekt,
                                 kropp.items, mappning=regler, torrkorning=True)
    tolkade = [adaptrar.mappa(p, objekt, regler) for p in kropp.items]
    ut = _sats_ut(svar, None)
    for post, m in zip(ut["items"], tolkade):
        post["interpreted"] = {**m.falt, **({"extra": m.extra} if m.extra else {})}
    return ut


# -- Synken ------------------------------------------------------------------


async def _las_sats(request: Request) -> tuple[str | None, list[Any]]:
    """(anslutning, poster) ur kroppen: JSON `{"items": [...]}` eller en lista,
    eller text/csv med rubrikrad."""
    ra = await request.body()
    if len(ra) > MAX_KROPP:
        raise fel(413, "body_too_large", "The body is larger than 8 MB. Send smaller batches.",
                  "Kroppen är större än 8 MB. Skicka mindre satser.")
    typ = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    anslutning = request.query_params.get("connection")
    if typ in ("text/csv", "text/plain", "application/csv"):
        try:
            poster: list[Any] = adaptrar.tolka_csv(ra.decode("utf-8-sig"), max_rader=MAX_SATS)
        except UnicodeDecodeError:
            raise fel(422, "invalid_encoding", "CSV must be UTF-8.", "CSV-filen ska vara UTF-8.") from None
        except adaptrar.MappningsFel as orsak:
            raise fel(422, "too_many_items", str(orsak), str(orsak)) from None
    else:
        try:
            data = json.loads(ra or b"null")
        except ValueError:
            raise fel(422, "invalid_json", "The body is not valid JSON.", "Kroppen är inte giltig JSON.") from None
        if isinstance(data, dict):
            anslutning = data.get("connection") or anslutning
            data = data.get("items")
        if not isinstance(data, list):
            raise fel(422, "invalid_body", 'Send {"items": [...]} or a JSON array.',
                      'Skicka {"items": [...]} eller en JSON-lista.')
        poster = data
    if not poster:
        raise fel(422, "empty_batch", "The batch has no items.", "Satsen är tom.")
    if len(poster) > MAX_SATS:
        raise fel(422, "too_many_items", f"A batch takes at most {MAX_SATS} items.",
                  f"En sats tar högst {MAX_SATS} poster.")
    return anslutning, poster


_SATSKROPP = {
    "requestBody": {"required": True, "content": {
        "application/json": {"schema": Batch.model_json_schema()},
        "text/csv": {"schema": {"type": "string", "description":
                                "UTF-8 with a header row. Semicolon, comma or tab separated. "
                                "Pass the connection as the query parameter `connection`."}},
    }},
}


@router.post("/sync/runs", status_code=201, summary="Start a sync run")
async def starta_korning(request: Request, kropp: RunIn, tenant: dict = Depends(kraev("crm:synk"))) -> Response:
    """Start a run, send batches to it and complete it. Use `mode: full` when
    the batches together are everything the source has: only then can records
    that have disappeared from the source be handled."""
    await _avtal(request, tenant)
    anslutning = await _anslutning(request, tenant, kropp.connection)

    async def arbete():
        rad = await lagring.skapa_korning(request.app.state.storage, tenant["tenant_id"],
                                          anslutning_id=anslutning["id"], lage=kropp.mode, startad_av="api")
        return 201, korning_ut(rad)

    return await _idempotent(request, tenant, arbete)


@router.get("/sync/runs", summary="List sync runs, newest first")
async def lista_korningar(request: Request, limit: int = Query(50, ge=1, le=200),
                          tenant: dict = Depends(kraev("crm:las"))) -> dict:
    return {"data": [korning_ut(k) for k in
                     await lagring.lista_korningar(request.app.state.storage, tenant["tenant_id"], limit=limit)]}


async def _korning(request: Request, tenant: dict, run_id: str) -> dict[str, Any]:
    rad = await lagring.hamta_korning(request.app.state.storage, tenant["tenant_id"], kraev_uuid(run_id, "Körningen"))
    if rad is None:
        raise fel(404, "run_not_found", "The sync run does not exist.", "Synkkörningen finns inte.")
    return rad


@router.get("/sync/runs/{run_id}", summary="Get a sync run with counts and errors")
async def hamta_korning(request: Request, run_id: str, tenant: dict = Depends(kraev("crm:las"))) -> dict:
    return korning_ut(await _korning(request, tenant, run_id))


async def _sats_i_korning(request: Request, tenant: dict, run_id: str, objekt: str) -> Response:
    await _avtal(request, tenant)
    storage = request.app.state.storage
    korning = await _korning(request, tenant, run_id)
    if korning["status"] != "processing":
        raise fel(409, "run_closed", "The run is already completed.", "Körningen är redan avslutad.")
    if not korning.get("anslutning_id"):
        raise fel(409, "connection_not_found", "The run's connection has been deleted.",
                  "Körningens anslutning är borttagen.")
    anslutning = await _anslutning(request, tenant, korning["anslutning_id"])
    _, poster = await _las_sats(request)

    async def arbete():
        svar = await synk.synka_sats(storage, tenant["tenant_id"], anslutning, korning, objekt, poster)
        return 200, _sats_ut(svar, await lagring.hamta_korning(storage, tenant["tenant_id"], korning["id"]))

    return await _idempotent(request, tenant, arbete)


@router.post("/sync/runs/{run_id}/companies", summary="Send a batch of companies to a run", openapi_extra=_SATSKROPP)
async def sats_bolag(request: Request, run_id: str, tenant: dict = Depends(kraev("crm:synk"))) -> Response:
    return await _sats_i_korning(request, tenant, run_id, "bolag")


@router.post("/sync/runs/{run_id}/people", summary="Send a batch of people to a run", openapi_extra=_SATSKROPP)
async def sats_personer(request: Request, run_id: str, tenant: dict = Depends(kraev("crm:synk"))) -> Response:
    """Send the companies first: a person is linked to its company through the
    company's id in the source system."""
    return await _sats_i_korning(request, tenant, run_id, "person")


@router.post("/sync/runs/{run_id}/complete", summary="Complete a run")
async def slutfor_korning(request: Request, run_id: str, tenant: dict = Depends(kraev("crm:synk"))) -> dict:
    """Closes the run. A full run then applies the connection's
    `missing_records` rule to what the source no longer has. A full run
    without a single item fails instead of emptying the register."""
    await _avtal(request, tenant)
    storage = request.app.state.storage
    korning = await _korning(request, tenant, run_id)
    if korning["status"] != "processing":
        return korning_ut(korning)
    if not korning.get("anslutning_id"):
        klar = await lagring.avsluta_korning(storage, tenant["tenant_id"], korning["id"], status="completed")
        return korning_ut(await supportrapport.lamna(storage, tenant["tenant_id"], None, klar))
    anslutning = await _anslutning(request, tenant, korning["anslutning_id"])
    return korning_ut(await synk.slutfor(storage, tenant["tenant_id"], anslutning, korning))


async def _enstaka_sats(request: Request, tenant: dict, objekt: str) -> Response:
    await _avtal(request, tenant)
    storage = request.app.state.storage
    ref, poster = await _las_sats(request)
    if not ref:
        raise fel(422, "connection_required", "connection is required.", "connection krävs.")
    anslutning = await _anslutning(request, tenant, ref)

    async def arbete():
        korning = await lagring.skapa_korning(storage, tenant["tenant_id"], anslutning_id=anslutning["id"],
                                              lage="delta", startad_av="api")
        svar = await synk.synka_sats(storage, tenant["tenant_id"], anslutning, korning, objekt, poster)
        return 200, _sats_ut(svar, await synk.slutfor(storage, tenant["tenant_id"], anslutning, korning))

    return await _idempotent(request, tenant, arbete)


@router.post("/sync/companies", summary="Sync a batch of companies in one call", openapi_extra=_SATSKROPP)
async def synka_bolag(request: Request, tenant: dict = Depends(kraev("crm:synk"))) -> Response:
    """The short way in: one batch, in the source system's own format, is one
    completed run. Records are matched on the source's id, then on organisation
    number, so sending the same batch again changes nothing."""
    return await _enstaka_sats(request, tenant, "bolag")


@router.post("/sync/people", summary="Sync a batch of people in one call", openapi_extra=_SATSKROPP)
async def synka_personer(request: Request, tenant: dict = Depends(kraev("crm:synk"))) -> Response:
    return await _enstaka_sats(request, tenant, "person")


# -- Specifikationen ---------------------------------------------------------

_BESKRIVNING = """\
Read and write the companies and people a Snajp customer keeps in Snajp CRM, and sync a customer
register in from another system.

**Authentication.** Send the key in `X-API-Key`. Keys are created under CRM, Developers, and carry
scopes: `crm:las` (read), `crm:skriv` (write), `crm:synk` (sync), `crm:admin` (connections).

**Idempotency.** Any POST accepts `Idempotency-Key`. Within 24 hours the same key and body return
the stored response, with `Idempotent-Replayed: true`.

**Pagination.** Lists return `next_cursor`. Pass it as `cursor` until it is `null`.

**Rate limit.** 600 requests per minute and customer. `X-RateLimit-Remaining` is on every
response; a 429 carries `Retry-After`.

**Errors.** `{"detail": {"code", "message", "meddelande"}}`. `code` is stable, `message` is English,
`meddelande` is Swedish.

**Swedish formats.** Organisation numbers are checked with the Luhn digit and stored as
`NNNNNN-NNNN`. Phone numbers are stored as E.164, Swedish postal codes as `NNN NN`, dates as ISO 8601.

**Keeping a copy in sync.** Read `GET /changes` from your last `next_cursor`: one feed for every
object, in order. Or have Snajp call you: register a webhook under `/webhooks`. Listing with
`sort=updated&include_deleted=true&updated_since=<your last sync>` works as before. Deleted
records carry `deleted_at` and must be removed on your side as well.

**Webhooks.** Each delivery is a POST with `X-Snajp-Signature: t=<unix time>,v1=<hex>`, where `v1`
is HMAC-SHA256 over `"{t}.{body}"` with the webhook's secret. Answer 2xx within ten seconds.
Anything else is retried seven times over about a day.
"""


def specifikation() -> dict[str, Any]:
    spec = get_openapi(title="Snajp CRM API", version=VERSION, description=_BESKRIVNING, routes=router.routes)
    spec["components"].setdefault("securitySchemes", {})["ApiKey"] = {"type": "apiKey", "in": "header", "name": "X-API-Key"}
    spec["security"] = [{"ApiKey": []}]
    return spec


@router.get("/openapi.json", summary="This specification", include_in_schema=False)
async def openapi(tenant: dict = Depends(kraev("crm:las"))) -> dict:
    return specifikation()
