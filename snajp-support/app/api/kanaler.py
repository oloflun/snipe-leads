"""/api/kanaler — kanalanslutningar och deras webhooks (bd snipe-36u).

Två sorters ändpunkter, med olika autentisering:

  Admin (X-API-Key, tenant-skopat):
    GET    /api/kanaler                 anslutningarna + webhookadresser
    POST   /api/kanaler                 ny anslutning
    PATCH  /api/kanaler/{id}            ändra (hemligheter slås ihop)
    DELETE /api/kanaler/{id}            ta bort
    POST   /api/kanaler/{id}/prova      fungerar nycklarna mot kanalens API?

  Webhook (ingen nyckel — kanalens SIGNATUR är autentiseringen):
    GET    /api/kanaler/{kanal}/{tenant_id}/{anslutning_id}/webhook
    POST   /api/kanaler/{kanal}/{tenant_id}/{anslutning_id}/webhook

Webhookadressen bär tenant och anslutning, så att uppslaget sker under RLS
utan en tenantlös sökväg genom databasen. Ett okänt id och en felaktig
signatur ger samma korta svar (404/401), utan att berätta vilket som var fel
för någon som provar sig fram.
"""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field

from ..config import get_settings
from ..integrationer.hemligheter import IngenNyckelError, OlasbarHemlighetError
from ..integrationer.lagring import sla_ihop_hemligheter
from ..kanaler import ADAPTRAR, KANALER, KanalFel, lagring
from ..kanaler.mottagning import starta_i_bakgrunden, ta_emot
from .deps import kraev_uuid, require_tenant

router = APIRouter(prefix="/api/kanaler", tags=["kanaler"])

_HEMLIGHETSNAMN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,39}$")
#: En webhook från Meta eller Slack är några kB. Något mycket större är inte
#: en webhook, och ska inte läsas in för att sedan avvisas av signaturen.
MAX_WEBHOOK_BYTES = 512_000


class NyAnslutning(BaseModel):
    kanal: str
    namn: str = Field(default="", max_length=80)
    extern_id: str = Field(min_length=1, max_length=200)
    konfig: dict[str, Any] = Field(default_factory=dict)
    hemligheter: dict[str, str] = Field(default_factory=dict)
    aktiv: bool = True


class AndraAnslutning(BaseModel):
    namn: str | None = Field(default=None, max_length=80)
    konfig: dict[str, Any] | None = None
    hemligheter: dict[str, str | None] | None = None
    aktiv: bool | None = None


def _bas_url() -> str:
    settings = get_settings()
    if settings.api_publik_url.strip():
        return settings.api_publik_url.strip().rstrip("/")
    if settings.railway_public_domain.strip():
        return f"https://{settings.railway_public_domain.strip()}"
    return ""


def webhook_url(tenant_id: str, rad: dict[str, Any]) -> str | None:
    bas = _bas_url()
    if not bas:
        return None
    return f"{bas}/api/kanaler/{rad['kanal']}/{tenant_id}/{rad['id']}/webhook"


def _med_webhook(tenant_id: str, rad: dict[str, Any]) -> dict[str, Any]:
    ut = lagring.offentlig(rad)
    ut["webhook_url"] = webhook_url(tenant_id, rad)
    adapter = ADAPTRAR[rad["kanal"]]
    ut["saknade_hemligheter"] = [h for h in adapter.hemligheter_kravs if h not in (rad.get("hemlighetsnamn") or [])]
    return ut


def _kontrollera_konfig(kanal: str, konfig: dict[str, Any]) -> dict[str, Any]:
    """Konfigen är liten och kanalspecifik: graph_version (Meta),
    app_tenant_id (Teams). Okända nycklar avvisas hellre än sparas tyst."""
    tillatna = {"whatsapp": {"graph_version"}, "messenger": {"graph_version"}, "slack": set(), "teams": {"app_tenant_id"}}
    okanda = set(konfig) - tillatna[kanal]
    if okanda:
        raise HTTPException(status_code=422, detail=f"Okända inställningar för {kanal}: {', '.join(sorted(okanda))}.")
    for nyckel, varde in konfig.items():
        if not isinstance(varde, str) or len(varde) > 100 or not re.fullmatch(r"[A-Za-z0-9._-]*", varde):
            raise HTTPException(status_code=422, detail=f"{nyckel} har ett ogiltigt värde.")
    return konfig


