"""Gissningsgrinden: påståenden om mottagaren som bär gissningsord.

## Varför en kodgrind och inte bara overlay-regeln

Regeln finns i `leads-hard-rules` sedan 2026-08-26 — och EFTER-körningen
samma kväll visade att den är en riktning, inte en garanti: "lär ni få många
frågor" och "är det vanligt att kundtjänsten får" gick igenom, trots att
researchen just läst mottagarens egna sidor. Samma läxa som varje annan grind
i det här repot: en regel som bara står i en instruktion är en förhoppning.

## Vad som fälls, och vad som medvetet inte gör det

Ett GISSNINGSORD i en mening som handlar om MOTTAGAREN (ni/er/era/ert).
Båda villkoren krävs:

  * "Med den volymen lär ni få många frågor"      -> fälls (gissning om dem)
  * "Vi brukar börja med en kort genomgång"        -> fälls INTE (om oss)
  * "Sådana frågor brukar vara vanliga i handeln"  -> fälls INTE (branschen,
    inte mottagaren — svagt, men ett generiskt påstående är inte en
    felaktig utsaga om just dem)

Grinden RETURNERAR träffarna i stället för att kasta, precis som
grundningsgrinden: anroparen behöver meningarna för att kunna be modellen
reparera exakt dem — skriv om med researchens belägg, eller stryk.

# ponytail: ordlista + meningsregex; en NLI-klassificerare vore rikare men
# kostar ett LLM-anrop per utkast för att fånga det en regex tar gratis.
"""

from __future__ import annotations

import re

from .text_delta import split_sentences

#: Orden som gör ett påstående om mottagaren till en gissning. Speglar
#: förbudslistan i agent-core/overlays/leads-hard-rules.md — ändras den ena
#: ska den andra ändras i samma diff.
GISSNINGSORD = (
    "troligen",
    "brukar",
    "antagligen",
    "borde",
    "säkert",
    "sannolikt",
    "förmodligen",
    "vanligtvis",
    "lär",
    "som de flesta",
)

_GISSNING_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(o) for o in GISSNINGSORD) + r")\b",
    re.IGNORECASE,
)
#: Mottagarreferens. "ni/er/era/ert" som egna ord — "internationell" ska inte
#: träffa på "er" inuti ordet.
_MOTTAGARE_RE = re.compile(r"\b(?:ni|er|era|ert|hos\s+er)\b", re.IGNORECASE)
#: Avsändarreferens som friskriver meningen: "vi brukar" handlar om oss.
#: Bara när AVSÄNDAREN är subjektet före gissningsordet — grov heuristik:
#: "vi"/"jag" förekommer FÖRE gissningsordet i meningen.
_AVSANDARE_RE = re.compile(r"\b(?:vi|jag|oss|vår|våra|vårt)\b", re.IGNORECASE)


def check_gissningar(text: str) -> tuple[str, ...]:
    """Meningarna som gissar om mottagaren. Tom tuple = rent."""
    text = text or ""
    traffar: list[str] = []
    for start, slut in split_sentences(text):
        mening = text[start:slut]
        gissning = _GISSNING_RE.search(mening)
        if not gissning:
            continue
        if not _MOTTAGARE_RE.search(mening):
            continue
        avsandare = _AVSANDARE_RE.search(mening)
        # "Vi brukar visa er…" — avsändaren äger gissningsordet när den står
        # först. Mottagarordet senare i meningen gör den inte till en utsaga
        # OM mottagaren.
        if avsandare and avsandare.start() < gissning.start():
            continue
        traffar.append(mening.strip())
    return tuple(traffar)
