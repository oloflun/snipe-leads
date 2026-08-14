"""Underlaget måste höra till ärendets fack — annars lämnas ärendet över.

Bakgrund: en kund skrev "vår hjärtstartare fungerar inte". Triagen klassade rätt
(teknisk_support), men nyckelordssökningen rankade bolagets kursutbud högst
eftersom den artikeln delade flest ord med meddelandet. Agenten svarade då med
en beskrivning av kursutbudet på ett larm om trasig utrustning — och gjorde det
utan att eskalera, eftersom grundningsregeln bara krävde att NÅGON träff fanns.

Kravet är därför "underlag i rätt fack", inte "någon träff alls".
"""

import pytest

from app.simulation.sim_agent import article_in_category


def _article(title: str, category: str) -> dict:
    return {"id": title, "title": title, "content": "x" * 40, "category": category, "similarity": 0.5}


def test_returns_none_when_no_hit_matches_the_category():
    """Det ursprungliga felet: bara artiklar ur andra fack."""
    hits = [
        _article("Första hjälpen och HLR med hjärtstartare", "utbildning"),
        _article("Hjärtstartare för hem, företag och förening", "ovrigt"),
        _article("Om Livrustning AB", "ovrigt"),
    ]
    assert article_in_category(hits, "teknisk_support") is None


def test_picks_the_matching_article_even_when_ranked_lower():
    """Sökordningen får inte avgöra — facket gör det."""
    hits = [
        _article("Om Livrustning AB", "ovrigt"),
        _article("Felsökning och larm", "teknisk_support"),
    ]
    chosen = article_in_category(hits, "teknisk_support")
    assert chosen is not None
    assert chosen["title"] == "Felsökning och larm"


def test_general_articles_never_answer_specific_questions():
    """En 'ovrigt'-artikel duger aldrig som svar på garanti eller reklamation."""
    hits = [_article("Om bolaget", "ovrigt")]
    assert article_in_category(hits, "garanti") is None
    assert article_in_category(hits, "retur_reklamation") is None
    assert article_in_category(hits, "betalning") is None
    # ... men den besvarar en allmän fråga.
    assert article_in_category(hits, "ovrigt") is not None


def test_warranty_and_returns_may_answer_each_other():
    """Garanti och reklamation överlappar i sak och får dela underlag."""
    warranty = [_article("Garanti — vilken gäller när", "garanti")]
    assert article_in_category(warranty, "retur_reklamation") is not None

    returns = [_article("Retur och reklamation", "retur_reklamation")]
    assert article_in_category(returns, "garanti") is not None


def test_empty_hits_give_none():
    assert article_in_category([], "leverans") is None


@pytest.mark.parametrize(
    "category", ["teknisk_support", "leverans", "betalning", "utbildning", "orderstatus"]
)
def test_each_category_requires_its_own_grounding(category):
    """Ingen kategori får tyst falla tillbaka på en allmän artikel."""
    assert article_in_category([_article("Allmänt", "ovrigt")], category) is None
