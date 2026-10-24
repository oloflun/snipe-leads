"""Iris-mejlen öppnar med erbjudandet (Sebbe 2026-10-24, förslag till Anton).

Varje Iris-mejl börjar med produkten och erbjudandets ord, så de fynd formen
själv ger (samma konstruktion som körningens andra Iris-mejl) är undantagna.
Klyschor, mallord och tilltalsfel fälls som förut, och Supportagenten skrivs
som förut."""

from app.agent.leads_research_v2 import _stilfynd, erbjudande_forst

IRIS = "Iris, leadsagenten"
VILLKOR = "Fem kvalificerade leads i er region, med kontaktperson och ett färdigt första mejl till vart och ett."


def _mejl(kundtyp: str, ort: str, extra: str = "") -> dict:
    return {
        "subject": f"{kundtyp} i {ort}",
        "body": (
            f"Hej,\n\nVår agent Iris tar fram fem {kundtyp} i {ort} åt er, med kontaktperson och ett "
            f"färdigt första mejl till vart och ett.\n\nNi skriver att ni bygger åt {kundtyp}.{extra} Det är "
            "utan kostnad och binder er inte.\n\nSvara \"ja\" så skickar vi de fem inom två arbetsdagar."
        ),
    }


def test_bara_iris_oppnar_med_erbjudandet():
    assert erbjudande_forst(IRIS)
    assert not erbjudande_forst("Supportagenten")
    assert not erbjudande_forst(None)


def test_iris_formen_falls_inte_for_samma_konstruktion():
    andra = [_mejl("fastighetsbolag", "Umeå")["body"]]
    fynd = _stilfynd(_mejl("bostadsrättsföreningar", "Göteborg"), villkor=VILLKOR, produkt=IRIS, andra=andra,
                     bolag="Walters Bygg AB")
    assert fynd == []


def test_iris_formen_faller_fortfarande_klyschor():
    fynd = _stilfynd(_mejl("fastighetsbolag", "Umeå", " Det är en smidig start."), villkor=VILLKOR,
                     produkt=IRIS, andra=[], bolag="Walters Bygg AB")
    assert any("säljklyscha" in f for f in fynd)


def test_andra_produkter_far_samma_konstruktion_som_forut():
    andra = [_mejl("fastighetsbolag", "Umeå")["body"]]
    fynd = _stilfynd(_mejl("bostadsrättsföreningar", "Göteborg"), villkor=None, produkt="Supportagenten",
                     andra=andra, bolag="Walters Bygg AB")
    assert any("byggd som ett annat mejl" in f for f in fynd)
