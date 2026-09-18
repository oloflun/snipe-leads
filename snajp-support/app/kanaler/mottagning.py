"""Ett inkommande kanalmeddelande hela vägen: spärr -> kund -> agent -> svar.

Körs i BAKGRUNDEN efter att webhooken kvitterats (api/kanaler.py): Slack
skickar om en händelse som inte kvitterats inom tre sekunder, Meta efter
något längre. En agentkörning tar längre tid än så. Kvittensen betyder alltså
"mottaget", inte "besvarat", och dubblettspärren gör att en omsändning som
ändå kommer inte ger kunden två svar.

## Kunden

En kanalkund har ofta varken e-post eller telefon hos oss (Messenger ger
bara ett sid-specifikt id). Kopplingen görs därför i ss_channel_contacts:
första meddelandet skapar kunden (med telefon för WhatsApp, e-post när Slack
ger den), och varje följande meddelande hittar samma kund via kontakten.
Samtalet blir då ett samtal och inte en rad nya kunder.

## Fel

Allt fångas här. En webhook kan inte bära ett felsvar till kunden, så ett
fel blir en rad i platform_events och, när det går, ett kort ärligt svar i
kanalen i stället för tystnad.
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

from ..api import rate_limit_db
from ..kvotfel import ar_kreditslut, larma_kreditslut
from . import lagring
from .bas import Adapter, Inkommande, KanalFel

logger = logging.getLogger("snajp-support.kanaler")

#: Till slutkunden när agenten inte kunde köra. Kort, sant och utan att lova
#: något: ingen människa har sett meddelandet, så ingen "kollega återkommer".
TEXT_TILLFALLIGT_FEL = "Vi kan tyvärr inte svara automatiskt just nu. Försök gärna igen om en stund."

#: Bakgrundsjobb hålls i en mängd tills de är klara — en task som ingen
#: refererar kan skräpsamlas mitt i körningen (asyncio-dokumentationens råd).
_pagaende: set[asyncio.Task[Any]] = set()


def starta_i_bakgrunden(koroutin: Any) -> asyncio.Task[Any]:
    task = asyncio.create_task(koroutin)
    _pagaende.add(task)
    task.add_done_callback(_pagaende.discard)
    return task


async def _logga(storage: Any, tenant_id: str, niva: str, meddelande: str, detalj: dict[str, Any]) -> None:
    try:
        await storage.log_platform_event(
            level=niva, source="kanal", message=meddelande[:300], tenant_id=tenant_id, detail=detalj
        )
    except Exception:  # noqa: BLE001 — loggningen får aldrig fälla något
        logger.warning("kunde inte skriva kanalhändelsen till platform_events")


async def _svara(
    storage: Any,
    tenant_id: str,
    adapter: Adapter,
    anslutning: dict[str, Any],
    hemligheter: dict[str, str],
    inkommande: Inkommande,
    text: str,
) -> bool:
    try:
        await adapter.skicka(
            anslutning,
            hemligheter,
            mottagare=inkommande.extern_anvandare,
            adress=inkommande.adress,
            text=text,
        )
        return True
    except KanalFel as fel:
        await _logga(
            storage, tenant_id, "error", f"{adapter.kanal}: svaret kunde inte skickas ({fel})",
            {"anslutning_id": anslutning["id"]},
        )
        return False


async def _kund_id(storage: Any, tenant_id: str, anslutning: dict[str, Any], inkommande: Inkommande) -> str:
    kontakt = await lagring.hamta_kontakt(storage, tenant_id, anslutning["id"], inkommande.extern_anvandare)
    if kontakt:
        kund_id = kontakt["customer_id"]
    else:
        kund = await storage.find_or_create_customer(
            tenant_id,
            email=inkommande.email,
            phone=inkommande.telefon,
            name=inkommande.visningsnamn,
        )
        kund_id = kund["id"]
    await lagring.spara_kontakt(
        storage,
        tenant_id,
        anslutning_id=anslutning["id"],
        customer_id=kund_id,
        extern_anvandare=inkommande.extern_anvandare,
        adress=inkommande.adress,
        visningsnamn=inkommande.visningsnamn,
    )
    return kund_id


async def ta_emot(
    app_state: Any,
    *,
    tenant_id: str,
    anslutning: dict[str, Any],
    adapter: Adapter,
    hemligheter: dict[str, str],
    inkommande: Inkommande,
) -> dict[str, Any]:
    """Kör ett inkommande meddelande. Kastar aldrig; returnerar ett utfall
    (för testerna och loggen)."""
    storage = app_state.storage
    try:
        if not await lagring.markera_sett(storage, tenant_id, anslutning["id"], inkommande.extern_meddelande_id):
            return {"status": "dubblett"}
        if random.random() < 0.01:
            await lagring.stada_sett(storage, tenant_id)

        berika = getattr(adapter, "berika", None)
        if berika is not None:
            await berika(hemligheter, inkommande)

        kund_id = await _kund_id(storage, tenant_id, anslutning, inkommande)
    except Exception as fel:  # noqa: BLE001
        logger.exception("Kanalmeddelandet kunde inte tas emot (tenant %s)", tenant_id)
        await _logga(
            storage, tenant_id, "error", f"{adapter.kanal}: mottagningen föll ({type(fel).__name__})",
            {"anslutning_id": anslutning["id"]},
        )
        return {"status": "fel"}

    scopes = rate_limit_db.scopes_for(tenant_id, None)
    try:
        await rate_limit_db.enforce(storage, scopes)
    except rate_limit_db.RateLimitDbExceededError as fel:
        await _logga(
            storage, tenant_id, "warning", f"{adapter.kanal}: kvoten för agentkörningar är slut ({fel})",
            {"anslutning_id": anslutning["id"]},
        )
        await _svara(storage, tenant_id, adapter, anslutning, hemligheter, inkommande, TEXT_TILLFALLIGT_FEL)
        return {"status": "kvot"}

    try:
        from ..agent.support_agent import run_support_agent

        resultat = await run_support_agent(
            storage,
            tenant_id,
            message=inkommande.text,
            subject="",
            channel=adapter.kanal,
            customer_email=inkommande.email,
            customer_name=inkommande.visningsnamn,
            attachments=[],
            kund_id=kund_id,
        )
    except Exception as fel:  # noqa: BLE001 — kunden ska få ett svar, inte tystnad
        logger.exception("Agentkörningen för %s föll (tenant %s)", adapter.kanal, tenant_id)
        await _logga(
            storage, tenant_id, "error", f"{adapter.kanal}: {type(fel).__name__}: {str(fel)[:200]}",
            {"anslutning_id": anslutning["id"]},
        )
        if ar_kreditslut(fel):
            await larma_kreditslut(storage, tenant_id=tenant_id, kalla=f"kanal:{adapter.kanal}", fel=fel)
        await _svara(storage, tenant_id, adapter, anslutning, hemligheter, inkommande, TEXT_TILLFALLIGT_FEL)
        return {"status": "agentfel"}

    llm_steg = [s for s in (resultat.get("step_log") or []) if "skill" in s]
    await rate_limit_db.record(storage, scopes, len(llm_steg))

    svar = str(resultat.get("reply") or "").strip()
    if not svar:
        # Samtalet ägs av en människa (sömlös överlämning): agenten svarar
        # inte, medarbetarens svar kommer via leverans.leverera.
        return {"status": "tyst", "kund_id": kund_id}
    skickat = await _svara(storage, tenant_id, adapter, anslutning, hemligheter, inkommande, svar)
    return {"status": "besvarat" if skickat else "leveransfel", "kund_id": kund_id, "svar": svar}
