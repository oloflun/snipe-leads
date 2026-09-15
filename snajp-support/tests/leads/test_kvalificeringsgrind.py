"""Kodgrinden för storlek och bemanning - rena funktioner, inget LLM.

Fallen är de uppmätta ur QA-kundens körningar 2026-09-15 (Nordform:
IT-konsulter/redovisningsbyråer/arkitektkontor/reklambyråer, 10–49 anställda).
"""

from __future__ import annotations

from app.leads.icp import normalize_icp
from app.leads.kvalificeringsgrind import TAK_ICP_FIT, skarp_kvalificering

NORDFORM = normalize_icp(
    {
        "industries": ["IT-konsulter", "redovisningsbyråer", "arkitektkontor", "reklambyråer"],
        "geography": ["Stockholm", "Göteborg"],
        "company_size": {"min": 10, "max": 49},
    }
)


def _godkant(**extra):
    return {"qualified": True, "icp_fit": 0.7, "disqualifiers": [], **extra}


def test_bemanningsforetag_som_modellen_godkande_falls():
    """Andara Group: godkänd 0,70, fast utkastet kallade det bemanningsföretag."""
    ut = skarp_kvalificering(_godkant(ar_bemanningsforetag=True), NORDFORM, company_name="Andara Group AB")
    assert ut["qualified"] is False
    assert ut["icp_fit"] == TAK_ICP_FIT
    assert any("Bemannings" in d for d in ut["disqualifiers"])


def test_bemanningsbolag_kanns_igen_pa_namnet_utan_faltet():
    ut = skarp_kvalificering(_godkant(), NORDFORM, company_name="Kraftsam Rekrytering & Bemanning AB")
    assert ut["qualified"] is False


def test_bemanningsbolag_ar_kvar_nar_de_ar_malgruppen():
    icp = normalize_icp({"industries": ["Bemanningsföretag"], "company_size": {"min": 10, "max": 49}})
    ut = skarp_kvalificering(_godkant(ar_bemanningsforetag=True), icp, company_name="Andara Group AB")
    assert ut["qualified"] is True
    assert ut["icp_fit"] == 0.7


def test_kand_storlek_over_taket_falls_med_antalet():
    ut = skarp_kvalificering(_godkant(antal_anstallda=250), NORDFORM, company_name="Eccera Professionals AB")
    assert ut["qualified"] is False
    assert any("250" in d and "49" in d for d in ut["disqualifiers"])


def test_kand_storlek_under_golvet_falls():
    ut = skarp_kvalificering(_godkant(antal_anstallda=4), NORDFORM, company_name="Liten Byrå AB")
    assert ut["qualified"] is False
    assert any("minst 10" in d for d in ut["disqualifiers"])


def test_storlek_inom_intervallet_rors_inte():
    fynd = _godkant(antal_anstallda=20)
    assert skarp_kvalificering(fynd, NORDFORM, company_name="Seequaly AB") == fynd


def test_okand_storlek_faller_ingenting():
    """De flesta småbolag skriver aldrig ut antalet - okänt är inte fel."""
    for okant in (None, "många", True, -3):
        fynd = _godkant(antal_anstallda=okant)
        assert skarp_kvalificering(fynd, NORDFORM, company_name="Filed AB")["qualified"] is True


def test_grinden_godkanner_aldrig_och_hojer_aldrig_fit():
    fynd = {"qualified": False, "icp_fit": 0.1, "disqualifiers": ["Fel bransch"], "antal_anstallda": 20}
    ut = skarp_kvalificering(fynd, NORDFORM, company_name="Städ AB")
    assert ut["qualified"] is False
    assert ut["icp_fit"] == 0.1
    assert ut["disqualifiers"] == ["Fel bransch"]


def test_befintliga_skal_behalls_och_dubbleras_inte():
    fynd = _godkant(antal_anstallda=250, disqualifiers=["Har redan chattlösning"])
    en = skarp_kvalificering(fynd, NORDFORM, company_name="Stort AB")
    tva = skarp_kvalificering(en, NORDFORM, company_name="Stort AB")
    assert tva["disqualifiers"][0] == "Har redan chattlösning"
    assert len(tva["disqualifiers"]) == 2


def test_utan_storlek_i_malgruppen_fallar_antalet_inget():
    icp = normalize_icp({"industries": ["IT-konsulter"]})
    assert skarp_kvalificering(_godkant(antal_anstallda=5000), icp, company_name="Stort AB")["qualified"] is True


def test_originalet_muteras_inte():
    fynd = _godkant(antal_anstallda=250)
    skarp_kvalificering(fynd, NORDFORM, company_name="Stort AB")
    assert fynd == _godkant(antal_anstallda=250)
