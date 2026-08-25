"""Maskeringen ska sitta på VARJE väg där kundens text når modellen.

## Varför det här testet finns, och varför det inte är ett live-anrop

Maskeringen provades först med ett riktigt anrop mot demo-endpointen. Svaret
innehöll inte personnumret, och det såg ut som ett bevis. Det var det inte:
modellen kan ha låtit bli att upprepa numret av sig själv. Ett svar som inte
nämner något säger ingenting om vad som skickades.

Värre: anropet gick genom `demo_agent.py`, som är en EGEN kodväg — den passerar
varken `triage_email_llm` eller `run_support_agent`, alltså inget av de två
ställen maskeringen då satt på. Testet mätte en väg som inte var maskerad, och
"godkände" den.

Testerna nedan inspekterar i stället DEN FAKTISKA STRÄNG som går till modellen.
Det är den enda frågan som betyder något, och den går inte att svara på genom
att läsa ett svar.

## Om en ny väg läggs till

Lägg till den här. En maskering som gäller överallt utom på ett ställe är den
sortens undantag ingen kommer ihåg — och det stället blir det som läcker.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.moderation.maskering import PLATSHALLARE

def _med_kontrollsiffra(nio: str) -> str:
    """Kontrollsiffran RÄKNAS, den skrivs inte av.

    Första versionen av det här testet bar ett handskrivet "850101-1230" —
    som inte passerar Luhn och alltså inte är ett personnummer. Testet föll,
    och det var testet som hade fel: maskeringen gjorde rätt som lät det stå.

    Samma misstag fanns i det live-anrop som först "bevisade" maskeringen.
    Ett testfall som inte är det man tror det är bevisar ingenting alls.
    """
    summa = 0
    for i, tecken in enumerate(nio):
        varde = int(tecken) * (2 if i % 2 == 0 else 1)
        summa += varde - 9 if varde > 9 else varde
    return nio + str((10 - summa % 10) % 10)


#: Giltigt datum OCH giltig Luhn, men hör inte till någon person.
_TIO = _med_kontrollsiffra("850101123")
PNR = f"{_TIO[:6]}-{_TIO[6:]}"

#: Tio siffror som INTE är ett personnummer. Måste överleva maskeringen —
#: utan ordernumret blir agentens svar oanvändbart.
ORDERNUMMER = "1234567890"


def _fangad_prompt(anrop) -> str:
    """Plockar ut all text som skickades, oavsett meddelandeform."""
    delar: list[str] = []
    for meddelande in anrop.kwargs.get("messages", []):
        innehall = meddelande.get("content")
        if isinstance(innehall, str):
            delar.append(innehall)
        elif isinstance(innehall, list):
            for bit in innehall:
                if isinstance(bit, dict):
                    delar.append(str(bit.get("text", "")))
    return "\n".join(delar)


@pytest.mark.anyio
async def test_triagen_skickar_inte_personnumret():
    from app.agent import triage

    svar = MagicMock()
    svar.choices = [MagicMock(message=MagicMock(content='{"category":"ovrigt"}'))]
    klient = MagicMock()
    klient.chat.completions.create = AsyncMock(return_value=svar)

    with patch.object(triage, "get_llm_client", return_value=klient):
        try:
            await triage.triage_email_llm(
                sender="anna@exempel.se",
                subject=f"Order {ORDERNUMMER}",
                body=f"Hej, mitt personnummer är {PNR}. Var är min order {ORDERNUMMER}?",
                kb_articles=[],
            )
        except Exception:
            # Svarsformatet kan falla på parsning — det är inte det vi mäter.
            pass

    klient.chat.completions.create.assert_awaited()
    skickat = _fangad_prompt(klient.chat.completions.create.await_args)

    assert PNR not in skickat, "personnumret gick till modellen"
    assert _TIO not in skickat.replace("-", ""), "personnumret gick utan bindestreck"
    assert PLATSHALLARE in skickat, "platshållaren saknas — maskerade den något alls?"
    # Och det som INTE får försvinna: utan ordernumret blir svaret oanvändbart.
    assert ORDERNUMMER in skickat, "ordernumret maskerades — för brett mönster"


def test_stallena_dar_kundtext_nar_modellen_ar_kanda():
    """Vaktar mot att en ny väg läggs till utan maskering.

    Det här är inte ett vackert test, men det är det som fångar felet som
    faktiskt hände: en tredje kodväg (demo_agent) som ingen tänkte på.
    Ändras någon av filerna nedan ska den som ändrar ta ställning till om
    maskeringen behövs — och testet tvingar fram frågan.
    """
    from pathlib import Path

    rot = Path(__file__).resolve().parent.parent / "app" / "agent"
    vagar = {
        "triage.py": "body=maskera_personnummer",
        "support_agent.py": "maskera_personnummer(message)",
        "demo_agent.py": "maskera_personnummer(message)",
    }
    saknas = [
        namn
        for namn, markor in vagar.items()
        if markor not in (rot / namn).read_text(encoding="utf-8")
    ]
    assert not saknas, (
        f"Maskeringen saknas i {', '.join(saknas)}. Varje väg där kundens text "
        f"når modellen ska maskera först — se app/moderation/maskering.py."
    )
