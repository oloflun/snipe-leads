"""Jobbsvaret bär inte agentens promptar (hittat i fas 2, 2026-11-10).

`GET /api/jobs/{id}` lämnade ut körningens hela steglogg i utförligt läge: för
varje steg agentens användarmeddelande (verksamhetskontext, SOUL, kundminne,
kunskapsbasens artiklar, samtalshistorik), modellens råa utdata och dess
resonemang. Vägen pollas av den anonyma chattwidgeten, så varje besökare kunde
läsa kundens interna instruktioner i webbläsarens nätverksflik. Leadsjobben går
samma väg och bär researchens promptar, där webbplatsbedömningen kan ingå.

Stegloggens mätvärden (steg, tid, tokens) får följa med; texterna inte. Den
fulla loggen står kvar i agent_runs för plattformsadmin.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.main import app

pytestmark = pytest.mark.anyio
DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}
HEMLIGT = "HEMLIG-INSTRUKTION-7731"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _steg(skill: str = "cs:ticket-triage") -> dict:
    return {
        "skill": skill,
        "attempts": 1,
        "latency_ms": 812,
        "tokens_in": 4000,
        "tokens_out": 120,
        "sources_used": ["kb-1"],
        "lager": [{"namn": "grundprompt", "tecken": 2500}],
        "user_message": f"## SOUL\n{HEMLIGT}",
        "raw_output": f'{{"reasoning": "{HEMLIGT}"}}',
        "reasoning_content": HEMLIGT,
        "system_prompt": HEMLIGT,
    }


async def _hamta(result: dict) -> dict:
    async with app.router.lifespan_context(app):
        job_id = await app.state.jobs.create(tenant_id=DEFAULT_TENANT_ID)
        await app.state.jobs.complete(job_id, result)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as klient:
            svar = await klient.get(f"/api/jobs/{job_id}", headers=DEMO)
    assert svar.status_code == 200, svar.text
    assert HEMLIGT not in svar.text, "en prompttext följde med i jobbsvaret"
    return svar.json()["result"]


async def test_chattsvaret_bar_inga_prompter():
    ut = await _hamta({"reply": "Hej! Kursen är på torsdag.", "step_log": [_steg(), _steg("cs:draft-response")]})

    assert ut["reply"] == "Hej! Kursen är på torsdag."
    for steg in ut["step_log"]:
        for falt in ("user_message", "raw_output", "reasoning_content", "system_prompt"):
            assert falt not in steg


async def test_matvardena_foljer_med():
    ut = await _hamta({"reply": "Hej", "step_log": [_steg()]})

    steg = ut["step_log"][0]
    assert (steg["skill"], steg["latency_ms"], steg["tokens_in"]) == ("cs:ticket-triage", 812, 4000)
    assert steg["sources_used"] == ["kb-1"] and steg["lager"]


async def test_stegloggar_langre_in_i_svaret_rensas_ocksa():
    """Leadsjobbens svar bär stegloggen under egna nycklar."""
    ut = await _hamta({"prospect": {"id": "p1"}, "research": {"step_log": [_steg("sa:research")]}, "utkast": [{"step_log": [_steg()]}]})

    assert ut["prospect"] == {"id": "p1"}
    assert "user_message" not in ut["research"]["step_log"][0]
    assert "raw_output" not in ut["utkast"][0]["step_log"][0]


async def test_stegens_fulla_utdata_foljer_inte_heller_med():
    """Researchsvaret bär `step_outputs`: stegloggen plus varje stegs hela utdata."""
    fullt = {**_steg("sa:research"), "output": {"fynd": HEMLIGT}}
    ut = await _hamta({"qualified": True, "niva": "A", "step_outputs": [fullt]})

    assert ut["qualified"] is True and ut["niva"] == "A"
    steg = ut["step_outputs"][0]
    assert steg["skill"] == "sa:research" and steg["latency_ms"] == 812
    for falt in ("output", "user_message", "raw_output", "reasoning_content"):
        assert falt not in steg


async def test_ett_svar_utan_steglogg_ar_orort():
    svar = {"list_id": "l1", "status": "klar", "rader": [{"user_message": "ett vanligt fält med samma namn"}]}
    assert await _hamta(svar) == svar


def test_ett_svar_utan_steglogg_kopieras_inte():
    """Körningens tillstånd är flera megabyte och pollas var tredje sekund."""
    from app.api.stegtexter import utan_stegtexter

    stort = {"korning": {"kandidater": [{"company_name": "Ett AB"}] * 500}, "jobs": ["a", "b"]}
    assert utan_stegtexter(stort) is stort


def test_de_direkta_agentsvaren_gar_genom_rensningen():
    """Researchsteget och prospektsvaret svarar utan jobb, med samma steglogg."""
    from pathlib import Path

    kalla = (Path(__file__).resolve().parents[2] / "app" / "api" / "leads.py").read_text(encoding="utf-8")
    assert "return utan_stegtexter(result)" in kalla
    assert "return utan_stegtexter(await hantera_prospektsvar(" in kalla


async def test_lagrade_jobbet_ar_orort():
    """Rensningen sker i läsvägen: kvotbokföringen och återtag läser det lagrade."""
    async with app.router.lifespan_context(app):
        job_id = await app.state.jobs.create(tenant_id=DEFAULT_TENANT_ID)
        await app.state.jobs.complete(job_id, {"step_log": [_steg()]})
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as klient:
            await klient.get(f"/api/jobs/{job_id}", headers=DEMO)
        lagrat = await app.state.jobs.get(job_id)
    assert lagrat["result"]["step_log"][0]["user_message"].endswith(HEMLIGT)
