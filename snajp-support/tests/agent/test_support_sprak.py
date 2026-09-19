"""Svar på kundens språk (bd snipe-xtr).

Språkvalet är kundens (tenantens) inställning; språket i ett samtal är
triagens bedömning, med förra turens språk som reserv och svenska som
standard i varje tveksamhet. De fasta texterna finns på svenska och engelska.
"""

import pytest

from app.agent import support_regler, support_texter
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _inst(sprak="kundens"):
    return support_regler.normalisera({"sprak": sprak})


def test_kundens_sprak_foljer_triagens_signal():
    assert support_regler.svarsprak(_inst(), "en") == "en"
    assert support_regler.svarsprak(_inst(), "DE") == "de"
    assert support_regler.svarsprak(_inst(), "ar-SA") == "ar"


def test_svenska_vinner_varje_tveksamhet():
    assert support_regler.svarsprak(_inst(), None) == "sv"
    assert support_regler.svarsprak(_inst(), "") == "sv"
    assert support_regler.svarsprak(_inst(), "123") == "sv"
    assert support_regler.svarsprak(_inst(), {"en": 1}) == "sv"


def test_forra_turens_sprak_bar_ett_samtal_utan_signal():
    """Ett "ok" mitt i ett engelskt samtal ska inte slå om till svenska."""
    assert support_regler.svarsprak(_inst(), None, tidigare="en") == "en"
    assert support_regler.svarsprak(_inst(), "fr", tidigare="en") == "fr"


def test_alltid_svenska_ar_alltid_svenska():
    assert support_regler.svarsprak(_inst("svenska"), "en", tidigare="en") == "sv"


def test_standard_ar_kundens_sprak_och_okant_val_faller_tillbaka():
    assert support_regler.STANDARD["sprak"] == "kundens"
    assert support_regler.normalisera({"sprak": "klingon"})["sprak"] == "kundens"
    assert support_regler.spraknamn("en") == "engelska"
    assert support_regler.spraknamn("xx") == "xx"


def test_fasta_texter_finns_pa_bada_spraken_och_faller_pa_engelska():
    for nyckel in support_texter.NYCKLAR:
        svensk = support_texter.text(nyckel, "sv")
        engelsk = support_texter.text(nyckel, "en")
        assert svensk and engelsk and svensk != engelsk, nyckel
        # Ett tredje språk får den engelska texten, inte den svenska.
        assert support_texter.text(nyckel, "de") in support_texter._TEXTER["en"][nyckel]
    assert support_texter.text("kvittens", None) in support_texter._TEXTER["sv"]["kvittens"]


@pytest.mark.anyio
async def test_samtalslaget_bar_spraket():
    storage = MemoryStorage()
    kund = await storage.find_or_create_customer(TENANT, email="a@session.snajp.se", phone=None, name=None)
    assert (await storage.get_chat_state(TENANT, kund["id"]))["sprak"] is None
    await storage.save_chat_state(
        TENANT, kund["id"], lage="agent", misslyckade_i_rad=0, erbjod_manniska=False, sprak="en"
    )
    assert (await storage.get_chat_state(TENANT, kund["id"]))["sprak"] == "en"


# -- Agenten svarar på kundens språk ---------------------------------------

import json  # noqa: E402
import re  # noqa: E402
from unittest.mock import AsyncMock, patch  # noqa: E402

from app.agent.support_agent import run_support_agent  # noqa: E402
from app.config import get_settings  # noqa: E402


@pytest.fixture(autouse=True)
def _fake_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _LLM:
    def __init__(self, triage: dict | None = None, draft: str = "You can pay by card or Swish."):
        self.calls: list[str] = []
        self.user_by_skill: dict[str, str] = {}
        self.triage = triage or {}
        self.draft = draft
        self.chat = self
        self.completions = self

    async def create(self, *, messages, **_):
        skill = re.search(r"styrs av skillen (\S+?),", messages[0]["content"]).group(1)
        self.calls.append(skill)
        self.user_by_skill[skill] = messages[1]["content"]
        payload = {"sources_used": ["kb"], "context_refs": ["context_pack"]}
        payload.update({
            "cs:ticket-triage": {
                "category": "betalning", "priority": "P3", "sentiment": 0.6, "escalate": False,
                "inom_amnesomradet": True, **self.triage,
            },
            "cs:customer-research": {"findings": "ok", "confidence": 0.8, "kb_supports_answer": True,
                                     "behover_fortydligande": False},
            "cs:draft-response": {"draft": self.draft},
            "snajp:humanizer-svenska": {"final_reply": "Du kan betala med kort eller Swish."},
        }.get(skill, {}))
        message = type("M", (), {"content": json.dumps(payload, ensure_ascii=False)})()
        usage = type("U", (), {"prompt_tokens": 1, "completion_tokens": 1})()
        return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()


