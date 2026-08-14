"""INV-GROUND-001 — ett utkast med ostödda påståenden köas aldrig.

INCIDENTEN SOM MOTIVERAR MODULEN (2026-08-10, skarp körning):

Utkastet till Sportamore påstod att en kund "minskat sina återkommande frågor
med 30 procent inom 30 dagar". Kontextpaketet innehöll noll procentsiffror —
verifierat programmatiskt. Siffran var inte en felformulering, den var
uppfunnen för att den lät bra, och mejlet var på väg ut i Snajps namn.

`strip_placeholders` tar mallrester. Ingen grind tog ogrundade påståenden.

KONSTRUKTIONEN:

`build_permitted_facts` kör SAMMA extraktor över källtexten som
`check_grounding` kör över mejlet. Ett påstående är stött omm dess
normaliserade form finns i den tillåtna mängden. En extraktor, två
riktningar — så kan de två sidorna inte glida isär.

Grinden RETURNERAR ett verdikt i stället för att kasta (som
check_cold_outreach_gate, inte som check_provenance): anroparen behöver
listan över ostödda påståenden för att kunna be modellen reparera just dem.

VAD SOM MEDVETET INTE KONTROLLERAS — se `ponytail:`-kommentarerna nedan:
  * kvalificerardrift ("över 30 %" när källan säger "30 %")
  * utskrivna räkneord ("hälften", "dubbelt", "tre")
  * kausala påståenden ("vilket ledde till")
  * namngivna entiteter utanför de uppräknade ramarna
  * relativa tidsangivelser ("nyligen", "förra veckan")
Varje utökning kostar falsklarm, och en grind som brinner på varje mejl blir
en grind någon stänger av.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from .text_delta import split_sentences

# -- Maskering: siffror som aldrig är påståenden ---------------------------

_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_URL_RE = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)
# Svenska telefonformat: 0771-123456, 08-123 45 67, +46 70 123 45 67
_PHONE_RE = re.compile(r"(?:\+46[\s-]?|\b0)\d[\d\s-]{5,}\d")

# -- Talextraktion ---------------------------------------------------------

_APPROXIMATORS = (
    "över", "under", "ca", "cirka", "runt", "nästan", "upp till", "minst",
    "mer än", "mindre än", "drygt", "omkring", "upp emot",
)
_PERCENT_WORDS = ("procent", "procentenheter", "pct", "%")
_CURRENCY = {
    "kr": "SEK", "kronor": "SEK", "sek": "SEK",
    "€": "EUR", "eur": "EUR", "euro": "EUR",
    "$": "USD", "usd": "USD", "dollar": "USD",
}
_TIME_UNITS = ("minut", "minuter", "min", "kvart", "timme", "timmar")

# Tal + valfri enhet. Tusenavskiljare: vanligt blanksteg, NBSP, smalt NBSP, punkt.
_NUMBER_RE = re.compile(
    r"(?P<num>\d{1,3}(?:[   .]\d{3})+|\d+(?:[.,]\d+)?)"
    r"\s*(?P<unit>%|procentenheter|procent|pct|kronor|kr|SEK|EUR|euro|USD|dollar|€|\$)?",
    re.IGNORECASE,
)

# Matchas som DELSTRÄNG, med flit: svensk böjning gör "störst"/"största" och
# "bäst"/"bästa" till samma påstående, och en ordlista över varje böjningsform
# hade blivit lång och ändå ofullständig. Symmetrin räddar det — den tillåtna
# mängden byggs med samma delsträngsmatchning, så en källa som säger "största"
# tillåter ett utkast som säger "störst".
_SUPERLATIVES = frozenset(
    {
        "marknadsledande", "branschledande", "ledande", "störst", "bäst",
        "snabbast", "enda", "revolutionerande", "garanterar", "garanterat",
        "världsledande", "nummer ett", "överlägsen", "oslagbar",
    }
)

# Namngivna kundreferenser fångas BARA i uppräknade ramar. Alternativet —
# "varje versal token" — träffar Vi, Bolagsverket, prospektets egna
# produktnamn och veckodagar, och gör grinden oanvändbar på första körningen.
# Ramorden är skiftlägesokänsliga, NAMNET är det inte — därför scoped (?i:...)
# i stället för re.IGNORECASE på hela mönstret. Med global IGNORECASE matchade
# [A-ZÅÄÖ] även gemener, så "hjälpt Zalando med" fångade namnet "Zalando med".
_CUSTOMER_FRAMES = re.compile(
    r"(?i:kunder\s+som|till\s+exempel|t\.ex\.|bland\s+andra|såsom|exempelvis|"
    r"hjälpt|arbetar\s+med|case\s+hos|tillsammans\s+med|liknande\s+som)\s+"
    r"(?P<name>[A-ZÅÄÖ][\wÅÄÖåäö&-]*(?:\s+[A-ZÅÄÖ][\wÅÄÖåäö&-]*)?)",
    re.UNICODE,
)
# Versala ordsekvenser — används BARA för att bygga den tillåtna mängden.
_ENTITY_RE = re.compile(r"\b[A-ZÅÄÖ][\wÅÄÖåäö&-]*(?:\s+[A-ZÅÄÖ][\wÅÄÖåäö&-]*)?")


@dataclass(frozen=True)
class Claim:
    kind: str  # "number" | "percent" | "amount" | "named_customer" | "superlative"
    raw: str
    normalized: str
    span: tuple[int, int]

    def describe(self) -> str:
        return f"{self.kind}: {self.raw!r}"


@dataclass(frozen=True)
class PermittedFacts:
    numbers: frozenset[str]
    entities: frozenset[str]
    superlatives: frozenset[str]
    source_labels: tuple[str, ...]


@dataclass(frozen=True)
class GroundingVerdict:
    ok: bool
    unsupported: tuple[Claim, ...] = ()

    def as_report(self) -> list[str]:
        return [claim.describe() for claim in self.unsupported]


def _mask_non_claims(text: str) -> str:
    """Ersätter e-post, URL:er och telefonnummer med lika många blanksteg.

    Lika många — offsets måste förbli giltiga, annars pekar en Claim.span på
    fel ställe i originaltexten."""
    out = text
    for pattern in (_EMAIL_RE, _URL_RE, _PHONE_RE):
        out = pattern.sub(lambda m: " " * len(m.group(0)), out)
    return out


def normalize_number(raw: str, unit: str | None) -> str:
    """'1 200 kr' -> '1200SEK', '30 procent' -> '30%', '3,5' -> '3.5'.

    Normaliseringen är hela jämförelsenyckeln. Går den isär mellan de två
    riktningarna slutar grinden fungera utan att något test märker det —
    därför kör build_permitted_facts och check_grounding SAMMA funktion.
    """
    cleaned = unicodedata.normalize("NFKC", raw).strip()
    # Tusenavskiljare bort. Punkt räknas som avskiljare bara i 1.234-mönstret.
    cleaned = re.sub(r"(?<=\d)[   ](?=\d{3}\b)", "", cleaned)
    cleaned = re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", cleaned)
    cleaned = cleaned.replace(",", ".")  # svensk decimalkomma

    try:
        value = float(cleaned)
    except ValueError:
        return cleaned.lower()
    # 30.0 -> "30", 3.50 -> "3.5"
    text = f"{value:.10g}"

    suffix = ""
    if unit:
        key = unit.strip().lower()
        if key in _PERCENT_WORDS:
            suffix = "%"
        elif key in _CURRENCY:
            suffix = _CURRENCY[key]
    return f"{text}{suffix}"


def _extract_numbers(text: str) -> list[Claim]:
    claims: list[Claim] = []
    for match in _NUMBER_RE.finditer(text):
        unit = match.group("unit")
        normalized = normalize_number(match.group("num"), unit)
        kind = "number"
        if normalized.endswith("%"):
            kind = "percent"
        elif normalized[-3:] in ("SEK", "EUR", "USD"):
            kind = "amount"
        claims.append(
            Claim(
                kind=kind,
                raw=match.group(0).strip(),
                normalized=normalized,
                span=(match.start(), match.end()),
            )
        )
    return claims


def _is_meeting_ask(text: str, span: tuple[int, int]) -> bool:
    """'Har du 15 minuter nästa vecka?' — 15 finns aldrig i källorna, så utan
    det här undantaget brinner grinden på i praktiken VARJE kallt mejl.

    Frågevillkoret är det som gör undantaget säkert: 'Vi sparar 15 minuter per
    ärende.' är ett påstående och fångas fortfarande."""
    tail = text[span[1] : span[1] + 24].lower()
    if not any(unit in tail for unit in _TIME_UNITS):
        return False
    for start, end in split_sentences(text):
        if start <= span[0] < end:
            return text[start:end].rstrip().endswith("?")
    return False


