"""Triage-endpointen: sortera en batch mail i fack + skapa svarsutkast (synkron)."""

from fastapi import APIRouter, Depends, Request

from ..config import CATEGORY_LABELS, get_settings
from ..simulation.sim_triage import classify
from .deps import require_tenant
from .schemas import TriageRequest

router = APIRouter()

_SIM_ESCALATION_DRAFT = (
    "Hej!\n\nTack för ditt meddelande. Den här typen av ärende hanteras alltid av en av "
    "våra medarbetare. Jag har öppnat ett ärende med hög prioritet och skickat vidare all "
    "information — du får svar från vår kundtjänst inom en vardag.\n\nVänliga hälsningar,\n"
    "Snajp-Support"
)

_SIM_NO_MATCH_DRAFT = (
    "Hej!\n\nTack för att du hör av dig. Jag hittar inget säkert svar på din fråga i vår "
    "kunskapsbas och gissar aldrig — därför tar en kollega över ärendet och återkommer "
    "till dig så snart som möjligt.\n\nVänliga hälsningar,\nSnajp-Support"
)


async def _simulate_one(storage, tenant_id: str, email) -> dict:
    triage = classify(email.subject, email.body)
    articles = await storage.search_kb(tenant_id, f"{email.subject} {email.body}".strip())

    if triage["escalate"]:
        draft = _SIM_ESCALATION_DRAFT
    elif not articles:
        triage["escalate"] = True
        triage["escalation_reason"] = "Ingen träff i kunskapsbasen."
        draft = _SIM_NO_MATCH_DRAFT
    else:
        top = articles[0]
        draft = (
            f"Hej!\n\nTack för att du hör av dig om "
            f"{CATEGORY_LABELS[triage['category']].lower()}. Så här fungerar det hos oss:\n\n"
            f"{top['content']}\n\nHör gärna av dig om något är oklart!\n\n"
            "Vänliga hälsningar,\nSnajp-Support"
        )

    return {
        **triage,
        "draft_reply": draft,
        "kb_sources": [{"title": a["title"], "similarity": a["similarity"]} for a in articles],
        "simulation": True,
    }


@router.post("/api/triage")
async def triage(
    request: Request, payload: TriageRequest, tenant: dict = Depends(require_tenant)
) -> dict:
    settings = get_settings()
    storage = request.app.state.storage
    tenant_id = tenant["tenant_id"]
    results = []

    for email in payload.emails:
        if settings.is_simulation():
            result = await _simulate_one(storage, tenant_id, email)
        else:
            from ..agent.embeddings import embed_text
            from ..agent.triage import triage_email_llm

            embedding = await embed_text(f"{email.subject} {email.body}")
            articles = await storage.search_kb(
                tenant_id, f"{email.subject} {email.body}".strip(), embedding=embedding
            )
            result = await triage_email_llm(
                sender=email.sender, subject=email.subject, body=email.body,
                kb_articles=articles,
            )
            result["kb_sources"] = [
                {"title": a["title"], "similarity": a["similarity"]} for a in articles
            ]
            result["simulation"] = False
        results.append({"from": email.sender, "subject": email.subject, **result})

    return {"results": results}
