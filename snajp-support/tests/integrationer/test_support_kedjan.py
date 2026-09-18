"""Support-kedjan MED en integration — den riktiga run_support_agent.

Bara nätverksgränserna är fejkade: LLM-klienten (som i
tests/agent/test_support_agent_wiring.py) och kundens ordersystem (en
httpx-transport under nätvakten). Det här testet bevisar kopplingen:

  - uppslaget körs efter triagen och före research, och bara då,
  - orderdatan når utkastet och räknas som underlag (ingen överlämning för
    att kunskapsbasen saknar orderstatus),
  - faktagrinden godtar ett datum som bara finns i systemets svar,
  - svaret cachas aldrig, och spårloggen visar anropet men inte datan.
"""

from __future__ import annotations

import json
import re
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.agent.support_agent import run_support_agent
from app.config import get_settings
from app.integrationer import lagring
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"

ORDERSYSTEM = {
    "requests": [
        {
            "name": "Orderstatus",
            "description": "Status och leveransdatum för kundens order.",
            "url": "https://butik.example.com/api/ordrar/{{ordernummer}}?email={{kund.email}}",
            "headers": {"Authorization": "Bearer {{hemlighet.token}}"},
            "placeholders": [{"key": "ordernummer", "description": "Ordernumret, t.ex. A-17"}],
        }
    ]
}


