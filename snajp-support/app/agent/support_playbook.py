"""support/v1 — playbook-DEFINITIONEN (plan Del E).

Själva körningen ligger i app/agent/support_agent.py, som kör ETT LLM-anrop
per steg via app/agent/step_runner.py. Den här modulen deklarerar bara
kedjan och dess förvillkor.

Historik värd att känna till: en tidigare version renderade alla steg till
EN hopklistrad systemprompt (`render_support_instructions`). Den togs bort
— den gjorde läsgarantin overifierbar, eftersom man bara kunde se vad som
injicerats, aldrig vad modellen faktiskt använt. Förvillkorsgrinden
(`requires`) verkställs nu per steg vid själva anropet i step_runner.
"""

from __future__ import annotations

from ..agentcore.packs import Playbook, PlaybookStep

SUPPORT_V1 = Playbook(
    name="support/v1",
    steps=(
        PlaybookStep(skill="cs:ticket-triage", requires=("context_pack",)),
        PlaybookStep(skill="cs:customer-research", requires=("skill:cs:ticket-triage",)),
        PlaybookStep(skill="cs:draft-response", requires=("skill:cs:customer-research",)),
        # thinking PÅ, medvetet mot den globala AV-defaulten: det enda steget
        # där "ska detta till en människa?" avgörs. En felaktig eskalering
        # (åt endera hållet) är dyrare än den extra latensen. Beslut 2026-08-07.
        PlaybookStep(
            skill="cs:customer-escalation",
            requires=("skill:cs:draft-response",),
            thinking="enabled",
        ),
        PlaybookStep(skill="cs:kb-article", requires=("skill:cs:customer-escalation",)),
        # ÖPPEN FRÅGA: thinking-läge inte beslutat här. Triggas bara när
        # uppsägningsrisk redan är sann (dvs. ärendet eskalerar oavsett) —
        # kan höra ihop med cs:customer-escalation-beslutet ovan, men
        # användaren sa uttryckligen "vid eskalering" (singular) om
        # bedömningssteget. Fråga innan du sätter thinking="enabled" här.
        PlaybookStep(
            skill="snajp:retention-conversation",
            requires=("skill:cs:draft-response",),
            condition="cancellation_risk",
        ),
        PlaybookStep(skill="snajp:humanizer-svenska", requires=("skill:cs:kb-article",)),
    ),
)
