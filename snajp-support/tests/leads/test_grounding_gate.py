"""Grundningsgrinden — rena funktioner, inget LLM.

Testet som är viktigast att INTE ta bort är
test_qualifier_drift_is_deliberately_not_caught: det gör grindens tak
explicit, så att någon som senare "fixar" det ser att det var ett beslut och
inte en glömska.
"""

from __future__ import annotations

import pytest

from app.leads.grounding_gate import (
    build_permitted_facts,
    check_grounding,
    normalize_number,
)


def _facts(**overrides):
    base = dict(
        context_pack="Snajp avlastar kundtjänst. Vi minskade svarstiden med 30 procent.",
        research_evidence=["Fri retur inom 30 dagar", "Öppet 08-17"],
        offer_summary="Pilot i 4 veckor för 12 000 kr.",
        brief="Kallt mejl till e-handlare.",
        tenant_name="Snajp",
        company_name="Sportamore",
    )
    base.update(overrides)
    return build_permitted_facts(**base)


# -- Normalisering ---------------------------------------------------------


@pytest.mark.parametrize(
    "raw,unit,expected",
    [
        ("30", "%", "30%"),
        ("30", "procent", "30%"),
        ("30", "pct", "30%"),
        ("30.0", "%", "30%"),
        ("3,5", None, "3.5"),
        ("1 200", "kr", "1200SEK"),
        ("1 200", None, "1200"),      # NBSP som tusenavskiljare
        ("1.200", None, "1200"),           # punkt som tusenavskiljare
        ("12 000", "kronor", "12000SEK"),
        ("99", "EUR", "99EUR"),
    ],
)
def test_number_normalisation_table(raw, unit, expected):
    assert normalize_number(raw, unit) == expected


def test_decimal_point_is_not_a_thousand_separator():
    """3.5 är tre och en halv, inte trettiofem hundra."""
    assert normalize_number("3.5", None) == "3.5"


# -- Kärnfallet: den påhittade siffran ------------------------------------


def test_invented_percentage_is_unsupported():
    """Regressionstestet för incidenten 2026-08-10."""
    verdict = check_grounding(
        "Vi har hjälpt liknande bolag minska återkommande frågor med 63 procent.",
        _facts(),
    )
    assert not verdict.ok
    assert any(c.normalized == "63%" for c in verdict.unsupported)


def test_sourced_percentage_is_supported():
    verdict = check_grounding("Svarstiden sjönk med 30 procent.", _facts())
    assert verdict.ok, verdict.as_report()


def test_percent_sign_matches_the_word_procent_in_the_source():
    """Källan säger 'procent', mejlet skriver '30 %'. Samma påstående."""
    assert check_grounding("Svarstiden sjönk med 30 %.", _facts()).ok


def test_amount_from_the_offer_is_supported():
    assert check_grounding("Piloten kostar 12 000 kr.", _facts()).ok


def test_invented_amount_is_unsupported():
    assert not check_grounding("Piloten kostar 47 500 kr.", _facts()).ok


# -- Undantagen som gör grinden användbar ---------------------------------


def test_meeting_ask_minutes_are_exempt_only_in_a_question():
    assert check_grounding("Har du 15 minuter nästa vecka?", _facts()).ok


def test_minutes_in_a_statement_are_still_checked():
    """Frågevillkoret är det som gör undantaget säkert."""
    verdict = check_grounding("Vi sparar 15 minuter per ärende.", _facts())
    assert not verdict.ok
    assert any(c.raw.startswith("15") for c in verdict.unsupported)


def test_digits_in_emails_urls_and_phone_numbers_are_ignored():
    text = (
        "Hör av dig till anna99@snajp.se eller ring 0771-123456. "
        "Mer på https://snajp.se/case-2024."
    )
    assert check_grounding(text, _facts()).ok, check_grounding(text, _facts()).as_report()


# -- Namngivna kunder ------------------------------------------------------


def test_invented_customer_in_an_enumerated_frame_is_caught():
    verdict = check_grounding("Vi har hjälpt Zalando med samma sak.", _facts())
    assert not verdict.ok
    assert any(c.kind == "named_customer" and c.raw == "Zalando" for c in verdict.unsupported)


def test_customer_present_in_the_sources_is_allowed():
    facts = _facts(research_evidence=["Vi arbetar redan med Livrustning AB"])
    assert check_grounding("Vi arbetar med Livrustning AB sedan i våras.", facts).ok


def test_named_customer_only_in_enumerated_frames():
    """ponytail-taket, medvetet: utanför de uppräknade ramarna kollas inget.

    Notera att meningen är superlativfri med flit — 'Sveriges största' hade
    fällts av superlativkontrollen i stället, och testet hade då passerat av
    fel skäl utan att säga något om ramarna."""
    assert check_grounding("Ett stort svenskt modeföretag valde oss.", _facts()).ok


def test_superlative_matches_across_swedish_inflection():
    """'största' innehåller 'störst' — delsträngsmatchningen är avsiktlig,
    se kommentaren vid _SUPERLATIVES."""
    assert not check_grounding("Vi är Sveriges största aktör.", _facts()).ok
    facts = _facts(offer_summary="Snajp är den största aktören på marknaden.")
    assert check_grounding("Vi är störst.", facts).ok


# -- Superlativ ------------------------------------------------------------


def test_superlative_requires_the_same_word_in_the_sources():
    assert not check_grounding("Vi är marknadsledande på svensk support.", _facts()).ok


def test_superlative_present_in_the_sources_is_allowed():
    facts = _facts(offer_summary="Snajp är marknadsledande på svensk kundtjänst-AI.")
    assert check_grounding("Vi är marknadsledande.", facts).ok


# -- Taken, explicit ------------------------------------------------------


def test_qualifier_drift_is_deliberately_not_caught():
    """MEDVETET TAK, inte en bugg.

    Källan säger '30 procent'; mejlet skriver 'över 30 procent'. Grinden
    kontrollerar MAGNITUDEN, inte kvalificeraren, eftersom att fånga driften
    kräver riktningsförståelse av källmeningen. Hanteras i prompten
    (agent-core/overlays/leads-grounding-repair.md).

    Ändrar du det här: mät falsklarmsfrekvensen på riktig output först.
    """
    assert check_grounding("Svarstiden sjönk med över 30 procent.", _facts()).ok


def test_spelled_out_numerals_are_deliberately_not_caught():
    """'hälften' är ett påstående, men svensk numeralparsning är ett kaninhål
    och frekvensen i ett 120-ordsmejl är låg."""
    assert check_grounding("Vi halverade antalet ärenden.", _facts()).ok


# -- Rapporten -------------------------------------------------------------


def test_report_names_the_actual_claims():
    """Reparationsprompten får den här listan — är den vag kan modellen inte
    laga rätt mening."""
    verdict = check_grounding("Vi ökade med 88 procent och är bäst.", _facts())
    report = verdict.as_report()
    assert any("88" in line for line in report)
    assert any("bäst" in line for line in report)


def test_permitted_facts_records_its_sources():
    facts = _facts()
    assert "context_pack" in facts.source_labels
    assert any("research_evidence" in label for label in facts.source_labels)


def test_empty_evidence_still_permits_context_pack_numbers():
    """Utan research (t.ex. outreach utan föregående Fas B) ska grinden inte
    brinna på siffror som står i kontextpaketet."""
    facts = _facts(research_evidence=[])
    assert check_grounding("Svarstiden sjönk med 30 procent.", facts).ok
