"""Seedningen ska fylla VARJE inkorg, inte sex slumpade.

Beställningen: "det ska direkt autogenereras flera olika inkommande demo mails
till alla inkorgar som man som kund får en känsla av hur det fungerar".

Det gamla urvalet tog sex ärenden ur en pool på tjugofem utan hänsyn till fack.
Utfallet var mätbart: två eller tre av de åtta facken blev regelmässigt tomma,
och en kund som klickar sig runt bland flikarna hittar då en tom inkorg och
drar slutsatsen att sorteringen inte fungerar.
"""

import random

import pytest

from app.config import CATEGORIES
from app.email_pipeline.connectors.mock import ESKALERANDE, build_mock_emails


def _kategorier(mail) -> set[str]:
    """Facken urvalet TÄNKTE sig, avlästa ur poolen via ämnesraden.

    Klassificeringen görs av agenten och prövas i pipelinetesterna. Här gäller
    frågan urvalet: fick varje fack ett ärende att skicka in?
    """
    from app.email_pipeline.connectors.mock import BESVARBARA

    per_amne = {m["amne"]: m["kategori"] for m in BESVARBARA + ESKALERANDE}
    return {per_amne[m.subject] for m in mail}


@pytest.mark.parametrize("fro", range(12))
def test_varje_fack_far_ett_arende(fro: int):
    """Tolv olika slumpfrön, samma krav. Ett urval som ibland lämnar ett fack
    tomt är ett urval som gör det i drift också."""
    mail = build_mock_emails(slump=random.Random(fro))
    assert _kategorier(mail) == set(CATEGORIES)


@pytest.mark.parametrize("fro", range(12))
def test_minst_ett_arende_ar_eskalerande(fro: int):
    """En demo där agenten svarar på allt visar en agent som gissar.

    Spärrarna är en del av produkten, och de syns bara om något faktiskt når
    en människa.
    """
    mail = build_mock_emails(slump=random.Random(fro))
    eskalerande_amnen = {m["amne"] for m in ESKALERANDE}
    assert any(m.subject in eskalerande_amnen for m in mail)


def test_urvalet_roterar_mellan_klick():
    """Två klick i rad ska inte ge exakt samma inkorg."""
    forsta = [m.subject for m in build_mock_emails(slump=random.Random(1))]
    andra = [m.subject for m in build_mock_emails(slump=random.Random(2))]
    assert forsta != andra
