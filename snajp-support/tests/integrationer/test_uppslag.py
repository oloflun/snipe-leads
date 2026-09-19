"""Integrationsuppslaget: modellen väljer, koden validerar, tar tak och kör.

LLM:en är fejkad på samma sätt som i tests/agent/test_support_agent_wiring.py
(bara nätverksgränsen mockas). Allt annat är den riktiga kodvägen: katalogen
ur lagringen, run_step med overlay och kontrakt, vakten, ifyllnaden.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest

from app.agent.step_runner import RunTrace, run_step
from app.agentcore.packs import RunLedger
from app.config import get_settings
from app.integrationer import lagring, uppslag
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"


@pytest.fixture(autouse=True)
def _fejkad_nyckel(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _FejkLLM:
    """Svarar på integrationssteget med förinspelade rundor."""

    def __init__(self, rundor: list[dict]):
        self.rundor = list(rundor)
        self.prompter: list[list[dict]] = []
        self.chat = self
        self.completions = self

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        assert "support-integrationsuppslag" in messages[0]["content"]
        self.prompter.append(messages)
        payload = {"sources_used": [], "context_refs": ["context_pack"], **self.rundor.pop(0)}
        message = type("M", (), {"content": json.dumps(payload, ensure_ascii=False)})()
        usage = type("U", (), {"prompt_tokens": 10, "completion_tokens": 5})()
        return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()


KONFIG = {
    "requests": [
        {
            "name": "Hitta kund",
            "description": "Slår upp kundens id med e-post.",
            "method": "GET",
            "url": "https://crm.example.com/kunder?email={{kund.email}}",
            "headers": {"Authorization": "Bearer {{hemlighet.token}}"},
            "responsePath": "kunder[0].id",
        },
        {
            "name": "Ordrar",
            "description": "Kundens ordrar.",
            "method": "GET",
            "url": "https://crm.example.com/kunder/{{kund_id}}/ordrar",
            "headers": {"Authorization": "Bearer {{hemlighet.token}}"},
        },
        {
            "name": "Avboka",
            "description": "Avbokar en order.",
            "method": "POST",
            "url": "https://crm.example.com/ordrar/{{ordernummer}}/avboka",
            "headers": {"Authorization": "Bearer {{hemlighet.token}}"},
        },
        {
            "name": "Ändra adress",
            "description": "Ändrar leveransadress.",
            "method": "PATCH",
            "url": "https://crm.example.com/ordrar/{{ordernummer}}",
            "headers": {"Authorization": "Bearer {{hemlighet.token}}"},
            "body": {"adress": "{{adress}}"},
        },
    ]
}

KONTEXT = uppslag.kontextvarden(
    kund_email="kund@example.com",
    kund_namn="Kim",
    kund_id="k-1",
    arende_id="a-1",
    kategori="leverans",
    kanal="web",
    tenant_namn="Testbutiken",
)


async def _med_integration(storage) -> None:
    await lagring.skapa(
        storage,
        TENANT,
        typ="http",
        namn="CRM",
        beskrivning="",
        konfig=KONFIG,
        hemligheter={"token": "hemlig-crm-token-99"},
    )


async def _kor(storage, llm, *, is_test=False):
    with patch("app.agent.step_runner.get_llm_client", return_value=llm):
        return await uppslag.hamta(
            storage,
            TENANT,
            steg=run_step,
            ledger=RunLedger(satisfied={"context_pack", "skill:cs:ticket-triage"}),
            trace=RunTrace(),
            case_context="## Ärendet\nVar är min order?",
            kontext=KONTEXT,
            is_test=is_test,
        )


@pytest.mark.anyio
async def test_utan_integrationer_gors_inget_llm_anrop():
    llm = _FejkLLM([])
    underlag = await _kor(MemoryStorage(), llm)
    assert not underlag and llm.prompter == []


@pytest.mark.anyio
async def test_tva_rundor_kedjar_kund_till_ordrar(svara):
    storage = MemoryStorage()
    await _med_integration(storage)

    def crm(request):
        if request.url.path == "/kunder":
            assert request.url.params["email"] == "kund@example.com"
            return httpx.Response(200, json={"kunder": [{"id": "K-77"}]})
        assert request.url.path == "/kunder/K-77/ordrar"
        return httpx.Response(200, json=[{"order": "A-17", "status": "skickad"}])

    mottagna = svara(crm)
    llm = _FejkLLM(
        [
            {"anrop": [{"verktyg": "request_hitta_kund", "argument": {}}], "klar": False},
            {"anrop": [{"verktyg": "request_ordrar", "argument": {"kund_id": "K-77"}}], "klar": True},
        ]
    )
    underlag = await _kor(storage, llm)

    assert len(mottagna) == 2 and underlag.rundor == 2
    assert all(r.headers["authorization"] == "Bearer hemlig-crm-token-99" for r in mottagna)
    # Runda 2 såg svaret från runda 1, inramat som opålitligt.
    runda2 = llm.prompter[1][1]["content"]
    assert "K-77" in runda2 and "untrusted-data" in runda2
    # Blocket bär svaren, opålitligt inramat; hemligheten syns aldrig.
    assert "A-17" in underlag.block and "untrusted-data" in underlag.block
    assert "hemlig-crm-token-99" not in underlag.block
    assert "hemlig-crm-token-99" not in json.dumps(llm.prompter, ensure_ascii=False)
    assert any("A-17" in k for k in underlag.kallor)
    assert [p["verktyg"] for p in underlag.logg] == ["request_hitta_kund", "request_ordrar"]


@pytest.mark.anyio
async def test_katalogen_bar_aldrig_url_eller_nyckel():
    storage = MemoryStorage()
    await _med_integration(storage)
    llm = _FejkLLM([{"anrop": [], "klar": True}])
    await _kor(storage, llm)
    prompt = llm.prompter[0][1]["content"]
    assert "request_ordrar" in prompt
    assert "crm.example.com" not in prompt
    assert "hemlig-crm-token-99" not in prompt


@pytest.mark.anyio
async def test_pahittat_verktyg_och_for_manga_anrop(svara):
    storage = MemoryStorage()
    await _med_integration(storage)
    mottagna = svara(lambda r: httpx.Response(200, json={"kunder": [{"id": "K"}]}))
    llm = _FejkLLM(
        [
            {
                "anrop": [
                    {"verktyg": "request_radera_allt", "argument": {}},
                    {"verktyg": "request_hitta_kund", "argument": {}},
                    {"verktyg": "request_hitta_kund", "argument": {}},  # dubblett
                    {"verktyg": "request_ordrar", "argument": {"kund_id": "1"}},
                    {"verktyg": "request_ordrar", "argument": {"kund_id": "2"}},  # fjärde: över taket
                ],
                "klar": True,
            }
        ]
    )
    underlag = await _kor(storage, llm)
    loggade = [p["verktyg"] for p in underlag.logg]
    assert "request_radera_allt" in loggade  # nekat, inte anropat
    assert len(mottagna) == 1  # tre första valen: påhittat, anropat, dubblett
    assert next(p for p in underlag.logg if p["verktyg"] == "request_radera_allt")["ok"] is False


@pytest.mark.anyio
async def test_hogst_ett_skrivande_anrop_per_arende(svara):
    storage = MemoryStorage()
    await _med_integration(storage)
    mottagna = svara(lambda r: httpx.Response(200, json={"ok": True}))
    llm = _FejkLLM(
        [
            {
                "anrop": [
                    {"verktyg": "request_avboka", "argument": {"ordernummer": "A-1"}},
                    {"verktyg": "request_andra_adress", "argument": {"ordernummer": "A-1", "adress": "X"}},
                ],
                "klar": True,
            }
        ]
    )
    underlag = await _kor(storage, llm)
    assert len(mottagna) == 1 and mottagna[0].url.path == "/ordrar/A-1/avboka"
    nekad = next(p for p in underlag.logg if p["verktyg"] == "request_andra_adress")
    assert nekad["ok"] is False and nekad["skrivande"] is True


@pytest.mark.anyio
async def test_testchatten_simulerar_skrivande_anrop():
    storage = MemoryStorage()
    await _med_integration(storage)
    llm = _FejkLLM([{"anrop": [{"verktyg": "request_avboka", "argument": {"ordernummer": "A-1"}}], "klar": True}])
    underlag = await _kor(storage, llm, is_test=True)  # ingen transport: ett anrop hade fällt testet
    assert underlag.logg[0]["simulerad"] is True
    assert underlag.kallor == []  # ett simulerat anrop är ingen faktakälla
    assert "simulerat" in underlag.block


@pytest.mark.anyio
async def test_foljdfragan_ber_om_nytt_uppslag_med_samtalets_identifierare(svara):
    """Uppmätt i development: en följdfråga ("Which carrier?") fick inget nytt
    uppslag eftersom svaret "redan stod i förra svaret", och lämnades sedan
    över. Agentens egna svar räknas aldrig som källa, så steget måste be om
    ett nytt uppslag. Både overlayen och uppgiften säger det."""
    storage = MemoryStorage()
    await _med_integration(storage)
    llm = _FejkLLM([{"anrop": [], "klar": True}])
    await _kor(storage, llm)
    system, anvandare = llm.prompter[0][0]["content"], llm.prompter[0][1]["content"]
    assert "Fråga systemet igen när kunden följer upp" in system  # overlayen
    assert "följdfråga om något som kom ur kundens system" in anvandare  # uppgiften
    assert "räknas inte som underlag" in anvandare


@pytest.mark.anyio
async def test_trasig_integration_hoppas_over_med_besked():
    storage = MemoryStorage()
    await _med_integration(storage)
    rad = next(iter(storage._integrationer.values()))
    rad["konfig"] = {"requests": [{"name": "x", "url": "http://inte-https"}]}
    llm = _FejkLLM([])
    underlag = await _kor(storage, llm)
    assert not underlag and underlag.katalogfel and "CRM" in underlag.katalogfel[0]
    assert llm.prompter == []
