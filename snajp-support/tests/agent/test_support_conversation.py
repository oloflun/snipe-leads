"""Samtalsform: vet agenten var i samtalet den befinner sig?

Bakgrunden är ett skarpt fel, inte en hypotes. Utkaststeget fick bara ANTALET
tidigare kontakter — en siffra, aldrig samtalet — så varje replik var formellt
sett ett första meddelande. Resultatet syntes i Livrustnings chatt: "Hej" på
varje tur och "Vänliga hälsningar," under varje, mitt i ett pågående samtal.

Testet mockar bara nätverksgränsen (LLM-klienten). Allt annat är den riktiga
kodvägen, inklusive lagringen och den faktiska prompten som skickas.
"""

import json
import re
from unittest.mock import AsyncMock, patch

import pytest

from app.agent.support_agent import (
    MAX_HISTORY_TURNS,
    run_support_agent,
    strip_dangling_sign_off,
)
from app.agent.support_playbook import SUPPORT_V1
from app.config import get_settings
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"
CUSTOMER = "kund@example.com"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _fake_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _CapturingLLM:
    """Kontraktsenliga svar, och sparar hela användarmeddelandet per skill.

    Det är prompten vi vill kunna asserta på — att koden BYGGT ett samtalsläge
    säger ingenting om att det nådde modellen.
    """

    def __init__(self, final_reply="Du kan betala med Swish eller kort."):
        self.user_by_skill: dict[str, str] = {}
        self.final_reply = final_reply
        self.chat = self
        self.completions = self

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        system = messages[0]["content"]
        skill = re.search(r"styrs av skillen (\S+?),", system).group(1)
        self.user_by_skill[skill] = messages[1]["content"]

        payload = {"sources_used": ["kb-1"], "context_refs": ["context_pack"]}
        payload.update(
            {
                "cs:ticket-triage": {
                    "category": "betalning", "priority": "P3",
                    "sentiment": 0.6, "escalate": False,
                },
                "cs:customer-research": {
                    "findings": "KB täcker frågan.", "confidence": 0.8,
                    "kb_supports_answer": True,
                },
                "cs:draft-response": {"draft": "Du kan betala med Swish eller kort."},
                "cs:customer-escalation": {"should_escalate": False, "reason": None},
                "cs:kb-article": {"should_create": False},
                "snajp:humanizer-svenska": {"final_reply": self.final_reply},
            }.get(skill, {})
        )

        message = type("M", (), {"content": json.dumps(payload, ensure_ascii=False)})()
        usage = type("U", (), {"prompt_tokens": 100, "completion_tokens": 20})()
        return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()


async def _turn(storage, llm, message):
    with patch("app.agent.step_runner.get_llm_client", return_value=llm), patch(
        "app.agent.support_agent.classify_cancellation_risk", new=AsyncMock(return_value=(0.0, 0.0))
    ):
        return await run_support_agent(
            storage, TENANT,
            message=message, subject="", channel="web",
            customer_email=CUSTOMER, customer_name="Test Person", attachments=[],
        )


# --- Samtalsläget når faktiskt prompten -----------------------------------


@pytest.mark.anyio
async def test_forsta_turen_markeras_som_forsta():
    storage, llm = MemoryStorage(), _CapturingLLM()
    await _turn(storage, llm, "Vilka betalsätt accepterar ni?")

    draft_prompt = llm.user_by_skill["cs:draft-response"]
    assert "## Samtalsläge" in draft_prompt
    assert "FÖRSTA svar" in draft_prompt
    assert "Tidigare i samtalet" not in draft_prompt


@pytest.mark.anyio
async def test_andra_turen_bar_med_utskriften_av_samtalet():
    storage, llm = MemoryStorage(), _CapturingLLM()
    await _turn(storage, llm, "Vilka betalsätt accepterar ni?")
    await _turn(storage, llm, "Går det med faktura?")

    draft_prompt = llm.user_by_skill["cs:draft-response"]
    assert "fortsättning" in draft_prompt
    assert "FÖRSTA svar" not in draft_prompt
    # Både kundens fråga och agentens eget svar från tur 1 ska finnas med —
    # utan agentens replik kan modellen inte veta att den redan hälsat.
    assert "Kunden: Vilka betalsätt accepterar ni?" in draft_prompt
    assert "Du: Du kan betala med Swish eller kort." in draft_prompt


