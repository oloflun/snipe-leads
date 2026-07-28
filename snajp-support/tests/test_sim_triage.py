"""Triage för hjärtstartarbranschen: rätt fack och ärlig konfidens."""

import pytest

from app.simulation.sim_triage import classify


@pytest.mark.parametrize(
    "subject,body,expected",
    [
        ("Hjärtstartaren piper", "Statusindikatorn visar rött kryss och den piper.", "teknisk_support"),
        ("Självtest misslyckas", "Felkod E-04 visas i displayen varje natt.", "teknisk_support"),
        ("Garantifråga", "Täcks batteribyte av garantin? Vi köpte den för tre år sedan.", "garanti"),
        ("Var är leveransen?", "Spårningen har inte uppdaterats på fyra dagar.", "leverans"),
        ("HLR-utbildning", "Vi vill boka en kurs i hjärt-lungräddning för 18 anställda.", "utbildning"),
        ("Hur använder man den?", "Hur gör man när man ska använda hjärtstartaren?", "utbildning"),
        ("Reklamation", "Enheten kom fram trasig, vi vill reklamera den.", "retur_reklamation"),
        ("Faktura saknar referens", "Kan ni skicka en ny faktura med referens INK-2291?", "betalning"),
        ("Orderbekräftelse", "Har min beställning gått igenom? Fick ingen bekräftelse.", "orderstatus"),
        ("Öppettider", "Har ni öppet på midsommarafton?", "ovrigt"),
    ],
)
def test_classifies_industry_cases(subject, body, expected):
    assert classify(subject, body)["category"] == expected


def test_scoring_beats_first_match_ordering():
    """Flera fack nämns — leverans ska vinna över teknik och orderstatus.

    Med "första träffen vinner" hade elektrod-ordet avgjort och gett fel fack.
    """
    result = classify(
        "Leveransen av elektroder är försenad",
        "Vi beställde elektroder till vår hjärtstartare men paketet har inte kommit.",
    )
    assert result["category"] == "leverans"


def test_confidence_reflects_signal_strength():
    tydligt = classify("Garantivillkor", "Vad omfattar garantin och hur lång är garantitiden?")
    vagt = classify("Fråga", "Hej, undrar en sak.")
    assert tydligt["confidence"] > 0.7
    assert vagt["confidence"] <= 0.4
    assert vagt["category"] == "ovrigt"


def test_low_confidence_blocks_autosvar():
    """Konfidensen måste understiga autosvarströskeln (0.75) för svaga signaler."""
    assert classify("", "Hej, undrar en sak.")["confidence"] < 0.75


@pytest.mark.parametrize(
    "body",
    [
        "Jag kräver pengarna tillbaka omgående, annars kopplar jag in vår jurist.",
        "Vi vill radera samtliga personuppgifter enligt GDPR.",
        "Hjärtstartaren användes vid en incident på arbetsplatsen i går.",
    ],
)
def test_sensitive_cases_escalate(body):
    result = classify("", body)
    assert result["escalate"] is True
    assert result["escalation_reason"]


def test_angry_customer_escalates_on_sentiment():
    result = classify("Usel service", "Helt oacceptabelt!! Ingen har svarat på en vecka.")
    assert result["sentiment"] < 0.3
    assert result["escalate"] is True


def test_reasoning_names_the_runner_up():
    result = classify("Garantifråga om leverans", "Gäller garantin och när kommer paketet?")
    assert "Garanti" in result["reasoning"] or "Leverans" in result["reasoning"]
