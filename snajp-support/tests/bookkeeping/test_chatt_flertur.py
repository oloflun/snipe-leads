"""Bokföringschatten över flera turer: 500:an, omförsöket, poleringen, tonen.

## Varför den här filen inte mockar `Runner.run`

`tests/agent/test_leads_agent_wiring.py` mockar `Runner.run` när den prövar
onboarding-turen. Det är rimligt där, men det är precis därför 500:an kunde nå
drift: felet SATT i Runner.run, i konverteringen från SDK:ns indataposter till
Chat Completions-meddelanden. Ett test som mockar bort Runner hade varit grönt
genom hela incidenten.

Här mockas därför bara NÄTVERKSGRÄNSEN — `chat.completions.create` — och allt
annat körs skarpt: den riktiga `Agent`, den riktiga `Runner`, den riktiga
`Converter`, de riktiga verktygen och den riktiga beloppsgrinden. När ett test
behöver att modellen slår upp något returnerar fejken ett RIKTIGT
verktygsanrop, som SDK:t exekverar mot MemoryStorage.

## Varför DeepSeek och inte OpenAI

`LLM_PROVIDER=deepseek` är vad som faktiskt kör (se docs/JURIDIK_ATGARDER.md
och app/agent/llm.py). Klienten byggs därför med DeepSeeks base_url, vilket
gör `ChatCmplHelpers.is_openai()` falsk och håller `store`/`stream_options`
borta — samma anropsform som i drift. Ett test mot en OpenAI-uppsättning hade
prövat en konfiguration ingen kund möter.
"""

from __future__ import annotations

import contextlib
import json
import time
from dataclasses import dataclass
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)