def _kontrollera_hemligheter(hemligheter: dict[str, Any]) -> None:
    for namn in hemligheter:
        if not _HEMLIGHETSNAMN.fullmatch(namn):
            raise HTTPException(status_code=422, detail=f"Hemlighetsnamnet {namn!r} är ogiltigt.")


# -- Admin --------------------------------------------------------------------


@router.get("")
async def lista_anslutningar(request: Request, tenant: dict = Depends(require_tenant)) -> dict:
    rader = await lagring.lista_anslutningar(request.app.state.storage, tenant["tenant_id"])
    return {
        "anslutningar": [_med_webhook(tenant["tenant_id"], r) for r in rader],
        "kanaler": {
            namn: {"hemligheter": list(a.hemligheter_kravs), "extern_id": a.extern_id_betyder}
            for namn, a in ADAPTRAR.items()
        },
        "webhook_bas": _bas_url() or None,
    }


@router.post("", status_code=201)
async def skapa_anslutning(request: Request, payload: NyAnslutning, tenant: dict = Depends(require_tenant)) -> dict:
    if payload.kanal not in ADAPTRAR:
        raise HTTPException(status_code=422, detail=f"Okänd kanal. Tillåtna: {', '.join(KANALER)}.")
    _kontrollera_hemligheter(payload.hemligheter)
    konfig = _kontrollera_konfig(payload.kanal, payload.konfig)
    try:
        rad = await lagring.skapa_anslutning(
            request.app.state.storage,
            tenant["tenant_id"],
            kanal=payload.kanal,
            namn=payload.namn.strip(),
            extern_id=payload.extern_id.strip(),
            konfig=konfig,
            hemligheter={k: v for k, v in payload.hemligheter.items() if v},
            aktiv=payload.aktiv,
        )
    except IngenNyckelError as fel:
        raise HTTPException(status_code=503, detail=str(fel)) from fel
    except lagring.AnslutningFinnsRedan as fel:
        raise HTTPException(status_code=409, detail=str(fel)) from fel
    return _med_webhook(tenant["tenant_id"], rad)


async def _anslutning_eller_404(request: Request, tenant_id: str, anslutning_id: str) -> dict[str, Any]:
    kraev_uuid(anslutning_id, "Anslutningen")
    rad = await lagring.hamta_anslutning(request.app.state.storage, tenant_id, anslutning_id)
    if rad is None:
        raise HTTPException(status_code=404, detail="Anslutningen finns inte.")
    return rad


@router.patch("/{anslutning_id}")
async def andra_anslutning(
    request: Request, anslutning_id: str, payload: AndraAnslutning, tenant: dict = Depends(require_tenant)
) -> dict:
    befintlig = await _anslutning_eller_404(request, tenant["tenant_id"], anslutning_id)
    nya: dict[str, str] | None = None
    if payload.hemligheter is not None:
        _kontrollera_hemligheter(payload.hemligheter)
        try:
            gamla = lagring.dekryptera_hemligheter(befintlig)
        except (IngenNyckelError, OlasbarHemlighetError) as fel:
            raise HTTPException(status_code=409, detail=str(fel)) from fel
        nya = sla_ihop_hemligheter(gamla, payload.hemligheter)
    try:
        rad = await lagring.uppdatera_anslutning(
            request.app.state.storage,
            tenant["tenant_id"],
            anslutning_id,
            namn=payload.namn.strip() if payload.namn is not None else None,
            konfig=_kontrollera_konfig(befintlig["kanal"], payload.konfig) if payload.konfig is not None else None,
            aktiv=payload.aktiv,
            hemligheter=nya,
        )
    except IngenNyckelError as fel:
        raise HTTPException(status_code=503, detail=str(fel)) from fel
    if rad is None:
        raise HTTPException(status_code=404, detail="Anslutningen finns inte.")
    return _med_webhook(tenant["tenant_id"], rad)


