"""Samma start två gånger ger en start (Fas 0-fyndet H5, 2026-11-09)."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from app.api import dubbelstart

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _rent():
    dubbelstart.nollstall()
    yield
    dubbelstart.nollstall()


async def test_tva_samtidiga_likadana_starter_gor_arbetet_en_gang():
    starter = 0
    slapp = asyncio.Event()

    async def arbete():
        nonlocal starter
        starter += 1
        await slapp.wait()
        return {"jobs": [{"job_id": "j1"}]}

    k = dubbelstart.nyckel("kund-1", "batch", {"limit": 30})
    forsta = asyncio.create_task(dubbelstart.en_gang(k, arbete))
    andra = asyncio.create_task(dubbelstart.en_gang(k, arbete))
    await asyncio.sleep(0)
    slapp.set()
    a, b = await asyncio.gather(forsta, andra)

    assert starter == 1
    assert a == {"jobs": [{"job_id": "j1"}]}
    assert b == {"jobs": [{"job_id": "j1"}], "dubblett": True}


async def test_ett_klick_strax_efterat_far_samma_svar():
    starter = 0

    async def arbete():
        nonlocal starter
        starter += 1
        return {"job_id": f"j{starter}"}

    k = dubbelstart.nyckel("kund-1", "batch", {"limit": 30})
    assert await dubbelstart.en_gang(k, arbete) == {"job_id": "j1"}
    assert await dubbelstart.en_gang(k, arbete) == {"job_id": "j1", "dubblett": True}
    assert starter == 1


async def test_efter_fonstret_ar_det_en_ny_start():
    starter = 0

    async def arbete():
        nonlocal starter
        starter += 1
        return {"job_id": f"j{starter}"}

    k = dubbelstart.nyckel("kund-1", "batch", {"limit": 30})
    await dubbelstart.en_gang(k, arbete, fonster_s=0.01)
    await asyncio.sleep(0.03)
    assert await dubbelstart.en_gang(k, arbete, fonster_s=0.01) == {"job_id": "j2"}


async def test_annan_kund_eller_annat_innehall_ar_en_egen_start():
    assert dubbelstart.nyckel("kund-1", "batch", {"limit": 30}) != dubbelstart.nyckel("kund-2", "batch", {"limit": 30})
    assert dubbelstart.nyckel("kund-1", "batch", {"limit": 30}) != dubbelstart.nyckel("kund-1", "batch", {"limit": 50})
    assert dubbelstart.nyckel("kund-1", "batch", {"limit": 30}) != dubbelstart.nyckel("kund-1", "utkast", {"limit": 30})


async def test_ett_fel_ger_bada_felet_och_gar_att_gora_om():
    forsok = 0

    async def arbete():
        nonlocal forsok
        forsok += 1
        if forsok == 1:
            await asyncio.sleep(0.01)
            raise HTTPException(status_code=422, detail="Budgeten är slut.")
        return {"job_id": "j2"}

    k = dubbelstart.nyckel("kund-1", "batch", {})
    forsta = asyncio.create_task(dubbelstart.en_gang(k, arbete))
    await asyncio.sleep(0)
    andra = asyncio.create_task(dubbelstart.en_gang(k, arbete))
    utfall = await asyncio.gather(forsta, andra, return_exceptions=True)

    assert all(isinstance(u, HTTPException) and u.status_code == 422 for u in utfall)
    assert forsok == 1
    assert await dubbelstart.en_gang(k, arbete) == {"job_id": "j2"}, "ett misslyckat försök ska gå att göra om direkt"


async def test_avbruten_dubblett_avbryter_inte_den_forsta():
    klar = asyncio.Event()

    async def arbete():
        await asyncio.sleep(0.05)
        klar.set()
        return {"ok": True}

    k = dubbelstart.nyckel("kund-1", "skicka", "korning-1")
    forsta = asyncio.create_task(dubbelstart.en_gang(k, arbete))
    await asyncio.sleep(0)
    andra = asyncio.create_task(dubbelstart.en_gang(k, arbete))
    await asyncio.sleep(0.01)
    andra.cancel()

    assert await forsta == {"ok": True}
    assert klar.is_set()
