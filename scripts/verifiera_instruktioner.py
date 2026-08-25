#!/usr/bin/env python3
"""Når varje ifyllbart fält fram till agenten? Mätt, inte antaget.

    python scripts/verifiera_instruktioner.py              # utan LLM: bara positionerna
    python scripts/verifiera_instruktioner.py --skarp      # + ett riktigt modellanrop

## Varför skriptet finns

`agent_configs.instructions_md` och `.tone` fanns i schemat från migration 010
till 049 utan att någon kodväg läste dem. Symptomet hos kunden var "jag ändrar
instruktionerna och svaren blir likadana", och det gick inte att falsifiera från
någon vy: fältet såg ifyllt ut, agenten svarade, och ingenstans stod det att
texten aldrig lämnade databasen.

Det här är kommandot som svarar på frågan. Varje fält får en unik markör, en
körning görs, och skriptet rapporterar var markören dök upp.

## De två nivåerna, och varför båda behövs

MEKANIK (alltid): nådde texten prompten, och i rätt position? Det är
deterministiskt och går att mäta utan att betala för ett modellanrop.
Positionen är inte en detalj — instruktioner i systemposition är regler
agenten lyder, kundskriven text i användarposition är uppgifter den läser.
Hamnar SOUL i systemprompten är det en säkerhetsregression (INV-SEC-009) även
om agenten då skulle bete sig "bättre".

BETEENDE (--skarp): gjorde modellen som instruktionen sa? Bara mekanik räcker
inte — en regel kan nå prompten och ändå ignoreras av en enkel modell, och det
är precis det man vill veta innan man skriver en instruktion man litar på.

## Varför MemoryStorage och inte en riktig databas

Frågan skriptet ställer är "läser promptbygget fälten", inte "fungerar
Postgres". MemoryStorage kör samma protokoll (tests/invariants/ vaktar att det
inte glider isär), och alternativet vore att peka en lokal körning mot
development-databasen — som bär riktiga kunders ärenden. Se CLAUDE.md.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "snajp-support"))

TENANT = "00000000-0000-4000-a000-000000000001"

#: Markörerna. Slumpartade nog att inte kunna uppstå av sig själva, och korta
#: nog att en enkel modell inte trasslar bort dem när den ombeds återge dem.
MARKORER = {
    "global": "GLOBAL-3311",
    "kund": "KUND-7742",
    "tone": "TON-5519",
    "soul": "ROST-8823",
    "affarskontext": "AFFAR-6614",
    "kunskapsbas": "KB-9905",
}

#: Var varje fält SKA hamna. "system" = regler agenten lyder. "user" = text den
#: läser som uppgifter. Ett fält som hamnar i fel kolumn är ett fel även när
#: agenten svarar bra.
FORVANTAD_POSITION = {
    "global": "system",
    "kund": "system",
    "tone": "user",
    "soul": "user",
    "affarskontext": "user",
    "kunskapsbas": "user",
}


class _Spion:
    """Fångar prompterna. Svarar kontraktsenligt så körningen går igenom."""

    def __init__(self):
        self.system: list[str] = []
        self.user: list[str] = []
        self.chat = self
        self.completions = self

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        import json

        self.system.append(messages[0]["content"])
        self.user.append(messages[1]["content"])
        payload = {
            "sources_used": ["Leveranstider"],
            "context_refs": [],
            "category": "leverans",
            "priority": "P3",
            "sentiment": 0.8,
            "escalate": False,
            "findings": "ok",
            "confidence": 0.9,
            "kb_supports_answer": True,
            "missing_info": None,
            "draft": "Ett svar.",
            "should_escalate": False,
            "reason": None,
            "humanized": "Ett svar.",
            "text": "Ett svar.",
        }
        return type(
            "Svar",
            (),
            {
                "choices": [
                    type("C", (), {"message": type("M", (), {
                        "content": json.dumps(payload, ensure_ascii=False),
                        "reasoning_content": None,
                    })()})()
                ],
                "usage": None,
            },
        )()


async def _fyll(storage) -> None:
    """Alla fält, alla ifyllda, var och en med sin egen markör."""
    from app.leads.soul import SOUL_KIND

    await storage.add_kb_article(
        TENANT,
        title="Leveranstider",
        content=f"Standardfrakt tar 2-4 vardagar. Internkod {MARKORER['kunskapsbas']}.",
        category="leverans",
    )
    await storage.save_global_instructions(
        ravtext="testdata",
        strukturerad_md=(
            "## Format\n"
            f"- Avsluta varje svar med exakt: {MARKORER['global']}"
        ),
        kalla="manuell",
    )
    await storage.set_agent_instructions(
        TENANT,
        agent_type="support",
        instructions_md=f"## Övrigt\n- Nämn kundnumret {MARKORER['kund']} i svaret.",
        instructions_rav="testdata",
        tone=f"kort och rak, internt tonläge {MARKORER['tone']}",
    )
    await storage.save_context_doc(
        TENANT, kind=SOUL_KIND, content=f"Vi låter enkelt och lugnt. {MARKORER['soul']}", source="test"
    )
    await storage.save_context_doc(
        TENANT,
        kind="product_marketing",
        content=f"Vi säljer cyklar till pendlare i Sverige. {MARKORER['affarskontext']}",
        source="test",
    )


def _position(system: str, user: str, markor: str) -> str:
    i_system = markor in system
    i_user = markor in user
    if i_system and i_user:
        return "BÅDA"
    if i_system:
        return "system"
    if i_user:
        return "user"
    return "SAKNAS"


async def mekanik() -> int:
    """Nådde varje fält prompten, i rätt position?"""
    from unittest.mock import AsyncMock, patch

    from app.agent.support_agent import run_support_agent
    from app.storage.memory import MemoryStorage

    storage = MemoryStorage()
    await _fyll(storage)

    spion = _Spion()
    with patch("app.agent.step_runner.get_llm_client", return_value=spion), patch(
        "app.agent.retention_classifier.classify_cancellation_risk",
        new=AsyncMock(return_value=(0.0, 0.0)),
    ):
        await run_support_agent(
            storage,
            TENANT,
            message="Hur lång är leveranstiden?",
            subject="Leverans",
            channel="web",
            customer_email="kund@example.test",
            customer_name="Testkund",
            attachments=[],
        )

    system = "\n".join(spion.system)
    user = "\n".join(spion.user)

    print(f"\n{len(spion.system)} steg kördes.\n")
    print(f"{'fält':<16}{'position':<12}{'förväntat':<12}utfall")
    print("-" * 56)
    fel = 0
    for falt, markor in MARKORER.items():
        faktisk = _position(system, user, markor)
        vantat = FORVANTAD_POSITION[falt]
        ok = faktisk == vantat
        fel += 0 if ok else 1
        print(f"{falt:<16}{faktisk:<12}{vantat:<12}{'ok' if ok else 'FEL'}")

    # Globala regler måste nå VARJE steg, inte bara det första. En regel som
    # bara nådde triagen ser rätt ut i en spårvy och påverkar inte utkastet.
    saknas = [i for i, s in enumerate(spion.system, 1) if MARKORER["global"] not in s]
    if saknas:
        fel += 1
        print(f"\nFEL: den globala regeln saknades i steg {saknas}.")
    else:
        print(f"\nDen globala regeln fanns i alla {len(spion.system)} steg.")
    return fel


async def skarp() -> int:
    """Gjorde en RIKTIG modell som instruktionen sa?

    Ett enda anrop, inte hela playbooken: frågan är om instruktionslagret styr
    modellen, och det svaret kostar inte sju steg.
    """
    from app.agent.llm import get_llm_client
    from app.agentcore.instruktioner import Instruktionslager
    from app.config import get_settings

    settings = get_settings()
    if settings.is_simulation():
        print("\nSKARP: ingen nyckel i miljön — hoppar över. Sätt GEMINI_API_KEY.")
        return 0

    lager = Instruktionslager(
        global_md=f"## Format\n- Avsluta ALLTID varje svar med exakt: {MARKORER['global']}",
        kund_md="",
    )
    client = get_llm_client()
    response = await client.chat.completions.create(
        model=settings.model,
        response_format={"type": "json_object"},
        temperature=0.3,
        messages=[
            {
                "role": "system",
                "content": f"{lager.global_block}\n\nDu svarar en kund. Svara med JSON: "
                '{"svar": "<text>"}',
            },
            {"role": "user", "content": "Hur lång är leveranstiden?"},
        ],
    )
    import json

    text = json.dumps(
        json.loads(response.choices[0].message.content or "{}"), ensure_ascii=False
    )
    lydde = MARKORER["global"] in text
    print(f"\nSKARP ({settings.llm_provider}/{settings.model}):")
    print(f"  svar: {text[:200]}")
    print(f"  följde instruktionen: {'JA' if lydde else 'NEJ'}")
    return 0 if lydde else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skarp", action="store_true", help="gör också ett riktigt modellanrop")
    args = ap.parse_args()

    # MemoryStorage, aldrig en riktig databas. En lokal körning mot
    # development-databasen läser riktiga kunders ärenden — se CLAUDE.md.
    os.environ["DATABASE_URL"] = ""

    fel = asyncio.run(mekanik())
    if args.skarp:
        fel += asyncio.run(skarp())

    print()
    if fel:
        print(f"{fel} fel. Ett fält når inte fram, eller hamnar i fel position.")
        return 1
    print("Alla fält når agenten, i rätt position.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
