"""Reparationsplaybooken (W5) — körs BARA när grundningsgrinden fäller.

VARFÖR DEN INTE ÄR TVÅ EXTRA STEG I OUTREACH_V1:

1. INV-LANG-002 kräver att humanizern är sista steget i den DEKLARERADE
   kedjan. Grindningen måste däremot köra EFTER humanizern — humanizern är
   det steg som mest sannolikt inför drift medan den "naturaliserar". De två
   kraven går inte att uppfylla i samma linjära kedja.
2. Reparationen är villkorad. Ett rent utkast ska kosta 4 LLM-anrop, inte 6.
   En playbook är en deklarerad sekvens, inte en if-sats.

Lösningen: OUTREACH_V1 förblir fyra steg, och den här playbooken körs från en
BUNDEN KODLOOP i run_outreach_draft efter dem. Ledgern bärs över, så
förvillkorsgrinden fortfarande bevisar ordningen — se `requires` på steg 1.
"""

from __future__ import annotations

from ..agentcore.packs import Playbook, PlaybookStep

# thinking AV i hela leadsflödet — se research_playbook.THINKING för beslutet.
from .research_playbook import THINKING

# Exakt EN reparationsrunda.
#
#   grind -> (faller) -> reparera -> delta-humanisera -> grind -> (faller) -> människa
#
# Tre skäl att inte loopa mer:
#   * varje runda är 2 LLM-anrop ovanpå en 4-stegs playbook (+50 %)
#   * klarade inte reparationen av med den påhittade siffran kommer samma
#     prompt inte göra det andra gången heller — då ska en människa titta
#   * en andra runda kan införa NYA påståenden, så grinden kan fälla på något
#     annat i runda två och loopen oscillerar i stället för att konvergera
MAX_GROUNDING_REPAIRS = 1

GROUNDING_V1 = Playbook(
    name="leads/grounding-v1",
    steps=(
        PlaybookStep(
            skill="mk:copy-editing",
            # ORDNINGSVILLKORET ÄR DEN HÄR RADEN. Grindningen får bara köra
            # efter humanizern, och det uttrycks i förvillkorsgrinden — inte i
            # en kommentar någon kan flytta på. Ledgern bärs över från
            # OUTREACH_V1, så nyckeln är satt först efter dess fjärde steg.
            requires=("skill:snajp:humanizer-svenska",),
            scope=("references/checklist.md", "§ Quick-Pass Editing Checks"),
            rationale=(
                "Reparationen är faktahygien på en färdig text, inte en omskrivning. "
                "Hela sjustegsmetodiken hade fått modellen att skriva om ett mejl som "
                "redan passerat personalisering, granskning och humanisering."
            ),
            overlay="leads-grounding-repair",
            thinking=THINKING,
        ),
        PlaybookStep(
            skill="snajp:humanizer-svenska",
            # Ny, distinkt ledgernyckel från steg 1 — alltså ett riktigt
            # villkor, inte ett som redan är uppfyllt av OUTREACH_V1.
            requires=("skill:mk:copy-editing",),
            overlay="leads-hard-rules",
            thinking=THINKING,
        ),
    ),
)
