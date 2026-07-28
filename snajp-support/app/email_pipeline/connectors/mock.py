"""Demoscenarier: realistiska svenska kundmail till ett bolag som säljer
hjärtstartare. Låter demon visa hela flödet utan en riktig inkorg.

Tre scenarier med olika syfte:
  blandat  — ett mail per fack, visar bredden i sorteringen
  teknik   — tekniska ärenden, visar hur nära besläktade frågor skiljs åt
  svara    — känsliga fall som ska eskaleras, visar säkerhetsspärrarna
"""

import uuid

from ..models import InboundAttachment, InboundEmail

# 1x1 röd PNG — giltig bild, minimal storlek. Exerciserar bilage- och vision-flödet.
_RED_PIXEL_PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _mail(batch: str, index: int, sender: str, name: str, subject: str, body: str, attachments=None):
    return InboundEmail(
        provider="mock",
        provider_message_id=f"mock-{batch}-{index}",
        from_email=sender,
        from_name=name,
        subject=subject,
        body_text=body,
        attachments=attachments or [],
    )


def _blandat(batch: str) -> list[InboundEmail]:
    return [
        _mail(
            batch, 1, "anna.lindqvist@vardcentralen.se", "Anna Lindqvist",
            "Hjärtstartaren piper och visar rött kryss",
            "Hej! Vår hjärtstartare i receptionen har börjat pipa och statusindikatorn "
            "visar ett rött kryss i stället för grön bock. Bifogar en bild på displayen. "
            "Vad behöver vi göra?",
            [InboundAttachment("display.png", "image/png", _RED_PIXEL_PNG, True, 68)],
        ),
        _mail(
            batch, 2, "johan.berg@brfsolsidan.se", "Johan Berg",
            "Täcks batteribyte av garantin?",
            "Hej, vi köpte vår hjärtstartare för tre år sedan och nu varnar den för "
            "batteriet. Ingår batteribyte i garantin eller får vi betala själva?",
        ),
        _mail(
            batch, 3, "sara.nystrom@industriab.se", "Sara Nyström",
            "Var är vår leverans?",
            "Vi beställde två väggskåp förra veckan och spårningen har inte uppdaterats "
            "på fyra dagar. När kan vi räkna med leverans?",
        ),
        _mail(
            batch, 4, "maria.ek@skolan.se", "Maria Ek",
            "HLR-utbildning för personalen",
            "Hej! Vi är 18 anställda och skulle vilja boka en utbildning i HLR med "
            "hjärtstartare. Har ni möjlighet att komma till oss, och hur lång tid tar "
            "en sådan genomgång?",
        ),
        _mail(
            batch, 5, "lars.strand@foretaget.se", "Lars Strand",
            "Fråga om faktura och referens",
            "Vi fick fakturan men vår inköpsreferens saknas, vilket gör att den fastnar "
            "i vårt system. Kan ni skicka en ny med referens INK-2291?",
        ),
        _mail(
            batch, 6, "peter.ohlsson@gymmet.se", "Peter Ohlsson",
            "Har min beställning gått igenom?",
            "Hej, jag lade en order i går kväll men har inte fått någon "
            "orderbekräftelse. Har den registrerats?",
        ),
    ]


def _teknik(batch: str) -> list[InboundEmail]:
    return [
        _mail(
            batch, 1, "drift@aldreboendet.se", "Karin Falk",
            "Självtestet misslyckas varje natt",
            "Vår enhet gör självtest varje natt och sedan i måndags misslyckas det. "
            "Felkoden som visas är E-04. Elektroderna byttes i våras.",
        ),
        _mail(
            batch, 2, "fastighet@kontorshuset.se", "Nils Ekström",
            "Beställa nya elektroder",
            "Vi behöver beställa nya elektroder till vår hjärtstartare. Utgångsdatumet "
            "har passerat. Vilken artikel passar modell HS-200?",
        ),
        _mail(
            batch, 3, "receptionen@hotellet.se", "Emma Sjögren",
            "Enheten startar inte alls",
            "Hjärtstartaren startar inte när man öppnar locket. Ingen lampa lyser. "
            "Den har suttit i skåpet orörd sedan installationen.",
        ),
        _mail(
            batch, 4, "vaktmastare@idrottshallen.se", "Tomas Berglund",
            "Hjärtstartaren tappades i golvet",
            "En av våra ledare råkade tappa hjärtstartaren från cirka en meters höjd. "
            "Den ser hel ut och visar grön bock. Kan vi lita på den eller behöver den "
            "kontrolleras?",
        ),
    ]


def _svara(batch: str) -> list[InboundEmail]:
    return [
        _mail(
            batch, 1, "erik.holm@foretaget.se", "Erik Holm",
            "Kräver återbetalning omgående",
            "Enheten vi köpte för två månader sedan fungerar inte och er support har "
            "inte svarat på en vecka. Helt oacceptabelt!! Jag kräver pengarna tillbaka "
            "omgående, annars kopplar jag in vår jurist.",
        ),
        _mail(
            batch, 2, "hr@storaforetaget.se", "Lena Dahl",
            "Hjärtstartaren användes vid en incident",
            "Vi hade en allvarlig incident på arbetsplatsen i går där vår hjärtstartare "
            "användes innan ambulansen kom. Vi behöver veta hur vi går vidare med "
            "enheten och om den kan användas igen.",
        ),
        _mail(
            batch, 3, "info@kunden.se", "Anonym Kund",
            "Radera våra uppgifter",
            "Vi vill att ni raderar samtliga personuppgifter ni har om oss och vår "
            "personal enligt GDPR. Bekräfta när det är gjort.",
        ),
        _mail(
            batch, 4, "curious@example.com", "Nyfiken Besökare",
            "Har ni öppet på midsommarafton?",
            "Hej! Undrar bara om ni har öppet i butiken på midsommarafton.",
        ),
    ]


SCENARIOS: dict[str, dict] = {
    "blandat": {
        "label": "Blandad inkorg",
        "description": "Ett ärende per fack — visar hur bredden sorteras.",
        "build": _blandat,
    },
    "teknik": {
        "label": "Tekniska ärenden",
        "description": "Snarlika tekniska frågor — visar hur nära fack skiljs åt.",
        "build": _teknik,
    },
    "svara": {
        "label": "Svåra fall",
        "description": "Återbetalning, incident och GDPR — visar eskaleringsspärrarna.",
        "build": _svara,
    },
}

DEFAULT_SCENARIO = "blandat"


def build_mock_emails(scenario: str = DEFAULT_SCENARIO) -> list[InboundEmail]:
    entry = SCENARIOS.get(scenario) or SCENARIOS[DEFAULT_SCENARIO]
    return entry["build"](uuid.uuid4().hex[:8])  # unika message-id per seedning


def list_scenarios() -> list[dict]:
    return [
        {"id": key, "label": value["label"], "description": value["description"]}
        for key, value in SCENARIOS.items()
    ]
