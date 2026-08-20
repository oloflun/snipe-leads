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
        assert set(b) == {"company_name", "contact_name", "motivering"}
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
    assert all("i Sverige" in b["motivering"] for b in bolag)
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
