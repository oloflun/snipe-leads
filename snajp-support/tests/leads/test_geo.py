"""Geografifiltret. Ett targetingfilter som är för generöst kostar pengar och
förtroende — varje falsk träff är ett mejl till fel bolag."""

from __future__ import annotations

import pytest

from app.leads.geo import (
    OkandRegionError,
    beskriv_region,
    hamta_region,
    kanda_regioner,
    matchar_region,
)


def test_de_tva_presetsen_finns():
    assert set(kanda_regioner()) >= {"umea", "goteborg"}


def test_umea_omfattar_de_fyra_kommunerna():
    kommuner = {k.namn for k in hamta_region("umea").kommuner}
    assert kommuner == {"Umeå", "Vännäs", "Nordmaling", "Robertsfors"}


def test_goteborg_omfattar_de_sju_kommunerna():
    kommuner = {k.namn for k in hamta_region("goteborg").kommuner}
    assert kommuner == {
        "Göteborg",
        "Mölndal",
        "Partille",
        "Härryda",
        "Kungsbacka",
        "Kungälv",
        "Lerum",
    }


def test_okand_region_kastar_i_stallet_for_att_tystna():
    """Ett tyst bortfall hade gett en körning helt utan geografiskt filter,
    alltså hela Sverige, utan att något sa ifrån."""
    with pytest.raises(OkandRegionError) as fel:
        hamta_region("malmo")
    assert "umea" in str(fel.value)  # felet räknar upp vad som FINNS


@pytest.mark.parametrize("postnr", ["903 27", "90327", " 907 30 "])
def test_postnummer_matchar_oavsett_formatering(postnr):
    assert matchar_region(["umea"], postnr=postnr)


def test_postnummer_avgor_ensamt_nar_det_finns():
    """Ortnamn är fritext och stavas olika. Postnumret är strukturerat, så det
    vinner — annars hade en felstavad ort släppt in ett bolag som postnumret
    redan dömt ut."""
    # Rätt ort, fel postnummer → utanför.
    assert not matchar_region(["umea"], postnr="931 57", ort="Umeå")
    # Fel ort, rätt postnummer → innanför.
    assert matchar_region(["umea"], postnr="903 27", ort="Skellefteå")


def test_ortnamn_anvands_bara_nar_postnummer_saknas():
    assert matchar_region(["goteborg"], ort="Mölndal")
    assert not matchar_region(["goteborg"], ort="Borås")


def test_okand_plats_slapps_inte_igenom():
    """'Vet inte' får aldrig betyda 'släpp igenom' i ett urvalsfilter."""
    assert not matchar_region(["umea"], postnr=None, ort=None)
    assert not matchar_region(["umea"], postnr="", ort="   ")


def test_tom_regionlista_betyder_ingen_begransning():
    assert matchar_region([], postnr="211 20", ort="Malmö")


def test_flera_regioner_ar_en_union():
    assert matchar_region(["umea", "goteborg"], postnr="411 03")
    assert matchar_region(["umea", "goteborg"], postnr="903 27")
    assert not matchar_region(["umea", "goteborg"], postnr="211 20")


def test_goteborgsserien_slutar_vid_426():
    assert matchar_region(["goteborg"], postnr="426 71")
    assert not matchar_region(["goteborg"], postnr="427 00")


def test_beskrivningen_raknar_upp_kommunerna():
    text = beskriv_region("umea")
    assert "Umeåområdet" in text and "Vännäs" in text
