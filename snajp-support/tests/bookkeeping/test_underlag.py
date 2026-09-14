"""Normaliseringen av modellens svar — den utelämnar hellre än gissar.

Regeln testerna vaktar: ett fält som inte går att tolka ska SAKNAS i
resultatet, inte bära ett rimligt värde. Ett gissat momsbelopp hamnar i en
momsdeklaration.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.bookkeeping.underlag import (
    LASBARA_MIMETYPER,
    MAX_BYTES,
    UnderlagsfelError,
    kontrollera_fil,
    normalisera_belopp,
    normalisera_datum,
    normalisera_falt,
    normalisera_momssats,
    sha256_av,
)


# -- Momssats --------------------------------------------------------------


@pytest.mark.parametrize(
    "ratt",
    [25, "25", "25 %", "25%", "0.25", "0,25", Decimal("0.25"), Decimal("0.250")],
)
def test_momssats_i_alla_former_ger_samma_decimal(ratt):
    """Modellen svarar olika beroende på hur kvittot var formulerat.

    Regeln som skiljer procent från andel: värde > 1 är procent. Entydig här
    eftersom 6/12/25 och 0.06/0.12/0.25 inte överlappar.
    """
    assert normalisera_momssats(ratt) == Decimal("0.25")


def test_alla_svenska_satser_kanns_igen():
    assert normalisera_momssats(12) == Decimal("0.12")
    assert normalisera_momssats(6) == Decimal("0.06")
    assert normalisera_momssats(0) == Decimal("0")


def test_utlandsk_sats_ger_none_inte_narmaste():
    """20 % finns inte i Sverige. Att avrunda till 25 hade gett ett fel som
    ser ut som ett belopp."""
    assert normalisera_momssats(20) is None
    assert normalisera_momssats("19%") is None


def test_oläsbar_sats_ger_none():
    assert normalisera_momssats("ungefär en fjärdedel") is None
    assert normalisera_momssats(None) is None
    assert normalisera_momssats("") is None


# -- Datum -----------------------------------------------------------------


@pytest.mark.parametrize(
    "ratt", ["2026-03-05", "20260305", "05/03/2026", "05.03.2026", date(2026, 3, 5)]
)
def test_datum_i_vanliga_format(ratt):
    assert normalisera_datum(ratt) == date(2026, 3, 5)


def test_datetime_blir_datum():
    assert normalisera_datum(datetime(2026, 3, 5, 14, 30)) == date(2026, 3, 5)


def test_olasbart_datum_ger_none_inte_idag():
    """Fallback till dagens datum hade lagt kvittot i fel period, och fel
    period är fel momsdeklaration."""
    assert normalisera_datum("i fredags") is None
    assert normalisera_datum("") is None
    assert normalisera_datum(None) is None


# -- Belopp ----------------------------------------------------------------


@pytest.mark.parametrize(
    "ratt", ["1250.00", "1250,00", "1 250,00", "1 250,00 kr", "1250 SEK", Decimal("1250")]
)
def test_belopp_med_valuta_och_avskiljare(ratt):
    assert normalisera_belopp(ratt) == Decimal("1250")


def test_olasbart_belopp_ger_none_inte_noll():
    """None och noll är olika saker för grinden: 0 kr är ett svar, tomt är
    ett underlag ingen har läst färdigt."""
    assert normalisera_belopp("ca 1200") is None
    assert normalisera_belopp("") is None


def test_noll_ar_ett_belopp():
    assert normalisera_belopp("0") == Decimal("0")


def test_json_float_bros_over_exakt_i_stallet_for_att_forsvinna():
    """Buggen som hade sänkt varje kvitto.

    Modellens svar går genom `json.loads`, och JSON-talet 1250.5 blir en
    Python-float innan vår kod ser det. `math.till_decimal` avvisar float, och
    normaliseringen fångade det undantaget — resultatet var att beloppet
    UTELÄMNADES och grinden eskalerade varje underlag där modellen svarat med
    ett tal i stället för en sträng.

    Bron går via `str()`, som ger den kortaste round-trippande strängen. Det
    är exakt i den mening som betyder något: talet modellen skrev bevaras.
    """
    assert normalisera_belopp(1250.5) == Decimal("1250.5")
    assert normalisera_belopp(0.1) == Decimal("0.1")
    assert normalisera_momssats(0.25) == Decimal("0.25")
    assert normalisera_momssats(25.0) == Decimal("0.25")


def test_math_modulen_avvisar_fortfarande_float():
    """Bron gäller BARA normaliseringen vid modellgränsen. Beräkningarna ska
    fortsätta kasta — det farliga med float är aritmetiken."""
    from app.bookkeeping.math import BeloppsfelError, till_decimal

    with pytest.raises(BeloppsfelError, match="float"):
        till_decimal(1250.5)


def test_bool_blir_inte_ett_belopp_via_bron():
    """bool är en int i Python och slinker igenom en slarvig float-gren."""
    assert normalisera_belopp(True) is None


# -- Hela fältuppsättningen ------------------------------------------------


def test_helt_svar_normaliseras():
    resultat = normalisera_falt(
        {
            "datum": "2026-03-05",
            "brutto": "1 250,00 kr",
            "momssats": "25 %",
            "motpart": "  Eknäs Bygg Gruppen AB  ",
            "riktning": "kostnad",
            "kategori": "varuinkop",
        }
    )
    assert resultat == {
        "datum": date(2026, 3, 5),
        "brutto": Decimal("1250"),
        "momssats": Decimal("0.25"),
        "motpart": "Eknäs Bygg Gruppen AB",
        "riktning": "kostnad",
        "kategori": "varuinkop",
    }


def test_otolkbart_falt_utelamnas_helt():
    """Nyckeln ska inte finnas — då namnger grinden den som saknad. Ett
    None-värde hade sett ut som ett svar för den som läser med .get()."""
    resultat = normalisera_falt(
        {"datum": "i fredags", "brutto": "1250", "momssats": "25", "motpart": "AB"}
    )
    assert "datum" not in resultat
    assert resultat["brutto"] == Decimal("1250")


def test_pahittad_riktning_utelamnas():
    assert "riktning" not in normalisera_falt({"riktning": "utgift"})


def test_okanda_extrafalt_ignoreras():
    """Modellen får svara med mer än vi läser utan att det blir ett fel."""
    resultat = normalisera_falt({"brutto": "100", "fakturanummer": "F-2026-1", "tips": "?"})
    assert resultat == {"brutto": Decimal("100")}


def test_tomt_svar_ger_tomt_resultat():
    assert normalisera_falt({}) == {}


# -- Filgrind --------------------------------------------------------------


def test_pdf_och_bild_slapps_igenom():
    for mimetyp in ("application/pdf", "image/jpeg", "image/png"):
        kontrollera_fil(b"x" * 100, mimetyp)


def test_okant_format_namnger_vad_som_gar_att_lasa():
    with pytest.raises(UnderlagsfelError) as fel:
        kontrollera_fil(b"x", "application/vnd.ms-excel")
    assert "application/pdf" in str(fel.value)


def test_tom_fil_avvisas():
    with pytest.raises(UnderlagsfelError, match="tom"):
        kontrollera_fil(b"", "application/pdf")


def test_for_stor_fil_avvisas():
    with pytest.raises(UnderlagsfelError, match="MB"):
        kontrollera_fil(b"x" * (MAX_BYTES + 1), "application/pdf")


def test_hashen_ar_stabil_och_skiljer_filer():
    """Hashen är det enda som blir kvar av originalet — se modulens docstring."""
    assert sha256_av(b"kvitto") == sha256_av(b"kvitto")
    assert sha256_av(b"kvitto") != sha256_av(b"kvittn")
    assert len(sha256_av(b"kvitto")) == 64


def test_lasbara_mimetyper_ar_en_sluten_lista():
    """Grinden är en allowlist. En ny typ ska LÄGGAS TILL, inte slinka in."""
    assert "application/pdf" in LASBARA_MIMETYPER
    assert "text/html" not in LASBARA_MIMETYPER
