"""Textkvalitetslagret (app/textkvalitet.py) — efterkontrollen av all
kundsynlig agenttext. Testfallen speglar uppdraget 2026-10-03: å/ä/ö,
långa och korta texter, blandspråk, egennamn, siffror och länkar samt
avsiktligt felstavad indata.
"""

import pytest

from app.textkvalitet import (
    FELSTAVNINGAR,
    SKYDDADE_NAMN,
    SPRAKREGLER,
    _verifiera_korrektur,
    kontrollera,
    putsa,
    sakra_utgaende_text,
)


# ---------------------------------------------------------------- putsa


def test_putsa_rattar_mellanslag_fore_skiljetecken():
    text, _ = putsa("Hej ,\n\nVi hjälpte  er gärna .")
    assert text == "Hej,\n\nVi hjälpte er gärna."


def test_putsa_rattar_kurerade_felstavningar_versalbevarat():
    text, anm = putsa("Intresant! Vi vill gärna sammarbeta — det vore intresant.")
    assert "Intressant!" in text
    assert "samarbeta" in text
    assert any(a.kod == "felstavning_rattad" for a in anm)


def test_putsa_ror_aldrig_lankar_adresser_orgnr():
    original = (
        "Läs mer på https://snajp.se/epost?medans=1 eller mejla "
        "epost@sammarbete.se. Orgnr 556677-8899."
    )
    text, _ = putsa(original)
    assert "https://snajp.se/epost?medans=1" in text
    assert "epost@sammarbete.se" in text
    assert "556677-8899" in text


def test_putsa_behaller_a_a_o_och_radbrytningar():
    original = "Hej Åsa!\n\nTack för ert svar om lönehantering på Fårö.\n\nVänliga hälsningar"
    text, _ = putsa(original)
    assert text == original


def test_putsa_ingen_felflagga_pa_ren_text():
    text, anm = putsa("Hej! Allt ser bra ut. Vänliga hälsningar, Iris")
    assert anm == []


# ---------------------------------------------------------- kontrollera


def test_kontrollera_flaggar_ersattningstecken():
    r = kontrollera("Vi såg att F�retaget expanderar.")
    assert r.kraver_granskning
    assert any(a.kod == "ersattningstecken" for a in r.allvarliga)


def test_kontrollera_flaggar_kvarlamnad_platshallare():
    r = kontrollera("Hej [förnamn], vi hjälpte [Similar Company] att växa.")
    assert r.kraver_granskning
    assert any(a.kod == "platshallare" for a in r.allvarliga)


def test_kontrollera_tillater_sifferreferens():
    r = kontrollera("Enligt villkoren [1] gäller fri retur i 30 dagar.")
    assert not any(a.kod == "platshallare" for a in r.anmarkningar)


def test_kontrollera_flaggar_engelska_inslag_i_svensk_text():
    r = kontrollera("Hej! We would love att hjälpa your team with detta.")
    assert any(a.kod == "engelska_inslag" for a in r.allvarliga)


def test_kontrollera_flaggar_inte_engelska_nar_spraket_ar_engelska():
    r = kontrollera("Hi! We would love to help your team with this.", sprak="en")
    assert not any(a.kod == "engelska_inslag" for a in r.anmarkningar)


def test_kontrollera_flaggar_avhuggen_text():
    r = kontrollera("Hej Anna!\n\nVi ville bara säga att,")
    assert any(a.kod == "avhuggen_text" for a in r.allvarliga)


def test_kontrollera_flaggar_markdownrester():
    r = kontrollera("Hej!\n\n**Viktigt:** läs detta.")
    assert any(a.kod == "markdownrester" for a in r.allvarliga)


def test_kontrollera_tom_text_kraver_granskning():
    assert kontrollera("   ").kraver_granskning


def test_kontrollera_ren_svensk_text_passerar():
    r = kontrollera(
        "Hej Johan!\n\nJag såg att Nordform öppnat ett nytt lager i Växjö. "
        "Många i er bransch får återkommande frågor om leveranstider — Snajp "
        "svarar på dem automatiskt, dygnet runt.\n\n"
        "Vore det intressant med en kort demo?\n\nVänliga hälsningar\nIris"
    )
    assert not r.kraver_granskning
    assert r.text.startswith("Hej Johan!")


def test_kontrollera_lang_text_med_siffror_och_lankar():
    stycken = [
        f"Stycke {i}: priset är {i * 100} kr per månad, se https://snajp.se/pris."
        for i in range(1, 30)
    ]
    r = kontrollera("Hej!\n\n" + "\n\n".join(stycken) + "\n\nVänliga hälsningar")
    assert not r.kraver_granskning
    assert "https://snajp.se/pris" in r.text


# ------------------------------------------------- _verifiera_korrektur


def test_verifiering_faller_borttappad_lank():
    assert not _verifiera_korrektur(
        "Se https://snajp.se/pris för detaljer.", "Se vår prissida för detaljer."
    )


def test_verifiering_faller_andrad_siffra():
    assert not _verifiera_korrektur("Priset är 1 495 kr.", "Priset är 1 595 kr.")


def test_verifiering_faller_andrat_produktnamn():
    assert not _verifiera_korrektur("Iris hittar era leads.", "Irris hittar era leads.")


def test_verifiering_faller_tom_och_for_kort_text():
    assert not _verifiera_korrektur("En rimligt lång mening om saker.", "")
    assert not _verifiera_korrektur("En rimligt lång mening om saker och ting.", "Kort.")


def test_verifiering_godkanner_ren_sprakrattning():
    assert _verifiera_korrektur(
        "Vi vill gärna sammarbeta kring er epost på https://snajp.se.",
        "Vi vill gärna samarbeta kring er e-post på https://snajp.se.",
    )


# -------------------------------------------------- sakra_utgaende_text


@pytest.mark.anyio
async def test_sakra_utgaende_text_ren_text_kostar_inget_llm_anrop():
    r = await sakra_utgaende_text("Hej! Tack för ditt svar. Vänliga hälsningar, Iris")
    assert not r.kraver_granskning
    assert not any(a.kod == "llm_korrektur" for a in r.anmarkningar)


@pytest.mark.anyio
async def test_sakra_utgaende_text_flaggad_text_utan_llm_kraver_granskning():
    # I simuleringsläge (testsvitens läge) görs inget LLM-pass — flaggan
    # ska då stå kvar och tvinga mänsklig granskning.
    r = await sakra_utgaende_text("Hej [förnamn]! Vi hörs.")
    assert r.kraver_granskning


# ------------------------------------------------------------- statiskt


def test_sprakregler_ar_svenska_och_namner_stavning():
    assert "stavning" in SPRAKREGLER
    assert "svenska" in SPRAKREGLER.lower()


def test_felstavningslistan_har_inga_noops_och_bara_gemener():
    for fel, ratt in FELSTAVNINGAR.items():
        assert fel != ratt, f"no-op: {fel}"
        assert fel == fel.lower()


def test_skyddade_namn_rattas_aldrig_av_listan():
    for namn in SKYDDADE_NAMN:
        assert namn.lower() not in FELSTAVNINGAR
