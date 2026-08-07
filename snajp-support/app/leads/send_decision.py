"""Den rena beslutslogiken bakom schemaläggaren (Del J): given en due
send_queue-post, en tråd och ett meddelande — vad ska hända? Ingen I/O här,
med avsikt: detta är exakt det app/leads/scheduler.py kör mot en riktig
databas, men går att testa fullständigt utan en.

Grindarna kontrolleras IGEN här (inte bara vid köning) — en köad tid kan ha
passerat fönstret sedan den köades (Del J)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .language_gate import LanguageGateError, check_send_gate
from .timing_gate import check_cold_outreach_gate, check_thread_reply_gate


@dataclass(frozen=True)
class SendDecision:
    action: str  # "send" | "requeue" | "block"
    reason: str


def decide_send_action(
    *,
    now: datetime,
    thread: dict | None,
    message: dict | None,
) -> SendDecision:
    if thread is None or message is None:
        return SendDecision("block", "tråd eller köat meddelande saknas — inget att skicka")

    last_inbound_at = thread.get("last_inbound_at")
    if last_inbound_at is not None:
        timing = check_thread_reply_gate(now, prospect_last_inbound_at=last_inbound_at)
    else:
        timing = check_cold_outreach_gate(now)

    if not timing.allowed:
        return SendDecision("requeue", timing.reason or "utanför tidsfönstret")

    try:
        check_send_gate(
            language_state=thread.get("language_state", "sv"),
            humanizer_variant=message.get("humanizer_variant"),
        )
    except LanguageGateError as error:
        # Ett språkfel löser sig inte av att vänta — blockera, kräv manuell
        # rättning, i stället för att köa om i evighet.
        return SendDecision("block", str(error))

    return SendDecision("send", "alla grindar godkände")
