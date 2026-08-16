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

from dataclasses import dataclass
from typing import Literal

Autonomy = Literal["draft", "first_contact", "meeting", "auto_send"]
Action = Literal["queue", "send", "hold"]

DEFAULT_AUTONOMY: Autonomy = "draft"
LEVELS: tuple[Autonomy, ...] = ("draft", "first_contact", "meeting", "auto_send")

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

    if level == "auto_send":
        # Enda nivån där även uppföljningar går ut självt. Den är omöjlig att
        # SÄTTA utan att `kan_aktivera_auto_send` godkänt — se den funktionen.
        # Att den ändå tolkas här, och inte antas vara giltig, är avsiktligt:
        # en rad som redan ligger i databasen har inte passerat någon grind.
        return "send"

    # meeting
    if MEETING_REQUIRES_HANDOFF and sequence_index > 0:
        # handoff.py saknar produktionsanropare. Att låta agenten driva tråden
        # vidare utan den betyder att den skriver mot ett svar den inte kan
        # tolka — köa i stället, så ser människan vad som hänt.
        return "queue"

    return "send"


# -- Grinden framför auto_send ----------------------------------------------


@dataclass(frozen=True)
class Aktiveringsbeslut:
    tillaten: bool
    hinder: tuple[str, ...]


def kan_aktivera_auto_send(
    *,
    icp_ar_ifyllt: bool,
    business_context_ar_ifyllt: bool,
    avsandardoman: str | None,
) -> Aktiveringsbeslut:
    """Får den här tenanten sättas till `auto_send`?

    Tre förutsättningar, och alla tre är samma fråga i olika form: vet vi
    tillräckligt för att ett mejl som går ut UTAN mänsklig granskning ska bli
    rätt?

    * **ICP** — utan urvalskriterier vet agenten inte vem som ska kontaktas,
      och "alla" är svaret som gör produkten till skräppost.
    * **Produktbeskrivning** — utan `business_contexts` skriver modellen
      generisk AI-text om ett erbjudande den gissat sig till. Se
      `MissingBusinessContextError` i leads_agent.
    * **Avsändardomän** — utan egen domän går utskicket från fel avsändare,
      och avregistreringslänken pekar på någon annans varumärke.

    Returnerar HINDER, inte bara ett nej. En kund som får "det går inte" utan
    att veta vad som saknas hör av sig till oss i stället för att fylla i
    fältet.
    """
    hinder: list[str] = []
    if not icp_ar_ifyllt:
        hinder.append(
            "Målgruppen (ICP) är tom. Utan urvalskriterier finns ingen gräns för "
            "vilka bolag agenten kontaktar."
        )
    if not business_context_ar_ifyllt:
        hinder.append(
            "Produktbeskrivningen saknas. Ett utskick grundat på en tom "
            "produktbeskrivning blir generisk AI-text."
        )
    if not (avsandardoman or "").strip():
        hinder.append(
            "Avsändardomänen är inte ifylld. Utskicket skulle gå från fel "
            "avsändare och avregistreringslänken peka på fel varumärke."
        )
    return Aktiveringsbeslut(tillaten=not hinder, hinder=tuple(hinder))


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
        "auto_send": (
            "Agenten skickar självt, även uppföljningar. Kräver ifylld målgrupp, "
            "produktbeskrivning och egen avsändardomän — och de tre första "
            "utskicken granskas ändå manuellt."
        ),
    }[level]
