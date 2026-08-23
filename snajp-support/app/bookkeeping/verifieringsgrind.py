"""Grinden. En periodrapport visas aldrig som klar om den inte går ihop.

## Varför den returnerar ett verdikt i stället för att kasta

Samma val som `grounding_gate.check_grounding` och av samma skäl: anroparen
behöver LISTAN över brister för att kunna visa den för människan som ska
granska. Ett undantag ger ett stackspår, och ett stackspår är inte något en
enskild firma kan agera på.

Undantag från det: `math.till_decimal` kastar fortfarande. Skillnaden är att
en float i ett belopp är ett PROGRAMFEL — det ska stanna bygget, inte hamna i
en granskningskö.

## De två villkoren, och inga fler

Briefen namnger exakt två saker som ska fälla:

  1. debet och kredit går inte jämnt ihop
  2. ett underlag saknar ett fält beräkningen behöver

Fler villkor är frestande — rimlighetskontroll på belopp, dubblettdetektering,
periodiseringsvarningar — och varje sådant kostar falsklarm. En grind som
brinner på varje period är en grind någon stänger av. Samma resonemang som
står utskrivet i grounding_gate.

## Vad grinden ALDRIG gör

Den avrundar inte bort en differens, och den fyller inte i ett saknat belopp
med noll. Ett underlag utan momsfält är inte ett underlag med 0 kr moms —
det är ett underlag ingen har läst färdigt.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from .math import Konteringsrad, balans

#: Status som når vyn. `klar` betyder att rapporten får visas som färdig.
STATUS_KLAR = "klar"
STATUS_GRANSKA = "granska_manuellt"

#: Fälten en beräkning behöver för att kunna göras alls.
#:
#: `momssats` står med trots att den ofta går att gissa ur bruttot: en gissad
#: sats ger ett gissat momsbelopp, och det beloppet hamnar i en
#: momsdeklaration. `motpart` behövs inte för matten men krävs för att
#: verifikatet ska gå att spåra tillbaka till sitt underlag.
KRAVDA_FALT: tuple[str, ...] = ("datum", "motpart", "brutto", "momssats", "riktning")


@dataclass(frozen=True)
class Brist:
    #: Vad som saknas eller inte går ihop. Fältnamn, eller "balans".
    vad: str
    #: Skrivet för människan som ska granska, inte för oss.
    skal: str
    underlag_id: str = ""

    def __str__(self) -> str:
        prefix = f"{self.underlag_id}: " if self.underlag_id else ""
        return f"{prefix}{self.vad} — {self.skal}"


@dataclass(frozen=True)
class Verdikt:
    ok: bool
    brister: tuple[Brist, ...] = ()

    @property
    def status(self) -> str:
        return STATUS_KLAR if self.ok else STATUS_GRANSKA

    def as_report(self) -> list[str]:
        return [str(brist) for brist in self.brister]


def _saknas(varde: object) -> bool:
    """Tomt är tomt. `0` är däremot ett svar — 0 % moms är en giltig sats,
    och 0 kr är ett giltigt (om ovanligt) belopp."""
    if varde is None:
        return True
    if isinstance(varde, str) and not varde.strip():
        return True
    return False


def check_underlag(underlag: dict, *, underlag_id: str = "") -> Verdikt:
    """Har det här kvittot allt beräkningen behöver?

    Kastar inte på okända extrafält — ett underlag får bära mer än vi läser.
    """
    ident = underlag_id or str(underlag.get("id") or "")
    brister = [
        Brist(falt, "saknas i underlaget och kan inte räknas fram", ident)
        for falt in KRAVDA_FALT
        if _saknas(underlag.get(falt))
    ]

    riktning = underlag.get("riktning")
    if not _saknas(riktning) and riktning not in ("intakt", "kostnad"):
        brister.append(
            Brist("riktning", f"{riktning!r} är varken intäkt eller kostnad", ident)
        )

    # En kostnad utan kategori går inte att kontera. Kravet gäller BARA
    # kostnader: en intäkt konteras på momssatsen, som redan är ett krävt fält.
    if riktning == "kostnad" and _saknas(underlag.get("kategori")):
        brister.append(
            Brist("kategori", "kostnaden saknar kategori och kan inte konteras", ident)
        )

    return Verdikt(ok=not brister, brister=tuple(brister))


def check_verifikat(rader: Sequence[Konteringsrad], *, underlag_id: str = "") -> Verdikt:
    """Går debet och kredit ihop?

    Differensen står i skälet, inte bara att den finns: ett öre är
    avrundning och något att förstå, tusen kronor är fel konto.
    """
    if not rader:
        return Verdikt(
            ok=False,
            brister=(Brist("balans", "verifikatet har inga rader", underlag_id),),
        )

    diff = balans(rader)
    if diff != Decimal(0):
        return Verdikt(
            ok=False,
            brister=(
                Brist("balans", f"debet minus kredit är {diff} kr, inte 0", underlag_id),
            ),
        )
    return Verdikt(ok=True)


def check_period(
    *,
    underlag: Sequence[dict],
    verifikat: Sequence[Sequence[Konteringsrad]],
) -> Verdikt:
    """Hela periodens grind. Körs FÖRE rapporten visas som klar.

    Ett underlag utan verifikat fälls också: annars kan en post tyst falla ur
    rapporten och summan se rimlig ut ändå. Det är samma klass av fel som
    adminvyns nollställda men trovärdiga tal (STATUS.md, 2026-08-16) — och
    trovärdiga fel är värre än tomma.
    """
    brister: list[Brist] = []

    for post in underlag:
        brister.extend(check_underlag(post).brister)

    for rader in verifikat:
        brister.extend(check_verifikat(rader).brister)

    if len(verifikat) != len(underlag):
        brister.append(
            Brist(
                "tackning",
                f"{len(underlag)} underlag men {len(verifikat)} verifikat — "
                "något underlag saknar kontering",
            )
        )

    return Verdikt(ok=not brister, brister=tuple(brister))
