"""Postens tidslinje: CRM:ets egna händelser, leadsflödet och supporten på ett
ställe, komponerat vid läsning (app/crm/tidslinje.py).
"""

from __future__ import annotations

import json

import pytest

from app.crm import lagring, tidslinje

from .conftest import ORGNR_A, ORGNR_B

V1 = "/api/crm/v1"
pytestmark = pytest.mark.anyio


async def _lead(storage, tenant_id: str, namn: str, *, orgnr: str | None = None, epost: str | None = None,
                kontakt: str | None = None, **mer) -> dict:
    p = await storage.create_prospect(tenant_id, company_name=namn, contact_email=epost, contact_name=kontakt, **mer)
    if orgnr:
        await storage.update_prospect(tenant_id, p["id"], orgnr=orgnr)
    return p


async def _mejl(storage, tenant_id: str, prospekt: dict, amne: str, *, skickat: str | None) -> dict:
    trad = await storage.ensure_outreach_thread(tenant_id, prospect_id=prospekt["id"])
    ut = await storage.queue_outreach_message(tenant_id, thread_id=trad["id"], body=f"Hej, {amne}. " + "x" * 400,
                                              subject=amne, humanizer_variant="a", scheduled_at=None)
    if skickat:
        await storage.mark_outreach_message_sent(tenant_id, ut["message"]["id"], skickat)
    return trad


async def test_bolagets_tidslinje_samlar_crm_leads_och_support(buddy, annan, storage):
    async with buddy.klient() as k:
        bolag = (await k.post(f"{V1}/companies", json={"name": "Bygg AB", "org_number": ORGNR_A})).json()
        await k.patch(f"{V1}/companies/{bolag['id']}", json={"phone": "08-123 456 78"})
        await k.post(f"{V1}/people", json={"first_name": "Anna", "email": "anna@bygg.se", "company_id": bolag["id"]})

    # Samma bolag som lead hos Iris, under ett annat namn men samma nummer.
    lead = await _lead(storage, buddy.id, "Byggarna i Umeå AB", orgnr=ORGNR_A, epost="vd@bygg.se", kontakt="Bo Ek")
    trad = await _mejl(storage, buddy.id, lead, "Förslag", skickat="2026-10-01T09:00:00+00:00")
    await _mejl(storage, buddy.id, lead, "Uppföljning", skickat="2026-10-08T09:00:00+00:00")
    await _mejl(storage, buddy.id, lead, "Utkast som aldrig gick", skickat=None)
    await storage.record_inbound_reply(buddy.id, thread_id=trad["id"], body="Låter bra, ring mig.")
    await storage.add_lead_samtal(buddy.id, prospect_id=lead["id"], utfall="mote", aterkom_datum=None,
                                  anteckning="Möte bokat till tisdag.")
    await storage.add_lead_note(buddy.id, prospect_id=lead["id"], text="Vill ha offert på två platser.")
    await storage.add_lead_task(buddy.id, prospect_id=lead["id"], titel="Skicka offert", forfaller="2026-12-01")
    await storage.update_prospect(buddy.id, lead["id"], status="replied")
    # Ett annat lead som inte har med bolaget att göra.
    await _lead(storage, buddy.id, "Helt Annat AB", orgnr=ORGNR_B, epost="info@annat.se")

    # Anna har skrivit till supporten, och ett av ärendena är ett test.
    kund = await storage.find_or_create_customer(buddy.id, email="anna@bygg.se", phone=None, name="Anna")
    arende = await storage.create_ticket(buddy.id, customer_id=kund["id"], subject="Fakturan stämmer inte",
                                         category="faktura", channel="email")
    await storage.create_ticket(buddy.id, customer_id=kund["id"], subject="Provärende", category="ovrigt",
                                channel="email", is_test=True)

    async with buddy.klient() as k:
        svar = await k.get(f"{V1}/companies/{bolag['id']}/timeline")
        assert svar.status_code == 200, svar.text
        linje = svar.json()["data"]
    typer = [p["type"] for p in linje]
    for typ in ("record_created", "record_updated", "lead_created", "email_sent", "followup_sent", "reply_received",
                "call", "note", "task", "lead_status", "support_ticket"):
        assert typ in typer, typ
    # Nyast först, och varje post har en stabil nyckel.
    assert [p["at"] for p in linje] == sorted((p["at"] for p in linje), reverse=True)
    assert len({p["key"] for p in linje}) == len(linje)
    # Ett utkast som aldrig gick är inte historik.
    assert "Utkast som aldrig gick" not in json.dumps(linje, ensure_ascii=False)
    assert typer.count("email_sent") == 1 and typer.count("followup_sent") == 1
    # Testärendet och det andra leadet hör inte hit.
    assert "Provärende" not in json.dumps(linje, ensure_ascii=False) and "Helt Annat" not in json.dumps(linje)
    arendepost = next(p for p in linje if p["type"] == "support_ticket")
    assert arendepost["title"] == "Fakturan stämmer inte" and arendepost["text"] is None
    assert arendepost["link"] == {"kind": "ticket", "id": arende["id"]}
    assert arendepost["data"] == {"channel": "email", "category": "faktura", "status": "open", "priority": "normal"}
    samtal = next(p for p in linje if p["type"] == "call")
    assert samtal["data"]["outcome"] == "mote" and samtal["link"] == {"kind": "lead", "id": lead["id"]}
    andrad = next(p for p in linje if p["type"] == "record_updated")
    assert andrad["data"]["fields"] == ["phone"] and andrad["origin"] == "crm"
    mejl = next(p for p in linje if p["type"] == "email_sent")
    assert mejl["title"] == "Förslag" and mejl["link"] == {"kind": "conversation", "id": trad["id"]}
    assert mejl["at"].startswith("2026-10-01T09:00:00")

    # Den andra kunden når inte bolaget, och ser inget av det på sitt eget bolag med samma nummer.
    async with annan.klient() as k:
        assert (await k.get(f"{V1}/companies/{bolag['id']}/timeline")).status_code == 404
        eget = (await k.post(f"{V1}/companies", json={"name": "Bygg AB", "org_number": ORGNR_A})).json()
        andras = (await k.get(f"{V1}/companies/{eget['id']}/timeline")).json()["data"]
        assert [p["type"] for p in andras] == ["record_created"]


