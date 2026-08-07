"""G8: publik, oautentiserad demoagent. Egen tenant (PUBLIC_DEMO_TENANT_ID),
strikt verktygsdelmängd (DEMO_TOOLS — inget kund-/ärendeskrivande verktyg,
inget sändverktyg), ingen bild/vision-sidovagn (ingen anledning att skicka
en besökares bild till en tredje part i ett smakprov).
"""

from typing import Any

from agents import Agent, Runner

from ..config import PUBLIC_DEMO_TENANT_ID
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

    result = await Runner.run(
        agent,
        [{"role": "user", "content": [{"type": "input_text", "text": message}]}],
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
