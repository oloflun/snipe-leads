"""Produktraden i pitchen måste kunna följa efter orden "Vi säljer ".

UPPMÄTT mot dev-deployen 2026-08-21. Pitchen sa:

    "Vi säljer Vad vi säljer: Inredning och utemiljö för företag …"

Affärskontexten är en FÄLTLISTA — onboardingen skriver den så — och att ta
dess första mening rakt av tar med etiketten. Läsaren ser inte ett mejl med ett
skarvfel; hen ser ett bolag som inte läst sitt eget utskick.
"""

from __future__ import annotations

from app.api.leads import _produktrad

KONTEXT = """Organisationsnummer: 556677-8899
Webbplats: https://nordlys.se
Vad vi säljer: Inredning och utemiljö för företag — förvaring, belysning, textil.
Särskilt fokus: kommuner"""


def test_etiketten_folier_inte_med():
    rad = _produktrad(KONTEXT)
    assert not rad.lower().startswith("vad vi säljer")
    assert rad.startswith("inredning och utemiljö")


def test_orgnr_och_webbplats_hamnar_aldrig_i_pitchen():
    """De står FÖRST i dokumentet, alltså är det dem en naiv läsning tar."""
    rad = _produktrad(KONTEXT)
    assert "556677" not in rad
    assert "nordlys.se" not in rad


def test_forsta_bokstaven_gemeniseras():
    """Raden fortsätter en mening som redan börjat.

    "Vi säljer Inredning och …" läser som ett citat mitt i en mening.
    """
    assert _produktrad("Vad vi säljer: Hjärtstartare till arbetsplatser")[0].islower()


def test_utan_kontext_blir_det_tomt_inte_en_gissning():
    """Anroparen har en tydlig platshållare. En halv rubrik är sämre."""
    assert _produktrad("") == ""
    assert _produktrad("   \n  ") == ""


def test_fritext_utan_etiketter_fungerar_ocksa():
    """Alla kunder skriver inte en fältlista."""
    rad = _produktrad("Vi hyr ut kaffemaskiner till kontor. Service ingår.")
    assert rad.startswith("vi hyr ut kaffemaskiner till kontor")
    assert "Service ingår" not in rad