async def test_integrationens_nyckel_far_inga_utdrag_men_appen_far_dem(buddy, storage):
    async with buddy.klient() as k:
        bolag = (await k.post(f"{V1}/companies", json={"name": "Bygg AB", "org_number": ORGNR_A})).json()
    lead = await _lead(storage, buddy.id, "Bygg AB", orgnr=ORGNR_A, epost="vd@bygg.se")
    await _mejl(storage, buddy.id, lead, "Förslag", skickat="2026-10-01T09:00:00+00:00")
    await storage.add_lead_note(buddy.id, prospect_id=lead["id"], text="Hemligt om kunden.")
    # Integrationens nyckel (med omfång): händelsen och länken, inget utdrag.
    async with buddy.klient() as k:
        linje = (await k.get(f"{V1}/companies/{bolag['id']}/timeline")).json()["data"]
    assert all(p["text"] is None for p in linje) and "Hemligt" not in json.dumps(linje)
    assert next(p for p in linje if p["type"] == "email_sent")["title"] == "Förslag"
    # Appen (kundens egen nyckel) får utdraget.
    await storage.create_api_key(buddy.id, tenant_name="Buddy", raw_key="snajp_live_appens_egen_nyckel")
    async with buddy.klient("snajp_live_appens_egen_nyckel") as k:
        linje = (await k.get(f"{V1}/companies/{bolag['id']}/timeline")).json()["data"]
    anteckning = next(p for p in linje if p["type"] == "note")
    assert anteckning["text"] == "Hemligt om kunden."
    assert len(next(p for p in linje if p["type"] == "email_sent")["text"]) == tidslinje.UTDRAG


