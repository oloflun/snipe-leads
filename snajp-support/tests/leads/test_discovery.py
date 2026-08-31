"""Urvalet mot ICP:t — rena funktioner, ingen Gemini-nyckel."""

from app.leads.discovery import (
    _plocka_json,
    _rena_traffar,
    normalisera_webbplats,
    webbplats_ar_bolagets,
)


def test_webbplats_ar_bolagets_egen_sajt():
    assert webbplats_ar_bolagets("https://acme.se")
    assert webbplats_ar_bolagets("acme.se")
    assert not webbplats_ar_bolagets("https://allabolag.se/foretag/acme")
    assert not webbplats_ar_bolagets("https://hitta.se/acme")
    assert not webbplats_ar_bolagets("https://acme.example")
    assert not webbplats_ar_bolagets("")


def test_plocka_json_ur_staket_och_rent():
    assert _plocka_json('[{"company_name": "A", "website": "https://a.se"}]')[0]["company_name"] == "A"
    text = 'Här: ```json\n[{"company_name": "B", "website": "https://b.se"}]\n```'
    assert _plocka_json(text)[0]["company_name"] == "B"


def test_rena_traffar_kastar_aggregat_exempel_och_dubbletter():
    rader = [
        {"company_name": "Riktiga AB", "website": "https://riktiga.se"},
        {"company_name": "Riktiga AB", "website": "https://riktiga.se/om"},
        {"company_name": "Fejk AB", "website": "https://fejk.example"},
        {"company_name": "Register AB", "website": "https://allabolag.se/x"},
        {"company_name": "Utesluten AB", "website": "https://utesluten.se"},
    ]
    rena = _rena_traffar(rader, uteslut={"utesluten ab"}, tak=10)
    assert [r["company_name"] for r in rena] == ["Riktiga AB"]
    assert rena[0]["website"].startswith("https://riktiga.se")


def test_normalisera_webbplats_lagger_https():
    assert normalisera_webbplats("www.acme.se/") == "https://www.acme.se"
