"""Gissningsgrinden — testad mot exakt de meningar EFTER-körningen
2026-08-26 släppte igenom, plus de klasser som INTE får fällas."""

from app.leads.gissnings_gate import GISSNINGSORD, check_gissningar


def test_faller_de_skarpa_exemplen_fran_efterkorningen():
    """Meningarna som passerade overlay-regeln i leads-20260826-205618."""
    traffar = check_gissningar(
        "Med en internationell kundbas i flera länder och valutor lär ni få "
        "många frågor om leverans, retur och storlekar."
    )
    assert len(traffar) == 1

    traffar = check_gissningar(
        "Med den volymen är det vanligt att er kundtjänst får återkommande "
        "frågor om leverans. Vi hörs!"
    )
    # "vanligt" är inte gissningsord (medvetet: adjektivet fäller för brett) —
    # men "vanligtvis" är det. Dokumentera gränsen:
    assert traffar == ()
    traffar = check_gissningar("Vanligtvis får ni många returfrågor under rean.")
    assert len(traffar) == 1


def test_faller_alla_forbudsorden_i_mottagarmening():
    for ord_ in GISSNINGSORD:
        text = f"Såhär i säsong {ord_} ni märka av fler frågor."
        assert check_gissningar(text), f"{ord_!r} fälldes inte"


def test_avsandarens_egna_vanor_ar_inte_gissningar():
    """'Vi brukar…' handlar om oss — även när mottagaren nämns senare."""
    assert check_gissningar("Vi brukar visa er kunskapsbas i en kort demo.") == ()
    assert check_gissningar("Jag lär mig gärna mer om er verksamhet.") == ()


def test_branschpastaende_utan_mottagare_faller_inte():
    assert (
        check_gissningar("Sådana frågor brukar vara vanliga i e-handeln.") == ()
    )


def test_mottagarord_inuti_andra_ord_faller_inte():
    """'internationell' innehåller 'er' — ordgränsen ska hålla."""
    assert check_gissningar("En internationell kundbas ställer säkra krav.") == ()


def test_ren_text_ger_tomt():
    assert check_gissningar("") == ()
    assert (
        check_gissningar(
            "Ni erbjuder fri retur. Er sajt listar leveranstider per land."
        )
        == ()
    )


def test_flera_traffar_returneras_som_meningar():
    text = (
        "Ni lär ha högt tryck i november. "
        "Er kundtjänst brukar nog svara långsamt då. "
        "Vi visar gärna en demo."
    )
    traffar = check_gissningar(text)
    assert len(traffar) == 2
    assert all("demo" not in t for t in traffar)
