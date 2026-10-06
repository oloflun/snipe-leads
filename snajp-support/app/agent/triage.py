"""Single-shot triage av mail för inkorgen (riktigt läge).

Klassar ett mail i ett fack och skriver ett svarsutkast i ett enda LLM-anrop —
lättviktigt jämfört med hela agent-loopen, avsett för batch-sortering.

Sedan 2026-10-05 är supportagentens grundprompt (agent-core/prompts/
support-systemprompt.md) systemmeddelandet, och svaret följer dess avsnitt 11.
"""

import json
from typing import Any

from ..config import CATEGORIES, CATEGORY_LABELS, get_settings
from ..leads.untrusted_content import wrap_untrusted_content
from ..moderation.maskering import maskera_personnummer
from .llm import get_llm_client, tankande_kwargs
from .support_systemprompt import rendera

#: Uppgiften i användarmeddelandet. Grundprompten (agent-core/prompts/
#: support-systemprompt.md, via support_systemprompt.rendera) är systemmeddelandet
#: sedan 2026-10-05 och bär policyn: källor, beslut, eskalering, mallar och
#: avsnitt 11:s utdataformat. Här står bara det inkorgen behöver UTÖVER det.
_TRIAGE_PROMPT = """## Din uppgift
Klassa kundmejlet nedan och skriv svarsutkastet enligt grundprompten. Om
bilder bifogats: beskriv kort vad du ser i "reasoning" och låt dem påverka fack
och svar (felskärmdump → teknisk_support, skadad vara → retur_reklamation).

Svara med ETT JSON-objekt med grundpromptens fält ur avsnitt 11 (beslut,
kategori, känsloläge, brådskande, kundens_frågor, svarsutkast, intern_notering,
eskaleringsorsak) och dessutom:
  "priority": "low|normal|high",
  "sentiment": 0.0-1.0,
  "confidence": 0.0-1.0 (hur säker du är på att svarsutkastet kan gå ut som det är),
  "reasoning": "kort svensk motivering av klassificeringen (inkl. vad ev. bilder visar)",
  "offertforfragan": true/false,
  "utbildningsintresse": true/false

"kategori" är exakt en av: {kategorier}.
"offertforfragan" är true när avsändaren frågar efter pris, offert eller
kostnadsförslag — även utan ordet offert. "utbildningsintresse" är true när
mejlet uttrycker intresse för en utbildning, kurs eller liknande. Båda kan
vara true samtidigt, och de är oberoende av vilket fack du väljer.

Frågar mejlet efter pris, offert eller kostnadsförslag OCH kunskapsbasen
innehåller prisuppgifterna: strukturera svarsutkastet som ett kostnadsförslag —
vad som ingår, pris per post (exakt ur kunskapsbasen), villkor som moms och
giltighetstid om de framgår, och ett tydligt nästa steg. Använd företagets
uppgifter ur avsändarprofilen (organisationsnummer, hemsida) där de hör hemma
i ett kostnadsförslag. Saknar kunskapsbasen prisuppgifterna: ställ en motfråga
om det som behövs för en offert, eller eskalera (grundprompten 6.2–6.3).

Saknas källa för en del av mejlet och den delen INTE rör ett ämne i 6.3
(pengar tillbaka, fakturafel, juridik, GDPR, säkerhet, kris, arg kund):
beslutet är DELVIS. Svara på det du har källa för, säg rakt ut vilken uppgift
du inte har, och skriv att kunden kan svara på mejlet om hen vill att en
kollega tittar på just det. Skriv ALDRIG att du har skickat frågan vidare
eller att en kollega återkommer — mall 6:s formulering gäller inte här, den
hör till ESKALERA (mall 7). Nämn aldrig kunskapsbasen, källor eller käll-ID:n.

{sprakregler} Skriv svarsutkastet som ren text utan markdown, och lämna ALDRIG
kvar platshållare i hakparentes (skriv ut uppgiften eller utelämna den).

## Avsändarprofil
Företaget du svarar för — bakgrund och identitet, INTE en faktakälla för
sakuppgifter till kunden utöver bolagsuppgifterna:
{profil}

## Kunskapsbas
{kb}

## Mejlet
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
    foretagsprofil: str = "",
    foretagsnamn: str = "",
) -> dict[str, Any]:
    settings = get_settings()
    # Käll-ID:n som grundprompten kräver (avsnitt 3), och wrappat: kunskaps-
    # basen är kundskriven text och hör hemma i användarposition (INV-SEC-009).
    kb_text = (
        wrap_untrusted_content(
            "\n\n".join(
                f"### [KB-{i}] {a['title']}\n{a['content']}"
                for i, a in enumerate(kb_articles, 1)
            ),
            source="tenant:kb_article",
        )
        if kb_articles
        else "(tom — inga träffar i kunskapsbasen)"
    )
    # Personnummer maskeras INNAN texten lämnar huset. Innehållet i ett
    # supportmejl är okontrollerat, och hela texten går till modelleverantören
    # — se DPIA:ns R1. Maskeringen stänger inte risken, den gör den mindre.
    # Originalet ligger kvar i databasen; det är bara modellen som får en
    # maskerad kopia.
    from ..textkvalitet import SPRAKREGLER

    prompt = _TRIAGE_PROMPT.format(
        kategorier=", ".join(CATEGORIES),
        sprakregler=SPRAKREGLER,
        kb=kb_text,
        profil=foretagsprofil.strip() or "(ingen profil registrerad)",
        sender=sender,
        subject=maskera_personnummer(subject),
        body=maskera_personnummer(body),
    )
    # Grundprompten är systemmeddelandet: allt kundarbete utgår från den.
    grundprompt = rendera(
        foretagsnamn=foretagsnamn,
        kanal="email",
        avsandare=foretagsnamn,
        kategorier=CATEGORIES,
        lage="mejl",
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
        messages=[
            {"role": "system", "content": grundprompt},
            {"role": "user", "content": content},
        ],
        **tankande_kwargs(),
    )
    data = json.loads(response.choices[0].message.content or "{}")
    return tolka_svar(data, kb_articles)


def _tal(varde: Any, standard: float) -> float:
    try:
        return max(0.0, min(1.0, float(varde)))
    except (TypeError, ValueError):
        return standard


def tolka_svar(data: dict[str, Any], kb_articles: list[dict[str, Any]]) -> dict[str, Any]:
    """Avsnitt 11-svaret (plus inkorgens extrafält) → processorns triageformat.

    Läser tolerant: de gamla fältnamnen (category, draft_reply, escalate)
    gäller fortfarande när modellen använder dem. Grundpromptens beslut kan
    bara LÄGGA TILL en eskalering, och bara med ESKALERA (driftregeln i
    support_systemprompt): DELVIS är en kunskapslucka med ett erbjudande.
    """
    from .support_agent import (
        _LOVAR_KOLLEGA,
        _intern_motivering,
        kb_kartan,
        tolka_beslut,
        utan_kall_id,
    )

    if not isinstance(data, dict):
        data = {}
    category = data.get("kategori") or data.get("category") or "ovrigt"
    if category not in CATEGORIES:
        category = "ovrigt"
    beslut = tolka_beslut(data)
    # Driftregeln (2026-10-06): bara ESKALERA går till en människa. DELVIS
    # är en kunskapslucka — utkastet svarar på det som har källa och erbjuder
    # en kollega, och går den vanliga utkastvägen.
    eskalera = bool(data.get("escalate")) or beslut["beslut"] == "ESKALERA"
    orsak = (
        beslut["eskaleringsorsak"]
        or str(data.get("escalation_reason") or "").strip()
        or ("Grundpromptens beslut: " + beslut["beslut"] if eskalera and beslut["beslut"] else "")
    )
    utkast = data.get("svarsutkast") or data.get("draft_reply") or ""
    utkast = utan_kall_id(utkast) if isinstance(utkast, str) else ""
    # Löftesgrinden, samma som chatten (grundprompten 4.2): ett utkast som
    # säger att frågan skickats vidare får inte gå ut i ett ärende ingen
    # människa ser. Skarptest 2026-10-06: DELVIS-mejlet "har jag skickat din
    # fråga vidare till en kollega" utan eskalering. Hellre att löftet blir sant.
    if not eskalera and _LOVAR_KOLLEGA.search(utkast):
        eskalera = True
        orsak = orsak or "Utkastet lovar att en kollega återkommer, så ärendet lämnades över."
    priority = str(data.get("priority") or "normal")
    if beslut["brådskande"]:
        priority = "high"
    return {
        "category": category,
        "category_label": CATEGORY_LABELS[category],
        "priority": priority if priority in ("low", "normal", "high") else "normal",
        "sentiment": _tal(data.get("sentiment"), 0.5),
        "confidence": _tal(data.get("confidence"), 0.5),
        "escalate": eskalera,
        "escalation_reason": (
            _intern_motivering(orsak, beslut, kb_kartan(kb_articles)) if eskalera else None
        )
        or None,
        "reasoning": str(data.get("reasoning") or ""),
        "draft_reply": utkast,
        "beslut": beslut["beslut"],
        "intern_notering": beslut["intern_notering"],
        "obesvarade": beslut["obesvarade"],
        "offertforfragan": bool(data.get("offertforfragan", False)),
        "utbildningsintresse": bool(data.get("utbildningsintresse", False)),
    }
