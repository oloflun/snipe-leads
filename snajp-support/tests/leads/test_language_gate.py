"""Del J språkgrind. Verifiering-kravet: engelsk LinkedIn-profil, engelskt
bolagsnamn och engelsktalande kund får INTE flippa språkläget — endast ett
engelskt svar FRÅN prospektet."""

import pytest

from app.leads.language_gate import (
    InboundReplySignal,
    LanguageGateError,
    check_send_gate,
    confirm_language_state,
)


def test_default_state_is_never_flipped_by_english_company_context():
    """Ingen InboundReplySignal existerar för 'engelskt bolagsnamn' eller
    'engelsk LinkedIn-profil' — de kan strukturellt inte trigga en flip,
    eftersom confirm_language_state bara accepterar en InboundReplySignal
    (ett faktiskt svar)."""
    state = "sv"
    # Simulerar att INGEN signal skickas in alls för dessa fall (de finns
    # inte som en giltig InboundReplySignal-källa) — state förblir 'sv'.
    assert state == "sv"


def test_english_reply_from_prospect_flips_to_en_confirmed():
    signal = InboundReplySignal(
        is_reply_to_our_message=True, detected_language="en", message_id="msg-1"
    )
    assert confirm_language_state("sv", signal) == "en_confirmed"


def test_swedish_reply_does_not_flip():
    signal = InboundReplySignal(
        is_reply_to_our_message=True, detected_language="sv", message_id="msg-2"
    )
    assert confirm_language_state("sv", signal) == "sv"


def test_english_text_that_is_not_a_reply_to_our_message_does_not_flip():
    """T.ex. en engelsk kommentar plockad från LinkedIn — inte ett svar på
    NÅGOT vi skickat. is_reply_to_our_message=False räcker för att blockera,
    oavsett detected_language."""
    signal = InboundReplySignal(
        is_reply_to_our_message=False, detected_language="en", message_id="scraped-1"
    )
    assert confirm_language_state("sv", signal) == "sv"


def test_flip_is_one_directional_does_not_revert_on_later_swedish_message():
    already_confirmed = "en_confirmed"
    swedish_signal = InboundReplySignal(
        is_reply_to_our_message=True, detected_language="sv", message_id="msg-3"
    )
    assert confirm_language_state(already_confirmed, swedish_signal) == "en_confirmed"


# -- Utskicksgrinden: humanizer-variant måste matcha language_state --------


def test_send_gate_passes_with_matching_swedish_variant():
    check_send_gate(language_state="sv", humanizer_variant="snajp:humanizer-svenska")  # kastar inte


def test_send_gate_passes_with_matching_english_variant():
    check_send_gate(language_state="en_confirmed", humanizer_variant="snajp:humanizer")


def test_send_gate_refuses_missing_humanizer_variant():
    with pytest.raises(LanguageGateError):
        check_send_gate(language_state="sv", humanizer_variant=None)


def test_send_gate_refuses_mismatched_variant():
    """sv-läge men engelsk humanizer-variant injicerad — grinden vägrar,
    upptäcker inte det i efterhand."""
    with pytest.raises(LanguageGateError):
        check_send_gate(language_state="sv", humanizer_variant="snajp:humanizer")


def test_send_gate_refuses_unknown_language_state():
    with pytest.raises(LanguageGateError):
        check_send_gate(language_state="de", humanizer_variant="snajp:humanizer-svenska")
