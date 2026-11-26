"""Synkens två nivåer (migration 163): kunden ser felen i enkla ord och att de
gått vidare, supporten får hela rapporten med koder.
"""

from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.api import admin_crm
from app.config import get_settings
from app.crm import supportrapport

from .conftest import ORGNR_A, ORGNR_B

V1 = "/api/crm/v1"
pytestmark = pytest.mark.anyio


def _master(app) -> AsyncClient:
    if not any(getattr(r, "path", "").startswith("/api/admin/crm") for r in app.routes):
        app.include_router(admin_crm.router)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                       headers={"X-API-Key": get_settings().snajp_master_api_key})


_SATS = [
    {"id": "1", "name": "Rent AB", "org_number": ORGNR_A},
    {"id": "2", "name": "Fel Telefon AB", "phone": "12 34 56 7", "email": "inte en adress"},
    {"id": "3", "name": "Annat Fel AB", "phone": "12 34"},
    {"id": "4"},                                               # saknar namn
    {"id": "5", "name": "Anna Berg", "is_private_person": True, "email": "anna@example.se"},
]


async def test_kunden_far_felen_i_enkla_ord_och_beskedet_att_de_gatt_vidare(buddy):
    async with buddy.klient() as k:
        await k.post(f"{V1}/connections", json={"name": "egen", "system": "generisk"})
        korning = (await k.post(f"{V1}/sync/companies", json={"connection": "egen", "items": _SATS})).json()["run"]
        enkelt = {(i["kind"], i["field"]): i["count"] for i in korning["issues"]}
        assert enkelt == {("ogiltigt_varde", "phone"): 2, ("ogiltigt_varde", "email"): 1,
                          ("saknar_uppgift", None): 1, ("privatperson", None): 1}
        assert all(i["object"] == "company" for i in korning["issues"])
        assert korning["support"]["forwarded_at"] and korning["support"]["ticket"] is None
        # Och det står kvar när körningen läses igen.
        igen = (await k.get(f"{V1}/sync/runs/{korning['id']}")).json()
        assert igen["support"] == korning["support"] and igen["issues"] == korning["issues"]


async def test_en_korning_utan_fel_gar_inte_till_supporten(buddy):
    async with buddy.klient() as k:
        await k.post(f"{V1}/connections", json={"name": "egen", "system": "generisk"})
        # En privatperson som hoppas över är avsedd, inget fel.
        korning = (await k.post(f"{V1}/sync/companies", json={"connection": "egen", "items": [
            _SATS[0], _SATS[4]]})).json()["run"]
        assert korning["support"] is None
        assert [i["kind"] for i in korning["issues"]] == ["privatperson"]


async def test_supporten_far_hela_rapporten_utan_de_felaktiga_vardena(app, buddy, annan):
    async with buddy.klient() as k:
        await k.post(f"{V1}/connections", json={"name": "egen", "system": "generisk",
                                                "mapping": {"bolag": {"telefon": "phone"}}})
        korning = (await k.post(f"{V1}/sync/companies", json={"connection": "egen", "items": _SATS})).json()["run"]
    async with annan.klient() as k:
        await k.post(f"{V1}/connections", json={"name": "ren", "system": "generisk"})
        await k.post(f"{V1}/sync/companies", json={"connection": "ren", "items": [_SATS[0]]})
    async with _master(app) as admin:
        listan = (await admin.get("/api/admin/crm/supportrapporter")).json()["rapporter"]
        assert [(r["kund"], r["korning_id"], r["arende"]) for r in listan] == [("Buddy", korning["id"], None)]
        assert listan[0]["koder"] == {"epost_ogiltig": 1, "saknar_namn": 1, "telefon_saknar_landskod": 1,
                                      "telefon_saknar_riktnummer": 1}
        svar = (await admin.get(f"/api/admin/crm/supportrapporter/{buddy.id}/{korning['id']}")).json()
        rapport = svar["rapport"]
        assert rapport["kund"] == "Buddy" and rapport["korning"]["raknare"]["totalt"] == 5
        assert rapport["anslutning"]["system"] == "generisk"
        assert rapport["anslutning"]["egen_mappning"] == {"bolag": {"telefon": "phone"}}
        rader = {r["externt_id"]: r for r in rapport["rader"]}
        # Privatpersonen är ingen felrad, och ingenting av henne står i rapporten.
        assert set(rader) == {"2", "3", "4"} and "Anna Berg" not in json.dumps(rapport) and "anna@" not in json.dumps(rapport)
        former = {f["falt"]: f["form"] for f in rader["2"]["faltfel"]}
        assert former == {"telefon": "99 99 99 9", "epost": "aaaa aa aaaaaa"}
        assert "12 34" not in json.dumps(rapport) and "inte en adress" not in json.dumps(rapport)
        assert rader["2"]["namn"] == "Fel Telefon AB" and rader["4"]["orsak"] == "saknar_namn"
        # Supportsystemet svarar med ärendets nummer, och kunden ser det.
        satt = await admin.post(f"/api/admin/crm/supportrapporter/{buddy.id}/{korning['id']}/arende",
                                json={"nummer": "F-7KQ2"})
        assert satt.status_code == 200 and satt.json()["arende"] == "F-7KQ2"
        assert (await admin.get("/api/admin/crm/supportrapporter", params={"utan_arende": "true"})).json() == {
            "rapporter": []}
        # Fel kund eller okänd körning finns inte.
        assert (await admin.get(f"/api/admin/crm/supportrapporter/{annan.id}/{korning['id']}")).status_code == 404
    async with buddy.klient() as k:
        assert (await k.get(f"{V1}/sync/runs/{korning['id']}")).json()["support"]["ticket"] == "F-7KQ2"
        # Adminvägen kräver huvudnyckeln: kundens nyckel når den inte.
        assert (await k.get("/api/admin/crm/supportrapporter")).status_code == 403


async def test_krockar_och_en_fallen_full_synk_gar_ocksa_vidare(buddy):
    async with buddy.klient() as k:
        await k.post(f"{V1}/connections", json={"name": "egen", "system": "generisk", "missing_records": "delete"})
        await k.post(f"{V1}/sync/companies", json={"connection": "egen", "items": [
            {"id": "1", "name": "Ett AB", "org_number": ORGNR_A}, {"id": "2", "name": "Två AB", "org_number": ORGNR_B}]})
        krock = (await k.post(f"{V1}/sync/companies", json={"connection": "egen", "items": [
            {"id": "2", "name": "Två AB", "org_number": ORGNR_A}]})).json()["run"]
        assert krock["support"] and [(i["kind"], i["count"]) for i in krock["issues"]] == [("dubblett", 1)]
        # En full synk utan poster faller i stället för att tömma registret.
        run = (await k.post(f"{V1}/sync/runs", json={"connection": "egen", "mode": "full"})).json()
        tom = (await k.post(f"{V1}/sync/runs/{run['id']}/complete")).json()
        assert tom["status"] == "failed" and tom["error"] == "tom_full_synk" and tom["support"]["forwarded_at"]


def test_formen_bar_inget_av_innehallet():
    assert supportrapport.form("070-123 45 67") == "999-999 99 99"
    assert supportrapport.form("Åsa.Öberg@bolaget.se") == "aaa.aaaaa@aaaaaaa.aa"
    assert supportrapport.form(None) is None and len(supportrapport.form("x" * 500)) == 80
