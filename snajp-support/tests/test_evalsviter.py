"""Evalsviterna håller sin form, och bedömningsmallen räknar rätt.

Sviterna (evals/) körs mot en driftsatt miljö med riktig modell och hör inte
hemma i CI. Det som går att låsa här är att de finns, att de är minst trettio
fall per agent, att varje fall går att bedöma, och att mallen ger rätt utslag
på svar vi vet facit för. En svit som tyst krympt eller en mall som godkänner
allt upptäcks annars först när någon litar på siffran.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from evals import bedomning

EVALS = Path(__file__).resolve().parents[1] / "evals"


def _fall(fil: str) -> list[dict]:
    return json.loads((EVALS / fil).read_text(encoding="utf-8"))["fall"]


# -- Sviternas form --------------------------------------------------------------


@pytest.mark.parametrize("fil", ["support_livrustning.json", "iris_utkast.json", "kvitto.json"])
def test_varje_svit_har_minst_trettio_fall_med_unika_id(fil):
    fall = _fall(fil)
    assert len(fall) >= bedomning.MINSTA_ANTAL_FALL
    ider = [f["id"] for f in fall]
    assert len(set(ider)) == len(ider)
    assert all(f.get("typ") and f.get("kommentar") for f in fall), "varje fall säger vad det prövar och varför"


def _kompilerar(monster: list[str]) -> None:
    for m in monster:
        re.compile(m, re.I)


def test_supportfallen_gar_att_bedoma():
    for f in _fall("support_livrustning.json"):
        assert f["fraga"].strip() and f["utfall"] in ("svar", "overlamning", "valfritt"), f["id"]
        _kompilerar([m for grupp in f.get("ska_innehalla", []) for m in grupp] + f.get("far_inte_innehalla", []))
        if f["utfall"] == "overlamning":
            assert not f.get("ska_innehalla"), f"{f['id']}: ett överlämnat ärende har inga faktakrav"


def test_supportsviten_tacker_overlamning_injektion_och_regression():
    typer = {f["typ"] for f in _fall("support_livrustning.json")}
    assert {"fakta", "overlamning", "regression", "injektion"} <= typer


def test_supportfallens_fakta_finns_i_kunskapsbasen():
    """Sviten prövar agenten mot kundens kunskapsbas. Ett faktakrav som inte
    går att hitta där prövar något annat."""
    kb = " ".join(a["content"] + " " + a["title"] for a in json.loads((EVALS / "kb" / "livrustning.json").read_text(encoding="utf-8")))
    saknas = [
        (f["id"], grupp)
        for f in _fall("support_livrustning.json")
        if f["typ"] == "fakta"
        for grupp in f.get("ska_innehalla", [])
        if not any(re.search(m, kb, re.I | re.S) for m in grupp)
    ]
    assert not saknas, saknas


def test_irisfallen_gar_att_bedoma():
    rubrik = json.loads((EVALS / "iris_rubrik.json").read_text(encoding="utf-8"))
    _kompilerar([p["monster"] for p in rubrik.get("forbjudna_fraser", []) + rubrik.get("forbjudna_tecken", [])])
    assert rubrik.get("max_ord"), "rubriken ska bära skrivreglernas ordtak"
    for f in _fall("iris_utkast.json"):
        assert f["prospect_email"].endswith(".example"), f"{f['id']}: bara påhittade mottagare"
        assert len(f["offer_summary"]) <= 2000 and len(f["brief"]) <= 2000 and len(f["research_summary"]) <= 8000
        assert 1 <= len(f["research_evidence"]) <= 60 and f["struktur"] in ("a", "b")
        _kompilerar([m for grupp in f.get("ska_innehalla", []) for m in grupp] + f.get("far_inte_innehalla", []))


def test_kvittofallen_gar_att_bedoma_och_blir_lasbara_pdf():
    from app.bookkeeping.underlag import las_pdf_text

    filnamn = set()
    for f in _fall("kvitto.json"):
        assert f["forvantat"]["status"] in ("klar", "granska"), f["id"]
        assert f["filnamn"] not in filnamn
        filnamn.add(f["filnamn"])
        f["text"].encode("latin-1")
        if f["forvantat"].get("motpart"):
            re.compile(f["forvantat"]["motpart"], re.I)
    forsta = _fall("kvitto.json")[0]
    last = las_pdf_text(bedomning.enkel_pdf(forsta["text"], titel="prov"))
    for rad in [r.strip() for r in forsta["text"].split("\n") if r.strip()][:5]:
        assert rad.split()[0] in last


# -- Mallen: support -------------------------------------------------------------

FALL_FAKTA = {
    "utfall": "svar",
    "ska_innehalla": [["45 dagar"], ["originalförpackning"]],
    "far_inte_innehalla": ["14 dagar"],
}


def test_support_ratt_svar_godkanns():
    svar = {"reply": "Hej! Du har öppet köp i 45 dagar. Varan ska vara oskadad och i originalförpackning.", "escalated": False}
    assert bedomning.bedom_support(FALL_FAKTA, svar) == {"utfall": True, "fakta": True, "inga_fel": True, "format": True}


def test_support_saknat_faktum_och_pahittat_faktum_underkanns_var_for_sig():
    saknas = bedomning.bedom_support(FALL_FAKTA, {"reply": "Du har öppet köp i 45 dagar hos oss.", "escalated": False})
    pahitt = bedomning.bedom_support(
        FALL_FAKTA, {"reply": "Öppet köp i 45 dagar, i originalförpackning. Lagen ger 14 dagar.", "escalated": False}
    )
    assert saknas["fakta"] is False and saknas["inga_fel"] is True
    assert pahitt["fakta"] is True and pahitt["inga_fel"] is False


def test_support_overlamning_nar_den_inte_ska_ske_underkanns():
    svar = {"reply": "Jag kopplar in en kollega som återkommer.", "escalated": True}
    assert bedomning.bedom_support(FALL_FAKTA, svar)["utfall"] is False
    assert bedomning.bedom_support({"utfall": "overlamning"}, svar) == {
        "utfall": True, "fakta": True, "inga_fel": True, "format": True,
    }
    assert bedomning.bedom_support({"utfall": "valfritt"}, svar)["utfall"] is True


@pytest.mark.parametrize(
    "text",
    ["**Öppet köp** gäller i 45 dagar.", "Hej 😊 du har 45 dagar på dig.", "", "You have 45 days. Original packaging required."],
)
def test_support_formatfel_underkanns(text):
    assert bedomning.bedom_support({"utfall": "svar"}, {"reply": text, "escalated": False})["format"] is False


# -- Mallen: Iris ----------------------------------------------------------------

RUBRIK = {
    "max_ord": 60, "max_ord_b": 30, "min_ord": 10, "amnesrad_max_tecken": 40,
    "forbjudna_fraser": [{"monster": "hoppas allt är bra", "kalla": "prov"}],
    "forbjudna_tecken": [{"monster": "!", "kalla": "prov"}],
    "halsning": {"kraver_halsningsrad": True, "monster": r"^Hej\b", "kalla": "prov"},
    "fragor_max": 1,
}
IRISFALL = {
    "struktur": "a", "offer_summary": "En supportagent för en fast månadsavgift.", "brief": "Byggbolag i Umeå.",
    "research_summary": "Bolaget öppnade ett kontor i Holmsund i oktober 2026 och har 14 anställda.",
    "research_evidence": ["Nytt kontor i Holmsund sedan oktober 2026."],
    "ska_innehalla": [["Holmsund"]], "far_inte_innehalla": ["procent"],
}
BRA_MEJL = (
    "Hej Anna,\n\nJag såg att ni öppnat kontor i Holmsund. När fler kunder hör av sig på flera orter "
    "brukar inkorgen växa fortare än teamet.\n\nÄr det något ni känner igen?\n\nVänliga hälsningar\nIris\n556000-0000"
)


def test_iris_bra_mejl_godkanns_och_signaturens_tal_raknas_inte():
    svar = {"subject": "Nya kontoret i Holmsund", "body": BRA_MEJL, "queued": True}
    assert bedomning.bedom_iris(IRISFALL, svar, RUBRIK) == {
        "levererat": True, "ingang": True, "inga_pahitt": True, "skrivregler": True,
    }


def test_iris_pahittat_tal_underkanns():
    mejl = BRA_MEJL.replace("brukar inkorgen", "brukar 37 av 100 mejl")
    assert bedomning.bedom_iris(IRISFALL, {"subject": "Holmsund", "body": mejl, "queued": True}, RUBRIK)["inga_pahitt"] is False


def test_iris_tal_ur_underlaget_godkanns():
    mejl = BRA_MEJL.replace("öppnat kontor i Holmsund", "öppnat kontor i Holmsund i oktober 2026 och är 14 anställda")
    assert bedomning.bedom_iris(IRISFALL, {"subject": "Holmsund", "body": mejl, "queued": True}, RUBRIK)["inga_pahitt"] is True


@pytest.mark.parametrize(
    "andring",
    [
        lambda m: m.replace("Hej Anna,", "Hoppas allt är bra, Anna."),
        lambda m: m.replace("igen?", "igen? Eller inte? Vad tror du?"),
        lambda m: m.replace("fortare än teamet.", "fortare än teamet!"),
        lambda m: m.replace("fortare än teamet.", "fortare än teamet. " + "Och så vidare " * 30),
    ],
)
def test_iris_brott_mot_skrivreglerna_underkanns(andring):
    svar = {"subject": "Holmsund", "body": andring(BRA_MEJL), "queued": True}
    assert bedomning.bedom_iris(IRISFALL, svar, RUBRIK)["skrivregler"] is False


def test_iris_utan_utkast_i_kon_ar_inte_levererat():
    assert bedomning.bedom_iris(IRISFALL, {"subject": "x", "body": BRA_MEJL, "queued": False}, RUBRIK)["levererat"] is False
    assert bedomning.bedom_iris(IRISFALL, {}, RUBRIK)["levererat"] is False


# -- Mallen: kvitto --------------------------------------------------------------

KVITTOFALL = {"forvantat": {"status": "klar", "brutto": "1250.00", "momssats": "25", "datum": "2026-03-05",
                            "motpart": "eknäs bygg", "kategori": "varuinkop"}}


def test_kvitto_ratt_avlasning_godkanns_oavsett_talformat():
    svar = {"status": "klar", "underlag": {"brutto": "1250", "momssats": "25.00", "datum": "2026-03-05",
                                           "motpart": "Eknäs Bygg Gruppen AB", "kategori": "varuinkop"}}
    assert bedomning.bedom_kvitto(KVITTOFALL, svar) == {"status": True, "belopp": True, "falt": True}


def test_kvitto_momssats_som_andel_ar_samma_som_procent():
    """Api:t svarar 0.25 och granska_manuellt; sviten skriver 25 och granska."""
    ratt = {"brutto": "1250.00", "momssats": "0.25", "datum": "2026-03-05", "motpart": "Eknäs Bygg", "kategori": "varuinkop"}
    assert bedomning.bedom_kvitto(KVITTOFALL, {"status": "klar", "underlag": ratt})["belopp"] is True
    assert bedomning.bedom_kvitto(KVITTOFALL, {"status": "klar", "underlag": {**ratt, "momssats": "0.12"}})["belopp"] is False
    nollmoms = {"forvantat": {"status": "granska", "momssats": "0"}}
    assert bedomning.bedom_kvitto(nollmoms, {"status": "granska_manuellt", "underlag": {"momssats": "0"}}) == {
        "status": True, "belopp": True, "falt": True,
    }


def test_kvitto_fel_belopp_fel_falt_och_fel_status_underkanns_var_for_sig():
    ratt = {"brutto": "1250.00", "momssats": "25", "datum": "2026-03-05", "motpart": "Eknäs Bygg", "kategori": "varuinkop"}
    assert bedomning.bedom_kvitto(KVITTOFALL, {"status": "klar", "underlag": {**ratt, "brutto": "1205.00"}})["belopp"] is False
    assert bedomning.bedom_kvitto(KVITTOFALL, {"status": "klar", "underlag": {**ratt, "datum": "2026-05-03"}})["falt"] is False
    assert bedomning.bedom_kvitto(KVITTOFALL, {"status": "granska", "underlag": ratt})["status"] is False


def test_kvitto_utan_sek_belopp_kraver_att_inget_belopp_satts():
    fall = {"forvantat": {"status": "granska", "brutto": None}}
    assert bedomning.bedom_kvitto(fall, {"status": "granska", "underlag": {"brutto": None}})["belopp"] is True
    assert bedomning.bedom_kvitto(fall, {"status": "granska", "underlag": {"brutto": "473.00"}})["belopp"] is False


def test_kvitto_avvisad_fil_raknas_som_granskning():
    assert bedomning.bedom_kvitto({"forvantat": {"status": "granska"}}, {"avvisad": True})["status"] is True
    assert bedomning.bedom_kvitto(KVITTOFALL, {"avvisad": True})["status"] is False


# -- Sammanfattningen ------------------------------------------------------------


def test_sammanfattningen_raknar_per_kriterium_och_typ():
    rader = [
        {"typ": "fakta", "kriterier": {"utfall": True, "fakta": True}},
        {"typ": "fakta", "kriterier": {"utfall": True, "fakta": False}},
        {"typ": "overlamning", "kriterier": {"utfall": False, "fakta": True}},
        {"typ": "overlamning", "kriterier": {"utfall": True, "fakta": True}},
    ]
    s = bedomning.sammanfatta(rader)
    assert (s["antal"], s["godkanda"], s["andel"]) == (4, 2, 0.5)
    assert s["per_kriterium"] == {"fakta": 0.75, "utfall": 0.75}
    assert s["per_typ"] == {"fakta": "1/2", "overlamning": "1/2"}
