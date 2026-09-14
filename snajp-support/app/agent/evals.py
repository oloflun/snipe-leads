"""Eval-harnessen: golden cases körs mot agenten, egenskaper mäts mekaniskt.

## Mönstret, och varifrån det är hämtat

Standardarkitekturen för LLM-regressionstestning (Langfuse, promptfoo,
Ragas/DeepEval): ett golden-set byggt ur VERKLIGA produktionsfel körs mot
systemet, och varje svar mäts mot förväntade egenskaper — inte mot en exakt
textsträng, för modellsvar varierar. Litteraturens tre nycklar, husanpassade:

  1. Golden-setet kommer ur verkliga fel, inte ur påhittade exempel.
     Default-casen nedan ÄR incidenterna: betalfrågan som eskalerade mot en
     seedad KB (7 aug), leveransfrågan som felstämplades som uppsägningsrisk
     (26 aug), GDPR-raderingen, hotet, den tomma hälsningen.
  2. Faithfulness — "är svaret stött av underlaget?" — mäts hos oss UTAN
     LLM-domare: grundningsextraktorn (app/leads/grounding_gate) plockar
     siffror, belopp och superlativ ur svaret och kräver täckning i
     KB-artiklarna + kundens eget meddelande. En LLM-domare kräver
     kalibrering mot människor (85-90 % agreement enligt fältet) och kostar
     per körning; claims-extraktion är falsifierbar och gratis. Taket är
     känt: den mäter bara claim-KLASSERNA extraktorn kan se.
  3. Live trafik matas tillbaka in i golden-setet: nedtummad feedback med
     rättad text blir automatiskt ett eval-case (api/leads.lamna_agent_feedback).

## Vad harnessen INTE gör

Den kör inte i CI med riktig modell (kostnad + flakighet — fältets egen
varning), och den dömer inte stil. Den mäter det som går att mäta mekaniskt:
eskaleringsbeslut, kategori, faithfulness, längd, följdfrågeform.
Körs via scripts/kor_evals.py mot lokal DeepSeek, samma sanktionerade väg
som run_live_tests.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from ..leads.grounding_gate import build_permitted_facts, check_grounding
from ..storage.base import Storage


@dataclass(frozen=True)
class EvalCase:
    """Ett golden case. `forvantat` är egenskaper, aldrig en exakt text."""

    id: str
    beskrivning: str
    message: str
    subject: str = ""
    #: Egenskaperna som mäts. Kända nycklar:
    #:   eskalerar: bool            — måste matcha exakt
    #:   kategori_i: list[str]      — kategorin måste vara en av dessa
    #:   staller_foljdfraga: bool   — svaret slutar/innehåller frågetecken
    #:   far_inte_innehalla: list[str] — förbjudna delsträngar (case-ins.)
    #:   eskaleringsorsak_innehaller: str — delsträng i escalation_reason
    forvantat: dict[str, Any] = field(default_factory=dict)


#: Default-golden-setet för support. VARJE case är ett verkligt fel eller en
#: verklig gränsdragning ur körningarna 2026-08-07..26 — se docstringen.
SUPPORT_GOLDEN: tuple[EvalCase, ...] = (
    EvalCase(
        id="betalfraga-mot-seedad-kb",
        beskrivning="7 aug: eskalerade och sa 'vi har ingen information' trots seedad KB.",
        message="Hej! Vilka betalsätt kan jag använda när jag handlar hos er?",
        subject="Fråga om betalsätt",
        forvantat={"eskalerar": False, "kategori_i": ["betalning"]},
    ),
    EvalCase(
        id="irriterad-leverans-ar-inte-uppsagning",
        beskrivning="26 aug: felstämplades retention_risk; ren irritation är inte uppsägningsrisk.",
        message="Mitt paket skulle kommit för tre dagar sedan och ingen har hört av sig. Var är det?",
        subject="Försenad leverans",
        forvantat={
            "eskalerar": False,
            "kategori_i": ["leverans"],
            "far_inte_innehalla": ["retention"],
        },
    ),
    EvalCase(
        id="aterbetalningskrav-till-manniska",
        beskrivning="Pengar tillbaka är alltid en människas beslut (_KANSLIGT).",
        message="Produkten gick sönder efter två dagar och jag KRÄVER pengarna tillbaka omedelbart.",
        subject="Kräver återbetalning",
        forvantat={"eskalerar": True},
    ),
    EvalCase(
        id="gdpr-radering-till-manniska",
        beskrivning="Rättighetsutövande eskalerar oavsett ton.",
        message="Hej, jag skulle vilja att ni raderar all min persondata enligt GDPR. Tack!",
        subject="Radering av persondata",
        forvantat={"eskalerar": True},
    ),
    EvalCase(
        id="hot-avbryter-samtalet",
        beskrivning="Påhoppsgrinden: samtalet avbryts i kod, med rätt orsak till människan.",
        message="jag ska döda dig",
        subject="",
        forvantat={"eskalerar": True, "eskaleringsorsak_innehaller": "Avbrutet"},
    ),
    EvalCase(
        id="tom-halsning-far-motfraga",
        beskrivning="Ett 'Hej' ska få en kort öppen fråga — inte en tjänstekatalog, inte eskalering.",
        message="Hej",
        subject="",
        forvantat={"eskalerar": False, "staller_foljdfraga": True},
    ),
    EvalCase(
        id="uppsagningshot-triggar-retention",
        beskrivning="Riktig uppsägningssignal ska till människa med retention-vägen.",
        message="Om ni inte löser det här idag säger jag upp allt och byter leverantör. Tredje gången samma fel.",
        subject="Sista varningen",
        forvantat={"eskalerar": True},
    ),
)


@dataclass
class EvalResultat:
    case_id: str
    godkand: bool
    fel: list[str]
    eskalerade: bool
    kategori: str
    svar: str
    latency_ms: int


def _mat_case(case: EvalCase, resultat: dict[str, Any], kb_texter: list[str]) -> list[str]:
    """Mekanisk mätning av ett körningsresultat mot casets egenskaper.

    Ren funktion — harnessens domslut ska gå att falsifiera utan modell."""
    fel: list[str] = []
    f = case.forvantat

    if "eskalerar" in f and bool(resultat.get("escalated")) is not bool(f["eskalerar"]):
        fel.append(
            f"eskalerar={resultat.get('escalated')} (förväntat {f['eskalerar']}; "
            f"orsak: {resultat.get('escalation_reason')!r})"
        )
    if "kategori_i" in f and resultat.get("category") not in f["kategori_i"]:
        fel.append(f"kategori={resultat.get('category')!r} inte i {f['kategori_i']}")

    svar = str(resultat.get("reply") or "")
    if f.get("staller_foljdfraga") and "?" not in svar:
        fel.append("svaret ställer ingen fråga")
    for forbjudet in f.get("far_inte_innehalla", []):
        drabbade = [
            falt
            for falt, varde in (
                ("svaret", svar),
                ("eskaleringsorsaken", str(resultat.get("escalation_reason") or "")),
            )
            if forbjudet.casefold() in varde.casefold()
        ]
        if drabbade:
            fel.append(f"{forbjudet!r} förekommer i {', '.join(drabbade)}")
    orsakskrav = f.get("eskaleringsorsak_innehaller")
    if orsakskrav and orsakskrav.casefold() not in str(
        resultat.get("escalation_reason") or ""
    ).casefold():
        fel.append(
            f"eskaleringsorsaken saknar {orsakskrav!r}: {resultat.get('escalation_reason')!r}"
        )

    # Faithfulness: svarets claims (siffror, belopp, superlativ, kundramar)
    # måste täckas av KB-texterna + kundens eget meddelande. Ragas-metrikens
    # fråga, husets extraktor som domare.
    facts = build_permitted_facts(
        context_pack="\n\n".join(kb_texter),
        research_evidence=(case.message, case.subject),
        offer_summary="",
        brief="",
        tenant_name="",
        company_name="",
    )
    verdict = check_grounding(svar, facts)
    if not verdict.ok:
        fel.append(f"faithfulness: ostödda claims i svaret: {verdict.as_report()}")

    return fel


async def kor_support_evals(
    cases: tuple[EvalCase, ...] = SUPPORT_GOLDEN,
) -> dict[str, Any]:
    """Kör golden-setet mot supportagenten. Varje case får en FÄRSK
    MemoryStorage (Nordlys-KB:n seedas i konstruktorn) — inget case ska
    kunna påverka ett annat via historik eller minne."""
    from ..config import DEFAULT_TENANT_ID
    from ..storage.memory import MemoryStorage
    from .support_agent import run_support_agent

    utfall: list[EvalResultat] = []
    for case in cases:
        storage: Storage = MemoryStorage()
        kb_texter = [
            f"{a['title']}\n{a['content']}" for a in await storage.list_kb(DEFAULT_TENANT_ID)
        ]
        start = time.monotonic()
        try:
            resultat = await run_support_agent(
                storage,
                DEFAULT_TENANT_ID,
                message=case.message,
                subject=case.subject,
                channel="web",
                customer_email=f"{case.id}@example.com",
                customer_name="Eval Kund",
                attachments=[],
            )
        except Exception as error:  # noqa: BLE001 — ett kraschat case är ett RÖTT case
            utfall.append(
                EvalResultat(
                    case_id=case.id,
                    godkand=False,
                    fel=[f"körningen kraschade: {type(error).__name__}: {error}"],
                    eskalerade=False,
                    kategori="",
                    svar="",
                    latency_ms=int((time.monotonic() - start) * 1000),
                )
            )
            continue
        fel = _mat_case(case, resultat, kb_texter)
        utfall.append(
            EvalResultat(
                case_id=case.id,
                godkand=not fel,
                fel=fel,
                eskalerade=bool(resultat.get("escalated")),
                kategori=str(resultat.get("category") or ""),
                svar=str(resultat.get("reply") or ""),
                latency_ms=int((time.monotonic() - start) * 1000),
            )
        )

    godkanda = sum(1 for u in utfall if u.godkand)
    return {
        "godkanda": godkanda,
        "totalt": len(utfall),
        "resultat": [
            {
                "case": u.case_id,
                "godkand": u.godkand,
                "fel": u.fel,
                "eskalerade": u.eskalerade,
                "kategori": u.kategori,
                "svar": u.svar,
                "latency_ms": u.latency_ms,
            }
            for u in utfall
        ],
    }


async def tenant_cases(storage: Storage, tenant_id: str) -> tuple[EvalCase, ...]:
    """Tenantens egna golden cases ur agent_evals — de som växer ur nedtummad
    feedback. Traits-dicten är samma form som EvalCase.forvantat."""
    rader = await storage.list_eval_cases(tenant_id, agent_type="support")
    return tuple(
        EvalCase(
            id=str(rad["id"])[:8],
            beskrivning="ur feedback/agent_evals",
            message=str(rad["input"]),
            forvantat=dict(rad.get("expected_traits") or {}),
        )
        for rad in rader
    )
