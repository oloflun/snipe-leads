"""INV-LEADS-EXIST-001: ett bolag som inte går att styrka blir aldrig ett lead.

Kärnan av invarianten, som rena funktioner. Bredden (körningen, prospektet,
registret, sändspärren) står i tests/leads/test_existens.py,
tests/agent/test_leads_v2_utkastgrind.py och tests/leads/test_scheduler.py.
"""

from app.leads import bedomning, existens

_PAHITTAT = {"company_name": "Detaljhandel Design AB", "website": "https://detaljhandeldesign.se", "kalla": "gemini"}


def test_soktraff_utan_svarande_webbplats_faller():
    assert existens.styrk(_PAHITTAT, {"matt": True, "svarar_inte": True})


def test_soktraff_vars_sajt_inte_bar_namnet_faller():
    annan = {**_PAHITTAT, "website": "https://cykelhuset.se"}
    assert existens.styrk(annan, {"matt": True, "sidtext": "Cykelhuset i Borås säljer cyklar"})


def test_soktraff_utan_webbplats_faller():
    assert existens.styrk({"company_name": "Okänt AB", "kalla": "gemini"}, {"har_webbplats": False})


def test_utan_kallmaterial_ar_bolaget_aldrig_kvalificerat():
    profil = {"kommuner": ["Göteborg"], "anstallda_min": 1, "anstallda_max": 49}
    b = bedomning.bedom(
        profil, {"ort": "Göteborg", "antal_anstallda": 15, "qualified": True}, korpus="",
        kandidat={"ort": "Göteborg", "anstallda": 15}, har_underlag=False,
    )
    assert (b["niva"], b["qualified"], b["score_total"]) == ("C", False, 0)


def test_niva_a_kraver_ett_uppfyllt_kriterium():
    profil = {"kommuner": ["Göteborg"], "anstallda_min": 1, "anstallda_max": 49}
    b = bedomning.bedom(profil, {"ort": "Göteborg", "antal_anstallda": 15}, korpus="x")
    assert b["niva"] != "A"
