"""Sömlös överlämning: medarbetaren svarar i SAMMA chatt som kunden sitter i.

## Flödet (bd snipe-1fl, Ebbot-modellen)

1. Agenten lämnar över (`support_agent`, orsakskod i ss_chat_state). Kunden
   får beskedet i chatten, och samtalet ägs från och med nu av en människa.
2. Kundens nya meddelanden läggs i det överlämnade ärendets tråd, utan
   AI-svar (`support_agent._svara_under_overlamning`).
3. Medarbetaren läser HELA samtalet — alla ärenden, inte bara det sista
   meddelandet — i portalens Chattar-vy (`samtalsutskrift`) och svarar
   (`medarbetarsvar`). Svaret sparas med author='human'.
4. Chattfönstret hämtar medarbetarens svar och visar dem i samma fönster.
5. Medarbetaren lämnar tillbaka samtalet (`aterlamna`); agenten svarar igen.

Funktionerna här är den enda skrivvägen för medarbetarens del, så att en
leveranskrok (en annan kanal än webbchatten) har ETT ställe att sitta på.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..storage.base import Storage
from . import support_regler


class OverlamningsFel(Exception):
    """Ett begripligt svenskt fel som API:t visar som 4xx."""


def _tid(varde: Any) -> datetime | None:
    if not varde:
        return None
    try:
        tid = datetime.fromisoformat(str(varde))
    except ValueError:
        return None
    return tid if tid.tzinfo else tid.replace(tzinfo=timezone.utc)


def _avsandare(meddelande: dict[str, Any]) -> str:
    """author-kolumnen, med äldre rader (NULL) tolkade som före migration 066."""
    author = meddelande.get("author")
    if author in ("customer", "agent", "human"):
        return author
    return "customer" if meddelande.get("direction") == "inbound" else "agent"


async def samtalsutskrift(
    storage: Storage, tenant_id: str, customer_id: str
) -> list[dict[str, Any]]:
    """Hela samtalet i tidsordning, över ALLA kundens ärenden.

    Varje chattmeddelande är ett eget ärende, så "hela historiken" är
    kundens ärenden i följd — inte det överlämnade ärendets tråd ensam. Det är
    kravet: medarbetaren ska se allt kunden redan sagt, inte bara sista
    meddelandet, och kunden ska aldrig behöva börja om.
    """
    rader: list[dict[str, Any]] = []
    for arende in reversed(await storage.get_customer_history(tenant_id, customer_id)):
        if not arende.get("conversation_id"):
            continue
        for m in await storage.get_messages(tenant_id, arende["conversation_id"]):
            rader.append(
                {
                    "id": str(m.get("id")),
                    "author": _avsandare(m),
                    "content": m.get("content") or "",
                    "created_at": m.get("created_at"),
                    "ticket_id": arende["id"],
                }
            )
    rader.sort(key=lambda r: _tid(r["created_at"]) or datetime.min.replace(tzinfo=timezone.utc))
    return rader


def efter(rader: list[dict[str, Any]], tidpunkt: str | None) -> list[dict[str, Any]]:
    """Raderna skapade EFTER tidpunkten (chattfönstrets inkrementella hämtning)."""
    grans = _tid(tidpunkt)
    if grans is None:
        return rader
    return [r for r in rader if (_tid(r["created_at"]) or grans) > grans]


async def medarbetarsvar(
    storage: Storage, tenant_id: str, customer_id: str, text: str
) -> dict[str, Any]:
    """Sparar medarbetarens svar i det överlämnade ärendets tråd.

    Är samtalet inte överlämnat tar medarbetaren över det här: en människa
    som vill kliva in i ett samtal ska inte behöva vänta på att agenten ger
    upp. Övertagandet registreras med orsakskoden `medarbetare_tog_over` på
    kundens senaste ärende.

    Returnerar {"message", "ticket"}; ärendet bär `channel`, så en
    leveranskrok för andra kanaler än webbchatten vet vart svaret ska.
    """
    text = (text or "").strip()
    if not text:
        raise OverlamningsFel("Svaret är tomt.")

    samtal = await storage.get_chat_state(tenant_id, customer_id)
    ticket_id = samtal.get("overlamnad_ticket_id") if samtal.get("lage") == "overlamnad" else None
    orsak = samtal.get("overlamnad_orsak")
    if not ticket_id:
        historik = await storage.get_customer_history(tenant_id, customer_id)
        if not historik:
            raise OverlamningsFel("Kunden har inget samtal att svara i.")
        ticket_id = historik[0]["id"]
        orsak = "medarbetare_tog_over"
        await storage.update_ticket(
            tenant_id,
            ticket_id,
            status="escalated",
            escalation_reason=support_regler.ORSAKER["medarbetare_tog_over"],
        )

    arende = await storage.get_ticket(tenant_id, ticket_id)
    if not arende or not arende.get("conversation_id"):
        raise OverlamningsFel("Det överlämnade ärendet finns inte längre.")

    meddelande = await storage.save_message(
        tenant_id,
        conversation_id=arende["conversation_id"],
        direction="outbound",
        content=text,
        sentiment=None,
        has_image=False,
        author="human",
    )
    # Flyttar updated_at: samtalet ligger kvar hos människan i ytterligare
    # OVERLAMNING_GILTIG_TIMMAR räknat från hennes senaste svar.
    await storage.save_chat_state(
        tenant_id,
        customer_id,
        lage="overlamnad",
        misslyckade_i_rad=0,
        erbjod_manniska=False,
        overlamnad_orsak=orsak,
        overlamnad_ticket_id=ticket_id,
    )
    arende.pop("messages", None)
    return {"message": meddelande, "ticket": arende}


async def aterlamna(storage: Storage, tenant_id: str, customer_id: str) -> dict[str, Any]:
    """Medarbetaren lämnar tillbaka samtalet till agenten. Ärendet markeras
    löst; nästa meddelande från kunden besvaras av agenten igen."""
    samtal = await storage.get_chat_state(tenant_id, customer_id)
    ticket_id = samtal.get("overlamnad_ticket_id")
    if ticket_id:
        await storage.update_ticket(tenant_id, ticket_id, status="resolved")
    return await storage.save_chat_state(
        tenant_id,
        customer_id,
        lage="agent",
        misslyckade_i_rad=0,
        erbjod_manniska=False,
        overlamnad_orsak=None,
        overlamnad_ticket_id=None,
    )
