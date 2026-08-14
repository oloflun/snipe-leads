"""Delta-humaniseringens mekanik.

test_split_is_lossless är det bärande testet. Så länge det håller kan en
felaktig meningsgräns bara göra en delta-enhet större eller mindre — den kan
aldrig tappa eller duplicera tecken i ett mejl som går ut i kundens namn.
"""

from __future__ import annotations

import pytest

from app.leads.text_delta import (
    Segment,
    SegmentShapeError,
    changed_segments,
    parse_humanized_segments,
    sentences,
    split_sentences,
    splice,
)

CORPUS = [
    "Hej Anna. Vi hjälper e-handlare med support. Har du 15 minuter?",
    "Vi sparar t.ex. 3,5 timmar per vecka. Det motsvarar ca 12 000 kr.",
    "Första stycket här.\n\nAndra stycket här. Och en till mening.",
    "Ett enda påstående utan avslutande skiljetecken",
    "Frågor? Ja! Absolut... Och sedan mer text.",
    "Vi växte 1 200 procent. Nej, bl.a. inte riktigt.",
    "",
    "   ",
    "Kontakta anna@snajp.se. Ring 0771-123456 vid behov.",
]


@pytest.mark.parametrize("text", CORPUS)
def test_split_is_lossless(text):
    """Offsetsen måste TÄCKA hela texten, utan luckor och utan överlapp."""
    spans = split_sentences(text)
    assert "".join(text[a:b] for a, b in spans) == text


@pytest.mark.parametrize("text", CORPUS)
def test_spans_are_ordered_and_non_overlapping(text):
    spans = split_sentences(text)
    for (_, end), (start, _) in zip(spans, spans[1:]):
        assert end == start, f"lucka eller överlapp vid {end}/{start}"


def test_swedish_abbreviations_do_not_split():
    assert len(sentences("Vi sparar t.ex. tre timmar.")) == 1
    assert len(sentences("Kostnaden är ca 500 kr per månad.")) == 1
    assert len(sentences("Det gäller bl.a. returer och frakt.")) == 1


def test_decimals_do_not_split():
    assert len(sentences("Vi växte 3.5 procent förra året.")) == 1


def test_real_boundaries_do_split():
    assert len(sentences("Hej Anna. Vi hjälper dig.")) == 2
    assert len(sentences("Går det bra? Hör av dig.")) == 2


def test_blank_line_is_a_hard_boundary():
    assert len(sentences("Rad ett\n\nRad två")) == 2


# -- Diffen ----------------------------------------------------------------


def test_only_changed_sentences_are_selected():
    before = "Hej Anna. Vi ökade med 63 procent. Hör av dig."
    after = "Hej Anna. Vi ökade svarstakten. Hör av dig."
    changed = changed_segments(before, after)
    assert len(changed) == 1
    assert "svarstakten" in changed[0].text


def test_untouched_text_yields_no_segments():
    text = "Hej Anna. Vi hjälper dig. Hör av dig."
    assert changed_segments(text, text) == ()


def test_inserted_sentence_is_selected():
    before = "Hej Anna. Hör av dig."
    after = "Hej Anna. Vi hjälper e-handlare. Hör av dig."
    changed = changed_segments(before, after)
    assert len(changed) == 1
    assert "e-handlare" in changed[0].text


# -- Splice ----------------------------------------------------------------


def test_splice_right_to_left_preserves_untouched_text():
    """Två ersättningar med olika längd. Görs de vänster till höger blir den
    andra offseten ogiltig och texten tyst sönderklippt."""
    text = "Ett. Två. Tre."
    out = splice(text, {0: "Ett mycket längre segment.", 2: "Tre."})
    assert "Ett mycket längre segment." in out
    assert "Två." in out
    assert out.endswith("Tre.")


def test_splice_keeps_separating_whitespace():
    text = "Hej Anna. Vi hjälper dig."
    out = splice(text, {0: "Hej Anna!"})
    assert out == "Hej Anna! Vi hjälper dig."


def test_splice_with_empty_replacement_merges_cleanly():
    """Humanizern kan slå ihop två meningar genom att returnera tom sträng
    för den ena och den sammanslagna texten för den andra."""
    text = "Ett. Två. Tre."
    out = splice(text, {0: "", 1: "Ett och två."})
    assert "Ett och två." in out
    assert out.strip().endswith("Tre.")


def test_splice_rejects_unknown_index():
    with pytest.raises(SegmentShapeError):
        splice("Ett. Två.", {99: "x"})


# -- Kontraktet ------------------------------------------------------------


def _expected():
    return [Segment(index=1, span=(5, 10), text="Två. "), Segment(index=2, span=(10, 14), text="Tre.")]


def test_matching_index_set_parses():
    output = {"segments": [{"index": 1, "text": "Två!"}, {"index": 2, "text": "Tre!"}]}
    assert parse_humanized_segments(output, _expected()) == {1: "Två!", 2: "Tre!"}


def test_wrong_index_set_raises():
    output = {"segments": [{"index": 1, "text": "Två!"}]}
    with pytest.raises(SegmentShapeError):
        parse_humanized_segments(output, _expected())


def test_extra_index_raises():
    output = {"segments": [{"index": i, "text": "x"} for i in (1, 2, 3)]}
    with pytest.raises(SegmentShapeError):
        parse_humanized_segments(output, _expected())


def test_duplicate_index_raises():
    output = {"segments": [{"index": 1, "text": "a"}, {"index": 1, "text": "b"}, {"index": 2, "text": "c"}]}
    with pytest.raises(SegmentShapeError):
        parse_humanized_segments(output, _expected())


def test_missing_segments_key_raises():
    with pytest.raises(SegmentShapeError):
        parse_humanized_segments({"final_body": "..."}, _expected())


def test_wrong_types_raise():
    with pytest.raises(SegmentShapeError):
        parse_humanized_segments({"segments": [{"index": "1", "text": "a"}, {"index": 2, "text": "b"}]}, _expected())
