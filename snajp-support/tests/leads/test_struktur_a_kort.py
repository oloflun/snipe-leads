"""Struktur A, kort (Antons förslag 1, 2026-11-06).

A låg på median 105 ord (96 av 105 över formens 90), 57 av 105 öppnade med
"Att … är en balansgång" och 47 ställde en fråga som mejlet själv besvarade.
Nu har A en mening per steg och högst 80 ord: ingången konstaterar något om
dem, produktmeningen tar vid med kundens utfall för den produkt researchen
valde, sedan piloten och inbjudan. Testerna låser formen och taket, att
anpassningen följer bolaget och produkten, och att ett rätt skrivet A-mejl
passerar hela grinden.
"""

import json
import sys
from pathlib import Path

import pytest

from app.agent.leads_research_v2 import _INGANGSFORMER, _INGANGSUPPGIFT, _stilfynd
from app.leads import erbjudanden, stilkontroll as stil, utkaststruktur
from app.storage.memory import MemoryStorage
from tests.leads.test_utkaststruktur_b import (  # noqa: F401 — fixturerna används via namnet
    IRIS,
    SUPPORT,
    TENANT,
    UTFALL_IRIS,
    _forbered,
    _skriv,
    anyio_backend,
    miljo,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import snajp_malgrupp as sm  # noqa: E402

UTFALL_SUPPORT = sm.KORT_UTFALL[sm.SUPPORT]

#: Förslag 1 som Anton valde, i Iris och Supportagentens tappning (påhittade bolag).
A_IRIS = (
    "Hej,\n\nNi lägger de flesta golven åt fastighetsbolag och bostadsrättsföreningar runt Göteborg. "
    "Vår agent Iris tar fram fler sådana kunder åt er varje vecka och skriver ett första mejl till varje, "
    "som ni godkänner innan det skickas.\n\nJust nu tar vi in 20 företag i en kostnadsfri pilot av Iris i "
    "tre månader. Den som stannar efteråt får upp till 50 % rabatt.\n\nTitta gärna på demon på "
    "snajp.se/demo, eller svara på mejlet om ni vill ha en genomgång."
)
A_SUPPORT = (
    "Hej Lena,\n\nDina kunder frågar ofta om skötsel och lagning av jeansen långt efter köpet. Vår "
    "Supportagent svarar på de frågorna direkt på din webbplats, dygnet runt och utifrån din egen "
    "information.\n\nJust nu tar vi in 20 företag i en kostnadsfri pilot av Supportagenten i tre månader. "
    "Den som stannar efteråt får upp till 50 % rabatt.\n\nTitta gärna på demon på snajp.se/demo, eller "
    "svara på mejlet om du vill ha en genomgång."
)


def _koder(text: str, tak: int | None = erbjudanden.ORDTAK["rak"]) -> set[str]:
    return {a.kod for a in stil.kontrollera(text, tak=tak).anmarkningar}


# -- formen ---------------------------------------------------------------------


def test_formen_ar_en_mening_per_steg_utan_balansgang_och_fraga():
    regler = erbjudanden.formregler("rak", IRIS)
    assert "konstaterande" in regler and "produktmeningen" in regler
    assert f"högst {erbjudanden.ORDTAK['rak']} ord" in regler
    assert "Ingen fråga" in regler
    # "balansgång" står bara som förbud, aldrig som anvisning.
    assert "Aldrig en utmaning, en balansgång" in regler
    assert erbjudanden.ORDTAK["rak"] < erbjudanden.ORDTAK["fraga"] <= stil.MAX_ORD_MEJL


def test_ingangsformerna_och_personaliseringen_ber_aldrig_om_balansgang_eller_fraga():
    for form in _INGANGSFORMER:
        assert "balansgång" not in form and "fråga till dem" not in form, form
    assert "som en balansgång" not in _INGANGSUPPGIFT
    assert "aldrig en utmaning, en balansgång" in _INGANGSUPPGIFT.casefold()
    # Steget skriver om första stycket: ingången OCH produktmeningen.
    assert "produktmeningen" in _INGANGSUPPGIFT or "meningen om produkten" in _INGANGSUPPGIFT


# -- anpassningen: produkten researchen valde och kundens utfall för den ----------


@pytest.mark.parametrize(
    ("produkt", "utfall", "moment"),
    [(IRIS, UTFALL_IRIS, "hitta nya kunder"), (SUPPORT, UTFALL_SUPPORT, "supportchattarna")],
)
def test_blocket_bar_utfallet_for_den_valda_produkten(produkt, utfall, moment):
    eget = erbjudanden.Erbjudande(nyckel="pilot_a", namn="Piloten", regler="", form="rak")
    block = erbjudanden.block("pilot_a", "Just nu tar vi in 20 företag.", eget, produkt, utfall)
    assert "### Utfallet produktmeningen bygger på\n" + utfall in block
    # Form B:s moment hör bara till form B.
    assert moment not in block


def test_utan_kort_utfall_bygger_produktmeningen_pa_nyttan():
    """En annan kund utan korta utfall: produktmeningen bygger på produktens nytta."""
    eget = erbjudanden.Erbjudande(nyckel="egen", namn="Eget", regler="", form="rak")
    assert "Produktens nytta i produktlistan." in erbjudanden.block("egen", "Fri offert.", eget, "Takläggning")


@pytest.mark.anyio
@pytest.mark.parametrize(("vald", "utfall"), [(IRIS, UTFALL_IRIS), (SUPPORT, UTFALL_SUPPORT)])
async def test_for_trad_ger_utfallet_for_produkten_researchen_valde(vald, utfall):
    storage = MemoryStorage()
    trad, _ = await _forbered(storage)
    await storage.set_agent_settings(
        TENANT,
        agent_type="leads",
        settings={
            "erbjudanden": {
                "aktiva": [{"nyckel": "pilot", "vikt": 1}],
                "villkor": {"pilot": {IRIS: "Pilot för Iris.", SUPPORT: "Pilot för Supportagenten."}},
                "kort_utfall": {IRIS: UTFALL_IRIS, SUPPORT: UTFALL_SUPPORT},
            }
        },
    )
    valt = await erbjudanden.for_trad(storage, TENANT, await storage.get_outreach_thread(TENANT, trad), vald)
    assert valt is not None and valt.utfall == utfall
    assert utfall in valt.block()


@pytest.mark.anyio
async def test_a_prompten_bar_utfallet_formen_och_mottagarens_research(miljo):
    from tests.agent.test_leads_v2_wiring import _FakeLLM

    storage = MemoryStorage()
    trad, _ = await _forbered(storage)
    llm = _FakeLLM()
    await _skriv(storage, trad, llm, "a")
    forsta = next(m for s, m in zip(llm.calls, llm.user_messages) if s == "sa:draft-outreach")
    assert "### Mejlets form (A, rakt på)" in forsta
    assert UTFALL_IRIS in forsta
    assert "bostadsrättsföreningar" in forsta and "## Ingångens form i det här mejlet\n" in forsta
    assert "balansgång:" not in forsta


# -- taket och grinden -------------------------------------------------------------


def test_a_taket_galler_forsta_mejlet_men_uppfoljningarnas_ar_oforandrat():
    tak = erbjudanden.ORDTAK["rak"]
    vid_taket = "Hej,\n\n" + " ".join(["ord"] * (tak - 1)) + " slut."
    over = "Hej,\n\n" + " ".join(["ord"] * tak) + " slut."
    assert "for_langt" not in _koder(vid_taket)
    assert "for_langt" in _koder(over)
    # Utan tak (uppföljningar, kampanjer): stilkontrollens allmänna tak.
    assert "for_langt" not in _koder(over, tak=None)


def test_balansgangen_falls_i_ingangen():
    text = (
        "Hej,\n\nAtt lägga golv och samtidigt hitta nya uppdrag är en balansgång. Vår agent Iris tar fram "
        "nya kunder åt er.\n\nTitta gärna på demon på snajp.se/demo."
    )
    assert "mallord_i_ingangen" in _koder(text)


@pytest.mark.parametrize(("text", "produkt"), [(A_IRIS, sm.IRIS), (A_SUPPORT, sm.SUPPORT)], ids=["iris", "support"])
def test_forslag_1_passerar_hela_grinden(text, produkt):
    villkor = sm._PILOTER[produkt]
    assert _koder(text) == set(), _koder(text)
    assert stil.erbjudande_fynd(text, villkor=villkor, produkt=produkt) == []
    assert not utkaststruktur.ar_b(stil._brodtext(text))


def test_agenten_namnd_i_forsta_stycket_ar_fore_lofte_aven_om_piloten_namner_den_igen():
    """Felet i grinden 2026-11-06: namnet söktes först efter första stycket, så
    pilotens "av Iris" efter "20" fällde ett mejl där Iris stod i produktmeningen."""
    villkor = sm._PILOTER[sm.IRIS]
    assert "agent_efter_loftet" not in {a.kod for a in stil.erbjudande_fynd(A_IRIS, villkor=villkor, produkt=sm.IRIS)}
    # Båthusets fel (2026-10-12) fälls fortfarande: löftet före agenten.
    fel = (
        "Hej,\n\nNi lägger golv åt fastighetsbolag runt Göteborg.\n\nJust nu tar vi in 20 företag i en "
        "kostnadsfri pilot i tre månader, och den som stannar får upp till 50 % rabatt. Vår agent Iris tar "
        "fram fler kunder åt er.\n\nTitta gärna på demon på snajp.se/demo."
    )
    assert "agent_efter_loftet" in {a.kod for a in stil.erbjudande_fynd(fel, villkor=villkor, produkt=sm.IRIS)}


def test_kedjans_grind_skriver_om_ett_for_langt_a_mejl():
    lang = {"subject": "Nya kunder", "body": A_IRIS.replace("Titta gärna", " ".join(["Därtill"] * 20) + ". Titta gärna")}
    def fynd(d):
        return _stilfynd(d, villkor=None, produkt=IRIS, andra=[], amne_i_kod=True, tak=erbjudanden.ORDTAK["rak"])
    assert any(f"ord (högst {erbjudanden.ORDTAK['rak']})" in f for f in fynd(lang))
    assert not any("ord (högst" in f for f in fynd({"subject": "Nya kunder", "body": A_IRIS}))


# -- Snajps inställningar -----------------------------------------------------------


def test_snajp_kor_bara_form_a_och_piloten_ryms_i_tva_korta_meningar():
    assert [a["nyckel"] for a in sm.ERBJUDANDEN["aktiva"]] == ["pilot_a"]
    # pilot_b står kvar, så att dess utfall syns och den kan slås på igen.
    assert sm.ERBJUDANDEN["egna"]["pilot_b"]["form"] == "fraga"
    villkor = sm._PILOTER[sm.IRIS]
    innehall = villkor.split("Handling:")[0]
    assert all(len(m.split()) <= 20 for m in innehall.split(". ") if m.strip())
    # Första meningen är den struktur B bär, med samma siffror som förut.
    forsta = utkaststruktur.kort_villkor(villkor)
    assert "20 företag" in forsta and "tre månader" in forsta and "50 %" not in forsta
    assert "Svara" not in villkor.split("Handling:")[1]
    assert json.dumps(sm.ERBJUDANDEN, ensure_ascii=False)  # serialiserbart till PUT /api/leads/erbjudanden
