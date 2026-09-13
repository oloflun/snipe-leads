"""Bokföringens uppladdning vid kvotfel: kunden får veta att dokumentet INTE
sparades.

Testarens fynd 2026-09-13: "bokföringsdokument kastas vid kvotfel". Filen
läses bara i minnet (ta_emot_underlag sparar aldrig bytesen), och
avläsningen körs före create_bk_underlag — så ett kvotfel betyder att
kvittot är borta. Routerna fångade bara UnderlagsfelError; kvotfelet gick
till den globala handlern, som svarade med en allmän kvottext utan ett ord om
dokumentet.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import DEFAULT_TENANT_ID, get_settings
from app.kvotfel import (
    KUNDTEXT_KREDITSLUT,
    KUNDTEXT_KREDITSLUT_DOKUMENT,
    KUNDTEXT_KVOT_DOKUMENT,
)
from app.main import app

DEMO = {"X-API-Key": get_settings().snajp_demo_api_key}


class _Kreditfel(Exception):
    status_code = 403

    def __str__(self) -> str:
        return (
            "Error code: 403 - [{'error': {'code': 403, 'message': 'This API method "
            "requires billing to be enabled.', 'status': 'PERMISSION_DENIED'}}]"
        )


class _Minutkvot(Exception):
    status_code = 429

    def __str__(self) -> str:
        return (
            "Error code: 429 - [{'error': {'code': 429, 'message': 'Resource exhausted. "
            "Please try again later.', 'status': 'RESOURCE_EXHAUSTED'}}]"
        )


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _ladda_upp(fel: Exception, data: bytes):
    async with app.router.lifespan_context(app):
        with (
            patch("app.api.bookkeeping.las_pdf_text", return_value="Kvitto 1 250 kr"),
            patch("app.api.bookkeeping.las_underlag", new=AsyncMock(side_effect=fel)),
            patch("app.api.bookkeeping.larma_kreditslut", new=AsyncMock()) as larm,
        ):
            async with _client() as client:
                svar = await client.post(
                    "/api/bookkeeping/underlag",
                    headers=DEMO,
                    files={"fil": ("kvitto.pdf", data, "application/pdf")},
                )
        sparade = await app.state.storage.list_bk_underlag(DEFAULT_TENANT_ID)
    return svar, larm, sparade


@pytest.mark.anyio
async def test_kreditslut_vid_uppladdning_ger_503_och_sager_att_inget_sparades():
    svar, larm, sparade = await _ladda_upp(_Kreditfel(), b"%PDF-1.4 kreditslut-kvitto")
    assert svar.status_code == 503, svar.text
    kropp = svar.json()
    assert kropp["error"] == KUNDTEXT_KREDITSLUT_DOKUMENT
    assert kropp["klass"] == "kreditslut"
    assert "sparades INTE" in kropp["error"]
    assert "billing" not in svar.text
    larm.assert_awaited_once()
    assert larm.await_args.kwargs["kalla"] == "bokforing"
    assert sparade == []


@pytest.mark.anyio
async def test_minutkvot_vid_uppladdning_ger_429_och_ber_om_ny_uppladdning():
    svar, larm, sparade = await _ladda_upp(_Minutkvot(), b"%PDF-1.4 minutkvot-kvitto")
    assert svar.status_code == 429, svar.text
    kropp = svar.json()
    assert kropp["error"] == KUNDTEXT_KVOT_DOKUMENT
    assert kropp["klass"] == "kvot"
    assert "ladda upp det igen" in kropp["error"]
    larm.assert_not_awaited()
    assert sparade == []


@pytest.mark.anyio
async def test_kreditslut_i_chattens_bilaga_sager_att_den_inte_sparades():
    async with app.router.lifespan_context(app):
        with (
            patch("app.api.bookkeeping.las_pdf_text", return_value="Kvitto"),
            patch("app.api.bookkeeping.las_underlag", new=AsyncMock(side_effect=_Kreditfel())),
            patch("app.api.bookkeeping.larma_kreditslut", new=AsyncMock()),
        ):
            async with _client() as client:
                svar = await client.post(
                    "/api/bookkeeping/chat",
                    headers=DEMO,
                    data={"meddelande": "Vad blev det här?"},
                    files={"fil": ("kvitto.pdf", b"%PDF-1.4 chattbilaga", "application/pdf")},
                )
    assert svar.status_code == 503, svar.text
    assert svar.json()["detail"] == KUNDTEXT_KREDITSLUT_DOKUMENT
    assert svar.json()["sparat"] is False


@pytest.mark.anyio
async def test_kreditslut_i_chattsvaret_efter_sparad_bilaga_sager_att_den_ar_sparad():
    """Bilagan hann sparas, svaret föll. Att be kunden ladda upp igen hade
    bara gett dubblettspärrens 422 — beskedet ska säga att den är inne."""
    bilaga = {
        "underlag": {"filnamn": "kvitto.pdf", "datum": None, "motpart": None, "brutto": None,
                     "momssats": None, "kategori": None},
        "status": "granska_manuellt",
        "brister": [],
        "text": "Kvitto",
    }
    async with app.router.lifespan_context(app):
        with (
            patch("app.api.bookkeeping.ta_emot_underlag", new=AsyncMock(return_value=bilaga)),
            patch(
                "app.api.bookkeeping.run_bookkeeping_chat_turn",
                new=AsyncMock(side_effect=_Kreditfel()),
            ),
            patch("app.api.bookkeeping.larma_kreditslut", new=AsyncMock()) as larm,
        ):
            async with _client() as client:
                svar = await client.post(
                    "/api/bookkeeping/chat",
                    headers=DEMO,
                    data={"meddelande": "Hej"},
                    files={"fil": ("kvitto.pdf", b"%PDF-1.4 x", "application/pdf")},
                )
    assert svar.status_code == 503, svar.text
    kropp = svar.json()
    assert kropp["sparat"] is True
    assert kropp["error"].startswith(KUNDTEXT_KREDITSLUT)
    assert "är sparat" in kropp["error"]
    larm.assert_awaited_once()


@pytest.mark.anyio
async def test_ett_riktigt_fel_maskeras_inte_som_kvot():
    """Skyddsnätet får aldrig gömma en bugg bakom 'kvoten är slut'."""
    async with app.router.lifespan_context(app):
        with (
            patch("app.api.bookkeeping.las_pdf_text", return_value="Kvitto"),
            patch(
                "app.api.bookkeeping.las_underlag",
                new=AsyncMock(side_effect=KeyError("datum")),
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app, raise_app_exceptions=False),
                base_url="http://test",
            ) as client:
                svar = await client.post(
                    "/api/bookkeeping/underlag",
                    headers=DEMO,
                    files={"fil": ("kvitto.pdf", b"%PDF-1.4 riktigt fel", "application/pdf")},
                )
    assert svar.status_code == 500
    assert "klass" not in svar.text
