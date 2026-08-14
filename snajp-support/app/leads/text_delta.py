"""Meningsdelning, diff och splice för delta-humanisering.

VARFÖR DELTA OCH INTE OM-HUMANISERING AV HELA TEXTEN:

När grundningsgrinden fäller ett påstående repareras 1-2 meningar. Skickar vi
sedan HELA mejlet genom humanizern igen slår vi om röst, rytm och ordval i
text som redan passerat personalisering, granskning och humanisering — och
som en människa i förekommande fall redan godkänt. Reparationen skulle alltså
kosta mer kvalitet än den räddar.

Delta betyder: bara de meningar som faktiskt ändrades går genom humanizern,
resten är byte-för-byte orörd.

ANTIKORRUPTIONSEGENSKAPEN (läs den här innan du ändrar något):

`split_sentences` returnerar OFFSETS, inte strängar, och offsetsen täcker
hela texten utan luckor eller överlapp. Det gör att en felaktig delning bara
kan göra ett segment för stort eller för litet — den kan ALDRIG tappa eller
duplicera tecken. Och att tappa eller duplicera tecken är det enda felläget
som faktiskt korrumperar ett mejl som går ut i kundens namn.
"""

from __future__ import annotations

import difflib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

# Svenska förkortningar som slutar på punkt utan att avsluta en mening.
# Listan är kort med flit: en missad förkortning gör delta-enheten större
# (två meningar humaniseras i stället för en), inte trasig.
_ABBREVIATIONS = frozenset(
    {
        "bl.a", "t.ex", "d.v.s", "dvs", "m.m", "osv", "kl", "ca", "ev", "nr",
        "fr.o.m", "t.o.m", "s.k", "e.d", "m.fl", "st", "milj", "kr", "inkl",
        "exkl", "resp", "ang", "enl", "jfr", "obs", "p.g.a", "pga", "avd",
    }
)

# Meningsslut: skiljetecken + blanksteg + versal/siffra.
_BOUNDARY_RE = re.compile(r"([.!?…]+)(\s+)(?=[A-ZÅÄÖ0-9])")


class SegmentShapeError(RuntimeError):
    """Humanizern returnerade inte den indexmängd den fick."""


@dataclass(frozen=True)
class Segment:
    index: int
    span: tuple[int, int]
    text: str


def split_sentences(text: str) -> list[tuple[int, int]]:
    """(start, end)-offsets som TILLSAMMANS TÄCKER hela texten:

        ''.join(text[s:e] for s, e in split_sentences(text)) == text

    Den garantin är hela poängen — se modulens docstring.
    """
    if not text:
        return []

    cuts: list[int] = [0]
    for match in _BOUNDARY_RE.finditer(text):
        # Ordet före skiljetecknet — är det en förkortning är det ingen gräns.
        head = text[: match.start()]
        last_word = re.split(r"[\s(\[]", head)[-1].rstrip(".").lower()
        if last_word in _ABBREVIATIONS:
            continue
        # Inte mellan siffror (decimaltal, ordningstal: "3.5", "den 1. maj").
        if head[-1:].isdigit() and text[match.end() : match.end() + 1].isdigit():
            continue
        # Gränsen läggs EFTER blanktecknet, så blanktecknet tillhör det
        # föregående segmentet och ingenting hamnar mellan två segment.
        cuts.append(match.end())

    # Hård gräns vid blankrad — stycken är alltid egna enheter.
    for match in re.finditer(r"\n[ \t]*\n", text):
        cuts.append(match.end())

    cuts.append(len(text))
    ordered = sorted(set(cuts))
    spans = [(a, b) for a, b in zip(ordered, ordered[1:]) if b > a]
    return spans or [(0, len(text))]


def sentences(text: str) -> list[str]:
    return [text[a:b] for a, b in split_sentences(text)]


def changed_segments(before: str, after: str) -> tuple[Segment, ...]:
    """Segment ur `after` som skiljer sig från `before`.

    difflib.SequenceMatcher över MENINGSLISTOR, inte tecken: vi vill ha hela
    meningar som enheter, eftersom en humanizer som får en halv mening
    producerar nonsens. 'equal'-block rörs aldrig — det ÄR delta-egenskapen.
    """
    spans_after = split_sentences(after)
    list_before, list_after = sentences(before), [after[a:b] for a, b in spans_after]

    matcher = difflib.SequenceMatcher(a=list_before, b=list_after, autojunk=False)
    out: list[Segment] = []
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        if tag in ("replace", "insert"):
            for j in range(j1, j2):
                if list_after[j].strip():
                    out.append(Segment(index=j, span=spans_after[j], text=list_after[j]))
    return tuple(out)


def splice(text: str, replacements: Mapping[int, str]) -> str:
    """Ersätter segment via deras span, HÖGER TILL VÄNSTER.

    Riktningen är inte en stilfråga: ersätter man vänster till höger blir
    varje efterföljande offset ogiltig så fort en ersättning har annan längd
    än originalet, och resultatet blir tyst sönderklippt text.
    """
    spans = split_sentences(text)
    unknown = [i for i in replacements if i < 0 or i >= len(spans)]
    if unknown:
        raise SegmentShapeError(f"Okända segmentindex: {unknown} (finns {len(spans)}).")

    out = text
    for index in sorted(replacements, reverse=True):
        start, end = spans[index]
        original = text[start:end]
        # Bevara efterföljande blanktecken så meningar inte klistras ihop.
        trailing = original[len(original.rstrip()) :]
        out = out[:start] + replacements[index].rstrip() + trailing + out[end:]
    return out


def parse_humanized_segments(
    output: dict, expected: Sequence[Segment]
) -> dict[int, str]:
    """Läser humanizerns segments[] och kräver EXAKT den indexmängd den fick.

    Kontraktet är index-nycklat, inte positionellt: en modell som returnerar
    fyra segment när den fick tre går inte att splica positionellt utan att
    gissa vilket som hör vart, och en gissning här skriver fel text i ett
    mejl som går ut i kundens namn.
    """
    raw = output.get("segments")
    if not isinstance(raw, list):
        raise SegmentShapeError("Utdata saknar segments[] som lista.")

    got: dict[int, str] = {}
    for item in raw:
        if not isinstance(item, dict) or "index" not in item or "text" not in item:
            raise SegmentShapeError(f"Ogiltigt segment: {item!r}")
        index, value = item["index"], item["text"]
        if not isinstance(index, int) or not isinstance(value, str):
            raise SegmentShapeError(f"Segment med fel typer: {item!r}")
        if index in got:
            raise SegmentShapeError(f"Dubblerat segmentindex: {index}")
        got[index] = value

    wanted = {segment.index for segment in expected}
    if got.keys() != wanted:
        raise SegmentShapeError(
            f"Indexmängden stämmer inte. Väntade {sorted(wanted)}, fick {sorted(got)}."
        )
    return got
