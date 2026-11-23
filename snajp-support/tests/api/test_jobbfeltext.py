"""Körningsrutans feltext ska gå att läsa för kunden.

`_jobbfeltext` lät allt som inte var ett leverantörsfel passera som "vårt eget
domänfel". Det gällde då också programfel: en KeyError visades som namnet på
nyckeln, en AttributeError som "'NoneType' object has no attribute 'get'" och
ett pydantic-fel som en engelsk fältlista, i rött i kundens körningsruta.
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from app.api.leads import _FEL_INTERNT, _jobbfeltext


class _Modell(BaseModel):
    antal: int


def _valideringsfel() -> ValidationError:
    try:
        _Modell(antal="inte ett tal")
    except ValidationError as fel:
        return fel
    raise AssertionError("modellen borde ha fällt")


def _jsonfel() -> json.JSONDecodeError:
    try:
        json.loads("{trasig")
    except json.JSONDecodeError as fel:
        return fel
    raise AssertionError("json borde ha fällt")


@pytest.mark.parametrize(
    "fel",
    [
        KeyError("company_name"),
        AttributeError("'NoneType' object has no attribute 'get'"),
        TypeError("unsupported operand type(s) for +: 'int' and 'str'"),
        IndexError("list index out of range"),
        TimeoutError("timed out"),
        ConnectionResetError("[WinError 10054]"),
        _valideringsfel(),
        _jsonfel(),
    ],
)
def test_programfel_blir_reservmeningen(fel):
    assert _jobbfeltext(fel) == _FEL_INTERNT


def test_eget_domanfel_passerar_orort():
    """Beslutet från 2026-09-13 står kvar: domänfel är skrivna för att läsas."""
    besked = "Prospektet saknar webbplats och kan inte undersökas."
    assert _jobbfeltext(ValueError(besked)) == besked


def test_tomt_fel_ger_reserven():
    assert _jobbfeltext(RuntimeError("")) == _FEL_INTERNT
