"""Flerturssamtal i bokföringschatten — regressionstestet för 500:an.

## Varför den här filen inte mockar `Runner.run`

`tests/agent/test_leads_agent_wiring.py` mockar `Runner.run` när den prövar
onboarding-turen. Det är rimligt där, men det är precis därför den här buggen
kunde nå drift: felet SATT i Runner.run, i konverteringen från SDK:ns
indataposter till Chat Completions-meddelanden. Ett test som mockar bort
Runner hade varit grönt genom hela incidenten.

Här mockas därför bara NÄTVERKSGRÄNSEN — `chat.completions.create` — och allt
annat körs skarpt: den riktiga `Agent`, den riktiga `Runner`, den riktiga
`Converter`, den riktiga beloppsgrinden.

## Varför DeepSeek och inte OpenAI

`LLM_PROVIDER=deepseek` är vad som faktiskt kör (se docs/JURIDIK_ATGARDER.md
och app/agent/llm.py). Klienten byggs därför med DeepSeeks base_url, vilket
gör `ChatCmplHelpers.is_openai()` falsk och håller `store`/`stream_options`
borta — samma anropsform som i drift. Ett test mot en OpenAI-uppsättning hade
prövat en konfiguration ingen kund möter.
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from app.agent.bookkeeping_agent import (
    FALLT_SVAR,
    bygg_turhistorik,
    run_bookkeeping_chat_turn,
)
from app.config import get_settings
from app.storage.memory import MemoryStorage

TENANT = "tenant-a-11111111"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _fake_deepseek_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _FakeDeepSeek:
    """En riktig AsyncOpenAI-klient mot DeepSeeks base_url, med enda skillnaden
    att `create` svarar ur minnet i stället för över nätet.

    Sparar `messages` från varje anrop — de är testets faktiska mätpunkt: vi
    vill veta vad konverteringen producerade, inte bara att inget kastade.
    """

    def __init__(self, svar: list[str]):
        self.svar = list(svar)
        self.messages_seen: list[list[dict]] = []
        self.klient = AsyncOpenAI(
            api_key="test-key-not-a-real-credential-000000",
            base_url="https://api.deepseek.com",
        )
        self.klient.chat.completions.create = self._create  # type: ignore[method-assign]

    async def _create(self, **kwargs) -> ChatCompletion:
        self.messages_seen.append(kwargs["messages"])
        text = self.svar.pop(0) if self.svar else "Klart."
        return ChatCompletion(
            id="chatcmpl-test",
            created=int(time.time()),
            model=kwargs.get("model", "deepseek-chat"),
            object="chat.completion",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(role="assistant", content=text),
                )
            ],
        )


def _modell(fake: _FakeDeepSeek):
    from agents import OpenAIChatCompletionsModel

    return OpenAIChatCompletionsModel(model="deepseek-chat", openai_client=fake.klient)


# -- 1. Formen på historiken ----------------------------------------------


def test_assistentraden_bar_type_message():
    """Utan `type: "message"` fångas raden som ett EasyInputMessage och dess
    `output_text` går till `extract_all_content`, som inte känner typen.

    Det är hela buggen, i en rad.
    """
    poster = bygg_turhistorik(
        [
            {"roll": "kund", "text": "hur mycket moms i augusti?"},
            {"roll": "assistent", "text": "Du har 3 125 kr."},
        ],
        "och i juli?",
    )
    assistent = [p for p in poster if p.get("role") == "assistant"]
    assert len(assistent) == 1
    assert assistent[0]["type"] == "message", (
        "Assistentraden saknar type=message — SDK:t kommer att kasta "
        "UserError: Unknown content på output_text."
    )


def test_historiken_gar_genom_sdk_konverteraren_utan_att_kasta():
    """Samma kontroll som ovan, men mot SDK:ns EGEN konverterare i stället för
    mot vår förväntan om den. Går den sönder i en uppgradering vill vi veta
    det här, inte i drift."""
    from agents.models.chatcmpl_converter import Converter

    poster = bygg_turhistorik(
        [{"roll": "kund", "text": "fråga ett"}, {"roll": "assistent", "text": "svar ett"}],
        "fråga två",
    )
    meddelanden = Converter.items_to_messages(poster)
    assert [m["role"] for m in meddelanden] == ["user", "assistant", "user"]
    assert meddelanden[1]["content"] == "svar ett"


def test_gamla_formen_kastar_fortfarande():
    """Bevisar att testet ovan mäter något.

    Skulle SDK:t en dag börja acceptera `output_text` i ett EasyInputMessage
    faller det här testet, och då vet vi att regressionsskyddet ovan blivit
    tomt — inte att något gått sönder.
    """
    from agents.exceptions import UserError
    from agents.models.chatcmpl_converter import Converter

    with pytest.raises(UserError, match="Unknown content"):
        Converter.items_to_messages(
            [{"role": "assistant", "content": [{"type": "output_text", "text": "hej"}]}]
        )


def test_tomma_och_okanda_roller_faller_bort():
    poster = bygg_turhistorik(
        [
            {"roll": "kund", "text": "  "},
            {"roll": "system", "text": "ska inte med"},
            {"roll": "assistent", "text": "med"},
        ],
        "nu",
    )
    assert len(poster) == 2
    assert poster[-1]["content"][0]["text"] == "nu"


# -- 2. Hela turen, skarpt genom Runner -----------------------------------


@pytest.mark.anyio
async def test_forsta_turen_utan_historik_svarar():
    """Referenspunkten: den här turen fungerade även före rättningen."""
    storage = MemoryStorage()
    fake = _FakeDeepSeek(["Hej! Vilken period gäller det?"])

    with patch("app.agent.bookkeeping_agent.get_agent_model", return_value=_modell(fake)):
        svar = await run_bookkeeping_chat_turn(storage, TENANT, message="hej")

    assert svar["reply"] == "Hej! Vilken period gäller det?"
    assert len(fake.messages_seen) == 1


@pytest.mark.anyio
async def test_andra_turen_med_historik_svarar_ocksa():
    """Regressionstestet. Före rättningen kastade det här anropet
    `agents.exceptions.UserError: Unknown content: {'type': 'output_text'...}`
    och endpointen svarade 500."""
    storage = MemoryStorage()
    fake = _FakeDeepSeek(["I juli har jag inte hämtat några siffror än."])

    historik = [
        {"roll": "kund", "text": "hur mycket moms i augusti?"},
        {"roll": "assistent", "text": "Du har 3 125 kr i utgående moms."},
    ]
    with patch("app.agent.bookkeeping_agent.get_agent_model", return_value=_modell(fake)):
        svar = await run_bookkeeping_chat_turn(
            storage, TENANT, message="och i juli?", historik=historik
        )

    assert svar["reply"] == "I juli har jag inte hämtat några siffror än."

    # Och historiken nådde faktiskt fram — annars hade testet passerat även om
    # vi tyst hade slängt den.
    skickade = fake.messages_seen[0]
    assert [m["role"] for m in skickade] == ["system", "user", "assistant", "user"]
    assert skickade[2]["content"] == "Du har 3 125 kr i utgående moms."


@pytest.mark.anyio
async def test_lang_historik_med_flera_assistentturer():
    """Flera assistentrader, inte bara en — buggen slog på den första, men en
    rättning som bara hanterar en rad är ingen rättning."""
    storage = MemoryStorage()
    fake = _FakeDeepSeek(["Ja."])
    historik = [
        {"roll": "kund", "text": "f1"},
        {"roll": "assistent", "text": "s1"},
        {"roll": "kund", "text": "f2"},
        {"roll": "assistent", "text": "s2"},
        {"roll": "kund", "text": "f3"},
        {"roll": "assistent", "text": "s3"},
    ]
    with patch("app.agent.bookkeeping_agent.get_agent_model", return_value=_modell(fake)):
        svar = await run_bookkeeping_chat_turn(storage, TENANT, message="f4", historik=historik)

    assert svar["reply"] == "Ja."
    roller = [m["role"] for m in fake.messages_seen[0]]
    assert roller == ["system"] + ["user", "assistant"] * 3 + ["user"]


@pytest.mark.anyio
async def test_beloppsgrinden_galler_fortfarande_i_en_andra_tur():
    """Rättningen får inte råka öppna en väg förbi INV-BOOK-003.

    Ett belopp som stod i en TIDIGARE turs svar är fortfarande ogrundat i den
    här turen — siffrorna kan ha ändrats sedan dess.
    """
    storage = MemoryStorage()
    fake = _FakeDeepSeek(["Du har fortfarande 3 125 kr i utgående moms."])
    historik = [
        {"roll": "kund", "text": "hur mycket moms i augusti?"},
        {"roll": "assistent", "text": "Du har 3 125 kr i utgående moms."},
    ]
    with patch("app.agent.bookkeeping_agent.get_agent_model", return_value=_modell(fake)):
        svar = await run_bookkeeping_chat_turn(
            storage, TENANT, message="och nu?", historik=historik
        )

    assert svar["grundad"] is False
    assert svar["reply"] == FALLT_SVAR
