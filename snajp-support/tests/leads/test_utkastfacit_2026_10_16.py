"""INV-LEADS-UTKAST-002: facit för Iris första mejl efter Antons granskning
2026-10-15 ("Det första utkastet med Christoffer var det bästa … det är den
nivån och anpassningen jag förväntar mig").

Referens: docs/UTKASTKEDJAN-REFERENS-2026-10-16.md. Facit
(fixtures/utkastfacit_2026-10-16.json) är sju verkliga utkast ur Snajps
granskningskö efter körningarna 2026-10-15/16. Testet fäller varje ändring i
stilgrinden som skulle underkänna dem, och varje uppmjukning som skulle släppa
igenom de fel nattens körningar visade: slentrianöppningar, uppräkning av
sortimentet, mallorden, bolagsnamn i ämnesraden, du och ni om samma person,
fel förnamn i hälsningen. Facit ändras bara när Anton godkänt nya referenser.
"""

import json
from pathlib import Path

import pytest

from app.leads import stilkontroll as stil
from app.leads.halsning import fornamn, normalisera_utkast
from app.leads.tilltal import amne_utan_namn

FACIT = json.loads(
    (Path(__file__).parent / "fixtures" / "utkastfacit_2026-10-16.json").read_text(encoding="utf-8")
)
UTKAST = FACIT["utkast"]
#: Fynd som villkoren själva orsakar (lång villkorsmening, samma handling i
#: varje mejl med samma erbjudande, över 90 ord med pilotens text), och
#: Båtladans ord som själva står i skrivstilens exempel.
#: svara_sa_avslut: facit slutar med "Svara 'pilot' …", som Anton förbjöd
#: 2026-10-25 (docs/BESLUT.md). Facit gäller för allt annat tills ett nytt
#: facit med den nya formen är godkänt.
TILLATNA = {"lang_mening", "samma_uppmaning", "for_langt", "kopierat_exempel", "svara_sa_avslut"}


def _koder(text: str) -> set[str]:
    return {a.kod for a in stil.kontrollera(text).anmarkningar}


@pytest.mark.parametrize("u", UTKAST, ids=[u["bolag"] for u in UTKAST])
def test_facitutkastet_passerar_hela_grinden(u):
    assert _koder(u["brodtext"]) - TILLATNA == set()
    assert stil.erbjudande_fynd(u["brodtext"], villkor=u["villkor"], produkt=u["produkt"]) == []
    if u["amne"]:
        assert stil.amne_fynd(u["amne"], bolag=u["bolag"], produkt=u["produkt"]) == []


def test_facitutkasten_borjar_olika_och_delar_inga_fraser():
    texter = [u["brodtext"] for u in UTKAST]
    for i, t in enumerate(texter):
        andra = [*texter[:i], *texter[i + 1 :]]
        assert not {a.kod for a in stil.mot_andra(t, andra)} & {"samma_ingang", "samma_konstruktion", "samma_fras"}, (
            UTKAST[i]["bolag"]
        )
    amnen = [u["amne"] for u in UTKAST if u["amne"]]
    assert len({" ".join(a.lower().split()[:2]) for a in amnen}) == len(amnen)


@pytest.mark.parametrize(
    "ingang,kod",
    [
        ("Med ert breda utbud av fordon, utrustning och service för snöskotrar, motorcyklar och ATV uppstår många kundfrågor.", "slentrian_ingang"),
        ("När ni säljer snöskotrar, ATV och båtar till både privatpersoner och företag får ni många frågor.", "slentrian_ingang"),
        ("Att erbjuda service, reservdelar, tillbehör och verkstad är er vardag, och frågorna blir många.", "uppraknad_ingang"),
        ("Att hjälpa kunder att hitta rätt båt är ert löfte, men frågorna tar tid från det arbetet.", "mallord_i_ingangen"),
        ("Att bygga hållbara fasader kräver fullt fokus, inte på att hitta nästa kund.", "mallord_i_ingangen"),
    ],
)
def test_nattens_fel_falls(ingang, kod):
    facit = UTKAST[0]["brodtext"]
    stycken = facit.split("\n\n")
    stycken[1] = ingang
    assert kod in _koder("\n\n".join(stycken))


@pytest.mark.parametrize(
    "amne,bolag",
    [
        ("Åkes Motor och era kundfrågor", "Åkes Motor Aktiebolag"),
        ("Båtladan i Gästrikland och livet på sjön", "Båtladan i Gästrikland AB"),
        ("Kundfrågor för Powersport parts & marine Scandinavia", "Powersport parts & marine Scandinavia AB"),
    ],
)
def test_bolagsnamnet_lamnar_alltid_amnesraden(amne, bolag):
    assert stil.amne_fynd(amne, bolag=bolag, produkt=None)
    assert stil.amne_fynd(amne_utan_namn(amne, bolag), bolag=bolag, produkt=None) == []


def test_halsningen_bar_mottagarens_riktiga_fornamn():
    assert fornamn("Delsbo Magnus", "magnus@akesmotor.se") == "Magnus"
    assert fornamn("Scandinavia") is None
    assert fornamn("Polarhandlare Inget", "info@x.se") is None
    assert fornamn("Hising Arbetsledare", "info@x.se") is None
    rad = normalisera_utkast("Hej Brobergs,\n\nText.", kontakt="Brobergs", bolag="Brobergs Tobakshandel Aktiebolag")
    assert rad.startswith("Hej,\n")


def test_du_och_ni_om_samma_person_falls():
    named_ni = "Hej Per,\n\nNi bygger hus åt kommunen och nästa projekt får vänta.\n\nVår agent Iris hittar dem åt er.\n\nSvara ja så skickar vi dem."
    assert "ni_till_person" in _koder(named_ni)
    blandat = "Hej,\n\nDu bygger hus åt kommunen och nästa projekt får vänta.\n\nVår agent Iris hittar dem åt er.\n\nSvara ja så skickar vi dem."
    assert "du_och_ni" in _koder(blandat)
