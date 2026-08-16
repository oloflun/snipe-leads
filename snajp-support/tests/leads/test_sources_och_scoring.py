"""CSV-källan och scoringen — hela DEL 1-kedjan mot den riktiga fixturen."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.leads.icp import validate_icp
from app.leads.scoring import MISS, TRAFF, score_prospect
from app.leads.sources import AllabolagSource, BolagsverketSource, CsvSource, Prospect, SourceError

FIXTURER = Path(__file__).resolve().parents[2] / "fixtures"
UMEA = FIXTURER / "prospects-umea.csv"
GOTEBORG = FIXTURER / "prospects-goteborg.csv"


def smaforetag_umea() -> dict:
    return validate_icp(
        {
            "geo": ["umea"],
            "size": {"anstallda_min": 1, "anstallda_max": 49},
            "max_prospects_per_run": 25,
        }
    )


# -- Källan -----------------------------------------------------------------


def test_fixturen_gar_att_lasa():
    prospekt = CsvSource(UMEA).search({})
    assert len(prospekt) == 12
    assert any(p.company_name == "Norrlands Elservice AB" for p in prospekt)


def test_saknad_fil_ger_begripligt_fel():
    with pytest.raises(SourceError) as fel:
        CsvSource(FIXTURER / "finns-inte.csv").search({})
    assert "finns inte" in str(fel.value)


def test_geografifiltret_tar_bort_skelleftea():
    """Fixturen innehåller ett bolag som SKA falla på geografin. En fixtur
    där allt passerar testar ingenting."""
    valda, bortvalda = CsvSource(UMEA).search_med_bortval(smaforetag_umea())
    namn = {p.company_name for p in valda}
    bortnamn = {p.company_name for p, _ in bortvalda}

    assert "Skellefteå Industriservice AB" in bortnamn
    assert "Skellefteå Industriservice AB" not in namn


def test_storleksfiltret_tar_bort_storbolaget():
    valda, _ = CsvSource(UMEA).search_med_bortval(smaforetag_umea())
    assert "Norrbottens Storbygg AB" not in {p.company_name for p in valda}


def test_bortvalda_behaller_sin_motivering():
    """Utan den blir ett för snävt ICP omöjligt att felsöka — kunden ser en
    tom lista utan att veta att det var det egna filtret som tömde den."""
    _, bortvalda = CsvSource(UMEA).search_med_bortval(smaforetag_umea())
    _, score = next(
        (p, s) for p, s in bortvalda if p.company_name == "Skellefteå Industriservice AB"
    )
    assert score["diskvalificerad"] is True
    assert any("utanför" in skäl for skäl in score["diskvalificerande_skal"])


def test_taket_kapar_listan():
    icp = validate_icp({"geo": ["umea"], "max_prospects_per_run": 3})
    assert len(CsvSource(UMEA).search(icp)) == 3


def test_sorteringen_ar_stabil():
    """Två körningar på samma fil ska ge samma ordning — annars blir 'de tre
    bästa utkasten' olika bolag mellan körningarna."""
    icp = smaforetag_umea()
    forsta = [p.company_name for p in CsvSource(UMEA).search(icp)]
    andra = [p.company_name for p in CsvSource(UMEA).search(icp)]
    assert forsta == andra


def test_scoren_foljer_med_prospektet():
    valda = CsvSource(UMEA).search(smaforetag_umea())
    assert all("score_breakdown" in p.extra for p in valda)
    assert all(0 <= p.extra["total"] <= 100 for p in valda)


def test_branschfiltret_valjer_nischen():
    icp = validate_icp({"geo": ["umea"], "sni_codes": ["43.210", "43.220"]})
    namn = {p.company_name for p in CsvSource(UMEA).search(icp)}
    assert namn == {"Norrlands Elservice AB", "Ume VVS och Värme AB"}


def test_uteslutna_domaner_biter():
    icp = validate_icp({"geo": ["umea"], "exclude_domains": ["kodverkstan.example"]})
    namn = {p.company_name for p in CsvSource(UMEA).search(icp)}
    assert "Kodverkstan i Umeå AB" not in namn


# -- Scoringen --------------------------------------------------------------


def test_namnaren_raknas_pa_det_som_faktiskt_ar_satt():
    """Ett ICP med bara geografi ska kunna ge 100, inte 30.

    Prospektet måste ha en kontaktväg för att nå 100: kontaktbarhet är en
    egenskap hos bolaget och räknas alltid, till skillnad från de kriterier
    kunden själv konfigurerar.
    """
    prospect = Prospect(
        company_name="Testbolaget AB",
        postnr="903 27",
        ort="Umeå",
        contact_email="info@testbolaget.example",
    )
    score = score_prospect(prospect, {"geo": ["umea"]})
    assert score.total == 100


def test_onabart_prospekt_nar_inte_hundra():
    prospect = Prospect(company_name="Onåbar AB", postnr="903 27", ort="Umeå")
    assert score_prospect(prospect, {"geo": ["umea"]}).total < 100