def build_permitted_facts(
    *,
    context_pack: str,
    research_evidence: Sequence[str],
    offer_summary: str,
    brief: str,
    tenant_name: str,
    company_name: str,
) -> PermittedFacts:
    """Den tillåtna faktamängden.

    ponytail: kurerade evidence-citat, INTE hela den 14 000 tecken långa
    skrapningen. Ett snävare set ger fler falsklarm, men ett falsklarm kostar
    en reparationsrunda medan en falsk negativ kostar en påhittad siffra i
    kundens namn. Taket är valt med öppna ögon.
    """
    sources = [context_pack, offer_summary, brief, tenant_name, company_name]
    sources.extend(str(item) for item in research_evidence)
    blob = "\n".join(part for part in sources if part)

    numbers = {claim.normalized for claim in _extract_numbers(blob)}
    entities = {match.group(0).strip().lower() for match in _ENTITY_RE.finditer(blob)}
    entities.update({tenant_name.strip().lower(), company_name.strip().lower()})
    lowered = blob.lower()
    superlatives = {word for word in _SUPERLATIVES if word in lowered}

    labels = ["context_pack", "offer_summary", "brief"]
    if research_evidence:
        labels.append(f"research_evidence[{len(research_evidence)}]")
    return PermittedFacts(
        numbers=frozenset(numbers),
        entities=frozenset(entities),
        superlatives=frozenset(superlatives),
        source_labels=tuple(labels),
    )


