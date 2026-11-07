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
    assert "deras vardag" in regler and "produktmeningen" in regler
    assert f"högst {erbjudanden.ORDTAK['rak']} ord" in regler
    assert "Ingen fråga" in regler
    # "balansgång" står bara som förbud, aldrig som anvisning.
    assert "aldrig en abstrakt utmaning eller balansgång" in regler
    assert erbjudanden.ORDTAK["rak"] < erbjudanden.ORDTAK["fraga"] <= stil.MAX_ORD_MEJL


def _alla_former() -> list[str]:
    return [form for former in _INGANGSFORMER.values() for form in former]


def test_ingangsformerna_och_personaliseringen_ber_aldrig_om_balansgang_eller_fraga():
    for form in _alla_former():
        assert "balansgång" not in form and "fråga till dem" not in form, form
    assert "som en balansgång" not in _INGANGSUPPGIFT
    assert "aldrig en abstrakt utmaning eller balansgång" in _INGANGSUPPGIFT.casefold()
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


# -- provet i development 2026-11-06 -------------------------------------------------


@pytest.mark.parametrize(
    "ingang",
    [
        "När Footnet säljer naturlig fotvård online svarar vår Supportagent direkt på kundfrågorna.",
        "När Nälsta Bygg välkomnar nya projekt kan vår agent Iris hitta nya företagskunder.",
        "När ni säljer fisk och skaldjur behöver ni nya företagskunder.",
    ],
)
def test_nar_oppningen_ar_en_mall_oavsett_subjekt(ingang):
    assert "slentrian_ingang" in _koder(f"Hej,\n\n{ingang}\n\nTitta gärna på demon på snajp.se/demo.")


def test_en_lang_produktmening_skrivs_om_nar_villkoren_ar_korta():
    lang = (
        "Hej,\n\nVIASALES utbildar unga säljare inom uppsökande försäljning. Vår agent Iris hittar nya "
        "företagskunder åt er och skriver färdiga första mejl som ni godkänner, så att tiden går till samtal i "
        "stället för research.\n\nTitta gärna på demon på snajp.se/demo."
    )
    utkast = {"subject": "Nya kunder", "body": lang}
    kort_villkor = sm._PILOTER[sm.IRIS]
    langt_villkor = "Vi lovar " + " ".join(["ord"] * 30) + ". Handling: svara på mejlet."
    def fynd(villkor):
        return _stilfynd(utkast, villkor=villkor, produkt=IRIS, andra=[], amne_i_kod=True, tak=erbjudanden.ORDTAK["rak"])
    assert any("mening över" in f for f in fynd(kort_villkor))
    assert any("mening över" in f for f in fynd(None))
    # Villkor med en lång mening dikterar meningen: då flaggas den bara vid köningen.
    assert not any("mening över" in f for f in fynd(langt_villkor))


# -- andra varvet 2026-11-06: de tre kvarvarande felen ----------------------------------


def test_en_kravande_ingang_falls_i_a_men_inte_i_uppfoljningen():
    lisa = (
        "Hej,\n\nAtt erbjuda delikatesser i Stockholm kräver att ni kontinuerligt når ut till nya företagskunder. "
        "Vår agent Iris hittar nya företagskunder åt er.\n\nTitta gärna på demon på snajp.se/demo."
    )
    assert "kravande_ingang" in _koder(lisa)
    assert "kravande_ingang" in _koder(lisa.replace("kräver att ni", "förutsätter att ni"))
    # B har sin egen kod, och ett konstaterande passerar.
    assert "kravande_ingang" not in {a.kod for a in stil.kontrollera(lisa, struktur="b").anmarkningar}
    assert "kravande_ingang" not in _koder(A_IRIS)
    from app.leads.follow_up_generator import _EJ_I_UPPFOLJNING

    assert "kravande_ingang" in _EJ_I_UPPFOLJNING


@pytest.mark.parametrize(
    "mening",
    [
        "Att ni själva hanterar er e-postsupport visar ert engagemang för integritet.",
        "Det visar ett aktivt engagemang i branschen.",
        "Er tillväxt är imponerande.",
    ],
)
def test_smicker_falls(mening):
    assert "smicker" in _koder(f"Hej,\n\n{mening} Vår Supportagent svarar på frågorna.\n\nTitta gärna på demon.")


