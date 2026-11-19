"""Gallringens bakgrundsjobb (app/jobs/gallring.py) — klockan och larmet.

Själva raderingen är databasfunktionen gallra_alla och prövas mot en riktig
Postgres i tests/db/test_gallring.py. Här prövas det som ligger i Python:
avstängd som standard, spegeln lämnad åt databasen, inte före natten, larm när taket
nås eller en kund faller, och att ett fel aldrig fäller loopen.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from app.config import Settings
from app.jobs import gallring
from app.storage.memory import MemoryStorage

NATT = datetime(2026, 11, 18, 4, 0, tzinfo=ZoneInfo("Europe/Stockholm"))
KVALL = datetime(2026, 11, 18, 1, 0, tzinfo=ZoneInfo("Europe/Stockholm"))


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _installning(monkeypatch, **varden):
    standard = {"gallring_aktiv": True, "gallring_tak": 5000, "gallring_timme": 3,
                "gallring_kontroll_sekunder": 3600}
    standard.update(varden)
    monkeypatch.setattr(gallring, "get_settings", lambda: SimpleNamespace(**standard))


class _Lagring(MemoryStorage):
    def __init__(self, svar=None, spegel=None):
        super().__init__()
        self.svar = svar or {"status": "kord", "dag": "2026-11-18", "kunder": []}
        self.spegel = spegel
        self.anrop: list[int] = []

    async def spegel_info(self):
        return self.spegel

    async def gallra_dygnet(self, *, tak: int):
        self.anrop.append(tak)
        return self.svar


def test_gallringen_ar_av_som_standard():
    assert Settings.model_fields["gallring_aktiv"].default is False


@pytest.mark.anyio
async def test_avstangd_gor_ingenting(monkeypatch):
    _installning(monkeypatch, gallring_aktiv=False)
    lagring = _Lagring()
    assert (await gallring.kor_gallring(lagring, nu=NATT))["status"] == "avstangd"
    assert lagring.anrop == []


@pytest.mark.anyio
async def test_spegeln_kor_databasens_gallring(monkeypatch):
    """Migration 133: spegeln anropar gallra_alla som main. Vad som får röras
    där (bara det synken inte för över) avgör databasfunktionen, som prövas i
    tests/db/test_gallring.py. Förut stannade jobbet här, och rader utanför
    synken låg kvar i spegeln för alltid."""
    _installning(monkeypatch)
    lagring = _Lagring(
        svar={"status": "kord", "dag": "2026-11-18", "kunder": [], "spegel": True},
        spegel={"environment": "development", "lage": "envags"},
    )
    svar = await gallring.kor_gallring(lagring, nu=NATT)
    assert svar["status"] == "kord" and svar["spegel"] is True
    assert lagring.anrop == [5000]


@pytest.mark.anyio
async def test_inte_fore_natten(monkeypatch):
    _installning(monkeypatch)
    lagring = _Lagring()
    assert (await gallring.kor_gallring(lagring, nu=KVALL))["status"] == "for_tidigt"
    assert lagring.anrop == []


@pytest.mark.anyio
async def test_taket_skickas_med_och_larmar(monkeypatch):
    _installning(monkeypatch, gallring_tak=10)
    kunder = [
        {"status": "klar", "tenant_id": "a", "totalt": 3},
        {"status": "tak_nadd", "tenant_id": "b", "totalt": 99, "antal": {}},
        {"status": "fel", "tenant_id": "c", "fel": "något föll"},
    ]
    lagring = _Lagring(svar={"status": "kord", "dag": "2026-11-18", "kunder": kunder})
    mejl: list[dict] = []

    async def _prioriterat(rubrik, **kw):
        mejl.append({"rubrik": rubrik, **kw})
        return True

    monkeypatch.setattr("app.notifications.prioriterat_mejl.skicka_prioriterat", _prioriterat)

    svar = await gallring.kor_gallring(lagring, nu=NATT)

    assert svar["status"] == "kord"
    assert lagring.anrop == [10]
    assert [m["tenant_id"] for m in mejl] == ["b", "c"]
    assert "taket" in mejl[0]["rubrik"]
    handelser = await lagring.list_platform_events(level="error")
    assert {h["tenant_id"] for h in handelser} == {"b", "c"}
    assert all(h["source"] == "gallring" for h in handelser)


@pytest.mark.anyio
async def test_minneslagret_gallrar_inte():
    assert (await MemoryStorage().gallra_dygnet(tak=1))["status"] == "ingen_databas"


@pytest.mark.anyio
async def test_ett_fel_faller_inte_loopen(monkeypatch):
    _installning(monkeypatch, gallring_kontroll_sekunder=300)
    varv = 0

    async def _kastar(storage, nu=None):
        nonlocal varv
        varv += 1
        raise RuntimeError("databasen svarar inte")

    sovningar: list[float] = []

    async def _sov(sekunder):
        sovningar.append(sekunder)
        if len(sovningar) >= 2:
            raise asyncio.CancelledError

    monkeypatch.setattr(gallring, "kor_gallring", _kastar)
    # Modulens egen asyncio-referens byts, inte den globala: händelseloopen
    # testet kör i ska fortfarande kunna sova.
    monkeypatch.setattr(
        gallring, "asyncio", SimpleNamespace(sleep=_sov, CancelledError=asyncio.CancelledError)
    )

    with pytest.raises(asyncio.CancelledError):
        await gallring.run_gallring(SimpleNamespace(storage=MemoryStorage()))
    assert varv == 2 and sovningar == [300, 300]
