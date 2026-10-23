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