@pytest.mark.parametrize(
    ("mening", "fel"),
    [
        ("Vår agent Iris tar fram nya hyresgäster åt dig.", True),
        ("Vår agent Iris hittar och kvalificerar nya privatpersoner åt er.", True),
        ("Vår agent Iris tar fram 40–50 nya investerare i veckan.", True),
        # "uppdrag" står i Antons facit 2026-10-12 och fälls bara i B:s fråga.
        ("Vår agent Iris hittar nya rivningsuppdrag åt er.", False),
        ("Vår agent Iris tar fram fler fastighetsbolag och bostadsrättsföreningar åt er.", False),
        ("Vår agent Iris hittar nya företagskunder som vill sälja via er plattform.", False),
    ],
)
def test_iris_tar_bara_fram_foretag(mening, fel):
    text = f"Hej,\n\nNi förvaltar fastigheter i Stockholm. {mening}\n\nTitta gärna på demon på snajp.se/demo."
    koder = {a.kod for a in stil.erbjudande_fynd(text, villkor=None, produkt=IRIS)}
    assert ("fel_sak" in koder) is fel
    # Supportagenten berörs inte.
    assert "fel_sak" not in {a.kod for a in stil.erbjudande_fynd(text.replace("agent Iris", "Supportagent"), villkor=None, produkt=SUPPORT)}


# -- tredje varvet 2026-11-06 ---------------------------------------------------------


@pytest.mark.parametrize(
    ("mening", "generisk"),
    [
        ("Vår agent Iris hittar och kvalificerar nya företagskunder åt er och skriver färdiga första mejl.", True),
        ("Vår agent Iris hittar nya företagskunder som passar dig och skriver ett första mejl till dem.", True),
        ("Den hittar och kvalificerar nya företagskunder som passar er och skriver ett första mejl.", True),
        ("Vår agent Iris hittar nya företagskunder som vill sälja via er plattform.", False),
        ("Vår agent Iris tar fram fler fastighetsbolag och bostadsrättsföreningar åt er varje vecka.", False),
        # Provet 2026-11-07: utfallet avskrivet i stället för "fler sådana".
        ("Vår agent Iris hittar 40–50 nya företagskunder åt er varje vecka och skriver ett första mejl.", True),
        ("Vår agent Iris tar fram 40–50 nya företagskunder varje vecka som behöver era produkter och skriver.", True),
        ("Vår agent Iris tar fram fler sådana kunder åt er varje vecka och skriver ett första mejl.", False),
    ],
)
def test_kedjan_ber_om_vilka_foretag_nar_iris_meningen_ar_generisk(mening, generisk):
    utkast = {"subject": "Nya kunder", "body": f"Hej,\n\nNi säljer maskiner till verkstäder. {mening}\n\nTitta gärna på demon."}
    fynd = _stilfynd(utkast, villkor=None, produkt=IRIS, andra=[], amne_i_kod=True, tak=erbjudanden.ORDTAK["rak"])
    assert any("vilka sorters företag" in f for f in fynd) is generisk
    # Supportagenten och B berörs inte, och stilkontrollen (facit) inte heller.
    assert not utkaststruktur.generisk_iris_mening(utkast["body"], SUPPORT)
    b = _stilfynd(utkast, villkor=None, produkt=IRIS, andra=[], amne_i_kod=True, struktur="b")
    assert not any("vilka sorters företag" in f for f in b)


def test_smicker_i_andra_ordalag_falls():
    assert "smicker" in _koder("Hej,\n\nAtt ni lanserade en ny tjänst visar ert kontinuerliga arbete med integritet. "
                               "Vår Supportagent svarar på frågorna.\n\nTitta gärna på demon.")


def test_ingangsformerna_bjuder_inte_in_till_nar_bisatsen():
    assert all("När" not in f for f in _alla_former())
    assert "egen huvudsats" in erbjudanden.formregler("rak", IRIS)
    assert "egen huvudsats" in _INGANGSUPPGIFT


# -- utdatakontraktet i omskrivningen (provet 2026-11-06, 3 av 36 utkast föll) --------


