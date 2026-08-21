"""Exempelbolagen — vägen IN i produkten för en arbetsyta utan prospekt.

Generatorn är ren och deterministisk med flit (se leads/exempelbolag.py), och
det är precis vad som gör den värd att testa här: utfallet går att fastställa
utan nyckel, nätverk eller databas.

Det testerna vaktar är två löften som inte syns i en diff:

 1. **ICP:t styr bolagen.** Ett formulär som beskriver en målgrupp och skapar
    bolag ur en annan är värre än inga bolag alls — kunden ser agenten arbeta
    på fel sorts företag och drar slutsatsen att produkten inte förstår dem.
 2. **Samma ICP ger samma lista.** Utan det byter demonstrationen innehåll
    mellan två klick, och "kör igen" blir omöjligt att jämföra.
"""

import pytest
from app.leads.exempelbolag import _DEFAULT_ORTER as DEFAULT_ORTER
from app.leads.exempelbolag import bygg_exempelbolag

VVS_ICP = {
    "industries": ["VVS"],
    "geography": ["Malmö"],
    "roles": ["Inköpschef"],
    "company_size": {"min": 10, "max": 40},
}


def test_ger_ratt_antal_och_alla_falt():
    bolag = bygg_exempelbolag(VVS_ICP, antal=3)

    assert len(bolag) == 3
    for b in bolag:
        # Samma fält som ett RIKTIGT prospekt bär efter research. Ett
        # exempelbolag med bara ett namn ser i listan ut som ett prospekt vars
        # research misslyckats, och det är fel intryck av produkten.
        assert set(b) == {
            "company_name", "contact_name", "orgnr", "ort", "website",
            "anstallda", "bransch", "signal", "beskrivning", "motivering",
            # Utkastet som öppnas i Email Studio. Ett exempelbolag utan pitch
            # är ett bolag man inte kan göra något med.
            "pitch_subject", "pitch_body", "pitch_varfor_nu",
        }
        assert all(str(v).strip() for v in b.values())
        assert b["company_name"].strip()
        # Bolagsformen är sista ledet i varje namn. Ett "bolag" utan bolagsform
        # läser som ett påhittat ord, inte som ett företag.
        assert b["company_name"].endswith("AB")


def test_samma_icp_ger_samma_lista():
    assert bygg_exempelbolag(VVS_ICP, antal=5) == bygg_exempelbolag(VVS_ICP, antal=5)


def test_icp_styr_bransch_ort_och_roll():
    b = bygg_exempelbolag(VVS_ICP, antal=1)[0]

    assert "Vvs" in b["company_name"]
    assert b["contact_name"] == "Inköpschef"
    assert "vvs i Malmö" in b["motivering"]
    assert "inköpschef" in b["motivering"]


def test_storleksspannet_star_i_motiveringen():
    b = bygg_exempelbolag(VVS_ICP, antal=1)[0]

    assert "10–40 anställda" in b["motivering"]


def test_utan_icp_faller_den_tillbaka_pa_svenska_smb_branscher():
    # En ny kund har ingen ICP ännu. Att svara med noll bolag då hade gjort
    # funktionen värdelös just när den behövs mest.
    bolag = bygg_exempelbolag(None, antal=2)

    assert len(bolag) == 2
    # Utan geografi i ICP:t väljs en svensk STAD, inte strängen "Sverige":
    # ortskolumnen ska bära en ort, och "Sverige" där läser sig som ett fält
    # som aldrig fylldes i.
    assert all(b["ort"] in DEFAULT_ORTER for b in bolag)
    assert all(b["contact_name"] for b in bolag)


def test_tomt_icp_beter_sig_som_inget_icp():
    assert bygg_exempelbolag({}, antal=2) == bygg_exempelbolag(None, antal=2)


def test_motiveringen_sager_att_bolaget_ar_pahittat():
    # Texten går rakt ut i UI:t. Ett exempelbolag som inte är märkt som
    # exempel är ett bolag kunden kan tro är en riktig lead.
    for b in bygg_exempelbolag(VVS_ICP, antal=3):
        assert "påhittat" in b["motivering"]
        assert b["motivering"].startswith("Exempelbolag:")


def test_antal_noll_eller_negativt_ger_tom_lista():
    assert bygg_exempelbolag(VVS_ICP, antal=0) == []
    assert bygg_exempelbolag(VVS_ICP, antal=-5) == []


