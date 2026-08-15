"""Hur långt leads-agenten får gå utan en människa.

EN regel, TVÅ anropsplatser: `leads_tools.queue_outreach_draft` när utkastet
skrivs, och `scheduler.process_due_item` när det är dags att skicka. Att låta
båda resonera var för sig hade betytt två ställen som kan glida isär — och den
glidningen syns först när ett mejl gått iväg.

Nivåerna, i stigande ordning:

| Nivå            | Vad agenten får göra                                    |
|-----------------|---------------------------------------------------------|
| `draft`         | Researchar och skriver. Inget lämnar huset utan att en  |
|   **(default)** | människa tryckt skicka.                                  |
| `first_contact` | Skickar första mejlet självt. Uppföljning och möte      |
|                 | kräver människa.                                         |
| `meeting`       | Får driva tråden till bokat möte.                        |

Default är `draft` för varje ny kund. Ett fel blir då ett dåligt utkast, inte
ett skickat mejl till en riktig mottagare — och skillnaden mellan de två är
skillnaden mellan en intern miss och ett brev till någons vd.

`meeting` kräver att `handoff.py` kopplas in, vilket ännu inte skett i
produktion. Nivån går att välja, men se `MEETING_REQUIRES_HANDOFF` nedan.
"""

from __future__ import annotations

from typing import Literal

Autonomy = Literal["draft", "first_contact", "meeting"]
Action = Literal["queue", "send", "hold"]

DEFAULT_AUTONOMY: Autonomy = "draft"
LEVELS: tuple[Autonomy, ...] = ("draft", "first_contact", "meeting")

#: `meeting` förutsätter att handoff.py har en produktionsanropare. Den har
#: ingen i dag. Tills dess beter sig meeting som first_contact — dokumenterat
#: här i stället för att tyst göra något annat än vad kunden valt.
MEETING_REQUIRES_HANDOFF = True


class UnknownAutonomyError(ValueError):
    pass


def normalize(value: object) -> Autonomy:
    """Okänt eller saknat värde blir `draft`.

    Fail-closed: en trasig konfiguration ska ge FÄRRE befogenheter, aldrig
    fler. Det motsatta valet gör ett skrivfel i en jsonb-nyckel till ett
    utskickat mejl.
    """
    if isinstance(value, str) and value in LEVELS:
        return value  # type: ignore[return-value]
    return DEFAULT_AUTONOMY


def allowed_action(autonomy: object, sequence_index: int) -> Action:
    """Vad som får hända med meddelande nr `sequence_index` i en tråd.

    `queue` = skriv utkastet och lämna det för granskning.
    `send`  = agenten får skicka självt.
    `hold`  = stanna, en människa måste ta över.

    sequence_index är nollindexerat: 0 är första kontakten.
    """
    level = normalize(autonomy)

    if sequence_index < 0:
        raise UnknownAutonomyError(f"sequence_index kan inte vara negativt: {sequence_index}")

    if level == "draft":
        # Inget lämnar huset. Även uppföljningar köas för granskning — en kund
        # som valt draft har inte valt "draft utom när det är tredje mejlet".
        return "queue"

    if level == "first_contact":
        return "send" if sequence_index == 0 else "queue"

    # meeting
    if MEETING_REQUIRES_HANDOFF and sequence_index > 0:
        # handoff.py saknar produktionsanropare. Att låta agenten driva tråden
        # vidare utan den betyder att den skriver mot ett svar den inte kan
        # tolka — köa i stället, så ser människan vad som hänt.
        return "queue"

    return "send"


def describe(autonomy: object) -> str:
    """Raden som står bredvid valet i UI:t. Kunden ska kunna välja utan att
    fråga oss vad orden betyder."""
    level = normalize(autonomy)
    return {
        "draft": "Agenten researchar och skriver. Ingenting skickas förrän du tryckt skicka.",
        "first_contact": "Agenten skickar första mejlet självt. Uppföljningar väntar på dig.",
        "meeting": (
            "Agenten får driva samtalet till ett bokat möte."
            + (" Uppföljningar köas fortfarande — överlämningen är inte påkopplad än."
               if MEETING_REQUIRES_HANDOFF else "")
        ),
    }[level]
