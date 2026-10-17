"""INV-LEADS-UTKAST-001: facit för Iris första mejl (Anton 2026-10-12: "alla
utkast är perfekta nu, lås in detta").

Tolv verkliga utkast ur Snajps granskningskö är facit
(fixtures/utkastfacit_2026-10-12.json). Testet fäller varje ändring i
stilgrinden eller skrivreglerna som skulle underkänna ett facitutkast, och
varje uppmjukning som skulle släppa igenom de fel Anton pekade ut: en allmän
ingång med etikett ("som ni gör"), registerfakta, antaganden, tappat
erbjudande. Ändras facit ska det vara för att Anton godkänt nya referenser.

Reviderat 2026-10-15 (Anton): Båtladan ("Hej Christoffer, Hur hinner du med att
ge personlig rådgivning …") är det bästa utkastet och nivån som gäller. Fem
facitutkast som började "Med er/ert/era …" eller räknade upp vad bolaget säljer
ligger nu under "ersatta" och ska fällas av grinden. Ämnesraderna är borttagna
ur facit: alla bar bolagets namn, som Anton förbjöd samma dag.
"""

import json
from pathlib import Path

import pytest

from app.leads import stilkontroll as stil

FACIT = json.loads(
    (Path(__file__).parent / "fixtures" / "utkastfacit_2026-10-12.json").read_text(encoding="utf-8")
)
UTKAST = FACIT["utkast"]
ERSATTA = FACIT["ersatta"]
#: Fynd som bara flaggar för granskning och som villkoren själva orsakar
#: (villkorens mening är ofta över 25 ord; handlingen är densamma i varje
#: gratisprov-mejl). Allt annat ska vara noll på ett facitutkast.
TILLATNA = {"lang_mening", "samma_uppmaning", "for_langt", "kopierat_exempel"}
# kopierat_exempel: facitutkasten ÄR skrivstilens exempel (Båtladan, Eketräs,
# ÅW står i tabellen fel/rätt), så de lånar ord ur sig själva.


def _koder(text: str) -> set[str]:
    return {a.kod for a in stil.kontrollera(text).anmarkningar}


@pytest.mark.parametrize("u", UTKAST, ids=[u["bolag"] for u in UTKAST])
def test_facitutkastet_passerar_stilgrinden(u):
    assert _koder(u["brodtext"]) - TILLATNA == set()
    assert stil.erbjudande_fynd(u["brodtext"], villkor=u["villkor"], produkt=u["produkt"]) == []


@pytest.mark.parametrize("u", UTKAST, ids=[u["bolag"] for u in UTKAST])
def test_facitutkastet_har_strukturen(u):
    """Ingången till dem, erbjudandet och handlingen (två till fyra stycken;
    erbjudande och handling får dela stycke). 50–110 ord, och ingången i
    andra person utan "man"."""
    stycken = [s for s in u["brodtext"].split("\n\n") if s.strip() and not s.strip().lower().startswith("hej")]
    assert 2 <= len(stycken) <= 4, stycken
    ingang = stycken[0].casefold()
    assert any(o in ingang for o in (" ni ", " er ", " era ", " ert ", " du ", " din ", "ni ", "er ", "era ", "ert ")), ingang
    assert " man " not in f" {ingang} "
    ord_ = sum(len(s.split()) for s in stycken)
    assert 50 <= ord_ <= 110, ord_
    assert not stycken[-1].rstrip().endswith("?"), "mejlet slutar med en handling, inte en fråga"


def test_facitutkasten_borjar_olika():
    """Inga två facitutkast har samma ingång eller samma konstruktion."""
    texter = [u["brodtext"] for u in UTKAST]
    for i, t in enumerate(texter):
        fynd = {a.kod for a in stil.mot_andra(t, [*texter[:i], *texter[i + 1 :]])}
        assert "samma_ingang" not in fynd, UTKAST[i]["bolag"]
    former = {" ".join(stil.ingang(t).split()[:2]) for t in texter}
    assert len(former) == len(texter), former


@pytest.mark.parametrize(
    "ingang",
    [
        "För företag som ert, som säljer till andra företag, är det ofta en utmaning att hitta nya kunder.",
        "När man arbetar med markarbeten och grundläggningar, som ni gör, kommer många förfrågningar.",
        "Med 20-25 anställda och fem platschefer vet jag att nästa kund får vänta.",
        "Den som utför markarbeten åt både företag och privatpersoner hinner sällan leta nästa kund.",
    ],
)
def test_de_utpekade_felen_falls_fortfarande(ingang):
    facit = UTKAST[0]["brodtext"]
    stycken = facit.split("\n\n")
    stycken[1] = ingang
    assert _koder("\n\n".join(stycken)) & {"mall_ingang", "generell_ingang", "registerfakta_i_ingangen", "antagande_om_dem"}


@pytest.mark.parametrize("u", ERSATTA, ids=[u["bolag"] for u in ERSATTA])
def test_de_ersatta_falls_nu(u):
    """Antons granskning 2026-10-15: slentrianöppningen, uppräkningen och
    agenten som namnges först efter löftet fälls."""
    koder = _koder(u["brodtext"]) | {
        a.kod for a in stil.erbjudande_fynd(u["brodtext"], villkor=u["villkor"], produkt=u["produkt"])
    }
    assert koder & {"slentrian_ingang", "uppraknad_ingang", "agent_efter_loftet", "mallord_i_ingangen"}, u["bolag"]


@pytest.mark.parametrize(
    "amne,bolag,produkt",
    [
        ("Åkes Motor och era kundfrågor", "Åkes Motor Aktiebolag", "Supportagenten"),
        ("Pilot för Iris, Törnqvist Etc.", "Törnqvist Etc. AB", "Iris, leadsagenten"),
        ("Båtladan i Gästrikland och livet på sjön", "Båtladan i Gästrikland AB", "Supportagenten"),
        ("Era kundfrågor, Sven-Åke Lindblads", "Sven-Åke Lindblads Aktiebolag", "Supportagenten"),
        ("Supportagenten för Yngvessons Maskin", "Yngvessons Maskin Aktiebolag", "Supportagenten"),
    ],
)
def test_amnesraderna_anton_pekade_ut_falls(amne, bolag, produkt):
    assert {a.kod for a in stil.amne_fynd(amne, bolag=bolag, produkt=produkt)} & {"namn_i_amnet", "produkt_i_amnet"}


def test_bra_amnesrad_passerar():
    assert stil.amne_fynd("Personlig service när frågorna blir många", bolag="Båtladan i Gästrikland AB",
                          produkt="Supportagenten") == []
