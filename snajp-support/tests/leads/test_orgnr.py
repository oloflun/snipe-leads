"""Org.nr: kontrollsiffran fångar skrivfel, ingenting annat."""

from __future__ import annotations

import pytest

from app.leads.orgnr import (
    OgiltigtOrgnrError,
    formatera,
    harled_webbplats,
    juridisk_form,
    normalisera,
    validera_format,
)

# Livrustning AB — riktigt nummer ur kundens egen kunskapsbas.
LIVRUSTNING = "556824-9022"


@pytest.mark.parametrize("skrivsatt", ["556824-9022", "5568249022", " 556824 9022 ", "16556824-9022"])
def test_alla_skrivsatt_normaliseras(skrivsatt):
    """Prefixet 16 är en sekelmarkör ur myndighetsregister och måste bort före
    kontrollsiffran, annars faller giltiga nummer."""
    assert validera_format(skrivsatt) == "5568249022"


def test_formateras_till_formen_folk_kanner_igen():
    assert formatera("5568249022") == "556824-9022"


def test_skrivfel_i_en_siffra_fangas():
    assert validera_format(LIVRUSTNING)
    with pytest.raises(OgiltigtOrgnrError) as fel:
        validera_format("556824-9023")
    assert "Kontrollsiffran" in str(fel.value)


def test_omkastade_siffror_fangas():
    with pytest.raises(OgiltigtOrgnrError):
        validera_format("556824-9202")


def test_personnummer_avvisas_med_ett_begripligt_skal():
    """Utan den här kontrollen lagrar vi en känslig personuppgift i en kolumn
    som aldrig var avsedd för det."""
    with pytest.raises(OgiltigtOrgnrError) as fel:
        validera_format("19850312-1234")
    assert "personnummer" in str(fel.value)


def test_fel_langd_sager_vilken_langd():
    with pytest.raises(OgiltigtOrgnrError) as fel:
        validera_format("55682490")
    assert "tio siffror" in str(fel.value) and "8" in str(fel.value)


def test_tomt_ger_en_uppmaning_inte_ett_tekniskt_fel():
    with pytest.raises(OgiltigtOrgnrError) as fel:
        validera_format("")
    assert "Fyll i" in str(fel.value)


def test_juridisk_form_ur_forsta_siffran():
    assert juridisk_form(LIVRUSTNING) == "aktiebolag"
    assert juridisk_form("769620-1234") is not None  # 7 = ekonomisk förening
    assert juridisk_form("") is None


# -- Webbplatsgissningen ----------------------------------------------------


def test_webbplats_harleds_ur_foretagsdoman():
    assert harled_webbplats("anna@livrustning.se") == "https://livrustning.se"


@pytest.mark.parametrize("epost", ["anna@gmail.com", "x@hotmail.com", "y@live.se"])
def test_publik_epostdoman_ger_ingen_gissning(epost):
    """Att föreslå gmail.com hade fått agenten att researcha Google."""
    assert harled_webbplats(epost) == ""


def test_skrap_ger_tom_strang():
    assert harled_webbplats("inte en adress") == ""
    assert harled_webbplats(None) == ""
