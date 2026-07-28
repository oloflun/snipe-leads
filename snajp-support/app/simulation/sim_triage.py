"""Regelbaserad triage för simuleringsläget — anpassad för hjärtstartarbranschen.

Klassar ett kundmail i ett fack, uppskattar sentiment och avgör eskalering,
deterministiskt så att demon fungerar utan LLM-nyckel.

Till skillnad från en "första träffen vinner"-lista poängsätts ALLA kategorier.
Det ger två fördelar: rätt fack vinner även när flera nyckelord förekommer
(”min order av elektroder har inte levererats” är leverans, inte teknik), och
konfidensen kan härledas ur hur tydligt vinnaren slog tvåan i stället för att
sättas till ett påhittat fast värde.
"""

import re

from ..config import CATEGORY_LABELS

# (mönster, vikt). Höga vikter = starkt särskiljande för facket.
_CATEGORY_TERMS: dict[str, list[tuple[re.Pattern, float]]] = {
    "garanti": [
        (re.compile(r"garanti", re.I), 3.0),
        (re.compile(r"täcks av|omfattas av|gäller det för", re.I), 1.5),
        (re.compile(r"garantitid|garantivillkor|garantibevis|förlängd", re.I), 2.5),
        (re.compile(r"gått sönder efter|slutade fungera efter \w+ år", re.I), 1.5),
    ],
    "utbildning": [
        (re.compile(r"utbildning|kurs|kursdatum|instruktör|certifikat", re.I), 3.0),
        (re.compile(r"\bhlr\b|hjärt-?lungräddning|d-?hlr", re.I), 3.0),
        (re.compile(r"hur (använder|gör) man|hur fungerar|lära sig|träning|öva", re.I), 2.0),
        (re.compile(r"webbutbildning|genomgång|handhavande|introduktion", re.I), 2.0),
        (re.compile(r"manual|bruksanvisning|instruktionsfilm", re.I), 1.5),
    ],
    "teknisk_support": [
        (re.compile(r"fungerar inte|funkar inte|slutat fungera|startar inte", re.I), 2.5),
        (re.compile(r"felkod|felmeddelande|error|larmar|pip(ljud|ar)|blinkar", re.I), 3.0),
        (re.compile(r"självtest|statusindikator|indikator(lampa)?|display", re.I), 3.0),
        (re.compile(r"rött? (ljus|kryss)|grön(t)? (ljus|bock)", re.I), 2.0),
        (re.compile(r"batteri(et|varning|byte)?|elektrod(er|byte)?", re.I), 1.5),
        (re.compile(r"logga in|inloggning|lösenord|kontot", re.I), 2.0),
        # Efter skarp användning måste enheten kontrolleras innan den återgår i
        # beredskap — en teknisk fråga, även om mailet handlar om en incident.
        (re.compile(r"användes vid|efter (användning|larm)|kan den användas igen|"
                    r"tillbaka i (drift|beredskap)|kontrolleras", re.I), 2.5),
    ],
    "leverans": [
        (re.compile(r"leverans|levere|frakt|transport|spårning|spåra", re.I), 3.0),
        (re.compile(r"paket|försändelse|postnord|dhl|schenker|budbil|ombud", re.I), 2.5),
        (re.compile(r"försenad|inte kommit|när kommer|inte anlänt|kommit fram", re.I), 2.0),
        (re.compile(r"leveransadress|fraktkostnad|leveranstid", re.I), 2.0),
    ],
    "betalning": [
        (re.compile(r"faktur|betal|betalning|inbetalning", re.I), 3.0),
        (re.compile(r"moms|pris|offert|kostnad|avgift|belopp|kredit", re.I), 2.0),
        (re.compile(r"betalningsvillkor|förfallodatum|dröjsmål|påminnelse", re.I), 2.5),
        (re.compile(r"org(anisations)?\.?\s?nr|referens(nummer)?|bokföring", re.I), 1.5),
        (re.compile(r"dragits|debiterad?|dubbelt", re.I), 2.0),
    ],
    "retur_reklamation": [
        (re.compile(r"reklam(ation|era)|retur(nera)?|returrätt", re.I), 3.0),
        (re.compile(r"trasig|sönder|skadad|skadat|defekt|felaktig vara", re.I), 2.5),
        (re.compile(r"ångra|byta ut|vill lämna tillbaka|fel (vara|modell|artikel)", re.I), 2.0),
    ],
    "orderstatus": [
        (re.compile(r"orderstatus|orderbekräftelse|ordernummer", re.I), 3.0),
        (re.compile(r"(min|vår) (order|beställning)|har ni (fått|mottagit)", re.I), 2.5),
        (re.compile(r"gått igenom|bekräftelse på|status på", re.I), 2.0),
        (re.compile(r"beställa|lägga (en )?order|offert på", re.I), 1.5),
    ],
}

