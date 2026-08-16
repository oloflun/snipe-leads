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
Den tabellen ligger i Supabase och läses av dashboarden (Next.js).

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
    """Körningen avbröts därför att produktbeskrivningen saknas eller är för tunn."""


async def require_business_context(storage, tenant_id: str) -> str:
    """Returnerar produktbeskrivningen, eller höjer med ett begripligt fel."""
    doc = await storage.get_latest_context_doc(tenant_id, kind="product_marketing")
    innehall = ((doc or {}).get("content") or "").strip()

    if not innehall:
        raise MissingBusinessContextError(
            "Produktbeskrivningen saknas för den här kunden. Ett utskick grundat "
            "på en tom produktbeskrivning blir generisk AI-text, vilket är värre "
            "än inget utskick. Fyll product_marketing via onboarding-samtalet "
            "(och business_contexts för workspacet, se TENANTS.md steg 5) innan "
            "körningen startas om."
        )

    if len(innehall) < MINSTA_ANVANDBARA_LANGD:
        raise MissingBusinessContextError(
            f"Produktbeskrivningen är {len(innehall)} tecken lång, vilket är för "
            f"tunt för att skriva ett mejl på (minst {MINSTA_ANVANDBARA_LANGD} "
            "krävs). Den behöver säga vad kunden säljer, till vem och vad som "
            "skiljer dem från konkurrenterna."
        )

    return innehall


def ar_ifyllt(innehall: object) -> bool:
    """Samma bedömning utan I/O. Används av auto_send-grinden."""
    return len(str(innehall or "").strip()) >= MINSTA_ANVANDBARA_LANGD
