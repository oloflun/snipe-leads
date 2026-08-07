"""Simuleringsläge för G8-demon. Motsvarar sim_agent.py:s roll för den
riktiga supportagenten, men utan NÅGON av de skrivningar G8 förbjuder —
inget find_or_create_customer, inget create_ticket, ingen save_message.
Bara ett deterministiskt, grundat svar ur demo-KB:n."""

from typing import Any

from ..config import PUBLIC_DEMO_TENANT_ID
from ..storage.base import Storage

_NO_MATCH_REPLY = (
    "Tack för din fråga! Jag hittar tyvärr inget säkert svar på just den i den här "
    "demons kunskapsbas. I en riktig installation skulle jag koppla in en kollega — "
    "men den här demon har ingen mänsklig kollega bakom sig."
)


async def run_demo_sim_agent(storage: Storage, *, message: str) -> dict[str, Any]:
    articles = await storage.search_kb(PUBLIC_DEMO_TENANT_ID, message)
    if not articles:
        reply = _NO_MATCH_REPLY
    else:
        top = articles[0]
        reply = f"{top['content']}\n\nHör gärna av dig igen om du har fler frågor om Snajp."
    return {
        "reply": reply,
        "kb_sources": [{"title": a["title"], "similarity": a["similarity"]} for a in articles],
        "skills_used": [],
        "demo": True,
        "simulation": True,
    }