async def test_personens_tidslinje_gar_pa_exakt_adress(buddy, storage):
    async with buddy.klient() as k:
        anna = (await k.post(f"{V1}/people", json={"first_name": "Anna", "email": "Anna@Bygg.se"})).json()
        bo = (await k.post(f"{V1}/people", json={"first_name": "Bo", "email": "bo@bygg.se"})).json()
    lead = await _lead(storage, buddy.id, "Bygg AB", epost="anna@bygg.se", kontakt="Anna Berg")
    await storage.add_lead_samtal(buddy.id, prospect_id=lead["id"], utfall="ej_svar", aterkom_datum=None, anteckning=None)
    kund = await storage.find_or_create_customer(buddy.id, email="anna@bygg.se", phone=None, name="Anna")
    await storage.create_ticket(buddy.id, customer_id=kund["id"], subject="Fråga", category="ovrigt", channel="chat")
    async with buddy.klient() as k:
        annas = [p["type"] for p in (await k.get(f"{V1}/people/{anna['id']}/timeline")).json()["data"]]
        bos = [p["type"] for p in (await k.get(f"{V1}/people/{bo['id']}/timeline")).json()["data"]]
    assert {"lead_created", "call", "support_ticket", "record_created"} <= set(annas)
    # Samma domän räcker inte: Bo har inget med Annas lead eller ärende att göra.
    assert bos == ["record_created"]


async def test_bolag_utan_nummer_hittar_sitt_lead_pa_doman_men_aldrig_pa_en_privat(buddy, storage):
    async with buddy.klient() as k:
        eget = (await k.post(f"{V1}/companies", json={"name": "Måleri Nord", "website": "www.malerinord.se"})).json()
        privat = (await k.post(f"{V1}/companies", json={"name": "Firma Ek", "website": "https://gmail.com"})).json()
    await _lead(storage, buddy.id, "Måleri Nord AB", epost="vd@malerinord.se")
    await _lead(storage, buddy.id, "Någon Annan", epost="nagon@gmail.com")
    egen = await tidslinje.for_bolag(storage, buddy.id, await lagring.hamta_post(storage, buddy.id, "bolag", eget["id"]))
    assert "lead_skapad" in [p["typ"] for p in egen]
    privata = await tidslinje.for_bolag(storage, buddy.id, await lagring.hamta_post(storage, buddy.id, "bolag", privat["id"]))
    assert [p["typ"] for p in privata] == ["post_skapad"]


async def test_exempel_och_testprospekt_hor_inte_till_tidslinjen(buddy, storage):
    async with buddy.klient() as k:
        bolag = (await k.post(f"{V1}/companies", json={"name": "Bygg AB", "org_number": ORGNR_A})).json()
    await _lead(storage, buddy.id, "Bygg AB", orgnr=ORGNR_A, epost="vd@bygg.se", origin="example")
    post = await lagring.hamta_post(storage, buddy.id, "bolag", bolag["id"])
    assert [p["typ"] for p in await tidslinje.for_bolag(storage, buddy.id, post)] == ["post_skapad"]


def test_prospektet_lases_med_en_uttrycklig_kolumnlista():
    """Webbplatsbedömningen är hemlig: frågan får aldrig bli `select *`."""
    import inspect

    kalla = inspect.getsource(tidslinje._prospekt)
    assert "select *" not in kalla and kalla.count("select ") == 1
    # Båda lagren läser samma uppräknade fält, och inget av dem hör till bedömningen av sajten.
    assert kalla.count("PROSPEKTFALT") == 2
    assert set(tidslinje.PROSPEKTFALT) == {"id", "company_name", "contact_name", "contact_email", "orgnr",
                                           "status", "origin", "created_at"}
