"""SNI-koder: formatet valideras strikt, innehållet gör det inte."""

from __future__ import annotations

import pytest

from app.leads.sni import (
    SNI_NAMN,
    OgiltigSniKodError,
    beskriv_kod,
    matchar_sni,
    namn_for_kod,
    normalisera_kod,
    validera_kod,
)


@pytest.mark.parametrize("rå", ["43.220", "43220", " 43.220 ", "43.22"])
def test_alla_skrivsatt_normaliseras_till_ett(rå):
    """Register skriver koden olika. Utan normalisering missar filtret
    hälften av träffarna för att källan utelämnade en punkt."""
    assert normalisera_kod(rå) == "43.220"


def test_okand_men_valformad_kod_slapps_igenom():
    """Tabellen är ett hjälpmedel för läsbarhet, inte en vitlista. SCB har
    800 koder och vi har ~50."""
    assert validera_kod("01.110") == "01.110"
    assert namn_for_kod("01.110") == "01.110"  # visas som sig själv


def test_trasigt_format_kastar():
    with pytest.raises(OgiltigSniKodError) as fel:
        validera_kod("VVS")
    assert "43.220" in str(fel.value)  # felet visar ett exempel


def test_beskrivningen_ar_kod_plus_klartext():
    assert beskriv_kod("43.220") == "43.220 — VVS-arbeten"


def test_alla_koder_i_tabellen_ar_valformade():
    for kod in SNI_NAMN:
        assert validera_kod(kod) == kod


def test_exkludering_vinner_over_inkludering():
    """En kund som både bett om 'bygg' och undantagit 'takarbeten' menar det
    senare som ett undantag från det förra."""
    assert not matchar_sni("43.910", inkludera=["43.910", "43.220"], exkludera=["43.910"])
    assert matchar_sni("43.220", inkludera=["43.910", "43.220"], exkludera=["43.910"])


def test_utan_inkluderingskrav_slapps_allt_igenom():
    assert matchar_sni("62.020")
    assert matchar_sni(None)


def test_saknad_kod_uppfyller_inte_ett_krav():
    """Ett okänt bolag uppfyller inte ett krav, det slipper det inte."""
    assert not matchar_sni(None, inkludera=["43.220"])
    assert not matchar_sni("", inkludera=["43.220"])
