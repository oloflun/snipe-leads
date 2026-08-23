"""SIE4-exporten — formatet är hela poängen, så testerna läser bytes.

Exempelbolaget följer regeln för leads exempelbolag: organisationsnumret har
medvetet fel kontrollsiffra (556677-8890; korrekt vore 9).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.bookkeeping.kontoplan import bygg_forsaljningsverifikat, bygg_inkopsverifikat
from app.bookkeeping.math import Konteringsrad
from app.bookkeeping.sie4 import SieExportError, Verifikat, skriv_sie4

FORETAG = {
    "foretagsnamn": "Eknäs Bygg Gruppen AB",
    "orgnr": "556677-8890",
    "rakenskapsar_start": date(2026, 1, 1),
    "rakenskapsar_slut": date(2026, 12, 31),
    "genererat": date(2026, 4, 1),
}


def _mars_verifikat() -> list[Verifikat]:
    return [
        Verifikat(
            serie="A",
            nummer="1",
            datum=date(2026, 3, 3),
            text="Faktura kund",
            rader=tuple(bygg_forsaljningsverifikat(brutto="1250.00", momssats="0.25")),
        ),
        Verifikat(
            serie="A",
            nummer="2",
            datum=date(2026, 3, 5),
            text="Inköp material",
            rader=tuple(
                bygg_inkopsverifikat(brutto="1250.00", momssats="0.25", kategori="varuinkop")
            ),
        ),
    ]


def _text(data: bytes) -> str:
    return data.decode("cp437")


def test_filen_ar_cp437_inte_utf8():
    """Hela skälet till att funktionen returnerar bytes.

    Bolagsnamnet innehåller ä. I UTF-8 är det två bytes; i CP437 en (0x84).
    En fil som deklarerar #FORMAT PC8 men bär UTF-8 ger å/ä/ö som skräp i
    mottagarsystemet — ett fel kunden upptäcker, inte vi.
    """
    data = skriv_sie4(**FORETAG, verifikat=_mars_verifikat())
    assert b"\x84" in data  # ä i CP437
    assert "Eknäs".encode("utf-8") not in data
    assert _text(data).count("Eknäs") == 1


def test_huvudet_har_de_obligatoriska_posterna():
    text = _text(skriv_sie4(**FORETAG, verifikat=_mars_verifikat()))
    for post in ("#FLAGGA 0", "#FORMAT PC8", "#SIETYP 4", "#GEN 20260401"):
        assert post in text
    assert '#FNAMN "Eknäs Bygg Gruppen AB"' in text
    assert "#ORGNR 556677-8890" in text
    assert "#RAR 0 20260101 20261231" in text


def test_trans_har_ett_signerat_belopp_inte_tva_kolumner():
    """Formatdetaljen som är lättast att få fel: debet positivt, kredit
    negativt, ett belopp per rad."""
    text = _text(skriv_sie4(**FORETAG, verifikat=_mars_verifikat()))
    assert "#TRANS 1930 {} 1250.00" in text  # debet
    assert "#TRANS 3001 {} -1000.00" in text  # kredit
    assert "#TRANS 2611 {} -250.00" in text  # kredit


def test_varje_verifikats_trans_summerar_till_noll():
    """Samma villkor som balans(), men läst ur den FÄRDIGA filen — det är den
    mottagarsystemet importerar, inte våra dataklasser."""
    text = _text(skriv_sie4(**FORETAG, verifikat=_mars_verifikat()))
    summa = Decimal(0)
    antal = 0
    for rad in text.splitlines():
        if rad.strip().startswith("#TRANS"):
            summa += Decimal(rad.split()[-1])
            antal += 1
    assert antal == 6
    assert summa == Decimal(0)


def test_bara_anvanda_konton_deklareras():
    text = _text(skriv_sie4(**FORETAG, verifikat=_mars_verifikat()))
    assert '#KONTO 4010 "Inköp av material och varor"' in text
    assert "#KTYP 4010 K" in text
    # 5010 Lokalhyra används inte i perioden och ska inte stå i filen.
    assert "#KONTO 5010" not in text


def test_obalanserat_verifikat_exporteras_inte():
    """Mottagarsystemet hade avvisat filen ändå — men då på kundens skärm,
    i deras program, och det är för sent."""
    trasigt = [
        Verifikat(
            serie="A",
            nummer="1",
            datum=date(2026, 3, 3),
            text="Fel",
            rader=(
                Konteringsrad("1930", debet=Decimal("1250.00")),
                Konteringsrad("3001", kredit=Decimal("1000.00")),
            ),
        )
    ]
    with pytest.raises(SieExportError, match="balanserar inte"):
        skriv_sie4(**FORETAG, verifikat=trasigt)


def test_verifikat_utan_rader_exporteras_inte():
    tomt = [Verifikat(serie="A", nummer="1", datum=date(2026, 3, 3), text="Tomt")]
    with pytest.raises(SieExportError, match="inga rader"):
        skriv_sie4(**FORETAG, verifikat=tomt)


def test_citattecken_i_text_escapas():
    """Ett okapslat citattecken bryter fältindelningen för resten av raden."""
    ver = [
        Verifikat(
            serie="A",
            nummer="1",
            datum=date(2026, 3, 3),
            text='Faktura "brådskande"',
            rader=tuple(bygg_forsaljningsverifikat(brutto="125.00", momssats="0.25")),
        )
    ]
    text = _text(skriv_sie4(**FORETAG, verifikat=ver))
    assert r'"Faktura \"brådskande\""' in text


def test_tecken_utanfor_cp437_stoppar_inte_exporten():
    """Ett tecken CP437 saknar ska inte stoppa ett bokslut.
    Frågetecknet är synligt och ofarligt — se ponytail-noten i _sanera.

    Eurotecknet, inte ett grekiskt: CP437 HAR grekiska versaler (Ω ligger på
    0xEA), vilket det här testet upptäckte genom att fälla på sitt eget
    antagande. Valutatecknet är dessutom det realistiska fallet — det står på
    kvitton.
    """
    ver = [
        Verifikat(
            serie="A",
            nummer="1",
            datum=date(2026, 3, 3),
            text="Inköp för 45 €",
            rader=tuple(
                bygg_inkopsverifikat(brutto="125.00", momssats="0.25", kategori="varuinkop")
            ),
        )
    ]
    text = _text(skriv_sie4(**FORETAG, verifikat=ver))
    assert "Inköp för 45 ?" in text


def test_typografiskt_streck_blir_bindestreck_inte_fragetecken():
    """Klipp och klistra ur ett kvitto ger tankstreck. CP437 saknar det, men
    ett bindestreck är rätt översättning — inte ett frågetecken."""
    ver = [
        Verifikat(
            serie="A",
            nummer="1",
            datum=date(2026, 3, 3),
            text="Mars–april",
            rader=tuple(bygg_forsaljningsverifikat(brutto="125.00", momssats="0.25")),
        )
    ]
    assert "Mars-april" in _text(skriv_sie4(**FORETAG, verifikat=ver))


def test_raderna_avslutas_med_crlf():
    data = skriv_sie4(**FORETAG, verifikat=_mars_verifikat())
    assert data.endswith(b"\r\n")
    assert b"\n" in data
    assert data.count(b"\r\n") == data.count(b"\n")
