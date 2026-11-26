"""Produktdatan som utskicket ska sälja — och grinden som kräver att den finns.

## Vems produkt mejlet handlar om

HYRESKUNDENS. Inte Snajps. Det är den vanligaste och dyraste förväxlingen i
den här produkten: en leads-agent som säljer sig själv i stället för kundens
erbjudande skickar ett mejl som är obegripligt för mottagaren och pinsamt för
kunden.

## Varför en tom produktbeskrivning stoppar körningen

En modell som får ett tomt underlag skriver inte ingenting — den skriver
något generiskt. "Vi hjälper företag som ert att effektivisera verksamheten"
är vad man får, och det är sämre än inget utskick alls: mottagaren har nu ett
intryck av kunden, och intrycket är att de skickar skräppost.

Därför är detta ett NAMNGIVET fel och inte en varning. En körning som avbryts
går att förklara för kunden. Ett generiskt mejl som redan gått iväg går inte
att ta tillbaka.

## Var datan faktiskt bor — och en avvikelse värd att veta om

`TENANTS.md` steg 5 säger att `business_contexts` ska fyllas för workspacet.
Den tabellen ligger i Postgres och läses av dashboarden (Next.js).

Backenden — den här tjänsten — läser inte den tabellen. Den läser
`context_docs` med `kind='product_marketing'`, vilket är vad
`build_context_pack` bygger paketet av och alltså vad agenten FAKTISKT ser.

De två är inte synkade. Grinden nedan står därför på den källa som styr
utfallet, inte på den som dokumentationen pekar ut. Avvikelsen noteras här
i stället för att jämkas ihop — samma disciplin som `TENANTS.md` föreskriver
för Livrustnings motstridiga garantitider.
"""

from __future__ import annotations

#: Under så här många tecken är beskrivningen i praktiken tom. Talet är satt
#: efter vad en användbar produktbeskrivning minst innehåller: vad ni säljer,
#: till vem och vad som skiljer er. Kortare än så går det inte att skriva ett
#: mejl på utan att gissa.
MINSTA_ANVANDBARA_LANGD = 120


class MissingBusinessContextError(RuntimeError):
    """Körningen avbröts därför att produktbeskrivningen saknas eller är för tunn.

    `kod` är en stabil kod som ytan översätter (lib/leads/suite.ts), när
    beskedet har en; texten är svensk, som resten av API:t."""

    def __init__(self, text: str, *, kod: str | None = None) -> None:
        super().__init__(text)
        self.kod = kod


#: Koden för en saknad eller för kort beskrivning av vad kunden säljer. Ytan
#: översätter den (lib/leads/felkoder.ts). Jobbposten bär bara texten, så
#: app/api/chat.py känner igen felet på inledningen nedan: båda beskeden
#: börjar med den, och det andra bär ett tal som varierar.
SAKNAR_BESKRIVNING = "saknar_beskrivning"
BESKRIVNING_INLEDNING = "Beskrivningen av vad ni säljer"


async def require_business_context(storage, tenant_id: str) -> str:
    """Returnerar produktbeskrivningen, eller höjer med ett begripligt fel."""
    doc = await storage.get_latest_context_doc(tenant_id, kind="product_marketing")
    innehall = ((doc or {}).get("content") or "").strip()

    if not innehall:
        # Texten visas för kunden som utkastets anteckning (draft_note). Förut
        # pekade den på product_marketing och TENANTS.md, som bara vi kan läsa.
        raise MissingBusinessContextError(
            f"{BESKRIVNING_INLEDNING} saknas, och utan den blir ett mejl "
            "bara allmän text. Fyll i den under Inställningar, Vad ni säljer, "
            "och kör sedan leadet igen.",
            kod=SAKNAR_BESKRIVNING,
        )

    if len(innehall) < MINSTA_ANVANDBARA_LANGD:
        raise MissingBusinessContextError(
            f"{BESKRIVNING_INLEDNING} är {len(innehall)} tecken, och det är "
            f"för lite att skriva ett mejl på (minst {MINSTA_ANVANDBARA_LANGD}). "
            "Skriv vad ni säljer, till vem och vad som skiljer er från andra, "
            "under Inställningar, Vad ni säljer.",
            kod=SAKNAR_BESKRIVNING,
        )

    return innehall


#: Koden för en tom produktlista. Ytan översätter den (lib/leads/suite.ts:
#: KUNDFELKODER); texten nedan är den svenska reserven.
SAKNAR_PRODUKT = "saknar_produkt"

#: Beskedet när produktlistan är tom. Produkterna ställs in under
#: Inställningar › Iris › Målgrupp och automation (IrisInstallningar).
EGEN_PRODUKT_SAKNAS = (
    "Iris vet inte vilken av era produkter mejlen ska sälja. Lägg till minst en "
    "produkt under Inställningar › Målgrupp och automation innan Iris skriver utkast."
)


async def require_egen_produkt(storage, tenant_id: str) -> list[dict[str, str]]:
    """Kundens produkter, eller ett begripligt fel när listan är tom.

    Kunddemon 2026-11-24: med tom produktlista valdes varken produkt eller
    erbjudande, och modellen lånade Snajps Supportagent ur skrivstilens
    exempel. Spärren går före modellen, så att körningen stannar innan
    research kostar något."""
    from ..agent.leads_research_v2 import las_produkter

    produkter = las_produkter(await storage.get_agent_settings(tenant_id, agent_type="leads"))
    if not produkter:
        raise MissingBusinessContextError(EGEN_PRODUKT_SAKNAS, kod=SAKNAR_PRODUKT)
    return produkter


def ar_ifyllt(innehall: object) -> bool:
    """Samma bedömning utan I/O. Används av auto_send-grinden."""
    return len(str(innehall or "").strip()) >= MINSTA_ANVANDBARA_LANGD
