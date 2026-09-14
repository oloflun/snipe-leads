"""G8: publik, oautentiserad demoagent. Egen tenant (PUBLIC_DEMO_TENANT_ID),
strikt verktygsdelmängd (DEMO_TOOLS — inget kund-/ärendeskrivande verktyg,
inget sändverktyg), ingen bild/vision-sidovagn (ingen anledning att skicka
en besökares bild till en tredje part i ett smakprov).
"""

from typing import Any

from agents import Agent, Runner

from ..config import PUBLIC_DEMO_TENANT_ID
from ..moderation.maskering import maskera_personnummer
from ..storage.base import Storage
from .context import SupportContext
from .demo_playbook import render_demo_instructions
from .llm import get_agent_model
from .tools import DEMO_TOOLS


def build_demo_agent() -> tuple[Agent[SupportContext], list[str]]:
    instructions, ledger = render_demo_instructions()
    agent = Agent[SupportContext](
        name="Snajp-Support-Demo",
        instructions=instructions,
        model=get_agent_model(),
        tools=DEMO_TOOLS,
    )
    return agent, ledger.executed_order


async def run_demo_agent(storage: Storage, *, message: str) -> dict[str, Any]:
    agent, executed_skills = build_demo_agent()
    context = SupportContext(storage=storage, tenant_id=PUBLIC_DEMO_TENANT_ID, channel="web")

    # Samma maskering som triagen och support-agenten gör. Den publika demon
    # är en EGEN kodväg — den går varken via triage_email_llm eller
    # run_support_agent — och saknade därför maskeringen helt när den byggdes.
    #
    # Här finns ingen kunddata, besökaren skriver sin egen text. Men en
    # besökare som klistrar in sitt eget personnummer för att pröva agenten
    # ska inte få det skickat vidare, och en maskering som gäller överallt
    # utom på ett ställe är den sortens undantag ingen kommer ihåg.
    result = await Runner.run(
        agent,
        [{"role": "user", "content": [{"type": "input_text", "text": maskera_personnummer(message)}]}],
        context=context,
        max_turns=10,
    )

    reply = context.final_reply or str(result.final_output or "").strip()
    if not reply:
        reply = "Demoläget kunde inte formulera ett svar just nu — testa gärna igen."

    return {
        "reply": reply,
        "kb_sources": context.kb_sources,
        "skills_used": executed_skills,
        "demo": True,
    }
