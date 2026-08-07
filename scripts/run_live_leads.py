"""Leads-pipelinen live: onboarding -> prospekt -> research -> outreach-utkast.

Körs via run_live_tests.py --leads. Separat modul för att hålla filerna läsbara.

Kör HELA kedjan i båda thinking-lägena mot samma prospekt, så att outputen
går att jämföra rakt av. Skickar ALDRIG något — utkasten hamnar i send_queue
med status='queued' (INV-SEC-004).
"""

from __future__ import annotations

import os
import time

# Tre riktiga svenska bolag som matchar Snajps ICP (mindre e-handel/tjänste-
# bolag med kundtjänst). Publika företagswebbplatser — INV-DATA-002 uppfylls
# genom att company_website alltid registreras som första källa.
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

# Snajps egen profil (användarkrav: "skapa en egen profil för oss på Snajp").
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


async def _ensure_snajp_context(storage) -> None:
    for kind, content in SNAJP_CONTEXT.items():
        existing = await storage.get_latest_context_doc(SNAJP_TENANT, kind=kind)
        if not existing:
            await storage.save_context_doc(
                SNAJP_TENANT, kind=kind, content=content, source="snajp-egen-profil"
            )


async def _run_one(storage, tenant_id, tenant_name, prospect_spec, mode, context_pack) -> dict:
    from app.agent.leads_agent import run_outreach_draft, run_research_step
    from app.config import get_settings

    os.environ["THINKING_MODE"] = mode
    get_settings.cache_clear()

    record = {"prospect": prospect_spec["company_name"], "thinking_mode": mode}

    prospect = await storage.create_prospect(
        tenant_id,
        company_name=prospect_spec["company_name"],
        contact_email=prospect_spec["contact_email"],
    )
    # INV-DATA-002: företagswebben registreras som FÖRSTA källa.
    await storage.create_prospect_source(
        tenant_id,
        prospect_id=prospect["id"],
        source_url=prospect_spec["url"],
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
                f"Researcha {prospect_spec['company_name']}. Deras webbplats är "
                f"{prospect_spec['url']} och den är redan registrerad som källa — "
                "hämta den med scrape_registered_source och grunda din analys i "
                "det du faktiskt läser. Bedöm om de är ett bra prospekt för "
                f"{tenant_name}, vilka problem de sannolikt har, och vilken "
                "vinkel ett första mejl borde ta."
            ),
        )
        record["research"] = research
        record["research_ms"] = int((time.monotonic() - started) * 1000)
    except Exception as error:  # noqa: BLE001
        record["research_error"] = f"{type(error).__name__}: {error}"
        return record

    thread = {"id": None}
    try:
        thread_row = await storage.create_outreach_thread(tenant_id, prospect_id=prospect["id"])
        thread["id"] = thread_row["id"]
    except AttributeError:
        thread["id"] = f"thread-{prospect['id']}"
        storage.outreach_threads.setdefault(tenant_id, {})[thread["id"]] = {
            "id": thread["id"],
            "language_state": "sv",
            "last_inbound_at": None,
            "prospect_email": prospect_spec["contact_email"],
        }

    started = time.monotonic()
    try:
        draft = await run_outreach_draft(
            storage,
            tenant_id,
            thread_id=thread["id"],
            prospect_email=prospect_spec["contact_email"],
            tenant_name=tenant_name,
            company_name=prospect_spec["company_name"],
            offer_summary=(
                "Svensk AI-supportagent som svarar grundat i kundens egen "
                "kunskapsbas och eskalerar i stället för att gissa."
            ),
            context_pack=context_pack,
            brief=(
                "Skriv ett kort, lågmält första mejl baserat på researchen. "
                "Konkret, ingen hype, inga superlativ. Ren text. Köa det — "
                "skicka inte."
            ),
        )
        record["draft"] = draft
        record["draft_ms"] = int((time.monotonic() - started) * 1000)
        messages = storage.outreach_messages.get(tenant_id, [])
        queued = [m for m in messages if m["thread_id"] == thread["id"]]
        record["queued_message"] = queued[-1] if queued else None
    except Exception as error:  # noqa: BLE001
        record["draft_error"] = f"{type(error).__name__}: {error}"
    return record


async def run_leads(modes: list[str]) -> dict:
    from app.leads.context_pack import build_context_pack
    from app.storage.memory import MemoryStorage

    storage = MemoryStorage()
    await _ensure_snajp_context(storage)

    out = {"kunder": {}, "snajp": {}}

    # 1) Kundfallet: Nordlys Handel UTAN onboarding (användarens uttryckliga
    #    krav — pipelinen ska jobba med det den har, inte fastna).
    customer_tenant = "00000000-0000-4000-a000-000000000001"
    customer_pack, customer_missing = await build_context_pack(storage, customer_tenant)
    out["kund_onboarding_missing"] = list(customer_missing)
    for mode in modes:
        for spec in PROSPECTS:
            key = f"{spec['company_name']}::{mode}"
            print(f"  [kund] {key} ...", flush=True)
            out["kunder"][key] = await _run_one(
                storage, customer_tenant, "Nordlys Handel", spec, mode, customer_pack
            )

    # 2) Snajps egen pipeline MED fullständig profil.
    snajp_pack, snajp_missing = await build_context_pack(storage, SNAJP_TENANT)
    out["snajp_onboarding_missing"] = list(snajp_missing)
    for mode in modes:
        for spec in PROSPECTS:
            key = f"{spec['company_name']}::{mode}"
            print(f"  [snajp] {key} ...", flush=True)
            out["snajp"][key] = await _run_one(
                storage, SNAJP_TENANT, "Snajp", spec, mode, snajp_pack
            )

    return out
