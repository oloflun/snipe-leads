"""Mallrester får ALDRIG nå kunden.

Upptäckt i skarp körning 2026-08-07 (docs/live-tests/support-20260807-200723):
3 av 10 svar slutade med "[Your name]" eller "[Kundtjänst]" i signaturen —
text som hade skickats till en riktig kund. Uppträdde i BÅDA thinking-lägena.
"""

from app.agent.tools import strip_markdown, strip_placeholders


def test_strips_your_name_placeholder_seen_in_live_run():
    reply = "Vänliga hälsningar,\n[Your name]"
    assert "[Your name]" not in strip_placeholders(reply)


def test_strips_swedish_placeholder_seen_in_live_run():
    reply = "Vänliga hälsningar,\n[Kundtjänst]"
    assert "[" not in strip_placeholders(reply)


def test_keeps_numeric_references():
    assert strip_placeholders("Se fotnot [1] för detaljer.") == "Se fotnot [1] för detaljer."


def test_keeps_bracketed_prose_with_punctuation():
    text = "Villkoren [se punkt 3, stycke b] gäller."
    assert strip_placeholders(text) == text


def test_does_not_leave_trailing_whitespace_or_blank_lines():
    result = strip_placeholders("Hej!\n\nVänliga hälsningar,\n[Your name]")
    assert not result.endswith(("\n", " "))
    assert "\n\n\n" not in result


def test_strip_markdown_also_applies_the_placeholder_gate():
    assert "[Your name]" not in strip_markdown("**Hej!**\n\nMvh\n[Your name]")


def test_markdown_links_still_become_plain_text():
    assert strip_markdown("Se [vår sida](https://x.se) för mer.") == "Se vår sida för mer."
