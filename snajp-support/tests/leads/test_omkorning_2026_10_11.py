"""Snajps omkörning 2026-10-11: 100 av 100 leads fälldes och doldes.

Två fel: researchuppgiften saknade fältet produkt (produktmatchningen föll
för varje bolag), och målområdet "Göteborg & Norrland (Umeå)" lästes som
ett enda område, så postnummer i Göteborg låg "utanför"."""

from app.agent.leads_research_v2 import _vald_produkt
from app.leads.bedomning import TRAFF, _ort_rad
from app.leads.profil import slå_ihop, tom_profil

PRODUKTER = [{"namn": "Iris, leadsagenten", "nytta": "x"}, {"namn": "Kvittohanteraren", "nytta": "y"}]


def test_sammansatt_omrade_delas_upp():
    p = slå_ihop(tom_profil(), {"geography": ["Göteborg & Norrland (Umeå)"]})
    assert "Göteborg" in p["kommuner"]
    assert p["omraden"] == ["Norrland (Umeå)"]
    assert _ort_rad(p, {"postnummer": "424 91"}, {})["utfall"] == TRAFF
    assert _ort_rad(p, {"postnummer": "903 27"}, {})["utfall"] == TRAFF


def test_produkten_ur_faltet_eller_erbjudandet():
    assert _vald_produkt({"produkt": "kvittohanteraren"}, PRODUKTER)["namn"] == "Kvittohanteraren"
    # Modellen lämnade produkt tomt men namngav produkten i offer.
    assert _vald_produkt({"offer": {"name": "Iris, leadsagenten"}}, PRODUKTER)["namn"] == "Iris, leadsagenten"
    assert _vald_produkt({"offer": {"name": "Snajps AI-agenter"}}, PRODUKTER) is None
    assert _vald_produkt({}, PRODUKTER) is None
