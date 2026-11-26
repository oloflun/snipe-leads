"""Jobbsvaret bär en känd felkod bredvid texten (2026-11-25).

Utkastrutorna för Iris-bolagen visade backendens svenska feltext även på
engelska: jobbposten bär bara texten, så ytan hade ingen kod att översätta.
`GET /api/jobs/{id}` härleder nu `error_kod` ur kända texter; ytan översätter
den med lib/leads/felkoder.ts. Fältet är additivt: `error` är oförändrat.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.kvotfel import KUNDTEXT_KREDITSLUT, KUNDTEXT_KVOT
from app.jobs.store import TIDSGRANS_FEL
from app.leads.business_context import EGEN_PRODUKT_SAKNAS, SAKNAR_PRODUKT
from app.main import app

pytestmark = pytest.mark.anyio
DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def _fallet(fel: str) -> dict:
    async with app.router.lifespan_context(app):
        job_id = await app.state.jobs.create(tenant_id=DEFAULT_TENANT_ID)
        await app.state.jobs.fail(job_id, fel)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as klient:
            svar = await klient.get(f"/api/jobs/{job_id}", headers=DEMO)
    assert svar.status_code == 200, svar.text
    return svar.json()


async def test_saknad_produkt_bar_sin_kod():
    ut = await _fallet(EGEN_PRODUKT_SAKNAS)
    assert ut["status"] == "failed"
    assert ut["error"] == EGEN_PRODUKT_SAKNAS
    assert ut["error_kod"] == SAKNAR_PRODUKT == "saknar_produkt"


@pytest.mark.parametrize(
    ("fel", "kod"),
    [
        (KUNDTEXT_KREDITSLUT, "kreditslut"),
        (KUNDTEXT_KVOT, "kvot"),
        (TIDSGRANS_FEL, "tidsgrans"),
    ],
)
async def test_andra_kanda_fel_bar_sina_koder(fel: str, kod: str):
    ut = await _fallet(fel)
    assert ut["error"] == fel
    assert ut["error_kod"] == kod


async def test_rått_kvotfel_oversatts_och_far_kvotkoden():
    ut = await _fallet("Error code: 429 - [{'error': {'status': 'RESOURCE_EXHAUSTED', 'message': 'quota'}}]")
    assert ut["error"] == KUNDTEXT_KVOT
    assert ut["error_kod"] == "kvot"


async def test_okant_fel_bar_ingen_kod():
    ut = await _fallet("Något helt annat gick fel.")
    assert ut["error"] == "Något helt annat gick fel."
    assert "error_kod" not in ut


async def test_klart_jobb_bar_ingen_kod():
    async with app.router.lifespan_context(app):
        job_id = await app.state.jobs.create(tenant_id=DEFAULT_TENANT_ID)
        await app.state.jobs.complete(job_id, {"body": "Hej"})
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as klient:
            svar = await klient.get(f"/api/jobs/{job_id}", headers=DEMO)
    ut = svar.json()
    assert ut["status"] == "completed" and ut["error"] is None
    assert "error_kod" not in ut


async def test_saknad_eller_kort_beskrivning_bar_sin_kod():
    """De vanligaste utkastfelen: beskrivningen av vad kunden säljer saknas
    eller är för kort. Det andra beskedet bär ett tal som varierar, så koden
    känns igen på inledningen. Texterna tas ur den riktiga kontrollen."""
    from app.leads.business_context import (
        MINSTA_ANVANDBARA_LANGD,
        SAKNAR_BESKRIVNING,
        MissingBusinessContextError,
        require_business_context,
    )

    class _Lager:
        def __init__(self, text):
            self.text = text

        async def get_latest_context_doc(self, tenant_id, kind):
            return {"content": self.text}

    for text in ("", "x" * (MINSTA_ANVANDBARA_LANGD - 1)):
        with pytest.raises(MissingBusinessContextError) as fel:
            await require_business_context(_Lager(text), DEFAULT_TENANT_ID)
        assert fel.value.kod == SAKNAR_BESKRIVNING == "saknar_beskrivning"
        ut = await _fallet(str(fel.value))
        assert ut["error"] == str(fel.value)
        assert ut["error_kod"] == "saknar_beskrivning", text
