"""Dubbelstartsvakten är inkopplad på startvägarna (Fas 0-fyndet H5, 2026-11-09).

Genom HTTP-lagret: två likadana beställningar av en körning ger EN körning.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

import app.api.leads as leads_api
from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}
T = DEFAULT_TENANT_ID

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _klient() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
def _startbar(monkeypatch):
    """Starten ska nå köläggningen utan modell, budget eller sökning."""
    korda: list[dict] = []

    async def _inget(*_a, **_k):
        return None

    async def _run_batch(_state, post):
        korda.append(post)

    monkeypatch.setattr(leads_api, "_require_live_llm", lambda: None)
    monkeypatch.setattr(leads_api, "_kraev_leads_budget", _inget)
    monkeypatch.setattr(leads_api, "_validera_batch_kan_starta", _inget)
    monkeypatch.setattr(leads_api, "_run_batch", _run_batch)
    return korda


async def test_dubbelklick_pa_kor_iris_ger_en_korning(_startbar):
    bestallning = {"limit": 5, "scope": "research"}
    async with app.router.lifespan_context(app):
        async with _klient() as klient:
            forsta = await klient.post("/api/leads/runs/batch", headers=DEMO, json=bestallning)
            andra = await klient.post("/api/leads/runs/batch", headers=DEMO, json=bestallning)

    assert forsta.status_code == 202 and andra.status_code == 202, (forsta.text, andra.text)
    assert forsta.json()["jobs"] == andra.json()["jobs"], "det andra klicket ska få samma körning tillbaka"
    assert andra.json().get("dubblett") is True
    assert "dubblett" not in forsta.json()
    assert len(_startbar) == 1, "bara en körning får ha startats"


async def test_en_annan_bestallning_ar_en_egen_korning(_startbar):
    async with app.router.lifespan_context(app):
        async with _klient() as klient:
            a = await klient.post("/api/leads/runs/batch", headers=DEMO, json={"limit": 5, "scope": "research"})
            b = await klient.post("/api/leads/runs/batch", headers=DEMO, json={"limit": 10, "scope": "research"})

    assert a.json()["jobs"] != b.json()["jobs"]
    assert len(_startbar) == 2


@pytest.mark.parametrize(
    ("fil", "handlingar"),
    [
        ("leads.py", ('"korning"', '"korningens-utkast"', '"korningens-utskick"')),
        ("leads_kampanjer.py", ('"kampanj"', '"kampanjens-utskick"')),
    ],
)
def test_varje_startvag_gar_genom_vakten(fil, handlingar):
    kalla = (Path(__file__).resolve().parents[2] / "app" / "api" / fil).read_text(encoding="utf-8")
    for handling in handlingar:
        assert f"dubbelstart.nyckel(tenant[\"tenant_id\"], {handling}" in kalla, f"{fil}: {handling} saknar vakten"
