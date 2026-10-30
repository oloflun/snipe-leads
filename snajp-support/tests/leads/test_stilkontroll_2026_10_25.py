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


def test_fokusgreppet_med_deras_hantverk_ibland():
    """Anton 2026-10-25: "kräver att ni kan fokusera på varje projekt, inte på
    att söka upp nästa uppdrag" är okej ibland, men med deras hantverk ("att ni
    fokuserar på måleriet") och inte i varje mejl."""
    hantverk = "Att lägga om tak i Umeå kräver att ni kan fokusera på takläggningen, inte på att hitta nästa uppdrag."
    allmant = "Att bygga i Umeå kräver att ni kan fokusera på varje projekt, inte på att söka upp nästa uppdrag."
    assert "mallord_i_ingangen" not in _koder(hantverk)
    assert "mallord_i_ingangen" in _koder(allmant)

    def mejl(ingang: str) -> str:
        return f"Hej,\n\n{ingang}\n\n{PRODUKT}\n\n{AVSLUT}"

    andra = [mejl(f"Att måla fasader i {ort} kräver att ni kan fokusera på måleriet.") for ort in ("Luleå", "Piteå")]
    assert "samma_grepp" in {a.kod for a in stil.mot_andra(mejl(hantverk), andra)}
    assert "samma_grepp" not in {a.kod for a in stil.mot_andra(mejl(hantverk), andra[:1])}


def test_fokusgreppet_far_bara_vart_fjarde_mejl_och_synonymerna_rakas():
    from app.agent.leads_research_v2 import _fokus_ok, _stilfynd

    andel = sum(_fokus_ok(f"p-{i}") for i in range(400)) / 400
    assert 0.18 < andel < 0.32
    nej = next(f"p-{i}" for i in range(50) if not _fokus_ok(f"p-{i}"))
    utkast = {"subject": "x", "body": "Hej,\n\nAtt kakla badrum kräver att ni kan ägna er åt plattsättningen.\n\nVår agent Iris hittar kunder åt er."}
    assert any("fokusera" in f for f in _stilfynd(utkast, villkor=None, produkt=None, andra=[], fokus_ok=_fokus_ok(nej)))
    assert "mallord_i_ingangen" in _koder("Att bygga kräver att ni kan ägna er åt varje projekt, inte åt nästa uppdrag.")


def test_avslutet_som_order_falls_men_inbjudan_passerar():
    for avslut in (
        "Svara på det här mejlet, så bokar vi 20 minuter.",
        "Svara \"pilot\" på mejlet, så håller vi en plats åt dig.",
        "Vill du testa kan du svara 'ja' på mejlet.",
    ):
        text = f"Hej,\n\nAtt hinna allt är en balansgång.\n\n{PRODUKT}\n\n{avslut}"
        assert "svara_sa_avslut" in {a.kod for a in stil.kontrollera(text).anmarkningar}, avslut
    assert "svara_sa_avslut" not in _koder("Att hinna allt är en balansgång.")
