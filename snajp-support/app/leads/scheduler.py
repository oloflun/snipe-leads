"""Del J / Genomförandeordning steg 11: bakgrundskö och schemaläggare.

Speglar app/email_pipeline/poller.py:s mönster exakt (samma
asyncio.create_task-loop, samma "aldrig krascha tjänsten"-princip) i
stället för att lägga till APScheduler som ett nytt beroende för samma
jobb — kodbasen har redan en beprövad periodisk bakgrundsloop.

INV-SEC-004: modellen kan bara köa. process_due_item() är den ENDA
kodvägen i hela tjänsten som får sätta ett send_queue-item till 'sent'.
Grindarna körs igen här (app/leads/send_decision.decide_send_action) —
en köad tid kan ha passerat fönstret sedan den köades.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from ..config import get_settings
from ..storage.base import Storage
from .autonomy import allowed_action, normalize
from .send_decision import decide_send_action
from .send_guard import BLOCKERA as SG_BLOCKERA
from .send_guard import GRANSKA as SG_GRANSKA
from .send_guard import KOLA_OM as SG_KOLA_OM
from .send_guard import SKICKA as SG_SKICKA
from .send_guard import (
    Avsandare,
    TenantHistorik,
    Utskick,
    check_send_guard,
    foretagsnyckel,
)
from .send_provider import SendProvider, get_send_provider

logger = logging.getLogger("snajp-support.leads-scheduler")


async def _outbound_sent_count(storage: Storage, tenant_id: str, thread_id: str) -> int:
    """Hur många utgående meddelanden som redan gått iväg i tråden.

    Det är sekvensindexet för nästa: har inget skickats är nästa nr 0, alltså
    första kontakten. Räknas ur faktiskt skickade rader i stället för ur en
    räknarkolumn — en räknare hade kunnat glida isär med verkligheten, och
    det här är fältet som avgör om ett mejl går ut utan mänsklig granskning.
    """
    thread_messages = await storage.list_outreach_messages(tenant_id, thread_id)
    return sum(
        1
        for message in thread_messages
        if message.get("direction") == "outbound" and message.get("sent_at")
    )


async def _kor_send_guard(storage, tenant_id: str, thread: dict, message: dict, *, now):
    """Samlar ihop fakta och låter `send_guard` döma.

    Uppdelningen är avsiktlig: den här funktionen gör I/O och ingen bedömning,
    `send_guard` gör bedömning och ingen I/O. Det är därför de sex reglerna
    går att testa utan databas, klocka eller mejlserver.

    Avsändaridentiteten kommer från tenantens konfiguration. Saknas något av
    de tre fälten faller regel 1 — vilket är rätt utfall: ett utskick utan
    lagstadgad avsändarinformation ska inte gå iväg bara för att vi glömt
    fylla i kunduppgifterna.
    """
    tenant = await storage.get_tenant(tenant_id) or {}
    dygnets_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    nyckel = thread.get("foretagsnyckel") or foretagsnyckel(
        orgnr=thread.get("prospect_orgnr"),
        epost=thread.get("prospect_email"),
        hemsida=thread.get("prospect_website"),
    )

    historik = TenantHistorik(
        skickade_totalt=await storage.count_sent_outreach(tenant_id),
        skickade_idag=await storage.count_sent_outreach(tenant_id, since=dygnets_start),
        tenant_alder_dagar=_alder_i_dagar(tenant.get("created_at"), now),
        senaste_kontakt_med_foretaget=await storage.last_contact_with_company(
            tenant_id, nyckel
        ),
        suppressions=frozenset(await storage.list_suppressions(tenant_id)),
        # Trådens egna tidigare kontakter räknas inte som "tidigare kontaktad" —
        # det är hela poängen med en uppföljning. Regel 3 gäller nya trådar.
        tidigare_kontaktade=frozenset(),
        egna_kunder=frozenset(),
    )

    return check_send_guard(
        avsandare=Avsandare(
            foretagsnamn=str(tenant.get("company_name") or tenant.get("name") or ""),
            orgnr=str(tenant.get("orgnr") or ""),
            postadress=str(tenant.get("postal_address") or ""),
        ),
        utskick=Utskick(
            mottagare=thread.get("prospect_email") or "",
            amne=message.get("subject") or "",
            brodtext=message.get("body") or "",
            foretagsnyckel=nyckel,
            personlig_adress=_ar_personlig(thread.get("prospect_email")),
        ),
        historik=historik,
        nu=now,
    )


def _alder_i_dagar(created_at, now) -> int:
    """Tenantens ålder styr domänuppvärmningen (regel 5c).

    Okänt skapandedatum behandlas som NY, inte som gammal. Fail-closed: en
    tenant vi inte vet åldern på ska få det försiktigare taket, inte det
    generösare.
    """
    if not created_at:
        return 0
    try:
        return max((now - created_at).days, 0)
    except TypeError:
        return 0


def _ar_personlig(epost) -> bool:
    """Samma bedömning som `Prospect.epost_ar_personlig`, mot en lös adress."""
    from .sources.base import Prospect

    return Prospect(company_name="", contact_email=epost).epost_ar_personlig


async def process_due_item(
    storage: Storage, tenant_id: str, item: dict, provider: SendProvider, *, now: datetime
) -> str:
    """Returnerar 'sent' | 'requeued' | 'blocked' | 'awaiting_review'."""
    thread = await storage.get_outreach_thread(tenant_id, item["thread_id"])
    message = (
        await storage.get_pending_outreach_message(tenant_id, item["thread_id"]) if thread else None
    )
    decision = decide_send_action(now=now, thread=thread, message=message)

    # Andra anropsplatsen för autonomiregeln. Grinden vid köningen räcker inte:
    # ett item kan ha köats innan kunden sänkte sin nivå, och det som ligger i
    # kön ska då stoppas — inte skickas för att det hann bli godkänt av en
    # regel som gällde igår.
    #
    # sequence_index räknas ur trådens redan skickade utgående meddelanden.
    if decision.action == "send":
        sent_before = await _outbound_sent_count(storage, tenant_id, item["thread_id"])
        settings = await storage.get_agent_settings(tenant_id, agent_type="leads")
        if allowed_action(settings.get("autonomy"), sent_before) != "send":
            await storage.update_send_queue_status(
                tenant_id,
                item["id"],
                status="awaiting_review",
                gate_checks={
                    "decision": decision.reason,
                    "autonomy": normalize(settings.get("autonomy")),
                    "held": "autonominivån tillåter inte utskick av det här steget",
                },
            )
            return "awaiting_review"

    if decision.action == "send":
        # DEL 2.3: de sex spärrarna. De körs SIST, direkt före provider.send(),
        # därför att det är den enda punkt där allt är känt samtidigt —
        # mottagaren, den färdiga texten, klockan och tenantens historik.
        #
        # En guard som körts vid köningen hade dömt på gårdagens sanning: en
        # mottagare kan ha avregistrerat sig medan utkastet låg i kön.
        guard = await _kor_send_guard(storage, tenant_id, thread, message, now=now)
        if guard.atgard != SG_SKICKA:
            status = {
                SG_BLOCKERA: "blocked",
                SG_GRANSKA: "awaiting_review",
                SG_KOLA_OM: "queued",
            }[guard.atgard]
            await storage.update_send_queue_status(
                tenant_id,
                item["id"],
                status=status,
                gate_checks={
                    "decision": decision.reason,
                    "send_guard_regel": guard.regel,
                    "send_guard_skal": guard.skal,
                },
            )
            logger.info(
                "send_guard %s stoppade %s: %s", guard.regel, item.get("id"), guard.skal
            )
            return {
                "blocked": "blocked",
                "awaiting_review": "awaiting_review",
                "queued": "requeued",
            }[status]

        await provider.send(
            to=thread.get("prospect_email", "okänd"),
            subject=message.get("subject", ""),
            body=message["body"],
        )
        await storage.mark_outreach_message_sent(tenant_id, message["id"], now)
        await storage.update_send_queue_status(
            tenant_id, item["id"], status="sent", gate_checks={"decision": decision.reason}
        )
        return "sent"

    if decision.action == "block":
        await storage.update_send_queue_status(
            tenant_id, item["id"], status="blocked", gate_checks={"decision": decision.reason}
        )
        return "blocked"

    # requeue: status förblir 'queued' — fångas upp igen nästa gång fönstret är öppet.
    await storage.update_send_queue_status(
        tenant_id, item["id"], status="queued", gate_checks={"decision": decision.reason}
    )
    return "requeued"


async def process_all_due(storage: Storage, provider: SendProvider) -> list[dict]:
    now = datetime.now(timezone.utc)
    results: list[dict] = []
    for tenant in await storage.list_tenants():
        for item in await storage.list_due_send_queue(tenant["id"], now):
            try:
                outcome = await process_due_item(storage, tenant["id"], item, provider, now=now)
            except Exception:  # noqa: BLE001 — en trasig post stoppar inte de andra
                logger.exception("send_queue-post %s misslyckades oväntat", item.get("id"))
                outcome = "error"
            results.append({"tenant": tenant["slug"], "item_id": item.get("id"), "outcome": outcome})
    return results


async def run_send_scheduler(app_state) -> None:
    settings = get_settings()
    interval = max(settings.send_queue_poll_seconds, 30)
    provider = get_send_provider()
    logger.info("send_queue-schemaläggare aktiv: var %s sekund.", interval)
    while True:
        try:
            for result in await process_all_due(app_state.storage, provider):
                if result["outcome"] != "requeued":
                    logger.info(
                        "send_queue %s (%s): %s",
                        result["item_id"],
                        result["tenant"],
                        result["outcome"],
                    )
        except Exception:  # noqa: BLE001 — schemaläggaren får aldrig dö
            logger.exception("Oväntat fel i send_queue-schemaläggaren — fortsätter nästa varv.")
        await asyncio.sleep(interval)
