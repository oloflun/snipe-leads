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

#: Googles egna formuleringar när modellanrop avvisas för att BETALNINGEN
#: saknas — inte för att takten är för hög. Gemener — jämförelsen casefoldar.
#:
#: Första raden är AI Studios förskottskredit (uppmätt 429-svar 2026-09-08).
#: Resten tillkom 2026-09-13 när miljön flyttade till Vertex AI (commit
#: b1a651e): där finns ingen förskottskredit, och ett tomt eller stängt
#: faktureringskonto svarar i stället 403 PERMISSION_DENIED med ErrorInfo-
#: orsaken BILLING_DISABLED ("This API method requires billing to be enabled"),
#: "The billing account for the owning project is disabled in state closed",
#: eller CONSUMER_SUSPENDED för ett avstängt projekt. Inget av dem är 429 —
#: ar_kvotfel såg dem aldrig, och chatten svarade med den GENERISKA "prova
#: igen"-meningen. Samma permanenta sanning, ny formulering. AI Studios
#: utgiftstak ("spending cap") hör hit av samma skäl: det släpper först när
#: en människa höjt taket eller månaden slagit om.
_KREDITMARKORER: tuple[str, ...] = (
    "prepayment credits",
    "credits are depleted",
    "billing#prepay",
    "billing_disabled",
    "billing to be enabled",
    "billing account for the owning project",
    "consumer_suspended",
    "has been suspended",
    "spending cap",
)

#: Hur djupt undantagskedjan (__cause__/__context__) följs. Ett omslaget fel
#: ("raise DiscoveryError(...) from fel", SDK-wrappers) bär leverantörens text
#: i orsaken, inte i sig själv. Taket skyddar mot cykliska kedjor.
_KEDJEDJUP = 5


def _kedja(fel: BaseException) -> list[BaseException]:
    """Felet och dess orsaker, närmast först."""
    sedda: list[BaseException] = []
    aktuell: BaseException | None = fel
    while aktuell is not None and len(sedda) < _KEDJEDJUP and aktuell not in sedda:
        sedda.append(aktuell)
        aktuell = aktuell.__cause__ or aktuell.__context__
    return sedda

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

#: Bokföringens uppladdning vid KREDITSLUT. Egen mening, inte KUNDTEXT_KREDITSLUT
#: plus ett tillägg: den allmänna texten lovar att "inget du skickat har gått
#: förlorat", och för ett kvitto som avvisades innan det sparades är det precis
#: fel besked — bytesen kastas per design (app/api/bookkeeping.py), så det
#: enda som hjälper kunden är att veta att filen måste laddas upp igen.
KUNDTEXT_KREDITSLUT_DOKUMENT = (
    "AI-kapaciteten är slut hos oss för tillfället — det beror inte på ditt "
    "dokument. Vi har larmats automatiskt och fyller på. Dokumentet sparades "
    "INTE: ladda upp det igen när tjänsten fungerar."
)

#: Bokföringens uppladdning vid ÖVERGÅENDE kvottak.
KUNDTEXT_KVOT_DOKUMENT = (
    "AI-leverantörens kvot är slut just nu — det beror inte på ditt dokument. "
    "Dokumentet sparades INTE: ladda upp det igen om en stund."
)


def ar_kvotfel(fel: Exception) -> bool:
    """Om felet är leverantörens kvottak (429-klassen) snarare än vårt fel.

    Följer undantagskedjan: ett kvotfel omslaget i ett eget undantag är
    fortfarande ett kvotfel. Vertex svarar på minutkvot med "Resource
    exhausted. Please try again later." utan ordet quota — därför räknas
    även RESOURCE_EXHAUSTED bredvid 429:an.
    """
    for led in _kedja(fel):
        if getattr(led, "status_code", None) == 429:
            return True
        if type(led).__name__ in ("RateLimitError", "ResourceExhausted"):
            return True
        text = str(led).casefold()
        if "429" in text and (
            "quota" in text
            or "rate limit" in text
            or "resource_exhausted" in text
            or "resource exhausted" in text
        ):
            return True
    return False


def ar_kreditslut(fel: BaseException | str) -> bool:
    """Om felet (eller en redan lagrad feltext) är KREDITSLUT: förskottskredit
    slut, fakturering avstängd, projekt avstängt eller utgiftstak nått.

    Markörerna är så specifika att de inte behöver statuskoden bredvid sig —
    en lagrad jobbfeltext bär ofta bara leverantörens mening. Undantag följs
    genom kedjan av samma skäl som i ar_kvotfel.
    """
    if isinstance(fel, str):
        texter = [fel]
    else:
        texter = [str(led) for led in _kedja(fel)]
    return any(markor in text.casefold() for text in texter for markor in _KREDITMARKORER)


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
    gemen = text.casefold()
    if "429" in text and (
        "quota" in gemen or "resource_exhausted" in gemen or "resource exhausted" in gemen
    ):
        return KUNDTEXT_KVOT
    return text


async def larma_kreditslut(
    storage,
    *,
    tenant_id: str | None,
    kalla: str,
    fel: BaseException | str | None = None,
) -> None:
    """Larma OSS om kreditslut: platform_event + prioriterat mejl. Kastar aldrig.

    Nyckeln är dygnet, inte anropet: kreditslut träffar varje LLM-anrop i
    varje tenant samtidigt, och hundra larm om samma tomma kredit är ett
    larm ingen läser. Ett mejl per dygn räcker — händelseloggen bär
    frekvensen (samma rad, räknad), och `skicka_prioriterat` har dessutom
    sitt eget dubblettfönster under dygnsnyckeln.

    `fel` följer med som ett kort utdrag i händelsens detail — INTERNT, aldrig
    till kunden. Sedan Vertex-flytten finns flera orsaker bakom samma klass
    (förskottskredit, avstängd fakturering, avstängt projekt), och den som
    ska åtgärda behöver veta vilken utan att gräva i Railways logg.
    """
    utdrag = None
    if fel is not None:
        utdrag = (fel if isinstance(fel, str) else f"{type(fel).__name__}: {fel}")[:400]
    try:
        from .api.events import log_event

        await log_event(
            storage,
            level="error",
            source=kalla,
            # "AI-krediterna är slut" står kvar ordagrant: lib/admin/handelsetext.ts
            # känner igen raden på just den frasen.
            message="AI-krediterna är slut hos Google — alla agentanrop avvisas",
            tenant_id=tenant_id,
            detail={
                "klass": "kreditslut",
                "atgard": "Vertex AI: kontrollera faktureringskontot och att "
                "projektet inte är avstängt (console.cloud.google.com/billing). "
                "AI Studio: fyll på förskottskrediterna i ai.studio/projects. "
                "Tills dess avvisas varje modellanrop i alla agenter.",
                "leverantorsutdrag": utdrag,
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
                "Google avvisar varje modellanrop av betalningsskäl (slut "
                "kredit, avstängd fakturering eller avstängt projekt). Alla "
                "agenter (leads, support, bokföring) är utan kapacitet tills "
                "det åtgärdats."
                + (f" Leverantörens svar: {utdrag}" if utdrag else "")
            ),
            varfor=(
                "Vertex AI: kontrollera faktureringskontot i "
                "console.cloud.google.com/billing. AI Studio: fyll på i "
                "ai.studio/projects och överväg auto-påfyllning — kunden ska "
                "aldrig vara den som upptäcker det här."
            ),
            lank="/admin/handelser",
            nyckel=f"kreditslut:{date.today().isoformat()}",
        )
    except Exception:  # noqa: BLE001
        logger.warning("kunde inte skicka kreditslut-larmet")
