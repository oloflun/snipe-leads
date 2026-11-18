"""Kvittots text når aldrig `agent_runs` från den äldre bokföringsytan.

Fram till 2026-11-18 sparade uppladdningen upp till 4 000 tecken av den
avlästa kvittotexten i `agent_runs.input_text` och hela texten igen i
stegloggens `user_message`, och chatten sparade texten ur ett bifogat
underlag som en del av frågan. Kvitton bär namn, adresser, kortnummer och
ibland personnummer, och `agent_runs` gallras först när ägaren beslutat en
period (DPIA R10). Nu står bara längd, hash och underlagets id kvar.

Kvittot här är påhittat: butiken, adressen och numren finns inte.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

import app.api.bookkeeping as bokforing
from app.agent.bookkeeping_agent import Avlasning
from app.agent.step_runner import RunTrace, StepResult
from app.bookkeeping.verifieringsgrind import Verdikt
from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app
from app.storage.memory import MemoryStorage

KVITTO = (
    "Exempelbutiken Testköping AB\nStorgatan 1, 123 45 Testköping\n"
    "Kund: Pelle Påhittad 19800101-0000\nKort ************4242\n"
    "Bensin 95 41,2 l 812,50 kr\nMoms 25 % 162,50 kr\nSumma 812,50 kr"
)
# Bitar som inte får finnas någonstans i loggraden.
KANSLIGT = ("Pelle Påhittad", "19800101-0000", "4242", "Storgatan 1", "Bensin 95")

TENANT = "tenant-kvittologg-1111"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _hela_raden(run: dict) -> str:
    import json

    return json.dumps(run, ensure_ascii=False, default=str)


def test_loggtexten_bar_langd_och_hash_men_ingen_text():
    rad = bokforing.kvittotext_for_logg(KVITTO, underlag_id="u-1")
    assert str(len(KVITTO)) in rad
    assert hashlib.sha256(KVITTO.encode("utf-8")).hexdigest()[:16] in rad
    assert "u-1" in rad
    for bit in KANSLIGT:
        assert bit not in rad
    # Ingen del av texten, inte ens början.
    assert KVITTO[:20] not in rad


@pytest.mark.anyio
async def test_uppladdningen_sparar_inte_kvittotexten(monkeypatch):
    """Både input_text och stegloggen. Stegloggens user_message bar samma text
    som input_text, så att bara korta input_text hade lämnat kvar allt."""
    trace = RunTrace()
    trace.steps.append(
        StepResult(
            skill="snajp:bokforing-avlasning",
            output={"motpart": "Exempelbutiken Testköping AB"},
            attempts=1,
            escalated=False,
            escalation_reason=None,
            latency_ms=12,
            tokens_in=100,
            tokens_out=20,
            system_prompt="Läs av underlaget.",
            user_message=KVITTO,
        )
    )
    avlasning = Avlasning(
        falt={"motpart": "Exempelbutiken Testköping AB", "brutto": Decimal("812.50")},
        verdikt=Verdikt(ok=False),
        verifikat=(),
        trace=trace,
    )

    async def _las_underlag(text: str, **_):
        assert text == KVITTO
        return avlasning

    monkeypatch.setattr(bokforing, "las_pdf_text", lambda data: KVITTO)
    monkeypatch.setattr(bokforing, "las_underlag", _las_underlag)

    storage = MemoryStorage()
    svar = await bokforing.ta_emot_underlag(
        storage, TENANT, b"%PDF-1.4 syntetisk", "application/pdf", "kvitto.pdf"
    )

    korningar = storage.agent_runs[TENANT]
    assert len(korningar) == 1
    run = korningar[0]
    hela = _hela_raden(run)
    for bit in KANSLIGT:
        assert bit not in hela, f"{bit!r} står kvar i agent_runs"
    assert str(len(KVITTO)) in run["input"]
    assert svar["underlag"]["id"] in run["input"]
    # Mätvärdena står kvar, texten är borta.
    assert run["step_log"][0]["tokens_in"] == 100
    assert "user_message" not in run["step_log"][0]
    assert "system_prompt" not in run["step_log"][0]


@pytest.mark.anyio
async def test_chatten_loggar_fragan_men_inte_underlagets_text(monkeypatch):
    async def _ta_emot(storage, tenant_id, data, mimetyp, filnamn):
        return {
            "underlag": {"id": "u-chatt-1", "filnamn": filnamn, "motpart": "Exempelbutiken"},
            "status": "granska",
            "brister": [],
            "text": KVITTO,
        }

    async def _tur(storage, tenant_id, *, message, historik, forhamtat):
        # Modellen FÅR texten; det är loggen som inte ska ha den.
        assert "Pelle Påhittad" in message
        return {
            "reply": "Kvittot gäller drivmedel.",
            "verktygsanrop": [],
            "grundad": True,
            "brister": [],
            "latency_ms": 5,
        }

    monkeypatch.setattr(bokforing, "ta_emot_underlag", _ta_emot)
    monkeypatch.setattr(bokforing, "run_bookkeeping_chat_turn", _tur)

    nyckel = {"X-API-Key": get_settings().snajp_demo_api_key}
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        fore = len(storage.agent_runs.get(DEFAULT_TENANT_ID, []))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as klient:
            svar = await klient.post(
                "/api/bookkeeping/chat",
                headers=nyckel,
                data={"meddelande": "Vad köpte jag?"},
                files={"fil": ("kvitto.pdf", b"%PDF-1.4 syntetisk", "application/pdf")},
            )
        assert svar.status_code == 200, svar.text
        korningar = storage.agent_runs[DEFAULT_TENANT_ID][fore:]

    assert len(korningar) == 1
    run = korningar[0]
    hela = _hela_raden(run)
    for bit in KANSLIGT:
        assert bit not in hela, f"{bit!r} står kvar i agent_runs"
    assert run["input"].startswith("Vad köpte jag?")
    assert "u-chatt-1" in run["input"]
    assert str(len(KVITTO)) in run["input"]