_ESCALATION_PATTERN = re.compile(
    r"återbetal|pengarna tillbaka|pengar tillbaka|kompensation|ersättning|skadestånd|"
    r"jurist|advokat|\barn\b|konsumentverket|anmäl|stäm(ma|ning)|juridisk|"
    r"radera (mitt |vårt )?konto|gdpr|personuppgift|"
    r"patient|dödsfall|olycka|incident|avled|larm(ade)? ambulans",
    re.I,
)

_NEGATIVE_PATTERN = re.compile(
    r"arg|förbannad|urusel|uselt?|skandal|oacceptabelt|besviken|frustrer|"
    r"trött på|aldrig mer|sämsta|katastrof|undermålig|!{2,}",
    re.I,
)

_POSITIVE_PATTERN = re.compile(
    r"tack så mycket|toppen|kanon|snabbt svar|nöjd|underbart|glad|uppskattar", re.I
)

# Subject-träffar väger tyngre — ämnesraden sammanfattar oftast ärendet.
_SUBJECT_WEIGHT = 2.0
_BODY_WEIGHT = 1.0


def _score_categories(subject: str, body: str) -> dict[str, float]:
    scores: dict[str, float] = {}
    for category, terms in _CATEGORY_TERMS.items():
        total = 0.0
        for pattern, weight in terms:
            if pattern.search(subject):
                total += weight * _SUBJECT_WEIGHT
            if pattern.search(body):
                total += weight * _BODY_WEIGHT
        if total:
            scores[category] = total
    return scores


def _confidence(top: float, second: float) -> float:
    """Konfidens ur signalstyrka och marginal till tvåan.

    Svag signal eller jämnt lopp mellan två fack ⇒ låg konfidens, vilket i sin
    tur hindrar autosvar (tröskeln är 0.75) och lyfter ärendet till granskning.
    """
    if top <= 0:
        return 0.35
    strength = min(top / 8.0, 1.0)          # mättar vid ~8 poäng
    margin = (top - second) / top            # 1.0 = ohotad vinnare
    return round(min(0.35 + 0.35 * strength + 0.30 * margin, 0.95), 2)


def classify(subject: str, body: str) -> dict:
    subject = subject or ""
    body = body or ""
    text = f"{subject}\n{body}"

    scores = _score_categories(subject, body)
    ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)

    if not ranked:
        category, confidence = "ovrigt", 0.35
        runner_up = None
    else:
        category = ranked[0][0]
        second = ranked[1][1] if len(ranked) > 1 else 0.0
        confidence = _confidence(ranked[0][1], second)
        runner_up = ranked[1][0] if len(ranked) > 1 else None

    sentiment = 0.5
    negative_hits = len(_NEGATIVE_PATTERN.findall(text))
    if negative_hits:
        sentiment = max(0.1, 0.4 - 0.1 * (negative_hits - 1))
    elif _POSITIVE_PATTERN.search(text):
        sentiment = 0.8

    escalation_match = _ESCALATION_PATTERN.search(text)
    escalate = bool(escalation_match) or sentiment < 0.3
    if escalation_match:
        escalation_reason = (
            f"Känsligt ärende ({escalation_match.group(0).lower()}) kräver mänsklig handläggare."
        )
    elif sentiment < 0.3:
        escalation_reason = "Kunden uttrycker stark frustration — lämnas till mänsklig handläggare."
    else:
        escalation_reason = None

    priority = "high" if escalate else ("normal" if category != "ovrigt" else "low")

    reasoning = (
        f"Nyckelordspoäng gav {CATEGORY_LABELS[category]}"
        + (f" före {CATEGORY_LABELS[runner_up]}" if runner_up else "")
        + f" (sentiment {round(sentiment, 2)})."
    )

    return {
        "category": category,
        "category_label": CATEGORY_LABELS[category],
        "sentiment": round(sentiment, 2),
        "confidence": confidence,
        "escalate": escalate,
        "escalation_reason": escalation_reason,
        "priority": priority,
        "runner_up": runner_up,
        "reasoning": reasoning,
    }