@pytest.mark.anyio
async def test_utskriften_kapas_till_de_senaste_turerna():
    storage, llm = MemoryStorage(), _CapturingLLM()
    for i in range(6):
        await _turn(storage, llm, f"Fråga {i}")

    draft_prompt = llm.user_by_skill["cs:draft-response"]
    transcript = draft_prompt.split("## Tidigare i samtalet\n", 1)[1]
    rader = [r for r in transcript.splitlines() if r.startswith(("Kunden:", "Du:"))]
    assert len(rader) <= MAX_HISTORY_TURNS

    # Kapningen tar de SENASTE turerna, inte de första. "Fråga 5" är det
    # AKTUELLA meddelandet och hör inte hemma i utskriften — historiken hämtas
    # innan ärendet skapas, så den innehåller bara avslutade turer.
    assert "Kunden: Fråga 4" in transcript
    assert "Fråga 5" not in transcript
    assert "Fråga 0" not in transcript
    assert "Fråga 1" not in transcript


# --- Kodgrinden mot hängande avslutningsfras ------------------------------


@pytest.mark.parametrize(
    "text,vantat",
    [
        ("Vi skickar en ny.\n\nVänliga hälsningar,", "Vi skickar en ny."),
        ("Vi skickar en ny.\n\nMed vänliga hälsningar,", "Vi skickar en ny."),
        ("Vi skickar en ny.\nMvh,", "Vi skickar en ny."),
        ("Vi skickar en ny.\n\nVänligen,", "Vi skickar en ny."),
        ("Vi skickar en ny.\n\nHälsningar", "Vi skickar en ny."),
        # Får INTE kapa när frasen faktiskt följs av ett namn.
        ("Vi skickar en ny.\n\nVänliga hälsningar,\nLivrustning AB",
         "Vi skickar en ny.\n\nVänliga hälsningar,\nLivrustning AB"),
        # Får inte äta text som bara innehåller ordet.
        ("Vi skickar hälsningar från lagret.", "Vi skickar hälsningar från lagret."),
    ],
)
def test_strip_dangling_sign_off(text, vantat):
    assert strip_dangling_sign_off(text) == vantat


@pytest.mark.anyio
async def test_hangande_signatur_nar_aldrig_kunden():
    storage = MemoryStorage()
    llm = _CapturingLLM(final_reply="Du kan betala med Swish.\n\nVänliga hälsningar,")
    result = await _turn(storage, llm, "Vilka betalsätt accepterar ni?")

    assert result["reply"] == "Du kan betala med Swish."


# --- Overlayen är bunden till stegen som skriver text ----------------------


def test_samtalsoverlay_bunden_till_bade_utkast_och_humanisering():
    """Humaniseraren är sista handen på texten. Utan overlayen där kan den
    sätta tillbaka hälsningen som utkaststeget just avstått från."""
    overlays = {step.skill: step.overlay for step in SUPPORT_V1.steps}
    assert overlays["cs:draft-response"] == "support-conversation"
    assert overlays["snajp:humanizer-svenska"] == "support-conversation"


# -- Påhoppsspärren i svarsvägen -------------------------------------------
#
# abuse_gate har sina egna enhetstester i tests/leads/test_abuse_gate.py.
# Testerna nedan bevisar något annat: att support-agenten faktiskt ANROPAR den
# och att beslutet får genomslag i svaret.


@pytest.mark.anyio
async def test_hot_ersatter_svaret_och_eskalerar():
    """Modellen har redan skrivit ett utkast. Det kastas — att fortsätta
    hjälpa som om inget hänt är att lära den som hotar att det fungerar."""
    storage, llm = MemoryStorage(), _CapturingLLM()
    resultat = await _turn(storage, llm, "Jag ska döda dig.")

    assert resultat["escalated"] is True
    assert "avslutar" in resultat["reply"]
    assert "Swish" not in resultat["reply"]  # modellens utkast är borta
    assert "allvarlig" in (resultat["escalation_reason"] or "")


@pytest.mark.anyio
async def test_riktad_forolampning_papekas_men_hjalpen_fortsatter():
    storage, llm = MemoryStorage(), _CapturingLLM()
    resultat = await _turn(storage, llm, "Du är helt korkad. Vilka betalsätt har ni?")

    assert "vill inte bli tilltalad så" in resultat["reply"]
    # Hjälpen finns kvar EFTER påpekandet.
    assert "Swish" in resultat["reply"]


@pytest.mark.anyio
async def test_arg_kund_far_inget_papekande():
    """Den som skriver så är arg på en verklig sak och har oftast rätt."""
    storage, llm = MemoryStorage(), _CapturingLLM()
    resultat = await _turn(storage, llm, "Det här är ju för jävligt, jag har väntat i tre veckor.")

    assert "vill inte bli tilltalad" not in resultat["reply"]
    assert "avslutar" not in resultat["reply"]
    # Men tonläget når prompten, så svaret kan möta känslan.
    assert "frustrerad" in llm.user_by_skill["cs:draft-response"]
