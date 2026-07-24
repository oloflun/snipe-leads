"""Single-shot triage av mail för inkorg-demon (riktigt läge).

Klassar ett mail i ett fack och skriver ett svarsutkast i ett enda LLM-anrop —
lättviktigt jämfört med hela agent-loopen, avsett för batch-sortering.
"""

import json
from typing import Any

from ..config import CATEGORIES, CATEGORY_LABELS, get_settings
from .llm import get_llm_client

_TRIAGE_PROMPT = """Du är Snajp-Supports triagemotor. Klassificera kundmailet och
skriv ett svenskt svarsutkast. Svara ENBART med JSON:
{{
  "category": "teknisk_support|leverans|betalning|retur_reklamation|konto|ovrigt",
  "priority": "low|normal|high",
  "sentiment": 0.0-1.0,
  "escalate": true/false,
  "escalation_reason": "svensk motivering eller null",
  "draft_reply": "komplett svenskt svarsutkast"
}}

Eskalera vid: återbetalning, juridik/ARN, GDPR/kontoradering, sentiment < 0.3.
Vid eskalering ska draft_reply vara ett artigt hållsvar.

Kunskapsbas (grunda svaret enbart i dessa fakta):
{kb}

Mail:
Från: {sender}
Ämne: {subject}

{body}"""


async def triage_email_llm(
    *, sender: str, subject: str, body: str, kb_articles: list[dict[str, Any]]
) -> dict[str, Any]:
    settings = get_settings()
    kb_text = "\n\n".join(f"### {a['title']}\n{a['content']}" for a in kb_articles) or "(tom)"
    response = await get_llm_client().chat.completions.create(
        model=settings.model,
        response_format={"type": "json_object"},
        temperature=0.3,
        messages=[
            {
                "role": "user",
                "content": _TRIAGE_PROMPT.format(
                    kb=kb_text, sender=sender, subject=subject, body=body
                ),
            }
        ],
    )
    data = json.loads(response.choices[0].message.content or "{}")
    category = data.get("category", "ovrigt")
    if category not in CATEGORIES:
        category = "ovrigt"
    return {
        "category": category,
        "category_label": CATEGORY_LABELS[category],
        "priority": data.get("priority", "normal"),
        "sentiment": float(data.get("sentiment", 0.5)),
        "escalate": bool(data.get("escalate", False)),
        "escalation_reason": data.get("escalation_reason"),
        "draft_reply": data.get("draft_reply", ""),
    }
