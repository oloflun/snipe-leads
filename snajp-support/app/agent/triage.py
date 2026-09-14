"""Single-shot triage av mail för inkorg-demon (riktigt läge).

Klassar ett mail i ett fack och skriver ett svarsutkast i ett enda LLM-anrop —
lättviktigt jämfört med hela agent-loopen, avsett för batch-sortering.
"""

import json
from typing import Any

from ..config import CATEGORIES, CATEGORY_LABELS, get_settings
from ..moderation.maskering import maskera_personnummer
from .llm import get_llm_client

_TRIAGE_PROMPT = """Du är Snajp-Supports triagemotor. Klassificera kundmailet och
skriv ett svenskt svarsutkast. Om bilder bifogats: beskriv kort vad du ser i
"reasoning" och låt dem påverka fack och svar (felskärmdump → teknisk_support,
skadad vara → retur_reklamation). Svara ENBART med JSON:
{{
  "category": "teknisk_support|leverans|betalning|retur_reklamation|orderstatus|konto|ovrigt",
  "priority": "low|normal|high",
  "sentiment": 0.0-1.0,
  "confidence": 0.0-1.0,
  "escalate": true/false,
  "escalation_reason": "svensk motivering eller null",
  "reasoning": "kort svensk motivering av klassificeringen (inkl. vad ev. bilder visar)",
  "draft_reply": "komplett svenskt svarsutkast grundat ENBART i kunskapsbasen"
}}

Eskalera vid: återbetalning, juridik/ARN, GDPR/kontoradering, sentiment < 0.3.
Vid eskalering ska draft_reply vara ett artigt hållsvar. Hitta ALDRIG på fakta
som inte står i kunskapsbasen — sätt låg confidence och eskalera hellre.

Kunskapsbas (grunda svaret enbart i dessa fakta):
{kb}

Mail:
Från: {sender}
Ämne: {subject}

{body}"""


async def triage_email_llm(
    *,
    sender: str,
    subject: str,
    body: str,
    kb_articles: list[dict[str, Any]],
    image_urls: list[str] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    kb_text = "\n\n".join(f"### {a['title']}\n{a['content']}" for a in kb_articles) or "(tom)"
    # Personnummer maskeras INNAN texten lämnar huset. Innehållet i ett
    # supportmejl är okontrollerat, och hela texten går till modelleverantören
    # — se DPIA:ns R1. Maskeringen stänger inte risken, den gör den mindre.
    # Originalet ligger kvar i databasen; det är bara modellen som får en
    # maskerad kopia.
    prompt = _TRIAGE_PROMPT.format(
        kb=kb_text,
        sender=sender,
        subject=maskera_personnummer(subject),
        body=maskera_personnummer(body),
    )
    # Vision stöds bara av OpenAI-modellerna; DeepSeek (deepseek-chat) är textbaserad.
    content: str | list[dict[str, Any]] = prompt
    if image_urls and settings.llm_provider == "openai":
        content = [{"type": "text", "text": prompt}] + [
            {"type": "image_url", "image_url": {"url": url}} for url in image_urls[:3]
        ]
    elif image_urls:
        content = prompt + "\n\n[Bild bifogad — bildanalys stöds ej av nuvarande modell.]"
    response = await get_llm_client().chat.completions.create(
        model=settings.model,
        response_format={"type": "json_object"},
        temperature=0.3,
        messages=[{"role": "user", "content": content}],
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
        "confidence": float(data.get("confidence", 0.5)),
        "escalate": bool(data.get("escalate", False)),
        "escalation_reason": data.get("escalation_reason"),
        "reasoning": data.get("reasoning", ""),
        "draft_reply": data.get("draft_reply", ""),
    }
