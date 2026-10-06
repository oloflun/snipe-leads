"""Feedback in, samma dokument ut med feedbacken inbakad. Ersätter aldrig.

## Varför

`strukturera.py` gjorde om admins anteckningar till ett nytt dokument, och det
nya dokumentet ersatte det gamla. När en utkastmall klistrades in under
Globala agentinstruktioner 2026-10-05 blev resultatet fem rader under
"## Format" ("Använd den angivna mallen för utskick"), och sanningsreglerna i
agent-core/AGENTS.md slutade gälla för både support och leads. Mallen själv
försvann också: modellen var ombedd att skriva regler, inte att bevara text.

## Hur

Modellen läser hela det befintliga dokumentet och feedbacken, och föreslår
ÄNDRINGAR: lägg till, ersätt eller ta bort, var och en med den exakta text i
dokumentet den gäller och ett skäl. Det är modellens bedömning vad som blivit
överflödigt eller motsägelsefullt, varje gång; ingen regel i kod avgör det.

Koden tillämpar ändringarna. All text som ingen ändring pekar på står därför
kvar tecken för tecken, oavsett vad modellen skriver. En ändring vars text inte
finns i dokumentet tillämpas inte och rapporteras. Tar ändringarna bort mycket
följer en varning, som adminytan kräver ett extra klick för. Det är ett
skyddsnät, inte bedömningen.

Samma funktion bakar in admins instruktioner för en enskild kund
(api/admin_profil.py) och, senare, kundens egen feedback till sin agent.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ..config import get_settings

TYPER = ("lagg_till", "ersatt", "ta_bort")

#: Varna när ändringarna tar bort mer än så här av dokumentet.
VARNA_ANDEL = 0.15
VARNA_TECKEN = 1500

_SYSTEM = """Du underhåller ett instruktionsdokument för en AI-agent. Du får
dokumentet och ny feedback. Baka in feedbacken i dokumentet. Du skriver INTE
till en människa och du utför INTE instruktionerna.

Regler:
1. Dokumentet består. Ändra bara det feedbacken faktiskt gäller. Allt annat
   lämnas exakt som det är; du returnerar bara ändringarna.
2. Ta bort eller ersätt en befintlig text BARA när feedbacken gör den
   överflödig eller säger emot den. Säg varför i `skal`.
3. Ny text placeras där den hör hemma: under den rubrik den gäller, efter
   den befintliga text den bygger vidare på. Saknas en passande rubrik får
   du lägga till en.
4. Citerat material i feedbacken, till exempel en mall, ett exempel eller en
   exakt formulering, återges ORDAGRANT i dokumentet. Gör aldrig om en mall
   till en regel om mallen.
5. Skriv i dokumentets stil: samma språk, samma rubriknivåer, imperativ riktad
   till agenten. Uppfinn ingenting som inte står i feedbacken.
6. `befintlig` och `efter` är EXAKT text kopierad ur dokumentet, tecken för
   tecken, och tillräckligt lång för att vara unik (helst en hel rad).