@pytest.fixture(autouse=True)
def _fejkad_nyckel(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-a-real-credential-000000")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _FejkLLM:
    def __init__(self, svar_fran_utkast: str):
        self.anrop: list[str] = []
        self.prompter: dict[str, str] = {}
        self.utkast = svar_fran_utkast
        self.chat = self
        self.completions = self

    async def create(self, *, model, response_format, temperature, messages, **kwargs):
        system = messages[0]["content"]
        skill = re.search(r"styrs av skillen (\S+?),", system).group(1)
        if "support-integrationsuppslag" in system:
            skill = "integrationsuppslag"
        self.anrop.append(skill)
        self.prompter[skill] = messages[1]["content"]
        payload = {"sources_used": [], "context_refs": ["context_pack"]}
        payload.update(
            {
                "cs:ticket-triage": {
                    "category": "leverans", "priority": "P3", "sentiment": 0.6, "escalate": False,
                    "ber_om_manniska": False, "inom_amnesomradet": True, "missforstadd": False,
                },
                "integrationsuppslag": {
                    "anrop": [{"verktyg": "request_orderstatus", "argument": {"ordernummer": "A-17"}}],
                    "klar": True,
                },
                # Kunskapsbasen är TOM för frågan; systemet bär svaret.
                "cs:customer-research": {
                    "findings": "Ordersystemet visar status.", "confidence": 0.9,
                    "kb_supports_answer": True, "behover_fortydligande": False,
                },
                "cs:draft-response": {"draft": self.utkast},
                "snajp:humanizer-svenska": {"final_reply": self.utkast},
            }.get(skill, {})
        )
        message = type("M", (), {"content": json.dumps(payload, ensure_ascii=False)})()
        usage = type("U", (), {"prompt_tokens": 10, "completion_tokens": 5})()
        return type("R", (), {"choices": [type("C", (), {"message": message})()], "usage": usage})()


async def _kor(storage, llm, **extra):
    with patch("app.agent.step_runner.get_llm_client", return_value=llm), patch(
        "app.agent.support_agent.classify_cancellation_risk", new=AsyncMock(return_value=(0.0, 0.0))
    ):
        return await run_support_agent(
            storage,
            TENANT,
            message="Var är min order A-17?",
            subject="",
            channel="web",
            customer_email="kund@example.com",
            customer_name="Kim",
            attachments=[],
            **extra,
        )


async def _med_ordersystem(storage):
    await lagring.skapa(
        storage, TENANT, typ="http", namn="Butiken", beskrivning="", konfig=ORDERSYSTEM,
        hemligheter={"token": "butik-hemlig-token-7"},
    )


@pytest.mark.anyio
async def test_ordersvaret_nar_kunden_utan_overlamning(svara):
    storage = MemoryStorage()
    await _med_ordersystem(storage)
    mottagna = svara(lambda r: httpx.Response(200, json={"order": "A-17", "status": "skickad", "levereras": "2026-09-22"}))
    llm = _FejkLLM("Din order A-17 är skickad och levereras 2026-09-22.")

    resultat = await _kor(storage, llm)

    assert llm.anrop[:3] == ["cs:ticket-triage", "integrationsuppslag", "cs:customer-research"]
    assert "cs:customer-escalation" not in llm.anrop  # ingen kunskapslucka
    assert mottagna[0].url.params["email"] == "kund@example.com"
    assert "2026-09-22" in llm.prompter["cs:draft-response"]  # datan nådde utkastet
    assert resultat["escalated"] is False
    # Faktagrinden godtog datumet: det stod i systemets svar.
    assert resultat["faktagrind"]["ok"] is True
    assert resultat["reply"] == "Din order A-17 är skickad och levereras 2026-09-22."
    # Spårloggen visar anropet, inte datan eller nyckeln.
    pseudo = next(s for s in resultat["step_log"] if s.get("step") == "integrationer")
    assert pseudo["anrop"][0]["verktyg"] == "request_orderstatus" and pseudo["anrop"][0]["ok"] is True
    logg = json.dumps(resultat["step_log"], ensure_ascii=False)
    assert "butik-hemlig-token-7" not in logg


@pytest.mark.anyio
async def test_faktagrinden_faller_datum_som_systemet_inte_sa(svara):
    """Kontrollen åt andra hållet: ett datum som INTE står i systemsvaret."""
    storage = MemoryStorage()
    await _med_ordersystem(storage)
    svara(lambda r: httpx.Response(200, json={"order": "A-17", "status": "skickad"}))
    llm = _FejkLLM("Din order A-17 levereras 2026-10-03.")
    resultat = await _kor(storage, llm)
    assert resultat["faktagrind"]["ok"] is False or resultat["faktagrind"].get("reparerad")
    assert "2026-10-03" not in resultat["reply"]


@pytest.mark.anyio
async def test_utan_integrationer_ar_kedjan_oforandrad():
    storage = MemoryStorage()
    llm = _FejkLLM("Hej!")
    await _kor(storage, llm)
    assert "integrationsuppslag" not in llm.anrop


@pytest.mark.anyio
async def test_kund_id_hoppar_over_kunduppslaget(svara):
    storage = MemoryStorage()
    kund = await storage.find_or_create_customer(TENANT, email=None, phone="+46701234567", name="Kim")
    antal_fore = len(storage.customers)
    llm = _FejkLLM("Hej!")
    resultat = await _kor(storage, llm, kund_id=kund["id"])
    assert resultat["customer_id"] == kund["id"]
    assert len(storage.customers) == antal_fore


@pytest.mark.anyio
async def test_svar_med_systemdata_cachas_aldrig(svara, monkeypatch):
    from app.cache import svarscache

    monkeypatch.setenv("SEMANTIC_CACHE", "on")
    get_settings.cache_clear()
    sparade: list = []

    async def spara(*a, **kw):
        sparade.append(kw)

    async def forbered(*a, **kw):
        return svarscache.CacheKontext(behorig=True)

    monkeypatch.setattr(svarscache, "spara", spara)
    monkeypatch.setattr(svarscache, "forbered", forbered)

    # Positiv kontroll: "leverans" ÄR en cachebar kategori, så samma kedja
    # utan systemdata cachar svaret. Utan den här raden kunde testet nedan
    # passera för att kategorin aldrig cachas, inte för att spärren finns.
    await _kor(MemoryStorage(), _FejkLLM("Leveranstiden är två till fyra dagar."))
    assert len(sparade) == 1

    storage = MemoryStorage()
    await _med_ordersystem(storage)
    svara(lambda r: httpx.Response(200, json={"status": "skickad", "levereras": "2026-09-22"}))
    await _kor(storage, _FejkLLM("Din order är skickad och levereras 2026-09-22."))
    assert len(sparade) == 1, "svaret med kundens orderdata fick inte cachas"