@router.delete("/{anslutning_id}")
async def ta_bort_anslutning(request: Request, anslutning_id: str, tenant: dict = Depends(require_tenant)) -> dict:
    kraev_uuid(anslutning_id, "Anslutningen")
    if not await lagring.ta_bort_anslutning(request.app.state.storage, tenant["tenant_id"], anslutning_id):
        raise HTTPException(status_code=404, detail="Anslutningen finns inte.")
    return {"borttagen": True}


@router.post("/{anslutning_id}/prova")
async def prova_anslutning(request: Request, anslutning_id: str, tenant: dict = Depends(require_tenant)) -> dict:
    rad = await _anslutning_eller_404(request, tenant["tenant_id"], anslutning_id)
    try:
        hemligheter = lagring.dekryptera_hemligheter(rad)
    except (IngenNyckelError, OlasbarHemlighetError) as fel:
        raise HTTPException(status_code=409, detail=str(fel)) from fel
    adapter = ADAPTRAR[rad["kanal"]]
    saknas = [h for h in adapter.hemligheter_kravs if not hemligheter.get(h)]
    if saknas:
        return {"ok": False, "besked": f"Saknar hemligheter: {', '.join(saknas)}."}
    try:
        besked = await adapter.kontrollera(rad, hemligheter)
    except KanalFel as fel:
        return {"ok": False, "besked": str(fel)}
    return {"ok": True, "besked": besked, "webhook_url": webhook_url(tenant["tenant_id"], rad)}


# -- Webhooks -------------------------------------------------------------------


async def _webhookens_anslutning(
    request: Request, kanal: str, tenant_id: str, anslutning_id: str
) -> tuple[Any, dict[str, Any], dict[str, str]]:
    adapter = ADAPTRAR.get(kanal)
    if adapter is None:
        raise HTTPException(status_code=404, detail="Finns inte.")
    kraev_uuid(tenant_id, "Anslutningen")
    kraev_uuid(anslutning_id, "Anslutningen")
    rad = await lagring.hamta_anslutning(request.app.state.storage, tenant_id, anslutning_id)
    if rad is None or rad["kanal"] != kanal or not rad.get("aktiv"):
        raise HTTPException(status_code=404, detail="Finns inte.")
    try:
        hemligheter = lagring.dekryptera_hemligheter(rad)
    except (IngenNyckelError, OlasbarHemlighetError):
        # Går inte att verifiera = går inte att ta emot. 503 får kanalen att
        # försöka igen senare, i stället för att släppa meddelandet.
        raise HTTPException(status_code=503, detail="Tillfälligt fel.") from None
    return adapter, rad, hemligheter


@router.get("/{kanal}/{tenant_id}/{anslutning_id}/webhook")
async def verifiera_webhook(request: Request, kanal: str, tenant_id: str, anslutning_id: str) -> Response:
    adapter, _, hemligheter = await _webhookens_anslutning(request, kanal, tenant_id, anslutning_id)
    utmaning = adapter.verifiera_prenumeration(dict(request.query_params), hemligheter)
    if utmaning is None:
        raise HTTPException(status_code=403, detail="Verifieringen misslyckades.")
    return PlainTextResponse(utmaning)


@router.post("/{kanal}/{tenant_id}/{anslutning_id}/webhook")
async def ta_emot_webhook(request: Request, kanal: str, tenant_id: str, anslutning_id: str) -> Response:
    adapter, rad, hemligheter = await _webhookens_anslutning(request, kanal, tenant_id, anslutning_id)
    raw = await request.body()
    if len(raw) > MAX_WEBHOOK_BYTES:
        raise HTTPException(status_code=413, detail="För stort.")
    if not await adapter.verifiera(raw, request.headers, hemligheter, rad):
        raise HTTPException(status_code=401, detail="Ogiltig signatur.")
    try:
        payload = json.loads(raw or b"{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Ogiltig JSON.") from None
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Ogiltig JSON.")

    omedelbart = adapter.omedelbart_svar(payload)
    if omedelbart is not None:
        return JSONResponse(omedelbart)

    for inkommande in adapter.tolka(payload, rad):
        starta_i_bakgrunden(
            ta_emot(
                request.app.state,
                tenant_id=tenant_id,
                anslutning=rad,
                adapter=adapter,
                hemligheter=hemligheter,
                inkommande=inkommande,
            )
        )
    return JSONResponse({"ok": True})
