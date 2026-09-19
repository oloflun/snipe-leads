"""/api/integrationer — kundens HTTP-verktyg och MCP-servrar (bd snipe-36u).

Tenant-skopat som resten av kundens inställningar (/api/rules och liknande):
nyckeln avgör tenant. Hemligheter kan skrivas men lämnas aldrig ut. Svaret
visar vilka som finns (`hemligheter: {"token": "[hemlighet]"}`), aldrig
värdet.

Provkörningen (`POST /{id}/prova`) gör ett RIKTIGT anrop, eftersom det är
hela poängen: administratören ska se vad agenten kommer att få. Ett skrivande
anrop kräver ändå `tillat_skrivning: true` i anropet, så att "prova" i
portalen aldrig avbokar en order av misstag.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..cache import versioner
from ..integrationer import lagring, mcp_klient
from ..integrationer.hemligheter import IngenNyckelError, OlasbarHemlighetError, tvatta_djupt
from ..integrationer.katalog import mcp_verktyget_skriver, mcp_verktyget_tillats
from ..integrationer.http_verktyg import kor as kor_http
from ..integrationer.modell import (
    HANDELSER,
    KONTEXTNAMN,
    HttpKonfig,
    KonfigFel,
    McpKonfig,
    las_konfig,
    saknade_hemligheter,
)
from .deps import kraev_uuid, require_tenant

router = APIRouter(prefix="/api/integrationer", tags=["integrationer"])

_HEMLIGHETSNAMN = r"^[A-Za-z_][A-Za-z0-9_]{0,39}$"


class NyIntegration(BaseModel):
    typ: Literal["http", "mcp"]
    namn: str = Field(min_length=1, max_length=80)
    beskrivning: str = Field(default="", max_length=500)
    konfig: dict[str, Any]
    hemligheter: dict[str, str] = Field(default_factory=dict)
    aktiv: bool = True


class AndraIntegration(BaseModel):
    namn: str | None = Field(default=None, min_length=1, max_length=80)
    beskrivning: str | None = Field(default=None, max_length=500)
    konfig: dict[str, Any] | None = None
    #: Bara de nycklar som ska ändras. null eller "" tar bort nyckeln.
    hemligheter: dict[str, str | None] | None = None
    aktiv: bool | None = None


class Provkorning(BaseModel):
    #: HTTP: förfrågans `name` eller verktygsnamn (request_...). MCP: verktyget
    #: på servern. Utelämnat för MCP = bara lista verktygen.
    verktyg: str | None = None
    argument: dict[str, Any] = Field(default_factory=dict)
    #: Exempelvärden för kontextplatshållarna ({"kund.email": "..."}), så att
    #: en uppslagning bunden till {{kund.email}} går att prova.
    kontext: dict[str, Any] = Field(default_factory=dict)
    tillat_skrivning: bool = False


def _kontrollera_hemlighetsnamn(hemligheter: dict[str, Any]) -> None:
    import re

    for namn in hemligheter:
        if not re.fullmatch(_HEMLIGHETSNAMN, namn):
            raise HTTPException(
                status_code=422,
                detail=f"Hemlighetsnamnet {namn!r} får bara innehålla bokstäver, siffror och _.",
            )


def _validera(typ: str, konfig: dict[str, Any], hemlighetsnamn: set[str]) -> HttpKonfig | McpKonfig:
    try:
        tolkad = las_konfig(typ, konfig)
    except KonfigFel as fel:
        raise HTTPException(status_code=422, detail=str(fel)) from fel
    saknas = saknade_hemligheter(typ, tolkad, hemlighetsnamn)
    if saknas:
        raise HTTPException(
            status_code=422,
            detail=(
                "Konfigurationen använder hemligheter som inte är sparade: "
                + ", ".join(f"{{{{hemlighet.{n}}}}}" for n in saknas)
                + ". Lägg till dem under hemligheter."
            ),
        )
    return tolkad


def _nyckelfel(fel: Exception) -> HTTPException:
    if isinstance(fel, IngenNyckelError):
        return HTTPException(status_code=503, detail=str(fel))
    return HTTPException(status_code=409, detail=str(fel))


async def _nya_svar_galler(tenant_id: str) -> None:
    """Svarscachen (INV-CACHE-001) nycklas på kundens konfigversion. Ett svar
    som cachades innan kunden kopplade in sitt ordersystem ("kolla mejlet
    för spårningslänken") ska inte fortsätta serveras när agenten nu kan slå
    upp ordern själv — så varje ändring här gör de cachade svaren ogiltiga."""
    await versioner.bumpa_config(tenant_id)


async def _hamta_eller_404(request: Request, tenant_id: str, integration_id: str) -> dict[str, Any]:
    kraev_uuid(integration_id, "Integrationen")
    rad = await lagring.hamta(request.app.state.storage, tenant_id, integration_id)
    if rad is None:
        raise HTTPException(status_code=404, detail="Integrationen finns inte.")
    return rad


@router.get("")
async def lista_integrationer(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    rader = await lagring.lista(request.app.state.storage, tenant["tenant_id"])
    return {
        "integrationer": [lagring.offentlig(r) for r in rader],
        # Hjälptext åt portalen: vad som går att skriva i en platshållare.
        "kontextvarden": list(KONTEXTNAMN),
        "handelser": {namn: list(varden) for namn, varden in HANDELSER.items()},
    }


@router.post("", status_code=201)
async def skapa_integration(
    request: Request, payload: NyIntegration, tenant: dict = Depends(require_tenant)
) -> dict:
    _kontrollera_hemlighetsnamn(payload.hemligheter)
    hemligheter = {k: v for k, v in payload.hemligheter.items() if v}
    tolkad = _validera(payload.typ, payload.konfig, set(hemligheter))
    try:
        rad = await lagring.skapa(
            request.app.state.storage,
            tenant["tenant_id"],
            typ=payload.typ,
            namn=payload.namn.strip(),
            beskrivning=payload.beskrivning.strip(),
            konfig=tolkad.model_dump(mode="json", exclude_none=True),
            hemligheter=hemligheter,
            aktiv=payload.aktiv,
        )
    except (IngenNyckelError, lagring.IntegrationFinnsRedan) as fel:
        raise _nyckelfel(fel) from fel
    await _nya_svar_galler(tenant["tenant_id"])
    return lagring.offentlig(rad)


@router.patch("/{integration_id}")
async def andra_integration(
    request: Request,
    integration_id: str,
    payload: AndraIntegration,
    tenant: dict = Depends(require_tenant),
) -> dict:
    storage = request.app.state.storage
    befintlig = await _hamta_eller_404(request, tenant["tenant_id"], integration_id)

    nya_hemligheter: dict[str, str] | None = None
    if payload.hemligheter is not None:
        _kontrollera_hemlighetsnamn(payload.hemligheter)
        try:
            gamla = lagring.dekryptera_hemligheter(befintlig)
        except (IngenNyckelError, OlasbarHemlighetError) as fel:
            # Oläsbara nycklar (bytt INTEGRATION_NYCKEL) slås inte ihop med
            # nya: att tyst tappa de gamla vore värre än ett fel. Ta bort
            # integrationen och skapa den på nytt i stället.
            raise HTTPException(status_code=409, detail=str(fel)) from fel
        nya_hemligheter = lagring.sla_ihop_hemligheter(gamla, payload.hemligheter)

    konfig = payload.konfig if payload.konfig is not None else befintlig["konfig"]
    hemlighetsnamn = (
        set(nya_hemligheter) if nya_hemligheter is not None else set(befintlig.get("hemlighetsnamn") or [])
    )
    tolkad = _validera(befintlig["typ"], konfig, hemlighetsnamn)
    try:
        rad = await lagring.uppdatera(
            storage,
            tenant["tenant_id"],
            integration_id,
            namn=payload.namn.strip() if payload.namn is not None else None,
            beskrivning=payload.beskrivning.strip() if payload.beskrivning is not None else None,
            konfig=tolkad.model_dump(mode="json", exclude_none=True) if payload.konfig is not None else None,
            aktiv=payload.aktiv,
            hemligheter=nya_hemligheter,
        )
    except (IngenNyckelError, lagring.IntegrationFinnsRedan) as fel:
        raise _nyckelfel(fel) from fel
    if rad is None:
        raise HTTPException(status_code=404, detail="Integrationen finns inte.")
    await _nya_svar_galler(tenant["tenant_id"])
    return lagring.offentlig(rad)


@router.delete("/{integration_id}")
async def ta_bort_integration(
    request: Request, integration_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    kraev_uuid(integration_id, "Integrationen")
    borta = await lagring.ta_bort(request.app.state.storage, tenant["tenant_id"], integration_id)
    if not borta:
        raise HTTPException(status_code=404, detail="Integrationen finns inte.")
    await _nya_svar_galler(tenant["tenant_id"])
    return {"borttagen": True}


@router.get("/{integration_id}/verktyg")
async def lista_verktyg(
    request: Request, integration_id: str, tenant: dict = Depends(require_tenant)
) -> dict:
    """Vad agenten ser av integrationen: verktygsnamn, beskrivning, argument."""
    rad = await _hamta_eller_404(request, tenant["tenant_id"], integration_id)
    try:
        konfig = las_konfig(rad["typ"], rad["konfig"])
        hemligheter = lagring.dekryptera_hemligheter(rad)
    except (KonfigFel, IngenNyckelError, OlasbarHemlighetError) as fel:
        raise HTTPException(status_code=409, detail=str(fel)) from fel

    if isinstance(konfig, HttpKonfig):
        bundna = set(konfig.handelser.values())
        return {
            "verktyg": [
                {
                    "namn": r.verktygsnamn,
                    "forfragan": r.name,
                    "beskrivning": r.description or r.name,
                    "argument": r.json_schema(set(hemligheter)),
                    "skrivande": r.ar_skrivande,
                    "handelse": next((h for h, n in konfig.handelser.items() if n == r.name), None),
                    "synligt_for_agenten": r.name not in bundna,
                }
                for r in konfig.requests
            ]
        }
    try:
        serverns = await mcp_klient.lista_verktyg(konfig, hemligheter)
    except mcp_klient.McpFel as fel:
        raise HTTPException(status_code=502, detail=str(fel)) from fel
    return {
        "verktyg": [
            {
                "namn": v.namn,
                "beskrivning": v.beskrivning,
                "argument": v.schema,
                "skrivande": mcp_verktyget_skriver(konfig, v),
                "synligt_for_agenten": mcp_verktyget_tillats(konfig, v),
            }
            for v in serverns
        ]
    }


@router.post("/{integration_id}/prova")
async def prova_integration(
    request: Request,
    integration_id: str,
    payload: Provkorning,
    tenant: dict = Depends(require_tenant),
) -> dict:
    rad = await _hamta_eller_404(request, tenant["tenant_id"], integration_id)
    try:
        konfig = las_konfig(rad["typ"], rad["konfig"])
        hemligheter = lagring.dekryptera_hemligheter(rad)
    except (KonfigFel, IngenNyckelError, OlasbarHemlighetError) as fel:
        raise HTTPException(status_code=409, detail=str(fel)) from fel

    kontext = {k: v for k, v in payload.kontext.items() if isinstance(k, str)}
    kontext.setdefault("tenant.namn", tenant.get("tenant_name"))

    if isinstance(konfig, HttpKonfig):
        onskat = (payload.verktyg or "").strip()
        forfragan = next(
            (r for r in konfig.requests if onskat in (r.name, r.verktygsnamn)), None
        )
        if forfragan is None:
            raise HTTPException(status_code=404, detail=f"Förfrågan {onskat!r} finns inte i integrationen.")
        if forfragan.ar_skrivande and not payload.tillat_skrivning:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Förfrågan ändrar data i ert system. Skicka tillat_skrivning: true "
                    "om provet verkligen ska genomföras."
                ),
            )
        # Händelsebundna förfrågningar provas med exempelvärden för handelse.*.
        for handelse, namn in konfig.handelser.items():
            if namn == forfragan.name:
                for falt in HANDELSER[handelse]:
                    kontext.setdefault(falt, f"(exempel: {falt})")
        resultat = await kor_http(
            forfragan, argument=payload.argument, hemligheter=hemligheter, kontext=kontext
        )
        return {"resultat": tvatta_djupt(resultat.for_modellen(), hemligheter), "logg": resultat.for_logg()}

    if not payload.verktyg:
        try:
            serverns = await mcp_klient.lista_verktyg(konfig, hemligheter)
        except mcp_klient.McpFel as fel:
            raise HTTPException(status_code=502, detail=str(fel)) from fel
        return {"ansluten": True, "verktyg": [v.namn for v in serverns]}

    try:
        serverns = await mcp_klient.lista_verktyg(konfig, hemligheter)
    except mcp_klient.McpFel as fel:
        raise HTTPException(status_code=502, detail=str(fel)) from fel
    mv = next((v for v in serverns if v.namn == payload.verktyg), None)
    if mv is None:
        raise HTTPException(status_code=404, detail=f"Servern har inget verktyg som heter {payload.verktyg!r}.")
    skrivande = mcp_verktyget_skriver(konfig, mv)
    if skrivande and not payload.tillat_skrivning:
        raise HTTPException(
            status_code=409,
            detail="Verktyget ändrar data. Skicka tillat_skrivning: true om provet ska genomföras.",
        )
    resultat = await mcp_klient.anropa_verktyg(
        konfig,
        hemligheter,
        verktygsnamn=mv.namn,
        serverns_namn=mv.namn,
        argument=payload.argument,
        skrivande=skrivande,
    )
    return {"resultat": resultat.for_modellen(), "logg": resultat.for_logg()}