def test_diskvalificerad_ger_noll_men_behaller_breakdown():
    """Kunden ska kunna se att bolaget var en bra träff på allt UTOM det som
    fällde det."""
    prospect = Prospect(
        company_name="Fel Ort AB",
        postnr="211 20",
        ort="Malmö",
        sni="43.220",
        contact_email="info@felort.example",
    )
    score = score_prospect(prospect, {"geo": ["umea"], "sni_codes": ["43.220"]})
    assert score.total == 0
    assert score.diskvalificerad
    # SNI-kriteriet är fortfarande en träff, trots att geografin fällde bolaget.
    sni = next(k for k in score.breakdown if k.nyckel == "sni")
    assert sni.utfall == TRAFF


def test_utan_kriterier_ar_poangen_omatbar_och_sager_det():
    score = score_prospect(Prospect(company_name="Testbolaget AB"), {})
    assert score.total == 0
    assert any(k.nyckel == "inga_kriterier" for k in score.breakdown)


def test_varje_kriterium_bar_en_motivering():
    """En användare som ser 84/100 utan att veta varför litar inte på listan."""
    prospect = Prospect(
        company_name="Testbolaget AB", postnr="903 27", sni="43.220", anstallda=12
    )
    score = score_prospect(prospect, smaforetag_umea() | {"sni_codes": ["43.220"]})
    assert all(k.motivering.strip() for k in score.breakdown)


def test_okand_storlek_diskvalificerar_inte():
    """Antal anställda saknas rutinmässigt även i bra källor — Bolagsverkets
    register har uppgiften inte alls. Att fälla på den hade tömt listan på
    allt utom de bolag som råkat ha en extra ifylld kolumn.

    Notera att poängen ändå BLIR lägre än för ett bolag med bekräftad storlek.
    Det är en oundviklig följd av att poängen är en kvot: en okänd uppgift kan
    inte vara neutral när något annat är en miss. Skillnaden mellan att inte
    diskvalificeras och att inte påverkas alls är värd att hålla isär.
    """
    utan_uppgift = Prospect(
        company_name="B AB", postnr="903 27", contact_email="info@b.example"
    )
    score = score_prospect(utan_uppgift, smaforetag_umea())
    assert not score.diskvalificerad
    anstallda = next(k for k in score.breakdown if k.nyckel == "anstallda")
    assert anstallda.utfall == "okänd"


def test_kant_varde_utanfor_spannet_diskvalificerar():
    """Skillnaden går mellan 'vi vet inte' och 'vi vet, och det stämmer inte'."""
    for_stort = Prospect(
        company_name="Storbolaget AB",
        postnr="903 27",
        anstallda=240,
        contact_email="info@stor.example",
    )
    score = score_prospect(for_stort, smaforetag_umea())
    assert score.diskvalificerad
    assert any("240" in skäl for skäl in score.diskvalificerande_skal)


def test_okand_plats_diskvalificerar_nar_geo_ar_satt():
    score = score_prospect(Prospect(company_name="Okänd AB"), {"geo": ["umea"]})
    assert score.diskvalificerad


def test_saknad_kontaktvag_ar_en_miss():
    prospect = Prospect(company_name="Onåbar AB", postnr="903 27")
    kontakt = next(
        k for k in score_prospect(prospect, {"geo": ["umea"]}).breakdown if k.nyckel == "kontakt"
    )
    assert kontakt.utfall == MISS


# -- Personlig kontra funktionell adress ------------------------------------


@pytest.mark.parametrize(
    "adress,personlig",
    [
        ("info@bolaget.example", False),
        ("kontakt@bolaget.example", False),
        ("order@bolaget.example", False),
        ("anna.lindqvist@bolaget.example", True),
        ("erik-sandberg@bolaget.example", True),
    ],
)
def test_personlig_adress_flaggas(adress, personlig):
    """Att felaktigt flagga en funktionsadress kostar en extra informationsruta
    i mejlet; att missa en personlig adress kostar ett regelbrott."""
    assert Prospect(company_name="X AB", contact_email=adress).epost_ar_personlig is personlig


# -- Stubbarna --------------------------------------------------------------


@pytest.mark.parametrize("kalla", [BolagsverketSource(), AllabolagSource()])
def test_registerkallorna_ar_arliga_stubbar(kalla):
    with pytest.raises(NotImplementedError) as fel:
        kalla.search({})
    assert "CsvSource" in str(fel.value)


def test_allabolagstubben_forbjuder_skrapning_i_sitt_felmeddelande():
    """Regeln ska möta nästa implementation innan den skrivs."""
    with pytest.raises(NotImplementedError) as fel:
        AllabolagSource().search({})
    assert "ALDRIG" in str(fel.value)


def test_goteborgsfixturen_fungerar_likadant():
    icp = validate_icp({"geo": ["goteborg"], "size": {"anstallda_min": 1, "anstallda_max": 49}})
    valda, bortvalda = CsvSource(GOTEBORG).search_med_bortval(icp)
    assert "Borås Textilservice AB" in {p.company_name for p, _ in bortvalda}
    assert "Västsvenska Entreprenad AB" in {p.company_name for p, _ in bortvalda}
    assert len(valda) == 10
