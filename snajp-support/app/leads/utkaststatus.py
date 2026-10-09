"""En sanning per lead om dess mejlutkast (Antons beställning 2026-10-07).

## Varför

Uppmätt i development 2026-10-07: 26 utkast godkändes av en människa efter
sändfönstret (16:41–22:05). De låg som `queued` med `approved_by='human'` och
skulle gå ut 08:00 — men syntes ingenstans: "Utkast att godkänna" räknade bara
`awaiting_review`, "Skickade mejl" bara riktiga utskick, och lådan visade
trådens senaste meddelande oavsett status, märkt som utkast.

Härledningen bodde dessutom i en enda vy (`_korningens_leads`). Nu bor den
här, och listan över alla leads (`GET /api/leads/prospects`), körningsvyn och
lådan läser samma funktion — på underlaget ur `storage.utkast_lagen`, EN fråga
per anrop.

## Statusarna

| Status | Betyder |
|---|---|
| `saknas` | inget utkast |
| `vantar` | väntar på granskarens ja (`awaiting_review`) |
| `godkant` | godkänt av en människa, skickas när sändfönstret öppnar |
| `koad` | köat utan mänskligt godkännande (äldre utkast; se scripts/koade_utkast_till_granskning.py) |
| `skickat` | ett mejl har gått ut |
| `avvisat` | utkastet avvisades eller ersattes, inget skickat |
| `stoppat` | en sändspärr sa nej (`utkast_skal` bär skälet) |

Ett aktivt nästa steg (väntar, godkänt, köat) går före "skickat": ett
uppföljningsutkast som väntar på ett ja är det leadet behöver nu. Ett skickat
mejl går före ett avvisat eller stoppat utkast: leadet ÄR kontaktat.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from .timing_gate import COLD_OUTREACH_END_HOUR, STOCKHOLM, WINDOW_START_HOUR, is_blocked_day

STATUSAR = ("saknas", "vantar", "godkant", "koad", "skickat", "avvisat", "stoppat")


def _grind(gate_checks: Any) -> dict[str, Any]:
    if isinstance(gate_checks, str):
        try:
            gate_checks = json.loads(gate_checks)
        except ValueError:
            return {}
    return gate_checks if isinstance(gate_checks, dict) else {}


def _tid(varde: Any) -> datetime | None:
    if isinstance(varde, datetime):
        return varde if varde.tzinfo else varde.replace(tzinfo=timezone.utc)
    if isinstance(varde, str) and varde:
        try:
            tid = datetime.fromisoformat(varde)
        except ValueError:
            return None
        return tid if tid.tzinfo else tid.replace(tzinfo=timezone.utc)
    return None


def nasta_sandtid(scheduled_at: Any, *, now: datetime) -> str | None:
    """När ett köat utkast tidigast går ut: den köade tiden eller nu, flyttad
    till nästa öppna sändfönster (vardagar 08–16 svensk tid, inte helgdag).
    Ett godkännande 16:41 har scheduled_at 16:41 men skickas 08:00 nästa
    vardag — det är den tiden kunden behöver se."""
    tid = _tid(scheduled_at) or now
    tid = max(tid, now).astimezone(STOCKHOLM)
    for _ in range(15):
        if not is_blocked_day(tid):
            if tid.hour < WINDOW_START_HOUR:
                return tid.replace(hour=WINDOW_START_HOUR, minute=0, second=0, microsecond=0).isoformat()
            if tid.hour < COLD_OUTREACH_END_HOUR:
                return tid.isoformat()
        tid = (tid + timedelta(days=1)).replace(hour=WINDOW_START_HOUR, minute=0, second=0, microsecond=0)
    return None


def harled(lage: dict[str, Any] | None, *, now: datetime | None = None) -> dict[str, Any]:
    """Utkaststatusen för ETT lead, ur dess rad i `storage.utkast_lagen`.

    Returnerar `utkast_status`, `utkast_skal` (sändspärrens eller
    granskningens skäl), `queue_item_id` (köposten ett godkännande eller en
    redigering gäller; vantar/godkant/koad/stoppat), `utkast_regel` (stoppat), `skickas_tidigast`
    (för godkant/koad) och `skickat_at`."""
    ut: dict[str, Any] = {
        "utkast_status": "saknas",
        "utkast_skal": None,
        "queue_item_id": None,
        "skickas_tidigast": None,
        "skickat_at": None,
        "utkast_regel": None,
    }
    if not lage:
        return ut
    ut["skickat_at"] = lage.get("skickat_at")
    ko = lage.get("ko_status")
    grind = _grind(lage.get("gate_checks"))
    skal = grind.get("send_guard_skal") or grind.get("held")

    if ko == "awaiting_review":
        ut.update(utkast_status="vantar", queue_item_id=lage.get("queue_item_id"), utkast_skal=skal)
    elif ko == "queued":
        ut.update(
            utkast_status="godkant" if grind.get("approved_by") == "human" else "koad",
            queue_item_id=lage.get("queue_item_id"),
            skickas_tidigast=nasta_sandtid(lage.get("scheduled_at"), now=now or datetime.now(timezone.utc)),
        )
    elif lage.get("skickat_at") or ko == "sent":
        ut["utkast_status"] = "skickat"
    elif ko == "cancelled":
        ut["utkast_status"] = "avvisat"
    elif ko == "blocked" and lage.get("antal_osanda") == 0:
        # Stoppat, men texten är kasserad (2026-10-09: dubbletterna städades
        # och lämnade stoppade poster utan utkast). Inget att skicka: leadet
        # saknar utkast, och Skapa utkast skriver ett nytt.
        pass
    elif ko == "blocked":
        # Köposten följer med (2026-10-09): Godkänn och skicka prövar ett
        # stoppat utkast igen när orsaken är åtgärdad. `utkast_regel` säger
        # vilken spärr, så att listan kan säga vad som ska göras.
        ut.update(
            utkast_status="stoppat",
            utkast_skal=skal or grind.get("decision"),
            queue_item_id=lage.get("queue_item_id"),
            utkast_regel=grind.get("send_guard_regel"),
        )
    return ut


def per_prospekt(lagen: dict[str, dict[str, Any]], prospect_ids, *, now: datetime | None = None) -> dict[str, dict[str, Any]]:
    """`harled` för varje prospekt-id; ett lead utan tråd blir `saknas`."""
    nu = now or datetime.now(timezone.utc)
    return {str(pid): harled(lagen.get(str(pid)), now=nu) for pid in prospect_ids}
