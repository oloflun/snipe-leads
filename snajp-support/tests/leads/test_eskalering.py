"""Eskaleringsreglerna: normalisering, tröskeln och ämnesfiltret."""

from app.leads.eskalering import (
    STANDARD,
    aktiva_amnen,
    amnen_i_svar,
    normalisera,
    under_troskel,
)


def test_saknat_eller_trasigt_varde_ger_standard():
    assert normalisera(None) == STANDARD
    assert normalisera("på") == STANDARD
    assert normalisera({"prisfragor": "ja", "kvalificeringstroskel": "hög"}) == STANDARD


def test_sparade_varden_och_tak_pa_troskeln():
    regler = normalisera({"prisfragor": False, "kvalificeringstroskel": 140})
    assert regler["prisfragor"] is False
    assert regler["kvalificeringstroskel"] == 100
    assert regler["juridik"] is True, "Ett ej sparat fält ska behålla standardvärdet."


def test_troskeln_galler_bara_kvalificerade_med_kant_fit():
    regler = normalisera({"kvalificeringstroskel": 60})
    assert under_troskel(regler, qualified=True, icp_fit=0.55) is True
    assert under_troskel(regler, qualified=True, icp_fit=0.60) is False
    assert under_troskel(regler, qualified=False, icp_fit=0.10) is False
    assert under_troskel(regler, qualified=True, icp_fit=None) is False
    avstangd = normalisera({"osaker_kvalificering": False})
    assert under_troskel(avstangd, qualified=True, icp_fit=0.10) is False


def test_amnesfiltret():
    assert amnen_i_svar("Vad kostar det i månaden?") == {"pris"}
    assert amnen_i_svar("Skicka gärna prisexempel") == {"pris"}
    assert amnen_i_svar("Hur ser avtalet ut, och följer ni GDPR?") == {"juridik"}
    assert amnen_i_svar("Kan ni ta ett möte på torsdag?") == set()
    # Prefix får inte träffa: "prisma" är inte ett pris, "kosta på" inte heller.
    assert amnen_i_svar("Vi jobbar med Prisma-plattformen.") == set()


def test_bara_paslagna_regler_lamnar_over():
    regler = normalisera({"prisfragor": False})
    assert aktiva_amnen(regler, {"pris", "juridik"}) == ["juridik"]
    assert aktiva_amnen(STANDARD, {"pris", "juridik"}) == ["pris", "juridik"]
