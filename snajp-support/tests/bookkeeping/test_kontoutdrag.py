"""Kontoutdraget: läsningen och avstämningen.

Ett kontoutdrag är inte "ett filformat till" — se modulens docstring. Testerna
nedan prövar två saker: att filen går att läsa i de former svenska banker
faktiskt exporterar, och att matchningen hellre säger "vet inte" än gissar.

Facit är handräknat. Där ett fall är valt för att det är en KANT står skälet
utskrivet.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.bookkeeping.kontoutdrag import (
    DAGSFONSTER,
    Banktransaktion,
    KontoutdragsfelError,
    las_kontoutdrag,
    stam_av,
)

SVENSK = (
    "Bokföringsdatum;Text;Belopp\n"
    "2026-08-14;KORTKOP 240814 NORDVIK DRIVMEDEL;-1250,00\n"
    "2026-08-16;SWISH INBETALNING;2500,00\n"
)


def _underlag(id_: str, datum: str, brutto: str, motpart: str = "Motpart") -> dict:
    return {"id": id_, "datum": datum, "brutto": Decimal(brutto), "motpart": motpart}


# -- Läsningen -------------------------------------------------------------


def test_semikolon_och_decimalkomma_ar_normalfallet():
    """Svenska banker exporterar så, eftersom kommat är decimaltecken."""
    tx = las_kontoutdrag(SVENSK.encode("utf-8"))
    assert [t.datum for t in tx] == [date(2026, 8, 14), date(2026, 8, 16)]
    assert tx[0].belopp == Decimal("-1250.00")
    assert tx[1].belopp == Decimal("2500.00")


def test_komma_som_avgransare_lases_ocksa():
    """Engelskspråkig export från samma bank. Hårdkodat semikolon hade läst
    hela raden som EN kolumn — alltså noll transaktioner och en avstämning som
    påstår att allt stämmer."""
    engelsk = "Date,Description,Amount\n2026-08-14,CARD PURCHASE,-1250.00\n"
    tx = las_kontoutdrag(engelsk.encode("utf-8"))
    assert len(tx) == 1
    assert tx[0].belopp == Decimal("-1250.00")


def test_cp1252_ger_lasbara_aao():
    """Windows-1252 är vanligast i svenska bankexporter. En UTF-8-läsning av
    den filen ger å/ä/ö som skräp — läsbart nog att passera, fel nog att
    irritera."""
    fil = "Datum;Text;Belopp\n2026-08-14;KÖP HOS ÅKESSON & SÖNER;-100,00\n"
    tx = las_kontoutdrag(fil.encode("cp1252"))
    assert "ÅKESSON" in tx[0].text
    assert "SÖNER" in tx[0].text


def test_bom_i_rubriken_hindrar_inte_kolumnvalet():
    """Excel skriver UTF-8 med BOM. Utan hanteringen heter första kolumnen
    "﻿Datum" och hittas inte."""
    tx = las_kontoutdrag("﻿Datum;Text;Belopp\n2026-08-14;X;-5,00\n".encode("utf-8"))
    assert len(tx) == 1


def test_okand_rubrik_sager_vilka_rubriker_som_fanns():
    """Ett fel som bara säger 'gick inte att läsa' kostar en supportrunda."""
    with pytest.raises(KontoutdragsfelError) as fel:
        las_kontoutdrag("Kolumn A;Kolumn B\n1;2\n".encode("utf-8"))
    assert "Kolumn A" in str(fel.value)


def test_tom_fil_avvisas():
    with pytest.raises(KontoutdragsfelError, match="tom"):
        las_kontoutdrag(b"")


def test_fil_utan_lasbara_rader_sager_vad_som_troligen_ar_fel():
    with pytest.raises(KontoutdragsfelError, match="sammanställning"):
        las_kontoutdrag("Datum;Text;Belopp\n;;\n".encode("utf-8"))


# -- Avstämningen ----------------------------------------------------------


def test_belopp_matchas_pa_absolutvarde():
    """Kvittot bär bruttot positivt med en `riktning`; banken bär tecknet i
    beloppet. Jämförs de som de står blir varje kostnad en miss."""
    tx = [Banktransaktion(date(2026, 8, 14), "KORTKOP", Decimal("-1250.00"))]
    resultat = stam_av(tx, [_underlag("u1", "2026-08-14", "1250.00")])
    assert len(resultat.matchade) == 1
    assert not resultat.saknar_underlag
    assert not resultat.saknar_banktransaktion


def test_kortkop_bokfort_nagra_dagar_senare_matchar_anda():
    """Vanligaste orsaken till att en KORREKT avstämning ser felaktig ut."""
    tx = [Banktransaktion(date(2026, 8, 17), "KORTKOP", Decimal("-500.00"))]
    resultat = stam_av(tx, [_underlag("u1", "2026-08-14", "500.00")])
    assert len(resultat.matchade) == 1


def test_utanfor_fonstret_matchar_inte():
    """Gränsen ska vara en gräns. Utan den matchar ett kvitto i mars mot en
    bankrad i september bara för att beloppen råkar vara lika."""
    tx = [Banktransaktion(date(2026, 8, 14 + DAGSFONSTER + 1), "KORTKOP", Decimal("-500.00"))]
    resultat = stam_av(tx, [_underlag("u1", "2026-08-14", "500.00")])
    assert not resultat.matchade
    assert len(resultat.saknar_underlag) == 1
    assert len(resultat.saknar_banktransaktion) == 1


def test_varje_underlag_matchas_hogst_en_gang():
    """Två likadana kvitton på 250 kr och EN bankrad.

    Utan bokföringen matchar bankraden mot båda, och avstämningen påstår att
    allt stämmer när ett underlag i själva verket saknar täckning.
    """
    tx = [Banktransaktion(date(2026, 8, 14), "KORTKOP", Decimal("-250.00"))]
    underlag = [_underlag("u1", "2026-08-14", "250.00"), _underlag("u2", "2026-08-14", "250.00")]
    resultat = stam_av(tx, underlag)
    assert len(resultat.matchade) == 1
    assert len(resultat.saknar_banktransaktion) == 1


def test_tva_bankrader_mot_tva_lika_underlag_matchar_bada():
    tx = [
        Banktransaktion(date(2026, 8, 14), "A", Decimal("-250.00")),
        Banktransaktion(date(2026, 8, 14), "B", Decimal("-250.00")),
    ]
    underlag = [_underlag("u1", "2026-08-14", "250.00"), _underlag("u2", "2026-08-14", "250.00")]
    resultat = stam_av(tx, underlag)
    assert len(resultat.matchade) == 2
    assert not resultat.saknar_banktransaktion


def test_underlag_utan_belopp_deltar_inte():
    """Ett fällt underlag har inget brutto att matcha på. Att räkna det som
    'saknar banktransaktion' hade lagt en andra anmärkning på ett underlag som
    redan bär en."""
    resultat = stam_av([], [{"id": "u1", "datum": "2026-08-14", "brutto": None}])
    assert not resultat.saknar_banktransaktion


def test_rapporten_sager_nar_allt_stammer():
    resultat = stam_av([], [])
    assert "Allt stämmer" in resultat.as_report()[0]


def test_ingen_textmatchning_pa_motpart():
    """Avsiktligt trubbig: bankens 'KORTKOP 240814 CIRCLE K 12345' liknar inte
    kvittots 'Circle K Sverige AB' tillräckligt för att en fuzzy-matchning ska
    bli annat än gissningar. Beloppet avgör, texten redovisas bara."""
    tx = [Banktransaktion(date(2026, 8, 14), "HELT ANNAN TEXT", Decimal("-1250.00"))]
    resultat = stam_av(tx, [_underlag("u1", "2026-08-14", "1250.00", "Circle K Sverige AB")])
    assert len(resultat.matchade) == 1
    assert resultat.matchade[0]["motpart"] == "Circle K Sverige AB"
    assert resultat.matchade[0]["text"] == "HELT ANNAN TEXT"


# -- Gränsen mot underlagsvägen -------------------------------------------


def test_csv_slapps_inte_igenom_som_ett_underlag():
    """Ett kontoutdrag får ALDRIG gå genom avläsningen.

    Gjorde det det blev varje rad ett nonsensverifikat, och en fil med hundra
    rader producerade hundra av dem.
    """
    from app.bookkeeping.underlag import LASBARA_MIMETYPER

    assert "text/csv" not in LASBARA_MIMETYPER
    assert "application/vnd.ms-excel" not in LASBARA_MIMETYPER


def test_avstamningen_skriver_ingenting():
    """Källkoden, inte beteendet. En avstämning som börjar skriva är inte
    längre ofarlig att köra om."""
    from pathlib import Path

    kalla = (
        Path(__file__).resolve().parents[2] / "app" / "bookkeeping" / "kontoutdrag.py"
    ).read_text(encoding="utf-8")
    for skrivning in ("create_bk_", "update_bk_", "log_agent_run", "INSERT", "insert into"):
        assert skrivning not in kalla, f"kontoutdrag.py innehåller en skrivning: {skrivning}"
