"""Live-entrypoints för leads-agenterna — EN LLM-KÖRNING PER SKILL-STEG,
samma arkitektur som app/agent/support_agent.py.

Varför den här filen skrevs om (2026-08-08): Fas B och C körde tidigare
`Runner.run(...)` med hela playbooken hopklistrad till en systemprompt. Det
gav exakt de fyra bristerna supportagenten hade före sin omskrivning:

  1. `thinking_kwargs()` anropades aldrig -> THINKING_MODE hade noll effekt,
     så en thinking-jämförelse mätte ingenting (upptäckt genom att latensen
     var identisk mellan lägena där support visade 6x skillnad)
  2. inget `step_log`, inga `reasoning_tokens`, ingen `agent_runs`-loggning (G10)
  3. inget utdatakontrakt per steg (Del C p.4)
  4. `skills_used` listade DEKLARERADE skills, aldrig använda

Nu: ett JSON-anrop per playbook-steg via `step_runner.run_step`, och
SIDOEFFEKTERNA (skrapning, köa utkast, eskalera) görs i KOD här — inte av
modellen via verktyg. Modellen resonerar, koden agerar.

Följdändring: skrapningen sker i kod FÖRE första steget i stället för via
`scrape_registered_source` som modellverktyg. Samma allowlist-garanti gäller
(`_scrape_registered_source_impl` kontrollerar fortfarande URL:en mot
prospect_sources), men nu kan ett steg inte längre "glömma" att hämta
underlaget — G4 blir en kodväg i stället för ett hopp om att modellen
anropar verktyget.

Fas A (onboarding) kör MEDVETET kvar på Runner.run: det är ett
flerturssamtal med kunden, inte en kedja av envägssteg, och per-steg-
kontrakt passar inte den formen. Konsekvens: Fas A saknar fortfarande
thinking-kontroll och step_log. Se docs/THINKING_MODE_COMPARISON.md §6.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from typing import Any

from agents import Agent, Runner

from ..agentcore.instruktioner import Instruktionslager, las_instruktioner
from ..agentcore.overlays import pack_version
from ..agentcore.packs import PlaybookStep, RunLedger
from ..config import get_settings
from ..leads.business_context import require_business_context
from ..leads.discovery import ar_privat_epost, ar_arbetsmejl, plocka_arbetsmejl
from ..leads.grounding_gate import PermittedFacts, build_permitted_facts, check_grounding
from ..leads.grounding_playbook import GROUNDING_V1
from ..leads.language_gate import last_humanizer_variant
from ..leads.onboarding_playbook import render_onboarding_instructions
from ..leads.outreach_playbook import OUTREACH_V1
from ..leads.research_playbook import RESEARCH_V1
from ..leads.soul import load_soul
from ..moderation.abuse_gate import check_abuse, ton_instruktion
from ..leads.text_delta import (
    SegmentShapeError,
    changed_segments,
    parse_humanized_segments,
    splice,
)
from ..leads.skatteverket import SkatteverketAtkomst
from .leads_context import OnboardingContext, OutreachContext, ResearchContext
from .leads_tools import (
    ONBOARDING_TOOLS,
    _queue_outreach_draft_impl,
    _request_human_handoff_impl,
)
from .llm import get_agent_model
from .research_tools import _scrape_registered_source_impl
from .step_runner import RunTrace, run_step
from .tools import strip_markdown

logger = logging.getLogger("snajp-support.leads-agent")

# Skrapat material kapas här. Ett steg som får 60 000 tecken råmarkdown
# lägger hela sin uppmärksamhet på sidfotslänkar; åtta steg som får det
# gör körningen dyr utan att bli bättre. Höj om researchen visar sig missa
# saker som ligger långt ned på sidan.
MAX_SOURCE_CHARS = 14_000

_RESEARCH_ROLE = "en svensk B2B-researchplaybook för ett enskilt prospekt"
_OUTREACH_ROLE = "en svensk playbook för ett kallt, lågmält första mejl"
_GROUNDING_ROLE = "en faktagranskning av ett färdigt svenskt mejlutkast"
_KUNSKAPSROLL = "en genomgång av vad ett avslutat researchvarv lärde oss"

#: Utkastuppgiften står som konstant för att omförsöket ska kunna skicka
#: EXAKT samma uppgift plus en tillsägelse. Två nästan lika strängar hade
#: glidit isär vid första ändringen.
_UTKASTSUPPGIFT = (
    "Skriv utkastet. Returnera JSON: subject (svenska, ren text), "
    "body (svenska, ren text, inga punktlistor), personalization_notes "
    "(vad i researchen mejlet faktiskt bygger på), draft_reasoning (svenska)."
)

#: Kunskapsfångsten efter ett avslutat researchvarv.
#:
#: Motsvarar supportens steg 5 (`cs:kb-article`) i IDÉ, inte i implementation:
#: support frågar om ETT ärende avslöjade en lucka i kunskapsbasen, det här
#: frågar om ett RESEARCHVARV avslöjade något om marknaden som kundens
#: kontextpaket och ICP inte bär. Det är två olika frågor mot två olika
#: dokument, och därför två steg och inte ett delat.
#:
#: `sa:call-summary` och inte `cs:kb-article`: skillen är skriven för att
#: destillera "vad lärde vi oss, vad gör vi med det" ur ett säljmoment, vilket
#: är precis formen här. cs:kb-article är skriven för att formulera en
#: supportartikel åt en slutkund.
#: `thinking="disabled"` sätts EXPLICIT, precis som varje steg i
#: research_playbook.py gör. Beslutet där är "thinking AV i hela leadsflödet"
#: (docs/THINKING_MODE_COMPARISON.md §8), och det gäller ett steg i flödet även
#: när steget deklareras här i stället för i playbooken. Att ärva
#: `settings.thinking_mode` hade gjort det här steget till det enda i leads vars
#: läge beror på en global default.
_RESEARCH_KUNSKAPSSTEG = PlaybookStep(
    skill="sa:call-summary",
    requires=("context_pack",),
    thinking="disabled",
)


# En avslutningsfras som slutar på komma och sedan inget mer. Uppstår när
# modellen skrev "[Signatur]"/"[Ditt namn]" och strip_placeholders (grinden
# från support-fixen) tog bort platshållaren — korrekt, men den lämnade
# hälsningen hängande. Hittat i 5 av 6 live-utkast 2026-08-09.
_DANGLING_SIGN_OFF = re.compile(
    r"(?:med\s+vänliga\s+hälsningar|vänliga\s+hälsningar|hälsningar|mvh|bästa\s+hälsningar)\s*,\s*$",
    re.IGNORECASE,
)


def sign_off(body: str, sender: str) -> str:
    """Sätter avsändarnamnet efter en hängande hälsningsfras.

    Att bara ta bort platshållaren räcker inte: ett kallt mejl som slutar
    "Med vänliga hälsningar," utan namn ser trasigt ut hos mottagaren, och
    det går ut i kundens namn. Grinden är i kod eftersom felet uppträder i
    BÅDA thinking-lägena — samma resonemang som strip_placeholders.
    """
    stripped = body.rstrip()
    if _DANGLING_SIGN_OFF.search(stripped):
        return f"{stripped}\n{sender}"
    return body