from app.agent.bookkeeping_agent import (
    FALLT_SVAR_VARIANTER,
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


async def _underlag(storage: MemoryStorage, tenant: str, *, motpart: str, brutto: str):
    return await storage.create_bk_underlag(
        tenant,
        sha256=f"sha-{tenant}-{motpart}",
        filnamn=f"{motpart}.pdf",
        mimetyp="application/pdf",
        status="klar",
        datum="2026-08-05",
        motpart=motpart,
        brutto=Decimal(brutto),
        momssats=Decimal("0.25"),
        riktning="kostnad",
        kategori="drivmedel",
    )


@dataclass(frozen=True)
class Verktygsanrop:
    """Ett steg där modellen slår upp något i stället för att svara.

    Fejken returnerar det som ett riktigt `tool_calls`-svar, så SDK:t kör det
    RIKTIGA verktyget mot MemoryStorage och lägger resultatet i
    `context.resultat`. Det är den vägen INV-BOOK-003 mäter, och en fejk som
    fyllde listan direkt hade testat vår mock i stället för vår kod.
    """

    namn: str
    argument: dict


def verktyg(namn: str, **argument) -> Verktygsanrop:
    return Verktygsanrop(namn, argument)


class _FakeDeepSeek:
    """En riktig AsyncOpenAI-klient mot DeepSeeks base_url, med enda skillnaden
    att `create` svarar ur ett manus i stället för över nätet.

    Manuset är en lista: en sträng = modellen svarar, ett `Verktygsanrop` =
    modellen slår upp något först.

    Sparar `messages` från varje anrop — de är testets faktiska mätpunkt: vi
    vill veta vad konverteringen producerade, inte bara att inget kastade.
    """

    def __init__(self, manus: list[str | Verktygsanrop]):
        self.manus = list(manus)
        self.messages_seen: list[list[dict]] = []
        self.klient = AsyncOpenAI(
            api_key="test-key-not-a-real-credential-000000",
            base_url="https://api.deepseek.com",
        )
        self.klient.chat.completions.create = self._create  # type: ignore[method-assign]

    @property
    def modellanrop(self) -> int:
        return len(self.messages_seen)

    def _svar(self, message: ChatCompletionMessage, finish: str) -> ChatCompletion:
        return ChatCompletion(
            id="chatcmpl-test",
            created=int(time.time()),
            model="deepseek-chat",
            object="chat.completion",
            choices=[Choice(finish_reason=finish, index=0, message=message)],
        )

    async def _create(self, **kwargs) -> ChatCompletion:
        self.messages_seen.append(kwargs["messages"])
        steg = self.manus.pop(0) if self.manus else "Klart."

        if isinstance(steg, Verktygsanrop):
            return self._svar(
                ChatCompletionMessage(
                    role="assistant",
                    content=None,
                    tool_calls=[
                        ChatCompletionMessageToolCall(
                            id=f"call_{len(self.messages_seen)}",
                            type="function",
                            function=Function(
                                name=steg.namn, arguments=json.dumps(steg.argument)
                            ),
                        )
                    ],
                ),
                "tool_calls",
            )

        return self._svar(ChatCompletionMessage(role="assistant", content=steg), "stop")


def _modell(fake: _FakeDeepSeek):
    from agents import OpenAIChatCompletionsModel

    return OpenAIChatCompletionsModel(model="deepseek-chat", openai_client=fake.klient)


@contextlib.contextmanager
def _chatt(fake: _FakeDeepSeek, *, polerat: str | None = None):
    """Kopplar in den fejkade modellen OCH poleringssteget.

    Poleringen mockas separat och inte via `fake`: den går inte genom Agents
    SDK:t utan genom `step_runner.run_step`, alltså genom `get_llm_client()` —
    och den klienten pekar på api.deepseek.com. Utan den här patchen gör varje
    grön tur ett SKARPT nätverksanrop, som `_polera` sedan sväljer tyst.
    Testsviten ska vara hermetisk (se tests/conftest.py), och ett anrop som
    "bara" tar en timeout och swallow:as är fortfarande ett anrop ut på
    internet.

    `polerat=None` => poleringen lämnar tillbaka tomt, och `_polera` behåller
    då originaltexten.

    Kunskapsfångsten patchas SEPARAT, trots att den också går genom
    `run_step`. Delade de mock hade `polering.assert_not_awaited()` i
    testet "poleringen rör aldrig ett fällt svar" blivit sant av fel skäl:
    kunskapssteget körs just på den vägen, och en gemensam räknare hade inte
    kunnat skilja de två stegen åt.
    """
    with patch("app.agent.bookkeeping_agent.get_agent_model", return_value=_modell(fake)):
        with patch(
            "app.agent.bookkeeping_agent._fanga_kunskap",
            new=AsyncMock(return_value={"reveals_gap": False}),
        ):
            with patch(
                "app.agent.bookkeeping_agent.run_step",
                new=AsyncMock(
                    return_value={"final_reply": polerat if polerat is not None else ""}
                ),
            ) as polering:
                yield polering


def _text(meddelande: dict) -> str:
    innehall = meddelande.get("content")
    if isinstance(innehall, str):
        return innehall
    if isinstance(innehall, list):
        return " ".join(str(d.get("text", "")) for d in innehall if isinstance(d, dict))
    return ""


# -- 1. Formen på historiken ----------------------------------------------


def test_assistentraden_bar_type_message():
    """Utan `type: "message"` fångas raden som ett EasyInputMessage och dess
    `output_text` går till `extract_all_content`, som inte känner typen.

    Det är hela 500:an, i en rad.
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
    mot vår förväntan om den. Går den sönder i en uppgradering vill vi veta det
    här, inte i drift."""
    from agents.models.chatcmpl_converter import Converter

    poster = bygg_turhistorik(
        [{"roll": "kund", "text": "fråga ett"}, {"roll": "assistent", "text": "svar ett"}],
        "fråga två",
    )
    meddelanden = Converter.items_to_messages(poster)
    assert [m["role"] for m in meddelanden] == ["user", "assistant", "user"]
    assert meddelanden[1]["content"] == "svar ett"


def test_assistentraden_bar_id_och_type_som_grinden_kraver():
    """De två nycklar SDK:ns konverterare grindar på, var för sig.

    Testet ovan går genom konverteraren och säger "det funkar". Det här säger
    VARFÖR, och det är skillnaden mellan ett skydd som överlever en refaktor
    och ett som tyst blir tomt: `maybe_response_output_message` kräver
    `type == "message"`, `role == "assistant"` OCH — sedan openai-agents
    0.22.0 — att både `id` och `content` finns i posten.

    Faller just det här testet har någon plockat bort ett fält som ser
    onödigt ut. Det är det inte: utan `id` faller raden igenom hela
    konverteraren och ger `UserError: Unhandled item type or structure` på tur
    två, alltså i drift och inte här.
    """
    poster = bygg_turhistorik([{"roll": "assistent", "text": "svar"}], "ny fråga")
    assistentrader = [p for p in poster if p.get("role") == "assistant"]
    assert len(assistentrader) == 1
    rad = assistentrader[0]

    assert rad["type"] == "message"
    saknas = {"id", "content"} - set(rad)
    assert not saknas, (
        "openai-agents >=0.22 grindar på att både id och content finns i "
        f"posten. Saknas: {sorted(saknas)}"
    )
    # Påhittat, och ska SE påhittat ut. Ett `msg_...` hade inbjudit någon att
    # tro att det kom från API:t och går att slå upp.
    assert not str(rad["id"]).startswith("msg_")


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

    with _chatt(fake):
        svar = await run_bookkeeping_chat_turn(storage, TENANT, message="hej")

    assert svar["reply"] == "Hej! Vilken period gäller det?"
    assert fake.modellanrop == 1


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
    with _chatt(fake):
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
    with _chatt(fake):
        svar = await run_bookkeeping_chat_turn(storage, TENANT, message="f4", historik=historik)

    assert svar["reply"] == "Ja."
    roller = [m["role"] for m in fake.messages_seen[0]]
    assert roller == ["system"] + ["user", "assistant"] * 3 + ["user"]


@pytest.mark.anyio
async def test_beloppsgrinden_galler_fortfarande_i_en_andra_tur():
    """Rättningen får inte råka öppna en väg förbi INV-BOOK-003.

    Ett belopp som stod i en TIDIGARE turs svar är fortfarande ogrundat i den
    här turen — siffrorna kan ha ändrats sedan dess. Modellen får ETT försök
    till (avsnitt 3), och när den upprepar sitt ogrundade tal faller det.
    """
    storage = MemoryStorage()
    fake = _FakeDeepSeek(
        [
            "Du har fortfarande 3 125 kr i utgående moms.",
            "Det är 3 125 kr, som jag sa.",  # omförsöket hämtar inte heller
        ]
    )
    historik = [
        {"roll": "kund", "text": "hur mycket moms i augusti?"},
        {"roll": "assistent", "text": "Du har 3 125 kr i utgående moms."},
    ]
    with _chatt(fake):
        svar = await run_bookkeeping_chat_turn(
            storage, TENANT, message="och nu?", historik=historik
        )

    assert svar["grundad"] is False
    assert svar["reply"] in FALLT_SVAR_VARIANTER


# -- 3. Ett försök till innan chatten ger upp (DEL 3.4) --------------------


@pytest.mark.anyio
async def test_ett_omforsok_raddar_en_tur_som_annars_hade_fallit():
    """Kärnan i "mindre lätt att ge upp".

    Modellen svarar först ur minnet, får en tillsägelse om att den MÅSTE hämta
    talet, hämtar det, och kunden får ett riktigt svar i stället för
    FALLT_SVAR. Utan omförsöket hade den här turen slutat i canned-texten.

    Verktygsanropet är ÄKTA: SDK:t kör `hamta_periodrapport` mot
    MemoryStorage, och det är dess svar beloppsgrinden sedan mäter mot.
    """
    storage = MemoryStorage()
    await _underlag(storage, TENANT, motpart="Circle K", brutto="1250.00")

    fake = _FakeDeepSeek(
        [
            "Du har ungefär 1 000 kr i kostnader.",  # ogrundat: inget hämtat
            verktyg("hamta_periodrapport", fran="2026-08-01", till="2026-08-31"),
            "Kostnaderna är 1 000,00 kr exklusive moms.",
        ]
    )

    with _chatt(fake):
        svar = await run_bookkeeping_chat_turn(
            storage, TENANT, message="vad har jag för kostnader i augusti?"
        )

    assert svar["grundad"] is True
    assert svar["reply"] == "Kostnaderna är 1 000,00 kr exklusive moms."
    assert svar["verktygsanrop"] == 1, "Verktyget kördes inte på riktigt."


@pytest.mark.anyio
async def test_omforsoket_sager_vad_som_gick_fel_och_kraver_ett_verktyg():
    """Tillsägelsen är hela mekanismen — den ska stå i klartext i indatan."""
    storage = MemoryStorage()
    fake = _FakeDeepSeek(["Cirka 12 000 kr.", "Jag vet inte."])

    with _chatt(fake):
        await run_bookkeeping_chat_turn(storage, TENANT, message="hur mycket?")

    sista = _text(fake.messages_seen[1][-1])
    assert "MÅSTE anropa ett verktyg" in sista
    assert "12 000" in sista, "Tillsägelsen säger inte VILKET tal som fällde."


@pytest.mark.anyio
async def test_ett_grundat_forstasvar_kostar_inget_extra_anrop():
    """Omförsöket får inte bli ett andra anrop i normalfallet."""
    storage = MemoryStorage()
    fake = _FakeDeepSeek(["Momssatsen är 25 % på köpet."])

    with _chatt(fake):
        svar = await run_bookkeeping_chat_turn(storage, TENANT, message="vilken momssats?")

    assert svar["grundad"] is True
    assert fake.modellanrop == 1


@pytest.mark.anyio
async def test_omforsoket_ar_inte_en_uppmjukning_av_inv_book_003():
    """Gränsen som INTE flyttades.

    Ett tal som fortfarande saknas i verktygssvaret efter omförsöket fälls
    fortfarande. Omförsöket ger modellen en chans att HÄMTA talet, inte rätt
    att behålla ett den hittat på.
    """
    storage = MemoryStorage()
    await _underlag(storage, TENANT, motpart="Circle K", brutto="1250.00")

    fake = _FakeDeepSeek(
        [
            "Du har 9 999 kr i kostnader.",
            verktyg("hamta_periodrapport", fran="2026-08-01", till="2026-08-31"),
            "Det är 9 999 kr.",  # hämtade — och struntade i vad den fick
        ]
    )
    with _chatt(fake):
        svar = await run_bookkeeping_chat_turn(storage, TENANT, message="kostnader i augusti?")

    assert svar["verktygsanrop"] == 1, "Verktyget kördes inte — testet mäter fel sak."
    assert svar["grundad"] is False
    assert svar["reply"] in FALLT_SVAR_VARIANTER


# -- 4. Poleringen ligger EFTER grinden (DEL 5) ---------------------------


@pytest.mark.anyio
async def test_poleringen_kor_pa_ett_grundat_svar():
    storage = MemoryStorage()
    fake = _FakeDeepSeek(["Momssatsen ar 25 % pa kopet."])

    with _chatt(fake, polerat="Momssatsen är 25 % på köpet.") as polering:
        svar = await run_bookkeeping_chat_turn(storage, TENANT, message="vilken momssats?")

    polering.assert_awaited_once()
    assert svar["reply"] == "Momssatsen är 25 % på köpet."


@pytest.mark.anyio
async def test_poleringen_ror_aldrig_ett_fallt_svar():
    """Samma ordning som abuse-repliken i support: ett kontrollerat svar ska
    inte skrivas om av ett steg som kommer efter."""
    storage = MemoryStorage()
    fake = _FakeDeepSeek(["Cirka 12 000 kr.", "Fortfarande cirka 12 000 kr."])

    with _chatt(fake, polerat="EN OMSKRIVEN TEXT") as polering:
        svar = await run_bookkeeping_chat_turn(storage, TENANT, message="hur mycket?")

    assert svar["reply"] in FALLT_SVAR_VARIANTER
    polering.assert_not_awaited()


@pytest.mark.anyio
async def test_en_polering_som_andrar_ett_belopp_kastas():
    """Poleringen får inte bli vägen förbi INV-BOOK-003.

    Humaniseraren skriver om text. Skriver den om ett belopp till "cirka" är
    svaret inte längre grundat, och då behålls det opolerade — sant och stelt
    slår ledigt och fel.
    """
    storage = MemoryStorage()
    await _underlag(storage, TENANT, motpart="Circle K", brutto="1250.00")
    fake = _FakeDeepSeek(
        [
            verktyg("hamta_periodrapport", fran="2026-08-01", till="2026-08-31"),
            "Kostnaderna är 1 000,00 kr.",
        ]
    )

    with _chatt(fake, polerat="Kostnaderna ligger på cirka 990 kr."):
        svar = await run_bookkeeping_chat_turn(storage, TENANT, message="kostnader i augusti?")

    assert svar["grundad"] is True
    assert svar["reply"] == "Kostnaderna är 1 000,00 kr."


# -- 5. Tonläget når chatten (DEL 4) --------------------------------------


@pytest.mark.anyio
async def test_en_stressad_kund_ger_en_tonlagesinstruktion():
    storage = MemoryStorage()
    fake = _FakeDeepSeek(["Jag hjälper dig."])

    with _chatt(fake):
        svar = await run_bookkeeping_chat_turn(
            storage,
            TENANT,
            message="momsdeklarationen ska in på fredag och jag får inte ihop det",
        )

    assert svar["tonlage"] == "oro"
    skickat = "\n".join(_text(m) for m in fake.messages_seen[0])
    assert "Kunden är stressad" in skickat


@pytest.mark.anyio
async def test_en_vanlig_fraga_ger_ingen_tonlagesinstruktion():
    storage = MemoryStorage()
    fake = _FakeDeepSeek(["Utgående moms är momsen på det du säljer."])

    with _chatt(fake):
        svar = await run_bookkeeping_chat_turn(storage, TENANT, message="vad är utgående moms?")

    assert svar["tonlage"] == "inget"
    assert len(fake.messages_seen[0]) == 2, "Något lades till som inte skulle det."


@pytest.mark.anyio
async def test_ett_hot_eskalerar_inte_chatten_men_syns_i_tonlaget():
    """`oro` är ett tonläge, inte en eskaleringsnivå — och `allvarlig` ändrade
    inte betydelse när den fjärde nivån tillkom."""
    from app.moderation.abuse_gate import check_abuse

    assert check_abuse("momsen ska in på fredag").ska_eskalera is False
    assert check_abuse("jag ska döda dig").ska_eskalera is True


# -- 6. Kunskapsfangst (DEL 5) --------------------------------------------


@pytest.mark.anyio
async def test_kunskapsfangsten_kor_bara_nar_svaret_fallde():
    """Support kor sitt steg pa varje arende. Har hade det blivit ett extra
    LLM-anrop pa varje "vad ar utgaende moms?" — en fraga som inte avslojar
    nagon lucka. Chatten svarar dessutom en manniska som vantar."""
    storage = MemoryStorage()
    fake = _FakeDeepSeek(["Momssatsen ar 25 % pa kopet."])

    with patch("app.agent.bookkeeping_agent.get_agent_model", return_value=_modell(fake)):
        with patch("app.agent.bookkeeping_agent.run_step", new=AsyncMock(return_value={})):
            with patch(
                "app.agent.bookkeeping_agent._fanga_kunskap",
                new=AsyncMock(return_value={"reveals_gap": False}),
            ) as kunskap:
                await run_bookkeeping_chat_turn(storage, TENANT, message="vilken momssats?")

    kunskap.assert_not_awaited()


@pytest.mark.anyio
async def test_kunskapsfangsten_kor_nar_svaret_fallde():
    storage = MemoryStorage()
    fake = _FakeDeepSeek(["Cirka 12 000 kr.", "Fortfarande cirka 12 000 kr."])

    with patch("app.agent.bookkeeping_agent.get_agent_model", return_value=_modell(fake)):
        with patch("app.agent.bookkeeping_agent.run_step", new=AsyncMock(return_value={})):
            with patch(
                "app.agent.bookkeeping_agent._fanga_kunskap",
                new=AsyncMock(return_value={"reveals_gap": True, "gap_kind": "verktyg"}),
            ) as kunskap:
                svar = await run_bookkeeping_chat_turn(
                    storage, TENANT, message="hur mycket drog jag av pa bilen?"
                )

    kunskap.assert_awaited_once()
    assert svar["kunskapslucka"]["reveals_gap"] is True


@pytest.mark.anyio
async def test_ett_trasigt_kunskapssteg_faller_inte_turen():
    """Kunden har redan fatt sitt svar nar steget kors."""
    storage = MemoryStorage()
    fake = _FakeDeepSeek(["Cirka 12 000 kr.", "Fortfarande cirka 12 000 kr."])

    with patch("app.agent.bookkeeping_agent.get_agent_model", return_value=_modell(fake)):
        with patch(
            "app.agent.bookkeeping_agent.run_step",
            new=AsyncMock(side_effect=RuntimeError("steget dog")),
        ):
            svar = await run_bookkeeping_chat_turn(storage, TENANT, message="hur mycket?")

    assert svar["reply"] in FALLT_SVAR_VARIANTER
    assert svar["kunskapslucka"]["reveals_gap"] is False
    assert "RuntimeError" in svar["kunskapslucka"]["fel"]
