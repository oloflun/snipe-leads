"""Betalstatus: skillnaden mellan ett kvitto och en obetald faktura.

Felet de här testerna stänger, mätt 2026-09-09: avläsningen läste sex fält och
inget av dem sa om underlaget var betalt, så VARJE inköp krediterade 1930
Företagskonto. En leverantörsfaktura med 30 dagars betalningsvillkor bokfördes
som om pengarna redan lämnat kontot — bankutflödet syntes som skett, och
skulden på 2440 uppstod aldrig.

Varje test här ska falla om någon återinför en tyst default.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.bookkeeping.kontoplan import (
    OkantKontoError,
    betalkonto_for,
    bygg_forsaljningsverifikat,
    bygg_inkopsverifikat,
)
from app.bookkeeping.underlag import normalisera_falt
from app.bookkeeping.verifieringsgrind import check_underlag, check_verifikat

#: Den riktiga fakturan ur QA-körningen: Kontorab Sverige AB, 4 375 kr inkl.
#: 25 % moms, "Betalningsvillkor: 30 dagar". Den som bokfördes fel.
FAKTURA = {
    "id": "f-1",
    "datum": date(2026, 9, 3),
    "motpart": "Kontorab Sverige AB",
    "brutto": Decimal("4375.00"),
    "momssats": Decimal("0.25"),
    "riktning": "kostnad",
    "kategori": "kontorsmateriel",
    "betalstatus": "obetald",
}


def _konton(rader):
    """Konto -> (debet, kredit). Den tomma sidan är Decimal("0"), inte None —
    se Konteringsrad i math.py."""
    return {r.konto: (r.debet, r.kredit) for r in rader}


NOLL = Decimal("0")


# -- Kärnan: motkontot följer betalstatus ----------------------------------


def test_obetald_leverantorsfaktura_blir_en_skuld_inte_ett_bankuttag():
    """Felet som fanns: den här fakturan krediterade 1930."""
    rader = bygg_inkopsverifikat(
        brutto="4375.00",
        momssats="0.25",
        kategori="kontorsmateriel",
        betalstatus="obetald",
    )
    konton = _konton(rader)

    assert konton["2440"] == (NOLL, Decimal("4375.00")), "skulden ska stå på 2440"
    assert "1930" not in konton, "en obetald faktura får inte röra företagskontot"
    # Kostnaden och momsen finns ändå — det är bara MOTPOSTEN som skiljer.
    assert konton["6110"][0] == Decimal("3500.00")
    assert konton["2641"][0] == Decimal("875.00")


def test_betalt_kvitto_krediterar_fortfarande_foretagskontot():
    """Kvittot ur samma körning: Circle K, betalt med företagskort."""
    rader = bygg_inkopsverifikat(
        brutto="823.50", momssats="0.25", kategori="drivmedel", betalstatus="betald"
    )
    konton = _konton(rader)

    assert konton["1930"] == (NOLL, Decimal("823.50"))
    assert "2440" not in konton
    assert konton["5611"][0] == Decimal("658.80")
    assert konton["2641"][0] == Decimal("164.70")


def test_obetald_kundfaktura_blir_en_fordran():
    rader = bygg_forsaljningsverifikat(
        brutto="12500.00", momssats="0.25", betalstatus="obetald"
    )
    konton = _konton(rader)

    assert konton["1510"] == (Decimal("12500.00"), NOLL), "fordran ska stå på 1510"
    assert "1930" not in konton
    assert konton["3001"][1] == Decimal("10000.00")
    assert konton["2611"][1] == Decimal("2500.00")


def test_betald_forsaljning_gar_till_foretagskontot():
    konton = _konton(
        bygg_forsaljningsverifikat(brutto="1250.00", momssats="0.25", betalstatus="betald")
    )
    assert konton["1930"][0] == Decimal("1250.00")
    assert "1510" not in konton


@pytest.mark.parametrize("betalstatus", ["betald", "obetald"])
@pytest.mark.parametrize("sats", ["0.25", "0.12", "0.06", "0"])
def test_bagge_statusar_balanserar_pa_varje_momssats(betalstatus, sats):
    """Motkontot byts ut — balansen får inte följa med."""
    for rader in (
        bygg_inkopsverifikat(
            brutto="1250.00", momssats=sats, kategori="varuinkop", betalstatus=betalstatus
        ),
        bygg_forsaljningsverifikat(brutto="1250.00", momssats=sats, betalstatus=betalstatus),
    ):
        assert check_verifikat(rader).ok


# -- Ingen tyst default -----------------------------------------------------


def test_byggarna_kraver_betalstatus_explicit():
    """Ett default-argument här vore återfallet. Anropet ska inte gå att göra."""
    with pytest.raises(TypeError):
        bygg_inkopsverifikat(brutto="100.00", momssats="0.25", kategori="varuinkop")
    with pytest.raises(TypeError):
        bygg_forsaljningsverifikat(brutto="100.00", momssats="0.25")


def test_okand_betalstatus_kastar_i_stallet_for_att_bli_betald():
    with pytest.raises(OkantKontoError) as fel:
        betalkonto_for("kanske")
    assert "betald" in str(fel.value)

    with pytest.raises(OkantKontoError):
        bygg_inkopsverifikat(
            brutto="100.00", momssats="0.25", kategori="varuinkop", betalstatus=""
        )


# -- Grinden ----------------------------------------------------------------


def test_underlag_utan_betalstatus_gar_till_granskning():
    """Samma utgång som ett saknat momsfält, och av samma skäl: en gissning
    hamnar i bokföringen."""
    utan = {k: v for k, v in FAKTURA.items() if k != "betalstatus"}
    verdikt = check_underlag(utan)

    assert not verdikt.ok
    assert [b.vad for b in verdikt.brister] == ["betalstatus"]


def test_ogiltig_betalstatus_namnges_i_bristen():
    verdikt = check_underlag({**FAKTURA, "betalstatus": "delbetald"})
    assert not verdikt.ok
    assert any(b.vad == "betalstatus" for b in verdikt.brister)
    assert "varken" in "\n".join(verdikt.as_report())


def test_helt_underlag_med_betalstatus_slapps_igenom():
    assert check_underlag(FAKTURA).ok


# -- Avläsningens normalisering --------------------------------------------


@pytest.mark.parametrize(
    "ratt, forvantat",
    [
        ("betald", "betald"),
        ("Betald", "betald"),
        ("  OBETALD  ", "obetald"),
        ("obetald", "obetald"),
    ],
)
def test_normalisering_tar_versaler_och_blanksteg(ratt, forvantat):
    assert normalisera_falt({"betalstatus": ratt})["betalstatus"] == forvantat


@pytest.mark.parametrize(
    "skrap",
    ["", "   ", "kanske", "delbetald", "paid", "ja", None, 1, True],
)
def test_allt_annat_utelamnas_och_fangas_av_grinden(skrap):
    """Utelämnat fält är rätt utgång — INTE tolkat som 'betald'."""
    assert "betalstatus" not in normalisera_falt({"betalstatus": skrap})


# -- Lagringen --------------------------------------------------------------


@pytest.mark.anyio
async def test_betalstatus_overlever_lagringen():
    """Fältet ska nå raden, inte tappas mellan avläsning och databas."""
    from app.storage.memory import MemoryStorage

    storage = MemoryStorage()
    rad = await storage.create_bk_underlag(
        "t-1",
        sha256="a" * 64,
        filnamn="faktura.pdf",
        mimetyp="application/pdf",
        status="klar",
        datum=date(2026, 9, 3),
        motpart="Kontorab Sverige AB",
        brutto=Decimal("4375.00"),
        momssats=Decimal("0.25"),
        riktning="kostnad",
        kategori="kontorsmateriel",
        betalstatus="obetald",
    )
    assert rad["betalstatus"] == "obetald"
    assert (await storage.get_bk_underlag("t-1", rad["id"]))["betalstatus"] == "obetald"

    # Människans rättelse när fakturan sedan betalas.
    uppdaterad = await storage.update_bk_underlag("t-1", rad["id"], betalstatus="betald")
    assert uppdaterad["betalstatus"] == "betald"


@pytest.mark.anyio
async def test_lagringen_avvisar_samma_varden_som_databasen():
    """Minnet får aldrig ta emot mer än check-villkoret i migration 062 —
    annars är sviten grön medan Postgres fäller vid första riktiga skrivning.
    Samma mekanism som AGENT_RUN_TYPES."""
    from app.storage.base import BkValideringsfel
    from app.storage.memory import MemoryStorage

    storage = MemoryStorage()
    with pytest.raises(BkValideringsfel):
        await storage.create_bk_underlag(
            "t-1",
            sha256="b" * 64,
            filnamn="x.pdf",
            mimetyp="application/pdf",
            status="klar",
            betalstatus="delbetald",
        )
