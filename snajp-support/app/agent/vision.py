"""G9: vision-sidovagn. deepseek-v4-flash saknar dokumenterat bildstöd, så en
bild beskrivs separat av en Gemini-modell (vision_model, default
gemini-3.6-flash — gratisnivå, se scripts/keys.py) och beskrivningen — text,
inte bilden — matas in i DeepSeek-loopen.

Bilden lagras ALDRIG efter beskrivningen: den här funktionen tar en data-URL
och returnerar text. Den skriver ingenting till storage-lagret, och anroparen
(support_agent.run_support_agent) håller data-URL:en bara i minnet under
anropet. Underbiträdet (Google) måste stå i personuppgiftsbiträdesavtalet
med kunden — se plan G9.
"""

from ..config import get_settings
from .llm import get_vision_client

_VISION_PROMPT = (
    "Beskriv kort på svenska vad bilden visar, med fokus på det som är "
    "relevant för ett kundtjänstärende: felmeddelanden, skador på en vara, "
    "kvitton/ordernummer, eller annat textinnehåll. Max 3 meningar."
)


async def describe_image(data_url: str) -> str:
    """Returnerar en svensk textbeskrivning, eller en tydlig felsträng om
    vision-klienten saknas — ALDRIG en tyst tom sträng som får agenten att
    agera som om bilden inte fanns."""
    client = get_vision_client()
    if client is None:
        return "[Bild bifogad — ingen bildbeskrivningsklient konfigurerad. Eskalera om bilden är relevant för ärendet.]"

    settings = get_settings()
    response = await client.chat.completions.create(
        model=settings.vision_model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _VISION_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        max_tokens=200,
    )
    description = (response.choices[0].message.content or "").strip()
    return description or "[Bildbeskrivning misslyckades — eskalera om bilden är relevant för ärendet.]"
