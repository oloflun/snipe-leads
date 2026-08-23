"""INV-BOOK-002 — en periodrapport visas aldrig som klar när den inte går ihop.

Exempeldata följer samma regel som leads exempelbolag: organisationsnumret har
MEDVETET fel kontrollsiffra (556677-8890; korrekt siffra vore 9) och domänen
ligger under `.example`, som är reserverad i RFC 2606. Se
`app/leads/exempelbolag.py` för varför.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.bookkeeping.kontoplan import bygg_forsaljningsverifikat, bygg_inkopsverifikat
from app.bookkeeping.math import Konteringsrad
from app.bookkeeping.verifieringsgrind import (
    STATUS_GRANSKA,
    STATUS_KLAR,
    check_period,
    check_underlag,
    check_verifikat,
)

HELT_UNDERLAG = {
    "id": "kv-1",
    "datum": date(2026, 3, 5),
    "motpart": "Eknäs Bygg Gruppen AB",
    "brutto": Decimal("1250.00"),
    "momssats": Decimal("0.25"),
    "riktning": "kostnad",
    "kategori": "varuinkop",
}


# -- Underlag --------------------------------------------------------------


def test_helt_underlag_slapps_igenom():
    verdikt = check_underlag(HELT_UNDERLAG)
    assert verdikt.ok
    assert verdikt.status == STATUS_KLAR


def test_underlag_utan_momssats_eskalerar_i_stallet_for_att_gissa():
    """Det testfall briefen kräver.

    Momssatsen går ofta att gissa ur bruttot. Grinden gör det inte: en gissad
    sats ger ett gissat momsbelopp, och det beloppet hamnar i en
    momsdeklaration. Ingen sats i verdiktet, inget belopp — bara en brist.
    """
    trasigt = {k: v for k, v in HELT_UNDERLAG.items() if k != "momssats"}
    verdikt = check_underlag(trasigt)

    assert not verdikt.ok
    assert verdikt.status == STATUS_GRANSKA
    assert [b.vad for b in verdikt.brister] == ["momssats"]
    # Ingenting i rapporten får se ut som ett belopp.
    assert "0" not in verdikt.as_report()[0].split("—")[0]


def test_noll_procent_moms_ar_ett_svar_inte_en_saknad_uppgift():
    """0 är en giltig momssats. En grind som behandlar 0 som tomt skickar
    varje momsfri post till manuell granskning."""
    momsfritt = {**HELT_UNDERLAG, "momssats": Decimal("0")}
    assert check_underlag(momsfritt).ok


def test_nollbelopp_ar_ocksa_ett_svar():
    assert check_underlag({**HELT_UNDERLAG, "brutto": Decimal("0")}).ok


def test_tom_strang_raknas_som_saknad():
    assert not check_underlag({**HELT_UNDERLAG, "motpart": "   "}).ok


def test_alla_saknade_falt_rapporteras_pa_en_gang():
    """En brist i taget hade betytt fyra rundor granskning för samma kvitto."""
    verdikt = check_underlag({"id": "kv-tomt"})
    assert {b.vad for b in verdikt.brister} == {
        "datum",
        "motpart",
        "brutto",
        "momssats",
        "riktning",
    }


def test_kostnad_utan_kategori_kan_inte_konteras():
    utan = {k: v for k, v in HELT_UNDERLAG.items() if k != "kategori"}
    assert [b.vad for b in check_underlag(utan).brister] == ["kategori"]


def test_intakt_kraver_ingen_kategori():
    """Intäkten konteras på momssatsen, som redan är ett krävt fält."""
    intakt = {
        "id": "f-1",
        "datum": date(2026, 3, 3),
        "motpart": "Kund hos exempelbolag.example",
        "brutto": Decimal("1250.00"),
        "momssats": Decimal("0.25"),
        "riktning": "intakt",
    }
    assert check_underlag(intakt).ok


def test_ogiltig_riktning_namnges():
    verdikt = check_underlag({**HELT_UNDERLAG, "riktning": "utgift"})
    assert not verdikt.ok
    assert "varken" in verdikt.as_report()[0]


# -- Verifikat -------------------------------------------------------------


def test_byggda_verifikat_balanserar_av_konstruktion():
    """Poängen med att koden bygger raderna: modellen kan inte skriva en obalans."""
    for sats in ("0.25", "0.12", "0.06", "0"):
        for brutto in ("1250.00", "10.00", "99.99", "1.00"):
            assert check_verifikat(
                bygg_inkopsverifikat(brutto=brutto, momssats=sats, kategori="varuinkop")
            ).ok
            assert check_verifikat(
                bygg_forsaljningsverifikat(brutto=brutto, momssats=sats)
            ).ok


def test_obalans_namnger_differensen():
    """Ett öre är avrundning, tusen kronor är fel konto. Verdiktet ska skilja dem."""
    rader = [
        Konteringsrad("1930", debet=Decimal("1250.00")),
        Konteringsrad("3001", kredit=Decimal("1000.00")),
        Konteringsrad("2611", kredit=Decimal("249.99")),
    ]
    verdikt = check_verifikat(rader)
    assert not verdikt.ok
    assert "0.01" in verdikt.as_report()[0]


def test_tomt_verifikat_fals():
    assert not check_verifikat([]).ok


# -- Period ----------------------------------------------------------------


def test_hel_period_gar_igenom():
    underlag = [HELT_UNDERLAG]
    verifikat = [bygg_inkopsverifikat(brutto="1250.00", momssats="0.25", kategori="varuinkop")]
    verdikt = check_period(underlag=underlag, verifikat=verifikat)
    assert verdikt.ok
    assert verdikt.status == STATUS_KLAR


def test_ett_trasigt_underlag_falsar_hela_perioden():
    trasigt = {k: v for k, v in HELT_UNDERLAG.items() if k != "brutto"}
    verdikt = check_period(
        underlag=[HELT_UNDERLAG, trasigt],
        verifikat=[
            bygg_inkopsverifikat(brutto="1250.00", momssats="0.25", kategori="varuinkop"),
            bygg_inkopsverifikat(brutto="500.00", momssats="0.25", kategori="varuinkop"),
        ],
    )
    assert verdikt.status == STATUS_GRANSKA


def test_underlag_utan_kontering_falsar_i_stallet_for_att_forsvinna():
    """Den tysta varianten: posten faller ur rapporten och summan ser rimlig ut.

    Trovärdiga men felaktiga tal är värre än tomma — samma klass av fel som
    adminvyns nollställda siffror (STATUS.md 2026-08-16).
    """
    verdikt = check_period(underlag=[HELT_UNDERLAG, HELT_UNDERLAG], verifikat=[
        bygg_inkopsverifikat(brutto="1250.00", momssats="0.25", kategori="varuinkop")
    ])
    assert not verdikt.ok
    assert any(b.vad == "tackning" for b in verdikt.brister)


def test_tom_period_ar_klar():
    """Noll underlag och noll verifikat går ihop. En månad utan kvitton är
    inte ett fel."""
    assert check_period(underlag=[], verifikat=[]).ok