async def _tur(storage, llm, message, *, kund="k@session.snajp.se"):
    with patch("app.agent.step_runner.get_llm_client", return_value=llm), patch(
        "app.agent.support_agent.classify_cancellation_risk", new=AsyncMock(return_value=(0.0, 0.0))
    ):
        return await run_support_agent(
            storage, TENANT, message=message, subject="", channel="web",
            customer_email=kund, customer_name="Visitor", attachments=[],
        )


@pytest.mark.anyio
async def test_engelsk_kund_far_engelskt_svar_utan_svensk_humanisering():
    storage = MemoryStorage()
    llm = _LLM(triage={"sprak": "en", "sokfraga_sv": "betalsätt"})
    svar = await _tur(storage, llm, "How can I pay?")

    assert svar["sprak"] == "en"
    assert svar["reply"] == "You can pay by card or Swish."
    # Den svenska humaniseraren hade översatt tillbaka — den körs inte.
    assert "snajp:humanizer-svenska" not in llm.calls
    assert "engelska" in llm.user_by_skill["cs:draft-response"]
    samtal = await storage.get_chat_state(TENANT, svar["customer_id"])
    assert samtal["sprak"] == "en"


@pytest.mark.anyio
async def test_kunskapsbasen_soks_pa_svenska_nar_kunden_skriver_engelska():
    storage = MemoryStorage()
    fragor: list[str] = []

    async def spion(storage_, tenant_, fraga):
        fragor.append(fraga)
        return [{"title": "Betalsätt", "content": "Kort eller Swish.", "similarity": 0.9}]

    with patch("app.agent.support_agent._sok_kb", new=spion):
        await _tur(storage, _LLM(triage={"sprak": "en", "sokfraga_sv": "betalsätt"}), "How can I pay?")
    assert fragor[0] == "betalsätt"


@pytest.mark.anyio
async def test_alltid_svenska_ger_svenskt_svar_aven_till_engelsk_kund():
    storage = MemoryStorage()
    await storage.set_agent_settings(TENANT, agent_type="support", settings={"sprak": "svenska"})
    llm = _LLM(triage={"sprak": "en"})
    svar = await _tur(storage, llm, "How can I pay?")
    assert svar["sprak"] == "sv"
    assert "snajp:humanizer-svenska" in llm.calls
    assert "Returnera JSON: draft (svenska)." in llm.user_by_skill["cs:draft-response"]


@pytest.mark.anyio
async def test_kvittensen_under_overlamning_foljer_samtalets_sprak():
    storage = MemoryStorage()
    llm = _LLM(triage={"sprak": "en", "ber_om_manniska": True},
               draft="I'm bringing in a colleague who will take over here in the chat.")
    forsta = await _tur(storage, llm, "Can I talk to a human?")
    assert forsta["escalated"] is True

    andra = await _tur(storage, _LLM(), "Hello?")
    assert andra["reply"] in support_texter._TEXTER["en"]["kvittens"]


@pytest.mark.anyio
async def test_icke_svenskt_utkast_ber_om_ett_strangfalt_och_tal_mallformatet():
    """Kundtest på dev 2026-09-19: på engelska följde utkaststeget skillens
    mejlmall ({"To", "Re", "Draft response text", "Notes for You"}) i stället
    för JSON-fältet draft, och ett korrekt svar byttes mot reservtexten. Två
    lager: instruktionen ber uttryckligen om ETT strängfält (här), och
    avläsningen tål mallformatet ändå (_textfalt, 7da19bb)."""
    storage = MemoryStorage()
    llm = _LLM(triage={"sprak": "en", "sokfraga_sv": "leverans"})
    mall = {
        "To": "Customer",
        "Re": "Delivery",
        "Draft response text": "Your order is delivered by PostNord.",
        "Notes for You": {"tone": "friendly"},
    }
    llm.draft = mall  # type: ignore[assignment]
    svar = await _tur(storage, llm, "Which carrier is delivering it?")

    prompt = llm.user_by_skill["cs:draft-response"]
    assert "Returnera JSON med fältet draft: EN sträng" in prompt
    assert "Inte skillens mallformat" in prompt
    assert svar["reply"] == "Your order is delivered by PostNord."
