"""Inkorgsflaggorna: offert-/prisförfrågan och utbildningsintresse.

## Varför vokabulär OCH modell, i förening med "eller"

Flaggan sätts om NÅGON av källorna säger ja: den deterministiska vokabulären
eller modellens bedömning (fältet i triage-JSON:en). Två oberoende vägar av
två skäl:

  * Simuleringsläget och den lokala stacken har ingen modell — vokabulären
    gör att flaggorna fungerar och går att testa deterministiskt där.
  * Modellen fångar formuleringar utan nyckelord ("hur mycket skulle det
    landa på för 40 personer?"), som en ordlista aldrig träffar.

En missad flagga kostar mer än en extra: flaggan är en sorteringshjälp i en
lista en människa ändå läser, inte ett automatiskt beslut. Därför "eller",
inte "och".

## Varför utbildningsorden ser ut som de gör

Mekanismen är generell (varje tenant får samma flaggor), men ordlistan får
gärna träffa brett: HLR, hjärtstartare och säkerhetsdag står med för att
pilotens kund säljer utbildningar i just det — och orden är ofarliga för en
tenant där de aldrig förekommer. Facket `utbildning` räknas alltid som
utbildningsintresse, oavsett ordval.
"""

from __future__ import annotations

import re
from typing import Any

#: Ord och fraser som betyder att avsändaren frågar efter pris eller offert.
#: Ordgränser där svenskan tillåter det — "kostar" ska träffa "vad kostar det"
#: men "pris" får inte träffa "prisad".
_OFFERTMONSTER = re.compile(
    r"""
    \boffert\w* |
    \bprisuppgift\w* |
    \bprisf[oö]rslag\w* |
    \bprisbild\w* |
    \bkostnadsf[oö]rslag\w* |
    \bkostar\b | \bkostnad\w* |
    \bvad\s+skulle\s+det\s+landa\s+p[aå]\b |
    \bpris(?:er|et|lista\w*)?\b |
    \brabatt\w*
    """,
    re.IGNORECASE | re.VERBOSE,
)

#: Ord som betyder intresse för utbildning.
_UTBILDNINGSMONSTER = re.compile(
    r"""
    \butbildning\w* |
    \bkurs(?:er|en|tillf[aä]lle\w*)?\b |
    \bworkshop\w* |
    \bhlr\b |
    \bhj[aä]rt-?lungr[aä]ddning\w* |
    \bhj[aä]rtstartare\b |
    \bs[aä]kerhetsdag\w* |
    \bf[oö]rsta\s+hj[aä]lpen\b |
    \bbrandutbildning\w*
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _text(subject: str, body: str) -> str:
    return f"{subject or ''} {body or ''}"


def ar_offertforfragan(subject: str, body: str, triage: dict[str, Any] | None = None) -> bool:
    """True om mejlet ber om pris/offert — vokabulär eller modellbedömning."""
    if triage and bool(triage.get("offertforfragan")):
        return True
    return bool(_OFFERTMONSTER.search(_text(subject, body)))


def ar_utbildningsintresse(
    subject: str, body: str, triage: dict[str, Any] | None = None
) -> bool:
    """True om mejlet uttrycker utbildningsintresse. Facket `utbildning`
    räknas alltid — ett mejl som klassats dit ÄR ett utbildningsärende."""
    if triage:
        if triage.get("category") == "utbildning":
            return True
        if bool(triage.get("utbildningsintresse")):
            return True
    return bool(_UTBILDNINGSMONSTER.search(_text(subject, body)))
