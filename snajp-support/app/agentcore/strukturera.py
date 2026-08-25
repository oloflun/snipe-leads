"""Råa anteckningar in, ett AGENTS.md-format ut — med en grind efter modellen.

## Varför struktureringen finns

Den som skriver instruktioner skriver löpande text och feedback: "agenten
svarar för långt", "sluta säga hej i varje replik", "vi hade ett ärende där
den lovade en återbetalning". Det är rätt sätt att TÄNKA på instruktioner och
fel form att SKICKA dem i — en modell som får en dagbok följer en dagbok.

Modellen skriver om det till imperativa regler under fasta rubriker. Råtexten
sparas orörd (migration 049), så struktureringen går att köra om när mallen
förbättras.

## Varför utdata valideras i kod

Modellen som kör det här är samma enkla modell som driver agenten
(gemini-3.6-flash i drift). Den lägger gärna på ```markdown-staket, en
inledande artighetsmening, eller en fråga på slutet. Ingenting av det får nå
systemprompten: det som står där LÄSES SOM REGLER av varje efterföljande
steg, och en modell som hittar "Vill du att jag utvecklar något?" i sina
regler kan mycket väl svara på den.

Grinden är därför inte kosmetik. Den är samma princip som resten av kodbasen:
en regel som bara står i en prompt är en förhoppning.

## Varför ett fel inte kastar

Struktureringen är ett HJÄLPMEDEL. Går den inte igenom ska admin få tillbaka
sin egen text att spara manuellt (`kalla='manuell'`), inte ett felmeddelande
som slänger det de nyss skrev. Att förlora någons anteckningar för att en
LLM-endpoint svajade är ett dyrare fel än en instruktion som inte blev
snyggt formaterad.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from ..config import get_settings
from .instruktioner import MAX_TECKEN

#: Rubrikerna en strukturerad instruktion får använda. Fast lista, inte fri
#: form: prompten är en systemprompt som redan bär skills och overlays, och en
#: instruktionstext med egenpåhittade rubriker konkurrerar med dem om
#: modellens uppmärksamhet. Fasta rubriker gör dessutom två versioner
#: jämförbara i en diff.
RUBRIKER = (
    "Sanning och grundning",
    "Ton och tilltal",
    "Format",
    "Vad agenten aldrig gör",
    "Eskalering",
    "Övrigt",
)

_SYSTEM = """Du omvandlar råa anteckningar till ett instruktionsdokument för en
AI-agent. Du skriver INTE till en människa och du utför INTE instruktionerna.

