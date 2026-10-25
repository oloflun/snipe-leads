"""Antons beställning 2026-10-25: ingången får inte läsas som kritik ("för
offensivt och angripande … kan träffa en öm tå"), och avslutet "Svara X så
gör vi Y" är förbjudet. Hans egna exempel ur produktionen är facit för
ingången: de tre första är rätt riktning, de två sista fel."""

import pytest

from app.leads import stilkontroll as stil

PRODUKT = "Vår agent Iris hittar nya företagskunder åt dig."
AVSLUT = "Vill du veta mer finns en demo på snajp.se/demo, eller så svarar du på mejlet och vi bokar en genomgång."


def _koder(ingang: str) -> set[str]:
    return {a.kod for a in stil.kontrollera(f"Hej Mats,\n\n{ingang}\n\n{PRODUKT}\n\n{AVSLUT}").anmarkningar}


@pytest.mark.parametrize(
    "ingang",
    [
        "Att svara på alla frågor om reparationer och nybyggnationer från företag och husägare kan göra det "
        "svårt att hålla de korta handläggningstider du lovar.",
        "En enkel och trygg affär är vad säljaren av en samlarbil vill ha. Men det förutsätter att du hinner "
        "hitta nästa säljare, samtidigt som du tar hand om bilarna du redan har.",
        "Att vara kontrollansvarig och samtidigt hinna hitta nästa uppdrag är en svår balansgång.",
    ],
)
def test_antons_goda_ingangar_passerar(ingang):
    assert not _koder(ingang) & {"kritisk_ingang", "svara_sa_avslut"}


@pytest.mark.parametrize(
    "ingang",
    [
        "Du lovar ett förutsättningslöst samtal och en kostnadsfri offert, men frågor om löpande underhåll "
        "och bygguppdrag hinner sällan besvaras.",
        "Du lovar varje kund det perfekta binderiet, med passion och omtanke. Men den tiden försvinner "
        "snabbt när frågor om öppettider kommer samtidigt som du har en kund i butiken.",
    ],
)
def test_ingang_som_kritik_falls(ingang):
    assert "kritisk_ingang" in _koder(ingang)


def test_avslutet_som_order_falls_men_inbjudan_passerar():
    for avslut in (
        "Svara på det här mejlet, så bokar vi 20 minuter.",
        "Svara \"pilot\" på mejlet, så håller vi en plats åt dig.",
        "Vill du testa kan du svara 'ja' på mejlet.",
    ):
        text = f"Hej,\n\nAtt hinna allt är en balansgång.\n\n{PRODUKT}\n\n{avslut}"
        assert "svara_sa_avslut" in {a.kod for a in stil.kontrollera(text).anmarkningar}, avslut
    assert "svara_sa_avslut" not in _koder("Att hinna allt är en balansgång.")
