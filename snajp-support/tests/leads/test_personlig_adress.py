"""Vilken mottagaradress som är personlig (2026-11-17).

`Prospect.epost_ar_personlig` avgör sidfoten (utskicksfot.bygg_fot) och
policylänkskravet (send_guard regel 2 och 4). Förut räknades en adress som
personlig bara om lokaldelen bar en punkt eller ett bindestreck, så att
anna@ och andersson@ fick den korta foten utan art. 14-information. En
förnamns- eller efternamnsadress är en personuppgift: nu är en adress
personlig om lokaldelen INTE är en känd funktionsadress.

Det gamla avgörandet lever kvar som `epost_bar_namnform` för det som inte är
sidfot: poängsättningens kontaktväg och rollkopplingsflaggan.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.leads.scheduler import _ar_personlig
from app.leads.send_guard import (
    BLOCKERA,
    SKICKA,
    Avsandare,
    Leveransutfall,
    TenantHistorik,
    Utskick,
    check_send_guard,
)
from app.leads.sources.base import FUNKTIONSADRESSER, Prospect
from app.leads.utskicksfot import avregistreringslank, bygg_fot


def _personlig(adress: str) -> bool:
    return Prospect(company_name="X AB", contact_email=adress).epost_ar_personlig


@pytest.mark.parametrize(
    "adress",
    [
        "anna@bolaget.se",  # förnamn
        "andersson@bolaget.se",  # efternamn
        "anna.andersson@bolaget.se",
        "anna-andersson@bolaget.se",
        "aa@bolaget.se",  # initialer
        "christoffer@bolaget.se",
    ],
)
def test_namnadresser_ar_personliga(adress):
    assert _personlig(adress) is True


@pytest.mark.parametrize(
    "adress",
    [
        "info@bolaget.se",
        "kontakt@bolaget.se",
        "order@bolaget.se",
        "kundtjänst@bolaget.se",
        "hello@bolaget.se",
        "kundservice@bolaget.se",
        "admin@bolaget.se",
        "office@bolaget.se",
        "kontoret@bolaget.se",
        "butik@bolaget.se",
        "butiken@bolaget.se",
        "shop@bolaget.se",
        "team@bolaget.se",
        "marknad@bolaget.se",
        "marketing@bolaget.se",
        "press@bolaget.se",
        "noreply@bolaget.se",
        "no-reply@bolaget.se",
        "verkstad@bolaget.se",  # avdelningsord ur discovery.AVDELNINGSORD
    ],
)
def test_funktionsadresser_ar_inte_personliga(adress):
    assert _personlig(adress) is False


@pytest.mark.parametrize("adress", ["vd@bolaget.se", "ceo@bolaget.se"])
def test_vd_och_ceo_ar_personliga(adress):
    """En roll som bara en person har pekar ut den personen: full fot."""
    assert _personlig(adress) is True


@pytest.mark.parametrize("adress", [" INFO@Bolaget.se ", "Kontakt@bolaget.se", "  Hello@x.se"])
def test_skiftlage_och_blanksteg_spelar_ingen_roll_for_funktionsadress(adress):
    assert _personlig(adress) is False


@pytest.mark.parametrize("adress", [" ANNA@Bolaget.se ", "Andersson@bolaget.se "])
def test_skiftlage_och_blanksteg_spelar_ingen_roll_for_namnadress(adress):
    assert _personlig(adress) is True


@pytest.mark.parametrize("adress", [None, "", "inte-en-adress"])
def test_ingen_adress_ar_inte_personlig(adress):
    assert _personlig(adress) is False


def test_listan_bar_beslutets_adresser():
    """Beslutet 2026-10-24 (kort fot till info@ och kontakt@) gäller oförändrat."""
    assert {"info", "kontakt"} <= FUNKTIONSADRESSER


def test_scheduler_dommer_som_prospektet():
    """send_guard får sin flagga ur scheduler._ar_personlig."""
    assert _ar_personlig("anna@bolaget.se") is True
    assert _ar_personlig("info@bolaget.se") is False


# -- Den gamla namnformen, för det som inte är sidfot ------------------------


@pytest.mark.parametrize(
    "adress,namnform",
    [
        ("anna.andersson@bolaget.se", True),
        ("anna-andersson@bolaget.se", True),
        ("anna@bolaget.se", False),
        ("info@bolaget.se", False),
    ],
)
def test_namnformen_ar_oforandrad(adress, namnform):
    assert Prospect(company_name="X AB", contact_email=adress).epost_bar_namnform is namnform


def test_poangen_for_forenamnsadress_ar_oforandrad():
    """Poängsättningens kontaktväg (urvalets rangordning) läser namnformen,
    inte sidfotsavgörandet: anna@ rankas som förut."""
    from app.leads.scoring import TRAFF, score_prospect

    p = Prospect(company_name="A AB", postnr="903 27", contact_email="anna@a.example")
    kontakt = next(k for k in score_prospect(p, {"geo": ["umea"]}).breakdown if k.nyckel == "kontakt")
    assert kontakt.utfall == TRAFF


def test_rollkopplingen_for_forenamnsadress_ar_oforandrad():
    from app.leads.rollkoppling import rollkoppling_oklar

    assert rollkoppling_oklar({"contact_email": "anna@bolaget.se"}) is False
    assert rollkoppling_oklar({"contact_email": "anna.lind@bolaget.se"}) is True


# -- Foten och spärrarna -----------------------------------------------------

AVSANDARE = Avsandare(foretagsnamn="Livrustning AB", orgnr="556824-9022", postadress="Storgatan 1, 411 38 Göteborg")
LANK = avregistreringslank("https://snajp.se", "a" * 32)
POLICY = "https://livrustning.example/integritetspolicy"


def _fot(adress: str, *, policy_url: str = POLICY) -> str:
    """Foten så som leads_tools.lagstadgad_fot bygger den."""
    return bygg_fot(
        foretagsnamn=AVSANDARE.foretagsnamn,
        orgnr=AVSANDARE.orgnr,
        postadress=AVSANDARE.postadress,
        lank=LANK,
        policy_url=policy_url,
        personlig=_personlig(adress),
    )


def _dom(adress: str, brodtext: str):
    """Spärrarna så som scheduler._kor_send_guard kör dem."""
    return check_send_guard(
        avsandare=AVSANDARE,
        utskick=Utskick(
            mottagare=adress,
            amne="En fråga",
            brodtext=brodtext,
            foretagsnyckel="bolaget.se",
            personlig_adress=_ar_personlig(adress),
        ),
        historik=TenantHistorik(
            skickade_totalt=50,
            skickade_idag=0,
            tenant_alder_dagar=400,
            storsta_dagsvolym=100,
            leverans=Leveransutfall(skickade=0, studsade=0, klagomal=0),
            senaste_kontakt_med_foretaget=None,
            suppressions=frozenset(),
            tidigare_kontaktade=frozenset(),
            egna_kunder=frozenset(),
        ),
        nu=datetime(2026, 8, 25, 8, 0, tzinfo=timezone.utc),  # tisdag 10:00
    )


TEXT = "Hej Anna,\n\nEtt kort och relevant erbjudande.\n\n"


def test_forenamnsadress_far_art14_foten_med_policylank():
    fot = _fot("anna@bolaget.se")
    assert "personuppgiftsansvarig" in fot and "hämtad" in fot and POLICY in fot
    assert _dom("anna@bolaget.se", TEXT + fot).atgard == SKICKA


def test_forenamnsadress_med_kort_fot_blockeras():
    kort = bygg_fot(
        foretagsnamn=AVSANDARE.foretagsnamn, orgnr=AVSANDARE.orgnr,
        postadress=AVSANDARE.postadress, lank=LANK, policy_url=POLICY, personlig=False,
    )
    beslut = _dom("anna@bolaget.se", TEXT + kort)
    assert beslut.atgard == BLOCKERA
    assert beslut.regel == "2_avregistrering"


def test_forenamnsadress_utan_policy_url_blockeras_med_besked():
    """Kund utan policy_url i kundregistret: foten byggs utan policyrad och
    regel 2 stoppar med beskedet att fylla i policy_url."""
    beslut = _dom("andersson@bolaget.se", TEXT + _fot("andersson@bolaget.se", policy_url=""))
    assert beslut.atgard == BLOCKERA
    assert beslut.regel == "2_avregistrering"
    assert "policy_url" in beslut.skal


@pytest.mark.parametrize("adress", ["info@bolaget.se", "kontakt@bolaget.se"])
def test_kort_fot_till_funktionsadress_galler_fortfarande(adress):
    fot = _fot(adress, policy_url="")
    assert "personuppgiftsansvarig" not in fot and "hämtad" not in fot
    assert _dom(adress, TEXT + fot).atgard == SKICKA
