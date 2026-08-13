"""Delade fixturer för testsviten.

Sviten ska enligt README gå att köra utan nycklar. På en maskin som ÄR
konfigurerad plockar pydantic-settings ändå upp riktiga SMTP-uppgifter ur
`.env` — och då kontaktade `test_approve_with_edit_sends_and_logs_review`
Gmail på riktigt och skickade ett skarpt mail till mock-adresserna. Testet gick
från grönt till 502 så fort Gmail började strypa inloggningen, alltså berodde
resultatet på nätverket i stället för på koden.

Spärren nedan är autouse: ingen test får nå en riktig mailserver. Tester som
vill inspektera utgående mail (test_sending.py) patchar samma funktioner själva
och skriver över den här stubben inom sitt eget test.
"""

import pytest

from app.email_pipeline import sender


@pytest.fixture(autouse=True)
def _no_real_smtp(monkeypatch):
    async def fake_send(*, to_email, subject, body, in_reply_to=None):
        return True, "<conftest-stub@snajp>"

    monkeypatch.setattr(sender, "send_reply", fake_send)
    # Modulerna importerade funktionen vid uppstart, så namnet måste bytas där också.
    monkeypatch.setattr("app.api.drafts.send_reply", fake_send)
