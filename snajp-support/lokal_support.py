"""Lokal backend för supportflödet i MINNESLÄGE, med en FEJKMODELL.

Till för att prova den sömlösa överlämningen (bd snipe-1fl) i webbläsaren
utan nycklar och utan kostnad: chattfönstret i huvudappen (port 8000) och
portalens Chattar-vy (support-webb, port 8010) pratar med SAMMA process och
alltså samma minneslagring — ett samtal som eskaleras i chatten syns direkt
i portalen, och medarbetarens svar dyker upp i chattfönstret.

Fejkmodellen är deterministisk och styrs av ord i kundens meddelande:

    "människa"    -> kunden ber om en människa (överlämning)
    "väder"       -> utanför ämnesområdet (agenten erbjuder en människa)
    "fattar"      -> kunden säger att svaret missade (räknas mot taket)
    "betal"       -> kunskapsbasen bär svaret
    allt annat    -> vag fråga, agenten ställer en motfråga

Samma grepp som lokal_iris.py: DATABASE_URL/REDIS_URL blankas innan
settings byggs, så en lokal server kan aldrig peka på en riktig databas.
Körs via .claude/launch.json ("support-backend") eller för hand:
    .venv/Scripts/python.exe lokal_support.py
"""

import asyncio
import json
import os
import re

os.environ["DATABASE_URL"] = ""
os.environ["REDIS_URL"] = ""
# En nyckel måste finnas, annars väljer appen simuleringsagenten i stället
# för run_support_agent. Den används aldrig: klienten nedan är fejkad.
os.environ["LLM_PROVIDER"] = "deepseek"
os.environ["DEEPSEEK_API_KEY"] = "lokal-fejkmodell-inte-en-riktig-nyckel"
# .env:ens MODEL är en gemini-modell; uppstartsvakten (config.py) vägrar med
# rätta den kombinationen. Namnet används aldrig — klienten är fejkad.
os.environ["MODEL"] = "deepseek-chat"
os.environ["SEMANTIC_CACHE"] = "off"

import uvicorn  # noqa: E402

from app.agent import step_runner, support_agent  # noqa: E402


def _kundens_meddelande(prompt: str) -> str:
    traff = re.search(r"Kundens meddelande:\n(.*?)(?:\n\n|$)", prompt, re.DOTALL)
    return (traff.group(1) if traff else "").lower()


def _utkast(uppgift: str) -> str:
    if "HÄR i chatten" in uppgift:
        return (
            "Jag kopplar in en kollega som tar över här i chatten. Hela samtalet "
            "följer med, så du behöver inte upprepa något."
        )
    if "EN kort, öppen följdfråga" in uppgift:
        return "Jag vill förstå rätt: vad är det du vill göra, mer precis?"
    if "utanför det du är här för" in uppgift:
        return (
            "Det ligger utanför det jag kan hjälpa till med här — jag svarar på "
            "frågor om beställningar och betalningar. Vill du att jag kopplar in en kollega?"
        )
    return (
        "Du kan betala med kort eller Swish. Vill du veta hur du byter kort på en "
        "pågående beställning?"
    )


class _Fejkmodell:
    def __init__(self) -> None:
        self.chat = self
        self.completions = self

    async def create(self, *, messages, **_):
        system, user = messages[0]["content"], messages[1]["content"]
        skill = re.search(r"styrs av skillen (\S+?),", system).group(1)
        uppgift = user.split("## Din uppgift i det här steget\n", 1)[-1]
        meddelande = _kundens_meddelande(user)
        svar: dict = {"sources_used": ["kb"], "context_refs": ["context_pack"]}
        if skill == "cs:ticket-triage":
            svar.update(
                category="ovrigt", priority="P3", sentiment=0.6, escalate=False,
                reasoning="fejk", kundfakta=[],
                ber_om_manniska="människa" in meddelande,
                inom_amnesomradet="väder" not in meddelande,
                missforstadd="fattar" in meddelande,
            )
        elif skill == "cs:customer-research":
            svar.update(
                findings="fejk", confidence=0.8,
                kb_supports_answer="betal" in meddelande,
                behover_fortydligande=True, missing_info=None,
            )
        elif skill == "cs:draft-response":
            svar.update(draft=_utkast(uppgift))
        elif skill == "snajp:humanizer-svenska":
            text = user.split("## Text att humanisera\n", 1)[-1]
            text = text.split("## Text att rätta\n", 1)[-1]
            svar.update(final_reply=text.split("\n\n## Din uppgift", 1)[0].strip())
        elif skill == "cs:customer-escalation":
            svar.update(should_escalate=False, reason=None)
        elif skill == "cs:kb-article":
            svar.update(should_create=False)
        innehall = json.dumps(svar, ensure_ascii=False)
        message = type("M", (), {"content": innehall})()
        usage = type("U", (), {"prompt_tokens": 0, "completion_tokens": 0})()
        return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()


async def _ingen_uppsagningsrisk(_message: str):
    return 0.0, 0.0


step_runner.get_llm_client = lambda: _Fejkmodell()
support_agent.classify_cancellation_risk = _ingen_uppsagningsrisk


# --- Webbplatsskanningen (Kunskapsbas -> Skanna webbplats) ------------------
#
# Lokalt skannas ALDRIG nätet: vilken adress som helst läses som testfixturen
# tests/fixtures/pilot_kb/exempelbutik (en påhittad kuddbutik med villkor,
# garanti, FAQ och kontakt), och fejkmodellen skriver en artikel per sida —
# rubriken och sidans första rader. Räcker för att prova hela flödet i
# portalen: skanna, välj förslag, lägg till, ta bort.
from pathlib import Path  # noqa: E402
from urllib.parse import urlparse  # noqa: E402

from app import kb_skanning  # noqa: E402

_FIXTUR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "pilot_kb" / "exempelbutik"


class _FixturHamtare:
    def hamta(self, url: str) -> kb_skanning.Svar:
        return kb_skanning.SimuleradHamtare(_FIXTUR, url).hamta(url)


async def _fejk_utkast(_system: str, anvandare: str) -> str:
    artiklar = []
    for kalla, rubrik, text in re.findall(
        r"source='([^']+)'>\n.*?\n\nRubrik: ([^\n]*)\n\n(.*?)\n</untrusted-data", anvandare, re.S
    ):
        rader = [r.lstrip("#- ").strip() for r in text.splitlines() if r.strip()]
        artiklar.append({
            "title": rubrik.split(" (del ")[0] or urlparse(kalla).path,
            "content": " ".join(rader)[:500],
            "category": kb_skanning.kategori_for(kalla, rubrik),
            "source_url": kalla,
            "confidence": 0.8,
        })
    return json.dumps({"artiklar": artiklar, "saknas": []}, ensure_ascii=False)


kb_skanning.PublikHamtare = _FixturHamtare
kb_skanning.ar_publik_vard = lambda _url: True
kb_skanning.bygg_anropare = lambda: _fejk_utkast


async def main() -> None:
    from app.main import app

    # EN app, TVÅ portar: huvudappens proxy pekar på 8000 och portalens på
    # 8010. Samma appobjekt = samma MemoryStorage, så båda ser samma samtal.
    servrar = [
        uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, lifespan="on" if i == 0 else "off"))
        for i, port in enumerate((8000, 8010))
    ]
    await asyncio.gather(*(s.serve() for s in servrar))


if __name__ == "__main__":
    asyncio.run(main())
