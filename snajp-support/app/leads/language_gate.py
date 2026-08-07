"""Del J: språkgrind. Svenska är alltid utgångsläget. Att kunden/prospektets
bolag talar engelska säger ingenting om prospektets egen preferens.

Enda tillåtna övergången: prospektet har SJÄLVT svarat på ett tidigare
mejl FRÅN oss, på engelska. Engelsk LinkedIn-profil, engelskt bolagsnamn
eller ett antagande om engelsktalande kund räknas ALDRIG — de representeras
inte ens som en InboundReplySignal här, för att göra dem strukturellt
omöjliga att använda som trigger (INV-LANG-001).

Verkställs som en UTSKICKSGRIND: check_send_gate() kräver att sista steget
var rätt humanizer-variant för language_state, vägrar annars med
LanguageGateError. En prompt går att prata omkull; en grind gör det inte
(INV-LANG-002).
"""

from __future__ import annotations

from dataclasses import dataclass

VALID_LANGUAGE_STATES = ("sv", "en_confirmed")

_HUMANIZER_VARIANT_BY_LANGUAGE_STATE = {
    "sv": "snajp:humanizer-svenska",
    "en_confirmed": "snajp:humanizer",
}


class LanguageGateError(RuntimeError):
    pass


@dataclass(frozen=True)
class InboundReplySignal:
    """Det ENDA en language_state-övergång får byggas på: ett faktiskt svar
    FRÅN prospektet på ett tidigare utskick FRÅN oss. message_id är beviset
    som loggas (plan Del J: 'loggat med meddelande-id som bevis')."""

    is_reply_to_our_message: bool
    detected_language: str  # t.ex. 'sv', 'en'
    message_id: str


def confirm_language_state(current_state: str, signal: InboundReplySignal) -> str:
    """Returnerar nytt language_state. Enkelriktat: en gång en_confirmed,
    flippar aldrig tillbaka till 'sv' av den här funktionen (att ett senare
    mejl råkar vara svenska är inte samma sak som att prospektet bytt
    preferens)."""
    if current_state == "en_confirmed":
        return current_state
    if signal.is_reply_to_our_message and signal.detected_language == "en":
        return "en_confirmed"
    return current_state


def check_send_gate(*, language_state: str, humanizer_variant: str | None) -> None:
    """INV-LANG-002. Kastar LanguageGateError om variant saknas eller inte
    matchar language_state — send_queue-vägen (migration 010) ska aldrig
    nå fram till ett faktiskt utskick utan att ha passerat detta."""
    if language_state not in VALID_LANGUAGE_STATES:
        raise LanguageGateError(f"Okänt language_state: {language_state!r}.")
    expected_variant = _HUMANIZER_VARIANT_BY_LANGUAGE_STATE[language_state]
    if humanizer_variant != expected_variant:
        raise LanguageGateError(
            f"send() vägrar: language_state={language_state!r} kräver "
            f"humanizer_variant={expected_variant!r}, fick {humanizer_variant!r}."
        )
