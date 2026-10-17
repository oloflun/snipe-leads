"""Målområdet med Norrlands städer (development 2026-10-08).

En körning på 40 leads med området "Umeå, Luleå, Sundsvall, Skellefteå,
Resten av Norrland" gav 6: Luleå, Sundsvall och Skellefteå fanns inte i
kommunregistret, och förfiltret och bedömningen räknade Umeå som enda
målområde. 22 bolag i just de valda städerna fälldes som "utanför
målområdet"."""

from app.leads.bedomning import _ort_rad
from app.leads.forfilter import forfiltrera
from app.leads.profil import slå_ihop

NORRLAND = {"geography": ["Umeå", "Luleå", "Sundsvall", "Skellefteå", "Resten av Norrland"]}


def _utfall(profil, postnr):
    return (_ort_rad(profil, {"postnummer": postnr}, {}) or {}).get("utfall")


def test_valda_norrlandsstader_falls_inte():
    p = slå_ihop({}, NORRLAND)
    for postnr in ("931 54", "973 42", "856 51", "903 26"):
        assert forfiltrera(p, {"company_name": "X", "postnr": postnr}) is None, postnr
        assert _utfall(p, postnr) == "träff", postnr


def test_resten_av_norrland_tar_hela_landsdelen_men_inte_stockholm():
    p = slå_ihop({}, NORRLAND)
    assert forfiltrera(p, {"company_name": "X", "postnr": "830 05"}) is None  # Jämtland
    assert forfiltrera(p, {"company_name": "X", "postnr": "111 22"})
    assert _utfall(p, "111 22") == "miss"


def test_utan_landsdel_galler_bara_de_valda_kommunerna():
    p = slå_ihop({}, {"geography": ["Umeå", "Luleå"]})
    assert forfiltrera(p, {"company_name": "X", "postnr": "973 42"}) is None
    assert forfiltrera(p, {"company_name": "X", "postnr": "856 51"})


def test_ett_oversattbart_omrade_faller_aldrig_pa_postnummer():
    """Okänt fäller aldrig: ett område vi inte har postnummer för kan inte
    användas för att säga att ett bolag ligger utanför."""
    p = slå_ihop({}, {"geography": ["Umeå", "Västerbottens inland"]})
    assert forfiltrera(p, {"company_name": "X", "postnr": "921 31"}) is None
    assert _utfall(p, "921 31") == "okänd"