def test_flera_branscher_fordelas_over_bolagen():
    # Roterar över listan i stället för att ta det första värdet: en kund med
    # tre branscher i sitt ICP ska se alla tre representerade.
    icp = {"industries": ["Bygg", "Logistik"], "geography": ["Göteborg"]}
    motiveringar = " ".join(b["motivering"] for b in bygg_exempelbolag(icp, antal=2))

    assert "bygg i Göteborg" in motiveringar
    assert "logistik i Göteborg" in motiveringar


def test_orgnumret_ar_alltid_ogiltigt():
    """Ett exempelbolag får ALDRIG bära ett org.nr som kan vara någons.

    Formen ska se rätt ut (556-serien, sex+fyra siffror) så att kolumnen är
    läsbar — men kontrollsiffran är medvetet fel. Klarar numret Luhn kan det
    tillhöra ett verkligt bolag, och då är exempelbolaget inte påhittat längre:
    det är ett riktigt företag med påhittade uppgifter om sig.
    """
    from app.leads.orgnr import validera_format

    for b in bygg_exempelbolag(VVS_ICP, antal=6):
        assert b["orgnr"].startswith("556")
        assert len(b["orgnr"]) == 11 and b["orgnr"][6] == "-"
        with pytest.raises(Exception):
            validera_format(b["orgnr"])


def test_webbplatsen_ligger_under_example():
    """RFC 2606 reserverar .example — domänen kan aldrig registreras.

    Adressen visas i vyn och går att klicka på av misstag. Då ska den leda
    ingenstans, inte till ett bolag som undrar varför de står i vår produkt.
    """
    for b in bygg_exempelbolag(VVS_ICP, antal=4):
        assert b["website"].endswith(".example")


def test_storleken_haller_sig_inom_icp_spannet():
    for b in bygg_exempelbolag(VVS_ICP, antal=8):
        assert 10 <= b["anstallda"] <= 40


# -- Pitchen ----------------------------------------------------------------


def test_pitchen_binder_signalen_till_produkten():
    """Signal → varför nu → produkt → en fråga. I den ordningen.

    Ordningen är också ett skydd: ett mejl som börjar med produkten kan skickas
    till vem som helst, och blir därför spam i praktisk mening även när det är
    lagligt. Med signalen först går texten inte att skriva utan att någon läst
    på om mottagaren.
    """
    b = bygg_exempelbolag(
        {"industries": ["Bygg"], "geography": ["Umeå"], "roles": ["Platschef"]},
        antal=1,
        produkt="hjärtstartare och HLR-utbildning till arbetsplatser",
        avsandare="Anna, Hjärtsäker AB",
    )[0]

    text = b["pitch_body"]
    assert text.index(b["ort"]) < text.index("hjärtstartare"), (
        "Produkten står före signalen. Då kan mejlet skickas till vem som helst."
    )
    assert "Anna, Hjärtsäker AB" in text
    assert text.rstrip().endswith("Anna, Hjärtsäker AB")
    assert b["pitch_subject"].strip()


def test_pitchen_hittar_inte_pa_siffror_eller_referenser():
    """INV-GROUND-001 i exempelform.

    Ett påhittat resultat ("vi sparade 40 %") i ett EXEMPEL är värre än vanligt:
    kunden skickar texten vidare i tron att den är kontrollerad.
    """
    for b in bygg_exempelbolag(VVS_ICP, antal=6, produkt="X", avsandare="Y"):
        text = b["pitch_body"].lower()
        for förbjudet in ("%", "kr ", "spara", "ökade", "kund hos oss", "referens"):
            assert förbjudet not in text, f"pitchen påstår något omätt: {förbjudet!r}"


def test_utan_affarskontext_lamnas_en_plats_att_fylla():
    """En påhittad produkt är en text kunden måste skriva OM.

    En tom plats är en text de fyller I. Det andra tar tio sekunder; det första
    tar en irritation och ett omdöme om produkten.
    """
    from app.leads.exempelbolag import PRODUKTPLATSHALLARE

    b = bygg_exempelbolag(VVS_ICP, antal=1)[0]
    assert PRODUKTPLATSHALLARE in b["pitch_body"]
    assert "[ert namn]" in b["pitch_body"]