Regler för din utdata:
1. Svenska.
2. Bara markdown-rubriker på nivå två (## Rubrik) och punktlistor med "- ".
3. Använd ENBART dessa rubriker, i den här ordningen, och hoppa över dem det
   inte finns underlag för: {rubriker}
4. Varje punkt är EN imperativ regel riktad till agenten. "Svara kort." — inte
   "Kunden tyckte att svaren var långa."
5. Uppfinn ingenting. Står det inte i anteckningarna ska det inte stå i
   dokumentet. Är en anteckning otydlig, återge den så nära originalet du kan
   i stället för att gissa vad som menades.
6. Ingen inledning, ingen sammanfattning, inga frågor, ingen kommentar om vad
   du gjort. Bara dokumentet.

Svara med ett JSON-objekt: {{"dokument": "<markdown>"}}"""

#: ```-staket, inledande artigheter och avslutande frågor. Modellen ombeds
#: avstå från alla tre i prompten ovan; det här är kodgrinden för när den
#: ändå inte gör det.
_STAKET = re.compile(r"^\s*```[a-z]*\s*\n|\n\s*```\s*$", re.IGNORECASE)
_AVSLUTANDE_FRAGA = re.compile(r"\n[^\n]*\?\s*$")


@dataclass(frozen=True)
class Strukturering:
    dokument: str
    kalla: str  # "ai" | "manuell"
    anmarkning: str = ""

    @property
    def lyckades(self) -> bool:
        return self.kalla == "ai"


def stada(text: str) -> str:
    """Tar bort det modellen lägger på trots att den blivit tillsagd.

    Ordningen spelar roll: staketet först (annars räknas ```-raden som
    innehåll), sedan den avslutande frågan, sedan kapning. Kapar man först
    kan man skära mitt i ett staket och lämna en ensam ``` kvar.
    """
    text = _STAKET.sub("", text or "").strip()
    # Bara om det som återstår ändå har innehåll — ett dokument som ÄR en
    # fråga ska inte tömmas här utan underkännas av validera().
    utan_fraga = _AVSLUTANDE_FRAGA.sub("", text).strip()
    if utan_fraga:
        text = utan_fraga
    return text[:MAX_TECKEN].strip()


def validera(dokument: str) -> str | None:
    """None när dokumentet duger, annars varför det inte gör det."""
    if len(dokument) < 20:
        return "Dokumentet blev tomt eller för kort för att vara en instruktion."
    if "##" not in dokument:
        return "Dokumentet saknar rubriker — modellen returnerade löptext."
    okanda = [
        rad.lstrip("#").strip()
        for rad in dokument.splitlines()
        if rad.startswith("##") and rad.lstrip("#").strip() not in RUBRIKER
    ]
    if okanda:
        return f"Okända rubriker: {', '.join(okanda)}."
    return None


async def strukturera(ravtext: str) -> Strukturering:
    """Rå text -> AGENTS.md-format. Kastar aldrig.

    Ett tomt underlag går inte till modellen alls: ett LLM-anrop på tom sträng
    kostar pengar för att få tillbaka ett påhittat dokument, vilket är precis
    vad regel 5 i prompten finns för att förhindra.
    """
    ravtext = (ravtext or "").strip()
    if not ravtext:
        return Strukturering(dokument="", kalla="manuell", anmarkning="Inget underlag.")

    settings = get_settings()
    if settings.is_simulation():
        # Utan nyckel finns ingen modell. Att returnera råtexten är rätt: den
        # BÄR instruktionen, den är bara inte formaterad — och ett tomt
        # dokument hade tyst tagit bort kundens regler i en testmiljö.
        return Strukturering(
            dokument=ravtext[:MAX_TECKEN],
            kalla="manuell",
            anmarkning="Simuleringsläge — texten sparas ostrukturerad.",
        )

    from ..agent.llm import get_llm_client

    try:
        client = get_llm_client()
        response = await client.chat.completions.create(
            model=settings.model,
            response_format={"type": "json_object"},
            # Lågt, inte noll: det här är omformatering, inte generering.
            # Kreativitet här visar sig som påhittade regler.
            temperature=0.1,
            messages=[
                {"role": "system", "content": _SYSTEM.format(rubriker=", ".join(RUBRIKER))},
                {"role": "user", "content": f"## Anteckningar att strukturera\n\n{ravtext}"},
            ],
        )
        svar = json.loads(response.choices[0].message.content or "{}")
        dokument = stada(str(svar.get("dokument") or ""))
    except Exception as fel:  # noqa: BLE001 — se modulens docstring
        return Strukturering(
            dokument=ravtext[:MAX_TECKEN],
            kalla="manuell",
            anmarkning=f"Struktureringen misslyckades ({type(fel).__name__}). Texten sparas som den är.",
        )

    problem = validera(dokument)
    if problem:
        return Strukturering(
            dokument=ravtext[:MAX_TECKEN],
            kalla="manuell",
            anmarkning=f"{problem} Texten sparas som den är.",
        )
    return Strukturering(dokument=dokument, kalla="ai")


def demo() -> None:
    """Kontrollen: städningen tar det modellen lägger på, valideringen släpper
    igenom rätt form och stoppar fel."""
    assert stada("```markdown\n## Format\n- Kort.\n```") == "## Format\n- Kort."
    assert stada("## Format\n- Kort.\n\nVill du att jag utvecklar?") == "## Format\n- Kort."
    # Ett dokument som BARA är en fråga ska inte städas till tomhet — det ska
    # underkännas, så att råtexten sparas i stället för ingenting.
    assert stada("Vad menar du?") == "Vad menar du?"

    assert validera("## Format\n- Skriv kort och konkret.") is None
    assert validera("kort") is not None
    assert validera("Skriv kort, det är hela regeln, men utan någon rubrik alls.") is not None
    assert "Påhittat" in (validera("## Påhittat\n- Något som inte finns i listan.") or "")
    print("strukturera: ok")


if __name__ == "__main__":
    demo()
