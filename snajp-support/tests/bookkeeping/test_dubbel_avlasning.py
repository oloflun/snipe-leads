"""Dubbelgenomgången: varje underlag läses två gånger, koden sammanför.

Regeln testerna vaktar (produktkrav 2026-09-14): den andra genomgången får
FYLLA luckor den första lämnade, men aldrig VINNA över den — läser de två
olika värden utelämnas fältet och grinden skickar underlaget till granskning.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.agent.bookkeeping_agent import (
    STEG_AVLASNING,
    STEG_KONTROLLASNING,
    _sammanfor_avlasningar,
    las_underlag,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


# -- Sammanföringen, ren funktion --------------------------------------------


def test_lucka_i_ena_genomgangen_fylls_av_den_andra():
    forsta = {"brutto": Decimal("1250"), "riktning": "kostnad"}
    andra = {"brutto": Decimal("1250"), "riktning": "kostnad", "datum": date(2026, 3, 5)}
    resultat, konflikter = _sammanfor_avlasningar(forsta, andra)
    assert resultat["datum"] == date(2026, 3, 5)
    assert konflikter == []


def test_konflikt_utelamnar_faltet_i_stallet_for_att_valja():
    forsta = {"brutto": Decimal("1250"), "datum": date(2026, 3, 5)}
    andra = {"brutto": Decimal("1520"), "datum": date(2026, 3, 5)}
    resultat, konflikter = _sammanfor_avlasningar(forsta, andra)
    assert "brutto" not in resultat
    assert resultat["datum"] == date(2026, 3, 5)
    assert len(konflikter) == 1
    assert "brutto" in konflikter[0]


def test_samstammiga_genomgangar_ger_hela_faltuppsattningen():
    falt = {
        "datum": date(2026, 3, 5),
        "motpart": "Eknäs Bygg Gruppen AB",
        "brutto": Decimal("1250"),
        "momssats": Decimal("0.25"),
        "riktning": "kostnad",
        "betalstatus": "betald",
        "kategori": "varuinkop",
    }
    resultat, konflikter = _sammanfor_avlasningar(dict(falt), dict(falt))
    assert resultat == falt
    assert konflikter == []


# -- Hela kedjan, med LLM-anropet fejkat vid nätverksgränsen -----------------


class _FejkadLLM:
    """Svarar med nästa kropp ur kön för varje anrop. Formen speglar det
    `_kor_avlasning` faktiskt läser: response.choices[0].message.content."""

    def __init__(self, kroppar: list[dict]):
        self._kon = list(kroppar)
        self.antal_anrop = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **_kwargs):
        self.antal_anrop += 1
        kropp = self._kon.pop(0)
        meddelande = SimpleNamespace(content=json.dumps(kropp), reasoning_content=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=meddelande)], usage=None)


def _kontrakt(**falt) -> dict:
    """Ett svar som uppfyller utdatakontraktet, med de fält testet vill ha."""
    return {"sources_used": ["rad 1"], "context_refs": ["underlag"], **falt}


KVITTOTEXT = "Eknäs Bygg Gruppen AB\n2026-03-05\nTotalt 1 250,00 kr\nMoms 25%\nBetalt med kort"


@pytest.mark.anyio
async def test_underlaget_las_tva_ganger_och_stegen_namnges():
    llm = _FejkadLLM(
        [
            _kontrakt(
                datum="2026-03-05",
                motpart="Eknäs Bygg Gruppen AB",
                brutto="1250.00",
                momssats=25,
                riktning="kostnad",
                betalstatus="betald",
                kategori="varuinkop",
            )
        ]
        * 2
    )
    with patch("app.agent.bookkeeping_agent.get_llm_client", return_value=llm):
        avlasning = await las_underlag(KVITTOTEXT)

    assert llm.antal_anrop == 2
    assert [steg.skill for steg in avlasning.trace.steps] == [
        STEG_AVLASNING,
        STEG_KONTROLLASNING,
    ]
    assert avlasning.status == "klar"
    assert avlasning.verifikat, "samstämmiga genomgångar ska ge ett konterat verifikat"


@pytest.mark.anyio
async def test_konflikt_mellan_genomgangarna_ger_granskning_inte_verifikat():
    gemensamt = dict(
        datum="2026-03-05",
        motpart="Eknäs Bygg Gruppen AB",
        momssats=25,
        riktning="kostnad",
        betalstatus="betald",
        kategori="varuinkop",
    )
    llm = _FejkadLLM(
        [
            _kontrakt(brutto="1250.00", **gemensamt),
            _kontrakt(brutto="1520.00", **gemensamt),  # sifferkast — klassikern
        ]
    )
    with patch("app.agent.bookkeeping_agent.get_llm_client", return_value=llm):
        avlasning = await las_underlag(KVITTOTEXT)

    assert "brutto" not in avlasning.falt
    assert avlasning.status != "klar"
    assert avlasning.verifikat == ()
    assert "Dubbelkontrollen" in avlasning.anmarkning


@pytest.mark.anyio
async def test_andra_genomgangen_fangar_falt_den_forsta_missade():
    fullstandigt = dict(
        datum="2026-03-05",
        motpart="Eknäs Bygg Gruppen AB",
        brutto="1250.00",
        momssats=25,
        riktning="kostnad",
        betalstatus="betald",
        kategori="varuinkop",
    )
    utan_datum = {k: v for k, v in fullstandigt.items() if k != "datum"}
    llm = _FejkadLLM([_kontrakt(**utan_datum), _kontrakt(**fullstandigt)])
    with patch("app.agent.bookkeeping_agent.get_llm_client", return_value=llm):
        avlasning = await las_underlag(KVITTOTEXT)

    assert avlasning.falt["datum"] == date(2026, 3, 5)
    assert avlasning.status == "klar"
