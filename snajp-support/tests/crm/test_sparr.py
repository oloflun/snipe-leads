"""Den gemensamma spärren för alla kanaler, NIX-importen och de tunna
webhookarna för personer (migration 166, app/crm/sparr.py).
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

import httpx
import pytest

from app.crm import lagring, sparr, webhooks
from app.integrationer import natvakt
from app.leads import samtal, scheduler

from .conftest import ORGNR_A, ORGNR_B

V1 = "/api/crm/v1"
pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def _rent():
    webhooks.nollstall()
    yield
    webhooks.nollstall()


class Mottagare:
    def __init__(self) -> None:
        self.anrop: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.anrop.append(request)
        return httpx.Response(200, json={"ok": True})

    def kroppar(self) -> list[dict]:
        return [json.loads(a.content) for a in self.anrop]


@pytest.fixture
def mottagare(monkeypatch) -> Mottagare:
    m = Mottagare()

    async def dns(vard: str, port: int) -> list[str]:
        return ["93.184.216.34"]

    monkeypatch.setattr(natvakt, "upplos", dns)
    monkeypatch.setattr(natvakt, "inre_transport", lambda: httpx.MockTransport(m))
    return m


async def _sparra(k, **kropp) -> dict:
    svar = await k.post(f"{V1}/suppressions", json={"reason": "objection", **kropp})
    assert svar.status_code in (200, 201), svar.text
    return svar.json()


async def _kolla(k, **kropp) -> dict:
    svar = await k.post(f"{V1}/suppressions/check", json=kropp)
    assert svar.status_code == 200, svar.text
    return svar.json()


async def _lead(storage, tenant_id: str, namn: str, *, epost: str, orgnr: str | None = None,
                status: str | None = None, telefon: str | None = None, origin: str = "manual") -> dict:
    p = await storage.create_prospect(tenant_id, company_name=namn, contact_email=epost, origin=origin,
                                      profil={"contact_phone": telefon} if telefon else None)
    andring = {**({"orgnr": orgnr} if orgnr else {}), **({"status": status} if status else {})}
    if andring:
        await storage.update_prospect(tenant_id, p["id"], **andring)
    return await storage.get_prospect(tenant_id, p["id"])


# -- Spärrlistan och kanalerna -----------------------------------------------


async def test_sparren_galler_i_sin_kanal_och_alla_galler_bada(buddy):
    async with buddy.klient() as k:
        tel = await _sparra(k, channel="phone", kind="phone", value="070-123 45 67", reason="nix")
        assert (tel["value"], tel["channel"], tel["kind"], tel["reason"]) == ("+46701234567", "phone", "phone", "nix")
        assert tel["source"] == "api" and tel["lifted_at"] is None
        # En telefonspärr stoppar inte mejl.
        assert (await _kolla(k, channel="phone", phone="+46 70 123 45 67"))["blocked"] is True
        assert (await _kolla(k, channel="email", phone="070-1234567"))["blocked"] is False
        # Alla stoppar båda kanalerna.
        await _sparra(k, channel="all", kind="email", value="VD@Bygg.se")
        for kanal in ("email", "all"):
            svar = await _kolla(k, channel=kanal, email="vd@bygg.se")
            assert svar == {"blocked": True, "sources": ["suppression_list"], "suppression_ids": svar["suppression_ids"]}
        await _sparra(k, channel="all", kind="phone", value="08-123 456 78")
        assert (await _kolla(k, channel="email", phone="08-12345678"))["blocked"] is True
        # Frågan `all` säger om något alls spärrar, i någon kanal.
        assert (await _kolla(k, channel="all", phone="0701234567"))["blocked"] is True


async def test_en_domansparr_stoppar_varje_adress_pa_domanen(buddy, storage):
    async with buddy.klient() as k:
        dom = await _sparra(k, channel="email", kind="domain", value="https://www.Konkurrent.se/om-oss")
        assert dom["value"] == "konkurrent.se"
        for adress in ("vd@konkurrent.se", "info@KONKURRENT.se"):
            assert (await _kolla(k, channel="email", email=adress))["blocked"] is True
        assert (await _kolla(k, channel="email", email="vd@annan.se"))["blocked"] is False
        assert (await _kolla(k, channel="email", email="vd@sub.konkurrent.se"))["blocked"] is False
    # Sändspärren prövar domänen innan något annat om mottagaren.
    beslut = await scheduler._kor_send_guard(storage, buddy.id, {"prospect_email": "Ny@konkurrent.se"}, {},
                                             now=datetime.now(timezone.utc))
    assert (beslut.atgard, beslut.regel) == (scheduler.SG_BLOCKERA, "sparrad_doman")


async def test_organisationsnummer_och_ogiltiga_varden(buddy):
    async with buddy.klient() as k:
        org = await _sparra(k, channel="all", kind="org_number", value="5560360793")
        assert org["value"] == ORGNR_A
        assert (await _kolla(k, channel="phone", org_number=ORGNR_A))["blocked"] is True
        # Samma spärr igen: 200 och den som redan gäller.
        igen = await k.post(f"{V1}/suppressions", json={"channel": "all", "kind": "org_number",
                                                         "value": ORGNR_A, "reason": "other"})
        assert igen.status_code == 200 and igen.json()["id"] == org["id"]
        for kropp, falt, kod in (
            ({"channel": "phone", "kind": "phone", "value": "123"}, "value", "telefon_saknar_landskod"),
            ({"channel": "email", "kind": "email", "value": "inte en adress"}, "value", "epost_ogiltig"),
            ({"channel": "all", "kind": "org_number", "value": "556036-0794"}, "value", "orgnr_kontrollsiffra"),
            # En enskild firmas nummer är ett personnummer och sparas aldrig.
            ({"channel": "all", "kind": "org_number", "value": "800101-1231"}, "value", "orgnr_ar_personnummer"),
            ({"channel": "phone", "kind": "email", "value": "a@b.se"}, "kind", "slag_passar_inte_kanalen"),
            ({"channel": "email", "kind": "phone", "value": "070-123 45 67"}, "kind", "slag_passar_inte_kanalen"),
        ):
            svar = await k.post(f"{V1}/suppressions", json={"reason": "other", **kropp})
            assert svar.status_code == 422, kropp
            assert svar.json()["detail"]["code"] == "invalid_fields"
            assert svar.json()["detail"]["fields"] == [{"field": falt, "code": kod}], kropp
        svar = await k.post(f"{V1}/suppressions/check", json={"channel": "email"})
        assert svar.status_code == 422 and svar.json()["detail"]["fields"][0]["code"] == "varde_saknas"


# -- Varje källa för sig ------------------------------------------------------


async def test_posten_markt_kontakta_inte_sparrar_utan_att_kopieras(buddy, storage):
    async with buddy.klient() as k:
        bolag = (await k.post(f"{V1}/companies", json={"name": "Tyst AB", "org_number": ORGNR_A,
                                                       "phone": "08-123 456 78", "do_not_contact": True})).json()
        await k.post(f"{V1}/people", json={"email": "anna@tyst.se", "mobile": "070-111 22 33",
                                           "company_id": bolag["id"]})
        await k.post(f"{V1}/people", json={"email": "bo@fri.se", "do_not_contact": True})
        for kropp in ({"email": "anna@tyst.se"}, {"phone": "0701112233"}, {"org_number": ORGNR_A},
                      {"phone": "08-12345678"}, {"email": "bo@fri.se"}):
            assert (await _kolla(k, channel="phone", **kropp))["sources"] == ["record"], kropp
        # Ingenting har kopierats till listan.
        assert (await k.get(f"{V1}/suppressions")).json()["data"] == []
    assert await sparr.sparrade_nummer(storage, buddy.id) == {"+46812345678", "+46701112233"}


async def test_avregistreringen_sparrar_bara_mejl(buddy, storage):
    await storage.add_suppression(buddy.id, email="ut@bygg.se", reason="avregistrering")
    async with buddy.klient() as k:
        assert (await _kolla(k, channel="email", email="UT@bygg.se"))["sources"] == ["unsubscribed"]
        assert (await _kolla(k, channel="phone", email="ut@bygg.se"))["blocked"] is False


async def test_leadet_som_bett_att_slippa_sparrar_pa_adress_och_orgnr(buddy, storage):
    await _lead(storage, buddy.id, "Nej AB", epost="vd@nej.se", orgnr=ORGNR_B, status="suppressed")
    await _lead(storage, buddy.id, "Ja AB", epost="vd@ja.se", orgnr=ORGNR_A, status="contacted")
    async with buddy.klient() as k:
        assert (await _kolla(k, channel="phone", email="vd@nej.se"))["sources"] == ["lead"]
        assert (await _kolla(k, channel="phone", org_number=ORGNR_B))["sources"] == ["lead"]
        assert (await _kolla(k, channel="email", email="vd@ja.se", org_number=ORGNR_A))["blocked"] is False


async def test_en_havd_sparr_star_kvar_men_galler_inte(buddy, annan):
    async with buddy.klient() as k:
        rad = await _sparra(k, channel="email", kind="email", value="vd@bygg.se", note="Ringde och bad oss sluta.")
        assert (await k.delete(f"{V1}/suppressions/{rad['id']}")).status_code == 204
        assert (await _kolla(k, channel="email", email="vd@bygg.se"))["blocked"] is False
        assert (await k.get(f"{V1}/suppressions")).json()["data"] == []
        (havd,) = (await k.get(f"{V1}/suppressions", params={"include_lifted": "true"})).json()["data"]
        assert havd["lifted_at"] and havd["lifted_by"].startswith("nyckel:") and havd["note"] == "Ringde och bad oss sluta."
        # Att häva igen ändrar ingenting, och en ny spärr på samma adress går att lägga.
        assert (await k.delete(f"{V1}/suppressions/{rad['id']}")).status_code == 204
        ny = await k.post(f"{V1}/suppressions", json={"channel": "email", "kind": "email", "value": "vd@bygg.se",
                                                       "reason": "unsubscribe"})
        assert ny.status_code == 201 and ny.json()["id"] != rad["id"]
        assert (await k.delete(f"{V1}/suppressions/inte-ett-id")).status_code == 404
    # Den andra kunden kan varken se eller häva Buddys spärr.
    async with annan.klient() as k:
        svar = await k.delete(f"{V1}/suppressions/{ny.json()['id']}")
        assert svar.status_code == 404 and svar.json()["detail"]["code"] == "suppression_not_found"


async def test_den_andra_kundens_sparr_galler_aldrig_har(buddy, annan, storage):
    async with annan.klient() as k:
        await _sparra(k, channel="all", kind="email", value="vd@bygg.se")
        await _sparra(k, channel="all", kind="domain", value="bygg.se")
        await _sparra(k, channel="phone", kind="phone", value="070-123 45 67")
    await storage.add_suppression(annan.id, email="vd@bygg.se", reason="avregistrering")
    async with buddy.klient() as k:
        assert (await _kolla(k, channel="all", email="vd@bygg.se", phone="0701234567"))["blocked"] is False
        assert (await k.get(f"{V1}/suppressions")).json()["data"] == []
    assert await lagring.kontakta_inte_adresser(storage, buddy.id) == set()
    assert await sparr.sparrade_domaner(storage, buddy.id) == set()
    assert await sparr.sparrade_nummer(storage, buddy.id) == set()


# -- Listan, importen och omfången --------------------------------------------


async def test_importen_raknar_dubbletter_ogiltiga_och_redan_sparrade(buddy):
    async with buddy.klient() as k:
        await _sparra(k, channel="phone", kind="phone", value="070-123 45 67", reason="nix")
        svar = await k.post(f"{V1}/suppressions/import", json={"channel": "phone", "reason": "nix", "values": [
            "0701234567", "070-765 43 21", "+46707654321", "123", "", "08-555 666 77"]})
        assert svar.status_code == 200, svar.text
        assert svar.json() == {"added": 2, "already_blocked": 2,
                               "invalid": [{"index": 3, "code": "telefon_saknar_landskod"},
                                           {"index": 4, "code": "varde_saknas"}]}
        nix = (await k.get(f"{V1}/suppressions", params={"reason": "nix", "limit": 2})).json()
        assert len(nix["data"]) == 2 and nix["next_cursor"]
        rest = (await k.get(f"{V1}/suppressions", params={"reason": "nix", "cursor": nix["next_cursor"]})).json()
        assert len(rest["data"]) == 1 and rest["next_cursor"] is None
        assert {s["source"] for s in nix["data"] + rest["data"]} == {"api", "import"}
        # Utan kind: en adress med @ är e-post, annars en domän i mejlkanalen.
        svar = await k.post(f"{V1}/suppressions/import", json={"channel": "email", "reason": "bounce",
                                                                 "values": ["a@b.se", "@c.se", "inte domän"]})
        assert svar.json() == {"added": 2, "already_blocked": 0, "invalid": [{"index": 2, "code": "doman_ogiltig"}]}
        assert {s["kind"] for s in (await k.get(f"{V1}/suppressions", params={"channel": "email"})).json()["data"]} == {
            "email", "domain"}
        assert len((await k.get(f"{V1}/suppressions", params={"q": "c.se"})).json()["data"]) == 1
        # Taket: högst 10 000 värden per anrop.
        svar = await k.post(f"{V1}/suppressions/import", json={"channel": "phone", "reason": "nix",
                                                                 "values": ["0701234567"] * (sparr.MAX_IMPORT + 1)})
        assert svar.status_code == 422 and svar.json()["detail"]["code"] == "too_many_items"


async def test_lasning_kraver_crm_las_och_skrivning_crm_skriv(buddy, utan_avtal):
    las = await buddy.ny_nyckel(["crm:las"])
    async with buddy.klient(las) as k:
        assert (await k.get(f"{V1}/suppressions")).status_code == 200
        assert (await _kolla(k, channel="email", email="a@b.se"))["blocked"] is False
        svar = await k.post(f"{V1}/suppressions", json={"channel": "email", "kind": "email", "value": "a@b.se",
                                                         "reason": "other"})
        assert svar.status_code == 403 and svar.json()["detail"]["code"] == "scope_missing"
    async with utan_avtal.klient() as k:
        svar = await k.post(f"{V1}/suppressions/import", json={"channel": "phone", "reason": "nix", "values": []})
        assert svar.status_code == 403 and svar.json()["detail"]["code"] == "agreement_missing"


# -- Utfallet, sändspärren och ringlistan --------------------------------------


async def test_utfallet_kontakta_inte_lagger_sparrar_i_alla_kanaler(buddy, storage):
    async with buddy.klient() as k:
        bolag = (await k.post(f"{V1}/companies", json={"name": "Bygg AB", "org_number": ORGNR_A,
                                                       "email": "info@bygg.se", "phone": "08-123 456 78"})).json()
        assert (await k.post(f"{V1}/companies/{bolag['id']}/outcome",
                             json={"outcome": "do_not_contact"})).status_code == 200
        rader = (await k.get(f"{V1}/suppressions")).json()["data"]
        assert sorted((r["kind"], r["value"]) for r in rader) == [
            ("email", "info@bygg.se"), ("org_number", ORGNR_A), ("phone", "+46812345678")]
        assert {(r["channel"], r["reason"], r["source"], r["company_id"]) for r in rader} == {
            ("all", "customer_request", "outcome", bolag["id"])}
        # Utfallet igen lägger inga dubbletter.
        await k.post(f"{V1}/companies/{bolag['id']}/outcome", json={"outcome": "do_not_contact"})
        assert len((await k.get(f"{V1}/suppressions")).json()["data"]) == 3
        # Spärren står kvar om märkningen tas bort från posten.
        await k.patch(f"{V1}/companies/{bolag['id']}", json={"do_not_contact": False})
        assert (await _kolla(k, channel="phone", phone="08-123 456 78"))["sources"] == ["suppression_list"]


async def test_sandsparrens_mangd_innehaller_sparrlistan(buddy, storage):
    async with buddy.klient() as k:
        await _sparra(k, channel="email", kind="email", value="ett@bygg.se")
        await _sparra(k, channel="all", kind="email", value="tva@bygg.se")
        havd = await _sparra(k, channel="email", kind="email", value="havd@bygg.se")
        await k.delete(f"{V1}/suppressions/{havd['id']}")
        await _sparra(k, channel="email", kind="domain", value="konkurrent.se")
    adresser = await lagring.kontakta_inte_adresser(storage, buddy.id)
    assert adresser == {"ett@bygg.se", "tva@bygg.se"}
    assert await sparr.sparrade_domaner(storage, buddy.id) == {"konkurrent.se"}
    assert "tva@bygg.se" in await sparr.sparrade_adresser(storage, buddy.id)


async def test_ringlistan_tappar_sparrade_nummer_och_orgnr(buddy, storage):
    fri = await _lead(storage, buddy.id, "Fri AB", epost="vd@fri.se", telefon="070-555 00 01", origin="ring")
    nix = await _lead(storage, buddy.id, "Nix AB", epost="vd@nix.se", telefon="0705550002", origin="ring")
    org = await _lead(storage, buddy.id, "Org AB", epost="vd@org.se", orgnr=ORGNR_B, telefon="0705550003",
                      origin="ring")
    async with buddy.klient() as k:
        await k.post(f"{V1}/suppressions/import", json={"channel": "phone", "reason": "nix", "values": ["+46705550002"]})
        await _sparra(k, channel="phone", kind="org_number", value=ORGNR_B)
        # En mejlspärr på samma bolag stoppar inte samtalet.
        await _sparra(k, channel="email", kind="email", value="vd@fri.se")
    nummer, orgnr = await sparr.sparrade_nummer(storage, buddy.id), await sparr.sparrade_orgnr(storage, buddy.id)
    prospekter = [fri, nix, org]
    rader = samtal.samtalslista(prospekter, [], {}, lista="ring", idag=date.today(),
                                sparrade_nummer=nummer, sparrade_orgnr=orgnr)
    assert [r["company_name"] for r in rader] == ["Fri AB"]
    # Utan spärren står alla tre kvar, som förut.
    assert len(samtal.samtalslista(prospekter, [], {}, lista="ring", idag=date.today())) == 3


# -- Händelser och webhooks ----------------------------------------------------


async def test_sparrens_handelser_bar_aldrig_vardet_eller_anteckningen(buddy, storage, mottagare):
    async with buddy.klient() as k:
        hake = (await k.post(f"{V1}/webhooks", json={"url": "https://kund.example.se/snajp",
                                                      "events": ["suppression.created", "suppression.lifted"]})).json()
        assert {"suppression.created", "suppression.lifted"} <= set(
            (await k.get(f"{V1}/webhooks/events")).json()["events"])
        rad = await _sparra(k, channel="all", kind="email", value="hemlig@bygg.se", note="Bad oss sluta, arg.")
        await k.post(f"{V1}/suppressions/import", json={"channel": "phone", "reason": "nix", "values": ["0709998877"]})
        await k.delete(f"{V1}/suppressions/{rad['id']}")
        await webhooks.kor_varv(storage)
        kroppar = mottagare.kroppar()
        assert [b["type"] for b in kroppar] == ["suppression.created", "suppression.created", "suppression.lifted"]
        last = kroppar[0]["data"]
        assert last["object"] == "suppression" and last["id"] == rad["id"]
        assert set(last["record"]) == {"id", "channel", "kind", "reason", "source", "created_at", "lifted_at"}
        assert kroppar[2]["data"]["record"]["lifted_at"]
        flode = (await k.get(f"{V1}/changes", params={"object": "suppression"})).json()["data"]
        assert [(h["object"], h["type"]) for h in flode] == [
            ("suppression", "created"), ("suppression", "created"), ("suppression", "lifted")]
        loggen = (await k.get(f"{V1}/webhooks/{hake['id']}/deliveries")).json()
    allt = json.dumps([kroppar, flode, loggen, storage._crm_handelser], default=str, ensure_ascii=False)
    for hemligt in ("hemlig@bygg.se", "Bad oss sluta", "+46709998877", "0709998877"):
        assert hemligt not in allt


async def test_personer_och_enskilda_firmor_gar_ut_tunna(buddy, storage, mottagare):
    async with buddy.klient() as k:
        await k.post(f"{V1}/webhooks", json={"url": "https://kund.example.se/snajp"})
        person = (await k.post(f"{V1}/people", json={"first_name": "Anna", "email": "anna@bygg.se"})).json()
        await k.patch(f"{V1}/people/{person['id']}", json={"title": "VD", "phone": "070-123 45 67"})
        # En enskild firma kommer in genom synken, utan sitt nummer (beslutet 2026-11-23).
        await k.post(f"{V1}/connections", json={"name": "egen", "system": "generisk"})
        ut = (await k.post(f"{V1}/sync/companies", json={"connection": "egen", "items": [
            {"id": "1", "name": "Annas Måleri", "org_number": "800101-1231"}]})).json()
        firma = (await k.get(f"{V1}/companies/{ut['items'][0]['id']}")).json()
        bolag = (await k.post(f"{V1}/companies", json={"name": "Bygg AB", "org_number": ORGNR_A})).json()
        await webhooks.kor_varv(storage)
    kroppar = {(b["type"], b["data"]["id"]): b["data"] for b in mottagare.kroppar()}
    skapad = kroppar[("person.created", person["id"])]
    assert set(skapad) == {"id", "object", "type", "occurred_at", "fields"}
    assert skapad["object"] == "person" and skapad["type"] == "person.created" and skapad["fields"] == []
    andrad = kroppar[("person.updated", person["id"])]
    assert andrad["fields"] == ["phone", "title"]
    assert firma["sole_proprietor"] is True
    assert "record" not in kroppar[("company.created", firma["id"])]
    # Ett vanligt bolag bär hela posten som förut.
    assert kroppar[("company.created", bolag["id"])]["record"]["org_number"] == ORGNR_A
    allt = json.dumps(mottagare.kroppar(), ensure_ascii=False)
    for hemligt in ("Anna", "anna@bygg.se", "+46701234567", "VD", "Annas Måleri"):
        assert hemligt not in allt
