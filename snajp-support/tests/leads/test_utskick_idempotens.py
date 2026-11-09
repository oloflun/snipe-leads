"""Idempotens i utskicken (Fas 0-fyndet K5, 2026-11-09).

Sändloopen skickar, markerar skickat och sätter status i tre steg. Bryts
processen mellan det första och det andra (deploy, dödsvakt, databasfel)
hittar nästa varv samma rad och skickar igen: prospektet får två likadana
kallmejl inom en minut. Resend tar en Idempotency-Key och svarar då med det
första utskickets svar i stället för att skicka en gång till.
"""

from __future__ import annotations

import pytest

from app.leads.send_provider import ResendMailer

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _fejk_resend(monkeypatch) -> list[dict]:
    anrop: list[dict] = []

    class _Svar:
        status_code, text = 200, "{}"

        def json(self):
            return {"id": "resend-1"}

    class _Klient:
        def __init__(self, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            anrop.append({"headers": headers, "json": json})
            return _Svar()

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", _Klient)
    return anrop


async def test_samma_utskick_far_samma_idempotensnyckel(monkeypatch):
    anrop = _fejk_resend(monkeypatch)
    m = ResendMailer(api_key="re_hemlig", avsandare="hej@snajp.se")

    for _ in range(2):
        await m.send(to="kund@example.com", subject="Hej", body="Text", idempotensnyckel="utskick-abc")

    nycklar = [a["headers"]["Idempotency-Key"] for a in anrop]
    assert nycklar[0] == nycklar[1], "ett omtag av samma utskick måste bära samma nyckel"
    assert nycklar[0].startswith("utskick-abc-")
    assert len(nycklar[0]) <= 256


async def test_andrat_innehall_ger_ny_nyckel(monkeypatch):
    """Resend svarar 409 på samma nyckel med annat innehåll. Ett utkast som
    redigerats efter ett misslyckat försök ska gå ut, inte fastna i 409."""
    anrop = _fejk_resend(monkeypatch)
    m = ResendMailer(api_key="re_hemlig", avsandare="hej@snajp.se")

    await m.send(to="kund@example.com", subject="Hej", body="Första texten", idempotensnyckel="utskick-abc")
    await m.send(to="kund@example.com", subject="Hej", body="Rättad text", idempotensnyckel="utskick-abc")

    assert anrop[0]["headers"]["Idempotency-Key"] != anrop[1]["headers"]["Idempotency-Key"]


async def test_utan_nyckel_skickas_ingen_idempotensheader(monkeypatch):
    anrop = _fejk_resend(monkeypatch)
    await ResendMailer(api_key="re_hemlig", avsandare="hej@snajp.se").send(
        to="kund@example.com", subject="Hej", body="Text"
    )
    assert "Idempotency-Key" not in anrop[0]["headers"]


async def test_sandloopen_skickar_meddelandets_id_som_nyckel(monkeypatch):
    """Loopen ska ge sändaren något att känna igen utskicket på."""
    from pathlib import Path

    kalla = (Path(__file__).resolve().parents[2] / "app" / "leads" / "scheduler.py").read_text(encoding="utf-8")
    fore_send = kalla[: kalla.index("await provider.send(")]
    assert 'extra["idempotensnyckel"] = f"utskick-{message[\'id\']}"' in fore_send


async def test_supportsvaret_skickar_en_nyckel_per_mejl_och_text(monkeypatch):
    """Dubbelklick på Godkänn, eller ett omtag efter att proxyn gett upp,
    får inte ge kunden samma svar två gånger. En ÄNDRAD text är ett nytt svar."""
    from app.email_pipeline import sender

    sedda: list[str | None] = []

    class _Provider:
        levererar = True

        async def send(self, *, to, subject, body, idempotensnyckel=None, **_k):
            sedda.append(idempotensnyckel)
            return "id-1"

    mejl = {"id": "mejl-1", "from_email": "kund@example.com", "subject": "Fråga", "provider": "imap"}
    for text in ("Hej, kursen är på torsdag.", "Hej, kursen är på torsdag.", "Hej, kursen är på fredag."):
        await sender.skicka_supportsvar(mejl, content=text, provider=_Provider())

    assert sedda[0] and sedda[0] == sedda[1]
    assert sedda[2] != sedda[0]