@pytest.mark.anyio
async def test_en_omskrivning_som_bryter_kontraktet_faller_inte_utkastet(miljo):
    """Utkastet och personaliseringen svarar rätt, men med en ingång grinden
    fäller; varje omskrivning därefter saknar sources_used, som i provet. Då
    står den senaste godkända versionen kvar och köas, med stilfyndet på
    köposten, i stället för att hela utkastet kastas."""
    from tests.agent.test_leads_v2_wiring import _FakeLLM

    med_fynd = (
        "Hej,\n\nAtt lägga golv och samtidigt hitta nya kunder är en balansgång. Vår agent Iris tar fram "
        "fler fastighetsbolag åt er.\n\nJust nu tar vi in 20 företag i en kostnadsfri pilot av Iris.\n\n"
        "Titta gärna på demon på snajp.se/demo."
    )

    class _BrytandeOmskrivning(_FakeLLM):
        async def create(self, **kw):
            svar = await super().create(**kw)
            if self.calls[-1] == "sa:draft-outreach" and self.calls.count("sa:draft-outreach") > 2:
                data = json.loads(svar.choices[0].message.content)
                data.pop("sources_used", None)
                data.pop("context_refs", None)
                svar.choices[0].message.content = json.dumps(data, ensure_ascii=False)
            return svar

    llm = _BrytandeOmskrivning(
        {
            "sa:draft-outreach": {"subject": "Nya kunder", "body": med_fynd},
            "snajp:humanizer-svenska": {"final_subject": "Nya kunder", "final_body": med_fynd},
        }
    )
    storage = MemoryStorage()
    trad, _ = await _forbered(storage)
    resultat = await _skriv(storage, trad, llm, "a")
    assert llm.calls.count("sa:draft-outreach") > 2, "omskrivningen ska ha körts och brutit kontraktet"
    assert resultat["queued"], resultat.get("escalation_reason")
    assert "balansgång" in storage.outreach_messages[TENANT][0]["body"]
    post = json.dumps(storage.send_queue[TENANT][0], ensure_ascii=False, default=str)
    assert "mallord" in post or "Stil:" in post


# -- Anton 2026-11-07: ingången är deras vardag, aldrig bolagets verksamhetsbeskrivning --


#: Provets ingångar med påhittade namn: bolagets namn som subjekt och sajtens
#: beskrivning av vad det gör.
BESKRIVNINGAR = [
    ("Fotnät AB", "Fotnät erbjuder naturlig fotvård online med produkter utvalda av en fotterapeut."),
    ("C Lindqvist Maskin & Verktyg Aktiebolag", "C Lindqvist Maskin & Verktyg säljer maskiner och verktyg till företagskunder."),
    ("Corvina Fastigheter AB", "Corvina Fastigheter förvaltar fastigheter med ett långsiktigt ägarperspektiv."),
    ("Mälsta Bygg AB", "Mälsta Bygg välkomnar frågor om nya projekt och tjänster."),
]


def _a_mejl(ingang: str, produktmening: str = "Vår agent Iris tar fram fler sådana kunder åt er.") -> str:
    return f"Hej,\n\n{ingang} {produktmening}\n\nTitta gärna på demon på snajp.se/demo."


@pytest.mark.parametrize(("bolag", "ingang"), BESKRIVNINGAR)
def test_bolagets_verksamhetsbeskrivning_som_ingang_falls(bolag, ingang):
    mejl = _a_mejl(ingang)
    assert "bolagsbeskrivning" in {a.kod for a in stil.kontrollera(mejl, tak=80, bolag=bolag).anmarkningar}
    # Kedjan skickar fyndet till omskrivningen med vad ingången ska säga i stället.
    fynd = _stilfynd({"subject": "Nya kunder", "body": mejl}, villkor=None, produkt=IRIS, andra=[], bolag=bolag,
                     amne_i_kod=True, tak=80)
    assert any("beskriver bolaget" in f and "vilka kunder" in f for f in fynd)
    # Utan bolagets namn (facit, uppföljningar) och i B prövas det inte.
    assert "bolagsbeskrivning" not in _koder(mejl)
    b = {a.kod for a in stil.kontrollera(mejl, struktur="b", bolag=bolag).anmarkningar}
    assert "bolagsbeskrivning" not in b


