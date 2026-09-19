"""Händelser: ett eskalerat ärende skickas till kundens ärendesystem."""

from __future__ import annotations

import json

import httpx
import pytest

from app.integrationer import handelser, lagring, uppslag
from app.storage.memory import MemoryStorage

TENANT = "00000000-0000-4000-a000-000000000001"

ZENDESK = {
    "requests": [
        {
            "name": "Skapa ärende",
            "method": "POST",
            "url": "https://{{hemlighet.instans}}.zendesk.com/api/v2/tickets.json",
            "headers": {"Authorization": "Basic {{hemlighet.token}}"},
            "body": {
                "ticket": {
                    "subject": "Från Snajp: {{handelse.orsak}}",
                    "comment": {"body": "{{handelse.samtal}}"},
                    "requester": {"email": "{{kund.email}}", "name": "{{kund.namn}}"},
                    "tags": ["snajp", "{{handelse.orsakskod}}"],
                    "custom_fields": [{"id": 1, "value": "{{handelse.meddelanden}}"}],
                }
            },
        }
    ],
    "handelser": {"arende_eskalerat": "Skapa ärende"},
}


async def _samtal(storage) -> str:
    kund = await storage.find_or_create_customer(TENANT, email="kund@example.com", phone=None, name="Kim")
    for fran, text in (("inbound", "Var är min order?"), ("outbound", "Jag kollar."), ("inbound", "Fattar du inte?")):
        arende = await storage.create_ticket(
            TENANT, customer_id=kund["id"], subject="", category="leverans", channel="web", priority="normal"
        )
        await storage.save_message(
            TENANT, conversation_id=arende["conversation_id"], direction=fran, content=text,
            sentiment=None, has_image=False,
        )
    return kund["id"]


@pytest.mark.anyio
async def test_eskalering_skapar_arende_med_hela_samtalet(svara):
    storage = MemoryStorage()
    kund_id = await _samtal(storage)
    await lagring.skapa(
        storage, TENANT, typ="http", namn="Zendesk", beskrivning="", konfig=ZENDESK,
        hemligheter={"instans": "butiken", "token": "zendesk-hemlig-42"},
    )
    mottagna = svara(lambda r: httpx.Response(201, json={"ticket": {"id": 9}}))

    data = await handelser.eskaleringsdata(
        storage, TENANT, customer_id=kund_id, orsak="Kunden bad om en människa",
        orsakskod="ber_om_manniska", arendelank="https://portal.example.com/arende/1",
    )
    utfall = await handelser.skicka(
        storage, TENANT, "arende_eskalerat",
        kontext=uppslag.kontextvarden(
            kund_email="kund@example.com", kund_namn="Kim", kund_id=kund_id, arende_id="a-1",
            kategori="leverans", kanal="web", tenant_namn="Butiken",
        ),
        data=data,
    )
    assert [u.ok for u in utfall] == [True]
    forfragan = mottagna[0]
    assert forfragan.url.host == "butiken.zendesk.com"
    kropp = json.loads(forfragan.content)["ticket"]
    assert kropp["subject"] == "Från Snajp: Kunden bad om en människa"
    assert kropp["requester"] == {"email": "kund@example.com", "name": "Kim"}
    assert kropp["tags"] == ["snajp", "ber_om_manniska"]
    # Hela samtalet, äldst först — som text och som strukturerad lista.
    assert kropp["comment"]["body"] == (
        "Kunden: Var är min order?\nAgenten: Jag kollar.\nKunden: Fattar du inte?"
    )
    assert [m["text"] for m in kropp["custom_fields"][0]["value"]] == [
        "Var är min order?", "Jag kollar.", "Fattar du inte?"
    ]


@pytest.mark.anyio
async def test_testchatten_skickar_aldrig_och_fel_faller_inget(svara):
    storage = MemoryStorage()
    kund_id = await _samtal(storage)
    await lagring.skapa(
        storage, TENANT, typ="http", namn="Zendesk", beskrivning="", konfig=ZENDESK,
        hemligheter={"instans": "butiken", "token": "zendesk-hemlig-42"},
    )
    kontext = {"kund.email": "kund@example.com", "kund.namn": "Kim"}
    data = await handelser.eskaleringsdata(
        storage, TENANT, customer_id=kund_id, orsak="x", orsakskod="y", arendelank=None
    )
    # Testläge: ingen transport satt, ett anrop hade fällt testet.
    simulerat = await handelser.skicka(storage, TENANT, "arende_eskalerat", kontext=kontext, data=data, is_test=True)
    assert simulerat[0].simulerad

    svara(lambda r: httpx.Response(500, json={"error": "nere"}))
    fel = await handelser.skicka(storage, TENANT, "arende_eskalerat", kontext=kontext, data=data)
    assert fel[0].ok is False
    handelselogg = [e for e in storage.platform_events if e.get("source") == "integration"]
    assert handelselogg and "Zendesk" in handelselogg[0]["message"]
