"""INV-BOOK-001 — belopp räknas i Decimal av kod, aldrig av modellen.

Testerna är skrivna mot handräknade facit, inte mot vad koden råkar svara.
Där ett fall är valt för att det är en KANT står skälet utskrivet — annars
läser en framtida läsare det som ett godtyckligt tal och tar bort det.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.bookkeeping.math import (
    BeloppsfelError,
    Konteringsrad,
    Post,
    avrunda_krona,
    avrunda_ore,
    balans,
    moms_fran_brutto,
    moms_fran_netto,
    netto_fran_brutto,
    summera_period,
    till_decimal,
)


# -- Grinden mot float -----------------------------------------------------


def test_float_avvisas_som_belopp():
    """Hela modulens premiss. Går den här igenom är resten oviktigt."""
    with pytest.raises(BeloppsfelError, match="float"):
        till_decimal(1199.50)


def test_float_avvisas_ocksa_via_post():
    with pytest.raises(BeloppsfelError, match="float"):
        Post(datum=date(2026, 3, 1), riktning="intakt", netto=1000.0, moms=Decimal("250"))


def test_float_avvisas_ocksa_via_konteringsrad():
    with pytest.raises(BeloppsfelError, match="float"):
        Konteringsrad(konto="1930", debet=1250.0)


def test_bool_ar_inte_ett_belopp():
    """bool är en int i Python, så utan egen gren hade True blivit 1 kr."""
    with pytest.raises(BeloppsfelError, match="bool"):
        till_decimal(True)


def test_strang_med_komma_och_mellanslag_lases():
    """Svensk inmatning: '1 199,50'. Både decimalkomma och tusenavskiljare."""
    assert till_decimal("1 199,50") == Decimal("1199.50")
    assert till_decimal("1\xa0199,50") == Decimal("1199.50")


def test_skrap_blir_fel_inte_noll():
    with pytest.raises(BeloppsfelError):
        till_decimal("ca 1200 kr")


def test_allt_som_kommer_ut_ar_decimal():
    assert isinstance(avrunda_ore("1.005"), Decimal)
    assert isinstance(avrunda_krona("1.5"), Decimal)
    assert isinstance(moms_fran_brutto("1250", "0.25"), Decimal)
    assert isinstance(netto_fran_brutto("1250", "0.25"), Decimal)


# -- Avrundning ------------------------------------------------------------


@pytest.mark.parametrize(
    ("belopp", "vantat"),
    [
        ("0.50", "1"),
        ("0.49", "0"),
        ("1.50", "2"),
        # 2,50 blir 3, inte 2. Med ROUND_HALF_EVEN (Pythons default) hade det
        # blivit 2 — det är precis den skillnaden testet finns för.
        ("2.50", "3"),
        # Kreditfakturan: halva bort från NOLL, inte uppåt.
        ("-0.50", "-1"),
        ("-1.50", "-2"),
        ("-0.49", "0"),
    ],
)
def test_oresavrundning_ar_halva_bort_fran_noll(belopp, vantat):
    assert avrunda_krona(belopp) == Decimal(vantat)


def test_avrunda_ore_pa_exakt_halvt_ore():
    assert avrunda_ore("0.005") == Decimal("0.01")
    assert avrunda_ore("-0.005") == Decimal("-0.01")


# -- Moms ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("brutto", "sats", "moms", "netto"),
    [
        ("1250.00", "0.25", "250.00", "1000.00"),
        ("1199.50", "0.25", "239.90", "959.60"),
        ("112.00", "0.12", "12.00", "100.00"),
        ("106.00", "0.06", "6.00", "100.00"),
        ("100.00", "0", "0.00", "100.00"),
    ],
)
def test_moms_ur_brutto(brutto, sats, moms, netto):
    assert moms_fran_brutto(brutto, sats) == Decimal(moms)
    assert netto_fran_brutto(brutto, sats) == Decimal(netto)


def test_netto_plus_moms_ar_alltid_exakt_brutto():
    """Kanten som motiverar att netto räknas som en subtraktion.

    10,00 kr med 12 % moms ger 1,0714... kr moms. Räknades nettot med en egen
    division skulle netto + moms kunna avvika med ett öre från brutto, och den
    differensen dyker upp som en obalans i verifikatet långt senare.
    """
    for brutto in ("10.00", "33.33", "99.99", "1.00", "7.77"):
        for sats in ("0.25", "0.12", "0.06", "0"):
            moms = moms_fran_brutto(brutto, sats)
            netto = netto_fran_brutto(brutto, sats)
            assert netto + moms == Decimal(brutto), f"{brutto} @ {sats}"


def test_pahittad_momssats_avvisas():
    """20 % finns i andra länder, inte här. Modellen ska inte kunna räkna med den."""
    with pytest.raises(BeloppsfelError, match="finns inte i Sverige"):
        moms_fran_brutto("1200", "0.20")


def test_moms_fran_netto_avrundar_halva_bort_fran_noll():
    assert moms_fran_netto("0.10", "0.25") == Decimal("0.03")
    assert moms_fran_netto("-0.10", "0.25") == Decimal("-0.03")


# -- Period ----------------------------------------------------------------


def _mars() -> list[Post]:
    """En månad med två fakturor, två kostnader och en kreditfaktura.

    Handräknat facit:
      intäkter   10 000 + 5 000 − 1 000 = 14 000
      utg. moms   2 500 + 1 250 −   250 =  3 500
      kostnader   2 000 +   800         =  2 800
      ing. moms     500 +    96         =    596
      resultat   14 000 − 2 800         = 11 200
      moms att betala 3 500 − 596       =  2 904
    """
    return [
        Post(date(2026, 3, 3), "intakt", Decimal("10000"), Decimal("2500"), "Kund A"),
        Post(date(2026, 3, 14), "intakt", Decimal("5000"), Decimal("1250"), "Kund B"),
        # Kreditfaktura: negativa belopp, SAMMA riktning som fakturan den krediterar.
        Post(date(2026, 3, 20), "intakt", Decimal("-1000"), Decimal("-250"), "Kund A"),
        Post(date(2026, 3, 5), "kostnad", Decimal("2000"), Decimal("500"), "Leverantor AB"),
        # 12 % — lunch/livsmedel. Med bara 25 % i sviten hade en sats-bugg
        # kunnat gömma sig bakom att alla poster råkade ha samma sats.
        Post(date(2026, 3, 18), "kostnad", Decimal("800"), Decimal("96"), "Fiket"),
    ]


def test_periodsummor_mot_handraknat_facit():
    s = summera_period(_mars())
    assert s.intakter == Decimal("14000.00")
    assert s.kostnader == Decimal("2800.00")
    assert s.utgaende_moms == Decimal("3500.00")
    assert s.ingaende_moms == Decimal("596.00")
    assert s.resultat_fore_skatt == Decimal("11200.00")
    assert s.moms_att_betala == Decimal("2904.00")
    assert s.antal_poster == 5


def test_kreditfaktura_tar_bort_lika_mycket_som_fakturan_lade_till():
    """Faktura + kreditfaktura på samma belopp ska ge en nollperiod."""
    poster = [
        Post(date(2026, 3, 3), "intakt", Decimal("10000"), Decimal("2500")),
        Post(date(2026, 3, 20), "intakt", Decimal("-10000"), Decimal("-2500")),
    ]
    s = summera_period(poster)
    assert s.intakter == Decimal("0.00")
    assert s.utgaende_moms == Decimal("0.00")
    assert s.resultat_fore_skatt == Decimal("0.00")


def test_tom_period_ar_nollor_inte_krasch():
    s = summera_period([])
    assert s.intakter == Decimal("0.00")
    assert s.resultat_fore_skatt == Decimal("0.00")
    assert s.antal_poster == 0


def test_avrundning_sker_en_gang_pa_slutet():
    """Tre poster om ett halvt öre.

    Summera först, avrunda sedan: 0,015 -> 0,02.
    Avrunda varje post och summera: 0,01 x 3 = 0,03.
    Skillnaden är hela skälet till att summeringen inte avrundar per post,
    och den växer med antalet rader.
    """
    poster = [
        Post(date(2026, 3, 1), "intakt", Decimal("0.005"), Decimal("0")) for _ in range(3)
    ]
    assert summera_period(poster).intakter == Decimal("0.02")


# -- Balans ----------------------------------------------------------------


def test_balanserat_verifikat_ger_noll():
    rader = [
        Konteringsrad("1930", debet=Decimal("1250.00")),
        Konteringsrad("3001", kredit=Decimal("1000.00")),
        Konteringsrad("2611", kredit=Decimal("250.00")),
    ]
    assert balans(rader) == Decimal("0.00")


def test_obalans_returnerar_differensen_inte_bara_falskt():
    """Den som fått en obalans behöver veta om det är ett öre eller ett fel."""
    rader = [
        Konteringsrad("1930", debet=Decimal("1250.00")),
        Konteringsrad("3001", kredit=Decimal("1000.00")),
        Konteringsrad("2611", kredit=Decimal("249.99")),
    ]
    assert balans(rader) == Decimal("0.01")


def test_kreditfaktura_balanserar_med_negativa_belopp():
    """Sidbyte hade också balanserat, men bryter kopplingen till originalet
    i rapporten. Negativa belopp på samma sida är det som gäller här."""
    rader = [
        Konteringsrad("1930", debet=Decimal("-1250.00")),
        Konteringsrad("3001", kredit=Decimal("-1000.00")),
        Konteringsrad("2611", kredit=Decimal("-250.00")),
    ]
    assert balans(rader) == Decimal("0.00")


def test_ogiltig_riktning_avvisas():
    with pytest.raises(BeloppsfelError, match="riktning"):
        Post(date(2026, 3, 1), "utgift", Decimal("100"), Decimal("25"))
