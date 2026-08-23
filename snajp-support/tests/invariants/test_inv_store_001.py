"""INV-STORE-001 — MemoryStorage och PostgresStorage har identiska signaturer.

## Buggen den här stänger

`agent_runs` avvisade varje leads-körning i ett halvår. Testsviten var grön
hela tiden, eftersom den kör mot `MemoryStorage`, som saknade villkoret
Postgres hade. En metod som bara finns i EN av implementationerna — eller
som finns i båda med olika parametrar — ger en testsvit som ljuger.

Testet jämför tre saker per metod i `Storage`-protokollet:
  1. att metoden finns i BÅDA implementationerna
  2. att parameternamnen och deras ordning är desamma
  3. att default-värdena är desamma

Punkt 3 är inte kosmetik: `is_test: bool = False` i den ena och
`is_test: bool = True` i den andra hade gett två olika svar på frågan "räknas
den här körningen som kundvolym", utan att någon signatur såg fel ut.

## Varför det inte räcker med signaturer, och vad som täcker resten

En identisk signatur säger ingenting om vad metoden GÖR. Därför bor
värdemängderna (`AGENT_RUN_TYPES`, `BK_STATUSAR`, `BK_RIKTNINGAR`) och
valideringarna (`kontrollera_bk_*`, `bk_belopp`, `bk_datum`) i `base.py` och
anropas av båda lagringarna — det är strukturellt omöjligt för dem att glida
isär. Se `tests/api/test_agent_run_types.py` för samma resonemang på
agent_type.
"""

from __future__ import annotations

import inspect
from typing import get_type_hints

import pytest

from app.storage.base import Storage
from app.storage.memory import MemoryStorage
from app.storage.postgres import PostgresStorage

IMPLEMENTATIONER = (MemoryStorage, PostgresStorage)


def _protokollmetoder() -> list[str]:
    """Publika, asynkrona metoder deklarerade i protokollet."""
    return sorted(
        namn
        for namn, varde in vars(Storage).items()
        if not namn.startswith("_") and inspect.isfunction(varde)
    )


def test_protokollet_har_metoder_att_jamfora():
    """Utan den här mäter resten av filen ingenting."""
    metoder = _protokollmetoder()
    assert len(metoder) > 40, f"Hittade bara {len(metoder)} metoder — läser testet rätt klass?"
    # Bokföringen ska finnas med. Står den inte i protokollet gäller inga av
    # kontrollerna nedan för den.
    for namn in (
        "create_bk_underlag",
        "get_bk_underlag",
        "list_bk_underlag",
        "update_bk_underlag",
        "create_bk_verifikat",
        "list_bk_verifikat",
    ):
        assert namn in metoder, f"{namn} saknas i Storage-protokollet"


@pytest.mark.parametrize("metod", _protokollmetoder())
def test_metoden_finns_i_bada_implementationerna(metod):
    saknas = [impl.__name__ for impl in IMPLEMENTATIONER if not hasattr(impl, metod)]
    assert not saknas, (
        f"{metod} saknas i {saknas}. En metod som bara finns i en av lagringarna "
        f"ger en grön testsvit och ett fel i drift — se modulens docstring."
    )


@pytest.mark.parametrize("metod", _protokollmetoder())
def test_signaturen_ar_densamma_i_bada(metod):
    signaturer = {}
    for impl in IMPLEMENTATIONER:
        funktion = getattr(impl, metod, None)
        if funktion is None:
            pytest.skip(f"{metod} saknas — fälls av test_metoden_finns_i_bada_implementationerna")
        parametrar = inspect.signature(funktion).parameters
        signaturer[impl.__name__] = [
            (namn, p.kind, p.default) for namn, p in parametrar.items()
        ]

    minne, postgres = signaturer["MemoryStorage"], signaturer["PostgresStorage"]
    assert minne == postgres, (
        f"{metod} har olika signatur:\n"
        f"  MemoryStorage:   {minne}\n"
        f"  PostgresStorage: {postgres}"
    )


@pytest.mark.parametrize("metod", _protokollmetoder())
def test_implementationen_foljer_protokollet(metod):
    """Protokollet är kontraktet. En implementation som tagit en extra
    parameter har i praktiken en egen metod med samma namn."""
    protokoll = [
        (namn, p.kind, p.default)
        for namn, p in inspect.signature(getattr(Storage, metod)).parameters.items()
    ]
    for impl in IMPLEMENTATIONER:
        funktion = getattr(impl, metod, None)
        if funktion is None:
            pytest.skip(f"{metod} saknas i {impl.__name__}")
        faktisk = [
            (namn, p.kind, p.default)
            for namn, p in inspect.signature(funktion).parameters.items()
        ]
        assert faktisk == protokoll, (
            f"{impl.__name__}.{metod} följer inte protokollet:\n"
            f"  protokoll:      {protokoll}\n"
            f"  {impl.__name__}: {faktisk}"
        )


@pytest.mark.anyio
async def test_belopp_lagras_med_kolumnens_skala():
    """Samma värde måste bli samma STRÄNG i båda lagringarna.

    Postgres lagrar `numeric(5,4)` och ger `Decimal("0.2500")`. MemoryStorage
    lagrade `Decimal("0.25")` — samma tal, olika sträng. API:t serialiserar
    belopp som strängar (`_kr` i app/api/bookkeeping.py), så vyn fick "0.06" i
    varje test och "0.0600" i drift.

    Det hann bli en bugg: momsetiketten i BokforingPanel räknade fram 60 %
    i stället för 6 %, och BARA mot Postgres. En signaturjämförelse hade
    aldrig sett den — det är därför skalan sitter i den delade `bk_belopp`.
    """
    from decimal import Decimal

    from app.storage.memory import MemoryStorage

    storage = MemoryStorage()
    for sats in ("0.25", "0.12", "0.06", "0"):
        rad = await storage.create_bk_underlag(
            "t",
            sha256="a" * 64,
            filnamn="k.pdf",
            mimetyp="application/pdf",
            status="klar",
            brutto=Decimal("1250"),
            momssats=Decimal(sats),
        )
        # numeric(5,4) respektive numeric(14,2) — se migration 045.
        assert rad["momssats"].as_tuple().exponent == -4, f"{sats}: fel skala på momssats"
        assert rad["brutto"].as_tuple().exponent == -2, f"{sats}: fel skala på brutto"


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_bokforingens_typannoteringar_ar_decimal_inte_float():
    """INV-BOOK-001 vid lagringsgränsen.

    En `float`-annotering här hade inbjudit anropare att skicka float in i en
    numeric(14,2)-kolumn, där asyncpg tyst approximerar. Ett öre som försvinner
    i lagringen syns först när en periodrapport inte går ihop.
    """
    hints = get_type_hints(Storage.create_bk_underlag)
    for falt in ("brutto", "momssats"):
        assert "float" not in str(hints[falt]).lower(), f"{falt} annoterad med float"
        assert "Decimal" in str(hints[falt]), f"{falt} saknar Decimal i annoteringen"
