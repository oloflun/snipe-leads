"""Regelbaserad triage för simuleringsläget.

Klassar ett kundmail i ett fack, uppskattar sentiment och avgör eskalering —
deterministiskt, så att demon fungerar utan OpenAI-nyckel.
"""

import re

from ..config import CATEGORY_LABELS

_CATEGORY_PATTERNS: list[tuple[str, re.Pattern]] = [
    (
        "retur_reklamation",
        re.compile(
            r"retur|reklam|trasig|sönder|skadad|skadat|defekt|ångra|byta|fel\s*(vara|storlek|färg)|gick sönder",
            re.IGNORECASE,
        ),
    ),
    # Leverans FÖRE betalning med flit: "vad kostar frakten" är en fraktfråga,
    # inte en betalningsfråga. Mönstren prövas i ordning och första träffen
    # vinner, så den som äger ordet "frakt" måste komma först.
    (
        "leverans",
        re.compile(
            r"leverans|levere|paket|försen|frakt|spårning|spåra|postnord|instabox|ombud|skicka(t|s)?\b|kommit fram|inte kommit|adress",
            re.IGNORECASE,
        ),
    ),
    (
        "betalning",
        re.compile(
            r"faktur|betal|drogs|dragning|debiter|kort(et|betalning)?\b|klarna|swish|belopp|avgift|kvitto"
            # "pris" fanns, men kunder skriver oftare "vad kostar" — utan detta
            # hamnade prisfrågor i ovrigt och besvarades ur en produktartikel.
            r"|pris|kostar|kostnad|offert|moms|dubbel|delbetal|ränta",
            re.IGNORECASE,
        ),
    ),
    (
        "orderstatus",
        re.compile(
            r"orderstatus|status på (min )?(order|beställning)|orderbekräftelse|bekräftelse på (min )?(order|beställning)|har min (order|beställning) gått igenom|när skickas (min )?(order|beställning)",
            re.IGNORECASE,
        ),
    ),
    (
        "teknisk_support",
        re.compile(
            r"fungerar inte|funkar inte|felkod|fel\s*meddelande|felmeddelande|logga in|inloggning|lösenord|krasch|bugg|hemsida|app(en)?\b|sidan|laddar|kassan|e-\d{3}"
            # Utrustningen, inte webbplatsen. En hjärtstartare som larmar eller
            # har utgångna elektroder hamnade tidigare i ovrigt och besvarades ur
            # en säljartikel — ett larm om trasig medicinteknisk utrustning måste
            # nå en människa.
            r"|larm(ar|et)?\b|blinkar|blinkande|piper|pipljud|indikator|självtest"
            r"|batteri|elektrod|gått ut|utgången|utgånget|går inte att starta|startar inte",
            re.IGNORECASE,
        ),
    ),
    (
        "garanti",
        re.compile(
            # "hjärtsäker zon"/"ss280000" låg här tidigare eftersom paketet har
            # egen garantitid — men det kapade varje fråga om vad Hjärtsäker zon
            # ÄR till garantifacket, och svaret kom då ur garantiartikeln.
            # Konceptet hör till ovrigt; garantitiden nämns i garantiartikeln.
            r"garanti|garantitid|garantin|tillverkningsfel|supportavtal",
            re.IGNORECASE,
        ),
    ),
    (
        "utbildning",
        re.compile(
            r"utbildning|kurs(en|er|tillfälle)?\b|hlr|första hjälpen|ehlr|eförstahjälpen|l-abcde|brandutbildning|släckövning|krisstöd|krishantering|deltagare|boka",
            re.IGNORECASE,
        ),
    ),
    # Kontofrågor (GDPR, personuppgifter) har ingen egen kategori i databasen och
    # hamnar i ovrigt. De eskaleras ändå via _ESCALATION_PATTERN nedan, så de
    # landar hos en människa oavsett fack.
]

_ESCALATION_PATTERN = re.compile(
    r"återbetal|pengarna tillbaka|pengar tillbaka|kompensation|ersättning|jurist|advokat|arn|konsumentverket|anmäl|stäm|juridisk|radera (mitt )?konto|gdpr",
    re.IGNORECASE,
)

_NEGATIVE_PATTERN = re.compile(
    r"arg|förbannad|urusel|uselt?|skandal|oacceptabelt|besviken|frustrer|trött på|aldrig mer|sämsta|katastrof|!{2,}|NU\b",
    re.IGNORECASE,
)

_POSITIVE_PATTERN = re.compile(r"tack så mycket|toppen|kanon|snabbt svar|nöjd|underbart|glad", re.IGNORECASE)


def classify(subject: str, body: str) -> dict:
    text = f"{subject}\n{body}"

    category = "ovrigt"
    for candidate, pattern in _CATEGORY_PATTERNS:
        if pattern.search(text):
            category = candidate
            break

    sentiment = 0.5
    negative_hits = len(_NEGATIVE_PATTERN.findall(text))
    if negative_hits:
        sentiment = max(0.1, 0.4 - 0.1 * (negative_hits - 1))
    elif _POSITIVE_PATTERN.search(text):
        sentiment = 0.8

    escalation_match = _ESCALATION_PATTERN.search(text)
    escalate = bool(escalation_match) or sentiment < 0.3
    if escalation_match:
        escalation_reason = f"Känsligt ärende ({escalation_match.group(0).lower()}) kräver mänsklig handläggare."
    elif sentiment < 0.3:
        escalation_reason = "Kunden uttrycker stark frustration — lämnas till mänsklig handläggare."
    else:
        escalation_reason = None

    priority = "high" if escalate else ("normal" if category != "ovrigt" else "low")

    return {
        "category": category,
        "category_label": CATEGORY_LABELS[category],
        "sentiment": round(sentiment, 2),
        "escalate": escalate,
        "escalation_reason": escalation_reason,
        "priority": priority,
    }
