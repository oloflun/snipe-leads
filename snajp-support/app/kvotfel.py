"""Kvotfel mot AI-leverantören: två klasser, två sanningar, ett larm.

## Varför en egen modul

Ett 429 från Gemini betyder en av TVÅ helt olika saker, och systemet
behandlade dem länge som en:

  1. MINUT-/DYGNSKVOT — övergående. "Försök igen om en stund" är sant, och
     tålamod (step_runner.talamod_429) är rätt svar.
  2. KREDITSLUT — "Your prepayment credits are depleted". Permanent tills en
     människa fyller på i AI Studio. Att vänta hjälper aldrig, att be kunden
     försöka igen är vilseledande, och den enda rätta mottagaren av beskedet
     är VI — inte kunden.

Uppmätt 2026-09-08: krediterna tog slut i båda miljöerna, chatten sa "försök
igen om en stund", en leadskörning blev stående i processing, och råtexten
"Error code: 429 - [{'error': ...}]" läckte ordagrant till kundytan när ett
utkastjobb föll. Kunden var den som upptäckte driftstoppet.

Klassificeringen läser TEXT, inte undantagsklass — samma skäl som
events._ar_kvotfel: leverantörer byter undantagsklass och formulering, och
den här modulen ska varken dra in en LLM-klient eller gå sönder när SDK:n
uppgraderas. Markörerna är Googles egna ord ur det uppmätta svaret.
"""

from __future__ import annotations

import logging
from datetime import date

logger = logging.getLogger("snajp-support.kvotfel")

#: Googles egna formuleringar vid slut förskottskredit, ur det uppmätta
#: 429-svaret 2026-09-08. Gemener — jämförelsen casefoldar.
_KREDITMARKORER: tuple[str, ...] = (
    "prepayment credits",
    "credits are depleted",
    "billing#prepay",
)

#: Vad kunden ska läsa vid KREDITSLUT. Ingen uppmaning att försöka igen
#: (det hjälper inte förrän vi agerat) och ingen uppmaning att "kontrollera
#: planen" (kunden har ingen plan hos Google — det är vår). Larmet är
#: automatiskt, och att säga det är hela poängen: kunden ska veta att felet
#: redan är hos rätt människa.
KUNDTEXT_KREDITSLUT = (
    "AI-kapaciteten är slut hos oss för tillfället — det beror inte på ditt "
    "ärende, och inget du skickat har gått förlorat ur ditt konto. Vi har "
    "larmats automatiskt och fyller på."
)

#: Vad kunden ska läsa vid ÖVERGÅENDE kvottak. Här är "försök igen" sant.
KUNDTEXT_KVOT = (
    "AI-leverantörens kvot är slut just nu. Det är inte ett fel i ditt "
    "ärende — försök igen om en stund."
)


def ar_kvotfel(fel: Exception) -> bool:
    """Om felet är leverantörens kvottak (429-klassen) snarare än vårt fel."""
    if getattr(fel, "status_code", None) == 429:
        return True
    if type(fel).__name__ in ("RateLimitError", "ResourceExhausted"):
        return True
    text = str(fel)
    return "429" in text and ("quota" in text.lower() or "rate limit" in text.lower())


def ar_kreditslut(fel: Exception | str) -> bool:
    """Om felet (eller en redan lagrad feltext) är SLUT FÖRSKOTTSKREDIT.

    Markörerna är så specifika att de inte behöver 429:an bredvid sig — en
    lagrad jobbfeltext bär ofta bara leverantörens mening, inte statuskoden.
    """
    text = (fel if isinstance(fel, str) else str(fel)).casefold()
    return any(markor in text for markor in _KREDITMARKORER)


def kundtext_for(fel: Exception) -> str | None:
    """Den ärliga svenska meningen för ett kvotklassfel, eller None.

    None betyder "inte ett kvotfel — hantera som förut". Anroparen ska
    aldrig visa leverantörens råtext för en kund; diagnosen hör hemma i
    loggen och i platform_events.
    """
    if ar_kreditslut(fel):
        return KUNDTEXT_KREDITSLUT
    if ar_kvotfel(fel):
        return KUNDTEXT_KVOT
    return None


def oversatt_felstext(text: str | None) -> str | None:
    """Läsvägens skyddsnät: en LAGRAD feltext till kundvänlig svenska.

    Jobbfel skrivs på många ställen och lästes länge ut ordagrant —
    "Error code: 429 - [{'error': ...}]" nådde kundytan via
    GET /api/jobs/{id} (uppmätt i Leadslistors mejlruta 2026-09-11).
    Att översätta VID LÄSNING täcker varje sådan yta på en gång, gamla
    redan-lagrade fel inräknade. Ett fel som inte är kvotklassen passerar
    orört — den här funktionen får aldrig gömma en riktig diagnos.
    """
    if not text:
        return text
    if ar_kreditslut(text):
        return KUNDTEXT_KREDITSLUT
    if "429" in text and ("quota" in text.casefold() or "resource_exhausted" in text.casefold()):
        return KUNDTEXT_KVOT
    return text


async def larma_kreditslut(storage, *, tenant_id: str | None, kalla: str) -> None:
    """Larma OSS om kreditslut: platform_event + prioriterat mejl. Kastar aldrig.

    Nyckeln är dygnet, inte anropet: kreditslut träffar varje LLM-anrop i
    varje tenant samtidigt, och hundra larm om samma tomma kredit är ett
    larm ingen läser. Ett mejl per dygn räcker — händelseloggen bär
    frekvensen (samma rad, räknad), och `skicka_prioriterat` har dessutom
    sitt eget dubblettfönster under dygnsnyckeln.
    """
    try:
        from .api.events import log_event

        await log_event(
            storage,
            level="error",
            source=kalla,
            message="AI-krediterna är slut hos Google — alla agentanrop avvisas",
            tenant_id=tenant_id,
            detail={
                "klass": "kreditslut",
                "atgard": "Fyll på förskottskrediterna i ai.studio/projects. "
                "Tills dess avvisas varje modellanrop i alla agenter.",
            },
        )
    except Exception:  # noqa: BLE001 — larmet får aldrig skugga grundfelet
        logger.warning("kunde inte skriva kreditslut till platform_events")

    try:
        from .notifications.prioriterat_mejl import skicka_prioriterat

        await skicka_prioriterat(
            "AI-krediterna är slut — alla agenter står",
            tenant_id=tenant_id or "alla kunder",
            vad=(
                "Google avvisar varje modellanrop med 'prepayment credits are "
                "depleted'. Alla agenter (leads, support, bokföring) är utan "
                "kapacitet tills krediterna fylls på."
            ),
            varfor=(
                "Förskottskrediten i AI Studio är förbrukad. Åtgärd: fyll på i "
                "ai.studio/projects och överväg auto-påfyllning — kunden ska "
                "aldrig vara den som upptäcker det här."
            ),
            lank="/admin/handelser",
            nyckel=f"kreditslut:{date.today().isoformat()}",
        )
    except Exception:  # noqa: BLE001
        logger.warning("kunde inte skicka kreditslut-larmet")
