"""Iris autopilot: en schemalagd leadskörning per vardag och kund (Anton
2026-10-10, docs/BESLUT.md).

Före 2026-10-10 startade ingenting en körning av sig själv; varje körning var
ett klick. Autopiloten startar EN Iris-körning (research och utkast) per vardag
från klockan KORTIMME, med kundens `automation.autopilot.leads_per_dag` leads
(standard 10, tak 50). Allt därefter går som en vanlig körning: utkasten,
uppföljningssvepet och svarshanteringen finns redan.

Vad som SKICKAS styrs av kontots spärr (`autonomy`, leads/autonomy.py) och av
utskicksloopen (`SEND_QUEUE_POLL_SECONDS`). Är den av, vilket den är i båda
miljöerna 2026-10-10, väntar varje utkast på en människas ja oavsett spärr.

Två lås, båda måste vara på:
  * miljöns `LEADS_AUTOPILOT=1` (av som standard, så att development, som
    speglar produktionen, aldrig startar körningar åt riktiga kunder av sig
    själv),
  * kundens `automation.autopilot.pa`.

Körs varje minut från leads-städaren (jobs/stadare.py). Kastar aldrig."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

from . import automation
from .timing_gate import STOCKHOLM, is_blocked_day

logger = logging.getLogger("snajp-support.leads.autopilot")

#: Körningen startar tidigast så här dags (svensk tid), så att utkasten är
#: klara när sändfönstret öppnar 08:00.
KORTIMME = 6


def aktiv() -> bool:
    return os.environ.get("LEADS_AUTOPILOT", "").strip() == "1"


def ska_kora(regler: dict[str, Any], korningar: list[dict[str, Any]], nu: datetime) -> bool:
    """Ren funktion: ska kunden få dagens autopilotkörning nu?"""
    if not regler["autopilot"]["pa"]:
        return False
    lokal = nu.astimezone(STOCKHOLM)
    if is_blocked_day(lokal) or lokal.hour < KORTIMME:
        return False
    idag = lokal.date()
    for rad in korningar:
        k = rad.get("korning") or {}
        skapad = rad.get("created_at")
        if isinstance(skapad, str):
            try:
                skapad = datetime.fromisoformat(skapad)
            except ValueError:
                continue
        if k.get("autopilot") and isinstance(skapad, datetime) and skapad.astimezone(STOCKHOLM).date() == idag:
            return False
        if rad.get("status") in ("queued", "processing") and k.get("autopilot"):
            return False
    return True


async def svep(app_state: Any, *, nu: datetime | None = None) -> list[str]:
    """Startar dagens körning hos varje kund där autopiloten är på.
    Returnerar de startade körningarnas job_id."""
    if not aktiv():
        return []
    nu = nu or datetime.now(timezone.utc)
    storage = app_state.storage
    if await storage.spegel_info():
        # Bara main kör autopiloten; en spegel får körningarna via synken.
        return []
    startade: list[str] = []
    for tenant in await storage.list_tenants():
        tid = tenant["id"]
        try:
            regler = automation.normalisera(
                (await storage.get_agent_settings(tid, agent_type="leads")).get("automation")
            )
            if not ska_kora(regler, await storage.list_leads_korningar(tid, limit=20), nu):
                continue
            startade.append(await _starta(app_state, tenant, regler["autopilot"]["leads_per_dag"]))
        except Exception:  # noqa: BLE001 — en kund stoppar inte de andra
            logger.exception("Autopiloten kunde inte starta en körning för %s.", tid)
    return startade


async def _starta(app_state: Any, tenant: dict[str, Any], antal: int) -> str:
    """Samma väg som POST /api/leads/runs/batch, märkt `autopilot`."""
    from ..api.leads import _run_batch
    from .budget import kontrollera_leads_budget

    tid = tenant["id"]
    await kontrollera_leads_budget(app_state.storage, tid)
    job_id = await app_state.jobs.create(tenant_id=tid, status="queued")
    await app_state.storage.set_leads_job_status(tid, job_id=job_id, status="queued", scope="batch")
    post = {
        "kind": "batch", "job_id": job_id, "tenant_id": tid, "tenant_name": tenant.get("name") or "",
        "scope": "research_and_draft", "overrides": None, "is_test": False, "limit": antal,
        "company_names": [], "autopilot": True,
    }
    strom = getattr(app_state, "leadsstrom", None)
    if strom is not None:
        await strom.enqueue(post)
    else:
        asyncio.create_task(_run_batch(app_state, post))
    logger.info("Autopiloten startade körning %s för %s (%s leads).", job_id, tid, antal)
    return job_id
