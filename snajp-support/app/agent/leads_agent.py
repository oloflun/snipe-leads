"""Live-entrypoints för leads-agenterna — samma mönster som
app/agent/support_agent.py: bygg instruktionerna genom förvillkorsgrinden
(Del C), konstruera en Agent med rätt verktygsdelmängd, kör EN agentisk
loop (Runner.run), returnera resultatet.

Fas B (research) fick sin skrapningsintegration efter att ha diskuterats
med användaren (ScrapeGraphAI, dubbelt allowlistad — se
app/agent/research_tools.py) i stället för att gissas fram.
"""

from typing import Any

from agents import Agent, Runner

from ..leads.onboarding_playbook import render_onboarding_instructions
from ..leads.outreach_playbook import render_outreach_instructions
from ..leads.research_playbook import render_research_instructions
from .leads_context import OnboardingContext, OutreachContext, ResearchContext
from .leads_tools import ONBOARDING_TOOLS, OUTREACH_TOOLS
from .llm import get_agent_model
from .research_tools import RESEARCH_TOOLS


def build_onboarding_agent(*, existing_product_marketing: str | None) -> tuple[Agent, list[str]]:
    instructions, ledger = render_onboarding_instructions(
        existing_product_marketing=existing_product_marketing
    )
    agent = Agent[OnboardingContext](
        name="Snajp-Leads-Onboarding",
        instructions=instructions,
        model=get_agent_model(),
        tools=ONBOARDING_TOOLS,
    )
    return agent, ledger.executed_order


async def run_onboarding_turn(storage, tenant_id: str, *, message: str) -> dict[str, Any]:
    """En tur i onboarding-samtalet (Fas A). Flerturssamtal — anropas en
    gång per kundmeddelande, precis som mk:product-marketing kräver
    ('frågor ställs sektion för sektion, aldrig alla på en gång')."""
    existing = await storage.get_latest_context_doc(tenant_id, kind="product_marketing")
    agent, executed_skills = build_onboarding_agent(
        existing_product_marketing=existing["content"] if existing else None
    )
    context = OnboardingContext(storage=storage, tenant_id=tenant_id)

    result = await Runner.run(
        agent,
        [{"role": "user", "content": [{"type": "input_text", "text": message}]}],
        context=context,
        max_turns=10,
    )

    reply = str(result.final_output or "").strip()
    return {
        "reply": reply,
        "done": context.done,
        "saved_docs": [d["kind"] for d in context.saved_docs],
        "skills_used": executed_skills,
    }


def build_research_agent(
    *, tenant_name: str, context_pack: str
) -> tuple[Agent, list[str]]:
    instructions, ledger = render_research_instructions(
        tenant_name=tenant_name, context_pack=context_pack
    )
    agent = Agent[ResearchContext](
        name="Snajp-Leads-Research",
        instructions=instructions,
        model=get_agent_model(),
        tools=RESEARCH_TOOLS,
    )
    return agent, ledger.executed_order


async def run_research_step(
    storage,
    tenant_id: str,
    *,
    prospect_id: str,
    tenant_name: str,
    context_pack: str,
    brief: str,
) -> dict[str, Any]:
    """Kör Fas B:s researchkedja för ETT prospekt. scrape_registered_source
    är det enda verktyget — kan bara läsa URL:er redan registrerade i
    prospect_sources för det här prospektet (se research_tools.py)."""
    agent, executed_skills = build_research_agent(tenant_name=tenant_name, context_pack=context_pack)
    context = ResearchContext(storage=storage, tenant_id=tenant_id, prospect_id=prospect_id)

    result = await Runner.run(
        agent,
        [{"role": "user", "content": [{"type": "input_text", "text": brief}]}],
        context=context,
        max_turns=15,
    )

    return {
        "scraped_sources": context.scraped_sources,
        "skills_used": executed_skills,
        "final_output": str(result.final_output or "").strip(),
    }


def build_outreach_agent(
    *, tenant_name: str, company_name: str, offer_summary: str, context_pack: str
) -> tuple[Agent, list[str]]:
    instructions, ledger = render_outreach_instructions(
        tenant_name=tenant_name,
        company_name=company_name,
        offer_summary=offer_summary,
        context_pack=context_pack,
    )
    agent = Agent[OutreachContext](
        name="Snajp-Leads-Outreach",
        instructions=instructions,
        model=get_agent_model(),
        tools=OUTREACH_TOOLS,
    )
    return agent, ledger.executed_order


async def run_outreach_draft(
    storage,
    tenant_id: str,
    *,
    thread_id: str,
    prospect_email: str,
    tenant_name: str,
    company_name: str,
    offer_summary: str,
    context_pack: str,
    brief: str,
) -> dict[str, Any]:
    """Kör Fas C: skriver ett utkast och köar det (aldrig skickar det
    direkt — INV-SEC-004). `brief` är den interna instruktionen till
    agenten om vad mejlet ska handla om (t.ex. vilken värdespak, se Del H)."""
    agent, executed_skills = build_outreach_agent(
        tenant_name=tenant_name,
        company_name=company_name,
        offer_summary=offer_summary,
        context_pack=context_pack,
    )
    context = OutreachContext(
        storage=storage, tenant_id=tenant_id, thread_id=thread_id, prospect_email=prospect_email
    )

    result = await Runner.run(
        agent,
        [{"role": "user", "content": [{"type": "input_text", "text": brief}]}],
        context=context,
        max_turns=10,
    )

    return {
        "queued": context.queued,
        "escalated": context.escalated,
        "escalation_reason": context.escalation_reason,
        "skills_used": executed_skills,
        "final_output": str(result.final_output or "").strip(),
    }
