from app.email_pipeline.processor import _wrap_reply


def test_wrap_reply_removes_generated_greeting_and_signature():
    raw = "Hej!\n\nTack för ditt meddelande.\n\nMed vänliga hälsningar,\nSnajp Support"
    result = _wrap_reply(raw, "Anna Andersson")

    assert result == (
        "Hej Anna!\n\nTack för ditt meddelande.\n\n"
        "Vänliga hälsningar,\nSnajp Support"
    )
    assert result.count("Hej") == 1
    assert result.count("Snajp Support") == 1


def test_wrap_reply_keeps_plain_body():
    assert _wrap_reply("Tack för ditt meddelande.", None) == (
        "Hej!\n\nTack för ditt meddelande.\n\n"
        "Vänliga hälsningar,\nSnajp Support"
    )
