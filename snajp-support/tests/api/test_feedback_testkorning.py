"""Feedback får bara lämnas på testkörningar — inte på riktiga kundsamtal."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.anyio
async def test_feedback_pa_skarp_korning_ger_403():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        rad = await storage.log_agent_run(
            "00000000-0000-4000-a000-000000000001",
            agent_type="support",
            pack_version="x:support/v1",
            skills_used=[],
            input_text="fråga",
            output_text="svar",
            step_log=[],
            tokens_in=1,
            tokens_out=1,
            latency_ms=1,
            is_test=False,
        )
        async with _client() as client:
            svar = await client.post(
                "/api/agent/feedback",
                headers=DEMO,
                json={"run_id": rad["id"], "verdict": "good"},
            )
            assert svar.status_code == 403, svar.text


@pytest.mark.anyio
async def test_feedback_pa_testkorning_sparas():
    async with app.router.lifespan_context(app):
        storage = app.state.storage
        rad = await storage.log_agent_run(
            "00000000-0000-4000-a000-000000000001",
            agent_type="support",
            pack_version="x:support/v1",
            skills_used=[],
            input_text="fråga",
            output_text="svar",
            step_log=[],
            tokens_in=1,
            tokens_out=1,
            latency_ms=1,
            is_test=True,
        )
        async with _client() as client:
            svar = await client.post(
                "/api/agent/feedback",
                headers=DEMO,
                json={"run_id": rad["id"], "verdict": "bad", "corrected_output": "Säg X i stället."},
            )
            assert svar.status_code == 201, svar.text
            assert svar.json()["feedback"]["verdict"] == "bad"
