"""Del E, steg 6: en billig klassificerare i KOD avgör om
snajp:retention-conversation injiceras — inte en promptinstruktion i
huvudloopen. Ett separat, litet LLM-anrop bedömer uppsägningsavsikt och
missnöje (0.0-1.0) på det inkommande meddelandet. Över tröskel: skillen
injiceras OCH ärendet flaggas för människa (agenten förhandlar aldrig
ensam)."""

import json

from ..config import get_settings
from .llm import get_llm_client

CANCELLATION_RISK_THRESHOLD = 0.6

_PROMPT = """Bedöm kundmeddelandet på två axlar, 0.0-1.0. Svara ENBART med JSON:
{{
  "uppsagningsavsikt": 0.0-1.0,
  "missnoje": 0.0-1.0
}}

uppsagningsavsikt: hur tydligt signalerar meddelandet att kunden vill
avsluta/säga upp (frågar hur man avslutar, hotar med uppsägning, jämför med
konkurrent som ersättning)?

missnoje: hur missnöjd/upprörd är kunden, oavsett uppsägningssignal?

Meddelande:
{message}"""


async def classify_cancellation_risk(message: str) -> tuple[float, float]:
    """Returnerar (uppsägningsavsikt, missnöje). Ett anropsfel eskalerar
    hellre än att tyst anta lågrisk — se anroparen (support_playbook)."""
    settings = get_settings()
    response = await get_llm_client().chat.completions.create(
        model=settings.model,
        response_format={"type": "json_object"},
        temperature=0.0,
        messages=[{"role": "user", "content": _PROMPT.format(message=message)}],
    )
    data = json.loads(response.choices[0].message.content or "{}")
    cancellation_intent = max(0.0, min(1.0, float(data.get("uppsagningsavsikt", 0.0))))
    dissatisfaction = max(0.0, min(1.0, float(data.get("missnoje", 0.0))))
    return cancellation_intent, dissatisfaction


def is_cancellation_risk(cancellation_intent: float, dissatisfaction: float) -> bool:
    return (
        cancellation_intent >= CANCELLATION_RISK_THRESHOLD
        or dissatisfaction >= CANCELLATION_RISK_THRESHOLD
    )