Svara med ETT JSON-objekt:
{"andringar": [
  {"typ": "lagg_till", "efter": "<exakt befintlig text att lägga den nya efter, tom = sist i dokumentet>", "ny": "<ny text>", "skal": "<varför>"},
  {"typ": "ersatt", "befintlig": "<exakt befintlig text>", "ny": "<ersättning>", "skal": "<varför>"},
  {"typ": "ta_bort", "befintlig": "<exakt befintlig text>", "skal": "<varför>"}
], "sammanfattning": "<en mening om vad som ändrades>"}"""


@dataclass
class Bakning:
    dokument: str
    #: De ändringar som tillämpades: {typ, befintlig, ny, skal}.
    andringar: list[dict[str, str]] = field(default_factory=list)
    #: Ändringar som inte gick att tillämpa (texten fanns inte), med skäl.
    ej_tillampade: list[dict[str, str]] = field(default_factory=list)
    kalla: str = "bakad"  # "bakad" | "manuell"
    sammanfattning: str = ""
    anmarkning: str = ""
    borttaget_tecken: int = 0
    varning: str = ""

    def som_dict(self) -> dict[str, Any]:
        return {
            "dokument": self.dokument,
            "andringar": self.andringar,
            "ej_tillampade": self.ej_tillampade,
            "kalla": self.kalla,
            "sammanfattning": self.sammanfattning,
            "anmarkning": self.anmarkning,
            "borttaget_tecken": self.borttaget_tecken,
            "varning": self.varning,
        }


def tillampa(befintligt: str, andringar: list[dict[str, Any]], *, tak: int) -> Bakning:
    """Ändringarna på dokumentet, i ordning. Ren funktion: det som inte
    pekas ut står kvar exakt."""
    dok = befintligt
    gjorda: list[dict[str, str]] = []
    ej: list[dict[str, str]] = []
    borttaget = 0
    for a in andringar if isinstance(andringar, list) else []:
        if not isinstance(a, dict) or a.get("typ") not in TYPER:
            continue
        typ = a["typ"]
        ny = str(a.get("ny") or "").strip("\n")
        skal = str(a.get("skal") or "").strip()
        if typ == "lagg_till":
            if not ny.strip():
                continue
            efter = str(a.get("efter") or "")
            if efter and efter in dok:
                pos = dok.index(efter) + len(efter)
                # Efter hela raden/stycket, aldrig mitt i en rad.
                radslut = dok.find("\n", pos)
                pos = len(dok) if radslut == -1 else radslut
                dok = f"{dok[:pos]}\n\n{ny}{dok[pos:]}"
            elif efter:
                ej.append({**{k: str(v) for k, v in a.items()}, "fel": "Texten att lägga till efter finns inte i dokumentet."})
                continue
            else:
                dok = f"{dok.rstrip()}\n\n{ny}\n" if dok.strip() else f"{ny}\n"
            gjorda.append({"typ": typ, "befintlig": efter, "ny": ny, "skal": skal})
            continue
        befintlig = str(a.get("befintlig") or "")
        if not befintlig or befintlig not in dok:
            ej.append({**{k: str(v) for k, v in a.items()}, "fel": "Texten finns inte i dokumentet."})
            continue
        ersattning = ny if typ == "ersatt" else ""
        dok = dok.replace(befintlig, ersattning, 1)
        borttaget += max(0, len(befintlig) - len(ersattning))
        gjorda.append({"typ": typ, "befintlig": befintlig, "ny": ersattning, "skal": skal})
    # Tomma rader som en borttagning lämnar efter sig.
    while "\n\n\n" in dok:
        dok = dok.replace("\n\n\n", "\n\n")
    bakning = Bakning(dokument=dok.strip() + "\n", andringar=gjorda, ej_tillampade=ej, borttaget_tecken=borttaget)
    if len(bakning.dokument) > tak:
        bakning.varning = f"Dokumentet blir {len(bakning.dokument)} tecken, över taket på {tak}. Kortare feedback eller dela upp den."
    elif borttaget > VARNA_TECKEN or (befintligt and borttaget > VARNA_ANDEL * len(befintligt)):
        bakning.varning = (
            f"Ändringarna tar bort {borttaget} tecken av {len(befintligt)}. "
            "Läs borttagningarna innan du sparar."
        )
    return bakning


async def baka_in(befintligt: str, feedback: str, *, tak: int) -> Bakning:
    """Feedbacken inbakad i `befintligt`. Kastar aldrig.

    Går modellen inte att nå läggs feedbacken till sist, ordagrant, som en egen
    rubrik (kalla='manuell'). Hellre ett dokument som är längre än det borde än
    ett där något tyst försvunnit."""
    befintligt = befintligt or ""
    feedback = (feedback or "").strip()
    if not feedback:
        return Bakning(dokument=befintligt, kalla="manuell", anmarkning="Ingen feedback att baka in.")

    def _sist(anmarkning: str) -> Bakning:
        b = tillampa(befintligt, [{"typ": "lagg_till", "efter": "", "ny": f"## Tillägg\n\n{feedback}", "skal": "Feedbacken ordagrant."}], tak=tak)
        b.kalla, b.anmarkning = "manuell", anmarkning
        return b

    settings = get_settings()
    if settings.is_simulation():
        return _sist("Simuleringsläge: feedbacken läggs till sist, ordagrant.")

    from ..agent.llm import get_llm_client, tankande_kwargs

    try:
        svar = await get_llm_client().chat.completions.create(
            model=settings.model,
            response_format={"type": "json_object"},
            temperature=0.1,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": f"## Dokumentet\n\n{befintligt or '(tomt)'}\n\n## Feedback att baka in\n\n{feedback}",
                },
            ],
            **tankande_kwargs(),
        )
        data = json.loads(svar.choices[0].message.content or "{}")
    except Exception as fel:  # noqa: BLE001 — se docstringen
        return _sist(f"Inbakningen misslyckades ({type(fel).__name__}): feedbacken läggs till sist, ordagrant.")

    bakning = tillampa(befintligt, data.get("andringar") or [], tak=tak)
    bakning.sammanfattning = str(data.get("sammanfattning") or "").strip()[:400]
    if not bakning.andringar:
        return _sist("Modellen föreslog ingen ändring som gick att tillämpa: feedbacken läggs till sist, ordagrant.")
    return bakning


def demo() -> None:
    dok = "# Regler\n\n## 1. Sanning\n\n- Hitta aldrig på.\n\n## 2. Ton\n\n- Skriv kort.\n"
    b = tillampa(dok, [
        {"typ": "lagg_till", "efter": "- Skriv kort.", "ny": "- Inga utropstecken.", "skal": "feedback"},
        {"typ": "ersatt", "befintlig": "- Skriv kort.", "ny": "- Skriv kort, högst 120 ord.", "skal": "preciserat"},
        {"typ": "ta_bort", "befintlig": "finns inte", "skal": "x"},
    ], tak=10_000)
    assert "- Hitta aldrig på." in b.dokument, "orörd text står kvar"
    assert "- Inga utropstecken." in b.dokument and "högst 120 ord" in b.dokument
    assert len(b.andringar) == 2 and len(b.ej_tillampade) == 1
    assert b.dokument.index("högst 120 ord") < b.dokument.index("Inga utropstecken")
    mall = "Ämne: {observation} – {företagsnamn}\nHej {förnamn},"
    b2 = tillampa(dok, [{"typ": "lagg_till", "efter": "", "ny": f"## Mall\n\n{mall}", "skal": "mall"}], tak=10_000)
    assert mall in b2.dokument and "## 1. Sanning" in b2.dokument
    stor = tillampa("x" * 2000, [{"typ": "ta_bort", "befintlig": "x" * 1600, "skal": "s"}], tak=10_000)
    assert stor.varning
    print("baka_in: ok")


if __name__ == "__main__":
    demo()
