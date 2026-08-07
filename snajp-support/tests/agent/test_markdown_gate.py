from app.agent.tools import strip_markdown


def test_strips_bold():
    assert strip_markdown("Det kostar **199 kr** per månad.") == "Det kostar 199 kr per månad."


def test_strips_headers():
    assert strip_markdown("# Rubrik\nBrödtext") == "Rubrik\nBrödtext"


def test_strips_bullets_to_dash():
    assert strip_markdown("- Punkt ett\n- Punkt två") == "– Punkt ett\n– Punkt två"


def test_strips_links_keeps_text():
    assert strip_markdown("Se [vår hemsida](https://example.se) för mer info.") == (
        "Se vår hemsida för mer info."
    )


def test_strips_inline_code():
    assert strip_markdown("Ange koden `ABC123` i fältet.") == "Ange koden ABC123 i fältet."


def test_plain_text_is_unchanged():
    text = "Hej! Tack för ditt meddelande – vi återkommer inom kort."
    assert strip_markdown(text) == text
