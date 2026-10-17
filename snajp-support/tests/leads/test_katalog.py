"""Företagskatalogen som kontaktkälla (Anton 2026-10-10): hitta.se på org.nr."""

import json

import pytest

from app.leads import katalog
from app.leads.sources import merinfo


def _sida(bolag: list[dict]) -> str:
    data = {"props": {"pageProps": {"result": {"companies": bolag}}}}
    return f'<html><script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script></html>'


def test_tolka_hitta_tar_telefon_och_epost():
    html = _sida([{
        "displayName": "Exempel VVS AB",
        "attribute": [{"name": "email", "value": "Kontor@Exempelvvs.se"}, {"name": "offices", "value": "1.0"}],
        "phone": [{"label": "Telefonnummer", "callTo": "+46910000000", "displayAs": "0910-00 00 00"}],
    }])
    assert katalog.tolka_hitta(html) == {
        "namn": "Exempel VVS AB", "telefon": "0910-00 00 00", "epost": "kontor@exempelvvs.se",
    }


def test_tolka_hitta_utan_traff_eller_uppgifter():
    assert katalog.tolka_hitta("<html></html>") is None
    assert katalog.tolka_hitta(_sida([])) is None
    assert katalog.tolka_hitta(_sida([{"displayName": "Tomt AB", "attribute": [], "phone": []}])) is None


@pytest.mark.anyio
async def test_berika_fyller_bara_det_som_saknas(monkeypatch):
    async def _hitta(_orgnr):
        return {"namn": "X", "telefon": "070-000 00 00", "epost": "info@x.se"}

    monkeypatch.setattr(katalog, "hitta", _hitta)
    k = await katalog.berika({"company_name": "X AB", "orgnr": "556000-0001", "_epost": "vd@x.se"})
    assert k["_epost"] == "vd@x.se" and k["_telefon"] == "070-000 00 00" and k["_telefon_katalog"]
    # Enskild firma slås aldrig upp (NIX).
    assert "_telefon" not in await katalog.berika({"company_name": "Y", "orgnr": "19800101-1234"})


def test_katalogens_nummer_racker_for_ringlistan_utan_vd():
    """Örnbergs Plåtslageri (Antons exempel): numret i katalogen är bolagets
    publicerade, som sajtens, och kräver ingen VD i registret."""
    utan = {"company_name": "Ö AB", "orgnr": "556000-0002", "_telefon": "070-000 00 00"}
    assert merinfo.fordela(utan, None) == ("ej_kvalificerad", "Ingen namngiven VD")
    assert merinfo.fordela({**utan, "_telefon_katalog": True}, None) == ("ring", None)
    rad = merinfo.ringrad({**utan, "_telefon_katalog": True}, None)
    assert rad["signal_detalj"] == "Bara telefon, bolagets nummer i hitta.se"


@pytest.fixture
def anyio_backend():
    return "asyncio"
