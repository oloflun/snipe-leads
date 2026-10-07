"""scripts/omklassa_listspar.py: listspårets rader körs om genom den nya
kontaktsökningen (Antons regler 12–16, 2026-10-07). Bara de rena delarna
testas här; skriptet körs aldrig mot en databas i sviten.

Antons krav 2026-10-07: ingen lista och ingen listrad raderas. En flyttad
rad märks i signal_detalj, i samma transaktion som prospektet skapas.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

import omklassa_listspar as ok  # noqa: E402

from app.leads.sources import merinfo  # noqa: E402

RAD = {
    "id": "rad-1",
    "company_name": "Alfa Bygg AB",
    "website": "https://alfabygg.se",
    "ort": "Mölndal",
    "orgnr": "556000-0001",
    "source_name": "merinfo",
    "source_url": "https://www.merinfo.se/foretag/Alfa-Bygg-AB-5560000001/2k",
    "signal_detalj": "Ingen kontaktmejl på webbplatsen",
    "is_test": False,
}

BOLAGSSIDA = """\
# [Alfa Bygg AB](https://www.merinfo.se/foretag/x)
Org.nr: 556000-0001
## Telefonnummer
[ __ 031-11 11 11 ](tel:+46311111111)
## Bolagsinformation
Verkställande direktör:
     [ Test Testsson ](https://www.merinfo.se/person/M%C3%B6lndal/Test-1970/xxxx)
E-post:
     __Lägg till e-post
## Bolagsfakta
Antal anställda:
    4 st
Bolagsform
    Aktiebolag
"""


def _kandidat(**andring):
    bolag = merinfo.tolka_bolag(BOLAGSSIDA, RAD["source_url"])
    return {**ok.kandidat_ur_rad(RAD, bolag), **andring}


def test_kandidaten_far_registrets_vd_och_bolagsnummer_ur_cachen():
    k = _kandidat()
    assert (k["vd_namn"], k["_telefon"], k["anstallda"], k["website"]) == (
        "Test Testsson", "031-11 11 11", 4, "https://alfabygg.se")


def test_mejl_blir_iris_prospekt():
    kontakt = {"contact_email": "info@alfabygg.se", "contact_name": None, "contact_level": "role_address"}
    spar, skal, prospekt = ok.planera(RAD, _kandidat(), kontakt)
    assert (spar, skal) == ("iris", None)
    assert prospekt["contact_email"] == "info@alfabygg.se"
    assert (prospekt["anstallda"], prospekt["orgnr"], prospekt["contact_level"]) == (4, "556000-0001", "role_address")


def test_bara_telefon_och_vd_blir_ringlistan():
    spar, _skal, prospekt = ok.planera(RAD, _kandidat(), {"contact_phone": "031-12 34 56"})
    assert spar == "ring"
    assert (prospekt["contact_name"], prospekt["contact_role"], prospekt["contact_phone"]) == (
        "Test Testsson", "VD", "031-12 34 56")
    assert prospekt["contact_email"] is None


def test_sajt_utan_kontakt_provas_om_och_markt_rad_rors_inte():
    assert ok.planera(RAD, _kandidat(_telefon=None), None) == ("prova_om", "Sajt utan hittad kontakt", None)
    flyttad = {**RAD, "signal_detalj": ok.ny_signal_detalj(RAD["signal_detalj"], "iris", "2026-10-08")}
    assert flyttad["signal_detalj"] == "Ingen kontaktmejl på webbplatsen → flyttad till Iris 2026-10-08"
    assert ok.planera(flyttad, _kandidat(), {"contact_email": "info@alfabygg.se"})[0] == "redan_flyttad"


class _Markor:
    def __init__(self):
        self.satser: list[tuple[str, tuple]] = []
        self.rowcount = 1

    def execute(self, sql, params=()):
        self.satser.append((" ".join(sql.split()).lower(), tuple(params)))

    def fetchone(self):
        return ("prospekt-1",)


@pytest.mark.parametrize("spar", ["iris", "ring"])
def test_skrivningen_skapar_och_marker_men_raderar_aldrig(spar):
    kontakt = {"contact_email": "info@alfabygg.se"} if spar == "iris" else {"contact_phone": "031-12 34 56"}
    _, _, prospekt = ok.planera(RAD, _kandidat(), kontakt)
    cur = _Markor()
    ok._skriv(cur, "tenant-1", RAD, spar, prospekt, "2026-10-08")
    satser = [s for s, _ in cur.satser]
    assert not any(s.startswith("delete") for s in satser)
    assert satser[0].startswith("insert into prospects")
    assert spar in cur.satser[0][1], "origin är spåret ('iris' eller 'ring')"
    assert [s.split(" (")[0] for s in satser[1:3]] == ["insert into prospect_sources"] * 2
    assert satser[-1].startswith("update lead_list_items set signal_detalj")
    assert cur.satser[-1][1][0].endswith(f"→ flyttad till {ok.MARKERING[spar]} 2026-10-08")