@pytest.mark.parametrize(
    ("bolag", "mejl"),
    [
        ("Golvbolaget i Göteborg AB", A_IRIS),
        ("Jeansverkstan AB", A_SUPPORT),
        ("Corvina Fastigheter AB", _a_mejl("Era hyresgäster hör av sig om felanmälningar, nycklar och tvättider.",
                                           "Vår Supportagent svarar på de frågorna direkt, dygnet runt.")),
        # Branschordet i namnet är inte namnordet: "fastigheter" i ingången är inte bolaget.
        ("Corvina Fastigheter AB", _a_mejl("Era fastigheter i Uppsala har många hyresgäster med frågor om avtalet.",
                                           "Vår Supportagent svarar på de frågorna direkt, dygnet runt.")),
        # Ett bolagsnamn som börjar med ett pronomen fäller aldrig "Era kunder …".
        ("Era Bygg AB", _a_mejl("Era kunder är bostadsrättsföreningar runt Uppsala.")),
    ],
)
def test_forslagets_ingang_passerar_med_bolagets_namn(bolag, mejl):
    assert "bolagsbeskrivning" not in {a.kod for a in stil.kontrollera(mejl, tak=80, bolag=bolag).anmarkningar}


def test_vad_deras_kunder_behover_ar_ingen_kravande_ingang():
    """Anton 2026-11-07: förbuden gjorde ingången generell. Kraven på dem fälls,
    vad deras kunder behöver får ingången säga."""
    kunder = _a_mejl("Era hyresgäster behöver snabba svar om nycklar och felanmälningar.",
                     "Vår Supportagent svarar på de frågorna direkt, dygnet runt.")
    assert "kravande_ingang" not in _koder(kunder)
    for krav in ("För att växa behöver ni hela tiden nya företagskunder.",
                 "Ni måste hela tiden hitta nya beställare.",
                 "Att sälja delikatesser kräver att ni når ut till nya kunder."):
        assert "kravande_ingang" in _koder(_a_mejl(krav)), krav
    # B behåller sitt bredare krav-förbud.
    assert "b_kravande_ingang" in {a.kod for a in stil.kontrollera(kunder, struktur="b").anmarkningar}


def test_ingangsformerna_foljer_produkten_och_ber_aldrig_om_vad_kunderna_far():
    assert all("kunder de säljer till" in f or "uppdrag" in f for f in _INGANGSFORMER["leads"])
    assert all("hör av sig" in f for f in _INGANGSFORMER["support"])
    for form in _alla_former():
        assert "får av dem" not in form, form
    # Personaliseringen och formregeln säger samma sak: deras vardag, aldrig bolagets namn.
    assert "aldrig bolagets namn" in _INGANGSUPPGIFT
    assert "verksamhetsbeskrivning, inte en ingång" in _INGANGSUPPGIFT
    assert "aldrig bolagets namn" in erbjudanden.formregler("rak", IRIS)


def test_skrivstilen_bar_forslagets_exempel_utan_att_grinden_fäller_dem():
    from app.agent.leads_systemprompt import skrivstil

    text = skrivstil()
    assert "Ni lägger de flesta golven" in text and "Dina kunder frågar ofta om skötsel" in text
    assert "Omgång 12" in text
    # Exemplen står utan citattecken: en verklig golvfirma med samma kunder
    # ska inte fällas som "kopierat_exempel".
    assert stil.kopierat_exempel("Ni lägger golv åt fastighetsbolag och bostadsrättsföreningar runt Göteborg.") is None


def test_iris_lovar_aldrig_fler_sadana_hyresgaster():
    """Provet 2026-11-07: "tar fram fler sådana hyresgäster åt dig" (ett fastighetsbolag)."""
    text = ("Hej,\n\nDu hyr ut bostäder och lokaler i Uppsala. Vår agent Iris tar fram fler sådana hyresgäster åt dig "
            "varje vecka.\n\nTitta gärna på demon.")
    assert "fel_sak" in {a.kod for a in stil.erbjudande_fynd(text, villkor=None, produkt=IRIS)}


def test_supportingangen_ar_en_fraga_kunderna_staller_inte_kategorin():
    for form in _INGANGSFORMER["support"][:1]:
        assert "aldrig bara bolagets bransch eller produktkategori" in form
    assert "aldrig bara bolagets bransch eller produktkategori" in _INGANGSUPPGIFT
    assert "aldrig bara bolagets bransch eller produktkategori" in erbjudanden.formregler("rak", SUPPORT)
