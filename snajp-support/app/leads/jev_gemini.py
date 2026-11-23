"""Jevs frågor besvarade av Gemini Flash-Lite på Vertex i EU (2026-11-22).

## Varför

TypeSafe (jev-1.13.0) är inte godkänt underbiträde och behandlar i USA
(BESLUT 2026-11-17). Googles motsvarighet, Gemini Decisions API
(`gemini-decision-1`), finns bara i AI Studio utan EU-läge (utredning
2026-11-22). Tills ett bättre alternativ finns svarar därför Snajps vanliga
modell (MODEL, i dag gemini-3.5-flash-lite i `eu`) på exakt samma typade
frågor. Antons ord: "Lägg och konfigurera Flash lite för klassificering
utifrån de kriterier vi har efter din bästa möjliga förmåga, så får vi
använda det tills vi har ett bättre alternativ."

## Kontraktet

Samma in och ut som TypeSafe, så att `jev.triage`, `jev.klassa` och
inkorgens `klassning.klassa` inte märker skillnad:

* `noul`   → `{"noul": p, "confidence": c}`, p = sannolikheten för ja.
* `score`  → `{"score": i, "confidence": c}`, i = index i `criteria`.
* `choice` → `{"choice": nyckel, "confidence": c}`.

## Kalibreringen

En språkmodell är inte kalibrerad som Jev, och den tenderar att svara för
säkert. Jev fäller bara vid p ≤ 0,08 på ett måste-krav och p ≥ 0,92 på en
uteslutning (jev.NEJ_GRANS/JA_GRANS). Prompten reserverar därför ytterlägena
för uttryckligt belägg i texten. Saknat belägg ska ge 0,2–0,8, aldrig ett
ytterläge. Svaren kläms dessutom i koden: ett ytterläge utan citerat belägg
flyttas till 0,15/0,85, så att en gissning aldrig kan fälla ett bolag.
Triagen faller öppet som förut.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..config import get_settings

logger = logging.getLogger("snajp-support.leads.jev_gemini")

TIMEOUT_S = 30.0
#: Ett ytterläge utan belägg flyttas hit (se modulens docstring).
GOLV, TAK = 0.15, 0.85

SYSTEM = """You are a strict, calibrated decision model. You answer typed questions about \
the data in STATE and return only JSON.

Question types:
- "noul": the probability (0.0-1.0) that the answer is YES.
- "score": the index (0-based) of the best matching item in "criteria".
- "choice": exactly one key from "criteria".

For every answer, also give "confidence" (0.0-1.0) and "evidence": a short verbatim \
quote from STATE that decides the answer, or "" if there is none.

Calibration rules (important):
- Use a probability at or below 0.08, or at or above 0.92, ONLY when STATE explicitly \
states the decisive fact, and quote it in "evidence".
- When STATE does not mention the fact, answer between 0.2 and 0.8 with confidence \
at most 0.5. Missing information is not evidence.
- Judge only from STATE. Never guess from the company name alone.

Return: {"answers": {"<question name>": {"noul"|"score"|"choice": ..., \
"confidence": ..., "evidence": "..."}}}"""


def _modell() -> str:
    s = get_settings()
    return (s.jev_modell or s.model or "").strip()


def redo() -> bool:
    """Kan Gemini svara? Bara via Vertex (servicekontot): AI Studio får inte
    bära kunddata (INV-DATA-004), och inkorgen skickar kundmejl hit."""
    s = get_settings()
    return s.llm_provider == "gemini" and bool(s.google_service_account_json)


def _klam(p: Any, belagg: str) -> float | None:
    try:
        p = max(0.0, min(1.0, float(p)))
    except (TypeError, ValueError):
        return None
    if not belagg.strip():
        p = min(max(p, GOLV), TAK)
    return round(p, 3)


def tolka(fragor: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    """Modellens JSON → TypeSafes svarsform. Ogiltiga svar utelämnas, så
    att anroparen behandlar dem som obesvarade (inget fälls)."""
    svar = (data or {}).get("answers") or {}
    ut: dict[str, Any] = {}
    for namn, fraga in fragor.items():
        a = svar.get(namn)
        if not isinstance(a, dict):
            continue
        belagg = str(a.get("evidence") or "")
        konf = _klam(a.get("confidence"), "x")  # konfidensen kläms inte mot belägg
        typ = fraga.get("type")
        if typ == "noul":
            p = _klam(a.get("noul"), belagg)
            if p is not None:
                ut[namn] = {"noul": p, "confidence": konf if belagg.strip() else min(konf or 0.5, 0.5)}
        elif typ == "score":
            kriterier = fraga.get("criteria") or []
            try:
                i = int(a.get("score"))
            except (TypeError, ValueError):
                continue
            if 0 <= i < len(kriterier):
                ut[namn] = {"score": i, "confidence": konf}
        elif typ == "choice":
            val = a.get("choice")
            if isinstance(val, str) and val in (fraga.get("criteria") or {}):
                ut[namn] = {"choice": val, "confidence": konf if belagg.strip() else min(konf or 0.5, 0.5)}
    return ut


async def fraga(state: dict[str, Any], fragor: dict[str, Any]) -> dict[str, Any]:
    """Ett anrop mot MODEL (Vertex, EU). Kastar vid fel, som jev.fraga."""
    import asyncio

    from ..agent.llm import get_llm_client, tankande_kwargs

    modell = _modell()
    anvandare = json.dumps({"STATE": state, "QUESTIONS": fragor}, ensure_ascii=False)
    svar = await asyncio.wait_for(
        get_llm_client().chat.completions.create(
            model=modell,
            response_format={"type": "json_object"},
            temperature=0,
            messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": anvandare}],
            **tankande_kwargs(modell),
        ),
        timeout=TIMEOUT_S,
    )
    text = svar.choices[0].message.content or "{}"
    try:
        data = json.loads(text)
    except ValueError:
        start, slut = text.find("{"), text.rfind("}")
        data = json.loads(text[start:slut + 1]) if start >= 0 < slut else {}
    return tolka(fragor, data)


def demo() -> None:
    fragor = {
        "krav": {"type": "noul"},
        "fit": {"type": "score", "criteria": ["a", "b", "c", "d"]},
        "k": {"type": "choice", "criteria": {"support": None, "lead": None}},
    }
    ut = tolka(fragor, {"answers": {
        "krav": {"noul": 0.01, "confidence": 0.9, "evidence": ""},
        "fit": {"score": 2, "confidence": 0.7},
        "k": {"choice": "spam", "confidence": 0.9},
    }})
    assert ut["krav"]["noul"] == GOLV and ut["krav"]["confidence"] == 0.5
    assert ut["fit"] == {"score": 2, "confidence": 0.7} and "k" not in ut
    belagt = tolka(fragor, {"answers": {"krav": {"noul": 0.02, "confidence": 0.95, "evidence": "Vi säljer bara till privatpersoner"}}})
    assert belagt["krav"]["noul"] == 0.02


if __name__ == "__main__":
    demo()
    print("ok")