def check_grounding(text: str, facts: PermittedFacts) -> GroundingVerdict:
    """Kontrollerar den EXAKTA text som ska köas, efter strip_markdown och
    sign_off. Inga positionsundantag för signaturen — tenant_name ligger i
    stället i den tillåtna mängden, vilket är enklare och har färre kanter."""
    masked = _mask_non_claims(text)
    unsupported: list[Claim] = []

    for claim in _extract_numbers(masked):
        if claim.normalized in facts.numbers:
            continue
        if _is_meeting_ask(masked, claim.span):
            continue
        unsupported.append(claim)

    # ponytail: kvalificerardrift ("över 30 %" när källan säger "30 %") passerar
    # medvetet — normalize_number strippar approximatorn, så magnituden är det
    # som jämförs. Att fånga driften kräver riktningsförståelse av källmeningen,
    # inte strängmatchning, och varje variant jag kan konstruera ger fler
    # falsklarm än fynd. Hanteras i prompt (overlays/leads-grounding-repair.md),
    # inte i grind. Taket känt och accepterat 2026-08-14.

    for match in _CUSTOMER_FRAMES.finditer(masked):
        name = match.group("name").strip()
        if name.lower() in facts.entities:
            continue
        unsupported.append(
            Claim(
                kind="named_customer",
                raw=name,
                normalized=name.lower(),
                span=match.span("name"),
            )
        )

    # ponytail: en påhittad kund utanför de uppräknade ramarna ("Ett av Sveriges
    # största modeföretag valde oss") passerar. Uppräknade ramar ÄR taket —
    # alternativet, att behandla varje versal ordsekvens som ett påstående,
    # träffar Vi/Bolagsverket/produktnamn och gör grinden oanvändbar.

    lowered = text.lower()
    for word in _SUPERLATIVES:
        if word in lowered and word not in facts.superlatives:
            position = lowered.index(word)
            unsupported.append(
                Claim(
                    kind="superlative",
                    raw=word,
                    normalized=word,
                    span=(position, position + len(word)),
                )
            )

    return GroundingVerdict(ok=not unsupported, unsupported=tuple(unsupported))
