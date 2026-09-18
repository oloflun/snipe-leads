"""Faktagrinden för supportsvar: ett svar får inte påstå något kunskapsbasen
inte bär.

## Varför en grind och inte bara en instruktion

Utkaststeget instrueras redan att grunda sig ENBART i kunskapsbasen. Det är
en förhoppning. Leads fick samma lärdom den hårda vägen (INV-GROUND-001: en
uppfunnen procentsats på väg ut i Snajps namn), och en supportagent som hittar
på ett telefonnummer, en returfrist eller en avgift gör kunden en björntjänst
i tenantens namn. Grinden körs i KOD på den exakta text kunden ska få.

## Nivåerna (per kund, `support_regler.FAKTAKONTROLL`)

Ebbots tre nivåer, men verkställda deterministiskt mot kunskapsbasen i
stället för av en andra modell — noll extra LLM-anrop när svaret håller:

  * **tillatande** — kontaktuppgifter: telefonnummer, e-postadresser och
    webbadresser måste finnas i underlaget. Det är den hallucination som
    skadar mest (kunden ringer ett nummer som inte finns).
  * **forsiktig** (standard) — dessutom siffror, belopp och procent:
    leveranstider, avgifter, frister.
  * **strikt** — dessutom löftesord (gratis, återbetalning, ersättning,
    garanti, rabatt), superlativ och namngivna exempel som inte står i
    underlaget.

## Underlaget

Kunskapsbasens träffar plus kundens EGNA repliker i samtalet (ordernumret
kunden själv angav är inte en hallucination) och tenantens namn.
Affärskontexten ingår INTE — den är bakgrund, inte faktakälla, samma gräns
som prompten drar.

Extraktorn för siffror och löftesord är leads-grindens
(`leads/grounding_gate.py`): en extraktor, två riktningar, så att underlaget
och svaret aldrig normaliseras olika.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from ..leads.grounding_gate import build_permitted_facts, check_grounding

_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
_URL = re.compile(r"\b(?:https?://|www\.)[^\s<>()\"']+", re.IGNORECASE)
# Samma svenska telefonformat som leads-grinden maskar bort: 0771-123456,
# 08-123 45 67, +46 70 123 45 67.
_TELEFON = re.compile(r"(?:\+46[\s-]?|\b0)\d[\d\s-]{5,}\d")
# Numrerade listor ("1. Logga in") — siffran är en ordningsmarkör, inte ett
# påstående. Maskas innan sifferkontrollen.
_LISTMARKOR = re.compile(r"(?m)^\s*\d{1,2}[.)]\s")

_LOFTESORD = re.compile(
    r"\b(gratis|kostnadsfri\w*|fri\s+frakt|återbetal\w*|ersätt\w*|kompensation\w*|"
    r"garanti\w*|garanter\w*|rabatt\w*|pengarna\s+tillbaka)\b",
    re.IGNORECASE,
)

#: Siffror och belopp — det `forsiktig` kontrollerar ur leads-grindens fynd.
_SIFFERSLAG = ("number", "percent", "amount")


@dataclass(frozen=True)
class Faktadom:
    ok: bool
    #: Läsbara beskrivningar av det som saknar stöd, i fyndordning.
    ostodda: tuple[str, ...] = ()


def _telefonsiffror(text: str) -> str:
    siffror = re.sub(r"\D", "", text)
    return "0" + siffror[2:] if siffror.startswith("46") else siffror


def _doman(url: str) -> str:
    utan = re.sub(r"^(?:https?://)?(?:www\.)?", "", url.lower())
    return utan.split("/", 1)[0].rstrip(".,;:!?")


def _kontaktuppgifter(svar: str, underlag: str) -> list[str]:
    ostodda: list[str] = []
    kallor_mejl = {m.group(0).lower() for m in _EMAIL.finditer(underlag)}
    for m in _EMAIL.finditer(svar):
        if m.group(0).lower() not in kallor_mejl:
            ostodda.append(f"e-postadress: {m.group(0)!r}")

    kallor_domaner = {_doman(m.group(0)) for m in _URL.finditer(underlag)}
    kallor_domaner |= {m.group(0).split("@", 1)[1].lower() for m in _EMAIL.finditer(underlag)}
    for m in _URL.finditer(svar):
        if _doman(m.group(0)) not in kallor_domaner:
            ostodda.append(f"webbadress: {m.group(0)!r}")

    kallor_nummer = {_telefonsiffror(m.group(0)) for m in _TELEFON.finditer(underlag)}
    for m in _TELEFON.finditer(svar):
        if _telefonsiffror(m.group(0)) not in kallor_nummer:
            ostodda.append(f"telefonnummer: {m.group(0).strip()!r}")
    return ostodda


def kontrollera(
    svar: str,
    *,
    niva: str,
    kallor: Sequence[str],
    tenant_namn: str = "",
) -> Faktadom:
    """Håller svaret mot underlaget på kundens nivå?

    `kallor` är kunskapsbasens träfftexter och kundens egna repliker. En
    okänd nivå behandlas som `forsiktig` — standardvärdet, inte det
    tillåtande.
    """
    underlag = "\n".join(k for k in kallor if k)
    ostodda = _kontaktuppgifter(svar, underlag)

    if niva != "tillatande":
        fakta = build_permitted_facts(
            context_pack=underlag,
            research_evidence=(),
            offer_summary="",
            brief="",
            tenant_name=tenant_namn,
            company_name=tenant_namn,
        )
        # Kontaktuppgifterna är redan kontrollerade ovan, och listmarkörer
        # är inga påståenden — båda maskas med samma längd.
        maskerad = _LISTMARKOR.sub(lambda m: " " * len(m.group(0)), svar)
        dom = check_grounding(maskerad, fakta)
        for claim in dom.unsupported:
            if niva == "strikt" or claim.kind in _SIFFERSLAG:
                ostodda.append(claim.describe())

    if niva == "strikt":
        lagt = underlag.lower()
        for m in _LOFTESORD.finditer(svar):
            if m.group(0).lower() not in lagt:
                ostodda.append(f"löfte: {m.group(0)!r}")

    return Faktadom(ok=not ostodda, ostodda=tuple(ostodda))
