"""Gränsen går vid vad uttrycket RIKTAS mot, inte vid hur hårt det är.

Det viktigaste testet i filen är det första: en arg kund ska få hjälp, inte en
tillrättavisning. Faller det har filtret börjat straffa den som har mest rätt
att vara upprörd.
"""

from __future__ import annotations

import pytest

from app.leads.abuse_gate import (
    ALLVARLIG,
    FRUSTRATION,
    INGET,
    RIKTAD,
    check_abuse,
    ton_instruktion,
)


# -- Frustration: släpps alltid igenom --------------------------------------


@pytest.mark.parametrize(
    "meddelande",
    [
        "Det här är ju för jävligt, jag har väntat i tre veckor.",
        "Vilken skitprodukt, den slutade fungera efter en dag.",
        "Fan vad dåligt att ingen svarar.",
        "Helvete vad krångligt det här är.",
        "This is bullshit, I have been waiting for weeks.",
    ],
)
def test_arg_kund_far_hjalp_inte_tillrattavisning(meddelande):
    """Den som skriver så är arg på en verklig sak och har oftast rätt."""
    beslut = check_abuse(meddelande)
    assert beslut.niva == FRUSTRATION
    assert beslut.replik is None  # ingen tillrättavisning
    assert beslut.ska_svara_normalt
    assert not beslut.ska_eskalera


def test_frustration_ger_en_toninstruktion_men_inget_avbrott():
    instruktion = ton_instruktion(check_abuse("Det här är ju för jävligt."))
    assert "frustrerad" in instruktion
    assert "kommentera ordvalet" in instruktion  # dvs: låt bli


# -- Riktat: påpekas, men hjälpen fortsätter --------------------------------


@pytest.mark.parametrize(
    "meddelande",
    [
        "Du är helt korkad.",
        "Ni är idioter allihop.",
        "Din dumma bot.",
        "You are stupid.",
    ],
)
def test_riktad_forolampning_papekas(meddelande):
    beslut = check_abuse(meddelande)
    assert beslut.niva == RIKTAD
    assert beslut.replik and "hjälper dig gärna" in beslut.replik
    assert beslut.ska_svara_normalt  # hjälpen fortsätter ändå


def test_samma_ord_utan_personmarkor_ar_inte_riktat():
    """'Det här är dumt' är frustration. 'Du är dum' är riktat. Skillnaden är
    vad ordet syftar på, och den skillnaden avgör om kunden får en
    tillrättavisning."""
    assert check_abuse("Det här upplägget är korkat.").niva != RIKTAD


# -- Allvarligt: avbryt och eskalera ----------------------------------------


@pytest.mark.parametrize(
    "meddelande",
    [
        "Jag ska döda dig.",
        "Ta livet av dig.",
        "I will find you.",
        "Fuck you.",
    ],
)
def test_hot_avbryter_och_eskalerar(meddelande):
    beslut = check_abuse(meddelande)
    assert beslut.niva == ALLVARLIG
    assert beslut.ska_eskalera
    assert not beslut.ska_svara_normalt
    assert beslut.replik and "avslutar" in beslut.replik


def test_krankning_mot_folkgrupp_avbryter():
    assert check_abuse("Jävla blattar överallt.").niva == ALLVARLIG


def test_allvarligt_vinner_over_frustration():
    """Ett meddelande som innehåller båda ska behandlas som det allvarligare."""
    assert check_abuse("Fan vad dåligt. Jag ska döda dig.").niva == ALLVARLIG


# -- Normalt ----------------------------------------------------------------


@pytest.mark.parametrize(
    "meddelande",
    [
        "Hej, hur lång är garantin på en hjärtstartare?",
        "Kan jag ångra mitt köp?",
        "",
        "   ",
    ],
)
def test_vanliga_meddelanden_passerar_orort(meddelande):
    beslut = check_abuse(meddelande)
    assert beslut.niva == INGET
    assert beslut.replik is None
    assert ton_instruktion(beslut) == ""


def test_filtret_faller_inte_pa_ord_som_innehaller_ett_kraftuttryck():
    """'Skitbra' och 'assistent' innehåller listade stammar men är oskyldiga.
    Varje falskt utslag är en kund som får en tillrättavisning i stället för
    hjälp."""
    assert check_abuse("Assistenten var skitbra, tack!").niva == INGET
