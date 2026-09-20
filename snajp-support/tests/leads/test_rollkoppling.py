"""Flaggan "rollkopplingen är oklar" — se app/leads/rollkoppling.py."""

from __future__ import annotations

import pytest

from app.leads.rollkoppling import rollkoppling_oklar


@pytest.mark.parametrize(
    ("rad", "vantat"),
    [
        # Namngiven person med roll — klar koppling, ingen flagga.
        ({"contact_name": "Anna Ek", "contact_role": "VD", "contact_email": "anna.ek@bolag.se"}, False),
        # Namngiven person UTAN roll — flaggas.
        ({"contact_name": "Anna Ek", "contact_role": None, "contact_email": "anna.ek@bolag.se"}, True),
        # Personlig adress utan namn och utan roll — en person nås ändå, flaggas.
        ({"contact_name": "", "contact_role": "", "contact_email": "anna.ek@bolag.se"}, True),
        # Funktionsadress utan namn — en funktion kontaktas, inte en person.
        ({"contact_name": "", "contact_role": "", "contact_email": "info@bolag.se"}, False),
        # Funktionsadress med belagd roll (kursadministratör bakom kurs@) — ingen flagga.
        ({"contact_name": "", "contact_role": "Kursadministratör", "contact_email": "kurs@bolag.se"}, False),
        # Ingen kontakt alls — inget att flagga.
        ({"contact_name": None, "contact_role": None, "contact_email": None}, False),
        # Roll i bara blanksteg räknas som saknad.
        ({"contact_name": "Bo Alm", "contact_role": "   ", "contact_email": None}, True),
    ],
)
def test_rollkoppling_oklar(rad, vantat):
    assert rollkoppling_oklar(rad) is vantat
