"""Iris grundprompt: den som allt leadsarbete utgår från.

Texten bor i `agent-core/prompts/leads-systemprompt.md` (eller i en sparad
rad för agent_type 'leads', migration 099, när admin bakat in feedback i den).
Den här modulen fyller i `{{PLATSHÅLLARNA}}` och väljer avsnitt per steg, i
samma mönster som supportagentens `support_systemprompt.py`.

## Var den når modellen

Som `Instruktionslager.agent_md`, alltså i varje steg, före skillen och med en
avgränsare som säger att den gäller över skillen. Researchen får avsnitten om
källor, påhitt, målgrupp, kontakt och arbetsflöde. Utkastet får avsnitten om
källor, påhitt, kontakt, skrivregler, grundmallen och exemplen. Skälet är
kostnad: hela prompten i varje anrop är ett par tusen tokens för text steget
inte använder.

## Vad som INTE renderas in här (INV-SEC-009)

Bara VÅR text och företagsnamnet. Allt kundskrivet (affärskontext, produkter,
Iris-profil, röstdokument) ligger kvar i användarmeddelandet.
"""

from __future__ import annotations

import re
from datetime import datetime
from functools import lru_cache

from ..agentcore.registry import AGENT_CORE_ROOT
from .support_systemprompt import dagens_datum

PROMPT_FIL = AGENT_CORE_ROOT / "prompts" / "leads-systemprompt.md"

_OM_FILEN = re.compile(r"^> \*\*Om filen:\*\*.*\n+", re.MULTILINE)
_PLATSHALLARE = re.compile(r"\{\{([A-ZÅÄÖ_]+)\}\}")
_INSTALLNINGSBLOCK = re.compile(r"## Injicerade företagsinställningar\s*```.*?```", re.DOTALL)

#: Avsnitten per steg (rubrikprefix i filen).
STEG = {
    "research": ("## 1.", "## 2.", "## 3.", "## 4.", "## 5.", "## 6.", "## 7.", "## 8.", "## 9.", "## 11."),
    "utkast": ("## 1.", "## 2.", "## 3.", "## 4.", "## 6.", "## 9.", "## 10.", "## 11.", "## 12."),
}


class OkandPlatshallare(KeyError):
    """En `{{PLATSHÅLLARE}}` renderaren inte känner till. Hellre ett fel i
    testsviten än en rå `{{...}}` hos modellen."""


@lru_cache(maxsize=1)
def fil_mall() -> str:
    return PROMPT_FIL.read_text(encoding="utf-8")


def _avsnitt(text: str, prefix: tuple[str, ...]) -> str:
    delar = re.split(r"(?m)^(?=## )", text)
    huvud = delar[0].strip()
    valda = [d.strip().removesuffix("---").strip() for d in delar[1:] if d.startswith(prefix)]
    return "\n\n---\n\n".join([huvud, *valda])


def rendera(
    *, foretagsnamn: str, steg: str = "utkast", mall: str | None = None, nu: datetime | None = None
) -> str:
    """Grundprompten för `steg` ('research' eller 'utkast'), ifylld.

    `mall` är en sparad version (agent_global_instructions, agent_type
    'leads'); utan den gäller filen."""
    varden = {
        "FÖRETAGSNAMN": (foretagsnamn or "").strip() or "företaget",
        "DAGENS_DATUM": dagens_datum(nu),
    }

    def _byt(traff: re.Match[str]) -> str:
        if traff.group(1) not in varden:
            raise OkandPlatshallare(traff.group(1))
        return varden[traff.group(1)]

    text = _PLATSHALLARE.sub(_byt, _OM_FILEN.sub("", mall or fil_mall()))
    text = _INSTALLNINGSBLOCK.sub("", text).rstrip()
    return _avsnitt(text, STEG[steg])


def demo() -> None:
    utkast = rendera(foretagsnamn="Snajp", steg="utkast")
    research = rendera(foretagsnamn="Snajp", steg="research")
    assert "{{" not in utkast and "{{" not in research
    assert "## 10. Utkastet" in utkast and "## 10. Utkastet" not in research
    assert "## 7. Arbetsflöde" in research and "## 7. Arbetsflöde" not in utkast
    assert "Du är Iris, leadsagent för **Snajp**" in utkast
    assert "Injicerade företagsinställningar" not in utkast
    print("leads_systemprompt: ok", len(research), len(utkast))


if __name__ == "__main__":
    demo()
