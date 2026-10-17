"""Loopvakten loggar stacken när händelseloopen står still (app/loopvakt.py)."""

import asyncio
import logging
import time

import pytest

from app import loopvakt


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _blockerande_arbete(sekunder: float) -> None:
    slut = time.monotonic() + sekunder
    while time.monotonic() < slut:
        pass


@pytest.mark.anyio
async def test_ett_stopp_loggas_med_raden_som_holl_loopen(caplog):
    caplog.set_level(logging.WARNING, logger="snajp-support.loopvakt")
    loopvakt.starta(100)
    await asyncio.sleep(0.12)
    _blockerande_arbete(0.4)
    await asyncio.sleep(0.15)

    rader = [r.getMessage() for r in caplog.records if r.name == "snajp-support.loopvakt"]
    assert rader, "vakten loggade inget stopp"
    assert "_blockerande_arbete" in rader[0]


@pytest.mark.anyio
async def test_avstangd_vakt_loggar_inget(caplog):
    caplog.set_level(logging.WARNING, logger="snajp-support.loopvakt")
    loopvakt.starta(0)
    _blockerande_arbete(0.3)
    await asyncio.sleep(0.1)
    assert not [r for r in caplog.records if r.name == "snajp-support.loopvakt"]
