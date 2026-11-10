"""Körningsloggen till kunden är ett sammandrag (fas 2, 2026-11-10).

`GET /api/leads/runs` läste hela agent_runs-rader: indata, utdata och hela
stegloggen med varje stegs prompt. Uppmätt i development: 8,5 MB och 1,7 s för
50 rader, som ingen vy läser. Samma rader bär Snajps interna promptar och,
i researchstegen, det som promptarna bär om bolaget. Kunden får nu
mätvärdena; texterna finns kvar för plattformsadmin.

Feedbackvägen läste 200 hela rader, två gånger, för att hitta en.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

pytestmark = pytest.mark.anyio
DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}
ANNAN_KUND = "00000000-0000-4000-a000-0000000000ff"
HEMLIGT = "HEMLIG-PROMPT-4412"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _klient() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _logga(storage, tenant_id: str = DEFAULT_TENANT_ID, *, is_test: bool = True) -> dict:
    return await storage.log_agent_run(
        tenant_id,
        agent_type="leads_research",
        pack_version="x:leads/v1",
        skills_used=["sa:research"],
        input_text=f"indata {HEMLIGT}",
        output_text=f"utdata {HEMLIGT}",
        step_log=[{"skill": "sa:research", "user_message": HEMLIGT, "latency_ms": 900}],
        tokens_in=1500,
        tokens_out=200,
        latency_ms=900,
        is_test=is_test,
    )


async def test_korningsloggen_bar_matvarden_men_inga_texter():
    async with app.router.lifespan_context(app):
        rad = await _logga(app.state.storage)
        async with _klient() as klient:
            svar = await klient.get("/api/leads/runs", headers=DEMO)

    assert svar.status_code == 200, svar.text
    assert HEMLIGT not in svar.text
    korning = next(r for r in svar.json()["runs"] if r["id"] == rad["id"])
    for falt in ("input", "output", "step_log", "grounding"):
        assert falt not in korning
    assert (korning["agent_type"], korning["tokens_in"], korning["latency_ms"]) == ("leads_research", 1500, 900)
    assert korning["skills_used"] == ["sa:research"]


async def test_lagringens_fulla_rader_finns_kvar_for_ovriga_anropare():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        rad = await _logga(storage)
        fulla = await storage.list_agent_runs(DEFAULT_TENANT_ID, limit=5)
        latta = await storage.list_agent_runs(DEFAULT_TENANT_ID, limit=5, sammandrag=True)

    assert next(r for r in fulla if r["id"] == rad["id"])["input"].endswith(HEMLIGT)
    assert "input" not in next(r for r in latta if r["id"] == rad["id"])


async def test_feedback_hittar_en_korning_utanfor_de_tvahundra_senaste():
    """Uppslaget gick via de 200 senaste raderna; en äldre körning fanns "inte"."""
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        gammal = await _logga(storage)
        for _ in range(205):
            await _logga(storage)
        async with _klient() as klient:
            svar = await klient.post(
                "/api/agent/feedback", headers=DEMO, json={"run_id": gammal["id"], "verdict": "good"}
            )
    assert svar.status_code == 201, svar.text


async def test_feedback_pa_en_annan_kunds_korning_ger_404():
    async with app.router.lifespan_context(app):
        frammande = await _logga(app.state.storage, ANNAN_KUND)
        async with _klient() as klient:
            svar = await klient.post(
                "/api/agent/feedback", headers=DEMO, json={"run_id": frammande["id"], "verdict": "good"}
            )
    assert svar.status_code == 404, svar.text


async def test_en_kunds_egen_korning_slas_upp_i_en_fraga():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        rad = await _logga(storage)
        egen = await storage.hamta_agent_run(DEFAULT_TENANT_ID, rad["id"])
        annans = await storage.hamta_agent_run(ANNAN_KUND, rad["id"])

    assert egen and egen["id"] == rad["id"] and egen["input"].endswith(HEMLIGT)
    assert annans is None
