"""Säljklyschorna (Sebbe 2026-10-24, skrivstilens omgång 7)."""

import pytest

from app.leads import stilkontroll as stil

BAS = (
    "Hej,\n\nNi söker två nya konsulter till kontoret i Luleå.\n\n"
    "Vår agent Iris hittar nya uppdrag åt er{}.\n\nSvara \"ja\" så skickar vi de fem."
)


def _koder(text: str) -> set[str]:
    return {a.kod for a in stil.kontrollera(text).anmarkningar}


@pytest.mark.parametrize(
    "fras",
    [", skräddarsytt för er", " och sparar tid och pengar", " så att ni tar nästa steg till nästa nivå",
     ", en möjlighet att växa", " med en smidig start", " och frigör tid"],
)
def test_klyschan_falls(fras):
    assert "klyscha" in _koder(BAS.format(fras))


def test_utan_klyscha_inget_fynd_och_dygnet_runt_ar_tillatet():
    assert "klyscha" not in _koder(BAS.format(" dygnet runt"))


#: Provet 2026-10-24: fem utkast efter omgång 7, verkliga ingångar.
@pytest.mark.parametrize(
    "ingang",
    [
        "Att leverera totalentreprenader kräver att ni kan vara på plats i varje projekt, inte att lägga tid på att hitta nästa företagskund.",
        "Att sätta kunden i fokus kräver att du är på plats i varje projekt, inte att du lägger tid på att hitta nästa.",
        "När er webbplats har tekniska problem kan det vara svårt för kunder att få svar på sina frågor.",
    ],
)
def test_provets_mallingangar_falls(ingang):
    text = f"Hej,\n\n{ingang}\n\nVår agent Iris hittar nya uppdrag åt er.\n\nSvara \"ja\" så skickar vi de fem."
    assert "mallord_i_ingangen" in _koder(text)


def test_effektivt_falls():
    assert "effektivisera" in _koder(BAS.format(" så att ni hanterar förfrågningarna effektivt"))


@pytest.mark.parametrize("amne", ["nya kunder", "Nya företagskunder", "fler uppdrag"])
def test_abstrakt_amne_falls(amne):
    assert "abstrakt_amne" in {a.kod for a in stil.abstrakt_amne(amne)}


@pytest.mark.parametrize("amne", ["offertförfrågningar inom 48 timmar", "Nya kunder utanför gruppen", "kontoret i Luleå"])
def test_konkret_amne_godkanns(amne):
    assert not stil.amne_fynd(amne, bolag="Walters Bygg AB", produkt="Iris, leadsagenten")
    assert not stil.abstrakt_amne(amne)
