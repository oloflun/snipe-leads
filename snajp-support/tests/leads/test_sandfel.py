"""Ett utskick som mejltjänsten inte tar emot (Fas 0, 2026-11-09).

Före: `provider.send` kastade rakt ut ur sändvägen. Köposten stod kvar som
godkänd och försöktes om varje minut utan slut, och i "Godkänn och skicka
alla" fällde ett enda avvisat mejl hela begäran, så att resten aldrig prövades.

Nu bokförs sändfelet på köposten. Ett mejl tjänsten avvisar (ogiltig adress,
avvisat innehåll) stoppas med ett skäl granskaren ser. Ett tillfälligt fel
försöks om med växande paus och stoppas efter ett bestämt antal försök.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.leads import scheduler
from app.leads.scheduler import process_godkanda, skicka_godkant
from app.leads.send_provider import SandningAvvisad
from app.storage.memory import MemoryStorage
from tests.leads.test_godkann_skicka import _Klocka, _ny_kund, _post
from tests.leads.test_scheduler import (
    OUTSIDE_WINDOW_UTC,
    TENANT,
    WITHIN_WINDOW_UTC,
    _FakeSendProvider,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _Trasig(_FakeSendProvider):
    """Kastar `fel` så länge det är satt; skickar som vanligt annars."""

    def __init__(self, fel: Exception | None) -> None:
        super().__init__()
        self.fel = fel
        self.forsok = 0

    async def send(self, *, to: str, subject: str, body: str) -> None:
        self.forsok += 1
        if self.fel is not None:
            raise self.fel
        await super().send(to=to, subject=subject, body=body)


def _avvisad() -> SandningAvvisad:
    return SandningAvvisad("Resend avvisade sändningen (422): invalid `to` field", status_code=422)


async def test_avvisat_mejl_stoppas_med_skal_i_stallet_for_att_kasta():
    storage, provider = MemoryStorage(), _Trasig(_avvisad())
    item_id, _, _ = _ny_kund(storage, scheduled_at=WITHIN_WINDOW_UTC)

    utfall, skal = await skicka_godkant(storage, TENANT, item_id, provider, now=WITHIN_WINDOW_UTC)

    assert utfall == "blocked"
    assert skal and "Mejltjänsten" in skal
    post = _post(storage, item_id)
    assert post["status"] == "blocked"
    assert post["gate_checks"]["send_guard_regel"] == "leverans"
    # Godkännandet står kvar: det är fortfarande en människas ja.
    assert post["gate_checks"]["approved_by"] == "human"


async def test_avvisat_mejl_forsoks_inte_om_av_loopen(monkeypatch):
    storage, provider = MemoryStorage(), _Trasig(_avvisad())
    item_id, _, _ = _ny_kund(storage, scheduled_at=WITHIN_WINDOW_UTC)
    await skicka_godkant(storage, TENANT, item_id, provider, now=WITHIN_WINDOW_UTC)

    monkeypatch.setattr(scheduler, "datetime", _Klocka(WITHIN_WINDOW_UTC + timedelta(hours=1)))
    await process_godkanda(storage, provider)

    assert provider.forsok == 1


async def test_ogiltig_adress_raknas_som_avvisad():
    storage, provider = MemoryStorage(), _Trasig(ValueError("Ogiltig mottagaradress: 'x' — inget skickat."))
    item_id, _, _ = _ny_kund(storage, scheduled_at=WITHIN_WINDOW_UTC)

    utfall, _ = await skicka_godkant(storage, TENANT, item_id, provider, now=WITHIN_WINDOW_UTC)

    assert utfall == "blocked"


async def test_tillfalligt_fel_lamnar_utkastet_godkant_och_sager_det():
    storage, provider = MemoryStorage(), _Trasig(RuntimeError("Resend avvisade sändningen (503): upstream"))
    item_id, _, _ = _ny_kund(storage, scheduled_at=WITHIN_WINDOW_UTC)

    utfall, skal = await skicka_godkant(storage, TENANT, item_id, provider, now=WITHIN_WINDOW_UTC)

    assert utfall == "sandfel"
    assert skal and "försöks igen" in skal
    post = _post(storage, item_id)
    assert post["status"] == "queued"
    assert post["gate_checks"]["approved_by"] == "human"
    assert post["gate_checks"]["sandfel_antal"] == 1


async def test_tillfalligt_fel_vantar_ut_pausen_fore_nasta_forsok(monkeypatch):
    storage, provider = MemoryStorage(), _Trasig(RuntimeError("timeout"))
    item_id, _, _ = _ny_kund(storage, scheduled_at=WITHIN_WINDOW_UTC)
    await skicka_godkant(storage, TENANT, item_id, provider, now=WITHIN_WINDOW_UTC)
    assert provider.forsok == 1

    # Trettio sekunder senare: pausen (en minut efter första felet) gäller.
    monkeypatch.setattr(scheduler, "datetime", _Klocka(WITHIN_WINDOW_UTC + timedelta(seconds=30)))
    await process_godkanda(storage, provider)
    assert provider.forsok == 1

    monkeypatch.setattr(scheduler, "datetime", _Klocka(WITHIN_WINDOW_UTC + timedelta(seconds=90)))
    await process_godkanda(storage, provider)
    assert provider.forsok == 2
    assert _post(storage, item_id)["gate_checks"]["sandfel_antal"] == 2


async def test_pausen_vaxer_med_antalet_fel():
    nu = WITHIN_WINDOW_UTC
    forsta = scheduler.nasta_forsok({"sandfel_antal": 1, "sandfel_senast": nu.isoformat()})
    fjarde = scheduler.nasta_forsok({"sandfel_antal": 4, "sandfel_senast": nu.isoformat()})
    manga = scheduler.nasta_forsok({"sandfel_antal": 15, "sandfel_senast": nu.isoformat()})

    assert forsta - nu == timedelta(minutes=1)
    assert fjarde - nu == timedelta(minutes=8)
    assert manga - nu == timedelta(minutes=30), "pausen har ett tak"
    assert scheduler.nasta_forsok({}) is None


async def test_tillfalligt_fel_ger_upp_efter_taket_och_stoppar_utkastet(monkeypatch):
    storage, provider = MemoryStorage(), _Trasig(RuntimeError("timeout"))
    item_id, _, _ = _ny_kund(storage, scheduled_at=WITHIN_WINDOW_UTC)
    await skicka_godkant(storage, TENANT, item_id, provider, now=WITHIN_WINDOW_UTC)

    # Tider inne i sändfönstret (vardagar, 10–15 svensk tid), längre isär än
    # pausens tak, så att varje varv är ett riktigt försök.
    nu = WITHIN_WINDOW_UTC
    for _ in range(scheduler.MAX_SANDFORSOK + 5):
        nu += timedelta(minutes=31)
        if nu.hour >= 13:
            nu = (nu + timedelta(days=1)).replace(hour=8, minute=0)
        if nu.weekday() >= 5:
            nu += timedelta(days=7 - nu.weekday())
        monkeypatch.setattr(scheduler, "datetime", _Klocka(nu))
        await process_godkanda(storage, provider)

    assert provider.forsok == scheduler.MAX_SANDFORSOK
    post = _post(storage, item_id)
    assert post["status"] == "blocked"
    assert post["gate_checks"]["send_guard_regel"] == "leverans"


async def test_lyckat_omforsok_skickar_och_rensar_felbokforingen(monkeypatch):
    storage, provider = MemoryStorage(), _Trasig(RuntimeError("timeout"))
    item_id, _, _ = _ny_kund(storage, scheduled_at=WITHIN_WINDOW_UTC)
    await skicka_godkant(storage, TENANT, item_id, provider, now=WITHIN_WINDOW_UTC)

    provider.fel = None
    monkeypatch.setattr(scheduler, "datetime", _Klocka(WITHIN_WINDOW_UTC + timedelta(minutes=2)))
    resultat = await process_godkanda(storage, provider)

    assert [r["outcome"] for r in resultat] == ["sent"]
    post = _post(storage, item_id)
    assert post["status"] == "sent"
    assert "sandfel_antal" not in post["gate_checks"]
    assert len(provider.sent) == 1


async def test_stangt_sandfonster_nollstaller_inte_felrakningen(monkeypatch):
    """Annars börjar räkningen om varje morgon och taket nås aldrig."""
    storage, provider = MemoryStorage(), _Trasig(RuntimeError("timeout"))
    item_id, _, _ = _ny_kund(storage, scheduled_at=WITHIN_WINDOW_UTC)
    await skicka_godkant(storage, TENANT, item_id, provider, now=WITHIN_WINDOW_UTC)

    monkeypatch.setattr(scheduler, "datetime", _Klocka(OUTSIDE_WINDOW_UTC))
    await process_godkanda(storage, provider)

    post = _post(storage, item_id)
    assert post["status"] == "queued"
    assert post["gate_checks"]["sandfel_antal"] == 1
    assert provider.forsok == 1


async def test_stoppat_utkast_kan_godkannas_igen_och_borjar_da_om():
    storage, provider = MemoryStorage(), _Trasig(_avvisad())
    item_id, _, _ = _ny_kund(storage, scheduled_at=WITHIN_WINDOW_UTC)
    await skicka_godkant(storage, TENANT, item_id, provider, now=WITHIN_WINDOW_UTC)

    provider.fel = None
    utfall, skal = await skicka_godkant(storage, TENANT, item_id, provider, now=WITHIN_WINDOW_UTC)

    assert (utfall, skal) == ("sent", None)
    assert "sandfel_antal" not in _post(storage, item_id)["gate_checks"]


async def test_resend_kastar_avvisad_med_statuskod(monkeypatch):
    """Sändvägen skiljer avvisat från tillfälligt på statuskoden."""

    class _Svar:
        status_code, text = 422, '{"message": "Invalid `to` field."}'

    class _Klient:
        def __init__(self, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            return _Svar()

    import httpx

    from app.leads.send_provider import ResendMailer

    monkeypatch.setattr(httpx, "AsyncClient", _Klient)
    with pytest.raises(SandningAvvisad) as fangad:
        await ResendMailer(api_key="re_hemlig", avsandare="hej@snajp.se").send(
            to="kund@example.com", subject="Hej", body="Text"
        )
    assert fangad.value.status_code == 422
    assert isinstance(fangad.value, RuntimeError), "äldre anropare fångar RuntimeError"
