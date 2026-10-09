"""Provmejlet (app/leads/provmejl.py): utkastet så som mottagaren ser det,
till kundens EGEN adress — och ingenting i kön, tråden eller leadet ändras."""

import uuid

import pytest

from app.leads.provmejl import PROVHEADRAR, ProvmejlFel, skicka_provmejl, tillatna_mottagare
from app.leads.scheduler import _fot_vid_godkannande
from app.leads.signatur import bygg_signaturtext, med_signatur_fore_fot
from app.storage.memory import MemoryStorage

TENANT = "tenant-prov"
SIGNATUR = {
    "aktiv": True,
    "namn": "Sebastian Bergman",
    "titel": "Grundare",
    "epost": "Kund@Example.se",
    "bolag": "Snajp",
    "logotyp_url": "https://example.se/logga.png",
}
FOT = "--\nSnajp · Org.nr 556000-0000 · Gatan 1\nAvregistrera dig: https://snajp.example/avregistrera?t=abc"


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _Levererande:
    levererar = True

    def __init__(self):
        self.skickat: list[dict] = []

    async def send(self, *, to, subject, body, html=None, from_email=None, from_name=None,
                   reply_to=None, tags=None, headers=None):
        self.skickat.append({"to": to, "subject": subject, "body": body, "html": html, "headers": headers})


def _seed(storage: MemoryStorage, *, body: str, sent_at=None) -> tuple[str, str]:
    storage.agent_settings[(TENANT, "leads")] = {"signatur": SIGNATUR}
    thread_id, message_id, item_id = (str(uuid.uuid4()) for _ in range(3))
    storage.outreach_threads.setdefault(TENANT, {})[thread_id] = {
        "id": thread_id, "language_state": "sv", "prospect_email": "lead@bolaget.se",
    }
    storage.outreach_messages.setdefault(TENANT, []).append(
        {"id": message_id, "thread_id": thread_id, "direction": "outbound", "sent_at": sent_at,
         "body": body, "subject": "En idé till er"}
    )
    storage.send_queue.setdefault(TENANT, []).append(
        {"id": item_id, "thread_id": thread_id, "status": "queued", "gate_checks": {"approved_by": "human"}}
    )
    return item_id, message_id


@pytest.mark.anyio
async def test_provet_gar_till_kundens_adress_med_signatur_och_rubbar_inget():
    storage = MemoryStorage()
    item_id, message_id = _seed(storage, body="Hej!\n\nEn idé.")
    provider = _Levererande()

    svar = await skicka_provmejl(storage, TENANT, provider, till="kund@example.se", queue_item_id=item_id)

    assert svar == {"till": "kund@example.se", "saknar_fot": True}
    [mejl] = provider.skickat
    assert mejl["to"] == "kund@example.se"
    assert bygg_signaturtext({k: v for k, v in SIGNATUR.items() if k != "aktiv"}) in mejl["body"]
    assert "logga.png" in (mejl["html"] or "")
    assert mejl["headers"] == PROVHEADRAR
    # Kön, meddelandet och texten är orörda.
    assert storage.send_queue[TENANT][-1]["status"] == "queued"
    meddelande = next(m for m in storage.outreach_messages[TENANT] if m["id"] == message_id)
    assert meddelande["sent_at"] is None
    assert meddelande["body"] == "Hej!\n\nEn idé."


@pytest.mark.anyio
async def test_provet_vagrar_en_adress_som_inte_ar_kundens():
    storage = MemoryStorage()
    item_id, _ = _seed(storage, body="Hej!")
    provider = _Levererande()

    for adress in ("lead@bolaget.se", "nagon@annan.se"):
        with pytest.raises(ProvmejlFel) as fel:
            await skicka_provmejl(storage, TENANT, provider, till=adress, queue_item_id=item_id)
        assert fel.value.status == 403
    assert provider.skickat == []


@pytest.mark.anyio
async def test_provet_skickar_inget_utan_levererande_provider():
    storage = MemoryStorage()
    item_id, _ = _seed(storage, body="Hej!")

    class _Simulerad:
        levererar = False

        async def send(self, **_):
            raise AssertionError("ska inte anropas")

    with pytest.raises(ProvmejlFel) as fel:
        await skicka_provmejl(storage, TENANT, _Simulerad(), till="kund@example.se", queue_item_id=item_id)
    assert fel.value.status == 503


@pytest.mark.anyio
async def test_ett_skickat_mejl_provskickas_som_det_gick_ut():
    from datetime import datetime, timezone

    storage = MemoryStorage()
    _, message_id = _seed(storage, body=f"Hej!\n\n{FOT}", sent_at=datetime(2026, 10, 1, tzinfo=timezone.utc))
    provider = _Levererande()

    svar = await skicka_provmejl(storage, TENANT, provider, till="kund@example.se", message_id=message_id)

    assert svar["saknar_fot"] is False
    assert provider.skickat[0]["body"] == f"Hej!\n\n{FOT}"


@pytest.mark.anyio
async def test_mottagarna_ar_kundens_egna_adresser():
    storage = MemoryStorage()
    _seed(storage, body="Hej!")
    storage.mailboxes["m1"] = {"tenant_id": TENANT, "address": "Inkorg@Example.se", "provider": "imap"}
    storage.mailboxes["m2"] = {"tenant_id": TENANT, "address": "mock@example.se", "provider": "mock"}
    storage.mailboxes["m3"] = {"tenant_id": "annan", "address": "annan@example.se", "provider": "imap"}

    assert await tillatna_mottagare(storage, TENANT) == ["kund@example.se", "inkorg@example.se"]


def test_signaturen_hamnar_fore_foten_och_bara_en_gang():
    sig = {k: v for k, v in SIGNATUR.items() if k != "aktiv"}
    med = med_signatur_fore_fot(f"Hej!\n\nEn idé.\n\n{FOT}", sig, halsning="Vänliga hälsningar,")

    assert med.index(sig["namn"]) < med.index("Avregistrera")
    assert med.endswith(FOT)
    assert med_signatur_fore_fot(med, sig, halsning="Vänliga hälsningar,") == med


@pytest.mark.anyio
async def test_godkannandet_lagger_pa_signaturen_som_saknas():
    storage = MemoryStorage()
    _, message_id = _seed(storage, body="Hej!\n\nEn idé.")

    await _fot_vid_godkannande(storage, TENANT, storage.send_queue[TENANT][-1])

    meddelande = next(m for m in storage.outreach_messages[TENANT] if m["id"] == message_id)
    assert "Sebastian Bergman\nGrundare" in meddelande["body"]
