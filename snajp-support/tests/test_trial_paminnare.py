"""Trial-påminnaren — se app/jobs/trial_paminnare.py för kontraktet."""

from __future__ import annotations

from datetime import date

import pytest

from app.jobs.trial_paminnare import kor_svep
from app.storage.memory import MemoryStorage

IDAG = date(2026, 9, 20)
WS = "00000000-0000-4000-c000-000000000001"


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _FakeProvider:
    levererar = True

    def __init__(self):
        self.sent: list[dict] = []

    async def send(self, *, to: str, subject: str, body: str) -> None:
        self.sent.append({"to": to, "subject": subject, "body": body})


class _DodProvider(_FakeProvider):
    levererar = False


def _kandidat(dagar_kvar: int, ws: str = WS) -> dict:
    return {
        "workspace_id": ws,
        "name": "Testkund AB",
        "trial_slut": date(2026, 9, 20 + dagar_kvar),
        "email": "agare@testkund.se",
        "dagar_kvar": dagar_kvar,
    }


@pytest.mark.anyio
@pytest.mark.parametrize(("dagar", "typ"), [(7, "7_dagar"), (1, "1_dag")])
async def test_paminnelse_skickas_och_loggas(dagar, typ, monkeypatch):
    storage = MemoryStorage()
    storage.trial_kandidater = [_kandidat(dagar)]
    provider = _FakeProvider()
    monkeypatch.setattr("app.jobs.trial_paminnare.get_send_provider", lambda: provider)

    skickade = await kor_svep(storage, idag=IDAG)

    assert [s["typ"] for s in skickade] == [typ]
    assert provider.sent[0]["to"] == "agare@testkund.se"
    assert "provperiod" in provider.sent[0]["subject"]
    assert (WS, typ) in storage.trial_paminnelser


@pytest.mark.anyio
async def test_svepet_ar_idempotent(monkeypatch):
    """Andra svepet samma dag skickar ingenting — loggen är spärren."""
    storage = MemoryStorage()
    storage.trial_kandidater = [_kandidat(7)]
    provider = _FakeProvider()
    monkeypatch.setattr("app.jobs.trial_paminnare.get_send_provider", lambda: provider)

    await kor_svep(storage, idag=IDAG)
    andra = await kor_svep(storage, idag=IDAG)

    assert andra == []
    assert len(provider.sent) == 1


@pytest.mark.anyio
async def test_utan_sandvag_loggas_ingenting(monkeypatch):
    """LoggingSendProvider levererar inte: då skickas inget OCH inget loggas
    som skickat — en loggad påminnelse kunden aldrig fick vore en lögn."""
    storage = MemoryStorage()
    storage.trial_kandidater = [_kandidat(1)]
    monkeypatch.setattr("app.jobs.trial_paminnare.get_send_provider", lambda: _DodProvider())

    assert await kor_svep(storage, idag=IDAG) == []
    assert storage.trial_paminnelser == {}


@pytest.mark.anyio
async def test_en_trasig_adress_stoppar_inte_de_andra(monkeypatch):
    storage = MemoryStorage()
    ws2 = "00000000-0000-4000-c000-000000000002"
    storage.trial_kandidater = [_kandidat(7), _kandidat(7, ws=ws2)]

    class _Halvtrasig(_FakeProvider):
        async def send(self, *, to, subject, body):
            if not self.sent:
                self.sent.append({"fel": True})
                raise RuntimeError("SMTP borta")
            await super().send(to=to, subject=subject, body=body)

    provider = _Halvtrasig()
    monkeypatch.setattr("app.jobs.trial_paminnare.get_send_provider", lambda: provider)

    skickade = await kor_svep(storage, idag=IDAG)

    assert [s["workspace_id"] for s in skickade] == [ws2]
    # Den fallna skickningen är INTE loggad — nästa svep försöker igen.
    assert (WS, "7_dagar") not in storage.trial_paminnelser
    assert (ws2, "7_dagar") in storage.trial_paminnelser
