"""Leads-pipelinen live: research -> outreach-utkast, för Snajps EGEN tenant.

Körs via `python scripts/run_live_tests.py --leads --modes disabled,enabled`.

Vad som körs (2026-08-08, efter per-steg-migreringen):
  3 riktiga svenska bolag x 2 thinking-lägen = 6 fulla pipelinekörningar,
  varje körning = 8 research-steg + 4 outreach-steg = 12 LLM-anrop.
  Totalt 72 skarpa anrop. Varje stegs KOMPLETTA utdata sparas.

Avsiktlig avgränsning mot 2026-08-07-versionen: den körde både en kund utan
onboarding (Nordlys Handel) och Snajp. Här körs bara Snajp-tenanten, för att
uppgiften är "marknadsför Snajps tjänster till tre bolag" — luckhanteringen
utan onboarding är en separat fråga med eget test
(tests/leads/test_onboarding_state.py).

Skickar ALDRIG något: utkasten hamnar i send_queue med status='queued'
(INV-SEC-004). Resultatet skrivs inkrementellt efter varje körning så att en
avbruten körning inte kastar bort det som redan kostat pengar.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

# Tre riktiga svenska bolag som matchar Snajps ICP (e-handel med en kundtjänst
# som får återkommande frågor). Publika företagswebbplatser — INV-DATA-002
# uppfylls genom att company_website alltid registreras som FÖRSTA källa.
PROSPECTS = [
    {
        "company_name": "Gina Tricot",
        "url": "https://www.ginatricot.com/se",
        "contact_email": "kundservice@ginatricot.com",
    },
    {
        "company_name": "Blomsterlandet",
        "url": "https://www.blomsterlandet.se",
        "contact_email": "kundservice@blomsterlandet.se",
    },
    {
        "company_name": "Sportamore",
        "url": "https://www.sportamore.se",
        "contact_email": "kundservice@sportamore.se",
    },
]

SNAJP_TENANT = "00000000-0000-4000-a000-000000000002"
SNAJP_CONTEXT = {
    "product_marketing": """# Snajp — produktmarknadsföring

## Vad vi säljer
AI-agenter för svensk kundsupport och B2B-leads. Två produkter:
1. Supportagenten — svarar kunder grundat ENBART i företagets egen
   kunskapsbas, eskalerar till människa när underlag saknas.
2. Leads-agenten — signalbaserad prospektresearch och lågmäld outreach.
   Aldrig massutskick.

## Vem det är för
Svenska små och medelstora bolag med en kundtjänst som drunknar i
återkommande frågor, och B2B-bolag som vill ha kvalificerade leads utan
att anställa en SDR.

## Vad som skiljer oss
- Svenska först. Agenten skriver svenska som en människa, inte översatt engelska.
- Grundningsregel: agenten hittar aldrig på. Saknas svar i kunskapsbasen
  eskalerar den i stället för att gissa.
- Kvalitet före kvantitet i outreach: 25 verifierade prospekt slår 250 dåliga.
- Kunden behåller sin egen hemsida — vi bygger chatten, inte sajten.

## Bevis
Livrustning (hjärtstartare och HLR-utbildning) kör supportagenten i drift.

## Ton
Lågmäld, specifik, inga superlativ. Vi lovar inte "revolutionerande AI".
""",
    "customer_research": """# Kundresearch — Snajps kunder

## Vanligaste problemen hos våra kunder
- Kundtjänsten svarar på samma fem frågor hela dagarna (leverans, retur,
  betalsätt, garanti, orderstatus).
- Svarstiderna växer i takt med volymen; kunden hinner bli irriterad först.
- Befintliga chatbottar hittar på svar, vilket kostar mer förtroende än de sparar.

## Vanliga invändningar
- "Vi har testat chatbot förr och den var värdelös." — nästan alltid en
  regelbaserad bot eller en generisk LLM utan grundning.
- "Vår verksamhet är för speciell." — kunskapsbasen ÄR det speciella;
  agenten läser bara deras egen.
- "Vi har inte tid att sätta upp det." — onboarding är sektionsvis, inte
  ett stort projekt.
- "Vad händer när den inte vet?" — den eskalerar. Det är designen, inte ett undantag.

## Var motståndet sitter
Kundtjänstchefen är rädd att bli av med kontrollen över tonen mot kund.
Därför är godkännandeflödet (utkast innan utskick) viktigare än autonomin.
""",
    "retention_playbook": """# Retentionsplaybook — Snajp

## Godkända åtgärder vid missnöje
- Kostnadsfri genomgång av kunskapsbasen med en av våra (max 60 min).
- Paus av abonnemanget i upp till 2 månader, en gång per kund.
- Nedgradering till en mindre plan.

## Aldrig utan mänskligt godkännande
- Prisrabatt av något slag.
- Förlängd bindningstid mot rabatt.
- Kompensation eller återbetalning.

