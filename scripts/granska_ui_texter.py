#!/usr/bin/env python3
"""Skannar hårdkodade användarsynliga strängar efter kända språkfel.

Del av textkvalitetsarbetet 2026-10-03: kunder ska aldrig se stavfel, vare
sig i agenttext (det tar app/textkvalitet.py hand om i körtid) eller i
hårdkodad UI-text (det tar den här skannern hand om i testkörningen).

Vad den fångar — medvetet bara det som går att flagga utan brus:
- orden i den kurerade felstavningslistan (samma lista som körtidslagret)
- ersättningstecken (trasig teckenkodning)
- mellanslag före skiljetecken och dubbla mellanslag, i strängar som
  innehåller å/ä/ö (gränsen håller CSS-selektorer och regexar utanför)

Vad den INTE är: en fullständig svensk stavningskontroll. Svenskans fria
sammansättningar gör en ordlista mot LLM-text mest till brus — därför en
kurerad lista i stället, som växer varje gång ett nytt fel upptäcks.

Körning:  python scripts/granska_ui_texter.py   (exit 1 vid fynd)
Körs även av snajp-support/tests/test_ui_texter.py i ordinarie pytest.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "snajp-support"))

from app.textkvalitet import FELSTAVNINGAR  # noqa: E402

#: Kataloger med användarsynlig text. tests/ och node_modules/ med flera
#: utesluts i _ska_skannas.
SKANNAS = (
    "components",
    "app",
    "lib",
    "support-webb/components",
    "support-webb/lib",
    "snajp-support/app",
)

_UTESLUT_DELAR = {
    "node_modules", ".next", "__pycache__", "tests", "test", "dist",
    ".venv", "backend", "frontend", "databas",
}

# Stränglitteraler: "...", '...' och `...` (TS) respektive "..." (Python).
# Medvetet enkel — en lexer vore exaktare, men regexen räcker för att hitta
# ord och interpunktionsfel, och falsklarm är billiga att undanta.
_TS_STRANG = re.compile(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'|`((?:[^`\\]|\\.)*)`', re.DOTALL)
_PY_STRANG = re.compile(r'"""(.*?)"""|"((?:[^"\\\n]|\\.)*)"', re.DOTALL)

# "epost" är nästan alltid en identifierare (kolumnnamn, fältnamn) i kod —
# körtidslagret rättar den i löptext, men skannern skulle mest larma falskt.
_SKANNER_UNDANTAG = {"epost", "epostadress"}

#: Filer som själva BÄR felstavningslistan eller exempel på trasiga tecken.
_UNDANTAGNA_FILER = {
    "snajp-support/app/textkvalitet.py",
    "lib/textkvalitet.ts",
    "snajp-support/app/agent/research_tools.py",  # kommentar visar �-fallet
    "snajp-support/app/notifications/prioriterat_mejl.py",  # kolumnjusterat internlarm
}

_FELORD = re.compile(
    r"\b("
    + "|".join(re.escape(o) for o in FELSTAVNINGAR if o not in _SKANNER_UNDANTAG)
    + r")\b",
    re.IGNORECASE,
)

# Interpolationsuttryck i TS-mallsträngar är kod, inte text — ternärer som
# `${x ? "a" : "b"}` gav annars falska "mellanslag före skiljetecken".
_TS_INTERPOLATION = re.compile(r"\$\{[^{}]*\}")
_SVENSKT = re.compile(r"[åäöÅÄÖ]")
# Mellanslag före skiljetecken — men inte före "..." (avsiktlig paus) och
# inte procentfallet "50 %" som är korrekt svenska.
_FORE_SKILJETECKEN = re.compile(r"\S [,.;:!?](?:\s|$)")


def _ska_skannas(path: Path) -> bool:
    if any(del_ in _UTESLUT_DELAR for del_ in path.parts):
        return False
    return path.suffix in {".ts", ".tsx", ".py"} and not path.name.endswith(".d.ts")


def _stranger(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    monster = _PY_STRANG if path.suffix == ".py" else _TS_STRANG
    resultat: list[str] = []
    for match in monster.finditer(text):
        strang = next((g for g in match.groups() if g), "")
        if strang:
            # "X" i stället för tomt: `Hej ${namn}!` ska bli "Hej X!", inte
            # "Hej !" — annars larmar blankstegskontrollen på vår egen lucka.
            resultat.append(_TS_INTERPOLATION.sub("X", strang))
    return resultat


def granska() -> list[str]:
    fynd: list[str] = []
    for katalog in SKANNAS:
        bas = ROT / katalog
        if not bas.exists():
            continue
        for path in sorted(bas.rglob("*")):
            if not path.is_file() or not _ska_skannas(path):
                continue
            rel = path.relative_to(ROT)
            if rel.as_posix() in _UNDANTAGNA_FILER:
                continue
            for strang in _stranger(path):
                for traff in _FELORD.finditer(strang):
                    fynd.append(f"{rel}: felstavning {traff.group(0)!r} i {strang[:80]!r}")
                if "�" in strang:
                    fynd.append(f"{rel}: ersättningstecken i {strang[:80]!r}")
                # Blankstegskontrollerna gäller bara enradiga strängar med
                # å/ä/ö — flerradiga litteraler (docstrings, prompter) bär
                # indentering som inte är kundtext.
                # "${" kvar efter substitutionen = nästlad mallsträng som
                # tokeniseraren klippte mitt i; blankstegskontroll på ett
                # sådant fragment larmar på koden, inte texten.
                if _SVENSKT.search(strang) and "\n" not in strang and "${" not in strang:
                    if "  " in strang.strip():
                        fynd.append(f"{rel}: dubbelt mellanslag i {strang[:80]!r}")
                    if _FORE_SKILJETECKEN.search(strang):
                        fynd.append(
                            f"{rel}: mellanslag före skiljetecken i {strang[:80]!r}"
                        )
    return fynd


if __name__ == "__main__":
    # Windows-konsolen kör cp1252 som default — fynden innehåller å/ä/ö.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    alla = granska()
    for rad in alla:
        print(rad)
    print(f"\n{len(alla)} fynd.")
    sys.exit(1 if alla else 0)