## Alltid till människa
- Ultimatum ("fixa detta annars säger vi upp").
- Hot om extern instans eller offentlig recension.
- Allt som rör avtalstext.
""",
}

PARTIAL_PATH = Path(__file__).resolve().parent.parent / "docs" / "live-tests" / "leads-partial.json"


async def _ensure_snajp_context(storage) -> None:
    for kind, content in SNAJP_CONTEXT.items():
        if not await storage.get_latest_context_doc(SNAJP_TENANT, kind=kind):
            await storage.save_context_doc(
                SNAJP_TENANT, kind=kind, content=content, source="snajp-egen-profil"
            )


async def _run_one(storage, tenant_id, tenant_name, spec, mode, context_pack) -> dict:
    from app.agent.leads_agent import run_outreach_draft, run_research_step
    from app.config import get_settings

    os.environ["THINKING_MODE"] = mode
    get_settings.cache_clear()

    record = {"prospect": spec["company_name"], "thinking_mode": mode, "tenant": tenant_name}

    prospect = await storage.create_prospect(
        tenant_id, company_name=spec["company_name"], contact_email=spec["contact_email"]
    )
    # INV-DATA-002: företagswebben registreras som FÖRSTA källa.
    await storage.create_prospect_source(
        tenant_id,
        prospect_id=prospect["id"],
        source_url=spec["url"],
        source_type="company_website",
        lawful_basis="Publikt tillgänglig företagsinformation (berättigat intresse)",
    )

    started = time.monotonic()
    try:
        research = await run_research_step(
            storage,
            tenant_id,
            prospect_id=prospect["id"],
            tenant_name=tenant_name,
            context_pack=context_pack,
            brief=(
                f"Researcha {spec['company_name']} ({spec['url']}) som prospekt för "
                f"{tenant_name}. Källmaterialet från deras webbplats är redan hämtat och "
                "ligger i kontexten — grunda analysen i det du faktiskt läser där. Bedöm "
                "om de är ett bra prospekt, vilka kundtjänstproblem de sannolikt har, och "
                "vilken vinkel ett första mejl borde ta."
            ),
        )
        record["research"] = research
        record["research_ms"] = int((time.monotonic() - started) * 1000)
    except Exception as error:  # noqa: BLE001 — en trasig körning ska rapporteras, inte döljas
        record["research_error"] = f"{type(error).__name__}: {error}"
        return record

    thread_id = f"thread-{prospect['id']}"
    storage.outreach_threads.setdefault(tenant_id, {})[thread_id] = {
        "id": thread_id,
        "language_state": "sv",
        "last_inbound_at": None,
        "prospect_email": spec["contact_email"],
    }

    started = time.monotonic()
    try:
        draft = await run_outreach_draft(
            storage,
            tenant_id,
            thread_id=thread_id,
            prospect_email=spec["contact_email"],
            tenant_name=tenant_name,
            company_name=spec["company_name"],
            # Erbjudandet kommer nu från researchens mk:offers-steg i stället
            # för en hårdkodad sträng — hela poängen med att köra kedjan.
            offer_summary=research["offer_summary"],
            context_pack=context_pack,
            research_summary=research["final_output"],
            brief=(
                "Skriv ett kort, lågmält första mejl baserat på researchen. Konkret, "
                "ingen hype, inga superlativ, ren text. Köa det — skicka inte."
            ),
        )
        record["draft"] = draft
        record["draft_ms"] = int((time.monotonic() - started) * 1000)
        queued = [
            m
            for m in storage.outreach_messages.get(tenant_id, [])
            if m["thread_id"] == thread_id
        ]
        record["queued_message"] = queued[-1] if queued else None
    except Exception as error:  # noqa: BLE001
        record["draft_error"] = f"{type(error).__name__}: {error}"
    return record


async def run_leads(modes: list[str]) -> dict:
    from app.leads.context_pack import build_context_pack
    from app.storage.memory import MemoryStorage

    storage = MemoryStorage()
    await _ensure_snajp_context(storage)

    pack, missing = await build_context_pack(storage, SNAJP_TENANT)
    out: dict = {
        "tenant": "Snajp",
        "onboarding_missing": list(missing),
        "context_pack_chars": len(pack),
        "prospects": [p["company_name"] for p in PROSPECTS],
        "modes": modes,
        "snajp": {},
    }

    total = len(modes) * len(PROSPECTS)
    done = 0
    for mode in modes:
        for spec in PROSPECTS:
            done += 1
            key = f"{spec['company_name']}::{mode}"
            print(f"  [{done}/{total}] {key} ...", flush=True)
            started = time.monotonic()
            out["snajp"][key] = await _run_one(
                storage, SNAJP_TENANT, "Snajp", spec, mode, pack
            )
            print(f"      klart på {int(time.monotonic() - started)}s", flush=True)
            # Inkrementell skrivning: en avbruten körning kastar inte bort
            # det som redan kostat riktiga API-anrop.
            PARTIAL_PATH.parent.mkdir(parents=True, exist_ok=True)
            PARTIAL_PATH.write_text(
                json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
            )

    return out
